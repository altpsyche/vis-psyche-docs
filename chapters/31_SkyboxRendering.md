\newpage

# Chapter 31: Skybox Rendering

Render immersive environment backgrounds using cubemap textures and specialized shader techniques.

---

## Introduction

In **Chapter 30**, you created a cubemap texture by converting an equirectangular HDR image. Now we'll use that cubemap to create a **skybox**—an environment cube that wraps around your scene, providing an immersive background.

**What is a Skybox?**
A skybox is a large cube textured with an environment map that:
- Surrounds the camera at all times
- Rotates with camera rotation (but not translation)
- Renders at infinite distance (always behind geometry)
- Provides visual context for the scene

This chapter focuses on the **rendering technique**, building directly on the cubemap you already created.

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **Skybox Shader** | Specialized vertex/fragment shader with depth trick |
| **Skybox Class** | Reusable renderer for cubemap backgrounds |
| **Camera Integration** | View matrix transformation for infinite distance illusion |
| **SandboxApp Integration** | Load and render skybox with toggle controls |
| **Environment Mapping Preview** | Understanding how skyboxes enable reflections |

**End result**: A scene surrounded by a photorealistic environment that enhances immersion.

---

## Skybox Rendering Theory

### The Challenge

We want a textured cube that:
- **Surrounds** the camera (infinite distance illusion)
- **Rotates** with camera rotation (not translation)
- **Never gets closer** when you move forward

If we rendered a normal cube at the camera position, it would move as you walk forward—breaking the illusion of an infinite environment.

### The Solution: Two Key Techniques

#### 1. Remove Translation from View Matrix

**Normal view matrix** includes both rotation and translation:
```cpp
glm::mat4 view = camera.GetViewMatrix();  // Translation + Rotation
```

**Skybox view matrix** (rotation only):
```cpp
glm::mat4 viewNoTranslation = glm::mat4(glm::mat3(view));
```

**How this works:**
- `glm::mat3(view)` extracts the upper-left 3×3 matrix (rotation only)
- `glm::mat4(...)` converts back to 4×4 with translation = (0, 0, 0)
- Result: Skybox rotates with camera but never moves in space

#### 2. Render at Maximum Depth

We want the skybox to render **behind** all geometry. The depth trick forces it to the far plane:

```glsl
// In vertex shader
vec4 pos = u_Projection * viewNoTranslation * vec4(aPos, 1.0);
gl_Position = pos.xyww;  // Swizzle to set z = w
```

**Why `z = w`?**
- After perspective divide: `z/w = w/w = 1.0`
- Depth = 1.0 is the maximum depth value (far plane)
- All geometry (depth < 1.0) renders in front

### Render Order

**Option 1: Render Last** (used in this chapter):
```cpp
// Scene first
RenderScene();

// Skybox last with depth disabled
glDepthMask(GL_FALSE);
RenderSkybox();
glDepthMask(GL_TRUE);
```

**Option 2: Render First**:
```cpp
RenderSkybox();
glClear(GL_DEPTH_BUFFER_BIT);  // Clear depth after skybox
RenderScene();
```

Option 1 is more common and efficient—skybox only renders where no geometry exists.

### Depth Function 

We use `glDepthFunc(GL_LEQUAL)` to allow depth = 1.0 to pass the depth test:

```cpp
glDepthFunc(GL_LEQUAL);  // Allow z = 1.0 (skybox)
RenderSkybox();
glDepthFunc(GL_LESS);     // Restore default
```

---

## Step 1: Create Skybox Rendering Shader

This shader samples the cubemap and implements the depth trick.

**Create `VizEngine/src/resources/shaders/skybox.shader`:**

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 aPos;

out vec3 v_TexCoords;

uniform mat4 u_Projection;
uniform mat4 u_View;

