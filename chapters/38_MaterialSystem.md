\newpage

# Chapter 38: Material System

Build a flexible material abstraction layer that encapsulates shaders, parameters, and textures, preparing for component-based rendering in the ECS architecture.

---

## Introduction

In **Chapters 33-37**, we implemented physically-based rendering, image-based lighting, HDR pipeline, bloom, and color grading. Our rendering is now production-quality—but there's a significant architectural problem hiding in `SandboxApp.cpp`.

**The problem**: Every render call manually sets shader uniforms:

```cpp
// Current approach: ~15 lines of uniform setup PER OBJECT
m_DefaultLitShader->Bind();
m_DefaultLitShader->SetMatrix4fv("u_Model", model);
m_DefaultLitShader->SetVec3("u_Albedo", glm::vec3(obj.Color));
m_DefaultLitShader->SetFloat("u_Metallic", obj.Metallic);
m_DefaultLitShader->SetFloat("u_Roughness", obj.Roughness);
m_DefaultLitShader->SetFloat("u_AO", 1.0f);
m_DefaultLitShader->SetBool("u_UseAlbedoTexture", obj.TexturePtr != nullptr);
// ... shadow uniforms, IBL uniforms, light uniforms, etc.
```

**Consequences**:
- **Duplication**: Same uniform-setting code repeated across render passes
- **Error-prone**: Miss one uniform? Silent rendering bugs
- **Inflexible**: Adding a new material property requires editing multiple places
- **Not scalable**: 1000 objects = 15,000 uniform calls per frame

**The solution**: A **Material System** that:
1. Encapsulates shader and material parameters together
2. Provides a single `Bind()` call that sets all uniforms
3. Supports different material types (lit, unlit, transparent)
4. Prepares for the ECS `MeshRenderer` component (Part XI)

```cpp
// After: One line
material->Bind();
material->SetTransform(model);
```

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **RenderMaterial Class** | Encapsulates shader + parameters + textures |
| **Material Parameters** | Type-safe storage for floats, vectors, textures |
| **PBR Material** | Pre-configured material for physically-based rendering |
| **Unlit Material** | Simple material for UI elements and debug rendering |
| **Material Instance** | Share shaders but override individual parameters |
| **Bind Pattern** | Single `Bind()` call uploads all uniforms to GPU |
| **SceneObject Integration** | Replace inline uniforms with material references |

**Architectural Impact**: This chapter bridges manual rendering (Chapters 1-37) to the production ECS architecture (Chapter 39+). Materials become components that can be attached to entities.

---

## Design Goals

### Why Abstract Materials?

Consider the current rendering code flow:

```
Application Code                     GPU
     │                                │
     ├─→ Bind Shader ────────────────→│
     ├─→ Set u_Albedo ───────────────→│
     ├─→ Set u_Metallic ─────────────→│
     ├─→ Set u_Roughness ────────────→│
     ├─→ Set u_AO ───────────────────→│
     ├─→ Bind Texture 0 ─────────────→│
     ├─→ Bind Texture 1 ─────────────→│
     ├─→ ... (12+ more uniforms) ───→│
     │                                │
```

With a Material System:

```
Application Code                     GPU
     │                                │
     ├─→ RenderMaterial::Bind() ─────→│ (encapsulates all uniforms)
     │                                │
```

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Encapsulation** | Hide shader uniform details from application code |
| **Composition** | Materials compose shader + parameters + textures |
| **Type Safety** | Compile-time or runtime checks for parameter types |
| **Extensibility** | Easy to add new material types without modifying core |
| **Performance** | Minimize state changes, sort by material for batching |

---

## Material System Architecture

### Class Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    RenderMaterial (Base Class)                   │
│  - Shader reference                                              │
│  - Parameter storage (map<string, variant>)                      │
│  - Texture slots                                                 │
│  - Bind() / Unbind()                                             │
│  - SetParameter() / GetParameter()                               │
└─────────────────────────────────────────────────────────────────┘
                              ↑
          ┌───────────────────┼───────────────────┐
          │                   │                   │
┌─────────┴─────────┐ ┌──────┴──────┐ ┌─────────┴─────────┐
│   PBRMaterial     │ │UnlitMaterial│ │  Custom Materials │
│ - Albedo          │ │ - Color     │ │ - User defined    │
│ - Metallic        │ │ - Texture   │ │                   │
│ - Roughness       │ │             │ │                   │
│ - Normal map      │ │             │ │                   │
│ - IBL references  │ │             │ │                   │
└───────────────────┘ └─────────────┘ └───────────────────┘
```

### Data Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────────┐
│RenderMaterial│──────│   Shader    │──────│  GPU Program    │
│  Instance   │      │  (shared)   │      │  (compiled)     │
└─────────────┘      └─────────────┘      └─────────────────┘
       │                    │
       │  SetParameter()    │  Bind()
       ▼                    ▼
┌─────────────┐      ┌─────────────────┐
│  Parameter  │      │    Uniform      │
│   Storage   │─────→│   Upload        │
└─────────────┘      └─────────────────┘
```

---

## TextureSlots Constants

Before implementing materials, we define standardized texture slot assignments. This prevents slot collisions between different texture types and makes the code self-documenting.

**The constants are defined in** `VizEngine/src/VizEngine/OpenGL/Commons.h`:

```cpp
namespace VizEngine
{
    /**
     * Standard texture slot assignments for PBR rendering.
     * Use these constants to avoid slot collisions between materials and manual binding.
     */
    namespace TextureSlots
    {
        // Material textures (0-4)
        constexpr int Albedo = 0;
        constexpr int Normal = 1;
        constexpr int MetallicRoughness = 2;
        constexpr int AO = 3;
        constexpr int Emissive = 4;

        // IBL textures (5-7)
        constexpr int Irradiance = 5;
        constexpr int Prefiltered = 6;
        constexpr int BRDF_LUT = 7;

        // Shadow map (8)
        constexpr int ShadowMap = 8;

        // Post-processing (9-11)
        constexpr int HDRBuffer = 9;
        constexpr int BloomTexture = 10;
        constexpr int ColorGradingLUT = 11;

        // User/custom (12-15)
        constexpr int Custom0 = 12;
        constexpr int Custom1 = 13;
        constexpr int Custom2 = 14;
        constexpr int Custom3 = 15;
    }
}
```

