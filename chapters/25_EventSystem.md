\newpage

# Chapter 25: Event System

Implement an event-driven architecture to handle window and input events through callbacks.

---

## Introduction

So far, we've used polling for input—checking button states every frame via `Input::IsKeyHeld()`. This works well for continuous actions like camera movement but has limitations:

**Problems with polling only:**
- Window resize doesn't update camera aspect ratio (objects stretch!)
- Can't react to events between frames
- Tightly couples input handling to the game loop

**Solution:** An event system that notifies the application when something happens.

### Polling vs Events

| Aspect | Polling | Events |
|--------|---------|--------|
| **Approach** | Check state every frame | React when something happens |
| **Best for** | Continuous input (WASD movement) | Discrete actions (resize, key press) |
| **Frame-independent** | No | Yes |
| **Example** | Camera controller | Window resize handling |

We'll keep both—polling for real-time input, events for system notifications.

---

## Architecture Overview

```
GLFW Callback → GLFWManager → Create Event → Engine → Application::OnEvent()
                                                          ↓
                                              EventDispatcher → Handler Lambda
```

**Event flow:**
1. GLFW fires a callback (resize, key press, etc.)
2. GLFWManager creates an Event object
3. Event is passed to Engine
4. Engine calls `app->OnEvent(event)`
5. Application uses EventDispatcher to handle specific event types

---

## Step 1: Create Event Base Class

Create the events directory and base class.

**Create `VizEngine/src/VizEngine/Events/Event.h`:**

```cpp
// VizEngine/src/VizEngine/Events/Event.h

#pragma once

#include <string>
#include <sstream>
#include <functional>
#include "VizEngine/Core.h"

namespace VizEngine
{
    // Event types
    enum class EventType
    {
        None = 0,
        WindowClose, WindowResize, WindowFocus, WindowLostFocus,
        KeyPressed, KeyReleased, KeyTyped,
        MouseButtonPressed, MouseButtonReleased, MouseMoved, MouseScrolled
    };

    // Event categories (bit flags for filtering)
    enum EventCategory
    {
        None = 0,
        EventCategoryApplication = (1 << 0),
        EventCategoryInput       = (1 << 1),
        EventCategoryKeyboard    = (1 << 2),
        EventCategoryMouse       = (1 << 3),
        EventCategoryMouseButton = (1 << 4)
    };

    // Abstract base class for all events
    class VizEngine_API Event
    {
    public:
        virtual ~Event() = default;

        virtual EventType GetEventType() const = 0;
        virtual const char* GetName() const = 0;
        virtual int GetCategoryFlags() const = 0;
        virtual std::string ToString() const { return GetName(); }

        bool IsInCategory(EventCategory category) const
        {
            return GetCategoryFlags() & category;
        }

        bool Handled = false;
    };

    // Type-safe event dispatcher
    class EventDispatcher
    {
    public:
        EventDispatcher(Event& event) : m_Event(event) {}

        template<typename T, typename F>
        bool Dispatch(const F& func)
        {
            if (m_Event.GetEventType() == T::GetStaticType())
            {
                m_Event.Handled |= func(static_cast<T&>(m_Event));
                return true;
            }
            return false;
        }

    private:
        Event& m_Event;
    };

    using EventCallbackFn = std::function<void(Event&)>;
}

// Macros to reduce boilerplate in event classes
#define EVENT_CLASS_TYPE(type) \
    static EventType GetStaticType() { return EventType::type; } \
    virtual EventType GetEventType() const override { return GetStaticType(); } \
    virtual const char* GetName() const override { return #type; }

#define EVENT_CLASS_CATEGORY(category) \
    virtual int GetCategoryFlags() const override { return category; }
```

> [!NOTE]
> **EventDispatcher Magic**: The `Dispatch<T>()` method uses templates to call your handler only if the event matches type `T`. The static type check happens at compile time, making this pattern both type-safe and efficient.

---

## Step 2: Create Application Events

Window-related events like resize and close.

**Create `VizEngine/src/VizEngine/Events/ApplicationEvent.h`:**

