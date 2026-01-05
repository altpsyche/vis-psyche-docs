\newpage

# Chapter 28: Shadow Mapping

Implement realistic shadows using depth maps and two-pass rendering with the framebuffer foundation from Chapter 27.

---

## Introduction

Shadows are essential for realistic 3D rendering. They provide:
- **Depth perception** - where objects are in 3D space
- **Spatial relationships** - which objects are above/below others
- **Realism** - scenes without shadows look flat and artificial

Until now, our lighting model has calculated diffuse and specular components, but every surface receives light equally—there are no shadows.

### The Shadow Problem

In the real world, shadows occur when an object blocks light from reaching another surface. To render shadows, we need to answer: **"Can this fragment see the light source?"**

If the fragment is blocked by another object, it's in shadow and shouldn't receive direct lighting (only ambient).

### Shadow Mapping Solution

**Shadow mapping** is a two-pass technique:

1. **Pass 1 (Depth Pass)**: Render scene from light's perspective, storing depth values
2. **Pass 2 (Shading Pass)**: Render scene normally, compare fragment depth to shadow map

```
Light's Perspective              Camera's Perspective
     (Pass 1)                         (Pass 2)
         
   ┌─────────┐                    ┌─────────┐
   │ Depth   │                    │ Compare │
   │  Map    │─────────────────>  │ & Shade │
   └─────────┘                    └─────────┘
   
Render to texture              Use texture in shader
```

This chapter builds directly on **Chapter 27's framebuffer** foundation—we'll render depth to a texture instead of color.

---

## Shadow Mapping Theory

### Two-Pass Rendering Workflow

```
Pass 1: Render from Light (Depth Pass)
├── Bind shadow map framebuffer
├── Use shadow depth shader
├── Set light-space matrices (view + projection)
├── Render scene → outputs depth values
└── Unbind framebuffer

Pass 2: Render from Camera (Shading Pass)
├── Bind default framebuffer (screen)
├── Use lit shader
├── Bind shadow map as texture
├── For each fragment:
│   ├── Transform position to light space
│   ├── Sample shadow map depth
│   ├── Compare fragment depth to shadow map
│   └── Apply shadow (0.0 = shadowed, 1.0 = lit)
└── Render scene with shadows
```

### Light-Space Transformation

To render from the light's perspective, we need two matrices:

**1. Light View Matrix**

For a directional light (like the sun), create a view matrix **looking from the light toward the scene**:

```cpp
glm::vec3 lightDir = glm::normalize(light.Direction);
glm::vec3 lightPos = -lightDir * 10.0f;  // Position light "behind" scene
glm::mat4 lightView = glm::lookAt(
    lightPos,                   // Light position
    glm::vec3(0.0f),           // Look at origin (scene center)
    glm::vec3(0.0f, 1.0f, 0.0f) // Up vector
);
```

> [!NOTE]
> Directional lights don't have a real position (they're infinitely far away), but `glm::lookAt()` requires a position. We place it far back along the light direction.

**2. Light Projection Matrix**

Use **orthographic projection** (not perspective) for directional lights:

```cpp
float orthoSize = 10.0f;  // How much of the scene to cover
glm::mat4 lightProjection = glm::ortho(
    -orthoSize, orthoSize,   // left, right
    -orthoSize, orthoSize,   // bottom, top
    0.1f, 20.0f              // near, far
);
```

> [!IMPORTANT]
> **Why orthographic?** Directional light rays are parallel (sun is infinitely far away). Perspective projection would make rays converge to a point, which is incorrect for directional lights. Point lights and spotlights use perspective projection (not covered in this chapter).

**Light-Space Matrix**

Combine projection and view:

```cpp
glm::mat4 lightSpaceMatrix = lightProjection * lightView;
```

This transforms world-space positions to **light's NDC space** (normalized device coordinates from the light's perspective).

### Depth Comparison

In the shading pass, for each fragment:

```glsl
// 1. Transform fragment position to light space
vec4 fragPosLightSpace = u_LightSpaceMatrix * vec4(fragWorldPos, 1.0);

// 2. Convert to NDC (perspective divide)
vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;

// 3. Transform from [-1, 1] to [0, 1] (texture coordinate space)
projCoords = projCoords * 0.5 + 0.5;

// 4. Sample shadow map (stored depth from light's perspective)
float closestDepth = texture(u_ShadowMap, projCoords.xy).r;

// 5. Get current fragment's depth (how far from light)
float currentDepth = projCoords.z;

// 6. Compare: if current depth > stored depth, fragment is in shadow
float shadow = currentDepth > closestDepth ? 1.0 : 0.0;

// 7. Apply to lighting (shadow = 1.0 means in shadow, so invert)
vec3 lighting = (ambient + (1.0 - shadow) * (diffuse + specular)) * color;
```

### Shadow Artifacts

Shadow mapping has three common artifacts:

#### 1. Shadow Acne

**Problem**: Self-shadowing creates stripes/dots on surfaces facing the light.

**Cause**: Limited depth precision. The shadow map stores discrete depth values, but when comparing, rounding errors cause surfaces to shadow themselves.

```
Surface        Shadow Map Grid
  |              ┌─┬─┬─┐
  |   Light      │ │ │ │  <- Stored depth
  | /            ├─┼─┼─┤
  |/             │▓│ │ │  <- Some fragments fail comparison
  +──────        └─┴─┴─┘
```

**Solution**: Add a small **depth bias** to push the comparison threshold:

```glsl
float shadow = (currentDepth - bias) > closestDepth ? 1.0 : 0.0;
```

Or use OpenGL's `glPolygonOffset()` to offset depth during rendering.

#### 2. Peter Panning

**Problem**: Objects appear detached from the ground (shadows start away from the object).

**Cause**: Depth bias is too large, causing shadows to disappear near the object.

**Solution**: Tune bias carefully (typically 0.001 - 0.005).

#### 3. Aliasing (Jagged Shadow Edges)

**Problem**: Shadow edges look pixelated/blocky.

**Cause**: Shadow map resolution is limited. Each texel represents a large area in world space.

**Solutions**:
- Increase shadow map resolution (1024×1024 → 2048×2048)
- Use **PCF (Percentage Closer Filtering)** - sample multiple texels and average

---

## Architecture Overview

We'll add to the existing VizEngine framework:

```cpp
// New member variables in SandboxApp
std::shared_ptr<Framebuffer> m_ShadowMapFramebuffer;
std::shared_ptr<Texture> m_ShadowMapDepth;
std::shared_ptr<Shader> m_ShadowDepthShader;
glm::mat4 m_LightSpaceMatrix;
bool m_ShowShadowMap = false;
```

---

## Step 1: Create Shadow Map Framebuffer

The shadow map is a **depth-only framebuffer** (no color attachment).

**Update `Sandbox/src/SandboxApp.cpp` in `OnCreate()`:**

Add to existing framebuffer setup:

```cpp
// =========================================================================
// Create Shadow Map Framebuffer (for depth rendering from light's POV)
// =========================================================================
int shadowMapResolution = 1024;  // Common: 1024, 2048, 4096

// Create depth texture (GL_DEPTH_COMPONENT24 for 24-bit precision)
m_ShadowMapDepth = std::make_shared<VizEngine::Texture>(
    shadowMapResolution, shadowMapResolution,
    GL_DEPTH_COMPONENT24,   // Internal format (24-bit depth)
    GL_DEPTH_COMPONENT,     // Format
    GL_FLOAT                // Data type
);

// Create framebuffer and attach depth texture
m_ShadowMapFramebuffer = std::make_shared<VizEngine::Framebuffer>(
    shadowMapResolution, shadowMapResolution
);
m_ShadowMapFramebuffer->AttachDepthTexture(m_ShadowMapDepth);

// Verify framebuffer is complete
if (!m_ShadowMapFramebuffer->IsComplete())
{
    VP_ERROR("Shadow map framebuffer is not complete!");
}
else
{
    VP_INFO("Shadow map framebuffer created: {}x{}", shadowMapResolution, shadowMapResolution);
}
```