> [!TIP]
> **Why standardized slots?** OpenGL has 16 texture units (0-15). By defining constants, we ensure materials, IBL, shadows, and post-processing never accidentally use the same slot. This eliminates a common source of rendering bugs.

---

## Step 1: Create MaterialParameter Type

We need a type-safe way to store different parameter types (float, vec3, vec4, int, textures).

**Create** `VizEngine/src/VizEngine/Renderer/MaterialParameter.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/MaterialParameter.h

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"
#include <variant>
#include <memory>
#include <string>

namespace VizEngine
{
    class Texture;

    /**
     * Type-safe storage for material parameter values.
     * Supports common shader uniform types.
     */
    using MaterialParameterValue = std::variant<
        float,
        int,
        bool,
        glm::vec2,
        glm::vec3,
        glm::vec4,
        glm::mat3,
        glm::mat4,
        std::shared_ptr<Texture>
    >;

    /**
     * Texture slot binding information.
     * Handles both 2D textures and cubemaps via the IsCubemap flag.
     */
    struct VizEngine_API TextureSlot
    {
        std::string UniformName;            // e.g., "u_AlbedoTexture"
        std::shared_ptr<Texture> TextureRef;
        int Slot = 0;                       // Texture unit (0-15)
        bool IsCubemap = false;             // True if texture is a cubemap

        TextureSlot() = default;
        TextureSlot(const std::string& name, std::shared_ptr<Texture> tex, int slot, bool isCube = false)
            : UniformName(name), TextureRef(tex), Slot(slot), IsCubemap(isCube) {}
    };
}
```

> [!NOTE]
> We use `std::variant` (C++17) for type-safe parameter storage. This provides compile-time checking while allowing flexible parameter types.

---

## Step 2: Create RenderMaterial Base Class

**Create** `VizEngine/src/VizEngine/Renderer/RenderMaterial.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/RenderMaterial.h

#pragma once

#include "VizEngine/Core.h"
#include "VizEngine/Renderer/MaterialParameter.h"
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace VizEngine
{
    class Shader;
    class Texture;

    /**
     * RenderMaterial encapsulates a shader and its parameters.
     * Provides a single Bind() call that sets all uniforms.
     *
     * Usage:
     *   auto material = std::make_shared<RenderMaterial>(shader);
     *   material->SetFloat("u_Roughness", 0.5f);
     *   material->SetTexture("u_AlbedoTexture", texture, 0);
     *
     *   // In render loop:
     *   material->Bind();
     *   // Render mesh...
     *
     * Note: Named "RenderMaterial" to avoid conflict with existing Material struct
     *       used for glTF model loading.
     */
    class VizEngine_API RenderMaterial
    {
    public:
        /**
         * Create material with shader.
         * @param shader Shader program to use for rendering
         * @param name Optional material name for debugging
         */
        RenderMaterial(std::shared_ptr<Shader> shader, const std::string& name = "Unnamed");
        virtual ~RenderMaterial() = default;

        // =====================================================================
        // Core Operations
        // =====================================================================

        /**
         * Bind shader and upload all parameters to GPU.
         * Call this before rendering with this material.
         */
        virtual void Bind();

        /**
         * Unbind shader (optional, for explicit state management).
         */
        virtual void Unbind();

        // =====================================================================
        // Parameter Setters (Type-safe)
        // =====================================================================

        void SetFloat(const std::string& name, float value);
        void SetInt(const std::string& name, int value);
        void SetBool(const std::string& name, bool value);
        void SetVec2(const std::string& name, const glm::vec2& value);
        void SetVec3(const std::string& name, const glm::vec3& value);
        void SetVec4(const std::string& name, const glm::vec4& value);
        void SetMat3(const std::string& name, const glm::mat3& value);
        void SetMat4(const std::string& name, const glm::mat4& value);

        // =====================================================================
        // Texture Binding
        // =====================================================================

        /**
         * Set texture for a uniform sampler.
         * @param name Uniform name (e.g., "u_AlbedoTexture")
         * @param texture Texture to bind
         * @param slot Texture unit (0-15)
         * @param isCubemap True if texture is a cubemap
         */
        void SetTexture(const std::string& name, std::shared_ptr<Texture> texture, int slot, bool isCubemap = false);

        // =====================================================================
        // Parameter Query
        // =====================================================================

        template<typename T>
        T GetParameter(const std::string& name, const T& defaultValue = T{}) const
        {
            auto it = m_Parameters.find(name);
            if (it != m_Parameters.end())
            {
                if (auto* value = std::get_if<T>(&it->second))
                {
                    return *value;
                }
            }
            return defaultValue;
        }

        bool HasParameter(const std::string& name) const;

        // =====================================================================
        // Accessors
        // =====================================================================

        const std::string& GetName() const { return m_Name; }
        void SetName(const std::string& name) { m_Name = name; }

        std::shared_ptr<Shader> GetShader() const { return m_Shader; }
        void SetShader(std::shared_ptr<Shader> shader) { m_Shader = shader; }

        bool IsValid() const { return m_Shader != nullptr; }

    protected:
        /**
         * Upload all stored parameters to the shader.
         * Override in derived classes for custom upload logic.
         */
        virtual void UploadParameters();

        /**
         * Bind all textures to their slots.
         */
        virtual void BindTextures();

    protected:
        std::string m_Name;
        std::shared_ptr<Shader> m_Shader;

        // Parameter storage
        std::unordered_map<std::string, MaterialParameterValue> m_Parameters;

        // Texture bindings (handles both 2D textures and cubemaps)
        std::vector<TextureSlot> m_TextureSlots;
    };
}
```

