\newpage

# Chapter 38: Image-Based Lighting

Complete our PBR pipeline by replacing the placeholder ambient term with environment-based diffuse and specular lighting.

---

## Introduction

In **Chapter 37**, we implemented Cook-Torrance PBR for direct lighting—point lights and directional lights. But our ambient term was a simple placeholder:

```glsl
vec3 ambient = vec3(0.03) * albedo * u_AO;  // Placeholder!
```

Real-world lighting comes from **everywhere**—the sky, reflected surfaces, distant objects. This chapter implements **Image-Based Lighting (IBL)**, using the HDR environment cubemap from Chapter 30 to provide physically-correct ambient lighting.

### Before vs After

| Lighting Component | Chapter 37 | Chapter 38 |
|-------------------|------------|------------|
| **Diffuse Ambient** | Flat 3% tint | Environment irradiance |
| **Specular Ambient** | None | Roughness-filtered reflections |
| **Material Response** | Same under all environments | Adapts to lighting |
| **Realism** | Acceptable | Photorealistic |

### What We're Building

| Feature | Description |
|---------|-------------|
| **Irradiance Map** | 32×32 cubemap storing hemisphere-averaged lighting for diffuse |
| **Prefiltered Environment** | Multi-mip cubemap with roughness-based blur for specular |
| **BRDF LUT** | 2D texture storing Fresnel scale/bias for split-sum approximation |
| **Updated PBR Shader** | IBL sampling replacing placeholder ambient |
| **IBL Intensity Control** | Slider to balance direct vs. ambient lighting (default 0.3) |
| **Generation Time** | ~2-5 seconds one-time cost at startup |

---

## The Split-Sum Approximation

### The Problem

The rendering equation for environment lighting is:

$$L_o = \int_\Omega L_i(\omega_i) \cdot f_r(\omega_i, \omega_o) \cdot (n \cdot \omega_i) \, d\omega_i$$

This integral has two inputs that vary together:
- $L_i$ — incoming light (from environment cubemap)
- $f_r$ — BRDF (depends on material and angles)

Evaluating this integral **per-pixel, per-frame** requires thousands of samples—too expensive for real-time.

### Karis's Solution (SIGGRAPH 2013)

Brian Karis at Epic Games proposed splitting the integral into two pre-computable parts:

$$\int_\Omega L_i \cdot f_r \cdot \cos\theta \, d\omega_i \approx \left(\int_\Omega L_i(\omega_i) \, d\omega_i\right) \cdot \left(\int_\Omega f_r \cdot \cos\theta \, d\omega_i\right)$$

This **split-sum approximation** separates:
1. **Pre-filtered environment** — Depends only on Li and roughness
2. **BRDF integration** — Depends only on material and view angle

> [!NOTE]
> The approximation is exact for constant Li and generally accurate for typical HDR environments. The error is acceptable for real-time rendering and used by Unreal Engine 4+, Unity, Filament, and all modern PBR renderers.

### Physical Interpretation

Think of it this way:
- **First term**: "What light is available from this direction?" (environment-dependent)
- **Second term**: "How much of that light does my material reflect?" (material-dependent)

Because these are independent, we can precompute both:
- Pre-filtered environment: Bake per-roughness blurred cubemap (one-time)
- BRDF LUT: Bake universal lookup table (once ever, environment-independent)

---

## Diffuse IBL: Irradiance Map

### Theory

For **diffuse** (Lambertian) reflection, the BRDF is constant:

$$f_{lambert} = \frac{albedo}{\pi}$$

This simplifies our integral to:

$$L_{diffuse} = \frac{albedo}{\pi} \int_\Omega L_i(\omega_i) \cdot \cos\theta_i \, d\omega_i$$

The integral depends **only on the surface normal**—not view direction or roughness. We can precompute it for every possible normal direction and store it in a cubemap.

### Irradiance Map Generation

For each direction (cubemap texel), we convolve the environment over the hemisphere:

```
For each normal direction N:
    sum = 0
    For phi = 0 to 2π:
        For theta = 0 to π/2:
            Sample direction = spherical_to_cartesian(phi, theta)
            Align sample to N's hemisphere
            sum += environment(sample) * cos(theta) * sin(theta)
    irradiance[N] = PI * sum / num_samples
```

The `sin(theta)` term corrects for varying solid angle at different latitudes (fewer samples near poles).

### Visual Description

The irradiance map looks like a **heavily blurred** version of the environment:
- Sharp sun → soft bright region
- Blue sky → blue-tinted hemisphere
- Ground plane → brown/green tinting from below

Resolution: 32×32 per face is sufficient because irradiance varies slowly (low-frequency signal).

---

## Specular IBL: Pre-filtered Environment

### Theory

Specular reflection concentrates in a lobe around the reflection direction. The lobe width depends on **roughness**:
- roughness = 0: Perfect mirror (sample single direction)
- roughness = 1: Wide lobe (nearly diffuse)

We importance-sample the GGX distribution and store roughness levels in mipmap chain:
- Mip 0 = roughness 0.0 (sharp environment)
- Mip N = roughness 1.0 (heavily blurred)

### Importance Sampling

Instead of uniform hemisphere sampling, we sample where the BRDF is high—along the GGX distribution:

```glsl
vec3 ImportanceSampleGGX(vec2 Xi, vec3 N, float roughness)
{
    float a = roughness * roughness;
    
    // GGX distribution inversion
    float phi = 2.0 * PI * Xi.x;
    float cosTheta = sqrt((1.0 - Xi.y) / (1.0 + (a*a - 1.0) * Xi.y));
    float sinTheta = sqrt(1.0 - cosTheta * cosTheta);
    
    // Spherical to Cartesian (tangent space)
    vec3 H;
    H.x = cos(phi) * sinTheta;
    H.y = sin(phi) * sinTheta;
    H.z = cosTheta;
    
    // Transform to world space (aligned with N)
    vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
    vec3 tangent = normalize(cross(up, N));
    vec3 bitangent = cross(N, tangent);
    
    return normalize(tangent * H.x + bitangent * H.y + N * H.z);
}
```

### Low-Discrepancy Sampling

For consistent results with fewer samples, we use the **Hammersley sequence** instead of random numbers:

```glsl
// Van der Corput radical inverse
float RadicalInverse_VdC(uint bits) 
{
    bits = (bits << 16u) | (bits >> 16u);
    bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
    bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
    bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
    bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
    return float(bits) * 2.3283064365386963e-10; // / 0x100000000
}

vec2 Hammersley(uint i, uint N)
{
    return vec2(float(i) / float(N), RadicalInverse_VdC(i));
}
```

