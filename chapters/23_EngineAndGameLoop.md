\newpage

# Chapter 23: Engine and Game Loop

Refactor the engine to separate infrastructure from game logic, introducing a proper game loop architecture with lifecycle methods.

---

## Introduction

Up until now, all of our game logic—scene setup, asset loading, camera controls, UI panels, and rendering—has lived inside `Application::Run()`. While this worked for getting things running quickly, it creates problems as the engine grows:

- **Tight coupling**: Engine infrastructure (window management, OpenGL setup, ImGui) is mixed with game-specific code
- **No reusability**: Every new game would need to copy-paste and modify the entire `Run()` method
- **Testing difficulties**: Can't test game logic independently of engine setup

In this chapter, we'll refactor the engine to cleanly separate **engine infrastructure** from **application logic**.

---

## Migrating Your Existing Code

If you've been building the engine through previous chapters, your `Application::Run()` contains the entire game loop. Here's how to distribute that code across lifecycle methods:

### Code Migration Map

| Current Location (in `Run()`) | New Location | Called When |
|-------------------------------|--------------|-------------|
| Asset loading, scene setup | `OnCreate()` | Once, before loop |
| Per-frame game logic (camera, physics) | `OnUpdate(deltaTime)` | Every frame |
| Scene rendering, shader setup | `OnRender()` | Every frame |
| ImGui panels | `OnImGuiRender()` | Every frame |
| Cleanup (if any) | `OnDestroy()` | Once, after loop |

### Key Differences

**Before (monolithic):**
```cpp
void Application::Run() {
    // Setup
    Shader shader("lit.shader");
    while (!window.ShouldClose()) {
        shader.Bind();
        scene.Render();
        ImGui::Begin("Panel");
        ImGui::End();
    }
}
```

**After (lifecycle):**
```cpp
class Sandbox : public Application {
    std::unique_ptr<Shader> m_Shader;  // Local → Member
    
    void OnCreate() override {
        m_Shader = std::make_unique<Shader>("lit.shader");
    }
    void OnRender() override {
        m_Shader->Bind();
        m_Scene.Render();
    }
    void OnImGuiRender() override {
        auto& ui = Engine::Get().GetUIManager();
        ui.StartWindow("Panel");
        ui.EndWindow();
    }
};
```

### What Changes

1. **Local variables → Member variables** (they persist across method calls)
2. **Direct `ImGui::` calls → `UIManager` wrappers** (avoids DLL boundary issues)
3. **Engine owns the game loop** (you implement focused hooks)
4. **`unique_ptr` ownership** (automatic cleanup, clear semantics)

---

## Architecture Overview

We'll split responsibilities:

| Component | Responsibility |
|-----------|---------------|
| **Engine** | Window, OpenGL context, ImGui, game loop, subsystems |
| **Application** | Scene setup, game logic, custom rendering, UI panels |

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

## Step 1: Update GLFWManager

Before we build the Engine class, we need to ensure the `GLFWManager` handles the Input system initialization. In previous chapters, we initialized `Input` in `Application::Run`, but now the Engine will manage this.

**Open `VizEngine/src/VizEngine/OpenGL/GLFWManager.cpp` and update `Init`:**

```cpp
#include "VizEngine/Core/Input.h" // Add this include

void GLFWManager::Init(unsigned int width, unsigned int height, const std::string& title)
{
    // ... (Window creation code) ...

    glfwMakeContextCurrent(m_Window);
    
    // ... (Callback setup) ...

    // Initialize Input system with the new window
    Input::Init(m_Window);
}
```

> [!NOTE]
> Moving `Input::Init` here ensures the input system is ready as soon as the window exists.

---

## Step 2: Create the Engine Class

**Create `VizEngine/src/VizEngine/Engine.h`:**

