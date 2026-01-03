\newpage

# Chapter 16: Blinn-Phong Lighting

Add realistic lighting with the Blinn-Phong illumination model.

---

## Lighting Components

| Component | Effect |
|-----------|--------|
| **Ambient** | Base illumination everywhere |
| **Diffuse** | Light scattered from matte surfaces |
| **Specular** | Shiny highlights on glossy surfaces |

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

## Step 2: Create Lit Shader

**Create `VizEngine/src/resources/shaders/lit.shader`:**

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
uniform float u_Roughness;

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

    // Convert roughness (0=shiny, 1=matte) to shininess exponent
    float shininess = mix(256.0, 8.0, u_Roughness);
    float spec = pow(max(dot(norm, halfDir), 0.0), shininess);
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
> - Uses `u_Roughness` with `mix(256.0, 8.0, roughness)` to convert to shininess

---

## Step 3: Set Light Uniforms

```cpp
DirectionalLight light;
light.Direction = glm::vec3(-0.5f, -1.0f, -0.3f);
light.Ambient = glm::vec3(0.2f, 0.2f, 0.25f);
light.Diffuse = glm::vec3(0.8f, 0.8f, 0.75f);
light.Specular = glm::vec3(1.0f, 1.0f, 0.95f);

// In render loop
litShader.Bind();
litShader.SetVec3("u_LightDirection", light.GetDirection());
litShader.SetVec3("u_LightAmbient", light.Ambient);
litShader.SetVec3("u_LightDiffuse", light.Diffuse);
litShader.SetVec3("u_LightSpecular", light.Specular);
litShader.SetVec3("u_ViewPos", camera.GetPosition());

scene.Render(renderer, litShader, camera);
```

---

## Roughness to Shininess

The shader converts roughness (PBR-style, 0-1) to Blinn-Phong shininess:

```glsl
float shininess = mix(256.0, 8.0, u_Roughness);
```

| Roughness | Shininess | Appearance |
|-----------|-----------|------------|
| 0.0 | 256 | Mirror-like |
| 0.5 | 132 | Semi-glossy |
| 1.0 | 8 | Very matte |

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
- Lit shader with roughness-to-shininess conversion
- In-shader normal matrix computation
- Matches actual codebase implementation

---

## What's Next

In **Chapter 17**, we'll cover glTF format and add `tinygltf`.

> **Next:** [Chapter 17: glTF Format](17_glTFFormat.md)

> **Previous:** [Chapter 15: Dear ImGui](15_DearImGui.md)
