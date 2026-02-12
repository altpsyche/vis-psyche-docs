\newpage

# Chapter 41: Color Grading

Implement LUT-based color grading and parametric color controls to achieve cinematic color palettes and establish visual identity for your scenes.

---

## Introduction

In **Chapter 40**, we implemented the bloom effect, adding realistic glow to bright surfaces by operating in HDR space before tone mapping. Our post-processing pipeline now handles bloom extraction, Gaussian blur, and bloom compositing.

**What's still missing?** The ability to establish mood and visual identity through color. Compare any AAA game screenshot—each has a distinct color palette that evokes emotion and guides the player. *The Last of Us* uses desaturated greens and browns for a post-apocalyptic feel. *Cyberpunk 2077* uses vibrant neons and deep blues. *Mad Max* uses orange/teal contrast.

**Color grading** is the process of altering the colors of an image to achieve a specific aesthetic or mood. Originated in film production, where colorists adjust footage in post-production, it's now essential in games for establishing visual identity.

This chapter completes our post-processing pipeline by adding:
- **3D LUT (Look-Up Table)** support for pre-baked color transformations
- **Parametric controls** for real-time color adjustments (saturation, contrast, brightness)
- **Artist-friendly workflow** using familiar tools like Photoshop or DaVinci Resolve

### What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **3D LUT Support** | Pre-baked color transformation via 3D texture sampling |
| **Neutral LUT Generation** | Identity mapping as a starting point for custom LUTs |
| **Parametric Controls** | Real-time saturation, contrast, and brightness adjustment |
| **Tone Mapping Integration** | Color grading applied after tone mapping in LDR space [0,1] |
| **ImGui Controls** | Runtime controls for all color grading parameters |

**Visual Impact**: Color grading establishes mood (warm = safe, cool = danger), differentiates locations (forest = green, desert = yellow), and creates time-of-day variations (sunrise = pink/orange, night = blue).

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

## Post-Processing Pipeline Review

Before implementing color grading, let's review where it fits in the pipeline:

```
Scene Rendering
   ↓
HDR Framebuffer (RGB16F, raw linear light values)
   ↓
Bloom Extraction → Bright regions only (threshold filter)
   ↓
Bloom Blur (horizontal + vertical) → Final bloom texture
   ↓
Bloom Composite → Add bloom to HDR buffer
   ↓
Tone Mapping → HDR→LDR (ACES Filmic, etc.)
   ↓
Color Grading → LUT or parametric (operates in LDR [0,1])  ← NEW
   ↓
Gamma Correction → Linear→sRGB (typically 1/2.2)
   ↓
Final Output → Screen (default framebuffer)
```

**Key insight**: 
- **Bloom** operates in **HDR space** (before tone mapping)
- **Color grading** operates in **LDR space** (after tone mapping)

This ensures color grading works with perceptually uniform values in the [0,1] range.

---

## Step 1: Texture3D RAII Class

We use a dedicated `Texture3D` class with RAII (Resource Acquisition Is Initialization) to manage 3D textures. This ensures automatic cleanup when the texture goes out of scope—no manual deletion required.

**Create** `VizEngine/src/VizEngine/OpenGL/Texture3D.h`:

```cpp
#pragma once

#include "VizEngine/Core.h"
#include <glad/glad.h>
#include <memory>

namespace VizEngine
{
    /**
     * RAII wrapper for OpenGL 3D textures.
     * Used for color grading LUTs and volumetric textures.
     */
    class VizEngine_API Texture3D
    {
    public:
        /**
         * Create a neutral (identity) color grading LUT.
         * @param size LUT dimensions (e.g., 16 for 16x16x16)
         */
        static std::unique_ptr<Texture3D> CreateNeutralLUT(int size = 16);

        /**
         * Create from raw data.
         * @param width, height, depth Dimensions
         * @param data RGB float data (size * size * size * 3 floats)
         */
        Texture3D(int width, int height, int depth, const float* data);

        ~Texture3D();

        // Non-copyable
        Texture3D(const Texture3D&) = delete;
        Texture3D& operator=(const Texture3D&) = delete;

        // Movable
        Texture3D(Texture3D&& other) noexcept;
        Texture3D& operator=(Texture3D&& other) noexcept;

        void Bind(unsigned int slot = 0) const;
        void Unbind() const;

        unsigned int GetID() const { return m_Texture; }
        int GetWidth() const { return m_Width; }
        int GetHeight() const { return m_Height; }
        int GetDepth() const { return m_Depth; }

    private:
        Texture3D() = default;  // For factory method

        unsigned int m_Texture = 0;
        int m_Width = 0;
        int m_Height = 0;
        int m_Depth = 0;
    };
}
```