```cpp
// VizEngine/src/VizEngine/Events/ApplicationEvent.h

#pragma once

#include "Event.h"

namespace VizEngine
{
    class VizEngine_API WindowResizeEvent : public Event
    {
    public:
        WindowResizeEvent(int width, int height)
            : m_Width(width), m_Height(height) {}

        int GetWidth() const { return m_Width; }
        int GetHeight() const { return m_Height; }

        std::string ToString() const override
        {
            std::stringstream ss;
            ss << "WindowResizeEvent: " << m_Width << ", " << m_Height;
            return ss.str();
        }

        EVENT_CLASS_TYPE(WindowResize)
        EVENT_CLASS_CATEGORY(EventCategoryApplication)

    private:
        int m_Width, m_Height;
    };

    class VizEngine_API WindowCloseEvent : public Event
    {
    public:
        WindowCloseEvent() = default;

        EVENT_CLASS_TYPE(WindowClose)
        EVENT_CLASS_CATEGORY(EventCategoryApplication)
    };

    class VizEngine_API WindowFocusEvent : public Event
    {
    public:
        WindowFocusEvent() = default;

        EVENT_CLASS_TYPE(WindowFocus)
        EVENT_CLASS_CATEGORY(EventCategoryApplication)
    };

    class VizEngine_API WindowLostFocusEvent : public Event
    {
    public:
        WindowLostFocusEvent() = default;

        EVENT_CLASS_TYPE(WindowLostFocus)
        EVENT_CLASS_CATEGORY(EventCategoryApplication)
    };
}
```

---

## Step 3: Create Key Events

Keyboard events for press, release, and typed characters.

**Create `VizEngine/src/VizEngine/Events/KeyEvent.h`:**

```cpp
// VizEngine/src/VizEngine/Events/KeyEvent.h

#pragma once

#include "Event.h"
#include "VizEngine/Core/Input.h"

namespace VizEngine
{
    class VizEngine_API KeyEvent : public Event
    {
    public:
        KeyCode GetKeyCode() const { return m_KeyCode; }

        EVENT_CLASS_CATEGORY(EventCategoryKeyboard | EventCategoryInput)

    protected:
        KeyEvent(KeyCode keycode) : m_KeyCode(keycode) {}
        KeyCode m_KeyCode;
    };

    class VizEngine_API KeyPressedEvent : public KeyEvent
    {
    public:
        KeyPressedEvent(KeyCode keycode, bool isRepeat = false)
            : KeyEvent(keycode), m_IsRepeat(isRepeat) {}

        bool IsRepeat() const { return m_IsRepeat; }

        std::string ToString() const override
        {
            std::stringstream ss;
            ss << "KeyPressedEvent: " << static_cast<int>(m_KeyCode)
               << (m_IsRepeat ? " (repeat)" : "");
            return ss.str();
        }

        EVENT_CLASS_TYPE(KeyPressed)

    private:
        bool m_IsRepeat;
    };

    class VizEngine_API KeyReleasedEvent : public KeyEvent
    {
    public:
        KeyReleasedEvent(KeyCode keycode) : KeyEvent(keycode) {}

        std::string ToString() const override
        {
            std::stringstream ss;
            ss << "KeyReleasedEvent: " << static_cast<int>(m_KeyCode);
            return ss.str();
        }

        EVENT_CLASS_TYPE(KeyReleased)
    };

    class VizEngine_API KeyTypedEvent : public KeyEvent
    {
    public:
        KeyTypedEvent(KeyCode keycode) : KeyEvent(keycode) {}

        EVENT_CLASS_TYPE(KeyTyped)
    };
}
```

---

## Step 4: Create Mouse Events

Mouse movement, scroll, and button events.

**Create `VizEngine/src/VizEngine/Events/MouseEvent.h`:**

