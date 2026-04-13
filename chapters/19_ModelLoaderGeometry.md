\newpage

# Chapter 19: Model Loader (Geometry)

We have a lighting system that shades using normals, a texture system that samples using UV coordinates, and hand-authored meshes for primitives. Now we connect those systems to real 3D assets by building a loader that reads glTF files and produces the `Mesh` objects our renderer already knows how to draw.

This chapter focuses on geometry: extracting positions, normals, and UV coordinates from a glTF binary blob and handing them to `Mesh`. Chapter 20 covers materials and textures.

---

## Keeping tinygltf out of Model.h

The natural first instinct is to put all the loading logic directly in `Model`. The problem is that `Model.h` is included by scene code, application code, and anywhere else that works with models. If `Model.h` includes `tiny_gltf.h`, that header — which is large — gets compiled into every one of those translation units. Compile times grow, and tinygltf's internal types pollute the namespace of every file that needed only `GetMeshes()`.

The fix is to forward-declare a private inner class in `Model.h` and define it entirely in `Model.cpp`. `tiny_gltf.h` is included only in `Model.cpp`. Every other file sees only the public interface.

```
Model.h   →  declares  class ModelLoader;   (no tinygltf)
Model.cpp →  defines   class Model::ModelLoader { ... }   (includes tiny_gltf.h here)
```

`Model::LoadFromFile()` delegates immediately to `ModelLoader::Load()`. The caller never sees tinygltf exist.

---

## Step 1: Create Model.h

**Create `VizEngine/src/VizEngine/Core/Model.h`:**

```cpp
// VizEngine/src/VizEngine/Core/Model.h

#pragma once

#include "VizEngine/Core.h"
#include "Mesh.h"
#include <vector>
#include <memory>
#include <string>

namespace VizEngine
{
    class VizEngine_API Model
    {
    public:
        // Static factory — only way to construct a Model.
        // Returns nullptr on any failure: file not found, parse error, empty geometry.
        static std::unique_ptr<Model> LoadFromFile(const std::string& filepath);

        ~Model() = default;

        // Models own GPU resources through their Meshes — no copying.
        Model(const Model&) = delete;
        Model& operator=(const Model&) = delete;

        Model(Model&&) noexcept = default;
        Model& operator=(Model&&) noexcept = default;

        const std::vector<std::shared_ptr<Mesh>>& GetMeshes() const { return m_Meshes; }
        size_t GetMeshCount() const { return m_Meshes.size(); }

        const std::string& GetName() const { return m_Name; }
        const std::string& GetFilePath() const { return m_FilePath; }
        bool IsValid() const { return !m_Meshes.empty(); }

    private:
        Model() = default;  // Only LoadFromFile may construct

        std::string m_Name;
        std::string m_FilePath;
        std::string m_Directory;

        std::vector<std::shared_ptr<Mesh>> m_Meshes;

        // Full definition is in Model.cpp — keeps tiny_gltf.h out of this header.
        class ModelLoader;
    };

}  // namespace VizEngine
```

The only difference from what you might write naturally is the `class ModelLoader;` line at the bottom and the private constructor. Everything else is the public interface you'd expect.

---

## Step 2: Create Model.cpp — accessor helpers

**Create `VizEngine/src/VizEngine/Core/Model.cpp`:**

Start with the includes and three small helper functions. The first two (`GetDirectory`, `GetFilename`) parse file paths. The third (`EndsWith`) detects `.glb` vs `.gltf` extension.

Then comes the important one: `GetBufferData<T>`.

In Chapter 18, the raw accessor pattern looked like this:

```cpp
const unsigned char* GetBufferData(const tinygltf::Model& model, int accessorIndex)
{
    const auto& accessor   = model.accessors[accessorIndex];
    const auto& bufferView = model.bufferViews[accessor.bufferView];
    const auto& buffer     = model.buffers[bufferView.buffer];
    return buffer.data.data() + bufferView.byteOffset + accessor.byteOffset;
}
```

That works for well-formed files. glTF files from the wild are not guaranteed to be well-formed. A negative `bufferView` index, a buffer offset past the end of the buffer, interleaved data with a stride our code doesn't handle — all of these crash or corrupt silently if unchecked. Because this data comes from external files rather than our own code, we validate before we dereference.

The template parameter `T` makes the cast explicit at the call site — `GetBufferData<float>` for positions and normals, which makes it immediately obvious what type is expected:

