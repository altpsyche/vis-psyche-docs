\newpage

# Chapter 20: Model Loader (Materials)

Extend the model loader to extract glTF materials and textures.

---

## Step 1: Material Struct

We already created Material.h in Chapter 19. The struct stores:

```cpp
struct Material {
    glm::vec4 BaseColor = glm::vec4(1.0f);
    float Shininess = 32.0f;  // Blinn-Phong exponent
    std::shared_ptr<Texture> BaseColorTexture;
};
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
    const std::vector<Material>& GetMaterials() const { return m_Materials; }
    const Material& GetMaterialForMesh(size_t meshIndex) const;

private:
    std::vector<Material> m_Materials;
    std::vector<size_t> m_MeshMaterialIndices;
};
```

---

## Step 3: Material Extraction (excerpt)

```cpp
// In Model.cpp LoadFromFile implementation
for (const auto& mat : gltf.materials)
{
    Material material;

    const auto& pbr = mat.pbrMetallicRoughness;
    material.BaseColor = glm::vec4(
        pbr.baseColorFactor[0],
        pbr.baseColorFactor[1],
        pbr.baseColorFactor[2],
        pbr.baseColorFactor[3]
    );

    // Convert glTF roughness (0-1) to Blinn-Phong shininess
    float roughness = static_cast<float>(pbr.roughnessFactor);
    material.Shininess = glm::mix(256.0f, 8.0f, roughness);

    if (pbr.baseColorTexture.index >= 0)
        material.BaseColorTexture = LoadTexture(gltf, pbr.baseColorTexture.index);

    model->m_Materials.push_back(std::move(material));
}
```

> [!NOTE]
> glTF stores PBR materials with roughness (0-1). We convert to shininess for Blinn-Phong rendering. Chapter 37 will upgrade to proper PBR using roughness directly.

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
    obj.Shininess = mat.Shininess;
    obj.TexturePtr = mat.BaseColorTexture;
}
```

> [!NOTE]
> - Use `Model::LoadFromFile()` (static factory), not constructor
> - Use `scene.Add()`, not `scene.AddObject()`
> - Use `obj.Shininess`, not `obj.Roughness` (that's for Chapter 37)

---

## Milestone

**Model Loader (Materials) Complete**

You have:
- `Material` struct with BaseColor, Shininess, Texture
- glTF roughness → shininess conversion
- `GetMaterialForMesh()` convenience method

---

## What's Next

In **Chapter 21**, we'll add an Input system.

> **Next:** [Chapter 21: Input System](21_InputSystem.md)

> **Previous:** [Chapter 19: Model Loader (Geometry)](19_ModelLoaderGeometry.md)
