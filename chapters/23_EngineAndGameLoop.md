\newpage

# Chapter 23: Engine and Game Loop

Refactor the engine to separate infrastructure from game logic, introducing a proper game loop architecture with lifecycle methods.

---

## Introduction

Up until now, all of our game logic—scene setup, asset loading, camera controls, UI panels, and rendering—has lived inside `Application::Run()`. While this worked for getting things running quickly, it creates problems as the engine grows:

- **Tight coupling**: Engine infrastructure (window management, OpenGL setup, ImGui) is mixed with game-specific code
- **No reusability**: Every new game would need to copy-paste and modify the entire `Run()` method
- **Testing difficulties**: Can't test game logic independently of engine setup

In this chapter, we'll refactor the engine to cleanly separate **engine infrastructure** from **application logic**, introducing a proper game loop architecture.

---

## The Problem

Let's examine our current `Application::Run()` method structure:

```cpp
int Application::Run()
{
    // 1. Engine setup (GLFW, GLAD, ImGui)
    GLFWManager window(...);
    // ... OpenGL initialization ...
    UIManager uiManager(window.GetWindow());
    Renderer renderer;

    // 2. Game-specific setup
    auto pyramidMesh = Mesh::CreatePyramid();
    Scene scene;
    scene.Add(pyramidMesh, "Pyramid");
    Camera camera(45.0f, 800.0f/800.0f, 0.1f, 100.0f);
    // ... more game setup ...

    // 3. Game loop
    while (!window.WindowShouldClose())
    {
        // Input, update, render, UI...
    }

    return 0;
}
```

This monolithic design means the engine can't exist independently of the game code.

---

## Solution: Engine Singleton + Application Lifecycle

We'll split responsibilities:

| Component | Responsibility |
|-----------|---------------|
| **Engine** | Window, OpenGL context, ImGui, game loop, subsystems |
| **Application** | Scene setup, game logic, custom rendering, UI panels |

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                      Engine                          │
│  ┌─────────────┐ ┌──────────┐ ┌─────────────┐       │
│  │ GLFWManager │ │ Renderer │ │  UIManager  │       │
│  └─────────────┘ └──────────┘ └─────────────┘       │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │               Game Loop                       │   │
│  │  while (running && !windowClosed)             │   │
│  │  {                                            │   │
│  │      ProcessInput();                          │   │
│  │      app->OnUpdate(deltaTime);                │   │
│  │      app->OnRender();                         │   │
│  │      app->OnImGuiRender();                    │   │
│  │      SwapBuffers();                           │   │
│  │  }                                            │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                   Application                        │
│  (Sandbox, Editor, or any game)                     │
│                                                      │
│  OnCreate()      → Load assets, build scene         │
│  OnUpdate(dt)    → Camera controller, game logic    │
│  OnRender()      → Set uniforms, render scene       │
│  OnImGuiRender() → UI panels                        │
│  OnDestroy()     → Cleanup                          │
└─────────────────────────────────────────────────────┘
```

---

## Implementation

### EngineConfig Struct

First, we define configuration options that applications can customize:

```cpp
// Engine.h
struct EngineConfig
{
    std::string Title = "VizPsyche";
    uint32_t Width = 800;
    uint32_t Height = 800;
    bool VSync = true;
};
```

### Engine Class (Singleton)

The Engine uses Meyer's singleton pattern for thread-safe lazy initialization:

```cpp
// Engine.h
class VizEngine_API Engine
{
public:
    // Meyer's singleton
    static Engine& Get();

    // Non-copyable
    Engine(const Engine&) = delete;
    Engine& operator=(const Engine&) = delete;

    // Main entry point
    void Run(Application* app, const EngineConfig& config = {});
    void Quit();

    // Subsystem accessors
    GLFWManager& GetWindow();
    Renderer& GetRenderer();
    UIManager& GetUIManager();
    
    float GetDeltaTime() const { return m_DeltaTime; }

private:
    Engine() = default;
    ~Engine() = default;

    bool Init(const EngineConfig& config);
    void Shutdown();

    // Subsystems
    std::unique_ptr<GLFWManager> m_Window;
    std::unique_ptr<Renderer> m_Renderer;
    std::unique_ptr<UIManager> m_UIManager;

    float m_DeltaTime = 0.0f;
    bool m_Running = false;
};
```

### Engine Implementation

```cpp
// Engine.cpp
Engine& Engine::Get()
{
    static Engine instance;
    return instance;
}

