\newpage

# Chapter 18: Camera Controller

## Building on the Input System

In the previous chapter, we built an Input system with keyboard polling, mouse position tracking, and scroll wheel support. Now we put it to practical use by creating an interactive camera controller.

By the end of this chapter, you'll have:
- WASD movement in camera-relative directions
- Mouse look (hold right mouse button)
- Scroll wheel zoom
- Sprint modifier (Shift key)

---

## The Camera Class

Our Camera class (from Chapter 10) already has movement methods:

```cpp
// VizEngine/Core/Camera.h

class Camera
{
public:
    // Movement
    void MoveForward(float amount);
    void MoveRight(float amount);
    void MoveUp(float amount);
    
    // Rotation (pitch = up/down, yaw = left/right)
    void SetRotation(float pitch, float yaw);
    float GetPitch() const;
    float GetYaw() const;
    
    // FOV for zoom
    void SetFOV(float fov);
    float GetFOV() const;
    
    // Direction vectors
    glm::vec3 GetForward() const;
    glm::vec3 GetRight() const;
    glm::vec3 GetUp() const;
};
```

These methods handle the math internally:
- `MoveForward()` moves along the camera's forward vector
- `MoveRight()` moves along the camera's right vector (cross product of forward and world up)
- `SetRotation()` updates pitch/yaw and recalculates the view matrix

---

## Camera-Relative Movement

The key insight for camera movement is using **camera-relative directions**, not world axes:

| Key | World Space | Camera Space |
|-----|-------------|--------------|
| W | Always +Z | Forward (where camera looks) |
| S | Always -Z | Backward |
| A | Always -X | Left |
| D | Always +X | Right |

Camera-relative movement feels natural because pressing W always moves "forward" from the player's perspective, regardless of which direction the camera is facing.

Our Camera class handles this with `GetForward()`:

```cpp
glm::vec3 Camera::GetForward() const
{
    return glm::normalize(glm::vec3(
        cos(m_Pitch) * sin(m_Yaw),
        sin(m_Pitch),
        cos(m_Pitch) * cos(m_Yaw)
    ));
}
```

---

## WASD Movement

Basic movement using the Input system:

```cpp
// Camera settings
float moveSpeed = 5.0f;

// In main loop, after window.ProcessInput():

float speed = moveSpeed * deltaTime;

if (Input::IsKeyHeld(KeyCode::W)) camera.MoveForward(speed);
if (Input::IsKeyHeld(KeyCode::S)) camera.MoveForward(-speed);
if (Input::IsKeyHeld(KeyCode::A)) camera.MoveRight(-speed);
if (Input::IsKeyHeld(KeyCode::D)) camera.MoveRight(speed);
```

Using `IsKeyHeld()` instead of `IsKeyPressed()` because we want continuous movement while the key is down.

### Adding Vertical Movement

For fly-mode cameras (useful for scene editors), add Q/E for up/down:

```cpp
if (Input::IsKeyHeld(KeyCode::E)) camera.MoveUp(speed);
if (Input::IsKeyHeld(KeyCode::Q)) camera.MoveUp(-speed);
```

---

## Sprint Modifier

Hold Shift to move faster:

```cpp
float moveSpeed = 5.0f;
float sprintMultiplier = 2.5f;

float speed = moveSpeed * deltaTime;

// Sprint when holding Shift
if (Input::IsKeyHeld(KeyCode::LeftShift))
    speed *= sprintMultiplier;

// Movement uses the modified speed
if (Input::IsKeyHeld(KeyCode::W)) camera.MoveForward(speed);
// ... etc
```

---

## Mouse Look

Rotate the camera by moving the mouse while holding the right mouse button:

```cpp
float lookSensitivity = 0.003f;  // Radians per pixel

if (Input::IsMouseButtonHeld(MouseCode::Right))
{
    glm::vec2 delta = Input::GetMouseDelta();
    
    // Yaw (left/right) - horizontal mouse movement
    float yaw = camera.GetYaw() - delta.x * lookSensitivity;
    
    // Pitch (up/down) - vertical mouse movement
    float pitch = camera.GetPitch() - delta.y * lookSensitivity;
    
    // Clamp pitch to prevent camera flip
    pitch = glm::clamp(pitch, -1.5f, 1.5f);  // ~85 degrees
    
    camera.SetRotation(pitch, yaw);
}
```

Why clamp pitch?
- At exactly ±90°, the camera "up" becomes parallel to "forward", causing gimbal lock
- Clamping to ±85° prevents this edge case

