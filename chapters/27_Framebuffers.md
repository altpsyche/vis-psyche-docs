\newpage

# Chapter 27: Framebuffers

Implement offscreen rendering with framebuffers, enabling render-to-texture workflows for advanced effects.

---

## Introduction

Until now, we've rendered directly to the **default framebuffer** (the screen). OpenGL always writes to *some* framebuffer—the default one is created automatically by the windowing system (GLFW).

**Limitation of default framebuffer:**
- Can only render to the window
- No way to capture render output as a texture
- Can't do post-processing effects
- Can't implement shadow mapping or screen-space effects

**Framebuffers solve this** by letting you create **custom framebuffers** and render to textures instead of the screen.

### Use Cases

| Technique | Why Framebuffers? |
|-----------|-------------------|
| **Shadow Mapping** | Render depth from light's perspective to a texture (Chapter 29) |
| **Post-Processing** | Render scene to texture, apply effects like bloom or blur (Part X) |
| **Portals/Mirrors** | Render scene from different camera to texture |
| **Deferred Rendering** | Multiple render targets for G-buffer (Part X) |
| **Cubemap Rendering** | 6 renders for environment maps (Part X) |

---

## Framebuffer Theory

### Framebuffer Structure

A framebuffer is a collection of **attachments**:

```
Framebuffer Object (FBO)
├── Color Attachment 0   (RGBA texture or renderbuffer)
├── Color Attachment 1   (optional, for MRT)
├── ...
├── Color Attachment N   (up to GL_MAX_COLOR_ATTACHMENTS)
├── Depth Attachment     (depth texture or renderbuffer)
└── Stencil Attachment   (stencil texture or renderbuffer)
```

Each attachment is either:
- **Texture**: Can sample in shaders (most common)
- **Renderbuffer**: Write-only, faster if you don't need to read (e.g., depth for shadows)

### Default vs Custom Framebuffer

| Aspect | Default Framebuffer | Custom Framebuffer |
|--------|---------------------|---------------------|
| **ID** | `0` | Generated with `glGenFramebuffers()` |
| **Binding** | Bound automatically | Must `glBindFramebuffer()` before use |
| **Attachments** | Created by GLFW | You attach textures/renderbuffers |
| **Output** | Window/screen | Textures (can be sampled later) |

### Render-to-Texture Workflow

```
1. Create Framebuffer
   ↓
2. Create Texture (same size as desired render resolution)
   ↓
3. Attach Texture to Framebuffer
   ↓
4. Bind Framebuffer
   ↓
5. Render Scene → Output goes to texture
   ↓
6. Unbind Framebuffer (bind default FBO 0)
   ↓
7. Use Texture (e.g., in ImGui, post-processing, etc.)
```

> [!TIP]
> **Automatic Viewport Management**: When you call `Framebuffer::Bind()`, the viewport is automatically set to match the framebuffer's dimensions. This ensures correct rendering without manual `glViewport()` calls.

---

## Architecture Overview

We'll create a `Framebuffer` class following RAII principles:

```cpp
class Framebuffer {
    // Create/Destroy
    Framebuffer(int width, int height);
    ~Framebuffer();  // Deletes FBO

    // Bind/Unbind
    void Bind();
    void Unbind();

    // Attachments
    void AttachColorTexture(std::shared_ptr<Texture> texture, int slot = 0);
    void AttachDepthTexture(std::shared_ptr<Texture> texture);

    // Validation
    bool IsComplete();
};
```

---

## Step 1: Create Framebuffer.h

