\newpage

# Chapter 13: Camera System

## What is a Camera?

In 3D graphics, a "camera" doesn't capture light like a real camera. Instead, it defines:

1. **Where we're looking from** (position)
2. **What direction we're facing** (orientation)
3. **How we project 3D to 2D** (perspective)

This produces two matrices:
- **View Matrix** - Transforms world space to camera space
- **Projection Matrix** - Transforms camera space to clip space

Together: `MVP = Projection * View * Model`

---

## The Camera Class

```cpp
// VizEngine/Core/Camera.h

class VizEngine_API Camera
{
public:
    Camera(float fov = 45.0f, float aspectRatio = 1.0f, 
           float nearPlane = 0.1f, float farPlane = 100.0f);
    
    // Transform
    void SetPosition(const glm::vec3& position);
    void SetRotation(float pitch, float yaw);
    
    // Getters
    const glm::vec3& GetPosition() const { return m_Position; }
    float GetPitch() const { return m_Pitch; }
    float GetYaw() const { return m_Yaw; }
    float GetFOV() const { return m_FOV; }
    
    // Matrices
    const glm::mat4& GetViewMatrix() const { return m_ViewMatrix; }
    const glm::mat4& GetProjectionMatrix() const { return m_ProjectionMatrix; }
    glm::mat4 GetViewProjectionMatrix() const 
    { 
        return m_ProjectionMatrix * m_ViewMatrix; 
    }
    
    // Movement helpers
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
    float m_Pitch, m_Yaw;  // Rotation in radians
    
    float m_FOV, m_AspectRatio;
    float m_NearPlane, m_FarPlane;
    
    glm::mat4 m_ViewMatrix;
    glm::mat4 m_ProjectionMatrix;
};
```

---

## The View Matrix

The view matrix transforms world coordinates to camera-relative coordinates. We use `glm::lookAt()`:

```cpp
void Camera::RecalculateViewMatrix()
{
    glm::vec3 forward = GetForward();
    glm::vec3 target = m_Position + forward;
    m_ViewMatrix = glm::lookAt(m_Position, target, glm::vec3(0, 1, 0));
}
```

**Parameters:**
- `eye` - Camera position in world space
- `target` - Point the camera looks at
- `up` - World up direction (usually Y-up)

### Direction Vectors

The camera's forward direction is computed from pitch (up/down) and yaw (left/right):

```cpp
glm::vec3 Camera::GetForward() const
{
    return glm::normalize(glm::vec3(
        cos(m_Pitch) * sin(m_Yaw),
        sin(m_Pitch),
        cos(m_Pitch) * cos(m_Yaw)
    ));
}

glm::vec3 Camera::GetRight() const
{
    return glm::normalize(glm::cross(GetForward(), glm::vec3(0, 1, 0)));
}

glm::vec3 Camera::GetUp() const
{
    return glm::normalize(glm::cross(GetRight(), GetForward()));
}
```

---

## The Projection Matrix

The projection matrix creates the perspective effect (things get smaller as they're farther away):

```cpp
void Camera::RecalculateProjectionMatrix()
{
    m_ProjectionMatrix = glm::perspective(
        glm::radians(m_FOV),  // Field of view (degrees → radians)
        m_AspectRatio,         // Width / Height
        m_NearPlane,           // Near clip plane
        m_FarPlane             // Far clip plane
    );
}
```

### Projection Parameters

| Parameter | Typical Value | Effect |
|-----------|---------------|--------|
| **FOV** | 45-90° | Wider = more visible, more distortion |
| **Aspect Ratio** | 16:9, 4:3 | Match window dimensions |
| **Near Plane** | 0.1 | Closest visible distance |
| **Far Plane** | 100-1000 | Farthest visible distance |

> **Note:** Don't set near plane to 0! This causes depth buffer precision issues.

---

## Camera Movement

Movement functions use direction vectors to move in camera-relative space:

```cpp
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
```

This enables camera-relative movement:
- `MoveForward(1.0f)` moves toward where camera is looking
- `MoveRight(1.0f)` moves to the camera's right side

---

## Usage Example

```cpp
// Create camera
Camera camera(45.0f, 800.0f / 600.0f, 0.1f, 100.0f);
camera.SetPosition(glm::vec3(0.0f, 5.0f, -10.0f));

// In render loop
shader.Bind();

// Each object needs MVP
for (auto& obj : scene)
{
    glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
    glm::mat4 mvp = camera.GetViewProjectionMatrix() * model;
    shader.SetMatrix4fv("u_MVP", mvp);
    
    // Draw object...
}
```

---

## The MVP Matrix Pipeline

```
Local Space    →    World Space    →    View Space    →    Clip Space
   (mesh)          (Model matrix)      (View matrix)     (Projection)
     │                   │                   │                 │
     ▼                   ▼                   ▼                 ▼
  Vertex         Positioned in        Relative to        Ready for
  at origin      world coords         camera             rasterizer
```

**MVP = Projection × View × Model**

The order matters! Matrix multiplication is right-to-left:
1. Model transforms vertex to world space
2. View transforms to camera-relative space  
3. Projection creates perspective

---

## Key Takeaways

1. **View matrix** - Computed from position and orientation via `lookAt()`
2. **Projection matrix** - Creates perspective from FOV and aspect ratio
3. **Direction vectors** - Derived from pitch/yaw for camera-relative movement
4. **MVP order** - Projection × View × Model (right-to-left application)
5. **Recalculate on change** - Matrices update when position/rotation changes

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Nothing visible | Camera inside objects | Move camera back (negative Z) |
| Objects flicker | Near plane too close | Use 0.1 instead of 0.001 |
| Perspective looks wrong | Aspect ratio mismatch | Match window width/height |
| Camera flips at ±90° pitch | Gimbal lock | Clamp pitch to ±85° |

---

## Checkpoint

This chapter covered the Camera system:

**Files:**
| File | Purpose |
|------|---------|
| `VizEngine/Core/Camera.h` | Camera class declaration |
| `VizEngine/Core/Camera.cpp` | View/projection matrix calculation |

**Concepts:**
- View matrix via `glm::lookAt()`
- Projection matrix via `glm::perspective()`
- Direction vectors from pitch/yaw

**Checkpoint:** Create Camera.h/.cpp, set up view and projection matrices, verify 3D perspective rendering works.

---

## Exercise

1. Add `SetFOV()` and `SetAspectRatio()` methods
2. Implement `LookAt(target)` - point camera at a world position
3. Add orthographic projection option
4. Create a `ResetCamera()` function

---

> **Next:** [Chapter 12: Scene Management](12_SceneManagement.md) - Managing multiple objects.

> **Previous:** [Chapter 10: Transform & Mesh](10_TransformAndMesh.md)