void main()
{
    v_TexCoords = aPos;
    
    // Remove translation from view matrix (keep rotation only)
    mat4 viewNoTranslation = mat4(mat3(u_View));
    
    vec4 pos = u_Projection * viewNoTranslation * vec4(aPos, 1.0);
    
    // Set depth to maximum (far plane) so skybox renders behind everything
    gl_Position = pos.xyww;  // Equivalent to setting z = w
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec3 v_TexCoords;

uniform samplerCube u_Skybox;

void main()
{
    // Sample cubemap using 3D direction vector
    vec3 color = texture(u_Skybox, v_TexCoords).rgb;
    
    FragColor = vec4(color, 1.0);
}
```

> [!NOTE]
> **Depth Trick Explained**: `gl_Position = pos.xyww` swizzles the position to set `z = w`. After perspective divide (`z/w`), depth becomes 1.0 (maximum depth).

---

## Step 2: Update Build Configuration

Before implementing the Skybox class, add the new files to the build system.

**Modify `VizEngine/CMakeLists.txt`:**

In the `VIZENGINE_SOURCES` section, add after `CubemapUtils.cpp`:

```cmake
    # Renderer
    src/VizEngine/Renderer/Skybox.cpp
```

In the `VIZENGINE_HEADERS` section, add after `CubemapUtils.h`:

```cmake
    # Renderer headers
    src/VizEngine/Renderer/Skybox.h
```

**Modify `VizEngine/src/VizEngine.h`:**

Add to the includes section (after `CubemapUtils.h`):

```cpp
#include "VizEngine/Renderer/Skybox.h"
```

> [!NOTE]
> This creates a new `Renderer` category in the build system for rendering-related classes (as opposed to low-level OpenGL wrappers).

---

## Step 3: Create Skybox Class

Encapsulate skybox rendering logic in a reusable class.

**Create `VizEngine/src/VizEngine/Renderer/Skybox.h`:**

```cpp
// VizEngine/src/VizEngine/Renderer/Skybox.h

#pragma once

#include <memory>
#include "VizEngine/Core.h"

namespace VizEngine
{
class Texture;
class Shader;
class VertexArray;
class VertexBuffer;
class Camera;

/**
 * Skybox renderer using cubemap textures.
 * Renders an environment cube that follows camera rotation but not translation.
 */
class VizEngine_API Skybox
{
public:
/**
 * Create skybox from cubemap texture.
 * @param cubemap Cubemap texture (must be GL_TEXTURE_CUBE_MAP)
 */
Skybox(std::shared_ptr<Texture> cubemap);
~Skybox() = default;

/**
 * Render the skybox.
 * Call this after rendering the scene (with depth write disabled if needed).
 * @param camera Camera for view/projection matrices
 */
void Render(const Camera& camera);

private:
std::shared_ptr<Texture> m_Cubemap;
std::unique_ptr<VertexArray> m_VAO;
std::unique_ptr<VertexBuffer> m_VBO;
std::shared_ptr<Shader> m_Shader;

void SetupMesh();
};
}
```

**Create `VizEngine/src/VizEngine/Renderer/Skybox.cpp`:**

```cpp
// VizEngine/src/VizEngine/Renderer/Skybox.cpp

#include "Skybox.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/VertexArray.h"
#include "VizEngine/OpenGL/VertexBuffer.h"
#include "VizEngine/Core/Camera.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>
#include <glm.hpp>

namespace VizEngine
{
	Skybox::Skybox(std::shared_ptr<Texture> cubemap)
		: m_Cubemap(cubemap)
	{
		if (!m_Cubemap)
		{
			VP_CORE_ERROR("Skybox: Cubemap texture is null!");
			throw std::runtime_error("Skybox: Cannot create skybox with null cubemap");
		}

		if (!m_Cubemap->IsCubemap())
		{
			VP_CORE_ERROR("Skybox: Texture is not a cubemap!");
		}

// Load skybox shader
m_Shader = std::make_shared<Shader>("resources/shaders/skybox.shader");

// Setup cube mesh
SetupMesh();

VP_CORE_INFO("Skybox created");
}

void Skybox::SetupMesh()
{
// Cube vertices (positions only)
// Skybox cube is centered at origin with size 1
float skyboxVertices[] = {
// Positions          
-1.0f,  1.0f, -1.0f,
-1.0f, -1.0f, -1.0f,
 1.0f, -1.0f, -1.0f,
 1.0f, -1.0f, -1.0f,
 1.0f,  1.0f, -1.0f,
-1.0f,  1.0f, -1.0f,

-1.0f, -1.0f,  1.0f,
-1.0f, -1.0f, -1.0f,
-1.0f,  1.0f, -1.0f,
-1.0f,  1.0f, -1.0f,
-1.0f,  1.0f,  1.0f,
-1.0f, -1.0f,  1.0f,

 1.0f, -1.0f, -1.0f,
 1.0f, -1.0f,  1.0f,
 1.0f,  1.0f,  1.0f,
 1.0f,  1.0f,  1.0f,
 1.0f,  1.0f, -1.0f,
 1.0f, -1.0f, -1.0f,

-1.0f, -1.0f,  1.0f,
-1.0f,  1.0f,  1.0f,
 1.0f,  1.0f,  1.0f,
 1.0f,  1.0f,  1.0f,
 1.0f, -1.0f,  1.0f,
-1.0f, -1.0f,  1.0f,

-1.0f,  1.0f, -1.0f,
 1.0f,  1.0f, -1.0f,
 1.0f,  1.0f,  1.0f,
 1.0f,  1.0f,  1.0f,
-1.0f,  1.0f,  1.0f,
-1.0f,  1.0f, -1.0f,

-1.0f, -1.0f, -1.0f,
-1.0f, -1.0f,  1.0f,
 1.0f, -1.0f, -1.0f,
 1.0f, -1.0f, -1.0f,
-1.0f, -1.0f,  1.0f,
 1.0f, -1.0f,  1.0f
};

// Create VBO
m_VBO = std::make_unique<VertexBuffer>(skyboxVertices, sizeof(skyboxVertices));

// Create VAO with layout
VertexBufferLayout layout;
layout.Push<float>(3);  // Position only

m_VAO = std::make_unique<VertexArray>();
m_VAO->LinkVertexBuffer(*m_VBO, layout);
}

void Skybox::Render(const Camera& camera)
{
// Disable depth writing (skybox should not block other objects)
glDepthFunc(GL_LEQUAL);  // Allow depth = 1.0 to pass
glDepthMask(GL_FALSE);

m_Shader->Bind();

// Set uniforms
m_Shader->SetMatrix4fv("u_View", camera.GetViewMatrix());
m_Shader->SetMatrix4fv("u_Projection", camera.GetProjectionMatrix());

// Bind cubemap
m_Cubemap->Bind(0);
m_Shader->SetInt("u_Skybox", 0);

// Render cube
m_VAO->Bind();
glDrawArrays(GL_TRIANGLES, 0, 36);

// Restore depth settings
glDepthMask(GL_TRUE);
glDepthFunc(GL_LESS);
}
}
```

> [!IMPORTANT]
> **Depth Function**: We set `glDepthFunc(GL_LEQUAL)` to allow fragments at exactly depth = 1.0 to pass the depth test. Then restore `GL_LESS` after rendering.

---

## Step 4: Integrate Skybox in SandboxApp

Now we can load an HDRI, convert it, and render the skybox.

### Download a Free HDRI

Visit [polyhaven.com](https://polyhaven.com/hdris) and download a free HDRI:
- Recommended: **"Qwantani Dusk 2 Puresky"** (2K HDR)
- Save to: `VizEngine/src/resources/textures/environments/qwantani_dusk_2_puresky_2k.hdr`

### Update SandboxApp.h

**Add to `Sandbox/src/SandboxApp.h`:**

```cpp
// Skybox members
std::shared_ptr<VizEngine::Texture> m_EnvironmentHDRI;
std::shared_ptr<VizEngine::Texture> m_SkyboxCubemap;
std::unique_ptr<VizEngine::Skybox> m_Skybox;
bool m_ShowSkybox = true;
```

### Update SandboxApp.cpp

**In `OnCreate()`, add after existing setup:**

```cpp
// =========================================================================
// Create Skybox from HDRI
// =========================================================================
VP_INFO("Loading environment HDRI...");

// Load HDR equirectangular map
m_EnvironmentHDRI = std::make_shared<VizEngine::Texture>(
    "resources/textures/environments/qwantani_dusk_2_puresky_2k.hdr", 
    true  // isHDR
);

// Convert to cubemap (one-time operation)
int cubemapResolution = 512;  // 512x512 per face
m_SkyboxCubemap = VizEngine::CubemapUtils::EquirectangularToCubemap(
    m_EnvironmentHDRI, 
    cubemapResolution
);

// Release original HDRI to free memory (~6MB for 2K texture)
// The cubemap now contains all the data we need
m_EnvironmentHDRI.reset();

// Create skybox
m_Skybox = std::make_unique<VizEngine::Skybox>(m_SkyboxCubemap);

VP_INFO("Skybox ready!");
```

**In `OnRender()`, add at the end (after scene rendering):**

```cpp
// Render scene with shadows
m_Scene.Render(renderer, *m_LitShader, m_Camera);

// Render Skybox to offscreen framebuffer
if (m_ShowSkybox)
{
    m_Skybox->Render(m_Camera);
}

m_Framebuffer->Unbind();

// Restore camera to window aspect ratio
m_Camera.SetAspectRatio(windowAspect);

// Restore viewport to window size
// Restore viewport to window size
renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);

