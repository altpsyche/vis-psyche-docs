\newpage

# Chapter 14: Scene Management

## The Problem

With Transform, Camera, and Mesh in place, we can render one object. But what about:
- 10 pyramids at different positions?
- A mix of pyramids, cubes, and planes?
- Adding/removing objects at runtime?

We need a **scene** - a collection of objects we can manage.

---

## A Note on Simplicity

**What we're building is intentionally simple.**

Production engines use Entity Component Systems (ECS). We're building a basic "object list" approach that's easy to understand.

Why start simple?
- **Learn fundamentals first** - Understand problems before learning solutions
- **See the pain points** - You'll feel *why* ECS exists
- **Working code > Perfect architecture** - Get something running, then improve

---

## The SceneObject Struct

Bundles everything that makes an "object" in our scene:

> [!NOTE]
> **Prerequisites:** This struct uses `Mesh` from [Chapter 10](10_TransformAndMesh.md), `Texture` from [Chapter 8](08_Textures.md), and `Transform` from [Chapter 10](10_TransformAndMesh.md).

```cpp
// VizEngine/Core/SceneObject.h

struct SceneObject
{
    std::string Name = "Object";
    std::shared_ptr<Mesh> MeshPtr;      // What to draw
    std::shared_ptr<Texture> TexturePtr; // Optional texture
    Transform ObjectTransform;           // Where to draw it
    glm::vec4 Color = glm::vec4(1.0f);  // Tint color
    float Roughness = 0.5f;             // Material roughness
    bool Active = true;                  // Enable/disable
};
```

### Why `shared_ptr` for Mesh?

**Key insight:** Mesh geometry can be shared, transforms must be unique.

Consider 100 trees:
- All use the **same** tree mesh (vertices, indices)
- Each has **different** position/rotation/scale

```cpp
auto treeMesh = std::make_shared<Mesh>(Mesh::CreatePyramid());

for (int i = 0; i < 100; i++)
{
    SceneObject tree;
    tree.MeshPtr = treeMesh;  // All share the same geometry!
    tree.ObjectTransform.Position = glm::vec3(i * 2.0f, 0.0f, 0.0f);
    scene.Add(tree);
}
```

This is **100× more efficient** than creating separate meshes!

---

## The Scene Class

A container managing object collection:

```cpp
// VizEngine/Core/Scene.h

class VizEngine_API Scene
{
public:
    // Modification
    SceneObject& Add(std::shared_ptr<Mesh> mesh, const std::string& name = "Object");
    void Remove(size_t index);
    void Clear();
    
    // Access
    SceneObject& operator[](size_t index);
    size_t Size() const;
    bool Empty() const;
    
    // Iteration (enables range-based for)
    auto begin() { return m_Objects.begin(); }
    auto end() { return m_Objects.end(); }
    
    // Rendering
    void Render(Renderer& renderer, Shader& shader, const Camera& camera);
    
private:
    std::vector<SceneObject> m_Objects;
};
```

### Render Implementation

```cpp
void Scene::Render(Renderer& renderer, Shader& shader, const Camera& camera)
{
    shader.Bind();
    
    for (auto& obj : m_Objects)
    {
        if (!obj.Active) continue;
        if (!obj.MeshPtr) continue;
        
        // Calculate matrices
        glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
        glm::mat4 mvp = camera.GetViewProjectionMatrix() * model;
        
        // Set uniforms
        shader.SetMatrix4fv("u_MVP", mvp);
        shader.SetMatrix4fv("u_Model", model);
        shader.Set4f("u_ObjectColor", obj.Color);
        shader.SetFloat("u_Roughness", obj.Roughness);
        
        // Bind texture
        if (obj.TexturePtr)
            obj.TexturePtr->Bind();
        
        // Draw
        obj.MeshPtr->Bind();
        renderer.Draw(obj.MeshPtr->GetVertexArray(), 
                      obj.MeshPtr->GetIndexBuffer(), 
                      shader);
    }
}
```

---

## Building a Scene

```cpp
int Application::Run()
{
    // ... initialization ...
    
    // Create shared meshes
    auto pyramidMesh = std::make_shared<Mesh>(Mesh::CreatePyramid());
    auto cubeMesh = std::make_shared<Mesh>(Mesh::CreateCube());
    auto planeMesh = std::make_shared<Mesh>(Mesh::CreatePlane(20.0f));
    
    // Build scene
    Scene scene;
    
    // Ground plane
    auto& ground = scene.Add(planeMesh, "Ground");
    ground.ObjectTransform.Position = glm::vec3(0.0f, -1.0f, 0.0f);
    ground.Color = glm::vec4(0.3f, 0.3f, 0.35f, 1.0f);
    
    // Row of pyramids
    for (int i = 0; i < 5; i++)
    {
        auto& obj = scene.Add(pyramidMesh, "Pyramid");
        obj.ObjectTransform.Position = glm::vec3((i - 2) * 3.0f, 0.0f, 0.0f);
        obj.Color = glm::vec4(1.0f, 0.5f + i * 0.1f, 0.2f, 1.0f);
    }
    
    // Main loop
    while (!window.WindowShouldClose())
    {
        // ... input, update ...
        
        renderer.Clear(clearColor);
        scene.Render(renderer, litShader, camera);
        
        // ... UI ...
    }
}
```

