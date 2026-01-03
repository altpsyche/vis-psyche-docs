\newpage

# Chapter 15: Lighting (Blinn-Phong)

## The Problem: Flat Objects

Look at our scene before lighting:

![Flat Objects](images/13-flat-objects.png)

Without lighting, a cube looks like a hexagon. A sphere looks like a circle. We lose all sense of 3D form.

---

## How Real Lighting Works

In the real world, we see objects because light bounces off them into our eyes:

1. **Light source** emits photons
2. **Surface** absorbs some, reflects others
3. **Eye** receives reflected light

We can't simulate every photon (that's ray tracing). Instead, we use mathematical approximations.

---

## The Rendering Equation (Conceptual)

All lighting models approximate this fundamental equation from computer graphics research:

```
L_o = L_e + ∫ f_r(ω_i, ω_o) · L_i(ω_i) · cos(θ_i) dω_i
```

**In plain English:** Light leaving a point = emitted light + (all incoming light × how the surface reflects it).

### What Blinn-Phong Approximates

| Term | Blinn-Phong Equivalent |
|------|------------------------|
| `L_e` (emission) | Not included (we skip this) |
| `f_r` (BRDF) | Ambient + Diffuse + Specular |
| `cos(θ)` | `dot(N, L)` in our shader |
| `∫ dω` | We only consider one light direction |

> [!NOTE]
> **Future:** PBR lighting (planned Advanced Lighting chapter) uses more physically accurate BRDF models like Cook-Torrance.

---

## The Blinn-Phong Lighting Model

The Blinn-Phong model breaks lighting into three components:

![Blinn-Phong Components](images/13-blinn-phong-components.png)

**Final Color = Ambient + Diffuse + Specular**

### Ambient Light

The "cheat" component. In reality, light bounces many times (global illumination). We approximate this with a constant:

```cpp
vec3 ambient = lightAmbient * objectColor;
```

Without ambient, surfaces facing away from the light would be pure black.

### Diffuse Light (Lambert)

Surfaces facing the light are brighter. This is **Lambert's Cosine Law**:

![Lambert's Diffuse](images/13-lambert-diffuse.png)

The math uses the **dot product** of the surface normal and light direction:

```glsl
float diff = max(dot(normal, lightDirection), 0.0);
vec3 diffuse = lightDiffuse * diff * objectColor;
```

- `dot(N, L) = 1.0` when surface faces light directly → full brightness
- `dot(N, L) = 0.0` when surface is perpendicular → no light
- `dot(N, L) < 0.0` when surface faces away → we clamp to 0

### Specular Light (Blinn-Phong)

Shiny highlights. Blinn-Phong uses a **half vector** between the light and view directions:

![Half Vector](images/13-half-vector.png)

```glsl
vec3 viewDir = normalize(cameraPos - fragmentPos);
vec3 halfDir = normalize(lightDir + viewDir);
float spec = pow(max(dot(normal, halfDir), 0.0), shininess);
vec3 specular = lightSpecular * spec;
```

**Why Blinn-Phong over Phong?**
- Faster: No `reflect()` calculation needed
- Better: More realistic highlights at grazing angles
- Industry standard: Used in most real-time renderers

The `shininess` exponent controls highlight size:
- Low (8-16): Matte, wide highlights
- High (64-256): Glossy, tight highlights

### Roughness vs Shininess

**Why use Roughness?**

Traditional Blinn-Phong uses a `shininess` exponent (8-256), but modern engines use **Roughness** (0-1) because:
- More intuitive: 0 = smooth/glossy, 1 = rough/matte
- Artist-friendly: Easy to understand without math
- PBR-ready: Roughness is standard in Physically Based Rendering (future chapter)

**The Conversion:**

| Roughness | Shininess | Appearance |
|-----------|-----------|------------|
| 0.0 | 256 | Mirror-like, tight highlight |
| 0.25 | 194 | Glossy plastic |
| 0.5 | 132 | Satin finish |
| 0.75 | 70 | Slightly rough |
| 1.0 | 8 | Completely matte, wide highlight |

**Shader Formula:**
```glsl
float shininess = mix(256.0, 8.0, u_Roughness);
```

This linearly interpolates: `roughness=0` → `shininess=256`, `roughness=1` → `shininess=8`.

> [!TIP]
> **Forward Compatibility:** We use Roughness now because it's the standard in PBR (Physically Based Rendering). When we implement full PBR in a future **Advanced Lighting** chapter, the same roughness values will work directly with the new shaders.

---

## Normals: The Key to Lighting

A **normal** is a vector perpendicular to a surface. Lighting calculations depend entirely on normals.

![Surface Normal](images/13-surface-normal.png)

### Adding Normals to Vertices

We need to add a `Normal` field to the `Vertex` struct (from [Chapter 12: Transform & Mesh](12_TransformAndMesh.md)):

> [!NOTE]
> **Vertex Struct Recap:** This is the same `Vertex` struct from [Chapter 12](12_TransformAndMesh.md). The `Normal` field was already included in anticipation of lighting. If you're building along, you should already have this.

```cpp
// Update Vertex in VizEngine/Core/Mesh.h
struct Vertex
{
    glm::vec4 Position;
    glm::vec3 Normal;     // ADD THIS for lighting
    glm::vec4 Color;
    glm::vec2 TexCoords;
};
```

Update the vertex buffer layout to match:

```cpp
layout.Push<float>(4); // Position
layout.Push<float>(3); // Normal (NEW)
layout.Push<float>(4); // Color
layout.Push<float>(2); // TexCoords
```

### Face Normals vs Smooth Normals

For **flat shading** (our current approach), each face has its own normal. For **smooth shading**, vertices share averaged normals:

![Face vs Smooth Normals](images/13-face-vs-smooth-normals.png)

We use flat shading because it's simpler and works well for hard-edged geometry like cubes.

---

## The DirectionalLight Class

A directional light represents a light infinitely far away (like the sun). All rays are parallel:

```cpp
struct DirectionalLight
{
    glm::vec3 Direction;  // Where light points
    glm::vec3 Ambient;    // Base illumination
    glm::vec3 Diffuse;    // Main light color
    glm::vec3 Specular;   // Highlight color
};
```

Usage:
```cpp
DirectionalLight light;
light.Direction = glm::vec3(-0.5f, -1.0f, -0.3f);  // Coming from upper-right
light.Ambient = glm::vec3(0.2f);   // 20% base
light.Diffuse = glm::vec3(0.8f);   // 80% main
light.Specular = glm::vec3(1.0f);  // Full highlights
```

---

## The Lit Shader

### Vertex Shader

```glsl
#version 460 core

layout (location = 0) in vec4 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec4 aColor;
layout (location = 3) in vec2 aTexCoords;

out vec3 v_FragPos;   // Position in world space
out vec3 v_Normal;    // Normal in world space
out vec4 v_Color;
out vec2 v_TexCoords;

uniform mat4 u_Model;
uniform mat4 u_MVP;

void main()
{
    // Position in world space (for lighting math)
    v_FragPos = vec3(u_Model * aPos);
    
    // Transform normal to world space
    v_Normal = mat3(transpose(inverse(u_Model))) * aNormal;
    
    v_Color = aColor;
    v_TexCoords = aTexCoords;
    
    gl_Position = u_MVP * aPos;
}
```

**Why `transpose(inverse(u_Model))`?**

If the model has non-uniform scaling, using just the model matrix would skew the normals. The inverse-transpose handles this correctly.

### Fragment Shader

```glsl
#version 460 core

out vec4 FragColor;

in vec3 v_FragPos;
in vec3 v_Normal;
in vec4 v_Color;
in vec2 v_TexCoords;

// Light
uniform vec3 u_LightDirection;
uniform vec3 u_LightAmbient;
uniform vec3 u_LightDiffuse;
uniform vec3 u_LightSpecular;

// Camera
uniform vec3 u_ViewPos;

// Material
uniform vec4 u_ObjectColor;
uniform sampler2D u_MainTex;
uniform float u_Roughness;  // 0 = shiny, 1 = matte

void main()
{
    vec4 texColor = texture(u_MainTex, v_TexCoords);
    vec3 baseColor = texColor.rgb * v_Color.rgb * u_ObjectColor.rgb;
    
    vec3 norm = normalize(v_Normal);
    vec3 lightDir = normalize(-u_LightDirection);
    
    // Ambient
    vec3 ambient = u_LightAmbient * baseColor;
    
    // Diffuse
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = u_LightDiffuse * diff * baseColor;
    
	// Specular (Blinn-Phong)
	vec3 viewDir = normalize(u_ViewPos - v_FragPos);
	vec3 halfDir = normalize(lightDir + viewDir);
	// Convert roughness to Blinn-Phong exponent
	float shininess = mix(256.0, 8.0, u_Roughness);
	float spec = pow(max(dot(norm, halfDir), 0.0), shininess);
	vec3 specular = u_LightSpecular * spec;
    
    vec3 result = ambient + diffuse + specular;
    FragColor = vec4(result, texColor.a);
}
```

---

## Setting Up Lighting in the Application

```cpp
// Create light
DirectionalLight light;
light.Direction = glm::vec3(-0.5f, -1.0f, -0.3f);
light.Ambient = glm::vec3(0.2f, 0.2f, 0.25f);
light.Diffuse = glm::vec3(0.8f, 0.8f, 0.75f);
light.Specular = glm::vec3(1.0f, 1.0f, 0.95f);

// In render loop, before drawing:
litShader.Bind();
litShader.SetVec3("u_LightDirection", light.GetDirection());
litShader.SetVec3("u_LightAmbient", light.Ambient);
litShader.SetVec3("u_LightDiffuse", light.Diffuse);
litShader.SetVec3("u_LightSpecular", light.Specular);
litShader.SetVec3("u_ViewPos", camera.GetPosition());
// Note: Roughness is set per-object in Scene::Render()

// Scene::Render handles per-object uniforms
scene.Render(renderer, litShader, camera);
```

---

## What Changed

| Before | After |
|--------|-------|
| `Vertex` had no normal | `Vertex` has `glm::vec3 Normal` |
| 8 vertices per cube | 24 vertices per cube (4 per face) |
| `unlit.shader` | `lit.shader` with Blinn-Phong lighting |
| `u_MVP` only | `u_MVP` + `u_Model` (for world-space positions) |
| Flat colors | Ambient + Diffuse + Specular |

---

## Key Takeaways

1. **Blinn-Phong = Ambient + Diffuse + Specular** - Three components approximate real lighting
2. **Normals define surface orientation** - Without normals, no lighting
3. **Dot product measures alignment** - Core math for diffuse and specular
4. **View direction matters** - Specular highlights depend on camera position
5. **Per-face vertices for flat shading** - Each face needs its own normals

---

## What's Next

This is basic lighting. Production engines add:

- **Multiple lights** - Point lights, spot lights, area lights
- **Shadows** - Shadow mapping
- **Normal maps** - Per-pixel normals from textures
- **PBR** - Physically Based Rendering for realistic materials
- **HDR** - High Dynamic Range for bright lights
- **Ambient Occlusion** - Soft shadows in crevices

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Object completely black | Normals pointing wrong way | Check winding order or flip normals |
| Lighting doesn't change with rotation | Using model-space normals | Transform normals by Normal Matrix |
| Specular on back of object | Forgot `max(dot, 0)` | Clamp negative values to 0 |
| Lighting looks faceted | Shared vertices, averaged normals | Duplicate verts for flat shading |

---

## Checkpoint

This chapter covered Blinn-Phong lighting:

**Formula:** `Final = Ambient + Diffuse + Specular`

**Requirements:**
- Normals in `Vertex` struct
- `lit.shader` with lighting calculations  
- Camera position uniform (`u_ViewPos`)

**Files:**
- `src/resources/shaders/lit.shader` — Lighting shader
- `VizEngine/Core/Mesh.cpp` — Updated with normals

**Checkpoint:** Create `Light.h` with `DirectionalLight` struct, create `lit.shader` with Blinn-Phong lighting, add Normal to Vertex struct, set lighting uniforms, and verify 3D shading appears.

---

## Exercises

1. **Add a PointLight** - Implement point light with attenuation
2. **Multiple lights** - Support multiple directional lights
3. **Colored lights** - Try a red or blue light
4. **Emissive objects** - Add objects that glow
5. **Compare Phong vs Blinn-Phong** - Implement original Phong and compare

---

> **Next:** [Chapter 16: Model Loading](16_ModelLoading.md) - Loading external 3D models with glTF.

> **Previous:** [Chapter 14: Scene Management](14_SceneManagement.md)

> **Reference:** For class diagrams and file locations, see [Appendix A: Code Reference](A_Reference.md).


