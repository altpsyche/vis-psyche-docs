\newpage

# Chapter 44: Light Management & SSBOs

Replace raw light pointer arrays with a `LightManager` that owns its data and streams point lights to the GPU via a Shader Storage Buffer Object, removing the hard cap of four lights.

---

## Introduction

In **Chapter 43**, we extracted the rendering pipeline into a composable `SceneRenderer`. The result was clean at the orchestration level—but light data was left in its original form from the early Blinn-Phong days:

```cpp
// SceneRenderer.h — Chapter 43
DirectionalLight* m_DirLight = nullptr;
glm::vec3* m_PointLightPositions = nullptr;
glm::vec3* m_PointLightColors = nullptr;
int m_PointLightCount = 0;
```

And in `RenderPassData`, mirrored as raw pointers again:

```cpp
// RenderPassData.h — Chapter 43
DirectionalLight* DirLight = nullptr;
glm::vec3* PointLightPositions = nullptr;
glm::vec3* PointLightColors = nullptr;
int PointLightCount = 0;
```

The `ForwardRenderPath` then uploaded each light individually in a loop:

```cpp
shader->SetInt("u_LightCount", lightCount);
for (int i = 0; i < lightCount; ++i)
{
    shader->SetVec3("u_LightPositions[" + std::to_string(i) + "]", data.PointLightPositions[i]);
    shader->SetVec3("u_LightColors[" + std::to_string(i) + "]", data.PointLightColors[i]);
}
```

And the shader declared a fixed-size array:

```glsl
uniform vec3 u_LightPositions[4];
uniform vec3 u_LightColors[4];
uniform int u_LightCount;
```

**Three concrete problems:**

| Problem | Consequence |
|---------|-------------|
| **Pointer ownership** | `SceneRenderer` doesn't own the light data — it borrows raw pointers from `SandboxApp`. Lifetime bugs are silent. |
| **Separated position and color** | `PointLight` (Ch17) already bundles position, attenuation, and color together. The engine was ignoring attenuation and passing position/color as separate arrays. |
| **Fixed cap of 4** | The uniform array is declared at compile time. More than 4 lights requires a shader recompile. |

**This chapter's solution**: a `ShaderStorageBuffer` class that streams an arbitrary-length array of lights to the GPU, and a `LightManager` that owns the lights, manages the dirty state, and drives the upload.

---

## What We're Building

| Class / File | Description |
|---|---|
| **ShaderStorageBuffer** | RAII wrapper for `GL_SHADER_STORAGE_BUFFER`. Like `VertexBuffer` (Ch9) but for SSBOs. |
| **GPUPointLight** | POD struct matching the GLSL `std430` layout. Uploaded as a tightly-packed array. |
| **LightManager** | Owns `DirectionalLight` (value) and `vector<PointLight>`. Converts to `GPUPointLight`, uploads via dirty flag. |
| **RenderPassData** update | Replace four raw pointer fields with `LightManager* Lights`. |
| **SceneRenderer** update | Create and own `LightManager`. New API: `SetDirectionalLight(const&)`, `AddPointLight`, `ClearPointLights`. |
| **ForwardRenderPath** update | Bind SSBO; set `u_PointLightCount` uniform. |
| **defaultlit.shader** update | `layout(std430, binding=0) readonly buffer LightBuffer`; tri-factor attenuation. |

---

## Background: SSBOs vs Uniforms

Before writing code, it helps to know exactly what an SSBO is and why it fits this use case.

### Three ways to get data into a shader

| Mechanism | Size Limit | Writable from Shader | Variable-length array | Use case |
|---|---|---|---|---|
| Uniform variables | ~64 KB | No | No (fixed at compile time) | Per-frame scalars, matrices |
| Uniform Buffer Object (UBO) | ~64 KB | No | No | Shared constant data across shaders |
| **Shader Storage Buffer (SSBO)** | ≥128 MB guaranteed | Yes | **Yes** (`T array[]`) | Large, variable-length data |

Point lights are the canonical SSBO use case: the count varies, the data is large enough to stress UBO limits in complex scenes, and the shader only needs to read it.