This produces a well-distributed sequence that converges faster than random sampling.

### Visual Description

The pre-filtered environment map mipmap chain:
- **Mip 0**: Nearly identical to source HDRI (mirror reflection)
- **Mip 1**: Slightly blurred (polished metal)
- **Mip 2-3**: Progressively softer (brushed metal)
- **Mip 4-5**: Very blurry (satin/matte finish)

Resolution: 512×512 base with 5-6 mip levels typical.

---

## BRDF Integration LUT

### Theory

The second half of split-sum is the BRDF integral:

$$\int_\Omega f_r \cdot \cos\theta \, d\omega_i$$

For GGX Cook-Torrance, this evaluates to:

$$F_0 \cdot \text{scale} + \text{bias}$$

Where scale and bias depend only on:
- **NdotV** (how perpendicular is the view?)
- **Roughness** (how rough is the surface?)

We store these as a 2D texture (512×512 is plenty):
- **U axis**: NdotV (0 to 1)
- **V axis**: Roughness (0 to 1)
- **R channel**: Scale factor
- **G channel**: Bias factor

### Visual Description

The BRDF LUT is a distinctive gradient:
- **Bottom-left** (rough + perpendicular): Dark (low reflection)
- **Top-right** (smooth + grazing): Bright (high Fresnel)
- **Smooth diagonal gradient** from dark to bright

This texture is **environment-independent**—generate once, use forever.

---

## Step 1: Create Irradiance Convolution Shader

**Create `VizEngine/src/resources/shaders/irradiance_convolution.shader`:**

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 aPos;

out vec3 v_WorldPos;

uniform mat4 u_Projection;
uniform mat4 u_View;

void main()
{
    v_WorldPos = aPos;
    gl_Position = u_Projection * u_View * vec4(aPos, 1.0);
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec3 v_WorldPos;

uniform samplerCube u_EnvironmentMap;

const float PI = 3.14159265359;

void main()
{
    // The world vector acts as the normal of the tangent surface
    vec3 N = normalize(v_WorldPos);
    
    vec3 irradiance = vec3(0.0);
    
    // Construct tangent-space basis
    vec3 up = vec3(0.0, 1.0, 0.0);
    vec3 right = normalize(cross(up, N));
    up = normalize(cross(N, right));
    
    // Hemisphere sampling parameters
    float sampleDelta = 0.025;  // Angular step size
    float nrSamples = 0.0;
    
    // Sample hemisphere aligned with N
    for (float phi = 0.0; phi < 2.0 * PI; phi += sampleDelta)
    {
        for (float theta = 0.0; theta < 0.5 * PI; theta += sampleDelta)
        {
            // Spherical to Cartesian (tangent space)
            vec3 tangentSample = vec3(
                sin(theta) * cos(phi),
                sin(theta) * sin(phi),
                cos(theta)
            );
            
            // Transform to world space
            vec3 sampleVec = tangentSample.x * right + 
                             tangentSample.y * up + 
                             tangentSample.z * N;
            
            // Sample environment and weight by cos(theta) * sin(theta)
            // cos(theta) = Lambert's law
            // sin(theta) = solid angle correction (more area near equator)
            irradiance += texture(u_EnvironmentMap, sampleVec).rgb * 
                          cos(theta) * sin(theta);
            nrSamples++;
        }
    }
    
    // Normalize: PI factor accounts for hemisphere solid angle
    irradiance = PI * irradiance * (1.0 / float(nrSamples));
    
    FragColor = vec4(irradiance, 1.0);
}
```

---

## Step 2: Create Pre-filter Environment Shader

**Create `VizEngine/src/resources/shaders/prefilter_environment.shader`:**

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 aPos;

out vec3 v_WorldPos;

uniform mat4 u_Projection;
uniform mat4 u_View;

void main()
{
    v_WorldPos = aPos;
    gl_Position = u_Projection * u_View * vec4(aPos, 1.0);
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec3 v_WorldPos;

uniform samplerCube u_EnvironmentMap;
uniform float u_Roughness;

const float PI = 3.14159265359;
const uint SAMPLE_COUNT = 1024u;

// ----------------------------------------------------------------------------
// Van der Corput radical inverse (bit manipulation for low-discrepancy)
// ----------------------------------------------------------------------------
float RadicalInverse_VdC(uint bits) 
{
    bits = (bits << 16u) | (bits >> 16u);
    bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
    bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
    bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
    bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
    return float(bits) * 2.3283064365386963e-10; // 1 / 2^32
}

// ----------------------------------------------------------------------------
// Hammersley low-discrepancy sequence
// Produces well-distributed 2D points for importance sampling
// ----------------------------------------------------------------------------
vec2 Hammersley(uint i, uint N)
{
    return vec2(float(i) / float(N), RadicalInverse_VdC(i));
}

// ----------------------------------------------------------------------------
// GGX Importance Sampling
// Generates sample directions biased toward GGX lobe
// ----------------------------------------------------------------------------
vec3 ImportanceSampleGGX(vec2 Xi, vec3 N, float roughness)
{
    float a = roughness * roughness;
    
    // Convert 2D sample to spherical coordinates using GGX distribution
    float phi = 2.0 * PI * Xi.x;
    float cosTheta = sqrt((1.0 - Xi.y) / (1.0 + (a*a - 1.0) * Xi.y));
    float sinTheta = sqrt(1.0 - cosTheta * cosTheta);
    
    // Spherical to Cartesian (tangent space, Z-up)
    vec3 H;
    H.x = cos(phi) * sinTheta;
    H.y = sin(phi) * sinTheta;
    H.z = cosTheta;
    
    // Transform from tangent space to world space
    vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
    vec3 tangent = normalize(cross(up, N));
    vec3 bitangent = cross(N, tangent);
    
    vec3 sampleVec = tangent * H.x + bitangent * H.y + N * H.z;
    return normalize(sampleVec);
}

// ----------------------------------------------------------------------------
// Main: Convolve environment with GGX for this roughness level
// ----------------------------------------------------------------------------
void main()
{
    vec3 N = normalize(v_WorldPos);
    
    // Assumption: view direction = reflection direction = normal
    // This is the "isotropic" simplification from Karis
    vec3 R = N;
    vec3 V = R;
    
    vec3 prefilteredColor = vec3(0.0);
    float totalWeight = 0.0;
    
    for (uint i = 0u; i < SAMPLE_COUNT; ++i)
    {
        vec2 Xi = Hammersley(i, SAMPLE_COUNT);
        vec3 H = ImportanceSampleGGX(Xi, N, u_Roughness);
        vec3 L = normalize(2.0 * dot(V, H) * H - V);
        
        float NdotL = max(dot(N, L), 0.0);
        if (NdotL > 0.0)
        {
            // Sample environment at reflected direction
            prefilteredColor += texture(u_EnvironmentMap, L).rgb * NdotL;
            totalWeight += NdotL;
        }
    }
    
    prefilteredColor = prefilteredColor / totalWeight;
    
    FragColor = vec4(prefilteredColor, 1.0);
}
```

---

## Step 3: Create BRDF Integration Shader

**Create `VizEngine/src/resources/shaders/brdf_integration.shader`:**

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec2 aTexCoords;

out vec2 v_TexCoords;

void main()
{
    v_TexCoords = aTexCoords;
    gl_Position = vec4(aPos, 1.0);
}


#shader fragment
#version 460 core

out vec2 FragColor;

in vec2 v_TexCoords;

const float PI = 3.14159265359;
const uint SAMPLE_COUNT = 1024u;

// ----------------------------------------------------------------------------
// Van der Corput radical inverse
// ----------------------------------------------------------------------------
float RadicalInverse_VdC(uint bits) 
{
    bits = (bits << 16u) | (bits >> 16u);
    bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
    bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
    bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
    bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
    return float(bits) * 2.3283064365386963e-10;
}

vec2 Hammersley(uint i, uint N)
{
    return vec2(float(i) / float(N), RadicalInverse_VdC(i));
}

vec3 ImportanceSampleGGX(vec2 Xi, vec3 N, float roughness)
{
    float a = roughness * roughness;
    
    float phi = 2.0 * PI * Xi.x;
    float cosTheta = sqrt((1.0 - Xi.y) / (1.0 + (a*a - 1.0) * Xi.y));
    float sinTheta = sqrt(1.0 - cosTheta * cosTheta);
    
    vec3 H;
    H.x = cos(phi) * sinTheta;
    H.y = sin(phi) * sinTheta;
    H.z = cosTheta;
    
    vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
    vec3 tangent = normalize(cross(up, N));
    vec3 bitangent = cross(N, tangent);
    
    return normalize(tangent * H.x + bitangent * H.y + N * H.z);
}

// ----------------------------------------------------------------------------
// Geometry function for IBL (different k than direct lighting!)
// ----------------------------------------------------------------------------
float GeometrySchlickGGX(float NdotV, float roughness)
{
    float a = roughness;
    float k = (a * a) / 2.0;  // IBL uses roughness²/2, not (roughness+1)²/8
    
    float nom = NdotV;
    float denom = NdotV * (1.0 - k) + k;
    
    return nom / denom;
}

float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness)
{
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2 = GeometrySchlickGGX(NdotV, roughness);
    float ggx1 = GeometrySchlickGGX(NdotL, roughness);
    
    return ggx1 * ggx2;
}

