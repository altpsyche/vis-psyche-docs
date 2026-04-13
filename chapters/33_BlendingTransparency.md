\newpage

# Chapter 33: Blending & Transparency

Enable alpha blending in the renderer and implement order-dependent transparency with a two-pass opaque/transparent rendering strategy.

---

## Introduction

So far, every object we render is fully opaque. The fragment shader outputs a color and it completely replaces whatever was in the framebuffer at that pixel. But real scenes contain **translucent** elements: tinted glass, particle effects, holographic UI overlays, volumetric fog, water surfaces, and fading objects.

**Why blending matters:**

| Use Case | Why Transparency? |
|----------|-------------------|
| **Glass & windows** | See-through materials with tinted color |
| **Particles** | Smoke, fire, sparks that additively blend |
| **UI overlays** | HUD elements composited over the 3D scene |
| **Fog & volumetrics** | Atmospheric effects that partially obscure geometry |
| **Fading transitions** | Objects that fade in/out over time |
| **Water surfaces** | Semi-transparent with refraction effects |

OpenGL provides a **blending stage** in the pipeline that controls how a new fragment's color is combined with the existing framebuffer color. By configuring blend factors and equations, you can achieve all of these effects.

> [!IMPORTANT]
> Transparency in rasterized rendering is fundamentally **order-dependent**. Unlike opaque geometry, transparent objects must be drawn **back-to-front** relative to the camera. This chapter addresses that challenge directly.

---

## Blending Theory

### The Blending Equation

When blending is enabled, OpenGL combines the **source** (incoming fragment) color with the **destination** (existing framebuffer) color using this equation:

```
Result = SourceColor * SrcFactor + DestColor * DstFactor
```

Where:
- **SourceColor** = the fragment shader output (`FragColor`)
- **DestColor** = the current value in the framebuffer at that pixel
- **SrcFactor** / **DstFactor** = configurable blend factors

### Common Blend Modes

| Blend Mode | SrcFactor | DstFactor | Effect |
|------------|-----------|-----------|--------|
| **Standard Alpha** | `GL_SRC_ALPHA` | `GL_ONE_MINUS_SRC_ALPHA` | Classic transparency (glass, fading) |
| **Additive** | `GL_ONE` | `GL_ONE` | Brightening (fire, glow, particles) |
| **Premultiplied Alpha** | `GL_ONE` | `GL_ONE_MINUS_SRC_ALPHA` | Pre-multiplied textures (UI compositing) |
| **Multiplicative** | `GL_DST_COLOR` | `GL_ZERO` | Darkening / tinting (stained glass) |

For this chapter, we use **Standard Alpha Blending**, which is the most common mode:

```
Result = FragColor.rgb * FragColor.a + FramebufferColor.rgb * (1.0 - FragColor.a)
```

When `alpha = 0.5`, the result is a 50/50 mix of the fragment and the background. When `alpha = 0.0`, the fragment is invisible. When `alpha = 1.0`, the fragment fully replaces the background (equivalent to opaque).

### Blend Equations

The blend equation controls the **operation** applied between the source and destination terms. The default is `GL_FUNC_ADD`, but OpenGL supports others:

| Equation | Formula | Use Case |
|----------|---------|----------|
| `GL_FUNC_ADD` | `Src * SrcFactor + Dst * DstFactor` | Standard blending (default) |
| `GL_FUNC_SUBTRACT` | `Src * SrcFactor - Dst * DstFactor` | Darkening effects |
| `GL_FUNC_REVERSE_SUBTRACT` | `Dst * DstFactor - Src * SrcFactor` | Inversion effects |
| `GL_MIN` | `min(Src, Dst)` | Shadow/depth compositing |
| `GL_MAX` | `max(Src, Dst)` | Light compositing |

### The Order-Dependent Transparency Problem

With opaque rendering, the depth buffer ensures correct occlusion regardless of draw order. But with blending, **draw order matters**:

```
Scenario: Camera -> [Glass A (near)] -> [Glass B (far)] -> [Wall (opaque)]
```

If you draw Glass A first, it blends with the (empty) framebuffer. Then Glass B draws behind it, but the depth test rejects it because Glass A already wrote to the depth buffer. The result: Glass B disappears entirely.

**The solution has two parts:**

1. **Draw opaque objects first** with normal depth testing and depth writing
2. **Draw transparent objects back-to-front** (farthest from camera first) with depth *testing* enabled but depth *writing* disabled

This is exactly what we implement in this chapter.

