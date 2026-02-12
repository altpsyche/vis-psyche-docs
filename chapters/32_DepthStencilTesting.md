\newpage

# Chapter 32: Depth & Stencil Testing

Control which fragments survive the pipeline with depth testing, stencil masking, and face culling -- then use them to render object outlines.

---

## Introduction

Every frame, your GPU rasterizes thousands of fragments. But not all of them should end up on screen. Two objects might overlap. A back face might be invisible. You might want to highlight a selected object with a glowing outline. The mechanisms that decide which fragments survive are **depth testing**, **stencil testing**, and **face culling**.

Until now, we have relied on OpenGL's default depth test (`GL_LESS`) that was enabled back in Chapter 7. That works for basic scenes, but advanced rendering demands finer control:

- **Skyboxes** need `GL_LEQUAL` so the box at depth 1.0 passes the test (Chapter 31).
- **Transparent objects** must disable depth *writing* while keeping depth *testing* (Chapter 33).
- **Object outlines** require the stencil buffer to mask where a selected object was drawn.
- **Double-sided geometry** (foliage, cloth) needs face culling disabled selectively.

In this chapter, you will add depth function control, stencil buffer operations, and face culling to the `Renderer` class. Then you will combine them to implement **stencil-based object outlines** -- a technique used in almost every 3D editor and many games for selection highlighting.

### What You Will Learn

| Concept | Why It Matters |
|---------|----------------|
| **Depth functions** | Control which fragments pass based on their Z value |
| **Depth mask** | Selectively disable depth writes (transparency, decals) |
| **Stencil buffer** | Per-pixel integer mask for advanced fragment tests |
| **Stencil function & operations** | Define how the stencil test passes and what happens to the buffer |
| **Face culling** | Skip invisible back-facing triangles for performance |
| **Stencil outlines** | Practical technique combining all of the above |

---

## Theory

### The Depth Buffer

The depth buffer (also called the Z-buffer) stores a floating-point depth value for every pixel on screen. When a fragment is rasterized, OpenGL compares its depth against the value already in the buffer. The **depth function** determines whether the fragment passes or is discarded.

```
Fragment depth: 0.45
Depth buffer:   0.60
Depth func:     GL_LESS   →  0.45 < 0.60  →  PASS (fragment is closer)
```

#### Depth Test Functions

| Function | Passes When | Typical Use |
|----------|-------------|-------------|
| `GL_LESS` | fragment < buffer | **Default.** Standard 3D rendering |
| `GL_LEQUAL` | fragment <= buffer | Skyboxes (depth = 1.0 must pass) |
| `GL_GREATER` | fragment > buffer | Reverse-Z depth buffers |
| `GL_GEQUAL` | fragment >= buffer | Reverse-Z with equal pass |
| `GL_EQUAL` | fragment == buffer | Multi-pass rendering on exact same geometry |
| `GL_NOTEQUAL` | fragment != buffer | Rarely used |
| `GL_ALWAYS` | always | Disable depth test without disabling the buffer |
| `GL_NEVER` | never | Debug: discard all fragments |

#### Depth Mask

The depth mask controls whether passing fragments actually *write* their depth to the buffer:

```cpp
glDepthMask(GL_TRUE);   // Depth writes ON (default)
glDepthMask(GL_FALSE);  // Depth writes OFF — test still runs, but buffer is read-only
```

This is critical for transparent objects: you want them to be occluded by opaque geometry (depth test ON), but you do not want them to occlude each other (depth write OFF).

### The Stencil Buffer

The stencil buffer is an 8-bit integer buffer (per pixel) that sits alongside the color and depth buffers. It acts as a **programmable mask** -- you can write values into it, then test against those values to accept or reject fragments.

```
Stencil Buffer (8-bit per pixel):
┌───┬───┬───┬───┬───┐
│ 0 │ 0 │ 1 │ 1 │ 0 │  ← Row of pixels
└───┴───┴───┴───┴───┘
          ↑   ↑
      Stencil = 1 where the selected object was drawn
```

The stencil test is configured with three OpenGL calls:

#### `glStencilFunc(func, ref, mask)`

Defines the **test condition**. A fragment passes the stencil test when:

```
(ref & mask) func (stencil & mask)
```

