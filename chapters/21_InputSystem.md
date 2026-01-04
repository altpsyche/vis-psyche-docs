\newpage

# Chapter 21: Input System

Create an `Input` class with keyboard and mouse polling using typed enums for key codes.

---

## Design

| Feature | Purpose |
|---------|---------|
| `KeyCode` enum | Type-safe key identifiers |
| `MouseCode` enum | Type-safe mouse button identifiers |
| Edge detection | `IsKeyPressed` vs `IsKeyHeld` |
| Static API | No instance needed |

---

## Step 1: Create Input.h

**Create `VizEngine/src/VizEngine/Core/Input.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Input.h

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"

struct GLFWwindow;

namespace VizEngine
{
    // Type-safe key codes (matches GLFW values)
    enum class KeyCode : int
    {
        Space = 32,
        Apostrophe = 39,
        Comma = 44,
        Minus = 45,
        Period = 46,
        Slash = 47,

        D0 = 48, D1, D2, D3, D4, D5, D6, D7, D8, D9,

        A = 65, B, C, D, E, F, G, H, I, J, K, L, M,
        N, O, P, Q, R, S, T, U, V, W, X, Y, Z,

        Escape = 256,
        Enter = 257,
        Tab = 258,
        Backspace = 259,
        Insert = 260,
        Delete = 261,
        Right = 262, Left = 263, Down = 264, Up = 265,

        F1 = 290, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12,

        LeftShift = 340,
        LeftControl = 341,
        LeftAlt = 342,
        RightShift = 344,
        RightControl = 345,
        RightAlt = 346,
    };

    enum class MouseCode : int
    {
        Button0 = 0,
        Button1 = 1,
        Button2 = 2,
        Left = Button0,
        Right = Button1,
        Middle = Button2
    };

    class VizEngine_API Input
    {
    public:
        static void Init(GLFWwindow* window);
        static void Update();  // Call once per frame

        // Keyboard
        static bool IsKeyPressed(KeyCode key);   // Just pressed this frame
        static bool IsKeyHeld(KeyCode key);      // Currently held
        static bool IsKeyReleased(KeyCode key);  // Just released this frame

        // Mouse buttons
        static bool IsMouseButtonPressed(MouseCode button);
        static bool IsMouseButtonHeld(MouseCode button);
        static bool IsMouseButtonReleased(MouseCode button);

        // Mouse position
        static glm::vec2 GetMousePosition();
        static glm::vec2 GetMouseDelta();

        // Scroll
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
        static bool s_FirstMouse;

        static void ScrollCallback(GLFWwindow* window, double xoffset, double yoffset);
    };

}  // namespace VizEngine
```

> [!IMPORTANT]
> Use `KeyCode::W` and `IsKeyHeld()`, not raw GLFW constants. This provides type safety and intellisense support.

---

## Step 2: Create Input.cpp

**Create `VizEngine/src/VizEngine/Core/Input.cpp`:**

