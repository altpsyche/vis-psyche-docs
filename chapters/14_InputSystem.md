\newpage

# Chapter 14: Input System

## The Problem

Currently, input handling in VizPsyche is minimal. In `GLFWManager::ProcessInput()`, there's just one check:

```cpp
if (glfwGetKey(m_Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
{
    glfwSetWindowShouldClose(m_Window, true);
}
```

This approach has problems:

| Issue | Problem |
|-------|---------|
| **Scattered checks** | GLFW calls spread throughout codebase |
| **No edge detection** | Can't tell "just pressed" from "held down" |
| **Platform coupling** | Game logic directly uses GLFW codes |
| **No mouse delta** | Can't implement camera look-around |

This chapter builds a proper `Input` class that solves all these problems.

---

## Polling vs. Events

There are two approaches to input handling:

| Polling | Events (Callbacks) |
|---------|-------------------|
| Check state every frame | React when input occurs |
| "Is W pressed right now?" | "W was just pressed" |
| Simple, predictable | More complex timing |
| **Preferred for games** | Better for UI/text input |

Most game engines use **polling** for gameplay input. Why?

- Game logic runs every frame anyway
- Input state is checked at a consistent point in the loop
- Easier to reason about than async callbacks

Our `Input` class uses polling with state tracking for edge detection.

---

## Edge Detection: Press, Hold, Release

The key insight is tracking **state changes across frames**:

```
Frame:     1    2    3    4    5    6    7
Key W:     -    -    [P]  [H]  [H]  [R]  -
                     ↑         ↑    ↑
                  Pressed    Held  Released
```

| State | Meaning | Use Case |
|-------|---------|----------|
| **Pressed** | First frame key is down | Jump, fire single shot |
| **Held** | Key is currently down | Move, charge weapon |
| **Released** | First frame key is up | Release charged attack |

Implementation:

```cpp
bool IsKeyPressed(KeyCode key)   // current && !previous
bool IsKeyHeld(KeyCode key)      // current
bool IsKeyReleased(KeyCode key)  // !current && previous
```

---

## The Input Class

### Design

Static class with frame-based state tracking:

```cpp
class Input
{
public:
    static void Init(GLFWwindow* window);
    static void Update();  // Call once per frame
    
    // Keyboard
    static bool IsKeyPressed(KeyCode key);
    static bool IsKeyHeld(KeyCode key);
    static bool IsKeyReleased(KeyCode key);
    
    // Mouse buttons
    static bool IsMouseButtonPressed(MouseCode button);
    static bool IsMouseButtonHeld(MouseCode button);
    static bool IsMouseButtonReleased(MouseCode button);
    
    // Mouse position
    static glm::vec2 GetMousePosition();
    static glm::vec2 GetMouseDelta();
    
    // Scroll wheel
    static float GetScrollDelta();
};
```

### Why Static?

There's exactly one input system per application. A static class:

- Provides global access without singletons
- Has no instance management overhead
- Is a proven pattern (Hazel, SDL)

---

## Key Codes

Abstract GLFW key codes to decouple game code from the platform:

```cpp
enum class KeyCode : int
{
    // Common keys
    Space = 32,
    A = 65, B, C, D, E, F, G, H, I, J, K, L, M,
    N, O, P, Q, R, S, T, U, V, W, X, Y, Z,
    
    // Arrow keys
    Right = 262, Left = 263, Down = 264, Up = 265,
    
    // Modifiers
    LeftShift = 340, LeftControl = 341, LeftAlt = 342,
    
    // Function keys
    Escape = 256, Enter = 257, Tab = 258,
    F1 = 290, F2, F3, /* ... */
};
```

Usage:

```cpp
if (Input::IsKeyHeld(KeyCode::W))
{
    // Move forward
}
```

---

## Mouse Codes

Similarly for mouse buttons:

```cpp
enum class MouseCode : int
{
    Left = 0,
    Right = 1,
    Middle = 2
};
```

Usage:

```cpp
if (Input::IsMouseButtonPressed(MouseCode::Left))
{
    // Click action
}
```

---