// ----------------------------------------------------------------------------
// Integrate BRDF for this (NdotV, roughness) pair
// Returns (scale, bias) for Fresnel reconstruction: F0 * scale + bias
// ----------------------------------------------------------------------------
vec2 IntegrateBRDF(float NdotV, float roughness)
{
    // Construct view vector for this NdotV
    vec3 V;
    V.x = sqrt(1.0 - NdotV * NdotV);  // sin(theta)
    V.y = 0.0;
    V.z = NdotV;                       // cos(theta) = NdotV
    
    float A = 0.0;  // Scale (multiplies F0)
    float B = 0.0;  // Bias (added to result)
    
    vec3 N = vec3(0.0, 0.0, 1.0);  // Normal points up in tangent space
    
    for (uint i = 0u; i < SAMPLE_COUNT; ++i)
    {
        vec2 Xi = Hammersley(i, SAMPLE_COUNT);
        vec3 H = ImportanceSampleGGX(Xi, N, roughness);
        vec3 L = normalize(2.0 * dot(V, H) * H - V);
        
        float NdotL = max(L.z, 0.0);
        float NdotH = max(H.z, 0.0);
        float VdotH = max(dot(V, H), 0.0);
        
        if (NdotL > 0.0)
        {
            float G = GeometrySmith(N, V, L, roughness);
            float G_Vis = (G * VdotH) / (NdotH * NdotV);
            float Fc = pow(1.0 - VdotH, 5.0);  // Fresnel Schlick
            
            A += (1.0 - Fc) * G_Vis;
            B += Fc * G_Vis;
        }
    }
    
    A /= float(SAMPLE_COUNT);
    B /= float(SAMPLE_COUNT);
    
    return vec2(A, B);
}

void main()
{
    // v_TexCoords.x = NdotV (0 to 1)
    // v_TexCoords.y = Roughness (0 to 1)
    vec2 integratedBRDF = IntegrateBRDF(v_TexCoords.x, v_TexCoords.y);
    FragColor = integratedBRDF;
}
```

> [!IMPORTANT]
> Note the **different geometry k value** for IBL: $k = \frac{roughness^2}{2}$ vs $k = \frac{(roughness+1)^2}{8}$ for direct lighting. This is per Karis's recommendation for environment lighting.

---

## Step 4: Extend CubemapUtils

**Modify `VizEngine/src/VizEngine/OpenGL/CubemapUtils.h`:**

Add after existing declaration:

```cpp
/**
 * Generate diffuse irradiance cubemap from environment map.
 * Convolves environment over hemisphere for each direction.
 * @param environmentMap Source HDR cubemap
 * @param resolution Resolution per face (32 typical)
 * @return Irradiance cubemap for diffuse IBL
 */
static std::shared_ptr<Texture> GenerateIrradianceMap(
    std::shared_ptr<Texture> environmentMap,
    int resolution = 32
);

/**
 * Generate specular pre-filtered environment map.
 * Each mip level stores environment convolved for that roughness.
 * @param environmentMap Source HDR cubemap
 * @param resolution Base resolution (512 typical)
 * @return Pre-filtered cubemap with roughness in mip chain
 */
static std::shared_ptr<Texture> GeneratePrefilteredMap(
    std::shared_ptr<Texture> environmentMap,
    int resolution = 512
);

/**
 * Generate BRDF integration lookup table.
 * 2D texture storing Fresnel scale/bias indexed by (NdotV, roughness).
 * Environment-independent - generate once, use forever.
 * @param resolution LUT resolution (512 typical)
 * @return 2D RG texture for BRDF lookup
 */
