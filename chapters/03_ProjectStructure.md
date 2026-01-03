\newpage

# Chapter 3: Project Structure & DLL Architecture

Time to refactor our single-file Hello Triangle into a proper engine architecture. By the end of this chapter, you'll have:

- **VizEngine** — A reusable DLL library
- **Sandbox** — An application that uses the engine
- **Git submodules** — For managing dependencies

---

## Why This Architecture?

| Benefit | Explanation |
|---------|-------------|
| **Separation of concerns** | Engine code vs. game code are distinct |
| **Faster iteration** | Change engine → rebuild DLL → app picks it up |
| **Reusability** | Multiple games can use the same engine |
| **Clear API** | Only exported symbols are public |

---

## Step 1: Restructure Directories

Clean up the Hello Triangle structure and create the engine layout.

### Create Directory Structure

```bash
cd C:\dev\VizPsyche

# Create engine directories
mkdir -p VizEngine/src/VizEngine
mkdir -p VizEngine/include
mkdir -p VizEngine/vendor

# Create application directory
mkdir -p Sandbox/src

# Move GLAD to engine
move include VizEngine/include
move src/glad.c VizEngine/src/glad.c
```

After restructuring:

```
VizPsyche/
├── VizEngine/
│   ├── include/
│   │   ├── glad/
│   │   │   └── glad.h
│   │   └── KHR/
│   │       └── khrplatform.h
│   ├── src/
│   │   ├── VizEngine/          ← Engine source files go here
│   │   └── glad.c
│   └── vendor/                 ← Third-party libraries
├── Sandbox/
│   └── src/                    ← Application source files
├── vendor/                     ← Can be deleted (we moved GLFW)
└── CMakeLists.txt              ← Root build file
```

---

## Step 2: Set Up Git Submodules

Instead of manually downloading libraries, we use Git submodules.

### Add GLFW Submodule

```bash
cd C:\dev\VizPsyche
git submodule add https://github.com/glfw/glfw.git VizEngine/vendor/glfw
```

### Add GLM Submodule (Math Library)

```bash
git submodule add https://github.com/g-truc/glm.git VizEngine/vendor/glm
```

### Add spdlog Submodule (Logging)

```bash
git submodule add https://github.com/gabime/spdlog.git VizEngine/vendor/spdlog
```

### Verify Submodules

```bash
git submodule status
```

Should show three submodules.

> [!TIP]
> When cloning this repo later, use:
> ```bash
> git clone --recursive <repo-url>
> ```
> Or if already cloned:
> ```bash
> git submodule update --init --recursive
> ```

---

## Step 3: Create Root CMakeLists.txt

**Replace `VizPsyche/CMakeLists.txt` with:**

```cmake
# VizPsyche/CMakeLists.txt

cmake_minimum_required(VERSION 3.16)
project(VizPsyche VERSION 1.0.0 LANGUAGES C CXX)

# =============================================================================
# C++ Standard
# =============================================================================
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# =============================================================================
# Output Directories
# =============================================================================
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# =============================================================================
# Platform Configuration
# =============================================================================
if(WIN32)
    add_definitions(-DNOMINMAX)
    add_definitions(-DUNICODE -D_UNICODE)
endif()

# =============================================================================
# Git Submodules (auto-update)
# =============================================================================
find_package(Git QUIET)
if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
    option(GIT_SUBMODULE "Update submodules during build" ON)
    if(GIT_SUBMODULE)
        message(STATUS "Updating git submodules...")
        execute_process(
            COMMAND ${GIT_EXECUTABLE} submodule update --init --recursive
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
            RESULT_VARIABLE GIT_SUBMOD_RESULT
        )
        if(NOT GIT_SUBMOD_RESULT EQUAL "0")
            message(WARNING "git submodule update failed: ${GIT_SUBMOD_RESULT}")
        endif()
    endif()
endif()

# =============================================================================
# GLFW Configuration
# =============================================================================
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_INSTALL OFF CACHE BOOL "" FORCE)

# =============================================================================
# Subdirectories
# =============================================================================
add_subdirectory(VizEngine/vendor/glfw)
add_subdirectory(VizEngine)
add_subdirectory(Sandbox)

# =============================================================================
# IDE Configuration
# =============================================================================
set_property(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY VS_STARTUP_PROJECT Sandbox)
set_property(GLOBAL PROPERTY USE_FOLDERS ON)
set_target_properties(glfw PROPERTIES FOLDER "Dependencies")

# =============================================================================
# Configuration Summary
# =============================================================================
message(STATUS "")
message(STATUS "=== VizPsyche Configuration ===")
message(STATUS "  Version:      ${PROJECT_VERSION}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Generator:    ${CMAKE_GENERATOR}")
message(STATUS "")
```