**Create `VizEngine/src/VizEngine/OpenGL/Framebuffer.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Framebuffer.h

#pragma once

#include <memory>
#include "VizEngine/Core.h"

namespace VizEngine
{
	class Texture;

	/**
	 * RAII wrapper for OpenGL framebuffer objects.
	 * Allows rendering to textures instead of the default framebuffer (screen).
	 */
	class VizEngine_API Framebuffer
	{
	public:
		/**
		 * Create a framebuffer with the specified dimensions.
		 * Note: Framebuffer is incomplete until attachments are added.
		 * @param width Width in pixels
		 * @param height Height in pixels
		 */
		Framebuffer(int width, int height);

		/**
		 * Destructor. Deletes the OpenGL framebuffer object.
		 */
		~Framebuffer();

		// Non-copyable
		Framebuffer(const Framebuffer&) = delete;
		Framebuffer& operator=(const Framebuffer&) = delete;

		// Movable (allows storing in std::vector and returning from functions)
		Framebuffer(Framebuffer&& other) noexcept;
		Framebuffer& operator=(Framebuffer&& other) noexcept;

		/**
		 * Bind this framebuffer for rendering.
		 * Subsequent draw calls will render to this framebuffer's attachments.
		 */
		void Bind() const;

		/**
		 * Unbind this framebuffer and return to the default framebuffer.
		 */
		void Unbind() const;

		/**
		 * Attach a color texture to a specific color attachment slot.
		 * @param texture The texture to attach (must match framebuffer dimensions)
		 * @param slot Attachment slot (0 for GL_COLOR_ATTACHMENT0, etc.)
		 */
		void AttachColorTexture(std::shared_ptr<Texture> texture, int slot = 0);

		/**
		 * Attach a depth texture.
		 * @param texture The depth texture to attach (format must be GL_DEPTH_COMPONENT*)
		 */
		void AttachDepthTexture(std::shared_ptr<Texture> texture);

		/**
		 * Check if the framebuffer is complete and ready for rendering.
		 * Call this after adding all attachments.
		 * @return true if complete, false otherwise
		 */
		bool IsComplete() const;

		/**
		 * Get the width of the framebuffer.
		 */
		int GetWidth() const { return m_Width; }

		/**
		 * Get the height of the framebuffer.
		 */
		int GetHeight() const { return m_Height; }

		/**
		 * Get the OpenGL framebuffer ID.
		 */
		unsigned int GetID() const { return m_fbo; }

	private:
		unsigned int m_fbo = 0;
		int m_Width = 0;
		int m_Height = 0;

		// Store references to attached textures to keep them alive
		std::shared_ptr<Texture> m_ColorAttachments[8];  // Up to 8 MRT
		std::shared_ptr<Texture> m_DepthAttachment;
	};
}
```

> [!NOTE]
> We store `shared_ptr<Texture>` to keep textures alive while attached. If a texture is destroyed while still attached to a framebuffer, OpenGL behavior is undefined.

---

## Step 2: Create Framebuffer.cpp

