\newpage

# Chapter 15: Scene Management

Create a `Scene` class to manage multiple objects. Each object has a mesh, transform, optional texture, and material properties.

---

## What We're Building

| Class | Purpose |
|-------|---------|
| `SceneObject` | Single renderable entity |
| `Scene` | Collection of objects + render logic |

---

## Step 1: Create SceneObject.h

**Create `VizEngine/src/VizEngine/Core/SceneObject.h`:**

```cpp
// VizEngine/src/VizEngine/Core/SceneObject.h

#pragma once

#include "VizEngine/Core.h"
#include "Transform.h"
#include "Mesh.h"
#include "VizEngine/OpenGL/Texture.h"
#include "glm.hpp"
#include <memory>

namespace VizEngine
{
    struct VizEngine_API SceneObject
    {
        std::shared_ptr<Mesh> MeshPtr;
        std::shared_ptr<Texture> TexturePtr;
        Transform ObjectTransform;
        glm::vec4 Color = glm::vec4(1.0f);
        bool Active = true;
        std::string Name = "Object";

        SceneObject() = default;

        SceneObject(std::shared_ptr<Mesh> mesh)
            : MeshPtr(mesh) {}

        SceneObject(std::shared_ptr<Mesh> mesh, const Transform& transform)
            : MeshPtr(mesh), ObjectTransform(transform) {}

        SceneObject(std::shared_ptr<Mesh> mesh, const Transform& transform, const glm::vec4& color)
            : MeshPtr(mesh), ObjectTransform(transform), Color(color) {}
    };

}  // namespace VizEngine
```

---

## Step 2: Create Scene.h

**Create `VizEngine/src/VizEngine/Core/Scene.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Scene.h

#pragma once

#include "VizEngine/Core.h"
#include "SceneObject.h"
#include "Camera.h"
#include "VizEngine/OpenGL/Renderer.h"
#include "VizEngine/OpenGL/Shader.h"
#include <vector>
#include <memory>

namespace VizEngine
{
    class VizEngine_API Scene
    {
    public:
        Scene() = default;
        ~Scene() = default;

        // Prevent copying
        Scene(const Scene&) = delete;
        Scene& operator=(const Scene&) = delete;

        // Allow moving
        Scene(Scene&&) noexcept = default;
        Scene& operator=(Scene&&) noexcept = default;

        // Add object, return reference for configuration
        SceneObject& Add(std::shared_ptr<Mesh> mesh, const std::string& name = "Object");

        void Remove(size_t index);
        void Clear();

        // Access by index
        SceneObject& operator[](size_t index) { return m_Objects[index]; }
        const SceneObject& operator[](size_t index) const { return m_Objects[index]; }

        size_t Size() const { return m_Objects.size(); }
        bool Empty() const { return m_Objects.empty(); }

        // Range-based for loop support
        auto begin() { return m_Objects.begin(); }
        auto end() { return m_Objects.end(); }

        // Update (placeholder for animation)
        void Update(float deltaTime);

        // Render all active objects
        void Render(Renderer& renderer, Shader& shader, const Camera& camera);

    private:
        std::vector<SceneObject> m_Objects;
    };

}  // namespace VizEngine
```

---

## Step 3: Create Scene.cpp

**Create `VizEngine/src/VizEngine/Core/Scene.cpp`:**