| Parameter | Meaning |
|-----------|---------|
| `func` | Comparison function (`GL_ALWAYS`, `GL_EQUAL`, `GL_NOTEQUAL`, etc.) |
| `ref` | Reference value to compare against |
| `mask` | Bitmask applied to both ref and stencil value before comparison |

#### `glStencilOp(sfail, dpfail, dppass)`

Defines what **happens to the stencil buffer** based on test results:

| Parameter | When It Fires |
|-----------|---------------|
| `sfail` | Stencil test **fails** |
| `dpfail` | Stencil test passes but depth test **fails** |
| `dppass` | Both stencil and depth tests **pass** |

Each parameter takes one of these operations:

| Operation | Effect |
|-----------|--------|
| `GL_KEEP` | Keep the current stencil value (do nothing) |
| `GL_ZERO` | Set the stencil value to 0 |
| `GL_REPLACE` | Set the stencil value to `ref` (from `glStencilFunc`) |
| `GL_INCR` | Increment (clamp at max 255) |
| `GL_INCR_WRAP` | Increment (wrap to 0 at overflow) |
| `GL_DECR` | Decrement (clamp at 0) |
| `GL_DECR_WRAP` | Decrement (wrap to 255 at underflow) |
| `GL_INVERT` | Bitwise invert the current value |

#### `glStencilMask(mask)`

Controls which bits of the stencil buffer are **writable**:

```cpp
glStencilMask(0xFF);  // All bits writable (default)
glStencilMask(0x00);  // No bits writable — stencil buffer is read-only
```

> [!NOTE]
> The stencil mask set via `glStencilMask()` is separate from the `mask` parameter in `glStencilFunc()`. The function mask filters the *comparison*; the write mask filters *writes* to the buffer.

### Face Culling

Every triangle has a **winding order** -- the order in which its vertices appear on screen. By convention, counter-clockwise (CCW) winding means the triangle is front-facing. OpenGL can skip back-facing triangles entirely, saving roughly 50% of rasterization work for closed meshes.

```
Front face (CCW):        Back face (CW):
    v0                       v0
   / \                      / \
  /   \                    /   \
 v1───v2                  v2───v1
  → visible                → culled
```

| Function | Effect |
|----------|--------|
| `glEnable(GL_CULL_FACE)` | Enable face culling |
| `glDisable(GL_CULL_FACE)` | Disable face culling |
| `glCullFace(GL_BACK)` | Cull back faces (**default**) |
| `glCullFace(GL_FRONT)` | Cull front faces (shadow mapping trick) |
| `glCullFace(GL_FRONT_AND_BACK)` | Cull everything (debug) |

> [!TIP]
> Disable face culling for thin geometry like leaves, cloth, or decals that are visible from both sides. Enable it for solid meshes (cubes, characters, buildings) to improve performance.

---

## Architecture Overview

In this chapter, we build four pieces:

```
Renderer (state management)
├── SetDepthFunc()          — Choose comparison function
├── SetDepthMask()          — Enable/disable depth writes
├── EnableStencilTest()     — Turn on stencil testing
├── DisableStencilTest()    — Turn off stencil testing
├── SetStencilFunc()        — Configure stencil comparison
├── SetStencilOp()          — Configure stencil write operations
├── SetStencilMask()        — Configure stencil write mask
├── ClearStencil()          — Clear the stencil buffer
├── EnableFaceCulling()     — Turn on face culling
├── DisableFaceCulling()    — Turn off face culling
└── SetCullFace()           — Choose which face to cull

Framebuffer (depth-stencil attachment)
└── AttachDepthStencilTexture()  — GL_DEPTH24_STENCIL8 combined format

Outline Shader
└── outline.shader           — Minimal solid-color shader

SandboxApp (integration)
└── RenderStencilOutline()   — Two-pass stencil outline algorithm
```

These wrap the raw OpenGL calls behind the engine's `Renderer` interface, keeping all `gl*` calls inside VizEngine and away from client code.

---

## Step 1: Renderer State Methods

Add depth, stencil, and face culling control methods to the `Renderer` class. These are thin wrappers around OpenGL state calls, but they serve an important purpose: client applications (like `SandboxApp`) link against VizEngine as a DLL and cannot call `gl*` functions directly because GLAD symbols are not exported.

