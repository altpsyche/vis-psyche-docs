\newpage

# Chapter 4: Logging System

Replace `std::cout` with a proper logging system. Good logging is essential for debugging—it tells you what's happening inside your engine without stepping through with a debugger.

---

## Why Not std::cout?

| Problem with std::cout | Solution with Logging |
|------------------------|----------------------|
| No log levels | Filter by severity (trace, info, warn, error) |
| No color | Colored output for quick scanning |
| Hard to disable | Compile-time or runtime level control |
| No formatting | Type-safe `{}` placeholder formatting |
| No source separation | Separate engine vs. client logs |

---

## Our Approach

We wrap the **spdlog** library (already added as a submodule in Chapter 3) with our own API:

- `VP_CORE_INFO("message")` — Engine logging
- `VP_INFO("message")` — Application logging

---

## Step 1: Update VizEngine CMakeLists.txt

Add the Log source file and spdlog include directory.

**Update `VizEngine/CMakeLists.txt`:**

```cmake
# VizEngine/CMakeLists.txt

project(VizEngine)

# =============================================================================
# Source Files
# =============================================================================
set(VIZENGINE_SOURCES
    src/VizEngine/Application.cpp
    src/VizEngine/Log.cpp              # NEW
    src/glad.c
)

set(VIZENGINE_HEADERS
    src/VizEngine.h
    src/VizEngine/Application.h
    src/VizEngine/Core.h
    src/VizEngine/EntryPoint.h
    src/VizEngine/Log.h                # NEW
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
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/vendor/spdlog/include>  # NEW
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

## Step 2: Create Log.h

**Create `VizEngine/src/VizEngine/Log.h`:**

```cpp
// VizEngine/src/VizEngine/Log.h

#pragma once

#include "Core.h"

// Silence MSVC warnings in spdlog headers
#ifdef _MSC_VER
    #pragma warning(push)
    #pragma warning(disable: 4189 4996)
#endif

#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>

#ifdef _MSC_VER
    #pragma warning(pop)
#endif

#include <memory>

namespace VizEngine
{
    /// @brief Logging system with separate core and client loggers.
    /// 
    /// Usage:
    ///   VP_CORE_INFO("Engine message: {}", value);  // Engine logs
    ///   VP_INFO("Application message: {}", value);  // Client logs
    class VizEngine_API Log
    {
    public:
        /// @brief Initialize the logging system. Call once at startup.
        static void Init();

        /// @brief Set log level for core (engine) logger.
        static void SetCoreLogLevel(spdlog::level::level_enum level);

        /// @brief Set log level for client (application) logger.
        static void SetClientLogLevel(spdlog::level::level_enum level);

        /// @brief Get the core logger instance.
        static std::shared_ptr<spdlog::logger>& GetCoreLogger() { return s_CoreLogger; }

        /// @brief Get the client logger instance.
        static std::shared_ptr<spdlog::logger>& GetClientLogger() { return s_ClientLogger; }

    private:
        static std::shared_ptr<spdlog::logger> s_CoreLogger;
        static std::shared_ptr<spdlog::logger> s_ClientLogger;
    };

}  // namespace VizEngine

// =============================================================================
// Logging Macros - Core (Engine)
// =============================================================================
#define VP_CORE_TRACE(...)    ::VizEngine::Log::GetCoreLogger()->trace(__VA_ARGS__)
#define VP_CORE_INFO(...)     ::VizEngine::Log::GetCoreLogger()->info(__VA_ARGS__)
#define VP_CORE_WARN(...)     ::VizEngine::Log::GetCoreLogger()->warn(__VA_ARGS__)
#define VP_CORE_ERROR(...)    ::VizEngine::Log::GetCoreLogger()->error(__VA_ARGS__)
#define VP_CORE_CRITICAL(...) ::VizEngine::Log::GetCoreLogger()->critical(__VA_ARGS__)

// =============================================================================
// Logging Macros - Client (Application)
// =============================================================================
#define VP_TRACE(...)    ::VizEngine::Log::GetClientLogger()->trace(__VA_ARGS__)
#define VP_INFO(...)     ::VizEngine::Log::GetClientLogger()->info(__VA_ARGS__)
#define VP_WARN(...)     ::VizEngine::Log::GetClientLogger()->warn(__VA_ARGS__)
#define VP_ERROR(...)    ::VizEngine::Log::GetClientLogger()->error(__VA_ARGS__)
#define VP_CRITICAL(...) ::VizEngine::Log::GetClientLogger()->critical(__VA_ARGS__)
```

---

## Step 3: Create Log.cpp

**Create `VizEngine/src/VizEngine/Log.cpp`:**

```cpp
// VizEngine/src/VizEngine/Log.cpp

