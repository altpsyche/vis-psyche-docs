\newpage

# Chapter 20: Model Loader (Materials)

Chapter 19 gave us geometry — the duck renders with correct shape and Blinn-Phong lighting. Every mesh still uses the scene object's default gray because we haven't taught the loader to read material data. This chapter does that.

glTF stores a base color, a shininess-equivalent, and a texture for each material. Our Blinn-Phong shader already has uniforms for all three. By the end of this chapter, loading a model applies its actual material — the duck renders yellow.

---

## What glTF gives us at this stage

Every glTF material has a `pbrMetallicRoughness` block. That name will matter in Chapter 36 when we study physically-based rendering. For now, two values from it are immediately useful:

**`baseColorFactor`** — RGBA color multiplied against the base texture. A white `(1, 1, 1, 1)` means the texture is used as-is. A colored factor tints it.

**`roughnessFactor`** — a 0–1 value where 0 is mirror-smooth and 1 is fully rough. Our `defaultlit.shader` accepts `u_Roughness` directly and converts it to a Blinn-Phong shininess exponent internally (`mix(256.0, 8.0, u_Roughness)`). We store the raw roughness value — no conversion needed in the loader.

**`baseColorTexture`** — index into the glTF texture array. This is the albedo map our shader samples as `u_MainTex`.

Those three cover everything our renderer can currently use. The rest of glTF's PBR material data — metallic factor, normal maps, occlusion, emissive — becomes relevant as later chapters add the rendering systems that consume them.

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
#include <string>

namespace VizEngine
{
    struct VizEngine_API Material
    {
        std::string Name = "Unnamed";

        glm::vec4 BaseColor = glm::vec4(1.0f);  // RGBA albedo tint
        float     Roughness = 0.5f;              // 0 = smooth/mirror, 1 = rough/matte

        std::shared_ptr<Texture> BaseColorTexture = nullptr;  // nullptr = use solid color

        Material() = default;

        explicit Material(const glm::vec4& baseColor)
            : BaseColor(baseColor) {}

        Material(const glm::vec4& baseColor, float roughness)
            : BaseColor(baseColor), Roughness(roughness) {}
    };

}  // namespace VizEngine
```

Simple. Every field maps directly to a uniform the current shader already accepts.

---

## Step 2: Update Model.h

Add material members and `GetMaterialForMesh` alongside the geometry members from Chapter 19:

**Modify `VizEngine/src/VizEngine/Core/Model.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Model.h

#pragma once

#include "VizEngine/Core.h"
#include "Mesh.h"
#include "Material.h"
#include <vector>
#include <memory>
#include <string>

namespace VizEngine
{
    class VizEngine_API Model
    {
    public:
        static std::unique_ptr<Model> LoadFromFile(const std::string& filepath);

        ~Model() = default;

        Model(const Model&) = delete;
        Model& operator=(const Model&) = delete;

        Model(Model&&) noexcept = default;
        Model& operator=(Model&&) noexcept = default;

        // Geometry
        const std::vector<std::shared_ptr<Mesh>>& GetMeshes() const { return m_Meshes; }
        size_t GetMeshCount() const { return m_Meshes.size(); }

        // Materials
        const std::vector<Material>& GetMaterials() const { return m_Materials; }
        const Material& GetMaterialForMesh(size_t meshIndex) const;

        const std::string& GetName()     const { return m_Name; }
        const std::string& GetFilePath() const { return m_FilePath; }
        bool IsValid() const { return !m_Meshes.empty(); }

    private:
        Model() = default;

        std::string m_Name;
        std::string m_FilePath;
        std::string m_Directory;

        std::vector<std::shared_ptr<Mesh>> m_Meshes;
        std::vector<Material>              m_Materials;
        std::vector<size_t>                m_MeshMaterialIndices;

        static Material s_DefaultMaterial;

