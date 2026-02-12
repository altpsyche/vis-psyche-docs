\newpage

# Chapter 37: PBR Implementation

Upgrade `defaultlit.shader` from Blinn-Phong to Cook-Torrance PBR for physically accurate material rendering.

---

## Introduction

In **Chapter 36**, we explored the mathematical foundation of Physically Based Rendering: the rendering equation, microfacet theory, and the Cook-Torrance BRDF with its D, F, and G components. Now we'll upgrade our existing `defaultlit.shader` and material system to use these physically-based calculations.

**What we're upgrading:**

| Before (Blinn-Phong) | After (Cook-Torrance) |
|---------------------|----------------------|
| `u_Shininess` exponent | `u_Roughness` + `u_Metallic` |
| `obj.Shininess` field | `obj.Roughness` + `obj.Metallic` fields |
| Arbitrary specular power | Physics-based D, F, G terms |
| No energy conservation | Fresnel-based energy conservation |
| Single directional light | Directional + 4 point lights |

---

## Step 0: Update SceneObject

Add PBR properties to replace Shininess:

```cpp
// In SceneObject.h - REPLACE Shininess with:
float Roughness = 0.5f;   // 0 = smooth, 1 = rough
float Metallic = 0.0f;    // 0 = dielectric, 1 = metal
```

---

## Step 0.5: Update Material Struct

Upgrade the Material struct for full PBR support:

```cpp
// In Material.h - REPLACE entire struct with:
struct VizEngine_API Material
{
    glm::vec4 BaseColor = glm::vec4(1.0f);
    float Roughness = 0.5f;     // Was: Shininess
    float Metallic = 0.0f;      // NEW
    
    std::shared_ptr<Texture> BaseColorTexture;
    std::shared_ptr<Texture> MetallicRoughnessTexture;
    std::shared_ptr<Texture> NormalTexture;
    
    // ... additional PBR textures
};
```

> [!NOTE]
> glTF models already store PBR properties. Previously we converted `roughness → shininess`, now we use roughness directly.

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **PBR Shader** | Complete implementation of Cook-Torrance specular + Lambertian diffuse |
| **GGX Distribution** | Normal distribution function for specular highlight shape |
| **Fresnel-Schlick** | Angle-dependent reflectivity with metallic workflow |
| **Smith Geometry** | Self-shadowing/masking for energy conservation |
| **Multi-Light Support** | Directional light + 4 point lights |
| **Texture Support** | Albedo texture sampling with color tinting |
| **Material Controls** | Per-object metallic/roughness editing via ImGui |

---

## Step 1: Upgrade the Shader

We'll upgrade our existing `defaultlit.shader` to implement Cook-Torrance PBR. The file already exists from Chapter 17—we're replacing the Blinn-Phong lighting with physically-based calculations.

**Key uniform changes:**
- Remove: `u_Shininess`
- Add: `u_Roughness`, `u_Metallic`, `u_Albedo`, `u_AO`
- Add: Point light arrays, directional light, albedo texture

**Upgrade `VizEngine/src/resources/shaders/defaultlit.shader`:**