Why hold right mouse button?
- Allows using the mouse for ImGui without fighting camera rotation
- Standard convention in 3D editors (Maya, Blender)

---

## Scroll Zoom

Adjust FOV with the scroll wheel for a zoom effect:

```cpp
float scroll = Input::GetScrollDelta();
if (scroll != 0.0f)
{
    float fov = camera.GetFOV() - scroll * 2.0f;
    fov = glm::clamp(fov, 10.0f, 90.0f);
    camera.SetFOV(fov);
}
```

- Lower FOV = zoomed in (telephoto lens)
- Higher FOV = zoomed out (wide angle)
- Clamping prevents extreme values

---

## Full Implementation

Here's the complete camera controller code for `Application.cpp`:

```cpp
#include "Core/Input.h"

// In Application::Run(), before the main loop:

// Camera controller settings
float moveSpeed = 5.0f;
float sprintMultiplier = 2.5f;
float lookSensitivity = 0.003f;

// In the main loop, after window.ProcessInput():

// --- Camera Controller ---

// Calculate speed with sprint modifier
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
    pitch = glm::clamp(pitch, -1.5f, 1.5f);
    camera.SetRotation(pitch, yaw);
}

// Scroll zoom
float scroll = Input::GetScrollDelta();
if (scroll != 0.0f)
{
    float fov = camera.GetFOV() - scroll * 2.0f;
    camera.SetFOV(glm::clamp(fov, 10.0f, 90.0f));
}
```

---

## ImGui Camera Panel

Expose camera settings in ImGui for runtime tweaking:

```cpp
uiManager.StartWindow("Camera");

ImGui::Text("Position: (%.1f, %.1f, %.1f)", 
    camera.GetPosition().x, camera.GetPosition().y, camera.GetPosition().z);
ImGui::Text("Pitch: %.1f, Yaw: %.1f", 
    glm::degrees(camera.GetPitch()), glm::degrees(camera.GetYaw()));

ImGui::Separator();

ImGui::SliderFloat("Move Speed", &moveSpeed, 1.0f, 20.0f);
ImGui::SliderFloat("Sprint Multiplier", &sprintMultiplier, 1.5f, 5.0f);
ImGui::SliderFloat("Look Sensitivity", &lookSensitivity, 0.001f, 0.01f);

ImGui::Separator();

float fov = camera.GetFOV();
if (ImGui::SliderFloat("FOV", &fov, 10.0f, 90.0f))
    camera.SetFOV(fov);

if (ImGui::Button("Reset Camera"))
{
    camera.SetPosition(glm::vec3(0.0f, 6.0f, -15.0f));
    camera.SetRotation(0.0f, 0.0f);
    camera.SetFOV(45.0f);
}

uiManager.EndWindow();
```

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Camera doesn't move | Input::Update() not called | Ensure ProcessInput() is called |
| Movement in wrong direction | Camera yaw not set | Initialize yaw to face -Z |
| Mouse look jittery | Sensitivity too high | Lower lookSensitivity value |
| Camera flips upside down | Pitch not clamped | Clamp to ±85 degrees |
| Movement speed varies | Not using deltaTime | Multiply speed by deltaTime |

---

## Key Takeaways

1. **Camera-relative movement** - Use `GetForward()`, `GetRight()` for natural controls
2. **Delta time** - Multiply speed by deltaTime for frame-rate independence
3. **Sprint modifier** - Simple multiplier on base speed
4. **Pitch clamping** - Prevents gimbal lock at ±90°
5. **Hold-to-look** - Standard convention for 3D editors

---

## Checkpoint

This chapter covered building a camera controller:

**Controls:**
| Input | Action |
|-------|--------|
| WASD | Move forward/back/left/right |
| Q/E | Move down/up |
| Shift | Sprint |
| Right Mouse + Drag | Look around |
| Scroll | Zoom in/out |

**Files Modified:**
- `VizEngine/Application.cpp` - Added camera controller logic

**Checkpoint:** Add WASD camera movement, mouse look, scroll zoom, and verify you can fly around the scene.

---

## Exercise

1. **Invert Y-axis** - Add option to invert vertical mouse look
2. **Smooth movement** - Implement acceleration/deceleration instead of instant start/stop
3. **Orbit mode** - Hold Alt + Right-click to orbit around a target point
4. **Camera presets** - Store/recall camera positions with number keys

---

> **Next:** [Chapter 17: Advanced OpenGL](17_AdvancedOpenGL.md) - Framebuffers, depth/stencil testing, cubemaps.

> **Previous:** [Chapter 15: Input System](15_InputSystem.md)