// =========================================================================
// Render Skybox to screen as well
// =========================================================================
if (m_ShowSkybox)
{
    m_Skybox->Render(m_Camera);
}
```

> [!NOTE]
> **Intentional Double Rendering:** The skybox is rendered **twice per frame**:
> 1. Before `Unbind()` → appears in framebuffer texture (F2 preview)
> 2. After `Unbind()` → appears on screen
> 
> This ensures the skybox is visible in both the main window and the ImGui framebuffer preview.
> 
> **Performance Impact:** Negligible for a cube (72 triangles total). The skybox shader is extremely lightweight.
> 
> **Future Refactoring:** we'll move debug framebuffers behind conditional compilation flags, transitioning to production-ready patterns. For now, the educational clarity justifies the minimal overhead.

**In `OnImGuiRender()`, add skybox controls:**

```cpp
// =========================================================================
// Skybox Controls
// =========================================================================
uiManager.BeginSection("Skybox");
uiManager.Checkbox("Show Skybox", &m_ShowSkybox);

if (m_SkyboxCubemap)
{
    uiManager.Text("Cubemap: %dx%d per face", m_SkyboxCubemap->GetWidth(), m_SkyboxCubemap->GetHeight());
}
else
{
    uiManager.Text("Cubemap: Not loaded");
}

