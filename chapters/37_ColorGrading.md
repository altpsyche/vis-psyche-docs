\newpage

# Chapter 37: Color Grading

Implement LUT-based color grading and parametric color controls to achieve cinematic color palettes and establish visual identity for your scenes.

---

## Introduction

In **Chapter 36**, we implemented the bloom effect, adding realistic glow to bright surfaces by operating in HDR space before tone mapping. Our post-processing pipeline now handles bloom extraction, Gaussian blur, and bloom compositing.

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

## Step 1: Extend Texture Class for 3D LUTs

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

---

## Step 2: Generate Neutral LUT

**2. Update** `VizEngine/src/VizEngine/OpenGL/Texture.cpp` to implement the static methods:

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

**In** `Sandbox/src/SandboxApp.cpp`, add private members (add to existing bloom members from Chapter 36):

```cpp
private:
    // ... existing members including bloom from Chapter 36 ...

    // Color Grading (Chapter 37)
    unsigned int m_ColorGradingLUT = 0;  // Raw OpenGL texture ID
    bool m_EnableColorGrading = false;
    float m_LUTContribution = 1.0f;
    float m_Saturation = 1.0f;
    float m_Contrast = 1.0f;
    float m_Brightness = 0.0f;
```

---

### OnCreate(): Initialize Color Grading LUT

Add to your existing `OnCreate()` method (after bloom initialization):

```cpp
void OnCreate() override
{
    // ... existing setup code including bloom (Chapter 36) ...

    // ====================================================================
    // Color Grading Setup (Chapter 37)
    // ====================================================================
    VP_INFO("Setting up color grading...");

    // Create Neutral Color Grading LUT (16x16x16)
    m_ColorGradingLUT = VizEngine::Texture::CreateNeutralLUT3D(16);

    if (m_ColorGradingLUT == 0)
    {
        VP_ERROR("Failed to create color grading LUT!");
    }

    VP_INFO("Color grading initialized successfully");
}
```

---

### OnRender(): Add Color Grading Uniforms

Update your existing tone mapping pass from Chapter 36 to include color grading:

```cpp
void OnRender() override
{
    // ... (existing HDR rendering and bloom from Chapter 36) ...

    // ====================================================================
    // Pass 3: Tone Mapping + Bloom + Color Grading to Screen
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

    // Bloom (from Chapter 36)
    m_ToneMappingShader->SetBool("u_EnableBloom", m_EnableBloom);
    m_ToneMappingShader->SetFloat("u_BloomIntensity", m_BloomIntensity);
    if (bloomTexture)
    {
        m_ToneMappingShader->SetInt("u_BloomTexture", 1);
        bloomTexture->Bind(1);
    }

    // Color grading (NEW - Chapter 37)
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

    m_FramebufferColor->Bind(0);

    // Render fullscreen quad
    m_FullscreenQuad->Render();

    // Re-enable depth test
    renderer.EnableDepthTest();
}
```

---

### OnImGuiRender(): Color Grading Controls

Update your existing Post-Processing panel from Chapter 36 to add color grading:

```cpp
void OnImGuiRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& uiManager = engine.GetUIManager();

    // ... existing panels ...

    // ====================================================================
    // Post-Processing Panel (Chapters 36 & 37)
    // ====================================================================
    uiManager.StartWindow("Post-Processing");

    // Bloom controls (from Chapter 36)
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

    // Color Grading controls (NEW - Chapter 37)
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

## Step 6: Resource Cleanup

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

> [!NOTE]
> The color grading LUT does not need recreation on window resize since it's resolution-independent (it's a lookup table, not a rendering target).

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

> In **Chapter 35**, we built the HDR pipeline with tone mapping. Color grading extends this by operating in the LDR space after tone mapping, where values are guaranteed to be in [0,1] range—perfect for perceptual color transformations.

> In **Chapter 36**, we implemented bloom which operates in HDR space (before tone mapping). Color grading complements bloom by working in LDR space (after tone mapping), demonstrating the complete post-processing pipeline architecture.

> The multi-pass rendering approach from **Chapter 27** (Framebuffers) underlies both bloom and color grading, showing how custom framebuffers enable complex image-space effects.

---

### Forward References

> The post-processing architecture established in Chapters 36-37 serves as the foundation for additional effects:
> - **Depth of Field** (Chapter 38): Uses G-buffer depth to blur based on focus distance
> - **Motion Blur** (Chapter 39): Samples velocity buffer to streak along movement
> - **Screen-Space Reflections** (Chapter 40): Ray-marches against depth buffer for reflections

> **Color grading LUTs** can be extended with temporal interpolation for cinematic sequences. Imagine a character entering a dark cave—the LUT crossfades from warm (outdoor) to cool/desaturated (cave interior) over 2 seconds, creating a smooth mood transition.

> In **Chapter 38: Material System**, materials with emissive properties will automatically integrate with bloom, while color grading ensures all materials maintain the scene's visual identity.

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

**Chapter 37 Complete - Color Grading**

At this point, your engine has **complete post-processing**:

**3D LUT color grading** for cinematic looks  
**Parametric color controls** (saturation, contrast, brightness)  
**Complete post-processing pipeline**: Scene → HDR → Bloom → Tone Map → Color Grade → sRGB  
**Modular architecture**: Each effect is independent and toggle-able  
**Artist-friendly workflow**: Use Photoshop/DaVinci for LUT creation  

Combined with Chapter 36's bloom implementation, you now have:

**Visual comparison**:
- **Before Chapters 36-37**: Functional PBR rendering but lacks cinematic polish
- **After Chapters 36-37**: Film-like quality with depth, glow, and mood-establishing color palettes

**Pipeline summary**:
```
Scene → HDR → Bloom Extract → Blur → Composite → Tone Map → Color Grade → Gamma → Screen
```

---

## What's Next

In **Chapter 38: Material System**, we'll build an abstraction layer for shaders and materials, preparing for component-based rendering with ECS. Materials with emissive properties will automatically integrate with the bloom system from Chapter 36, while maintaining the color grading from Chapter 37.

> **Next:** [Chapter 38: Material System](38_MaterialSystem.md)

> **Previous:** [Chapter 36: Bloom Post-Processing](36_BloomPostProcessing.md)

> **Index:** [Table of Contents](INDEX.md)