static std::shared_ptr<Texture> GenerateBRDFLUT(int resolution = 512);
```

**Add implementations to `VizEngine/src/VizEngine/OpenGL/CubemapUtils.cpp`:**

```cpp
std::shared_ptr<Texture> CubemapUtils::GenerateIrradianceMap(
    std::shared_ptr<Texture> environmentMap,
    int resolution)
{
    if (!environmentMap || !environmentMap->IsCubemap())
    {
        VP_CORE_ERROR("GenerateIrradianceMap: Input must be a cubemap!");
        return nullptr;
    }

    VP_CORE_INFO("Generating irradiance map ({}x{})...", resolution, resolution);

    // Create empty irradiance cubemap
    auto irradianceMap = std::make_shared<Texture>(resolution, true);
    
    // Create framebuffer
    auto framebuffer = std::make_shared<Framebuffer>(resolution, resolution);
    unsigned int rbo;
    glGenRenderbuffers(1, &rbo);
    glBindRenderbuffer(GL_RENDERBUFFER, rbo);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, resolution, resolution);
    
    framebuffer->Bind();
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, rbo);

    // Load irradiance convolution shader
    auto shader = std::make_shared<Shader>("resources/shaders/irradiance_convolution.shader");
    if (!shader->IsValid())
    {
        VP_CORE_ERROR("Failed to load irradiance_convolution.shader");
        glDeleteRenderbuffers(1, &rbo);
        return nullptr;
    }

    // Capture matrices (same as equirect conversion)
    glm::mat4 captureProjection = glm::perspective(glm::radians(90.0f), 1.0f, 0.1f, 10.0f);
    glm::mat4 captureViews[] = {
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3(-1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  1.0f,  0.0f), glm::vec3(0.0f,  0.0f,  1.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f, -1.0f,  0.0f), glm::vec3(0.0f,  0.0f, -1.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  0.0f,  1.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  0.0f, -1.0f), glm::vec3(0.0f, -1.0f,  0.0f))
    };

    // Cube vertices (same as EquirectangularToCubemap in Chapter 30)
    // See CubemapUtils.cpp for full vertex data
    float cubeVertices[] = {
        -1.0f, -1.0f, -1.0f,   1.0f,  1.0f, -1.0f,   1.0f, -1.0f, -1.0f,
         1.0f,  1.0f, -1.0f,  -1.0f, -1.0f, -1.0f,  -1.0f,  1.0f, -1.0f,
        -1.0f, -1.0f,  1.0f,   1.0f, -1.0f,  1.0f,   1.0f,  1.0f,  1.0f,
         1.0f,  1.0f,  1.0f,  -1.0f,  1.0f,  1.0f,  -1.0f, -1.0f,  1.0f,
        -1.0f,  1.0f,  1.0f,  -1.0f,  1.0f, -1.0f,  -1.0f, -1.0f, -1.0f,
        -1.0f, -1.0f, -1.0f,  -1.0f, -1.0f,  1.0f,  -1.0f,  1.0f,  1.0f,
         1.0f,  1.0f,  1.0f,   1.0f, -1.0f, -1.0f,   1.0f,  1.0f, -1.0f,
         1.0f, -1.0f, -1.0f,   1.0f,  1.0f,  1.0f,   1.0f, -1.0f,  1.0f,
        -1.0f, -1.0f, -1.0f,   1.0f, -1.0f, -1.0f,   1.0f, -1.0f,  1.0f,
         1.0f, -1.0f,  1.0f,  -1.0f, -1.0f,  1.0f,  -1.0f, -1.0f, -1.0f,
        -1.0f,  1.0f, -1.0f,   1.0f,  1.0f,  1.0f,   1.0f,  1.0f, -1.0f,
         1.0f,  1.0f,  1.0f,  -1.0f,  1.0f, -1.0f,  -1.0f,  1.0f,  1.0f
    };
    auto cubeVBO = std::make_shared<VertexBuffer>(cubeVertices, static_cast<unsigned int>(sizeof(cubeVertices)));
    VertexBufferLayout layout;
    layout.Push<float>(3);
    auto cubeVAO = std::make_shared<VertexArray>();
    cubeVAO->LinkVertexBuffer(*cubeVBO, layout);

    shader->Bind();
    shader->SetMatrix4fv("u_Projection", captureProjection);
    environmentMap->Bind(0);
    shader->SetInt("u_EnvironmentMap", 0);

    GLint prevViewport[4];
    glGetIntegerv(GL_VIEWPORT, prevViewport);
    glViewport(0, 0, resolution, resolution);

    for (unsigned int i = 0; i < 6; ++i)
    {
        shader->SetMatrix4fv("u_View", captureViews[i]);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
            GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, irradianceMap->GetID(), 0);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        
        cubeVAO->Bind();
        glDrawArrays(GL_TRIANGLES, 0, 36);
    }

    framebuffer->Unbind();
    glViewport(prevViewport[0], prevViewport[1], prevViewport[2], prevViewport[3]);
    glDeleteRenderbuffers(1, &rbo);

    VP_CORE_INFO("Irradiance map complete!");
    return irradianceMap;
}