> [!NOTE]
> **Why RAII?** The destructor automatically calls `glDeleteTextures`, preventing GPU memory leaks. When `unique_ptr<Texture3D>` goes out of scope, cleanup happens automatically—no manual `OnDestroy()` code needed.

---

## Step 2: Implement Texture3D

**Create** `VizEngine/src/VizEngine/OpenGL/Texture3D.cpp`:

```cpp
#include "Texture3D.h"
#include "VizEngine/Log.h"
#include <vector>

namespace VizEngine
{
    std::unique_ptr<Texture3D> Texture3D::CreateNeutralLUT(int size)
    {
        // Early validation to prevent division by zero
        if (size <= 0)
        {
            VP_CORE_ERROR("Texture3D::CreateNeutralLUT: Invalid size {} (must be > 0)", size);
            return nullptr;
        }

        std::vector<float> data(size * size * size * 3);

        // Safe denominator to prevent division by zero when size <= 1
        const float denom = (size > 1) ? static_cast<float>(size - 1) : 1.0f;

        // Generate identity mapping: input RGB = output RGB
        for (int b = 0; b < size; ++b)
        {
            for (int g = 0; g < size; ++g)
            {
                for (int r = 0; r < size; ++r)
                {
                    int index = (b * size * size + g * size + r) * 3;
                    data[index + 0] = static_cast<float>(r) / denom;
                    data[index + 1] = static_cast<float>(g) / denom;
                    data[index + 2] = static_cast<float>(b) / denom;
                }
            }
        }

        auto lut = std::unique_ptr<Texture3D>(new Texture3D());
        lut->m_Width = size;
        lut->m_Height = size;
        lut->m_Depth = size;

        glGenTextures(1, &lut->m_Texture);
        glBindTexture(GL_TEXTURE_3D, lut->m_Texture);

        glTexImage3D(GL_TEXTURE_3D, 0, GL_RGB16F,
            size, size, size, 0,
            GL_RGB, GL_FLOAT, data.data());

        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

        glBindTexture(GL_TEXTURE_3D, 0);

        VP_CORE_INFO("Texture3D LUT created: {}x{}x{}, ID={}", size, size, size, lut->m_Texture);

        return lut;
    }

    Texture3D::Texture3D(int width, int height, int depth, const float* data)
        : m_Width(width), m_Height(height), m_Depth(depth)
    {
        glGenTextures(1, &m_Texture);
        glBindTexture(GL_TEXTURE_3D, m_Texture);

        glTexImage3D(GL_TEXTURE_3D, 0, GL_RGB16F,
            width, height, depth, 0,
            GL_RGB, GL_FLOAT, data);

        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

        glBindTexture(GL_TEXTURE_3D, 0);
    }

    Texture3D::~Texture3D()
    {
        if (m_Texture != 0)
        {
            VP_CORE_INFO("Texture3D destroyed: ID={}", m_Texture);
            glDeleteTextures(1, &m_Texture);
            m_Texture = 0;
        }
    }

    // Move constructor and assignment operator...
    // (Transfer ownership, zero out source)

    void Texture3D::Bind(unsigned int slot) const
    {
        glActiveTexture(GL_TEXTURE0 + slot);
        glBindTexture(GL_TEXTURE_3D, m_Texture);
    }

    void Texture3D::Unbind() const
    {
        glBindTexture(GL_TEXTURE_3D, 0);
    }
}
```

> [!TIP]
> **Add to CMakeLists.txt**: Include `src/VizEngine/OpenGL/Texture3D.cpp` in `VIZENGINE_SOURCES` and `src/VizEngine/OpenGL/Texture3D.h` in `VIZENGINE_HEADERS`.

---

## Step 3: Add Color Grading to Tone Mapping Shader

**Update** `VizEngine/src/resources/shaders/tonemapping.shader`:

Add uniforms (after bloom uniforms):

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

Add parametric grading function:

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