```cpp
// VizEngine/src/VizEngine/Events/MouseEvent.h

#pragma once

#include "Event.h"
#include "VizEngine/Core/Input.h"

namespace VizEngine
{
    class VizEngine_API MouseMovedEvent : public Event
    {
    public:
        MouseMovedEvent(float x, float y) : m_MouseX(x), m_MouseY(y) {}

        float GetX() const { return m_MouseX; }
        float GetY() const { return m_MouseY; }

        std::string ToString() const override
        {
            std::stringstream ss;
            ss << "MouseMovedEvent: " << m_MouseX << ", " << m_MouseY;
            return ss.str();
        }

        EVENT_CLASS_TYPE(MouseMoved)
        EVENT_CLASS_CATEGORY(EventCategoryMouse | EventCategoryInput)

    private:
        float m_MouseX, m_MouseY;
    };

    class VizEngine_API MouseScrolledEvent : public Event
    {
    public:
        MouseScrolledEvent(float xOffset, float yOffset)
            : m_XOffset(xOffset), m_YOffset(yOffset) {}

        float GetXOffset() const { return m_XOffset; }
        float GetYOffset() const { return m_YOffset; }

        std::string ToString() const override
        {
            std::stringstream ss;
            ss << "MouseScrolledEvent: " << m_XOffset << ", " << m_YOffset;
            return ss.str();
        }

        EVENT_CLASS_TYPE(MouseScrolled)
        EVENT_CLASS_CATEGORY(EventCategoryMouse | EventCategoryInput)

    private:
        float m_XOffset, m_YOffset;
    };

    class VizEngine_API MouseButtonEvent : public Event
    {
    public:
        MouseCode GetMouseButton() const { return m_Button; }

        EVENT_CLASS_CATEGORY(EventCategoryMouse | EventCategoryInput | EventCategoryMouseButton)

    protected:
        MouseButtonEvent(MouseCode button) : m_Button(button) {}
        MouseCode m_Button;
    };

    class VizEngine_API MouseButtonPressedEvent : public MouseButtonEvent
    {
    public:
        MouseButtonPressedEvent(MouseCode button) : MouseButtonEvent(button) {}

        EVENT_CLASS_TYPE(MouseButtonPressed)
    };

    class VizEngine_API MouseButtonReleasedEvent : public MouseButtonEvent
    {
    public:
        MouseButtonReleasedEvent(MouseCode button) : MouseButtonEvent(button) {}

        EVENT_CLASS_TYPE(MouseButtonReleased)
    };
}
```

---

## Step 5: Update Application

Add `OnEvent()` to the application lifecycle.

**Update `VizEngine/src/VizEngine/Application.h`:**

```diff
 #pragma once
 
 #include "Core.h"
 
 namespace VizEngine
 {
     struct EngineConfig;
+    class Event;
 
     class VizEngine_API Application
     {
     public:
         Application();
         virtual ~Application();
 
         Application(const Application&) = delete;
         Application& operator=(const Application&) = delete;
 
         virtual void OnCreate() {}
         virtual void OnUpdate(float deltaTime) { (void)deltaTime; }
         virtual void OnRender() {}
         virtual void OnImGuiRender() {}
+        virtual void OnEvent(Event& e) { (void)e; }
         virtual void OnDestroy() {}
     };
 
     Application* CreateApplication(EngineConfig& config);
 }
```

> [!IMPORTANT]
> `OnEvent()` is called before `OnUpdate()` each frame for any pending events. The default implementation does nothing—override it to handle events in your application.

---

## Step 6: Update GLFWManager

Add event callback storage and update callbacks to fire events.

**Update `VizEngine/src/VizEngine/OpenGL/GLFWManager.h`:**

```diff
 #pragma once
 
+#include "VizEngine/Events/Event.h"
 #include <GLFW/glfw3.h>
 #include <string>
 
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
 
+        void SetEventCallback(const EventCallbackFn& callback) { m_EventCallback = callback; }
+
+        int GetWidth() const { return m_Width; }
+        int GetHeight() const { return m_Height; }
 
     private:
         GLFWwindow* m_Window;
+        int m_Width, m_Height;
+        EventCallbackFn m_EventCallback;
 
         void Init(unsigned int width, unsigned int height, const std::string& title);
         void Shutdown();
 
         static void FramebufferSizeCallback(GLFWwindow* window, int width, int height);
         static void KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods);
+        static void MouseButtonCallback(GLFWwindow* window, int button, int action, int mods);
+        static void ScrollCallback(GLFWwindow* window, double xoffset, double yoffset);
+        static void CursorPosCallback(GLFWwindow* window, double xpos, double ypos);
+        static void WindowCloseCallback(GLFWwindow* window);
     };
 }
```

**Update `VizEngine/src/VizEngine/OpenGL/GLFWManager.cpp`:**