> [!NOTE]
> We only attach a depth texture, no color attachment. OpenGL allows depth-only framebuffers. The fragment shader in Pass 1 can be empty—depth is written automatically by the GPU.

---

## Step 2: Compute Light-Space Matrix

Create a helper function to compute the light-space transformation matrix.

**Add to `Sandbox/src/SandboxApp.cpp` (private section or helper):**

```cpp
glm::mat4 ComputeLightSpaceMatrix(const VizEngine::DirectionalLight& light)
{
    // Step 1: Create view matrix looking from light toward scene
    glm::vec3 lightDir = light.GetDirection();  // Normalized direction
    
    // Position light "behind" the scene (directional lights are infinitely far)
    glm::vec3 lightPos = -lightDir * 10.0f;
    
    // Handle degenerate up vector (when light direction is vertical)
    glm::vec3 up = glm::vec3(0.0f, 1.0f, 0.0f);
    if (glm::abs(glm::dot(lightDir, up)) > 0.999f)
    {
        up = glm::vec3(0.0f, 0.0f, 1.0f);
    }

    glm::mat4 lightView = glm::lookAt(
        lightPos,                      // Light position (behind scene)
        glm::vec3(0.0f, 0.0f, 0.0f),  // Look at origin (scene center)
        up                            // Up vector
    );
    
    // Step 2: Create orthographic projection
    // Coverage determines how much of the scene gets shadows
    float orthoSize = 10.0f;  // Adjust based on scene size
    
    glm::mat4 lightProjection = glm::ortho(
        -orthoSize, orthoSize,   // Left, right
        -orthoSize, orthoSize,   // Bottom, top
        0.1f, 20.0f              // Near, far planes
    );
    
    // Step 3: Combine into light-space matrix
    return lightProjection * lightView;
}
```

> [!TIP]
> The `orthoSize` parameter controls shadow coverage. If shadows disappear at scene edges, increase this value. If shadow quality is low, decrease it (but ensure scene fits within bounds).

---

## Step 3: Create Shadow Depth Shader

This shader renders scene geometry from the light's perspective, outputting only depth.

**Create `Sandbox/shaders/shadow_depth.shader`:**

```glsl
#shader vertex
#version 330 core

layout(location = 0) in vec3 a_Position;

uniform mat4 u_LightSpaceMatrix;  // Light's projection * view
uniform mat4 u_Model;              // Model matrix

void main()
{
    // Transform vertex to light's clip space
    gl_Position = u_LightSpaceMatrix * u_Model * vec4(a_Position, 1.0);
}


#shader fragment
#version 330 core

void main()
{
    // Fragment shader can be empty
    // Depth is written automatically to GL_DEPTH_ATTACHMENT
    // No color output needed for depth-only pass
}
```

> [!IMPORTANT]
> The fragment shader is intentionally empty. When rendering to a depth-only framebuffer, OpenGL automatically writes `gl_FragCoord.z` to the depth attachment. We don't need to output anything manually.

**Load the shader in `SandboxApp::OnCreate()`:**

```cpp
// Load shadow depth shader
m_ShadowDepthShader = std::make_shared<VizEngine::Shader>("shaders/shadow_depth.shader");
```

---

## Step 4: Update Lit Shader to Receive Shadows

Modify the existing lit shader to sample the shadow map and apply shadows to lighting.

**Update `Sandbox/shaders/lit.shader`:**

Add uniforms and shadow calculation to the fragment shader:

```glsl
#shader fragment
#version 330 core

layout(location = 0) out vec4 FragColor;

// Existing inputs
in vec3 v_Normal;
in vec2 v_TexCoord;
in vec3 v_FragPos;

// New input for shadow mapping
in vec4 v_FragPosLightSpace;

// Existing uniforms
uniform vec3 u_LightDirection;
uniform vec3 u_LightAmbient;
uniform vec3 u_LightDiffuse;
uniform vec3 u_LightSpecular;
uniform vec3 u_ViewPos;

uniform sampler2D u_Texture;
uniform vec3 u_MaterialAmbient;
uniform vec3 u_MaterialDiffuse;
uniform vec3 u_MaterialSpecular;
uniform float u_MaterialRoughness;

// New uniforms for shadow mapping
uniform sampler2D u_ShadowMap;
uniform mat4 u_LightSpaceMatrix;

// Calculate shadow (0.0 = fully lit, 1.0 = in shadow)
float CalculateShadow(vec4 fragPosLightSpace, vec3 normal, vec3 lightDir)
{
    // Perspective divide to get NDC coordinates
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    
    // Transform from [-1, 1] to [0, 1] range for texture sampling
    projCoords = projCoords * 0.5 + 0.5;
    
    // Outside shadow map bounds = no shadow
    if (projCoords.z > 1.0)
        return 0.0;
    
    // Sample shadow map (get closest depth from light's perspective)
    float closestDepth = texture(u_ShadowMap, projCoords.xy).r;
    
    // Get current fragment's depth
    float currentDepth = projCoords.z;
    
    // Slope-scaled bias to prevent shadow acne
    float bias = max(0.005 * (1.0 - dot(normal, lightDir)), 0.001);
    
    // Compare depths: if current > closest, fragment is in shadow
    float shadow = currentDepth - bias > closestDepth ? 1.0 : 0.0;
    
    return shadow;
}

void main()
{
    // Normalize interpolated normal
    vec3 norm = normalize(v_Normal);
    vec3 lightDir = normalize(-u_LightDirection);
    vec3 viewDir = normalize(u_ViewPos - v_FragPos);
    
    // Ambient lighting (always present, even in shadow)
    vec3 ambient = u_LightAmbient * u_MaterialAmbient;
    
    // Diffuse lighting
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = u_LightDiffuse * (diff * u_MaterialDiffuse);
    
    // Specular lighting (Blinn-Phong)
    vec3 halfwayDir = normalize(lightDir + viewDir);
    float shininess = (1.0 - u_MaterialRoughness) * 128.0;
    float spec = pow(max(dot(norm, halfwayDir), 0.0), shininess);
    vec3 specular = u_LightSpecular * (spec * u_MaterialSpecular);
    
    // Calculate shadow (0.0 = lit, 1.0 = shadowed)
    float shadow = CalculateShadow(v_FragPosLightSpace, norm, lightDir);
    
    // Apply shadow to diffuse and specular (NOT to ambient)
    // Ambient light reaches shadowed areas (indirect lighting)
    vec3 lighting = ambient + (1.0 - shadow) * (diffuse + specular);
    
    // Apply texture color
    vec4 texColor = texture(u_Texture, v_TexCoord);
    FragColor = vec4(lighting * texColor.rgb, texColor.a);
}
```

**Update vertex shader to pass light-space position:**

```glsl
#shader vertex
#version 330 core

layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec3 a_Normal;
layout(location = 2) in vec2 a_TexCoord;

out vec3 v_Normal;
out vec2 v_TexCoord;
out vec3 v_FragPos;
out vec4 v_FragPosLightSpace;  // NEW: position in light space

uniform mat4 u_Model;
uniform mat4 u_View;
uniform mat4 u_Projection;
uniform mat4 u_LightSpaceMatrix;  // NEW

void main()
{
    vec4 worldPos = u_Model * vec4(a_Position, 1.0);
    v_FragPos = worldPos.xyz;
    
    // Transform normal to world space (handle non-uniform scaling)
    v_Normal = mat3(transpose(inverse(u_Model))) * a_Normal;
    
    v_TexCoord = a_TexCoord;
    
    // NEW: Transform position to light space for shadow mapping
    v_FragPosLightSpace = u_LightSpaceMatrix * worldPos;
    
    gl_Position = u_Projection * u_View * worldPos;
}
```

> [!NOTE]
> We use **slope-scaled bias** in `CalculateShadow()`. Surfaces facing away from the light need more bias to prevent acne. The formula `max(0.005 * (1.0 - dot(normal, lightDir)), 0.001)` adjusts bias based on surface angle.