void Engine::Run(Application* app, const EngineConfig& config)
{
    if (!app)
    {
        VP_CORE_ERROR("Engine::Run called with null application!");
        return;
    }

    if (!Init(config))
    {
        VP_CORE_ERROR("Engine initialization failed!");
        return;
    }

    m_Running = true;
    app->OnCreate();

    double prevTime = glfwGetTime();

    // Main game loop
    while (m_Running && !m_Window->WindowShouldClose())
    {
        // Delta time
        double currentTime = glfwGetTime();
        m_DeltaTime = static_cast<float>(currentTime - prevTime);
        prevTime = currentTime;

        // Input phase
        m_Window->ProcessInput();
        m_UIManager->BeginFrame();

        // Application hooks
        app->OnUpdate(m_DeltaTime);
        app->OnRender();
        app->OnImGuiRender();

        // Present
        m_UIManager->Render();
        m_Window->SwapBuffersAndPollEvents();
    }

    app->OnDestroy();
    Shutdown();
}
```

### Application Base Class

The Application class becomes an abstract base with virtual lifecycle methods:

```cpp
// Application.h
class VizEngine_API Application
{
public:
    Application();
    virtual ~Application();

    // Non-copyable
    Application(const Application&) = delete;
    Application& operator=(const Application&) = delete;

    virtual void OnCreate() {}
    virtual void OnUpdate(float deltaTime) { (void)deltaTime; }
    virtual void OnRender() {}
    virtual void OnImGuiRender() {}
    virtual void OnDestroy() {}
};

// Factory function implemented by client applications
Application* CreateApplication(EngineConfig& config);
```

> [!NOTE]
> The constructor and destructor are declared in the header but defined in Application.cpp. This ensures proper vtable generation in the DLL.

### Entry Point

The entry point in VizEngine handles `main()` for the client:

```cpp
// EntryPoint.h
#pragma once

#ifdef VP_PLATFORM_WINDOWS

#include "Engine.h"
#include "Application.h"

int main(int argc, char** argv)
{
    (void)argc;
    (void)argv;

    VizEngine::Log::Init();

    VizEngine::EngineConfig config;
    auto app = VizEngine::CreateApplication(config);
    VizEngine::Engine::Get().Run(app, config);
    delete app;

    return 0;
}

#endif
```

> [!NOTE]
> `EntryPoint.h` lives in VizEngine but is included by client applications via `VizEngine.h`. This means clients don't need to write their own `main()`.

## DLL Architecture Considerations

When building VizEngine as a shared library (DLL), several patterns must be followed:

### VizEngine_API Macro

Classes with methods defined in .cpp files need the export macro:

```cpp
class VizEngine_API Engine { ... };
class VizEngine_API Application { ... };
class VizEngine_API UIManager { ... };
```

### Header-Only Structs

Simple structs fully defined in headers (with inline constructors) do **NOT** need `VizEngine_API`:

```cpp
// These are fine without VizEngine_API
struct DirectionalLight { ... };
struct PointLight { ... };
struct Material { ... };
```

### ImGui and DLL Boundaries

ImGui uses global state (`GImGui` context). When ImGui is compiled into a DLL and the application tries to call ImGui functions directly, you get separate contexts—causing crashes.

**Solution**: UIManager provides wrapper methods so applications go through the DLL:

```cpp
// UIManager provides wrappers
class UIManager
{
public:
    // Applications call these instead of ImGui:: directly
    void Text(const char* fmt, ...);
    void Separator();
    bool Button(const char* label);
    bool SliderFloat(const char* label, float* value, float min, float max);
    bool DragFloat3(const char* label, float* values, float speed = 0.1f);
    bool ColorEdit3(const char* label, float* color);
    bool ColorEdit4(const char* label, float* color);
    bool Checkbox(const char* label, bool* value);
    bool Selectable(const char* label, bool selected);
    void SameLine();
    // ... more as needed
};
```

The implementations simply forward to ImGui:

```cpp
void UIManager::Text(const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::TextV(fmt, args);
    va_end(args);
}

bool UIManager::Button(const char* label)
{
    return ImGui::Button(label);
}
```

## Migrating Sandbox

With the new architecture, Sandbox becomes much cleaner:

```cpp
// SandboxApp.cpp
#include <VizEngine.h>

class Sandbox : public VizEngine::Application
{
public:
    void OnCreate() override
    {
        // Load assets and build scene
        m_PyramidMesh = VizEngine::Mesh::CreatePyramid();
        m_Scene.Add(m_PyramidMesh, "Pyramid");
        m_Camera = VizEngine::Camera(45.0f, 1.0f, 0.1f, 100.0f);
        m_LitShader = std::make_unique<VizEngine::Shader>("...");
    }

    void OnUpdate(float deltaTime) override
    {
        // Camera controller, input handling
        if (VizEngine::Input::IsKeyHeld(VizEngine::KeyCode::W))
            m_Camera.MoveForward(5.0f * deltaTime);
    }