**Update `VizEngine/src/VizEngine/OpenGL/Renderer.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.h

#pragma once

#include "Shader.h"
#include "VertexArray.h"
#include "VertexBuffer.h"
#include "IndexBuffer.h"
#include "VizEngine/Core.h"
#include <vector>
#include <array>

namespace VizEngine
{
	class VizEngine_API Renderer
	{
	public:
		void Clear(float clearColor[4]);
		void ClearDepth();
		void SetViewport(int x, int y, int width, int height);
		void Draw(const VertexArray& va, const IndexBuffer& ib, const Shader& shader) const;

		// Viewport stack for safe state management
		void PushViewport();
		void PopViewport();
		void GetViewport(int& x, int& y, int& width, int& height) const;

		// Shadow mapping helpers
		void EnablePolygonOffset(float factor, float units);
		void DisablePolygonOffset();

		// Depth test control (for post-processing)
		void EnableDepthTest();
		void DisableDepthTest();

		// =====================================================================
		// Chapter 32: Depth & Stencil Testing
		// =====================================================================

		// Depth function control
		void SetDepthFunc(unsigned int func);  // GL_LESS, GL_LEQUAL, GL_ALWAYS, etc.
		void SetDepthMask(bool write);         // Enable/disable depth writing

		// Stencil testing
		void EnableStencilTest();
		void DisableStencilTest();
		void SetStencilFunc(unsigned int func, int ref, unsigned int mask);
		void SetStencilOp(unsigned int sfail, unsigned int dpfail, unsigned int dppass);
		void SetStencilMask(unsigned int mask);
		void ClearStencil();

		// Face culling
		void EnableFaceCulling();
		void DisableFaceCulling();
		void SetCullFace(unsigned int face);   // GL_BACK, GL_FRONT

		// ...
	private:
		std::vector<std::array<int, 4>> m_ViewportStack;
	};
}
```

The methods are grouped into three logical sections: **depth control**, **stencil testing**, and **face culling**. Each takes OpenGL enum values directly (`GL_LESS`, `GL_ALWAYS`, etc.) so that the caller has full control without VizEngine needing to define its own enum wrappers.

**Implement in `VizEngine/src/VizEngine/OpenGL/Renderer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.cpp

// =========================================================================
// Chapter 32: Depth & Stencil Testing
// =========================================================================

void Renderer::SetDepthFunc(unsigned int func)
{
	glDepthFunc(func);
}

void Renderer::SetDepthMask(bool write)
{
	glDepthMask(write ? GL_TRUE : GL_FALSE);
}

void Renderer::EnableStencilTest()
{
	glEnable(GL_STENCIL_TEST);
}

void Renderer::DisableStencilTest()
{
	glDisable(GL_STENCIL_TEST);
}

void Renderer::SetStencilFunc(unsigned int func, int ref, unsigned int mask)
{
	glStencilFunc(func, ref, mask);
}

void Renderer::SetStencilOp(unsigned int sfail, unsigned int dpfail, unsigned int dppass)
{
	glStencilOp(sfail, dpfail, dppass);
}

void Renderer::SetStencilMask(unsigned int mask)
{
	glStencilMask(mask);
}

void Renderer::ClearStencil()
{
	glClear(GL_STENCIL_BUFFER_BIT);
}

void Renderer::EnableFaceCulling()
{
	glEnable(GL_CULL_FACE);
}

void Renderer::DisableFaceCulling()
{
	glDisable(GL_CULL_FACE);
}

void Renderer::SetCullFace(unsigned int face)
{
	glCullFace(face);
}
```

> [!NOTE]
> Notice that `SetDepthMask()` takes a `bool` instead of a raw `GL_TRUE`/`GL_FALSE`. This is a deliberate ergonomic choice -- booleans are clearer at the call site than magic OpenGL constants. The implementation converts to the GL type internally.

Each function is a single OpenGL call. The value of wrapping them is not abstraction for its own sake -- it is **DLL boundary safety**. Without these wrappers, `SandboxApp` would need to link GLAD directly, which creates duplicate OpenGL function pointer state and leads to subtle crashes.

> [!IMPORTANT]
> The `Clear()` method already clears all three buffers (`GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT`). The `ClearStencil()` method clears *only* the stencil buffer, which is needed mid-frame when you want to reset the stencil mask without affecting color or depth.