---

## Step 4: Create VizEngine CMakeLists.txt

**Create `VizPsyche/VizEngine/CMakeLists.txt`:**

```cmake
# VizEngine/CMakeLists.txt

project(VizEngine)

# =============================================================================
# Source Files
# =============================================================================
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

# =============================================================================
# Library Target (DLL)
# =============================================================================
add_library(VizEngine SHARED
    ${VIZENGINE_SOURCES}
    ${VIZENGINE_HEADERS}
)

# Group files in IDE
source_group("Source Files" FILES ${VIZENGINE_SOURCES})
source_group("Header Files" FILES ${VIZENGINE_HEADERS})

# =============================================================================
# Include Directories
# =============================================================================
target_include_directories(VizEngine
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/vendor/glm>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/vendor/glfw/include
)

# =============================================================================
# Compile Definitions
# =============================================================================
target_compile_definitions(VizEngine
    PUBLIC
        $<$<PLATFORM_ID:Windows>:VP_PLATFORM_WINDOWS>
    PRIVATE
        VP_BUILD_DLL
        _CRT_SECURE_NO_WARNINGS
)

# =============================================================================
# Compiler Warnings
# =============================================================================
if(MSVC)
    target_compile_options(VizEngine PRIVATE
        /W4
        /utf-8
        /wd4251
        /wd4275
    )
else()
    target_compile_options(VizEngine PRIVATE
        -Wall -Wextra -Wpedantic
    )
endif()

# =============================================================================
# Link Libraries
# =============================================================================
target_link_libraries(VizEngine
    PRIVATE
        glfw
        $<$<PLATFORM_ID:Windows>:opengl32>
)
```

---

## Step 5: Create Core.h (Export Macros)

The DLL needs to export symbols. We use macros to handle this.

**Create `VizPsyche/VizEngine/src/VizEngine/Core.h`:**

```cpp
// VizEngine/src/VizEngine/Core.h

#pragma once

// =============================================================================
// Platform Detection
// =============================================================================
#ifdef VP_PLATFORM_WINDOWS
    // ==========================================================================
    // DLL Export/Import
    // ==========================================================================
    #ifdef VP_BUILD_DLL
        // Building the DLL: export symbols
        #define VizEngine_API __declspec(dllexport)
    #else
        // Using the DLL: import symbols
        #define VizEngine_API __declspec(dllimport)
    #endif
#else
    #error VizEngine only supports Windows!
#endif
```

---

## Step 6: Create Application Base Class

**Create `VizPsyche/VizEngine/src/VizEngine/Application.h`:**

```cpp
// VizEngine/src/VizEngine/Application.h

#pragma once

#include "Core.h"

namespace VizEngine
{
    /// @brief Base class for all VizEngine applications.
    /// Users derive from this and implement their game logic.
    class VizEngine_API Application
    {
    public:
        Application();
        virtual ~Application();

        /// @brief Main application loop. Called by EntryPoint.
        void Run();
    };

    /// @brief Factory function that users must implement.
    /// Create and return your Application subclass here.
    Application* CreateApplication();

}  // namespace VizEngine
```

