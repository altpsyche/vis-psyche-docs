\newpage

# Chapter 12: Renderer Class

Create a `Renderer` class to centralize drawing operations and OpenGL state management.

---

## What We're Building

| Method | Purpose |
|--------|---------|
| `Clear(float*)` | Clear screen with color |
| `ClearDepth()` | Clear depth buffer only |
| `SetViewport(x, y, w, h)` | Set OpenGL viewport |
| `PushViewport()` | Save current viewport to stack |
| `PopViewport()` | Restore viewport from stack |
| `Draw(VAO, IBO, Shader)` | Issue draw call |

---

## Step 1: Create Renderer.h

**Create `VizEngine/src/VizEngine/OpenGL/Renderer.h`:**

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

    private:
        std::vector<std::array<int, 4>> m_ViewportStack;
    };
}
```

> [!TIP]
> The viewport stack (`PushViewport`/`PopViewport`) is essential for multi-pass rendering. When rendering to a shadow map at a different resolution, save the current viewport, render to the shadow map, then restore—preventing hard-coded viewport restoration bugs.

---

## Step 2: Create Renderer.cpp

**Create `VizEngine/src/VizEngine/OpenGL/Renderer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.cpp

#include "Renderer.h"
#include "VizEngine/Log.h"
#include <glad/glad.h>

namespace VizEngine
{
    void Renderer::Clear(float clearColor[4])
    {
        glClearColor(clearColor[0], clearColor[1], clearColor[2], clearColor[3]);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    }

    void Renderer::ClearDepth()
    {
        glClear(GL_DEPTH_BUFFER_BIT);
    }

    void Renderer::SetViewport(int x, int y, int width, int height)
    {
        glViewport(x, y, width, height);
    }

    void Renderer::PushViewport()
    {
        std::array<int, 4> viewport;
        glGetIntegerv(GL_VIEWPORT, viewport.data());
        m_ViewportStack.push_back(viewport);
    }

    void Renderer::PopViewport()
    {
        if (m_ViewportStack.empty())
        {
            VP_CORE_WARN("Renderer::PopViewport() called with empty stack");
            return;
        }

        auto& vp = m_ViewportStack.back();
        glViewport(vp[0], vp[1], vp[2], vp[3]);
        m_ViewportStack.pop_back();
    }

    void Renderer::GetViewport(int& x, int& y, int& width, int& height) const
    {
        GLint viewport[4];
        glGetIntegerv(GL_VIEWPORT, viewport);
        x = viewport[0];
        y = viewport[1];
        width = viewport[2];
        height = viewport[3];
    }

    void Renderer::Draw(const VertexArray& va, const IndexBuffer& ib, const Shader& shader) const
    {
        shader.Bind();
        va.Bind();
        ib.Bind();
        glDrawElements(GL_TRIANGLES, ib.GetCount(), GL_UNSIGNED_INT, nullptr);
    }

}  // namespace VizEngine
```

---

## Step 3: Update CMakeLists.txt

```cmake
set(VIZENGINE_SOURCES
    # ... existing ...
    src/VizEngine/OpenGL/Renderer.cpp
)

set(VIZENGINE_HEADERS
    # ... existing ...
    src/VizEngine/OpenGL/Renderer.h
)
```

---

## Usage Example

```cpp
Renderer renderer;

// In render loop
float clearColor[4] = { 0.1f, 0.1f, 0.15f, 1.0f };
renderer.Clear(clearColor);

// Draw a mesh manually
shader.Bind();
shader.SetMatrix4fv("u_MVP", mvp);
renderer.Draw(mesh.GetVertexArray(), mesh.GetIndexBuffer(), shader);

// Or use Scene::Render which calls renderer.Draw internally
scene.Render(renderer, shader, camera);
```

> [!NOTE]
> The `Draw()` method takes a VertexArray and IndexBuffer separately. Mesh provides `GetVertexArray()` and `GetIndexBuffer()` accessors for this purpose.

---

## Why Separate Draw Method?

| Approach | Pros | Cons |
|----------|------|------|
| `glDrawElements` everywhere | Simple | Scattered OpenGL calls |
| `Renderer::Draw()` | Centralized, easy to extend | Extra abstraction |

Benefits of centralized Draw:
- Easy to add instanced drawing later
- Statistics tracking (draw call count)
- Debug rendering hooks

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Nothing renders | Shader not bound | `Draw()` binds shader - ensure uniforms set first |
| Objects overlap | Depth not cleared | Use `Clear()` which clears depth |
| Wrong indices | IBO mismatch | Ensure IBO matches VAO |

---

## Milestone

**Renderer Class Complete**

You have:
- `Clear(float[4])` for screen clearing
- `ClearDepth()` for depth-only clear
- `SetViewport()` for viewport control
- `PushViewport()`/`PopViewport()` for safe multi-pass rendering
- `Draw(VAO, IBO, Shader)` for draw calls
- Centralized OpenGL draw logic

---

## What's Next

In **Chapter 13**, we'll create `Transform` and `Mesh` classes.

> **Next:** [Chapter 13: Transform & Mesh](13_TransformAndMesh.md)

> **Previous:** [Chapter 11: Texture System](11_Textures.md)