```cpp
// VizEngine/src/VizEngine/Core/Model.cpp

#include "Model.h"
#include "VizEngine/Log.h"

#define TINYGLTF_NO_INCLUDE_STB_IMAGE
#define TINYGLTF_NO_STB_IMAGE_WRITE
#define TINYGLTF_NO_INCLUDE_STB_IMAGE_WRITE
#include "tiny_gltf.h"

#include <filesystem>
#include <cmath>

namespace VizEngine
{
    //==========================================================================
    // File path utilities
    //==========================================================================
    static std::string GetDirectory(const std::string& filepath)
    {
        return std::filesystem::path(filepath).parent_path().string();
    }

    static std::string GetFilename(const std::string& filepath)
    {
        return std::filesystem::path(filepath).filename().string();
    }

    static bool EndsWith(const std::string& str, const std::string& suffix)
    {
        if (suffix.size() > str.size()) return false;
        return str.compare(str.size() - suffix.size(), suffix.size(), suffix) == 0;
    }

    //==========================================================================
    // Accessor helpers
    //==========================================================================

    // Returns a typed pointer into the glTF binary buffer described by the accessor.
    // Returns nullptr and logs an error if any bounds check fails.
    template<typename T>
    static const T* GetBufferData(const tinygltf::Model& model,
                                   const tinygltf::Accessor& accessor)
    {
        if (accessor.bufferView < 0 ||
            accessor.bufferView >= static_cast<int>(model.bufferViews.size()))
        {
            VP_CORE_ERROR("Accessor bufferView index {} out of range", accessor.bufferView);
            return nullptr;
        }

        const auto& bufferView = model.bufferViews[accessor.bufferView];

        if (bufferView.buffer < 0 ||
            bufferView.buffer >= static_cast<int>(model.buffers.size()))
        {
            VP_CORE_ERROR("BufferView buffer index {} out of range", bufferView.buffer);
            return nullptr;
        }

        const auto& buffer = model.buffers[bufferView.buffer];

        // Determine element size from accessor type (VEC3 = 3 floats, etc.)
        size_t componentsPerElement = 1;
        switch (accessor.type)
        {
            case TINYGLTF_TYPE_SCALAR: componentsPerElement = 1; break;
            case TINYGLTF_TYPE_VEC2:   componentsPerElement = 2; break;
            case TINYGLTF_TYPE_VEC3:   componentsPerElement = 3; break;
            case TINYGLTF_TYPE_VEC4:   componentsPerElement = 4; break;
            default: break;
        }
        size_t elementSize = componentsPerElement * sizeof(T);

        // Tightly packed data only — interleaved buffers (byteStride != 0) are not supported.
        if (bufferView.byteStride != 0 && bufferView.byteStride != elementSize)
        {
            VP_CORE_ERROR("Interleaved buffer (byteStride={}) not supported", bufferView.byteStride);
            return nullptr;
        }

        size_t totalOffset = bufferView.byteOffset + accessor.byteOffset;
        size_t requiredBytes = accessor.count * elementSize;

        if (totalOffset > buffer.data.size() ||
            totalOffset + requiredBytes > buffer.data.size())
        {
            VP_CORE_ERROR("Buffer data range exceeds buffer size");
            return nullptr;
        }

        return reinterpret_cast<const T*>(buffer.data.data() + totalOffset);
    }

    // Validates that an optional attribute accessor covers the expected vertex count.
    // Used before reading NORMAL, TEXCOORD_0 — attributes that glTF does not require.
    static bool ValidateAttributeBuffer(
        const tinygltf::Model& gltfModel,
        const tinygltf::Accessor& accessor,
        size_t vertexCount,
        size_t componentsPerVertex,
        const std::string& attributeName)
    {
        if (accessor.bufferView < 0 ||
            accessor.bufferView >= static_cast<int>(gltfModel.bufferViews.size()))
        {
            VP_CORE_WARN("{} bufferView out of range, skipping", attributeName);
            return false;
        }

        const auto& bufferView = gltfModel.bufferViews[accessor.bufferView];

        if (bufferView.buffer < 0 ||
            bufferView.buffer >= static_cast<int>(gltfModel.buffers.size()))
        {
            VP_CORE_WARN("{} buffer out of range, skipping", attributeName);
            return false;
        }

        const auto& buffer  = gltfModel.buffers[bufferView.buffer];
        size_t totalOffset  = bufferView.byteOffset + accessor.byteOffset;
        size_t requiredBytes = vertexCount * componentsPerVertex * sizeof(float);

        if (totalOffset > buffer.data.size() ||
            requiredBytes > buffer.data.size() - totalOffset)
        {
            VP_CORE_WARN("{} buffer too small, skipping", attributeName);
            return false;
        }

        return true;
    }
```