#include "Log.h"

namespace VizEngine
{
    // Static member definitions
    std::shared_ptr<spdlog::logger> Log::s_CoreLogger;
    std::shared_ptr<spdlog::logger> Log::s_ClientLogger;

    void Log::Init()
    {
        // Set global pattern: [timestamp] [logger] [level] message
        // %^...%$ applies color to the level
        spdlog::set_pattern("%^[%T] [%n] [%l]%$ %v");

        // Create core logger (for engine messages)
        s_CoreLogger = spdlog::stdout_color_mt("VizEngine");
        s_CoreLogger->set_level(spdlog::level::trace);

        // Create client logger (for application messages)
        s_ClientLogger = spdlog::stdout_color_mt("App");
        s_ClientLogger->set_level(spdlog::level::trace);
    }

    void Log::SetCoreLogLevel(spdlog::level::level_enum level)
    {
        s_CoreLogger->set_level(level);
    }

    void Log::SetClientLogLevel(spdlog::level::level_enum level)
    {
        s_ClientLogger->set_level(level);
    }

}  // namespace VizEngine
```

---

## Step 4: Update VizEngine.h

Add Log.h to the public includes.

**Update `VizEngine/src/VizEngine.h`:**

```cpp
// VizEngine/src/VizEngine.h

#pragma once

// =============================================================================
// VizEngine Public API
// =============================================================================

#include "VizEngine/Application.h"
#include "VizEngine/Log.h"         // NEW

// EntryPoint must be included LAST
#include "VizEngine/EntryPoint.h"
```

---

## Step 5: Update EntryPoint.h

Initialize logging before creating the application.

**Update `VizEngine/src/VizEngine/EntryPoint.h`:**

```cpp
// VizEngine/src/VizEngine/EntryPoint.h

#pragma once

#include "Application.h"
#include "Log.h"

extern VizEngine::Application* VizEngine::CreateApplication();

int main(int argc, char** argv)
{
    (void)argc;
    (void)argv;

    // Initialize logging FIRST
    VizEngine::Log::Init();
    VP_CORE_INFO("VizEngine initialized");

    // Create and run application
    auto app = VizEngine::CreateApplication();
    app->Run();
    delete app;

    VP_CORE_INFO("VizEngine shutdown");
    return 0;
}
```

---

## Step 6: Update Application.cpp

Replace `std::cout` with logging macros.

**Update `VizEngine/src/VizEngine/Application.cpp`:**

```cpp
// VizEngine/src/VizEngine/Application.cpp

#include "Application.h"
#include "Log.h"

#include <glad/glad.h>
#include <GLFW/glfw3.h>

namespace VizEngine
{
    Application::Application()
    {
        VP_CORE_TRACE("Application constructor");
    }

    Application::~Application()
    {
        VP_CORE_TRACE("Application destructor");
    }

    void Application::Run()
    {
        VP_CORE_INFO("Starting main loop...");

        // Initialize GLFW
        if (!glfwInit())
        {
            VP_CORE_CRITICAL("Failed to initialize GLFW!");
            return;
        }
        VP_CORE_TRACE("GLFW initialized");

        // OpenGL hints
        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

        // Create window
        GLFWwindow* window = glfwCreateWindow(1280, 720, "VizEngine", nullptr, nullptr);
        if (!window)
        {
            VP_CORE_CRITICAL("Failed to create window!");
            glfwTerminate();
            return;
        }
        VP_CORE_INFO("Window created: 1280x720");

        glfwMakeContextCurrent(window);

        // Load OpenGL functions
        if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
        {
            VP_CORE_CRITICAL("Failed to initialize GLAD!");
            return;
        }
        VP_CORE_INFO("OpenGL {}", (const char*)glGetString(GL_VERSION));

        // Main loop
        while (!glfwWindowShouldClose(window))
        {
            if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            {
                glfwSetWindowShouldClose(window, true);
            }

            glClearColor(0.1f, 0.1f, 0.15f, 1.0f);
            glClear(GL_COLOR_BUFFER_BIT);

            glfwSwapBuffers(window);
            glfwPollEvents();
        }

        glfwTerminate();
        VP_CORE_INFO("Main loop ended");
    }

}  // namespace VizEngine
```

---

## Step 7: Update SandboxApp.cpp

Use client logging macros.

**Update `Sandbox/src/SandboxApp.cpp`:**

```cpp
// Sandbox/src/SandboxApp.cpp

