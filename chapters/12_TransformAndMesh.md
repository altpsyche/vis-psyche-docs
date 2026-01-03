\newpage

# Chapter 12: Transform & Mesh

## Building Blocks for 3D Objects

With our OpenGL abstractions in place (buffers, shaders, textures), we need higher-level concepts for 3D objects. This chapter introduces:

- **Transform** - Position, rotation, scale in 3D space
- **Vertex** - Data structure for mesh vertices  
- **Mesh** - Geometry container with factory methods

---

## The Transform Struct

Represents an object's position, rotation, and scale:

```cpp
// VizEngine/Core/Transform.h

struct VizEngine_API Transform
{
    glm::vec3 Position = glm::vec3(0.0f);
    glm::vec3 Rotation = glm::vec3(0.0f);  // Euler angles (radians)
    glm::vec3 Scale = glm::vec3(1.0f);
    
    // Compute the model matrix
    glm::mat4 GetModelMatrix() const
    {
        glm::mat4 model = glm::mat4(1.0f);
        
        // Order matters! Scale → Rotate → Translate
        model = glm::translate(model, Position);
        model = glm::rotate(model, Rotation.x, glm::vec3(1, 0, 0));
        model = glm::rotate(model, Rotation.y, glm::vec3(0, 1, 0));
        model = glm::rotate(model, Rotation.z, glm::vec3(0, 0, 1));
        model = glm::scale(model, Scale);
        
        return model;
    }
    
    // Convenience for UI (degrees are easier for humans)
    void SetRotationDegrees(const glm::vec3& degrees)
    {
        Rotation = glm::radians(degrees);
    }
};
```

### Why Transform Order Matters

We want transformations applied in this order:
```
Scale → Rotate → Translate
```

Think about it:
1. **Scale** - Make the object bigger/smaller (at origin)
2. **Rotate** - Spin it (around origin)
3. **Translate** - Move it to final position

If you translate first, the object rotates around the world origin, not itself!

**But the code looks backwards:**
```cpp
model = glm::translate(model, Position);  // Last in code = Applied last
model = glm::rotate(model, ...);          // Middle
model = glm::scale(model, Scale);         // First in code = Applied first
```

**Why?** Matrix math is applied right-to-left:
```
Final = Translate * Rotate * Scale * Vertex
        ←───────── read this way ──────────
```

So even though `translate` is written first in code, it's applied last to the vertex!

---

## The Vertex Struct

> [!NOTE]
> **Vertex Evolution:** In [Chapter 6](06_OpenGLFundamentals.md), we used raw `float[]` arrays for position only. Here we introduce a proper `Vertex` struct with all the data needed for textured, lit rendering. This is the definitive Vertex struct used throughout the engine.

Defines what data each vertex contains:

```cpp
// VizEngine/Core/Mesh.h

struct Vertex
{
    glm::vec4 Position;
    glm::vec3 Normal;      // For lighting (Chapter 13)
    glm::vec4 Color;
    glm::vec2 TexCoords;

    Vertex() = default;
    
    Vertex(const glm::vec4& pos, const glm::vec4& col, const glm::vec2& tex)
        : Position(pos), Normal(0, 1, 0), Color(col), TexCoords(tex) {}
        
    Vertex(const glm::vec4& pos, const glm::vec3& norm, 
           const glm::vec4& col, const glm::vec2& tex)
        : Position(pos), Normal(norm), Color(col), TexCoords(tex) {}
};
```

### Vertex Buffer Layout

The layout must match the Vertex struct:

```cpp
VertexBufferLayout layout;
layout.Push<float>(4); // Position (vec4)
layout.Push<float>(3); // Normal (vec3)
layout.Push<float>(4); // Color (vec4)
layout.Push<float>(2); // TexCoords (vec2)
```

---

## The Mesh Class

Encapsulates geometry data with GPU buffers:

