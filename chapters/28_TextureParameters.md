\newpage

# Chapter 28: Advanced Texture Configuration

Extend our Texture class with sampling configuration for advanced rendering techniques.

---

## Introduction

In Chapter 11, we loaded textures from files and used default sampling parameters. For basic texturing, those defaults work well. However, advanced techniques like **shadow mapping**, **post-processing**, and **cubemaps** require precise control over how textures are sampled.

This chapter extends our `Texture` class with configuration methods and explains when to use each setting.

### Why This Matters

Without proper texture configuration:
- **Shadow maps** produce artifacts at scene edges
- **Post-processing** bleeds colors at screen edges
- **Tiled textures** show visible seams
- **Pixel art** appears blurry instead of crisp

| Technique | Required Configuration |
|-----------|------------------------|
| **Shadow Mapping** | `GL_CLAMP_TO_BORDER` + white border color |
| **Post-Processing** | `GL_CLAMP_TO_EDGE` to prevent bleeding |
| **Tiled Textures** | `GL_REPEAT` for seamless tiling |
| **Pixel Art** | `GL_NEAREST` for crisp pixels |

---

## Texture Sampling Theory

When a shader samples a texture using `texture(sampler, texCoord)`, OpenGL must answer two questions:

1. **Filtering**: If the texture is scaled, how do we compute the color?
2. **Wrapping**: If coordinates are outside [0, 1], what do we sample?

### Filtering Modes

Filtering determines how texture colors are computed when the texture is scaled (magnified or minified).

#### Magnification Filter

When a texture is **stretched larger** than its native resolution (camera close to surface):

| Filter | Result | Use Case |
|--------|--------|----------|
| `GL_NEAREST` | Pixelated, blocky | Pixel art, retro style |
| `GL_LINEAR` | Smooth, blurred | Most 3D rendering |

```
Original Texture    GL_NEAREST       GL_LINEAR
   ┌─┬─┐            ┌──┬──┐          ┌─────┐
   │A│B│   →        │AA│BB│          │ A→B │
   ├─┼─┤   →        ├──┼──┤          │  ↓  │
   │C│D│            │CC│DD│          │ C→D │
   └─┴─┘            └──┴──┘          └─────┘
```

`GL_NEAREST` samples the single closest texel—fast but blocky. `GL_LINEAR` interpolates the four surrounding texels—smoother but slightly blurrier.

#### Minification Filter

When a texture is **shrunk smaller** than its native resolution (camera far from surface):

| Filter | Mipmaps | Quality | Use Case |
|--------|---------|---------|----------|
| `GL_NEAREST` | No | Poor (shimmering) | Rarely used |
| `GL_LINEAR` | No | Fair | Simple cases |
| `GL_NEAREST_MIPMAP_NEAREST` | Yes | Good | Performance |
| `GL_LINEAR_MIPMAP_LINEAR` | Yes | Best (trilinear) | Default for 3D |

> [!TIP]
> **Trilinear filtering** (`GL_LINEAR_MIPMAP_LINEAR`) interpolates within mipmap levels AND between levels. This eliminates visible mipmap transitions ("mip banding").

Without mipmaps, distant textures "shimmer" as you move—pixels fight to represent too much detail. Mipmaps pre-compute downscaled versions, and trilinear filtering blends between them smoothly.

### Wrap Modes

Wrap mode controls what happens when texture coordinates fall outside the [0, 1] range.

#### Available Modes

| Mode | Behavior | Visual |
|------|----------|--------|
| `GL_REPEAT` | Tile infinitely | Pattern repeats |
| `GL_MIRRORED_REPEAT` | Tile with mirroring | Seamless for symmetric textures |
| `GL_CLAMP_TO_EDGE` | Stretch edge pixels | Prevents seams on edges |
| `GL_CLAMP_TO_BORDER` | Use border color | Returns specific color outside |