---

## Step 3: Implement RenderMaterial Base Class

**Create** `VizEngine/src/VizEngine/Renderer/RenderMaterial.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/RenderMaterial.cpp

#include "RenderMaterial.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    RenderMaterial::RenderMaterial(std::shared_ptr<Shader> shader, const std::string& name)
        : m_Shader(shader), m_Name(name)
    {
        if (!m_Shader)
        {
            VP_CORE_WARN("RenderMaterial '{}' created with null shader", name);
        }
    }

    void RenderMaterial::Bind()
    {
        if (!m_Shader)
        {
            VP_CORE_ERROR("RenderMaterial::Bind() called with null shader: {}", m_Name);
            return;
        }

        m_Shader->Bind();
        BindTextures();
        UploadParameters();
    }

    void RenderMaterial::Unbind()
    {
        if (m_Shader)
        {
            m_Shader->Unbind();
        }
    }

    // =========================================================================
    // Parameter Setters
    // =========================================================================

    void RenderMaterial::SetFloat(const std::string& name, float value)
    {
        m_Parameters[name] = value;
    }

    void RenderMaterial::SetInt(const std::string& name, int value)
    {
        m_Parameters[name] = value;
    }

    void RenderMaterial::SetBool(const std::string& name, bool value)
    {
        m_Parameters[name] = value;
    }

    void RenderMaterial::SetVec2(const std::string& name, const glm::vec2& value)
    {
        m_Parameters[name] = value;
    }

    void RenderMaterial::SetVec3(const std::string& name, const glm::vec3& value)
    {
        m_Parameters[name] = value;
    }

    void RenderMaterial::SetVec4(const std::string& name, const glm::vec4& value)
    {
        m_Parameters[name] = value;
    }

    void RenderMaterial::SetMat3(const std::string& name, const glm::mat3& value)
    {
        m_Parameters[name] = value;
    }

    void RenderMaterial::SetMat4(const std::string& name, const glm::mat4& value)
    {
        m_Parameters[name] = value;
    }

    // =========================================================================
    // Texture Binding
    // =========================================================================

    void RenderMaterial::SetTexture(const std::string& name, std::shared_ptr<Texture> texture, int slot, bool isCubemap)
    {
        // Check if slot already exists, update it
        for (auto& texSlot : m_TextureSlots)
        {
            if (texSlot.UniformName == name)
            {
                texSlot.TextureRef = texture;
                texSlot.Slot = slot;
                texSlot.IsCubemap = isCubemap;
                return;
            }
        }

        // Add new slot
        m_TextureSlots.emplace_back(name, texture, slot, isCubemap);
    }

    // =========================================================================
    // Parameter Query
    // =========================================================================

    bool RenderMaterial::HasParameter(const std::string& name) const
    {
        return m_Parameters.find(name) != m_Parameters.end();
    }

    // =========================================================================
    // Upload Logic
    // =========================================================================

    void RenderMaterial::UploadParameters()
    {
        if (!m_Shader) return;

        for (const auto& [name, value] : m_Parameters)
        {
            // Use std::visit to handle each variant type
            std::visit([this, &name](auto&& arg) {
                using T = std::decay_t<decltype(arg)>;

                if constexpr (std::is_same_v<T, float>)
                {
                    m_Shader->SetFloat(name, arg);
                }
                else if constexpr (std::is_same_v<T, int>)
                {
                    m_Shader->SetInt(name, arg);
                }
                else if constexpr (std::is_same_v<T, bool>)
                {
                    m_Shader->SetBool(name, arg);
                }
                else if constexpr (std::is_same_v<T, glm::vec2>)
                {
                    m_Shader->SetVec2(name, arg);
                }
                else if constexpr (std::is_same_v<T, glm::vec3>)
                {
                    m_Shader->SetVec3(name, arg);
                }
                else if constexpr (std::is_same_v<T, glm::vec4>)
                {
                    m_Shader->SetVec4(name, arg);
                }
                else if constexpr (std::is_same_v<T, glm::mat3>)
                {
                    m_Shader->SetMatrix3fv(name, arg);
                }
                else if constexpr (std::is_same_v<T, glm::mat4>)
                {
                    m_Shader->SetMatrix4fv(name, arg);
                }
                // Textures are handled separately in BindTextures
            }, value);
        }
    }

    void RenderMaterial::BindTextures()
    {
        if (!m_Shader) return;

        for (const auto& texSlot : m_TextureSlots)
        {
            if (texSlot.TextureRef)
            {
                texSlot.TextureRef->Bind(texSlot.Slot);
                m_Shader->SetInt(texSlot.UniformName, texSlot.Slot);
            }
        }
    }
}
```

---

## Step 4: Create PBR Material

The PBR material pre-configures all the uniforms needed for our `defaultlit.shader`.

