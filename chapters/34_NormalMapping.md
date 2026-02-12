\newpage

# Chapter 34: Normal Mapping

Add per-pixel surface detail without increasing geometry, using tangent-space normal maps and a per-vertex TBN matrix.

---

## Introduction

Up to this point, the lighting in our engine computes shading based on **per-vertex normals** that are interpolated across each triangle. This produces smooth, accurate lighting for large-scale curvature, but every surface appears perfectly flat at close range. A brick wall, a cobblestone road, or a weathered metal panel all look like smooth planes under our current lighting model.

In the real world, surfaces have tiny bumps, grooves, and ridges that scatter light in complex patterns. Modelling this micro-geometry with actual triangles would be prohibitively expensive -- a single brick wall could require millions of polygons.

**Normal mapping** solves this by encoding surface detail into a texture. Instead of storing colour values, a normal map stores **perturbed normal vectors** at every texel. During shading, the fragment shader reads the per-pixel normal from the map and uses it for lighting instead of the smooth interpolated vertex normal. The geometry stays simple; only the lighting response changes.

### Why Normal Mapping Matters

| Without Normal Map | With Normal Map |
|--------------------|-----------------|
| Flat surface, uniform lighting | Rich surface detail, realistic light interaction |
| Lighting varies only with mesh curvature | Lighting responds to per-pixel bumps and grooves |
| Smooth, plastic appearance | Convincing stone, metal, fabric, skin |

The cost is minimal: one extra texture sample and a matrix multiply per fragment. The visual improvement is dramatic.

### What You Will Build

By the end of this chapter, you will have:

1. Extended the `Vertex` struct with tangent and bitangent vectors
2. Implemented a `ComputeTangents` utility using the edge/deltaUV method with Gram-Schmidt orthogonalization
3. Updated every mesh factory method and the glTF loader to produce tangent frames
4. Modified the vertex shader to build a TBN matrix and the fragment shader to sample a normal map

---

## Theory

### Tangent Space

Every point on a textured surface lives in a local coordinate system called **tangent space** (also called **texture space**). This coordinate system is defined by three orthogonal axes:

| Axis | Name | Direction |
|------|------|-----------|
| **T** | Tangent | Along the U texture coordinate (horizontal in the texture) |
| **B** | Bitangent | Along the V texture coordinate (vertical in the texture) |
| **N** | Normal | Perpendicular to the surface (what you already have) |

```
         N (Normal)
         ^
         |
         |
         +-------> T (Tangent, along U)
        /
       /
      v
     B (Bitangent, along V)
```

Together, T, B, and N form an orthonormal basis at each vertex. This basis lets you transform vectors between tangent space and world space.

### How Normal Maps Work

A normal map is an RGB texture where each texel encodes a direction:

```
Normal Map Texel:  (R, G, B)  in [0, 1]
                      |
                      v  (remap)
Tangent-Space Normal: (X, Y, Z) in [-1, 1]

Formula:  normal = texel * 2.0 - 1.0
```

Most texels in a normal map are a bluish-purple colour `(0.5, 0.5, 1.0)`, which maps to the tangent-space vector `(0, 0, 1)` -- pointing straight "up" from the surface. Deviations from this colour encode surface perturbations: bumps, ridges, and scratches.

> [!NOTE]
> Normal maps are authored in **tangent space**, which is why they appear predominantly blue. The blue channel (Z) is almost always close to 1.0, meaning the normal points mostly away from the surface with small X and Y perturbations.

### The TBN Matrix

To use a tangent-space normal in world-space lighting calculations, you need a transformation matrix. The **TBN matrix** is a 3x3 matrix whose columns are the tangent (T), bitangent (B), and normal (N) vectors, all transformed to world space:

```
TBN = [ T.x  B.x  N.x ]
      [ T.y  B.y  N.y ]
      [ T.z  B.z  N.z ]
```

Or equivalently in GLSL: `mat3 TBN = mat3(T, B, N);`

Multiplying a tangent-space normal by this matrix transforms it into world space:

```glsl
vec3 worldNormal = normalize(TBN * tangentSpaceNormal);
```

### Computing Tangents from Geometry

The tangent and bitangent vectors must align with the UV mapping of the mesh. Given a triangle with vertices `P0`, `P1`, `P2` and texture coordinates `(u0, v0)`, `(u1, v1)`, `(u2, v2)`, the two edges of the triangle can be expressed in terms of T and B:

```
Edge1 = P1 - P0 = deltaUV1.x * T + deltaUV1.y * B
Edge2 = P2 - P0 = deltaUV2.x * T + deltaUV2.y * B
```

Where:
```
deltaUV1 = (u1 - u0, v1 - v0)
deltaUV2 = (u2 - u0, v2 - v0)
```

This gives us a system of equations. Solving for T and B using the inverse of the UV delta matrix:

```
          1
T = ------------- * ( deltaUV2.y * Edge1 - deltaUV1.y * Edge2 )
     determinant

          1
B = ------------- * ( -deltaUV2.x * Edge1 + deltaUV1.x * Edge2 )
     determinant

Where:  determinant = deltaUV1.x * deltaUV2.y - deltaUV2.x * deltaUV1.y
```

In matrix form:

```
[ T ]       1       [ deltaUV2.y  -deltaUV1.y ] [ Edge1 ]
[   ] = --------- * [                         ] [       ]
[ B ]    det(UV)    [ -deltaUV2.x  deltaUV1.x ] [ Edge2 ]
```

### Per-Vertex Accumulation and Gram-Schmidt Orthogonalization

Because vertices are shared between multiple triangles, each triangle contributes its computed tangent to the shared vertices. After accumulating, you must:

1. **Normalize** the accumulated tangent
2. **Orthogonalize** it against the vertex normal using Gram-Schmidt:

```
T' = normalize( T - N * dot(N, T) )
```

This subtracts the component of T that lies along N, ensuring T is perpendicular to N.

3. **Compute the bitangent** from the cross product to guarantee a perfectly orthogonal frame:

```
B = cross(N, T')
```

> [!IMPORTANT]
> Gram-Schmidt orthogonalization is essential. Without it, non-uniform UV mapping or mesh deformation can produce a non-orthogonal TBN matrix, leading to skewed or incorrect lighting.

---

## Architecture Overview

Normal mapping requires changes across the entire vertex pipeline:

```
Vertex Struct          SetupMesh Layout        Vertex Shader
 + Tangent (vec3)       + Push<float>(3)       + aTangent (location 4)
 + Bitangent (vec3)     + Push<float>(3)       + aBitangent (location 5)
       |                       |                      |
       v                       v                      v
  Factory Methods        GPU Layout             TBN Matrix
  + ComputeTangents()    Stride: 19 floats      mat3(T, B, N)
       |                                              |
       v                                              v
  glTF Loader                                  Fragment Shader
  + Load TANGENT attr                          + Sample normal map
  + Fallback compute                           + Transform via TBN
```

The vertex stride increases from **13 floats** (vec4 + vec3 + vec4 + vec2) to **19 floats** (adding two vec3 fields). This is a fundamental change that affects every mesh in the engine -- all factory methods and the model loader must produce valid tangent data, even when no normal map is applied.

> [!NOTE]
> Even meshes that do not use normal maps must include tangent and bitangent data in their vertex buffer because the vertex layout is shared across all meshes. The shader simply ignores the TBN matrix when `u_UseNormalMap` is `false`.

---

## Step 1: Extend the Vertex Struct

Add `Tangent` and `Bitangent` fields to the `Vertex` struct, initialized to zero by default.

```cpp
// VizEngine/src/VizEngine/Core/Mesh.h

struct Vertex
{
    glm::vec4 Position;
    glm::vec3 Normal;
    glm::vec4 Color;
    glm::vec2 TexCoords;
    glm::vec3 Tangent;    // Tangent vector for normal mapping (Chapter 34)
    glm::vec3 Bitangent;  // Bitangent vector for normal mapping (Chapter 34)

    Vertex() = default;

    // Constructor with normal
    Vertex(const glm::vec4& pos, const glm::vec3& norm, const glm::vec4& col, const glm::vec2& tex)
        : Position(pos), Normal(norm), Color(col), TexCoords(tex),
          Tangent(0.0f), Bitangent(0.0f) {}

    // Legacy constructor (defaults normal to up)
    Vertex(const glm::vec4& pos, const glm::vec4& col, const glm::vec2& tex)
        : Position(pos), Normal(0.0f, 1.0f, 0.0f), Color(col), TexCoords(tex),
          Tangent(0.0f), Bitangent(0.0f) {}
};
```