std::shared_ptr<Texture> CubemapUtils::GeneratePrefilteredMap(
    std::shared_ptr<Texture> environmentMap,
    int resolution)
{
    if (!environmentMap || !environmentMap->IsCubemap())
    {
        VP_CORE_ERROR("GeneratePrefilteredMap: Input must be a cubemap!");
        return nullptr;
    }

    VP_CORE_INFO("Generating pre-filtered environment map ({}x{})...", resolution, resolution);

    // Create empty cubemap with mipmaps
    auto prefilteredMap = std::make_shared<Texture>(resolution, true);
    
    // Enable mipmaps and allocate mip storage
    glBindTexture(GL_TEXTURE_CUBE_MAP, prefilteredMap->GetID());
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
    glGenerateMipmap(GL_TEXTURE_CUBE_MAP);  // Allocates storage
    glBindTexture(GL_TEXTURE_CUBE_MAP, 0);

    // Load prefilter shader
    auto shader = std::make_shared<Shader>("resources/shaders/prefilter_environment.shader");
    if (!shader->IsValid())
    {
        VP_CORE_ERROR("Failed to load prefilter_environment.shader");
        return nullptr;
    }

    // Capture matrices
    glm::mat4 captureProjection = glm::perspective(glm::radians(90.0f), 1.0f, 0.1f, 10.0f);
    glm::mat4 captureViews[] = {
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3(-1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  1.0f,  0.0f), glm::vec3(0.0f,  0.0f,  1.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f, -1.0f,  0.0f), glm::vec3(0.0f,  0.0f, -1.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  0.0f,  1.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
        glm::lookAt(glm::vec3(0.0f), glm::vec3( 0.0f,  0.0f, -1.0f), glm::vec3(0.0f, -1.0f,  0.0f))
    };

    // Cube vertices (same as GenerateIrradianceMap above)
    float cubeVertices[] = {
        -1.0f, -1.0f, -1.0f,   1.0f,  1.0f, -1.0f,   1.0f, -1.0f, -1.0f,
         1.0f,  1.0f, -1.0f,  -1.0f, -1.0f, -1.0f,  -1.0f,  1.0f, -1.0f,
        -1.0f, -1.0f,  1.0f,   1.0f, -1.0f,  1.0f,   1.0f,  1.0f,  1.0f,
         1.0f,  1.0f,  1.0f,  -1.0f,  1.0f,  1.0f,  -1.0f, -1.0f,  1.0f,
        -1.0f,  1.0f,  1.0f,  -1.0f,  1.0f, -1.0f,  -1.0f, -1.0f, -1.0f,
        -1.0f, -1.0f, -1.0f,  -1.0f, -1.0f,  1.0f,  -1.0f,  1.0f,  1.0f,
         1.0f,  1.0f,  1.0f,   1.0f, -1.0f, -1.0f,   1.0f,  1.0f, -1.0f,
         1.0f, -1.0f, -1.0f,   1.0f,  1.0f,  1.0f,   1.0f, -1.0f,  1.0f,
        -1.0f, -1.0f, -1.0f,   1.0f, -1.0f, -1.0f,   1.0f, -1.0f,  1.0f,
         1.0f, -1.0f,  1.0f,  -1.0f, -1.0f,  1.0f,  -1.0f, -1.0f, -1.0f,
        -1.0f,  1.0f, -1.0f,   1.0f,  1.0f,  1.0f,   1.0f,  1.0f, -1.0f,
         1.0f,  1.0f,  1.0f,  -1.0f,  1.0f, -1.0f,  -1.0f,  1.0f,  1.0f
    };
    auto cubeVBO = std::make_shared<VertexBuffer>(cubeVertices, static_cast<unsigned int>(sizeof(cubeVertices)));
    VertexBufferLayout layout;
    layout.Push<float>(3);
    auto cubeVAO = std::make_shared<VertexArray>();
    cubeVAO->LinkVertexBuffer(*cubeVBO, layout);

    shader->Bind();
    shader->SetMatrix4fv("u_Projection", captureProjection);
    environmentMap->Bind(0);
    shader->SetInt("u_EnvironmentMap", 0);

    // Create framebuffer
    auto framebuffer = std::make_shared<Framebuffer>(resolution, resolution);
    framebuffer->Bind();

    GLint prevViewport[4];
    glGetIntegerv(GL_VIEWPORT, prevViewport);

    unsigned int maxMipLevels = 5;

    // Create one RBO and reuse it across mip levels (resized per mip)
    unsigned int rbo;
    glGenRenderbuffers(1, &rbo);
    glBindRenderbuffer(GL_RENDERBUFFER, rbo);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, resolution, resolution);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, rbo);

    for (unsigned int mip = 0; mip < maxMipLevels; ++mip)
    {
        // Calculate mip dimensions
        unsigned int mipWidth = static_cast<unsigned int>(resolution * std::pow(0.5f, mip));
        unsigned int mipHeight = mipWidth;

        // Resize the existing RBO for this mip level
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, mipWidth, mipHeight);

        glViewport(0, 0, mipWidth, mipHeight);

        // Roughness for this mip level
        float roughness = (float)mip / (float)(maxMipLevels - 1);
        shader->SetFloat("u_Roughness", roughness);

        // Render to each face at this mip level
        for (unsigned int i = 0; i < 6; ++i)
        {
            shader->SetMatrix4fv("u_View", captureViews[i]);
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, prefilteredMap->GetID(), mip);
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

            cubeVAO->Bind();
            glDrawArrays(GL_TRIANGLES, 0, 36);
        }
    }

    glDeleteRenderbuffers(1, &rbo);

    framebuffer->Unbind();
    glViewport(prevViewport[0], prevViewport[1], prevViewport[2], prevViewport[3]);

    VP_CORE_INFO("Pre-filtered environment map complete ({} mip levels)!", maxMipLevels);
    return prefilteredMap;
}

