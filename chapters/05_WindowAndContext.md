\newpage

# Chapter 5: Window & Context

Refactor the OpenGL window setup from `Application.cpp` into a dedicated `GLFWManager` class. This separation makes the code cleaner and prepares for future features like resize callbacks.

---

## What We're Building

A `GLFWManager` class that handles:

- GLFW initialization and window creation
- Framebuffer resize callbacks
- Input processing (basic Escape key)
- Buffer swapping and event polling

---

## Step 1: Create OpenGL Directory

```bash
mkdir VizEngine/src/VizEngine/OpenGL
```

---

## Step 2: Create GLFWManager.h

**Create `VizEngine/src/VizEngine/OpenGL/GLFWManager.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/GLFWManager.h

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
        GLFWManager(unsigned int width, unsigned int height, const std::string& title);
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

## Step 3: Create GLFWManager.cpp

**Create `VizEngine/src/VizEngine/OpenGL/GLFWManager.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/GLFWManager.cpp

#include "GLFWManager.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    GLFWManager::GLFWManager(unsigned int width, unsigned int height, const std::string& title)
        : m_Window(nullptr)
    {
        Init(width, height, title);
    }

    GLFWManager::~GLFWManager()
    {
        Shutdown();
    }

    void GLFWManager::Init(unsigned int width, unsigned int height, const std::string& title)
    {
        // Initialize GLFW
        if (!glfwInit())
        {
            VP_CORE_CRITICAL("Failed to initialize GLFW!");
            return;
        }
        VP_CORE_TRACE("GLFW initialized");

        // OpenGL version hints
        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

        // Create window
        m_Window = glfwCreateWindow(width, height, title.c_str(), nullptr, nullptr);
        if (!m_Window)
        {
            VP_CORE_CRITICAL("Failed to create GLFW window!");
            glfwTerminate();
            return;
        }

        VP_CORE_INFO("Window created: {}x{} - '{}'", width, height, title);

        // Make context current
        glfwMakeContextCurrent(m_Window);

        // Set callbacks
        glfwSetFramebufferSizeCallback(m_Window, FramebufferSizeCallback);
        glfwSetKeyCallback(m_Window, KeyCallback);
    }

    void GLFWManager::Shutdown()
    {
        if (m_Window)
        {
            glfwDestroyWindow(m_Window);
            m_Window = nullptr;
        }
        glfwTerminate();
        VP_CORE_TRACE("GLFW terminated");
    }

    void GLFWManager::ProcessInput()
    {
        // Basic input: Escape to close
        if (glfwGetKey(m_Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        {
            glfwSetWindowShouldClose(m_Window, true);
        }
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
        VP_CORE_TRACE("Framebuffer resized: {}x{}", width, height);
    }

    void GLFWManager::KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods)
    {
        (void)window;
        (void)scancode;
        (void)mods;

        if (action == GLFW_PRESS)
        {
            VP_CORE_TRACE("Key pressed: {}", key);
        }
    }

}  // namespace VizEngine
```

---

## Step 4: Create Commons.h

A shared header for OpenGL includes.

**Create `VizEngine/src/VizEngine/OpenGL/Commons.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Commons.h

#pragma once

#include <glad/glad.h>
#include <GLFW/glfw3.h>
```

---

## Step 5: Create ErrorHandling

OpenGL debug output for catching errors.

**Create `VizEngine/src/VizEngine/OpenGL/ErrorHandling.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/ErrorHandling.h

#pragma once

#include "VizEngine/Core.h"

namespace VizEngine
{
    namespace ErrorHandling
    {
        VizEngine_API void HandleErrors();
    }
}
```

**Create `VizEngine/src/VizEngine/OpenGL/ErrorHandling.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/ErrorHandling.cpp