---

## Step 2: Depth-Stencil Framebuffer Attachment

In Chapter 27, we attached separate depth textures using `AttachDepthTexture()`. For stencil outlines, we need a **combined depth-stencil texture** using the `GL_DEPTH24_STENCIL8` format. This packs 24 bits of depth and 8 bits of stencil into a single texture.

**Update `VizEngine/src/VizEngine/OpenGL/Framebuffer.h`:**

Add the new method declaration:

```cpp
// VizEngine/src/VizEngine/OpenGL/Framebuffer.h

/**
 * Attach a combined depth-stencil texture (Chapter 32).
 * @param texture The texture to attach (format must be GL_DEPTH24_STENCIL8 or GL_DEPTH32F_STENCIL8)
 */
void AttachDepthStencilTexture(std::shared_ptr<Texture> texture);
```

**Implement in `VizEngine/src/VizEngine/OpenGL/Framebuffer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Framebuffer.cpp

void Framebuffer::AttachDepthStencilTexture(std::shared_ptr<Texture> texture)
{
	if (!texture)
	{
		VP_CORE_ERROR("Framebuffer: Cannot attach null depth-stencil texture");
		return;
	}

	if (texture->GetWidth() != m_Width || texture->GetHeight() != m_Height)
	{
		VP_CORE_WARN("Framebuffer: Depth-stencil texture dimensions ({}x{}) don't match framebuffer ({}x{})",
			texture->GetWidth(), texture->GetHeight(), m_Width, m_Height);
	}

	Bind();
	glFramebufferTexture2D(
		GL_FRAMEBUFFER,
		GL_DEPTH_STENCIL_ATTACHMENT,
		GL_TEXTURE_2D,
		texture->GetID(),
		0
	);

	m_DepthAttachment = texture;

	VP_CORE_INFO("Framebuffer {}: Attached depth-stencil texture {}", m_fbo, texture->GetID());
}
```

The key difference from `AttachDepthTexture()` is the attachment point: `GL_DEPTH_STENCIL_ATTACHMENT` instead of `GL_DEPTH_ATTACHMENT`. This tells OpenGL to use the texture for **both** depth and stencil operations simultaneously.

### Creating the Depth-Stencil Texture

When you create the texture for this attachment, use the combined format:

```cpp
// In SandboxApp::OnCreate()

m_FramebufferDepth = std::make_shared<VizEngine::Texture>(
	fbWidth, fbHeight,
	GL_DEPTH24_STENCIL8,    // Internal format: 24-bit depth + 8-bit stencil
	GL_DEPTH_STENCIL,       // Format
	GL_UNSIGNED_INT_24_8    // Data type: packed 24+8
);

m_Framebuffer->AttachDepthStencilTexture(m_FramebufferDepth);
```

### Depth-Stencil Format Reference

| Internal Format | Depth Bits | Stencil Bits | Data Type | Notes |
|-----------------|------------|--------------|-----------|-------|
| `GL_DEPTH24_STENCIL8` | 24 | 8 | `GL_UNSIGNED_INT_24_8` | **Most common.** Good balance of precision and size |
| `GL_DEPTH32F_STENCIL8` | 32 (float) | 8 | `GL_FLOAT_32_UNSIGNED_INT_24_8_REV` | High-precision depth with stencil |

> [!TIP]
> `GL_DEPTH24_STENCIL8` is the standard choice. The 24-bit depth is identical to what most default framebuffers provide, and 8 bits of stencil gives you 256 possible stencil values per pixel -- more than enough for outlines, portals, mirrors, and multi-pass masking.

---

## Step 3: Outline Shader

The stencil outline technique needs a shader that outputs a **solid color** with no lighting, no textures -- just a flat color uniform. This is what gets drawn in the "scaled-up silhouette" pass.

**Create `VizEngine/src/resources/shaders/outline.shader`:**