---

## UI for Object Selection

Use ImGui (from [Chapter 9](09_DearImGui.md)) to select and edit objects:

```cpp
ui.StartWindow("Scene Objects");

static int selectedObject = 0;

// Object list
for (size_t i = 0; i < scene.Size(); i++)
{
    if (ImGui::Selectable(scene[i].Name.c_str(), selectedObject == (int)i))
        selectedObject = (int)i;
}

ImGui::Separator();

// Edit selected
if (selectedObject >= 0 && selectedObject < (int)scene.Size())
{
    auto& obj = scene[selectedObject];
    
    ImGui::Checkbox("Active", &obj.Active);
    ImGui::DragFloat3("Position", &obj.ObjectTransform.Position.x, 0.1f);
    ImGui::DragFloat3("Rotation", &obj.ObjectTransform.Rotation.x, 0.01f);
    ImGui::DragFloat3("Scale", &obj.ObjectTransform.Scale.x, 0.1f);
    ImGui::ColorEdit4("Color", &obj.Color.x);
    ImGui::SliderFloat("Roughness", &obj.Roughness, 0.0f, 1.0f);
    
    if (ImGui::Button("Delete"))
    {
        scene.Remove(selectedObject);
        selectedObject = std::min(selectedObject, (int)scene.Size() - 1);
    }
}

ImGui::Separator();

// Add buttons
if (ImGui::Button("Add Pyramid"))
    scene.Add(pyramidMesh, "Pyramid");
ImGui::SameLine();
if (ImGui::Button("Add Cube"))
    scene.Add(cubeMesh, "Cube");

ui.EndWindow();
```

---

## Shared vs Owned Resources

| Resource | Ownership | Why |
|----------|-----------|-----|
| Mesh | `shared_ptr` | Same geometry, multiple objects |
| Texture | `shared_ptr` | Same image, multiple objects |
| Transform | Owned | Unique per object |
| Color | Owned | Unique per object |

---

## Limitations

### The "God Struct" Problem

What happens as we add features?

```cpp
struct SceneObject
{
    // Rendering
    std::shared_ptr<Mesh> MeshPtr;
    Transform ObjectTransform;
    glm::vec4 Color;
    
    // Physics?
    glm::vec3 Velocity;
    float Mass;
    
    // AI?
    AIBehavior* Behavior;
    
    // Health?
    float Health;
    // ...keeps growing...
};
```

**Problems:**
- A static rock wastes memory with `Velocity`, `Health` fields
- Can't mix-and-match capabilities
- Querying is expensive

### This Is Fine (For Now)

For < 100 objects, this works. When you hit walls, it's time for ECS.

---

## Looking Ahead: ECS

Entity Component System separates concerns:

| Concept | Description |
|---------|-------------|
| **Entity** | Just an ID (integer) |
| **Component** | Pure data, no logic |
| **System** | Logic operating on components |

Libraries: **EnTT**, **Flecs**

We'll cover ECS in a future chapter.

---

## Key Takeaways

1. **SceneObject bundles render data** - Mesh + Transform + Color
2. **Share meshes, own transforms** - `shared_ptr<Mesh>` + unique `Transform`
3. **Scene manages collection** - Add, remove, iterate, render
4. **MVP per object** - Each object needs its own matrix
5. **Simple approach works for learning** - ECS comes later

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| All objects at same position | Shared transform | Each object needs own Transform |
| Crash on delete | Iterator invalidation | Use index-based loop |
| Object disappears | Wrong index after deletion | Update selectedObject index |

---

## Checkpoint

**Files:**
| File | Purpose |
|------|---------|
| `VizEngine/Core/SceneObject.h` | Object data bundle |
| `VizEngine/Core/Scene.h/.cpp` | Object collection manager |

**Checkpoint:** Create Scene class, populate with multiple objects, verify rendering and UI editing works.

---

## Exercise

1. Create a 5×5 grid of cubes with different colors
2. Add object naming and display in UI
3. Implement "duplicate object" button
4. Add animation - make pyramids rotate

---

> **Next:** [Chapter 13: Lighting](13_Lighting.md) - Blinn-Phong lighting.

> **Previous:** [Chapter 11: Camera System](11_CameraSystem.md)

