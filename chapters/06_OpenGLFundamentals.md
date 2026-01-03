\newpage

# Chapter 6: OpenGL Fundamentals

Before we abstract OpenGL into clean C++ classes, we need to understand what's happening at the GPU level. This chapter explains the core concepts that power everything we'll build.

> [!NOTE]
> This chapter is conceptual. No new files are created—we're building understanding. Implementation starts in Chapter 8.

---

## The CPU-GPU Divide

Your computer has two processors:

| Processor | Good At | Memory |
|-----------|---------|--------|
| **CPU** | Sequential tasks, branching, complex logic | RAM (fast access) |
| **GPU** | Parallel tasks, same operation on many items | VRAM (separate from RAM) |

Rendering means:
1. CPU prepares data and commands
2. Data is uploaded to GPU memory (VRAM)
3. GPU processes data in parallel
4. Result appears on screen

**Key insight:** Data transfer between CPU and GPU is slow. Minimize it by uploading once, then referencing.

---

## The Graphics Pipeline

When you call `glDrawArrays()` or `glDrawElements()`, data flows through this pipeline:

```
Vertex Data (in VRAM)
       │
       ▼
┌──────────────────┐
│  Vertex Shader   │  ← Runs once per vertex (programmable)
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Primitive Assembly│  ← Groups vertices into triangles
└──────────────────┘
       │
       ▼
┌──────────────────┐
│   Rasterization  │  ← Converts triangles to fragments (pixels)
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Fragment Shader  │  ← Runs once per fragment (programmable)
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  Tests & Blend   │  ← Depth test, blending, stencil
└──────────────────┘
       │
       ▼
    Framebuffer (screen)
```

### What You Control

- **Vertex Shader** — Written in GLSL, transforms vertex positions
- **Fragment Shader** — Written in GLSL, determines pixel colors

Everything else is handled by the GPU hardware.

---

## Buffers: GPU Memory

A **buffer** is a block of GPU memory. We use three types:

### Vertex Buffer Object (VBO)

Stores vertex data: positions, colors, texture coordinates, normals.

```cpp
float vertices[] = {
    // Position (x,y,z)    Color (r,g,b)
    -0.5f, -0.5f, 0.0f,    1.0f, 0.0f, 0.0f,
     0.5f, -0.5f, 0.0f,    0.0f, 1.0f, 0.0f,
     0.0f,  0.5f, 0.0f,    0.0f, 0.0f, 1.0f,
};

unsigned int VBO;
glGenBuffers(1, &VBO);
glBindBuffer(GL_ARRAY_BUFFER, VBO);
glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
```

### Index Buffer Object (IBO / EBO)

Stores indices that reference vertices. Avoids duplicating shared vertices.

```cpp
// A quad (two triangles) shares 2 vertices
unsigned int indices[] = {
    0, 1, 2,  // First triangle
    2, 3, 0   // Second triangle (shares vertices 0 and 2)
};

unsigned int IBO;
glGenBuffers(1, &IBO);
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, IBO);
glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indices), indices, GL_STATIC_DRAW);
```

### Vertex Array Object (VAO)

Stores the *configuration* of vertex attributes. It remembers:
- Which VBO is bound
- How to interpret the vertex data (layout)
- Which IBO is bound

```cpp
unsigned int VAO;
glGenVertexArrays(1, &VAO);
glBindVertexArray(VAO);

// Now configure attributes...
// VAO remembers this configuration
```

---

## Vertex Attributes

Vertices have **attributes**: position, color, normals, texture coordinates, etc.

We tell OpenGL how to interpret the raw bytes:

```cpp
// Attribute 0: Position (3 floats, offset 0)
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
glEnableVertexAttribArray(0);

// Attribute 1: Color (3 floats, offset 3 floats)
glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
glEnableVertexAttribArray(1);
```

**Parameters explained:**

| Parameter | Meaning |
|-----------|---------|
| Index | Attribute location (matches shader `layout(location = X)`) |
| Size | Number of components (3 for vec3) |
| Type | Data type (GL_FLOAT) |
| Normalized | Convert to 0-1 range (usually false) |
| Stride | Bytes between consecutive vertices |
| Offset | Byte offset to this attribute within the vertex |

---

## Shaders

Shaders are programs that run on the GPU, written in **GLSL** (OpenGL Shading Language).

