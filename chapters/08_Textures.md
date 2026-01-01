\newpage

# Chapter 8: Textures

A 3D model without textures is like a coloring book without colors. Textures are images wrapped onto geometry, adding detail that would be impossible with just vertices.

## What is a Texture?

A texture is a 2D image that gets mapped onto 3D geometry. Each pixel in the texture is called a **texel** (texture element).

![Texture Mapping](images/08-texture-mapping.png)

---

## Texture Coordinates (UV)

Every vertex has **texture coordinates** (often called **UV coordinates**) that tell OpenGL which part of the texture maps to that vertex.

### The UV Space

![UV Coordinates](images/08-uv-coordinates.png)

- **U** = horizontal (0.0 = left, 1.0 = right)
- **V** = vertical (0.0 = bottom, 1.0 = top)

### Example: Triangle

```cpp
// Each vertex has: position + color + texcoord
float vertices[] = {
    // Position           Color              TexCoords
    -0.5f, -0.5f, 0.0f,   1,1,1,1,          0.0f, 0.0f,  // bottom-left
     0.5f, -0.5f, 0.0f,   1,1,1,1,          1.0f, 0.0f,  // bottom-right
     0.0f,  0.5f, 0.0f,   1,1,1,1,          0.5f, 1.0f,  // top-center
};
```

The texture will be stretched to fit the triangle shape.

---

## Loading Images with stb_image

OpenGL doesn't load images - it just accepts raw pixel data. We use **stb_image** to decode image files.

### The Loading Process

```cpp
int width, height, channels;
unsigned char* data = stbi_load("texture.png", &width, &height, &channels, 4);
```

Parameters:
- `path` - File to load
- `width`, `height` - Output: image dimensions
- `channels` - Output: color channels in file (3=RGB, 4=RGBA)
- `4` - Request 4 channels (we always want RGBA)

### Flipping for OpenGL

Most image formats store pixels top-to-bottom, but OpenGL expects bottom-to-top:

```cpp
stbi_set_flip_vertically_on_load(1);  // Call BEFORE loading
```

Without this, textures appear upside-down!

---

## Creating an OpenGL Texture

Once we have pixel data, we upload it to the GPU:

```cpp
// Generate texture ID
unsigned int textureID;
glGenTextures(1, &textureID);

// Bind texture (make it active)
glBindTexture(GL_TEXTURE_2D, textureID);

// Set texture parameters
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);

// Upload pixel data
glTexImage2D(
    GL_TEXTURE_2D,      // Target
    0,                  // Mipmap level
    GL_RGBA8,           // Internal format (GPU storage)
    width, height,      // Dimensions
    0,                  // Border (must be 0)
    GL_RGBA,            // Format of input data
    GL_UNSIGNED_BYTE,   // Type of input data
    data                // Pixel data pointer
);

// Free CPU-side data (GPU has it now)
stbi_image_free(data);
```

---

## Texture Parameters

### Filtering: What Happens at Different Sizes

When a texture is bigger or smaller than the area it's drawn to, OpenGL must **filter** it.

#### Minification (Texture → Smaller)

```cpp
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
```

| Filter | Result | Performance |
|--------|--------|-------------|
| `GL_NEAREST` | Pixelated, blocky | Fastest |
| `GL_LINEAR` | Smooth, blurry | Fast |
| `GL_LINEAR_MIPMAP_LINEAR` | Smooth, uses mipmaps | Best quality |

#### Magnification (Texture → Larger)

```cpp
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
```

| Filter | Result |
|--------|--------|
| `GL_NEAREST` | Pixelated (Minecraft-style) |
| `GL_LINEAR` | Smooth |

### Wrapping: What Happens Outside 0-1

UV coordinates can go outside 0-1 range. Wrapping controls what happens:

```cpp
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);  // U axis
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);  // V axis
```