**Order is critical**:
1. Tone map HDR → LDR
2. Apply parametric grading
3. Apply LUT grading (optional)
4. Gamma correct

---

## Step 4: Add Parametric Controls

The parametric controls are already integrated into the shader from Step 3. Now we need to expose them to the application.

**Explanation of Parametric Controls**:

**Saturation**:
- `0.0` = Grayscale (completely desaturated)
- `1.0` = Normal (original colors)
- `2.0` = Oversaturated (very vibrant)

**Contrast**:
- `0.0` = Flat (no contrast, washed out)
- `1.0` = Normal (original contrast)
- `2.0` = High contrast (deeper blacks, brighter whites)

**Brightness**:
- `-1.0` = Very dark
- `0.0` = Normal (original brightness)
- `+1.0` = Very bright

These controls are applied **before** the LUT, allowing artists to quickly experiment with different looks without exporting new LUTs.

---

## Step 5: Integrate into SandboxApp

### Add Members

**In** `Sandbox/src/SandboxApp.cpp`, add private members (add to existing bloom members from Chapter 40):

```cpp
private:
    // ... existing members including bloom from Chapter 40 ...

    // Color Grading (Chapter 41)
    std::unique_ptr<VizEngine::Texture3D> m_ColorGradingLUT;  // RAII wrapper
    bool m_EnableColorGrading = false;
    float m_LUTContribution = 1.0f;
    float m_Saturation = 1.0f;
    float m_Contrast = 1.0f;
    float m_Brightness = 0.0f;
```

> [!NOTE]
> **RAII vs Raw ID**: Using `unique_ptr<Texture3D>` instead of `unsigned int` means automatic cleanup—no manual deletion in `OnDestroy()` required.

---

### OnCreate(): Initialize Color Grading LUT

Add to your existing `OnCreate()` method (after bloom initialization):

```cpp
void OnCreate() override
{
    // ... existing setup code including bloom (Chapter 40) ...

    // ====================================================================
    // Color Grading Setup (Chapter 41)
    // ====================================================================
    VP_INFO("Setting up color grading...");

    // Create Neutral Color Grading LUT (16x16x16) using RAII wrapper
    m_ColorGradingLUT = VizEngine::Texture3D::CreateNeutralLUT(16);

    if (!m_ColorGradingLUT)
    {
        VP_ERROR("Failed to create color grading LUT!");
    }

    VP_INFO("Color grading initialized successfully");
}
```

---

### OnRender(): Add Color Grading Uniforms

Update your existing tone mapping pass from Chapter 40 to include color grading:

```cpp
void OnRender() override
{
    // ... (existing HDR rendering and bloom from Chapter 40) ...

    // ====================================================================
    // Pass 3: Tone Mapping + Bloom + Color Grading to Screen
    // ====================================================================
    renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);
    renderer.DisableDepthTest();
    renderer.Clear(m_ClearColor);

    m_ToneMappingShader->Bind();
    
    // HDR and tone mapping
    m_ToneMappingShader->SetInt("u_HDRBuffer", 0);
    m_ToneMappingShader->SetInt("u_ToneMappingMode", m_ToneMappingMode);
    m_ToneMappingShader->SetFloat("u_Exposure", m_Exposure);
    m_ToneMappingShader->SetFloat("u_Gamma", m_Gamma);
    m_ToneMappingShader->SetFloat("u_WhitePoint", m_WhitePoint);

    // Bloom (from Chapter 40)
    m_ToneMappingShader->SetBool("u_EnableBloom", m_EnableBloom);
    m_ToneMappingShader->SetFloat("u_BloomIntensity", m_BloomIntensity);
    if (bloomTexture)
    {
        m_ToneMappingShader->SetInt("u_BloomTexture", 1);
        bloomTexture->Bind(1);
    }

    // Color grading (NEW - Chapter 41)
    m_ToneMappingShader->SetBool("u_EnableColorGrading", m_EnableColorGrading);
    m_ToneMappingShader->SetFloat("u_LUTContribution", m_LUTContribution);
    m_ToneMappingShader->SetFloat("u_Saturation", m_Saturation);
    m_ToneMappingShader->SetFloat("u_Contrast", m_Contrast);
    m_ToneMappingShader->SetFloat("u_Brightness", m_Brightness);

    if (m_EnableColorGrading && m_ColorGradingLUT)
    {
        m_ColorGradingLUT->Bind(VizEngine::TextureSlots::ColorGradingLUT);
        m_ToneMappingShader->SetInt("u_ColorGradingLUT", VizEngine::TextureSlots::ColorGradingLUT);
    }

    m_FramebufferColor->Bind(0);

    // Render fullscreen quad
    m_FullscreenQuad->Render();

    // Re-enable depth test
    renderer.EnableDepthTest();
}
```

