\newpage

# Chapter 22: Camera Controller

Use the Input system to create a fly camera with WASD movement and mouse look.

---

## Controls

| Input | Action |
|-------|--------|
| **W/A/S/D** | Move forward/left/back/right |
| **Q/E** | Move down/up |
| **Shift** | Sprint (faster movement) |
| **Right-click + drag** | Look around |
| **Scroll** | Adjust FOV (zoom) |

---

## Implementation in Application.cpp

Add camera controller logic to `Application::Run`:

```cpp
#include "Core/Input.h"
#include "Core/Camera.h"

int Application::Run()
{
    // ... initialization ...

    Camera camera(45.0f, float(SCR_WIDTH) / float(SCR_HEIGHT), 0.1f, 100.0f);
    camera.SetPosition(glm::vec3(0.0f, 5.0f, 10.0f));

    float moveSpeed = 5.0f;
    float sprintMultiplier = 2.5f;
    float lookSensitivity = 0.003f;

    Input::Init(window.GetWindow());

    double prevTime = glfwGetTime();

    while (!window.WindowShouldClose())
    {
        // Delta time
        double currentTime = glfwGetTime();
        float deltaTime = float(currentTime - prevTime);
        prevTime = currentTime;

        // Update input (MUST be at start of frame)
        Input::Update();

        window.ProcessInput();

        // Movement speed
        float speed = moveSpeed * deltaTime;
        if (Input::IsKeyHeld(KeyCode::LeftShift))
            speed *= sprintMultiplier;

        // WASD movement
        if (Input::IsKeyHeld(KeyCode::W)) camera.MoveForward(speed);
        if (Input::IsKeyHeld(KeyCode::S)) camera.MoveForward(-speed);
        if (Input::IsKeyHeld(KeyCode::A)) camera.MoveRight(-speed);
        if (Input::IsKeyHeld(KeyCode::D)) camera.MoveRight(speed);
        if (Input::IsKeyHeld(KeyCode::E)) camera.MoveUp(speed);
        if (Input::IsKeyHeld(KeyCode::Q)) camera.MoveUp(-speed);

        // Mouse look (hold right mouse button)
        if (Input::IsMouseButtonHeld(MouseCode::Right))
        {
            glm::vec2 delta = Input::GetMouseDelta();
            float yaw = camera.GetYaw() - delta.x * lookSensitivity;
            float pitch = camera.GetPitch() - delta.y * lookSensitivity;
            pitch = glm::clamp(pitch, -1.5f, 1.5f);  // Clamp in radians
            camera.SetRotation(pitch, yaw);
        }

        // Scroll zoom
        float scroll = Input::GetScrollDelta();
        if (scroll != 0.0f)
        {
            float fov = camera.GetFOV() - scroll * 2.0f;
            camera.SetFOV(glm::clamp(fov, 10.0f, 90.0f));
        }

        // Render
        renderer.Clear(clearColor);
        scene.Render(renderer, shader, camera);

        // UI
        uiManager.BeginFrame();
        // ... ImGui panels ...
        uiManager.Render();

        window.SwapBuffersAndPollEvents();
    }

    return 0;
}
```

> [!IMPORTANT]
> Remember:
> - `Input::Update()` must be called at the start of each frame
> - Camera rotation is in **radians**
> - Multiply movement by `deltaTime` for frame-rate independence

---

## Understanding the Controls

### Movement Vectors

```cpp
camera.MoveForward(speed);  // Uses GetForward() internally
camera.MoveRight(speed);    // Uses GetRight() internally
camera.MoveUp(speed);       // World up (Y axis)
```

### Mouse Look

Note the subtraction for inverted-style look:

```cpp
float yaw = camera.GetYaw() - delta.x * sensitivity;
float pitch = camera.GetPitch() - delta.y * sensitivity;
```

### Delta Time

Movement is multiplied by `deltaTime` to be frame-rate independent:

```cpp
float speed = moveSpeed * deltaTime;
// At 60 FPS: deltaTime ≈ 0.0167
// At 30 FPS: deltaTime ≈ 0.0333
// Result: Same distance per second
```

---

## Optional: Camera Info Panel

Add an ImGui panel to show camera values:

```cpp
ImGui::Begin("Camera");
ImGui::Text("Position: %.2f, %.2f, %.2f",
    camera.GetPosition().x,
    camera.GetPosition().y,
    camera.GetPosition().z);
ImGui::Text("Pitch: %.2f rad, Yaw: %.2f rad",
    camera.GetPitch(),
    camera.GetYaw());
ImGui::SliderFloat("Speed", &moveSpeed, 0.5f, 20.0f);
ImGui::SliderFloat("Sensitivity", &lookSensitivity, 0.001f, 0.01f);
ImGui::End();
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Camera jumps on click | Large first delta | `s_FirstMouse` in Input handles this |
| Movement too fast | Missing deltaTime | Multiply speed by deltaTime |
| Can't look up past limit | Pitch overflow | Clamp to ±1.5 radians |
| Wrong rotation direction | Sign error | Adjust ± in yaw/pitch calculation |

---

## Milestone

**Camera Controller Complete**

You have:
- WASD + Q/E movement
- Shift to sprint
- Right-click mouse look
- Scroll wheel zoom
- Frame-rate independent movement

---

## Book Complete!

Congratulations! You've built a complete 3D rendering engine:

- **Windowing**: GLFW + OpenGL context
- **Rendering**: Buffers, Shaders, Textures
- **Architecture**: Mesh, Scene, Camera
- **Lighting**: Blinn-Phong shading
- **Assets**: glTF model loading
- **UI**: Dear ImGui integration
- **Input**: Keyboard + mouse controls

> **Appendix:** [Code Reference](A_Reference.md)

> **Previous:** [Chapter 21: Input System](21_InputSystem.md)