## Implementation

### Header (Input.h)

```cpp
#pragma once
#include "VizEngine/Core.h"
#include <glm/glm.hpp>

struct GLFWwindow;

namespace VizEngine
{
    enum class KeyCode : int { /* ... */ };
    enum class MouseCode : int { /* ... */ };

    class VizEngine_API Input
    {
    public:
        static void Init(GLFWwindow* window);
        static void Update();
        
        static bool IsKeyPressed(KeyCode key);
        static bool IsKeyHeld(KeyCode key);
        static bool IsKeyReleased(KeyCode key);
        
        static bool IsMouseButtonPressed(MouseCode button);
        static bool IsMouseButtonHeld(MouseCode button);
        static bool IsMouseButtonReleased(MouseCode button);
        
        static glm::vec2 GetMousePosition();
        static glm::vec2 GetMouseDelta();
        static float GetScrollDelta();

    private:
        static GLFWwindow* s_Window;
        static bool s_CurrentKeys[512];
        static bool s_PreviousKeys[512];
        static bool s_CurrentMouseButtons[8];
        static bool s_PreviousMouseButtons[8];
        static glm::vec2 s_MousePosition;
        static glm::vec2 s_LastMousePosition;
        static float s_ScrollDelta;
        
        static void ScrollCallback(GLFWwindow* window, double x, double y);
    };
}
```

### Source (Input.cpp)

```cpp
void Input::Init(GLFWwindow* window)
{
    s_Window = window;
    glfwSetScrollCallback(window, ScrollCallback);
    
    // Initialize mouse position
    double x, y;
    glfwGetCursorPos(window, &x, &y);
    s_MousePosition = glm::vec2(static_cast<float>(x), static_cast<float>(y));
    s_LastMousePosition = s_MousePosition;
}

void Input::Update()
{
    // Copy current to previous
    std::memcpy(s_PreviousKeys, s_CurrentKeys, sizeof(s_CurrentKeys));
    std::memcpy(s_PreviousMouseButtons, s_CurrentMouseButtons, sizeof(s_CurrentMouseButtons));
    
    // Poll current key states
    for (int key = 0; key < 512; key++)
        s_CurrentKeys[key] = (glfwGetKey(s_Window, key) == GLFW_PRESS);
    
    // Poll current mouse button states
    for (int btn = 0; btn < 8; btn++)
        s_CurrentMouseButtons[btn] = (glfwGetMouseButton(s_Window, btn) == GLFW_PRESS);
    
    // Update mouse position
    s_LastMousePosition = s_MousePosition;
    double x, y;
    glfwGetCursorPos(s_Window, &x, &y);
    s_MousePosition = glm::vec2(static_cast<float>(x), static_cast<float>(y));
}
```

### Edge Detection

```cpp
bool Input::IsKeyPressed(KeyCode key)
{
    int k = static_cast<int>(key);
    return s_CurrentKeys[k] && !s_PreviousKeys[k];
}

bool Input::IsKeyHeld(KeyCode key)
{
    int k = static_cast<int>(key);
    return s_CurrentKeys[k];
}

bool Input::IsKeyReleased(KeyCode key)
{
    int k = static_cast<int>(key);
    return !s_CurrentKeys[k] && s_PreviousKeys[k];
}
```

### Mouse Delta

```cpp
glm::vec2 Input::GetMouseDelta()
{
    return s_MousePosition - s_LastMousePosition;
}
```

### Scroll Wheel (Callback-Based)

Scroll wheel is different - GLFW provides deltas via callback:

```cpp
void Input::ScrollCallback(GLFWwindow* window, double xoffset, double yoffset)
{
    s_ScrollDelta += static_cast<float>(yoffset);
}

float Input::GetScrollDelta()
{
    float delta = s_ScrollDelta;
    s_ScrollDelta = 0.0f;  // Reset after reading
    return delta;
}
```

---

## Integration

### Initializing Input

In `GLFWManager::Init()`, after creating the window:

```cpp
// In GLFWManager::Init()
glfwMakeContextCurrent(m_Window);
glfwSetFramebufferSizeCallback(m_Window, FramebufferSizeCallback);
glfwSetKeyCallback(m_Window, KeyCallback);

// Initialize input system
Input::Init(m_Window);
```

### Updating Each Frame

In `GLFWManager::ProcessInput()`:

```cpp
void GLFWManager::ProcessInput()
{
    // Update input state first
    Input::Update();
    
    // Handle escape key to close window
    if (Input::IsKeyPressed(KeyCode::Escape))
    {
        glfwSetWindowShouldClose(m_Window, true);
    }
}
```

### Debug Logging Example

Add to `Application.cpp` to verify input is working:

```cpp
#include "Core/Input.h"

// In the main loop, after window.ProcessInput():

// --- Debug: Test Input System ---
if (Input::IsKeyPressed(KeyCode::Space))
    VP_INFO("Space PRESSED!");

if (Input::IsKeyHeld(KeyCode::W))
    VP_INFO("W held...");

if (Input::IsMouseButtonPressed(MouseCode::Left))
    VP_INFO("Left click at: ({}, {})", 
        Input::GetMousePosition().x, Input::GetMousePosition().y);

float scroll = Input::GetScrollDelta();
if (scroll != 0.0f)
    VP_INFO("Scroll: {}", scroll);
```

Run the app and watch the console output as you interact.

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Input not responding | Forgot `Input::Update()` | Call it first each frame |
| Key always "pressed" | Using `IsKeyHeld` instead of `IsKeyPressed` | Use correct function for use case |
| Large mouse delta on start | First frame has no previous position | Handle first-frame case |
| ImGui captures input | ImGui handles input before you | Check `ImGui::GetIO().WantCaptureKeyboard` |
| Scroll not working | Callback not registered | Ensure `Input::Init()` is called |

### ImGui Input Conflict

When ImGui wants keyboard input (e.g., typing in a text field), you should skip game input:

```cpp
if (!ImGui::GetIO().WantCaptureKeyboard)
{
    // Handle game keyboard input
}

if (!ImGui::GetIO().WantCaptureMouse)
{
    // Handle game mouse input
}
```

---

## Key Takeaways

1. **Polling** - Check input state each frame, not via callbacks
2. **Edge detection** - Track previous frame state to detect press/release
3. **Static class** - One input system, global access, proven pattern
4. **Key/Mouse codes** - Abstract platform-specific codes
5. **Mouse delta** - Difference from last frame, not absolute position
6. **Scroll callback** - Events accumulate, reset after reading

---

## Checkpoint

This chapter covered keyboard and mouse input:

**Key Concepts:**
| Concept | Description |
|---------|-------------|
| Polling vs Events | Polling preferred for game input |
| Edge Detection | IsKeyPressed = current && !previous |
| Mouse Delta | Position change since last frame |
| Static Class | Proven pattern for input systems |

**Files:**
- `VizEngine/Core/Input.h`
- `VizEngine/Core/Input.cpp`

**Checkpoint:** Create Input class, initialize in GLFWManager, add WASD camera movement, verify movement works.

---

## Exercise

1. Add a "sprint" modifier - hold Shift to move faster
2. Implement toggle mode - press a key to toggle a state
3. Add double-click detection for mouse buttons
4. Create a simple "input log" ImGui window showing current input state

---

## Future: Action Mapping

The current system works well but has a limitation: keys are hardcoded. A future "Input II" chapter will cover action mapping:

```cpp
// Future pattern
InputAction moveForward;
moveForward.BindKey(KeyCode::W);
moveForward.BindGamepadAxis(GamepadAxis::LeftY, -1.0f);

if (Input::GetActionValue(moveForward) > 0.0f) { /* move */ }
```

This enables:
- Remappable controls
- Gamepad support
- Multiple bindings per action

For now, direct key checks are sufficient.

---

> **Next:** [Chapter 15: Advanced OpenGL](15_AdvancedOpenGL.md) - Framebuffers, depth/stencil testing, cubemaps.

> **Reference:** For the complete Input implementation, see [Appendix A: Code Reference](A_Reference.md#input).