```cpp
// VizEngine/src/VizEngine/Engine.h

#pragma once

#include <string>
#include <memory>
#include <cstdint>
#include "Core.h"

namespace VizEngine
{
	// Forward declarations
	class Application;
	class GLFWManager;
	class Renderer;
	class UIManager;

	/**
	 * Configuration for the Engine.
	 * Pass to CreateApplication() to customize window and rendering settings.
	 */
	struct EngineConfig
	{
		std::string Title = "VizPsyche";
		uint32_t Width = 800;
		uint32_t Height = 800;
		bool VSync = true;
	};

	/**
	 * Engine singleton that owns the game loop and core subsystems.
	 * Separates engine infrastructure from game logic.
	 */
	class VizEngine_API Engine
	{
	public:
		/**
		 * Get the singleton instance.
		 * Uses Meyer's singleton pattern for thread-safe lazy initialization.
		 */
		static Engine& Get();

		// Non-copyable
		Engine(const Engine&) = delete;
		Engine& operator=(const Engine&) = delete;

		/**
		 * Run the game loop with the given application.
		 * @param app The application to run (ownership transferred via unique_ptr)
		 * @param config Engine configuration settings
		 */
		void Run(std::unique_ptr<Application> app, const EngineConfig& config = {});

		/**
		 * Request the engine to quit at the end of the current frame.
		 */
		void Quit();

		// Subsystem accessors
		GLFWManager& GetWindow();
		Renderer& GetRenderer();
		UIManager& GetUIManager();

		/**
		 * Get the delta time (seconds) since the last frame.
		 */
		float GetDeltaTime() const { return m_DeltaTime; }

	private:
		Engine() = default;
		~Engine() = default;

		/**
		 * Initialize the engine and all subsystems.
		 * @return true if initialization succeeded
		 */
		bool Init(const EngineConfig& config);

		/**
		 * Shutdown the engine and clean up subsystems.
		 */
		void Shutdown();

		// Subsystems
		std::unique_ptr<GLFWManager> m_Window;
		std::unique_ptr<Renderer> m_Renderer;
		std::unique_ptr<UIManager> m_UIManager;

		float m_DeltaTime = 0.0f;
		bool m_Running = false;
	};
}
```

---

## Step 2: Create Engine.cpp

**Create `VizEngine/src/VizEngine/Engine.cpp`:**

```cpp
// VizEngine/src/VizEngine/Engine.cpp

#include "Engine.h"
#include "Application.h"
#include "Log.h"

#include "OpenGL/GLFWManager.h"
#include "OpenGL/Renderer.h"
#include "OpenGL/ErrorHandling.h"
#include "GUI/UIManager.h"
#include "Core/Input.h"

#include <glad/glad.h>
#include <GLFW/glfw3.h>

namespace VizEngine
{
	Engine& Engine::Get()
	{
		static Engine instance;
		return instance;
	}

	void Engine::Run(std::unique_ptr<Application> app, const EngineConfig& config)
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

		bool appCreated = false;
		try
		{
			// Application initialization
			app->OnCreate();
			appCreated = true;

			double prevTime = glfwGetTime();

			// Main game loop
			while (m_Running && !m_Window->WindowShouldClose())
			{
				// Delta time calculation
				double currentTime = glfwGetTime();
				m_DeltaTime = static_cast<float>(currentTime - prevTime);
				prevTime = currentTime;

				// Poll events first (fresh input for this frame)
				m_Window->PollEvents();

				// Input phase
				m_Window->ProcessInput();
				m_UIManager->BeginFrame();

				// Application hooks
				app->OnUpdate(m_DeltaTime);
				app->OnRender();
				app->OnImGuiRender();

				// Present phase
				m_UIManager->Render();
				m_Window->SwapBuffers();
				Input::EndFrame();  // Reset scroll delta for next frame
			}

			// Application cleanup
			app->OnDestroy();
		}
		catch (const std::exception& e)
		{
			VP_CORE_ERROR("Exception in engine loop: {}", e.what());
			if (appCreated)
			{
				app->OnDestroy();
			}
		}
		catch (...)
		{
			VP_CORE_ERROR("Unknown exception in engine loop");
			if (appCreated)
			{
				app->OnDestroy();
			}
		}

		Shutdown();
	}

	void Engine::Quit()
	{
		m_Running = false;
	}

	GLFWManager& Engine::GetWindow()
	{
		VP_CORE_ASSERT(m_Window, "Engine not initialized or already shut down!");
		return *m_Window;
	}

	Renderer& Engine::GetRenderer()
	{
		VP_CORE_ASSERT(m_Renderer, "Engine not initialized or already shut down!");
		return *m_Renderer;
	}

	UIManager& Engine::GetUIManager()
	{
		VP_CORE_ASSERT(m_UIManager, "Engine not initialized or already shut down!");
		return *m_UIManager;
	}

	bool Engine::Init(const EngineConfig& config)
	{
		VP_CORE_INFO("Initializing Engine...");

		// Create window
		try
		{
			m_Window = std::make_unique<GLFWManager>(
				config.Width, 
				config.Height, 
				config.Title.c_str()
			);
		}
		catch (const std::exception& e)
		{
			VP_CORE_ERROR("Failed to create window: {}", e.what());
			return false;
		}
		catch (...)
		{
			VP_CORE_ERROR("Failed to create window: Unknown error");
			return false;
		}

		// Initialize GLAD
		if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
		{
			VP_CORE_ERROR("Failed to initialize GLAD");
			return false;
		}

		// OpenGL state setup
		glEnable(GL_BLEND);
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
		glEnable(GL_DEPTH_TEST);

		// Create subsystems
		m_UIManager = std::make_unique<UIManager>(m_Window->GetWindow());
		m_Renderer = std::make_unique<Renderer>();

		// Enable OpenGL debug output
		ErrorHandling::HandleErrors();

		VP_CORE_INFO("Engine initialized successfully");
		return true;
	}

	void Engine::Shutdown()
	{
		VP_CORE_INFO("Shutting down Engine...");

		// Reset subsystems in reverse order of creation
		m_Renderer.reset();
		m_UIManager.reset();
		m_Window.reset();

		VP_CORE_INFO("Engine shutdown complete");
	}
}
```