```glsl
// VizEngine/src/resources/shaders/outline.shader

#shader vertex
#version 460 core

// Chapter 32: Simple solid-color shader for stencil outlines
layout(location = 0) in vec4 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec4 aColor;
layout(location = 3) in vec2 aTexCoords;
layout(location = 4) in vec3 aTangent;
layout(location = 5) in vec3 aBitangent;

uniform mat4 u_Model;
uniform mat4 u_View;
uniform mat4 u_Projection;

void main()
{
    gl_Position = u_Projection * u_View * u_Model * aPos;
}


#shader fragment
#version 460 core

out vec4 FragColor;

uniform vec4 u_OutlineColor;

void main()
{
    FragColor = u_OutlineColor;
}
```

A few things to note about this shader:

- The **vertex shader** still declares all vertex attributes (`aNormal`, `aColor`, `aTexCoords`, `aTangent`, `aBitangent`) even though it only uses `aPos`. This is because the VAO layout is shared with the main PBR shader, and mismatched attribute locations would cause OpenGL errors or garbage data.
- The **fragment shader** outputs a single `u_OutlineColor` uniform. This color (typically a bright orange or yellow) is configurable from the ImGui panel.
- There is no lighting calculation -- the outline should be a flat, unshaded color that stands out clearly against the rendered scene.

> [!NOTE]
> The outline shader uses the same `#shader vertex` / `#shader fragment` preprocessor format as all other VizEngine shaders. The `Shader` class parser splits on these markers when loading the file (see Chapter 8).

---

## Step 4: SandboxApp Integration -- Stencil Outline Algorithm

Now we combine everything into a practical rendering technique. The **stencil outline algorithm** highlights a selected object by drawing a colored border around it. It works in two passes:

### The Algorithm

```
Pass 1: Mark the Object in the Stencil Buffer
──────────────────────────────────────────────
1. Clear the stencil buffer
2. Enable stencil test
3. Set stencil func: GL_ALWAYS, ref=1, mask=0xFF
   → Every fragment that passes depth will write 1 to stencil
4. Set stencil op: GL_KEEP, GL_KEEP, GL_REPLACE
   → On depth+stencil pass, replace stencil with ref (1)
5. Set depth func: GL_LEQUAL
   → Allow re-rendering at the same depth as the original draw
6. Render the selected object normally
7. Restore depth func to GL_LESS

Pass 2: Draw the Outline Where Stencil != 1
──────────────────────────────────────────────
1. Set stencil func: GL_NOTEQUAL, ref=1, mask=0xFF
   → Only draw where stencil is NOT 1 (outside the object)
2. Set stencil mask: 0x00
   → Don't modify stencil buffer during this pass
3. Disable depth writes (SetDepthMask(false))
   → Outline always renders on top, doesn't occlude anything
4. Render a scaled-up version of the object with the outline shader
5. Restore all state
```

The result: a colored border appears around the object's silhouette. The border width is controlled by the scale factor -- a scale of `1.05` produces a thin outline, while `1.3` produces a thick one.

```
┌─────────────────────────────┐
│                             │
│     ┌───────────────┐       │
│     │ ░░░░░░░░░░░░░ │       │  ░ = Original object (stencil = 1)
│     │ ░░░░░░░░░░░░░ │       │  █ = Scaled-up outline (stencil != 1)
│     │ ░░░░░░░░░░░░░ │       │
│     └───────────────┘       │
│     █████████████████       │  ← Outline visible only OUTSIDE original
│                             │
└─────────────────────────────┘
```

### Implementation

Add these member variables to `SandboxApp`:

```cpp
// SandboxApp member variables

// Chapter 32: Stencil Outlines
std::shared_ptr<VizEngine::Shader> m_OutlineShader;
bool m_EnableOutlines = true;
glm::vec4 m_OutlineColor = glm::vec4(1.0f, 0.6f, 0.0f, 1.0f);  // Orange
float m_OutlineScale = 1.05f;
int m_SelectedObject = 0;
```

Load the outline shader in `OnCreate()`:

```cpp
// In SandboxApp::OnCreate()

m_OutlineShader = std::make_shared<VizEngine::Shader>("resources/shaders/outline.shader");
```

Create the framebuffer with a combined depth-stencil attachment:

```cpp
// In SandboxApp::OnCreate()

int fbWidth = 800;
int fbHeight = 800;

// Create color attachment (RGBA8)
m_FramebufferColor = std::make_shared<VizEngine::Texture>(
	fbWidth, fbHeight,
	GL_RGBA8,           // Internal format
	GL_RGBA,            // Format
	GL_UNSIGNED_BYTE    // Data type
);

// Create depth-stencil attachment (Chapter 32: depth + stencil for outlines)
m_FramebufferDepth = std::make_shared<VizEngine::Texture>(
	fbWidth, fbHeight,
	GL_DEPTH24_STENCIL8,    // Internal format (Chapter 32)
	GL_DEPTH_STENCIL,       // Format
	GL_UNSIGNED_INT_24_8    // Data type
);

// Create framebuffer and attach textures
m_Framebuffer = std::make_shared<VizEngine::Framebuffer>(fbWidth, fbHeight);
m_Framebuffer->AttachColorTexture(m_FramebufferColor, 0);
m_Framebuffer->AttachDepthStencilTexture(m_FramebufferDepth);

// Verify framebuffer is complete
if (!m_Framebuffer->IsComplete())
{
	VP_ERROR("Framebuffer is not complete! Disabling offscreen render.");
}
```

> [!IMPORTANT]
> Note that we use `AttachDepthStencilTexture()` instead of `AttachDepthTexture()`. If you attach a `GL_DEPTH24_STENCIL8` texture to `GL_DEPTH_ATTACHMENT` (the old method), OpenGL will ignore the stencil bits and stencil operations will silently fail.

> [!NOTE]
> **HDR Pipeline Integration**: If you have the HDR pipeline from Chapter 39, the HDR framebuffer (`m_HDRFramebuffer`) also needs `AttachDepthStencilTexture()` with `GL_DEPTH24_STENCIL8`. Since the stencil outline is rendered within the HDR framebuffer's render pass, both framebuffers must have stencil support for outlines to appear in the final output.

Implement the `RenderStencilOutline()` helper method:

```cpp
// SandboxApp::RenderStencilOutline() — Chapter 32

void RenderStencilOutline(VizEngine::Renderer& renderer)
{
	if (!m_EnableOutlines || !m_OutlineShader) return;
	if (m_SelectedObject < 0 || m_SelectedObject >= static_cast<int>(m_Scene.Size())) return;

	auto& obj = m_Scene[static_cast<size_t>(m_SelectedObject)];
	if (!obj.Active || !obj.MeshPtr) return;

	// Pass 1: Fill stencil buffer with 1s where the selected object is
	renderer.ClearStencil();
	renderer.EnableStencilTest();
	renderer.SetStencilFunc(GL_ALWAYS, 1, 0xFF);
	renderer.SetStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE);
	renderer.SetStencilMask(0xFF);
	renderer.SetDepthFunc(GL_LEQUAL);  // Allow re-rendering at same depth

	// Re-render selected object (writes 1s to stencil where visible)
	RenderSingleObject(obj, renderer);

	renderer.SetDepthFunc(GL_LESS);  // Restore

	// Pass 2: Render scaled-up outline where stencil != 1
	renderer.SetStencilFunc(GL_NOTEQUAL, 1, 0xFF);
	renderer.SetStencilMask(0x00);     // Don't write to stencil
	renderer.SetDepthMask(false);      // Don't write to depth

	m_OutlineShader->Bind();
	m_OutlineShader->SetMatrix4fv("u_View", m_Camera.GetViewMatrix());
	m_OutlineShader->SetMatrix4fv("u_Projection", m_Camera.GetProjectionMatrix());
	m_OutlineShader->SetVec4("u_OutlineColor", m_OutlineColor);

	glm::mat4 scaledModel = glm::scale(
		obj.ObjectTransform.GetModelMatrix(),
		glm::vec3(m_OutlineScale)
	);
	m_OutlineShader->SetMatrix4fv("u_Model", scaledModel);

	obj.MeshPtr->Bind();
	renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), *m_OutlineShader);

	// Restore state
	renderer.SetDepthMask(true);
	renderer.SetStencilMask(0xFF);
	renderer.DisableStencilTest();
}
```

Let's walk through the critical lines:

1. **`ClearStencil()`** -- Resets the stencil buffer to all zeros. We do this at the start of the outline pass, not at frame start, because `Clear()` already handles it there. The explicit clear here ensures a clean slate even if other stencil operations ran earlier in the frame.

