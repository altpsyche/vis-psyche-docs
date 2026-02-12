\newpage

# Chapter 14: Camera System

Create a `Camera` class that generates view and projection matrices. This lets you look at your 3D scene from any angle.

---

## Camera Concepts

### View Matrix

Transforms world space → camera space. Created using:
- Camera position
- Pitch (up/down) and Yaw (left/right) rotation

### Projection Matrix

Transforms camera space → clip space. We use **perspective projection**:
- Field of view (FOV)
- Aspect ratio
- Near/far planes

---

## Step 1: Create Camera.h

**Create `VizEngine/src/VizEngine/Core/Camera.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Camera.h

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"
#include "gtc/matrix_transform.hpp"

namespace VizEngine
{
    class VizEngine_API Camera
    {
    public:
        Camera(float fov = 45.0f, float aspectRatio = 1.0f,
               float nearPlane = 0.1f, float farPlane = 100.0f);

        // Setters
        void SetPosition(const glm::vec3& position);
        void SetRotation(float pitch, float yaw);  // In RADIANS
        void SetFOV(float fov);                    // In DEGREES
        void SetAspectRatio(float aspectRatio);
        void SetClipPlanes(float nearPlane, float farPlane);

        // Getters
        const glm::vec3& GetPosition() const { return m_Position; }
        float GetPitch() const { return m_Pitch; }  // Returns RADIANS
        float GetYaw() const { return m_Yaw; }      // Returns RADIANS
        float GetFOV() const { return m_FOV; }      // Returns DEGREES

        // Matrix getters
        const glm::mat4& GetViewMatrix() const { return m_ViewMatrix; }
        const glm::mat4& GetProjectionMatrix() const { return m_ProjectionMatrix; }
        glm::mat4 GetViewProjectionMatrix() const { return m_ProjectionMatrix * m_ViewMatrix; }

        // Movement (convenience methods)
        void Move(const glm::vec3& offset);
        void MoveForward(float amount);
        void MoveRight(float amount);
        void MoveUp(float amount);

        // Direction vectors
        glm::vec3 GetForward() const;
        glm::vec3 GetRight() const;
        glm::vec3 GetUp() const;

    private:
        void RecalculateViewMatrix();
        void RecalculateProjectionMatrix();

        glm::vec3 m_Position;
        float m_Pitch;  // Up/down rotation (RADIANS)
        float m_Yaw;    // Left/right rotation (RADIANS)

        float m_FOV;    // Field of view (DEGREES)
        float m_AspectRatio;
        float m_NearPlane;
        float m_FarPlane;

        glm::mat4 m_ViewMatrix;
        glm::mat4 m_ProjectionMatrix;
    };
}
```

> [!IMPORTANT]
> **Rotation is in radians**, not degrees. Pitch and Yaw are stored and returned in radians for consistency with GLM functions. FOV is in degrees (as is standard for camera settings).

---

## Step 2: Create Camera.cpp

**Create `VizEngine/src/VizEngine/Core/Camera.cpp`:**

