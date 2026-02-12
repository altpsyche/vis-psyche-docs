\newpage

# Chapter 39: HDR Pipeline

Implement a complete High Dynamic Range rendering pipeline with floating-point framebuffers, multiple tone mapping operators, and automatic exposure control.

---

## Introduction

In **Chapters 37-38**, we implemented physically-based rendering with Cook-Torrance BRDF and image-based lighting. Our PBR calculations produce **High Dynamic Range (HDR)** values—colors that can exceed the traditional [0, 1] range. A bright metal surface in sunlight might have a specular value of 50.0 or higher, while a dark shadow might be 0.001.

**The problem**: Standard displays can only show colors in the [0, 1] range. Our current shader includes basic Reinhard tone mapping (line 381 in `defaultlit.shader`):

```glsl
// Reinhard tone mapping (simple, will be improved in Chapter 39)
color = color / (color + vec3(1.0));
```

This works, but it's applied **inside the PBR shader**, which limits our flexibility. We can't adjust exposure, switch tone mapping operators, or apply post-processing effects.

**The solution**: A proper HDR pipeline that separates rendering from tone mapping:

```
Scene Rendering → HDR Framebuffer (RGB16F) → Tone Mapping Pass → LDR Display (sRGB)
     ↓                    ↓                           ↓                ↓
  PBR + IBL          Stores [0, ∞) values      Maps to [0,1]      Monitor output
```

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **HDR Framebuffer** | RGB16F floating-point color attachment for unlimited range |
| **Tone Mapping Shader** | Multiple operators: Reinhard, Exposure, ACES, Uncharted 2 |
| **Exposure Control** | Manual exposure adjustment (f-stops) and automatic adaptation |
| **Two-Pass Rendering** | Scene to HDR buffer, then tone map to screen |
| **ImGui Controls** | Real-time operator selection, exposure, and gamma adjustment |
| **Gamma Correction** | Proper linear → sRGB conversion after tone mapping |

**End result**: Industry-standard HDR workflow used by Unreal Engine, Unity, and modern AAA games.

---

## Why HDR?

### The Problem with LDR

Traditional **Low Dynamic Range (LDR)** rendering uses 8-bit color channels (0-255), normalized to [0, 1]:

```cpp
// LDR framebuffer
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
```

**What this means**:
- 0.0 = black
- 1.0 = white
- Everything must fit in this range

**Real-world light doesn't work this way**:
- Sunlight: ~100,000 lux
- Indoor lighting: ~100-500 lux
- Moonlight: ~0.1 lux

Forcing all these into [0, 1] loses information. A bright specular highlight (value 50.0) and a slightly brighter one (value 100.0) both clamp to 1.0—indistinguishable white.

### PBR Needs HDR

Physically-based rendering **inherently produces HDR values**:

```glsl
// From defaultlit.shader (Chapter 37)
vec3 radiance = u_LightColors[i] * attenuation;  // Can be >> 1.0
vec3 specular = (D * F * G) / denominator;        // Can be >> 1.0
Lo += (diffuse + specular) * radiance * NdotL;    // Accumulates HDR values
```

**Examples of HDR values in PBR**:
- **Bright metal in sunlight**: Specular peak = 50-200
- **IBL from bright HDRI**: Irradiance = 5-20
- **Multiple lights**: Accumulation can easily exceed 10.0

**Without HDR**, all these values clamp to 1.0, losing the subtle gradations that make materials look realistic.

### Visual Comparison

| LDR (Clamped) | HDR (Preserved) |
|---------------|-----------------|
| Bright areas → pure white | Bright areas → smooth gradation to white |
| Loss of detail in highlights | Detail preserved in all ranges |
| Harsh transitions | Smooth, natural transitions |
| Unrealistic specular | Film-like specular rolloff |

---

## Floating-Point Framebuffers

### Format Comparison

OpenGL supports several framebuffer formats:

| Format | Channels | Bits/Channel | Range | Memory/Pixel | Use Case |
|--------|----------|--------------|-------|--------------|----------|
| `GL_RGBA8` | RGBA | 8 (integer) | [0, 1] | 4 bytes | LDR rendering |
| `GL_RGBA16F` | RGBA | 16 (half-float) | [-65504, 65504] | 8 bytes | **HDR rendering (recommended)** |
| `GL_RGBA32F` | RGBA | 32 (full float) | [±3.4×10³⁸] | 16 bytes | High precision (compute shaders) |
| `GL_RGB16F` | RGB | 16 (half-float) | [-65504, 65504] | 6 bytes | HDR without alpha |

### Why RGB16F?

**Precision vs Performance**:
- **RGB16F** (half-float): 16 bits per channel
  - Range: ±65,504 (more than enough for HDR)
  - Precision: ~3 decimal digits
  - Memory: 6 bytes/pixel (50% more than RGBA8)
  - Performance: Excellent on modern GPUs

- **RGB32F** (full float): 32 bits per channel
  - Range: ±3.4×10³⁸ (overkill for rendering)
  - Precision: ~7 decimal digits
  - Memory: 12 bytes/pixel (3× RGBA8)
  - Performance: Slower due to bandwidth

**Recommendation**: Use `GL_RGB16F` for HDR rendering. It provides sufficient range and precision while maintaining good performance. Only use `GL_RGB32F` if you encounter banding or precision issues (rare in practice).

> [!NOTE]
> **Memory Cost**: An 1920×1080 HDR framebuffer with RGB16F uses ~12 MB (vs 8 MB for RGBA8). This is acceptable for the quality improvement.

---

## HDR Rendering Pipeline

### The Two-Pass Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  Pass 1: Scene Rendering (HDR)                                  │
│  ┌──────────────┐                                               │
│  │ PBR Shader   │ → HDR Framebuffer (RGB16F)                    │
│  │ + IBL        │    Stores values [0, ∞)                       │
│  └──────────────┘    No clamping, no tone mapping               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Pass 2: Tone Mapping (LDR)                                     │
│  ┌──────────────┐                                               │
│  │ Tone Mapping │ → Default Framebuffer (screen)                │
│  │ Shader       │    Maps HDR [0, ∞) → LDR [0, 1]               │
│  └──────────────┘    Applies gamma correction                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: Rendering and display are **separate concerns**. We render in linear HDR space (physically correct), then convert to display space (perceptually correct).

### Why Separate Passes?

**Flexibility**:
- Switch tone mapping operators in real-time
- Adjust exposure without re-rendering
- Apply post-processing effects (bloom, color grading) to HDR buffer
- Save HDR buffer for later processing

**Performance**:
- Tone mapping is cheap (one fullscreen quad)
- Can use different resolutions (render at 4K, display at 1080p)

---

## Tone Mapping Theory

### The Problem

We have HDR values (e.g., 50.0) that must fit in the display range [0, 1]. Naive clamping loses information:

```glsl
// BAD: Naive clamping
color = clamp(hdrColor, 0.0, 1.0);  // Everything > 1.0 becomes pure white
```

**Tone mapping** compresses the HDR range while preserving perceptual detail.

### Desirable Properties

A good tone mapping operator should:
1. **Preserve blacks**: Dark values stay dark (no lifting)
2. **Preserve highlights**: Bright values don't clip to pure white
3. **Smooth rolloff**: Gradual compression (no harsh transitions)
4. **Perceptually pleasing**: Film-like, natural appearance
5. **Tunable**: Artist control over brightness and contrast

---

## Tone Mapping Operators

### 1. Reinhard (Simple)

**Formula**:
$$L_{out} = \frac{L_{in}}{1 + L_{in}}$$

**GLSL Implementation**:
```glsl
vec3 ReinhardToneMapping(vec3 color)
{
    return color / (color + vec3(1.0));
}
```

