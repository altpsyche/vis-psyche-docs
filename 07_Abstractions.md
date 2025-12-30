# Chapter 7: OpenGL Abstractions

## Why Abstract OpenGL?

Raw OpenGL code is verbose and error-prone:

```cpp
// Raw OpenGL - 15+ lines just to create a buffer
unsigned int VBO;
glGenBuffers(1, &VBO);
glBindBuffer(GL_ARRAY_BUFFER, VBO);
glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
// ... later
glDeleteBuffers(1, &VBO);  // Easy to forget!
```

Our abstraction:

```cpp
// Clean C++ - RAII handles everything
VertexBuffer vbo(data, size);  // Created and uploaded
// ... use it
// Destructor automatically cleans up
```

---

## RAII: Resource Acquisition Is Initialization

**RAII** is a C++ pattern where:
- **Constructor** acquires the resource
- **Destructor** releases the resource

```cpp
class VertexBuffer
{
public:
    VertexBuffer(const void* data, unsigned int size)
    {
        glGenBuffers(1, &m_ID);        // Acquire
        glBindBuffer(GL_ARRAY_BUFFER, m_ID);
        glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
    }
    
    ~VertexBuffer()
    {
        if (m_ID != 0)
            glDeleteBuffers(1, &m_ID);  // Release
    }
    
private:
    unsigned int m_ID;
};
```

Benefits:
- **No memory leaks** - Destructor always runs
- **Exception safe** - Even if an error occurs
- **Clear ownership** - Object owns the resource

---

## The Rule of 5

When a class manages a resource, you need to handle:
1. **Destructor** - Cleanup
2. **Copy Constructor** - What if copied?
3. **Copy Assignment** - What if assigned?
4. **Move Constructor** - Efficient transfer
5. **Move Assignment** - Efficient transfer

### The Problem with Copying

```cpp
VertexBuffer vb1(data, size);   // Creates OpenGL buffer ID=1
VertexBuffer vb2 = vb1;         // DEFAULT: shallow copy, ID=1

// Now both vb1 and vb2 have ID=1
// When vb2 destructor runs: glDeleteBuffers(ID=1)
// When vb1 destructor runs: glDeleteBuffers(ID=1) ← CRASH! Already deleted!
```

### Our Solution: Delete Copy, Allow Move

```cpp
class VertexBuffer
{
public:
    // Delete copying (prevent the problem)
    VertexBuffer(const VertexBuffer&) = delete;
    VertexBuffer& operator=(const VertexBuffer&) = delete;
    
    // Allow moving (transfer ownership)
    VertexBuffer(VertexBuffer&& other) noexcept
        : m_ID(other.m_ID)
    {
        other.m_ID = 0;  // Source no longer owns it
    }
    
    VertexBuffer& operator=(VertexBuffer&& other) noexcept
    {
        if (this != &other)
        {
            if (m_ID != 0)
                glDeleteBuffers(1, &m_ID);  // Clean up our old resource
            m_ID = other.m_ID;
            other.m_ID = 0;
        }
        return *this;
    }
};
```

Now:
```cpp
VertexBuffer vb1(data, size);
VertexBuffer vb2 = vb1;              // ERROR: can't copy
VertexBuffer vb3 = std::move(vb1);   // OK: vb1 gives ownership to vb3
```

---

## Our OpenGL Wrappers

### VertexBuffer

```cpp
// VizEngine/OpenGL/VertexBuffer.h

class VizEngine_API VertexBuffer
{
public:
    VertexBuffer(const void* vertices, unsigned int size);
    ~VertexBuffer();
    
    // Rule of 5
    VertexBuffer(const VertexBuffer&) = delete;
    VertexBuffer& operator=(const VertexBuffer&) = delete;
    VertexBuffer(VertexBuffer&& other) noexcept;
    VertexBuffer& operator=(VertexBuffer&& other) noexcept;
    
    void Bind() const;    // glBindBuffer(GL_ARRAY_BUFFER, m_ID)
    void Unbind() const;  // glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    unsigned int GetID() const { return m_ID; }
    
private:
    unsigned int m_ID;
};
```

### IndexBuffer

Same pattern, but for `GL_ELEMENT_ARRAY_BUFFER`:

```cpp
class VizEngine_API IndexBuffer
{
public:
    IndexBuffer(const unsigned int* indices, unsigned int count);
    // ... same pattern
    
    unsigned int GetCount() const { return m_Count; }  // For glDrawElements
    
private:
    unsigned int m_ID;
    unsigned int m_Count;
};
```

### VertexArray

Stores the vertex attribute configuration:

```cpp
class VizEngine_API VertexArray
{
public:
    VertexArray();
    ~VertexArray();
    // ... Rule of 5
    
    void LinkVertexBuffer(const VertexBuffer& vb, const VertexBufferLayout& layout) const;
    void Bind() const;
    void Unbind() const;
    
private:
    unsigned int m_ID;
};
```

### VertexBufferLayout

Describes how vertex data is organized:

```cpp
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
    
    const std::vector<VertexBufferElement>& GetElements() const;
    unsigned int GetStride() const;  // Total bytes per vertex
    
private:
    std::vector<VertexBufferElement> m_Elements;
    unsigned int m_Stride = 0;
};
```