### The GL call that matters

```cpp
// Bind an SSBO to a numbered "binding point"
glBindBufferBase(GL_SHADER_STORAGE_BUFFER, bindingPoint, m_ssbo);
```

The binding point is just an integer index—a rendezvous point between C++ and GLSL:

```cpp
// C++: bind to point 0
glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, m_ssbo);
```

```glsl
// GLSL: declare at point 0
layout(std430, binding = 0) readonly buffer LightBuffer { ... };
```

As long as both sides use the same integer, the GPU knows which buffer to read.

---

## Step 1: ShaderStorageBuffer

Create the RAII wrapper. It mirrors `VertexBuffer` (Chapter 9): generate on construction, delete on destruction, no copying.

**Create** `VizEngine/src/VizEngine/OpenGL/ShaderStorageBuffer.h`:

```cpp
// VizEngine/src/VizEngine/OpenGL/ShaderStorageBuffer.h
// Chapter 44: Light Management & SSBOs — RAII wrapper for GL_SHADER_STORAGE_BUFFER.
// Mirrors VertexBuffer (Chapter 9): construct, SetData, Bind to a binding point, destroy.

#pragma once

#include "VizEngine/Core.h"
#include <cstddef>

namespace VizEngine
{
    /**
     * ShaderStorageBuffer wraps a GL_SHADER_STORAGE_BUFFER (SSBO).
     *
     * SSBOs (OpenGL 4.3+) are like uniform buffers but:
     *   - Readable AND writable from shaders
     *   - Much larger capacity (at least 128 MB guaranteed)
     *   - Support variable-length arrays (`[]` in GLSL)
     *
     * Usage:
     *   ShaderStorageBuffer ssbo;
     *   ssbo.SetData(data.data(), data.size() * sizeof(T));  // upload
     *   ssbo.Bind(0);  // bind to binding point 0 → layout(binding=0) in shader
     */
    class VizEngine_API ShaderStorageBuffer
    {
    public:
        ShaderStorageBuffer();
        ~ShaderStorageBuffer();

        // Prevent copying — one buffer, one owner.
        ShaderStorageBuffer(const ShaderStorageBuffer&) = delete;
        ShaderStorageBuffer& operator=(const ShaderStorageBuffer&) = delete;

        // Allow moving.
        ShaderStorageBuffer(ShaderStorageBuffer&& other) noexcept;
        ShaderStorageBuffer& operator=(ShaderStorageBuffer&& other) noexcept;

        /**
         * Upload data to the GPU.
         * If size <= previously allocated size, uses glBufferSubData (no reallocation).
         * Otherwise reallocates with glBufferData and GL_DYNAMIC_DRAW.
         */
        void SetData(const void* data, size_t size);

        /**
         * Bind this SSBO to a numbered binding point.
         * Must match `layout(std430, binding = N)` in the GLSL shader.
         */
        void Bind(unsigned int bindingPoint) const;

        void Unbind() const;

        unsigned int GetID() const { return m_ssbo; }

    private:
        unsigned int m_ssbo = 0;
        size_t       m_allocatedSize = 0;
    };
}
```

**Create** `VizEngine/src/VizEngine/OpenGL/ShaderStorageBuffer.cpp`:

```cpp
// VizEngine/src/VizEngine/OpenGL/ShaderStorageBuffer.cpp
// Chapter 44: Light Management & SSBOs

#include "ShaderStorageBuffer.h"
#include <glad/glad.h>

namespace VizEngine
{
    ShaderStorageBuffer::ShaderStorageBuffer()
    {
        glGenBuffers(1, &m_ssbo);
    }

    ShaderStorageBuffer::~ShaderStorageBuffer()
    {
        if (m_ssbo)
            glDeleteBuffers(1, &m_ssbo);
    }

    ShaderStorageBuffer::ShaderStorageBuffer(ShaderStorageBuffer&& other) noexcept
        : m_ssbo(other.m_ssbo), m_allocatedSize(other.m_allocatedSize)
    {
        other.m_ssbo = 0;
        other.m_allocatedSize = 0;
    }

    ShaderStorageBuffer& ShaderStorageBuffer::operator=(ShaderStorageBuffer&& other) noexcept
    {
        if (this != &other)
        {
            if (m_ssbo)
                glDeleteBuffers(1, &m_ssbo);
            m_ssbo = other.m_ssbo;
            m_allocatedSize = other.m_allocatedSize;
            other.m_ssbo = 0;
            other.m_allocatedSize = 0;
        }
        return *this;
    }

    void ShaderStorageBuffer::SetData(const void* data, size_t size)
    {
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, m_ssbo);

        if (size <= m_allocatedSize)
        {
            // Reuse existing allocation — no realloc overhead.
            glBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, (GLsizeiptr)size, data);
        }
        else
        {
            // Allocate (or grow) the buffer.
            glBufferData(GL_SHADER_STORAGE_BUFFER, (GLsizeiptr)size, data, GL_DYNAMIC_DRAW);
            m_allocatedSize = size;
        }

        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0);
    }

    void ShaderStorageBuffer::Bind(unsigned int bindingPoint) const
    {
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, bindingPoint, m_ssbo);
    }

    void ShaderStorageBuffer::Unbind() const
    {
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0);
    }
}
```

### SetData: the allocation strategy

`SetData` tracks the last-allocated size and avoids a full `glBufferData` reallocation when the new data fits the existing buffer:

```
First frame (10 lights, 480 B):
  m_allocatedSize == 0 → glBufferData(480 B, GL_DYNAMIC_DRAW)
  m_allocatedSize = 480

Second frame (still 10 lights, 480 B):
  480 <= 480 → glBufferSubData (no realloc, faster)

Third frame (20 lights, 960 B):
  960 > 480 → glBufferData(960 B) — grows the buffer
  m_allocatedSize = 960
```

`glBufferData` orphans the old buffer and allocates a new one; the GPU can pipeline this without a stall. `glBufferSubData` just copies into the existing allocation — faster when the size is stable.

---

## Step 2: GPUPointLight and std430 Layout

Before building `LightManager`, we need to understand *why* the C++ struct must be written exactly the way it is.

### The std430 layout rules

GLSL's `std430` packing defines precise alignment rules for every type:

| GLSL type | Base alignment (bytes) |
|---|---|
| `float` | 4 |
| `vec2` | 8 |
| `vec3` | **16** (rounded up) |
| `vec4` | 16 |
| `struct` | max member alignment, rounded to 16 |

The key trap: **`vec3` has 16-byte alignment**. If you declare a GLSL struct with a `vec3` field, the GPU expects it at a 16-byte boundary, with 4 bytes of implicit padding after it. A C++ `glm::vec3` is only 12 bytes—so if you just `memcpy` a `glm::vec3` array, the GPU reads garbage.

### The solution: vec4 instead of vec3

Use `vec4` for position and color. A `vec4` is naturally 16-byte aligned and 16 bytes in size—there is no padding. The C++ `glm::vec4` has identical layout. The GPU reads exactly what you write.

```
GPUPointLight memory layout (std430):

Offset  Size  Field
──────  ────  ─────
0       16    Position  (vec4: xyz = world pos, w unused)
16      16    Color     (vec4: xyz = diffuse radiance, w unused)
32       4    Constant
36       4    Linear
40       4    Quadratic
44       4    _pad
Total   48 bytes — multiple of 16 ✓
```

The C++ struct mirrors this exactly:

```cpp
struct GPUPointLight
{
    glm::vec4 Position;   // 16 bytes
    glm::vec4 Color;      // 16 bytes
    float Constant;       //  4 bytes
    float Linear;         //  4 bytes
    float Quadratic;      //  4 bytes
    float _pad = 0.0f;    //  4 bytes (explicit — no surprises)
};                        // 48 bytes total
static_assert(sizeof(GPUPointLight) == 48,
    "GPUPointLight must be 48 bytes for std430 compatibility");
```

The `static_assert` turns a silent runtime misread into a compile error. If you ever change the struct and break the layout, the build tells you immediately.