**Create `VizEngine/src/VizEngine/OpenGL/Framebuffer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Framebuffer.cpp

#include "Framebuffer.h"
#include "Texture.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>

namespace VizEngine
{
	Framebuffer::Framebuffer(int width, int height)
		: m_Width(width), m_Height(height)
	{
		// Generate framebuffer object
		glGenFramebuffers(1, &m_fbo);
		VP_CORE_INFO("Framebuffer created: ID={}, Size={}x{}", m_fbo, m_Width, m_Height);
	}

	Framebuffer::~Framebuffer()
	{
		if (m_fbo != 0)
		{
			VP_CORE_INFO("Framebuffer destroyed: ID={}", m_fbo);
			glDeleteFramebuffers(1, &m_fbo);
			m_fbo = 0;
		}
	}

	Framebuffer::Framebuffer(Framebuffer&& other) noexcept
		: m_fbo(other.m_fbo)
		, m_Width(other.m_Width)
		, m_Height(other.m_Height)
	{
		// Move texture attachments
		for (int i = 0; i < 8; ++i)
		{
			m_ColorAttachments[i] = std::move(other.m_ColorAttachments[i]);
		}
		m_DepthAttachment = std::move(other.m_DepthAttachment);

		// Nullify moved-from object
		other.m_fbo = 0;
		other.m_Width = 0;
		other.m_Height = 0;
	}

	Framebuffer& Framebuffer::operator=(Framebuffer&& other) noexcept
	{
		if (this != &other)
		{
			// Delete current FBO
			if (m_fbo != 0)
			{
				glDeleteFramebuffers(1, &m_fbo);
			}

			// Move data
			m_fbo = other.m_fbo;
			m_Width = other.m_Width;
			m_Height = other.m_Height;

			// Move texture attachments
			for (int i = 0; i < 8; ++i)
			{
				m_ColorAttachments[i] = std::move(other.m_ColorAttachments[i]);
			}
			m_DepthAttachment = std::move(other.m_DepthAttachment);

			// Nullify moved-from object
			other.m_fbo = 0;
			other.m_Width = 0;
			other.m_Height = 0;
		}
		return *this;
	}

	void Framebuffer::Bind() const
	{
		glBindFramebuffer(GL_FRAMEBUFFER, m_fbo);
		// Set viewport to match framebuffer size
		glViewport(0, 0, m_Width, m_Height);
	}

	void Framebuffer::Unbind() const
	{
		// Bind default framebuffer (the screen)
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
	}

	void Framebuffer::AttachColorTexture(std::shared_ptr<Texture> texture, int slot)
	{
		if (slot < 0 || slot >= 8)
		{
			VP_CORE_ERROR("Framebuffer: Color attachment slot {} out of range [0-7]", slot);
			return;
		}

		if (!texture)
		{
			VP_CORE_ERROR("Framebuffer: Cannot attach null texture to color slot {}", slot);
			return;
		}

		// Verify texture dimensions match framebuffer
		if (texture->GetWidth() != m_Width || texture->GetHeight() != m_Height)
		{
			VP_CORE_WARN("Framebuffer: Texture dimensions ({}x{}) don't match framebuffer ({}x{})",
				texture->GetWidth(), texture->GetHeight(), m_Width, m_Height);
		}

		// Bind framebuffer and attach texture
		Bind();
		glFramebufferTexture2D(
			GL_FRAMEBUFFER,
			GL_COLOR_ATTACHMENT0 + slot,
			GL_TEXTURE_2D,
			texture->GetID(),
			0  // mipmap level
		);

		// Store reference to keep texture alive
		m_ColorAttachments[slot] = texture;

		VP_CORE_INFO("Framebuffer {}: Attached color texture {} to slot {}", m_fbo, texture->GetID(), slot);
	}

	void Framebuffer::AttachDepthTexture(std::shared_ptr<Texture> texture)
	{
		if (!texture)
		{
			VP_CORE_ERROR("Framebuffer: Cannot attach null depth texture");
			return;
		}

		// Verify texture dimensions match framebuffer
		if (texture->GetWidth() != m_Width || texture->GetHeight() != m_Height)
		{
			VP_CORE_WARN("Framebuffer: Depth texture dimensions ({}x{}) don't match framebuffer ({}x{})",
				texture->GetWidth(), texture->GetHeight(), m_Width, m_Height);
		}

		// Bind framebuffer and attach depth texture
		Bind();
		glFramebufferTexture2D(
			GL_FRAMEBUFFER,
			GL_DEPTH_ATTACHMENT,
			GL_TEXTURE_2D,
			texture->GetID(),
			0  // mipmap level
		);

		// Store reference
		m_DepthAttachment = texture;

		VP_CORE_INFO("Framebuffer {}: Attached depth texture {}", m_fbo, texture->GetID());
	}

	bool Framebuffer::IsComplete() const
	{
		// Temporarily bind framebuffer to check status
		// Save current binding to restore later (avoid side effects)
		GLint previousFBO = 0;
		glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previousFBO);

		glBindFramebuffer(GL_FRAMEBUFFER, m_fbo);
		GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER);

		// Restore previous binding
		glBindFramebuffer(GL_FRAMEBUFFER, previousFBO);

		if (status != GL_FRAMEBUFFER_COMPLETE)
		{
			const char* errorMsg = "Unknown error";
			switch (status)
			{
			case GL_FRAMEBUFFER_UNDEFINED:
				errorMsg = "Framebuffer undefined (target is default framebuffer)";
				break;
			case GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT:
				errorMsg = "Incomplete attachment (texture parameters invalid)";
				break;
			case GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT:
				errorMsg = "Missing attachment (no color or depth attached)";
				break;
			case GL_FRAMEBUFFER_INCOMPLETE_DRAW_BUFFER:
				errorMsg = "Incomplete draw buffer";
				break;
			case GL_FRAMEBUFFER_INCOMPLETE_READ_BUFFER:
				errorMsg = "Incomplete read buffer";
				break;
			case GL_FRAMEBUFFER_UNSUPPORTED:
				errorMsg = "Framebuffer format combination not supported";
				break;
			case GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE:
				errorMsg = "Incomplete multisample (attachment sample counts don't match)";
				break;
			case GL_FRAMEBUFFER_INCOMPLETE_LAYER_TARGETS:
				errorMsg = "Incomplete layer targets";
				break;
			}

			VP_CORE_ERROR("Framebuffer {}: Not complete - {}", m_fbo, errorMsg);
			return false;
		}

		return true;
	}
}
```

