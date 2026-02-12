\newpage

# Chapter 40: Bloom Post-Processing

Implement industry-standard bloom effect using physically-based bright-pass filtering and multi-pass Gaussian blur to achieve cinematic glow around bright regions.

---

## Introduction

In **Chapter 39**, we built a complete HDR rendering pipeline with tone mapping. Our engine now renders in HDR (RGB16F framebuffers) and maps to display space using operators like ACES Filmic. This gives us linear light values throughout the rendering pipeline and professional tone mapping at the end.

**What's missing?** The cinematic polish that makes modern games look photorealistic. Compare a screenshot from *The Last of Us Part II* or *Cyberpunk 2077* to our current output—there's a noticeable difference in visual richness.

**Post-processing effects** bridge this gap. They're image-space effects applied *after* scene rendering:

```
Scene Render → HDR Framebuffer → Post-Processing → Tone Mapping → Screen
     ↓              ↓                    ↓               ↓           ↓
  PBR + IBL    Raw HDR values        Bloom          Map to LDR   Display
```

This chapter focuses on the **bloom effect**, the most impactful post-processing technique for realism. Bloom simulates the natural glow that occurs when extremely bright light scatters in camera lenses or the human eye, making HDR values visible even after tone mapping. In the next chapter, we'll add color grading to complete our post-processing pipeline.

### What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **Bloom Effect** | Physically-based glow around bright regions with soft threshold filtering |
| **Gaussian Blur** | Separable 2-pass blur with optimized kernel weights |
| **Bloom Class** | Reusable post-processing component with ping-pong framebuffers |
| **HDR Integration** | Bloom composited before tone mapping in HDR space |
| **ImGui Controls** | Runtime controls for threshold, intensity, and blur passes |

**Visual Impact**: Bloom makes bright surfaces glow naturally, mimicking camera lens scatter. Only pixels with luminance significantly above the scene average will bloom, creating realistic highlights on metals, lights, and emissive surfaces.

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

We're implementing **bloom** because:
1. **Most impactful** for realism (makes HDR visible)
2. **Foundation** for the post-processing pipeline architecture
3. **Demonstrates** multi-pass rendering with custom framebuffers

**Other effects** (depth of field, motion blur, etc.) follow the same pattern and can be added incrementally. Color grading will be covered in Chapter 41.

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

### Bright Pass Filtering

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

### Gaussian Blur

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

### Bloom Composite

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
Gamma Correction → Linear→sRGB (typically 1/2.2)
   ↓
Final Output → Screen (default framebuffer)
```

**Key insight**: 
- **Bloom** operates in **HDR space** (before tone mapping)
- This preserves the full dynamic range of bright values

> [!NOTE]
> Color grading (covered in Chapter 41) operates in **LDR space** (after tone mapping).

---

### Framebuffer Strategy

**Requirements**:
- HDR framebuffer (already exists from Chapter 39)
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

## Step 1: Engine Extensions

Before we implement the bloom effect, we need to extend our core engine components with a few utility functions for configuration and shader management.

### Add Shader Uniform Support

We'll need to pass `vec2` uniforms (e.g., texture sizes) to our shaders for the Gaussian blur.

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

### Extend UI Controls

For tweaking bloom parameters, we'll need integer sliders (for iteration counts) and collapsible headers (for organizing the settings) in our `UIManager`.

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

## Step 2: Create Bloom Extraction Shader

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

//============================================================================
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

## Step 3: Create Gaussian Blur Shader

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

## Step 4: Create Bloom Class

This class encapsulates the entire bloom pipeline: extraction, blur, and resource management.

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
         * @return Bloom texture (same resolution as bloom buffers)
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
            return;
        }

        // ====================================================================
        // Load Shaders
        // ====================================================================
        m_ExtractShader = std::make_shared<Shader>("resources/shaders/bloom_extract.shader");
        m_BlurShader = std::make_shared<Shader>("resources/shaders/bloom_blur.shader");

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
        // Save and disable depth test (post-processing operates in 2D)
        // ====================================================================
        GLboolean depthTestEnabled;
        glGetBooleanv(GL_DEPTH_TEST, &depthTestEnabled);
        glDisable(GL_DEPTH_TEST);

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
            // Ping-pong between buffer pairs to avoid read/write conflicts:
            // - If source is Blur1, write horizontal to Blur2, vertical to Blur1
            // - Otherwise (Extract or Blur2), write horizontal to Blur1, vertical to Blur2
            bool sourceIsBlur1 = (sourceTexture == m_BlurTexture1);
            
            std::shared_ptr<Framebuffer> intermediateFB = sourceIsBlur1 ? m_BlurFB2 : m_BlurFB1;
            std::shared_ptr<Texture> intermediateTex = sourceIsBlur1 ? m_BlurTexture2 : m_BlurTexture1;
            std::shared_ptr<Framebuffer> finalFB = sourceIsBlur1 ? m_BlurFB1 : m_BlurFB2;
            std::shared_ptr<Texture> finalTex = sourceIsBlur1 ? m_BlurTexture1 : m_BlurTexture2;

            // Horizontal pass: read from sourceTexture, write to intermediateFB
            intermediateFB->Bind();
            glClear(GL_COLOR_BUFFER_BIT);
            m_BlurShader->SetBool("u_Horizontal", true);
            m_BlurShader->SetInt("u_Image", 0);
            sourceTexture->Bind(0);
            m_Quad->Render();
            intermediateFB->Unbind();

            // Vertical pass: read from intermediateTex, write to finalFB
            finalFB->Bind();
            glClear(GL_COLOR_BUFFER_BIT);
            m_BlurShader->SetBool("u_Horizontal", false);
            m_BlurShader->SetInt("u_Image", 0);
            intermediateTex->Bind(0);
            m_Quad->Render();
            finalFB->Unbind();

            // Update source for next iteration
            sourceTexture = finalTex;
        }

        // ====================================================================
        // Restore depth test state
        // ====================================================================
        if (depthTestEnabled)
            glEnable(GL_DEPTH_TEST);

        // Return final blurred result
        return sourceTexture;
    }
}
```