uiManager.EndSection();
```

> [!TIP]
> Add F4 toggle for skybox in `OnEvent()` (similar to F1-F3):
> ```cpp
> if (event.GetKeyCode() == VizEngine::KeyCode::F4 && !event.IsRepeat())
> {
>     m_ShowSkybox = !m_ShowSkybox;
>     VP_INFO("Skybox: {}", m_ShowSkybox ? "ON" : "OFF");
>     return true;
> }
> ```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|-------------|
| **Black/white skybox** | HDR not loaded | Use `stbi_loadf()` not `stbi_load()`, check `GL_RGB16F` format |
| **Skybox too dark** | HDR needs exposure | This is expected; tone mapping in Chapter 34 will fix this |
| **Skybox moves with camera** | Translation not removed | Verify `mat4(mat3(u_View))` in shader |
| **Skybox clipped** | Depth function wrong | Use `glDepthFunc(GL_LEQUAL)` during skybox render |
| **Seams between faces** | Filtering not set | Set `GL_CLAMP_TO_EDGE` for S, T, **and R** wrap modes |
| **Distorted conversion** | UV formula wrong | Check `atan(v.z, v.x)` and `asin(v.y)` order |
| **Slow conversion** | Converting every frame | Convert once in `OnCreate()`, cache result |
| **Compilation error** | Missing includes | Add `#include "VizEngine/OpenGL/CubemapUtils.h"` |
| **Cubemap shows solid color** | Face ordering wrong | Check `captureViews[]` matrices match face constants |

---

## Best Practices

### HDR Resolution Guidelines

| Source Resolution | Use Case | File Size |
|-------------------|----------|-----------|
| **2048×1024** | Good quality, fast loading | ~10-15 MB |
| **4096×2048** | High quality, production | ~40-60 MB |
| **8192×4096** | Overkill for real-time | ~150+ MB |

> **Recommendation**: Start with 2K (2048×1024). Only use 4K if targeting high-end systems.

### Cubemap Face Resolution

| Resolution | Quality | Memory (HDR) | Use Case |
|------------|---------|--------------|----------|
| **512×512** | Fast | ~9 MB | Mobile, low-end PCs |
| **1024×1024** | Balanced | ~36 MB | Desktop, most games |
| **2048×2048** | High | ~144 MB | High-end, close-up skyboxes |