> [!IMPORTANT]
> Always call `IsComplete()` after attaching textures. An incomplete framebuffer will cause undefined behavior when you try to render to it.

---

## Step 3: Update CMakeLists.txt

Add the new `Framebuffer.cpp` to the build system.

**Modify `VizEngine/CMakeLists.txt`:**

In the `VIZENGINE_SOURCES` section (OpenGL subsection), add:

```cmake
    src/VizEngine/OpenGL/Framebuffer.cpp
```

In the `VIZENGINE_HEADERS` section (OpenGL headers subsection), add:

```cmake
    src/VizEngine/OpenGL/Framebuffer.h
```

---

## Step 4: Update Texture for Framebuffer Usage

Our `Texture` class needs a constructor that creates empty textures suitable for framebuffer attachments.

**Update `VizEngine/src/VizEngine/OpenGL/Texture.h`:**

Add a new constructor:

```cpp
/**
 * Create an empty texture for use as a framebuffer attachment.
 * @param width Texture width
 * @param height Texture height
 * @param internalFormat OpenGL internal format (e.g., GL_RGBA8, GL_DEPTH_COMPONENT24)
 * @param format OpenGL format (e.g., GL_RGBA, GL_DEPTH_COMPONENT)
 * @param dataType Data type (e.g., GL_UNSIGNED_BYTE, GL_FLOAT)
 */
Texture(int width, int height, unsigned int internalFormat, unsigned int format, unsigned int dataType);
```

**Update `VizEngine/src/VizEngine/OpenGL/Texture.cpp`:**

```cpp
Texture::Texture(int width, int height, unsigned int internalFormat, unsigned int format, unsigned int dataType)
	: m_texture(0), m_FilePath("framebuffer"), m_LocalBuffer(nullptr),
	  m_Width(width), m_Height(height), m_BPP(4)
{
	glGenTextures(1, &m_texture);
	glBindTexture(GL_TEXTURE_2D, m_texture);

	// Allocate texture storage (data = nullptr for empty texture)
	glTexImage2D(
		GL_TEXTURE_2D,
		0,                    // mipmap level
		internalFormat,       // e.g., GL_RGBA8 or GL_DEPTH_COMPONENT24
		m_Width,
		m_Height,
		0,                    // border (must be 0)
		format,               // e.g., GL_RGBA or GL_DEPTH_COMPONENT
		dataType,             // e.g., GL_UNSIGNED_BYTE or GL_FLOAT
		nullptr               // no pixel data (allocate empty)
	);

	// Set texture parameters suitable for framebuffer attachments
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

	glBindTexture(GL_TEXTURE_2D, 0);

	VP_CORE_INFO("Empty texture created: ID={}, Size={}x{}", m_texture, m_Width, m_Height);
}
```

> [!NOTE]
> Passing `nullptr` as the last argument to `glTexImage2D` allocates GPU memory but doesn't upload any data. This is perfect for framebuffer attachments, which will be filled by rendering.

---

## Step 4: Create Render-to-Texture Demo

Let's create a simple demo in Sandbox that renders the scene to a texture.

**Update `Sandbox/src/SandboxApp.cpp`:**

First, ensure you have the necessary includes at the top of the file:

```cpp
#include <VizEngine.h>
#include <VizEngine/Events/ApplicationEvent.h>
#include <VizEngine/Events/KeyEvent.h>
// Note: GL constants (GL_RGBA8, etc.) are available via VizEngine.h -> Texture.h -> glad.h
```

Add member variables:

```cpp
private:
	// ... existing members ...

	// Framebuffer for offscreen rendering
	std::shared_ptr<VizEngine::Framebuffer> m_Framebuffer;
	std::shared_ptr<VizEngine::Texture> m_FramebufferColor;
	std::shared_ptr<VizEngine::Texture> m_FramebufferDepth;
	bool m_ShowFramebufferTexture = true;
```

In `OnCreate()`, create the framebuffer:

```cpp
void OnCreate() override
{
	// ... existing setup code ...

	// =========================================================================
	// Create Framebuffer for offscreen rendering
	// =========================================================================
	int fbWidth = 800;
	int fbHeight = 800;

	// Create color attachment (RGBA8)
	m_FramebufferColor = std::make_shared<VizEngine::Texture>(
		fbWidth, fbHeight,
		GL_RGBA8,           // Internal format
		GL_RGBA,            // Format
		GL_UNSIGNED_BYTE    // Data type
	);

	// Create depth attachment (Depth24)
	m_FramebufferDepth = std::make_shared<VizEngine::Texture>(
		fbWidth, fbHeight,
		GL_DEPTH_COMPONENT24,   // Internal format
		GL_DEPTH_COMPONENT,     // Format
		GL_FLOAT                // Data type
	);

	// Create framebuffer and attach textures
	m_Framebuffer = std::make_shared<VizEngine::Framebuffer>(fbWidth, fbHeight);
	m_Framebuffer->AttachColorTexture(m_FramebufferColor, 0);
	m_Framebuffer->AttachDepthTexture(m_FramebufferDepth);

	// Verify framebuffer is complete
	if (!m_Framebuffer->IsComplete())
	{
		VP_ERROR("Framebuffer is not complete!");
	}
	else
	{
		VP_INFO("Framebuffer created successfully: {}x{}", fbWidth, fbHeight);
	}
}
```

In `OnRender()`, render to the framebuffer:

```cpp
void OnRender() override
{
	auto& engine = VizEngine::Engine::Get();
	auto& renderer = engine.GetRenderer();

	// Set light uniforms
	m_LitShader->Bind();
	m_LitShader->SetVec3("u_LightDirection", m_Light.GetDirection());
	m_LitShader->SetVec3("u_LightAmbient", m_Light.Ambient);
	m_LitShader->SetVec3("u_LightDiffuse", m_Light.Diffuse);
	m_LitShader->SetVec3("u_LightSpecular", m_Light.Specular);
	m_LitShader->SetVec3("u_ViewPos", m_Camera.GetPosition());

	// =========================================================================
	// Render to Framebuffer (offscreen)
	// =========================================================================
	// Use 1:1 aspect ratio for the 800x800 framebuffer
	float windowAspect = static_cast<float>(m_WindowWidth) / static_cast<float>(m_WindowHeight);
	m_Camera.SetAspectRatio(1.0f);  // Framebuffer is square (800x800)

	m_Framebuffer->Bind();
	renderer.Clear(m_ClearColor);
	m_Scene.Render(renderer, *m_LitShader, m_Camera);
	m_Framebuffer->Unbind();

	// =========================================================================
	// Render to Screen (default framebuffer)
	// =========================================================================
	// Restore camera to window aspect ratio
	m_Camera.SetAspectRatio(windowAspect);

	// Restore viewport to window size
	renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);

	// Render scene to screen (same as framebuffer for demonstration)
	renderer.Clear(m_ClearColor);
	m_Scene.Render(renderer, *m_LitShader, m_Camera);
}
```

> [!IMPORTANT]
> We switch the camera aspect ratio between passes. The framebuffer is fixed at 800×800 (1:1), while the screen matches the window dimensions. Without this, resizing the window would stretch the framebuffer preview.

---

## Step 5: Display Framebuffer Texture in ImGui

ImGui can display textures using `ImGui::Image()`. Let's add a panel to show the offscreen render.

**Update `Sandbox/src/SandboxApp.cpp` in `OnImGuiRender()`:**