**Create** `VizEngine/src/VizEngine/Renderer/PBRMaterial.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/PBRMaterial.h

#pragma once

#include "RenderMaterial.h"
#include "glm.hpp"

namespace VizEngine
{
    /**
     * Physically-Based Rendering material for use with defaultlit.shader.
     * Encapsulates metallic-roughness workflow parameters.
     *
     * Usage:
     *   auto pbrMaterial = std::make_shared<PBRMaterial>(shader);
     *   pbrMaterial->SetAlbedo(glm::vec3(1.0f, 0.76f, 0.33f));  // Gold
     *   pbrMaterial->SetMetallic(1.0f);
     *   pbrMaterial->SetRoughness(0.3f);
     */
    class VizEngine_API PBRMaterial : public RenderMaterial
    {
    public:
        /**
         * Create PBR material with shader.
         * @param shader Should be the defaultlit.shader or compatible
         * @param name Material name for debugging
         */
        PBRMaterial(std::shared_ptr<Shader> shader, const std::string& name = "PBR Material");
        ~PBRMaterial() override = default;

        // =====================================================================
        // PBR Properties (Metallic-Roughness Workflow)
        // =====================================================================

        void SetAlbedo(const glm::vec3& albedo);
        glm::vec3 GetAlbedo() const;

        void SetMetallic(float metallic);
        float GetMetallic() const;

        void SetRoughness(float roughness);
        float GetRoughness() const;

        void SetAO(float ao);
        float GetAO() const;

        // =====================================================================
        // Texture Maps
        // =====================================================================

        void SetAlbedoTexture(std::shared_ptr<Texture> texture);
        void SetNormalTexture(std::shared_ptr<Texture> texture);
        void SetMetallicRoughnessTexture(std::shared_ptr<Texture> texture);
        void SetAOTexture(std::shared_ptr<Texture> texture);
        void SetEmissiveTexture(std::shared_ptr<Texture> texture);

        // =====================================================================
        // IBL (Environment) Maps
        // =====================================================================

        void SetIrradianceMap(std::shared_ptr<Texture> irradianceMap);
        void SetPrefilteredMap(std::shared_ptr<Texture> prefilteredMap);
        void SetBRDFLUT(std::shared_ptr<Texture> brdfLut);
        void SetUseIBL(bool useIBL);

        // =====================================================================
        // Shadow Mapping
        // =====================================================================

        void SetShadowMap(std::shared_ptr<Texture> shadowMap);
        void SetLightSpaceMatrix(const glm::mat4& lightSpaceMatrix);
        void SetUseShadows(bool useShadows);

        // =====================================================================
        // Transform (per-object, set before each draw)
        // =====================================================================

        void SetModelMatrix(const glm::mat4& model);
        void SetNormalMatrix(const glm::mat3& normalMatrix);
        void SetViewMatrix(const glm::mat4& view);
        void SetProjectionMatrix(const glm::mat4& projection);
        void SetViewPosition(const glm::vec3& viewPos);

        /**
         * Set all matrices at once (including normal matrix).
         */
        void SetTransforms(const glm::mat4& model, const glm::mat4& view,
                          const glm::mat4& projection, const glm::vec3& viewPos,
                          const glm::mat3& normalMatrix);

    protected:
        void UploadParameters() override;

    private:
        // Cached values for convenience getters
        glm::vec3 m_Albedo = glm::vec3(1.0f);
        float m_Metallic = 0.0f;
        float m_Roughness = 0.5f;
        float m_AO = 1.0f;

        bool m_UseIBL = false;
        bool m_UseShadows = false;
        bool m_HasAlbedoTexture = false;
        bool m_HasNormalTexture = false;
    };
}
```

---