---

## Step 5: Two-Pass Rendering in SandboxApp

Update `OnRender()` to perform the two rendering passes.

**Update `Sandbox/src/SandboxApp.cpp` in `OnRender()`:**

```cpp
void OnRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();
    
    // =========================================================================
    // Compute Light-Space Matrix (once per frame)
    // =========================================================================
    m_LightSpaceMatrix = ComputeLightSpaceMatrix(m_Light);
    
    // =========================================================================
    // Pass 1: Render scene from light's perspective to shadow map
    // =========================================================================
    m_ShadowMapFramebuffer->Bind();
    renderer.SetViewport(0, 0, m_ShadowMapFramebuffer->GetWidth(), m_ShadowMapFramebuffer->GetHeight());
    renderer.ClearDepth();  // Clear depth buffer (no color attachment)
    
    // Use shadow depth shader
    m_ShadowDepthShader->Bind();
    m_ShadowDepthShader->SetMatrix4fv("u_LightSpaceMatrix", m_LightSpaceMatrix);
    
    // Render scene geometry (only need depth, no lighting)
    m_Scene.Render(renderer, *m_ShadowDepthShader, m_Camera);
    
    m_ShadowMapFramebuffer->Unbind();
    
    // =========================================================================
    // Pass 2: Render scene normally with shadows
    // =========================================================================
    // Restore viewport to window size
    renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);
    
    // Clear screen
    renderer.Clear(m_ClearColor);
    
    // Use lit shader
    m_LitShader->Bind();
    
    // Set lighting uniforms (existing code)
    m_LitShader->SetVec3("u_LightDirection", m_Light.GetDirection());
    m_LitShader->SetVec3("u_LightAmbient", m_Light.Ambient);
    m_LitShader->SetVec3("u_LightDiffuse", m_Light.Diffuse);
    m_LitShader->SetVec3("u_LightSpecular", m_Light.Specular);
    m_LitShader->SetVec3("u_ViewPos", m_Camera.GetPosition());
    
    // NEW: Set shadow mapping uniforms
    m_LitShader->SetMatrix4fv("u_LightSpaceMatrix", m_LightSpaceMatrix);
    
    // Bind shadow map to texture slot 1
    m_ShadowMapDepth->Bind(1);
    m_LitShader->SetInt("u_ShadowMap", 1);
    
    // Render scene with shadows
    m_Scene.Render(renderer, *m_LitShader, m_Camera);
}
```

> [!IMPORTANT]
> **Texture slot management**: Material textures typically use slot 0 (`u_Texture`). The shadow map uses slot 1 (`u_ShadowMap`). Ensure these don't conflict.

---

## Step 6: Fix Shadow Acne with Polygon Offset

For better quality, use OpenGL's built-in polygon offset during the depth pass.

**Update Pass 1 in `OnRender()`:**

```cpp
// Pass 1: Render to shadow map with polygon offset
m_ShadowMapFramebuffer->Bind();
renderer.SetViewport(0, 0, m_ShadowMapFramebuffer->GetWidth(), m_ShadowMapFramebuffer->GetHeight());
renderer.ClearDepth();

// Enable polygon offset to reduce shadow acne
glEnable(GL_POLYGON_OFFSET_FILL);
glPolygonOffset(2.0f, 4.0f);  // Factor, units

m_ShadowDepthShader->Bind();
m_ShadowDepthShader->SetMatrix4fv("u_LightSpaceMatrix", m_LightSpaceMatrix);
m_Scene.Render(renderer, *m_ShadowDepthShader, m_Camera);

// Disable polygon offset
glDisable(GL_POLYGON_OFFSET_FILL);

m_ShadowMapFramebuffer->Unbind();
```

> [!TIP]
> **Tuning polygon offset:**
> - `factor`: Slope-based offset (2.0 - 4.0 typical)
> - `units`: Constant offset (4.0 - 8.0 typical)
> 
> Start with (2.0, 4.0). If shadow acne persists, increase both. If peter panning occurs, decrease them.

---

