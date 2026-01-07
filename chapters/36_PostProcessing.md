\newpage

# Chapter 36: Post-Processing Effects

Implement industry-standard post-processing effects including physically-based bloom and LUT-based color grading to achieve cinematic visual quality.

---

## Introduction

In **Chapter 35**, we built a complete HDR rendering pipeline with tone mapping. Our engine now renders in HDR (RGB16F framebuffers) and maps to display space using operators like ACES Filmic. This gives us linear light values throughout the rendering pipeline and professional tone mapping at the end.

**What's missing?** The cinematic polish that makes modern games look photorealistic. Compare a screenshot from *The Last of Us Part II* or *Cyberpunk 2077* to our current output—there's a noticeable difference in visual richness.

**Post-processing effects** bridge this gap. They're image-space effects applied *after* scene rendering:

```
Scene Render → HDR Framebuffer → Post-Processing → Tone Mapping → Screen
     ↓              ↓                    ↓               ↓           ↓
  PBR + IBL    Raw HDR values     Bloom, etc.    Map to LDR   Display
```

### What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **Bloom Effect** | Physically-based glow around bright regions with soft threshold filtering |
| **Gaussian Blur** | Separable 2-pass blur with linear sampling optimization |
| **Bloom Class** | Reusable post-processing component with ping-pong framebuffers |
| **Color Grading** | 3D LUT-based color transformation for cinematic looks |
| **Parametric Controls** | Real-time saturation, contrast, and brightness adjustment |
| **ImGui Integration** | Runtime controls for all post-processing parameters |

**Visual Impact**: Bloom makes bright surfaces glow naturally (mimicking camera lens scatter), while color grading establishes mood and style (warm sunset, cool night, desaturated apocalypse).

---

## Post-Processing Overview

### What is Post-Processing?

**Post-processing** refers to effects applied to the final rendered image as a 2D texture, rather than during 3D scene rendering. The input is a fully-rendered frame; the output is a modified version of that frame.

**Key characteristic**: Post-processing operates in **image space**, not world space. It has no knowledge of 3D geometry, lights, or materials—only pixel colors and optional G-buffer data (depth, normals).

### Common Post-Processing Effects

| Effect | Purpose | Visual Result |
|--------|---------|---------------|
| **Bloom** | Simulate lens scatter | Soft glow around bright areas |
| **Color Grading** | Cinematic color palette | Mood (warm, cool, desaturated) |
| **Depth of Field** | Simulate camera focus | Blur based on distance |
| **Motion Blur** | Simulate exposure time | Streak along movement |
| **Chromatic Aberration** | Simulate lens defects | Color fringing at edges |
| **Vignette** | Darken screen edges | Film camera look |
| **Film Grain** | Add noise | Analog film aesthetic |
| **Screen-Space Reflections** | Reflect visible pixels | Mirror-like surfaces |

### This Chapter's Focus

We'll implement **bloom** and **color grading** because:
1. **Bloom** is the most impactful effect for realism (makes HDR visible)
2. **Color grading** is essential for establishing visual identity
3. Together they demonstrate the full post-processing pipeline architecture

**Other effects** (depth of field, motion blur, etc.) follow the same pattern and can be added incrementally.

### Why Post-Processing?

**Advantages**:
- **Performance**: Resolution-independent (can render scene at 4K, post-process at 1080p)
- **Flexibility**: Toggle effects on/off, change parameters in real-time
- **Modularity**: Each effect is independent, easy to add/remove
- **Artist Control**: Non-programmers can tweak parameters via ImGui

**Limitations**:
- **No 3D information**: Can't perfectly reconstruct geometry or occlusion
- **Screen-space artifacts**: Effects only work on visible pixels
- **Memory overhead**: Requires additional framebuffers

---

## Bloom Theory

### Physical Basis

In the real world, when extremely bright light (like the sun or a specular highlight) enters a camera lens, it scatters due to:
- **Lens imperfections**: Tiny scratches, dust, optical aberrations
- **Internal reflections**: Light bouncing inside the lens assembly
- **Diffraction**: Light bending around aperture blades

**Result**: Bright regions "bleed" or "glow" into surrounding areas, creating a soft halo.

**For the human eye**: A similar effect occurs due to scattering in the cornea and lens. Very bright lights appear to have a glow.

**Bloom simulates this phenomenon** in a physically plausible way, making HDR values visible even after tone mapping.

> [!IMPORTANT]
> Bloom is **not** "make everything glow." Only pixels with luminance significantly above the average scene brightness should bloom. On a properly exposed image, this means **HDR values > 1.0** (after exposure adjustment).

### Algorithm Overview

Bloom consists of three steps:

```
1. Bright Pass (Extraction)
   ↓
   Extract pixels above threshold → Black image with bright spots

2. Blur Pass
   ↓
   Apply Gaussian blur → Soft, blurred glow

3. Composite Pass
   ↓
   Add blurred result to original HDR image
```

**Mathematically**:
$$Final = HDR_{original} + Blur(Extract(HDR_{original}))$$

---

### Step 1: Bright Pass Filtering

**Goal**: Isolate pixels that are "over-bright" (significantly brighter than average).

**Naive approach** (hard threshold):
```glsl
float luminance = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
if (luminance > threshold) {
    return color;  // Keep this pixel
} else {
    return vec3(0.0);  // Discard
}
```

**Problem**: Creates harsh transitions. Pixels at `threshold - 0.01` are black, pixels at `threshold + 0.01` are full brightness. This causes **banding artifacts**.

---

#### Soft Threshold (Knee)

A **soft knee** creates a smooth transition around the threshold:

```glsl
threshold = 1.0  // Only HDR values > 1.0 bloom
knee = 0.5       // Transition range: [0.5, 1.5]

luminance = 0.3  → contribution = 0.0   (too dark)
luminance = 0.7  → contribution = 0.1   (gradual increase)
luminance = 1.0  → contribution = 0.5   (halfway)
luminance = 1.3  → contribution = 0.9   (almost full)
luminance = 2.0  → contribution = 1.0   (full bloom)
```

**Formula** (quadratic soft knee):

$$
soft = luminance - threshold + knee \\
soft = clamp(soft, 0, 2 \times knee) \\
soft = \frac{soft^2}{4 \times knee + \epsilon}
$$

$$
contribution = \frac{max(soft, luminance - threshold)}{luminance + \epsilon}
$$

**Visualization**:
- Below `threshold - knee`: No bloom
- Within `[threshold - knee, threshold + knee]`: Smooth ramp
- Above `threshold + knee`: Full bloom

**Sources**: Unity Post Processing Stack, Unreal Engine bloom implementation

---

### Step 2: Gaussian Blur

**Goal**: Create a soft, natural-looking glow by blurring the extracted bright regions.

#### Why Gaussian?

A **Gaussian blur** approximates the point spread function (PSF) of real camera lenses—the pattern light makes when it scatters.

**Gaussian function** (1D):
$$G(x) = \frac{1}{\sqrt{2\pi\sigma^2}} e^{-\frac{x^2}{2\sigma^2}}$$

Where $\sigma$ (sigma) controls the blur radius.

**For a 5-tap kernel** ($\sigma = 1.0$):

