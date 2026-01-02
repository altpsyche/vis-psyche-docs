\newpage

# Chapter 10: Multiple Objects & Scene Management

## The Problem

Look at our current `Application::Run()`. It works, but it's limited:

```cpp
auto pyramidMesh = Mesh::CreatePyramid();
Transform pyramidTransform;
// ... render one pyramid
```

What if we want:
- 10 pyramids at different positions?
- A mix of pyramids, cubes, and planes?
- The ability to add/remove objects at runtime?

### The Naive Approach (Don't Do This)

```cpp
// This doesn't scale!
auto pyramid1 = Mesh::CreatePyramid();
Transform transform1;

auto pyramid2 = Mesh::CreatePyramid();
Transform transform2;

auto cube1 = Mesh::CreateCube();
Transform transform3;

// ... and so on for 100 objects?
```

Problems:
- **Copy-paste nightmare** - Repetitive, error-prone
- **Fixed at compile time** - Can't add objects dynamically
- **Hard to manage** - What if you want to delete object #47?

---

## A Note on Simplicity

**What we're building in this chapter is intentionally simple.**

Production game engines like Unity and Unreal use sophisticated patterns like Entity Component Systems (ECS). We're not doing that yet. Instead, we're building a basic "object list" approach that's easy to understand and implement.

Why start simple?

- **Learn the fundamentals first** - Understand what problems arise before learning their solutions
- **See the pain points** - You'll naturally feel *why* ECS exists by hitting the walls of this approach
- **Working code > Perfect architecture** - Get something running, then improve it

By the end of this chapter, you'll have a working multi-object scene. You'll also understand the limitations that motivate more sophisticated architectures. We'll revisit this topic later when we implement ECS.

---

## The SceneObject Concept

We need a struct that bundles everything that makes an "object" in our scene:

```cpp
struct SceneObject
{
    std::shared_ptr<Mesh> MeshPtr;     // What to draw (geometry)
    Transform ObjectTransform;          // Where to draw it
    glm::vec4 Color = glm::vec4(1.0f); // Per-object tint color
    bool Active = true;                 // Enable/disable rendering
};
```

### Why `shared_ptr` for Mesh?

**Key insight:** The mesh (geometry data) can be shared, but the transform must be unique.

Consider 100 trees in a forest:
- They all use the **same** tree mesh (vertices, indices)
- They each have **different** positions/rotations/scales

```cpp
// Create one mesh, share it
auto treeMesh = std::make_shared<Mesh>(Mesh::CreatePyramid());

// 100 objects, one mesh
for (int i = 0; i < 100; i++)
{
    SceneObject tree;
    tree.MeshPtr = treeMesh;  // All share the same geometry
    tree.ObjectTransform.Position = glm::vec3(i * 2.0f, 0.0f, 0.0f);  // Different positions
    scene.push_back(tree);
}
```

This is **much** more efficient than creating 100 separate meshes!

---

## The Scene Class

A container that manages our collection of objects:

```cpp
// VizEngine/Core/Scene.h

class VizEngine_API Scene
{
public:
    // Modification
    SceneObject& Add(std::shared_ptr<Mesh> mesh, const std::string& name = "Object");
    void Remove(size_t index);
    void Clear();
    
    // Access (container-like)
    SceneObject& operator[](size_t index);        // scene[0]
    SceneObject& At(size_t index);                // scene.At(0) - bounds checked
    size_t Size() const;
    bool Empty() const;
    
    // Iteration (enables range-based for)
    auto begin();
    auto end();
    
    // Scene operations
    void Update(float deltaTime);
    void Render(Renderer& renderer, Shader& shader, const Camera& camera);
    
private:
    std::vector<SceneObject> m_Objects;
};
```

### Implementation

```cpp
// VizEngine/Core/Scene.cpp

SceneObject& Scene::Add(std::shared_ptr<Mesh> mesh, const std::string& name)
{
    SceneObject obj;
    obj.MeshPtr = mesh;
    obj.ObjectTransform = Transform{};  // Default transform
    obj.Color = glm::vec4(1.0f);        // White (no tint)
    obj.Active = true;
    obj.Name = name;
    
    m_Objects.push_back(std::move(obj));
    return m_Objects.back();
}

void Scene::Remove(size_t index)
{
    if (index < m_Objects.size())
    {
        m_Objects.erase(m_Objects.begin() + index);
    }
}

void Scene::Render(Renderer& renderer, Shader& shader, const Camera& camera)
{
    shader.Bind();
    
    for (auto& obj : m_Objects)
    {
        if (!obj.Active) continue;  // Skip disabled objects
        if (!obj.MeshPtr) continue; // Safety check
        
        // Calculate MVP for this object
        glm::mat4 mvp = camera.GetViewProjectionMatrix() 
                      * obj.ObjectTransform.GetModelMatrix();
        
        shader.SetMatrix4fv("u_MVP", mvp);
        shader.Set4f("u_Color", obj.Color);
        
        obj.MeshPtr->Bind();
        renderer.Draw(obj.MeshPtr->GetVertexArray(), 
                      obj.MeshPtr->GetIndexBuffer(), 
                      shader);
    }
}
```

