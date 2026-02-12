# Chapter 34: Normal Mapping

> **Part X: OpenGL Essentials**

## Overview

Normal mapping adds surface detail (bumps, scratches, grooves) without adding geometry. This chapter extends the vertex format with tangent vectors and implements tangent-space normal mapping in the PBR shader.

## Key Concepts

- **Tangent Space**: A per-vertex coordinate system (T, B, N) for interpreting normal maps
- **TBN Matrix**: Transforms normal map vectors from tangent space to world space
- **Tangent Computation**: Derived from triangle edges and UV deltas
- **Gram-Schmidt Orthogonalization**: Ensures T, B, N are orthonormal

## What We Build

1. **Extended Vertex Format** — Add `Tangent` and `Bitangent` to `Vertex` struct
2. **Tangent Computation** — `ComputeTangents()` utility function
3. **TBN Matrix in Shader** — Vertex shader builds TBN, fragment shader transforms normals
4. **glTF Tangent Loading** — Load TANGENT attribute or compute if missing

## Vertex Format (After)

```cpp
struct Vertex {
    glm::vec4 Position;   // location 0
    glm::vec3 Normal;     // location 1
    glm::vec4 Color;      // location 2
    glm::vec2 TexCoords;  // location 3
    glm::vec3 Tangent;    // location 4 (NEW)
    glm::vec3 Bitangent;  // location 5 (NEW)
};
```

## Shader Integration

```glsl
// Vertex shader
vec3 T = normalize(u_NormalMatrix * aTangent);
vec3 B = normalize(u_NormalMatrix * aBitangent);
vec3 N = normalize(u_NormalMatrix * aNormal);
v_TBN = mat3(T, B, N);

// Fragment shader
if (u_UseNormalMap) {
    vec3 normalMap = texture(u_NormalTexture, v_TexCoords).rgb * 2.0 - 1.0;
    N = normalize(v_TBN * normalMap);
}
```

## Files Modified

| File | Changes |
|------|---------|
| `Mesh.h` | Tangent/Bitangent fields in Vertex struct |
| `Mesh.cpp` | `ComputeTangents()`, updated layout and factory methods |
| `Model.cpp` | glTF TANGENT attribute loading, fallback computation |
| `defaultlit.shader` | TBN matrix, normal map sampling |

---

*Next: [Chapter 35: Instancing](35_Instancing.md)*