```cpp
// VizEngine/src/VizEngine/Core/Input.cpp

#include "Input.h"
#include "VizEngine/Log.h"
#include <GLFW/glfw3.h>

namespace VizEngine
{
    GLFWwindow* Input::s_Window = nullptr;
    bool Input::s_CurrentKeys[512] = {};
    bool Input::s_PreviousKeys[512] = {};
    bool Input::s_CurrentMouseButtons[8] = {};
    bool Input::s_PreviousMouseButtons[8] = {};
    glm::vec2 Input::s_MousePosition = {};
    glm::vec2 Input::s_LastMousePosition = {};
    float Input::s_ScrollDelta = 0.0f;
    bool Input::s_FirstMouse = true;

    void Input::Init(GLFWwindow* window)
    {
        s_Window = window;
        glfwSetScrollCallback(window, ScrollCallback);

        double x, y;
        glfwGetCursorPos(window, &x, &y);
        s_MousePosition = { float(x), float(y) };
        s_LastMousePosition = s_MousePosition;

        VP_CORE_TRACE("Input system initialized");
    }

> [!NOTE]
> We register the scroll callback directly here for simplicity. When adopting an event-driven architecture later, you may centralize all GLFW callbacks in the window manager and forward scroll data to the Input system. This keeps callback ownership clear while maintaining polling support.

    void Input::Update()
    {
        // Copy current to previous
        for (int i = 0; i < 512; i++) s_PreviousKeys[i] = s_CurrentKeys[i];
        for (int i = 0; i < 8; i++) s_PreviousMouseButtons[i] = s_CurrentMouseButtons[i];

        // Poll current keyboard state
        for (int i = 0; i < 512; i++)
        {
            s_CurrentKeys[i] = glfwGetKey(s_Window, i) == GLFW_PRESS;
        }

        // Poll current mouse button state
        for (int i = 0; i < 8; i++)
        {
            s_CurrentMouseButtons[i] = glfwGetMouseButton(s_Window, i) == GLFW_PRESS;
        }

        // Update mouse position
        s_LastMousePosition = s_MousePosition;
        double x, y;
        glfwGetCursorPos(s_Window, &x, &y);
        s_MousePosition = { float(x), float(y) };

        if (s_FirstMouse)
        {
            s_LastMousePosition = s_MousePosition;
            s_FirstMouse = false;
        }

        s_ScrollDelta = 0.0f;  // Reset at frame start (accumulates via callback)
    }

    bool Input::IsKeyPressed(KeyCode key)
    {
        int k = static_cast<int>(key);
        return s_CurrentKeys[k] && !s_PreviousKeys[k];
    }

    bool Input::IsKeyHeld(KeyCode key)
    {
        return s_CurrentKeys[static_cast<int>(key)];
    }

    bool Input::IsKeyReleased(KeyCode key)
    {
        int k = static_cast<int>(key);
        return !s_CurrentKeys[k] && s_PreviousKeys[k];
    }

    bool Input::IsMouseButtonPressed(MouseCode button)
    {
        int b = static_cast<int>(button);
        return s_CurrentMouseButtons[b] && !s_PreviousMouseButtons[b];
    }

    bool Input::IsMouseButtonHeld(MouseCode button)
    {
        return s_CurrentMouseButtons[static_cast<int>(button)];
    }

    bool Input::IsMouseButtonReleased(MouseCode button)
    {
        int b = static_cast<int>(button);
        return !s_CurrentMouseButtons[b] && s_PreviousMouseButtons[b];
    }

    glm::vec2 Input::GetMousePosition()
    {
        return s_MousePosition;
    }

    glm::vec2 Input::GetMouseDelta()
    {
        return s_MousePosition - s_LastMousePosition;
    }

    float Input::GetScrollDelta()
    {
        return s_ScrollDelta;
    }

    void Input::ScrollCallback(GLFWwindow* window, double xoffset, double yoffset)
    {
        (void)window;
        (void)xoffset;
        s_ScrollDelta += float(yoffset);  // Accumulates during frame
    }

}  // namespace VizEngine
```

---

## Usage Example

```cpp
// Initialize once
Input::Init(window.GetWindow());

// In render loop
Input::Update();  // MUST be called at start of frame!

// Keyboard
if (Input::IsKeyHeld(KeyCode::W)) camera.MoveForward(speed);
if (Input::IsKeyHeld(KeyCode::S)) camera.MoveForward(-speed);
if (Input::IsKeyHeld(KeyCode::A)) camera.MoveRight(-speed);
if (Input::IsKeyHeld(KeyCode::D)) camera.MoveRight(speed);
if (Input::IsKeyHeld(KeyCode::E)) camera.MoveUp(speed);
if (Input::IsKeyHeld(KeyCode::Q)) camera.MoveUp(-speed);

// Sprint with shift
if (Input::IsKeyHeld(KeyCode::LeftShift))
    speed *= 2.5f;

// Mouse look on right-click hold
if (Input::IsMouseButtonHeld(MouseCode::Right))
{
    glm::vec2 delta = Input::GetMouseDelta();
    float newYaw = camera.GetYaw() - delta.x * 0.003f;
    float newPitch = camera.GetPitch() - delta.y * 0.003f;
    camera.SetRotation(newPitch, newYaw);
}

// Scroll zoom
float scroll = Input::GetScrollDelta();
if (scroll != 0.0f)
{
    camera.SetFOV(camera.GetFOV() - scroll * 2.0f);
}
```

---

## Edge Detection

| Method | When True |
|--------|-----------|
| `IsKeyPressed` | First frame key goes down |
| `IsKeyHeld` | Every frame while key is down |
| `IsKeyReleased` | First frame key goes up |

```
Frame 1: Key up      → Pressed:NO  Held:NO  Released:NO
Frame 2: Key down    → Pressed:YES Held:YES Released:NO
Frame 3: Key down    → Pressed:NO  Held:YES Released:NO
Frame 4: Key up      → Pressed:NO  Held:NO  Released:YES
Frame 5: Key up      → Pressed:NO  Held:NO  Released:NO
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Keys don't work | `Update()` not called | Call `Input::Update()` each frame |
| Double input | `IsKeyPressed` vs `IsKeyHeld` | Use `IsKeyHeld` for movement |
| Mouse jumps | First frame delta | `s_FirstMouse` flag handles this |

---

## Milestone

**Input System Complete**

You have:
- `KeyCode` and `MouseCode` enums
- `IsKeyPressed` / `IsKeyHeld` / `IsKeyReleased`
- Mouse button state
- Mouse position and delta
- Scroll wheel support

---

## What's Next

In **Chapter 22**, we'll use Input to create a fly camera controller.

> **Next:** [Chapter 22: Camera Controller](22_CameraController.md)

> **Previous:** [Chapter 20: Model Loader (Materials)](20_ModelLoaderMaterials.md)
