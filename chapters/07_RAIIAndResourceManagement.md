\newpage

# Chapter 7: RAII & Resource Management

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

This chapter covers the **C++ patterns** that make this possible. The next chapters apply these patterns to actual OpenGL objects.

---

## RAII: Resource Acquisition Is Initialization

**RAII** is a fundamental C++ pattern where:
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

### Benefits of RAII

| Benefit | Explanation |
|---------|-------------|
| **No memory leaks** | Destructor always runs when object goes out of scope |
| **Exception safe** | Even if an error occurs mid-function, cleanup happens |
| **Clear ownership** | The object *owns* the resource - no confusion |

### RAII in Action

```cpp
void RenderScene()
{
    VertexBuffer vbo(vertices, sizeof(vertices));  // Created
    
    // ... do rendering work
    
    if (error) return;  // vbo destructor runs here!
    
    // More work...
    
}  // vbo destructor runs here too!
```

No matter how we exit the function, the destructor runs. No `delete` or `glDeleteBuffers` needed.

---

## The Rule of 5

When a class manages a resource, you must handle 5 special member functions:

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

The default copy constructor just copies member variables. For resource handles, this is **disastrous**.

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

### Using Move Semantics

```cpp
VertexBuffer vb1(data, size);
VertexBuffer vb2 = vb1;              // ERROR: can't copy (deleted)
VertexBuffer vb3 = std::move(vb1);   // OK: vb1 gives ownership to vb3
// vb1.m_ID is now 0, vb3 owns the buffer
```

### Why Delete Copy?

| Approach | When to Use |
|----------|-------------|
| **Delete copy** | When copying doesn't make sense (OpenGL handles, file handles) |
| **Deep copy** | When you want independent copies (strings, vectors) |
| **Reference counting** | When sharing ownership (`shared_ptr`) |

For OpenGL resources, copying doesn't make sense - we'd need to create a *new* OpenGL object and copy all the GPU data. It's expensive and rarely needed.

---

## The Pattern Template

Every OpenGL wrapper in our engine follows this pattern:

```cpp
class VizEngine_API SomeOpenGLResource
{
public:
    // Constructor: Acquire
    SomeOpenGLResource(/* parameters */)
    {
        glGen*(1, &m_ID);
        // ... initialization
    }
    
    // Destructor: Release
    ~SomeOpenGLResource()
    {
        if (m_ID != 0)
            glDelete*(1, &m_ID);
    }
    
    // Rule of 5: Delete copy, allow move
    SomeOpenGLResource(const SomeOpenGLResource&) = delete;
    SomeOpenGLResource& operator=(const SomeOpenGLResource&) = delete;
    SomeOpenGLResource(SomeOpenGLResource&& other) noexcept;
    SomeOpenGLResource& operator=(SomeOpenGLResource&& other) noexcept;
    
    // Common operations
    void Bind() const;
    void Unbind() const;
    unsigned int GetID() const { return m_ID; }
    
private:
    unsigned int m_ID = 0;
};
```

---

## Key Takeaways

1. **RAII** - Constructor acquires, destructor releases
2. **Rule of 5** - Handle copy/move for resource-owning classes
3. **Delete copy** - Prevents double-free crashes
4. **Allow move** - Enables efficient ownership transfer
5. **Consistent pattern** - All wrappers follow the same structure

---

## Checkpoint

This chapter covered C++ resource management patterns:

**Concepts:**
| Pattern | Purpose |
|---------|---------|
| RAII | Automatic resource cleanup |
| Rule of 5 | Proper copy/move semantics |
| Move semantics | Transfer ownership efficiently |

**Checkpoint:** Understand these patterns before moving on. They're used in *every* OpenGL wrapper we create.

---

## Exercise

1. Create a simple `FileHandle` class that opens a file in constructor and closes in destructor
2. Implement Rule of 5 for `FileHandle` (delete copy, allow move)
3. Test what happens when you try to copy a `FileHandle`

---

> **Next:** [Chapter 8: Buffer Classes](08_BufferClasses.md) - Applying RAII to OpenGL buffers.

> **Previous:** [Chapter 6: OpenGL Fundamentals](06_OpenGLFundamentals.md)

