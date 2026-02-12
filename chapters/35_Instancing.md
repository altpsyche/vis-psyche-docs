\newpage

# Chapter 35: Instancing

Render hundreds or thousands of identical meshes in a single draw call by leveraging GPU instancing. By the end of this chapter, you will have a working instanced rendering pipeline that draws a 10x10 grid of cubes with one `glDrawElementsInstanced` call.

---

## The Draw Call Bottleneck

Every time you call `glDrawElements`, the CPU must validate state, push commands to the driver, and synchronize with the GPU. For a scene with one cube that is fine. For a forest of 10,000 trees, each requiring its own draw call, the CPU becomes the bottleneck long before the GPU breaks a sweat.

| Approach | Draw Calls for 100 Cubes | CPU Overhead |
|----------|--------------------------|--------------|
| Naive loop | 100 | High -- 100 state validations |
| Instancing | **1** | Minimal -- single validation |

> [!NOTE]
> The GPU is massively parallel and can shade millions of vertices per frame. The real cost of rendering many identical objects is usually on the **CPU side** -- preparing and issuing draw calls, not the shading itself.

Instancing solves this by telling the GPU: "Here is one mesh. Here are N transforms. Draw it N times in a single call." The per-instance data (model matrices, colors, etc.) is stored in a vertex buffer and read via vertex attributes, with `glVertexAttribDivisor` controlling how fast the attribute pointer advances.

---

## Theory

### glDrawElementsInstanced

The instanced variant of `glDrawElements` takes one additional parameter -- the **instance count**:

```cpp
glDrawElementsInstanced(GL_TRIANGLES, indexCount, GL_UNSIGNED_INT, nullptr, instanceCount);
```

The GPU executes the vertex shader `indexCount * instanceCount` times. Each invocation receives the built-in variable `gl_InstanceID` (0 to instanceCount-1), which you can use to index into per-instance data.

### glVertexAttribDivisor

By default, vertex attributes advance once per **vertex** (divisor = 0). Setting the divisor to 1 makes the attribute advance once per **instance** instead:

```cpp
glVertexAttribDivisor(attribIndex, 1);  // Advance once per instance
```

| Divisor | Behaviour |
|---------|-----------|
| 0 | Advance per vertex (default) |
| 1 | Advance per instance |
| N | Advance every N instances |

### Passing a mat4 as Vertex Attributes

A `mat4` is 16 floats, but a single vertex attribute slot can hold at most 4 floats (a `vec4`). The solution is to split the matrix across **4 consecutive attribute locations**, each carrying one column:

| Attribute Location | Data |
|-------------------|------|
| 6 | Column 0 (`vec4`) |
| 7 | Column 1 (`vec4`) |
| 8 | Column 2 (`vec4`) |
| 9 | Column 3 (`vec4`) |

In the vertex shader, you reconstruct the matrix:

```glsl
mat4 model = mat4(aInstanceModel0, aInstanceModel1,
                  aInstanceModel2, aInstanceModel3);
```

> [!IMPORTANT]
> You must call `glVertexAttribDivisor` on **each** of the 4 attribute locations (6, 7, 8, 9). Missing even one will cause that column to advance per-vertex instead of per-instance, producing scrambled transforms.

---

## Architecture Overview

The instancing pipeline touches four layers of the engine:

```
Renderer::DrawInstanced()          <-- Issues glDrawElementsInstanced
    |
VertexArray::LinkInstanceBuffer()  <-- Configures per-instance attributes + divisor
    |
VertexBuffer (instance VBO)        <-- Stores N x mat4 transforms
    |
instanced.shader                   <-- Reads per-instance model matrix at locations 6-9
```

The Sandbox demo generates a grid of transforms, uploads them to a VBO, links the VBO to the mesh's VAO with `LinkInstanceBuffer`, and renders the entire grid with a single `DrawInstanced` call.

---

## Step 1: DrawInstanced on Renderer

Add the instanced draw call to the `Renderer` class. It mirrors the existing `Draw` method but calls `glDrawElementsInstanced` with an instance count.

**Header (`Renderer.h`):**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.h

// =====================================================================
// Chapter 35: Instancing
// =====================================================================

void DrawInstanced(const VertexArray& va, const IndexBuffer& ib,
                   const Shader& shader, int instanceCount) const;