> [!NOTE]
> `GPUPointLight` is a *separate* struct from `PointLight` (Chapter 17). `PointLight` is the user-facing representation with `Ambient`, `Diffuse`, `Specular` — a Blinn-Phong legacy. `GPUPointLight` is the GPU-side layout optimized for PBR: just position, a single diffuse color (the radiance), and the three attenuation coefficients. `LightManager::Upload()` converts between them.

---

## Step 3: LightManager

`LightManager` owns the lights, manages a dirty flag, and drives the `ShaderStorageBuffer`.

**Create** `VizEngine/src/VizEngine/Renderer/LightManager.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/LightManager.h
// Chapter 44: Light Management & SSBOs — owns scene lights and streams point lights
// to the GPU via a Shader Storage Buffer Object.

#pragma once

#include "VizEngine/Core.h"
#include "VizEngine/Core/Light.h"
#include "VizEngine/OpenGL/ShaderStorageBuffer.h"
#include "glm.hpp"
#include <vector>
#include <memory>

namespace VizEngine
{
    /**
     * GPU-side point light struct matching GLSL std430 layout.
     *
     * std430 packs vec3 with 16-byte alignment, leaving 4 bytes of implicit padding
     * after each vec3 field. Using vec4 instead absorbs that padding explicitly and
     * makes the C++ struct layout identical to what the GPU sees — no surprises.
     *
     * Size: 2 × vec4 (32 B) + 3 × float + pad (16 B) = 48 bytes per light.
     * The GLSL counterpart (layout(std430)) produces the same 48-byte stride.
     */
    struct GPUPointLight
    {
        glm::vec4 Position;   // xyz = world position, w unused
        glm::vec4 Color;      // xyz = diffuse radiance, w unused
        float Constant;
        float Linear;
        float Quadratic;
        float _pad = 0.0f;
    };
    static_assert(sizeof(GPUPointLight) == 48,
        "GPUPointLight must be 48 bytes for std430 compatibility");

    /**
     * LightManager owns the scene's lights and handles GPU upload.
     *
     * Responsibilities:
     *   - Stores DirectionalLight (value, not pointer — no dangling risk)
     *   - Stores an arbitrary number of PointLights (vector, no fixed cap)
     *   - Converts PointLight → GPUPointLight and uploads to SSBO on demand
     *   - Dirty flag: skips re-upload when lights haven't changed
     *
     * SceneRenderer owns one LightManager and calls Upload() + Bind() each frame
     * before dispatching to the active render path.
     */
    class VizEngine_API LightManager
    {
    public:
        LightManager();

        // =====================================================================
        // Mutation (each sets m_Dirty = true)
        // =====================================================================

        void AddPointLight(const PointLight& light);
        void ClearPointLights();
        void SetDirectionalLight(const DirectionalLight& light);

        // =====================================================================
        // Accessors
        // =====================================================================

        const DirectionalLight& GetDirectionalLight() const { return m_DirLight; }
        bool HasDirectionalLight() const { return m_HasDirLight; }
        int  GetPointLightCount() const  { return static_cast<int>(m_PointLights.size()); }

        // =====================================================================
        // GPU operations (called by SceneRenderer once per frame)
        // =====================================================================

        /**
         * Convert PointLights to GPUPointLight array and upload to SSBO.
         * No-op if nothing changed since last Upload().
         */
        void Upload();

        /**
         * Bind the SSBO to a numbered binding point.
         * Must match `layout(std430, binding = N)` in the shader.
         * Default binding point 0 matches the defaultlit.shader LightBuffer block.
         */
        void Bind(unsigned int bindingPoint = 0) const;

    private:
        DirectionalLight         m_DirLight;
        bool                     m_HasDirLight = false;

        std::vector<PointLight>  m_PointLights;

        std::unique_ptr<ShaderStorageBuffer> m_SSBO;
        bool m_Dirty = true;
    };
}
```