**Notes**:
- **Depth test state management**: Saves depth test state, disables for 2D post-processing, then restores. This prevents rendering artifacts if called when depth test is enabled.
- **Framebuffer validation**: The constructor checks that all framebuffers are complete and sets `m_IsValid = false` if any fail
- **Shader validation**: The constructor checks that shaders loaded successfully via `IsValid()`
- **Null-check in Process**: Added validation for `hdrTexture` parameter
- **Ping-pong logic**: Checks if source is `Blur1` to determine buffer targets, ensuring no read/write conflicts within a pass
- **Multiple blur passes**: Each iteration creates a softer bloom (5 passes = 10 total blur operations)
- **RGB16F textures**: Preserve HDR values during blur

---

## Step 5: Modify Tone Mapping Shader for Bloom Composite

**Update** `VizEngine/src/resources/shaders/tonemapping.shader`:

Add uniforms after existing uniforms (after gamma/exposure/etc):

```glsl
// Bloom
uniform sampler2D u_BloomTexture;
uniform float u_BloomIntensity;
uniform bool u_EnableBloom;
```

In `main()` function, **before** tone mapping (right after sampling HDR buffer):

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
5. Gamma correct

---

## Step 6: Update CMakeLists.txt

**Add to** `VizEngine/CMakeLists.txt`:

```cmake
# In VIZENGINE_SOURCES (Renderer subsection)
    src/VizEngine/Renderer/Bloom.cpp

# In VIZENGINE_HEADERS (Renderer subsection)
    src/VizEngine/Renderer/Bloom.h
```

---

## Step 7: Integrate Bloom into SandboxApp

### Add Members

**In** `Sandbox/src/SandboxApp.cpp`, add private members:

```cpp
private:
    // ... existing members ...

    // Bloom (Chapter 40)
    std::unique_ptr<VizEngine::Bloom> m_Bloom;
    bool m_EnableBloom = true;
    float m_BloomThreshold = 1.5f;   // Higher threshold for properly balanced scenes
    float m_BloomKnee = 0.5f;
    float m_BloomIntensity = 0.04f;
    int m_BloomBlurPasses = 5;
```

---

### OnCreate(): Initialize Bloom

Add at the end of your existing `OnCreate()` method:

```cpp
void OnCreate() override
{
    // ... existing setup code ...

    // ====================================================================
    // Bloom Setup (Chapter 40)
    // ====================================================================
    VP_INFO("Setting up bloom...");

    // Create Bloom Processor (half resolution for performance)
    int bloomWidth = m_WindowWidth / 2;
    int bloomHeight = m_WindowHeight / 2;
    m_Bloom = std::make_unique<VizEngine::Bloom>(bloomWidth, bloomHeight);
    m_Bloom->SetThreshold(m_BloomThreshold);
    m_Bloom->SetKnee(m_BloomKnee);
    m_Bloom->SetBlurPasses(m_BloomBlurPasses);

    VP_INFO("Bloom initialized: {}x{}", bloomWidth, bloomHeight);
}
```

