\newpage

# Chapter 30: Cubemaps and HDR Environment Maps

Convert equirectangular HDR images to cubemap textures using modern shader-based workflow.

---

## Introduction

Every 3D scene needs a background. Until now, we've rendered against a solid color (the clear color). This works for simple demos, but real 3D environments need **context**—a sense of place.

**Skyboxes** solve this by wrapping the scene in an environment that gives the illusion of infinite space. Look in any direction, and you see the environment extending to the horizon.

### Why Skyboxes Matter

| Benefit | Impact |
|---------|--------|
| **Immersion** | Outdoor scenes feel vast; indoor scenes feel enclosed |
| **Visual context** | Establishes time of day, weather, location |
| **Lighting reference** | Provides ambient environment (preview of IBL in Chapter 33) |
| **Fills gaps** | No empty space where geometry ends |
| **Professionalism** | Every modern game uses skyboxes |

### Real-World Examples

- **Outdoor scenes**: Sky, clouds, mountains, sun
- **Indoor scenes**: Ceiling, walls, distant architecture  
- **Space games**: Stars, nebulae, planets
- **Abstract environments**: Procedural patterns, artistic designs

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **HDR Loading** | Load `.hdr` equirectangular environment maps with `stbi_loadf()` |
| **Cubemap Conversion** | Convert equirectangular maps to cubemaps using shaders and framebuffers |
| **Skybox Rendering** | Render a cubemap-textured cube that follows the camera |
| **ImGui Controls** | Toggle skybox visibility and view conversion info |
| **Asset Integration** | Load free HDRI assets from polyhaven.com |

**End result**: A scene surrounded by a photorealistic environment that rotates with the camera but never gets closer.

---

## Cubemap Theory

### What is a Cubemap?

A **cubemap** is a special OpenGL texture type (`GL_TEXTURE_CUBE_MAP`) consisting of **6 square 2D textures** arranged as the faces of a cube:

```
        +---+
        | Y+|  Top
    +---+---+---+---+
    | X-| Z+| X+| Z-|  Left, Front, Right, Back
    +---+---+---+---+
        | Y-|  Bottom
        +---+
```

**OpenGL Face Constants:**
- `GL_TEXTURE_CUBE_MAP_POSITIVE_X` (+X, right)
- `GL_TEXTURE_CUBE_MAP_NEGATIVE_X` (-X, left)
- `GL_TEXTURE_CUBE_MAP_POSITIVE_Y` (+Y, top)
- `GL_TEXTURE_CUBE_MAP_NEGATIVE_Y` (-Y, bottom)
- `GL_TEXTURE_CUBE_MAP_POSITIVE_Z` (+Z, front)
- `GL_TEXTURE_CUBE_MAP_NEGATIVE_Z` (-Z, back)

### Cubemap Sampling

Unlike regular 2D textures (sampled with UV coordinates), cubemaps are sampled with a **3D direction vector**:

```glsl
// 2D texture sampling (regular textures)
vec4 color = texture(u_Texture2D, vec2(u, v));

// Cubemap sampling (direction vector)
vec4 color = texture(u_Cubemap, vec3(x, y, z));
```

**How it works:**
1. Start at the cube's center
2. Cast a ray in the direction `(x, y, z)`
3. Sample the texel where the ray hits a cube face

This makes cubemaps perfect for **environment mapping**—use the view direction to sample the environment.

---

## Equirectangular to Cubemap Conversion

### Why Not Load 6 Images?

**Traditional approach** (not used in this chapter):
- Load 6 separate image files (`right.png`, `left.png`, etc.)
- Manually match them to cube faces
- Hard to find matching sets
- Cumbersome asset management

**Modern approach** (used in this chapter):
- Load 1 equirectangular HDR image (`.hdr` file)
- Convert to cubemap using a shader
- Industry standard (Unreal, Unity, Blender all use this)
- Abundant free HDR assets (polyhaven.com, hdri-haven.com)
- Preserves HDR data for PBR lighting (Chapters 31-36)

### Equirectangular Projection

An **equirectangular map** is a 2D image that represents a 360° sphere, like a world map:

```
Equirectangular (2D image)        Sphere (3D)           Cubemap (6 faces)
┌─────────────────────┐              ╭─╮                  +---+
│                     │             │   │                 | Y+|
│    Environment      │    →       │  ●  │        →   +---+---+---+---+
│     (360° × 180°)   │             │   │           | X-| Z+| X+| Z-|
└─────────────────────┘              ╰─╯            +---+---+---+---+
   2:1 aspect ratio               Lat/Long              | Y-|
                                                         +---+
```

**Conversion process:**
1. For each cubemap face (6 iterations):
   - Render a fullscreen quad facing that direction
   - In fragment shader: compute direction vector for each pixel
   - Convert direction to equirectangular UV coordinates
   - Sample the equirectangular map
   - Write to cubemap face texture

This is a **one-time** operation done at load time, not every frame.

---

## Skybox Rendering Technique

### The Challenge

We want a cube texture that:
- **Surrounds** the camera (infinite distance illusion)
- **Rotates** with camera rotation (not translation)
- **Never gets closer** when you move forward

### The Solution

**Key technique**: Remove translation from the view matrix and render cube at maximum depth.

```cpp
// Normal view matrix
glm::mat4 view = camera.GetViewMatrix();  // Includes translation + rotation

// Skybox view matrix (rotation only)
glm::mat4 viewNoTranslation = glm::mat4(glm::mat3(view));  // Strip translation
```

**What this does:**
- `glm::mat3(view)` extracts the upper-left 3×3 (rotation only)
- `glm::mat4(...)` converts back to 4×4 with translation = (0, 0, 0)
- Result: Skybox rotates with camera but never moves

**Depth trick** (in vertex shader):
```glsl
gl_Position = projection * viewNoTranslation * vec4(position, 1.0);
gl_Position.z = gl_Position.w;  // Set depth to maximum (far plane)
```

Setting `z = w` means after perspective divide (`z/w`), depth = 1.0 (farthest possible). The skybox renders "behind" all geometry.

### Render Order

**Option 1: Render last** (used in this chapter)
```cpp
// Disable depth writes so skybox doesn't block anything
glDepthMask(GL_FALSE);
RenderSkybox();
glDepthMask(GL_TRUE);
```

**Option 2: Render first**
```cpp
// Clear depth buffer after skybox
RenderSkybox();
glClear(GL_DEPTH_BUFFER_BIT);
RenderScene();
```

Option 1 is more common and efficient.

---

## Step 1: Add HDR Texture Loading Support

Standard image loading (`stbi_load()`) clamps colors to [0, 1]. **HDR images** store floating-point values beyond 1.0 (bright light sources, sky).

### Update Texture.h

Add support for HDR loading.

**Modify `VizEngine/src/VizEngine/OpenGL/Texture.h`:**

Add new constructor after the existing one:

```cpp
/**
 * Load HDR equirectangular image (for environment maps).
 * Uses stbi_loadf for floating-point data.
 * @param filepath Path to .hdr file
 * @param isHDR Set to true to load as HDR (GL_RGB16F)
 */
Texture(const std::string& filepath, bool isHDR);
```

Add helper methods:

```cpp
bool IsCubemap() const { return m_IsCubemap; }
bool IsHDR() const { return m_IsHDR; }
```

Add member variables (in private section):

```cpp
bool m_IsCubemap = false;
bool m_IsHDR = false;
```

### Update Texture.cpp

Implement HDR loading.

**Add to `VizEngine/src/VizEngine/OpenGL/Texture.cpp`:**

After the existing constructor, add:

```cpp
Texture::Texture(const std::string& filepath, bool isHDR)
	: m_texture(0), m_FilePath(filepath), m_LocalBuffer(nullptr),
	  m_Width(0), m_Height(0), m_BPP(0), m_IsHDR(isHDR)
{
	// stb_image loads with bottom-left origin, OpenGL expects bottom-left
	stbi_set_flip_vertically_on_load(1);

	glGenTextures(1, &m_texture);
	glBindTexture(GL_TEXTURE_2D, m_texture);

	if (m_IsHDR)
	{
		// Load HDR image (floating-point data)
		float* hdrData = stbi_loadf(filepath.c_str(), &m_Width, &m_Height, &m_BPP, 0);

		if (hdrData)
		{
			// Upload as 16-bit float texture (GL_RGB16F)
			glTexImage2D(
				GL_TEXTURE_2D,
				0,                  // Mipmap level
				GL_RGB16F,          // Internal format (HDR)
				m_Width,
				m_Height,
				0,                  // Border
				GL_RGB,             // Format
				GL_FLOAT,           // Data type
				hdrData
			);

			// Set texture parameters
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

			VP_CORE_INFO("HDR Texture loaded: {} ({}x{}, {} channels)", filepath, m_Width, m_Height, m_BPP);

			stbi_image_free(hdrData);
		}
		else
		{
			VP_CORE_ERROR("Failed to load HDR texture: {}", filepath);
		}
	}
	else
	{
		// Regular LDR loading (delegate to existing logic)
		// This path allows Texture(filepath, false) to work like Texture(filepath)
		unsigned char* data = stbi_load(filepath.c_str(), &m_Width, &m_Height, &m_BPP, 4);

		if (data)
		{
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, m_Width, m_Height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

			VP_CORE_INFO("LDR Texture loaded: {} ({}x{}, {} channels)", filepath, m_Width, m_Height, m_BPP);

			stbi_image_free(data);
		}
		else
		{
			VP_CORE_ERROR("Failed to load LDR texture: {}", filepath);
		}
	}

	glBindTexture(GL_TEXTURE_2D, 0);
}
```

> [!NOTE]
> **HDR Format Choice**: `GL_RGB16F` is 16-bit floating-point per channel. This preserves HDR range while using less memory than `GL_RGB32F`. For skyboxes, 16-bit is sufficient.

---

## Step 2: Create Empty Cubemap Texture Constructor

We need to create empty cubemap textures for the conversion target.

**Add to `VizEngine/src/VizEngine/OpenGL/Texture.h`:**

```cpp
/**
 * Create an empty cubemap texture.
 * @param resolution Resolution per face (e.g., 512, 1024)
 * @param isHDR Use HDR format (GL_RGB16F) or LDR (GL_RGB8)
 */
Texture(int resolution, bool isHDR);
```

**Add to `VizEngine/src/VizEngine/OpenGL/Texture.cpp`:**

```cpp
Texture::Texture(int resolution, bool isHDR)
	: m_texture(0), m_FilePath("cubemap"), m_LocalBuffer(nullptr),
	  m_Width(resolution), m_Height(resolution), m_BPP(3),
	  m_IsCubemap(true), m_IsHDR(isHDR)
{
	glGenTextures(1, &m_texture);
	glBindTexture(GL_TEXTURE_CUBE_MAP, m_texture);

	// Allocate storage for all 6 faces
	GLenum internalFormat = isHDR ? GL_RGB16F : GL_RGB8;
	GLenum format = GL_RGB;
	GLenum type = isHDR ? GL_FLOAT : GL_UNSIGNED_BYTE;

	for (unsigned int i = 0; i < 6; ++i)
	{
		glTexImage2D(
			GL_TEXTURE_CUBE_MAP_POSITIVE_X + i,  // Face target
			0,                                    // Mipmap level
			internalFormat,
			m_Width,
			m_Height,
			0,                                    // Border
			format,
			type,
			nullptr                               // No data (allocate empty)
		);
	}

	// Set texture parameters
	glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

	glBindTexture(GL_TEXTURE_CUBE_MAP, 0);

	VP_CORE_INFO("Empty cubemap created: {}x{} per face ({})", 
		m_Width, m_Height, isHDR ? "HDR" : "LDR");
}
```

> [!IMPORTANT]
> Cubemaps use `GL_TEXTURE_CUBE_MAP` as the target and have a **wrap mode for R** (third texture coordinate). Always set all three wrap modes (S, T, R).

### Update Bind() for Cubemaps

**Modify `Texture::Bind()` in `Texture.cpp`:**

```cpp
void Texture::Bind(unsigned int slot) const
{
	glActiveTexture(GL_TEXTURE0 + slot);
	
	if (m_IsCubemap)
		glBindTexture(GL_TEXTURE_CUBE_MAP, m_texture);
	else
		glBindTexture(GL_TEXTURE_2D, m_texture);
}
```

**Modify `Texture::Unbind()` in `Texture.cpp`:**

```cpp
void Texture::Unbind() const
{
	if (m_IsCubemap)
		glBindTexture(GL_TEXTURE_CUBE_MAP, 0);
	else
		glBindTexture(GL_TEXTURE_2D, 0);
}
```

---

## Step 3: Create Equirectangular-to-Cubemap Shader

This shader converts equirect UV coordinates to cubemap direction sampling.