```
Texture: [ABCD]     Coordinates: -0.5 to 1.5

GL_REPEAT:          [...CDABCDAB...]
GL_MIRRORED_REPEAT: [...DCBAABCD...]
GL_CLAMP_TO_EDGE:   [AAAABCDDDDD...]
GL_CLAMP_TO_BORDER: [###ABCD####...]  (# = border color)
```

#### When to Use Each

| Use Case | Recommended Mode | Why |
|----------|------------------|-----|
| Tiled floor/wall textures | `GL_REPEAT` | Seamless repetition |
| Seamless environment maps | `GL_MIRRORED_REPEAT` | Avoids visible seams |
| UI elements, render targets | `GL_CLAMP_TO_EDGE` | Prevents edge bleeding |
| Shadow maps | `GL_CLAMP_TO_BORDER` | Areas outside light = not shadowed |

### Border Color

When using `GL_CLAMP_TO_BORDER`, you must specify what color to return for coordinates outside [0, 1].

**Shadow Map Example:**

For shadow maps, we want areas **outside the light's view** to be treated as "not in shadow". Since we compare fragment depth against shadow map depth:
- Shadow map stores depth values (0.0 = near, 1.0 = far)
- Border color of **white (1.0)** means "maximum depth"
- Fragment depth will always be less than 1.0, so comparison passes → not shadowed

Without this configuration, shadows would appear incorrectly at the edges of the light's frustum.

---

## Architecture Overview

We'll add three configuration methods to our existing `Texture` class:

```cpp
class Texture
{
public:
    // Existing constructors and methods...
    
    // NEW: Configuration methods
    void SetFilter(unsigned int minFilter, unsigned int magFilter);
    void SetWrap(unsigned int sWrap, unsigned int tWrap);
    void SetBorderColor(const float color[4]);
};
```

Each method binds the texture, sets the parameter via `glTexParameteri` or `glTexParameterfv`, then unbinds.

---

## Step 1: Add SetFilter Method

The filter method controls how textures appear when scaled.

**Update `VizEngine/OpenGL/Texture.h` - add public method:**

```cpp
/**
 * Set texture filtering modes.
 * @param minFilter Minification filter (GL_LINEAR, GL_LINEAR_MIPMAP_LINEAR, etc.)
 * @param magFilter Magnification filter (GL_LINEAR or GL_NEAREST)
 */
void SetFilter(unsigned int minFilter, unsigned int magFilter);
```

**Update `VizEngine/OpenGL/Texture.cpp`:**

```cpp
void Texture::SetFilter(unsigned int minFilter, unsigned int magFilter)
{
    glBindTexture(GL_TEXTURE_2D, m_texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, minFilter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, magFilter);
    glBindTexture(GL_TEXTURE_2D, 0);
}
```

> [!NOTE]
> We bind, set parameters, then unbind. This ensures we don't accidentally modify whatever texture was previously bound.

---

## Step 2: Add SetWrap Method

The wrap method controls edge behavior when sampling outside [0, 1].

**Update `VizEngine/OpenGL/Texture.h`:**

```cpp
/**
 * Set texture wrap modes for S and T coordinates.
 * @param sWrap Horizontal wrap mode (GL_REPEAT, GL_CLAMP_TO_EDGE, etc.)
 * @param tWrap Vertical wrap mode
 */
void SetWrap(unsigned int sWrap, unsigned int tWrap);
```

**Update `VizEngine/OpenGL/Texture.cpp`:**

```cpp
void Texture::SetWrap(unsigned int sWrap, unsigned int tWrap)
{
    glBindTexture(GL_TEXTURE_2D, m_texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, sWrap);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, tWrap);
    glBindTexture(GL_TEXTURE_2D, 0);
}
```

> [!NOTE]
> `S` and `T` are OpenGL's names for texture coordinates (equivalent to `U` and `V` in other APIs). `S` is horizontal, `T` is vertical.

---

## Step 3: Add SetBorderColor Method

The border color method specifies what color to return when using `GL_CLAMP_TO_BORDER`.

**Update `VizEngine/OpenGL/Texture.h`:**