---

### OnRender(): Add Bloom Pass

**Insert the bloom pass** between HDR rendering and tone mapping from Chapter 39.

Your `OnRender()` from Chapter 39 currently has two passes:
- **Pass 1**: Render to HDR framebuffer
- **Pass 2**: Tone mapping to screen

We'll add **Pass 2 (Bloom)** in between, making it a 3-pass pipeline.

**Add after the HDR framebuffer unbind, before tone mapping**:

```cpp
void OnRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();

    // =========================================================================
    // Pass 1: Render Scene to HDR Framebuffer (from Chapter 39)
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
        // LDR fallback
        renderer.Clear(m_ClearColor);
        SetupDefaultLitShader();
        RenderSceneObjects();
        if (m_ShowSkybox && m_Skybox)
        {
            m_Skybox->Render(m_Camera);
        }
    }

    // =========================================================================
    // Pass 2: Generate Bloom (NEW - Chapter 40)
    // =========================================================================
    std::shared_ptr<VizEngine::Texture> bloomTexture = nullptr;
    if (m_HDREnabled && m_EnableBloom && m_Bloom && m_HDRColorTexture)
    {
        m_Bloom->SetThreshold(m_BloomThreshold);
        m_Bloom->SetKnee(m_BloomKnee);
        m_Bloom->SetBlurPasses(m_BloomBlurPasses);
        bloomTexture = m_Bloom->Process(m_HDRColorTexture);
    }

    // =========================================================================
    // Pass 3: Tone Mapping + Bloom Composite (from Chapter 39, updated)
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

        // NEW: Bloom parameters
        m_ToneMappingShader->SetBool("u_EnableBloom", m_EnableBloom);
        m_ToneMappingShader->SetFloat("u_BloomIntensity", m_BloomIntensity);
        if (bloomTexture)
        {
            bloomTexture->Bind(1);
            m_ToneMappingShader->SetInt("u_BloomTexture", 1);
        }

        m_FullscreenQuad->Render();
        renderer.EnableDepthTest();
    }
}
```

**What Changed**:

1. **Added Pass 2**: Bloom processing between HDR rendering and tone mapping
2. **Updated Pass 3**: Added bloom uniform bindings to the existing tone mapping pass
3. **Preserved structure**: Kept the HDR/LDR fallback and `SetupDefaultLitShader()` from Chapter 39

> [!NOTE]
> If you also implemented shadow mapping (Chapter 28), it would be **Pass 1** before HDR rendering. The numbering here reflects the HDR pipeline from Chapter 39.

---

### OnImGuiRender(): Bloom Controls