```glsl
#shader vertex
#version 460 core

// Match existing Mesh vertex layout (see Mesh.cpp SetupMesh)
layout(location = 0) in vec4 aPos;       // Position (vec4)
layout(location = 1) in vec3 aNormal;    // Normal (vec3)
layout(location = 2) in vec4 aColor;     // Color (vec4) - unused in PBR but must be declared
layout(location = 3) in vec2 aTexCoords; // TexCoords (vec2)

out vec3 v_WorldPos;
out vec3 v_Normal;
out vec2 v_TexCoords;

uniform mat4 u_Model;
uniform mat4 u_View;
uniform mat4 u_Projection;
uniform mat3 u_NormalMatrix;      // Pre-computed: transpose(inverse(mat3(model)))

void main()
{
    // Transform position to world space
    v_WorldPos = vec3(u_Model * aPos);

    // Transform normal to world space using pre-computed normal matrix
    // This is more efficient than computing inverse() per-vertex
    v_Normal = u_NormalMatrix * aNormal;

    // Pass through texture coordinates
    v_TexCoords = aTexCoords;

    gl_Position = u_Projection * u_View * vec4(v_WorldPos, 1.0);
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec3 v_WorldPos;
in vec3 v_Normal;
in vec2 v_TexCoords;

// ============================================================================
// Material Parameters
// ============================================================================
uniform vec3 u_Albedo;           // Base color (or tint if using texture)
uniform float u_Metallic;        // 0 = dielectric, 1 = metal
uniform float u_Roughness;       // 0 = smooth, 1 = rough
uniform float u_AO;              // Ambient occlusion

// Albedo/Base color texture
uniform sampler2D u_AlbedoTexture;
uniform bool u_UseAlbedoTexture;

// ============================================================================
// Camera
// ============================================================================
uniform vec3 u_ViewPos;

// ============================================================================
// Lights (up to 4 point lights)
// ============================================================================
uniform vec3 u_LightPositions[4];
uniform vec3 u_LightColors[4];
uniform int u_LightCount;

// ============================================================================
// Directional Light (optional, for unified lighting with existing scene)
// ============================================================================
uniform vec3 u_DirLightDirection;   // Direction FROM light (normalized)
uniform vec3 u_DirLightColor;       // Radiance (intensity baked in)
uniform bool u_UseDirLight;         // Enable directional light

// ============================================================================
// Constants
// ============================================================================
const float PI = 3.14159265359;

// ============================================================================
// PBR Helper Functions
// ============================================================================

// ----------------------------------------------------------------------------
// Normal Distribution Function: GGX/Trowbridge-Reitz
// Approximates the proportion of microfacets aligned with halfway vector H.
// 
// Formula: D = α² / (π * ((n·h)²(α² - 1) + 1)²)
// Where α = roughness²
// ----------------------------------------------------------------------------
float DistributionGGX(vec3 N, vec3 H, float roughness)
{
    float a = roughness * roughness;        // α = roughness² (perceptual mapping)
    float a2 = a * a;                       // α²
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;
    
    float nom = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;
    
    return nom / denom;
}

// ----------------------------------------------------------------------------
// Geometry Function: Schlick-GGX (single direction)
// Models self-shadowing of microfacets.
// 
// Formula: G1 = (n·v) / ((n·v)(1 - k) + k)
// Where k = (roughness + 1)² / 8 for direct lighting
// ----------------------------------------------------------------------------
float GeometrySchlickGGX(float NdotV, float roughness)
{
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;    // k for direct lighting
    
    float nom = NdotV;
    float denom = NdotV * (1.0 - k) + k;
    
    return nom / denom;
}

// ----------------------------------------------------------------------------
// Geometry Function: Smith (combined shadowing and masking)
// Combines view and light direction geometry terms.
// 
// Formula: G = G1(n, v) * G1(n, l)
// ----------------------------------------------------------------------------
float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness)
{
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2 = GeometrySchlickGGX(NdotV, roughness);  // View direction (masking)
    float ggx1 = GeometrySchlickGGX(NdotL, roughness);  // Light direction (shadowing)
    
    return ggx1 * ggx2;
}

// ----------------------------------------------------------------------------
// Fresnel Equation: Schlick Approximation
// Models how reflectivity increases at grazing angles.
// 
// Formula: F = F0 + (1 - F0)(1 - cosθ)^5
// Where F0 = reflectance at normal incidence
// ----------------------------------------------------------------------------
vec3 FresnelSchlick(float cosTheta, vec3 F0)
{
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

// ============================================================================
// Main Fragment Shader
// ============================================================================
void main()
{
    // Normalize interpolated vectors
    vec3 N = normalize(v_Normal);
    vec3 V = normalize(u_ViewPos - v_WorldPos);
    
    // Get albedo from texture or uniform
    vec3 albedo = u_Albedo;
    if (u_UseAlbedoTexture)
    {
        vec4 texColor = texture(u_AlbedoTexture, v_TexCoords);
        albedo = texColor.rgb * u_Albedo;  // Multiply texture with tint color
    }
    
    // Calculate F0 (base reflectivity)
    // Dielectrics: 0.04 (approximately 4% reflectivity)
    // Metals: use albedo as F0 (tinted reflections)
    vec3 F0 = vec3(0.04);
    F0 = mix(F0, albedo, u_Metallic);
    
    // Accumulate radiance from all lights
    vec3 Lo = vec3(0.0);
    
    for (int i = 0; i < u_LightCount; ++i)
    {
        // ====================================================================
        // Per-Light Calculations
        // ====================================================================
        
        // Light direction and distance
        vec3 L = normalize(u_LightPositions[i] - v_WorldPos);
        vec3 H = normalize(V + L);  // Halfway vector
        float distance = length(u_LightPositions[i] - v_WorldPos);
        
        // Attenuation (inverse square law)
        float attenuation = 1.0 / (distance * distance);
        vec3 radiance = u_LightColors[i] * attenuation;
        
        // ====================================================================
        // Cook-Torrance BRDF
        // ====================================================================
        
        // D: Normal Distribution Function (microfacet alignment)
        float D = DistributionGGX(N, H, u_Roughness);
        
        // F: Fresnel (angle-dependent reflectivity)
        float cosTheta = max(dot(H, V), 0.0);
        vec3 F = FresnelSchlick(cosTheta, F0);
        
        // G: Geometry (self-shadowing/masking)
        float G = GeometrySmith(N, V, L, u_Roughness);
        
        // Specular BRDF: (D * F * G) / (4 * NdotV * NdotL)
        vec3 numerator = D * F * G;
        float NdotV = max(dot(N, V), 0.0);
        float NdotL = max(dot(N, L), 0.0);
        float denominator = 4.0 * NdotV * NdotL + 0.0001;  // Avoid divide by zero
        vec3 specular = numerator / denominator;
        
        // ====================================================================
        // Diffuse Component (Lambertian)
        // ====================================================================
        
        // kS = Fresnel (specular contribution)
        // kD = 1 - kS (diffuse contribution, energy conservation)
        vec3 kS = F;
        vec3 kD = vec3(1.0) - kS;
        
        // Metals have no diffuse (all energy goes to specular)
        kD *= (1.0 - u_Metallic);
        
        // Lambertian diffuse: albedo / π
        vec3 diffuse = kD * albedo / PI;
        
        // ====================================================================
        // Combine and Accumulate
        // ====================================================================
        Lo += (diffuse + specular) * radiance * NdotL;
    }
    
    // ========================================================================
    // Directional Light Contribution (if enabled)
    // ========================================================================
    if (u_UseDirLight)
    {
        // Direction TO light (negate the uniform which is FROM light)
        vec3 L = normalize(-u_DirLightDirection);
        vec3 H = normalize(V + L);
        
        // No attenuation for directional lights (infinitely far)
        vec3 radiance = u_DirLightColor;
        
        // Cook-Torrance BRDF (same as point lights)
        float D = DistributionGGX(N, H, u_Roughness);
        float cosTheta = max(dot(H, V), 0.0);
        vec3 F = FresnelSchlick(cosTheta, F0);
        float G = GeometrySmith(N, V, L, u_Roughness);
        
        vec3 numerator = D * F * G;
        float NdotV = max(dot(N, V), 0.0);
        float NdotL = max(dot(N, L), 0.0);
        float denominator = 4.0 * NdotV * NdotL + 0.0001;
        vec3 specular = numerator / denominator;
        
        vec3 kS = F;
        vec3 kD = (vec3(1.0) - kS) * (1.0 - u_Metallic);
        vec3 diffuse = kD * albedo / PI;
        
        Lo += (diffuse + specular) * radiance * NdotL;
    }
    
    // ========================================================================
    // Ambient Lighting (simple constant term for now)
    // Chapter 38 will replace this with Image-Based Lighting
    // ========================================================================
    vec3 ambient = vec3(0.03) * albedo * u_AO;
    
    vec3 color = ambient + Lo;
    
    // ========================================================================
    // Tone Mapping and Gamma Correction
    // ========================================================================
    
    // Reinhard tone mapping (simple, will be improved in Chapter 39)
    color = color / (color + vec3(1.0));
    
    // Gamma correction (linear -> sRGB)
    color = pow(color, vec3(1.0 / 2.2));
    
    FragColor = vec4(color, 1.0);
}
```