> [!NOTE]
> Order-independent transparency (OIT) techniques exist (weighted blended OIT, depth peeling, linked lists), but they add significant complexity. The painter's algorithm (back-to-front sorting) is the standard approach used by most real-time engines and is what we implement here.

---

## Architecture Overview

Blending and transparency in VizPsyche spans three layers:

```
1. Renderer (OpenGL state)
   +-- EnableBlending() / DisableBlending()
   +-- SetBlendFunc(src, dst)
   +-- SetBlendEquation(mode)
   +-- SetDepthMask(bool)

2. Shader (fragment output)
   +-- FragColor = vec4(result, texColor.a * u_ObjectColor.a)
       (u_ObjectColor is vec4 — alpha already lives in its w component)

3. SandboxApp (rendering strategy)
   +-- OnRender()
       +-- Classify objects: opaque (Color.a == 1.0) vs transparent (Color.a < 1.0)
       +-- Render opaque objects (normal depth test + write)
       +-- Sort transparent back-to-front, render with blending ON + depth write OFF
```

Each layer has a single responsibility: the Renderer wraps OpenGL state, the shader uses the alpha that arrives via `u_ObjectColor`, and the application orchestrates the two-pass rendering.

---

## Step 1: Renderer Blending Methods

The `Renderer` class gets four new methods that wrap the corresponding OpenGL calls. This keeps all raw OpenGL behind the engine's API boundary, which is important for our DLL architecture.

**`VizEngine/src/VizEngine/OpenGL/Renderer.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.h

class VizEngine_API Renderer
{
public:
    // ... existing methods ...

    // =====================================================================
    // Chapter 33: Blending & Transparency
    // =====================================================================

    void EnableBlending();
    void DisableBlending();
    void SetBlendFunc(unsigned int src, unsigned int dst);
    void SetBlendEquation(unsigned int mode);

    // ... rest of class ...
};
```

**`VizEngine/src/VizEngine/OpenGL/Renderer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Renderer.cpp

// =========================================================================
// Chapter 33: Blending & Transparency
// =========================================================================

void Renderer::EnableBlending()
{
    glEnable(GL_BLEND);
}

void Renderer::DisableBlending()
{
    glDisable(GL_BLEND);
}

void Renderer::SetBlendFunc(unsigned int src, unsigned int dst)
{
    glBlendFunc(src, dst);
}

void Renderer::SetBlendEquation(unsigned int mode)
{
    glBlendEquation(mode);
}
```

Each method is a thin wrapper. `EnableBlending()` activates the blend stage in the OpenGL pipeline. `SetBlendFunc()` configures the source and destination factors. `SetBlendEquation()` sets the mathematical operation (addition, subtraction, etc.).

> [!TIP]
> Notice that `SetBlendFunc` takes raw `unsigned int` parameters. This lets client code pass OpenGL constants like `GL_SRC_ALPHA` and `GL_ONE_MINUS_SRC_ALPHA` directly. The engine re-exports these constants through the `Commons.h` header.

---

## Step 2: Alpha Already Supported in defaultlit.shader

No shader changes needed. The `defaultlit.shader` from Chapter 17 already outputs a four-component color:

```glsl
// defaultlit.shader fragment — end of main()
FragColor = vec4(result, texColor.a * u_ObjectColor.a);
```

`u_ObjectColor` is a `vec4`. Its `w` component is the alpha. When `Scene::Render` sets this uniform per-object, it passes the full `obj.Color` vec4 — so `obj.Color.a` flows through automatically.

When `obj.Color.a` is `1.0` (the default), the object is fully opaque. When it is less than `1.0`, the blend stage mixes the fragment with the framebuffer background according to the blend function you configure.

> [!NOTE]
> **Why no dedicated `u_Alpha` uniform?** We already have alpha in `u_ObjectColor.w`. Adding a separate uniform would be redundant. The vec4 color carries all four channels — the shader just uses all of them.

---

## Step 3: Making Objects Transparent

Transparency is controlled through `SceneObject::Color.a`. No extra infrastructure is needed — `Color` is already a `vec4`.

**Set alpha when creating an object:**

```cpp
auto& glass = m_Scene.Add(m_CubeMesh, "GlassPane");
glass.ObjectTransform.Position = glm::vec3(0.0f, 1.0f, 0.0f);
glass.Color = glm::vec4(0.3f, 0.6f, 0.9f, 0.4f);  // Blue tint, 40% opacity
```

**The ImGui color editor already includes alpha:**

```cpp
// In OnImGuiRender() — already in the Sandbox from Chapter 24
uiManager.ColorEdit4("Color", &obj.Color.x);
```