#include <VizEngine.h>

class Sandbox : public VizEngine::Application
{
public:
    Sandbox()
    {
        VP_INFO("Sandbox created!");
        VP_TRACE("This is a trace message");
        VP_WARN("This is a warning");
    }

    ~Sandbox()
    {
        VP_INFO("Sandbox destroyed!");
    }
};

VizEngine::Application* VizEngine::CreateApplication()
{
    return new Sandbox();
}
```

---

## Step 8: Build and Run

```bash
cmake --build build --config Debug
.\build\bin\Debug\Sandbox.exe
```

---

## Expected Output

Colored console output:

```
[HH:MM:SS] [VizEngine] [info] VizEngine initialized
[HH:MM:SS] [VizEngine] [trace] Application constructor
[HH:MM:SS] [App] [info] Sandbox created!
[HH:MM:SS] [App] [trace] This is a trace message
[HH:MM:SS] [App] [warning] This is a warning
[HH:MM:SS] [VizEngine] [info] Starting main loop...
[HH:MM:SS] [VizEngine] [trace] GLFW initialized
[HH:MM:SS] [VizEngine] [info] Window created: 1280x720
[HH:MM:SS] [VizEngine] [info] OpenGL 4.6.0 NVIDIA ...
```

After pressing Escape:

```
[HH:MM:SS] [VizEngine] [info] Main loop ended
[HH:MM:SS] [VizEngine] [trace] Application destructor
[HH:MM:SS] [App] [info] Sandbox destroyed!
[HH:MM:SS] [VizEngine] [info] VizEngine shutdown
```

---

## Log Levels

| Level | Macro | Use Case |
|-------|-------|----------|
| **trace** | `VP_CORE_TRACE` | Detailed debugging info |
| **info** | `VP_CORE_INFO` | General information |
| **warn** | `VP_CORE_WARN` | Something unexpected, not fatal |
| **error** | `VP_CORE_ERROR` | Error, operation failed |
| **critical** | `VP_CORE_CRITICAL` | Fatal error, must stop |

### Controlling Output

```cpp
// Show only warnings and above
VizEngine::Log::SetCoreLogLevel(spdlog::level::warn);
```

---

## Formatting

spdlog uses `{}` placeholders (similar to Python's f-strings):

```cpp
VP_INFO("Player {} scored {} points", playerName, score);
VP_INFO("Position: ({:.2f}, {:.2f})", x, y);  // 2 decimal places
VP_INFO("Hex: {:#x}", value);                 // Hexadecimal
```

---

## Project Structure After This Chapter

```
VizPsyche/
├── VizEngine/
│   ├── CMakeLists.txt
│   ├── src/
│   │   ├── VizEngine.h
│   │   ├── glad.c
│   │   └── VizEngine/
│   │       ├── Application.cpp
│   │       ├── Application.h
│   │       ├── Core.h
│   │       ├── EntryPoint.h
│   │       ├── Log.cpp          ← NEW
│   │       └── Log.h            ← NEW
│   └── vendor/
│       ├── glfw/
│       ├── glm/
│       └── spdlog/              ← Used for the first time
├── Sandbox/
│   └── src/
│       └── SandboxApp.cpp
└── CMakeLists.txt
```

---

## Commit Your Progress

```bash
git add .
git commit -m "Chapter 4: Logging system with spdlog"
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "spdlog/spdlog.h not found" | Include path wrong | Check spdlog submodule and CMake include dirs |
| No output / blank console | Log not initialized | Ensure `Log::Init()` called in EntryPoint |
| "unresolved external symbol Log" | Static members not defined | Ensure Log.cpp has static member definitions |
| Colors don't show | Windows terminal issue | Use Windows Terminal or enable ANSI in cmd |

---

## Milestone

**Milestone: Logging System Working**

You have:
- Colored, formatted logging output
- Separate engine (`VP_CORE_*`) and client (`VP_*`) loggers
- Log level control
- spdlog integrated and working

---

## What's Next

In **Chapter 5**, we'll wrap GLFW into a `GLFWManager` class for cleaner window and context management.

> **Next:** [Chapter 5: Window & Context](05_WindowAndContext.md)

> **Previous:** [Chapter 3: Project Structure](03_ProjectStructure.md)