        class ModelLoader;
    };

}  // namespace VizEngine
```

---

## Step 3: LoadMaterials in Model.cpp

Add the static default material, `GetMaterialForMesh`, and `LoadMaterials` to `Model.cpp`.

First, the static default and the accessor (these go near the top of the file, after the file-path helpers):

```cpp
    Material Model::s_DefaultMaterial = Material(glm::vec4(0.8f, 0.8f, 0.8f, 1.0f));

    const Material& Model::GetMaterialForMesh(size_t meshIndex) const
    {
        if (meshIndex < m_MeshMaterialIndices.size())
        {
            size_t matIdx = m_MeshMaterialIndices[meshIndex];
            if (matIdx < m_Materials.size())
                return m_Materials[matIdx];
        }
        return s_DefaultMaterial;
    }
```

Update the `ModelLoader` class definition to declare the new methods:

```cpp
    class Model::ModelLoader
    {
    public:
        static std::unique_ptr<Model> Load(const std::string& filepath);

    private:
        ModelLoader(Model* model, const std::string& filepath)
            : m_Model(model), m_Directory(GetDirectory(filepath)) {}

        void LoadMaterials(const tinygltf::Model& gltfModel);
        void LoadMeshes(const tinygltf::Model& gltfModel);
        void LoadIndices(const tinygltf::Model& gltfModel,
                         const tinygltf::Accessor& accessor,
                         std::vector<unsigned int>& indices);

        std::shared_ptr<Texture> LoadTexture(const tinygltf::Model& gltfModel,
                                              int textureIndex);

        Model*      m_Model;
        std::string m_Directory;

        // Multiple materials can reference the same image — load each once.
        std::unordered_map<int, std::shared_ptr<Texture>> m_TextureCache;
    };
```

Update `ModelLoader::Load` to call `LoadMaterials` before `LoadMeshes`. Material indices in `LoadMeshes` are validated against `m_Materials.size()`, so the vector must be populated first:

```cpp
        ModelLoader modelLoader(model.get(), filepath);
        modelLoader.LoadMaterials(gltfModel);  // fills m_Materials — must run before LoadMeshes
        modelLoader.LoadMeshes(gltfModel);
```

Now the implementation of `LoadMaterials`:

```cpp
    void Model::ModelLoader::LoadMaterials(const tinygltf::Model& gltfModel)
    {
        for (const auto& gltfMat : gltfModel.materials)
        {
            Material material;
            material.Name = gltfMat.name.empty() ? "Material" : gltfMat.name;

            const auto& pbr = gltfMat.pbrMetallicRoughness;

            // Base color
            material.BaseColor = glm::vec4(
                static_cast<float>(pbr.baseColorFactor[0]),
                static_cast<float>(pbr.baseColorFactor[1]),
                static_cast<float>(pbr.baseColorFactor[2]),
                static_cast<float>(pbr.baseColorFactor[3])
            );

            // glTF roughnessFactor maps directly to our u_Roughness uniform.
            // The shader converts roughness → shininess internally.
            material.Roughness = static_cast<float>(pbr.roughnessFactor);

            // Base color texture
            if (pbr.baseColorTexture.index >= 0)
                material.BaseColorTexture = LoadTexture(gltfModel, pbr.baseColorTexture.index);

            m_Model->m_Materials.push_back(std::move(material));
        }

        // Always have at least one material so LoadMeshes can safely index into m_Materials.
        if (m_Model->m_Materials.empty())
            m_Model->m_Materials.push_back(Model::s_DefaultMaterial);
    }
