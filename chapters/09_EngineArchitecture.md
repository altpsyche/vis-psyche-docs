\newpage

# Chapter 9: Engine Architecture

## The Problem: Monolithic Code

Our original `Application::Run()` was doing everything:

```cpp
int Application::Run()
{
    // Window creation
    // OpenGL initialization
    // Hardcoded vertex data ← Bad!
    // Shader loading
    // Texture loading
    // Camera matrices calculated inline ← Bad!
    // Render loop with everything mixed together ← Bad!
}
```

Problems:
- **Hard to change** - Everything is tangled
- **Can't reuse** - Want a different shape? Rewrite everything
- **Hard to understand** - 200+ lines of mixed concerns

---

## Separation of Concerns

Professional engines separate responsibilities:

```
Application (orchestrates)
    ├── Window (GLFW, input)
    ├── Renderer (draw calls)
    ├── Camera (view/projection)
    ├── Scene
    │   ├── Entity 1 (Mesh + Transform)
    │   ├── Entity 2 (Mesh + Transform)
    │   └── ...
    └── Assets
        ├── Shaders
        └── Textures
```

Each piece has **one job** and does it well.

---

## The Transform Struct

Represents position, rotation, scale in 3D space:

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

## The Camera Class

Manages view and projection matrices:

```cpp
// VizEngine/Core/Camera.h

class VizEngine_API Camera
{
public:
    Camera(float fov, float aspectRatio, float nearPlane, float farPlane);
    
    // Transform
    void SetPosition(const glm::vec3& position);
    void SetRotation(float pitch, float yaw);
    
    // Matrices
    const glm::mat4& GetViewMatrix() const { return m_ViewMatrix; }
    const glm::mat4& GetProjectionMatrix() const { return m_ProjectionMatrix; }
    glm::mat4 GetViewProjectionMatrix() const 
    { 
        return m_ProjectionMatrix * m_ViewMatrix; 
    }
    
    // Movement helpers
    void MoveForward(float amount);
    void MoveRight(float amount);
    
    // Direction vectors
    glm::vec3 GetForward() const;
    glm::vec3 GetRight() const;
    
private:
    void RecalculateViewMatrix();
    void RecalculateProjectionMatrix();
    
    glm::vec3 m_Position;
    float m_Pitch, m_Yaw;  // Rotation in radians
    
    float m_FOV, m_AspectRatio;
    float m_NearPlane, m_FarPlane;
    
    glm::mat4 m_ViewMatrix;
    glm::mat4 m_ProjectionMatrix;
};
```

### View Matrix

Transforms world space to camera space:

```cpp
void Camera::RecalculateViewMatrix()
{
    glm::vec3 forward = GetForward();
    glm::vec3 target = m_Position + forward;
    m_ViewMatrix = glm::lookAt(m_Position, target, glm::vec3(0, 1, 0));
}
```

`glm::lookAt(eye, target, up)` creates a matrix that:
- Puts the camera at `eye`
- Points toward `target`
- Uses `up` to orient (usually Y-up)

### Projection Matrix

Transforms view space to clip space:

```cpp
void Camera::RecalculateProjectionMatrix()
{
    m_ProjectionMatrix = glm::perspective(
        glm::radians(m_FOV),  // Field of view (degrees → radians)
        m_AspectRatio,         // Width / Height
        m_NearPlane,           // Near clip plane
        m_FarPlane             // Far clip plane
    );
}
```

**Perspective projection** makes things smaller as they get further away (realistic).

---

## The Mesh Class

Encapsulates geometry data:

```cpp
// VizEngine/Core/Mesh.h

struct Vertex
{
    glm::vec4 Position;
    glm::vec3 Normal;      // For lighting calculations
    glm::vec4 Color;
    glm::vec2 TexCoords;
};
```

> **Note:** This struct matches our current engine. The `Normal` field is required for lighting (see [Chapter 11: Lighting](11_Lighting.md)). If you're following along and haven't reached lighting yet, you can temporarily omit it, but you'll need to add it back later.


```cpp
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
// Old way
float vertices[] = { /* 50 numbers */ };
unsigned int indices[] = { /* 18 numbers */ };
VertexBuffer vb(vertices, sizeof(vertices));
// ... setup code

// New way
auto pyramid = Mesh::CreatePyramid();  // Done!
```

The factory creates the data internally:

```cpp
std::unique_ptr<Mesh> Mesh::CreatePyramid()
{
    std::vector<Vertex> vertices = {
        // Base
        Vertex(glm::vec4(-0.5f, 0.0f,  0.5f, 1.0f), 
               glm::vec4(1.0f), 
               glm::vec2(0.0f, 0.0f)),
        // ... more vertices
    };
    
    std::vector<unsigned int> indices = {
        0, 1, 2,  // base triangles
        0, 2, 3,
        // ... side triangles
    };
    
    return std::make_unique<Mesh>(vertices, indices);
}
```