| Mode | Effect | Visual |
|------|--------|--------|
| `GL_REPEAT` | Tile the texture | `ABCABC` |
| `GL_MIRRORED_REPEAT` | Tile, flipping each time | `ABCCBA` |
| `GL_CLAMP_TO_EDGE` | Stretch edge pixels | `ABCCC` |
| `GL_CLAMP_TO_BORDER` | Use border color | `ABC...` |

---

## Our Texture Class

We wrap all this in a clean RAII class:

```cpp
class Texture
{
public:
    Texture(const std::string& path);
    ~Texture();

    // Prevent copying (GPU resource)
    Texture(const Texture&) = delete;
    Texture& operator=(const Texture&) = delete;

    // Allow moving
    Texture(Texture&& other) noexcept;
    Texture& operator=(Texture&& other) noexcept;

    void Bind(unsigned int slot = 0) const;
    void Unbind() const;

    int GetWidth() const { return m_Width; }
    int GetHeight() const { return m_Height; }

private:
    unsigned int m_RendererID;
    std::string m_FilePath;
    int m_Width, m_Height, m_BPP;
};
```

### Constructor: Load and Upload

```cpp
Texture::Texture(const std::string& path)
    : m_RendererID(0), m_FilePath(path), 
      m_Width(0), m_Height(0), m_BPP(0)
{
    stbi_set_flip_vertically_on_load(1);
    unsigned char* data = stbi_load(path.c_str(), &m_Width, &m_Height, &m_BPP, 4);

    if (!data)
    {
        std::cerr << "Failed to load texture: " << path << std::endl;
        return;
    }

    glGenTextures(1, &m_RendererID);
    glBindTexture(GL_TEXTURE_2D, m_RendererID);

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, m_Width, m_Height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, data);
    glBindTexture(GL_TEXTURE_2D, 0);

    stbi_image_free(data);
}
```

### Destructor: Cleanup

```cpp
Texture::~Texture()
{
    if (m_RendererID != 0)
    {
        glDeleteTextures(1, &m_RendererID);
    }
}
```

---

## Texture Slots (Units)

GPUs have multiple **texture slots** (units). You can have many textures bound at once:

```cpp
// Slot 0: diffuse texture
texture1.Bind(0);

// Slot 1: normal map
texture2.Bind(1);

// Slot 2: specular map
texture3.Bind(2);
```

### How Binding Works

```cpp
void Texture::Bind(unsigned int slot) const
{
    glActiveTexture(GL_TEXTURE0 + slot);  // Select slot
    glBindTexture(GL_TEXTURE_2D, m_RendererID);  // Bind to slot
}
```

- `glActiveTexture(GL_TEXTURE0 + slot)` - Select which slot to use
- `glBindTexture(...)` - Bind texture to the active slot

Most GPUs have at least 16 texture slots (0-15).

---

## Using Textures in Shaders

### Sampler Uniform

In your fragment shader:

```glsl
uniform sampler2D u_MainTex;  // Texture sampler

in vec2 v_TexCoords;  // From vertex shader

void main()
{
    vec4 texColor = texture(u_MainTex, v_TexCoords);
    FragColor = texColor;
}
```

### Setting the Sampler

The sampler uniform takes an **integer** - the texture slot number:

```cpp
Texture tex("brick.png");
tex.Bind(0);  // Bind to slot 0

shader.Bind();
shader.SetInt("u_MainTex", 0);  // Tell shader: u_MainTex is in slot 0
```

---

## Move Semantics

Our Texture class supports moving (but not copying):

```cpp
// Move constructor
Texture::Texture(Texture&& other) noexcept
    : m_RendererID(other.m_RendererID),
      m_FilePath(std::move(other.m_FilePath)),
      m_Width(other.m_Width),
      m_Height(other.m_Height),
      m_BPP(other.m_BPP)
{
    other.m_RendererID = 0;  // Prevent double-delete
}
```

Why no copying?
- GPU resources shouldn't be duplicated accidentally
- Copying would require `glCopyTexSubImage2D` - expensive!
- Move transfers ownership cleanly