```cpp
// VizEngine/Core/Mesh.h

class VizEngine_API Mesh
{
public:
    Mesh(const std::vector<Vertex>& vertices, 
         const std::vector<unsigned int>& indices);
    
    void Bind() const;
    void Unbind() const;
    
    const VertexArray& GetVertexArray() const;
    const IndexBuffer& GetIndexBuffer() const;
    
    // Factory methods for common shapes
    static std::unique_ptr<Mesh> CreatePyramid();
    static std::unique_ptr<Mesh> CreateCube();
    static std::unique_ptr<Mesh> CreatePlane(float size = 1.0f);
    
private:
    std::unique_ptr<VertexArray> m_VertexArray;
    std::unique_ptr<VertexBuffer> m_VertexBuffer;
    std::unique_ptr<IndexBuffer> m_IndexBuffer;
};
```

### Factory Methods

Instead of manually specifying vertices:

```cpp
// Old way - tedious and error-prone
float vertices[] = { /* 50+ numbers */ };
unsigned int indices[] = { /* 18+ numbers */ };
VertexBuffer vb(vertices, sizeof(vertices));
// ... more setup

// New way - clean and reusable
auto pyramid = Mesh::CreatePyramid();  // Done!
auto cube = Mesh::CreateCube();
auto floor = Mesh::CreatePlane(20.0f);
```

### Factory Implementation Example

```cpp
std::unique_ptr<Mesh> Mesh::CreatePyramid()
{
    std::vector<Vertex> vertices = {
        // Base (facing down, normal = -Y)
        Vertex(glm::vec4(-0.5f, 0.0f,  0.5f, 1.0f), 
               glm::vec3(0, -1, 0),
               glm::vec4(1.0f), 
               glm::vec2(0.0f, 0.0f)),
        // ... more vertices
    };
    
    std::vector<unsigned int> indices = {
        0, 1, 2,  // base triangle 1
        0, 2, 3,  // base triangle 2
        // ... side triangles
    };
    
    return std::make_unique<Mesh>(vertices, indices);
}
```

---

## Usage Example

```cpp
// Create meshes
auto pyramidMesh = Mesh::CreatePyramid();
auto cubeMesh = Mesh::CreateCube();

// Create transforms
Transform pyramidTransform;
pyramidTransform.Position = glm::vec3(-3.0f, 0.0f, 0.0f);
pyramidTransform.Scale = glm::vec3(2.0f, 4.0f, 2.0f);

Transform cubeTransform;
cubeTransform.Position = glm::vec3(3.0f, 1.0f, 0.0f);

// In render loop
glm::mat4 pyramidModel = pyramidTransform.GetModelMatrix();
glm::mat4 cubeModel = cubeTransform.GetModelMatrix();
```

---

## Key Takeaways

1. **Transform = Position + Rotation + Scale** - Converts to a 4x4 model matrix
2. **Matrix order is right-to-left** - Code order is opposite of application order
3. **Vertex struct defines per-vertex data** - Position, normal, color, UVs
4. **Mesh encapsulates GPU buffers** - VAO, VBO, IBO together
5. **Factory methods simplify creation** - `CreatePyramid()` vs manual vertex arrays

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Object at wrong position | Transform not applied | Check `GetModelMatrix()` call |
| Rotation seems wrong | Degrees vs radians | Use `SetRotationDegrees()` or `glm::radians()` |
| Object rotates around world origin | Wrong transform order | Ensure Scale → Rotate → Translate |
| Mesh doesn't render | Layout mismatch | Verify buffer layout matches Vertex struct |

---

## Checkpoint

This chapter covered Transform and Mesh:

**Files:**
| File | Purpose |
|------|---------|
| `VizEngine/Core/Transform.h` | Position, rotation, scale → model matrix |
| `VizEngine/Core/Mesh.h` | Vertex struct + Mesh class |
| `VizEngine/Core/Mesh.cpp` | Factory methods implementation |

**Checkpoint:** Create Transform.h, Mesh.h/.cpp with Vertex struct and factory methods, verify CreatePyramid() works.

---

## Exercise

1. Add `CreateSphere()` factory method
2. Add `CreateCylinder()` factory method  
3. Implement `SetRotationDegrees()` for X, Y, Z independently
4. Add a `Reset()` method to Transform

---

> **Next:** [Chapter 11: Camera System](11_CameraSystem.md) - View and projection matrices.