```cpp
void OnImGuiRender() override
{
	auto& engine = VizEngine::Engine::Get();
	auto& uiManager = engine.GetUIManager();

	// =========================================================================
	// Framebuffer Texture Preview
	// =========================================================================
	if (m_ShowFramebufferTexture)
	{
		uiManager.StartFixedWindow("Offscreen Render", 360.0f, 420.0f);

		// ImGui::Image takes texture ID, size
		unsigned int texID = m_FramebufferColor->GetID();

		// Display at fixed size (framebuffer is 800x800, preview is 320x320)
		float displaySize = 320.0f;
		uiManager.Image(
			reinterpret_cast<void*>(static_cast<uintptr_t>(texID)),
			displaySize,
			displaySize  // 1:1 aspect for square framebuffer
		);

		uiManager.Separator();
		uiManager.Text("Framebuffer: %dx%d", m_Framebuffer->GetWidth(), m_Framebuffer->GetHeight());
		uiManager.Checkbox("Show Preview", &m_ShowFramebufferTexture);

		uiManager.EndWindow();
	}

	// ... existing panels ...
}
```

> [!TIP]
> You can toggle the framebuffer preview window with **F2** (similar to F1 for engine stats). This is useful if you accidentally close the window via the ImGui close button.

**Add F2 toggle in `OnEvent()`:**

```cpp
void OnEvent(VizEngine::Event& e) override
{
	VizEngine::EventDispatcher dispatcher(e);

	// ... existing event handlers ...

	// F1 toggles Engine Stats panel
	dispatcher.Dispatch<VizEngine::KeyPressedEvent>(
		[this](VizEngine::KeyPressedEvent& event) {
			if (event.GetKeyCode() == VizEngine::KeyCode::F1 && !event.IsRepeat())
			{
				m_ShowEngineStats = !m_ShowEngineStats;
				VP_INFO("Engine Stats: {}", m_ShowEngineStats ? "ON" : "OFF");
				return true;  // Consumed
			}
			// F2 toggles Framebuffer Preview
			if (event.GetKeyCode() == VizEngine::KeyCode::F2 && !event.IsRepeat())
			{
				m_ShowFramebufferTexture = !m_ShowFramebufferTexture;
				VP_INFO("Framebuffer Preview: {}", m_ShowFramebufferTexture ? "ON" : "OFF");
				return true;  // Consumed
			}
			return false;
		}
	);
}
```

---

Add the `Image()` and `StartFixedWindow()` methods to `UIManager`:

**Update `VizEngine/src/VizEngine/GUI/UIManager.h`:**

```cpp
void StartFixedWindow(const std::string& windowName, float width, float height);
void Image(void* textureID, float width, float height);
```

**Update `VizEngine/src/VizEngine/GUI/UIManager.cpp`:**

```cpp
void UIManager::StartFixedWindow(const std::string& windowName, float width, float height)
{
	ImGui::SetNextWindowSize(ImVec2(width, height), ImGuiCond_FirstUseEver);
	ImGui::Begin(windowName.c_str(), nullptr, ImGuiWindowFlags_NoResize);
}

void UIManager::Image(void* textureID, float width, float height)
{
	ImGui::Image(textureID, ImVec2(width, height), ImVec2(0, 1), ImVec2(1, 0));  // Flip UV
}
```

> [!IMPORTANT]
> - `StartFixedWindow()` creates a non-resizable ImGui window, perfect for fixed-size framebuffer previews.
> - OpenGL textures are bottom-left origin, but ImGui expects top-left. We flip the UV coordinates: `ImVec2(0, 1)` to `ImVec2(1, 0)`.

---

## Step 6: Add Viewport Method to Renderer

Client applications can't call OpenGL functions directly (they're inside the VizEngine DLL). Add a viewport wrapper:

**Update `VizEngine/src/VizEngine/OpenGL/Renderer.h`:**

```cpp
class VizEngine_API Renderer
{
public:
	void Clear(float clearColor[4]);
	void ClearDepth();
	void SetViewport(int x, int y, int width, int height);
	void Draw(const VertexArray& va, const IndexBuffer& ib, const Shader& shader) const;
};
```

**Update `VizEngine/src/VizEngine/OpenGL/Renderer.cpp`:**

```cpp
void Renderer::SetViewport(int x, int y, int width, int height)
{
	glViewport(x, y, width, height);
}
```