---

## Common Issues

### Black Texture

**Symptom:** Object renders black instead of textured.

**Causes:**
1. Texture didn't load (check path)
2. Forgot to bind texture before drawing
3. Shader sampler not set correctly
4. UV coordinates wrong (all 0,0)

### Upside-Down Texture

**Cause:** Forgot `stbi_set_flip_vertically_on_load(1)`.

### Texture Bleeding

**Symptom:** Colors from adjacent texels appear at edges.

**Fix:** Use `GL_CLAMP_TO_EDGE` or add padding in texture atlas.

### Wrong Colors

**Symptom:** Colors are swapped (red/blue reversed).

**Cause:** Format mismatch. If image is BGR, use `GL_BGR` not `GL_RGB`.

---

## Mipmaps

**Mipmaps** are pre-computed smaller versions of a texture:

```
256×256 → 128×128 → 64×64 → 32×32 → 16×16 → 8×8 → 4×4 → 2×2 → 1×1
```

When an object is far away, the GPU uses a smaller mipmap (faster, less aliasing).

### Generating Mipmaps

```cpp
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data);
glGenerateMipmap(GL_TEXTURE_2D);

// Use mipmapped filtering
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
```

---

## Complete Usage Example

```cpp
// Load texture
Texture brickTexture("src/resources/textures/brick.png");

// In render loop:
brickTexture.Bind(0);

shader.Bind();
shader.SetInt("u_MainTex", 0);
shader.SetMat4("u_MVP", mvp);

mesh.Bind();
glDrawElements(GL_TRIANGLES, mesh.GetIndexCount(), GL_UNSIGNED_INT, nullptr);
```

---

## Key Takeaways

1. **UV coordinates map textures to vertices** - Range 0-1, origin at bottom-left
2. **stb_image loads files** - Returns raw pixel data
3. **Flip for OpenGL** - Call `stbi_set_flip_vertically_on_load(1)`
4. **Texture parameters control behavior** - Filtering and wrapping
5. **Texture slots allow multiple textures** - Bind to different slots
6. **Samplers are integers** - They hold the slot number
7. **RAII for cleanup** - Destructor calls `glDeleteTextures`
8. **Mipmaps improve quality and performance** - Use for textures viewed at varying distances

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Texture appears upside-down | stb_image Y origin | `stbi_set_flip_vertically_on_load(1)` |
| Texture is black | Wrong texture slot | Verify `shader.SetInt("u_Texture", slot)` |
| Texture is white | Failed to load file | Check file path and console for errors |
| Pixelated when close | Wrong min filter | Use `GL_LINEAR` or `GL_LINEAR_MIPMAP_LINEAR` |
| Blurry when far | No mipmaps | Call `glGenerateMipmap()` |

---

## Checkpoint

This chapter covered textures:

**Key Concepts:**
- **UV coords** — Map 2D texture to 3D vertices (0,0 = bottom-left)
- **stb_image** — Loads PNG, JPG, BMP to raw pixel data
- **Texture slots** — Multiple textures bound simultaneously
- **Filtering** — `NEAREST` (pixelated) vs `LINEAR` (smooth)
- **Mipmaps** — Pre-computed smaller versions

**Files:**
- `VizEngine/OpenGL/Texture.h/cpp`

✓ **Checkpoint:** Create `Texture.h/.cpp`, add stb_image to vendor, load a texture, and verify it displays on geometry.

---

## Exercise

1. Load a different texture format (JPG instead of PNG)
2. Try `GL_NEAREST` filtering for a pixelated look
3. Use `GL_MIRRORED_REPEAT` wrapping with UV > 1.0
4. Add a second texture and blend them in the shader
5. Implement mipmap generation in the Texture class

---

> **Next:** [Chapter 9: Engine Architecture](09_EngineArchitecture.md) - How all the pieces fit together.



