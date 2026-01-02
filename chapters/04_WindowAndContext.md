\newpage

# Chapter 4: Window & Context

Every graphical application needs a window to display in and an OpenGL context to render with. Our `GLFWManager` class wraps GLFW to handle both, plus input handling.

## What is an OpenGL Context?

An **OpenGL context** is like a "connection" to the GPU. All OpenGL state (bound buffers, current shader, etc.) belongs to a context. Without one, OpenGL functions fail.

Think of it like a database connection:
- You can't run SQL without connecting first
- You can't call `glDrawElements()` without a context

GLFW creates both the window AND the context together.

---

## Creating the GLFWManager Class

We need a wrapper class that handles window creation, context setup, input, and cleanup.

Create **`VizEngine/src/VizEngine/OpenGL/GLFWManager.h`**:

```cpp
#pragma once
#include <iostream>
#include <string>
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include "VizEngine/Core.h"

namespace VizEngine
{
    class VizEngine_API GLFWManager
    {
    public:
        GLFWManager(unsigned int width, unsigned int height, 
                    const std::string& title);
        ~GLFWManager();

        void ProcessInput();
        bool WindowShouldClose();
        void SwapBuffersAndPollEvents();
        GLFWwindow* GetWindow() const;

    private:
        GLFWwindow* m_Window;
        static void FramebufferSizeCallback(GLFWwindow* window, int width, int height);
        static void KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods);
        void Init(unsigned int width, unsigned int height, const std::string& title);
        void Shutdown();
    };
}
```

---

## Implementing GLFWManager

Create **`VizEngine/src/VizEngine/OpenGL/GLFWManager.cpp`**:

```cpp
#include "GLFWManager.h"
#include "VizEngine/Log.h"
#include <glad/glad.h>
#include <GLFW/glfw3.h>

namespace VizEngine
{
    GLFWManager::GLFWManager(unsigned int width, unsigned int height,
                             const std::string& title)
    {
        // Step 1: Initialize GLFW
        if (!glfwInit()) {
            VP_CORE_ERROR("Failed to initialize GLFW");
            return;
        }
        
        // Step 2: Set window hints
        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
        
        // Step 3: Create window
        m_Window = glfwCreateWindow(width, height, title.c_str(), 
                                    nullptr, nullptr);
        if (!m_Window) {
            VP_CORE_ERROR("Failed to create GLFW window");
            glfwTerminate();
            return;
        }
        
        // Step 4: Make context current
        glfwMakeContextCurrent(m_Window);
        
        // Step 5: Load OpenGL functions via GLAD
        if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
            VP_CORE_ERROR("Failed to initialize GLAD");
            return;
        }
        
        // Step 6: Set callbacks
        glfwSetFramebufferSizeCallback(m_Window, FramebufferSizeCallback);
        glfwSetKeyCallback(m_Window, KeyCallback);
    }

    GLFWManager::~GLFWManager()
    {
        glfwDestroyWindow(m_Window);
        glfwTerminate();
    }

    void GLFWManager::ProcessInput()
    {
        if (glfwGetKey(m_Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            glfwSetWindowShouldClose(m_Window, true);
    }

    bool GLFWManager::WindowShouldClose()
    {
        return glfwWindowShouldClose(m_Window);
    }

    void GLFWManager::SwapBuffersAndPollEvents()
    {
        glfwSwapBuffers(m_Window);
        glfwPollEvents();
    }

    GLFWwindow* GLFWManager::GetWindow() const
    {
        return m_Window;
    }

    void GLFWManager::FramebufferSizeCallback(GLFWwindow* window, int width, int height)
    {
        (void)window;
        glViewport(0, 0, width, height);
    }

    void GLFWManager::KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods)
    {
        (void)window; (void)scancode; (void)mods;
        if (key == GLFW_KEY_F1 && action == GLFW_PRESS)
        {
            // Toggle help menu (placeholder)
        }
    }
}
```

### Understanding Window Hints

Before creating the window, we tell GLFW what kind of OpenGL context we want:

| Hint | Values | Purpose |
|------|--------|---------|
| `CONTEXT_VERSION_MAJOR/MINOR` | 4.6, 3.3, etc. | OpenGL version |
| `OPENGL_PROFILE` | `CORE` / `COMPAT` | Core removes deprecated features |
| `OPENGL_DEBUG_CONTEXT` | `TRUE` / `FALSE` | Enables error callbacks |
| `RESIZABLE` | `TRUE` / `FALSE` | Can user resize window? |