---

## Step 3: ModelLoader — the inner class

Still inside `Model.cpp`, define `Model::ModelLoader` and its `Load` entry point. The constructor takes a raw pointer to the `Model` being built — ModelLoader exists only during the load call and writes directly into the model's private members.

```cpp
    //==========================================================================
    // ModelLoader — inner class definition (Model.h only forward-declares this)
    //==========================================================================
    class Model::ModelLoader
    {
    public:
        static std::unique_ptr<Model> Load(const std::string& filepath);

    private:
        ModelLoader(Model* model, const std::string& filepath)
            : m_Model(model)
            , m_Directory(GetDirectory(filepath))
        {}

        void LoadMeshes(const tinygltf::Model& gltfModel);
        void LoadIndices(const tinygltf::Model& gltfModel,
                         const tinygltf::Accessor& accessor,
                         std::vector<unsigned int>& indices);

        Model*      m_Model;
        std::string m_Directory;
    };

    //==========================================================================
    // Model public interface — delegates to ModelLoader
    //==========================================================================
    std::unique_ptr<Model> Model::LoadFromFile(const std::string& filepath)
    {
        return ModelLoader::Load(filepath);
    }

    std::unique_ptr<Model> Model::ModelLoader::Load(const std::string& filepath)
    {
        VP_CORE_INFO("Loading model: {}", filepath);

        if (!std::filesystem::exists(filepath))
        {
            VP_CORE_ERROR("Model file not found: {}", filepath);
            return nullptr;
        }

        tinygltf::Model   gltfModel;
        tinygltf::TinyGLTF loader;
        std::string err, warn;
        bool success = false;

        if (EndsWith(filepath, ".glb"))
            success = loader.LoadBinaryFromFile(&gltfModel, &err, &warn, filepath);
        else if (EndsWith(filepath, ".gltf"))
            success = loader.LoadASCIIFromFile(&gltfModel, &err, &warn, filepath);
        else
        {
            VP_CORE_ERROR("Unsupported format: {}", filepath);
            return nullptr;
        }

        if (!warn.empty()) VP_CORE_WARN("glTF warning: {}", warn);
        if (!err.empty())  VP_CORE_ERROR("glTF error: {}", err);

        if (!success)
        {
            VP_CORE_ERROR("Failed to parse: {}", filepath);
            return nullptr;
        }

        auto model = std::unique_ptr<Model>(new Model());
        model->m_Name      = GetFilename(filepath);
        model->m_FilePath  = filepath;
        model->m_Directory = GetDirectory(filepath);

        ModelLoader modelLoader(model.get(), filepath);
        modelLoader.LoadMeshes(gltfModel);

        VP_CORE_INFO("Loaded '{}': {} mesh(es)", model->m_Name, model->m_Meshes.size());
        return model;
    }
```

---

## Step 4: LoadMeshes

This is the core of the chapter. Each glTF mesh contains one or more primitives — each primitive is a single draw call. We iterate all primitives, extract vertex attributes into a `std::vector<Vertex>`, build the index list, and hand both to `Mesh`.

POSITION is the only required glTF attribute. NORMAL and TEXCOORD_0 are optional — our Blinn-Phong shader needs both, so we extract them when present and fall back to safe defaults when not.

