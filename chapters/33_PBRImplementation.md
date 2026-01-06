\newpage

# Chapter 33: PBR Implementation

Implement the Cook-Torrance BRDF in GLSL, creating a complete PBR shader for realistic material rendering.

---

## Introduction

In **Chapter 32**, we explored the mathematical foundation of Physically Based Rendering: the rendering equation, microfacet theory, and the Cook-Torrance BRDF with its D, F, and G components. Now we'll translate that theory into working GLSL code.

**What we'll build:**

| Component | Description |
|-----------|-------------|
| **pbr.shader** | Complete vertex/fragment shader implementing Cook-Torrance BRDF |
| **Helper functions** | `DistributionGGX()`, `FresnelSchlick()`, `GeometrySmith()` |
| **Multi-light support** | Four point lights for testing |
| **Material uniforms** | Albedo, metallic, roughness, ambient occlusion |

**Expected result:** A PBR-lit sphere (or any mesh) that responds realistically to roughness and metallic parameters—matching industry-standard renderers like glTF Sample Viewer.

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **PBR Shader** | Complete implementation of Cook-Torrance specular + Lambertian diffuse |
| **GGX Distribution** | Normal distribution function for specular highlight shape |
| **Fresnel-Schlick** | Angle-dependent reflectivity with metallic workflow |
| **Smith Geometry** | Self-shadowing/masking for energy conservation |
| **Multi-Light Loop** | Support for multiple point lights |
| **Testing Setup** | Material parameter sweeps for validation |

---

## Step 1: Create the PBR Shader File

Create a new shader file that implements the complete PBR lighting model.

**Create `VizEngine/src/resources/shaders/pbr.shader`:**

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoords;

out vec3 v_WorldPos;
out vec3 v_Normal;
out vec2 v_TexCoords;

uniform mat4 u_Model;
uniform mat4 u_View;
uniform mat4 u_Projection;

void main()
{
    // Transform position to world space
    v_WorldPos = vec3(u_Model * vec4(aPos, 1.0));
    
    // Transform normal to world space (use normal matrix for non-uniform scaling)
    v_Normal = mat3(transpose(inverse(u_Model))) * aNormal;
    
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
uniform vec3 u_Albedo;       // Base color
uniform float u_Metallic;    // 0 = dielectric, 1 = metal
uniform float u_Roughness;   // 0 = smooth, 1 = rough
uniform float u_AO;          // Ambient occlusion

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
    
    // Calculate F0 (base reflectivity)
    // Dielectrics: 0.04 (approximately 4% reflectivity)
    // Metals: use albedo as F0 (tinted reflections)
    vec3 F0 = vec3(0.04);
    F0 = mix(F0, u_Albedo, u_Metallic);
    
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
        vec3 diffuse = kD * u_Albedo / PI;
        
        // ====================================================================
        // Combine and Accumulate
        // ====================================================================
        Lo += (diffuse + specular) * radiance * NdotL;
    }
    
    // ========================================================================
    // Ambient Lighting (simple constant term for now)
    // Chapter 34 will replace this with Image-Based Lighting
    // ========================================================================
    vec3 ambient = vec3(0.03) * u_Albedo * u_AO;
    
    vec3 color = ambient + Lo;
    
    // ========================================================================
    // Tone Mapping and Gamma Correction
    // ========================================================================
    
    // Reinhard tone mapping (simple, will be improved in Chapter 35)
    color = color / (color + vec3(1.0));
    
    // Gamma correction (linear -> sRGB)
    color = pow(color, vec3(1.0 / 2.2));
    
    FragColor = vec4(color, 1.0);
}
```

> [!NOTE]
> **Tone Mapping**: We include basic Reinhard tone mapping and gamma correction in this shader. Chapter 35 (HDR Pipeline) will move these to a post-processing pass for more control.

---

## Step 2: Understanding the Shader Structure

Let's break down the key sections of our PBR shader.

### Vertex Shader

The vertex shader prepares data for fragment processing:

```glsl
v_WorldPos = vec3(u_Model * vec4(aPos, 1.0));
```
Transforms vertex position to world space for lighting calculations.

```glsl
v_Normal = mat3(transpose(inverse(u_Model))) * aNormal;
```
Uses the **normal matrix** to correctly transform normals. This handles non-uniform scaling (e.g., stretching a sphere into an ellipsoid).

> [!WARNING]
> Computing `inverse(u_Model)` in the shader is expensive. In production, precompute the normal matrix on the CPU and pass it as a uniform.

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

We iterate over all active lights, computing the BRDF contribution for each and summing the results. This matches the discrete sum approximation of the rendering equation from Chapter 32.

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
m_PBRShader = std::make_shared<VizEngine::Shader>("resources/shaders/pbr.shader");
```