Both constructors initialize tangent and bitangent to zero. The actual values are computed later by `ComputeTangents()` or loaded from glTF data.

---

## Step 2: Update SetupMesh Layout

The vertex buffer layout must match the new struct. Add two `Push<float>(3)` calls for the tangent and bitangent attributes.

```cpp
// VizEngine/src/VizEngine/Core/Mesh.cpp -- SetupMesh()

void Mesh::SetupMesh(const float* vertexData, size_t vertexDataSize,
                     const unsigned int* indices, size_t indexCount)
{
    m_VertexArray = std::make_unique<VertexArray>();
    m_VertexBuffer = std::make_unique<VertexBuffer>(vertexData, static_cast<unsigned int>(vertexDataSize));

    VertexBufferLayout layout;
    layout.Push<float>(4); // Position (vec4)
    layout.Push<float>(3); // Normal (vec3)
    layout.Push<float>(4); // Color (vec4)
    layout.Push<float>(2); // TexCoords (vec2)
    layout.Push<float>(3); // Tangent (vec3)   - Chapter 34: Normal Mapping
    layout.Push<float>(3); // Bitangent (vec3) - Chapter 34: Normal Mapping

    m_VertexArray->LinkVertexBuffer(*m_VertexBuffer, layout);
    m_IndexBuffer = std::make_unique<IndexBuffer>(indices, static_cast<unsigned int>(indexCount));
}
```

Each `Push<float>(N)` call creates one vertex attribute at the next sequential location. The resulting layout is:

| Location | Attribute | Type | Components | Cumulative Offset (floats) |
|----------|-----------|------|------------|---------------------------|
| 0 | Position | vec4 | 4 | 0 |
| 1 | Normal | vec3 | 3 | 4 |
| 2 | Color | vec4 | 4 | 7 |
| 3 | TexCoords | vec2 | 2 | 11 |
| 4 | Tangent | vec3 | 3 | 13 |
| 5 | Bitangent | vec3 | 3 | 16 |

**Total stride: 19 floats = 76 bytes per vertex.**

---

## Step 3: Implement ComputeTangents

This is the core algorithm. It processes every triangle, computes tangent and bitangent vectors from the triangle edges and UV deltas, accumulates them per-vertex, then orthogonalizes.

```cpp
// VizEngine/src/VizEngine/Core/Mesh.cpp -- ComputeTangents()

static void ComputeTangents(std::vector<Vertex>& vertices,
                            const std::vector<unsigned int>& indices)
{
    // Zero out tangents/bitangents for accumulation
    for (auto& v : vertices)
    {
        v.Tangent = glm::vec3(0.0f);
        v.Bitangent = glm::vec3(0.0f);
    }

    // Process each triangle
    for (size_t i = 0; i + 2 < indices.size(); i += 3)
    {
        Vertex& v0 = vertices[indices[i + 0]];
        Vertex& v1 = vertices[indices[i + 1]];
        Vertex& v2 = vertices[indices[i + 2]];

        glm::vec3 edge1 = glm::vec3(v1.Position) - glm::vec3(v0.Position);
        glm::vec3 edge2 = glm::vec3(v2.Position) - glm::vec3(v0.Position);

        glm::vec2 deltaUV1 = v1.TexCoords - v0.TexCoords;
        glm::vec2 deltaUV2 = v2.TexCoords - v0.TexCoords;

        float det = deltaUV1.x * deltaUV2.y - deltaUV2.x * deltaUV1.y;
        if (std::abs(det) < 1e-8f)
            continue;  // Degenerate UV triangle, skip

        float invDet = 1.0f / det;

        glm::vec3 tangent;
        tangent.x = invDet * (deltaUV2.y * edge1.x - deltaUV1.y * edge2.x);
        tangent.y = invDet * (deltaUV2.y * edge1.y - deltaUV1.y * edge2.y);
        tangent.z = invDet * (deltaUV2.y * edge1.z - deltaUV1.y * edge2.z);

        glm::vec3 bitangent;
        bitangent.x = invDet * (-deltaUV2.x * edge1.x + deltaUV1.x * edge2.x);
        bitangent.y = invDet * (-deltaUV2.x * edge1.y + deltaUV1.x * edge2.y);
        bitangent.z = invDet * (-deltaUV2.x * edge1.z + deltaUV1.x * edge2.z);

        // Accumulate per-vertex (shared vertices get averaged)
        v0.Tangent += tangent;
        v1.Tangent += tangent;
        v2.Tangent += tangent;

        v0.Bitangent += bitangent;
        v1.Bitangent += bitangent;
        v2.Bitangent += bitangent;
    }

    // Normalize and orthogonalize (Gram-Schmidt)
    for (auto& v : vertices)
    {
        const glm::vec3& n = v.Normal;
        glm::vec3& t = v.Tangent;

        if (glm::length(t) < 1e-6f)
        {
            // Fallback: generate tangent from normal
            if (std::abs(n.x) < 0.9f)
                t = glm::normalize(glm::cross(n, glm::vec3(1.0f, 0.0f, 0.0f)));
            else
                t = glm::normalize(glm::cross(n, glm::vec3(0.0f, 1.0f, 0.0f)));
        }

        // Gram-Schmidt: make tangent perpendicular to normal
        t = glm::normalize(t - n * glm::dot(n, t));

        // Compute bitangent from cross product (ensures orthogonal frame)
        v.Bitangent = glm::cross(n, t);
    }
}
```