**Create `VizPsyche/VizEngine/src/VizEngine/Application.cpp`:**

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

    void Application::Run()
    {
        std::cout << "[VizEngine] Running..." << std::endl;

        // Initialize GLFW
        if (!glfwInit())
        {
            std::cerr << "[VizEngine] Failed to initialize GLFW" << std::endl;
            return;
        }

        // OpenGL hints
        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

        // Create window
        GLFWwindow* window = glfwCreateWindow(1280, 720, "VizEngine", nullptr, nullptr);
        if (!window)
        {
            std::cerr << "[VizEngine] Failed to create window" << std::endl;
            glfwTerminate();
            return;
        }
        glfwMakeContextCurrent(window);

        // Load OpenGL functions
        if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
        {
            std::cerr << "[VizEngine] Failed to initialize GLAD" << std::endl;
            return;
        }

        std::cout << "[VizEngine] OpenGL " << glGetString(GL_VERSION) << std::endl;

        // Main loop
        while (!glfwWindowShouldClose(window))
        {
            // Input
            if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            {
                glfwSetWindowShouldClose(window, true);
            }

            // Render
            glClearColor(0.1f, 0.1f, 0.15f, 1.0f);
            glClear(GL_COLOR_BUFFER_BIT);

            // Swap and poll
            glfwSwapBuffers(window);
            glfwPollEvents();
        }

        glfwTerminate();
        std::cout << "[VizEngine] Shutdown complete" << std::endl;
    }

}  // namespace VizEngine
```

---

## Step 7: Create EntryPoint.h

The entry point contains `main()` so users don't need to write it.

**Create `VizPsyche/VizEngine/src/VizEngine/EntryPoint.h`:**

```cpp
// VizEngine/src/VizEngine/EntryPoint.h

#pragma once

#include "Application.h"

// =============================================================================
// Entry Point
// =============================================================================
// This header defines main(). The user's application only needs to:
// 1. Include <VizEngine.h>
// 2. Implement VizEngine::CreateApplication()
//
// The engine handles the rest.
// =============================================================================

extern VizEngine::Application* VizEngine::CreateApplication();

int main(int argc, char** argv)
{
    (void)argc;  // Unused
    (void)argv;  // Unused

    // Create user application
    auto app = VizEngine::CreateApplication();

    // Run main loop
    app->Run();

    // Cleanup
    delete app;

    return 0;
}
```

---

## Step 8: Create VizEngine.h (Public Include)

Users include this single header to access the engine.

**Create `VizPsyche/VizEngine/src/VizEngine.h`:**

```cpp
// VizEngine/src/VizEngine.h

#pragma once

// =============================================================================
// VizEngine Public API
// =============================================================================
// Include this header in client applications.
// It pulls in all necessary engine headers.
// =============================================================================

#include "VizEngine/Application.h"

// EntryPoint must be included LAST (it defines main)
#include "VizEngine/EntryPoint.h"
```

---

## Step 9: Create Sandbox CMakeLists.txt

**Create `VizPsyche/Sandbox/CMakeLists.txt`:**

```cmake
# Sandbox/CMakeLists.txt

project(Sandbox)

# =============================================================================
# Source Files
# =============================================================================
set(SANDBOX_SOURCES
    src/SandboxApp.cpp
)

# =============================================================================
# Executable
# =============================================================================
add_executable(Sandbox ${SANDBOX_SOURCES})

# =============================================================================
# Link to Engine
# =============================================================================
target_link_libraries(Sandbox PRIVATE VizEngine)

# =============================================================================
# Copy DLL to Output (Windows)
# =============================================================================
if(WIN32)
    add_custom_command(TARGET Sandbox POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:VizEngine>
            $<TARGET_FILE_DIR:Sandbox>
        COMMENT "Copying VizEngine.dll to Sandbox output"
    )
endif()
```

---

## Step 10: Create SandboxApp.cpp

The user's application.

**Create `VizPsyche/Sandbox/src/SandboxApp.cpp`:**

```cpp
// Sandbox/src/SandboxApp.cpp

#include <VizEngine.h>