> [!NOTE]
> This follows the pattern of keeping all OpenGL calls inside VizEngine. Client applications use `renderer.SetViewport()` instead of calling `glViewport()` directly, avoiding DLL boundary issues with GLAD symbols.

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Framebuffer incomplete** | Missing attachment or wrong format | Call `IsComplete()` and check error message |
| **Black screen** | Forgot to bind framebuffer | Ensure `Bind()` before rendering |
| **Texture not updating** | Rendering to wrong framebuffer | Verify `Bind()` is called before draw calls |
| **Viewport wrong size** | Viewport not set after `Bind()` | Set viewport in `Bind()` (already done in our code) |
| **ImGui shows upside-down texture** | UV coordinates not flipped | Use `ImVec2(0,1)` to `ImVec2(1,0)` in `Image()` |
| **Dimensions mismatch warning** | Texture size ≠ framebuffer size | Create textures with same width/height as framebuffer |

---

## Framebuffer Formats

### Color Attachments

| Format | Channels | Bits per channel | Use Case |
|--------|----------|------------------|----------|
| `GL_RGBA8` | RGBA | 8 | Standard LDR rendering |
| `GL_RGBA16F` | RGBA | 16 (float) | HDR rendering (Part X) |
| `GL_RGBA32F` | RGBA | 32 (float) | High precision (compute shaders) |
| `GL_RGB8` | RGB | 8 | No alpha needed |
| `GL_R32F` | R | 32 (float) | Single-channel data (e.g., distance fields) |

### Depth Attachments

| Format | Bits | Use Case |
|--------|------|----------|
| `GL_DEPTH_COMPONENT16` | 16 | Low-precision shadow maps |
| `GL_DEPTH_COMPONENT24` | 24 | Standard depth buffer |
| `GL_DEPTH_COMPONENT32F` | 32 (float) | High-precision depth (far view distances) |
| `GL_DEPTH24_STENCIL8` | 24 + 8 | Combined depth and stencil |

---

## Best Practices

### 1. Match Dimensions

Always create textures with the same dimensions as the framebuffer:

```cpp
int resolution = 1024;
auto framebuffer = std::make_shared<Framebuffer>(resolution, resolution);
auto colorTex = std::make_shared<Texture>(resolution, resolution, GL_RGBA8, GL_RGBA, GL_UNSIGNED_BYTE);
framebuffer->AttachColorTexture(colorTex);
```

### 2. Check Completeness

Always validate the framebuffer after attaching textures:

```cpp
if (!framebuffer->IsComplete())
{
    VP_ERROR("Framebuffer setup failed!");
    // Fall back to default framebuffer or skip offscreen pass
}
```

### 3. Unbind After Use

Always unbind the framebuffer when done rendering to it:

```cpp
framebuffer->Bind();
// ... render scene ...
framebuffer->Unbind();  // Return to default framebuffer
```

### 4. Restore Viewport

After unbinding, restore the viewport to match the window size:

```cpp
framebuffer->Unbind();
// Use tracked window dimensions (set via WindowResizeEvent - see Chapter 26)
renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);
```

---

## Testing

1. **Build and run** the application
2. **Verify console** shows "Framebuffer created successfully"
3. **Check ImGui** "Offscreen Render" panel appears
4. **Observe texture** shows the same scene as the main window
5. **Resize window** → Main render adjusts, framebuffer texture stays fixed size
6. **Toggle checkbox** → Preview panel hides/shows

---

## Milestone

**Chapter 27 Complete**

You have:
- Created a RAII `Framebuffer` class
- Implemented offscreen rendering to textures
- Added framebuffer completeness validation
- Displayed rendered texture in ImGui
- Established foundation for shadow mapping and post-processing

The framebuffer abstraction is the **foundation for all advanced rendering techniques**. In the next chapter, we'll extend our Texture class with configuration methods needed for advanced techniques.

---

## What's Next

In **Chapter 28: Advanced Texture Configuration**, we'll add filtering, wrap mode, and border color controls to our Texture class—essential for shadow mapping and other advanced techniques.

> **Next:** [Chapter 28: Advanced Texture Configuration](28_TextureParameters.md)

> **Previous:** [Chapter 26: Advanced Lifecycle](26_AdvancedLifecycle.md)