> [!NOTE]
> **Tone Mapping**: We include basic Reinhard tone mapping and gamma correction in this shader. Chapter 39 (HDR Pipeline) will move these to a post-processing pass for more control.

---

## Step 2: Understanding the Shader Structure

Let's break down the key sections of our PBR shader.

### Vertex Shader

The vertex shader prepares data for fragment processing:

```glsl
v_WorldPos = vec3(u_Model * aPos);
```
Transforms vertex position to world space for lighting calculations.

```glsl
v_Normal = u_NormalMatrix * aNormal;
```
Uses the **pre-computed normal matrix** (`u_NormalMatrix`) to correctly transform normals. This handles non-uniform scaling (e.g., stretching a sphere into an ellipsoid).

> [!TIP]
> The normal matrix is computed on the CPU as `transpose(inverse(mat3(model)))` once per object, then passed to the shader. This is **40-60% faster** than computing `inverse()` per-vertex in the shader (which Chapter 17's simpler approach did). The `PBRMaterial::SetNormalMatrix()` method handles this.

### Material Uniforms

| Uniform | Type | Range | Purpose |
|---------|------|-------|---------|
| `u_Albedo` | `vec3` | [0,1] per channel | Base color |
| `u_Metallic` | `float` | [0,1] | Dielectric (0) to metal (1) |
| `u_Roughness` | `float` | [0,1] | Smooth (0) to rough (1) |
| `u_AO` | `float` | [0,1] | Ambient occlusion factor |

### F0 Calculation

```glsl
vec3 F0 = vec3(0.04);
F0 = mix(F0, u_Albedo, u_Metallic);
```

This is the **metallic workflow** core:
- **Dielectrics** (metallic=0): F0 = 0.04 (gray, ~4% reflectivity)
- **Metals** (metallic=1): F0 = albedo (gold reflects gold, copper reflects copper)

### The Light Loop

```glsl
for (int i = 0; i < u_LightCount; ++i)
```

We iterate over all active lights, computing the BRDF contribution for each and summing the results. This matches the discrete sum approximation of the rendering equation from Chapter 36.

### Energy Conservation

```glsl
vec3 kS = F;
vec3 kD = vec3(1.0) - kS;
kD *= (1.0 - u_Metallic);
```

The Fresnel term `F` tells us how much light is reflected (specular). The rest is available for diffuse:
- `kD = 1 - kS` ensures total energy ≤ 1
- Metals absorb refracted light, so we zero out diffuse

---

## Step 3: Using the PBR Shader

### Loading the Shader

In your application (e.g., `SandboxApp.cpp`), load the PBR shader:

```cpp
// In OnCreate()
m_PBRShader = std::make_unique<VizEngine::Shader>("resources/shaders/pbr.shader");
```

### Setting Up Lights

Configure both directional and point lights:

```cpp
// Directional light (unified with existing scene)
m_Light.Direction = glm::vec3(-0.5f, -1.0f, -0.3f);
m_Light.Diffuse = glm::vec3(0.8f, 0.8f, 0.75f);

// Four corner point lights for PBR
glm::vec3 m_PBRLightPositions[4] = {
    glm::vec3(-10.0f,  10.0f, 10.0f),
    glm::vec3( 10.0f,  10.0f, 10.0f),
    glm::vec3(-10.0f, -10.0f, 10.0f),
    glm::vec3( 10.0f, -10.0f, 10.0f)
};

float m_PBRLightIntensity = 300.0f;
glm::vec3 m_PBRLightColor = glm::vec3(1.0f, 1.0f, 1.0f);
glm::vec3 m_PBRLightColors[4];  // = color * intensity
```

> [!NOTE]
> **High Intensity Values**: PBR uses physical light units. Values like 300.0 represent bright lights; the tone mapping operator compresses the range to displayable values.

### Rendering with PBR

```cpp
// In OnRender()
m_PBRShader->Bind();

// Set camera matrices
m_PBRShader->SetMatrix4fv("u_View", m_Camera.GetViewMatrix());
m_PBRShader->SetMatrix4fv("u_Projection", m_Camera.GetProjectionMatrix());
m_PBRShader->SetVec3("u_ViewPos", m_Camera.GetPosition());

// Set point lights
m_PBRShader->SetInt("u_LightCount", 4);
for (int i = 0; i < 4; ++i)
{
    m_PBRShader->SetVec3("u_LightPositions[" + std::to_string(i) + "]", m_PBRLightPositions[i]);
    m_PBRShader->SetVec3("u_LightColors[" + std::to_string(i) + "]", m_PBRLightColors[i]);
}

// Set directional light
m_PBRShader->SetBool("u_UseDirLight", true);
m_PBRShader->SetVec3("u_DirLightDirection", m_Light.GetDirection());
m_PBRShader->SetVec3("u_DirLightColor", m_Light.Diffuse * 2.0f);

// Render scene objects
for (auto& obj : m_Scene)
{
    if (!obj.Active || !obj.MeshPtr) continue;

    glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
    m_PBRShader->SetMatrix4fv("u_Model", model);

    // Pre-compute normal matrix on CPU (40-60% faster than per-vertex inverse)
    glm::mat3 normalMatrix = glm::transpose(glm::inverse(glm::mat3(model)));
    m_PBRShader->SetMatrix3fv("u_NormalMatrix", normalMatrix);

    // Set material properties from SceneObject
    m_PBRShader->SetVec3("u_Albedo", glm::vec3(obj.Color));
    m_PBRShader->SetFloat("u_Metallic", obj.Metallic);
    m_PBRShader->SetFloat("u_Roughness", obj.Roughness);
    m_PBRShader->SetFloat("u_AO", 1.0f);

    // Bind texture if available
    if (obj.TexturePtr)
    {
        obj.TexturePtr->Bind(0);
        m_PBRShader->SetInt("u_AlbedoTexture", 0);
        m_PBRShader->SetBool("u_UseAlbedoTexture", true);
    }
    else
    {
        m_PBRShader->SetBool("u_UseAlbedoTexture", false);
    }

    obj.MeshPtr->Bind();
    renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), *m_PBRShader);
}
```

---

## Step 4: Testing Material Variations

Use the Scene Objects panel to interactively test different material properties.

### Adding Spheres for Testing

First, create a sphere mesh in `OnCreate()`:

```cpp
// In OnCreate()
m_SphereMesh = std::shared_ptr<VizEngine::Mesh>(
    VizEngine::Mesh::CreateSphere(1.0f, 32).release()
);
```

Then use the **"Add Sphere"** button in the Scene Objects panel to dynamically create test objects.

### Roughness Test (Dielectric)

Test how roughness affects specular highlights:

1. Click **"Add Sphere"** multiple times to create several spheres
2. For each sphere, select it and adjust:
   - **Metallic**: 0.0 (dielectric)
   - **Roughness**: Vary from 0.0 to 1.0
   - **Color**: Set to red (0.5, 0.0, 0.0) or any base color
3. Position spheres in a row using the Position controls

**Expected result**:
- **roughness=0.0**: Sharp, bright specular highlight
- **roughness=0.5**: Soft, spread-out highlight
- **roughness=1.0**: Almost no visible highlight, matte appearance

### Metallic Test (Gold)

Test how roughness affects metallic surfaces:

1. Click **"Add Sphere"** to create spheres
2. For each sphere, adjust:
   - **Metallic**: 1.0 (metal)
   - **Roughness**: Vary from 0.0 to 1.0
   - **Color**: Set to gold (1.0, 0.76, 0.33)
3. Arrange in a row

**Expected result**:
- **roughness=0.0**: Perfect gold mirror
- **roughness=0.5**: Brushed gold appearance
- **roughness=1.0**: Matte gold (still somewhat reflective due to Fresnel)

### Metallic Transition Test

Test the dielectric-to-metal transition:

1. Click **"Add Sphere"** to create spheres
2. For each sphere, adjust:
   - **Metallic**: Vary from 0.0 to 1.0
   - **Roughness**: 0.3 (constant)
   - **Color**: Set to orange (0.9, 0.6, 0.2)
3. Arrange in a row

**Expected result**:
- **metallic=0.0**: Plastic-like, colorless highlights
- **metallic=0.5**: Transition (rarely used in practice)
- **metallic=1.0**: Metal-like, tinted (orange) reflections

### Using the ImGui Controls

The **Scene Objects** panel provides:
- **Add Sphere** button: Creates a new sphere with default PBR properties
- **Material sliders**: Adjust Metallic (0-1) and Roughness (0.05-1)
- **Color picker**: Change albedo color
- **Transform controls**: Position, rotation, scale

The **Lighting** panel allows you to:
- Adjust directional light direction and color
- Control point light intensity (50-1000) and color
- See real-time PBR response to lighting changes

---

## Common Issues and Solutions

### Issue: Scene is Too Dark

| Symptom | Cause | Solution |
|---------|-------|----------|
| Nearly black output | Light intensity too low | Increase light colors (try 300.0+) |
| | Missing π in diffuse | Verify `albedo / PI` |
| | Wrong attenuation | Check `1.0 / (distance * distance)` |

### Issue: Scene is Too Bright / Washed Out

| Symptom | Cause | Solution |
|---------|-------|----------|
| Clipped whites everywhere | No tone mapping | Add `color / (color + 1.0)` |
| | Light intensity too high | Reduce light colors |
| | Missing gamma correction | Add `pow(color, vec3(1.0/2.2))` |

### Issue: No Specular Highlights

| Symptom | Cause | Solution |
|---------|-------|----------|
| Only diffuse visible | Roughness = 1.0 | Lower roughness value |
| | NDF returning 0 | Check `DistributionGGX()` math |
| | F0 = 0 | Verify `mix(0.04, albedo, metallic)` |

### Issue: Black Fragments / NaN

| Symptom | Cause | Solution |
|---------|-------|----------|
| Random black pixels | Division by zero | Add epsilon: `+ 0.0001` to denominator |
| | NdotV or NdotL = 0 | Clamp to `max(dot(), 0.0)` |
| | Negative sqrt input | Should not occur with correct formulas |

**Debugging tip**: Output intermediate values as colors:

```glsl
// Debug: visualize the normal
FragColor = vec4(N * 0.5 + 0.5, 1.0);

// Debug: visualize roughness effect on D
FragColor = vec4(vec3(D * 0.1), 1.0);

// Debug: visualize Fresnel
FragColor = vec4(F, 1.0);
```

### Issue: Metals Look Like Plastic

| Symptom | Cause | Solution |
|---------|-------|----------|
| No tinted reflections | F0 not using albedo | Verify `F0 = mix(0.04, albedo, metallic)` |
| | kD not zeroed | Check `kD *= (1.0 - metallic)` |
| Diffuse visible on metal | Energy not conserved | Above fix should also solve this |

---

## Performance Considerations

### Current Shader Cost

| Operation | Cost | Notes |
|-----------|------|-------|
| `u_NormalMatrix` | **Low** | Pre-computed on CPU (40-60% faster than in-shader inverse) |
| `pow(x, 5.0)` | Medium | Could use `x*x*x*x*x` (marginal gain) |
| Per-light loop | Medium | 4 lights = 4× the work |
| GGX distribution | Low | Simple arithmetic |

### Optimizations Already Applied

1. **Normal Matrix on CPU**: We pass `u_NormalMatrix` computed as `transpose(inverse(mat3(model)))` once per object instead of per-vertex in the shader. This is the most impactful optimization for PBR shaders.

### Future Optimization Opportunities

1. **Early Out**: Skip back-facing fragments
2. **Light Culling**: Skip lights with zero contribution (future chapter)
3. **Deferred Rendering**: Compute lighting once per pixel regardless of mesh complexity (future chapter)

Performance is now optimized for learning while remaining production-ready.

---

## Comparison with Reference Implementations

Validate your results against known-good PBR renderers:

### LearnOpenGL PBR Demo
- **Reference**: [learnopengl.com/PBR/Lighting](https://learnopengl.com/PBR/Lighting)
- **Expected match**: Roughness and metallic sweeps should look identical

### glTF Sample Viewer
- **Reference**: [github.khronos.org/glTF-Sample-Viewer](https://github.khronos.org/glTF-Sample-Viewer)
- **Test**: Load a PBR model and compare

### Common Differences
- **Ambient**: Our simple `0.03 * albedo * AO` differs from IBL (Chapter 38)
- **Tone mapping**: Reinhard vs ACES vs other operators
- **Gamma**: Ensure both you and reference use sRGB output

---

## Integration Notes

### Current Limitations

| Limitation | Solution (Future Chapter) |
|------------|---------------------------|
| Only albedo textures | Chapter 42: Material System (metallic/roughness/normal maps) |
| Simple ambient | Chapter 38: Image-Based Lighting |
| Basic tone mapping | Chapter 39: HDR Pipeline |
| No normal mapping | Chapter 42: Material System |

### Preparing for IBL (Chapter 38)

The skybox cubemap from Chapter 30-31 will be used for:
- **Diffuse irradiance**: Replace ambient term with environment lighting
- **Specular prefiltering**: Blurred environment reflections based on roughness

Our shader structure is ready—we'll add these as additional terms.

---

## Milestone

**Chapter 37 Complete - PBR Implementation**

You have:
- Implemented the complete Cook-Torrance BRDF in GLSL
- Created helper functions for GGX, Fresnel-Schlick, and Smith geometry
- Set up multi-light support with point lights
- Understood the metallic-roughness workflow in practice
- Tested material variations (roughness and metallic sweeps)
- Learned debugging techniques for PBR shaders
- Added basic tone mapping and gamma correction

Your engine now supports **physically based materials** that behave correctly under various lighting conditions—the same rendering approach used by Unreal Engine, Unity, and Blender.

---

## What's Next

In **Chapter 38: Image-Based Lighting**, we'll replace the simple ambient term with environment-based lighting using HDR cubemaps. This adds realistic diffuse irradiance and specular reflections from the environment itself.

> **Next:** [Chapter 38: Image-Based Lighting](38_ImageBasedLighting.md)

> **Previous:** [Chapter 36: PBR Theory](36_PBRTheory.md)

> **Index:** [Table of Contents](INDEX.md)