2. **`SetStencilFunc(GL_ALWAYS, 1, 0xFF)`** -- Every fragment that passes the depth test will pass the stencil test. The reference value `1` is what gets written to the stencil buffer (via `GL_REPLACE` in the next call).

3. **`SetStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)`** -- Only when *both* stencil and depth tests pass (`dppass`) do we replace the stencil value with `ref` (1). If a fragment is behind something else (depth fail), we keep the stencil value unchanged.

4. **`SetDepthFunc(GL_LEQUAL)`** -- The selected object was already drawn during the main scene pass. Its fragments are in the depth buffer at their exact depth values. Using `GL_LESS` would fail (same depth is not less than itself), so we switch to `GL_LEQUAL` to allow the re-render to pass.

5. **`SetStencilFunc(GL_NOTEQUAL, 1, 0xFF)`** -- For Pass 2, only draw where the stencil is *not* 1. This means the outline only appears **outside** the original object silhouette.

6. **`SetDepthMask(false)`** -- The outline should not write to the depth buffer. This ensures it does not occlude other objects or interfere with subsequent rendering passes.

7. **`glm::scale(..., glm::vec3(m_OutlineScale))`** -- The outline geometry is a slightly larger version of the original mesh. The scale factor controls the outline thickness. Values between `1.01` and `1.3` work well for most objects.

### Calling the Outline Pass

Call `RenderStencilOutline()` from `OnRender()` after the main scene and skybox have been drawn:

```cpp
// In SandboxApp::OnRender()

// Render scene objects...
RenderSceneObjects();

// Render skybox before outlines so outline is visible on top
if (m_ShowSkybox && m_Skybox)
{
	m_Skybox->Render(m_Camera);
}

// Chapter 32: Stencil Outline Pass (after skybox so outline is visible)
RenderStencilOutline(renderer);
```

> [!TIP]
> Render outlines **after** the skybox. If you render them before, the skybox pass might overwrite the outline fragments in the color buffer (the skybox renders at depth 1.0 and covers the full screen).

### ImGui Controls

Add an ImGui panel to control outline parameters:

```cpp
// In SandboxApp::OnImGuiRender()

// Chapter 32: Stencil Outlines
if (uiManager.CollapsingHeader("Stencil Outlines (Ch 32)"))
{
	uiManager.Checkbox("Enable Outlines", &m_EnableOutlines);
	uiManager.ColorEdit4("Outline Color", &m_OutlineColor.x);
	uiManager.SliderFloat("Outline Scale", &m_OutlineScale, 1.01f, 1.3f);
	uiManager.Text("Outline drawn on: %s",
		(m_SelectedObject >= 0 && m_SelectedObject < static_cast<int>(m_Scene.Size()))
			? m_Scene[static_cast<size_t>(m_SelectedObject)].Name.c_str()
			: "None");
	uiManager.Text("Toggle: F5");
}
```

Add a keyboard toggle:

```cpp
// In SandboxApp::OnEvent()

// F5 toggles Stencil Outlines (Chapter 32)
if (event.GetKeyCode() == VizEngine::KeyCode::F5 && !event.IsRepeat())
{
	m_EnableOutlines = !m_EnableOutlines;
	VP_INFO("Stencil Outlines: {}", m_EnableOutlines ? "ON" : "OFF");
	return true;  // Consumed
}
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **No outline visible** | Stencil buffer not allocated | Use `GL_DEPTH24_STENCIL8` format and `AttachDepthStencilTexture()` |
| **Outline fills entire object** | Stencil func set to `GL_ALWAYS` in Pass 2 | Ensure Pass 2 uses `GL_NOTEQUAL` |
| **Outline flickers or Z-fights** | Depth func still `GL_LESS` during re-render | Switch to `GL_LEQUAL` for Pass 1, restore to `GL_LESS` after |
| **Outline occluded by other objects** | Depth writes enabled during outline pass | Set `SetDepthMask(false)` before drawing the outline |
| **Outline too thick or thin** | Scale factor too high or low | Adjust `m_OutlineScale` (1.01 = thin, 1.3 = thick) |
| **Outline appears inside object** | Scale origin not at object center | Ensure the model's pivot point is at its center |
| **Stencil test does nothing** | Stencil test not enabled | Call `EnableStencilTest()` before stencil operations |
| **Black screen after stencil pass** | Forgot to restore state | Always restore `SetDepthMask(true)`, `SetStencilMask(0xFF)`, and `DisableStencilTest()` |
| **Stencil works on screen but not in FBO** | FBO uses depth-only attachment | Use `AttachDepthStencilTexture()` with `GL_DEPTH24_STENCIL8` |
| **Face culling breaks thin geometry** | Back faces culled on two-sided mesh | Call `DisableFaceCulling()` for foliage, cloth, etc. |

---

## Best Practices

### 1. Always Restore State

Stencil and depth state is global. If you change it and forget to restore it, every subsequent draw call in the frame will be affected:

```cpp
// BAD — state leak
renderer.EnableStencilTest();
renderer.SetDepthMask(false);
// ... draw outline ...
// Forgot to restore! Everything after this has no depth writes.