### Algorithm Walkthrough

**Phase 1 -- Per-Triangle Tangent Computation:**

For each triangle, the algorithm:
1. Computes two edge vectors (`edge1`, `edge2`) from the triangle's positions
2. Computes the corresponding UV deltas (`deltaUV1`, `deltaUV2`)
3. Solves the 2x2 linear system for T and B using the inverse determinant
4. Skips degenerate triangles where the UV determinant is near zero (overlapping or collapsed UVs)
5. Accumulates the tangent and bitangent into all three vertices of the triangle

**Phase 2 -- Gram-Schmidt Orthogonalization:**

For each vertex, the algorithm:
1. Checks if the accumulated tangent is valid (non-zero length). If not, it generates a fallback tangent by crossing the normal with a reference axis
2. Subtracts the component of T along N (`t - n * dot(n, t)`) and normalizes
3. Recomputes the bitangent as `cross(N, T)` to guarantee an orthogonal frame

> [!TIP]
> The fallback tangent generation handles edge cases like vertices with degenerate UVs (all triangles sharing the vertex were skipped). By crossing the normal with a reference axis, we always produce a valid tangent frame, even if it does not perfectly align with the texture.

---

## Step 4: Update Factory Methods

Every factory method must call `ComputeTangents` before constructing the mesh. Here is how each one is updated:

### CreatePyramid

```cpp
// VizEngine/src/VizEngine/Core/Mesh.cpp -- CreatePyramid() (end of function)

    // ... vertices and indices defined above ...

    ComputeTangents(vertices, indices);
    return std::make_unique<Mesh>(vertices, indices);
}
```

### CreateCube

```cpp
// VizEngine/src/VizEngine/Core/Mesh.cpp -- CreateCube() (end of function)

    // ... 24 vertices (4 per face) and 36 indices defined above ...

    ComputeTangents(vertices, indices);
    return std::make_unique<Mesh>(vertices, indices);
}
```

### CreatePlane

```cpp
// VizEngine/src/VizEngine/Core/Mesh.cpp -- CreatePlane() (end of function)

    // ... 4 vertices and 6 indices defined above ...

    ComputeTangents(vertices, indices);
    return std::make_unique<Mesh>(vertices, indices);
}
```

### CreateSphere

```cpp
// VizEngine/src/VizEngine/Core/Mesh.cpp -- CreateSphere() (end of function)

    // ... UV sphere vertices and indices generated above ...

    ComputeTangents(vertices, indices);
    return std::make_unique<Mesh>(vertices, indices);
}
```

The pattern is the same for every factory method: define geometry as before, call `ComputeTangents`, then construct the `Mesh`. Tangent computation runs once at mesh creation time, not every frame.

---

## Step 5: Update the glTF Loader

The glTF format supports an optional `TANGENT` attribute. When present, it is stored as a **vec4** where `xyz` is the tangent direction and `w` is the handedness sign (+1 or -1) used to reconstruct the bitangent. When absent, we compute tangents ourselves using the same algorithm as the factory methods.