`ColorEdit4` shows an alpha slider. Drag it below 1.0 in the UI and the object becomes transparent on the next frame — no code change needed.

**The alpha flows through automatically:**

```
obj.Color.a  →  Scene::Render sets u_ObjectColor = obj.Color  →  shader outputs FragColor.a = texColor.a * u_ObjectColor.a  →  blend stage mixes with framebuffer
```

The only thing left is to separate opaque and transparent objects at render time so they're drawn in the right order.

---

## Step 4: Two-Pass Rendering in SandboxApp

Update `OnRender()` in `SandboxApp.cpp` to split rendering into two passes. Classify objects by their `Color.a`, render opaque first, then sort and render transparent with blending.

**`Sandbox/src/SandboxApp.cpp` — replace the body of `OnRender()`:**

```cpp
void OnRender() override
{
    auto& engine   = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();

    // Set light and camera uniforms
    m_DefaultLitShader->Bind();
    m_DefaultLitShader->SetVec3("u_LightDirection", m_Light.GetDirection());
    m_DefaultLitShader->SetVec3("u_LightAmbient",   m_Light.Ambient);
    m_DefaultLitShader->SetVec3("u_LightDiffuse",   m_Light.Diffuse);
    m_DefaultLitShader->SetVec3("u_LightSpecular",  m_Light.Specular);
    m_DefaultLitShader->SetVec3("u_ViewPos",        m_Camera.GetPosition());

    renderer.Clear(m_ClearColor);

    // =========================================================================
    // Chapter 33: Two-Pass Rendering
    // Classify scene objects: opaque (Color.a == 1.0) vs transparent (Color.a < 1.0)
    // =========================================================================
    std::vector<size_t> opaqueIndices;
    std::vector<size_t> transparentIndices;

    for (size_t i = 0; i < m_Scene.Size(); i++)
    {
        auto& obj = m_Scene[i];
        if (!obj.Active || !obj.MeshPtr) continue;

        if (obj.Color.a < 1.0f)
            transparentIndices.push_back(i);
        else
            opaqueIndices.push_back(i);
    }

    // Pass 1: Opaque objects — normal depth test + depth write
    for (size_t idx : opaqueIndices)
    {
        auto& obj  = m_Scene[idx];
        glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
        m_DefaultLitShader->SetMatrix4fv("u_Model", model);
        m_DefaultLitShader->SetMatrix4fv("u_MVP",   m_Camera.GetViewProjectionMatrix() * model);
        m_DefaultLitShader->SetVec4("u_ObjectColor", obj.Color);
        m_DefaultLitShader->SetFloat("u_Roughness",  obj.Roughness);

        if (obj.TexturePtr)
            obj.TexturePtr->Bind(0);
        m_DefaultLitShader->SetInt("u_MainTex", 0);

        renderer.Draw(obj.MeshPtr->GetVertexArray(),
                      obj.MeshPtr->GetIndexBuffer(),
                      *m_DefaultLitShader);
    }

    // Pass 2: Transparent objects — sort back-to-front, blend ON, depth write OFF
    if (!transparentIndices.empty())
    {
        glm::vec3 camPos = m_Camera.GetPosition();
        std::sort(transparentIndices.begin(), transparentIndices.end(),
            [this, &camPos](size_t a, size_t b) {
                float distA = glm::length(m_Scene[a].ObjectTransform.Position - camPos);
                float distB = glm::length(m_Scene[b].ObjectTransform.Position - camPos);
                return distA > distB;  // Far objects rendered first
            });

        renderer.EnableBlending();
        renderer.SetBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        renderer.SetDepthMask(false);

        for (size_t idx : transparentIndices)
        {
            auto& obj  = m_Scene[idx];
            glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
            m_DefaultLitShader->SetMatrix4fv("u_Model", model);
            m_DefaultLitShader->SetMatrix4fv("u_MVP",   m_Camera.GetViewProjectionMatrix() * model);
            m_DefaultLitShader->SetVec4("u_ObjectColor", obj.Color);  // .a drives alpha
            m_DefaultLitShader->SetFloat("u_Roughness",  obj.Roughness);

            if (obj.TexturePtr)
                obj.TexturePtr->Bind(0);
            m_DefaultLitShader->SetInt("u_MainTex", 0);

            renderer.Draw(obj.MeshPtr->GetVertexArray(),
                          obj.MeshPtr->GetIndexBuffer(),
                          *m_DefaultLitShader);
        }

        // Restore default state
        renderer.SetDepthMask(true);
        renderer.DisableBlending();
    }
}
```

