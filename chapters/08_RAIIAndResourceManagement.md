\newpage

# Chapter 8: RAII & Resource Management

OpenGL resources (buffers, shaders, textures) must be explicitly deleted. C++ gives us tools to automate this and prevent leaks.

> [!NOTE]
> This chapter explains C++ patterns. No new files yet—we'll apply these patterns in Chapters 9-12.

---

## The Problem

Raw OpenGL code is error-prone:

```cpp
unsigned int VBO;
glGenBuffers(1, &VBO);
glBindBuffer(GL_ARRAY_BUFFER, VBO);
glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);

// ... later, maybe forgot to:
glDeleteBuffers(1, &VBO);  // Memory leak!
```

What can go wrong:
- **Forget to delete** → GPU memory leak
- **Delete twice** → Crash or corruption
- **Exception thrown** → Cleanup code never runs

---

## RAII: Resource Acquisition Is Initialization

**RAII** ties resource lifetime to object lifetime:

- **Constructor** → Acquire resource
- **Destructor** → Release resource

```cpp
class VertexBuffer
{
public:
    VertexBuffer(const float* data, size_t size)
    {
        glGenBuffers(1, &m_ID);
        glBindBuffer(GL_ARRAY_BUFFER, m_ID);
        glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
    }
    
    ~VertexBuffer()
    {
        glDeleteBuffers(1, &m_ID);  // Always cleaned up!
    }
    
private:
    unsigned int m_ID = 0;
};
```

When the object goes out of scope, the destructor runs automatically—even if an exception is thrown.

---

## The Rule of 5

When a class manages a resource, you must handle these five special functions:

| Function | Purpose |
|----------|---------|
| **Destructor** | Release resource |
| **Copy Constructor** | Create copy of resource |
| **Copy Assignment** | Replace with copy |
| **Move Constructor** | Transfer ownership |
| **Move Assignment** | Replace via transfer |

### The Problem with Copies

```cpp
VertexBuffer a(data, size);  // Creates OpenGL buffer
VertexBuffer b = a;          // Default: copies m_ID

// Now both a and b have the same ID
// When b is destroyed → glDeleteBuffers(ID)
// When a is destroyed → glDeleteBuffers(ID) again!  // Crash!
```

### Solution: Delete Copy, Allow Move

For OpenGL wrappers, we:
- **Delete copy operations** — Can't duplicate GPU resources cheaply
- **Implement move operations** — Transfer ownership instead

```cpp
class VertexBuffer
{
public:
    // Constructor
    VertexBuffer(const float* data, size_t size)
    {
        glGenBuffers(1, &m_ID);
        glBindBuffer(GL_ARRAY_BUFFER, m_ID);
        glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
    }
    
    // Destructor
    ~VertexBuffer()
    {
        if (m_ID != 0)
            glDeleteBuffers(1, &m_ID);
    }
    
    // Delete copy operations
    VertexBuffer(const VertexBuffer&) = delete;
    VertexBuffer& operator=(const VertexBuffer&) = delete;
    
    // Move constructor
    VertexBuffer(VertexBuffer&& other) noexcept
        : m_ID(other.m_ID)
    {
        other.m_ID = 0;  // Prevent other's destructor from deleting
    }
    
    // Move assignment
    VertexBuffer& operator=(VertexBuffer&& other) noexcept
    {
        if (this != &other)
        {
            // Release our current resource
            if (m_ID != 0)
                glDeleteBuffers(1, &m_ID);
            
            // Take ownership
            m_ID = other.m_ID;
            other.m_ID = 0;
        }
        return *this;
    }
    
private:
    unsigned int m_ID = 0;
};
```

---

## Move Semantics Explained

**Move** transfers ownership instead of copying:

```cpp
VertexBuffer a(data, size);  // a owns buffer ID 1
VertexBuffer b = std::move(a);  // b takes ID 1, a becomes 0

// a.m_ID is now 0 (no resource)
// b.m_ID is now 1 (owns the resource)
// When b is destroyed → glDeleteBuffers(1) runs once
```

### When Moves Happen

```cpp
// 1. std::move()
VertexBuffer b = std::move(a);

// 2. Returning from functions (often optimized away)
VertexBuffer CreateBuffer() {
    VertexBuffer vb(data, size);
    return vb;  // Move (or copy elision)
}

// 3. Passing temporaries
void UseBuffer(VertexBuffer buf);
UseBuffer(VertexBuffer(data, size));  // Move from temporary
```

---

## The Complete Pattern

Every OpenGL wrapper class follows this pattern:

```cpp
class OpenGLResource
{
public:
    // Constructor: Acquire
    OpenGLResource(/* params */)
    {
        glGen*(1, &m_ID);
        // Configure...
    }
    
    // Destructor: Release
    ~OpenGLResource()
    {
        if (m_ID != 0)
            glDelete*(1, &m_ID);
    }
    
    // No copying
    OpenGLResource(const OpenGLResource&) = delete;
    OpenGLResource& operator=(const OpenGLResource&) = delete;
    
    // Allow moving
    OpenGLResource(OpenGLResource&& other) noexcept
        : m_ID(other.m_ID)
    {
        other.m_ID = 0;
    }
    
    OpenGLResource& operator=(OpenGLResource&& other) noexcept
    {
        if (this != &other)
        {
            if (m_ID != 0)
                glDelete*(1, &m_ID);
            m_ID = other.m_ID;
            other.m_ID = 0;
        }
        return *this;
    }
    
    // Usage
    void Bind() const { glBind*(m_ID); }
    void Unbind() const { glBind*(0); }
    unsigned int GetID() const { return m_ID; }
    
private:
    unsigned int m_ID = 0;
};
```

---

## Why noexcept?

Move operations should be `noexcept`:

```cpp
VertexBuffer(VertexBuffer&& other) noexcept
```

Why:
- Standard containers (like `std::vector`) use `noexcept` moves for optimization
- If a move can throw, containers fall back to slower copying
- Our moves just copy integers—they can't fail

---

## Using the Classes

With RAII, resource management is automatic:

```cpp
void RenderScene()
{
    VertexBuffer vbo(vertices, sizeof(vertices));
    IndexBuffer ibo(indices, sizeof(indices));
    
    // Use buffers...
    vbo.Bind();
    ibo.Bind();
    glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);
    
}  // vbo and ibo automatically deleted here
```

Even if an exception is thrown, destructors run and resources are freed.

---

## Summary

| Concept | Rule |
|---------|------|
| **RAII** | Acquire in constructor, release in destructor |
| **Rule of 5** | Define all 5 special functions or delete them |
| **No Copy** | Delete copy constructor and copy assignment |
| **Allow Move** | Implement move constructor and move assignment |
| **Zero Check** | Check `m_ID != 0` before deletion |
| **Null After Move** | Set source's ID to 0 after moving |
| **noexcept** | Mark moves as noexcept for container compatibility |

---

## What's Next

In **Chapter 9**, we'll apply these patterns to create `VertexBuffer`, `IndexBuffer`, and `VertexArray` classes.

> **Next:** [Chapter 9: Buffer Classes](09_BufferClasses.md)

> **Previous:** [Chapter 7: OpenGL Fundamentals](07_OpenGLFundamentals.md)