---

## Rendering Multiple Objects

### Before: Single Object

```cpp
// One object, one draw call
glm::mat4 mvp = camera.GetViewProjectionMatrix() * pyramidTransform.GetModelMatrix();
shader.SetMatrix4fv("u_MVP", mvp);
pyramidMesh->Bind();
renderer.Draw(pyramidMesh->GetVertexArray(), pyramidMesh->GetIndexBuffer(), shader);
```

### After: Multiple Objects

```cpp
// Many objects, loop through them (range-based for works!)
for (auto& obj : scene)
{
    if (!obj.Active) continue;
    
    glm::mat4 mvp = camera.GetViewProjectionMatrix() 
                  * obj.ObjectTransform.GetModelMatrix();
    
    shader.SetMatrix4fv("u_MVP", mvp);
    shader.Set4f("u_Color", obj.Color);
    
    obj.MeshPtr->Bind();
    renderer.Draw(obj.MeshPtr->GetVertexArray(), 
                  obj.MeshPtr->GetIndexBuffer(), 
                  shader);
}
```

The key difference: we calculate a **new MVP matrix for each object** because each has its own transform.

---

## Shared vs Owned Resources

Understanding resource ownership is crucial:

![Shared Mesh Architecture](images/10-shared-mesh-diagram.png)

**Shared (via `shared_ptr`):**
- Mesh geometry (vertices, indices, GPU buffers)
- Multiple objects can reference the same mesh
- Mesh is deleted when last reference is gone

**Owned (per object):**
- Transform (position, rotation, scale)
- Color
- Active state
- Each object has its own copy

---

## Updating the Application

Here's how `Application::Run()` changes:

```cpp
int Application::Run()
{
    // ... initialization code ...
    
    // ═══════════════════════════════════════════════════
    // Create Shared Meshes
    // ═══════════════════════════════════════════════════
    auto pyramidMesh = std::make_shared<Mesh>(Mesh::CreatePyramid());
    auto cubeMesh = std::make_shared<Mesh>(Mesh::CreateCube());
    
    // ═══════════════════════════════════════════════════
    // Build Scene
    // ═══════════════════════════════════════════════════
    Scene scene;
    
    // Add a row of pyramids
    for (int i = 0; i < 5; i++)
    {
        auto& obj = scene.Add(pyramidMesh);
        obj.ObjectTransform.Position = glm::vec3((i - 2) * 3.0f, 0.0f, 0.0f);
        obj.Color = glm::vec4(1.0f, 0.5f + i * 0.1f, 0.2f, 1.0f);
    }
    
    // Add a cube in the middle
    auto& cube = scene.Add(cubeMesh);
    cube.ObjectTransform.Position = glm::vec3(0.0f, 2.0f, -5.0f);
    cube.ObjectTransform.Scale = glm::vec3(2.0f);
    
    // ═══════════════════════════════════════════════════
    // Main Loop
    // ═══════════════════════════════════════════════════
    while (!window.WindowShouldClose())
    {
        // ... input, deltaTime ...
        
        // Update scene (e.g., rotate all objects)
        scene.Update(deltaTime);
        
        // Render
        renderer.Clear(clearColor);
        scene.Render(renderer, shader, camera);
        
        // ... UI, swap buffers ...
    }
}
```

---

## ImGui: Immediate Mode GUI

Before diving into object selection UI, this section covers the GUI library we're using.

### What is Dear ImGui?

**Dear ImGui** (often just "ImGui") is an **immediate mode** GUI library. This is different from traditional "retained mode" GUIs:

| Retained Mode (Qt, WinForms) | Immediate Mode (ImGui) |
|------------------------------|------------------------|
| Create widgets once, update them | Describe widgets every frame |
| Widgets maintain their own state | You maintain state in your variables |
| Complex event callbacks | Simple if-statement logic |
| Heavy, feature-rich | Lightweight, programmer-friendly |

### How It Works

Every frame, you tell ImGui what to draw:

```cpp
// This runs every frame in your render loop
if (ImGui::Button("Click Me"))
{
    // Button was clicked THIS frame
    DoSomething();
}

ImGui::DragFloat("Speed", &mySpeed, 0.1f);  // Directly modifies mySpeed
```