**Create** `VizEngine/src/VizEngine/Renderer/LightManager.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/LightManager.cpp
// Chapter 44: Light Management & SSBOs

#include "LightManager.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    LightManager::LightManager()
        : m_SSBO(std::make_unique<ShaderStorageBuffer>())
    {
    }

    void LightManager::AddPointLight(const PointLight& light)
    {
        m_PointLights.push_back(light);
        m_Dirty = true;
    }

    void LightManager::ClearPointLights()
    {
        m_PointLights.clear();
        m_Dirty = true;
    }

    void LightManager::SetDirectionalLight(const DirectionalLight& light)
    {
        m_DirLight = light;
        m_HasDirLight = true;
        m_Dirty = true;
    }

    void LightManager::Upload()
    {
        if (!m_Dirty)
            return;

        if (m_PointLights.empty())
        {
            // Upload a single zero-filled light so the SSBO is never empty.
            // The shader uses u_PointLightCount to skip the loop — this is safe.
            GPUPointLight empty{};
            m_SSBO->SetData(&empty, sizeof(GPUPointLight));
        }
        else
        {
            // Convert PointLight (Blinn-Phong layout) → GPUPointLight (std430).
            std::vector<GPUPointLight> gpu;
            gpu.reserve(m_PointLights.size());

            for (const auto& pl : m_PointLights)
            {
                GPUPointLight g;
                g.Position  = glm::vec4(pl.Position, 0.0f);
                g.Color     = glm::vec4(pl.Diffuse,  0.0f);  // PBR uses diffuse as radiance
                g.Constant  = pl.Constant;
                g.Linear    = pl.Linear;
                g.Quadratic = pl.Quadratic;
                g._pad      = 0.0f;
                gpu.push_back(g);
            }

            m_SSBO->SetData(gpu.data(), gpu.size() * sizeof(GPUPointLight));
        }

        m_Dirty = false;
    }

    void LightManager::Bind(unsigned int bindingPoint) const
    {
        m_SSBO->Bind(bindingPoint);
    }
}
```

### The dirty flag

Every mutation method sets `m_Dirty = true`. `Upload()` checks the flag first and returns early if nothing changed:

```
Frame N:   AddPointLight() called → m_Dirty = true
           Upload() → converts + uploads → m_Dirty = false

Frame N+1: No changes
           Upload() → m_Dirty == false → early return (no GL call)

Frame N+2: ColorEdit3 in UI → ClearPointLights + AddPointLight → m_Dirty = true
           Upload() → re-converts + uploads → m_Dirty = false
```

The dirty flag makes the common case (static lights, most frames) zero-overhead at the upload level.

### Why a placeholder when empty?

Uploading a single zeroed element is a belt-and-suspenders measure — the buffer is always a valid, non-empty allocation regardless of what any driver does with a zero-size SSBO. The shader's `u_PointLightCount` uniform controls loop iteration count, so the placeholder is never read.

---

## Step 4: Wire SceneRenderer

### RenderPassData

Replace the four raw pointer light fields with a single `LightManager*` forward declaration.

**Modify** `VizEngine/src/VizEngine/Renderer/RenderPassData.h`:

```cpp
// Forward declaration — no include needed
class LightManager;

// In RenderPassData struct:

// Before:
DirectionalLight* DirLight = nullptr;
glm::vec3* PointLightPositions = nullptr;
glm::vec3* PointLightColors = nullptr;
int PointLightCount = 0;

// After:
LightManager* Lights = nullptr;
```

The `DirectionalLight` forward declaration can also be removed now since it was only needed for the raw pointer field.

### SceneRenderer.h

**Modify** `VizEngine/src/VizEngine/Renderer/SceneRenderer.h`:

```cpp
// Add forward declarations:
class LightManager;
struct PointLight;

// Replace setters:

// Before:
void SetDirectionalLight(DirectionalLight* light) { m_DirLight = light; }
void SetPointLights(glm::vec3* positions, glm::vec3* colors, int count);

// After:
void SetDirectionalLight(const DirectionalLight& light);
void AddPointLight(const PointLight& light);
void ClearPointLights();
LightManager* GetLightManager() { return m_LightManager.get(); }

// Replace private members:

// Before:
DirectionalLight* m_DirLight = nullptr;
glm::vec3* m_PointLightPositions = nullptr;
glm::vec3* m_PointLightColors = nullptr;
int m_PointLightCount = 0;

// After:
std::unique_ptr<LightManager> m_LightManager;
```

