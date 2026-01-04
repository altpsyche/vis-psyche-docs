\newpage

# Chapter 26: Advanced Lifecycle

Implement event propagation with the `Handled` flag and integrate ImGui event handling for proper layer ordering.

---

## Introduction

In the previous chapter, we built an event system where GLFW callbacks create events that flow through the Engine to the Application. However, there's a problem:

**Current Issue:**
```cpp
void Engine::OnEvent(Event& e)
{
    // Routes ALL events to application, regardless of Handled flag
    if (m_App)
    {
        m_App->OnEvent(e);
    }
}
```

The `Handled` flag exists on events but nothing respects it. This means:
- ImGui text fields receive key input, but so does the game
- Clicking on ImGui windows also moves the camera
- No way to "consume" an event

---

## Event Propagation

The `Handled` flag should stop event propagation once an event is consumed.

### Step 1: Check Handled Flag in Engine

**Update `VizEngine/src/VizEngine/Engine.cpp`:**

```cpp
void Engine::OnEvent(Event& e)
{
    // Give ImGui first chance to handle events
    m_UIManager->OnEvent(e);
    
    // Only forward to application if not consumed
    if (!e.Handled && m_App)
    {
        m_App->OnEvent(e);
    }
}
```

---

## Layer System

Events should flow through layers in order. ImGui (overlay) gets events first, then the application.

### Step 2: Add OnEvent to UIManager

**Update `VizEngine/src/VizEngine/GUI/UIManager.h`:**

```diff
 class VizEngine_API UIManager
 {
 public:
     UIManager(GLFWwindow* window);
     ~UIManager();
     
     void BeginFrame();
     void Render();
+    void OnEvent(Event& e);
     
     // ... existing methods ...
 };
```

**Update `VizEngine/src/VizEngine/GUI/UIManager.cpp`:**

```cpp
#include "VizEngine/Events/Event.h"

void UIManager::OnEvent(Event& e)
{
    ImGuiIO& io = ImGui::GetIO();
    
    // If ImGui wants keyboard, consume keyboard events
    if (io.WantCaptureKeyboard && e.IsInCategory(EventCategoryKeyboard))
    {
        e.Handled = true;
    }
    
    // If ImGui wants mouse, consume mouse events
    if (io.WantCaptureMouse && e.IsInCategory(EventCategoryMouse))
    {
        e.Handled = true;
    }
}
```

> [!NOTE]
> ImGui's `io.WantCaptureKeyboard` is true when a text input is focused. `io.WantCaptureMouse` is true when hovering/clicking on an ImGui window.

---

## Event Flow

After these changes, events flow through layers in order:

```
GLFW Callback
     ↓
GLFWManager (creates Event)
     ↓
Engine::OnEvent
     ↓
UIManager::OnEvent ← sets Handled if ImGui wants it
     ↓
if (!e.Handled):
     ↓
Application::OnEvent
```

---

## When to Mark Handled

| Scenario | Action |
|----------|--------|
| Typing in ImGui text field | Mark keyboard events Handled |
| Clicking ImGui button | Mark mouse events Handled |
| Window resize | Don't mark Handled (camera needs it) |
| ESC to close | Don't mark Handled in EventDispatcher |

Your event handlers return `bool`:
- Return `true` = event consumed, stops propagation
- Return `false` = event continues to other handlers

```cpp
dispatcher.Dispatch<KeyPressedEvent>(
    [](KeyPressedEvent& event) {
        if (event.GetKeyCode() == KeyCode::Escape)
        {
            // Handle ESC...
            return true;  // Consumed
        }
        return false;  // Let others handle it
    }
);
```

---

## Best Practices

### 1. Check Handled Before Processing

```cpp
void Sandbox::OnEvent(Event& e)
{
    if (e.Handled) return;  // Early exit if already consumed
    
    EventDispatcher dispatcher(e);
    // ... dispatch handlers ...
}
```

### 2. Use Categories for Filtering

```cpp
// Handle all mouse events at once
if (e.IsInCategory(EventCategoryMouse))
{
    // Process mouse event
}
```

### 3. Window Events Should Propagate

Window events like resize typically shouldn't be consumed—multiple systems may need them:

```cpp
dispatcher.Dispatch<WindowResizeEvent>(
    [this](WindowResizeEvent& event) {
        m_Camera.SetAspectRatio(event.GetWidth() / (float)event.GetHeight());
        return false;  // Don't consume - others may need it
    }
);
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Game moves while typing | ImGui not consuming events | Add `UIManager::OnEvent()` |
| Camera moves when clicking UI | Missing mouse capture check | Check `io.WantCaptureMouse` |
| Resize handler not called | Event incorrectly consumed | Return `false` from handlers |

---

## Testing

1. Run the application
2. Click inside an ImGui text field (if any) → Type → Game should not respond
3. Click outside ImGui → Type → Game should respond (e.g., WASD movement)
4. Hover over ImGui window → Scroll → ImGui scrolls, game doesn't zoom
5. Resize window → Both camera and ImGui update correctly

---

## Engine Stats Panel

Let's tie Part VIII together with an **Engine Stats Panel** that demonstrates all the concepts we've built:

| Feature | Part VIII Concept |
|---------|-------------------|
| FPS / Delta Time | `Engine::GetDeltaTime()` from Chapter 23 |
| Frame Counter | Game loop from Chapter 23 |
| Window Dimensions | Resize events from Chapter 25-26 |
| F1 Toggle | Event-driven hotkey from Chapter 25 |

### Step 1: Add Member Variables

**Update `Sandbox/src/SandboxApp.cpp`:**

Add these member variables to the Sandbox class:

```cpp
private:
    // ... existing members ...

    // Engine stats
    bool m_ShowEngineStats = true;
    uint64_t m_FrameCount = 0;
    float m_FpsUpdateTimer = 0.0f;
    float m_CurrentFPS = 0.0f;
    int m_WindowWidth = 800;
    int m_WindowHeight = 800;
```

### Step 2: Update OnUpdate()

Calculate FPS using delta time:

```cpp
void OnUpdate(float deltaTime) override
{
    // =========================================================================
    // Engine Stats
    // =========================================================================
    m_FrameCount++;
    m_FpsUpdateTimer += deltaTime;
    if (m_FpsUpdateTimer >= 0.5f)  // Update every 0.5 seconds
    {
        m_CurrentFPS = 1.0f / deltaTime;
        m_FpsUpdateTimer = 0.0f;
    }

    // ... existing camera controller code ...
}
```

### Step 3: Update OnEvent()

Track window dimensions and add F1 toggle:

```cpp
void OnEvent(VizEngine::Event& e) override
{
    VizEngine::EventDispatcher dispatcher(e);

    // Handle window resize - update camera and track dimensions
    dispatcher.Dispatch<VizEngine::WindowResizeEvent>(
        [this](VizEngine::WindowResizeEvent& event) {
            m_WindowWidth = event.GetWidth();
            m_WindowHeight = event.GetHeight();

            if (m_WindowWidth > 0 && m_WindowHeight > 0)
            {
                float aspect = static_cast<float>(m_WindowWidth)
                             / static_cast<float>(m_WindowHeight);
                m_Camera.SetAspectRatio(aspect);
            }
            return false;
        }
    );

    // F1 toggles Engine Stats panel
    dispatcher.Dispatch<VizEngine::KeyPressedEvent>(
        [this](VizEngine::KeyPressedEvent& event) {
            if (event.GetKeyCode() == VizEngine::KeyCode::F1 && !event.IsRepeat())
            {
                m_ShowEngineStats = !m_ShowEngineStats;
                VP_INFO("Engine Stats: {}", m_ShowEngineStats ? "ON" : "OFF");
                return true;
            }
            return false;
        }
    );
}
```

### Step 4: Add Engine Stats Panel

Add a new ImGui panel in `OnImGuiRender()`:

```cpp
void OnImGuiRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& uiManager = engine.GetUIManager();

    // =========================================================================
    // Engine Stats Panel (toggle with F1)
    // =========================================================================
    if (m_ShowEngineStats)
    {
        uiManager.StartWindow("Engine Stats");

        uiManager.Text("FPS: %.1f", m_CurrentFPS);
        uiManager.Text("Delta: %.2f ms", engine.GetDeltaTime() * 1000.0f);
        uiManager.Text("Frame: %llu", m_FrameCount);
        uiManager.Separator();
        uiManager.Text("Window: %d x %d", m_WindowWidth, m_WindowHeight);
        uiManager.Separator();
        uiManager.Text("Press F1 to toggle");

        uiManager.EndWindow();
    }

    // ... existing panels ...
}
```

### Result

The Engine Stats panel provides visual proof that Part VIII is working:

- **FPS/Delta**: Engine's game loop timing
- **Frame count**: Loop iterations
- **Window dimensions**: Real-time event updates on resize
- **F1 toggle**: Event-driven input without polling

---

## Milestone

**Part VIII Complete**

You have:
- Event flow with proper layer ordering
- ImGui event consumption
- Handled flag that stops propagation
- Engine Stats panel demonstrating all concepts

---

## What's Next

Part VIII: Application Lifecycle is complete! The engine now has:
- Engine singleton with game loop
- Application lifecycle methods
- Event system with propagation

In **Part IX**, we'll explore advanced OpenGL techniques like framebuffers and shadow mapping.

> **Next:** [Chapter 27: Framebuffers](27_Framebuffers.md)

> **Previous:** [Chapter 25: Event System](25_EventSystem.md)