### Loading the TANGENT Attribute

```cpp
// VizEngine/src/VizEngine/Core/Model.cpp -- LoadMeshes(), after TEXCOORD_0 loading

// Load tangent data (Chapter 34: Normal Mapping)
// glTF stores TANGENT as vec4 (xyz = tangent direction, w = handedness sign)
const float* tangents = nullptr;
if (primitive.attributes.find("TANGENT") != primitive.attributes.end())
{
    int tanAccessorIndex = primitive.attributes.at("TANGENT");
    if (tanAccessorIndex >= 0 && tanAccessorIndex < static_cast<int>(gltfModel.accessors.size()))
    {
        const auto& tanAccessor = gltfModel.accessors[tanAccessorIndex];
        if (ValidateAttributeBuffer(gltfModel, tanAccessor, vertexCount, 4, "Tangent"))
        {
            tangents = GetBufferData<float>(gltfModel, tanAccessor);
        }
    }
    else
    {
        VP_CORE_WARN("TANGENT accessor index {} out of range", tanAccessorIndex);
    }
}
```

### Applying Tangent Data Per-Vertex

When tangent data is available from glTF, the bitangent is reconstructed from the cross product of the normal and tangent, scaled by the handedness sign:

```cpp
// VizEngine/src/VizEngine/Core/Model.cpp -- inside per-vertex loop

// Chapter 34: Load tangent from glTF (vec4: xyz=tangent, w=handedness)
if (tangents)
{
    v.Tangent = glm::vec3(
        tangents[i * 4 + 0],
        tangents[i * 4 + 1],
        tangents[i * 4 + 2]
    );
    float handedness = tangents[i * 4 + 3];  // +1 or -1
    v.Bitangent = glm::cross(v.Normal, v.Tangent) * handedness;
}
```

> [!NOTE]
> The glTF specification stores tangents as vec4 rather than storing a separate bitangent. The `w` component encodes **handedness** -- whether the UV coordinate system is right-handed (+1) or left-handed (-1). This is more compact (4 floats instead of 6) and avoids ambiguity in mirrored UV islands.

### Fallback: Compute Tangents When Not Provided

Many glTF files do not include pre-computed tangent data. In that case, we apply the same edge/deltaUV algorithm used by the factory methods:

```cpp
// VizEngine/src/VizEngine/Core/Model.cpp -- after index loading, before mesh creation

// Chapter 34: Compute tangents if not provided by glTF
if (!tangents && !vertices.empty() && !indices.empty())
{
    // Use the same tangent computation algorithm as Mesh factory methods
    for (auto& v : vertices)
    {
        v.Tangent = glm::vec3(0.0f);
        v.Bitangent = glm::vec3(0.0f);
    }

    for (size_t ti = 0; ti + 2 < indices.size(); ti += 3)
    {
        Vertex& v0 = vertices[indices[ti + 0]];
        Vertex& v1 = vertices[indices[ti + 1]];
        Vertex& v2 = vertices[indices[ti + 2]];

        glm::vec3 edge1 = glm::vec3(v1.Position) - glm::vec3(v0.Position);
        glm::vec3 edge2 = glm::vec3(v2.Position) - glm::vec3(v0.Position);
        glm::vec2 dUV1 = v1.TexCoords - v0.TexCoords;
        glm::vec2 dUV2 = v2.TexCoords - v0.TexCoords;

        float det = dUV1.x * dUV2.y - dUV2.x * dUV1.y;
        if (std::abs(det) < 1e-8f) continue;
        float invDet = 1.0f / det;

        glm::vec3 tan;
        tan.x = invDet * (dUV2.y * edge1.x - dUV1.y * edge2.x);
        tan.y = invDet * (dUV2.y * edge1.y - dUV1.y * edge2.y);
        tan.z = invDet * (dUV2.y * edge1.z - dUV1.y * edge2.z);

        v0.Tangent += tan; v1.Tangent += tan; v2.Tangent += tan;
    }

    for (auto& v : vertices)
    {
        const glm::vec3& n = v.Normal;
        glm::vec3& t = v.Tangent;
        if (glm::length(t) < 1e-6f)
        {
            t = (std::abs(n.x) < 0.9f)
                ? glm::normalize(glm::cross(n, glm::vec3(1, 0, 0)))
                : glm::normalize(glm::cross(n, glm::vec3(0, 1, 0)));
        }
        t = glm::normalize(t - n * glm::dot(n, t));
        v.Bitangent = glm::cross(n, t);
    }
}
```

