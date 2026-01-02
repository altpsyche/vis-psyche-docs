\newpage

# Chapter 6: OpenGL Fundamentals

## Before We Begin: What Actually Happens When You Render?

When you call `glDrawElements()`, a complex dance occurs between your CPU and GPU:

```
Your C++ Code (CPU)
      │
      ▼
OpenGL Driver (translates commands)
      │
      ▼
GPU Command Queue
      │
      ▼
GPU Reads Vertex Data from Buffers
      │
      ▼
Vertex Shader (runs per vertex)
      │
      ▼
Rasterizer (turns triangles into pixels)
      │
      ▼
Fragment Shader (runs per pixel)
      │
      ▼
Pixels appear on screen!
```

**Why buffers?** The GPU can't directly read your C++ variables. You must explicitly upload data to GPU memory. That's what buffers are for.

**Why shaders?** The GPU doesn't know how to transform or color your vertices. You write small programs (shaders) that tell it exactly what to do.

This chapter teaches you to set up each piece. By the end, you'll understand the full flow.

---

## Hello Triangle: Your First Pixel on Screen

Before building abstractions, here is the **absolute minimum** needed to render pixels. This is the "Hello World" of graphics programming.

> **Note:** This code is intentionally ugly - raw OpenGL with no wrappers. We'll clean it up in [Chapter 7: Abstractions](07_Abstractions.md). The goal here is understanding, not elegance.

### The 3-Vertex Triangle

```cpp
// Three vertices, position only (x, y, z)
float vertices[] = {
    -0.5f, -0.5f, 0.0f,   // bottom-left
     0.5f, -0.5f, 0.0f,   // bottom-right
     0.0f,  0.5f, 0.0f    // top-center
};
```

### Minimal Shaders (Hardcoded)

```cpp
const char* vertexShaderSource = R"(
    #version 460 core
    layout (location = 0) in vec3 aPos;
    void main() {
        gl_Position = vec4(aPos, 1.0);
    }
)";

const char* fragmentShaderSource = R"(
    #version 460 core
    out vec4 FragColor;
    void main() {
        FragColor = vec4(1.0, 0.4, 0.7, 1.0);  // Pink!
    }
)";
```

### The Minimal Setup (Raw OpenGL)

```cpp
// 1. Create and compile shaders
unsigned int vertexShader = glCreateShader(GL_VERTEX_SHADER);
glShaderSource(vertexShader, 1, &vertexShaderSource, NULL);
glCompileShader(vertexShader);

unsigned int fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
glShaderSource(fragmentShader, 1, &fragmentShaderSource, NULL);
glCompileShader(fragmentShader);

// 2. Link into a program
unsigned int shaderProgram = glCreateProgram();
glAttachShader(shaderProgram, vertexShader);
glAttachShader(shaderProgram, fragmentShader);
glLinkProgram(shaderProgram);
glDeleteShader(vertexShader);
glDeleteShader(fragmentShader);

// 3. Create VAO and VBO
unsigned int VAO, VBO;
glGenVertexArrays(1, &VAO);
glGenBuffers(1, &VBO);

glBindVertexArray(VAO);
glBindBuffer(GL_ARRAY_BUFFER, VBO);
glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);

glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
glEnableVertexAttribArray(0);

// 4. Draw!
glUseProgram(shaderProgram);
glBindVertexArray(VAO);
glDrawArrays(GL_TRIANGLES, 0, 3);
```

**If you see a pink triangle, OpenGL is working!**

This is ~30 lines of raw OpenGL. The following sections explain what each piece does, then wrap it all in clean C++ classes.

---

## What is OpenGL?