**Create** `VizEngine/src/VizEngine/Renderer/PBRMaterial.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/PBRMaterial.cpp

#include "PBRMaterial.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/OpenGL/Commons.h"  // TextureSlots constants

namespace VizEngine
{
    PBRMaterial::PBRMaterial(std::shared_ptr<Shader> shader, const std::string& name)
        : RenderMaterial(shader, name)
    {
        // Set default PBR values
        SetFloat("u_Metallic", m_Metallic);
        SetFloat("u_Roughness", m_Roughness);
        SetFloat("u_AO", m_AO);
        SetVec3("u_Albedo", m_Albedo);
        SetBool("u_UseAlbedoTexture", false);
        SetBool("u_UseNormalMap", false);
        SetBool("u_UseIBL", false);
        SetBool("u_UseShadows", false);
    }

    // =========================================================================
    // PBR Properties
    // =========================================================================

    void PBRMaterial::SetAlbedo(const glm::vec3& albedo)
    {
        m_Albedo = albedo;
        SetVec3("u_Albedo", albedo);
    }

    glm::vec3 PBRMaterial::GetAlbedo() const
    {
        return m_Albedo;
    }

    void PBRMaterial::SetMetallic(float metallic)
    {
        m_Metallic = glm::clamp(metallic, 0.0f, 1.0f);
        SetFloat("u_Metallic", m_Metallic);
    }

    float PBRMaterial::GetMetallic() const
    {
        return m_Metallic;
    }

    void PBRMaterial::SetRoughness(float roughness)
    {
        m_Roughness = glm::clamp(roughness, 0.05f, 1.0f);  // Min 0.05 to avoid singularities
        SetFloat("u_Roughness", m_Roughness);
    }

    float PBRMaterial::GetRoughness() const
    {
        return m_Roughness;
    }

    void PBRMaterial::SetAO(float ao)
    {
        m_AO = glm::clamp(ao, 0.0f, 1.0f);
        SetFloat("u_AO", m_AO);
    }

    float PBRMaterial::GetAO() const
    {
        return m_AO;
    }

    // =========================================================================
    // Texture Maps (using TextureSlots constants from Commons.h)
    // =========================================================================

    void PBRMaterial::SetAlbedoTexture(std::shared_ptr<Texture> texture)
    {
        if (texture)
        {
            SetTexture("u_AlbedoTexture", texture, TextureSlots::Albedo);
            m_HasAlbedoTexture = true;
            SetBool("u_UseAlbedoTexture", true);
        }
        else
        {
            m_HasAlbedoTexture = false;
            SetBool("u_UseAlbedoTexture", false);
        }
    }

    void PBRMaterial::SetNormalTexture(std::shared_ptr<Texture> texture)
    {
        if (texture)
        {
            SetTexture("u_NormalTexture", texture, TextureSlots::Normal);
            m_HasNormalTexture = true;
            SetBool("u_UseNormalMap", true);
        }
        else
        {
            m_HasNormalTexture = false;
            SetBool("u_UseNormalMap", false);
        }
    }

    void PBRMaterial::SetMetallicRoughnessTexture(std::shared_ptr<Texture> texture)
    {
        if (texture)
        {
            SetTexture("u_MetallicRoughnessTexture", texture, TextureSlots::MetallicRoughness);
            SetBool("u_UseMetallicRoughnessTexture", true);
        }
        else
        {
            SetBool("u_UseMetallicRoughnessTexture", false);
        }
    }

    void PBRMaterial::SetAOTexture(std::shared_ptr<Texture> texture)
    {
        if (texture)
        {
            SetTexture("u_AOTexture", texture, TextureSlots::AO);
            SetBool("u_UseAOTexture", true);
        }
        else
        {
            SetBool("u_UseAOTexture", false);
        }
    }

    void PBRMaterial::SetEmissiveTexture(std::shared_ptr<Texture> texture)
    {
        if (texture)
        {
            SetTexture("u_EmissiveTexture", texture, TextureSlots::Emissive);
            SetBool("u_UseEmissiveTexture", true);
        }
        else
        {
            SetBool("u_UseEmissiveTexture", false);
        }
    }

    // =========================================================================
    // IBL Maps (using TextureSlots constants)
    // =========================================================================

    void PBRMaterial::SetIrradianceMap(std::shared_ptr<Texture> irradianceMap)
    {
        if (irradianceMap)
        {
            SetTexture("u_IrradianceMap", irradianceMap, TextureSlots::Irradiance, true);  // true = cubemap
        }
    }

    void PBRMaterial::SetPrefilteredMap(std::shared_ptr<Texture> prefilteredMap)
    {
        if (prefilteredMap)
        {
            SetTexture("u_PrefilteredMap", prefilteredMap, TextureSlots::Prefiltered, true);  // true = cubemap
        }
    }

    void PBRMaterial::SetBRDFLUT(std::shared_ptr<Texture> brdfLut)
    {
        if (brdfLut)
        {
            SetTexture("u_BRDF_LUT", brdfLut, TextureSlots::BRDF_LUT);  // Note: uniform name must match shader
        }
    }

    void PBRMaterial::SetUseIBL(bool useIBL)
    {
        m_UseIBL = useIBL;
        SetBool("u_UseIBL", useIBL);
    }

    // =========================================================================
    // Shadow Mapping
    // =========================================================================

    void PBRMaterial::SetShadowMap(std::shared_ptr<Texture> shadowMap)
    {
        if (shadowMap)
        {
            SetTexture("u_ShadowMap", shadowMap, TextureSlots::ShadowMap);
        }
    }

    void PBRMaterial::SetLightSpaceMatrix(const glm::mat4& lightSpaceMatrix)
    {
        SetMat4("u_LightSpaceMatrix", lightSpaceMatrix);
    }

    void PBRMaterial::SetUseShadows(bool useShadows)
    {
        m_UseShadows = useShadows;
        SetBool("u_UseShadows", useShadows);
    }

    // =========================================================================
    // Transforms
    // =========================================================================

    void PBRMaterial::SetModelMatrix(const glm::mat4& model)
    {
        SetMat4("u_Model", model);
    }

    void PBRMaterial::SetNormalMatrix(const glm::mat3& normalMatrix)
    {
        SetMat3("u_NormalMatrix", normalMatrix);
    }

    void PBRMaterial::SetViewMatrix(const glm::mat4& view)
    {
        SetMat4("u_View", view);
    }

    void PBRMaterial::SetProjectionMatrix(const glm::mat4& projection)
    {
        SetMat4("u_Projection", projection);
    }

    void PBRMaterial::SetViewPosition(const glm::vec3& viewPos)
    {
        SetVec3("u_ViewPos", viewPos);
    }

    void PBRMaterial::SetTransforms(const glm::mat4& model, const glm::mat4& view,
                                    const glm::mat4& projection, const glm::vec3& viewPos,
                                    const glm::mat3& normalMatrix)
    {
        SetModelMatrix(model);
        SetNormalMatrix(normalMatrix);
        SetViewMatrix(view);
        SetProjectionMatrix(projection);
        SetViewPosition(viewPos);
    }

    // =========================================================================
    // Upload Override
    // =========================================================================

    void PBRMaterial::UploadParameters()
    {
        // Call base implementation to upload all stored parameters
        RenderMaterial::UploadParameters();

        // Any PBR-specific upload logic can be added here
        // (currently all handled by base class via stored parameters)
    }
}
```

---

## Step 5: Create Unlit Material

For UI elements, skyboxes, and debug rendering, we need a simple unlit material.

**Create** `VizEngine/src/VizEngine/Renderer/UnlitMaterial.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/UnlitMaterial.h

#pragma once

#include "RenderMaterial.h"
#include <glm/glm.hpp>

namespace VizEngine
{
    /**
     * Simple unlit material for UI, debug rendering, and effects.
     * Uses unlit.shader - no lighting calculations.
     */
    class VizEngine_API UnlitMaterial : public RenderMaterial
    {
    public:
        UnlitMaterial(std::shared_ptr<Shader> shader, const std::string& name = "Unlit Material");
        ~UnlitMaterial() override = default;

        // Color
        void SetColor(const glm::vec4& color);
        glm::vec4 GetColor() const;

        // Texture
        void SetMainTexture(std::shared_ptr<Texture> texture);
        void SetUseTexture(bool useTexture);

        // Transforms
        void SetMVP(const glm::mat4& mvp);

    private:
        glm::vec4 m_Color = glm::vec4(1.0f);
    };
}
```