## Step 7: Add PCF for Soft Shadows

**Percentage Closer Filtering (PCF)** samples multiple shadow map texels and averages the results, creating soft shadow edges.

**Update `CalculateShadow()` in `lit.shader`:**

```glsl
float CalculateShadow(vec4 fragPosLightSpace, vec3 normal, vec3 lightDir)
{
    // Perspective divide
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;
    
    // Outside shadow map bounds = no shadow
    if (projCoords.z > 1.0)
        return 0.0;
    
    float currentDepth = projCoords.z;
    float bias = max(0.005 * (1.0 - dot(normal, lightDir)), 0.001);
    
    // PCF: Sample 3x3 kernel and average
    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(u_ShadowMap, 0);  // Size of one texel
    
    for (int x = -1; x <= 1; ++x)
    {
        for (int y = -1; y <= 1; ++y)
        {
            // Sample neighboring texel
            vec2 offset = vec2(x, y) * texelSize;
            float closestDepth = texture(u_ShadowMap, projCoords.xy + offset).r;
            
            // Accumulate shadow comparison
            shadow += currentDepth - bias > closestDepth ? 1.0 : 0.0;
        }
    }
    
    // Average over 9 samples
    shadow /= 9.0;
    
    return shadow;
}
```

> [!NOTE]
> **PCF Tradeoff**: 3×3 kernel = 9 samples per fragment. Larger kernels (5×5, 7×7) give softer shadows but cost more performance. For real-time applications, 3×3 is a good balance.

---

## Step 8: Shadow Map Preview in ImGui

Add a debug panel to visualize the shadow map depth texture.

**Update `Sandbox/src/SandboxApp.cpp` in `OnImGuiRender()`:**

```cpp
// =========================================================================
// Shadow Map Preview (toggle with F3)
// =========================================================================
if (m_ShowShadowMap)
{
    uiManager.StartFixedWindow("Shadow Map Debug", 360.0f, 420.0f);
    
    unsigned int shadowTexID = m_ShadowMapDepth->GetID();
    float displaySize = 320.0f;
    
    uiManager.Image(
        reinterpret_cast<void*>(static_cast<uintptr_t>(shadowTexID)),
        displaySize,
        displaySize
    );
    
    uiManager.Separator();
    uiManager.Text("Shadow Map: %dx%d", 
        m_ShadowMapFramebuffer->GetWidth(), 
        m_ShadowMapFramebuffer->GetHeight()
    );
    uiManager.Checkbox("Show Shadow Map", &m_ShowShadowMap);
    
    uiManager.EndWindow();
}
```

**Add F3 toggle in `OnEvent()`:**

```cpp
// F3 toggles Shadow Map Preview
dispatcher.Dispatch<VizEngine::KeyPressedEvent>(
    [this](VizEngine::KeyPressedEvent& event) {
        if (event.GetKeyCode() == VizEngine::KeyCode::F3 && !event.IsRepeat())
        {
            m_ShowShadowMap = !m_ShowShadowMap;
            VP_INFO("Shadow Map Preview: {}", m_ShowShadowMap ? "ON" : "OFF");
            return true;  // Consumed
        }
        return false;
    }
);
```

> [!TIP]
> The shadow map depth texture appears mostly white (near light) with darker areas (far from light). Objects closer to the light appear lighter. This visualization helps debug shadow coverage and resolution issues.

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Shadow acne** (stripes on surfaces) | Depth precision errors | Increase polygon offset or shader bias |
| **Peter panning** (shadows detached) | Bias too large | Decrease polygon offset or bias values |
| **No shadows visible** | Shadow map not bound or wrong texture slot | Verify `m_ShadowMapDepth->Bind(1)` and `SetInt("u_ShadowMap", 1)` |
| **Shadows cut off at edges** | Orthographic bounds too small | Increase `orthoSize` in light projection |
| **Blocky/pixelated shadows** | Shadow map resolution too low | Increase resolution (1024 → 2048) or use PCF |
| **Shadow map appears black** | Not clearing depth buffer | Ensure `renderer.ClearDepth()` in Pass 1 |
| **PCF samples outside bounds** | Shadow map edges | Add bounds check: `if (projCoords.x < 0.0 || projCoords.x > 1.0 ...) return 0.0;` |
| **Entire scene in shadow** | Light-space matrix incorrect | Verify `lightView` and `lightProjection` calculations |