class Sandbox : public VizEngine::Application
{
public:
    Sandbox()
    {
        // Custom initialization here
    }

    ~Sandbox()
    {
        // Custom cleanup here
    }
};

// =============================================================================
// Factory Function
// =============================================================================
// The engine calls this to create our application instance.
// =============================================================================
VizEngine::Application* VizEngine::CreateApplication()
{
    return new Sandbox();
}
```

---

## Step 11: Build and Run

### Clean Previous Build

```bash
cd C:\dev\VizPsyche
rmdir /s /q build
```

### Generate and Build

```bash
cmake -B build -G "Visual Studio 17 2022"
cmake --build build --config Debug
```

### Run

```bash
.\build\bin\Debug\Sandbox.exe
```

---

## Expected Result

Console output:

```
[VizEngine] Application created
[VizEngine] Running...
[VizEngine] OpenGL 4.6.0 NVIDIA ...
```

A dark window appears. Press Escape to close.

```
[VizEngine] Shutdown complete
[VizEngine] Application destroyed
```

---

## Understanding the Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                          Sandbox.exe                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SandboxApp.cpp                                             │  │
│  │   - Includes <VizEngine.h>                                 │  │
│  │   - Implements CreateApplication()                         │  │
│  │   - EntryPoint.h provides main()                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ Links to                          │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      VizEngine.dll                         │  │
│  │   - Application base class                                 │  │
│  │   - OpenGL initialization                                  │  │
│  │   - Window management                                      │  │
│  │   - Rendering (future chapters)                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Symbol Export Flow

```
VP_BUILD_DLL defined (when building VizEngine)
    → VizEngine_API = __declspec(dllexport)
    → Symbols exported to DLL

VP_BUILD_DLL NOT defined (when building Sandbox)
    → VizEngine_API = __declspec(dllimport)
    → Symbols imported from DLL
```

---

## Project Structure After This Chapter

```
VizPsyche/
├── .git/
├── .gitignore
├── .gitmodules                    ← Submodule configuration
├── CMakeLists.txt                 ← Root build file
├── VizEngine/
│   ├── CMakeLists.txt             ← Engine build file
│   ├── include/
│   │   ├── glad/
│   │   │   └── glad.h
│   │   └── KHR/
│   │       └── khrplatform.h
│   ├── src/
│   │   ├── glad.c
│   │   ├── VizEngine.h            ← Public include
│   │   └── VizEngine/
│   │       ├── Application.cpp
│   │       ├── Application.h
│   │       ├── Core.h
│   │       └── EntryPoint.h
│   └── vendor/
│       ├── glfw/                  ← Git submodule
│       ├── glm/                   ← Git submodule
│       └── spdlog/                ← Git submodule
├── Sandbox/
│   ├── CMakeLists.txt
│   └── src/
│       └── SandboxApp.cpp
└── build/                         ← Generated (gitignored)
```

---

## Commit Your Progress

```bash
git add .
git commit -m "Chapter 3: Engine/Sandbox architecture with DLL"
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "VizEngine.dll not found" | DLL not copied | Check post-build command in Sandbox CMake |
| "unresolved external symbol" | Symbol not exported | Add `VizEngine_API` to class declaration |
| "Application created" not shown | stdout buffered | Add `std::cout.flush()` or use logging (next chapter) |
| Submodule folder empty | Submodules not initialized | Run `git submodule update --init --recursive` |

---

## Milestone

**Milestone: Engine Architecture Established**

You have:
- VizEngine as a DLL
- Sandbox application linking to engine
- Git submodules for GLFW, GLM, spdlog
- Working export/import macros
- Entry point abstraction

---

## What's Next

The current console output uses `std::cout`. In **Chapter 4**, we'll add a proper logging system with:

- Colored output
- Log levels (trace, info, warn, error)
- Separate engine and client loggers

> **Next:** [Chapter 4: Logging System](04_LoggingSystem.md)

> **Previous:** [Chapter 2: Hello Triangle](02_HelloTriangle.md)