There's no "create button, attach callback" setup. You just describe the UI and ImGui handles input, rendering, and state.

### Common Widgets We'll Use

```cpp
// Windows - container for widgets
ImGui::Begin("My Window");   // Start window
// ... widgets go here ...
ImGui::End();                // End window

// Input widgets - directly modify your variables
ImGui::DragFloat3("Position", &transform.Position.x, 0.1f);
ImGui::DragFloat("Speed", &speed, 0.01f);
ImGui::Checkbox("Enabled", &isEnabled);
ImGui::ColorEdit4("Color", &color.x);

// Selection
if (ImGui::Selectable("Item 1", isSelected))
{
    // Item was clicked
}

// Buttons
if (ImGui::Button("Do Thing"))
{
    // Button clicked this frame
}

// Layout helpers
ImGui::Separator();          // Horizontal line
ImGui::SameLine();           // Next widget on same line
ImGui::Text("Label: %d", value);  // Static text
```

### Our UIManager Wrapper

We wrap ImGui setup/teardown in `UIManager`:

```cpp
// UIManager handles ImGui initialization and per-frame boilerplate
UIManager ui(window.GetWindow());

// In render loop:
ui.BeginFrame();           // Starts ImGui frame

ui.StartWindow("Controls"); // Our wrapper for ImGui::Begin
// ... ImGui widgets ...
ui.EndWindow();            // Our wrapper for ImGui::End

ui.Render();               // Renders all ImGui draw data
```

This keeps OpenGL/GLFW integration details out of your application code.

---

## UI for Object Selection

With multiple objects, we need UI to select and manipulate them:

```cpp
// In your main loop, after ui.BeginFrame():

ui.StartWindow("Scene Objects");

// Object list
static int selectedObject = 0;

for (size_t i = 0; i < scene.Size(); i++)
{
    char label[32];
    snprintf(label, sizeof(label), "Object %zu", i);
    
    if (ImGui::Selectable(label, selectedObject == (int)i))
    {
        selectedObject = (int)i;
    }
}

ImGui::Separator();

// Edit selected object
if (selectedObject >= 0 && selectedObject < (int)scene.Size())
{
    auto& obj = scene[selectedObject];
    
    ImGui::Checkbox("Active", &obj.Active);
    ImGui::DragFloat3("Position", &obj.ObjectTransform.Position.x, 0.1f);
    ImGui::DragFloat3("Rotation", &obj.ObjectTransform.Rotation.x, 0.01f);
    ImGui::DragFloat3("Scale", &obj.ObjectTransform.Scale.x, 0.1f);
    ImGui::ColorEdit4("Color", &obj.Color.x);
    
    if (ImGui::Button("Delete"))
    {
        scene.Remove(selectedObject);
        selectedObject = std::min(selectedObject, (int)scene.Size() - 1);
    }
}

ImGui::Separator();

// Add new objects
if (ImGui::Button("Add Pyramid"))
{
    scene.Add(pyramidMesh);
}
ImGui::SameLine();
if (ImGui::Button("Add Cube"))
{
    scene.Add(cubeMesh);
}

ui.EndWindow();
```

---

## Limitations of This Approach

To be honest about what our simple `SceneObject` can't do.

### The "God Struct" Problem

Our `SceneObject` bundles everything together:

```cpp
struct SceneObject
{
    std::shared_ptr<Mesh> MeshPtr;
    Transform ObjectTransform;
    glm::vec4 Color;
    bool Active;
};
```

What happens when we need more features?

```cpp
// This gets ugly fast...
struct SceneObject
{
    std::shared_ptr<Mesh> MeshPtr;
    Transform ObjectTransform;
    glm::vec4 Color;
    bool Active;
    
    // Physics? Add it here...
    glm::vec3 Velocity;
    float Mass;
    bool IsStatic;
    
    // AI? Add it here too...
    AIBehavior* Behavior;
    float DetectionRadius;
    
    // Audio? Sure, why not...
    AudioSource* Sound;
    
    // Health system?
    float Health;
    float MaxHealth;
    
    // And on and on...
};
```

**Problems:**

| Issue | Why It's Bad |
|-------|--------------|
| **Wasted memory** | A static rock has `Velocity`, `AIBehavior`, `Health`... all unused |
| **Rigid structure** | Adding features means changing `SceneObject` everywhere |
| **No composition** | Can't mix-and-match capabilities per object |
| **Hard to iterate** | Want all objects with physics? Loop through everything, check each one |

### What We Can't Easily Do

With our current approach:

- **Different object types** - A "player" and a "tree" are the same struct
- **Behaviors** - No way to attach scripts or AI to specific objects
- **Physics** - Would need to add physics fields to *every* object
- **Parent-child relationships** - No scene hierarchy
- **Querying** - "Give me all objects with health < 50" requires full scan

