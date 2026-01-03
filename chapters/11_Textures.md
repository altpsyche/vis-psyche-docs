\newpage

# Chapter 11: Texture System

Add texture support by integrating **stb_image** and creating a `Texture` class. This is the first time we add a new library since Chapter 3.

---

## Adding stb_image

stb_image is a single-header library for loading images.

### Step 1: Create Vendor Directory

```bash
mkdir VizEngine/vendor/stb_image
```

### Step 2: Download stb_image.h

Download from: https://raw.githubusercontent.com/nothings/stb/master/stb_image.h

Save to: `VizEngine/vendor/stb_image/stb_image.h`

### Step 3: Create Implementation File

**Create `VizEngine/vendor/stb_image/stb_image.cpp`:**

```cpp
// VizEngine/vendor/stb_image/stb_image.cpp

// This file contains the implementation of stb_image.
// Only ONE file in the project should define this.

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
```

### Step 4: Update CMakeLists.txt

```cmake
# Add to VENDOR_SOURCES (create this section if needed)
set(VENDOR_SOURCES
    vendor/stb_image/stb_image.cpp
)

# Update add_library to include vendor sources
add_library(VizEngine SHARED
    ${VIZENGINE_SOURCES}
    ${VIZENGINE_HEADERS}
    ${VENDOR_SOURCES}
)

# Add include directory
target_include_directories(VizEngine
    PRIVATE
        # ... existing ...
        ${CMAKE_CURRENT_SOURCE_DIR}/vendor/stb_image
)
```

---

## Step 5: Create Texture.h

**Create `VizEngine/src/VizEngine/OpenGL/Texture.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Texture.h

#pragma once

#include "VizEngine/Core.h"
#include <string>

namespace VizEngine
{
    class VizEngine_API Texture
    {
    public:
        Texture(const std::string& filepath);
        ~Texture();

        // No copying
        Texture(const Texture&) = delete;
        Texture& operator=(const Texture&) = delete;

        // Allow moving
        Texture(Texture&& other) noexcept;
        Texture& operator=(Texture&& other) noexcept;

        void Bind(unsigned int slot = 0) const;
        void Unbind() const;

        int GetWidth() const { return m_Width; }
        int GetHeight() const { return m_Height; }
        unsigned int GetID() const { return m_ID; }

    private:
        unsigned int m_ID = 0;
        std::string m_Filepath;
        int m_Width = 0;
        int m_Height = 0;
        int m_Channels = 0;
    };

}  // namespace VizEngine
```

---

## Step 6: Create Texture.cpp

**Create `VizEngine/src/VizEngine/OpenGL/Texture.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Texture.cpp

#include "Texture.h"
#include "Commons.h"
#include "VizEngine/Log.h"

#include <stb_image.h>

namespace VizEngine
{
    Texture::Texture(const std::string& filepath)
        : m_Filepath(filepath)
    {
        // Flip texture vertically (OpenGL expects bottom-left origin)
        stbi_set_flip_vertically_on_load(true);

        // Load image
        unsigned char* data = stbi_load(
            filepath.c_str(),
            &m_Width, &m_Height, &m_Channels,
            0  // Don't force channels
        );

        if (!data)
        {
            VP_CORE_ERROR("Failed to load texture: {}", filepath);
            return;
        }

        VP_CORE_TRACE("Loaded texture: {}x{} ({} channels)", m_Width, m_Height, m_Channels);

        // Determine format
        GLenum internalFormat = GL_RGB8;
        GLenum dataFormat = GL_RGB;

        if (m_Channels == 4)
        {
            internalFormat = GL_RGBA8;
            dataFormat = GL_RGBA;
        }
        else if (m_Channels == 1)
        {
            internalFormat = GL_R8;
            dataFormat = GL_RED;
        }

        // Create texture
        glGenTextures(1, &m_ID);
        glBindTexture(GL_TEXTURE_2D, m_ID);

        // Set parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);

        // Upload to GPU
        glTexImage2D(
            GL_TEXTURE_2D,
            0,                  // Mipmap level
            internalFormat,     // Internal format
            m_Width, m_Height,
            0,                  // Border (must be 0)
            dataFormat,         // Source format
            GL_UNSIGNED_BYTE,   // Source type
            data
        );

        // Generate mipmaps
        glGenerateMipmap(GL_TEXTURE_2D);

        // Free CPU-side data
        stbi_image_free(data);

        VP_CORE_INFO("Texture created: {} (ID={})", filepath, m_ID);
    }

    Texture::~Texture()
    {
        if (m_ID != 0)
        {
            glDeleteTextures(1, &m_ID);
            VP_CORE_TRACE("Texture deleted: {}", m_Filepath);
        }
    }

    Texture::Texture(Texture&& other) noexcept
        : m_ID(other.m_ID)
        , m_Filepath(std::move(other.m_Filepath))
        , m_Width(other.m_Width)
        , m_Height(other.m_Height)
        , m_Channels(other.m_Channels)
    {
        other.m_ID = 0;
        other.m_Width = 0;
        other.m_Height = 0;
        other.m_Channels = 0;
    }

    Texture& Texture::operator=(Texture&& other) noexcept
    {
        if (this != &other)
        {
            if (m_ID != 0)
                glDeleteTextures(1, &m_ID);

            m_ID = other.m_ID;
            m_Filepath = std::move(other.m_Filepath);
            m_Width = other.m_Width;
            m_Height = other.m_Height;
            m_Channels = other.m_Channels;

            other.m_ID = 0;
            other.m_Width = 0;
            other.m_Height = 0;
            other.m_Channels = 0;
        }
        return *this;
    }

    void Texture::Bind(unsigned int slot) const
    {
        glActiveTexture(GL_TEXTURE0 + slot);
        glBindTexture(GL_TEXTURE_2D, m_ID);
    }

    void Texture::Unbind() const
    {
        glBindTexture(GL_TEXTURE_2D, 0);
    }

}  // namespace VizEngine
```