**Create** `VizEngine/src/VizEngine/Renderer/UnlitMaterial.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/UnlitMaterial.cpp

#include "UnlitMaterial.h"
#include "VizEngine/OpenGL/Texture.h"

namespace VizEngine
{
    UnlitMaterial::UnlitMaterial(std::shared_ptr<Shader> shader, const std::string& name)
        : RenderMaterial(shader, name)
    {
        SetVec4("u_Color", m_Color);
        SetBool("u_UseTexture", false);
    }

    void UnlitMaterial::SetColor(const glm::vec4& color)
    {
        m_Color = color;
        SetVec4("u_Color", color);
    }

    glm::vec4 UnlitMaterial::GetColor() const
    {
        return m_Color;
    }

    void UnlitMaterial::SetMainTexture(std::shared_ptr<Texture> texture)
    {
        if (texture)
        {
            SetTexture("u_Texture", texture, 0);
            SetBool("u_UseTexture", true);
        }
        else
        {
            SetBool("u_UseTexture", false);
        }
    }

    void UnlitMaterial::SetUseTexture(bool useTexture)
    {
        SetBool("u_UseTexture", useTexture);
    }

    void UnlitMaterial::SetMVP(const glm::mat4& mvp)
    {
        SetMat4("u_MVP", mvp);
    }
}
```

---

## Step 6: Material Factory

Provide convenient factory methods for creating common material types.

**Create** `VizEngine/src/VizEngine/Renderer/MaterialFactory.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/MaterialFactory.h

#pragma once

#include "VizEngine/Core.h"
#include <memory>
#include <string>
#include "glm.hpp"

namespace VizEngine
{
    class RenderMaterial;
    class PBRMaterial;
    class UnlitMaterial;
    class Shader;

    /**
     * Factory for creating pre-configured materials.
     * Centralizes shader loading and default parameter setup.
     */
    class VizEngine_API MaterialFactory
    {
    public:
        /**
         * Create a PBR material with the default lit shader.
         * @param name Material name
         * @return Configured PBRMaterial
         */
        static std::shared_ptr<PBRMaterial> CreatePBR(const std::string& name = "PBR Material");

        /**
         * Create a PBR material with custom shader.
         * @param shader Custom PBR-compatible shader
         * @param name Material name
         * @return Configured PBRMaterial
         */
        static std::shared_ptr<PBRMaterial> CreatePBR(
            std::shared_ptr<Shader> shader, 
            const std::string& name = "PBR Material"
        );

        /**
         * Create an unlit material with the default unlit shader.
         * @param name Material name
         * @return Configured UnlitMaterial
         */
        static std::shared_ptr<UnlitMaterial> CreateUnlit(const std::string& name = "Unlit Material");

        /**
         * Create an unlit material with custom shader.
         * @param shader Custom unlit-compatible shader
         * @param name Material name
         * @return Configured UnlitMaterial
         */
        static std::shared_ptr<UnlitMaterial> CreateUnlit(
            std::shared_ptr<Shader> shader,
            const std::string& name = "Unlit Material"
        );

        // =====================================================================
        // Pre-configured Material Presets
        // =====================================================================

        /**
         * Create a metallic gold material.
         */
        static std::shared_ptr<PBRMaterial> CreateGold(const std::string& name = "Gold");

        /**
         * Create a rough plastic material.
         */
        static std::shared_ptr<PBRMaterial> CreatePlastic(
            const glm::vec3& color = glm::vec3(0.8f, 0.2f, 0.2f),
            const std::string& name = "Plastic"
        );

        /**
         * Create a polished chrome material.
         */
        static std::shared_ptr<PBRMaterial> CreateChrome(const std::string& name = "Chrome");

    private:
        // Cached default shaders (lazy loaded)
        static std::shared_ptr<Shader> s_DefaultPBRShader;
        static std::shared_ptr<Shader> s_DefaultUnlitShader;

        static std::shared_ptr<Shader> GetDefaultPBRShader();
        static std::shared_ptr<Shader> GetDefaultUnlitShader();
    };
}
```

**Create** `VizEngine/src/VizEngine/Renderer/MaterialFactory.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/MaterialFactory.cpp

#include "MaterialFactory.h"
#include "PBRMaterial.h"
#include "UnlitMaterial.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    // Static shader cache
    std::shared_ptr<Shader> MaterialFactory::s_DefaultPBRShader = nullptr;
    std::shared_ptr<Shader> MaterialFactory::s_DefaultUnlitShader = nullptr;

    std::shared_ptr<Shader> MaterialFactory::GetDefaultPBRShader()
    {
        if (!s_DefaultPBRShader)
        {
            s_DefaultPBRShader = std::make_shared<Shader>("resources/shaders/defaultlit.shader");
            if (!s_DefaultPBRShader->IsValid())
            {
                VP_CORE_ERROR("MaterialFactory: Failed to load default PBR shader");
            }
        }
        return s_DefaultPBRShader;
    }

    std::shared_ptr<Shader> MaterialFactory::GetDefaultUnlitShader()
    {
        if (!s_DefaultUnlitShader)
        {
            s_DefaultUnlitShader = std::make_shared<Shader>("resources/shaders/unlit.shader");
            if (!s_DefaultUnlitShader->IsValid())
            {
                VP_CORE_ERROR("MaterialFactory: Failed to load default unlit shader");
            }
        }
        return s_DefaultUnlitShader;
    }

    // =========================================================================
    // Factory Methods
    // =========================================================================

    std::shared_ptr<PBRMaterial> MaterialFactory::CreatePBR(const std::string& name)
    {
        return CreatePBR(GetDefaultPBRShader(), name);
    }

    std::shared_ptr<PBRMaterial> MaterialFactory::CreatePBR(
        std::shared_ptr<Shader> shader,
        const std::string& name)
    {
        return std::make_shared<PBRMaterial>(shader, name);
    }

    std::shared_ptr<UnlitMaterial> MaterialFactory::CreateUnlit(const std::string& name)
    {
        return CreateUnlit(GetDefaultUnlitShader(), name);
    }

    std::shared_ptr<UnlitMaterial> MaterialFactory::CreateUnlit(
        std::shared_ptr<Shader> shader,
        const std::string& name)
    {
        return std::make_shared<UnlitMaterial>(shader, name);
    }

    // =========================================================================
    // Presets
    // =========================================================================

    std::shared_ptr<PBRMaterial> MaterialFactory::CreateGold(const std::string& name)
    {
        auto material = CreatePBR(name);
        material->SetAlbedo(glm::vec3(1.0f, 0.766f, 0.336f));  // Gold color
        material->SetMetallic(1.0f);
        material->SetRoughness(0.3f);
        return material;
    }

    std::shared_ptr<PBRMaterial> MaterialFactory::CreatePlastic(
        const glm::vec3& color,
        const std::string& name)
    {
        auto material = CreatePBR(name);
        material->SetAlbedo(color);
        material->SetMetallic(0.0f);
        material->SetRoughness(0.5f);
        return material;
    }

    std::shared_ptr<PBRMaterial> MaterialFactory::CreateChrome(const std::string& name)
    {
        auto material = CreatePBR(name);
        material->SetAlbedo(glm::vec3(0.95f, 0.95f, 0.95f));  // Near-white for chrome
        material->SetMetallic(1.0f);
        material->SetRoughness(0.1f);
        return material;
    }
}
```