### SceneRenderer.cpp

The constructor creates the `LightManager`. `Render()` calls `Upload()` and `Bind()` before the shadow pass, so the SSBO is ready for every pass that follows.

**Modify** `VizEngine/src/VizEngine/Renderer/SceneRenderer.cpp`:

```cpp
// Include:
#include "LightManager.h"

// Constructor — after creating the post-process pipeline:
m_LightManager = std::make_unique<LightManager>();

// Render() — before the shadow pass:
// 0. Light upload — convert + stream to SSBO before any pass
m_LightManager->Upload();
m_LightManager->Bind(0);

// Shadow pass — use LightManager instead of raw pointer:
if (m_ShadowPass && m_ShadowPass->IsValid() && m_LightManager->HasDirectionalLight())
{
    shadowData = m_ShadowPass->Process(
        scene, m_LightManager->GetDirectionalLight(), renderer);
}

// RenderPassData assembly — replace four raw fields with one:
passData.Lights = m_LightManager.get();

// Replace SetPointLights implementation with the three new methods:
void SceneRenderer::SetDirectionalLight(const DirectionalLight& light)
{
    m_LightManager->SetDirectionalLight(light);
}

void SceneRenderer::AddPointLight(const PointLight& light)
{
    m_LightManager->AddPointLight(light);
}

void SceneRenderer::ClearPointLights()
{
    m_LightManager->ClearPointLights();
}
```

### Why Upload before the shadow pass?

The shadow pass doesn't read the point light SSBO, but `Bind(0)` establishes the binding point for the duration of the frame. Once `glBindBufferBase` is called, the binding persists until explicitly changed. The forward pass executes after the shadow pass and reads the already-bound SSBO—no rebind needed.

`ForwardRenderPath::SetupLighting` calls `data.Lights->Bind(0)` again as a defensive measure (in case a future render path or post-process step rebinds point 0), but for the forward path it's a no-op.

---

## Step 5: Wire ForwardRenderPath

`SetupLighting` previously ran a loop building uniform strings like `"u_LightPositions[2]"`. That loop is gone. One bind call and one integer uniform replaces it.

**Modify** `VizEngine/src/VizEngine/Renderer/ForwardRenderPath.cpp`:

```cpp
// Include:
#include "LightManager.h"

// SetupLighting — replace the point-light loop:

// Before:
int lightCount = data.PointLightCount;
if (lightCount > 0 && (!data.PointLightPositions || !data.PointLightColors))
    lightCount = 0;

shader->SetInt("u_LightCount", lightCount);
for (int i = 0; i < lightCount; ++i)
{
    shader->SetVec3("u_LightPositions[" + std::to_string(i) + "]",
                    data.PointLightPositions[i]);
    shader->SetVec3("u_LightColors[" + std::to_string(i) + "]",
                    data.PointLightColors[i]);
}

// After:
// Point lights — SSBO already uploaded + bound by SceneRenderer.
// Just tell the shader how many entries are valid.
if (data.Lights)
{
    data.Lights->Bind(0);
    shader->SetInt("u_PointLightCount", data.Lights->GetPointLightCount());
}
else
{
    shader->SetInt("u_PointLightCount", 0);
}

// Directional light — replace data.DirLight pointer:
if (data.Lights && data.Lights->HasDirectionalLight())
{
    const auto& dl = data.Lights->GetDirectionalLight();
    shader->SetBool("u_UseDirLight", true);
    shader->SetVec3("u_DirLightDirection", dl.GetDirection());
    shader->SetVec3("u_DirLightColor", dl.Diffuse);
}
else
{
    shader->SetBool("u_UseDirLight", false);
}
```

Also update `RenderInstancedObject` which had its own `data.DirLight` check:

```cpp
// Before:
if (data.DirLight)
{
    shader.SetVec3("u_DirLightDirection", data.DirLight->GetDirection());
    shader.SetVec3("u_DirLightColor", data.DirLight->Diffuse);
}

// After:
if (data.Lights && data.Lights->HasDirectionalLight())
{
    const auto& dl = data.Lights->GetDirectionalLight();
    shader.SetVec3("u_DirLightDirection", dl.GetDirection());
    shader.SetVec3("u_DirLightColor", dl.Diffuse);
}
```