Usage:
```cpp
VertexBufferLayout layout;
layout.Push<float>(4);  // Position: vec4
layout.Push<float>(4);  // Color: vec4
layout.Push<float>(2);  // TexCoord: vec2
// Stride = 10 * sizeof(float) = 40 bytes
```

---

## The Shader Class

### Combined Shader Files

We use a single file with both shaders:

```glsl
#shader vertex
#version 460 core
// ... vertex shader code

#shader fragment
#version 460 core
// ... fragment shader code
```

### Parsing

```cpp
ShaderPrograms Shader::ShaderParser(const std::string& filepath)
{
    std::ifstream file(filepath);
    std::stringstream ss[2];  // [0] = vertex, [1] = fragment
    ShaderType type = ShaderType::NONE;
    
    std::string line;
    while (getline(file, line))
    {
        if (line.find("#shader") != std::string::npos)
        {
            if (line.find("vertex") != std::string::npos)
                type = ShaderType::VERTEX;
            else if (line.find("fragment") != std::string::npos)
                type = ShaderType::FRAGMENT;
        }
        else
        {
            ss[(int)type] << line << '\n';
        }
    }
    return { ss[0].str(), ss[1].str() };
}
```

### Uniform Caching

Getting uniform locations is expensive. We cache them:

```cpp
class Shader
{
private:
    std::unordered_map<std::string, int> m_LocationCache;
    
    int GetUniformLocation(const std::string& name)
    {
        // Check cache first
        if (m_LocationCache.find(name) != m_LocationCache.end())
            return m_LocationCache[name];
        
        // Not cached, query OpenGL
        int location = glGetUniformLocation(m_RendererID, name.c_str());
        m_LocationCache[name] = location;
        return location;
    }
};
```

---

## The Texture Class

For the complete Texture implementation details, see [Chapter 8: Textures](08_Textures.md).

```cpp
class VizEngine_API Texture
{
public:
    Texture(const std::string& path)
    {
        // Load image using stb_image
        stbi_set_flip_vertically_on_load(1);  // OpenGL expects bottom-left origin
        m_LocalBuffer = stbi_load(path.c_str(), &m_Width, &m_Height, &m_BPP, 4);
        
        if (!m_LocalBuffer)
        {
            std::cerr << "Failed to load texture: " << path << std::endl;
            return;
        }
        
        // Create OpenGL texture
        glGenTextures(1, &m_RendererID);
        glBindTexture(GL_TEXTURE_2D, m_RendererID);
        
        // Filtering
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        
        // Wrapping
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
        
        // Upload to GPU
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, m_Width, m_Height, 
                     0, GL_RGBA, GL_UNSIGNED_BYTE, m_LocalBuffer);
        
        // Free CPU memory (data is now on GPU)
        stbi_image_free(m_LocalBuffer);
        m_LocalBuffer = nullptr;
    }
    
    void Bind(unsigned int slot = 0) const
    {
        glActiveTexture(GL_TEXTURE0 + slot);  // Select texture unit
        glBindTexture(GL_TEXTURE_2D, m_RendererID);
    }
};
```

---

## The Renderer Class

High-level rendering operations:

```cpp
class VizEngine_API Renderer
{
public:
    void Clear(float clearColor[4])
    {
        glClearColor(clearColor[0], clearColor[1], clearColor[2], clearColor[3]);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    }
    
    void Draw(const VertexArray& va, const IndexBuffer& ib, const Shader& shader) const
    {
        shader.Bind();
        va.Bind();
        ib.Bind();
        glDrawElements(GL_TRIANGLES, ib.GetCount(), GL_UNSIGNED_INT, nullptr);
    }
};
```

---

## Using the Abstractions

Before:
```cpp
// 50+ lines of raw OpenGL...
unsigned int VAO, VBO, IBO;
glGenVertexArrays(1, &VAO);
glBindVertexArray(VAO);
glGenBuffers(1, &VBO);
// ... etc
```

After:
```cpp
VertexArray vao;
VertexBuffer vbo(vertices, sizeof(vertices));

VertexBufferLayout layout;
layout.Push<float>(4);  // Position
layout.Push<float>(4);  // Color
layout.Push<float>(2);  // TexCoord

vao.LinkVertexBuffer(vbo, layout);
IndexBuffer ibo(indices, indexCount);

Shader shader("shaders/lit.shader");
Texture texture("textures/uvchecker.png");

// Render
renderer.Draw(vao, ibo, shader);
```

---

## Key Takeaways

1. **RAII manages resources** - Constructor acquires, destructor releases
2. **Rule of 5** - Delete copy, implement move for resource-owning classes
3. **Abstractions hide complexity** - Clean API, OpenGL internals hidden
4. **Cache expensive operations** - Uniform locations are cached
5. **Consistent patterns** - All wrappers follow the same structure

---

## Exercise

1. Add a `SetVec3` method to the Shader class
2. Create a wrapper for OpenGL Framebuffers
3. Add mipmap support to the Texture class

---

> **Next:** [Chapter 8: Textures](08_Textures.md) - Loading and using images on the GPU.

> **Reference:** For the full class diagram showing all abstractions, see [Appendix A: Code Reference](A_Reference.md#class-diagram).