```cpp
    void Model::ModelLoader::LoadMeshes(const tinygltf::Model& gltfModel)
    {
        for (const auto& gltfMesh : gltfModel.meshes)
        {
            for (const auto& primitive : gltfMesh.primitives)
            {
                // We only handle triangle primitives.
                // mode == -1 means the default, which is triangles.
                if (primitive.mode != TINYGLTF_MODE_TRIANGLES && primitive.mode != -1)
                {
                    VP_CORE_WARN("Skipping non-triangle primitive in '{}'", gltfMesh.name);
                    continue;
                }

                //--------------------------------------------------------------
                // POSITION — required
                //--------------------------------------------------------------
                if (primitive.attributes.find("POSITION") == primitive.attributes.end())
                {
                    VP_CORE_ERROR("Primitive in '{}' missing POSITION", gltfMesh.name);
                    continue;
                }

                int posIdx = primitive.attributes.at("POSITION");
                if (posIdx < 0 || posIdx >= static_cast<int>(gltfModel.accessors.size()))
                {
                    VP_CORE_ERROR("POSITION accessor index out of range");
                    continue;
                }

                const auto& posAccessor = gltfModel.accessors[posIdx];
                const float* positions  = GetBufferData<float>(gltfModel, posAccessor);
                if (!positions)
                {
                    VP_CORE_ERROR("Failed to read POSITION data");
                    continue;
                }

                size_t vertexCount = posAccessor.count;

                //--------------------------------------------------------------
                // NORMAL — optional
                // Default: glm::vec3(0, 1, 0) — facing up.
                // This will shade incorrectly on most models but will not crash.
                //--------------------------------------------------------------
                const float* normals = nullptr;
                if (primitive.attributes.find("NORMAL") != primitive.attributes.end())
                {
                    int normIdx = primitive.attributes.at("NORMAL");
                    if (normIdx >= 0 && normIdx < static_cast<int>(gltfModel.accessors.size()))
                    {
                        const auto& normAccessor = gltfModel.accessors[normIdx];
                        if (ValidateAttributeBuffer(gltfModel, normAccessor, vertexCount, 3, "NORMAL"))
                            normals = GetBufferData<float>(gltfModel, normAccessor);
                    }
                }

                //--------------------------------------------------------------
                // TEXCOORD_0 — optional
                // Default: glm::vec2(0, 0) — samples top-left corner of any texture.
                //--------------------------------------------------------------
                const float* texCoords = nullptr;
                if (primitive.attributes.find("TEXCOORD_0") != primitive.attributes.end())
                {
                    int uvIdx = primitive.attributes.at("TEXCOORD_0");
                    if (uvIdx >= 0 && uvIdx < static_cast<int>(gltfModel.accessors.size()))
                    {
                        const auto& uvAccessor = gltfModel.accessors[uvIdx];
                        if (ValidateAttributeBuffer(gltfModel, uvAccessor, vertexCount, 2, "TEXCOORD_0"))
                            texCoords = GetBufferData<float>(gltfModel, uvAccessor);
                    }
                }

                //--------------------------------------------------------------
                // Build vertex array
                //--------------------------------------------------------------
                std::vector<Vertex> vertices;
                vertices.reserve(vertexCount);

                for (size_t i = 0; i < vertexCount; i++)
                {
                    Vertex v;

                    v.Position = glm::vec4(
                        positions[i * 3 + 0],
                        positions[i * 3 + 1],
                        positions[i * 3 + 2],
                        1.0f
                    );

                    v.Normal = normals
                        ? glm::vec3(normals[i * 3 + 0], normals[i * 3 + 1], normals[i * 3 + 2])
                        : glm::vec3(0.0f, 1.0f, 0.0f);

                    v.TexCoords = texCoords
                        ? glm::vec2(texCoords[i * 2 + 0], texCoords[i * 2 + 1])
                        : glm::vec2(0.0f);

                    v.Color = glm::vec4(1.0f);  // material tint applied at render time

                    vertices.push_back(v);
                }

                //--------------------------------------------------------------
                // Build index array
                //--------------------------------------------------------------
                std::vector<unsigned int> indices;

                if (primitive.indices >= 0 &&
                    primitive.indices < static_cast<int>(gltfModel.accessors.size()))
                {
                    LoadIndices(gltfModel, gltfModel.accessors[primitive.indices], indices);
                }
                else
                {
                    // Non-indexed geometry — generate sequential indices
                    indices.reserve(vertexCount);
                    for (size_t i = 0; i < vertexCount; i++)
                        indices.push_back(static_cast<unsigned int>(i));
                }

                m_Model->m_Meshes.push_back(std::make_shared<Mesh>(vertices, indices));
            }
        }
    }
```

---

## Step 5: LoadIndices

glTF allows index buffers to use three different integer widths: `uint8` for small meshes (< 256 vertices), `uint16` for typical meshes (< 65536 vertices), and `uint32` for large ones. Our `Mesh` uses `unsigned int` throughout, so we promote each type uniformly:

```cpp
    void Model::ModelLoader::LoadIndices(
        const tinygltf::Model& gltfModel,
        const tinygltf::Accessor& accessor,
        std::vector<unsigned int>& indices)
    {
        if (accessor.bufferView < 0 ||
            accessor.bufferView >= static_cast<int>(gltfModel.bufferViews.size()))
        {
            VP_CORE_ERROR("Index accessor bufferView out of range");
            return;
        }

        const auto& bufferView = gltfModel.bufferViews[accessor.bufferView];

        if (bufferView.buffer < 0 ||
            bufferView.buffer >= static_cast<int>(gltfModel.buffers.size()))
        {
            VP_CORE_ERROR("Index bufferView buffer out of range");
            return;
        }

        const auto& buffer  = gltfModel.buffers[bufferView.buffer];
        size_t totalOffset  = bufferView.byteOffset + accessor.byteOffset;

        size_t componentSize = 0;
        switch (accessor.componentType)
        {
            case TINYGLTF_COMPONENT_TYPE_UNSIGNED_BYTE:  componentSize = 1; break;
            case TINYGLTF_COMPONENT_TYPE_UNSIGNED_SHORT: componentSize = 2; break;
            case TINYGLTF_COMPONENT_TYPE_UNSIGNED_INT:   componentSize = 4; break;
            default:
                VP_CORE_ERROR("Unsupported index component type: {}", accessor.componentType);
                return;
        }

        if (totalOffset > buffer.data.size() ||
            accessor.count * componentSize > buffer.data.size() - totalOffset)
        {
            VP_CORE_ERROR("Index buffer out of bounds");
            return;
        }

        const void* dataPtr = buffer.data.data() + totalOffset;
        indices.reserve(accessor.count);

        switch (accessor.componentType)
        {
            case TINYGLTF_COMPONENT_TYPE_UNSIGNED_BYTE:
            {
                const uint8_t* buf = static_cast<const uint8_t*>(dataPtr);
                for (size_t i = 0; i < accessor.count; i++)
                    indices.push_back(static_cast<unsigned int>(buf[i]));
                break;
            }
            case TINYGLTF_COMPONENT_TYPE_UNSIGNED_SHORT:
            {
                const uint16_t* buf = static_cast<const uint16_t*>(dataPtr);
                for (size_t i = 0; i < accessor.count; i++)
                    indices.push_back(static_cast<unsigned int>(buf[i]));
                break;
            }
            case TINYGLTF_COMPONENT_TYPE_UNSIGNED_INT:
            {
                const uint32_t* buf = static_cast<const uint32_t*>(dataPtr);
                for (size_t i = 0; i < accessor.count; i++)
                    indices.push_back(buf[i]);
                break;
            }
        }
    }

}  // namespace VizEngine
```

---

## Step 6: Update CMakeLists.txt

**Modify `VizEngine/CMakeLists.txt`:**

In `VIZENGINE_SOURCES`, add:

```cmake
src/VizEngine/Core/Model.cpp
```

In `VIZENGINE_HEADERS`, add:

```cmake
src/VizEngine/Core/Model.h
```

`tinygltf` include path was already added in Chapter 18. No change needed there.

---

## Usage Example

```cpp
// Load a glTF binary model
auto duck = Model::LoadFromFile("assets/gltf-samples/Models/Duck/glTF-Binary/Duck.glb");

if (!duck)
{
    VP_CORE_ERROR("Failed to load model");
    return;
}

VP_CORE_INFO("Duck: {} mesh(es)", duck->GetMeshCount());

// Add each mesh to the scene
for (size_t i = 0; i < duck->GetMeshCount(); i++)
{
    auto& obj = scene.Add(duck->GetMeshes()[i], "Duck");
    obj.ObjectTransform.Scale = glm::vec3(0.01f);  // glTF uses meters — scale down
}
```

The duck renders lit by `defaultlit.shader` with correct normals from the glTF file. The material is the scene object's default color for now — Chapter 20 will replace that with the glTF material.

---

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Returns `nullptr` | File not found | Path is relative to the executable, not the project root |
| Correct shape, flat shading | glTF file missing NORMAL | Regenerate normals in your DCC tool and re-export |
| Correct shape, all same UV | glTF file missing TEXCOORD_0 | Check export settings in Blender/Maya — enable UV export |
| Wrong scale | glTF uses meters | Scale by 0.01 for centimeter-scale assets |
| Load succeeds but `GetMeshCount()` is 0 | All primitives were non-triangle | Check export: ensure triangulate is enabled |

---

## Milestone

**Model Loader (Geometry) complete.**

You have:
- `Model::LoadFromFile()` — static factory, returns `nullptr` on failure
- `Model::ModelLoader` inner class — tinygltf confined to `Model.cpp`
- Typed, bounds-checked accessor reading with `GetBufferData<T>()`
- POSITION, NORMAL, TEXCOORD_0 extraction with safe defaults for optional attributes
- Index buffer handling for `uint8`, `uint16`, and `uint32` index types
- Arbitrary glTF binary and text models load and render with correct lighting

---

## What's Next

Models render with correct geometry and lighting. The material — color, roughness, textures — is still the scene object's default. Chapter 20 extracts glTF's PBR material data and applies it.

> **Next:** [Chapter 20: Model Loader (Materials)](20_ModelLoaderMaterials.md)

> **Previous:** [Chapter 18: glTF Format](18_glTFFormat.md)