std::shared_ptr<Texture> CubemapUtils::GenerateBRDFLUT(int resolution)
{
    VP_CORE_INFO("Generating BRDF LUT ({}x{})...", resolution, resolution);

    // Create 2D texture (RG16F format for scale + bias)
    auto brdfLUT = std::make_shared<Texture>(
        resolution, resolution, 
        GL_RG16F, GL_RG, GL_FLOAT
    );

    // Load BRDF integration shader
    auto shader = std::make_shared<Shader>("resources/shaders/brdf_integration.shader");
    if (!shader->IsValid())
    {
        VP_CORE_ERROR("Failed to load brdf_integration.shader");
        return nullptr;
    }

    // Create framebuffer
    auto framebuffer = std::make_shared<Framebuffer>(resolution, resolution);
    framebuffer->AttachColorTexture(brdfLUT, 0);
    
    if (!framebuffer->IsComplete())
    {
        VP_CORE_ERROR("BRDF LUT framebuffer incomplete!");
        return nullptr;
    }

    // Fullscreen quad (clip space, position + UV)
    float quadVertices[] = {
        // Positions    // TexCoords
        -1.0f,  1.0f, 0.0f,  0.0f, 1.0f,
        -1.0f, -1.0f, 0.0f,  0.0f, 0.0f,
         1.0f,  1.0f, 0.0f,  1.0f, 1.0f,
         1.0f, -1.0f, 0.0f,  1.0f, 0.0f,
    };
    
    auto quadVBO = std::make_shared<VertexBuffer>(quadVertices, sizeof(quadVertices));
    VertexBufferLayout layout;
    layout.Push<float>(3);  // Position
    layout.Push<float>(2);  // TexCoords
    
    auto quadVAO = std::make_shared<VertexArray>();
    quadVAO->LinkVertexBuffer(*quadVBO, layout);

    GLint prevViewport[4];
    glGetIntegerv(GL_VIEWPORT, prevViewport);

    framebuffer->Bind();
    glViewport(0, 0, resolution, resolution);
    glClear(GL_COLOR_BUFFER_BIT);

    shader->Bind();
    quadVAO->Bind();
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);

    framebuffer->Unbind();
    glViewport(prevViewport[0], prevViewport[1], prevViewport[2], prevViewport[3]);

    VP_CORE_INFO("BRDF LUT complete!");
    return brdfLUT;
}
```

---

## Step 5: Update PBR Shader for IBL

**Modify `VizEngine/src/resources/shaders/defaultlit.shader`:**

Add uniforms after existing IBL-related ones:

```glsl
// ============================================================================
// Image-Based Lighting
// ============================================================================
uniform samplerCube u_IrradianceMap;
uniform samplerCube u_PrefilteredMap;
uniform sampler2D u_BRDF_LUT;
uniform float u_MaxReflectionLOD;
uniform bool u_UseIBL;
uniform float u_IBLIntensity;  // Controls strength of environment lighting (0.0-2.0)
```

Add a new Fresnel-Schlick with roughness function after the existing `FresnelSchlick`:

```glsl
// Fresnel-Schlick with roughness for IBL (accounts for rough surfaces)
vec3 FresnelSchlickRoughness(float cosTheta, vec3 F0, float roughness)
{
    return F0 + (max(vec3(1.0 - roughness), F0) - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}
```

Replace the ambient calculation at the end of `main()`:

```glsl
// ========================================================================
// Ambient Lighting (IBL or fallback)
// ========================================================================
vec3 ambient;

if (u_UseIBL)
{
    // ----- Diffuse IBL -----
    // Use Fresnel with roughness for IBL to account for surface roughness
    vec3 kS_IBL = FresnelSchlickRoughness(max(dot(N, V), 0.0), F0, u_Roughness);
    vec3 kD_IBL = (vec3(1.0) - kS_IBL) * (1.0 - u_Metallic);
    
    vec3 irradiance = texture(u_IrradianceMap, N).rgb;
    vec3 diffuseIBL = irradiance * albedo;
    
    // ----- Specular IBL -----
    vec3 R = reflect(-V, N);
    
    // Sample pre-filtered environment at roughness-appropriate mip level
    vec3 prefilteredColor = textureLod(u_PrefilteredMap, R, 
        u_Roughness * u_MaxReflectionLOD).rgb;
    
    // Look up BRDF integration
    vec2 envBRDF = texture(u_BRDF_LUT, vec2(max(dot(N, V), 0.0), u_Roughness)).rg;
    
    // Reconstruct specular: F0 * scale + bias
    vec3 specularIBL = prefilteredColor * (F0 * envBRDF.x + envBRDF.y);
    
    // ----- Combine -----
    ambient = (kD_IBL * diffuseIBL + specularIBL) * u_AO * u_IBLIntensity;
}
else
{
    // Fallback to simple ambient (Chapter 37 style)
    ambient = vec3(0.03) * albedo * u_AO;
}
```

> [!NOTE]
> We use `FresnelSchlickRoughness` for IBL instead of the standard `FresnelSchlick`. This variant accounts for rough surfaces by clamping the maximum Fresnel value, providing more accurate results for non-shiny materials.

---

## Step 6: SandboxApp Integration

**Modify `Sandbox/src/SandboxApp.h`:**

Add new members:

```cpp
// IBL maps
std::shared_ptr<VizEngine::Texture> m_IrradianceMap;
std::shared_ptr<VizEngine::Texture> m_PrefilteredMap;
std::shared_ptr<VizEngine::Texture> m_BRDFLut;
bool m_UseIBL = true;
float m_IBLIntensity = 0.3f;  // Balance between direct and ambient lighting
```

**Modify `Sandbox/src/SandboxApp.cpp` `OnCreate()`:**

After environment cubemap generation:

```cpp
// ============================================================================
// Generate IBL Maps (one-time cost at startup)
// ============================================================================
auto iblStart = std::chrono::high_resolution_clock::now();

m_IrradianceMap = VizEngine::CubemapUtils::GenerateIrradianceMap(m_SkyboxCubemap, 32);
m_PrefilteredMap = VizEngine::CubemapUtils::GeneratePrefilteredMap(m_SkyboxCubemap, 512);
m_BRDFLut = VizEngine::CubemapUtils::GenerateBRDFLUT(512);

auto iblEnd = std::chrono::high_resolution_clock::now();
auto iblDuration = std::chrono::duration_cast<std::chrono::milliseconds>(iblEnd - iblStart);
VP_CORE_INFO("IBL maps generated in {}ms", iblDuration.count());
```

**Modify `Sandbox/src/SandboxApp.cpp` `OnRender()`:**

Before the scene rendering loop, bind IBL textures:

```cpp
// Bind IBL textures if enabled
if (m_UseIBL && m_IrradianceMap && m_PrefilteredMap && m_BRDFLut)
{
    m_IrradianceMap->Bind(5);
    m_DefaultLitShader->SetInt("u_IrradianceMap", 5);

    m_PrefilteredMap->Bind(6);
    m_DefaultLitShader->SetInt("u_PrefilteredMap", 6);

    m_BRDFLut->Bind(7);
    m_DefaultLitShader->SetInt("u_BRDF_LUT", 7);

    m_DefaultLitShader->SetFloat("u_MaxReflectionLOD", 4.0f);  // maxMipLevels - 1
    m_DefaultLitShader->SetBool("u_UseIBL", true);
    m_DefaultLitShader->SetFloat("u_IBLIntensity", m_IBLIntensity);
}
else
{
    m_DefaultLitShader->SetBool("u_UseIBL", false);
    m_DefaultLitShader->SetFloat("u_IBLIntensity", 0.0f);
}
```

**Modify `Sandbox/src/SandboxApp.cpp` `OnImGuiRender()`:**

Add IBL controls:

```cpp
if (ImGui::CollapsingHeader("Image-Based Lighting"))
{
    ImGui::Checkbox("Use IBL", &m_UseIBL);
    ImGui::SliderFloat("IBL Intensity", &m_IBLIntensity, 0.0f, 2.0f);

    if (m_IrradianceMap && m_PrefilteredMap && m_BRDFLut)
    {
        ImGui::Text("Irradiance: 32x32 cubemap");
        ImGui::Text("Prefiltered: 512x512 cubemap (5 mips)");
        ImGui::Text("BRDF LUT: 512x512 RG texture");
    }
    else
    {
        ImGui::TextColored(ImVec4(1.0f, 0.3f, 0.3f, 1.0f), "IBL maps not generated!");
    }
}
```

---

## Testing and Validation

### Visual Validation

After implementing IBL, you should see dramatic improvements:

| Test | Without IBL | With IBL |
|------|-------------|----------|
| **Metallic sphere** | Only direct lighting highlights | Environment visible in reflection |
| **Rough dielectric** | Flat ambient tint | Soft environment color bleed |
| **Grazing angles** | No Fresnel brightening in ambient | Environment brightens at edges |
| **Shadow areas** | Unnaturally dark | Natural environment-lit fill |

### Material Ball Test

Create a grid of spheres varying metallic (0→1) and roughness (0→1):

- **Metallic=0, Roughness=0**: Shiny plastic with environment Fresnel
- **Metallic=0, Roughness=1**: Matte surface with diffuse environment color
- **Metallic=1, Roughness=0**: Perfect mirror showing sharp environment
- **Metallic=1, Roughness=1**: Rough metal with blurred tinted reflection

### Performance Benchmarks

| Operation | Expected Time |
|-----------|---------------|
| **Irradiance generation** | ~500ms (32×32, many samples) |
| **Prefiltered generation** | ~2-3s (512×512, 5 mips, 1024 samples per texel) |
| **BRDF LUT generation** | ~200ms (512×512, 1024 samples per texel) |
| **Total startup cost** | ~3-4 seconds (one-time) |
| **Runtime per frame** | ~0.1ms (3 texture lookups) |

### Memory Usage

| Texture | Size |
|---------|------|
| **Irradiance** | 32×32×6 × RGB16F = ~36 KB |
| **Prefiltered** | 512×512×6 × RGB16F + mips ≈ 9 MB |
| **BRDF LUT** | 512×512 × RG16F = 1 MB |
| **Total** | ~10 MB |

---

## Common Issues and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| **Black/missing reflections** | IBL textures not bound | Check texture binding order (slots 5, 6, 7) |
| **Too dark with IBL** | Missing diffuse IBL | Verify `u_IrradianceMap` sampling works |
| **Scene looks flat/washed out** | IBL ambient too strong | Lower `u_IBLIntensity` (try 0.2-0.5) |
| **No contrast between light/shadow** | IBL overwhelming direct lights | Reduce IBL intensity or increase direct light intensity |
| **Seams in irradiance** | Hemisphere sampling incomplete | Check theta range is `[0, π/2]` |
| **Blocky prefilter** | Too few samples | Increase `SAMPLE_COUNT` in shader |
| **Wrong roughness response** | Mip level miscalculation | Verify `roughness * maxMipLevels` in lookup |
| **Pink/NaN artifacts** | Texture format wrong | Ensure `GL_RGB16F` for cubemaps |
| **Metals look plastic** | F0 not tinted | Verify `F0 = mix(0.04, albedo, metallic)` |

### Debug Visualization

Add debug modes to verify each IBL component:

```glsl
// Debug: visualize irradiance only
FragColor = vec4(texture(u_IrradianceMap, N).rgb, 1.0);

// Debug: visualize prefiltered at roughness level
FragColor = vec4(textureLod(u_PrefilteredMap, N, u_Roughness * 4.0).rgb, 1.0);

// Debug: visualize BRDF LUT lookup
FragColor = vec4(texture(u_BRDF_LUT, vec2(dot(N, V), u_Roughness)).rg, 0.0, 1.0);
```

---

## Lower Hemisphere Fallback

### The Problem with Flat Metallic Surfaces

After implementing IBL, you may notice that flat metallic surfaces (like a cube face) can appear completely black when facing certain directions. This is actually **physically correct**—a flat mirror reflects what's in front of it, and if that direction points to a dark area of the environment (like below the horizon), you see dark.

**Curved surfaces** (spheres, duck) always have areas at grazing angles where the Fresnel effect kicks in, producing bright highlights regardless of reflection direction. **Flat surfaces** don't have this gradation—they show the raw environment reflection.

### Why Engines Like Unreal Don't Have This Issue

Professional engines use multiple reflection techniques layered together:

| Technique | Description |
|-----------|-------------|
| **Screen Space Reflections (SSR)** | Traces rays in screen space to reflect visible objects |
| **Reflection Capture Probes** | Local cubemaps placed throughout the scene |
| **Planar Reflections** | Renders scene from mirrored camera for flat surfaces |
| **Lower Hemisphere Color** | Fallback color for reflections pointing below horizon |

For our simple IBL implementation, we add a **lower hemisphere color** as a quick, effective solution.

### Implementation

Add uniforms for the reflection fallback:

```glsl
// Lower hemisphere fallback (prevents black reflections on flat surfaces)
uniform vec3 u_LowerHemisphereColor;  // Color for reflections pointing below horizon
uniform float u_LowerHemisphereIntensity;  // Blend intensity (0 = off, 1 = full)
```

Add helper functions for environment sampling with fallback. The implementation uses two strategies:
1. **Direction-based**: Blend fallback color when reflection points below horizon
2. **Darkness-based**: Detect dark environment samples and blend fallback regardless of direction

```glsl
// ----------------------------------------------------------------------------
// Environment Reflection Fallback
// Provides a minimum reflection floor to prevent pure black reflections on
// flat metallic surfaces. Works in two ways:
// 1. Blends in fallback color for downward-facing reflections (below horizon)
// 2. Adds minimum ambient to ALL dark reflections (prevents black regardless of direction)
// ----------------------------------------------------------------------------
vec3 SampleEnvironmentWithFallback(samplerCube envMap, vec3 direction, float lod)
{
    vec3 envColor = textureLod(envMap, direction, lod).rgb;

    // Calculate luminance of the environment sample
    float envLuminance = dot(envColor, vec3(0.2126, 0.7152, 0.0722));

    // Fallback color (what we blend in when environment is dark)
    vec3 fallbackColor = u_LowerHemisphereColor;

    // Factor 1: How much the direction points below horizon
    float downFactor = max(-direction.y, 0.0);  // 0 at horizon, 1 pointing straight down
    downFactor = smoothstep(0.0, 0.5, downFactor);

    // Factor 2: How dark is the environment sample (inverse luminance)
    // This ensures even horizontal reflections into dark areas get some color
    float darknessFactor = 1.0 - smoothstep(0.0, 0.1, envLuminance);

    // Combine factors: use whichever is stronger
    float blendFactor = max(downFactor, darknessFactor * 0.7) * u_LowerHemisphereIntensity;

    return mix(envColor, fallbackColor, blendFactor);
}

vec3 SampleIrradianceWithFallback(samplerCube irrMap, vec3 normal)
{
    vec3 irrColor = texture(irrMap, normal).rgb;

    // Calculate luminance
    float irrLuminance = dot(irrColor, vec3(0.2126, 0.7152, 0.0722));

    // Fallback color (dimmer for diffuse)
    vec3 fallbackColor = u_LowerHemisphereColor * 0.5;

    // Factor 1: Normals pointing down
    float downFactor = max(-normal.y, 0.0);
    downFactor = smoothstep(0.0, 0.5, downFactor);

    // Factor 2: Dark irradiance samples
    float darknessFactor = 1.0 - smoothstep(0.0, 0.05, irrLuminance);

    // Combine factors
    float blendFactor = max(downFactor, darknessFactor * 0.5) * u_LowerHemisphereIntensity;

    return mix(irrColor, fallbackColor, blendFactor);
}
```

Update the IBL sampling in the main function, including a **minimum metallic reflection floor** that bypasses the BRDF for shiny metals:

```glsl
// Sample irradiance with fallback
vec3 irradiance = SampleIrradianceWithFallback(u_IrradianceMap, N);
vec3 diffuseIBL = irradiance * albedo;

// Sample pre-filtered environment with fallback
float mipLevel = u_Roughness * u_MaxReflectionLOD;
vec3 prefilteredColor = SampleEnvironmentWithFallback(u_PrefilteredMap, R, mipLevel);

// Look up BRDF integration
vec2 envBRDF = texture(u_BRDF_LUT, vec2(max(dot(N, V), 0.0), u_Roughness)).rg;

// Reconstruct specular: F0 * scale + bias
vec3 specularIBL = prefilteredColor * (F0 * envBRDF.x + envBRDF.y);

// ----- Minimum Metallic Reflection Floor -----
// For highly metallic surfaces, ensure a minimum reflection based on the fallback color
// This prevents pure black even when environment and BRDF combine to near-zero
float metallicFactor = u_Metallic * (1.0 - u_Roughness);  // Strongest for shiny metals
vec3 minReflection = u_LowerHemisphereColor * F0 * metallicFactor * u_LowerHemisphereIntensity;
specularIBL = max(specularIBL, minReflection);
```

> [!WARNING]
> **This is an approximation, not physically accurate.** The minimum metallic reflection floor bypasses the BRDF integration to guarantee visible reflections on shiny metals. This is a common technique in real-time rendering where visual quality takes precedence over physical accuracy.

### PBRMaterial API

Add lower hemisphere support to `PBRMaterial`:

```cpp
// PBRMaterial.h
void SetLowerHemisphereColor(const glm::vec3& color);
glm::vec3 GetLowerHemisphereColor() const;
void SetLowerHemisphereIntensity(float intensity);
float GetLowerHemisphereIntensity() const;

// Member variables
glm::vec3 m_LowerHemisphereColor = glm::vec3(0.1f, 0.1f, 0.15f);  // Slightly blue-ish
float m_LowerHemisphereIntensity = 0.5f;
```

### UI Controls

Add controls in the IBL panel:

```cpp
uiManager.Separator();
uiManager.Text("Lower Hemisphere");
uiManager.ColorEdit3("Ground Color", &m_LowerHemisphereColor.x);
uiManager.SliderFloat("Ground Intensity", &m_LowerHemisphereIntensity, 0.0f, 2.0f);
```

### How It Works

The fallback system has three layers of protection against black reflections:

| Layer | Trigger | Effect |
|-------|---------|--------|
| **Direction-based** | Reflection points below horizon (R.y < 0) | Blends in fallback color |
| **Darkness-based** | Environment sample luminance near zero | Blends in fallback color |
| **Metallic floor** | High metallic + low roughness | Guarantees minimum reflection |

### Results

| Before | After |
|--------|-------|
| Flat metallic cube = **pure black** | Flat metallic cube = **visible reflection** |
| Vertical walls reflecting dark areas = **black** | Vertical walls = **fallback color** |
| Only Fresnel at curved edges visible | Full surface shows some reflection |

### Trade-offs

| Aspect | Reality |
|--------|---------|
| **Physically accurate?** | No - this is an approximation |
| **Why do it anyway?** | Pure black metals look wrong to human eyes |
| **Production engines?** | Use the same technique as a fallback layer |
| **Better alternatives?** | SSR, reflection probes (Part XII, Chapters 43-46) |

> [!NOTE]
> This is a common real-time rendering approximation. The "minimum metallic reflection floor" bypasses the BRDF to guarantee visibility. For production quality, layer this with Screen Space Reflections (SSR) or reflection probes, covered in **Chapter 45 (Screen-Space Reflections) and Chapter 46 (Reflection Probes)**.

---

## Milestone

**Chapter 38 Complete - Image-Based Lighting**

You have implemented:
- **Diffuse irradiance map** - Hemisphere-convolved environment for diffuse ambient
- **Specular pre-filtered map** - Roughness-mipped cubemap for specular reflections
- **BRDF integration LUT** - Universal Fresnel scale/bias lookup
- **Split-sum approximation** - Real-time IBL matching Unreal Engine's approach
- **Reflection fallback system** - Three-layer protection against black reflections:
  - Direction-based fallback for below-horizon reflections
  - Darkness detection for any dark environment samples
  - Minimum metallic floor for shiny metals
- **Full PBR pipeline** - Direct + ambient lighting with physically-based materials

Your engine now renders materials that respond correctly to **both** direct lighting and environment lighting—the same approach used by AAA game engines.

> [!TIP]
> The reflection fallback is an approximation technique common in real-time rendering. For production-quality reflections, see **Part XII (Chapters 43-46)** which covers Screen Space Reflections (SSR), reflection probes, and planar reflections.

---

## References

This chapter implementation is based on:

1. **Brian Karis, "Real Shading in Unreal Engine 4"**, SIGGRAPH 2013 - Split-sum approximation
2. **Joey de Vries, LearnOpenGL IBL Tutorial** - Implementation reference
3. **Khronos glTF 2.0 IBL Specification** - Industry standard
4. **Google Filament Renderer** - Production IBL implementation

---

## What's Next

In **Chapter 39: HDR Pipeline**, we'll move tone mapping and exposure control from the shader to a dedicated post-processing pass, enabling more sophisticated HDR effects like bloom and proper exposure adjustment.

> **Next:** [Chapter 39: HDR Pipeline](39_HDRPipeline.md)

> **Previous:** [Chapter 37: PBR Implementation](37_PBRImplementation.md)

> **Index:** [Table of Contents](INDEX.md)
