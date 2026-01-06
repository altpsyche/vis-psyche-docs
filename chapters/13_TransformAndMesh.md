\newpage

# Chapter 13: Transform & Mesh

Create `Transform` and `Mesh` classes to represent 3D objects with position, rotation, scale, and geometry.

---

## What We're Building

| Class | Purpose |
|-------|---------|
| `Transform` | Position, rotation, scale → model matrix |
| `Vertex` | Vertex data structure (vec4 position) |
| `Mesh` | Geometry with VAO/VBO/IBO and factory methods |

---

## Step 1: Create Transform.h

**Create `VizEngine/src/VizEngine/Core/Transform.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Transform.h

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"
#include "gtc/matrix_transform.hpp"
#include "gtc/quaternion.hpp"

namespace VizEngine
{
    struct VizEngine_API Transform
    {
        glm::vec3 Position = glm::vec3(0.0f);
        glm::vec3 Rotation = glm::vec3(0.0f);  // Euler angles in radians
        glm::vec3 Scale = glm::vec3(1.0f);

        Transform() = default;

        Transform(const glm::vec3& position)
            : Position(position) {}

        Transform(const glm::vec3& position, const glm::vec3& rotation)
            : Position(position), Rotation(rotation) {}

        Transform(const glm::vec3& position, const glm::vec3& rotation, const glm::vec3& scale)
            : Position(position), Rotation(rotation), Scale(scale) {}

        glm::mat4 GetModelMatrix() const
        {
            glm::mat4 model = glm::mat4(1.0f);

            // Apply: Translate -> Rotate -> Scale
            model = glm::translate(model, Position);
            model = glm::rotate(model, Rotation.x, glm::vec3(1.0f, 0.0f, 0.0f));
            model = glm::rotate(model, Rotation.y, glm::vec3(0.0f, 1.0f, 0.0f));
            model = glm::rotate(model, Rotation.z, glm::vec3(0.0f, 0.0f, 1.0f));
            model = glm::scale(model, Scale);

            return model;
        }

        void SetRotationDegrees(const glm::vec3& degrees)
        {
            Rotation = glm::radians(degrees);
        }

        glm::vec3 GetRotationDegrees() const
        {
            return glm::degrees(Rotation);
        }
    };

}  // namespace VizEngine
```

> [!NOTE]
> Rotation is stored in **radians** internally. Use `GetRotationDegrees()` and `SetRotationDegrees()` for UI.

---

## Step 2: Create Mesh.h

**Create `VizEngine/src/VizEngine/Core/Mesh.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Mesh.h

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"
#include "VizEngine/OpenGL/VertexArray.h"
#include "VizEngine/OpenGL/VertexBuffer.h"
#include "VizEngine/OpenGL/IndexBuffer.h"
#include "VizEngine/OpenGL/VertexBufferLayout.h"
#include <vector>
#include <memory>

namespace VizEngine
{
    // Vertex with vec4 Position for homogeneous coordinates
    struct Vertex
    {
        glm::vec4 Position;   // w=1 for points
        glm::vec3 Normal;
        glm::vec4 Color;
        glm::vec2 TexCoords;

        Vertex() = default;

        Vertex(const glm::vec4& pos, const glm::vec3& norm, const glm::vec4& col, const glm::vec2& tex)
            : Position(pos), Normal(norm), Color(col), TexCoords(tex) {}

        // Convenience: vec3 position (w defaults to 1)
        Vertex(const glm::vec3& pos, const glm::vec3& norm, const glm::vec4& col, const glm::vec2& tex)
            : Position(glm::vec4(pos, 1.0f)), Normal(norm), Color(col), TexCoords(tex) {}
    };

    class VizEngine_API Mesh
    {
    public:
        Mesh(const std::vector<Vertex>& vertices, const std::vector<unsigned int>& indices);
        ~Mesh() = default;

        // No copying
        Mesh(const Mesh&) = delete;
        Mesh& operator=(const Mesh&) = delete;

        // Allow moving
        Mesh(Mesh&&) noexcept = default;
        Mesh& operator=(Mesh&&) noexcept = default;

        void Bind() const;
        void Unbind() const;

        unsigned int GetIndexCount() const { return m_IndexBuffer->GetCount(); }

        // Accessors for Renderer.Draw()
        const VertexArray& GetVertexArray() const { return *m_VertexArray; }
        const IndexBuffer& GetIndexBuffer() const { return *m_IndexBuffer; }

        // Factory methods
        static std::unique_ptr<Mesh> CreatePyramid();
        static std::unique_ptr<Mesh> CreateCube();
        static std::unique_ptr<Mesh> CreatePlane(float size = 1.0f);

    private:
        std::unique_ptr<VertexArray> m_VertexArray;
        std::unique_ptr<VertexBuffer> m_VertexBuffer;
        std::unique_ptr<IndexBuffer> m_IndexBuffer;
    };

}  // namespace VizEngine
```

> [!IMPORTANT]
> - `Position` is `vec4` (homogeneous coordinates, w=1 for points)
> - `GetVertexArray()` and `GetIndexBuffer()` are used by `Renderer::Draw()`
> - Internal buffers use `unique_ptr` for RAII

---

## Step 3: Create Mesh.cpp

**Create `VizEngine/src/VizEngine/Core/Mesh.cpp`:**