**Characteristics**:
- **Pros**: Extremely simple, smooth, never exceeds 1.0
- **Cons**: Can be too flat, all bright values compress toward 1.0
- **Visual**: Soft, slightly desaturated, low contrast
- **Use case**: Quick preview, educational purposes

**Source**: Reinhard et al., "Tone Reproduction for Realistic Images" (2002)

---

### 2. Reinhard Extended (White Point)

**Formula**:
$$L_{out} = \frac{L_{in} \cdot (1 + \frac{L_{in}}{L_{white}^2})}{1 + L_{in}}$$

**GLSL Implementation**:
```glsl
vec3 ReinhardExtendedToneMapping(vec3 color, float whitePoint)
{
    vec3 numerator = color * (1.0 + (color / (whitePoint * whitePoint)));
    return numerator / (1.0 + color);
}
```

**Characteristics**:
- **Pros**: Control over what maps to pure white
- **Cons**: More complex, needs tuning
- **Visual**: More control over bright regions than simple Reinhard
- **Use case**: When you need to preserve specific bright values

**Parameters**:
- `whitePoint`: Luminance value that maps to 1.0 (typical: 4.0-11.2)

---

### 3. Exposure-Based (Photographer's)

**Formula**:
$$L_{out} = 1 - e^{-L_{in} \cdot exposure}$$

**GLSL Implementation**:
```glsl
vec3 ExposureToneMapping(vec3 color, float exposure)
{
    return vec3(1.0) - exp(-color * exposure);
}
```

**Characteristics**:
- **Pros**: Intuitive (like camera exposure stops), simple, natural
- **Cons**: Can crush blacks or blow highlights if exposure is wrong
- **Visual**: Camera-like, natural response
- **Use case**: When you want artist control over brightness

**Exposure Values**:
- `1.0` = normal exposure
- `2.0` = +1 stop (2× brighter)
- `0.5` = -1 stop (2× darker)
- Typical range: 0.5 to 4.0

**Source**: Standard photographic exposure formula

---

### 4. ACES Filmic (Industry Standard)

**The Stephen Hill Fitted Curve** provides more accurate results than simpler approximations. It includes proper color space transforms (sRGB → ACES AP1 → sRGB) and the RRT+ODT fit for better contrast and color preservation.

**GLSL Implementation**:
```glsl
// sRGB => XYZ => D65_2_D60 => AP1 => RRT_SAT
const mat3 ACESInputMat = mat3(
    0.59719, 0.07600, 0.02840,
    0.35458, 0.90834, 0.13383,
    0.04823, 0.01566, 0.83777
);

// ODT_SAT => XYZ => D60_2_D65 => sRGB
const mat3 ACESOutputMat = mat3(
     1.60475, -0.10208, -0.00327,
    -0.53108,  1.10813, -0.07276,
    -0.07367, -0.00605,  1.07602
);

vec3 RRTAndODTFit(vec3 v)
{
    vec3 a = v * (v + 0.0245786) - 0.000090537;
    vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081;
    return a / b;
}

vec3 ACESFilmic(vec3 color)
{
    color = ACESInputMat * color;
    color = RRTAndODTFit(color);
    color = ACESOutputMat * color;
    return clamp(color, 0.0, 1.0);
}
```

**Characteristics**:
- **Pros**: Film-like contrast, industry-standard, excellent highlight rolloff, proper color space handling
- **Cons**: More complex, requires matrix multiplications
- **Visual**: Cinematic, deep blacks, saturated colors, smooth highlight compression
- **Use case**: Production rendering, when you want a filmic look

**Used by**: Unreal Engine, Unity, many AAA games

**Source**: Stephen Hill, "ACES Fitted" (based on the Academy Color Encoding System)

> [!IMPORTANT]
> ACES is the **recommended default** for production. The Stephen Hill curve provides better contrast and color saturation than simpler approximations like Narkowicz.

---

### 5. Uncharted 2 (Hable)

**Formula** (shoulder function):
$$f(x) = \frac{x \cdot (A \cdot x + C \cdot B) + D \cdot E}{x \cdot (A \cdot x + B) + D \cdot F} - \frac{E}{F}$$

**GLSL Implementation**:
```glsl
vec3 Uncharted2ToneMapping(vec3 color)
{
    float A = 0.15;  // Shoulder strength
    float B = 0.50;  // Linear strength
    float C = 0.10;  // Linear angle
    float D = 0.20;  // Toe strength
    float E = 0.02;  // Toe numerator
    float F = 0.30;  // Toe denominator
    float W = 11.2;  // Linear white point
    
    // Apply curve to color
    vec3 curr = ((color * (A * color + C * B) + D * E) / 
                 (color * (A * color + B) + D * F)) - E / F;
    
    // Apply curve to white point
    float white = ((W * (A * W + C * B) + D * E) / 
                   (W * (A * W + B) + D * F)) - E / F;
    
    return curr / white;
}
```

**Characteristics**:
- **Pros**: Excellent highlight preservation, filmic look, tunable parameters
- **Cons**: Most complex, many parameters to understand
- **Visual**: Video game industry favorite, strong shoulder (smooth highlight rolloff)
- **Use case**: When ACES is too flat or you need more control