> [!NOTE]
> The game loop is wrapped in a try-catch block to ensure `Shutdown()` is always called, even if an application hook throws an exception. This prevents resource leaks.

> [!IMPORTANT]
> The subsystem accessors use `VP_CORE_ASSERT` to guard against null pointer dereference. These trigger in debug builds if accessed before `Init()` succeeds or after `Shutdown()`.

---

## Step 3: Update Application.h

The Application class becomes an abstract base with virtual lifecycle methods.

**Replace `VizEngine/src/VizEngine/Application.h`:**

```cpp
// VizEngine/src/VizEngine/Application.h

#pragma once

#include <memory>
#include "Core.h"

namespace VizEngine
{
	// Forward declaration
	struct EngineConfig;

	/**
	 * Base class for game applications.
	 * Inherit from this class and override lifecycle methods to implement your game.
	 */
	class VizEngine_API Application
	{
	public:
		Application();
		virtual ~Application();

		// Non-copyable
		Application(const Application&) = delete;
		Application& operator=(const Application&) = delete;

		/**
		 * Called once before the game loop starts.
		 * Use for loading assets, creating the scene, and initial setup.
		 */
		virtual void OnCreate() {}

		/**
		 * Called every frame.
		 * @param deltaTime Time in seconds since the last frame.
		 * Use for game logic, camera controllers, physics updates.
		 */
		virtual void OnUpdate(float deltaTime) { (void)deltaTime; }

		/**
		 * Called every frame after OnUpdate.
		 * Use for rendering the scene.
		 */
		virtual void OnRender() {}

		/**
		 * Called every frame after OnRender.
		 * Use for ImGui panels and debug UI.
		 */
		virtual void OnImGuiRender() {}

		/**
		 * Called once after the game loop ends.
		 * Use for cleanup (though RAII handles most cases).
		 */
		virtual void OnDestroy() {}
	};

	/**
	 * Factory function implemented by client applications.
	 * @param config Engine configuration that the application can modify.
	 * @return A new Application instance (ownership transferred via unique_ptr).
	 */
	std::unique_ptr<Application> CreateApplication(EngineConfig& config);
}
```

---

## Step 4: Update Application.cpp

**Replace `VizEngine/src/VizEngine/Application.cpp`:**

