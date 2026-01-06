\newpage

# Chapter 17: Lighting

Add realistic lighting with the Blinn-Phong illumination model.

---

## Lighting Components

| Component | Effect |
|-----------|--------|
| **Ambient** | Base illumination everywhere |
| **Diffuse** | Light scattered from matte surfaces |
| **Specular** | Shiny highlights on glossy surfaces |

> [!NOTE]
> **Shader Transition**: Until now we've been using `unlit.shader` from Chapter 10. This chapter introduces `defaultlit.shader` with lighting calculations, and we'll switch to using it.

---

## Step 0: Update SceneObject

Add a `Shininess` field to `SceneObject` for specular control:

```cpp
// In SceneObject.h - add after Color field
float Shininess = 32.0f;  // Blinn-Phong exponent (higher = shinier)
```

---

## Step 1: Create Light.h

**Create `VizEngine/src/VizEngine/Core/Light.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Light.h

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"

namespace VizEngine
{
    struct VizEngine_API DirectionalLight
    {
        glm::vec3 Direction = glm::vec3(-0.2f, -1.0f, -0.3f);

        glm::vec3 Ambient  = glm::vec3(0.2f, 0.2f, 0.2f);
        glm::vec3 Diffuse  = glm::vec3(0.8f, 0.8f, 0.8f);
        glm::vec3 Specular = glm::vec3(1.0f, 1.0f, 1.0f);

        DirectionalLight() = default;

        DirectionalLight(const glm::vec3& direction)
            : Direction(glm::normalize(direction)) {}

        DirectionalLight(const glm::vec3& direction, const glm::vec3& color)
            : Direction(glm::normalize(direction))
            , Ambient(color * 0.2f)
            , Diffuse(color * 0.8f)
            , Specular(color) {}

        glm::vec3 GetDirection() const { return glm::normalize(Direction); }
    };

    struct VizEngine_API PointLight
    {
        glm::vec3 Position = glm::vec3(0.0f, 5.0f, 0.0f);

        glm::vec3 Ambient  = glm::vec3(0.1f, 0.1f, 0.1f);
        glm::vec3 Diffuse  = glm::vec3(0.8f, 0.8f, 0.8f);
        glm::vec3 Specular = glm::vec3(1.0f, 1.0f, 1.0f);

        float Constant  = 1.0f;
        float Linear    = 0.09f;
        float Quadratic = 0.032f;

        PointLight() = default;
        PointLight(const glm::vec3& position) : Position(position) {}
    };

}  // namespace VizEngine
```

---

## Step 2: Create Default Lit Shader

**Create `VizEngine/src/resources/shaders/defaultlit.shader`:**

```glsl
#shader vertex
#version 460 core

layout (location = 0) in vec4 aPos;      // vec4 for homogeneous coords
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec4 aColor;
layout (location = 3) in vec2 aTexCoord;

out vec3 v_FragPos;
out vec3 v_Normal;
out vec4 v_Color;
out vec2 v_TexCoord;

uniform mat4 u_Model;
uniform mat4 u_MVP;

void main()
{
    // Fragment position in world space
    v_FragPos = vec3(u_Model * aPos);

    // Transform normal to world space
    // Note: For non-uniform scaling, use inverse transpose
    v_Normal = mat3(transpose(inverse(u_Model))) * aNormal;

    v_Color = aColor;
    v_TexCoord = aTexCoord;

    gl_Position = u_MVP * aPos;
}

#shader fragment
#version 460 core

out vec4 FragColor;

in vec3 v_FragPos;
in vec3 v_Normal;
in vec4 v_Color;
in vec2 v_TexCoord;

// Light
uniform vec3 u_LightDirection;
uniform vec3 u_LightAmbient;
uniform vec3 u_LightDiffuse;
uniform vec3 u_LightSpecular;

// Camera
uniform vec3 u_ViewPos;

// Object
uniform vec4 u_ObjectColor;
uniform sampler2D u_MainTex;

// Material
uniform float u_Shininess;

void main()
{
    // Sample texture
    vec4 texColor = texture(u_MainTex, v_TexCoord);

    // Base color: texture * vertex color * object color
    vec3 baseColor = texColor.rgb * v_Color.rgb * u_ObjectColor.rgb;

    // Normalize normal (interpolation can denormalize)
    vec3 norm = normalize(v_Normal);

    // Light direction (pointing FROM light TO fragment)
    vec3 lightDir = normalize(-u_LightDirection);

    // === AMBIENT ===
    vec3 ambient = u_LightAmbient * baseColor;

    // === DIFFUSE ===
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = u_LightDiffuse * diff * baseColor;

    // === SPECULAR (Blinn-Phong) ===
    vec3 viewDir = normalize(u_ViewPos - v_FragPos);
    vec3 halfDir = normalize(lightDir + viewDir);

    // Shininess exponent: higher = tighter specular highlight
    float spec = pow(max(dot(norm, halfDir), 0.0), u_Shininess);
    vec3 specular = u_LightSpecular * spec;

    // Combine
    vec3 result = ambient + diffuse + specular;

    FragColor = vec4(result, texColor.a * u_ObjectColor.a);
}
```

> [!IMPORTANT]
> **Key differences from basic Phong:**
> - Uses `vec4 aPos` for homogeneous coordinates (matches Vertex struct)
> - Normal matrix computed **in-shader** for simplicity: `mat3(transpose(inverse(u_Model)))`
> - Uses `u_Shininess` directly as Blinn-Phong exponent (higher = shinier)
>
> **Chapter 33** will replace `u_Shininess` with `u_Roughness` and `u_Metallic` for full PBR.

---

## Step 3: Set Light Uniforms

```cpp
DirectionalLight light;
light.Direction = glm::vec3(-0.5f, -1.0f, -0.3f);
light.Ambient = glm::vec3(0.2f, 0.2f, 0.25f);
light.Diffuse = glm::vec3(0.8f, 0.8f, 0.75f);
light.Specular = glm::vec3(1.0f, 1.0f, 0.95f);

// In render loop
defaultLitShader.Bind();
defaultLitShader.SetVec3("u_LightDirection", light.GetDirection());
defaultLitShader.SetVec3("u_LightAmbient", light.Ambient);
defaultLitShader.SetVec3("u_LightDiffuse", light.Diffuse);
defaultLitShader.SetVec3("u_LightSpecular", light.Specular);
defaultLitShader.SetVec3("u_ViewPos", camera.GetPosition());

scene.Render(renderer, defaultLitShader, camera);
```

---

## Shininess Values

| Shininess | Appearance |
|-----------|------------|
| 8 | Very matte |
| 32 | Default |
| 128 | Glossy |
| 256 | Mirror-like |

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Flat shading | Normals zero | Mesh must have valid normals |
| Dark objects | No ambient | Increase `Ambient` component |
| Harsh specular | Low roughness | Increase roughness (try 0.5) |

---

## Milestone

**Blinn-Phong Lighting Complete**

You have:
- `DirectionalLight` with Ambient/Diffuse/Specular
- `defaultlit.shader` with Shininess-based specular
- In-shader normal matrix computation

> [!TIP]
> In **Chapter 33**, we'll upgrade `defaultlit.shader` to use Cook-Torrance PBR, replacing the Blinn-Phong specular calculation with physically-based equations.

---

## What's Next

In **Chapter 18**, we'll cover glTF format and add `tinygltf`.

> **Next:** [Chapter 18: glTF Format](18_glTFFormat.md)

> **Previous:** [Chapter 16: Dear ImGui](16_DearImGui.md)