> [!TIP]
> The fallback tangent computation in the glTF loader only computes tangents (not bitangents) during the per-triangle pass. The bitangent is derived from `cross(N, T)` during orthogonalization, which is sufficient and avoids accumulating a second vector.

---

## Step 6: Update the Vertex Shader

The vertex shader declares two new input attributes (`aTangent`, `aBitangent`) and constructs the TBN matrix by transforming all three basis vectors through the normal matrix.

```glsl
// VizEngine/src/resources/shaders/defaultlit.shader -- vertex shader

#shader vertex
#version 460 core

// Match existing Mesh vertex layout (see Mesh.cpp SetupMesh)
layout(location = 0) in vec4 aPos;       // Position (vec4)
layout(location = 1) in vec3 aNormal;    // Normal (vec3)
layout(location = 2) in vec4 aColor;     // Color (vec4) - unused in PBR but must be declared
layout(location = 3) in vec2 aTexCoords; // TexCoords (vec2)
layout(location = 4) in vec3 aTangent;   // Tangent (vec3) - Chapter 34: Normal Mapping
layout(location = 5) in vec3 aBitangent; // Bitangent (vec3) - Chapter 34: Normal Mapping

out vec3 v_WorldPos;
out vec3 v_Normal;
out vec2 v_TexCoords;
out vec4 v_FragPosLightSpace;  // Position in light space for shadow mapping
out mat3 v_TBN;                // Tangent-Bitangent-Normal matrix (Chapter 34)

uniform mat4 u_Model;
uniform mat3 u_NormalMatrix;      // Pre-computed: transpose(inverse(mat3(model)))
uniform mat4 u_View;
uniform mat4 u_Projection;
uniform mat4 u_LightSpaceMatrix;  // Light's projection * view

void main()
{
    // Transform position to world space
    vec4 worldPos = u_Model * aPos;
    v_WorldPos = worldPos.xyz;

    // Transform normal to world space (use normal matrix for non-uniform scaling)
    v_Normal = u_NormalMatrix * aNormal;

    // Pass through texture coordinates
    v_TexCoords = aTexCoords;

    // Transform position to light space for shadow mapping
    v_FragPosLightSpace = u_LightSpaceMatrix * worldPos;

    // Build TBN matrix for normal mapping (Chapter 34)
    vec3 T = normalize(u_NormalMatrix * aTangent);
    vec3 B = normalize(u_NormalMatrix * aBitangent);
    vec3 N = normalize(u_NormalMatrix * aNormal);
    v_TBN = mat3(T, B, N);

    gl_Position = u_Projection * u_View * vec4(v_WorldPos, 1.0);
}
```

### Why Use u_NormalMatrix?

The **normal matrix** (`transpose(inverse(mat3(model)))`) correctly transforms direction vectors under non-uniform scaling. If you used the model matrix directly, a scaled object would have skewed normals (and therefore skewed tangent frames). By applying the normal matrix to T, B, and N uniformly, the TBN matrix remains valid regardless of the object's scale.

> [!IMPORTANT]
> All three TBN vectors must be transformed by the same matrix (`u_NormalMatrix`) and individually normalized after transformation. The interpolation across the triangle surface can denormalize them, but the per-fragment `normalize()` on the final result handles that.

---

## Step 7: Update the Fragment Shader

The fragment shader declares the normal map sampler and a boolean toggle. When enabled, it samples the normal map, remaps from `[0,1]` to `[-1,1]`, and transforms the result to world space using the interpolated TBN matrix.

```glsl
// VizEngine/src/resources/shaders/defaultlit.shader -- fragment shader (relevant sections)

in mat3 v_TBN;  // Tangent-Bitangent-Normal matrix (Chapter 34)

// Normal map (Chapter 34: Normal Mapping)
uniform sampler2D u_NormalTexture;
uniform bool u_UseNormalMap;

void main()
{
    // Normalize interpolated vectors
    vec3 N = normalize(v_Normal);

    // Chapter 34: Normal Mapping -- perturb normal using tangent-space map
    if (u_UseNormalMap)
    {
        vec3 normalMap = texture(u_NormalTexture, v_TexCoords).rgb;
        normalMap = normalMap * 2.0 - 1.0;  // [0,1] -> [-1,1] (tangent space)
        N = normalize(v_TBN * normalMap);    // Transform to world space via TBN
    }

    vec3 V = normalize(u_ViewPos - v_WorldPos);

    // ... rest of PBR lighting uses N as usual ...
}
```