```cpp
// VizEngine/src/VizEngine/Application.cpp

#include "Application.h"

namespace VizEngine
{
	// Out-of-line definitions for exported class with virtual destructor.
	// This ensures proper vtable generation in the DLL.
	Application::Application() = default;
	Application::~Application() = default;
}
```

> [!NOTE]
> The constructor and destructor must be defined out-of-line (in the .cpp file) for proper vtable generation when building VizEngine as a DLL.

---

## Step 5: Update EntryPoint.h

The entry point now uses the Engine singleton.

**Replace `VizEngine/src/VizEngine/EntryPoint.h`:**

```cpp
// VizEngine/src/VizEngine/EntryPoint.h

#pragma once

#ifdef VP_PLATFORM_WINDOWS

#include "Engine.h"
#include "Application.h"  // For CreateApplication declaration

int main()
{
	VizEngine::Log::Init();

	VizEngine::EngineConfig config;
	auto app = VizEngine::CreateApplication(config);
	VizEngine::Engine::Get().Run(std::move(app), config);
	// No delete needed - unique_ptr ownership transferred to Engine

	return 0;
}

#endif
```

> [!NOTE]
> `EntryPoint.h` lives in VizEngine but is included by client applications via `VizEngine.h`. This means clients don't need to write their own `main()`. The entry point owns the Application pointer and deletes it after the engine exits.

---

## Step 6: Update UIManager.h

UIManager provides wrapper methods so applications don't call ImGui directly—this avoids DLL boundary issues with ImGui's global context.

**Replace `VizEngine/src/VizEngine/GUI/UIManager.h`:**

```cpp
// VizEngine/src/VizEngine/GUI/UIManager.h

#pragma once

#include <string>
#include "VizEngine/Core.h"

// Forward declaration - avoid exposing GLFW to consumers
struct GLFWwindow;

namespace VizEngine
{
	/**
	 * Manages ImGui integration with the engine.
	 * Provides wrapper methods so client applications don't need direct ImGui access.
	 * This avoids DLL boundary issues with ImGui's global context.
	 */
	class VizEngine_API UIManager
	{
	public:
		UIManager(GLFWwindow* window);
		~UIManager();

		// Non-copyable (owns ImGui context state)
		UIManager(const UIManager&) = delete;
		UIManager& operator=(const UIManager&) = delete;

		// Frame lifecycle
		void BeginFrame();
		void Render();

		// Window helpers
		void StartWindow(const std::string& windowName);
		void EndWindow();

		// =========================================================================
		// ImGui Widget Wrappers
		// These forward to ImGui internally so consumers don't need ImGui access
		// =========================================================================
		
		// Text and labels
		void Text(const char* fmt, ...);
		void Separator();
		void SameLine();

		// Input widgets
		bool Button(const char* label);
		bool Checkbox(const char* label, bool* value);
		bool SliderFloat(const char* label, float* value, float min, float max);
		bool DragFloat3(const char* label, float* values, float speed = 0.1f, float min = 0.0f, float max = 0.0f);
		
		// Color editors
		bool ColorEdit3(const char* label, float* color);
		bool ColorEdit4(const char* label, float* color);
		
		// Selection
		bool Selectable(const char* label, bool selected);

	private:
		void Init(GLFWwindow* window);
		void Shutdown();
	};
}
```

---

## Step 7: Update UIManager.cpp

**Replace `VizEngine/src/VizEngine/GUI/UIManager.cpp`:**