```

---

## Step 4: LoadTexture

glTF images are either embedded in the binary (`.glb`) or referenced by a relative path (`.gltf`). tinygltf handles both cases: for embedded images it decodes the pixel data into `image.image`; for external files it sets `image.uri` and leaves decoding to us.

```cpp
    std::shared_ptr<Texture> Model::ModelLoader::LoadTexture(
        const tinygltf::Model& gltfModel, int textureIndex)
    {
        if (textureIndex < 0 ||
            textureIndex >= static_cast<int>(gltfModel.textures.size()))
            return nullptr;

        // Return cached texture if already loaded
        auto it = m_TextureCache.find(textureIndex);
        if (it != m_TextureCache.end())
            return it->second;

        const auto& texture = gltfModel.textures[textureIndex];

        if (texture.source < 0 ||
            texture.source >= static_cast<int>(gltfModel.images.size()))
            return nullptr;

        const auto& image = gltfModel.images[texture.source];
        std::shared_ptr<Texture> tex;

        if (!image.image.empty())
        {
            // Embedded image (GLB) — pixel data already decoded by tinygltf
            tex = std::make_shared<Texture>(
                image.image.data(),
                image.width,
                image.height,
                image.component
            );
            VP_CORE_TRACE("Loaded embedded texture: {}x{}", image.width, image.height);
        }
        else if (!image.uri.empty())
        {
            // External image (GLTF) — path is relative to the model directory
            std::string fullPath = m_Directory.empty()
                ? image.uri
                : m_Directory + "/" + image.uri;

            tex = std::make_shared<Texture>(fullPath);
            VP_CORE_TRACE("Loaded external texture: {}", image.uri);
        }

        if (tex)
            m_TextureCache[textureIndex] = tex;

        return tex;
    }
```

---

## Step 5: Track material indices in LoadMeshes

Each glTF primitive carries a `material` index (-1 means none). After pushing the mesh, record which material it uses:

**In `LoadMeshes`, after `m_Model->m_Meshes.push_back(...)`:**

```cpp
                m_Model->m_Meshes.push_back(std::make_shared<Mesh>(vertices, indices));

                size_t materialIndex = 0;
                if (primitive.material >= 0)
                {
                    size_t matIdx = static_cast<size_t>(primitive.material);
                    if (matIdx < m_Model->m_Materials.size())
                        materialIndex = matIdx;
                    else
                        VP_CORE_WARN("Material index {} out of bounds, using default", matIdx);
                }
                m_Model->m_MeshMaterialIndices.push_back(materialIndex);
```

---

## Usage Example

```cpp
auto duck = Model::LoadFromFile("assets/gltf-samples/Models/Duck/glTF-Binary/Duck.glb");

if (!duck) return;

for (size_t i = 0; i < duck->GetMeshCount(); i++)
{
    auto& obj = scene.Add(duck->GetMeshes()[i], "Duck");
    obj.ObjectTransform.Scale = glm::vec3(0.01f);

    const auto& mat = duck->GetMaterialForMesh(i);
    obj.Color      = mat.BaseColor;
    obj.Roughness  = mat.Roughness;
    obj.TexturePtr = mat.BaseColorTexture;  // nullptr if no texture
}
```

The duck renders yellow with its embedded texture and a shininess derived from its glTF roughness value.

---

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| No texture on mesh | `BaseColorTexture` is nullptr | Check glTF export — enable texture embedding for `.glb` |
| Correct shape, wrong color | Scene object color overriding | Apply `mat.BaseColor` to `obj.Color` |
| All meshes same color | `GetMaterialForMesh` always returning default | Verify materials are assigned in your DCC tool |
| External textures not loading | Path resolution failure | Use `.glb`, or ensure texture files sit beside the `.gltf` |

---

## Milestone

**Model Loader (Materials) complete.**

You have:
- `Material` struct with BaseColor, Roughness, BaseColorTexture
- `LoadMaterials()` extracting color, roughness (direct from glTF), and base texture
- `LoadTexture()` with cache — each image uploaded to the GPU once
- `GetMaterialForMesh()` for per-mesh material lookup
- Models render with their actual colors and textures

---

## What's Next

In **Chapter 21**, we'll add an input system to handle keyboard and mouse events.

> **Next:** [Chapter 21: Input System](21_InputSystem.md)

> **Previous:** [Chapter 19: Model Loader (Geometry)](19_ModelLoaderGeometry.md)