### The Normal Map Pipeline in Detail

```
1. Sample texture:   normalMap = texture(u_NormalTexture, uv).rgb
                     Result: (0.5, 0.5, 1.0) for a flat surface

2. Remap to [-1,1]:  normalMap = normalMap * 2.0 - 1.0
                     Result: (0.0, 0.0, 1.0) -- pointing along tangent-space Z

3. Transform:        N = normalize(v_TBN * normalMap)
                     Result: world-space normal, perturbed by the map

4. Use in lighting:  All subsequent dot(N, L), dot(N, V), etc. use
                     the perturbed normal for per-pixel detail
```

When `u_UseNormalMap` is `false`, the shader falls back to the interpolated vertex normal, and the TBN matrix is simply unused.

---

## Step 8: Material Integration

The shader now has `u_NormalTexture` and `u_UseNormalMap` uniforms, but we need the material system to bind them. Three pieces connect the pipeline.

### Material Struct (Material.h)

The `Material` struct (used by the glTF loader) already has a `NormalTexture` field:

```cpp
// VizEngine/src/VizEngine/Core/Material.h
struct Material
{
    // ... existing fields ...

    // Textures (nullptr if not present)
    std::shared_ptr<Texture> NormalTexture = nullptr;

    // Helper
    bool HasNormalTexture() const { return NormalTexture != nullptr; }
};
```

### glTF Normal Texture Loading (Model.cpp)

The glTF loader extracts the normal texture from the material definition:

```cpp
// In Model::LoadMaterials() -- VizEngine/src/VizEngine/Core/Model.cpp
if (gltfMat.normalTexture.index >= 0)
{
    material.NormalTexture = LoadTexture(gltfModel, gltfMat.normalTexture.index);
}
```

### PBRMaterial Binding (PBRMaterial.cpp)

`PBRMaterial::SetNormalTexture()` binds the texture to the correct slot and enables the shader flag:

```cpp
// VizEngine/src/VizEngine/Renderer/PBRMaterial.cpp
void PBRMaterial::SetNormalTexture(std::shared_ptr<Texture> texture)
{
    if (texture)
    {
        SetTexture("u_NormalTexture", texture, TextureSlots::Normal);
        m_HasNormalTexture = true;
        SetBool("u_UseNormalMap", true);
    }
    else
    {
        m_HasNormalTexture = false;
        SetBool("u_UseNormalMap", false);
    }
}
```

When a normal texture is assigned, `u_UseNormalMap` is automatically set to `true` and the texture is bound to `TextureSlots::Normal` (slot 1). When cleared (passed `nullptr`), the flag is set to `false` and the shader falls back to vertex normals.

> [!NOTE]
> The PBR material constructor sets `u_UseNormalMap` to `false` by default, so normal mapping is opt-in. Models loaded from glTF that include normal textures will have them enabled automatically via `SetNormalTexture()`.

> [!TIP]
> You can control the "strength" of normal mapping by blending between the flat tangent-space normal `(0,0,1)` and the sampled value before transforming:
> ```glsl
> vec3 normalMap = texture(u_NormalTexture, v_TexCoords).rgb * 2.0 - 1.0;
> normalMap = mix(vec3(0.0, 0.0, 1.0), normalMap, u_NormalStrength);
> N = normalize(v_TBN * normalMap);
> ```
> This is not implemented in the current shader but is a common extension.

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Lighting looks unchanged with normal map** | `u_UseNormalMap` not set to `true` | Ensure the material binding code sets the uniform when a normal texture is present |
| **Surface appears completely wrong/inverted** | Normal map stored in DirectX convention (Y-flipped) | Negate the green channel: `normalMap.y = -normalMap.y` before transforming |
| **Black or dark patches on mesh** | TBN matrix has zero-length vectors | Check that `ComputeTangents` is called; verify UVs are not degenerate |
| **Seams visible at UV island boundaries** | Tangent discontinuity at UV seams | This is expected; average tangents at shared vertices or use MikkTSpace for production |
| **Normal map has no effect on glTF model** | Model lacks UV coordinates | Normal maps require valid texture coordinates; check `TEXCOORD_0` attribute |
| **Shading flickers or shimmers** | Non-orthogonal TBN from skipped Gram-Schmidt | Ensure orthogonalization runs for every vertex, including fallback cases |
| **Crash in ComputeTangents** | Empty vertex or index arrays | The function guards with `i + 2 < indices.size()` and length checks, but verify mesh data is valid before calling |
| **glTF model tangents look wrong** | Handedness sign ignored | Multiply bitangent by `tangents[i * 4 + 3]` (the w component) |

