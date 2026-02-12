# Chapter 35: Instancing

> **Part X: OpenGL Essentials**

## Overview

GPU instancing renders many copies of the same mesh in a single draw call, dramatically reducing CPU overhead. This chapter implements instanced rendering with per-instance transform matrices passed through vertex attributes.

## Key Concepts

- **`glDrawElementsInstanced`**: Renders multiple instances in one call
- **`glVertexAttribDivisor`**: Controls attribute advancement (per-vertex vs per-instance)
- **Instance Buffer**: A VBO containing per-instance data (transforms, colors, etc.)
- **mat4 as Vertex Attributes**: A 4x4 matrix requires 4 consecutive vec4 attribute slots

## What We Build

1. **`DrawInstanced()`** on `Renderer` — Calls `glDrawElementsInstanced`
2. **`LinkInstanceBuffer()`** on `VertexArray` — Sets up per-instance attributes with divisor
3. **Instanced Shader** — Reads per-instance model matrix from vertex attributes
4. **Grid Demo** — 100 cubes rendered in a single draw call

## Instance Attribute Setup

```cpp
// mat4 = 4 x vec4 at locations 6-9
VertexBufferLayout instanceLayout;
instanceLayout.Push<float>(4);  // Column 0 → location 6
instanceLayout.Push<float>(4);  // Column 1 → location 7
instanceLayout.Push<float>(4);  // Column 2 → location 8
instanceLayout.Push<float>(4);  // Column 3 → location 9

vao.LinkInstanceBuffer(instanceVBO, instanceLayout, 6);
// Internally calls glVertexAttribDivisor(attrib, 1) for each
```

## Instanced Shader (Vertex)

```glsl
// Per-instance model matrix (4 vec4 attributes)
layout(location = 6) in vec4 aInstanceModel0;
layout(location = 7) in vec4 aInstanceModel1;
layout(location = 8) in vec4 aInstanceModel2;
layout(location = 9) in vec4 aInstanceModel3;

void main() {
    mat4 model = mat4(aInstanceModel0, aInstanceModel1,
                      aInstanceModel2, aInstanceModel3);
    gl_Position = u_Projection * u_View * model * aPos;
}
```

## Files Modified

| File | Changes |
|------|---------|
| `Renderer.h/cpp` | `DrawInstanced()` |
| `VertexArray.h/cpp` | `LinkInstanceBuffer()` with `glVertexAttribDivisor` |
| `instanced.shader` | Per-instance transform + basic lighting |
| `SandboxApp.cpp` | Instance VBO setup, grid demo rendering |

---

*Next: [Chapter 36: PBR Theory](36_PBRTheory.md)*