---

## Step 7: Update CMakeLists.txt Sources

```cmake
set(VIZENGINE_SOURCES
    # ... existing ...
    src/VizEngine/OpenGL/Texture.cpp      # NEW
)

set(VIZENGINE_HEADERS
    # ... existing ...
    src/VizEngine/OpenGL/Texture.h        # NEW
)
```

---

## Texture Concepts

### Texture Coordinates (UV)

Vertices need UV coordinates (0-1 range) to map texture pixels:

```cpp
struct Vertex {
    glm::vec3 Position;
    glm::vec3 Color;
    glm::vec2 TexCoords;  // NEW
};

float vertices[] = {
    // Position           Color            TexCoords
    -0.5f, -0.5f, 0.0f,   1.0f, 1.0f, 1.0f,  0.0f, 0.0f,  // Bottom-left
     0.5f, -0.5f, 0.0f,   1.0f, 1.0f, 1.0f,  1.0f, 0.0f,  // Bottom-right
     0.5f,  0.5f, 0.0f,   1.0f, 1.0f, 1.0f,  1.0f, 1.0f,  // Top-right
    -0.5f,  0.5f, 0.0f,   1.0f, 1.0f, 1.0f,  0.0f, 1.0f,  // Top-left
};
```

### Texture Slots

OpenGL has multiple texture slots (typically 16-32):

```cpp
texture1.Bind(0);  // GL_TEXTURE0
texture2.Bind(1);  // GL_TEXTURE1

shader.SetInt("u_Texture1", 0);  // Tell shader which slot
shader.SetInt("u_Texture2", 1);
```

### Filtering

| Mode | Use Case |
|------|----------|
| `GL_NEAREST` | Pixel art, sharp edges |
| `GL_LINEAR` | Smooth scaling |
| `GL_LINEAR_MIPMAP_LINEAR` | Best quality with mipmaps |

### Wrapping

| Mode | Effect |
|------|--------|
| `GL_REPEAT` | Tile the texture |
| `GL_CLAMP_TO_EDGE` | Stretch edge pixels |
| `GL_MIRRORED_REPEAT` | Tile with mirroring |

---

## Usage Example

```cpp
// Load texture
Texture texture("assets/textures/wood.png");

// In render loop
texture.Bind(0);

shader.Bind();
shader.SetInt("u_Texture", 0);
shader.SetInt("u_UseTexture", 1);

vao.Bind();
glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);

texture.Unbind();
```

---

## Shader Update

Ensure your shader samples the texture:

```glsl
#shader fragment
#version 460 core

in vec2 texCoord;
out vec4 FragColor;

uniform sampler2D u_Texture;
uniform int u_UseTexture;
uniform vec4 u_Color;

void main()
{
    if (u_UseTexture == 1)
        FragColor = texture(u_Texture, texCoord) * u_Color;
    else
        FragColor = u_Color;
}
```

---

## Project Structure After This Chapter

```
VizEngine/
├── vendor/
│   ├── glfw/
│   ├── glm/
│   ├── spdlog/
│   └── stb_image/          # NEW
│       ├── stb_image.h
│       └── stb_image.cpp
└── src/VizEngine/OpenGL/
    ├── Texture.cpp         # NEW
    └── Texture.h           # NEW
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Texture upside down | Different coordinate origin | `stbi_set_flip_vertically_on_load(true)` |
| Black texture | Texture not bound | Call `texture.Bind()` before draw |
| Wrong texture shows | Slot mismatch | Ensure `Bind(N)` matches `SetInt("u_Texture", N)` |
| Blurry texture | Linear filtering on pixel art | Use `GL_NEAREST` filter |

---

## Milestone

**Texture System Complete**

You have:
- stb_image integrated
- RAII-compliant `Texture` class
- Texture slot support
- Proper filtering and wrapping

---

## What's Next

In **Chapter 12**, we'll create a `Renderer` class to centralize draw calls.

> **Next:** [Chapter 12: Renderer Class](12_Renderer.md)

> **Previous:** [Chapter 10: Shader System](10_ShaderAndRenderer.md)