---

## Using GLFWManager in Your Application

Update **`Application.cpp`** to create a window and render loop:

```cpp
#include "Application.h"
#include "VizEngine/OpenGL/GLFWManager.h"

namespace VizEngine
{
    int Application::Run()
    {
        GLFWManager window(1280, 720, "VizPsyche");
        
        while (!window.WindowShouldClose())
        {
            window.ProcessInput();
            
            // Clear the screen
            glClearColor(0.1f, 0.1f, 0.2f, 1.0f);
            glClear(GL_COLOR_BUFFER_BIT);
            
            // Swap and poll
            window.SwapBuffersAndPollEvents();
        }
        
        return 0;
    }
}
```

Add the files to **`VizEngine/CMakeLists.txt`**:

```cmake
add_library(VizEngine SHARED
    src/VizEngine/OpenGL/GLFWManager.cpp
    src/VizEngine/OpenGL/glad.c
    # ... other files
)
```

Rebuild and run. A dark blue window appears and stays open!

---

## Framebuffer Callback: Handling Resize

When the user resizes the window, the framebuffer callback updates the OpenGL viewport:

```cpp
void GLFWManager::FramebufferSizeCallback(GLFWwindow* window, int width, int height)
{
    (void)window;
    glViewport(0, 0, width, height);
}
```

### Why Framebuffer, Not Window?

On high-DPI displays (Retina, 4K), the framebuffer size differs from window size:

| Display | Window Size | Framebuffer Size |
|---------|-------------|------------------|
| Regular | 800×600 | 800×600 |
| Retina (2x) | 800×600 | 1600×1200 |

OpenGL renders to the **framebuffer**, so we use framebuffer callbacks.

---

## Input Handling

### Polling (Continuous Input)

For movement and other continuous input, poll each frame:

```cpp
void GLFWManager::ProcessInput()
{
    if (glfwGetKey(m_Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(m_Window, true);
}
```

### Callbacks (Single Events)

For events that should trigger once per press:

```cpp
void GLFWManager::KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods)
{
    if (key == GLFW_KEY_F1 && action == GLFW_PRESS)
    {
        // Toggle help menu
    }
}
```

| Action | Meaning |
|--------|---------|
| `GLFW_PRESS` | Key was just pressed |
| `GLFW_RELEASE` | Key was just released |
| `GLFW_REPEAT` | Key is held (repeat events) |

---

## The Main Loop Pattern

```cpp
while (!window.WindowShouldClose())
{
    // 1. Input
    window.ProcessInput();
    
    // 2. Update (game logic)
    UpdateGame(deltaTime);
    
    // 3. Render
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    RenderScene();
    
    // 4. Swap and poll
    window.SwapBuffersAndPollEvents();
}
```

This is the standard game loop order: **Input → Update → Render → Present**.

---

## RAII: Automatic Cleanup

Our `GLFWManager` follows RAII (Resource Acquisition Is Initialization):

- **Constructor** initializes GLFW and creates the window
- **Destructor** destroys the window and terminates GLFW

```cpp
{
    GLFWManager window(800, 600, "Test");
    // ... use window
}  // Destructor called automatically, cleans up
```

No need to call cleanup manually — the destructor handles it.

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "proc-address" crash | GLAD not initialized | Call `gladLoadGLLoader(...)` after making context current |
| `glfwInit()` returns false | GLFW already initialized or lib missing | Check console for error messages |
| Window opens then crashes | GLAD not initialized | Call `gladLoadGLLoader(...)` after context |
| Nothing appears | VSync + slow code = no frame | Check `glfwSwapInterval()` setting |

---

## Checkpoint

- Created `GLFWManager.h` with class declaration  
- Created `GLFWManager.cpp` with implementation  
- Updated `Application::Run()` with render loop  
- Added files to CMakeLists.txt  

**Verify:** Rebuild and run — a dark blue window appears and stays open.

---

## Exercise

1. Modify `GLFWManager` to support fullscreen mode (pass a monitor to `glfwCreateWindow`)
2. Add a callback to print window size whenever it changes
3. Add mouse position callback and log the coordinates
4. Try disabling VSync - do you see any tearing?

---

> **Next:** [Chapter 5: Logging System](05_LoggingSystem.md) - How we track what's happening in the engine.