---

## Step 7: Update CMakeLists.txt

Add the new material files to the build:

**Update** `VizEngine/CMakeLists.txt`:

```cmake
# In VIZENGINE_SOURCES (Core subsection)
    src/VizEngine/Core/MaterialParameter.h

# In VIZENGINE_SOURCES (Renderer subsection)
    src/VizEngine/Renderer/RenderMaterial.cpp
    src/VizEngine/Renderer/PBRMaterial.cpp
    src/VizEngine/Renderer/UnlitMaterial.cpp
    src/VizEngine/Renderer/MaterialFactory.cpp

# In VIZENGINE_HEADERS (Renderer subsection)
    src/VizEngine/Renderer/RenderMaterial.h
    src/VizEngine/Renderer/PBRMaterial.h
    src/VizEngine/Renderer/UnlitMaterial.h
    src/VizEngine/Renderer/MaterialFactory.h
```

---

## Step 8: Update VizEngine.h

Export the new material classes in the main header:

**Update** `VizEngine/src/VizEngine.h`:

```cpp
// Add after existing includes:

// Material System (Chapter 38)
#include "VizEngine/Renderer/MaterialParameter.h"
#include "VizEngine/Renderer/RenderMaterial.h"
#include "VizEngine/Renderer/PBRMaterial.h"
#include "VizEngine/Renderer/UnlitMaterial.h"
#include "VizEngine/Renderer/MaterialFactory.h"
```

---

## Step 9: Refactor SandboxApp with Materials

Now we'll refactor `SandboxApp.cpp` to use the new Material System.

### Option A: Gradual Integration (Recommended)

For an incremental migration, create materials once and reuse them:

**In** `SandboxApp.cpp`, add members:

```cpp
private:
    // ... existing members ...

    // Material System (Chapter 38)
    std::shared_ptr<VizEngine::PBRMaterial> m_DefaultPBRMaterial;
```

**In** `OnCreate()`, initialize the material:

```cpp
// =========================================================================
// Material System Setup (Chapter 38)
// =========================================================================
VP_INFO("Setting up material system...");

m_DefaultPBRMaterial = std::make_shared<VizEngine::PBRMaterial>(
    m_DefaultLitShader, "Default PBR"
);

// Configure shared settings (IBL, shadows, etc.)
if (m_UseIBL && m_IrradianceMap && m_PrefilteredMap && m_BRDFLut)
{
    m_DefaultPBRMaterial->SetIrradianceMap(m_IrradianceMap);
    m_DefaultPBRMaterial->SetPrefilteredMap(m_PrefilteredMap);
    m_DefaultPBRMaterial->SetBRDFLUT(m_BRDFLut);
    m_DefaultPBRMaterial->SetUseIBL(true);
}

if (m_ShadowMapDepth)
{
    m_DefaultPBRMaterial->SetShadowMap(m_ShadowMapDepth);
    m_DefaultPBRMaterial->SetUseShadows(true);
}

VP_INFO("Material system initialized");
```

### Option B: Full Refactor

For complete integration, replace the render loop:

```cpp
void RenderSceneObjects()
{
    auto& engine = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();

    // Set view-dependent uniforms once
    m_DefaultPBRMaterial->SetViewMatrix(m_Camera.GetViewMatrix());
    m_DefaultPBRMaterial->SetProjectionMatrix(m_Camera.GetProjectionMatrix());
    m_DefaultPBRMaterial->SetViewPosition(m_Camera.GetPosition());
    m_DefaultPBRMaterial->SetLightSpaceMatrix(m_LightSpaceMatrix);

    // Set lighting uniforms (could be moved to material if lights are static)
    auto shader = m_DefaultPBRMaterial->GetShader();
    shader->Bind();
    shader->SetInt("u_LightCount", 4);
    for (int i = 0; i < 4; ++i)
    {
        shader->SetVec3("u_LightPositions[" + std::to_string(i) + "]", m_PBRLightPositions[i]);
        shader->SetVec3("u_LightColors[" + std::to_string(i) + "]", m_PBRLightColors[i]);
    }
    shader->SetBool("u_UseDirLight", true);
    shader->SetVec3("u_DirLightDirection", m_Light.GetDirection());
    shader->SetVec3("u_DirLightColor", m_Light.Diffuse * 2.0f);

    // Render each object
    for (auto& obj : m_Scene)
    {
        if (!obj.Active || !obj.MeshPtr) continue;

        // Compute model and normal matrices (normal matrix computed on CPU for performance)
        glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
        glm::mat3 normalMatrix = glm::transpose(glm::inverse(glm::mat3(model)));

        // Per-object transforms
        m_DefaultPBRMaterial->SetModelMatrix(model);
        m_DefaultPBRMaterial->SetNormalMatrix(normalMatrix);

        // Per-object material properties
        m_DefaultPBRMaterial->SetAlbedo(glm::vec3(obj.Color));
        m_DefaultPBRMaterial->SetMetallic(obj.Metallic);
        m_DefaultPBRMaterial->SetRoughness(obj.Roughness);
        m_DefaultPBRMaterial->SetAO(1.0f);

        if (obj.TexturePtr)
        {
            m_DefaultPBRMaterial->SetAlbedoTexture(obj.TexturePtr);
        }
        else
        {
            m_DefaultPBRMaterial->SetAlbedoTexture(nullptr);
        }

        // Bind material (uploads all uniforms)
        m_DefaultPBRMaterial->Bind();

        // Draw
        obj.MeshPtr->Bind();
        renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(),
                     *m_DefaultPBRMaterial->GetShader());
    }
}

> [!NOTE]
> **Normal Matrix Optimization**: The normal matrix is computed as `transpose(inverse(mat3(model)))` once per object on the CPU, avoiding expensive per-vertex inverse() calls in the shader. See **Chapter 33** for details.
```