| Offset | Weight |
|--------|--------|
| 0 | 0.227027 |
| ±1 | 0.1945946 |
| ±2 | 0.1216216 |
| ±3 | 0.054054 |
| ±4 | 0.016216 |

**Sum = 1.0** (energy-conserving)

---

#### Separable Filtering Optimization

A 2D Gaussian blur can be decomposed into two 1D blurs:

$$Blur_{2D}(image) = Blur_{vertical}(Blur_{horizontal}(image))$$

**Complexity reduction**:
- Naive 2D: $N^2$ samples per pixel (e.g., 9×9 = 81 samples)
- Separable: $2N$ samples per pixel (e.g., 9+9 = 18 samples)

**For a 9-tap blur**: $81 \rightarrow 18$ samples (**4.5× faster**)

**Implementation**:
1. **Pass 1**: Horizontal blur to temporary framebuffer
2. **Pass 2**: Vertical blur from temporary to final output

> [!TIP]
> Always use separable Gaussian blur for real-time graphics. The performance improvement is massive for larger kernel sizes.

---

#### Linear Sampling Optimization

GPUs provide hardware bilinear filtering. By carefully positioning texture coordinates **between** pixels, we can sample two pixels with one texture fetch.

**Example** (5-tap blur, center + 2 on each side):

**Standard approach**:
```glsl
// 5 texture fetches
result  = texture(tex, uv + offset * 0) * weight[0];
result += texture(tex, uv + offset * 1) * weight[1];
result += texture(tex, uv - offset * 1) * weight[1];
result += texture(tex, uv + offset * 2) * weight[2];
result += texture(tex, uv - offset * 2) * weight[2];
```

**Optimized approach** (combine pairs):
```glsl
// Combine weights: weight[1] + weight[2]
// Sample offset: (1 * weight[1] + 2 * weight[2]) / (weight[1] + weight[2])
// Result: 3 texture fetches instead of 5

newWeight01 = weight[0] + weight[1];
newOffset01 = (0 * weight[0] + 1 * weight[1]) / newWeight01;

newWeight12 = weight[1] + weight[2];
newOffset12 = (1 * weight[1] + 2 * weight[2]) / newWeight12;

result  = texture(tex, uv + newOffset01) * newWeight01;
result += texture(tex, uv - newOffset01) * newWeight01;
result += texture(tex, uv + newOffset12) * newWeight12;
result += texture(tex, uv - newOffset12) * newWeight12;
// Center sample handled separately if needed
```

**Performance gain**: ~40-60% faster (depends on texture cache behavior).

**Source**: GPU Gems 3, "Efficient Gaussian Blur with Linear Sampling" by Daniel Rákos.

---

#### Downsampling Strategy

Blurring at full resolution is expensive. **Solution**: Downsample before blurring.

**Common strategy**:
1. Render scene at 1920×1080 (full resolution)
2. Extract bright pass at 960×540 (1/2 resolution)
3. Blur at 960×540
4. Composite back to full resolution

**Memory savings**: $\frac{1}{4}$ (half width × half height)  
**Performance gain**: $\frac{1}{4}$ blur cost  
**Visual quality**: Minimal loss (bloom is inherently blurry)

**Advanced**: Use multiple mip levels (mip chain bloom) for multi-scale glow. Used by Unreal Engine for extremely realistic results.

---

### Step 3: Bloom Composite

**Goal**: Add the blurred bloom texture to the original HDR image.

**Simple additive blend**:
```glsl
vec3 hdrColor = texture(u_HDRBuffer, texCoords).rgb;
vec3 bloomColor = texture(u_BloomTexture, texCoords).rgb;

vec3 result = hdrColor + bloomColor * u_BloomIntensity;
```

**Intensity control**:
- `u_BloomIntensity = 0.0`: No bloom
- `u_BloomIntensity = 0.04`: Subtle enhancement (recommended starting point)
- `u_BloomIntensity = 0.2`: Dramatic glow
- `u_BloomIntensity = 1.0`: Very strong (can wash out image)

**When to composite**:
- **Before tone mapping** (operates in HDR space)
- Tone mapping then converts the bloomed HDR values to LDR

---

## Color Grading Theory

### What is Color Grading?

**Color grading** is the process of altering the colors of an image to achieve a specific aesthetic or mood. Originated in film production, where colorists adjust footage in post-production.

**In games**:
- Establish visual identity (e.g., *Mad Max* is desaturated orange/teal)
- Guide player emotion (warm = safe, cool = danger)
- Differentiate locations (forest = green, desert = yellow)
- Create time-of-day variations (sunrise = pink/orange, night = blue)

**Examples**:
| Look | Color Adjustments |
|------|-------------------|
| **Warm Sunset** | Shift toward orange/yellow, boost saturation |
| **Cool Night** | Shift toward blue, reduce saturation |
| **Post-Apocalyptic** | Desaturate, crush blacks, lift shadows |
| **Vintage Film** | Adjust curves, add grain, subtle vignette |

---

### 3D LUT (Look-Up Table) Approach

A **3D LUT** is a pre-baked color transformation stored as a 3D texture. It maps input RGB to output RGB.

**Structure**:
```
Input RGB (0-1, 0-1, 0-1) → Sample 3D texture at (r, g, b) → Output RGB
```

**Texture coordinates = input color**  
**Sampled value = output color**

**Resolution**: Typically 16×16×16 or 32×32×32 3D texture

Example (16×16×16):
- 16 red levels
- 16 green levels
- 16 blue levels
- Total: $16^3 = 4096$ color entries
- Memory: $4096 \times 3 \times 4 bytes (RGB32F) = 48 KB$

#### Neutral (Identity) LUT

A neutral LUT performs no transformation:

```glsl
// For each entry (r, g, b) in [0, 15]:
float red = r / 15.0;
float green = g / 15.0;
float blue = b / 15.0;

LUT[r][g][b] = vec3(red, green, blue);  // Identity mapping
```

**Result**: `texture(LUT, color) == color`

---

#### Creating Custom LUTs

**Workflow**:
1. **Export neutral LUT** as a 3D texture (or 2D "strip" format: 256×16)
2. **Load into Photoshop/DaVinci Resolve**
3. **Apply color adjustments**: Curves, levels, saturation, hue shifts
4. **Export modified LUT**
5. **Import into engine**

**Advantage**: Artists use familiar color grading tools (Photoshop, DaVinci Resolve) instead of programming shader code.

**Alternative**: Generate LUTs procedurally in shaders for specific looks (sepia, night vision, etc.).

---

#### Applying the LUT in Shaders

```glsl
uniform sampler3D u_ColorGradingLUT;

vec3 gradedColor = texture(u_ColorGradingLUT, ldrColor).rgb;
```

**Critical**: Apply color grading **after** tone mapping (in LDR space [0,1]), not before. Tone mapping operates on linear HDR values; color grading is a perceptual transform.

**Blending** (optional):
```glsl
vec3 finalColor = mix(ldrColor, gradedColor, u_LUTContribution);
```

Allows fading between original and graded for artistic control.

---

### Parametric Color Grading (Alternative/Complement)

Instead of pre-baked LUTs, apply adjustments procedurally:

**Saturation**:
```glsl
vec3 grayscale = vec3(dot(color, vec3(0.2126, 0.7152, 0.0722)));
color = mix(grayscale, color, u_Saturation);  // 0=grayscale, 1=normal, 2=oversaturated
```

**Contrast**:
```glsl
color = (color - 0.5) * u_Contrast + 0.5;  // 1=normal, >1=more contrast, <1=less
```

**Brightness**:
```glsl
color = color + u_Brightness;  // -1 to +1
```

**Color Filter** (tint):
```glsl
color *= u_ColorFilter;  // e.g., vec3(1.0, 0.9, 0.8) for warm tint
```

**Advantage**: Real-time tuning, no texture required.  
**Disadvantage**: Limited expressiveness compared to LUTs (can't do complex curve adjustments).

**Best of both worlds**: Use parametric controls to generate a LUT on the GPU, giving artists real-time feedback.

---

## Post-Processing Pipeline Architecture

### Render Pass Order

```
Scene Rendering
   ↓
HDR Framebuffer (RGB16F, raw linear light values)
   ↓
Bloom Extraction → Bright regions only (threshold filter)
   ↓
Bloom Blur (horizontal) → Temporary framebuffer
   ↓
Bloom Blur (vertical) → Final bloom texture
   ↓
Bloom Composite → Add bloom to HDR buffer
   ↓
Tone Mapping → HDR→LDR (ACES Filmic, etc.)
   ↓
Color Grading → LUT or parametric (operates in LDR [0,1])
   ↓
Gamma Correction → Linear→sRGB (typically 1/2.2)
   ↓
Final Output → Screen (default framebuffer)
```

**Key insight**: 
- **Bloom** operates in **HDR space** (before tone mapping)
- **Color grading** operates in **LDR space** (after tone mapping)

---

### Framebuffer Strategy

**Requirements**:
- HDR framebuffer (already exists from Chapter 35)
- Bloom extraction framebuffer (RGB16F, downsampled)
- Two ping-pong framebuffers for blur passes (swap between horizontal/vertical)

**Example setup** (1920×1080 scene):
- **m_HDRFramebuffer**: 1920×1080, RGB16F
- **m_BloomExtractFB**: 960×540, RGB16F (1/2 resolution)
- **m_BloomBlurFB1**: 960×540, RGB16F
- **m_BloomBlurFB2**: 960×540, RGB16F

**Ping-pong pattern**:
```
Extract → BloomExtractFB
BloomExtractFB → Blur Horizontal → BloomBlurFB1
BloomBlurFB1 → Blur Vertical → BloomBlurFB2
BloomBlurFB2 → Blur Horizontal → BloomBlurFB1
BloomBlurFB1 → Blur Vertical → BloomBlurFB2
... (repeat for desired blur quality)
Final: BloomBlurFB2
```

**Why ping-pong?** Allows reusing framebuffers, reducing memory usage.

---

## Engine Extensions

Before we implement the post-processing classes, we need to extend our core engine components with a few utility functions that we'll need for configuration and shader management.

### Step 1: Add Shader Uniform Support

We'll need to pass `vec2` uniforms (e.g., texture sizes) to our shaders for the Gaussian blur and downsampling ops.

**1. Update** `VizEngine/src/VizEngine/OpenGL/Shader.h` to add the declaration:
```cpp
void SetVec2(const std::string& name, const glm::vec2& value);
```

**2. Update** `VizEngine/src/VizEngine/OpenGL/Shader.cpp` to implement it:
```cpp
void Shader::SetVec2(const std::string& name, const glm::vec2& value)
{
    glUniform2f(GetUniformLocation(name), value.x, value.y);
}
```

### Step 2: Extend UI Controls

For tweaking post-processing parameters, we'll need integer sliders (for iteration counts) and collapsible headers (for organizing the settings) in our `UIManager`.

**1. Update** `VizEngine/src/VizEngine/GUI/UIManager.h` to add these declarations:
```cpp
// Layout
bool CollapsingHeader(const char* label);

// Integers
bool SliderInt(const char* label, int* value, int min, int max);
```

**2. Update** `VizEngine/src/VizEngine/GUI/UIManager.cpp` to implement them:
```cpp
bool UIManager::CollapsingHeader(const char* label)
{
    return ImGui::CollapsingHeader(label);
}

bool UIManager::SliderInt(const char* label, int* value, int min, int max)
{
    return ImGui::SliderInt(label, value, min, max);
}
```

---

## Bloom Implementation

### Bloom Extraction Shader

**Create** `VizEngine/src/resources/shaders/bloom_extract.shader`:

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec2 a_TexCoords;

out vec2 v_TexCoords;

void main()
{
    v_TexCoords = a_TexCoords;
    gl_Position = vec4(a_Position, 1.0);
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec2 v_TexCoords;

// ============================================================================
// Uniforms
// ============================================================================
uniform sampler2D u_HDRBuffer;
uniform float u_Threshold;  // Typically 1.0 for HDR
uniform float u_Knee;        // Soft threshold range (e.g., 0.1-0.5)

// ============================================================================
// Bright Pass Extraction with Soft Threshold
// ============================================================================

vec3 ExtractBrightRegions(vec3 color)
{
    // Calculate luminance (perceptual brightness)
    float luminance = dot(color, vec3(0.2126, 0.7152, 0.0722));
    
    // Quadratic soft threshold (smooth knee)
    // This creates a smooth transition around the threshold instead of a hard cut
    float soft = luminance - u_Threshold + u_Knee;
    soft = clamp(soft, 0.0, 2.0 * u_Knee);
    soft = (soft * soft) / (4.0 * u_Knee + 0.00001);  // +epsilon to prevent divide by zero
    
    // Calculate contribution
    float contribution = max(soft, luminance - u_Threshold);
    contribution /= max(luminance, 0.00001);  // Normalize by luminance
    
    // Return color scaled by contribution (preserves color, only adjusts intensity)
    return color * contribution;
}

void main()
{
    vec3 hdrColor = texture(u_HDRBuffer, v_TexCoords).rgb;
    vec3 brightColor = ExtractBrightRegions(hdrColor);
    
    FragColor = vec4(brightColor, 1.0);
}
```

**Key aspects**:
- **Soft threshold** prevents banding artifacts
- **Luminance-based** filtering (not just magnitude)
- **Color preservation**: Maintains hue, only adjusts intensity
- **Epsilon values**: Prevent divide-by-zero

---

### Gaussian Blur Shader

**Create** `VizEngine/src/resources/shaders/bloom_blur.shader`:

```glsl
#shader vertex
#version 460 core

layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec2 a_TexCoords;

out vec2 v_TexCoords;

void main()
{
    v_TexCoords = a_TexCoords;
    gl_Position = vec4(a_Position, 1.0);
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec2 v_TexCoords;

// ============================================================================
// Uniforms
// ============================================================================
uniform sampler2D u_Image;
uniform bool u_Horizontal;      // true = horizontal pass, false = vertical
uniform vec2 u_TextureSize;     // For calculating pixel offsets

// ============================================================================
// Gaussian Blur (5-tap separable)
// ============================================================================

void main()
{
    // Gaussian weights for 5-tap kernel (sigma ≈ 1.0)
    // Normalized to sum to 1.0 (energy-conserving)
    float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    
    // Pixel size in texture coordinates [0,1]
    vec2 texelSize = 1.0 / u_TextureSize;
    
    // Sample center pixel
    vec3 result = texture(u_Image, v_TexCoords).rgb * weights[0];
    
    // Sample neighboring pixels
    if (u_Horizontal)
    {
        // Horizontal blur (vary x, keep y constant)
        for (int i = 1; i < 5; ++i)
        {
            vec2 offset = vec2(texelSize.x * float(i), 0.0);
            result += texture(u_Image, v_TexCoords + offset).rgb * weights[i];
            result += texture(u_Image, v_TexCoords - offset).rgb * weights[i];
        }
    }
    else
    {
        // Vertical blur (vary y, keep x constant)
        for (int i = 1; i < 5; ++i)
        {
            vec2 offset = vec2(0.0, texelSize.y * float(i));
            result += texture(u_Image, v_TexCoords + offset).rgb * weights[i];
            result += texture(u_Image, v_TexCoords - offset).rgb * weights[i];
        }
    }
    
    FragColor = vec4(result, 1.0);
}
```

**Notes**:
- **5-tap kernel**: Good balance between quality and performance (9 texture fetches: center + 4 pairs)
- **Separable**: Horizontal and vertical passes use the same shader with `u_Horizontal` flag
- **For better quality**: Use 9-tap or 13-tap (increases GPU time proportionally)
- **Linear sampling optimization**: Can reduce to 3 effective taps (advanced, not shown for clarity)

---

### Bloom Composite (Modify Tone Mapping Shader)

**Update** `VizEngine/src/resources/shaders/tonemapping.shader`:

Add uniforms after existing ones:

```glsl
uniform sampler2D u_BloomTexture;
uniform float u_BloomIntensity;
uniform bool u_EnableBloom;
```

In `main()` function, **before** tone mapping:

```glsl
void main()
{
    // Sample HDR color from framebuffer
    vec3 hdrColor = texture(u_HDRBuffer, v_TexCoords).rgb;
    
    // ========================================================================
    // Bloom Composite (BEFORE tone mapping, in HDR space)
    // ========================================================================
    if (u_EnableBloom)
    {
        vec3 bloomColor = texture(u_BloomTexture, v_TexCoords).rgb;
        hdrColor += bloomColor * u_BloomIntensity;
    }
    
    // Apply exposure (for all modes except Reinhard simple)
    vec3 exposedColor = hdrColor * u_Exposure;
    
    // Apply tone mapping based on selected mode
    vec3 ldrColor;
    // ... (existing tone mapping code) ...
```

**Order is critical**:
1. Sample HDR buffer
2. Add bloom (in HDR space)
3. Apply exposure
4. Tone map to LDR
5. Color grade (next section)
6. Gamma correct

---

### Bloom Class Implementation

**Create** `VizEngine/src/VizEngine/Renderer/Bloom.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/Bloom.h

#pragma once

#include "VizEngine/Core.h"
#include <memory>

namespace VizEngine
{
    class Framebuffer;
    class Shader;
    class Texture;
    class FullscreenQuad;

    /**
     * Bloom post-processing effect.
     * Extracts bright regions, applies Gaussian blur, returns bloom texture.
     */
    class VizEngine_API Bloom
    {
    public:
        /**
         * Create bloom processor.
         * @param width Bloom buffer width (typically half of scene resolution)
         * @param height Bloom buffer height
         */
        Bloom(int width, int height);
        ~Bloom() = default;

        /**
         * Process HDR texture to generate bloom.
         * @param hdrTexture Input HDR framebuffer color attachment
         * @return Bloom texture (same resolution as input)
         */
        std::shared_ptr<Texture> Process(std::shared_ptr<Texture> hdrTexture);

        // Settings
        void SetThreshold(float threshold) { m_Threshold = threshold; }
        void SetKnee(float knee) { m_Knee = knee; }
        void SetIntensity(float intensity) { m_Intensity = intensity; }
        void SetBlurPasses(int passes) { m_BlurPasses = passes; }

        float GetThreshold() const { return m_Threshold; }
        float GetKnee() const { return m_Knee; }
        float GetIntensity() const { return m_Intensity; }
        int GetBlurPasses() const { return m_BlurPasses; }

        // Validation
        bool IsValid() const { return m_IsValid; }

    private:
        // Framebuffers for multi-pass rendering
        std::shared_ptr<Framebuffer> m_ExtractFB;
        std::shared_ptr<Framebuffer> m_BlurFB1;  // Ping-pong buffer 1
        std::shared_ptr<Framebuffer> m_BlurFB2;  // Ping-pong buffer 2

        // Textures (attached to framebuffers)
        std::shared_ptr<Texture> m_ExtractTexture;
        std::shared_ptr<Texture> m_BlurTexture1;
        std::shared_ptr<Texture> m_BlurTexture2;

        // Shaders
        std::shared_ptr<Shader> m_ExtractShader;
        std::shared_ptr<Shader> m_BlurShader;

        // Fullscreen quad for rendering
        std::shared_ptr<FullscreenQuad> m_Quad;

        // Bloom parameters
        float m_Threshold = 1.0f;    // Brightness threshold for bloom
        float m_Knee = 0.1f;         // Soft threshold range
        float m_Intensity = 0.04f;   // Bloom intensity (set via composite, but stored here)
        int m_BlurPasses = 5;        // Number of blur iterations (more = softer)

        int m_Width, m_Height;

        // Validation flag
        bool m_IsValid = false;
    };
}
```

---

**Create** `VizEngine/src/VizEngine/Renderer/Bloom.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/Bloom.cpp

#include "Bloom.h"
#include "VizEngine/OpenGL/Framebuffer.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/OpenGL/FullscreenQuad.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>

namespace VizEngine
{
    Bloom::Bloom(int width, int height)
        : m_Width(width), m_Height(height)
    {
        // ====================================================================
       // Create Textures (RGB16F for HDR bloom)
        // ====================================================================
        m_ExtractTexture = std::make_shared<Texture>(
            width, height, GL_RGB16F, GL_RGB, GL_FLOAT
        );
        m_BlurTexture1 = std::make_shared<Texture>(
            width, height, GL_RGB16F, GL_RGB, GL_FLOAT
        );
        m_BlurTexture2 = std::make_shared<Texture>(
            width, height, GL_RGB16F, GL_RGB, GL_FLOAT
        );

        // ====================================================================
        // Create Framebuffers
        // ====================================================================
        m_ExtractFB = std::make_shared<Framebuffer>(width, height);
        m_ExtractFB->AttachColorTexture(m_ExtractTexture, 0);
        
        m_BlurFB1 = std::make_shared<Framebuffer>(width, height);
        m_BlurFB1->AttachColorTexture(m_BlurTexture1, 0);
        
        m_BlurFB2 = std::make_shared<Framebuffer>(width, height);
        m_BlurFB2->AttachColorTexture(m_BlurTexture2, 0);

        // Verify framebuffers are complete
        if (!m_ExtractFB->IsComplete() || !m_BlurFB1->IsComplete() || !m_BlurFB2->IsComplete())
        {
            VP_CORE_ERROR("Bloom: Framebuffers not complete!");
            m_IsValid = false;
        }

        // ====================================================================
        // Load Shaders
        // ====================================================================
        m_ExtractShader = std::make_shared<Shader>("../VizEngine/src/resources/shaders/bloom_extract.shader");
        m_BlurShader = std::make_shared<Shader>("../VizEngine/src/resources/shaders/bloom_blur.shader");

        // Validate shaders loaded successfully
        if (!m_ExtractShader->IsValid() || !m_BlurShader->IsValid())
        {
            VP_CORE_ERROR("Bloom: Failed to load shaders!");
            m_IsValid = false;
            return;
        }

        // ====================================================================
        // Create Fullscreen Quad
        // ====================================================================
        m_Quad = std::make_shared<FullscreenQuad>();

        // All validations passed - mark as valid
        m_IsValid = true;

        VP_CORE_INFO("Bloom created: {}x{}, {} blur passes", width, height, m_BlurPasses);
    }

    std::shared_ptr<Texture> Bloom::Process(std::shared_ptr<Texture> hdrTexture)
    {
        // Early return if shaders failed to load
        if (!m_IsValid)
        {
            VP_CORE_ERROR("Bloom::Process called on invalid Bloom instance");
            return hdrTexture;  // Return input unchanged
        }

        // Validate input parameter
        if (!hdrTexture)
        {
            VP_CORE_ERROR("Bloom::Process called with null hdrTexture");
            return nullptr;
        }

        // ====================================================================
        // Pass 1: Extract Bright Regions
        // ====================================================================
        m_ExtractFB->Bind();
        glClear(GL_COLOR_BUFFER_BIT);

        m_ExtractShader->Bind();
        m_ExtractShader->SetInt("u_HDRBuffer", 0);
        m_ExtractShader->SetFloat("u_Threshold", m_Threshold);
        m_ExtractShader->SetFloat("u_Knee", m_Knee);

        hdrTexture->Bind(0);
        m_Quad->Render();

        m_ExtractFB->Unbind();

        // ====================================================================
        // Pass 2: Blur (Ping-Pong between two framebuffers)
        // ====================================================================
        m_BlurShader->Bind();
        m_BlurShader->SetVec2("u_TextureSize", glm::vec2(m_Width, m_Height));

        std::shared_ptr<Texture> sourceTexture = m_ExtractTexture;

        for (int i = 0; i < m_BlurPasses; ++i)
        {
            // Determine targets for this iteration (explicit to avoid read/write hazards)
            std::shared_ptr<Framebuffer> horizTargetFB = (i % 2 == 0) ? m_BlurFB1 : m_BlurFB2;
            std::shared_ptr<Texture> horizTargetTex = (i % 2 == 0) ? m_BlurTexture1 : m_BlurTexture2;
            std::shared_ptr<Framebuffer> vertTargetFB = (i % 2 == 0) ? m_BlurFB2 : m_BlurFB1;
            std::shared_ptr<Texture> vertTargetTex = (i % 2 == 0) ? m_BlurTexture2 : m_BlurTexture1;

            // Horizontal pass: read from sourceTexture, write to horizTargetFB
            horizTargetFB->Bind();
            glClear(GL_COLOR_BUFFER_BIT);

            m_BlurShader->SetBool("u_Horizontal", true);
            m_BlurShader->SetInt("u_Image", 0);

            sourceTexture->Bind(0);
            m_Quad->Render();

            horizTargetFB->Unbind();

            // Vertical pass: read from horizTargetTex, write to vertTargetFB
            vertTargetFB->Bind();
            glClear(GL_COLOR_BUFFER_BIT);

            m_BlurShader->SetBool("u_Horizontal", false);
            m_BlurShader->SetInt("u_Image", 0);

            horizTargetTex->Bind(0);
            m_Quad->Render();

            vertTargetFB->Unbind();

            // Update source for next iteration
            sourceTexture = vertTargetTex;
        }

        // Return final blurred result
        return sourceTexture;
    }
}
```

**Notes**:
- **Framebuffer validation**: The constructor checks that all framebuffers are complete and sets `m_IsValid = false` if any fail, ensuring `Process()` won't run with incomplete framebuffers.
- **Shader validation**: The constructor checks that shaders loaded successfully via `IsValid()`. If validation fails, sets `m_IsValid = false` and returns early.
- **Initialization order**: `m_IsValid = true` is set **only after** all validations pass (framebuffers, shaders, quad creation), guaranteeing the Bloom object is fully initialized. 
- **Null-check in Process**: Added validation for `hdrTexture` parameter. If null, logs error and returns `nullptr` to prevent crash.
- **Ping-pong logic with explicit targets**: Uses `horizTargetFB`/`horizTargetTex` and `vertTargetFB`/`vertTargetTex` per iteration to make read/write separation crystal clear:
  - **Iteration start**: Determines all 4 targets upfront based on `i % 2`
  - **Horizontal pass**: Reads `sourceTexture` → Writes `horizTargetFB`
  - **Vertical pass**: Reads `horizTargetTex` (output of horizontal) → Writes `vertTargetFB` (opposite buffer)
  - **Next iteration**: `sourceTexture = vertTargetTex`
  - **Guarantee**: No pass ever reads from the texture it's writing to
- **Multiple blur passes**: Each iteration creates a softer bloom (5 passes = 10 total blur operations: 5 horizontal + 5 vertical)
- **RGB16F textures**: Preserve HDR values during blur

---

### Update CMakeLists.txt

**Add to** `VizEngine/CMakeLists.txt`:

```cmake
# In VIZENGINE_SOURCES (Renderer subsection)
    src/VizEngine/Renderer/Bloom.cpp

# In VIZENGINE_HEADERS (Renderer subsection)
    src/VizEngine/Renderer/Bloom.h
```

---

## Color Grading Implementation

### Neutral LUT Generation

We'll add static methods to the `Texture` class to handle 3D LUT creation and binding. This keeps OpenGL calls encapsulated in the engine layer.

**1. Update** `VizEngine/src/VizEngine/OpenGL/Texture.h` to add static methods:

```cpp
// =========================================================================
// Static Utility Methods
// =========================================================================

/**
 * Create a neutral (identity) 3D color grading LUT.
 * @param size LUT dimensions (e.g., 16 for 16x16x16)
 * @return OpenGL texture ID for GL_TEXTURE_3D (caller owns, must delete)
 */
static unsigned int CreateNeutralLUT3D(int size = 16);

/**
 * Bind a 3D texture (e.g., color grading LUT) to a texture unit.
 * @param textureID OpenGL texture ID for GL_TEXTURE_3D
 * @param slot Texture unit (0-15)
 */
static void BindTexture3D(unsigned int textureID, unsigned int slot);

/**
 * Delete a 3D texture created by CreateNeutralLUT3D.
 * @param textureID OpenGL texture ID to delete
 */
static void DeleteTexture3D(unsigned int textureID);
```

**2. Update** `VizEngine/src/VizEngine/OpenGL/Texture.cpp` to implement them:

```cpp
unsigned int Texture::CreateNeutralLUT3D(int size)
{
    const int totalTexels = size * size * size;
    std::vector<float> lutData(totalTexels * 3);

    // Generate identity mapping: input RGB = output RGB
    for (int b = 0; b < size; ++b)
    {
        for (int g = 0; g < size; ++g)
        {
            for (int r = 0; r < size; ++r)
            {
                int index = (b * size * size + g * size + r) * 3;
                lutData[index + 0] = r / float(size - 1);
                lutData[index + 1] = g / float(size - 1);
                lutData[index + 2] = b / float(size - 1);
            }
        }
    }

    // Create 3D texture
    unsigned int textureID;
    glGenTextures(1, &textureID);
    glBindTexture(GL_TEXTURE_3D, textureID);

    glTexImage3D(
        GL_TEXTURE_3D,
        0,                      // Mip level
        GL_RGB16F,              // Internal format (HDR precision)
        size, size, size,
        0,                      // Border
        GL_RGB,                 // Format
        GL_FLOAT,               // Data type
        lutData.data()
    );

    // Set texture parameters
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

    glBindTexture(GL_TEXTURE_3D, 0);

    VP_CORE_INFO("Neutral 3D LUT created: {}x{}x{} (ID: {})", size, size, size, textureID);

    return textureID;
}

void Texture::BindTexture3D(unsigned int textureID, unsigned int slot)
{
    glActiveTexture(GL_TEXTURE0 + slot);
    glBindTexture(GL_TEXTURE_3D, textureID);
}

void Texture::DeleteTexture3D(unsigned int textureID)
{
    if (textureID != 0)
    {
        glDeleteTextures(1, &textureID);
    }
}
```

> [!TIP]
> By using static methods in the `Texture` class, we keep all OpenGL calls encapsulated in the engine. This prevents linker errors in applications that don't link directly against OpenGL.

---

### Color Grading in Tone Mapping Shader

**Update** `VizEngine/src/resources/shaders/tonemapping.shader`:

Add uniforms:

```glsl
// Color Grading
uniform sampler3D u_ColorGradingLUT;
uniform bool u_EnableColorGrading;
uniform float u_LUTContribution;  // Blend factor (0=off, 1=full)

// Parametric color controls
uniform float u_Saturation;
uniform float u_Contrast;
uniform float u_Brightness;
```

Add functions:

```glsl
// ============================================================================
// Parametric Color Grading
// ============================================================================

vec3 ApplyParametricGrading(vec3 color)
{
    // Saturation
    vec3 grayscale = vec3(dot(color, vec3(0.2126, 0.7152, 0.0722)));
    color = mix(grayscale, color, u_Saturation);
    
    // Contrast
    color = (color - 0.5) * u_Contrast + 0.5;
    
    // Brightness
    color = color + u_Brightness;
    
    // Clamp to valid range
    color = clamp(color, 0.0, 1.0);
    
    return color;
}
```

Update `main()` function (after tone mapping, before gamma correction):

```glsl
    // Apply tone mapping based on selected mode
    vec3 ldrColor;
    // ... (existing tone mapping code) ...

    // ========================================================================
    // Color Grading (AFTER tone mapping, in LDR space [0,1])
    // ========================================================================
    
    // Apply parametric grading first
    ldrColor = ApplyParametricGrading(ldrColor);
    
    // Apply LUT grading (if enabled)
    if (u_EnableColorGrading)
    {
        vec3 lutColor = texture(u_ColorGradingLUT, ldrColor).rgb;
        ldrColor = mix(ldrColor, lutColor, u_LUTContribution);
    }
    
    // Apply gamma correction (linear -> sRGB)
    vec3 srgbColor = pow(ldrColor, vec3(1.0 / u_Gamma));
    
    FragColor = vec4(srgbColor, 1.0);
}
```

---

## SandboxApp Integration

### Add Members

**In** `Sandbox/src/SandboxApp.cpp`, add private members:

```cpp
private:
    // ... existing members ...

    // Bloom
    std::unique_ptr<VizEngine::Bloom> m_Bloom;
    bool m_EnableBloom = true;
    float m_BloomThreshold = 1.0f;
    float m_BloomKnee = 0.5f;
    float m_BloomIntensity = 0.04f;
    int m_BloomBlurPasses = 5;

    // Color Grading
    unsigned int m_ColorGradingLUT = 0;  // Raw OpenGL texture ID
    bool m_EnableColorGrading = false;
    float m_LUTContribution = 1.0f;
    float m_Saturation = 1.0f;
    float m_Contrast = 1.0f;
    float m_Brightness = 0.0f;
```

---

### OnCreate(): Initialize Bloom and LUT

```cpp
void OnCreate() override
{
    // ... existing setup code ...

    // ====================================================================
    // Post-Processing Setup (Chapter 36)
    // ====================================================================
    VP_INFO("Setting up post-processing...");

    // Create Bloom Processor (half resolution for performance)
    int bloomWidth = m_WindowWidth / 2;
    int bloomHeight = m_WindowHeight / 2;
    m_Bloom = std::make_unique<VizEngine::Bloom>(bloomWidth, bloomHeight);
    m_Bloom->SetThreshold(m_BloomThreshold);
    m_Bloom->SetKnee(m_BloomKnee);
    m_Bloom->SetBlurPasses(m_BloomBlurPasses);

    VP_INFO("Bloom initialized: {}x{}", bloomWidth, bloomHeight);

    // Create Neutral Color Grading LUT (16x16x16)
    m_ColorGradingLUT = VizEngine::Texture::CreateNeutralLUT3D(16);

    if (m_ColorGradingLUT == 0)
    {
        VP_ERROR("Failed to create color grading LUT!");
    }

    VP_INFO("Post-processing initialized successfully");
}
```

---

### OnRender(): Multi-Pass Rendering

**Update render loop**:

```cpp
void OnRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();

    // ... (existing light setup) ...

    // ====================================================================
    // Pass 1: Render Scene to HDR Framebuffer
    // ====================================================================
    m_Framebuffer->Bind();
    renderer.Clear(m_ClearColor);
    renderer.EnableDepthTest();
    
    m_Scene.Render(renderer, *m_DefaultLitShader, m_Camera);
    
    m_Framebuffer->Unbind();

    // ====================================================================
    // Pass 2: Generate Bloom
    // ====================================================================
    std::shared_ptr<VizEngine::Texture> bloomTexture = nullptr;
    if (m_EnableBloom)
    {
        // Update bloom parameters (in case they changed via ImGui)
        m_Bloom->SetThreshold(m_BloomThreshold);
        m_Bloom->SetKnee(m_BloomKnee);
        m_Bloom->SetBlurPasses(m_BloomBlurPasses);

        // Process HDR buffer to generate bloom
        bloomTexture = m_Bloom->Process(m_FramebufferColor);
    }

    // ====================================================================
    // Pass 3: Tone Mapping + Color Grading to Screen
    // ====================================================================
    renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);
    renderer.DisableDepthTest();
    renderer.Clear(m_ClearColor);

    m_ToneMappingShader->Bind();
    
    // HDR and tone mapping
    m_ToneMappingShader->SetInt("u_HDRBuffer", 0);
    m_ToneMappingShader->SetInt("u_ToneMappingMode", static_cast<int>(m_ToneMappingMode));
    m_ToneMappingShader->SetFloat("u_Exposure", m_Exposure);
    m_ToneMappingShader->SetFloat("u_Gamma", m_Gamma);
    m_ToneMappingShader->SetFloat("u_WhitePoint", m_WhitePoint);

    // Bloom
    m_ToneMappingShader->SetBool("u_EnableBloom", m_EnableBloom);
    m_ToneMappingShader->SetFloat("u_BloomIntensity", m_BloomIntensity);
    if (bloomTexture)
    {
        m_ToneMappingShader->SetInt("u_BloomTexture", 1);
        bloomTexture->Bind(1);
    }

    // Color grading
    m_ToneMappingShader->SetBool("u_EnableColorGrading", m_EnableColorGrading);
    m_ToneMappingShader->SetFloat("u_LUTContribution", m_LUTContribution);
    m_ToneMappingShader->SetFloat("u_Saturation", m_Saturation);
    m_ToneMappingShader->SetFloat("u_Contrast", m_Contrast);
    m_ToneMappingShader->SetFloat("u_Brightness", m_Brightness);

    if (m_EnableColorGrading && m_ColorGradingLUT != 0)
    {
        VizEngine::Texture::BindTexture3D(m_ColorGradingLUT, 2);
        m_ToneMappingShader->SetInt("u_ColorGradingLUT", 2);
    }

    // Render fullscreen quad
    m_FullscreenQuad->Render();

    // Re-enable depth test
    renderer.EnableDepthTest();
}
```

---

### OnImGuiRender(): Post-Processing Controls

```cpp
void OnImGuiRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& uiManager = engine.GetUIManager();

    // ... existing panels ...

    // ====================================================================
    // Post-Processing Panel
    // ====================================================================
    uiManager.StartWindow("Post-Processing");

    if (uiManager.CollapsingHeader("Bloom"))
    {
        uiManager.Checkbox("Enable##Bloom", &m_EnableBloom);
        uiManager.SliderFloat("Threshold", &m_BloomThreshold, 0.0f, 5.0f);
        uiManager.SliderFloat("Knee (Soft)", &m_BloomKnee, 0.0f, 1.0f);
        uiManager.SliderFloat("Intensity", &m_BloomIntensity, 0.0f, 1.0f);
        uiManager.SliderInt("Blur Passes", &m_BloomBlurPasses, 1, 10);
        
        uiManager.Separator();
        uiManager.Text("Threshold: Minimum brightness for bloom");
        uiManager.Text("Knee: Smooth transition around threshold");
        uiManager.Text("Intensity: Bloom strength (0.04 typical)");
        uiManager.Text("Blur Passes: More = softer bloom");
    }

    if (uiManager.CollapsingHeader("Color Grading"))
    {
        uiManager.Checkbox("Enable LUT##ColorGrading", &m_EnableColorGrading);
        if (m_EnableColorGrading)
        {
            uiManager.SliderFloat("LUT Contribution", &m_LUTContribution, 0.0f, 1.0f);
        }
        
        uiManager.Separator();
        uiManager.Text("Parametric Controls:");
        uiManager.SliderFloat("Saturation", &m_Saturation, 0.0f, 2.0f);
        uiManager.SliderFloat("Contrast", &m_Contrast, 0.0f, 2.0f);
        uiManager.SliderFloat("Brightness", &m_Brightness, -1.0f, 1.0f);
        
        if (uiManager.Button("Reset to Neutral"))
        {
            m_Saturation = 1.0f;
            m_Contrast = 1.0f;
            m_Brightness = 0.0f;
        }
        
        uiManager.Separator();
        uiManager.Text("Saturation: 0=grayscale, 1=normal, 2=vibrant");
        uiManager.Text("Contrast: 0=flat, 1=normal, 2=high");
        uiManager.Text("Brightness: -1=dark, 0=normal, +1=bright");
    }

    uiManager.EndWindow();
}
```

---

### OnEvent(): Handle Window Resize

When the window resizes, we need to recreate the Bloom processor to match the new dimensions:

```cpp
// In WindowResizeEvent handler, after HDR framebuffer recreation:
if (m_Bloom)
{
    VP_INFO("Recreating Bloom processor: {}x{}", m_WindowWidth / 2, m_WindowHeight / 2);
    m_Bloom = std::make_unique<VizEngine::Bloom>(m_WindowWidth / 2, m_WindowHeight / 2);
    m_Bloom->SetThreshold(m_BloomThreshold);
    m_Bloom->SetKnee(m_BloomKnee);
    m_Bloom->SetBlurPasses(m_BloomBlurPasses);
}
```

> [!NOTE]
> The color grading LUT does not need recreation on resize since it's resolution-independent.

---

## Testing and Validation

### Visual Tests

**Bloom verification**:
1. **Enable bloom**, set threshold to 1.0, intensity to 0.04
2. **Expected**: Bright specular highlights and emissive surfaces have soft glow
3. **Adjust threshold**: Lower values (0.5) = more pixels bloom; higher (2.0) = only very bright
4. **Adjust knee**: Higher values (0.5-1.0) = smoother transition, no banding
5. **Adjust blur passes**: 1 = sharp glow, 10 = very soft, diffuse halo

**No bloom on dark areas**: Ensure shadows and mid-tones don't glow (threshold working correctly)

**Color grading verification**:
1. **Saturation = 0**: Image should be grayscale
2. **Saturation = 2**: Colors should be very vibrant (potentially oversaturated)
3. **Contrast = 0**: Flat, washed out
4. **Contrast = 2**: High contrast, deeper blacks, brighter whites
5. **Brightness = -0.5**: Darker overall
6. **Brightness = +0.5**: Brighter overall

---

### Performance Benchmarks

**Expected timings** (1920×1080 scene, bloom at 960×540):
- **Bloom extraction**: < 0.3 ms
- **Bloom blur** (5 passes): 1-2 ms
- **Color grading**: < 0.1 ms (single texture lookup)
- **Total post-processing overhead**: 1.5-2.5 ms

**Optimization tips**:
- Lower bloom resolution: 1/4 instead of 1/2 (4× faster blur)
- Fewer blur passes: 3 instead of 5 (40% faster)
- Disable color grading LUT if using only parametric controls

---

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Bloom too strong** | Intensity too high | Lower `u_BloomIntensity` (try 0.02-0.06) |
| **Everything glows** | Threshold too low | Raise threshold to 1.0+ for HDR scenes |
| **Banding in bloom** | Hard threshold | Increase `u_Knee` to 0.5 or higher |
| **Bloom not visible** | Threshold too high or intensity = 0 | Lower threshold, increase intensity |
| ** Blocked/pixelated bloom** | Not enough blur passes or low resolution | Increase blur passes or bloom buffer size |
| **Color grading too strong** | LUT contribution = 1.0 with extreme LUT | Lower `u_LUTContribution` (try 0.5-0.8) |
| **Washed out colors** | Contrast too low or saturation = 0 | Reset parametric controls to neutral |
| **Performance issues** | Bloom resolution too high | Use 1/4 scene resolution instead of 1/2 |

---

## Cross-Chapter Integration

### Callbacks to Previous Chapters

> In **Chapter 27**, we implemented framebuffers for offscreen rendering. The bloom effect leverages this infrastructure heavily—bloom extraction, blur passes, and ping-pong rendering all use custom framebuffers.

> In **Chapter 35**, we built the HDR pipeline with floating-point framebuffers and tone mapping. Bloom operates in this HDR space (before tone mapping), preserving the full dynamic range of bright values. Color grading operates in LDR space (after tone mapping), matching the display range [0,1].

> The `FullscreenQuad` and multi-pass rendering techniques from **Chapter 35** are reused directly for bloom and color grading, demonstrating the modularity of our post-processing architecture.

---

### Forward References

> In **Chapter 37: Material System**, we'll add per-material emissive properties. When a material has an emissive color, it will automatically interact with bloom—emissive surfaces will glow naturally without additional code, showcasing the power of our HDR+bloom pipeline.

> The post-processing architecture established in this chapter serves as the foundation for additional effects:
> - **Depth of Field** (Chapter 38): Uses G-buffer depth to blur based on focus distance
> - **Motion Blur** (Chapter 39): Samples velocity buffer to streak along movement
> - **Screen-Space Reflections** (Chapter 40): Ray-marches against depth buffer for reflections

> **Color grading LUTs** can be extended with temporal interpolation for cinematic sequences. Imagine a character entering a dark cave—the LUT crossfades from warm (outdoor) to cool/desaturated (cave interior) over 2 seconds, creating a smooth mood transition.

---

### Architectural Notes

**Modularity**: Each post-processing effect is independent. Bloom can be toggled without affecting color grading, and vice versa. This allows artists to enable/disable effects based on performance budgets or artistic direction.

**Ping-Pong Pattern**: The dual-framebuffer approach used in bloom (swapping between `m_BlurFB1` and `m_BlurFB2`) is reusable for any multi-pass effect:
- **Temporal Anti-Aliasing (TAA)**: Blend current frame with previous frame
- **Iterative filters**: Repeated application of the same effect
- **Feedback loops**: Effects that reference their own previous output

**Separable Blur Optimization**: The 2-pass horizontal/vertical technique applies to all convolution-based effects:
- **Depth of Field**: Circular bokeh can be approximated with separable kernels
- **Shadow map blurring**: PCF or PCSS with large filter kernels
- **Ambient Occlusion**: Bilateral blur for noise reduction

**Performance Scaling**: Rendering bloom at half resolution (or quarter) demonstrates resolution-independent post-processing. This technique extends to other expensive effects—render the costly effect at low resolution, upsample to full resolution for final composite.

---

## Best Practices

### Bloom

1. **Start subtle**: `Intensity = 0.04` is a good baseline. Increase gradually.
2. **Threshold around 1.0**: For properly exposed HDR scenes, only pixels > 1.0 should bloom.
3. **Use soft knee**: Values between 0.1 and 0.5 prevent banding.
4. **Blur quality vs performance**: 5 passes is a sweet spot. 3 for performance, 7-10 for quality.
5. **Downsample**: Always render bloom at reduced resolution (1/2 or 1/4).

### Color Grading

1. **LDR space only**: Apply after tone mapping, never before.
2. **Artist workflow**: Export neutral LUT, grade in Photoshop/DaVinci, import result.
3. **Blend factor**: Allow artists to dial down LUT intensity (`u_LUTContribution < 1.0`).
4. **Multiple LUTs**: Load different LUTs for different scenes/moods, crossfade between them.
5. **Parametric as preview**: Use parametric controls for quick iteration, bake into LUT for final quality.

### General Post-Processing

1. **Order matters**: Bloom → Tone Map → Color Grade → Gamma is the standard pipeline.
2. **Toggle-able**: All effects should have an enable/disable flag for debugging.
3. **ImGui controls**: Expose all parameters for real-time tuning.
4. **Framebuffer reuse**: Ping-pong between two buffers to minimize memory.
5. **Profiling**: Measure GPU time per effect to identify bottlenecks.

---

## Milestone

At this point, your engine has **industry-standard post-processing**:

**Physically-based bloom** with soft threshold and multi-pass Gaussian blur  
**3D LUT color grading** for cinematic looks  
**Parametric color controls** (saturation, contrast, brightness)  
**Complete HDR pipeline**: Scene → HDR → Bloom → Tone Map → Color Grade → sRGB  
**Modular architecture**: Each effect is independent and toggle-able  
**Performance-optimized**: Separable blur, downsampling, ping-pong framebuffers  

**Visual comparison**:
- **Before**: Flat, game-like rendering
- **After**: Cinematic, film-like quality with depth and polish

**Next steps**: In **Chapter 37**, we'll build a Material System that abstracts shader management and parameter binding, preparing for component-based rendering with ECS. Materials with emissive properties will automatically integrate with the bloom system we just built.

---

## Resource Cleanup

### Color Grading LUT Cleanup

The color grading LUT is stored as a raw OpenGL texture ID (`m_ColorGradingLUT`) rather than being wrapped in a RAII class. This means it requires **manual cleanup** in `OnDestroy()` to prevent resource leaks.

**Update** `Sandbox/src/SandboxApp.cpp` `OnDestroy()` method:

```cpp
void OnDestroy() override
{
    // Clean up raw OpenGL resources not wrapped in RAII
    if (m_ColorGradingLUT != 0)
    {
        VizEngine::Texture::DeleteTexture3D(m_ColorGradingLUT);
        m_ColorGradingLUT = 0;
    }
}
```

> [!IMPORTANT]
> **Why manual cleanup?** The `m_ColorGradingLUT` is a raw `unsigned int` (OpenGL texture ID) created via `Texture::CreateNeutralLUT3D()`. Unlike `shared_ptr<Texture>` objects that use RAII for automatic cleanup, raw texture IDs must be explicitly deleted to avoid GPU memory leaks.

**Key points**:
- **Check before deleting**: Only delete if `m_ColorGradingLUT != 0`
- **Use correct deletion function**: `DeleteTexture3D()` for 3D textures, not `DeleteTexture()`
- **Reset to zero**: Set `m_ColorGradingLUT = 0` after deletion to prevent double-free
- **Other RAII objects**: Bloom, framebuffers, and textures wrapped in `shared_ptr` clean up automatically

---

## Summary

**Post-processing effects** transform rendered images to achieve photorealistic or stylized visuals:

**Bloom** simulates lens scatter, creating soft glows around bright regions:
1. **Extract** bright pixels (threshold with soft knee)
2. **Blur** with separable Gaussian (2-pass: horizontal, vertical)
3. **Composite** additive blend back to HDR buffer (before tone mapping)

**Color Grading** remaps colors for cinematic looks:
- **3D LUT**: Pre-baked transformation (fast, flexible, artist-friendly)
- **Parametric**: Real-time controls (saturation, contrast, brightness)
- Apply **after tone mapping** in LDR space [0,1]

**Architecture**:
- Multi-pass rendering with custom framebuffers
- Ping-pong pattern for blur iterations
- Modularity: Each effect is independent
- Performance: Downsampling, separable filters, optimized sampling

**Pipeline order**:
```
Scene → HDR → Bloom Extract → Blur → Composite → Tone Map → Color Grade → Gamma → Screen
```

This chapter establishes the **post-processing foundation** used in all modern game engines (Unreal, Unity, CryEngine). Future effects (depth of field, motion blur, SSR) follow the same patterns and integrate seamlessly into this pipeline.