#include "ErrorHandling.h"
#include "Commons.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    namespace ErrorHandling
    {
        static void APIENTRY GLDebugCallback(
            GLenum source, GLenum type, GLuint id, GLenum severity,
            GLsizei length, const GLchar* message, const void* userParam)
        {
            (void)length;
            (void)userParam;

            if (severity == GL_DEBUG_SEVERITY_NOTIFICATION)
                return;

            const char* sourceStr = "Unknown";
            switch (source)
            {
                case GL_DEBUG_SOURCE_API: sourceStr = "API"; break;
                case GL_DEBUG_SOURCE_SHADER_COMPILER: sourceStr = "Shader"; break;
            }

            switch (severity)
            {
                case GL_DEBUG_SEVERITY_HIGH:
                    VP_CORE_ERROR("[GL {} {}] ({}): {}", sourceStr, type, id, message);
                    break;
                case GL_DEBUG_SEVERITY_MEDIUM:
                    VP_CORE_WARN("[GL {} {}] ({}): {}", sourceStr, type, id, message);
                    break;
                default:
                    VP_CORE_TRACE("[GL {} {}] ({}): {}", sourceStr, type, id, message);
                    break;
            }
        }

        void HandleErrors()
        {
            glEnable(GL_DEBUG_OUTPUT);
            glEnable(GL_DEBUG_OUTPUT_SYNCHRONOUS);
            glDebugMessageCallback(GLDebugCallback, nullptr);
            glDebugMessageControl(GL_DONT_CARE, GL_DONT_CARE, GL_DEBUG_SEVERITY_NOTIFICATION, 0, nullptr, GL_FALSE);
            VP_CORE_TRACE("OpenGL debug output enabled");
        }
    }
}
```

---

## Step 6: Update CMakeLists.txt

Add the new OpenGL files.

```cmake
set(VIZENGINE_SOURCES
    src/VizEngine/Application.cpp
    src/VizEngine/Log.cpp
    # OpenGL
    src/VizEngine/OpenGL/ErrorHandling.cpp
    src/VizEngine/OpenGL/GLFWManager.cpp
    src/VizEngine/OpenGL/glad.c
)

set(VIZENGINE_HEADERS
    src/VizEngine.h
    src/VizEngine/Application.h
    src/VizEngine/Core.h
    src/VizEngine/EntryPoint.h
    src/VizEngine/Log.h
    # OpenGL
    src/VizEngine/OpenGL/Commons.h
    src/VizEngine/OpenGL/ErrorHandling.h
    src/VizEngine/OpenGL/GLFWManager.h
    include/glad/glad.h
    include/KHR/khrplatform.h
)
```

---

## Step 7: Update Application.cpp

Use `GLFWManager` in `Application::Run`:

```cpp
#include "OpenGL/GLFWManager.h"
#include "OpenGL/ErrorHandling.h"

int Application::Run()
{
    // Create window (constructor initializes everything)
    GLFWManager window(1280, 720, "VizPsyche Engine");

    // Load OpenGL functions (after context is current)
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
    {
        VP_CORE_CRITICAL("Failed to initialize GLAD!");
        return -1;
    }

    VP_CORE_INFO("OpenGL {}", (const char*)glGetString(GL_VERSION));

    // Enable features
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glEnable(GL_DEPTH_TEST);

    // Enable debug output
    ErrorHandling::HandleErrors();

    // Main loop
    while (!window.WindowShouldClose())
    {
        window.ProcessInput();

        glClearColor(0.1f, 0.1f, 0.15f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        // Rendering goes here

        window.SwapBuffersAndPollEvents();
    }

    return 0;
}
```

> [!NOTE]
> `Application::Run` returns `int` to allow error codes. The constructor of `GLFWManager` handles all initialization—no separate `Init()` call needed.

---

## Step 8: Build and Run

```bash
cmake --build build --config Debug
.\build\bin\Debug\Sandbox.exe
```

---

## Expected Output

```
[HH:MM:SS] [VizEngine] [info] VizEngine initialized
[HH:MM:SS] [VizEngine] [trace] GLFW initialized
[HH:MM:SS] [VizEngine] [info] Window created: 1280x720 - 'VizPsyche Engine'
[HH:MM:SS] [VizEngine] [info] OpenGL 4.6.0 NVIDIA ...
[HH:MM:SS] [VizEngine] [trace] OpenGL debug output enabled
```

Window displays. Press Escape to close.

---

## Project Structure After This Chapter

```
VizEngine/src/VizEngine/OpenGL/
├── Commons.h
├── ErrorHandling.cpp
├── ErrorHandling.h
├── GLFWManager.cpp
├── GLFWManager.h
└── glad.c
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "GLFWManager.h not found" | Include path wrong | Use `"VizEngine/OpenGL/GLFWManager.h"` |
| Window opens and closes | `ProcessInput()` not called | Ensure loop calls `ProcessInput()` |
| No debug messages | Driver doesn't support | Check OpenGL 4.3+ |

---

## Milestone

**Clean Window Management**

You have:
- `GLFWManager` class wrapping GLFW
- Constructor does all initialization
- Framebuffer resize handling
- OpenGL debug output enabled

---

## What's Next

In **Chapter 6**, we'll learn the fundamental concepts of OpenGL—the graphics pipeline, shaders, buffers, and how they work together.

> **Next:** [Chapter 6: OpenGL Fundamentals](06_OpenGLFundamentals.md)

> **Previous:** [Chapter 4: Logging System](04_LoggingSystem.md)