---

## Testing and Validation

### Verify Correct Binding

1. **Test basic rendering**: Scene should look identical to before refactoring
2. **Test parameter changes**: Modify material properties in ImGui, verify real-time updates
3. **Test textures**: Ensure albedo textures still apply correctly

### Performance Comparison

| Metric | Before (Manual) | After (Material) |
|--------|-----------------|------------------|
| **Uniform calls/object** | ~15 | ~15 (same, but encapsulated) |
| **Code lines/render** | 30+ | 5-10 |
| **State change overhead** | Scattered | Batched in Bind() |

> [!NOTE]
> The Material System doesn't immediately improve GPU performance—it's an **architectural improvement** that enables future optimizations like material sorting and instancing.

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Black objects** | Material not bound | Call `material->Bind()` before rendering |
| **Wrong textures** | Slot conflicts | Ensure unique texture slots (0-15) |
| **Missing uniforms** | Parameter not set | Verify all required uniforms are set |
| **Shader errors** | Wrong shader for material | Use PBRMaterial with defaultlit.shader |

---

## Best Practices

### Material Organization

1. **One material per visual appearance**: Gold, chrome, plastic should be separate materials
2. **Share shaders**: Multiple materials can reference the same shader
3. **Cache materials**: Don't create materials every frame
4. **Use the factory**: `MaterialFactory::CreateGold()` ensures correct configuration

### Parameter Management

1. **Set once, bind many**: Set view/projection matrices once per frame, not per object
2. **Group by frequency**: Separate per-frame, per-material, and per-object parameters
3. **Default values**: Always set sensible defaults in material constructors

### Future Considerations

1. **Material Instances**: Share base material, override specific parameters (Chapter 39)
2. **Material Sorting**: Sort draw calls by material to minimize state changes (Chapter 41)
3. **Shader Variants**: Compile-time permutations for optional features (Part XV)

---

## Cross-Chapter Integration

### Callbacks to Previous Chapters

> In **Chapter 33**, we implemented the Cook-Torrance BRDF with manual uniform setup. The Material System now encapsulates all those uniforms (`u_Albedo`, `u_Metallic`, `u_Roughness`, `u_AO`) in a type-safe interface.

> In **Chapter 34**, we added IBL with irradiance and prefiltered maps. The `PBRMaterial` class provides `SetIrradianceMap()` and `SetPrefilteredMap()` methods that handle cubemap binding.

> The shadow mapping from **Chapter 29** is integrated via `SetShadowMap()` and `SetLightSpaceMatrix()`, keeping all rendering concerns in one place.

### Forward References

> In **Chapter 39: ECS with EnTT**, we'll create a `MeshRendererComponent` that stores a `std::shared_ptr<Material>`. The renderer will iterate over entities with `MeshRendererComponent` and call `material->Bind()` for each.

> **Chapter 40: Core Components** will introduce `MaterialComponent` as a reusable building block, enabling material assignment in the scene editor.

> The Material System prepares for **shader variants** (Part XV) by abstracting which shader is used from how it's configured.

---

## Milestone

**Chapter 38 Complete - Material System**

At this point, your engine has:

**Material abstraction** that encapsulates shader + parameters + textures  
**Type-safe parameters** using C++17 `std::variant` for compile-time safety  
**PBRMaterial class** pre-configured for metallic-roughness workflow  
**UnlitMaterial class** for UI and debug rendering  
**MaterialFactory** with convenient presets (Gold, Chrome, Plastic)  
**Clean render interface**: `material->Bind()` replaces 15+ manual uniform calls  

**Architectural comparison**:
- **Before**: Shader uniforms scattered across render code
- **After**: RenderMaterials encapsulate all rendering state

**Code cleanup**:
- **Before**: 30+ lines per object for uniform setup
- **After**: 5-10 lines with material interface

The Material System is the **bridge** between manual rendering (Chapters 1-37) and component-based architecture (Chapters 39+). You now have the abstraction layer needed for a professional ECS-based renderer.

---

## What's Next

In **Chapter 39: ECS with EnTT**, we'll integrate the industry-standard EnTT library to create a proper Entity-Component System. Materials will become components attached to entities, and a RenderSystem will automatically render all entities with `MeshRendererComponent`.

> **Next:** [Chapter 39: ECS with EnTT](39_ECSWithEnTT.md)

> **Previous:** [Chapter 37: Color Grading](37_ColorGrading.md)

> **Index:** [Table of Contents](INDEX.md)
