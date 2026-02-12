# Chapter 32: Depth & Stencil Testing

> **Part X: OpenGL Essentials**

## Overview

This chapter covers depth testing functions and stencil buffer operations — two fundamental OpenGL features that control which fragments are written to the framebuffer.

## Key Concepts

- **Depth Functions**: `GL_LESS`, `GL_LEQUAL`, `GL_ALWAYS`, etc.
- **Depth Mask**: Enabling/disabling depth writes with `glDepthMask`
- **Stencil Buffer**: Per-pixel integer buffer for masking and effects
- **Stencil Operations**: `glStencilFunc`, `glStencilOp`, `glStencilMask`
- **Face Culling**: `GL_BACK`, `GL_FRONT`, `glCullFace`

## What We Build

1. **Renderer State Management** — Methods on `Renderer` for depth, stencil, and culling
2. **Depth-Stencil Framebuffers** — `GL_DEPTH24_STENCIL8` combined format
3. **Stencil Outlines** — Highlight selected objects with a colored outline using the stencil buffer

## Stencil Outline Algorithm

```
1. Clear stencil buffer
2. Enable stencil test, always write 1
3. Render selected object (stencil = 1 where visible)
4. Set stencil to pass only where != 1
5. Render scaled-up object with flat-color shader
6. Disable stencil test
```

## Files Modified

| File | Changes |
|------|---------|
| `Renderer.h/cpp` | Depth, stencil, cull state methods |
| `Framebuffer.h/cpp` | `AttachDepthStencilTexture()` |
| `outline.shader` | Solid-color shader for outlines |
| `SandboxApp.cpp` | Stencil outline rendering pass |

## Key API

```cpp
renderer.EnableStencilTest();
renderer.SetStencilFunc(GL_ALWAYS, 1, 0xFF);
renderer.SetStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE);
// ... render object ...
renderer.SetStencilFunc(GL_NOTEQUAL, 1, 0xFF);
// ... render outline ...
renderer.DisableStencilTest();
```

---

*Next: [Chapter 33: Blending & Transparency](33_BlendingTransparency.md)*