```cpp
// VizEngine/src/VizEngine/GUI/UIManager.cpp

#include "UIManager.h"

#include <cstdarg>
#include <GLFW/glfw3.h>
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"

namespace VizEngine
{
	UIManager::UIManager(GLFWwindow* window)
	{
		Init(window);
	}

	UIManager::~UIManager()
	{
		Shutdown();
	}

	void UIManager::BeginFrame()
	{
		ImGui_ImplOpenGL3_NewFrame();
		ImGui_ImplGlfw_NewFrame();
		ImGui::NewFrame();
	}

	void UIManager::Render()
	{
		ImGui::Render();
		ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
	}

	void UIManager::StartWindow(const std::string& windowName)
	{
		ImGui::Begin(windowName.c_str());
	}

	void UIManager::EndWindow()
	{
		ImGui::End();
	}

	// =========================================================================
	// ImGui Widget Wrappers
	// =========================================================================

	void UIManager::Text(const char* fmt, ...)
	{
		va_list args;
		va_start(args, fmt);
		ImGui::TextV(fmt, args);
		va_end(args);
	}

	void UIManager::Separator()
	{
		ImGui::Separator();
	}

	void UIManager::SameLine()
	{
		ImGui::SameLine();
	}

	bool UIManager::Button(const char* label)
	{
		return ImGui::Button(label);
	}

	bool UIManager::Checkbox(const char* label, bool* value)
	{
		return ImGui::Checkbox(label, value);
	}

	bool UIManager::SliderFloat(const char* label, float* value, float min, float max)
	{
		return ImGui::SliderFloat(label, value, min, max);
	}

	bool UIManager::DragFloat3(const char* label, float* values, float speed, float min, float max)
	{
		return ImGui::DragFloat3(label, values, speed, min, max);
	}

	bool UIManager::ColorEdit3(const char* label, float* color)
	{
		return ImGui::ColorEdit3(label, color);
	}

	bool UIManager::ColorEdit4(const char* label, float* color)
	{
		return ImGui::ColorEdit4(label, color);
	}

	bool UIManager::Selectable(const char* label, bool selected)
	{
		return ImGui::Selectable(label, selected);
	}

	// =========================================================================
	// Private Methods
	// =========================================================================

	void UIManager::Init(GLFWwindow* window)
	{
		IMGUI_CHECKVERSION();
		ImGui::CreateContext();
		ImGuiIO& io = ImGui::GetIO();
		(void)io;
		ImGui::StyleColorsDark();
		ImGui_ImplGlfw_InitForOpenGL(window, true);
		ImGui_ImplOpenGL3_Init("#version 460");
	}

	void UIManager::Shutdown()
	{
		ImGui_ImplOpenGL3_Shutdown();
		ImGui_ImplGlfw_Shutdown();
		ImGui::DestroyContext();
	}
}
```

> [!IMPORTANT]
> **Why wrappers?** ImGui uses global state (`GImGui` context). When ImGui is compiled into a DLL and the application calls `ImGui::` functions directly, you get separate contexts—causing crashes. By routing all ImGui calls through UIManager (which is in the DLL), we use the same context.

---

## Step 8: Update VizEngine.h

Add the Engine header to the public API.

**Update `VizEngine/src/VizEngine.h`:**

```cpp
// VizEngine/src/VizEngine.h

#pragma once

// =============================================================================
// VizEngine Public API
// =============================================================================
// This is the main header for VizEngine applications.
// Include this single header to access the entire public API.

// Core engine
#include "VizEngine/Application.h"
#include "VizEngine/Engine.h"
#include "VizEngine/Log.h"

// Subsystems accessible to applications
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

---

## Step 9: Update CMakeLists.txt

Add the new Engine files to the build.

**Update `VizEngine/CMakeLists.txt` sources:**

Add to `VIZENGINE_SOURCES`:
```cmake
src/VizEngine/Engine.cpp
```

Add to `VIZENGINE_HEADERS`:
```cmake
src/VizEngine/Engine.h
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| App crashes immediately | `CreateApplication` returns null | Check factory function returns valid pointer |
| ImGui context assertion | Direct ImGui calls from Sandbox | Use `UIManager` wrappers instead of `ImGui::` |
| `VP_CORE_ASSERT` failure | Accessing subsystems before `Init()` succeeds | Only access Engine subsystems inside lifecycle methods |
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
- Exception handling to ensure cleanup on errors

---

## What's Next

In **Chapter 24**, we'll migrate the Sandbox application to use the new Engine/Application architecture.

> **Next:** [Chapter 24: Sandbox Migration](24_SandboxMigration.md)

> **Previous:** [Chapter 22: Camera Controller](22_CameraController.md)