The alpha flows from `obj.Color.a` → `u_ObjectColor.w` → `FragColor.a` → blend stage. No extra material system required.

---

## The Transparency Sorting Algorithm Explained

The sorting algorithm in `RenderSceneObjects()` deserves a closer look. Here is what happens step by step:

### 1. Classification

```cpp
if (obj.Color.a < 1.0f)
    transparentIndices.push_back(i);
else
    opaqueIndices.push_back(i);
```

Every active object is classified as either opaque (`alpha == 1.0`) or transparent (`alpha < 1.0`). We collect indices rather than copying objects, keeping the operation lightweight.

### 2. Opaque Pass

```cpp
for (size_t idx : opaqueIndices)
{
    RenderSingleObject(m_Scene[idx], renderer);
}
```

Opaque objects are rendered first, in any order, with the default depth test (`GL_LESS`) and depth writing enabled. After this pass, the depth buffer contains the correct depths for all opaque surfaces.

### 3. Transparent Sort

```cpp
std::sort(transparentIndices.begin(), transparentIndices.end(),
    [this, &camPos](size_t a, size_t b) {
        float distA = glm::length(m_Scene[a].ObjectTransform.Position - camPos);
        float distB = glm::length(m_Scene[b].ObjectTransform.Position - camPos);
        return distA > distB;  // Far objects first
    });
```

Transparent objects are sorted by their **distance from the camera**. The comparison `distA > distB` places the farthest object first in the sorted order. This implements the classic **painter's algorithm**: draw the background layers before the foreground layers so that nearer transparent objects correctly blend over farther ones.

> [!TIP]
> We sort by object position (center point), not by individual triangle. For simple convex objects this works well. For large or overlapping transparent meshes, you may need per-triangle sorting or an order-independent technique.

### 4. Transparent Pass

```cpp
renderer.EnableBlending();
renderer.SetBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
renderer.SetDepthMask(false);  // Don't write to depth buffer
```

Three state changes are critical here:

1. **`EnableBlending()`** turns on the blend stage so fragments mix with the background
2. **`SetBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)`** configures standard alpha blending
3. **`SetDepthMask(false)`** disables depth **writing** (but depth **testing** stays on)

The depth mask is the subtle but crucial part. Depth testing remains enabled so that transparent objects are correctly occluded by opaque objects in front of them. But depth writing is disabled so that transparent objects do not occlude each other -- if Glass A is at depth 5 and Glass B is at depth 10, we want both to be visible, not have Glass A's depth reject Glass B.

> [!NOTE]
> **Two-Pass Depth Pattern**: This structure — write depth in pass 1, read-only in pass 2 — is the same principle as shadow mapping (Chapter 29). In that chapter, pass 1 renders the scene from the light's perspective to a shadow FBO (depth writes enabled), and pass 2 reads that depth texture without writing. Both techniques rely on precise depth mask state to prevent artifacts. If you've already implemented Chapter 29, this two-pass pattern should feel familiar.

### 5. State Restoration

```cpp
renderer.SetDepthMask(true);
renderer.DisableBlending();
```

After rendering all transparent objects, we restore the default state so that subsequent rendering passes (skybox, outlines, UI) are not affected.

---

## Setting Object Transparency at Runtime

The ImGui panel in the Sandbox already uses `ColorEdit4()` which includes an alpha slider:

```cpp
// Sandbox/src/SandboxApp.cpp (in OnImGuiRender, Scene Objects panel)

uiManager.ColorEdit4("Color", &obj.Color.x);
```

Since `obj.Color` is a `glm::vec4`, the fourth component (`obj.Color.a`) is the alpha. When you drag the alpha slider below 1.0 in the color editor, the object immediately becomes transparent and is routed through the blending pass on the next frame.

You can also set transparency programmatically when creating objects:

```cpp
// Example: Creating a transparent object
auto& glass = m_Scene.Add(m_CubeMesh, "GlassPane");
glass.ObjectTransform.Position = glm::vec3(0.0f, 1.0f, 0.0f);
glass.Color = glm::vec4(0.3f, 0.6f, 0.9f, 0.4f);  // Blue tint, 40% opacity
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| **Transparent objects invisible** | Blending not enabled | Ensure `EnableBlending()` is called before drawing transparent objects |
| **Transparent objects flicker / z-fight** | Depth writing enabled during blend pass | Call `SetDepthMask(false)` before the transparent pass |
| **Transparent objects occlude each other** | Wrong sort order | Sort back-to-front (`distA > distB`, not `<`) |
| **Transparent objects not occluded by opaque** | Depth testing disabled | Keep `glDepthFunc(GL_LESS)` active; only disable depth *writing* |
| **Opaque objects drawn with blending** | Forgot to classify or disable blending | Ensure opaque pass runs with blending off; transparent pass re-enables it |
| **Black fringes around transparent edges** | Blend func not set correctly | Use `GL_SRC_ALPHA` / `GL_ONE_MINUS_SRC_ALPHA` for standard alpha blending |
| **Blending state leaks to other passes** | State not restored after transparent pass | Always call `DisableBlending()` and `SetDepthMask(true)` after the pass |
| **Objects pop between opaque/transparent** | Alpha toggling at threshold boundary | Use a small epsilon or hysteresis; `alpha < 1.0f` is the standard test |

---

## Best Practices

### 1. Always Render Opaque First

Opaque objects fill the depth buffer. This allows transparent objects to be correctly depth-tested against them. Never interleave opaque and transparent draw calls.

### 2. Disable Depth Writing for Transparent Objects

Use `SetDepthMask(false)` during the transparent pass. Transparent fragments should not update the depth buffer because doing so would prevent other transparent objects behind them from being drawn.

### 3. Keep Depth Testing Enabled

Disabling depth testing entirely (`DisableDepthTest()`) during the transparent pass would cause transparent objects to draw on top of opaque objects that are in front of them. Only disable depth *writing*, not depth *testing*.

### 4. Restore State After Blending

Always clean up after the transparent pass:

```cpp
renderer.SetDepthMask(true);
renderer.DisableBlending();
```

Other rendering passes (skybox, stencil outlines, post-processing) depend on the default state.

### 5. Sort by Distance, Not Depth

Sorting by Euclidean distance from the camera position is simpler and more robust than projecting to clip space. For most scenes with moderate numbers of transparent objects, `glm::length()` per object is negligible.

### 6. Consider Performance

The per-frame sort is `O(n log n)` where `n` is the number of transparent objects. For scenes with hundreds of transparent objects, consider:
- Spatial partitioning to cull distant transparent objects
- Reducing the number of transparent objects visible at once
- Order-independent transparency (OIT) techniques for complex scenes

---

## Blend Factor Reference

| OpenGL Constant | Factor Value |
|-----------------|--------------|
| `GL_ZERO` | `(0, 0, 0, 0)` |
| `GL_ONE` | `(1, 1, 1, 1)` |
| `GL_SRC_COLOR` | `(Rs, Gs, Bs, As)` |
| `GL_ONE_MINUS_SRC_COLOR` | `(1-Rs, 1-Gs, 1-Bs, 1-As)` |
| `GL_DST_COLOR` | `(Rd, Gd, Bd, Ad)` |
| `GL_ONE_MINUS_DST_COLOR` | `(1-Rd, 1-Gd, 1-Bd, 1-Ad)` |
| `GL_SRC_ALPHA` | `(As, As, As, As)` |
| `GL_ONE_MINUS_SRC_ALPHA` | `(1-As, 1-As, 1-As, 1-As)` |
| `GL_DST_ALPHA` | `(Ad, Ad, Ad, Ad)` |
| `GL_ONE_MINUS_DST_ALPHA` | `(1-Ad, 1-Ad, 1-Ad, 1-Ad)` |
| `GL_CONSTANT_COLOR` | `(Rc, Gc, Bc, Ac)` |

---

## Milestone

**Chapter 33 Complete**

You have:
- Added `EnableBlending()`, `DisableBlending()`, `SetBlendFunc()`, and `SetBlendEquation()` to the Renderer
- Understood that `defaultlit.shader` already supports alpha via `u_ObjectColor.a` — no shader changes needed
- Split `OnRender()` into two passes: opaque first, then transparent back-to-front
- Added back-to-front sorting for transparent objects using the painter's algorithm
- Properly managed depth mask state to avoid transparent-on-transparent occlusion errors

Any object in the scene can now be made transparent by setting its `Color.a` below 1.0, either through the ImGui color editor or programmatically.

---

## What's Next

In **Chapter 34: Normal Mapping**, we'll add tangent-space normal maps to our PBR pipeline, giving flat surfaces the illusion of fine geometric detail without adding extra polygons.

> **Previous:** [Chapter 32: Depth & Stencil Testing](32_DepthStencilTesting.md) | **Next:** [Chapter 34: Normal Mapping](34_NormalMapping.md)
