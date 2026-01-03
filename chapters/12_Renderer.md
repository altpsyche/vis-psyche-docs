\newpage

# Chapter 12: Renderer Class

Create a `Renderer` class to centralize drawing operations and OpenGL state management.

---

## What We're Building

| Method | Purpose |
|--------|---------|
| `Clear(float*)` | Clear screen with color |
| `ClearDepth()` | Clear depth buffer only |
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

namespace VizEngine
{
    class VizEngine_API Renderer
    {
    public:
        void Clear(float clearColor[4]);
        void ClearDepth();
        void Draw(const VertexArray& va, const IndexBuffer& ib, const Shader& shader) const;
    };
}
```

---

## Step 2: Create Renderer.cpp

**Create `VizEngine/src/VizEngine/OpenGL/Renderer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.cpp

#include "Renderer.h"
#include "Commons.h"
#include "VizEngine/Log.h"

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
- `Draw(VAO, IBO, Shader)` for draw calls
- Centralized OpenGL draw logic

---

## What's Next

In **Chapter 13**, we'll create `Transform` and `Mesh` classes.

> **Next:** [Chapter 13: Transform & Mesh](13_TransformAndMesh.md)

> **Previous:** [Chapter 11: Texture System](11_Textures.md)
