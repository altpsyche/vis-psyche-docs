# Chapter 33: Blending & Transparency

> **Part X: OpenGL Essentials**

## Overview

Alpha blending allows semi-transparent rendering. This chapter covers OpenGL blending modes, the order-dependent transparency problem, and a practical back-to-front sorting solution.

## Key Concepts

- **Blend Functions**: `GL_SRC_ALPHA`, `GL_ONE_MINUS_SRC_ALPHA`
- **Blend Equation**: `GL_FUNC_ADD`, `GL_FUNC_SUBTRACT`
- **Render Order**: Why transparent objects must be drawn after opaque ones
- **Back-to-Front Sorting**: Distance-based ordering for correct blending

## What We Build

1. **Blending API** on `Renderer` — `EnableBlending()`, `SetBlendFunc()`
2. **Alpha Uniform** in PBR shader — `u_Alpha` controls per-object opacity
3. **Two-Pass Rendering** — Opaque objects first, then sorted transparent objects

## Rendering Strategy

```
Pass 1: Render opaque objects (alpha == 1.0)
  - Normal depth test and depth write

Pass 2: Render transparent objects (alpha < 1.0)
  - Sort back-to-front by distance to camera
  - Enable blending (SRC_ALPHA, ONE_MINUS_SRC_ALPHA)
  - Disable depth writing (read-only depth test)
  - Render each transparent object
  - Re-enable depth writing
```

## Files Modified

| File | Changes |
|------|---------|
| `Renderer.h/cpp` | Blending enable/disable, blend func/equation |
| `PBRMaterial.h/cpp` | `SetAlpha()` / `GetAlpha()` |
| `defaultlit.shader` | `uniform float u_Alpha;` in fragment output |
| `SandboxApp.cpp` | Opaque/transparent split, back-to-front sorting |

## Key API

```cpp
renderer.EnableBlending();
renderer.SetBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
renderer.SetDepthMask(false);
// ... render transparent objects ...
renderer.SetDepthMask(true);
renderer.DisableBlending();
```

---

*Next: [Chapter 34: Normal Mapping](34_NormalMapping.md)*