**Create `VizEngine/src/resources/shaders/equirect_to_cube.shader`:**

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 aPos;

out vec3 v_WorldPos;

uniform mat4 u_Projection;
uniform mat4 u_View;

void main()
{
    v_WorldPos = aPos;
    gl_Position = u_Projection * u_View * vec4(aPos, 1.0);
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec3 v_WorldPos;

uniform sampler2D u_EquirectangularMap;

// Convert 3D direction vector to equirectangular UV coordinates
vec2 SampleSphericalMap(vec3 v)
{
    // Inverse of spherical coordinates
    // atan(y, x) gives angle in XZ plane (longitude)
    // asin(z) gives angle from equator (latitude)
    
    vec2 uv = vec2(atan(v.z, v.x), asin(v.y));
    
    // Normalize from [-π, π] × [-π/2, π/2] to [0, 1] × [0, 1]
    uv *= vec2(0.1591, 0.3183);  // inv(2π), inv(π)
    uv += 0.5;
    
    return uv;
}

void main()
{
    // Convert fragment's 3D position to spherical UV
    vec2 uv = SampleSphericalMap(normalize(v_WorldPos));
    
    // Sample equirectangular map
    vec3 color = texture(u_EquirectangularMap, uv).rgb;
    
    FragColor = vec4(color, 1.0);
}
```

> [!NOTE]
> **Spherical coordinate math**:
> - `atan(z, x)` gives horizontal angle (longitude): [-π, π]
> - `asin(y)` gives vertical angle (latitude): [-π/2, π/2]
> - We normalize these ranges to [0, 1] for texture sampling

---

## Step 4: Update Build Configuration

Add the new files to the build system.

**Modify `VizEngine/CMakeLists.txt`:**

In the `VIZENGINE_SOURCES` section, add after `VertexBuffer.cpp`:

```cmake
    src/VizEngine/OpenGL/CubemapUtils.cpp
```

In the `VIZENGINE_HEADERS` section, add after `VertexBufferLayout.h`:

```cmake
    src/VizEngine/OpenGL/CubemapUtils.h
```

**Modify `VizEngine/src/VizEngine.h`:**

Add to the OpenGL includes section (after `Framebuffer.h`):

```cpp
#include "VizEngine/OpenGL/CubemapUtils.h"
```

> [!IMPORTANT]
> **Build System Integration**: Every new `.cpp` file must be added to `CMakeLists.txt` for the build to succeed. Every public header should be added to `VizEngine.h` for easy access by applications.

---

## Step 5: Create Cubemap Conversion Utility

This utility renders the equirectangular map to each cubemap face.

**Create `VizEngine/src/VizEngine/OpenGL/CubemapUtils.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/CubemapUtils.h

#pragma once

#include <memory>
#include "VizEngine/Core.h"

namespace VizEngine
{
	class Texture;

	/**
	 * Utilities for cubemap texture operations.
	 */
	class VizEngine_API CubemapUtils
	{
	public:
		/**
		 * Convert equirectangular HDR texture to cubemap.
		 * Renders the equirectangular map to 6 cubemap faces using a shader.
		 * This is a one-time conversion operation.
		 * @param equirectangularMap Source HDR texture (2:1 aspect ratio)
		 * @param resolution Resolution per cubemap face (e.g., 512, 1024)
		 * @return Cubemap texture ready for use in skybox or IBL
		 */
		static std::shared_ptr<Texture> EquirectangularToCubemap(
			std::shared_ptr<Texture> equirectangularMap,
			int resolution
		);
	};
}
```

**Create `VizEngine/src/VizEngine/OpenGL/CubemapUtils.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/CubemapUtils.cpp

#include "CubemapUtils.h"
#include "Texture.h"
#include "Shader.h"
#include "Framebuffer.h"
#include "VertexArray.h"
#include "VertexBuffer.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>
#include <glm.hpp>
#include <gtc/matrix_transform.hpp>

namespace VizEngine
{
	std::shared_ptr<Texture> CubemapUtils::EquirectangularToCubemap(
		std::shared_ptr<Texture> equirectangularMap,
		int resolution)
	{
		VP_CORE_INFO("Converting equirectangular map to cubemap ({}x{} per face)...", resolution, resolution);

		// Create empty cubemap texture
		auto cubemap = std::make_shared<Texture>(resolution, equirectangularMap->IsHDR());

		// Create framebuffer for rendering to cubemap faces
		auto framebuffer = std::make_shared<Framebuffer>(resolution, resolution);

		// Create depth renderbuffer (we don't need to sample it)
		unsigned int rbo;
		glGenRenderbuffers(1, &rbo);
		glBindRenderbuffer(GL_RENDERBUFFER, rbo);
		glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, resolution, resolution);
		glBindRenderbuffer(GL_RENDERBUFFER, 0);

		// Attach depth renderbuffer to framebuffer
		framebuffer->Bind();
		glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, rbo);

		// Load conversion shader
		auto shader = std::make_shared<Shader>("resources/shaders/equirect_to_cube.shader");

		// Projection matrix (90° FOV to cover each face exactly)
		glm::mat4 captureProjection = glm::perspective(glm::radians(90.0f), 1.0f, 0.1f, 10.0f);

		// View matrices for each cubemap face
		glm::mat4 captureViews[] = {
			glm::lookAt(glm::vec3(0.0f), glm::vec3( 1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),  // +X
			glm::lookAt(glm::vec3(0.0f), glm::vec3(-1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),  // -X
			glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  1.0f,  0.0f), glm::vec3(0.0f,  0.0f,  1.0f)),  // +Y
			glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f, -1.0f,  0.0f), glm::vec3(0.0f,  0.0f, -1.0f)),  // -Y
			glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  0.0f,  1.0f), glm::vec3(0.0f, -1.0f,  0.0f)),  // +Z
			glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  0.0f, -1.0f), glm::vec3(0.0f, -1.0f,  0.0f))   // -Z
		};

		// Cube vertices (positions only, for fullscreen rendering)
		float cubeVertices[] = {
			// Positions
			-1.0f, -1.0f, -1.0f,
			 1.0f,  1.0f, -1.0f,
			 1.0f, -1.0f, -1.0f,
			 1.0f,  1.0f, -1.0f,
			-1.0f, -1.0f, -1.0f,
			-1.0f,  1.0f, -1.0f,

			-1.0f, -1.0f,  1.0f,
			 1.0f, -1.0f,  1.0f,
			 1.0f,  1.0f,  1.0f,
			 1.0f,  1.0f,  1.0f,
			-1.0f,  1.0f,  1.0f,
			-1.0f, -1.0f,  1.0f,

			-1.0f,  1.0f,  1.0f,
			-1.0f,  1.0f, -1.0f,
			-1.0f, -1.0f, -1.0f,
			-1.0f, -1.0f, -1.0f,
			-1.0f, -1.0f,  1.0f,
			-1.0f,  1.0f,  1.0f,

			 1.0f,  1.0f,  1.0f,
			 1.0f, -1.0f, -1.0f,
			 1.0f,  1.0f, -1.0f,
			 1.0f, -1.0f, -1.0f,
			 1.0f,  1.0f,  1.0f,
			 1.0f, -1.0f,  1.0f,

			-1.0f, -1.0f, -1.0f,
			 1.0f, -1.0f, -1.0f,
			 1.0f, -1.0f,  1.0f,
			 1.0f, -1.0f,  1.0f,
			-1.0f, -1.0f,  1.0f,
			-1.0f, -1.0f, -1.0f,

			-1.0f,  1.0f, -1.0f,
			 1.0f,  1.0f,  1.0f,
			 1.0f,  1.0f, -1.0f,
			 1.0f,  1.0f,  1.0f,
			-1.0f,  1.0f, -1.0f,
			-1.0f,  1.0f,  1.0f
		};

		// Setup cube VAO/VBO
		auto cubeVBO = std::make_shared<VertexBuffer>(cubeVertices, sizeof(cubeVertices));
		VertexBufferLayout layout;
		layout.Push<float>(3);  // Position

		auto cubeVAO = std::make_shared<VertexArray>();
		cubeVAO->LinkVertexBuffer(*cubeVBO, layout);

		// Bind shader and equirectangular map
		shader->Bind();
		shader->SetMatrix4fv("u_Projection", captureProjection);
		equirectangularMap->Bind(0);
		shader->SetInt("u_EquirectangularMap", 0);

		glViewport(0, 0, resolution, resolution);
		framebuffer->Bind();

		// Render to each cubemap face
		for (unsigned int i = 0; i < 6; ++i)
		{
			shader->SetMatrix4fv("u_View", captureViews[i]);

			// Attach current cubemap face to framebuffer
			glFramebufferTexture2D(
				GL_FRAMEBUFFER,
				GL_COLOR_ATTACHMENT0,
				GL_TEXTURE_CUBE_MAP_POSITIVE_X + i,
				cubemap->GetID(),
				0  // Mipmap level
			);

			// Verify framebuffer is complete after attachment
			if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
			{
				VP_CORE_ERROR("Cubemap conversion: FBO incomplete for face {}", i);
				glDeleteRenderbuffers(1, &rbo);
				return nullptr;
			}

			glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

			// Render cube
			cubeVAO->Bind();
			glDrawArrays(GL_TRIANGLES, 0, 36);
		}

		framebuffer->Unbind();

		// Generate mipmaps for the cubemap (improves quality and required for IBL)
		glBindTexture(GL_TEXTURE_CUBE_MAP, cubemap->GetID());
		glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
		glGenerateMipmap(GL_TEXTURE_CUBE_MAP);
		glBindTexture(GL_TEXTURE_CUBE_MAP, 0);

		// Cleanup
		glDeleteRenderbuffers(1, &rbo);

		VP_CORE_INFO("Cubemap conversion complete (with mipmaps)!");

		return cubemap;
	}
}
```

> [!IMPORTANT]
> **View Matrix Setup**: Each `lookAt()` matrix faces a cube direction:
> - First parameter: origin (always vec3(0))
> - Second parameter: look direction (+X, -X, +Y, -Y, +Z, -Z)
> - Third parameter: up vector (varies per face to avoid gimbal lock)

---


## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Black/white cubemap** | HDR not loaded | Use `stbi_loadf()` not `stbi_load()`, check `GL_RGB16F` format |
| **Conversion fails** | Shader not found | Verify `equirect_to_cube.shader` path is correct |
| **Distorted cubemap** | UV formula wrong | Check `atan(v.z, v.x)` and `asin(v.y)` order in shader |
| **Slow conversion** | Converting every frame | Convert once in `OnCreate()`, cache result |
| **Seams between faces** | Filtering not set | Use `GL_CLAMP_TO_EDGE` for S, T, R wrap modes |
| **Memory issues** | Resolution too high | Start with 512, only use 1024+ if needed |
| **Compilation error** | Missing includes | Add `#include "VizEngine/OpenGL/CubemapUtils.h"` |

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
| **2048×2048** | High | ~144 MB | High-end, close-up environments |

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

