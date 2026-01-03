\newpage

# Chapter 8: Buffer Classes

## Applying RAII to OpenGL Buffers

In the previous chapter, we learned RAII and the Rule of 5. Now we apply these patterns to create clean wrappers for OpenGL buffer objects.

> [!NOTE]
> **Prerequisites:** You should understand RAII and Rule of 5 from [Chapter 7](07_RAIIAndResourceManagement.md).

---

## VertexBuffer

Wraps `GL_ARRAY_BUFFER` - stores vertex data (positions, colors, UVs):

```cpp
// VizEngine/OpenGL/VertexBuffer.h

class VizEngine_API VertexBuffer
{
public:
    VertexBuffer(const void* vertices, unsigned int size)
    {
        glGenBuffers(1, &m_ID);
        glBindBuffer(GL_ARRAY_BUFFER, m_ID);
        glBufferData(GL_ARRAY_BUFFER, size, vertices, GL_STATIC_DRAW);
    }
    
    ~VertexBuffer()
    {
        if (m_ID != 0)
            glDeleteBuffers(1, &m_ID);
    }
    
    // Rule of 5
    VertexBuffer(const VertexBuffer&) = delete;
    VertexBuffer& operator=(const VertexBuffer&) = delete;
    VertexBuffer(VertexBuffer&& other) noexcept;
    VertexBuffer& operator=(VertexBuffer&& other) noexcept;
    
    void Bind() const { glBindBuffer(GL_ARRAY_BUFFER, m_ID); }
    void Unbind() const { glBindBuffer(GL_ARRAY_BUFFER, 0); }
    
    unsigned int GetID() const { return m_ID; }
    
private:
    unsigned int m_ID = 0;
};
```

### Usage

```cpp
float vertices[] = {
    // Position (x, y, z)    Color (r, g, b, a)
    -0.5f, -0.5f, 0.0f,      1.0f, 0.0f, 0.0f, 1.0f,
     0.5f, -0.5f, 0.0f,      0.0f, 1.0f, 0.0f, 1.0f,
     0.0f,  0.5f, 0.0f,      0.0f, 0.0f, 1.0f, 1.0f
};

VertexBuffer vbo(vertices, sizeof(vertices));
vbo.Bind();
// Draw...
// Destructor cleans up automatically
```

---

## IndexBuffer

Wraps `GL_ELEMENT_ARRAY_BUFFER` - stores indices for indexed drawing:

```cpp
// VizEngine/OpenGL/IndexBuffer.h

class VizEngine_API IndexBuffer
{
public:
    IndexBuffer(const unsigned int* indices, unsigned int count)
        : m_Count(count)
    {
        glGenBuffers(1, &m_ID);
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m_ID);
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, count * sizeof(unsigned int), 
                     indices, GL_STATIC_DRAW);
    }
    
    ~IndexBuffer()
    {
        if (m_ID != 0)
            glDeleteBuffers(1, &m_ID);
    }
    
    // Rule of 5 (same as VertexBuffer)
    
    void Bind() const { glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m_ID); }
    void Unbind() const { glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0); }
    
    unsigned int GetCount() const { return m_Count; }  // For glDrawElements
    
private:
    unsigned int m_ID = 0;
    unsigned int m_Count;
};
```

### Why Index Buffers?

Without indices (6 vertices for a quad):
```
Triangle 1: v0, v1, v2
Triangle 2: v0, v2, v3  ← v0 and v2 duplicated!
```

With indices (4 vertices + 6 indices):
```
Vertices: v0, v1, v2, v3
Indices: 0, 1, 2, 0, 2, 3  ← Reuse vertices!
```

**Result:** Less GPU memory, better cache performance.

---

## VertexBufferLayout

Describes how vertex data is organized in memory:

```cpp
// VizEngine/OpenGL/VertexBufferLayout.h

struct VertexBufferElement
{
    unsigned int type;       // GL_FLOAT, GL_UNSIGNED_INT, etc.
    unsigned int count;      // Number of components (3 for vec3, 4 for vec4)
    unsigned char normalised;
};

class VizEngine_API VertexBufferLayout
{
public:
    template<typename T>
    void Push(unsigned int count);  // Add an attribute
    
    const std::vector<VertexBufferElement>& GetElements() const 
    { return m_Elements; }
    
    unsigned int GetStride() const { return m_Stride; }
    
private:
    std::vector<VertexBufferElement> m_Elements;
    unsigned int m_Stride = 0;
};

// Template specializations
template<>
void VertexBufferLayout::Push<float>(unsigned int count)
{
    m_Elements.push_back({ GL_FLOAT, count, GL_FALSE });
    m_Stride += count * sizeof(float);
}

template<>
void VertexBufferLayout::Push<unsigned int>(unsigned int count)
{
    m_Elements.push_back({ GL_UNSIGNED_INT, count, GL_FALSE });
    m_Stride += count * sizeof(unsigned int);
}
```