```cpp
// VizEngine/src/VizEngine/Core/Camera.cpp

#include "Camera.h"
#include "VizEngine/Log.h"
#include <cmath>

namespace VizEngine
{
    Camera::Camera(float fov, float aspectRatio, float nearPlane, float farPlane)
        : m_Position(0.0f, 0.0f, 0.0f)
        , m_Pitch(0.0f)
        , m_Yaw(0.0f)
        , m_FOV(fov)
        , m_AspectRatio(aspectRatio)
        , m_NearPlane(nearPlane)
        , m_FarPlane(farPlane)
    {
        RecalculateViewMatrix();
        RecalculateProjectionMatrix();
        VP_CORE_TRACE("Camera created: FOV={}, Aspect={}", m_FOV, m_AspectRatio);
    }

    void Camera::SetPosition(const glm::vec3& position)
    {
        m_Position = position;
        RecalculateViewMatrix();
    }

    void Camera::SetRotation(float pitch, float yaw)
    {
        m_Pitch = pitch;
        m_Yaw = yaw;
        RecalculateViewMatrix();
    }

    void Camera::SetFOV(float fov)
    {
        m_FOV = glm::clamp(fov, 10.0f, 120.0f);
        RecalculateProjectionMatrix();
    }

    void Camera::SetAspectRatio(float aspectRatio)
    {
        m_AspectRatio = aspectRatio;
        RecalculateProjectionMatrix();
    }

    void Camera::SetClipPlanes(float nearPlane, float farPlane)
    {
        m_NearPlane = nearPlane;
        m_FarPlane = farPlane;
        RecalculateProjectionMatrix();
    }

    glm::vec3 Camera::GetForward() const
    {
        return glm::vec3(
            cos(m_Pitch) * sin(m_Yaw),
            sin(m_Pitch),
            cos(m_Pitch) * cos(m_Yaw)
        );
    }

    glm::vec3 Camera::GetRight() const
    {
        return glm::normalize(glm::cross(GetForward(), glm::vec3(0, 1, 0)));
    }

    glm::vec3 Camera::GetUp() const
    {
        return glm::normalize(glm::cross(GetRight(), GetForward()));
    }

    void Camera::Move(const glm::vec3& offset)
    {
        m_Position += offset;
        RecalculateViewMatrix();
    }

    void Camera::MoveForward(float amount)
    {
        m_Position += GetForward() * amount;
        RecalculateViewMatrix();
    }

    void Camera::MoveRight(float amount)
    {
        m_Position += GetRight() * amount;
        RecalculateViewMatrix();
    }

    void Camera::MoveUp(float amount)
    {
        m_Position += GetUp() * amount;
        RecalculateViewMatrix();
    }

    void Camera::RecalculateViewMatrix()
    {
        m_ViewMatrix = glm::lookAt(m_Position, m_Position + GetForward(), glm::vec3(0, 1, 0));
    }

    void Camera::RecalculateProjectionMatrix()
    {
        m_ProjectionMatrix = glm::perspective(
            glm::radians(m_FOV),
            m_AspectRatio,
            m_NearPlane,
            m_FarPlane
        );
    }

}  // namespace VizEngine
```

---

## Step 3: Update CMakeLists.txt

Add the new `Camera.cpp` to the build system.

**Modify `VizEngine/CMakeLists.txt`:**

In the `VIZENGINE_SOURCES` section (Core subsection), add:

```cmake
    src/VizEngine/Core/Camera.cpp
```

In the `VIZENGINE_HEADERS` section (Core headers subsection), add:

```cmake
    src/VizEngine/Core/Camera.h
```

---

## Usage Example

```cpp
// Create camera
Camera camera(45.0f, 16.0f / 9.0f, 0.1f, 100.0f);
camera.SetPosition(glm::vec3(0.0f, 5.0f, 10.0f));

// Rotation is in RADIANS
camera.SetRotation(-0.3f, 0.0f);  // Slight downward pitch

// In render loop - WASD movement
float speed = 5.0f * deltaTime;
if (Input::IsKeyHeld(KeyCode::W)) camera.MoveForward(speed);
if (Input::IsKeyHeld(KeyCode::S)) camera.MoveForward(-speed);
if (Input::IsKeyHeld(KeyCode::A)) camera.MoveRight(-speed);
if (Input::IsKeyHeld(KeyCode::D)) camera.MoveRight(speed);

// Mouse look (delta in radians)
glm::vec2 mouseDelta = Input::GetMouseDelta();
float sensitivity = 0.003f;
float newYaw = camera.GetYaw() - mouseDelta.x * sensitivity;
float newPitch = camera.GetPitch() - mouseDelta.y * sensitivity;
newPitch = glm::clamp(newPitch, -1.5f, 1.5f);  // Clamp at caller level
camera.SetRotation(newPitch, newYaw);

// Get matrices for rendering
glm::mat4 vp = camera.GetViewProjectionMatrix();
```

---

## Radians vs Degrees

| Property | Unit | Why |
|----------|------|-----|
| `Pitch`, `Yaw` | **Radians** | GLM trigonometric functions use radians |
| `FOV` | **Degrees** | Industry standard for camera settings |

Converting:
```cpp
float radians = glm::radians(degrees);
float degrees = glm::degrees(radians);
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Nothing visible | Camera inside object | Move camera back (increase Z) |
| Camera flips | Pitch > ~89° | Clamp pitch to ±1.5 radians |
| Movement too fast | Not using deltaTime | Multiply speed by deltaTime |

---

## Milestone

**Camera System Complete**

You have:
- `Camera` class with position and rotation
- View matrix from lookAt
- Perspective projection matrix
- Movement methods (`MoveForward`, `MoveRight`, `MoveUp`)
- Direction vectors (`GetForward`, `GetRight`, `GetUp`)
- Note: **Rotation uses radians**

---

## What's Next

In **Chapter 15**, we'll create a `Scene` class to manage multiple objects.

> **Next:** [Chapter 15: Scene Management](15_SceneManagement.md)

> **Previous:** [Chapter 13: Transform & Mesh](13_TransformAndMesh.md)