**Parameters** (Hable's defaults):
- `A` (Shoulder Strength): Controls how quickly highlights compress
- `B` (Linear Strength): Affects mid-tone contrast
- `C` (Linear Angle): Adjusts the linear section slope
- `D` (Toe Strength): Controls shadow compression
- `E`, `F` (Toe Numerator/Denominator): Fine-tune shadow behavior
- `W` (White Point): What luminance maps to pure white

**Source**: John Hable, "Filmic Tonemapping Operators" (GDC 2010)

---

### Operator Comparison

| Operator | Complexity | Visual Style | Tuning | Best For |
|----------|-----------|--------------|--------|----------|
| **Reinhard** | Very Simple | Soft, flat | None | Learning, previews |
| **Reinhard Extended** | Simple | Controlled highlights | White point | Specific bright values |
| **Exposure** | Simple | Natural, camera-like | Exposure value | Artist control |
| **ACES Filmic** | Medium | Cinematic, industry-standard | None | **Production (recommended)** |
| **Uncharted 2** | Complex | Filmic, strong shoulder | 7 parameters | Advanced tuning |

**Recommendation**: Start with **ACES** for production. Use **Exposure** when artists need brightness control. Use **Uncharted 2** only if you need specific curve shaping.

---

## Gamma Correction

### Linear vs Gamma Space

**Linear space**: Where lighting calculations happen (PBR, IBL)
- Math is physically correct
- Values represent actual light energy
- Example: 2.0 is twice as bright as 1.0

**Gamma space**: Where monitors display (sRGB ~2.2 gamma)
- Compensates for CRT phosphor response (historical)
- Modern displays emulate this for compatibility
- Example: 0.5 in gamma space ≠ half brightness

### The Conversion

**Linear → Gamma (sRGB)**:
$$color_{sRGB} = color_{linear}^{1/2.2}$$

**GLSL Implementation**:
```glsl
vec3 GammaCorrection(vec3 color, float gamma)
{
    return pow(color, vec3(1.0 / gamma));
}
```

**Typical gamma value**: 2.2 (standard sRGB)

### Pipeline Placement

**Critical**: Apply gamma correction **AFTER** tone mapping:

```glsl
// CORRECT order
vec3 hdrColor = texture(u_HDRBuffer, texCoords).rgb;
vec3 ldrColor = ACESFilmic(hdrColor);           // Tone map: HDR → LDR
vec3 srgbColor = pow(ldrColor, vec3(1.0/2.2));  // Gamma correct: Linear → sRGB
FragColor = vec4(srgbColor, 1.0);

// WRONG order (don't do this)
vec3 srgbColor = pow(hdrColor, vec3(1.0/2.2));  // Gamma first = wrong
vec3 ldrColor = ACESFilmic(srgbColor);          // Tone map after = broken
```

**Why this order?**
- Tone mapping operates on **linear light values**
- Gamma correction is a **display transform**, not a lighting operation
- Applying gamma first breaks the tone mapping math

> [!WARNING]
> If your image looks too dark or washed out, check that gamma correction is applied **after** tone mapping, not before.

---

## Exposure Control

### Manual Exposure

**Concept**: Simulate camera exposure adjustment (f-stops).

**Implementation**:
```glsl
vec3 exposedColor = hdrColor * exposure;
vec3 ldrColor = ACESFilmic(exposedColor);
```

**Exposure values**:
- `exposure = 1.0`: Normal (no change)
- `exposure = 2.0`: +1 stop (2× brighter)
- `exposure = 0.5`: -1 stop (2× darker)
- `exposure = 4.0`: +2 stops (4× brighter)

**Use case**: Artist control, consistent results, cinematic control

---

### Automatic Exposure (Eye Adaptation)

**Concept**: Simulate how the human eye adapts to different light levels.

#### Theory

The human eye adjusts its sensitivity based on the average brightness of the scene:
- **Bright scene** (outdoors): Eye reduces sensitivity (contracts pupil)
- **Dark scene** (indoors): Eye increases sensitivity (dilates pupil)
- **Transition**: Adaptation takes time (temporal smoothing)

#### Implementation Steps

**Step 1: Calculate Average Luminance**

Convert RGB to luminance using the standard formula:
$$L = 0.2126 \cdot R + 0.7152 \cdot G + 0.0722 \cdot B$$

**Step 2: Downsample HDR Buffer**

Create a mipmap chain to efficiently compute average:
```cpp
// Generate mipmaps for HDR texture
glBindTexture(GL_TEXTURE_2D, hdrTexture);
glGenerateMipmap(GL_TEXTURE_2D);

// Sample the smallest mip level (1×1 pixel) = average color
vec3 avgColor = textureLod(u_HDRBuffer, vec2(0.5), maxMipLevel).rgb;
float avgLuminance = dot(avgColor, vec3(0.2126, 0.7152, 0.0722));
```

**Step 3: Calculate Target Exposure**

```glsl
// Target middle gray (18% reflectance, photographic standard)
float targetLuminance = 0.18;

// Calculate exposure to map average luminance to target
float exposure = targetLuminance / (avgLuminance + 0.001);  // +epsilon to avoid divide by zero

// Clamp to reasonable range
exposure = clamp(exposure, 0.1, 10.0);
```

**Step 4: Temporal Smoothing (Eye Adaptation)**

Smooth exposure changes over time to simulate eye adaptation:

```glsl
// In shader (requires previous frame's exposure)
uniform float u_PreviousExposure;
uniform float u_DeltaTime;

float adaptationSpeed = 2.0;  // Higher = faster adaptation
float newExposure = mix(u_PreviousExposure, targetExposure, 
                        1.0 - exp(-u_DeltaTime * adaptationSpeed));
```

**In C++ (per-frame update)**:
```cpp
// Calculate target exposure from scene luminance
float targetExposure = 0.18f / (avgLuminance + 0.001f);
targetExposure = glm::clamp(targetExposure, 0.1f, 10.0f);

// Smooth transition
float adaptationSpeed = 2.0f;  // Adjust for faster/slower adaptation
m_CurrentExposure = glm::mix(m_CurrentExposure, targetExposure, 
                             1.0f - exp(-deltaTime * adaptationSpeed));
```

#### Adaptation Speed

**Typical values**:
- `adaptationSpeed = 1.0`: Slow adaptation (1-2 seconds)
- `adaptationSpeed = 2.0`: Medium adaptation (~1 second)
- `adaptationSpeed = 5.0`: Fast adaptation (~0.5 seconds)

**Realistic behavior**:
- **Dark → Bright**: Faster adaptation (eyes contract quickly)
- **Bright → Dark**: Slower adaptation (eyes dilate slowly)

```cpp
// Asymmetric adaptation (more realistic)
float adaptSpeed = (targetExposure < m_CurrentExposure) ? 
                   3.0f :  // Bright to dark (slower)
                   1.5f;   // Dark to bright (faster)
```

#### Alternative: Histogram-Based Exposure

For more control, analyze the luminance histogram:

```glsl
// Create 256-bin histogram of log luminance
// Find median or percentile (e.g., 50th percentile)
// Use as target luminance

// This prevents extreme values from skewing the average
// Used by Unreal Engine's "Auto Exposure Histogram" mode
```

**Pros**: More robust to outliers (bright sun, dark shadows)  
**Cons**: More complex, requires compute shader

> [!NOTE]
> **Advanced Topic**: Full histogram-based exposure is beyond this chapter's scope. The mipmap-based average luminance method works well for most cases and is used by many games.

---

## Step 1: Remove Tone Mapping from PBR Shader

Our current `defaultlit.shader` applies tone mapping and gamma correction at the end. We need to remove this so the shader outputs **raw HDR values**.

**Modify `VizEngine/src/resources/shaders/defaultlit.shader`:**

Find the end of the fragment shader (lines 376-386):

```glsl
vec3 color = ambient + Lo;

// ========================================================================
// Tone Mapping and Gamma Correction
// ========================================================================

// Reinhard tone mapping (simple, will be improved in Chapter 39)
color = color / (color + vec3(1.0));

// Gamma correction (linear -> sRGB)
color = pow(color, vec3(1.0 / 2.2));

FragColor = vec4(color, 1.0);
```

**Replace with**:

```glsl
vec3 color = ambient + Lo;

// ========================================================================
// Output HDR Color (Chapter 39: Tone mapping moved to separate pass)
// ========================================================================

// Output raw linear HDR values (no tone mapping, no gamma correction)
// These will be processed by the tone mapping shader
FragColor = vec4(color, 1.0);
```

**Why?**
- Tone mapping and gamma correction now happen in a dedicated post-processing pass
- The PBR shader outputs pure linear HDR values
- This gives us flexibility to change tone mapping operators without modifying the PBR shader

---

## Step 2: Create Tone Mapping Shader

**Create `VizEngine/src/resources/shaders/tonemapping.shader`:**

```glsl
#shader vertex
#version 460 core

// Fullscreen quad (NDC coordinates)
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

out vec4 FragColor;

in vec2 v_TexCoords;

// ============================================================================
// Uniforms
// ============================================================================
uniform sampler2D u_HDRBuffer;
uniform int u_ToneMappingMode;  // 0=Reinhard, 1=ReinhardExt, 2=Exposure, 3=ACES, 4=Uncharted2
uniform float u_Exposure;       // For exposure-based and manual control
uniform float u_Gamma;          // Typically 2.2
uniform float u_WhitePoint;     // For Reinhard Extended

// ============================================================================
// Tone Mapping Functions
// ============================================================================

// ----------------------------------------------------------------------------
// 1. Reinhard (Simple)
// ----------------------------------------------------------------------------
vec3 ReinhardToneMapping(vec3 color)
{
    return color / (color + vec3(1.0));
}

// ----------------------------------------------------------------------------
// 2. Reinhard Extended (White Point Control)
// ----------------------------------------------------------------------------
vec3 ReinhardExtendedToneMapping(vec3 color, float whitePoint)
{
    vec3 numerator = color * (1.0 + (color / (whitePoint * whitePoint)));
    return numerator / (1.0 + color);
}

// ----------------------------------------------------------------------------
// 3. Exposure-Based (Photographer's)
// ----------------------------------------------------------------------------
vec3 ExposureToneMapping(vec3 color, float exposure)
{
    return vec3(1.0) - exp(-color * exposure);
}

// ----------------------------------------------------------------------------
// 4. ACES Filmic (Stephen Hill Fitted Curve)
// More accurate than Narkowicz, with proper color space transforms
// ----------------------------------------------------------------------------

// sRGB => XYZ => D65_2_D60 => AP1 => RRT_SAT
const mat3 ACESInputMat = mat3(
    0.59719, 0.07600, 0.02840,
    0.35458, 0.90834, 0.13383,
    0.04823, 0.01566, 0.83777
);

// ODT_SAT => XYZ => D60_2_D65 => sRGB
const mat3 ACESOutputMat = mat3(
     1.60475, -0.10208, -0.00327,
    -0.53108,  1.10813, -0.07276,
    -0.07367, -0.00605,  1.07602
);

vec3 RRTAndODTFit(vec3 v)
{
    vec3 a = v * (v + 0.0245786) - 0.000090537;
    vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081;
    return a / b;
}

vec3 ACESFilmic(vec3 color)
{
    color = ACESInputMat * color;
    color = RRTAndODTFit(color);
    color = ACESOutputMat * color;
    return clamp(color, 0.0, 1.0);
}

// ----------------------------------------------------------------------------
// 5. Uncharted 2 (Hable)
// Complex shoulder function with excellent highlight preservation
// ----------------------------------------------------------------------------
vec3 Uncharted2ToneMapping(vec3 color)
{
    float A = 0.15;  // Shoulder strength
    float B = 0.50;  // Linear strength
    float C = 0.10;  // Linear angle
    float D = 0.20;  // Toe strength
    float E = 0.02;  // Toe numerator
    float F = 0.30;  // Toe denominator
    float W = 11.2;  // Linear white point
    
    // Apply curve to color
    vec3 curr = ((color * (A * color + C * B) + D * E) / 
                 (color * (A * color + B) + D * F)) - E / F;
    
    // Apply curve to white point
    float white = ((W * (A * W + C * B) + D * E) / 
                   (W * (A * W + B) + D * F)) - E / F;
    
    return curr / white;
}

// ============================================================================
// Main Fragment Shader
// ============================================================================
void main()
{
    // Sample HDR color from framebuffer
    vec3 hdrColor = texture(u_HDRBuffer, v_TexCoords).rgb;
    
    // Apply exposure (for all modes except Reinhard simple)
    vec3 exposedColor = hdrColor * u_Exposure;
    
    // Apply tone mapping based on selected mode
    vec3 ldrColor;
    
    if (u_ToneMappingMode == 0)
    {
        // Reinhard (simple, no exposure)
        ldrColor = ReinhardToneMapping(hdrColor);
    }
    else if (u_ToneMappingMode == 1)
    {
        // Reinhard Extended (with white point)
        ldrColor = ReinhardExtendedToneMapping(exposedColor, u_WhitePoint);
    }
    else if (u_ToneMappingMode == 2)
    {
        // Exposure-based
        ldrColor = ExposureToneMapping(hdrColor, u_Exposure);
    }
    else if (u_ToneMappingMode == 3)
    {
        // ACES Filmic (recommended)
        ldrColor = ACESFilmic(exposedColor);
    }
    else if (u_ToneMappingMode == 4)
    {
        // Uncharted 2
        ldrColor = Uncharted2ToneMapping(exposedColor);
    }
    else
    {
        // Fallback: no tone mapping (for debugging)
        ldrColor = clamp(exposedColor, 0.0, 1.0);
    }
    
    // Apply gamma correction (linear -> sRGB)
    vec3 srgbColor = pow(ldrColor, vec3(1.0 / u_Gamma));
    
    FragColor = vec4(srgbColor, 1.0);
}
```

> [!NOTE]
> **Shader Organization**: Each tone mapping operator is a separate function for clarity. This makes it easy to understand, debug, and modify individual operators.

---

## Step 3: Create Fullscreen Quad Utility

We need a simple quad that covers the entire screen in NDC coordinates.

**Create `VizEngine/src/VizEngine/OpenGL/FullscreenQuad.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/FullscreenQuad.h

#pragma once

#include "VizEngine/Core.h"
#include <memory>

namespace VizEngine
{
    class VertexArray;
    class VertexBuffer;
    class IndexBuffer;

    /**
     * Simple fullscreen quad for post-processing effects.
     * Covers the entire screen in NDC coordinates [-1, 1].
     */
    class VizEngine_API FullscreenQuad
    {
    public:
        FullscreenQuad();
        ~FullscreenQuad() = default;

        /**
         * Render the fullscreen quad.
         * Call this after binding your post-processing shader.
         */
        void Render();

    private:
        std::shared_ptr<VertexArray> m_VAO;
        std::shared_ptr<VertexBuffer> m_VBO;
        std::shared_ptr<IndexBuffer> m_IBO;
    };
}
```

**Create `VizEngine/src/VizEngine/OpenGL/FullscreenQuad.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/FullscreenQuad.cpp

#include "FullscreenQuad.h"
#include "VertexArray.h"
#include "VertexBuffer.h"
#include "IndexBuffer.h"
#include "VertexBufferLayout.h"

#include <glad/glad.h>

namespace VizEngine
{
    FullscreenQuad::FullscreenQuad()
    {
        // Fullscreen quad vertices (NDC coordinates)
        // Position (x, y, z) + TexCoords (u, v)
        float vertices[] = {
            // Positions        // TexCoords
            -1.0f, -1.0f, 0.0f,  0.0f, 0.0f,  // Bottom-left
             1.0f, -1.0f, 0.0f,  1.0f, 0.0f,  // Bottom-right
             1.0f,  1.0f, 0.0f,  1.0f, 1.0f,  // Top-right
            -1.0f,  1.0f, 0.0f,  0.0f, 1.0f   // Top-left
        };

        // Indices for two triangles
        unsigned int indices[] = {
            0, 1, 2,  // First triangle
            2, 3, 0   // Second triangle
        };

        // Create vertex buffer
        m_VBO = std::make_shared<VertexBuffer>(vertices, sizeof(vertices));

        // Define layout
        VertexBufferLayout layout;
        layout.Push<float>(3);  // Position
        layout.Push<float>(2);  // TexCoords

        // Create vertex array and link buffer
        m_VAO = std::make_shared<VertexArray>();
        m_VAO->LinkVertexBuffer(*m_VBO, layout);

        // Create index buffer
        m_IBO = std::make_shared<IndexBuffer>(indices, 6);
    }

    void FullscreenQuad::Render()
    {
        m_VAO->Bind();
        m_IBO->Bind();
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, nullptr);
    }
}
```

> [!TIP]
> **NDC Coordinates**: The quad uses Normalized Device Coordinates (NDC) where (-1, -1) is bottom-left and (1, 1) is top-right. This covers the entire screen regardless of resolution.

---

## Step 4: Update Build System

Add the new files to CMake.

**Modify `VizEngine/CMakeLists.txt`:**

In the `VIZENGINE_SOURCES` section (OpenGL subsection), add:

```cmake
    src/VizEngine/OpenGL/FullscreenQuad.cpp
```

In the `VIZENGINE_HEADERS` section (OpenGL headers subsection), add:

```cmake
    src/VizEngine/OpenGL/FullscreenQuad.h
```

**Modify `VizEngine/src/VizEngine.h`:**

Add to the OpenGL includes section (after `Framebuffer.h`):

```cpp
#include "VizEngine/OpenGL/FullscreenQuad.h"
```

---

## Step 4: Extend UIManager with Combo Widget

Before we can create the HDR controls UI, we need to add a combo box (dropdown) widget to the UIManager. This is needed for selecting tone mapping operators.

**Modify `VizEngine/src/VizEngine/GUI/UIManager.h`:**

Add the declaration after the `Selectable` method:

```cpp
// Selection
bool Selectable(const char* label, bool selected);
bool Combo(const char* label, int* currentItem, const char* const items[], int itemCount);
```

**Modify `VizEngine/src/VizEngine/GUI/UIManager.cpp`:**

Add the implementation:

```cpp
bool UIManager::Combo(const char* label, int* currentItem, const char* const items[], int itemCount)
{
    return ImGui::Combo(label, currentItem, items, itemCount);
}
```

> [!NOTE]
> **Why UIManager?**: Our `UIManager` wraps ImGui calls to avoid DLL boundary issues. All ImGui functionality used by client applications must go through UIManager methods.

---

## Step 5: Extend Renderer with Depth Test Control

The fullscreen quad for tone mapping should render without depth testing (it's a 2D overlay). We need to add depth test control methods to the Renderer.

**Modify `VizEngine/src/VizEngine/OpenGL/Renderer.h`:**

Add the declarations after the polygon offset methods:

```cpp
// Shadow mapping helpers
void EnablePolygonOffset(float factor, float units);
void DisablePolygonOffset();

// Depth test control (for post-processing)
void EnableDepthTest();
void DisableDepthTest();
```

**Modify `VizEngine/src/VizEngine/OpenGL/Renderer.cpp`:**

Add the implementations:

```cpp
void Renderer::EnableDepthTest()
{
    glEnable(GL_DEPTH_TEST);
}

void Renderer::DisableDepthTest()
{
    glDisable(GL_DEPTH_TEST);
}
```

> [!IMPORTANT]
> **Why Renderer methods?**: We could use raw `glDisable(GL_DEPTH_TEST)` in SandboxApp, but this would require including `<glad/glad.h>` in application code. Using Renderer methods maintains the clean separation between engine and application, and prevents linker errors if someone forgets the include.

---

## Step 6: Integrate HDR Pipeline into SandboxApp

Now we'll update the Sandbox application to use the HDR pipeline.

**Modify `Sandbox/src/SandboxApp.cpp`:**

### Add Member Variables

Add to the private section of `SandboxApp` class:

```cpp
private:
    // ... existing members ...

    // HDR Pipeline (Chapter 39)
    std::shared_ptr<VizEngine::Framebuffer> m_HDRFramebuffer;
    std::shared_ptr<VizEngine::Texture> m_HDRColorTexture;
    std::shared_ptr<VizEngine::Texture> m_HDRDepthTexture;
    std::shared_ptr<VizEngine::Shader> m_ToneMappingShader;
    std::shared_ptr<VizEngine::FullscreenQuad> m_FullscreenQuad;

    // HDR Settings
    int m_ToneMappingMode = 3;      // 0=Reinhard, 1=ReinhardExt, 2=Exposure, 3=ACES, 4=Uncharted2
    float m_Exposure = 1.0f;
    float m_Gamma = 2.2f;
    float m_WhitePoint = 4.0f;      // For Reinhard Extended
```

### Initialize HDR Pipeline in OnCreate()

Add after existing initialization code:

```cpp
void OnCreate() override
{
    // ... existing setup code ...

    // =========================================================================
    // HDR Pipeline Setup (Chapter 39)
    // =========================================================================
    VP_INFO("Setting up HDR pipeline...");

    // Create HDR color texture (RGB16F)
    m_HDRColorTexture = std::make_shared<VizEngine::Texture>(
        m_WindowWidth, m_WindowHeight,
        GL_RGB16F,           // Internal format (HDR)
        GL_RGB,              // Format
        GL_FLOAT             // Data type
    );

    // Create depth texture (can remain standard precision)
    m_HDRDepthTexture = std::make_shared<VizEngine::Texture>(
        m_WindowWidth, m_WindowHeight,
        GL_DEPTH_COMPONENT24,   // Internal format
        GL_DEPTH_COMPONENT,     // Format
        GL_FLOAT                // Data type
    );

    // Create HDR framebuffer and attach textures
    m_HDRFramebuffer = std::make_shared<VizEngine::Framebuffer>(m_WindowWidth, m_WindowHeight);
    m_HDRFramebuffer->AttachColorTexture(m_HDRColorTexture, 0);
    m_HDRFramebuffer->AttachDepthTexture(m_HDRDepthTexture);

    // Verify framebuffer is complete
    if (!m_HDRFramebuffer->IsComplete())
    {
        VP_ERROR("HDR Framebuffer is not complete!");
    }
    else
    {
        VP_INFO("HDR Framebuffer created successfully: {}x{} (RGB16F)", 
                m_WindowWidth, m_WindowHeight);
    }

    // Load tone mapping shader
    m_ToneMappingShader = std::make_shared<VizEngine::Shader>("resources/shaders/tonemapping.shader");
    if (!m_ToneMappingShader->IsValid())
    {
        VP_ERROR("Failed to load tone mapping shader!");
    }

    // Create fullscreen quad for tone mapping pass
    m_FullscreenQuad = std::make_shared<VizEngine::FullscreenQuad>();

    VP_INFO("HDR pipeline initialized successfully");
}
```

### Update OnRender() for Two-Pass Rendering

Replace the existing render code with:

```cpp
void OnRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();

    // =========================================================================
    // Pass 1: Render Scene to HDR Framebuffer
    // =========================================================================
    m_HDRFramebuffer->Bind();
    renderer.Clear(m_ClearColor);

    // Set shader uniforms (PBR + IBL)
    m_DefaultLitShader->Bind();
    m_DefaultLitShader->SetMatrix4fv("u_View", m_Camera.GetViewMatrix());
    m_DefaultLitShader->SetMatrix4fv("u_Projection", m_Camera.GetProjectionMatrix());
    m_DefaultLitShader->SetVec3("u_ViewPos", m_Camera.GetPosition());

    // Set lights (directional + point lights)
    // ... (existing light setup code) ...

    // Set IBL textures
    if (m_IrradianceMap && m_PrefilteredMap && m_BRDFLUT)
    {
        m_IrradianceMap->Bind(5);
        m_PrefilteredMap->Bind(6);
        m_BRDFLUT->Bind(7);
        m_DefaultLitShader->SetInt("u_IrradianceMap", 5);
        m_DefaultLitShader->SetInt("u_PrefilteredMap", 6);
        m_DefaultLitShader->SetInt("u_BRDF_LUT", 7);
        m_DefaultLitShader->SetFloat("u_MaxReflectionLOD", 4.0f);
        m_DefaultLitShader->SetBool("u_UseIBL", true);
    }

    // Render scene objects
    RenderSceneObjects(renderer, *m_DefaultLitShader);

    // Render skybox (if enabled)
    if (m_Skybox && m_ShowSkybox)
    {
        m_Skybox->Render(m_Camera);
    }

    m_HDRFramebuffer->Unbind();

    // =========================================================================
    // Pass 2: Tone Mapping to Screen
    // =========================================================================
    // Restore viewport to window size (framebuffer may have changed it)
    renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);

    // Clear screen
    renderer.Clear(m_ClearColor);

    // Disable depth test for fullscreen quad
    renderer.DisableDepthTest();

    // Bind tone mapping shader
    m_ToneMappingShader->Bind();

    // Bind HDR texture
    m_HDRColorTexture->Bind(0);
    m_ToneMappingShader->SetInt("u_HDRBuffer", 0);

    // Set tone mapping parameters
    m_ToneMappingShader->SetInt("u_ToneMappingMode", m_ToneMappingMode);
    m_ToneMappingShader->SetFloat("u_Exposure", m_Exposure);
    m_ToneMappingShader->SetFloat("u_Gamma", m_Gamma);
    m_ToneMappingShader->SetFloat("u_WhitePoint", m_WhitePoint);

    // Render fullscreen quad
    m_FullscreenQuad->Render();

    // Re-enable depth test
    renderer.EnableDepthTest();
}
```

**Create a helper method** for shader setup (add to private section after `RenderSceneObjects()`):

```cpp
void SetupDefaultLitShader()
{
    if (!m_DefaultLitShader) return;

    m_DefaultLitShader->Bind();
    m_DefaultLitShader->SetMatrix4fv("u_View", m_Camera.GetViewMatrix());
    m_DefaultLitShader->SetMatrix4fv("u_Projection", m_Camera.GetProjectionMatrix());
    m_DefaultLitShader->SetVec3("u_ViewPos", m_Camera.GetPosition());

    m_DefaultLitShader->SetInt("u_LightCount", 4);
    for (int i = 0; i < 4; ++i)
    {
        m_DefaultLitShader->SetVec3("u_LightPositions[" + std::to_string(i) + "]", m_PBRLightPositions[i]);
        m_DefaultLitShader->SetVec3("u_LightColors[" + std::to_string(i) + "]", m_PBRLightColors[i]);
    }

    m_DefaultLitShader->SetBool("u_UseDirLight", true);
    m_DefaultLitShader->SetVec3("u_DirLightDirection", m_Light.GetDirection());
    m_DefaultLitShader->SetVec3("u_DirLightColor", m_Light.Diffuse * 2.0f);
    
    m_DefaultLitShader->SetMatrix4fv("u_LightSpaceMatrix", m_LightSpaceMatrix);
    
    // Shadow mapping (only enable if shadow map resource is valid)
    if (m_ShadowMapDepth)
    {
        m_DefaultLitShader->SetMatrix4fv("u_LightSpaceMatrix", m_LightSpaceMatrix);
        m_ShadowMapDepth->Bind(1);
        m_DefaultLitShader->SetInt("u_ShadowMap", 1);
        m_DefaultLitShader->SetBool("u_UseShadows", true);
    }
    else
    {
        m_DefaultLitShader->SetBool("u_UseShadows", false);
    }

    // IBL (only enable if all IBL resources are valid)
    const bool iblResourcesValid = m_UseIBL && m_IrradianceMap && m_PrefilteredMap && m_BRDFLut;
    m_DefaultLitShader->SetBool("u_UseIBL", iblResourcesValid);
    if (iblResourcesValid)
    {
        m_IrradianceMap->Bind(5);
        m_DefaultLitShader->SetInt("u_IrradianceMap", 5);
        m_PrefilteredMap->Bind(6);
        m_DefaultLitShader->SetInt("u_PrefilteredMap", 6);
        m_BRDFLut->Bind(7);
        m_DefaultLitShader->SetInt("u_BRDF_LUT", 7);
        m_DefaultLitShader->SetFloat("u_MaxReflectionLOD", 4.0f);
    }
}
```

**Now update `OnRender()`** to use the helper and include LDR fallback:

```cpp
void OnRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();

    // =========================================================================
    // Pass 1: Render Scene to HDR Framebuffer
    // =========================================================================
    if (m_HDREnabled && m_HDRFramebuffer && m_HDRFramebuffer->IsComplete())
    {
        m_HDRFramebuffer->Bind();
        renderer.Clear(m_ClearColor);

        SetupDefaultLitShader();
        RenderSceneObjects();

        if (m_ShowSkybox && m_Skybox)
        {
            m_Skybox->Render(m_Camera);
        }

        m_HDRFramebuffer->Unbind();
    }
    else
    {
        // LDR fallback if HDR unavailable
        renderer.Clear(m_ClearColor);
        SetupDefaultLitShader();
        RenderSceneObjects();
        
        if (m_ShowSkybox && m_Skybox)
        {
            m_Skybox->Render(m_Camera);
        }
    }

    // =========================================================================
    // Pass 2: Tone Mapping to Screen
    // =========================================================================
    if (m_HDREnabled && m_ToneMappingShader && m_HDRColorTexture && m_FullscreenQuad)
    {
        renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);
        renderer.Clear(m_ClearColor);
        renderer.DisableDepthTest();

        m_ToneMappingShader->Bind();
        m_HDRColorTexture->Bind(0);
        m_ToneMappingShader->SetInt("u_HDRBuffer", 0);
        m_ToneMappingShader->SetInt("u_ToneMappingMode", m_ToneMappingMode);
        m_ToneMappingShader->SetFloat("u_Exposure", m_Exposure);
        m_ToneMappingShader->SetFloat("u_Gamma", m_Gamma);
        m_ToneMappingShader->SetFloat("u_WhitePoint", m_WhitePoint);

        m_FullscreenQuad->Render();
        renderer.EnableDepthTest();
    }
}
```

### Add HDR Controls to OnImGuiRender()

Add a new ImGui panel for HDR controls:

```cpp
void OnImGuiRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& uiManager = engine.GetUIManager();

    // ... existing panels ...

    // =========================================================================
    // HDR & Tone Mapping Panel
    // =========================================================================
    uiManager.StartWindow("HDR & Tone Mapping");

    // Tone mapping operator selection
    const char* toneMappingModes[] = { 
        "Reinhard", 
        "Reinhard Extended", 
        "Exposure", 
        "ACES Filmic", 
        "Uncharted 2" 
    };
    uiManager.Combo("Tone Mapping", &m_ToneMappingMode, toneMappingModes, 5);

    // Exposure control (for all modes except simple Reinhard)
    if (m_ToneMappingMode != 0)
    {
        uiManager.SliderFloat("Exposure", &m_Exposure, 0.1f, 5.0f);
        
        // Show f-stop equivalent
        float fStops = log2(m_Exposure);
        uiManager.Text("(%.2f f-stops)", fStops);
    }

    // White point (for Reinhard Extended)
    if (m_ToneMappingMode == 1)
    {
        uiManager.SliderFloat("White Point", &m_WhitePoint, 1.0f, 20.0f);
    }

    // Gamma control
    uiManager.SliderFloat("Gamma", &m_Gamma, 1.8f, 2.6f);

    uiManager.Separator();

    // Framebuffer info
    uiManager.Text("HDR Buffer: %dx%d RGB16F", 
                   m_HDRFramebuffer->GetWidth(), 
                   m_HDRFramebuffer->GetHeight());
    uiManager.Text("Memory: ~%.2f MB", 
                   (m_HDRFramebuffer->GetWidth() * m_HDRFramebuffer->GetHeight() * 6) / (1024.0f * 1024.0f));

    uiManager.EndWindow();

    // ... existing panels ...
}
```

### Handle Window Resize

Update `OnResize()` to recreate the HDR framebuffer:

```cpp
void OnResize(int width, int height) override
{
    m_WindowWidth = width;
    m_WindowHeight = height;

    // Update camera aspect ratio
    m_Camera.SetAspectRatio(static_cast<float>(width) / static_cast<float>(height));

    // Recreate HDR framebuffer with new dimensions
    if (m_HDRFramebuffer)
    {
        VP_INFO("Recreating HDR framebuffer for new window size: {}x{}", width, height);

        // Preserve old resources in case new creation fails
        auto oldFramebuffer = m_HDRFramebuffer;
        auto oldColorTexture = m_HDRColorTexture;
        auto oldDepthTexture = m_HDRDepthTexture;

        // Create new textures
        m_HDRColorTexture = std::make_shared<VizEngine::Texture>(
            width, height, GL_RGB16F, GL_RGB, GL_FLOAT
        );
        m_HDRDepthTexture = std::make_shared<VizEngine::Texture>(
            width, height, GL_DEPTH_COMPONENT24, GL_DEPTH_COMPONENT, GL_FLOAT
        );

        // Recreate framebuffer
        m_HDRFramebuffer = std::make_shared<VizEngine::Framebuffer>(width, height);
        m_HDRFramebuffer->AttachColorTexture(m_HDRColorTexture, 0);
        m_HDRFramebuffer->AttachDepthTexture(m_HDRDepthTexture);

        if (!m_HDRFramebuffer->IsComplete())
        {
            VP_ERROR("HDR Framebuffer incomplete after resize! Restoring previous.");
            // Restore old resources and disable HDR
            m_HDRFramebuffer = oldFramebuffer;
            m_HDRColorTexture = oldColorTexture;
            m_HDRDepthTexture = oldDepthTexture;
            m_HDREnabled = false;
        }
        else
        {
            // Validate tone-mapping resources before enabling HDR
            const bool hdrResourcesOk =
                m_ToneMappingShader && m_ToneMappingShader->IsValid() && m_FullscreenQuad;

            if (hdrResourcesOk)
            {
                m_HDREnabled = true;
            }
            else
            {
                VP_WARN("HDR framebuffer resized, but tone-mapping resources are missing; keeping HDR disabled.");
                m_HDREnabled = false;
            }
        }
    }
}
```

> [!IMPORTANT]
> **Tone-Mapping Resource Validation**: After successfully recreating the HDR framebuffer, we validate that the tone-mapping shader and fullscreen quad are available before enabling HDR. This prevents rendering issues if resources are missing.

---

## Testing & Validation

### Visual Tests

**Expected Results**:

1. **Bright Areas**: Detail preserved in highlights, no blown-out whites
   - Metal specular highlights should show smooth gradation from bright to white
   - Bright IBL reflections should maintain color information

2. **Dark Areas**: Shadows maintain depth, no crushed blacks
   - Shadow detail should be visible
   - Dark materials should show subtle color variations

3. **Specular Highlights**: Smooth rolloff from bright to white
   - No harsh clipping at bright values
   - Natural, film-like appearance

4. **Overall Contrast**: Natural, film-like appearance
   - ACES should look cinematic
   - Uncharted 2 should have strong shoulder (smooth highlights)

5. **Exposure Adjustment**: Smooth brightness changes without artifacts
   - Increasing exposure should brighten naturally
   - No banding or posterization

### Comparison Tests

**LDR vs HDR**:

| Aspect | LDR (Old) | HDR (New) |
|--------|-----------|-----------|
| Bright areas | Clipped to white, loss of detail | Smooth highlight rolloff, all detail visible |
| Specular | Harsh white spots | Gradual transition to white |
| IBL reflections | Clamped, flat | Natural, depth |
| Overall | Unrealistic | Film-like |

**Tone Mapping Comparison**:

Test each operator with the same scene:

| Operator | Visual Characteristics |
|----------|------------------------|
| **Reinhard** | Softer, flatter, less contrast |
| **Reinhard Extended** | More control over bright regions |
| **Exposure** | Natural, tunable, camera-like |
| **ACES** | Cinematic, pleasing contrast, slightly desaturated highlights |
| **Uncharted 2** | Strong shoulder, excellent highlight preservation |

**Exposure Sweep**:

Test exposure values: 0.5×, 1.0×, 2.0×, 4.0×

- Should show consistent quality at all exposures
- No artifacts, banding, or color shifts
- Natural brightness progression

### Technical Validation

**Framebuffer Format Check**:

```cpp
// In OnCreate(), after creating HDR texture
GLint internalFormat;
glBindTexture(GL_TEXTURE_2D, m_HDRColorTexture->GetID());
glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_INTERNAL_FORMAT, &internalFormat);
VP_INFO("HDR Texture Internal Format: 0x{:X} (GL_RGB16F = 0x{:X})", 
        internalFormat, GL_RGB16F);
// Should print matching values
```

**No Clamping Verification**:

Create a test scene with very bright values:
```cpp
// In scene setup
SceneObject brightCube;
brightCube.Color = glm::vec4(10.0f, 10.0f, 10.0f, 1.0f);  // Very bright
// Should render correctly, not clipped to white
```

**Performance Check**:

```cpp
// Measure frame time
auto start = std::chrono::high_resolution_clock::now();
OnRender();
auto end = std::chrono::high_resolution_clock::now();
float ms = std::chrono::duration<float, std::milli>(end - start).count();
VP_INFO("Frame time: {:.2f}ms ({:.1f} FPS)", ms, 1000.0f / ms);
```

**Expected**: Tone mapping pass should add < 1ms overhead

**Memory Usage**:

```cpp
// HDR framebuffer memory
size_t hdrMemory = m_WindowWidth * m_WindowHeight * 6;  // RGB16F = 6 bytes/pixel
VP_INFO("HDR Framebuffer Memory: {:.2f} MB", hdrMemory / (1024.0f * 1024.0f));

// For 1920×1080: ~12 MB (acceptable)
```

---

## Common Issues & Solutions

### Issue: Scene is Too Dark

| Symptom | Cause | Solution |
|---------|-------|----------|
| Nearly black output | Gamma not applied | Verify `pow(color, vec3(1.0/2.2))` in tone mapping shader |
| | Gamma applied twice | Check that PBR shader doesn't apply gamma |
| | Exposure too low | Increase exposure value |

### Issue: Scene is Too Bright / Washed Out

| Symptom | Cause | Solution |
|---------|-------|----------|
| Clipped whites everywhere | No tone mapping | Verify tone mapping shader is active |
| | Exposure too high | Reduce exposure value |
| | Gamma not applied | Add `pow(color, vec3(1.0/2.2))` |

### Issue: Banding in Gradients

| Symptom | Cause | Solution |
|---------|-------|----------|
| Visible steps in smooth gradients | Using RGBA8 instead of RGB16F | Verify `GL_RGB16F` in texture creation |
| | 8-bit output | Check monitor settings (should be 10-bit if available) |

### Issue: Colors Look Wrong

| Symptom | Cause | Solution |
|---------|-------|----------|
| Overly saturated | sRGB textures not converted | Ensure albedo textures use sRGB format |
| | Gamma applied before tone mapping | Move gamma correction after tone mapping |
| Desaturated | Tone mapping too aggressive | Try different operator or adjust exposure |

### Issue: Performance Drop

| Symptom | Cause | Solution |
|---------|-------|----------|
| Low FPS | HDR framebuffer too large | Reduce resolution or use RGB16F (not RGB32F) |
| | Inefficient fullscreen quad | Verify only 6 vertices, not thousands |
| | Multiple framebuffer recreations | Only recreate on window resize |

### Debugging Tips

**Visualize HDR Buffer**:
```glsl
// In tone mapping shader, temporarily bypass tone mapping
FragColor = vec4(texture(u_HDRBuffer, v_TexCoords).rgb * 0.1, 1.0);
// If you see color, HDR buffer is working
```

**Test Individual Operators**:
```cpp
// Force specific operator for testing
m_ToneMappingMode = 3;  // ACES
// If this works but others don't, check operator implementations
```

**Check Shader Compilation**:
```cpp
if (!m_ToneMappingShader->IsValid())
{
    VP_ERROR("Tone mapping shader failed to compile!");
    // Check console for shader errors
}
```

---

## Advanced Topics

### Automatic Exposure Implementation

For a complete automatic exposure system, add these components:

**1. Luminance Calculation Texture**:
```cpp
// Create 1×1 texture to store average luminance
m_LuminanceTexture = std::make_shared<VizEngine::Texture>(
    1, 1, GL_R16F, GL_RED, GL_FLOAT
);
```

**2. Compute Average Luminance** (using mipmaps):
```cpp
// Generate mipmaps for HDR texture
glBindTexture(GL_TEXTURE_2D, m_HDRColorTexture->GetID());
glGenerateMipmap(GL_TEXTURE_2D);

// Sample smallest mip level (1×1) = average color
// In tone mapping shader:
vec3 avgColor = textureLod(u_HDRBuffer, vec2(0.5), maxMipLevel).rgb;
float avgLuminance = dot(avgColor, vec3(0.2126, 0.7152, 0.0722));
```

**3. Calculate Target Exposure**:
```cpp
// In C++ (per-frame)
float targetExposure = 0.18f / (avgLuminance + 0.001f);
targetExposure = glm::clamp(targetExposure, 0.1f, 10.0f);
```

**4. Temporal Smoothing**:
```cpp
// Smooth exposure changes over time
float adaptationSpeed = 2.0f;
m_CurrentExposure = glm::mix(m_CurrentExposure, targetExposure, 
                             1.0f - exp(-deltaTime * adaptationSpeed));
```

**5. Use in Tone Mapping**:
```cpp
m_ToneMappingShader->SetFloat("u_Exposure", m_CurrentExposure);
```

> [!NOTE]
> **Full Implementation**: A complete automatic exposure system with histogram analysis is beyond this chapter's scope. The mipmap-based approach shown here works well for most cases.

### HDR Display Output

**Emerging Technology**: HDR monitors (HDR10, Dolby Vision) can display values > 1.0 natively.

**How it works**:
- Monitor supports extended color gamut (Rec. 2020)
- Brightness > 1000 nits (vs ~300 for SDR)
- Would bypass tone mapping for native HDR display

**Current Status**:
- Not yet common for real-time applications
- Requires OS and driver support
- Different API (DXGI for Windows, Metal for macOS)

**Future Work**: When HDR displays become standard, you could output HDR directly:
```cpp
// Hypothetical HDR output
if (displaySupportsHDR)
{
    // Output raw HDR values (no tone mapping)
    FragColor = vec4(hdrColor, 1.0);
}
else
{
    // Tone map for SDR display
    FragColor = vec4(ACESFilmic(hdrColor), 1.0);
}
```

---

## Cross-Chapter Integration

### Callbacks to Previous Chapters

**Chapter 27 (Framebuffers)**:
> "In Chapter 27, we created our `Framebuffer` class with support for color and depth attachments. Now we extend it to support HDR formats by using `GL_RGB16F` instead of `GL_RGBA8`."

**Chapters 37-38 (PBR + IBL)**:
> "In Chapters 37-38, our PBR and IBL systems produce HDR values—bright specular highlights, environment reflections, and accumulated light from multiple sources. Now we properly display them with tone mapping instead of clamping."

**Chapter 30 (HDR Environment Maps)**:
> "Remember the HDR environment maps from Chapter 30? They're actually HDR—storing values beyond 1.0. Now our entire pipeline is HDR, from loading to rendering to display."

### Forward References

**Chapter 42 (Material System)**:
> "In Chapter 42, we'll create a Material System that abstracts shader parameters and manages texture bindings. The HDR pipeline will integrate seamlessly—materials will output HDR values, and the tone mapping pass will handle display."

**Chapter 40 (Bloom)**:
> "In Chapter 40, we'll add bloom effect which enhances bright regions in the HDR buffer. Bloom works by extracting bright pixels (> 1.0) from the HDR buffer—impossible without the HDR pipeline we built here."

**Future Chapters**:
> "The HDR pipeline enables advanced post-processing like cinematic color grading, lens flares, and depth of field. All these effects benefit from the extended dynamic range."

### Architectural Notes

**Two-Pass Foundation**:
> "Our two-pass rendering (scene → HDR buffer → tone map → screen) is the foundation for **all post-processing effects**. Bloom, color grading, motion blur—they all operate on the HDR buffer before tone mapping."

**Separation of Concerns**:
> "Separating tone mapping from scene rendering provides flexibility. You can change tone mapping operators, adjust exposure, or add post-processing effects without modifying the PBR shader."

**HDR as Standard**:
> "The HDR pipeline will be reused in Chapter 40 for bloom and other effects. It's not a one-off feature—it's the new standard for how we render."

---

## Performance Considerations

### Current Costs

| Operation | Cost | Notes |
|-----------|------|-------|
| HDR Framebuffer | +50% memory | 6 bytes/pixel vs 4 bytes (acceptable) |
| Tone Mapping Pass | < 1ms | Fullscreen quad, simple math |
| Mipmap Generation | ~0.5ms | Only if using automatic exposure |
| Total Overhead | ~1-2ms | Negligible for 60 FPS (16.7ms budget) |

### Optimization Opportunities

**1. Reduce HDR Buffer Resolution**:
```cpp
// Render at lower resolution, tone map to full resolution
int hdrWidth = m_WindowWidth / 2;
int hdrHeight = m_WindowHeight / 2;
// Can improve performance on low-end GPUs
```

**2. Use RGB16F, Not RGB32F**:
```cpp
// RGB16F is sufficient for HDR rendering
// RGB32F is 2× the memory and slower
GL_RGB16F  // Recommended
```

**3. Minimize Framebuffer Recreations**:
```cpp
// Only recreate on window resize, not every frame
if (m_WindowWidth != width || m_WindowHeight != height)
{
    RecreateHDRFramebuffer(width, height);
}
```

**4. Efficient Fullscreen Quad**:
```cpp
// Use indexed rendering (6 vertices, not 4 triangles)
glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, nullptr);
// NOT: glDrawArrays(GL_TRIANGLES, 0, thousands_of_vertices);
```

---

## Comparison with Reference Implementations

### LearnOpenGL HDR Tutorial

**Reference**: [learnopengl.com/Advanced-Lighting/HDR](https://learnopengl.com/Advanced-Lighting/HDR)

**Expected Match**:
- Reinhard operator should look identical
- Exposure-based should behave the same
- Gamma correction should match

**Differences**:
- We include ACES and Uncharted 2 (LearnOpenGL doesn't)
- We have ImGui controls (LearnOpenGL is hardcoded)

### Unreal Engine HDR

**Reference**: Unreal Engine's tone mapping (ACES by default)

**Expected Match**:
- ACES operator should look very similar (we use the same Stephen Hill fitted curve)
- Exposure control should behave the same

**Differences**:
- Unreal has automatic exposure by default (we have manual)
- Unreal has additional color grading options built into the tone mapper

### Unity HDR

**Reference**: Unity's Universal Render Pipeline (URP)

**Expected Match**:
- Tone mapping operators should be similar
- HDR workflow should be identical

**Differences**:
- Unity uses Neutral and ACES (we have more options)
- Unity's post-processing stack is more complex

---

## Milestone

**Chapter 39 Complete - HDR Pipeline**

You have:
- Implemented floating-point HDR framebuffers (RGB16F)
- Created a comprehensive tone mapping shader with 5 operators
- Understood the theory behind each tone mapping operator
- Implemented manual exposure control (f-stops)
- Learned about automatic exposure and eye adaptation
- Built a two-pass rendering pipeline (scene → HDR → tone map → screen)
- Added ImGui controls for real-time adjustment
- Applied proper gamma correction (linear → sRGB)
- Tested and validated the HDR pipeline

Your engine now supports **industry-standard HDR rendering**—the same workflow used by Unreal Engine, Unity, and modern AAA games. This is a critical foundation for advanced post-processing effects and photorealistic rendering.

---

## What's Next

In **Chapter 40: Bloom**, we'll add bloom effect, that leverage the HDR pipeline we built here.

> **Next**: [Chapter 40: Bloom](40_Bloom.md)

> **Previous**: [Chapter 38: Image-Based Lighting](38_ImageBasedLighting.md)

> **Index**: [Table of Contents](INDEX.md)