```

**Implementation (`Renderer.cpp`):**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.cpp

// =========================================================================
// Chapter 35: Instancing
// =========================================================================

void Renderer::DrawInstanced(const VertexArray& va, const IndexBuffer& ib,
                             const Shader& shader, int instanceCount) const
{
    shader.Bind();
    va.Bind();
    ib.Bind();

    glDrawElementsInstanced(GL_TRIANGLES, ib.GetCount(), GL_UNSIGNED_INT, nullptr, instanceCount);
}
```

The method is intentionally simple. It binds the shader, VAO, and IBO -- exactly like `Draw` -- but calls the instanced variant. The GPU uses the per-instance attribute data already configured on the VAO to differentiate each instance.

> [!TIP]
> Compare `Draw` and `DrawInstanced` side by side. The only difference is the final OpenGL call. All the instancing "magic" lives in the VAO configuration (Step 2) and the shader (Step 3).

---

## Step 2: LinkInstanceBuffer on VertexArray

The existing `LinkVertexBuffer` always starts attribute indices at 0 and uses a divisor of 0 (per-vertex). For instancing, you need to:

1. Start at an arbitrary attribute index (e.g., 6, after the mesh's own attributes)
2. Set `glVertexAttribDivisor` to 1 for each attribute

**Header (`VertexArray.h`):**

```cpp
// VizEngine/src/VizEngine/OpenGL/VertexArray.h

// Chapter 35: Links a per-instance VBO with glVertexAttribDivisor
void LinkInstanceBuffer(const VertexBuffer& instanceBuffer, const VertexBufferLayout& layout,
                        unsigned int startAttribIndex) const;
```

**Implementation (`VertexArray.cpp`):**

```cpp
// VizEngine/src/VizEngine/OpenGL/VertexArray.cpp

// Chapter 35: Links a per-instance VBO with glVertexAttribDivisor
void VertexArray::LinkInstanceBuffer(const VertexBuffer& instanceBuffer,
                                      const VertexBufferLayout& layout,
                                      unsigned int startAttribIndex) const
{
    Bind();
    instanceBuffer.Bind();
    const auto& elements = layout.GetElements();
    unsigned int offset = 0;
    for (unsigned int i = 0; i < elements.size(); i++)
    {
        unsigned int attribIndex = startAttribIndex + i;
        const auto& element = elements[i];
        glEnableVertexAttribArray(attribIndex);
        glVertexAttribPointer(attribIndex, element.count, element.type, element.normalised,
                              layout.GetStride(), reinterpret_cast<const void*>(static_cast<size_t>(offset)));
        glVertexAttribDivisor(attribIndex, 1);  // Advance once per instance
        offset += element.count * VertexBufferElement::GetSizeOfType(element.type);
    }
}
```

### How It Works

The method iterates through the layout elements (4 entries for a mat4, each with `count = 4` floats). For each element it:

1. **Enables** the attribute at `startAttribIndex + i`
2. **Configures** the pointer with the layout's stride and the running byte offset
3. **Sets the divisor to 1** so the attribute advances per-instance, not per-vertex

The stride for a `mat4` layout is `4 * 4 * sizeof(float) = 64 bytes`, which is exactly `sizeof(glm::mat4)`. Each column occupies 16 bytes within that stride.

> [!NOTE]
> The VAO remembers the divisor setting. Once you call `LinkInstanceBuffer`, the VAO is permanently configured for instancing on those attribute slots. You do not need to re-set the divisor before each draw call.

---

## Step 3: The Instanced Shader

The instanced shader reads per-vertex mesh data from locations 0-5 (position, normal, color, texcoords, tangent, bitangent) and per-instance model matrix data from locations 6-9. It applies basic Blinn-Phong lighting.

**Full shader (`instanced.shader`):**

```glsl
// VizEngine/src/resources/shaders/instanced.shader

#shader vertex
#version 460 core

// Chapter 35: Instanced rendering shader
// Per-vertex attributes (from mesh VBO)
layout(location = 0) in vec4 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec4 aColor;
layout(location = 3) in vec2 aTexCoords;
layout(location = 4) in vec3 aTangent;
layout(location = 5) in vec3 aBitangent;

// Per-instance attributes (from instance VBO, 4 vec4s = one mat4)
layout(location = 6) in vec4 aInstanceModel0;
layout(location = 7) in vec4 aInstanceModel1;
layout(location = 8) in vec4 aInstanceModel2;
layout(location = 9) in vec4 aInstanceModel3;

out vec3 v_WorldPos;
out vec3 v_Normal;
out vec2 v_TexCoords;

uniform mat4 u_View;
uniform mat4 u_Projection;

void main()
{
    // Reconstruct model matrix from per-instance attributes
    mat4 instanceModel = mat4(
        aInstanceModel0,
        aInstanceModel1,
        aInstanceModel2,
        aInstanceModel3
    );

    vec4 worldPos = instanceModel * aPos;
    v_WorldPos = worldPos.xyz;

    // Compute normal matrix from instance model (for uniform scaling this is sufficient)
    mat3 normalMatrix = mat3(instanceModel);
    v_Normal = normalize(normalMatrix * aNormal);

    v_TexCoords = aTexCoords;

    gl_Position = u_Projection * u_View * worldPos;
}


#shader fragment
#version 460 core

out vec4 FragColor;

in vec3 v_WorldPos;
in vec3 v_Normal;
in vec2 v_TexCoords;

// Simple directional lighting for instanced objects
uniform vec3 u_DirLightDirection;
uniform vec3 u_DirLightColor;
uniform vec3 u_ViewPos;
uniform vec3 u_ObjectColor;

void main()
{
    vec3 N = normalize(v_Normal);
    vec3 L = normalize(-u_DirLightDirection);
    vec3 V = normalize(u_ViewPos - v_WorldPos);
    vec3 H = normalize(V + L);

    // Ambient
    vec3 ambient = 0.15 * u_ObjectColor;

    // Diffuse (Lambertian)
    float diff = max(dot(N, L), 0.0);
    vec3 diffuse = diff * u_DirLightColor * u_ObjectColor;

    // Specular (Blinn-Phong for simplicity)
    float spec = pow(max(dot(N, H), 0.0), 32.0);
    vec3 specular = spec * u_DirLightColor * 0.3;

    vec3 color = ambient + diffuse + specular;
    FragColor = vec4(color, 1.0);
}
```

### Key Design Decisions

- **No `u_Model` uniform.** The model matrix comes from vertex attributes, not a uniform. This is the core of instancing -- each instance has its own transform without a separate uniform upload.
- **Normal matrix shortcut.** `mat3(instanceModel)` is only correct for uniform scaling (no shear). For non-uniform scaling you would need `transpose(inverse(mat3(instanceModel)))`, but computing that per-vertex is expensive. Uniform scaling is the common case for instanced objects.
- **Simplified lighting.** The instanced shader uses basic Blinn-Phong rather than the full PBR pipeline. This keeps the demo focused on the instancing technique itself.

> [!TIP]
> You can extend this shader to support per-instance colors by adding another attribute (e.g., `layout(location = 10) in vec3 aInstanceColor`) with its own `glVertexAttribDivisor(10, 1)` call. Just add another `Push<float>(3)` to the instance layout.

---

## Step 4: SetupInstancingDemo in the Sandbox

The demo creates a dedicated cube mesh, generates a 10x10 grid of transform matrices, uploads them to a VBO, and links that VBO to the mesh's VAO.

```cpp
// Sandbox/src/SandboxApp.cpp

void SetupInstancingDemo()
{
    // Create a dedicated cube mesh for instancing (separate VAO from scene cubes)
    m_InstancedCubeMesh = std::shared_ptr<VizEngine::Mesh>(VizEngine::Mesh::CreateCube().release());

    // Generate a grid of instance transforms
    const int gridSize = 10;
    m_InstanceCount = gridSize * gridSize;
    std::vector<glm::mat4> instanceMatrices(m_InstanceCount);

    float spacing = 3.0f;
    float offset = (gridSize - 1) * spacing * 0.5f;

    int index = 0;
    for (int z = 0; z < gridSize; z++)
    {
        for (int x = 0; x < gridSize; x++)
        {
            glm::mat4 model = glm::mat4(1.0f);
            model = glm::translate(model, glm::vec3(
                x * spacing - offset,
                5.0f,   // Elevated above scene
                z * spacing - offset
            ));
            instanceMatrices[index++] = model;
        }
    }

    // Create instance VBO with transform data
    m_InstanceVBO = std::make_unique<VizEngine::VertexBuffer>(
        instanceMatrices.data(),
        static_cast<unsigned int>(m_InstanceCount * sizeof(glm::mat4))
    );

    // Setup instance attributes on the dedicated cube mesh's VAO
    // mat4 = 4 x vec4 (locations 6, 7, 8, 9)
    VizEngine::VertexBufferLayout instanceLayout;
    instanceLayout.Push<float>(4);  // Column 0 (location 6)
    instanceLayout.Push<float>(4);  // Column 1 (location 7)
    instanceLayout.Push<float>(4);  // Column 2 (location 8)
    instanceLayout.Push<float>(4);  // Column 3 (location 9)

    m_InstancedCubeMesh->GetVertexArray().LinkInstanceBuffer(*m_InstanceVBO, instanceLayout, 6);

    VP_INFO("Instancing demo ready: {} instances ({}x{} grid)", m_InstanceCount, gridSize, gridSize);
}
```

### Walkthrough

1. **Dedicated mesh.** A separate cube mesh is created so the instancing attributes do not interfere with the normal scene cubes (which use the PBR shader at different attribute locations).

2. **Transform generation.** A nested loop produces a flat grid of `glm::mat4` identity matrices, each translated to a grid position. The grid is centered at the origin and elevated to `y = 5.0` so it floats above the scene's ground plane.

3. **VBO creation.** The `std::vector<glm::mat4>` is uploaded directly to a `VertexBuffer`. Since `glm::mat4` is 64 bytes of tightly-packed floats, the total upload is `100 * 64 = 6400 bytes`.

4. **Layout configuration.** Four `Push<float>(4)` calls describe the mat4 as four vec4 columns. The resulting stride is 64 bytes.

5. **LinkInstanceBuffer.** Starting at attribute index 6, this binds the instance VBO to the VAO and sets `glVertexAttribDivisor(attrib, 1)` on locations 6, 7, 8, and 9.

> [!IMPORTANT]
> The `startAttribIndex` of 6 must match the `layout(location = ...)` values in the instanced shader. Our mesh vertex format uses locations 0-5 (position, normal, color, texcoords, tangent, bitangent), so 6 is the first available slot.

The member variables supporting this demo are:

```cpp
// Sandbox/src/SandboxApp.cpp (member declarations)

// Chapter 35: Instancing
std::shared_ptr<VizEngine::Shader> m_InstancedShader;
std::shared_ptr<VizEngine::Mesh> m_InstancedCubeMesh;
std::unique_ptr<VizEngine::VertexBuffer> m_InstanceVBO;
int m_InstanceCount = 0;
bool m_ShowInstancingDemo = false;
glm::vec3 m_InstanceColor = glm::vec3(0.4f, 0.7f, 0.9f);  // Light blue
```

The shader is loaded during `OnCreate`:

```cpp
// Sandbox/src/SandboxApp.cpp (in OnCreate)

m_InstancedShader = std::make_shared<VizEngine::Shader>("resources/shaders/instanced.shader");
```

And `SetupInstancingDemo()` is called at the end of `OnCreate`:

```cpp
// =========================================================================
// Chapter 35: Instancing Demo Setup
// =========================================================================
SetupInstancingDemo();
```

---

## Step 5: Rendering the Instanced Grid in OnRender

During the main render pass (inside the HDR framebuffer), the instanced grid is drawn with a single `DrawInstanced` call when the user enables the demo.

```cpp
// Sandbox/src/SandboxApp.cpp (inside OnRender, within the HDR framebuffer pass)

// =========================================================================
// Chapter 35: Instancing Demo
// =========================================================================
if (m_ShowInstancingDemo && m_InstancedShader && m_InstancedCubeMesh && m_InstanceVBO)
{
    m_InstancedShader->Bind();
    m_InstancedShader->SetMatrix4fv("u_View", m_Camera.GetViewMatrix());
    m_InstancedShader->SetMatrix4fv("u_Projection", m_Camera.GetProjectionMatrix());
    m_InstancedShader->SetVec3("u_ViewPos", m_Camera.GetPosition());
    m_InstancedShader->SetVec3("u_DirLightDirection", m_Light.GetDirection());
    m_InstancedShader->SetVec3("u_DirLightColor", m_Light.Diffuse);
    m_InstancedShader->SetVec3("u_ObjectColor", m_InstanceColor);

    m_InstancedCubeMesh->Bind();
    renderer.DrawInstanced(
        m_InstancedCubeMesh->GetVertexArray(),
        m_InstancedCubeMesh->GetIndexBuffer(),
        *m_InstancedShader,
        m_InstanceCount
    );
}
```

### What Happens on the GPU

1. The vertex shader runs `indexCount * 100` times (once per vertex per instance).
2. For each invocation, `gl_InstanceID` determines which mat4 to read from the instance VBO. Because of `glVertexAttribDivisor(attrib, 1)`, all vertices within instance `i` read the same transform -- columns 6-9 from row `i` of the instance buffer.
3. Each vertex is transformed by its instance's model matrix, then by the shared view and projection matrices.
4. The fragment shader applies basic Blinn-Phong lighting using the same `u_ObjectColor` for all instances.

The ImGui panel in the "OpenGL Essentials" window lets you toggle the demo and change the instance color at runtime:

```cpp
// Sandbox/src/SandboxApp.cpp (inside OnImGuiRender)

// Chapter 35: Instancing
if (uiManager.CollapsingHeader("Instancing (Ch 35)"))
{
    uiManager.Checkbox("Show Instancing Demo", &m_ShowInstancingDemo);
    uiManager.ColorEdit3("Instance Color", &m_InstanceColor.x);
    if (m_ShowInstancingDemo)
    {
        uiManager.Text("Instances: %d cubes", m_InstanceCount);
        uiManager.Text("Drawn in 1 draw call");
    }
}
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| All instances render at the origin | `glVertexAttribDivisor` not set (divisor = 0) | Ensure `LinkInstanceBuffer` calls `glVertexAttribDivisor(attrib, 1)` for each of the 4 mat4 columns |
| Instances appear garbled/stretched | Attribute locations in shader do not match `startAttribIndex` | Verify shader `layout(location = 6..9)` matches the `startAttribIndex` of 6 passed to `LinkInstanceBuffer` |
| Only the first instance renders | Instance VBO not bound when setting up attributes | `LinkInstanceBuffer` must call `instanceBuffer.Bind()` before `glVertexAttribPointer` |
| Crash or no rendering | Wrong buffer size | Ensure VBO size is `instanceCount * sizeof(glm::mat4)`, not `instanceCount * sizeof(float)` |
| Normal matrix wrong for some instances | Non-uniform scale on instance transforms | Use `transpose(inverse(mat3(instanceModel)))` in the shader instead of `mat3(instanceModel)` |
| Scene cubes break after adding instancing | Instance attributes bound to shared VAO | Create a **dedicated** mesh for instancing so its VAO is separate from scene objects |

---

## Best Practices

| Guideline | Detail |
|-----------|--------|
| **Use instancing for 50+ identical objects** | Below ~50 objects, the overhead of setting up the instance buffer may not pay off versus a simple loop. Profile your specific case. |
| **Prefer static instance buffers** | If transforms do not change, create the VBO once with `GL_STATIC_DRAW`. For dynamic instances (particles, crowds), use `GL_DYNAMIC_DRAW` and `glBufferSubData`. |
| **Keep per-instance data minimal** | A mat4 (64 bytes) per instance is standard. Adding color (12 bytes) is fine. Avoid putting entire material descriptions per instance. |
| **Batch by mesh and material** | Instancing only works for objects sharing the same mesh and shader. Group objects by mesh type, then issue one instanced call per group. |
| **Consider frustum culling the instance buffer** | For very large instance counts (10,000+), rebuild or filter the instance buffer each frame to exclude off-screen instances. |
| **Attribute location planning** | Reserve a block of locations (e.g., 6-9) for instance data. Document this in your vertex format so future shaders do not collide. |

> [!TIP]
> For truly massive instance counts (100,000+), consider `glMultiDrawElementsIndirect` which batches multiple instanced draws into a single GPU command. That is beyond the scope of this chapter but builds directly on the concepts here.

---

## Milestone

**Part X: OpenGL Essentials -- Complete.**

Across Chapters 32-35 you have built:

| Chapter | Feature | Key OpenGL Concept |
|---------|---------|-------------------|
| 32 | Depth & Stencil Testing | `glStencilFunc`, `glStencilOp`, `glDepthFunc` |
| 33 | Blending & Transparency | `glBlendFunc`, back-to-front sorting |
| 34 | Normal Mapping | Tangent space, TBN matrix |
| **35** | **Instancing** | **`glDrawElementsInstanced`, `glVertexAttribDivisor`** |

You now have a solid command of the essential OpenGL techniques that sit between basic rendering and advanced effects. The engine can render lit scenes with shadows, outlines, transparency, surface detail, and efficiently batched geometry.

---

## What's Next

With OpenGL Essentials complete, we move into **Part XI: Physically Based Rendering**. In **Chapter 36: PBR Theory**, you will learn the physics behind the Cook-Torrance BRDF, the split-sum approximation, and how energy conservation produces realistic materials under any lighting condition.

> **Previous:** [Chapter 34: Normal Mapping](34_NormalMapping.md) | **Next:** [Chapter 36: PBR Theory](36_PBRTheory.md)