---

## Step 6: Update the Shader

The shader change is the most visible part of this chapter. The fixed uniform arrays become a single SSBO block, and the attenuation model gains the full three-factor formula from Chapter 17.

**Modify** `VizEngine/src/resources/shaders/defaultlit.shader`:

### Remove the old uniform arrays

```glsl
// Remove:
uniform vec3 u_LightPositions[4];
uniform vec3 u_LightColors[4];
uniform int u_LightCount;
```

### Add the SSBO block

Place this after the camera uniforms, before `main()`:

```glsl
// ============================================================================
// Lights — Chapter 44: SSBO replaces fixed uniform arrays (no 4-light cap).
//
// GPUPointLight must match the C++ GPUPointLight struct in LightManager.h.
// std430 packs vec4 at 16-byte alignment, float at 4-byte — 48 bytes total.
// ============================================================================
struct PointLight
{
    vec4 Position;   // xyz = world position, w unused
    vec4 Color;      // xyz = diffuse radiance, w unused
    float Constant;
    float Linear;
    float Quadratic;
    float _pad;
};

layout(std430, binding = 0) readonly buffer LightBuffer
{
    PointLight lights[];
};
uniform int u_PointLightCount;
```

### Update the lighting loop

```glsl
// Before:
for (int i = 0; i < u_LightCount; ++i)
{
    vec3 L = normalize(u_LightPositions[i] - v_WorldPos);
    vec3 H = normalize(V + L);
    float distance = length(u_LightPositions[i] - v_WorldPos);

    float attenuation = 1.0 / (distance * distance);
    vec3 radiance = u_LightColors[i] * attenuation;
    ...
}

// After:
for (int i = 0; i < u_PointLightCount; ++i)
{
    vec3 lightPos = lights[i].Position.xyz;
    vec3 L = normalize(lightPos - v_WorldPos);
    vec3 H = normalize(V + L);
    float dist = length(lightPos - v_WorldPos);

    // Tri-factor attenuation (Chapter 17): 1 / (Kc + Kl*d + Kq*d²)
    // Artist-controllable falloff vs the physically correct inverse-square.
    float attenuation = 1.0 / (lights[i].Constant
                              + lights[i].Linear    * dist
                              + lights[i].Quadratic * dist * dist);
    vec3 radiance = lights[i].Color.xyz * attenuation;
    ...
}
```

### Attenuation: inverse-square vs tri-factor

The old shader used `1.0 / (distance * distance)` — the physically correct inverse-square law. The new shader uses the tri-factor model from Chapter 17's `PointLight` struct:

```
attenuation = 1 / (Kc + Kl*d + Kq*d²)
```

This gives artists three knobs:

| Coefficient | Effect |
|---|---|
| **Kc** (Constant) | Minimum attenuation floor. Keep at 1.0. |
| **Kl** (Linear) | Linear falloff. Larger → faster dropoff. |
| **Kq** (Quadratic) | Quadratic falloff. Dominates at distance. |

The `PointLight` struct's defaults (`Constant=1.0`, `Linear=0.09`, `Quadratic=0.032`) give a range of roughly 30 units—appropriate for a room-sized scene. Inverse-square gives infinite physical range but no artist control over where the light effectively cuts off.

---

## Step 7: Update SandboxApp

`SandboxApp` previously passed raw pointers and separate arrays. The new API takes values and individual lights.

**Initialization** (inside `OnCreate`):

```cpp
// Before:
m_SceneRenderer->SetDirectionalLight(&m_Light);
m_SceneRenderer->SetPointLights(m_PBRLightPositions, m_PBRLightColors, 4);

// After:
m_SceneRenderer->SetDirectionalLight(m_Light);
for (int i = 0; i < 4; ++i)
{
    VizEngine::PointLight pl;
    pl.Position = m_PBRLightPositions[i];
    pl.Diffuse  = m_PBRLightColors[i];
    m_SceneRenderer->AddPointLight(pl);
}
```