// GOOD — always restore
renderer.EnableStencilTest();
renderer.SetDepthMask(false);
// ... draw outline ...
renderer.SetDepthMask(true);
renderer.SetStencilMask(0xFF);
renderer.DisableStencilTest();
```

### 2. Clear Stencil Per-Effect, Not Per-Frame

The `Clear()` method already clears the stencil buffer at frame start. If you run multiple stencil effects per frame (outlines + portal masking, for example), clear the stencil buffer before each effect with `ClearStencil()` rather than relying on the frame-level clear:

```cpp
// Effect 1: Object outline
renderer.ClearStencil();
// ... outline pass ...

// Effect 2: Portal mask
renderer.ClearStencil();
// ... portal pass ...
```

### 3. Use GL_LEQUAL Judiciously

Switching to `GL_LEQUAL` allows fragments at the same depth to pass. This is necessary for re-rendering the selected object into the stencil buffer, but it can cause Z-fighting if left enabled. Always restore to `GL_LESS` immediately after the re-render:

```cpp
renderer.SetDepthFunc(GL_LEQUAL);
RenderSingleObject(obj, renderer);  // Re-render for stencil
renderer.SetDepthFunc(GL_LESS);     // Restore immediately
```

### 4. Disable Depth Writes for Overlays

Outlines, wireframes, gizmos, and other overlay effects should not write to the depth buffer. They are visual aids, not scene geometry:

```cpp
renderer.SetDepthMask(false);
// ... draw outline, gizmo, debug wireframe ...
renderer.SetDepthMask(true);
```

### 5. Order Your Passes Carefully

The recommended render order for a frame with outlines:

```
1. Clear buffers (color + depth + stencil)
2. Render opaque scene objects        — depth test ON, depth write ON
3. Render skybox                      — depth func GL_LEQUAL, depth write OFF
4. Render stencil outlines            — stencil test ON, depth write OFF
5. Render transparent objects         — depth test ON, depth write OFF, blending ON
6. Post-processing                    — fullscreen quad, depth test OFF
```

---

## Milestone

**Chapter 32 Complete.**

You have:

- Added **depth function control** (`SetDepthFunc`, `SetDepthMask`) to the Renderer
- Implemented **stencil buffer operations** (`EnableStencilTest`, `SetStencilFunc`, `SetStencilOp`, `SetStencilMask`, `ClearStencil`)
- Added **face culling control** (`EnableFaceCulling`, `DisableFaceCulling`, `SetCullFace`)
- Created a **combined depth-stencil framebuffer attachment** (`AttachDepthStencilTexture` with `GL_DEPTH24_STENCIL8`)
- Built a **solid-color outline shader** for the stencil highlight pass
- Implemented a **two-pass stencil outline algorithm** that highlights selected objects with a configurable colored border
- Added **ImGui controls** for outline color, thickness, and toggle (F5)

These depth and stencil operations form the foundation for many advanced techniques: transparent object sorting (Chapter 33), portal rendering, mirror reflections, shadow volumes, and decal systems.

---

## What's Next

In **Chapter 33: Blending & Transparency**, you will add blend function control to the Renderer and implement proper transparent object rendering with depth-sorted draw order.

> **Previous:** [Chapter 31: Skybox Rendering](31_SkyboxRendering.md) | **Next:** [Chapter 33: Blending & Transparency](33_BlendingTransparency.md)