## Testing

1. **Build and run** the application
2. **Add test code** in `SandboxApp::OnCreate()`:
  
```cpp
// Test HDRI loading and conversion
auto hdri = std::make_shared<VizEngine::Texture>(
    "resources/textures/environments/newport_loft.hdr", 
    true
);

auto cubemap = VizEngine::CubemapUtils::EquirectangularToCubemap(hdri, 512);

VP_INFO("Cubemap ready! ID: {}", cubemap->GetID());
```

3. **Verify console logs**:
   - "HDR Texture loaded: ..."
   - "Converting equirectangular map to cubemap..."
   - "Cubemap conversion complete!"
4. **Check performance**: Conversion should complete in < 1 second for 512×512
5. **Verify no OpenGL errors**: Check debug output

---

## Milestone

**Chapter 30 Complete - Cubemaps and HDR Environment Maps**

You have:
- Extended `Texture` class with HDR loading (`stbi_loadf`)
- Implemented floating-point texture support (`GL_RGB16F`)
- Created empty cubemap textures with proper OpenGL targets
- Built equirectangular-to-cubemap conversion shader
- Implemented `CubemapUtils` helper class for conversion
- Understood cubemap structure (6 faces, 3D sampling)
- Learned modern HDRI workflow (industry standard)

Your cubemap texture is ready to use for **skybox rendering** (Chapter 31), **environment reflections** (Chapter 32), and **image-based lighting** (Chapter 33).

---

## What's Next

In **Chapter 31: Skybox Rendering**, we'll use the cubemap you created to render an immersive environment that surrounds the camera, implementing the view matrix trick and depth rendering technique.

> **Next:** [Chapter 31: Skybox Rendering](31_SkyboxRendering.md)

> **Previous:** [Chapter 29: Shadow Mapping](29_ShadowMapping.md)

> **Index:** [Table of Contents](INDEX.md)
