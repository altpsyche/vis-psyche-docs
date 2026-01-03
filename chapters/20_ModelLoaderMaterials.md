\newpage

# Chapter 20: Model Loader (Materials)

Extend the model loader to extract glTF materials and textures.

---

## Step 1: Create Material.h

**Create `VizEngine/src/VizEngine/Core/Material.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Material.h

#pragma once

#include "VizEngine/Core.h"
#include "VizEngine/OpenGL/Texture.h"
#include "glm.hpp"
#include <memory>

namespace VizEngine
{
    struct VizEngine_API PBRMaterial
    {
        glm::vec4 BaseColor = glm::vec4(1.0f);
        std::shared_ptr<Texture> BaseColorTexture;

        float Metallic = 0.0f;
        float Roughness = 0.5f;
        std::shared_ptr<Texture> MetallicRoughnessTexture;

        std::shared_ptr<Texture> NormalTexture;
        float NormalScale = 1.0f;

        glm::vec3 EmissiveFactor = glm::vec3(0.0f);
        std::shared_ptr<Texture> EmissiveTexture;

        enum class AlphaMode { Opaque, Mask, Blend };
        AlphaMode Alpha = AlphaMode::Opaque;
        float AlphaCutoff = 0.5f;

        bool DoubleSided = false;

        PBRMaterial() = default;
    };

}  // namespace VizEngine
```

---

## Step 2: Update Model.h

Add material loading to Model:

```cpp
// In Model.h
#include "Material.h"

class Model
{
public:
    const std::vector<PBRMaterial>& GetMaterials() const { return m_Materials; }
    const PBRMaterial& GetMaterialForMesh(size_t meshIndex) const;

private:
    std::vector<PBRMaterial> m_Materials;
    std::vector<size_t> m_MeshMaterialIndices;
};
```

---

## Step 3: Material Extraction (excerpt)

```cpp
// In Model.cpp LoadFromFile implementation
for (const auto& mat : gltf.materials)
{
    PBRMaterial material;

    const auto& pbr = mat.pbrMetallicRoughness;
    material.BaseColor = glm::vec4(
        pbr.baseColorFactor[0],
        pbr.baseColorFactor[1],
        pbr.baseColorFactor[2],
        pbr.baseColorFactor[3]
    );

    material.Metallic = static_cast<float>(pbr.metallicFactor);
    material.Roughness = static_cast<float>(pbr.roughnessFactor);

    if (pbr.baseColorTexture.index >= 0)
        material.BaseColorTexture = LoadTexture(gltf, pbr.baseColorTexture.index);

    model->m_Materials.push_back(std::move(material));
}
```

---

## Usage Example

```cpp
// Load model using static factory
auto model = Model::LoadFromFile("assets/helmet.glb");

if (!model)
{
    VP_CORE_ERROR("Failed to load model!");
    return;
}

// Add meshes to scene with materials
for (size_t i = 0; i < model->GetMeshCount(); i++)
{
    auto& obj = scene.Add(model->GetMeshes()[i], "Part_" + std::to_string(i));

    // Apply material properties
    const auto& mat = model->GetMaterialForMesh(i);
    obj.Color = mat.BaseColor;
    obj.Roughness = mat.Roughness;
    obj.TexturePtr = mat.BaseColorTexture;
}
```

> [!NOTE]
> - Use `Model::LoadFromFile()` (static factory), not constructor
> - Use `scene.Add()`, not `scene.AddObject()`
> - Use `obj.TexturePtr`, not `obj.ObjectTexture`
> - Use `obj.Roughness`, not `obj.Shininess`

---

## Milestone

**Model Loader (Materials) Complete**

You have:
- `PBRMaterial` struct with glTF PBR properties
- Material extraction from glTF
- `GetMaterialForMesh()` convenience method

---

## What's Next

In **Chapter 21**, we'll add an Input system.

> **Next:** [Chapter 21: Input System](21_InputSystem.md)

> **Previous:** [Chapter 19: Model Loader (Geometry)](19_ModelLoaderGeometry.md)