**UI callbacks** — sync LightManager when the user edits values:

```cpp
// Before: fire-and-forget widget calls
uiManager.DragFloat3("Direction", &m_Light.Direction.x, 0.01f, -1.0f, 1.0f);
uiManager.ColorEdit3("Dir Color", &m_Light.Diffuse.x);

// After: sync on change
if (uiManager.DragFloat3("Direction", &m_Light.Direction.x, 0.01f, -1.0f, 1.0f))
    m_SceneRenderer->SetDirectionalLight(m_Light);
if (uiManager.ColorEdit3("Dir Color", &m_Light.Diffuse.x))
    m_SceneRenderer->SetDirectionalLight(m_Light);
```

For point light intensity and color changes, a local lambda avoids repetition:

```cpp
auto rebuildPointLights = [&]()
{
    m_SceneRenderer->ClearPointLights();
    for (int i = 0; i < 4; ++i)
    {
        VizEngine::PointLight pl;
        pl.Position = m_PBRLightPositions[i];
        pl.Diffuse  = m_PBRLightColors[i];
        m_SceneRenderer->AddPointLight(pl);
    }
};

if (uiManager.SliderFloat("Intensity", &m_PBRLightIntensity, 0.0f, 1000.0f))
{
    for (int i = 0; i < 4; ++i)
        m_PBRLightColors[i] = m_PBRLightColor * m_PBRLightIntensity;
    rebuildPointLights();
}
if (uiManager.ColorEdit3("Point Color", &m_PBRLightColor.x))
{
    for (int i = 0; i < 4; ++i)
        m_PBRLightColors[i] = m_PBRLightColor * m_PBRLightIntensity;
    rebuildPointLights();
}
```

> [!NOTE]
> With the old pointer API, any mutation to `m_Light` was automatically visible to the renderer—the pointer always pointed at the live struct. With `LightManager`, it owns a copy, so you must call `SetDirectionalLight(m_Light)` to sync changes. This is the cost of clear ownership: the engine controls its own data lifetime, but the caller must explicitly push updates. The dirty flag means multiple `SetDirectionalLight` calls in a frame are coalesced into one GPU upload.

---

## CMakeLists.txt

Add the four new files to the explicit source list in `VizEngine/CMakeLists.txt`:

```cmake
# OpenGL sources:
src/VizEngine/OpenGL/ShaderStorageBuffer.cpp

# Renderer sources:
src/VizEngine/Renderer/LightManager.cpp

# OpenGL headers:
src/VizEngine/OpenGL/ShaderStorageBuffer.h

# Renderer headers:
src/VizEngine/Renderer/LightManager.h
```

---

## What We Changed

| Before (Chapter 43) | After (Chapter 44) |
|---|---|
| `DirectionalLight* m_DirLight` in SceneRenderer | `LightManager` owns a `DirectionalLight` value |
| `glm::vec3* m_PointLightPositions/Colors` | `vector<PointLight>` — no pointer aliasing |
| Fixed cap of 4 lights | Arbitrary count via `vector<>` and SSBO |
| Per-light `shader->SetVec3` loop each frame | Single `Bind(0)` + one `SetInt` |
| Inverse-square attenuation in shader | Tri-factor attenuation via SSBO data |
| `SetDirectionalLight(DirectionalLight*)` | `SetDirectionalLight(const DirectionalLight&)` |
| `SetPointLights(vec3*, vec3*, int)` | `AddPointLight / ClearPointLights` |

The `SceneRenderer` now owns everything it needs for a frame. No raw pointers into application memory.

---

## What's Next

Chapter 44 removes the light cap from the forward path. The same SSBO binding point 0 is available to Forward+ (Chapter 46) and Deferred (Chapter 47)—those paths read the same `LightBuffer` block and add tile-based or screen-space culling on top of it.

Before those advanced paths, **Chapter 45: Depth Prepass** adds an optional geometry pass that writes depth before the main render. Forward+ requires it; it also enables screen-space effects (SSAO, SSR) that need a camera-space depth buffer before shading begins.
