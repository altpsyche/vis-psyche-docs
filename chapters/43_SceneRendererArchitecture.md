\newpage

# Chapter 43: Scene Renderer Architecture

Extract the monolithic render pipeline from SandboxApp into a composable SceneRenderer with swappable render paths, preparing for Forward+, Deferred, and screen-space effects.

---

## Introduction

In **Chapter 42**, we built a Material System that encapsulates shaders, parameters, and textures. Our PBRMaterial provides a clean `Bind()` interface for surface properties. But there's a bigger problem: **SandboxApp.cpp is 1660 lines** and growing.

**The problem**: All rendering logic lives in one monolithic `OnRender()` method:

```cpp
void Sandbox::OnRender()
{
    // Shadow pass (~40 lines)
    m_ShadowFramebuffer->Bind();
    // ... shadow map generation ...

    // Main render pass (~80 lines)
    m_HDRFramebuffer->Bind();
    m_DefaultLitShader->Bind();
    // ... camera, lights, IBL, per-object uniforms ...

    // Skybox (~5 lines)
    m_Skybox->Render(m_Camera);

    // Stencil outlines (~50 lines)
    // ... two-pass stencil buffer technique ...

    // Post-processing (~30 lines)
    // ... bloom, tone mapping, color grading ...

    // Offscreen preview (~40 lines)
    // ... mini framebuffer for ImGui viewport ...
}
```

**Consequences**:
- **Can't swap rendering strategies**: Want to try Deferred shading? Rewrite everything.
- **Code duplication**: Forward+, Deferred, and Forward all need shadow passes and post-processing.
- **Scaling problems**: Adding SSAO, SSR, or depth prepass means more code in one giant function.
- **Testing difficulty**: Can't test individual passes in isolation.

**The solution**: A **SceneRenderer** orchestrator with a **Strategy Pattern** for swappable render paths:

```cpp
// Before: 1660 lines in SandboxApp
void OnRender() {
    // Shadow pass...
    // Main render...
    // Skybox...
    // Outlines...
    // Post-processing...
}

// After: SceneRenderer handles everything
void OnRender() {
    m_SceneRenderer->Render(m_Scene, m_Camera);
}
```

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **SceneRenderer** | Central orchestrator composing all rendering passes |
| **RenderPath** | Abstract base class for swappable rendering strategies |
| **ForwardRenderPath** | Concrete forward rendering path (refactored from SandboxApp) |
| **ShadowPass** | Extracted shadow map generation with its own FBO and shader |
| **PostProcessPipeline** | Composes Bloom + Tone Mapping + Color Grading |
| **RenderPassData** | Shared data structures for the multi-pass pipeline |
| **Reduced SandboxApp** | From ~1660 lines to ~970 lines (scene setup + UI only) |

**Architectural Impact**: This chapter establishes the rendering architecture for all of Part XII. Every future rendering technique (Forward+, Deferred, SSAO, SSR) plugs into this framework as either a new `RenderPath` or a new pass in the `SceneRenderer` pipeline.

---

## Design Goals

### The Strategy Pattern

The core idea is **polymorphic render paths**. The SceneRenderer doesn't know *how* the scene is rendered—it delegates to whichever `RenderPath` is active:

```
SceneRenderer (orchestrator)
    │
    ├── ShadowPass::Process()           → ShadowData
    │
    ├── RenderPath::Execute(data)       → HDR framebuffer
    │       ├── ForwardRenderPath          (Chapter 43)
    │       ├── ForwardPlusRenderPath      (Chapter 46)
    │       └── DeferredRenderPath         (Chapter 47)
    │
    ├── Skybox::Render()                → Skybox on HDR buffer
    │
    ├── RenderStencilOutline()          → Stencil outlines
    │
    └── PostProcessPipeline::Process()  → Screen output
```

**Frame execution order**:
1. Shadow pass (shared across all paths)
2. Main render path (polymorphic dispatch)
3. Skybox
4. Stencil outlines
5. Post-processing (Bloom → Tone Mapping → Color Grading)

### Separation of Concerns

A key architectural decision: **materials own surface properties, renderers own transforms and lighting**.

| Concern | Owner | Set Via |
|---------|-------|---------|
| Albedo, metallic, roughness | `PBRMaterial` | `material->SetAlbedo()` |
| Texture bindings (IBL, shadow) | `PBRMaterial` | `material->SetIrradianceMap()` |
| Model, view, projection matrices | Renderer | `shader->SetMatrix4fv()` |
| Camera position | Renderer | `shader->SetVec3()` |
| Light positions and colors | Renderer | `shader->SetVec3()` |
| Light-space matrix | Renderer | `shader->SetMatrix4fv()` |