---

### OnImGuiRender(): Color Grading Controls

Update your existing Post-Processing panel from Chapter 40 to add color grading:

```cpp
void OnImGuiRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& uiManager = engine.GetUIManager();

    // ... existing panels ...

    // ====================================================================
    // Post-Processing Panel (Chapters 40 & 41)
    // ====================================================================
    uiManager.StartWindow("Post-Processing");

    // Bloom controls (from Chapter 40)
    if (uiManager.CollapsingHeader("Bloom"))
    {
        uiManager.Checkbox("Enable Bloom", &m_EnableBloom);
        uiManager.SliderFloat("Threshold", &m_BloomThreshold, 0.0f, 5.0f);
        uiManager.SliderFloat("Knee", &m_BloomKnee, 0.0f, 1.0f);
        uiManager.SliderFloat("Intensity", &m_BloomIntensity, 0.0f, 0.2f);
        uiManager.SliderInt("Blur Passes", &m_BloomBlurPasses, 1, 10);
    }

    // Color Grading controls (NEW - Chapter 41)
    if (uiManager.CollapsingHeader("Color Grading"))
    {
        uiManager.Checkbox("Enable Color Grading", &m_EnableColorGrading);
        uiManager.SliderFloat("LUT Contribution", &m_LUTContribution, 0.0f, 1.0f);

        uiManager.Separator();
        uiManager.Text("Parametric Controls");
        uiManager.SliderFloat("Saturation", &m_Saturation, 0.0f, 2.0f);
        uiManager.SliderFloat("Contrast", &m_Contrast, 0.5f, 2.0f);
        uiManager.SliderFloat("Brightness", &m_Brightness, -0.5f, 0.5f);
    }

    uiManager.EndWindow();
}
```

---

## Step 6: Resource Cleanup (RAII)

### Automatic Cleanup via RAII

Because `m_ColorGradingLUT` is a `unique_ptr<Texture3D>`, cleanup is **automatic**. When the `SandboxApp` object is destroyed, the `unique_ptr` destructor runs, which calls `Texture3D::~Texture3D()`, which calls `glDeleteTextures`.

**No manual cleanup required:**

```cpp
void OnDestroy() override
{
    // No manual cleanup needed for m_ColorGradingLUT!
    // unique_ptr<Texture3D> handles deletion automatically via RAII.

    // Other cleanup (if any)...
}
```

> [!TIP]
> **RAII Advantage**: By wrapping OpenGL resources in classes with proper destructors, we eliminate memory leak bugs. The compiler ensures cleanup happens—even if exceptions are thrown or early returns occur.

**Key points**:
- **No manual deletion**: `unique_ptr` destructor handles it
- **No null checks**: `unique_ptr::reset()` handles null automatically
- **No double-free bugs**: Move semantics prevent aliasing
- **Resolution-independent**: LUT doesn't need recreation on window resize (it's a lookup table, not a render target)

> [!NOTE]
> This RAII pattern is consistent with how we handle `Texture`, `Shader`, `Framebuffer`, and other GPU resources throughout the engine.

---

## Step 7: Testing and Validation

### Visual Tests

**Color grading verification**:
1. **Saturation = 0**: Image should be grayscale
2. **Saturation = 2**: Colors should be very vibrant (potentially oversaturated)
3. **Contrast = 0**: Flat, washed out
4. **Contrast = 2**: High contrast, deeper blacks, brighter whites
5. **Brightness = -0.5**: Darker overall
6. **Brightness = +0.5**: Brighter overall

**LUT verification**:
1. **Disable LUT** (`m_EnableColorGrading = false`): Should see only parametric effects
2. **Enable LUT with neutral** (`m_EnableColorGrading = true`): No visual change (identity mapping)
3. **LUT Contribution = 0.5**: Should blend 50% between original and LUT

---

### Performance Benchmarks