---

## Best Practices

### 1. Shadow Map Resolution

Choose resolution based on quality needs and performance budget:

| Resolution | Use Case | Performance |
|------------|----------|-------------|
| **1024×1024** | Mobile, low-end PCs, distant shadows | Fast |
| **2048×2048** | Desktop, medium quality | Moderate |
| **4096×4096** | High-end, close-up shadows | Expensive |

> [!TIP]
> Start with 1024×1024. If shadows look too blocky, increase to 2048. Only use 4096 if targeting high-end systems.

### 2. Depth Bias Tuning

**Shader bias**: `max(0.005 * (1.0 - dot(normal, lightDir)), 0.001)`
- Increase `0.005` if acne persists
- Decrease `0.001` minimum to reduce peter panning

**Polygon offset**: `glPolygonOffset(factor, units)`
- Start with `(2.0, 4.0)`
- Increase if acne remains
- Decrease if peter panning occurs

### 3. PCF Kernel Size

| Kernel Size | Samples | Quality | Performance |
|-------------|---------|---------|-------------|
| **3×3** | 9 | Soft edges | Moderate |
| **5×5** | 25 | Very soft | Expensive |
| **7×7** | 49 | Ultra soft | Very expensive |

Use 3×3 for real-time applications. Larger kernels are for offline rendering or high-end GPUs.

### 4. Orthographic Bounds

The `orthoSize` parameter controls shadow coverage:

```cpp
float orthoSize = 10.0f;  // Covers [-10, 10] in X and Y
```

- **Too small**: Shadows disappear at scene edges
- **Too large**: Shadow quality decreases (fewer texels per world unit)

**Rule of thumb**: Set `orthoSize` just large enough to cover your scene with 10-20% padding.

### 5. Cascaded Shadow Maps (Preview)

For large scenes with distant views, a single shadow map wastes resolution:
- Close objects need high detail
- Distant objects need low detail

**Cascaded Shadow Maps (CSM)** use multiple shadow maps at different distances:
- Near cascade: 0-10 meters, 2048×2048
- Mid cascade: 10-50 meters, 1024×1024
- Far cascade: 50-200 meters, 512×512

This is beyond the scope of this chapter but is the industry standard for open-world games.

---

## Testing

1. **Build and run** the application
2. **Verify Pass 1** completes without errors (check console logs)
3. **Check shadows appear** on the ground and between objects
4. **Test F3 toggle** to view shadow map depth texture
5. **Observe shadow quality**:
   - Soft edges (if PCF is enabled)
   - No obvious acne or peter panning
   - Shadows update as light direction changes
6. **Adjust bias** if artifacts are visible
7. **Test scene movement** - shadows should follow objects correctly

---

## Milestone

**Chapter 28 Complete - Shadow Mapping**

You have:
- Implemented two-pass shadow mapping using framebuffers
- Rendered depth maps from the light's perspective
- Calculated light-space transformations with orthographic projection
- Applied shadows in shaders using depth comparison
- Fixed shadow acne with polygon offset and slope-scaled bias
- Softened shadow edges with PCF (Percentage Closer Filtering)
- Added shadow map visualization for debugging

Your scenes now have **realistic shadows** that respond to light direction and object occlusion. This is a foundational technique used in virtually all modern 3D games and renderers.

The next chapter will explore **cubemaps and skyboxes**, adding environment mapping and reflections.

---

## What's Next

In **Chapter 29: Cubemaps and Skybox**, we'll render 6-sided environment maps and create immersive skyboxes using cubemap textures.

> **Next:** [Chapter 29: Cubemaps and Skybox](29_CubemapsAndSkybox.md)

> **Previous:** [Chapter 27: Framebuffers](27_Framebuffers.md)
