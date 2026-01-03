\newpage

# Chapter 4: DLL Architecture

Create a reusable DLL engine with export macros and an Application base class.

---

## Why a DLL?

| Benefit | Explanation |
|---------|-------------|
| **Separation** | Engine vs. game code are distinct |
| **Fast iteration** | Rebuild only what changed |
| **Reusability** | Multiple apps can use same engine |
| **Clear API** | Only exported symbols are public |

---

## Step 1: Create VizEngine CMakeLists.txt

**Create `VizEngine/CMakeLists.txt`:**

```cmake
project(VizEngine)

# Source Files
set(VIZENGINE_SOURCES
    src/VizEngine/Application.cpp
    src/glad.c
)

set(VIZENGINE_HEADERS
    src/VizEngine.h
    src/VizEngine/Application.h
    src/VizEngine/Core.h
    src/VizEngine/EntryPoint.h
    include/glad/glad.h
    include/KHR/khrplatform.h
)

# DLL Target
add_library(VizEngine SHARED
    ${VIZENGINE_SOURCES}
    ${VIZENGINE_HEADERS}
)

# Include Directories
target_include_directories(VizEngine
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/vendor/glm>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/vendor/glfw/include
)

# Export Macros
target_compile_definitions(VizEngine
    PUBLIC
        $<$<PLATFORM_ID:Windows>:VP_PLATFORM_WINDOWS>
    PRIVATE
        VP_BUILD_DLL
        _CRT_SECURE_NO_WARNINGS
)

# Warnings
if(MSVC)
    target_compile_options(VizEngine PRIVATE /W4 /utf-8 /wd4251 /wd4275)
endif()

# Link Libraries
target_link_libraries(VizEngine
    PRIVATE glfw $<$<PLATFORM_ID:Windows>:opengl32>
)
```

---

## Step 2: Create Core.h (Export Macros)

**Create `VizEngine/src/VizEngine/Core.h`:**

```cpp
// VizEngine/src/VizEngine/Core.h

#pragma once

#ifdef VP_PLATFORM_WINDOWS
    #ifdef VP_BUILD_DLL
        #define VizEngine_API __declspec(dllexport)
    #else
        #define VizEngine_API __declspec(dllimport)
    #endif
#else
    #error VizEngine only supports Windows!
#endif
```

---

## Step 3: Create Application Class

**Create `VizEngine/src/VizEngine/Application.h`:**

```cpp
// VizEngine/src/VizEngine/Application.h

#pragma once

#include "Core.h"

namespace VizEngine
{
    class VizEngine_API Application
    {
    public:
        Application();
        virtual ~Application();
        int Run();
    };

    // Users implement this factory function
    Application* CreateApplication();

}  // namespace VizEngine
```

**Create `VizEngine/src/VizEngine/Application.cpp`:**

```cpp
// VizEngine/src/VizEngine/Application.cpp

#include "Application.h"
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <iostream>

namespace VizEngine
{
    Application::Application()
    {
        std::cout << "[VizEngine] Application created" << std::endl;
    }

    Application::~Application()
    {
        std::cout << "[VizEngine] Application destroyed" << std::endl;
    }

    int Application::Run()
    {
        std::cout << "[VizEngine] Running..." << std::endl;

        if (!glfwInit())
        {
            std::cerr << "[VizEngine] Failed to initialize GLFW" << std::endl;
            return -1;
        }

        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

        GLFWwindow* window = glfwCreateWindow(1280, 720, "VizEngine", nullptr, nullptr);
        if (!window)
        {
            std::cerr << "[VizEngine] Failed to create window" << std::endl;
            glfwTerminate();
            return -1;
        }
        glfwMakeContextCurrent(window);

        if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
        {
            std::cerr << "[VizEngine] Failed to initialize GLAD" << std::endl;
            return -1;
        }

        std::cout << "[VizEngine] OpenGL " << glGetString(GL_VERSION) << std::endl;

        while (!glfwWindowShouldClose(window))
        {
            if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
                glfwSetWindowShouldClose(window, true);

            glClearColor(0.1f, 0.1f, 0.15f, 1.0f);
            glClear(GL_COLOR_BUFFER_BIT);

            glfwSwapBuffers(window);
            glfwPollEvents();
        }

        glfwTerminate();
        std::cout << "[VizEngine] Shutdown complete" << std::endl;
        return 0;
    }

}  // namespace VizEngine
```

---

## Step 4: Create EntryPoint.h

**Create `VizEngine/src/VizEngine/EntryPoint.h`:**

```cpp
// VizEngine/src/VizEngine/EntryPoint.h

#pragma once

#include "Application.h"

extern VizEngine::Application* VizEngine::CreateApplication();

int main(int argc, char** argv)
{
    (void)argc;
    (void)argv;

    auto app = VizEngine::CreateApplication();
    int result = app->Run();
    delete app;

    return result;
}
```

---

## Step 5: Create VizEngine.h (Public Header)

**Create `VizEngine/src/VizEngine.h`:**

```cpp
// VizEngine/src/VizEngine.h

#pragma once

#include "VizEngine/Application.h"

// EntryPoint defines main() - include LAST
#include "VizEngine/EntryPoint.h"
```

---

## Step 6: Create Sandbox CMakeLists.txt

**Create `Sandbox/CMakeLists.txt`:**

```cmake
project(Sandbox)

set(SANDBOX_SOURCES src/SandboxApp.cpp)

add_executable(Sandbox ${SANDBOX_SOURCES})

target_link_libraries(Sandbox PRIVATE VizEngine)

# Copy DLL
if(WIN32)
    add_custom_command(TARGET Sandbox POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:VizEngine>
            $<TARGET_FILE_DIR:Sandbox>
    )
endif()
```

---

## Step 7: Create SandboxApp.cpp

**Create `Sandbox/src/SandboxApp.cpp`:**

```cpp
// Sandbox/src/SandboxApp.cpp

#include <VizEngine.h>

class Sandbox : public VizEngine::Application
{
public:
    Sandbox() {}
    ~Sandbox() {}
};

VizEngine::Application* VizEngine::CreateApplication()
{
    return new Sandbox();
}
```

---

## Step 8: Build and Run

```bash
cd C:\dev\VizPsyche
cmake -B build -G "Visual Studio 17 2022"
cmake --build build --config Debug
.\build\bin\Debug\Sandbox.exe
```

Expected output:

```
[VizEngine] Application created
[VizEngine] Running...
[VizEngine] OpenGL 4.6.0 ...
```

Press Escape to close.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      Sandbox.exe                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ SandboxApp.cpp                                       │ │
│  │   - #include <VizEngine.h>                           │ │
│  │   - class Sandbox : public Application               │ │
│  │   - CreateApplication() returns new Sandbox()        │ │
│  └─────────────────────────────────────────────────────┘ │
│                           │ links to                     │
│                           ▼                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                   VizEngine.dll                      │ │
│  │   - Application base class (exported)                │ │
│  │   - OpenGL/GLFW initialization                       │ │
│  │   - Window + render loop                             │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| "VizEngine.dll not found" | Check post-build copy command |
| "unresolved external" | Add `VizEngine_API` to class |
| Submodule empty | `git submodule update --init` |

---

## Milestone

**Engine Architecture Established**

You have:
- VizEngine as a DLL
- Export/import macros
- Application base class
- EntryPoint abstraction
- Sandbox linking to engine

---

## What's Next

In **Chapter 5**, we'll add a proper logging system with spdlog.

> **Next:** [Chapter 5: Logging System](05_LoggingSystem.md)

> **Previous:** [Chapter 3: Project Structure](03_ProjectStructure.md)