    void OnRender() override
    {
        auto& renderer = VizEngine::Engine::Get().GetRenderer();
        renderer.Clear(m_ClearColor);
        m_Scene.Render(renderer, *m_LitShader, m_Camera);
    }

    void OnImGuiRender() override
    {
        auto& ui = VizEngine::Engine::Get().GetUIManager();
        
        ui.StartWindow("Scene Controls");
        ui.ColorEdit4("Clear Color", m_ClearColor);
        ui.SliderFloat("Rotation Speed", &m_RotationSpeed, 0.0f, 5.0f);
        ui.EndWindow();
    }

private:
    VizEngine::Scene m_Scene;
    VizEngine::Camera m_Camera;
    std::unique_ptr<VizEngine::Shader> m_LitShader;
    float m_ClearColor[4] = {0.1f, 0.1f, 0.15f, 1.0f};
    float m_RotationSpeed = 0.5f;
};

VizEngine::Application* VizEngine::CreateApplication(VizEngine::EngineConfig& config)
{
    config.Title = "Sandbox - VizPsyche";
    config.Width = 800;
    config.Height = 800;
    return new Sandbox();
}
```

Notice:
- Only one include: `#include <VizEngine.h>`
- UI goes through `UIManager` wrappers, not direct `ImGui::` calls
- Subsystems accessed via `Engine::Get().GetRenderer()`, etc.

## Public API Design

`VizEngine.h` exports the complete public API:

```cpp
#pragma once

// Core engine
#include "VizEngine/Application.h"
#include "VizEngine/Engine.h"
#include "VizEngine/Log.h"

// Subsystems
#include "VizEngine/GUI/UIManager.h"
#include "VizEngine/OpenGL/Renderer.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"

// Core types
#include "VizEngine/Core/Camera.h"
#include "VizEngine/Core/Scene.h"
#include "VizEngine/Core/Mesh.h"
#include "VizEngine/Core/Light.h"
#include "VizEngine/Core/Input.h"

// Asset loading
#include "VizEngine/Core/Model.h"
#include "VizEngine/Core/Material.h"

// Entry point (must be last)
#include "VizEngine/EntryPoint.h"
```

This means client applications only need:
```cpp
#include <VizEngine.h>
```

## Consistency Patterns

Throughout the engine, follow these patterns for consistency:

### Non-Copyable Classes

All classes that own resources should be non-copyable:

```cpp
class SomeClass
{
public:
    // Non-copyable
    SomeClass(const SomeClass&) = delete;
    SomeClass& operator=(const SomeClass&) = delete;
};
```

Applied to: `Engine`, `Application`, `UIManager`

### Out-of-Line Definitions for Exported Classes

For classes with `VizEngine_API`, define constructors/destructors in .cpp:

```cpp
// Header
class VizEngine_API Application
{
public:
    Application();
    virtual ~Application();
};

// Source
Application::Application() = default;
Application::~Application() = default;
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| App crashes immediately | `CreateApplication` returns null | Check factory function returns valid pointer |
| ImGui context assertion | Direct ImGui calls from Sandbox | Use `UIManager` wrappers instead of `ImGui::` |
| "Engine not initialized" | Accessing subsystems before `Run()` | Only access Engine subsystems inside lifecycle methods |
| Input not working | `Input::Init` not called | Engine initializes Input via GLFWManager |
| Linker errors | Missing `VizEngine_API` | Add export macro to classes with .cpp implementation |

---

## Milestone

**Engine Architecture Complete**

You have:
- `Engine` singleton with Meyer's pattern
- `EngineConfig` for window/rendering settings
- `Application` base class with virtual lifecycle methods
- `EntryPoint.h` that owns `main()`
- `UIManager` wrappers for DLL-safe ImGui access
- Clean separation of engine infrastructure from game code

---

## Summary

| Before | After |
|--------|-------|
| Monolithic `Application::Run()` | Clean Engine/Application separation |
| Game code mixed with engine setup | Virtual lifecycle methods |
| Direct ImGui calls | UIManager wrappers for DLL safety |
| Multiple includes needed | Single `#include <VizEngine.h>` |

The engine now follows the professional pattern used by engines like Hazel, allowing games to focus purely on game logic while the engine handles infrastructure.

---

## What's Next

In **Chapter 24**, we'll make Application a true abstract base class with virtual lifecycle methods, allowing derived applications to implement their own startup, update, and shutdown logic.

> **Next:** [Chapter 24: Virtual Lifecycle](24_VirtualLifecycle.md)

> **Previous:** [Chapter 22: Camera Controller](22_CameraController.md)