---

## Putting It Together

The refactored `Application::Run()`:

```cpp
int Application::Run()
{
    // ═══════════════════════════════════════════════════
    // Initialization
    // ═══════════════════════════════════════════════════
    GLFWManager window(800, 800, "VizPsyche");
    
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
        return -1;
    
    glEnable(GL_BLEND);
    glEnable(GL_DEPTH_TEST);
    
    // ═══════════════════════════════════════════════════
    // Create Scene Objects
    // ═══════════════════════════════════════════════════
    Camera camera(45.0f, 800.0f / 800.0f, 0.1f, 100.0f);
    camera.SetPosition(glm::vec3(0.0f, 4.0f, -15.0f));
    
    auto pyramidMesh = Mesh::CreatePyramid();
    
    Transform pyramidTransform;
    pyramidTransform.Scale = glm::vec3(5.0f, 10.0f, 5.0f);
    
    // ═══════════════════════════════════════════════════
    // Load Assets
    // ═══════════════════════════════════════════════════
    Shader shader("src/resources/shaders/lit.shader");
    Texture texture("src/resources/textures/uvchecker.png");
    texture.Bind();
    
    // ═══════════════════════════════════════════════════
    // Systems
    // ═══════════════════════════════════════════════════
    UIManager ui(window.GetWindow());
    Renderer renderer;
    
    // Variables
    float clearColor[4] = { 0.05f, 0.02f, 0.01f, 1.0f };
    float rotationSpeed = 0.5f;
    double prevTime = glfwGetTime();
    
    // ═══════════════════════════════════════════════════
    // Main Loop
    // ═══════════════════════════════════════════════════
    while (!window.WindowShouldClose())
    {
        // --- Input ---
        window.ProcessInput();
        ui.BeginFrame();
        
        // --- Update ---
        double currentTime = glfwGetTime();
        float deltaTime = float(currentTime - prevTime);
        prevTime = currentTime;
        
        pyramidTransform.Rotation.y += rotationSpeed * deltaTime;
        
        // --- Render ---
        renderer.Clear(clearColor);
        
        glm::mat4 mvp = camera.GetViewProjectionMatrix() 
                      * pyramidTransform.GetModelMatrix();
        
        shader.Bind();
        shader.SetMatrix4fv("u_MVP", mvp);
        
        pyramidMesh->Bind();
        renderer.Draw(pyramidMesh->GetVertexArray(), 
                      pyramidMesh->GetIndexBuffer(), 
                      shader);
        
        // --- UI ---
        ui.StartWindow("Controls");
        ImGui::DragFloat3("Position", &pyramidTransform.Position.x);
        ImGui::DragFloat("Speed", &rotationSpeed);
        ui.EndWindow();
        
        ui.Render();
        window.SwapBuffersAndPollEvents();
    }
    
    return 0;
}
```

### What Changed

| Before | After |
|--------|-------|
| Hardcoded vertex arrays | `Mesh::CreatePyramid()` |
| Inline matrix math | `camera.GetViewProjectionMatrix()` |
| Manual transform calculation | `pyramidTransform.GetModelMatrix()` |
| Mixed concerns | Clear sections: Init, Create, Load, Loop |

---

## The Update Loop Pattern

Every game engine has this loop:

```
while (running)
{
    ProcessInput();   // Handle keyboard/mouse
    Update(dt);       // Game logic, physics, AI
    Render();         // Draw everything
}
```

The `deltaTime` (dt) is crucial:
- Time since last frame
- Makes movement **frame-rate independent**

```cpp
// Bad: Moves 60 units/second at 60fps, 30 units/second at 30fps
position += 1.0f;

// Good: Moves 60 units/second regardless of framerate
position += 60.0f * deltaTime;
```

---

## Key Takeaways

1. **Separate concerns** - Each class has one job
2. **Transform holds spatial data** - Position, rotation, scale → Model matrix
3. **Camera handles viewing** - View matrix + Projection matrix
4. **Mesh encapsulates geometry** - Factory methods for common shapes
5. **Delta time** - Frame-rate independent updates

---

## What's Next?

The current architecture is good for learning. A production engine would add:

- **Scene Graph** - Parent-child relationships for transforms
- **Entity Component System** - Flexible object composition
- **Asset Manager** - Caching, async loading
- **Material System** - Shader + textures as one unit
- **Multiple Render Passes** - Shadows, post-processing

---

## Exercise

1. Add a `CreateSphere()` factory method to Mesh
2. Make the camera controllable with WASD keys
3. Add a second pyramid with a different transform
4. Create a simple Material class that bundles Shader + Texture

---

> **Next:** [Chapter 10: Multiple Objects & Scene](10_MultipleObjects.md) - Managing multiple objects in a scene.

> **Reference:** For a complete file reference and memory ownership table, see [Appendix A: Code Reference](A_Reference.md).