### Usage

```cpp
VertexBufferLayout layout;
layout.Push<float>(4);  // Position: vec4
layout.Push<float>(3);  // Normal: vec3
layout.Push<float>(4);  // Color: vec4
layout.Push<float>(2);  // TexCoords: vec2

// Stride = (4 + 3 + 4 + 2) * sizeof(float) = 52 bytes per vertex
```

---

## VertexArray

The VAO stores the configuration of vertex attributes:

```cpp
// VizEngine/OpenGL/VertexArray.h

class VizEngine_API VertexArray
{
public:
    VertexArray()
    {
        glGenVertexArrays(1, &m_ID);
    }
    
    ~VertexArray()
    {
        if (m_ID != 0)
            glDeleteVertexArrays(1, &m_ID);
    }
    
    // Rule of 5 (same pattern)
    
    void LinkVertexBuffer(const VertexBuffer& vb, 
                          const VertexBufferLayout& layout) const
    {
        Bind();
        vb.Bind();
        
        const auto& elements = layout.GetElements();
        unsigned int offset = 0;
        
        for (unsigned int i = 0; i < elements.size(); i++)
        {
            const auto& element = elements[i];
            glEnableVertexAttribArray(i);
            glVertexAttribPointer(
                i,                          // Attribute index
                element.count,              // Number of components
                element.type,               // Data type
                element.normalised,         // Normalize?
                layout.GetStride(),         // Stride (bytes between vertices)
                (const void*)offset         // Offset to this attribute
            );
            offset += element.count * sizeof(float);
        }
    }
    
    void Bind() const { glBindVertexArray(m_ID); }
    void Unbind() const { glBindVertexArray(0); }
    
private:
    unsigned int m_ID = 0;
};
```

### Why Use VAO?

Without VAO, you'd need to call `glVertexAttribPointer` every frame.  
With VAO, you configure once, then just `Bind()` to restore the configuration.

```cpp
// Setup (once)
VertexArray vao;
VertexBuffer vbo(vertices, sizeof(vertices));
vao.LinkVertexBuffer(vbo, layout);

// Render loop (every frame)
vao.Bind();  // Restores all attribute configuration!
glDrawElements(...);
```

---

## Putting It All Together

```cpp
// Create geometry
float vertices[] = { /* position, color, uvs */ };
unsigned int indices[] = { 0, 1, 2, 0, 2, 3 };

// Create buffers
VertexArray vao;
VertexBuffer vbo(vertices, sizeof(vertices));
IndexBuffer ibo(indices, 6);

// Configure layout
VertexBufferLayout layout;
layout.Push<float>(4);  // Position
layout.Push<float>(4);  // Color
layout.Push<float>(2);  // TexCoords

vao.LinkVertexBuffer(vbo, layout);

// Render
vao.Bind();
glDrawElements(GL_TRIANGLES, ibo.GetCount(), GL_UNSIGNED_INT, nullptr);
```

---

## Key Takeaways

1. **VertexBuffer** - Stores vertex data on GPU
2. **IndexBuffer** - Enables vertex reuse
3. **VertexBufferLayout** - Describes attribute structure
4. **VertexArray** - Stores the complete configuration
5. **All use RAII** - Automatic cleanup, no leaks

---

## Checkpoint

**Files:**
| File | Purpose |
|------|---------|
| `VizEngine/OpenGL/VertexBuffer.h/.cpp` | VBO wrapper |
| `VizEngine/OpenGL/IndexBuffer.h/.cpp` | IBO wrapper |
| `VizEngine/OpenGL/VertexArray.h/.cpp` | VAO wrapper |
| `VizEngine/OpenGL/VertexBufferLayout.h` | Attribute layout |

**Checkpoint:** Create all buffer classes, render a colored triangle using the new wrappers.

---

## Exercise

1. Add a `SetData()` method to VertexBuffer for dynamic updates
2. Create an `InstanceBuffer` class for instanced rendering
3. Add validation that checks if VAO is bound before drawing

---

> **Next:** [Chapter 9: Shader & Renderer](09_ShaderAndRenderer.md) - Compiling shaders and managing draw calls.

> **Previous:** [Chapter 7: RAII & Resource Management](07_RAIIAndResourceManagement.md)