Add a new Post-Processing panel:

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
        uiManager.Checkbox("Enable Bloom", &m_EnableBloom);
        uiManager.SliderFloat("Threshold", &m_BloomThreshold, 0.0f, 5.0f);
        uiManager.SliderFloat("Knee", &m_BloomKnee, 0.0f, 1.0f);
        uiManager.SliderFloat("Intensity", &m_BloomIntensity, 0.0f, 0.2f);
        uiManager.SliderInt("Blur Passes", &m_BloomBlurPasses, 1, 10);
    }

    uiManager.EndWindow();
}
```

---

### OnEvent(): Handle Window Resize

When the window resizes, recreate the Bloom processor to match the new dimensions:

```cpp
// In WindowResizeEvent handler, after HDR framebuffer recreation:
if (m_Bloom)
{
    VP_INFO("Recreating Bloom processor: {}x{}", m_WindowWidth / 2, m_WindowHeight / 2);
    
    // Preserve old bloom processor and settings
    auto oldBloom = std::move(m_Bloom);
    
    try
    {
        // Attempt to create new bloom processor
        auto newBloom = std::make_unique<VizEngine::Bloom>(m_WindowWidth / 2, m_WindowHeight / 2);
        
        if (newBloom)
        {
            // Copy settings from old bloom to new
            newBloom->SetThreshold(m_BloomThreshold);
            newBloom->SetKnee(m_BloomKnee);
            newBloom->SetBlurPasses(m_BloomBlurPasses);
            
            // Success - swap in new bloom processor
            m_Bloom = std::move(newBloom);
        }
        else
        {
            // Failed to create - restore old bloom
            VP_ERROR("Failed to create new Bloom processor, keeping previous instance");
            m_Bloom = std::move(oldBloom);
        }
    }
    catch (const std::exception& e)
    {
        // Exception during creation - restore old bloom
        VP_ERROR("Exception while recreating Bloom processor: {}", e.what());
        VP_ERROR("Keeping previous Bloom instance");
        m_Bloom = std::move(oldBloom);
    }
}
```

> [!TIP]
> The Bloom processor contains multiple internal framebuffers. Using move semantics (`std::move`) is essential to avoid expensive framebuffer copies and ensure the old processor is properly released when the swap succeeds.

---

## Step 8: Testing and Validation

### Visual Tests

**Bloom verification**:
1. **Enable bloom**, set threshold to 1.5, intensity to 0.04
2. **Expected**: Bright specular highlights and emissive surfaces have soft glow
3. **Adjust threshold**: Lower values (0.5) = more pixels bloom; higher (2.0+) = only very bright
4. **Adjust knee**: Higher values (0.5-1.0) = smoother transition, no banding
5. **Adjust blur passes**: 1 = sharp glow, 10 = very soft, diffuse halo

**No bloom on dark areas**: Ensure shadows and mid-tones don't glow (threshold working correctly)

---

### Performance Benchmarks

**Expected timings** (1920×1080 scene, bloom at 960×540):
- **Bloom extraction**: < 0.3 ms
- **Bloom blur** (5 passes): 1-2 ms
- **Total bloom overhead**: 1.5-2.5 ms

**Optimization tips**:
- Lower bloom resolution: 1/4 instead of 1/2 (4× faster blur)
- Fewer blur passes: 3 instead of 5 (40% faster)

---

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Bloom too strong** | Intensity too high | Lower `u_BloomIntensity` (try 0.02-0.06) |
| **Everything glows** | Threshold too low | Raise threshold to 1.5+ for properly lit HDR scenes |
| **Banding in bloom** | Hard threshold | Increase `u_Knee` to 0.5 or higher |
| **Bloom not visible** | Threshold too high or intensity = 0 | Lower threshold, increase intensity |
| **Blocky/pixelated bloom** | Not enough blur passes or low resolution | Increase blur passes or bloom buffer size |
| **Performance issues** | Bloom resolution too high | Use 1/4 scene resolution instead of 1/2 |

---

## Best Practices

### Bloom Configuration

1. **Start subtle**: `Intensity = 0.04` is a good baseline. Increase gradually.
2. **Threshold around 1.5**: For properly exposed HDR scenes with balanced lighting, a threshold of 1.5 ensures only genuinely bright pixels bloom. Lower to 1.0 if your scene is darker.
3. **Use soft knee**: Values between 0.1 and 0.5 prevent banding.
4. **Blur quality vs performance**: 5 passes is a sweet spot. 3 for performance, 7-10 for quality.
5. **Downsample**: Always render bloom at reduced resolution (1/2 or 1/4).

### Architecture Notes

**Modularity**: Bloom is independent from other post-processing effects. It can be toggled without affecting anything else, allowing artists to enable/disable based on performance budgets or artistic direction.

**Ping-Pong Pattern**: The dual-framebuffer approach (swapping between `m_BlurFB1` and `m_BlurFB2`) is reusable for any multi-pass effect:
- **Temporal Anti-Aliasing (TAA)**: Blend current frame with previous frame
- **Iterative filters**: Repeated application of the same effect
- **Feedback loops**: Effects that reference their own previous output

**Separable Blur Optimization**: The 2-pass horizontal/vertical technique applies to all convolution-based effects:
- **Depth of Field**: Circular bokeh can be approximated with separable kernels
- **Shadow map blurring**: PCF or PCSS with large filter kernels
- **Ambient Occlusion**: Bilateral blur for noise reduction

---

## Milestone

**Chapter 40 Complete - Bloom Post-Processing**

At this point, your engine has **industry-standard bloom**:

**Physically-based bloom** with soft threshold and multi-pass Gaussian blur  
**Performance-optimized**: Separable blur, downsampling, ping-pong framebuffers  
**Complete HDR integration**: Bloom operates in HDR space before tone mapping  
**Modular architecture**: Bloom is independent and toggle-able  
**Runtime controls**: ImGui sliders for all bloom parameters  

**Visual comparison**:
- **Before**: Rendered highlights clamp to white, no glow
- **After**: Bright surfaces have natural, soft glow that feels cinematic

---

## What's Next

In **Chapter 41: Color Grading**, we'll add the final piece of our post-processing pipeline: LUT-based color grading and parametric color controls (saturation, contrast, brightness). This will allow artists to establish mood and visual identity for different scenes.

> **Next:** [Chapter 41: Color Grading](41_ColorGrading.md)

> **Previous:** [Chapter 39: HDR Pipeline](39_HDRPipeline.md)

> **Index:** [Table of Contents](INDEX.md)