OpenGL is a **graphics API** - a set of functions that talk to your GPU. It's:
- Cross-platform (Windows, Mac, Linux)
- Low-level (close to hardware)
- State-machine based (we'll explain this)

### The Graphics Pipeline

When you want to draw something, data flows through a pipeline:

![OpenGL Graphics Pipeline](images/06-graphics-pipeline.png)

1. **Your Data** - Vertices (points in 3D space)
2. **Vertex Shader** - Runs for each vertex, transforms positions
3. **Rasterization** - Converts triangles to pixels
4. **Fragment Shader** - Runs for each pixel, determines color
5. **Screen** - Final image displayed

---

## Setting Up OpenGL

### GLFW - Window & Context

OpenGL doesn't create windows - it just renders. We use **GLFW** for:
- Creating windows
- Creating OpenGL context (the "connection" to GPU)
- Handling input

```cpp
// Initialize GLFW
glfwInit();

// Set OpenGL version (4.6 Core Profile)
glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

// Create window with OpenGL context
GLFWwindow* window = glfwCreateWindow(800, 800, "VizPsyche", NULL, NULL);
glfwMakeContextCurrent(window);
```

For details on window and context setup, see [Chapter 4: Window & Context](04_WindowAndContext.md).

### GLAD - Function Loading

OpenGL functions aren't directly available on Windows. **GLAD** loads them:

```cpp
// After creating context, load OpenGL functions
if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
{
    VP_CORE_ERROR("Failed to initialize GLAD");
    return -1;
}
```

Now we can call `glClear()`, `glDrawElements()`, etc.

---

## Buffers: Getting Data to the GPU

The GPU can't read your C++ variables directly. You need **buffers**.

### Vertex Buffer Object (VBO)

Stores vertex data on the GPU:

```cpp
float vertices[] = {
    // Position (x,y,z,w)    Color (r,g,b,a)       TexCoords (u,v)
    -0.5f, 0.0f, 0.5f, 1.0f,  1.0f, 1.0f, 1.0f, 1.0f,  0.0f, 0.0f,
    // ... more vertices
};

unsigned int VBO;
glGenBuffers(1, &VBO);                          // Create buffer ID
glBindBuffer(GL_ARRAY_BUFFER, VBO);             // "Select" this buffer
glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
```

- `glGenBuffers` - Ask OpenGL for a buffer ID (just a number)
- `glBindBuffer` - Make this buffer "active" (OpenGL is a state machine!)
- `glBufferData` - Upload data to GPU

### Index Buffer Object (IBO/EBO)

Instead of repeating vertices, use indices:

```cpp
// A square has 4 vertices but 2 triangles (6 points)
// Without indices: 6 vertices with duplicate data
// With indices: 4 vertices + 6 indices

unsigned int indices[] = {
    0, 1, 2,   // First triangle
    0, 2, 3    // Second triangle (shares vertices 0 and 2)
};

unsigned int IBO;
glGenBuffers(1, &IBO);
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, IBO);
glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indices), indices, GL_STATIC_DRAW);
```

### Vertex Array Object (VAO)

Remembers the buffer configuration:

```cpp
unsigned int VAO;
glGenVertexArrays(1, &VAO);
glBindVertexArray(VAO);

// Now configure vertex attributes...
// (This configuration is stored in the VAO)
```

---

## Vertex Attributes

The GPU needs to know how to interpret your vertex data.

```cpp
// Our vertex layout:
// [Position: 4 floats][Color: 4 floats][TexCoords: 2 floats]
// Total: 10 floats per vertex = 40 bytes

// Attribute 0: Position
glEnableVertexAttribArray(0);
glVertexAttribPointer(0,           // Attribute index
                      4,           // Number of components (vec4)
                      GL_FLOAT,    // Data type
                      GL_FALSE,    // Normalize?
                      40,          // Stride (bytes between vertices)
                      (void*)0);   // Offset to this attribute

// Attribute 1: Color
glEnableVertexAttribArray(1);
glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 40, (void*)16);  // Offset: 4 floats * 4 bytes

// Attribute 2: TexCoords
glEnableVertexAttribArray(2);
glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 40, (void*)32);  // Offset: 8 floats * 4 bytes
```

---

## Shaders: GPU Programs

Shaders are programs that run on the GPU.

> **Our Custom Format:** We combine vertex and fragment shaders in one `.shader` file,
> separated by `#shader vertex` and `#shader fragment` markers. This is NOT standard 
> OpenGL - it's our engine's convention for convenience. Our `Shader` class parses 
> this format.

### Vertex Shader

Runs once per vertex. Transforms positions:

```glsl
#version 460 core

layout (location = 0) in vec4 aPos;       // From attribute 0
layout (location = 1) in vec4 aColor;     // From attribute 1
layout (location = 2) in vec2 aTexCoords; // From attribute 2

out vec4 v_Color;        // Pass to fragment shader
out vec2 v_TexCoords;

uniform mat4 u_MVP;      // Model-View-Projection matrix

void main()
{
    gl_Position = u_MVP * aPos;   // Transform position
    v_Color = aColor;
    v_TexCoords = aTexCoords;
}
```

### Fragment Shader

Runs once per pixel. Determines final color:

```glsl
#version 460 core

out vec4 FragColor;           // Output: pixel color

in vec4 v_Color;
in vec2 v_TexCoords;

uniform vec4 u_Color;         // Tint color
uniform sampler2D u_MainTex;  // Texture

void main()
{
    vec4 textureColor = texture(u_MainTex, v_TexCoords);
    vec3 combinedColor = v_Color.rgb * u_Color.rgb * textureColor.rgb;
    FragColor = vec4(combinedColor, textureColor.a);
}
```

### Compiling Shaders

```cpp
// Create shader objects
unsigned int vertexShader = glCreateShader(GL_VERTEX_SHADER);
glShaderSource(vertexShader, 1, &vertexCode, NULL);
glCompileShader(vertexShader);

unsigned int fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
glShaderSource(fragmentShader, 1, &fragmentCode, NULL);
glCompileShader(fragmentShader);

// Link into program
unsigned int program = glCreateProgram();
glAttachShader(program, vertexShader);
glAttachShader(program, fragmentShader);
glLinkProgram(program);

// Use the program
glUseProgram(program);
```

---

## Uniforms: Sending Data to Shaders

Uniforms are shader variables you set from C++:

```cpp
// Get uniform location (cached for performance)
int location = glGetUniformLocation(program, "u_MVP");

// Set the value
glUniformMatrix4fv(location, 1, GL_FALSE, &matrix[0][0]);
```

Common uniform types:
- `glUniform1f(loc, float)` - Single float
- `glUniform4f(loc, x, y, z, w)` - vec4
- `glUniformMatrix4fv(loc, 1, GL_FALSE, ptr)` - mat4

---

## Drawing

Finally, to draw:

```cpp
glBindVertexArray(VAO);          // Use this vertex configuration
glUseProgram(shaderProgram);     // Use this shader

// Draw indexed triangles
glDrawElements(GL_TRIANGLES,     // Mode: triangles
               indexCount,        // Number of indices
               GL_UNSIGNED_INT,   // Index type
               nullptr);          // Offset (0 = start)
```

---

## The OpenGL State Machine

OpenGL remembers what's "bound" (selected):

```cpp
glBindBuffer(GL_ARRAY_BUFFER, VBO1);  // VBO1 is now active
glBufferData(...);                     // Operates on VBO1

glBindBuffer(GL_ARRAY_BUFFER, VBO2);  // Now VBO2 is active
glBufferData(...);                     // Operates on VBO2

glBindBuffer(GL_ARRAY_BUFFER, 0);     // Nothing bound (safe state)
```

This is why we have Bind/Unbind methods in our classes!

---

## Coordinate Systems

Understanding how vertices get from your 3D model to 2D pixels is crucial:

```
┌──────────────┐   Model   ┌──────────────┐   View   ┌──────────────┐
│ Object Space │  Matrix   │ World Space  │  Matrix  │  View Space  │
│   (Local)    │ ───────►  │              │ ───────► │   (Camera)   │
│ Your vertices│           │ In the world │          │ Relative to  │
│ around origin│           │              │          │   camera     │
└──────────────┘           └──────────────┘          └──────────────┘
                                                            │
                                                            │ Projection
                                                            │   Matrix
                                                            ▼
                           ┌──────────────┐          ┌──────────────┐
                           │ Screen Space │ ◄─────── │ Clip Space   │
                           │  (Pixels)    │  OpenGL  │ (-1 to +1)   │
                           │              │  handles │              │
                           └──────────────┘          └──────────────┘
```

### Object Space (Local)
- Vertices defined relative to object center
- Our pyramid: tip at (0, 0.8, 0)

### World Space
- Object placed in the world
- Model matrix transforms Local → World

### View Space (Camera)
- World relative to camera
- View matrix transforms World → View

### Clip Space
- After projection
- Projection matrix transforms View → Clip

### Screen Space
- Final 2D pixels
- OpenGL handles Clip → Screen

```cpp
// The MVP matrix combines all transforms:
glm::mat4 MVP = Projection * View * Model;

// In shader:
gl_Position = u_MVP * aPos;
```

---

## Key Takeaways

1. **Buffers store GPU data** - VBO for vertices, IBO for indices, VAO for configuration
2. **Shaders are GPU programs** - Vertex transforms positions, Fragment colors pixels
3. **Uniforms pass data to shaders** - Matrices, colors, textures
4. **OpenGL is a state machine** - Bind before operating
5. **MVP transforms coordinates** - Model → World → View → Clip → Screen

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Black screen (nothing drawn) | VAO not bound before draw | `glBindVertexArray(vao)` before `glDrawElements` |
| Shader compilation error | Typo in GLSL | Check `glGetShaderInfoLog()` output |
| Triangle is white | Shader not linked/used | Call `glUseProgram(shaderProgram)` |
| Triangle appears upside-down | Y-axis mismatch | Check projection matrix or flip Y |
| Crash on `glDrawElements` | Invalid index buffer | Ensure indices are in valid range |

---

## Checkpoint

This chapter covered OpenGL fundamentals:

**Key Concepts:**
- **VBO** — Stores vertex data on GPU
- **IBO** — Stores triangle indices
- **VAO** — Stores vertex attribute configuration
- **Shaders** — Vertex (position) + Fragment (color)
- **MVP** — Model × View × Projection for transforms

**The Pipeline:**
```
CPU Data → VBO → Vertex Shader → Rasterizer → Fragment Shader → Pixels
```

**Checkpoint:** Copy the Hello Triangle code into `Application::Run()`, rebuild, and verify an orange/pink triangle appears.

---

## Exercise

1. Change the clear color in `glClearColor()` and see the result
2. Try drawing with `GL_LINES` instead of `GL_TRIANGLES`
3. Modify the fragment shader to output a solid red color

---

> **Next:** [Chapter 7: Abstractions](07_Abstractions.md) - Wrapping OpenGL in clean C++ classes.

> **Reference:** For a complete list of all OpenGL wrapper classes and their methods, see [Appendix A: Code Reference](A_Reference.md#opengl).