```cpp
// VizEngine/src/VizEngine/Core/Scene.cpp

#include "Scene.h"
#include <glad/glad.h>

namespace VizEngine
{
    SceneObject& Scene::Add(std::shared_ptr<Mesh> mesh, const std::string& name)
    {
        SceneObject obj;
        obj.MeshPtr = mesh;
        obj.ObjectTransform = Transform{};
        obj.Color = glm::vec4(1.0f);
        obj.Active = true;
        obj.Name = name;

        m_Objects.push_back(std::move(obj));
        return m_Objects.back();
    }

    void Scene::Remove(size_t index)
    {
        if (index < m_Objects.size())
        {
            m_Objects.erase(m_Objects.begin() + static_cast<std::ptrdiff_t>(index));
        }
    }

    void Scene::Clear()
    {
        m_Objects.clear();
    }

    void Scene::Update(float deltaTime)
    {
        (void)deltaTime;  // Placeholder
    }

    void Scene::Render(Renderer& renderer, Shader& shader, const Camera& camera)
    {
        shader.Bind();

        // Explicitly set texture slot for main texture
        shader.SetInt("u_MainTex", 0);

        for (auto& obj : m_Objects)
        {
            if (!obj.Active) continue;
            if (!obj.MeshPtr) continue;

            // Matrices
            glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
            glm::mat4 mvp = camera.GetViewProjectionMatrix() * model;

            // Uniforms (for unlit.shader)
            shader.SetMatrix4fv("u_MVP", mvp);
            shader.SetVec4("u_ObjectColor", obj.Color);

            // Texture
            if (obj.TexturePtr)
            {
                obj.TexturePtr->Bind();
            }
            else
            {
                glBindTexture(GL_TEXTURE_2D, 0);
            }

            // Draw using renderer
            obj.MeshPtr->Bind();
            renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), shader);
        }
    }

}  // namespace VizEngine
```

> [!IMPORTANT]
> Note how `Render()` uses `renderer.Draw()` with `mesh->GetVertexArray()` and `mesh->GetIndexBuffer()`. This connects the Mesh, Renderer, and Scene classes.

---

## Step 4: Update CMakeLists.txt

Add the new `Scene.cpp` to the build system.

**Modify `VizEngine/CMakeLists.txt`:**

In the `VIZENGINE_SOURCES` section (Core subsection), add:

```cmake
    src/VizEngine/Core/Scene.cpp
```

In the `VIZENGINE_HEADERS` section (Core headers subsection), add:

```cmake
    src/VizEngine/Core/Scene.h
    src/VizEngine/Core/SceneObject.h
```

> [!NOTE]
> `SceneObject.h` is a header-only struct, so it only needs to be in `VIZENGINE_HEADERS`.

---

## Usage Example

```cpp
// Create shared meshes
std::shared_ptr<Mesh> cubeMesh(Mesh::CreateCube().release());
std::shared_ptr<Mesh> planeMesh(Mesh::CreatePlane(20.0f).release());

Scene scene;

// Add ground
auto& ground = scene.Add(planeMesh, "Ground");
ground.ObjectTransform.Position = glm::vec3(0.0f, -1.0f, 0.0f);
ground.Roughness = 0.9f;  // Very matte

// Add cube
auto& cube = scene.Add(cubeMesh, "Cube");
cube.ObjectTransform.Position = glm::vec3(0.0f, 1.0f, 0.0f);
cube.Color = glm::vec4(0.9f, 0.3f, 0.3f, 1.0f);
cube.TexturePtr = std::make_shared<Texture>("assets/crate.png");

// In render loop
scene.Render(renderer, shader, camera);

// Access by index
scene[0].ObjectTransform.Rotation.y += 0.01f;

// Iterate
for (auto& obj : scene)
{
    obj.ObjectTransform.Rotation.y += 0.01f;
}
```

> [!NOTE]
> **Scene Setup Location**: Scene creation and management currently happens in `Application::Run()`. When we later separate game logic from engine infrastructure, scene setup will move to an `OnCreate()` lifecycle method, keeping Application focused on game-specific code.

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Object not visible | `Active = false` | Set `obj.Active = true` |
| Texture on wrong object | State leak | Scene unbinds when no texture |
| Can't call Draw | Missing Renderer param | Scene::Render takes Renderer& |

---

## Milestone

**Scene Management Complete**

You have:
- `SceneObject` with mesh, transform, texture, roughness
- `Scene::Add()` returns reference
- `Scene::Render()` uses `renderer.Draw(mesh->GetVertexArray(), mesh->GetIndexBuffer(), shader)`
- Range-based for loop support

---

## What's Next

In **Chapter 16**, we'll add Dear ImGui for debug UI.

> **Next:** [Chapter 16: Dear ImGui](16_DearImGui.md)

> **Previous:** [Chapter 14: Camera System](14_CameraSystem.md)