```cpp
/**
 * Set border color for GL_CLAMP_TO_BORDER wrap mode.
 * @param color RGBA color array (4 floats)
 */
void SetBorderColor(const float color[4]);
```

**Update `VizEngine/OpenGL/Texture.cpp`:**

```cpp
void Texture::SetBorderColor(const float color[4])
{
    glBindTexture(GL_TEXTURE_2D, m_texture);
    glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, color);
    glBindTexture(GL_TEXTURE_2D, 0);
}
```

> [!IMPORTANT]
> Border color only has an effect when wrap mode is `GL_CLAMP_TO_BORDER`. Setting it with other wrap modes does nothing.

---

## Step 4: Practical Examples

Let's see how these methods are used in practice.

### Example 1: Shadow Map Configuration

```cpp
// Create depth texture for shadow map
auto shadowMap = std::make_shared<Texture>(2048, 2048, 
    GL_DEPTH_COMPONENT24, GL_DEPTH_COMPONENT, GL_FLOAT);

// Configure for shadow sampling
shadowMap->SetFilter(GL_LINEAR, GL_LINEAR);
shadowMap->SetWrap(GL_CLAMP_TO_BORDER, GL_CLAMP_TO_BORDER);
float borderWhite[] = { 1.0f, 1.0f, 1.0f, 1.0f };
shadowMap->SetBorderColor(borderWhite);
```

**Why these settings?**
- `GL_LINEAR` provides smooth sampling when comparing depths
- `GL_CLAMP_TO_BORDER` returns border color outside shadow map bounds
- White border (1.0 depth) means "no shadow" for areas outside light's view

### Example 2: Render Target for Post-Processing

```cpp
auto colorBuffer = std::make_shared<Texture>(width, height,
    GL_RGBA16F, GL_RGBA, GL_FLOAT);

// Prevent edge bleeding during blur/bloom
colorBuffer->SetWrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE);
```

### Example 3: Tiled Floor Texture

```cpp
auto floorTile = std::make_shared<Texture>("floor.png");

// Repeat seamlessly across large surfaces
floorTile->SetWrap(GL_REPEAT, GL_REPEAT);
floorTile->SetFilter(GL_LINEAR_MIPMAP_LINEAR, GL_LINEAR);
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Texture edges visible on tiled floors | Wrong wrap mode | Use `GL_REPEAT` |
| Shadow artifacts at scene edges | Missing border config | Use `GL_CLAMP_TO_BORDER` + white |
| Blurry textures up close | Wrong mag filter | Use `GL_LINEAR` (or `NEAREST` for pixel art) |
| Shimmering in distance | No mipmaps | Use `GL_LINEAR_MIPMAP_LINEAR` |
| Visible mip transitions | Only nearest mipmap | Switch to trilinear filtering |

---

## Best Practices

1. **Always use mipmaps** for 3D scene textures (generate with `glGenerateMipmap`)
2. **Use `GL_CLAMP_TO_EDGE`** for render targets and UI to prevent bleeding
3. **Use `GL_CLAMP_TO_BORDER`** for shadow maps with appropriate border color
4. **Default to trilinear filtering** (`GL_LINEAR_MIPMAP_LINEAR`) for quality
5. **Consider anisotropic filtering** for surfaces viewed at angles (not covered here)

---

## Milestone

**Chapter 28 Complete - Advanced Texture Configuration**

You have:
- Implemented `SetFilter()`, `SetWrap()`, and `SetBorderColor()` methods
- Understood when to use each filtering and wrap mode
- Learned practical applications for shadow maps and render targets

Your `Texture` class now supports the configuration needed for advanced rendering techniques.

---

## What's Next

In **Chapter 29: Shadow Mapping**, we'll use these texture configuration methods to create realistic shadows using depth maps and two-pass rendering.

> **Next:** [Chapter 29: Shadow Mapping](29_ShadowMapping.md)

> **Previous:** [Chapter 27: Framebuffers](27_Framebuffers.md)