### Setting Up Lights

Configure point lights for testing:

```cpp
// Four corner lights for even illumination
glm::vec3 lightPositions[] = {
    glm::vec3(-10.0f,  10.0f, 10.0f),
    glm::vec3( 10.0f,  10.0f, 10.0f),
    glm::vec3(-10.0f, -10.0f, 10.0f),
    glm::vec3( 10.0f, -10.0f, 10.0f)
};

glm::vec3 lightColors[] = {
    glm::vec3(300.0f, 300.0f, 300.0f),
    glm::vec3(300.0f, 300.0f, 300.0f),
    glm::vec3(300.0f, 300.0f, 300.0f),
    glm::vec3(300.0f, 300.0f, 300.0f)
};
```

> [!NOTE]
> **High Intensity Values**: PBR uses physical light units. Values like 300.0 represent bright lights; the tone mapping operator compresses the range to displayable values.

### Rendering with PBR

```cpp
// In OnRender()
m_PBRShader->Bind();

// Set matrices
m_PBRShader->SetMatrix4fv("u_Model", modelMatrix);
m_PBRShader->SetMatrix4fv("u_View", m_Camera.GetViewMatrix());
m_PBRShader->SetMatrix4fv("u_Projection", m_Camera.GetProjectionMatrix());

// Set camera position
m_PBRShader->SetVec3("u_ViewPos", m_Camera.GetPosition());

// Set material properties
m_PBRShader->SetVec3("u_Albedo", glm::vec3(0.5f, 0.0f, 0.0f));  // Red
m_PBRShader->SetFloat("u_Metallic", 0.0f);   // Dielectric
m_PBRShader->SetFloat("u_Roughness", 0.5f);  // Medium rough
m_PBRShader->SetFloat("u_AO", 1.0f);         // No occlusion

// Set lights
m_PBRShader->SetInt("u_LightCount", 4);
for (int i = 0; i < 4; ++i)
{
    m_PBRShader->SetVec3("u_LightPositions[" + std::to_string(i) + "]", lightPositions[i]);
    m_PBRShader->SetVec3("u_LightColors[" + std::to_string(i) + "]", lightColors[i]);
}

// Render mesh
m_Mesh->Draw();
```

---

## Step 4: Testing Material Variations

Create a grid of spheres to visualize parameter effects:

### Roughness Test (Dielectric)

Render 7 spheres in a row with roughness varying from 0.0 to 1.0:

```cpp
for (int i = 0; i < 7; ++i)
{
    float roughness = i / 6.0f;  // 0.0, 0.167, 0.333, 0.5, 0.667, 0.833, 1.0
    
    glm::mat4 model = glm::translate(glm::mat4(1.0f), 
        glm::vec3((i - 3) * 2.5f, 0.0f, 0.0f));
    
    m_PBRShader->SetMatrix4fv("u_Model", model);
    m_PBRShader->SetVec3("u_Albedo", glm::vec3(0.5f, 0.0f, 0.0f));
    m_PBRShader->SetFloat("u_Metallic", 0.0f);
    m_PBRShader->SetFloat("u_Roughness", roughness);
    m_PBRShader->SetFloat("u_AO", 1.0f);
    
    m_Sphere->Draw();
}
```

**Expected result**:
- **roughness=0.0**: Sharp, bright specular highlight
- **roughness=0.5**: Soft, spread-out highlight
- **roughness=1.0**: Almost no visible highlight, matte appearance

### Metallic Test (Gold)