```cpp
// Add includes at the top
#include "VizEngine/Events/ApplicationEvent.h"
#include "VizEngine/Events/KeyEvent.h"
#include "VizEngine/Events/MouseEvent.h"

// Update Init() to register callbacks and store user pointer
void GLFWManager::Init(unsigned int width, unsigned int height, const std::string& title)
{
    // ... existing GLFW init code ...
    
    m_Width = width;
    m_Height = height;
    
    // Store this pointer for callbacks
    glfwSetWindowUserPointer(m_Window, this);
    
    // Register callbacks
    glfwSetFramebufferSizeCallback(m_Window, FramebufferSizeCallback);
    glfwSetKeyCallback(m_Window, KeyCallback);
    glfwSetMouseButtonCallback(m_Window, MouseButtonCallback);
    glfwSetScrollCallback(m_Window, ScrollCallback);
    glfwSetCursorPosCallback(m_Window, CursorPosCallback);
    glfwSetWindowCloseCallback(m_Window, WindowCloseCallback);
    
    // ... rest of init ...
}

// Update FramebufferSizeCallback
void GLFWManager::FramebufferSizeCallback(GLFWwindow* window, int width, int height)
{
    glViewport(0, 0, width, height);
    
    auto* manager = static_cast<GLFWManager*>(glfwGetWindowUserPointer(window));
    if (manager)
    {
        manager->m_Width = width;
        manager->m_Height = height;
        
        if (manager->m_EventCallback)
        {
            WindowResizeEvent event(width, height);
            manager->m_EventCallback(event);
        }
    }
}

// Update KeyCallback
void GLFWManager::KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods)
{
    (void)scancode;
    (void)mods;
    
    auto* manager = static_cast<GLFWManager*>(glfwGetWindowUserPointer(window));
    if (!manager || !manager->m_EventCallback)
        return;
    
    switch (action)
    {
        case GLFW_PRESS:
        {
            KeyPressedEvent event(static_cast<KeyCode>(key), false);
            manager->m_EventCallback(event);
            break;
        }
        case GLFW_RELEASE:
        {
            KeyReleasedEvent event(static_cast<KeyCode>(key));
            manager->m_EventCallback(event);
            break;
        }
        case GLFW_REPEAT:
        {
            KeyPressedEvent event(static_cast<KeyCode>(key), true);
            manager->m_EventCallback(event);
            break;
        }
    }
}

// Add new callbacks
void GLFWManager::MouseButtonCallback(GLFWwindow* window, int button, int action, int mods)
{
    (void)mods;
    
    auto* manager = static_cast<GLFWManager*>(glfwGetWindowUserPointer(window));
    if (!manager || !manager->m_EventCallback)
        return;
    
    switch (action)
    {
        case GLFW_PRESS:
        {
            MouseButtonPressedEvent event(static_cast<MouseCode>(button));
            manager->m_EventCallback(event);
            break;
        }
        case GLFW_RELEASE:
        {
            MouseButtonReleasedEvent event(static_cast<MouseCode>(button));
            manager->m_EventCallback(event);
            break;
        }
    }
}

void GLFWManager::ScrollCallback(GLFWwindow* window, double xoffset, double yoffset)
{
    auto* manager = static_cast<GLFWManager*>(glfwGetWindowUserPointer(window));
    if (manager && manager->m_EventCallback)
    {
        MouseScrolledEvent event(static_cast<float>(xoffset), static_cast<float>(yoffset));
        manager->m_EventCallback(event);
    }
}

void GLFWManager::CursorPosCallback(GLFWwindow* window, double xpos, double ypos)
{
    auto* manager = static_cast<GLFWManager*>(glfwGetWindowUserPointer(window));
    if (manager && manager->m_EventCallback)
    {
        MouseMovedEvent event(static_cast<float>(xpos), static_cast<float>(ypos));
        manager->m_EventCallback(event);
    }
}

void GLFWManager::WindowCloseCallback(GLFWwindow* window)
{
    auto* manager = static_cast<GLFWManager*>(glfwGetWindowUserPointer(window));
    if (manager && manager->m_EventCallback)
    {
        WindowCloseEvent event;
        manager->m_EventCallback(event);
    }
}
```

> [!NOTE]
> Previously, the scroll callback was registered in `Input::Init()`. Now that GLFWManager handles all GLFW callbacks for event dispatch, we centralize callback registration here. To maintain polling support (`Input::GetScrollDelta()`), GLFWManager should also forward scroll data to `Input::ScrollCallback()`.

---

## Step 7: Update Engine

Store the application pointer and wire events.

**Update `VizEngine/src/VizEngine/Engine.h`:**

```diff
 class VizEngine_API Engine
 {
 public:
     static Engine& Get();
     
     void Run(Application* app, const EngineConfig& config);
     void Quit();
     
     // ... existing getters ...
     
+    void OnEvent(Event& e);
 
 private:
     Engine() = default;
     ~Engine() = default;
     
     bool Init(const EngineConfig& config);
     void Shutdown();
     
+    Application* m_App = nullptr;
     // ... existing members ...
 };
```