> **Rule of thumb**: Use 512 for distant skyboxes, 1024 for normal use, 2048 only if skybox is prominent.

### Performance Tips

1. **Convert once**: Do equirect→cubemap conversion at load time, not runtime
2. **Cache converted cubemaps**: Save converted cubemaps to disk (Chapter 40: Asset Management)
3. **Use mipmaps**: Generate mipmaps for cubemaps with `glGenerateMimpap(GL_TEXTURE_CUBE_MAP)`
4. **Optimize resolution**: Balance quality vs memory/performance

### Memory Calculation

```
Cubemap memory = 6 × width × height × bytes_per_pixel

Examples:
- 512²  × RGB16F: 6 × 512 × 512 × 6 bytes     =  9.4 MB
- 1024² × RGB16F: 6 × 1024 × 1024 × 6 bytes   = 37.7 MB
- 2048² × RGB16F: 6 × 2048 × 2048 × 6 bytes   = 150.9 MB
```

### Asset Sources

**Free CC0 HDRIs**:
- [polyhaven.com/hdris](https://polyhaven.com/hdris) - Best quality, curated
- [hdrihaven.com](https://hdrihaven.com) - Large collection
- Both offer 1K, 2K, 4K, 8K, 16K resolutions

**License**: CC0 (public domain) - free for commercial use, no attribution required

---

## Environment Mapping Preview

While this chapter focuses on skyboxes, cubemaps have another major use: **environment reflections**.

### Reflection on Surfaces

In **Chapter 32 (PBR Implementation)**, we'll use the same skybox cubemap to create reflections on metallic surfaces:

```glsl
// Calculate reflection direction
vec3 I = normalize(v_WorldPos - u_ViewPos);  // View direction
vec3 R = reflect(I, normal);                 // Reflection vector

// Sample environment map
vec3 reflection = texture(u_EnvironmentMap, R).rgb;

// Apply to metallic materials
vec3 color = mix(baseColor, reflection, metallic);
```

This creates realistic environment reflections "for free" using the skybox cubemap.

### Image-Based Lighting (IBL)

In **Chapter 33 (Image-Based Lighting)**, we'll use the HDRI to compute:
- **Diffuse irradiance**: Ambient lighting from environment
- **Specular pre-filtering**: Blurry reflections based on roughness

This makes objects lit by the environment itself, creating photorealistic lighting.

> **For now**: Just know that the HDRI and cubemap you created will be reused in upcoming chapters. That's why we use HDR format—it preserves lighting information.

---

## Testing

1. **Build and run** the application
2. **Verify console logs**:
   - "HDR Texture loaded: ..."
   - "Converting equirectangular map to cubemap..."
   - "Cubemap conversion complete!"
   - "Skybox created"
3. **Observe skybox**: Should surround the scene with the environment
4. **Rotate camera**: Skybox rotates but never moves closer
5. **Move camera**: Skybox stays at infinite distance
6. **Toggle with F4**: Skybox appears/disappears
7. **Check ImGui**: Displays HDRI and cubemap resolutions
8. **Performance**: Conversion should happen once at startup (< 1 second)

---

## Milestone

**Chapter 31 Complete - Skybox Rendering**

You have:
- Created specialized skybox shader with view matrix transformation
- Implemented depth trick for far-plane rendering
- Built reusable `Skybox` class for environment rendering
- Integrated skybox in SandboxApp with toggle controls
- Rendered immersive environments with cubemap textures
- Understood how cubemaps enable reflections and IBL
- Applied camera-following technique (rotation only, no translation)

Your scenes now have **immersive skybox backgrounds** that establish atmosphere and prepare for PBR reflections. The cubemap you created in Chapter 30 is now actively rendering!

---

## What's Next

In **Chapter 32: PBR Theory**, we'll dive into physically-based rendering, understanding energy conservation, microfacet models, and the Cook-Torrance BRDF that forms the core of modern game engines.

> **Next:** [Chapter 32: PBR Theory](32_PBRTheory.md)

> **Previous:** [Chapter 30: Cubemaps and HDR](30_CubemapsAndHDR.md)

> **Index:** [Table of Contents](INDEX.md)