### This Is Fine (For Now)

For a learning engine with < 100 objects, this approach works. It's:
- Easy to understand
- Easy to debug
- Sufficient for visualization

But when you find yourself adding `if (object.hasPhysics)` checks everywhere, it's time for a better architecture.

---

## Performance Considerations

### Draw Calls

Each object = 1 draw call. For our learning engine, this is fine.

Production engines optimize with:
- **Batching** - Combine similar objects into one draw call
- **Instancing** - GPU draws multiple copies with one call
- **Frustum Culling** - Skip objects outside camera view

### Memory {#performance-memory}

With `shared_ptr`, we efficiently share mesh data:

| Scenario | Mesh Memory | Transform Memory |
|----------|-------------|------------------|
| 100 unique pyramids | 100× mesh size | 100× transform size |
| 100 pyramids (shared) | 1× mesh size | 100× transform size |

The shared approach uses ~100× less GPU memory for geometry!

---

## Looking Ahead: Entity Component System (ECS)

The limitations we discussed aren't unique to our engine. Every game developer hits these walls, which is why the industry converged on a powerful pattern: **Entity Component System**.

### The ECS Concept

Instead of objects owning all their data, ECS separates concerns:

| Concept | What It Is | Example |
|---------|-----------|---------|
| **Entity** | Just an ID (integer) | `Entity player = 42;` |
| **Component** | Pure data, no logic | `Transform`, `Health`, `Velocity` |
| **System** | Logic that operates on components | `PhysicsSystem`, `RenderSystem` |

### Our Approach vs ECS

![ECS Comparison](images/10-ecs-comparison.png)

### Why ECS Wins

1. **Composition over inheritance** - Mix and match components freely
2. **Memory efficiency** - Only store what's needed per entity
3. **Cache-friendly** - Systems iterate over contiguous component arrays
4. **Parallel-friendly** - Systems can run on different threads
5. **Flexible queries** - "All entities with Transform + Velocity" is fast

### ECS in the Wild

Real engines using ECS or similar patterns:

- **Unity DOTS** - Data-Oriented Technology Stack with full ECS
- **Unreal Mass Entity** - ECS-like system for large crowds
- **EnTT** - Popular C++ ECS library (header-only, fast)
- **Flecs** - Another excellent C++ ECS library

### Beyond Simple Scenes

For more complex games, consider libraries like:
- **EnTT** - Popular C++ ECS library (header-only, fast)
- **Flecs** - Another excellent C++ ECS library

Our simple `std::vector<SceneObject>` approach works well for learning and prototyping.

---

## Key Takeaways

1. **SceneObject bundles rendering data** - Mesh + Transform + Color + Active flag
2. **Share geometry, own transforms** - `shared_ptr<Mesh>` with unique `Transform`
3. **Scene manages the collection** - Add, remove, update, render
4. **MVP per object** - Each object needs its own Model-View-Projection matrix
5. **UI enables editing** - Select, modify, delete objects at runtime
6. **This is a stepping stone** - Simple and effective for learning, but ECS is the production-grade solution

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| All objects drawn same place | Using same transform | Each `SceneObject` needs its own `Transform` |
| Object disappears when moved | Wrong index after deletion | Update indices after `erase()` |
| Memory leak | Not using `shared_ptr` correctly | Ensure proper ownership semantics |
| Crash when iterating + deleting | Iterator invalidation | Use index-based loop or `erase-remove` idiom |

---

## Checkpoint

This chapter covered managing multiple objects in a scene:

**Key Classes:**
| Class | Purpose |
|-------|---------|
| `SceneObject` | Mesh (shared) + Transform (owned) + Color |
| Scene (vector) | Collection of `SceneObject`s |

**Memory Pattern:**
- `shared_ptr<Mesh>` — Geometry shared across instances
- `Transform` — Unique per object (position, rotation, scale)

**Checkpoint:** Create `Mesh.h` with Vertex struct and factory methods, `SceneObject.h`, `Scene.h`, use the Scene class in `Application::Run()` to manage multiple objects, and verify they render.

---

## Exercises

1. **Implement SceneObject and Scene** - Create the classes described above
2. **Create a grid of cubes** - 5×5 cubes with different colors
3. **Add object selection in UI** - Click list to select, show transform controls
4. **Implement object deletion** - Remove selected object, handle index updates
5. **Add rotation animation** - Make all pyramids spin at different speeds

---

> **Next:** [Chapter 12: Lighting](12_Lighting.md) - Making objects look 3D with Blinn-Phong lighting.

> **Reference:** For implementation details, class diagrams, and debugging tips, see [Appendix A: Code Reference](A_Reference.md).