Render 7 spheres with roughness varying, metallic=1.0:

```cpp
for (int i = 0; i < 7; ++i)
{
    float roughness = i / 6.0f;
    
    glm::mat4 model = glm::translate(glm::mat4(1.0f), 
        glm::vec3((i - 3) * 2.5f, 3.0f, 0.0f));
    
    m_PBRShader->SetMatrix4fv("u_Model", model);
    m_PBRShader->SetVec3("u_Albedo", glm::vec3(1.0f, 0.76f, 0.33f));  // Gold
    m_PBRShader->SetFloat("u_Metallic", 1.0f);
    m_PBRShader->SetFloat("u_Roughness", roughness);
    m_PBRShader->SetFloat("u_AO", 1.0f);
    
    m_Sphere->Draw();
}
```

**Expected result**:
- **roughness=0.0**: Perfect gold mirror
- **roughness=0.5**: Brushed gold appearance
- **roughness=1.0**: Matte gold (still somewhat reflective due to Fresnel)

### Metallic Transition Test

Render 7 spheres with metallic varying from 0 to 1:

```cpp
for (int i = 0; i < 7; ++i)
{
    float metallic = i / 6.0f;
    
    glm::mat4 model = glm::translate(glm::mat4(1.0f), 
        glm::vec3((i - 3) * 2.5f, -3.0f, 0.0f));
    
    m_PBRShader->SetMatrix4fv("u_Model", model);
    m_PBRShader->SetVec3("u_Albedo", glm::vec3(0.9f, 0.6f, 0.2f));
    m_PBRShader->SetFloat("u_Metallic", metallic);
    m_PBRShader->SetFloat("u_Roughness", 0.3f);
    m_PBRShader->SetFloat("u_AO", 1.0f);
    
    m_Sphere->Draw();
}
```

**Expected result**:
- **metallic=0**: Plastic-like, colorless highlights
- **metallic=0.5**: Transition (rarely used in practice)
- **metallic=1**: Metal-like, tinted (orange-gold) reflections

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
| `inverse(u_Model)` | **High** | Move to CPU (one-time per object) |
| `pow(x, 5.0)` | Medium | Could use `x*x*x*x*x` (marginal gain) |
| Per-light loop | Medium | 4 lights = 4× the work |
| GGX distribution | Low | Simple arithmetic |

### Optimization Opportunities

1. **Precompute Normal Matrix**: Pass as uniform instead of computing in shader
2. **Early Out**: Skip back-facing fragments
3. **Light Culling**: Skip lights with zero contribution (future chapter)
4. **Deferred Rendering**: Compute lighting once per pixel regardless of mesh complexity (future chapter)

For now, performance is adequate for learning. Optimization becomes important with many lights and complex scenes.

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
- **Ambient**: Our simple `0.03 * albedo * AO` differs from IBL (Chapter 34)
- **Tone mapping**: Reinhard vs ACES vs other operators
- **Gamma**: Ensure both you and reference use sRGB output

---

## Integration Notes

### Current Limitations

| Limitation | Solution (Future Chapter) |
|------------|---------------------------|
| No texture support | Chapter 36: Material System |
| Simple ambient | Chapter 34: Image-Based Lighting |
| Basic tone mapping | Chapter 35: HDR Pipeline |
| No normal mapping | Chapter 36: Material System |

### Preparing for IBL (Chapter 34)

The skybox cubemap from Chapter 30-31 will be used for:
- **Diffuse irradiance**: Replace ambient term with environment lighting
- **Specular prefiltering**: Blurred environment reflections based on roughness

Our shader structure is ready—we'll add these as additional terms.

---

## Milestone

**Chapter 33 Complete - PBR Implementation**

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

In **Chapter 34: Image-Based Lighting**, we'll replace the simple ambient term with environment-based lighting using the cubemap from Chapter 30-31. This adds realistic ambient lighting and reflections from the environment itself.

> **Next:** [Chapter 34: Image-Based Lighting](34_ImageBasedLighting.md)

> **Previous:** [Chapter 32: PBR Theory](32_PBRTheory.md)

> **Index:** [Table of Contents](INDEX.md)
