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

#include <iostream>
#include <string>
#include <glad/glad.h>
#include "VizEngine/Core.h"

namespace VizEngine
{
    class VizEngine_API Texture
    {
    public:
        // Load from file
        Texture(const std::string& path);
        ~Texture();

        // No copying
        Texture(const Texture&) = delete;
        Texture& operator=(const Texture&) = delete;

        // Allow moving
        Texture(Texture&& other) noexcept;
        Texture& operator=(Texture&& other) noexcept;

        void Bind(unsigned int slot = 0) const;
        void Unbind() const;

        inline int GetWidth() const { return m_Width; }
        inline int GetHeight() const { return m_Height; }
        inline unsigned int GetID() const { return m_RendererID; }

    private:
        unsigned int m_RendererID;
        std::string m_FilePath;
        unsigned char* m_LocalBuffer;
        int m_Width, m_Height, m_BPP;
    };

}  // namespace VizEngine
```

---

## Step 6: Create Texture.cpp

**Create `VizEngine/src/VizEngine/OpenGL/Texture.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Texture.cpp

#include "Texture.h"
#include "VizEngine/Log.h"
#include "stb_image.h"

namespace VizEngine
{
    Texture::Texture(const std::string& path)
        : m_RendererID(0), m_FilePath(path), m_LocalBuffer(nullptr),
          m_Width(0), m_Height(0), m_BPP(0)
    {
        // Flip texture vertically (OpenGL expects bottom-left origin)
        stbi_set_flip_vertically_on_load(1);
        
        // Load image (force 4 channels - RGBA)
        m_LocalBuffer = stbi_load(path.c_str(), &m_Width, &m_Height, &m_BPP, 4);

        if (!m_LocalBuffer)
        {
            VP_CORE_ERROR("Failed to load texture: {}", path);
            return;
        }

        // Create texture
        glGenTextures(1, &m_RendererID);
        glBindTexture(GL_TEXTURE_2D, m_RendererID);

        // Set parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);

        // Upload to GPU
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, m_Width, m_Height, 0, GL_RGBA, GL_UNSIGNED_BYTE, m_LocalBuffer);
        glGenerateMipmap(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, 0);

        // Free CPU-side data
        stbi_image_free(m_LocalBuffer);
        m_LocalBuffer = nullptr;
    }

    Texture::~Texture()
    {
        if (m_RendererID != 0)
        {
            glDeleteTextures(1, &m_RendererID);
        }
    }

    Texture::Texture(Texture&& other) noexcept
        : m_RendererID(other.m_RendererID)
        , m_FilePath(std::move(other.m_FilePath))
        , m_LocalBuffer(other.m_LocalBuffer)
        , m_Width(other.m_Width)
        , m_Height(other.m_Height)
        , m_BPP(other.m_BPP)
    {
        other.m_RendererID = 0;
        other.m_LocalBuffer = nullptr;
    }

    Texture& Texture::operator=(Texture&& other) noexcept
    {
        if (this != &other)
        {
            if (m_RendererID != 0)
                glDeleteTextures(1, &m_RendererID);

            m_RendererID = other.m_RendererID;
            m_FilePath = std::move(other.m_FilePath);
            m_LocalBuffer = other.m_LocalBuffer;
            m_Width = other.m_Width;
            m_Height = other.m_Height;
            m_BPP = other.m_BPP;

            other.m_RendererID = 0;
            other.m_LocalBuffer = nullptr;
        }
        return *this;
    }

    void Texture::Bind(unsigned int slot) const
    {
        glActiveTexture(GL_TEXTURE0 + slot);
        glBindTexture(GL_TEXTURE_2D, m_RendererID);
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