**Expected timings**:
- **Color grading (parametric)**: < 0.05 ms
- **Color grading (LUT)**: < 0.1 ms (single 3D texture lookup)
- **Total post-processing overhead** (bloom + color grading): 1.6-2.6 ms

**Optimization tips**:
- Disable LUT if using only parametric controls (saves texture lookup)
- Consider baking parametric settings into a custom LUT for production

---

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Color grading too strong** | LUT contribution = 1.0 with extreme LUT | Lower `u_LUTContribution` (try 0.5-0.8) |
| **Washed out colors** | Contrast too low or saturation = 0 | Reset parametric controls to neutral |
| **No effect visible** | Applied before tone mapping | Ensure color grading is after tone mapping |
| **LUT not loading** | Wrong texture format or binding | Check `glTexImage3D` parameters |

---

## Cross-Chapter Integration

### Callbacks to Previous Chapters

> In **Chapter 39**, we built the HDR pipeline with tone mapping. Color grading extends this by operating in the LDR space after tone mapping, where values are guaranteed to be in [0,1] range—perfect for perceptual color transformations.

> In **Chapter 40**, we implemented bloom which operates in HDR space (before tone mapping). Color grading complements bloom by working in LDR space (after tone mapping), demonstrating the complete post-processing pipeline architecture.

> The multi-pass rendering approach from **Chapter 27** (Framebuffers) underlies both bloom and color grading, showing how custom framebuffers enable complex image-space effects.

---

### Forward References

> The post-processing architecture established in Chapters 40-41 serves as the foundation for additional effects:
> - **Depth of Field**: Uses G-buffer depth to blur based on focus distance
> - **Motion Blur**: Samples velocity buffer to streak along movement
> - **Screen-Space Reflections** (Chapter 45): Ray-marches against depth buffer for reflections

> **Color grading LUTs** can be extended with temporal interpolation for cinematic sequences. Imagine a character entering a dark cave—the LUT crossfades from warm (outdoor) to cool/desaturated (cave interior) over 2 seconds, creating a smooth mood transition.

> In **Chapter 42: Material System**, materials with emissive properties will automatically integrate with bloom, while color grading ensures all materials maintain the scene's visual identity.

---

## Best Practices

### Color Grading Configuration

1. **LDR space only**: Apply after tone mapping, never before.
2. **Artist workflow**: Export neutral LUT, grade in Photoshop/DaVinci, import result.
3. **Blend factor**: Allow artists to dial down LUT intensity (`u_LUTContribution < 1.0`).
4. **Multiple LUTs**: Load different LUTs for different scenes/moods, crossfade between them.
5. **Parametric as preview**: Use parametric controls for quick iteration, bake into LUT for final quality.

### General Post-Processing

1. **Order matters**: Bloom → Tone Map → Color Grade → Gamma is the standard pipeline.
2. **Toggle-able**: All effects should have an enable/disable flag for debugging.
3. **ImGui controls**: Expose all parameters for real-time tuning.
4. **Profiling**: Measure GPU time per effect to identify bottlenecks.

---

## Milestone

**Chapter 41 Complete - Color Grading**

At this point, your engine has **complete post-processing**:

**3D LUT color grading** for cinematic looks  
**Parametric color controls** (saturation, contrast, brightness)  
**Complete post-processing pipeline**: Scene → HDR → Bloom → Tone Map → Color Grade → sRGB  
**Modular architecture**: Each effect is independent and toggle-able  
**Artist-friendly workflow**: Use Photoshop/DaVinci for LUT creation  

Combined with Chapter 40's bloom implementation, you now have:

**Visual comparison**:
- **Before Chapters 40-41**: Functional PBR rendering but lacks cinematic polish
- **After Chapters 40-41**: Film-like quality with depth, glow, and mood-establishing color palettes

**Pipeline summary**:
```
Scene → HDR → Bloom Extract → Blur → Composite → Tone Map → Color Grade → Gamma → Screen
```

---

## What's Next

In **Chapter 42: Material System**, we'll build an abstraction layer for shaders and materials, preparing for component-based rendering with ECS. Materials with emissive properties will automatically integrate with the bloom system from Chapter 40, while maintaining the color grading from Chapter 41.

> **Next:** [Chapter 42: Material System](42_MaterialSystem.md)

> **Previous:** [Chapter 40: Bloom](40_Bloom.md)

> **Index:** [Table of Contents](INDEX.md)