---

## Best Practices

### 1. Normal Map Authoring

Normal maps should be:
- **Tangent-space** (not object-space or world-space) for maximum portability
- **Stored in linear colour space** (no sRGB gamma correction on load)
- **OpenGL convention** by default (Y-up). If using DirectX-convention maps, negate the green channel

> [!IMPORTANT]
> When loading normal map textures, make sure the texture loader does **not** apply sRGB-to-linear conversion. Normal maps store direction data, not colour data. Loading them as sRGB will distort the encoded normals and produce incorrect lighting.

### 2. Tangent Computation Alternatives

The edge/deltaUV method used in this chapter is straightforward and correct for most cases. For production engines, consider:

| Method | Pros | Cons |
|--------|------|------|
| **Edge/DeltaUV (this chapter)** | Simple, no dependencies | Can produce seam artifacts on complex UV layouts |
| **MikkTSpace** | Industry standard, matches most DCC tools | Requires external library, more complex integration |
| **Pre-computed in DCC tool** | Best quality, artist-controlled | Requires export pipeline support |

### 3. Performance Considerations

- **Vertex size increase**: 13 to 19 floats per vertex (46% more vertex data). For vertex-bound scenes, this matters
- **Fragment cost**: One texture sample + one matrix-vector multiply per fragment when normal mapping is active
- **Memory**: One additional texture per material that uses normal mapping

For most scenes, the fragment cost is negligible compared to the visual improvement.

### 4. When to Use Normal Maps

| Use Case | Recommendation |
|----------|---------------|
| Brick, stone, concrete | Excellent -- high-frequency detail without geometry |
| Metal panels, rivets | Excellent -- sharp detail responds well |
| Organic surfaces (skin, bark) | Good -- subtle detail improves realism |
| Large-scale curvature | Poor -- use actual geometry instead |
| Distant objects | Unnecessary -- detail not visible; save texture memory |

---

## Milestone

**Chapter 34 Complete -- Normal Mapping**

You have:

- Extended the `Vertex` struct with `Tangent` and `Bitangent` vectors (vec3 each)
- Updated the vertex buffer layout from 13 to 19 floats per vertex
- Implemented `ComputeTangents()` with edge/deltaUV computation and Gram-Schmidt orthogonalization
- Updated all four factory methods (`CreatePyramid`, `CreateCube`, `CreatePlane`, `CreateSphere`) to compute tangent frames
- Updated the glTF loader to read the `TANGENT` attribute (vec4 with handedness) or fall back to automatic computation
- Built the TBN matrix in the vertex shader from transformed tangent, bitangent, and normal vectors
- Sampled and applied normal maps in the fragment shader using the `[0,1]` to `[-1,1]` remap and TBN transformation
- Connected the material pipeline: `Material.NormalTexture` (glTF loader) → `PBRMaterial::SetNormalTexture()` (binding) → `u_NormalTexture` / `u_UseNormalMap` (shader)

Your engine now supports **per-pixel surface detail** through normal mapping. Flat geometry can exhibit the appearance of complex surface structure -- bricks, scratches, fabric weave, pores -- all without adding a single triangle. This technique is foundational to modern real-time rendering and works seamlessly with the PBR lighting pipeline from earlier chapters.

---

## What's Next

In **Chapter 35: Instancing**, we will render many copies of the same mesh in a single draw call using hardware instancing, dramatically reducing draw call overhead for scenes with repeated geometry.

> **Previous:** [Chapter 33: Blending and Transparency](33_BlendingTransparency.md) | **Next:** [Chapter 35: Instancing](35_Instancing.md)
