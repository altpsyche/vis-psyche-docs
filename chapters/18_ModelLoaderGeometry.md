\newpage

# Chapter 18: Model Loader (Geometry)

Create a `Model` class that loads glTF geometry using a static factory pattern.

---

## Step 1: Create Model.h

**Create `VizEngine/src/VizEngine/Core/Model.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Model.h

#pragma once

#include "VizEngine/Core.h"
#include "Mesh.h"
#include "Material.h"
#include "VizEngine/OpenGL/Texture.h"
#include "glm.hpp"
#include <vector>
#include <memory>
#include <string>
#include <unordered_map>

namespace VizEngine
{
    class VizEngine_API Model
    {
    public:
        // Static factory - returns nullptr on failure
        static std::unique_ptr<Model> LoadFromFile(const std::string& filepath);

        ~Model() = default;

        // Prevent copying
        Model(const Model&) = delete;
        Model& operator=(const Model&) = delete;

        // Allow moving
        Model(Model&&) noexcept = default;
        Model& operator=(Model&&) noexcept = default;

        // Access loaded data
        const std::vector<std::shared_ptr<Mesh>>& GetMeshes() const { return m_Meshes; }
        const std::vector<PBRMaterial>& GetMaterials() const { return m_Materials; }

        // Get material for a mesh
        const PBRMaterial& GetMaterialForMesh(size_t meshIndex) const;

        // Info
        const std::string& GetName() const { return m_Name; }
        const std::string& GetFilePath() const { return m_FilePath; }
        size_t GetMeshCount() const { return m_Meshes.size(); }
        bool IsValid() const { return !m_Meshes.empty(); }

    private:
        Model() = default;  // Only LoadFromFile can create

        std::string m_Name;
        std::string m_FilePath;
        std::string m_Directory;

        std::vector<std::shared_ptr<Mesh>> m_Meshes;
        std::vector<PBRMaterial> m_Materials;
        std::vector<size_t> m_MeshMaterialIndices;

        std::unordered_map<int, std::shared_ptr<Texture>> m_TextureCache;

        static PBRMaterial s_DefaultMaterial;
    };

}  // namespace VizEngine
```

> [!IMPORTANT]
> Model uses a **static factory pattern**: `Model::LoadFromFile()` returns `unique_ptr` which is `nullptr` on failure. There is no public constructor.

---

## Step 2: Create Material.h

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

## Step 3: Create Model.cpp (excerpt)

**Create `VizEngine/src/VizEngine/Core/Model.cpp`:**

```cpp
// VizEngine/src/VizEngine/Core/Model.cpp

#include "Model.h"
#include "VizEngine/Log.h"
#include <tiny_gltf.h>
#include <filesystem>

namespace VizEngine
{
    PBRMaterial Model::s_DefaultMaterial{};

    std::unique_ptr<Model> Model::LoadFromFile(const std::string& filepath)
    {
        tinygltf::Model gltf;
        tinygltf::TinyGLTF loader;
        std::string err, warn;

        bool success;
        if (filepath.ends_with(".glb"))
            success = loader.LoadBinaryFromFile(&gltf, &err, &warn, filepath);
        else
            success = loader.LoadASCIIFromFile(&gltf, &err, &warn, filepath);

        if (!warn.empty())
            VP_CORE_WARN("glTF [{}]: {}", filepath, warn);
        if (!err.empty())
            VP_CORE_ERROR("glTF [{}]: {}", filepath, err);

        if (!success)
        {
            VP_CORE_ERROR("Failed to load model: {}", filepath);
            return nullptr;  // Return nullptr on failure
        }

        // Create model (private constructor - only we can call it)
        auto model = std::unique_ptr<Model>(new Model());
        model->m_FilePath = filepath;
        model->m_Directory = std::filesystem::path(filepath).parent_path().string();
        model->m_Name = std::filesystem::path(filepath).stem().string();

        VP_CORE_INFO("Loaded glTF: {} ({} meshes)", filepath, gltf.meshes.size());

        // Process meshes and materials (implementation details omitted for brevity)
        // ... mesh extraction code ...
        // ... material extraction code ...

        return model;
    }

    const PBRMaterial& Model::GetMaterialForMesh(size_t meshIndex) const
    {
        if (meshIndex >= m_MeshMaterialIndices.size())
            return s_DefaultMaterial;

        size_t matIndex = m_MeshMaterialIndices[meshIndex];
        if (matIndex >= m_Materials.size())
            return s_DefaultMaterial;

        return m_Materials[matIndex];
    }

}  // namespace VizEngine
```

---

## Usage Example

```cpp
// Load model using static factory
auto duckModel = Model::LoadFromFile("assets/Duck.glb");

// Check for failure - returns nullptr on error
if (!duckModel)
{
    VP_CORE_ERROR("Failed to load model!");
    return;
}

VP_CORE_INFO("Loaded {} meshes", duckModel->GetMeshCount());

// Add meshes to scene
for (size_t i = 0; i < duckModel->GetMeshCount(); i++)
{
    auto& obj = scene.Add(duckModel->GetMeshes()[i], "Duck");
    obj.ObjectTransform.Scale = glm::vec3(0.02f);  // glTF uses meters

    // Get material
    const auto& mat = duckModel->GetMaterialForMesh(i);
    obj.Color = mat.BaseColor;
    obj.Roughness = mat.Roughness;
    obj.TexturePtr = mat.BaseColorTexture;
}
```

---

## Why Static Factory?

| Constructor Pattern | Static Factory Pattern |
|---------------------|------------------------|
| `Model model("file.glb")` | `auto model = Model::LoadFromFile("file.glb")` |
| Throws on error (or uses isValid) | Returns `nullptr` on error |
| Object exists but may be invalid | Object only exists if valid |
| Harder to convey failure | Clear nullptr check |

The factory pattern is preferred for resource loading because:
1. Clear success/failure via nullptr
2. No partially constructed objects
3. Unique_ptr enforces ownership

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Returns nullptr | File not found | Check path relative to executable |
| Wrong scale | glTF uses meters | Scale by 0.01 for typical models |
| Missing textures | Textures not embedded | Use .glb or check texture paths |

---

## Milestone

**Model Loader (Geometry) Complete**

You have:
- Static factory `Model::LoadFromFile()`
- Returns `unique_ptr` (nullptr on failure)
- Mesh and material extraction
- `GetMaterialForMesh()` convenience method

---

## What's Next

In **Chapter 19**, we'll look at the material extraction in more detail.

> **Next:** [Chapter 19: Model Loader (Materials)](19_ModelLoaderMaterials.md)

> **Previous:** [Chapter 17: glTF Format](17_glTFFormat.md)