**Update `VizEngine/src/VizEngine/Engine.cpp`:**

```cpp
// Add include
#include "Events/Event.h"

// Update Run() to store app and set callback
void Engine::Run(Application* app, const EngineConfig& config)
{
    if (!app)
    {
        VP_CORE_ERROR("Engine::Run called with null application!");
        return;
    }
    
    m_App = app;  // Store for event routing
    
    if (!Init(config))
    {
        VP_CORE_ERROR("Engine initialization failed!");
        return;
    }
    
    // ... rest of Run() ...
}

// Update Init() to wire callback
bool Engine::Init(const EngineConfig& config)
{
    // ... existing guard and window creation ...
    
    // Wire event callback
    m_Window->SetEventCallback([this](Event& e) {
        OnEvent(e);
    });
    
    // ... rest of Init() ...
}

// Add OnEvent()
void Engine::OnEvent(Event& e)
{
    // Route to application
    if (m_App)
    {
        m_App->OnEvent(e);
    }
}
```

---

## Step 8: Update Sandbox

Handle window resize to fix camera aspect ratio.

**Update `Sandbox/src/SandboxApp.cpp`:**

```cpp
// Add includes
#include <VizEngine/Events/ApplicationEvent.h>
#include <VizEngine/Events/KeyEvent.h>

class Sandbox : public VizEngine::Application
{
public:
    // ... existing methods ...
    
    void OnEvent(VizEngine::Event& e) override
    {
        VizEngine::EventDispatcher dispatcher(e);
        
        // Handle window resize
        dispatcher.Dispatch<VizEngine::WindowResizeEvent>(
            [this](VizEngine::WindowResizeEvent& event) {
                if (event.GetWidth() > 0 && event.GetHeight() > 0)
                {
                    float aspect = static_cast<float>(event.GetWidth()) 
                                 / static_cast<float>(event.GetHeight());
                    m_Camera.SetAspectRatio(aspect);
                }
                return false;  // Don't consume, allow propagation
            }
        );
        
        // Example: Handle F1 for debug toggle
        dispatcher.Dispatch<VizEngine::KeyPressedEvent>(
            [](VizEngine::KeyPressedEvent& event) {
                if (event.GetKeyCode() == VizEngine::KeyCode::F1)
                {
                    VP_INFO("F1 pressed - debug toggle!");
                    return true;  // Consumed
                }
                return false;
            }
        );
    }
    
    // ... rest of class ...
};
```

---

## Lifecycle Order

Events are processed during input handling, before game logic:

```
Frame Start
├── glfwPollEvents()         ← GLFW callbacks fire here
│   └── Event callbacks      ← Your OnEvent() called
├── Input::Update()
├── OnUpdate(deltaTime)
├── OnRender()
├── OnImGuiRender()
└── SwapBuffers
Frame End
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Events not firing | Callback not set | Verify `SetEventCallback()` in Engine::Init |
| Camera still stretches | OnEvent not overridden | Add `OnEvent` override to Sandbox |
| Crash in callback | Null manager pointer | Check `glfwSetWindowUserPointer` call |
| Handler not called | Wrong event type | Verify `Dispatch<CorrectType>()` |

---

## Milestone

**Event System Complete**

You have:
- Event base class with polymorphic dispatch
- Application, Key, and Mouse event types
- EventDispatcher for type-safe handling
- GLFWManager firing events from callbacks
- Engine routing events to Application
- Window resize properly updating camera

---

## Summary

| Component | Purpose |
|-----------|---------|
| `Event.h` | Base class, EventDispatcher, macros |
| `ApplicationEvent.h` | WindowResize, WindowClose, Focus events |
| `KeyEvent.h` | KeyPressed, KeyReleased, KeyTyped |
| `MouseEvent.h` | MouseMoved, MouseScrolled, MouseButton events |
| `Application::OnEvent()` | Application-level event handler |
| `Engine::OnEvent()` | Routes events to application |

---

## What's Next

In **Chapter 26**, we'll explore advanced lifecycle patterns including OnResize helpers and best practices for organizing event handlers.

> **Next:** Chapter 26: Advanced Lifecycle

> **Previous:** [Chapter 24: Sandbox Migration](24_SandboxMigration.md)