This separation prevents bugs (e.g., storing a `mat4` for a `mat3` uniform in the material's variant map) and keeps PBRMaterial focused on what it represents: surface appearance.

---

## Step 1: Create RenderPassData

The data structs define the contract between SceneRenderer and RenderPath. Everything a render path needs is packed into a single struct.

**Create** `VizEngine/src/VizEngine/Renderer/RenderPassData.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/RenderPassData.h

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"
#include <memory>

namespace VizEngine
{
    class Scene;
    class Camera;
    class Renderer;
    class Framebuffer;
    class Texture;
    class Shader;
    class PBRMaterial;
    class Skybox;
    class FullscreenQuad;
    struct DirectionalLight;

    /**
     * Output from the shadow mapping pass.
     */
    struct ShadowData
    {
        std::shared_ptr<Texture> ShadowMap;
        glm::mat4 LightSpaceMatrix = glm::mat4(1.0f);
        bool Valid = false;
    };

    /**
     * Output from the depth/normal prepass (used by Forward+ and screen-space effects).
     */
    struct PrepassOutput
    {
        std::shared_ptr<Texture> DepthTexture;
        std::shared_ptr<Texture> NormalTexture;
        bool Valid = false;
    };

    /**
     * Render path type enumeration for runtime switching.
     */
    enum class RenderPathType
    {
        Forward,
        ForwardPlus,
        Deferred
    };

    /**
     * All data needed by a render path to execute its main pass.
     * Passed by the SceneRenderer orchestrator to the active RenderPath.
     */
    struct RenderPassData
    {
        // Scene data
        Scene* ScenePtr = nullptr;
        Camera* CameraPtr = nullptr;
        Renderer* RendererPtr = nullptr;

        // Shared resources
        ShadowData Shadow;
        PrepassOutput* Prepass = nullptr;

        // Target framebuffer for HDR output
        std::shared_ptr<Framebuffer> TargetFramebuffer;

        // Shared rendering resources
        std::shared_ptr<PBRMaterial> Material;
        std::shared_ptr<Shader> DefaultLitShader;
        std::shared_ptr<FullscreenQuad> Quad;

        // IBL resources
        std::shared_ptr<Texture> IrradianceMap;
        std::shared_ptr<Texture> PrefilteredMap;
        std::shared_ptr<Texture> BRDFLut;
        bool UseIBL = false;
        float IBLIntensity = 0.3f;

        // Light data (forward path uses these directly)
        DirectionalLight* DirLight = nullptr;
        glm::vec3* PointLightPositions = nullptr;
        glm::vec3* PointLightColors = nullptr;
        int PointLightCount = 0;

        // Lower hemisphere fallback
        glm::vec3 LowerHemisphereColor = glm::vec3(0.15f, 0.15f, 0.2f);
        float LowerHemisphereIntensity = 0.5f;

        // Clear color
        float ClearColor[4] = { 0.1f, 0.1f, 0.15f, 1.0f };
    };
}
```

> [!NOTE]
> `RenderPassData` uses raw pointers for Scene, Camera, and Renderer because these are owned by SandboxApp with lifetimes that outlive any single frame. `shared_ptr` is used for GPU resources (textures, framebuffers) that need reference counting.

---

## Step 2: Create RenderPath Abstract Base Class

The abstract base defines the interface that all rendering strategies must implement.

**Create** `VizEngine/src/VizEngine/Renderer/RenderPath.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/RenderPath.h

#pragma once

#include "VizEngine/Core.h"
#include "RenderPassData.h"

namespace VizEngine
{
    /**
     * Abstract base class for rendering paths.
     * Each derived class implements a different rendering strategy.
     * The SceneRenderer orchestrator delegates the main render pass to the active path.
     */
    class VizEngine_API RenderPath
    {
    public:
        virtual ~RenderPath() = default;

        virtual void OnAttach(int width, int height) = 0;
        virtual void OnDetach() = 0;
        virtual void Execute(const RenderPassData& data) = 0;
        virtual bool NeedsDepthPrepass() const = 0;

        // Optional: paths that produce G-buffer data (Deferred)
        virtual bool ProvidesGBufferDepth() const { return false; }
        virtual bool ProvidesGBufferNormals() const { return false; }
        virtual std::shared_ptr<Texture> GetDepthTexture() const { return nullptr; }
        virtual std::shared_ptr<Texture> GetNormalTexture() const { return nullptr; }

        virtual void OnResize(int width, int height) = 0;
        virtual void OnImGuiDebug() {}

        virtual const char* GetName() const = 0;
        virtual RenderPathType GetType() const = 0;

        bool IsValid() const { return m_IsValid; }

    protected:
        bool m_IsValid = false;
    };
}
```

**Design decisions**:
- `Execute()` receives all data via `RenderPassData`—no back-references to SceneRenderer.
- `NeedsDepthPrepass()` tells the orchestrator whether to run a depth/normal prepass before this path.
- `ProvidesGBufferDepth()`/`ProvidesGBufferNormals()` let the Deferred path skip the prepass since its G-buffer already contains this data.
- `OnAttach()`/`OnDetach()` manage path-specific resources when switching at runtime.

---

## Step 3: Create ShadowPass

Extract shadow map generation from SandboxApp into its own class.

**Create** `VizEngine/src/VizEngine/Renderer/ShadowPass.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/ShadowPass.h

#pragma once

#include "VizEngine/Core.h"
#include "RenderPassData.h"
#include <memory>

namespace VizEngine
{
    class Framebuffer;
    class Texture;
    class Shader;
    class Scene;
    class Renderer;
    struct DirectionalLight;

    /**
     * Generates a shadow map from a directional light's perspective.
     * Produces a ShadowData struct containing the depth texture and light-space matrix.
     */
    class VizEngine_API ShadowPass
    {
    public:
        ShadowPass(int resolution = 2048);
        ~ShadowPass() = default;

        ShadowData Process(Scene& scene, const DirectionalLight& light, Renderer& renderer);

        bool IsValid() const { return m_IsValid; }
        int GetResolution() const { return m_Resolution; }
        std::shared_ptr<Texture> GetShadowMap() const { return m_ShadowMapDepth; }

    private:
        glm::mat4 ComputeLightSpaceMatrix(const DirectionalLight& light) const;

        std::shared_ptr<Framebuffer> m_ShadowMapFramebuffer;
        std::shared_ptr<Texture> m_ShadowMapDepth;
        std::shared_ptr<Shader> m_ShadowDepthShader;

        int m_Resolution;
        bool m_IsValid = false;
    };
}
```

**Create** `VizEngine/src/VizEngine/Renderer/ShadowPass.cpp`:

```cpp
ShadowPass::ShadowPass(int resolution)
    : m_Resolution(resolution)
{
    // Create depth texture for the shadow map
    m_ShadowMapDepth = std::make_shared<Texture>();
    m_ShadowMapDepth->CreateDepth(m_Resolution, m_Resolution, GL_DEPTH_COMPONENT24);

    // Configure border sampling (samples outside the map return 1.0 = no shadow)
    float borderColor[] = { 1.0f, 1.0f, 1.0f, 1.0f };
    m_ShadowMapDepth->SetBorderColor(borderColor);

    // Create framebuffer with depth-only attachment
    m_ShadowMapFramebuffer = std::make_shared<Framebuffer>();
    m_ShadowMapFramebuffer->AttachDepthTexture(m_ShadowMapDepth);

    // Load shadow depth shader
    m_ShadowDepthShader = std::make_shared<Shader>("resources/shaders/shadowdepth.shader");

    m_IsValid = m_ShadowMapFramebuffer->IsComplete() && m_ShadowDepthShader->IsValid();
}

ShadowData ShadowPass::Process(Scene& scene, const DirectionalLight& light, Renderer& renderer)
{
    ShadowData result;
    if (!m_IsValid) return result;

    glm::mat4 lightSpaceMatrix = ComputeLightSpaceMatrix(light);

    // Render scene from light's perspective
    m_ShadowMapFramebuffer->Bind();
    renderer.SetViewport(0, 0, m_Resolution, m_Resolution);
    renderer.ClearDepth();
    renderer.EnablePolygonOffset(2.0f, 4.0f);

    m_ShadowDepthShader->Bind();
    m_ShadowDepthShader->SetMatrix4fv("u_LightSpaceMatrix", lightSpaceMatrix);

    for (size_t i = 0; i < scene.Size(); i++)
    {
        auto& obj = scene[i];
        if (!obj.Active || !obj.MeshPtr) continue;

        m_ShadowDepthShader->SetMatrix4fv("u_Model", obj.ObjectTransform.GetModelMatrix());
        obj.MeshPtr->Bind();
        // Draw call...
    }

    renderer.DisablePolygonOffset();

    result.ShadowMap = m_ShadowMapDepth;
    result.LightSpaceMatrix = lightSpaceMatrix;
    result.Valid = true;
    return result;
}
```

> [!TIP]
> The ShadowPass follows the same ownership pattern as Bloom (Chapter 40): it owns its FBO, textures, and shader, and exposes a `Process()` method that returns output data. This pattern will repeat for DepthNormalPrepass (Chapter 45), SSAOEffect (Chapter 48), and SSREffect (Chapter 49).

---

## Step 4: Create ForwardRenderPath

The forward path extracts the main rendering logic from SandboxApp.

**Create** `VizEngine/src/VizEngine/Renderer/ForwardRenderPath.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/ForwardRenderPath.h

#pragma once

#include "RenderPath.h"
#include <memory>

namespace VizEngine
{
    struct SceneObject;

    /**
     * Traditional forward rendering path.
     * Each object is fully shaded in a single pass with all lights.
     * Simple and correct, but scales poorly with many lights.
     */
    class VizEngine_API ForwardRenderPath : public RenderPath
    {
    public:
        void OnAttach(int width, int height) override;
        void OnDetach() override;
        void Execute(const RenderPassData& data) override;
        bool NeedsDepthPrepass() const override { return false; }
        void OnResize(int width, int height) override;
        const char* GetName() const override { return "Forward"; }
        RenderPathType GetType() const override { return RenderPathType::Forward; }

    private:
        void SetupLighting(const RenderPassData& data);
        void RenderSceneObjects(const RenderPassData& data);
        void RenderSingleObject(SceneObject& obj, const RenderPassData& data);
    };
}
```

**Create** `VizEngine/src/VizEngine/Renderer/ForwardRenderPath.cpp`:

```cpp
void ForwardRenderPath::Execute(const RenderPassData& data)
{
    if (!data.ScenePtr || !data.CameraPtr || !data.RendererPtr || !data.Material) return;
    if (!data.TargetFramebuffer) return;

    // Bind HDR framebuffer
    data.TargetFramebuffer->Bind();
    data.RendererPtr->Clear(data.ClearColor);

    // Setup per-frame lighting uniforms
    SetupLighting(data);

    // Render all objects
    RenderSceneObjects(data);
}
```

The critical architectural pattern is in `SetupLighting()` and `RenderSingleObject()`:

```cpp
void ForwardRenderPath::SetupLighting(const RenderPassData& data)
{
    auto& material = *data.Material;
    auto shader = material.GetShader();
    shader->Bind();

    // Camera matrices — set directly on shader (not through material parameter map)
    shader->SetMatrix4fv("u_View", data.CameraPtr->GetViewMatrix());
    shader->SetMatrix4fv("u_Projection", data.CameraPtr->GetProjectionMatrix());
    shader->SetVec3("u_ViewPos", data.CameraPtr->GetPosition());

    // Point lights
    shader->SetInt("u_LightCount", data.PointLightCount);
    for (int i = 0; i < data.PointLightCount; ++i)
    {
        shader->SetVec3("u_LightPositions[" + std::to_string(i) + "]",
                        data.PointLightPositions[i]);
        shader->SetVec3("u_LightColors[" + std::to_string(i) + "]",
                        data.PointLightColors[i]);
    }

    // Directional light
    if (data.DirLight)
    {
        shader->SetBool("u_UseDirLight", true);
        shader->SetVec3("u_DirLightDirection", data.DirLight->GetDirection());
        shader->SetVec3("u_DirLightColor", data.DirLight->Diffuse);
    }

    // Shadow mapping — matrix on shader, texture via material
    if (data.Shadow.Valid && data.Shadow.ShadowMap)
    {
        shader->SetMatrix4fv("u_LightSpaceMatrix", data.Shadow.LightSpaceMatrix);
        material.SetShadowMap(data.Shadow.ShadowMap);
    }

    // IBL — textures via material (slot management), scalars directly on shader
    material.SetUseIBL(data.UseIBL);
    if (data.UseIBL && data.IrradianceMap && data.PrefilteredMap && data.BRDFLut)
    {
        material.SetIrradianceMap(data.IrradianceMap);
        material.SetPrefilteredMap(data.PrefilteredMap);
        material.SetBRDFLUT(data.BRDFLut);
        shader->SetFloat("u_MaxReflectionLOD", 4.0f);
        shader->SetFloat("u_IBLIntensity", data.IBLIntensity);
    }

    // Lower hemisphere fallback
    material.SetLowerHemisphereColor(data.LowerHemisphereColor);
    material.SetLowerHemisphereIntensity(data.LowerHemisphereIntensity);
}
```

```cpp
void ForwardRenderPath::RenderSingleObject(SceneObject& obj, const RenderPassData& data)
{
    auto& material = *data.Material;
    auto shader = material.GetShader();
    auto& renderer = *data.RendererPtr;

    // Set PBR properties via material (uploaded during material.Bind())
    material.SetAlbedo(glm::vec3(obj.Color));
    material.SetAlpha(obj.Color.a);
    material.SetMetallic(obj.Metallic);
    material.SetRoughness(obj.Roughness);
    material.SetAO(1.0f);

    if (obj.TexturePtr)
        material.SetAlbedoTexture(obj.TexturePtr);
    else
        material.SetAlbedoTexture(nullptr);

    // Bind material: shader + textures + PBR uniform upload
    material.Bind();

    // Set per-object matrices directly on shader (after Bind ensures shader is active)
    glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
    glm::mat3 normalMatrix = glm::transpose(glm::inverse(glm::mat3(model)));
    shader->SetMatrix4fv("u_Model", model);
    shader->SetMatrix3fv("u_NormalMatrix", normalMatrix);

    obj.MeshPtr->Bind();
    renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), *shader);
}
```

**Key patterns**:
1. **Material owns surface properties**: `material.SetAlbedo()`, `material.SetMetallic()`, `material.SetIrradianceMap()` — these go through the material's parameter map and are uploaded during `Bind()`.
2. **Renderer sets transforms directly on shader**: `shader->SetMatrix4fv("u_Model", ...)` — these bypass the material entirely.
3. **Transparency sorting**: `RenderSceneObjects()` separates opaque and transparent objects, sorting transparent ones back-to-front by distance to camera.

---

## Step 5: Create PostProcessPipeline

Compose the existing Bloom (Chapter 40), tone mapping (Chapter 39), and color grading (Chapter 41) into a single pipeline.

**Create** `VizEngine/src/VizEngine/Renderer/PostProcessPipeline.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/PostProcessPipeline.h

#pragma once

#include "VizEngine/Core.h"
#include <memory>

namespace VizEngine
{
    class Texture;
    class Texture3D;
    class Shader;
    class Bloom;
    class FullscreenQuad;
    class Renderer;

    /**
     * Post-processing pipeline: Bloom -> Tone Mapping -> Color Grading.
     * Reads an HDR color texture and renders the final LDR result to the screen.
     */
    class VizEngine_API PostProcessPipeline
    {
    public:
        PostProcessPipeline(int width, int height);
        ~PostProcessPipeline();

        void Process(std::shared_ptr<Texture> hdrColorTexture, Renderer& renderer,
                     int windowWidth, int windowHeight);
        void OnResize(int width, int height);
        bool IsValid() const { return m_IsValid; }

        // Bloom settings
        void SetEnableBloom(bool enable);
        void SetBloomThreshold(float threshold);
        void SetBloomIntensity(float intensity);
        // ... getters ...

        // Tone mapping settings
        void SetToneMappingMode(int mode);
        void SetExposure(float exposure);
        void SetGamma(float gamma);
        // ... getters ...

        // Color grading settings
        void SetEnableColorGrading(bool enable);
        void SetSaturation(float sat);
        void SetContrast(float contrast);
        // ... getters ...

    private:
        std::unique_ptr<Bloom> m_Bloom;
        std::shared_ptr<Shader> m_ToneMappingShader;
        std::shared_ptr<FullscreenQuad> m_FullscreenQuad;
        std::unique_ptr<Texture3D> m_ColorGradingLUT;

        // Parameters with sensible defaults
        bool m_EnableBloom = true;
        float m_BloomThreshold = 1.5f;
        float m_BloomIntensity = 0.04f;
        int m_ToneMappingMode = 3;  // ACES
        float m_Exposure = 1.0f;
        float m_Gamma = 2.2f;
        // ...
    };
}
```

The `Process()` method chains the effects:

```cpp
void PostProcessPipeline::Process(std::shared_ptr<Texture> hdrColorTexture,
                                   Renderer& renderer,
                                   int windowWidth, int windowHeight)
{
    std::shared_ptr<Texture> bloomTexture = nullptr;

    // Step 1: Bloom (optional)
    if (m_EnableBloom && m_Bloom && m_Bloom->IsValid())
    {
        m_Bloom->SetThreshold(m_BloomThreshold);
        m_Bloom->SetKnee(m_BloomKnee);
        m_Bloom->SetIntensity(m_BloomIntensity);
        m_Bloom->Process(hdrColorTexture, m_BloomBlurPasses);
        bloomTexture = m_Bloom->GetBloomTexture();
    }

    // Step 2: Tone Mapping + Color Grading → screen
    // Unbind all framebuffers (render to screen)
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    renderer.SetViewport(0, 0, windowWidth, windowHeight);

    m_ToneMappingShader->Bind();
    hdrColorTexture->Bind(TextureSlots::HDRBuffer);
    m_ToneMappingShader->SetInt("u_HDRBuffer", TextureSlots::HDRBuffer);
    m_ToneMappingShader->SetFloat("u_Exposure", m_Exposure);
    m_ToneMappingShader->SetInt("u_ToneMappingMode", m_ToneMappingMode);

    if (bloomTexture)
    {
        bloomTexture->Bind(TextureSlots::BloomTexture);
        m_ToneMappingShader->SetInt("u_BloomTexture", TextureSlots::BloomTexture);
        m_ToneMappingShader->SetBool("u_BloomEnabled", true);
    }

    // Color grading LUT
    if (m_EnableColorGrading && m_ColorGradingLUT)
    {
        // Bind 3D LUT and set parameters...
    }

    m_FullscreenQuad->Draw();
}
```

---

## Step 6: Create SceneRenderer

The orchestrator ties everything together.

**Create** `VizEngine/src/VizEngine/Renderer/SceneRenderer.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/SceneRenderer.h

#pragma once

#include "VizEngine/Core.h"
#include "RenderPassData.h"
#include <memory>

namespace VizEngine
{
    class VizEngine_API SceneRenderer
    {
    public:
        SceneRenderer(int width, int height);
        ~SceneRenderer();

        /**
         * Execute the full rendering pipeline for one frame.
         */
        void Render(Scene& scene, Camera& camera, Renderer& renderer);

        /**
         * Switch the active rendering path at runtime.
         */
        void SetRenderPath(RenderPathType type);
        RenderPathType GetRenderPathType() const;
        const char* GetRenderPathName() const;

        void OnResize(int width, int height);
        void OnImGuiDebug();

        // External resource setters (called by SandboxApp during OnCreate)
        void SetDefaultLitShader(std::shared_ptr<Shader> shader);
        void SetPBRMaterial(std::shared_ptr<PBRMaterial> material);
        void SetIBLMaps(std::shared_ptr<Texture> irradiance,
                        std::shared_ptr<Texture> prefiltered,
                        std::shared_ptr<Texture> brdfLut);
        void SetDirectionalLight(DirectionalLight* light);
        void SetPointLights(glm::vec3* positions, glm::vec3* colors, int count);
        void SetSkybox(Skybox* skybox);

        // Post-processing access (for ImGui controls)
        PostProcessPipeline* GetPostProcess();
        ShadowPass* GetShadowPass();

        // HDR state
        std::shared_ptr<Texture> GetHDRColorTexture() const;
        std::shared_ptr<Framebuffer> GetHDRFramebuffer() const;

    private:
        void CreateHDRFramebuffer(int width, int height);
        void RenderStencilOutline(Scene& scene, Camera& camera, Renderer& renderer);

        // Rendering pipeline components
        std::unique_ptr<RenderPath> m_ActivePath;
        std::unique_ptr<ShadowPass> m_ShadowPass;
        std::unique_ptr<PostProcessPipeline> m_PostProcess;

        RenderPathType m_CurrentPathType = RenderPathType::Forward;

        // HDR framebuffer (shared across all paths)
        std::shared_ptr<Framebuffer> m_HDRFramebuffer;
        std::shared_ptr<Texture> m_HDRColorTexture;
        std::shared_ptr<Texture> m_HDRDepthTexture;

        // Shared rendering resources (set externally by SandboxApp)
        std::shared_ptr<Shader> m_DefaultLitShader;
        std::shared_ptr<PBRMaterial> m_PBRMaterial;

        // IBL, lights, skybox, outlines...
        // (full member list in source)
    };
}
```

The `Render()` method is the frame pipeline:

```cpp
void SceneRenderer::Render(Scene& scene, Camera& camera, Renderer& renderer)
{
    // Step 1: Shadow pass
    ShadowData shadowData;
    if (m_ShadowPass && m_ShadowPass->IsValid() && m_DirLight)
    {
        shadowData = m_ShadowPass->Process(scene, *m_DirLight, renderer);
    }

    // Step 2: Build RenderPassData
    RenderPassData data;
    data.ScenePtr = &scene;
    data.CameraPtr = &camera;
    data.RendererPtr = &renderer;
    data.Shadow = shadowData;
    data.TargetFramebuffer = m_HDRFramebuffer;
    data.Material = m_PBRMaterial;
    data.DefaultLitShader = m_DefaultLitShader;
    data.IrradianceMap = m_IrradianceMap;
    data.PrefilteredMap = m_PrefilteredMap;
    data.BRDFLut = m_BRDFLut;
    data.UseIBL = m_UseIBL;
    data.IBLIntensity = m_IBLIntensity;
    data.DirLight = m_DirLight;
    data.PointLightPositions = m_PointLightPositions;
    data.PointLightColors = m_PointLightColors;
    data.PointLightCount = m_PointLightCount;
    // ... clear color, lower hemisphere ...

    // Step 3: Execute active render path
    if (m_ActivePath && m_ActivePath->IsValid())
    {
        m_ActivePath->Execute(data);
    }

    // Step 4: Skybox (rendered into HDR framebuffer, after main pass)
    if (m_ShowSkybox && m_Skybox)
    {
        m_Skybox->Render(camera);
    }

    // Step 5: Stencil outlines (optional)
    if (m_EnableOutlines && m_OutlineShader)
    {
        RenderStencilOutline(scene, camera, renderer);
    }

    // Step 6: Post-processing (reads HDR buffer, renders to screen)
    if (m_PostProcess && m_PostProcess->IsValid())
    {
        m_PostProcess->Process(m_HDRColorTexture, renderer, m_Width, m_Height);
    }
}
```

### Runtime Path Switching

```cpp
void SceneRenderer::SetRenderPath(RenderPathType type)
{
    if (m_ActivePath) m_ActivePath->OnDetach();

    switch (type)
    {
        case RenderPathType::Forward:
            m_ActivePath = std::make_unique<ForwardRenderPath>();
            break;
        // Future:
        // case RenderPathType::ForwardPlus:
        //     m_ActivePath = std::make_unique<ForwardPlusRenderPath>();
        //     break;
        // case RenderPathType::Deferred:
        //     m_ActivePath = std::make_unique<DeferredRenderPath>();
        //     break;
    }

    if (m_ActivePath) m_ActivePath->OnAttach(m_Width, m_Height);
    m_CurrentPathType = type;
}
```

---

## Step 7: Update Build Files

**Update** `VizEngine/CMakeLists.txt`:

```cmake
# In VIZENGINE_SOURCES (Renderer subsection)
    src/VizEngine/Renderer/ShadowPass.cpp
    src/VizEngine/Renderer/PostProcessPipeline.cpp
    src/VizEngine/Renderer/ForwardRenderPath.cpp
    src/VizEngine/Renderer/SceneRenderer.cpp

# In VIZENGINE_HEADERS (Renderer subsection)
    src/VizEngine/Renderer/RenderPassData.h
    src/VizEngine/Renderer/RenderPath.h
    src/VizEngine/Renderer/ShadowPass.h
    src/VizEngine/Renderer/PostProcessPipeline.h
    src/VizEngine/Renderer/ForwardRenderPath.h
    src/VizEngine/Renderer/SceneRenderer.h
```

**Update** `VizEngine/src/VizEngine.h`:

```cpp
// Scene Renderer Architecture (Chapter 43)
#include "VizEngine/Renderer/RenderPassData.h"
#include "VizEngine/Renderer/RenderPath.h"
#include "VizEngine/Renderer/SceneRenderer.h"
```

---

## Step 8: Refactor SandboxApp

The key refactoring: replace the monolithic `OnRender()` with SceneRenderer delegation.

### Before (1660 lines)

```cpp
class Sandbox : public VizEngine::Application
{
    // ... 50+ member variables for rendering ...

    void OnRender() override
    {
        // 200+ lines: shadow pass, main render, skybox, outlines, post-process
    }
};
```

### After (970 lines)

```cpp
class Sandbox : public VizEngine::Application
{
    // Scene Renderer (Chapter 43)
    std::unique_ptr<VizEngine::SceneRenderer> m_SceneRenderer;

    void OnCreate() override
    {
        // ... scene setup, shader loading, IBL generation ...

        // Create SceneRenderer and configure it
        m_SceneRenderer = std::make_unique<VizEngine::SceneRenderer>(m_WindowWidth, m_WindowHeight);
        m_SceneRenderer->SetDefaultLitShader(m_DefaultLitShader);
        m_SceneRenderer->SetPBRMaterial(m_PBRMaterial);
        m_SceneRenderer->SetIBLMaps(m_IrradianceMap, m_PrefilteredMap, m_BRDFLut);
        m_SceneRenderer->SetDirectionalLight(&m_Light);
        m_SceneRenderer->SetPointLights(m_PBRLightPositions, m_PBRLightColors, 4);
        m_SceneRenderer->SetSkybox(&m_Skybox);
    }

    void OnRender() override
    {
        auto& renderer = VizEngine::Engine::Get().GetRenderer();

        // Main rendering — ONE LINE replaces 200+ lines
        m_SceneRenderer->Render(m_Scene, m_Camera, renderer);

        // Offscreen preview (F2 toggle, separate from SceneRenderer)
        if (m_Framebuffer && m_ShowFramebufferTexture && m_PBRMaterial)
        {
            // ... mini preview rendering ...
        }
    }
};
```

> [!NOTE]
> SandboxApp still owns scene objects, camera, shaders, IBL resources, and input handling. SceneRenderer receives pointers to these and orchestrates the rendering pipeline. The application remains the authority on *what* to render; SceneRenderer decides *how*.

---

## Testing and Validation

### Verify Identical Visual Output

The most important test: **the scene must look exactly the same after refactoring**.

1. Build and run
2. Compare with pre-refactor screenshots:
   - PBR materials render correctly (metallic spheres, rough surfaces)
   - IBL reflections present (irradiance + prefiltered)
   - Shadow mapping works (directional light shadows with PCF)
   - Bloom glow around bright surfaces
   - Tone mapping and color grading applied
   - Stencil outlines on selected object
   - Transparency sorting (back-to-front)

### No OpenGL Errors

With `GL_DEBUG_OUTPUT_SYNCHRONOUS` enabled, any errors will be caught immediately. Common issues during this refactor:

| Error | Cause | Solution |
|-------|-------|----------|
| `GL_INVALID_OPERATION: Uniform must be a matrix type` | Calling `SetMatrix4fv` for a `mat3` uniform (or vice versa) | Use `SetMatrix3fv` for `u_NormalMatrix` |
| Dark/black scene after post-processing | Post-processing clobbers OpenGL texture bindings | Call `material.Bind()` to rebind textures |
| Stencil outlines missing | View/projection not set on shader in stencil pass | Explicitly set `u_View`/`u_Projection` after `Bind()` |

### Runtime Path Switching

When the ImGui dropdown changes the render path, the scene should remain visually identical (since only Forward is implemented so far).

---

## Cross-Chapter Integration

### Callbacks to Previous Chapters

> In **Chapter 42**, we built the Material System. This chapter separates material concerns (surface properties) from renderer concerns (transforms, camera, lights). The PBRMaterial keeps `SetAlbedo()`, `SetMetallic()`, `SetIrradianceMap()`, etc. Transform matrices are now set directly on the shader by the render path.

> The shadow mapping from **Chapter 29** is extracted into `ShadowPass`, which owns its framebuffer, depth texture, and shader—following the same pattern as `Bloom` (Chapter 40).

> The post-processing chain from **Chapters 39-41** (HDR, Bloom, Color Grading) is composed into `PostProcessPipeline`, which reads the HDR framebuffer and outputs the final LDR image to the screen.

> The stencil outline technique from **Chapter 32** is preserved in `SceneRenderer::RenderStencilOutline()`, with explicit view/projection matrix setup to avoid relying on residual GL state.

### Forward References

> **Chapter 44: Light Management & SSBOs** introduces Shader Storage Buffer Objects for dynamic light counts. The `LightManager` will replace the raw pointer arrays in `RenderPassData` with SSBO-backed light data.

> **Chapter 45: Depth & Normal Prepass** adds a `DepthNormalPrepass` class (same pattern as ShadowPass and Bloom) that the SceneRenderer calls when `m_ActivePath->NeedsDepthPrepass()` returns true.

> **Chapter 46: Forward+ Rendering** adds `ForwardPlusRenderPath` — a new strategy that plugs into `SetRenderPath(RenderPathType::ForwardPlus)` with compute shader light culling.

> **Chapter 47: Deferred Rendering** adds `DeferredRenderPath` with a G-buffer geometry pass and fullscreen lighting pass, demonstrating MRT (Multiple Render Targets).

---

## Milestone

**Chapter 43 Complete — Scene Renderer Architecture**

At this point, your engine has:

**SceneRenderer orchestrator** that composes shadow, render path, skybox, outlines, and post-processing into a single `Render()` call.

**Strategy Pattern** for swappable render paths via `RenderPath` abstract base class and `ForwardRenderPath` concrete implementation.

**ShadowPass** extracted from SandboxApp with its own FBO, depth texture, and shader.

**PostProcessPipeline** composing Bloom + Tone Mapping + Color Grading.

**RenderPassData** structs providing a clean contract between orchestrator and render paths.

**Material/Renderer separation**: PBRMaterial owns surface properties and texture slots; renderers set transforms and lighting directly on the shader.

**SandboxApp reduced** from ~1660 to ~970 lines — now focused on scene setup, camera control, and ImGui UI.

**New file count**: 6 new files (RenderPassData.h, RenderPath.h, ShadowPass.h/cpp, PostProcessPipeline.h/cpp, ForwardRenderPath.h/cpp, SceneRenderer.h/cpp)

This architecture is the foundation for every remaining chapter in Part XII. Each new rendering technique plugs in as either a new `RenderPath` implementation or a new pass in the SceneRenderer pipeline.

---

## What's Next

In **Chapter 44: Light Management & SSBOs**, we'll introduce Shader Storage Buffer Objects (SSBOs) to support dynamic light counts. The current pipeline hardcodes 4 point lights as uniform arrays—SSBOs remove this limit, enabling scenes with hundreds of lights (a prerequisite for Forward+ and Deferred rendering).

> **Next:** [Chapter 44: Light Management & SSBOs](44_LightManagementSSBOs.md)

> **Previous:** [Chapter 42: Material System](42_MaterialSystem.md)

> **Index:** [Table of Contents](INDEX.md)
