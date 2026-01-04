\newpage

# Chapter 2: Hello Triangle

Get pixels on screen as fast as possible. This chapter creates a minimal OpenGL program—a single source file that renders a colored triangle.

> [!NOTE]
> This chapter intentionally uses "bad" practices (everything in one file, no abstractions) to get something working immediately. We'll refactor into proper architecture starting Chapter 3.

---

## What We're Building

A window displaying a pink triangle on a dark background. When you press Escape, the window closes.

**Why start here?**

- Instant gratification motivates learning
- Proves your environment works
- Introduces OpenGL concepts we'll abstract later

---

## Step 1: Download GLAD

GLAD loads OpenGL functions at runtime. We'll generate it from the web.

### Generate GLAD Files

1. Go to [glad.dav1d.de](https://glad.dav1d.de/)
2. Configure:
   - **Language:** C/C++
   - **Specification:** OpenGL
   - **API gl:** Version 4.6
   - **Profile:** Core
   - **Generate a loader:** ✓ (checked)
3. Click **Generate**
4. Download the ZIP file

### Extract Files

Create this structure and extract:

```
VizPsyche/
├── include/
│   ├── glad/
│   │   └── glad.h        ← From ZIP: include/glad/glad.h
│   └── KHR/
│       └── khrplatform.h ← From ZIP: include/KHR/khrplatform.h
└── src/
    └── glad.c            ← From ZIP: src/glad.c
```

---

## Step 2: Download GLFW

GLFW handles window creation and input.

### Download Pre-built Binaries

1. Go to [glfw.org/download](https://www.glfw.org/download.html)
2. Download **64-bit Windows binaries**
3. Extract to `VizPsyche/vendor/glfw-3.3.x/`

Your structure:

```
VizPsyche/
├── include/
│   ├── glad/
│   └── KHR/
├── src/
│   └── glad.c
└── vendor/
    └── glfw-3.3.9/
        ├── include/
        │   └── GLFW/
        │       └── glfw3.h
        └── lib-vc2022/
            ├── glfw3.lib
            └── glfw3dll.lib
```

> [!TIP]
> Note the exact path to `lib-vc2022` (or `lib-vc2019` depending on version). You'll need this for CMake.

---

## Step 3: Create CMakeLists.txt

**Create `VizPsyche/CMakeLists.txt`:**

```cmake
cmake_minimum_required(VERSION 3.16)
project(HelloTriangle LANGUAGES C CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# Find GLFW library (adjust path if different version)
set(GLFW_DIR ${CMAKE_SOURCE_DIR}/vendor/glfw-3.3.9)
set(GLFW_INCLUDE ${GLFW_DIR}/include)
set(GLFW_LIB ${GLFW_DIR}/lib-vc2022/glfw3.lib)

# Source files
set(SOURCES
    src/main.cpp
    src/glad.c
)

# Create executable
add_executable(HelloTriangle ${SOURCES})

# Include directories
target_include_directories(HelloTriangle PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${GLFW_INCLUDE}
)

# Link libraries
target_link_libraries(HelloTriangle PRIVATE
    ${GLFW_LIB}
    opengl32
)

# Windows-specific
if(WIN32)
    target_compile_definitions(HelloTriangle PRIVATE NOMINMAX)
endif()
```

---

## Step 4: Create main.cpp

This is the complete Hello Triangle program.

**Create `VizPsyche/src/main.cpp`:**

```cpp
// VizPsyche/src/main.cpp
// Hello Triangle - Minimal OpenGL Example

#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <iostream>

// Vertex shader source
const char* vertexShaderSource = R"(
#version 460 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;
out vec3 vertexColor;
void main()
{
    gl_Position = vec4(aPos, 1.0);
    vertexColor = aColor;
}
)";

// Fragment shader source
const char* fragmentShaderSource = R"(
#version 460 core
in vec3 vertexColor;
out vec4 FragColor;
void main()
{
    FragColor = vec4(vertexColor, 1.0);
}
)";

// Callback for window resize
void framebufferSizeCallback(GLFWwindow* window, int width, int height)
{
    glViewport(0, 0, width, height);
}

// Compile shader and check for errors
unsigned int compileShader(unsigned int type, const char* source)
{
    unsigned int shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    
    // Check for errors
    int success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        char infoLog[512];
        glGetShaderInfoLog(shader, 512, nullptr, infoLog);
        std::cerr << "Shader compilation error:\n" << infoLog << std::endl;
    }
    return shader;
}

// Create shader program from vertex and fragment shaders
unsigned int createShaderProgram()
{
    unsigned int vertexShader = compileShader(GL_VERTEX_SHADER, vertexShaderSource);
    unsigned int fragmentShader = compileShader(GL_FRAGMENT_SHADER, fragmentShaderSource);
    
    unsigned int program = glCreateProgram();
    glAttachShader(program, vertexShader);
    glAttachShader(program, fragmentShader);
    glLinkProgram(program);
    
    // Check for errors
    int success;
    glGetProgramiv(program, GL_LINK_STATUS, &success);
    if (!success)
    {
        char infoLog[512];
        glGetProgramInfoLog(program, 512, nullptr, infoLog);
        std::cerr << "Shader linking error:\n" << infoLog << std::endl;
    }
    
    // Clean up individual shaders (no longer needed after linking)
    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);
    
    return program;
}

int main()
{
    // =========================================================================
    // Initialize GLFW
    // =========================================================================
    if (!glfwInit())
    {
        std::cerr << "Failed to initialize GLFW" << std::endl;
        return -1;
    }
    
    // Request OpenGL 4.6 Core Profile
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    
    // =========================================================================
    // Create Window
    // =========================================================================
    GLFWwindow* window = glfwCreateWindow(800, 600, "Hello Triangle", nullptr, nullptr);
    if (!window)
    {
        std::cerr << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebufferSizeCallback);
    
    // =========================================================================
    // Load OpenGL Functions via GLAD
    // =========================================================================
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
    {
        std::cerr << "Failed to initialize GLAD" << std::endl;
        return -1;
    }
    
    std::cout << "OpenGL Version: " << glGetString(GL_VERSION) << std::endl;
    
    // =========================================================================
    // Create Shader Program
    // =========================================================================
    unsigned int shaderProgram = createShaderProgram();
    
    // =========================================================================
    // Define Triangle Vertices (Position + Color)
    // =========================================================================
    float vertices[] = {
        // Position          // Color (RGB)
        -0.5f, -0.5f, 0.0f,  1.0f, 0.4f, 0.7f,  // Bottom left  - pink
         0.5f, -0.5f, 0.0f,  1.0f, 0.6f, 0.8f,  // Bottom right - light pink
         0.0f,  0.5f, 0.0f,  1.0f, 0.2f, 0.5f,  // Top center   - magenta
    };
    
    // =========================================================================
    // Create Vertex Array Object (VAO) and Vertex Buffer Object (VBO)
    // =========================================================================
    unsigned int VAO, VBO;
    glGenVertexArrays(1, &VAO);
    glGenBuffers(1, &VBO);
    
    // Bind VAO first
    glBindVertexArray(VAO);
    
    // Bind and fill VBO
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
    
    // Configure vertex attributes
    // Attribute 0: Position (3 floats)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    
    // Attribute 1: Color (3 floats, offset by 3 floats)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);
    
    // Unbind (optional, for safety)
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
    
    // =========================================================================
    // Render Loop
    // =========================================================================
    while (!glfwWindowShouldClose(window))
    {
        // Input: Close on Escape
        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        {
            glfwSetWindowShouldClose(window, true);
        }
        
        // Clear screen with dark gray
        glClearColor(0.1f, 0.1f, 0.12f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        
        // Draw triangle
        glUseProgram(shaderProgram);
        glBindVertexArray(VAO);
        glDrawArrays(GL_TRIANGLES, 0, 3);
        
        // Swap buffers and poll events
        glfwSwapBuffers(window);
        glfwPollEvents();
    }
    
    // =========================================================================
    // Cleanup
    // =========================================================================
    glDeleteVertexArrays(1, &VAO);
    glDeleteBuffers(1, &VBO);
    glDeleteProgram(shaderProgram);
    glfwTerminate();
    
    return 0;
}
```

---

## Step 5: Build and Run

### Generate Build Files

```bash
cd C:\dev\VizPsyche
cmake -B build -G "Visual Studio 17 2022"
```

### Build

```bash
cmake --build build --config Debug
```

### Run

```bash
.\build\bin\Debug\HelloTriangle.exe
```

---

## Expected Result

A window titled "Hello Triangle" displays a pink gradient triangle on a dark background.

- Press **Escape** to close
- Console shows: `OpenGL Version: 4.6.0 ...`

---

## What Just Happened?

| Code Section | Purpose |
|--------------|---------|
| `glfwInit()` | Initialize GLFW library |
| `glfwCreateWindow()` | Create window with OpenGL context |
| `gladLoadGLLoader()` | Load OpenGL function pointers |
| `glGenBuffers()` | Create GPU buffer for vertex data |
| `glVertexAttribPointer()` | Describe vertex data layout |
| `glDrawArrays()` | Tell GPU to render triangles |

We'll explain these in depth in later chapters. For now, celebrate—you've rendered your first pixels!

---

## Project Structure After This Chapter

```
VizPsyche/
├── .git/
├── .gitignore
├── CMakeLists.txt
├── build/                    ← Generated (gitignored)
├── include/
│   ├── glad/
│   │   └── glad.h
│   └── KHR/
│       └── khrplatform.h
├── src/
│   ├── glad.c
│   └── main.cpp
└── vendor/
    └── glfw-3.3.9/
        ├── include/
        └── lib-vc2022/
```

---

## Commit Your Progress

```bash
git add .
git commit -m "Chapter 2: Hello Triangle renders"
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "Cannot find glfw3.lib" | Wrong GLFW path in CMake | Check `GLFW_DIR` matches your extracted folder |
| Black window, no triangle | Shader error | Check console for compilation errors |
| "Failed to initialize GLAD" | Context not created | Ensure `glfwMakeContextCurrent()` called before GLAD |
| Window immediately closes | Missing render loop | Ensure `while (!glfwWindowShouldClose)` loop exists |

---

## Milestone

**Milestone: First Pixels Rendered**

You have:
- GLAD and GLFW integrated
- CMake build working
- A colored triangle rendering
- Basic input handling (Escape to close)

---

## What's Next

This single-file approach doesn't scale. In **Chapter 3**, we'll restructure into a proper engine/application architecture with:

- VizEngine (DLL library)
- Sandbox (uses the engine)
- Git submodules for dependencies

> **Next:** [Chapter 3: Project Structure](03_ProjectStructure.md)

> **Previous:** [Chapter 1: Environment Setup](01_EnvironmentSetup.md)
