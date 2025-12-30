\newpage

# Chapter 6: OpenGL Fundamentals

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
    std::cout << "Failed to initialize GLAD" << std::endl;
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
    // Position (x,y,z,w)    Color (r,g,b,a)       TexCoord (u,v)
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
// [Position: 4 floats][Color: 4 floats][TexCoord: 2 floats]
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

// Attribute 2: TexCoord
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
layout (location = 1) in vec4 vertColor;  // From attribute 1
layout (location = 2) in vec2 texCoord;   // From attribute 2

out vec4 v_VertColor;    // Pass to fragment shader
out vec2 v_TexCoord;

uniform mat4 u_MVP;      // Model-View-Projection matrix

void main()
{
    gl_Position = u_MVP * aPos;   // Transform position
    v_VertColor = vertColor;      // Pass through
    v_TexCoord = texCoord;
}
```

### Fragment Shader

Runs once per pixel. Determines final color:

```glsl
#version 460 core

out vec4 FragColor;           // Output: pixel color

in vec4 v_VertColor;          // From vertex shader
in vec2 v_TexCoord;

uniform vec4 u_Color;         // Tint color
uniform sampler2D u_MainTex;  // Texture

void main()
{
    vec4 textureColor = texture(u_MainTex, v_TexCoord);
    vec3 combinedColor = v_VertColor.rgb * u_Color.rgb * textureColor.rgb;
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

## Exercise

1. Change the clear color in `glClearColor()` and see the result
2. Try drawing with `GL_LINES` instead of `GL_TRIANGLES`
3. Modify the fragment shader to output a solid red color

---

> **Next:** [Chapter 7: Abstractions](07_Abstractions.md) - Wrapping OpenGL in clean C++ classes.

> **Reference:** For a complete list of all OpenGL wrapper classes and their methods, see [Appendix A: Code Reference](A_Reference.md#opengl).