### Vertex Shader

Runs once per vertex. Main job: transform position to clip space.

```glsl
#version 460 core

layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;

out vec3 vertexColor;  // Pass to fragment shader

uniform mat4 u_MVP;    // Model-View-Projection matrix

void main()
{
    gl_Position = u_MVP * vec4(aPos, 1.0);
    vertexColor = aColor;
}
```

### Fragment Shader

Runs once per pixel. Main job: determine the final color.

```glsl
#version 460 core

in vec3 vertexColor;   // From vertex shader
out vec4 FragColor;    // Final output

void main()
{
    FragColor = vec4(vertexColor, 1.0);
}
```

### Shader Compilation

```cpp
// 1. Create shader
unsigned int vertexShader = glCreateShader(GL_VERTEX_SHADER);

// 2. Attach source
glShaderSource(vertexShader, 1, &vertexShaderSource, nullptr);

// 3. Compile
glCompileShader(vertexShader);

// 4. Check for errors
int success;
glGetShaderiv(vertexShader, GL_COMPILE_STATUS, &success);
if (!success) {
    char infoLog[512];
    glGetShaderInfoLog(vertexShader, 512, nullptr, infoLog);
    // Handle error
}

// 5. Create program and link
unsigned int program = glCreateProgram();
glAttachShader(program, vertexShader);
glAttachShader(program, fragmentShader);
glLinkProgram(program);

// 6. Use program
glUseProgram(program);
```

---

## Uniforms

**Uniforms** are global variables you set from C++ that all shader invocations can read.

Common uniforms:
- `u_MVP` — Transformation matrix
- `u_Color` — Object color
- `u_Time` — Animation time
- `u_Texture` — Texture sampler

```cpp
// Get location (cache this!)
int location = glGetUniformLocation(program, "u_MVP");

// Set value
glUniformMatrix4fv(location, 1, GL_FALSE, glm::value_ptr(mvp));
```

---

## Coordinate Systems

A vertex passes through multiple coordinate spaces:

```
Local Space (model coordinates)
       │  × Model Matrix
       ▼
World Space (scene coordinates)
       │  × View Matrix
       ▼
View Space (camera-relative)
       │  × Projection Matrix
       ▼
Clip Space (normalized device coordinates)
       │  (GPU perspective divide)
       ▼
Screen Space (pixel coordinates)
```

The **MVP matrix** combines all three transformations:

```cpp
glm::mat4 model = glm::translate(glm::mat4(1.0f), position);
glm::mat4 view = glm::lookAt(cameraPos, target, up);
glm::mat4 projection = glm::perspective(glm::radians(45.0f), aspect, 0.1f, 100.0f);

glm::mat4 MVP = projection * view * model;  // Order matters!
```

---

## The Draw Call

Finally, we tell OpenGL to render:

```cpp
glBindVertexArray(VAO);                    // Bind configuration
glUseProgram(shaderProgram);               // Use shader

// Non-indexed drawing
glDrawArrays(GL_TRIANGLES, 0, 3);          // 3 vertices

// Indexed drawing (preferred)
glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);  // 6 indices
```

---

## State Machine

OpenGL is a **state machine**. Functions modify global state:

```cpp
glBindBuffer(GL_ARRAY_BUFFER, VBO);    // VBO is now "current"
glBindVertexArray(VAO);                // VAO is now "current"
glUseProgram(shader);                  // Shader is now "current"
```

Subsequent calls operate on whatever is currently bound. This is why we "bind before use."

---

## Summary

| Concept | Purpose |
|---------|---------|
| **VBO** | Stores vertex data in GPU memory |
| **IBO** | Stores indices to avoid vertex duplication |
| **VAO** | Stores vertex attribute configuration |
| **Vertex Shader** | Transforms vertex positions |
| **Fragment Shader** | Determines pixel colors |
| **Uniforms** | Pass data from C++ to shaders |
| **MVP Matrix** | Transforms from local to clip space |

---

## What's Next

In **Chapter 7**, we'll learn about RAII and C++ patterns for safely managing these OpenGL resources.

> **Next:** [Chapter 7: RAII & Resource Management](07_RAIIAndResourceManagement.md)

> **Previous:** [Chapter 5: Window & Context](05_WindowAndContext.md)