```cpp
// VizEngine/src/VizEngine/Core/Mesh.cpp

#include "Mesh.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    Mesh::Mesh(const std::vector<Vertex>& vertices, const std::vector<unsigned int>& indices)
    {
        // Create buffers
        m_VertexBuffer = std::make_unique<VertexBuffer>(
            vertices.data(), vertices.size() * sizeof(Vertex));

        m_IndexBuffer = std::make_unique<IndexBuffer>(
            indices.data(), static_cast<unsigned int>(indices.size()));

        // Create VAO and configure layout
        m_VertexArray = std::make_unique<VertexArray>();

        VertexBufferLayout layout;
        layout.Push<float>(4);  // Position (vec4)
        layout.Push<float>(3);  // Normal
        layout.Push<float>(4);  // Color
        layout.Push<float>(2);  // TexCoords

        m_VertexArray->LinkVertexBuffer(*m_VertexBuffer, layout);

        VP_CORE_TRACE("Mesh created: {} vertices, {} indices",
            vertices.size(), indices.size());
    }

    void Mesh::Bind() const
    {
        m_VertexArray->Bind();
        m_IndexBuffer->Bind();
    }

    void Mesh::Unbind() const
    {
        m_VertexArray->Unbind();
    }

    std::unique_ptr<Mesh> Mesh::CreateCube()
    {
        std::vector<Vertex> vertices = {
            // Front face (z = 0.5)
            {{-0.5f, -0.5f,  0.5f, 1.0f}, { 0,  0,  1}, {1, 1, 1, 1}, {0, 0}},
            {{ 0.5f, -0.5f,  0.5f, 1.0f}, { 0,  0,  1}, {1, 1, 1, 1}, {1, 0}},
            {{ 0.5f,  0.5f,  0.5f, 1.0f}, { 0,  0,  1}, {1, 1, 1, 1}, {1, 1}},
            {{-0.5f,  0.5f,  0.5f, 1.0f}, { 0,  0,  1}, {1, 1, 1, 1}, {0, 1}},
            // Back, Top, Bottom, Right, Left faces...
            // (Similar pattern with appropriate normals)
        };

        std::vector<unsigned int> indices;
        for (unsigned int i = 0; i < 6; i++)
        {
            unsigned int base = i * 4;
            indices.push_back(base + 0);
            indices.push_back(base + 1);
            indices.push_back(base + 2);
            indices.push_back(base + 2);
            indices.push_back(base + 3);
            indices.push_back(base + 0);
        }

        return std::make_unique<Mesh>(vertices, indices);
    }

    std::unique_ptr<Mesh> Mesh::CreatePlane(float size)
    {
        float half = size / 2.0f;
        std::vector<Vertex> vertices = {
            {{-half, 0.0f, -half, 1.0f}, {0, 1, 0}, {1, 1, 1, 1}, {0, 0}},
            {{ half, 0.0f, -half, 1.0f}, {0, 1, 0}, {1, 1, 1, 1}, {1, 0}},
            {{ half, 0.0f,  half, 1.0f}, {0, 1, 0}, {1, 1, 1, 1}, {1, 1}},
            {{-half, 0.0f,  half, 1.0f}, {0, 1, 0}, {1, 1, 1, 1}, {0, 1}},
        };
        std::vector<unsigned int> indices = { 0, 1, 2, 2, 3, 0 };
        return std::make_unique<Mesh>(vertices, indices);
    }

    std::unique_ptr<Mesh> Mesh::CreatePyramid()
    {
        // ... similar pattern with vec4 positions
        return std::make_unique<Mesh>(/*vertices*/{}, /*indices*/{});
    }

}  // namespace VizEngine
```

---

## Step 4: Update CMakeLists.txt

Add the new `Mesh.cpp` to the build system.

**Modify `VizEngine/CMakeLists.txt`:**

In the `VIZENGINE_SOURCES` section (Core subsection), add:

```cmake
    src/VizEngine/Core/Mesh.cpp
```

In the `VIZENGINE_HEADERS` section (Core headers subsection), add:

```cmake
    src/VizEngine/Core/Mesh.h
    src/VizEngine/Core/Transform.h
```

> [!NOTE]
> `Transform.h` is header-only (no `.cpp` file), so it only needs to be in `VIZENGINE_HEADERS`.

---

## Usage Example

```cpp
// Factory returns unique_ptr
auto cubeUnique = Mesh::CreateCube();

// Convert to shared_ptr for sharing
std::shared_ptr<Mesh> cubeMesh(cubeUnique.release());

// Use in scene
auto& cube = scene.Add(cubeMesh, "Cube");
cube.ObjectTransform.Position = glm::vec3(0.0f, 1.0f, 0.0f);

// Draw manually using renderer
renderer.Draw(cubeMesh->GetVertexArray(), cubeMesh->GetIndexBuffer(), shader);
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Mesh distorted | Wrong layout stride | Layout must match Vertex struct |
| Can't call Draw | No GetVertexArray | Use mesh accessors |
| Position shifted | vec3 vs vec4 | Use vec4 with w=1 |

---

## Milestone

**Transform & Mesh Complete**

You have:
- `Transform` struct with radians and constructors
- `Vertex` struct with `vec4 Position`
- `Mesh` with `unique_ptr` buffers
- `GetVertexArray()`, `GetIndexBuffer()` for Renderer

---

## What's Next

In **Chapter 14**, we'll add a `Camera` class for view and projection matrices.

> **Next:** [Chapter 14: Camera System](14_CameraSystem.md)

> **Previous:** [Chapter 12: Renderer Class](12_Renderer.md)
