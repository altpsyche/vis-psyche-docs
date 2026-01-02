\newpage

# Chapter 12: Model Loading (glTF)

## The Problem: Hardcoded Geometry

Look at our current mesh factory methods:

```cpp
auto pyramid = Mesh::CreatePyramid();
auto cube = Mesh::CreateCube();
auto plane = Mesh::CreatePlane();
```

These are fine for learning, but real games have:
- Characters with thousands of vertices
- Detailed environments
- Props, weapons, vehicles
- All created by artists in 3D modeling software

We need to **load external 3D model files**.

---

## Why glTF?

There are many 3D file formats. Here's why we chose glTF:

| Format | Pros | Cons |
|--------|------|------|
| **OBJ** | Simple, text-based, widely supported | No materials, no animations, outdated |
| **FBX** | Industry standard, full-featured | Proprietary (Autodesk), complex to parse |
| **COLLADA** | Open standard, XML-based | Verbose, slow to parse |
| **glTF** | Modern, PBR materials, compact binary | Newer (less legacy content) |

### The "JPEG of 3D"

glTF (GL Transmission Format) was designed by Khronos Group (the same people behind OpenGL) specifically for real-time rendering:

- **Efficient** - Designed to be fast to load and render
- **Complete** - Geometry, materials, textures, animations, scenes
- **PBR** - Physically-based rendering materials built-in
- **Two formats** - `.gltf` (JSON + binary) or `.glb` (single binary file)

> [!NOTE]
> **About PBR Materials:** glTF uses Physically-Based Rendering (PBR) with metallic-roughness workflow. Our engine currently uses Blinn-Phong shading (from Chapter 11). In this chapter, we'll parse and store the PBR material data from glTF files, but render using our existing Blinn-Phong shader. The base color texture works directly, and we approximate roughness by converting it to shininess. Full PBR rendering will be covered in a future **Advanced Lighting** chapter.

---

## glTF File Structure

Understanding glTF's structure is key to loading it correctly.

### The Hierarchy

```
glTF File
├── scenes[]           ← Root of the scene graph
│   └── nodes[]        ← References to node indices
├── nodes[]            ← Transform + mesh/camera/light reference
│   ├── translation, rotation, scale
│   ├── mesh           ← Index into meshes[]
│   └── children[]     ← Child node indices
├── meshes[]           ← Geometry containers
│   └── primitives[]   ← Actual geometry (one mesh can have multiple primitives)
│       ├── attributes ← Position, normal, texcoord accessors
│       ├── indices    ← Index accessor
│       └── material   ← Material index
├── materials[]        ← PBR material definitions
│   └── pbrMetallicRoughness
│       ├── baseColorFactor
│       ├── metallicFactor
│       ├── roughnessFactor
│       └── baseColorTexture
├── textures[]         ← Texture definitions
│   ├── source         ← Image index
│   └── sampler        ← Sampler index
├── images[]           ← Image data (embedded or URI)
├── accessors[]        ← Typed views into buffer data
├── bufferViews[]      ← Byte ranges within buffers
└── buffers[]          ← Raw binary data (vertices, indices, etc.)
```

### Accessors and Buffer Views

This is the trickiest part of glTF. Data flows like this:

```
Buffer (raw bytes)
    ↓
BufferView (byte offset + length, stride)
    ↓
Accessor (component type, count, type like VEC3)
    ↓
Your vertex array
```

For example, to get positions:

```cpp
// 1. Find the accessor
const auto& accessor = model.accessors[primitive.attributes.at("POSITION")];

// 2. Find the buffer view
const auto& bufferView = model.bufferViews[accessor.bufferView];

// 3. Find the buffer
const auto& buffer = model.buffers[bufferView.buffer];

// 4. Calculate the pointer
const float* positions = reinterpret_cast<const float*>(
    buffer.data.data() + bufferView.byteOffset + accessor.byteOffset
);

// 5. Read 'accessor.count' elements of type VEC3 (3 floats each)
```

### .gltf vs .glb

| Format | Structure | Use Case |
|--------|-----------|----------|
| `.gltf` | JSON file + separate `.bin` + image files | Development, debugging |
| `.glb` | Single binary file (JSON + binary chunks) | Distribution, faster loading |

Both contain the same data, just packaged differently. tinygltf handles both transparently.

---

## The tinygltf Library

We use [tinygltf](https://github.com/syoyo/tinygltf) - a header-only glTF loader.

### Why tinygltf?

- **Header-only** - Same pattern as stb_image
- **Uses stb_image** - We already have it for texture loading
- **Well-tested** - Used by many projects
- **Complete** - Supports glTF 2.0 fully

### Basic Usage

```cpp
#include "tiny_gltf.h"

tinygltf::Model model;
tinygltf::TinyGLTF loader;
std::string err, warn;

// Load .glb (binary)
bool success = loader.LoadBinaryFromFile(&model, &err, &warn, "model.glb");

// Or load .gltf (JSON)
// bool success = loader.LoadASCIIFromFile(&model, &err, &warn, "model.gltf");

if (!warn.empty()) {
    VP_CORE_WARN("glTF warning: {}", warn);
}

if (!err.empty()) {
    VP_CORE_ERROR("glTF error: {}", err);
    return nullptr;
}

if (!success) {
    VP_CORE_ERROR("Failed to load glTF: {}", filepath);
    return nullptr;
}

// Now 'model' contains all the data!
```

### Getting Test Assets

Khronos Group provides official glTF sample models for testing. We add these as a Git submodule:

```bash
git submodule add https://github.com/KhronosGroup/glTF-Sample-Assets.git VizEngine/assets/gltf-samples
```

This gives you access to many test models:

| Model | Complexity | Good For Testing |
|-------|------------|------------------|
| `Box.glb` | Simple cube | Basic loading |
| `Duck.glb` | Single mesh with texture | Textures, transforms |
| `BoxTextured.glb` | Cube with UV mapping | UV coordinates |
| `DamagedHelmet.glb` | Complex PBR | Full material system |

### Loading a Model in Application

Here's how to load the Duck model:

```cpp
// In Application.cpp - include the Model header
#include "Core/Model.h"
#include "Log.h"

// After adding scene objects...
auto duckModel = Model::LoadFromFile(
    "assets/gltf-samples/Models/Duck/glTF-Binary/Duck.glb"
);

if (duckModel)
{
    VP_CORE_INFO("Duck loaded: {} meshes", duckModel->GetMeshCount());
    
    for (size_t i = 0; i < duckModel->GetMeshCount(); i++)
    {
        auto& duckObj = scene.Add(duckModel->GetMeshes()[i], "Duck");
        duckObj.ObjectTransform.Position = glm::vec3(0.0f, 0.0f, 3.0f);
        duckObj.ObjectTransform.Scale = glm::vec3(0.02f);  // Duck is large!
        duckObj.Color = glm::vec4(1.0f);  // Don't tint, use texture colors
        
        // Use the model's own texture if available
        const auto& material = duckModel->GetMaterialForMesh(i);
        if (material.BaseColorTexture)
        {
            duckObj.TexturePtr = material.BaseColorTexture;
        }
    }
}
else
{
    VP_CORE_ERROR("Failed to load Duck model!");
}
```

> **Note:** We assign the model's embedded `BaseColorTexture` to the SceneObject's `TexturePtr`. This enables per-object textures - objects without a texture use the globally bound default. The path is relative to the executable directory (CMake copies assets alongside the exe).

### Per-Object Textures Pattern

With model loading, we evolve from a single global texture to per-object textures:

```cpp
// Create a shared default texture
auto defaultTexture = std::make_shared<Texture>("resources/textures/uvchecker.png");
defaultTexture->Bind();

// Assign default texture to all existing objects
for (size_t i = 0; i < scene.Size(); i++)
{
    if (!scene[i].TexturePtr)
    {
        scene[i].TexturePtr = defaultTexture;
    }
}
```

Now each object explicitly has a texture. Scene::Render binds the object's texture before drawing:

```cpp
// In Scene::Render()
if (obj.TexturePtr)
{
    obj.TexturePtr->Bind();
}
else
{
    // Unbind texture to prevent state leak from previous objects
    glBindTexture(GL_TEXTURE_2D, 0);
}
obj.MeshPtr->Bind();
renderer.Draw(...);
```

This ensures:
- **Models** use their embedded textures
- **Basic objects** use the default texture (uvchecker.png)
- **No texture bleeding** between objects

### Runtime Model Object Creation

To add more instances of a loaded model at runtime, store the mesh and texture:

```cpp
// Store for reuse
std::shared_ptr<Mesh> duckMesh = nullptr;
std::shared_ptr<Texture> duckTexture = nullptr;

if (duckModel && duckModel->GetMeshCount() > 0)
{
    duckMesh = duckModel->GetMeshes()[0];
    const auto& material = duckModel->GetMaterialForMesh(0);
    if (material.BaseColorTexture)
    {
        duckTexture = material.BaseColorTexture;
    }
}

// Later, in UI:
if (duckMesh && ImGui::Button("Add Duck"))
{
    auto& newObj = scene.Add(duckMesh, "Duck " + std::to_string(scene.Size() + 1));
    newObj.ObjectTransform.Scale = glm::vec3(0.02f);
    newObj.Color = glm::vec4(1.0f);  // No tint
    newObj.TexturePtr = duckTexture;
}
```

This pattern lets you spawn multiple instances of any loaded model!

---

## The PBRMaterial Struct

Before loading models, we need a way to represent materials. glTF uses the PBR metallic-roughness workflow:

```cpp
// VizEngine/Core/Material.h

struct VizEngine_API PBRMaterial
{
    std::string Name = "Unnamed";

    // PBR base properties
    glm::vec4 BaseColor = glm::vec4(1.0f);  // RGBA albedo color
    float Metallic = 0.0f;                   // 0 = dielectric, 1 = metal
    float Roughness = 0.5f;                  // 0 = smooth/mirror, 1 = rough

    // Textures (nullptr if not present)
    std::shared_ptr<Texture> BaseColorTexture = nullptr;
    std::shared_ptr<Texture> MetallicRoughnessTexture = nullptr;  // G=roughness, B=metallic
    std::shared_ptr<Texture> NormalTexture = nullptr;
    std::shared_ptr<Texture> OcclusionTexture = nullptr;
    std::shared_ptr<Texture> EmissiveTexture = nullptr;

    // Emissive
    glm::vec3 EmissiveFactor = glm::vec3(0.0f);

    // Alpha mode
    enum class AlphaMode { Opaque, Mask, Blend };
    AlphaMode Alpha = AlphaMode::Opaque;
    float AlphaCutoff = 0.5f;

    // Double-sided rendering
    bool DoubleSided = false;

    PBRMaterial() = default;

    // Simple constructor with just color
    explicit PBRMaterial(const glm::vec4& baseColor)
        : BaseColor(baseColor) {}

    // Constructor with color and metallic/roughness
    PBRMaterial(const glm::vec4& baseColor, float metallic, float roughness)
        : BaseColor(baseColor), Metallic(metallic), Roughness(roughness) {}

    // Helper methods
    bool HasBaseColorTexture() const { return BaseColorTexture != nullptr; }
    bool HasMetallicRoughnessTexture() const { return MetallicRoughnessTexture != nullptr; }
    bool HasNormalTexture() const { return NormalTexture != nullptr; }
    bool HasOcclusionTexture() const { return OcclusionTexture != nullptr; }
    bool HasEmissiveTexture() const { return EmissiveTexture != nullptr; }
    bool HasAnyTexture() const 
    { 
        return HasBaseColorTexture() || HasMetallicRoughnessTexture() || 
               HasNormalTexture() || HasOcclusionTexture() || HasEmissiveTexture(); 
    }
};
```

### PBR: Metallic-Roughness Workflow

glTF uses the **metallic-roughness** PBR workflow:

| Property | Range | Meaning |
|----------|-------|---------|
| **Base Color** | RGBA | Albedo/diffuse color |
| **Metallic** | 0-1 | 0 = plastic/wood, 1 = metal |
| **Roughness** | 0-1 | 0 = mirror-smooth, 1 = completely rough |
| **Emissive** | RGB | Self-illumination color |
| **Alpha Mode** | Opaque/Mask/Blend | How transparency is handled |
| **Alpha Cutoff** | 0-1 | Threshold for Mask mode |
| **Double Sided** | bool | Render back faces? |

Why PBR?
- **Physically accurate** - Materials look correct under any lighting
- **Artist-friendly** - Intuitive parameters
- **Consistent** - Same material looks good in any engine

---

## The Model Class

A container for loaded model data:

```cpp
// VizEngine/Core/Model.h

class VizEngine_API Model
{
public:
    // Factory method - the main way to create models
    static std::unique_ptr<Model> LoadFromFile(const std::string& filepath);

    ~Model() = default;

    // Prevent copying (models can be large)
    Model(const Model&) = delete;
    Model& operator=(const Model&) = delete;

    // Allow moving
    Model(Model&&) noexcept = default;
    Model& operator=(Model&&) noexcept = default;

    // Access loaded data
    const std::vector<std::shared_ptr<Mesh>>& GetMeshes() const { return m_Meshes; }
    const std::vector<PBRMaterial>& GetMaterials() const { return m_Materials; }

    // Get the material index for a specific mesh
    size_t GetMaterialIndexForMesh(size_t meshIndex) const;
    
    // Get the material for a specific mesh (convenience)
    const PBRMaterial& GetMaterialForMesh(size_t meshIndex) const;

    // Model info
    const std::string& GetName() const { return m_Name; }
    const std::string& GetFilePath() const { return m_FilePath; }
    size_t GetMeshCount() const { return m_Meshes.size(); }
    size_t GetMaterialCount() const { return m_Materials.size(); }

    // Check if model loaded successfully
    bool IsValid() const { return !m_Meshes.empty(); }

private:
    // Only LoadFromFile can create Models
    Model() = default;

    // Internal loading implementation (keeps tinygltf out of header)
    class ModelLoader;
    friend class ModelLoader;

    std::string m_Name;
    std::string m_FilePath;
    std::string m_Directory;  // For resolving relative texture paths

    std::vector<std::shared_ptr<Mesh>> m_Meshes;
    std::vector<PBRMaterial> m_Materials;
    std::vector<size_t> m_MeshMaterialIndices;  // Material index for each mesh

    // Texture cache to avoid reloading same texture (keyed by texture index)
    std::unordered_map<int, std::shared_ptr<Texture>> m_TextureCache;

    // Default material for meshes without one
    static PBRMaterial s_DefaultMaterial;
};
```

### Design Notes

- **Rule of 5**: Copy is deleted (models are large), move is allowed
- **Pimpl-like pattern**: `ModelLoader` inner class keeps tinygltf out of the header
- **Texture caching**: Uses texture index as key to avoid reloading embedded textures
- **Default material**: Static fallback for meshes without materials

---

## Loading Geometry

The core of model loading - extracting vertex data from glTF. We use a helper class `ModelLoader` to keep tinygltf internals out of the header:

```cpp
// Helper functions
static std::string GetDirectory(const std::string& filepath)
{
    std::filesystem::path path(filepath);
    return path.parent_path().string();
}

static std::string GetFilename(const std::string& filepath)
{
    std::filesystem::path path(filepath);
    return path.filename().string();
}

static bool EndsWith(const std::string& str, const std::string& suffix)
{
    if (suffix.size() > str.size()) return false;
    return str.compare(str.size() - suffix.size(), suffix.size(), suffix) == 0;
}

template<typename T>
static const T* GetBufferData(const tinygltf::Model& model, const tinygltf::Accessor& accessor)
{
    const auto& bufferView = model.bufferViews[accessor.bufferView];
    const auto& buffer = model.buffers[bufferView.buffer];
    return reinterpret_cast<const T*>(
        buffer.data.data() + bufferView.byteOffset + accessor.byteOffset
    );
}
```

### LoadFromFile Implementation

```cpp
std::unique_ptr<Model> Model::ModelLoader::Load(const std::string& filepath)
{
    VP_CORE_INFO("Loading model: {}", filepath);

    tinygltf::Model gltfModel;
    tinygltf::TinyGLTF loader;
    std::string err, warn;

    // Load based on file extension
    bool success = false;
    if (EndsWith(filepath, ".glb"))
    {
        success = loader.LoadBinaryFromFile(&gltfModel, &err, &warn, filepath);
    }
    else if (EndsWith(filepath, ".gltf"))
    {
        success = loader.LoadASCIIFromFile(&gltfModel, &err, &warn, filepath);
    }
    else
    {
        VP_CORE_ERROR("Unsupported model format: {}", filepath);
        return nullptr;
    }

    if (!warn.empty())
    {
        VP_CORE_WARN("glTF warning: {}", warn);
    }

    if (!err.empty())
    {
        VP_CORE_ERROR("glTF error: {}", err);
    }

    if (!success)
    {
        VP_CORE_ERROR("Failed to load model: {}", filepath);
        return nullptr;
    }

    // Create model instance
    auto model = std::unique_ptr<Model>(new Model());
    model->m_FilePath = filepath;
    model->m_Name = GetFilename(filepath);
    model->m_Directory = GetDirectory(filepath);

    // Use ModelLoader to do the actual loading
    ModelLoader modelLoader(model.get(), filepath);
    modelLoader.LoadMaterials(gltfModel);
    modelLoader.LoadMeshes(gltfModel);

    VP_CORE_INFO("Loaded model '{}': {} meshes, {} materials",
        model->m_Name, model->m_Meshes.size(), model->m_Materials.size());

    return model;
}
```

### Extracting Vertex Data

```cpp
void Model::ModelLoader::LoadMeshes(const tinygltf::Model& gltfModel)
{
    for (const auto& gltfMesh : gltfModel.meshes)
    {
        for (const auto& primitive : gltfMesh.primitives)
        {
            // Only support triangle primitives
            if (primitive.mode != TINYGLTF_MODE_TRIANGLES && primitive.mode != -1)
            {
                VP_CORE_WARN("Skipping non-triangle primitive in mesh '{}'", gltfMesh.name);
                continue;
            }

            std::vector<Vertex> vertices;
            std::vector<unsigned int> indices;

            // POSITION is required
            if (primitive.attributes.find("POSITION") == primitive.attributes.end())
            {
                VP_CORE_ERROR("Mesh primitive missing POSITION attribute");
                continue;
            }

            const auto& posAccessor = gltfModel.accessors[primitive.attributes.at("POSITION")];
            const float* positions = GetBufferData<float>(gltfModel, posAccessor);
            size_t vertexCount = posAccessor.count;

            // Normal data (optional)
            const float* normals = nullptr;
            if (primitive.attributes.find("NORMAL") != primitive.attributes.end())
            {
                const auto& normAccessor = gltfModel.accessors[primitive.attributes.at("NORMAL")];
                normals = GetBufferData<float>(gltfModel, normAccessor);
            }

            // Texture coordinates (optional)
            const float* texCoords = nullptr;
            if (primitive.attributes.find("TEXCOORD_0") != primitive.attributes.end())
            {
                const auto& uvAccessor = gltfModel.accessors[primitive.attributes.at("TEXCOORD_0")];
                texCoords = GetBufferData<float>(gltfModel, uvAccessor);
            }

            // Vertex colors (optional)
            const float* colors = nullptr;
            int colorComponents = 0;
            if (primitive.attributes.find("COLOR_0") != primitive.attributes.end())
            {
                const auto& colorAccessor = gltfModel.accessors[primitive.attributes.at("COLOR_0")];
                colorComponents = (colorAccessor.type == TINYGLTF_TYPE_VEC4) ? 4 : 3;
                if (colorAccessor.componentType == TINYGLTF_COMPONENT_TYPE_FLOAT)
                {
                    colors = GetBufferData<float>(gltfModel, colorAccessor);
                }
            }

            // Build vertices
            vertices.reserve(vertexCount);
            for (size_t i = 0; i < vertexCount; i++)
            {
                Vertex v;

                // Position (always present)
                v.Position = glm::vec4(
                    positions[i * 3 + 0],
                    positions[i * 3 + 1],
                    positions[i * 3 + 2],
                    1.0f
                );

                // Normal (default to up if missing)
                if (normals)
                {
                    v.Normal = glm::vec3(
                        normals[i * 3 + 0],
                        normals[i * 3 + 1],
                        normals[i * 3 + 2]
                    );
                }
                else
                {
                    v.Normal = glm::vec3(0.0f, 1.0f, 0.0f);
                }

                // Texture coordinates (default to 0,0 if missing)
                if (texCoords)
                {
                    v.TexCoords = glm::vec2(
                        texCoords[i * 2 + 0],
                        texCoords[i * 2 + 1]
                    );
                }
                else
                {
                    v.TexCoords = glm::vec2(0.0f);
                }

                // Vertex colors (default to white if missing)
                if (colors)
                {
                    v.Color = glm::vec4(
                        colors[i * colorComponents + 0],
                        colors[i * colorComponents + 1],
                        colors[i * colorComponents + 2],
                        colorComponents == 4 ? colors[i * colorComponents + 3] : 1.0f
                    );
                }
                else
                {
                    v.Color = glm::vec4(1.0f);
                }

                vertices.push_back(v);
            }

            // Load indices (or generate sequential indices if none)
            if (primitive.indices >= 0)
            {
                const auto& indexAccessor = gltfModel.accessors[primitive.indices];
                LoadIndices(gltfModel, indexAccessor, indices);
            }
            else
            {
                // Non-indexed mesh: generate sequential indices
                indices.reserve(vertexCount);
                for (size_t i = 0; i < vertexCount; i++)
                {
                    indices.push_back(static_cast<unsigned int>(i));
                }
            }

            // Create mesh and store
            auto mesh = std::make_shared<Mesh>(vertices, indices);
            m_Model->m_Meshes.push_back(mesh);

            // Track which material this mesh uses
            size_t materialIndex = (primitive.material >= 0)
                ? static_cast<size_t>(primitive.material)
                : 0;
            m_Model->m_MeshMaterialIndices.push_back(materialIndex);
        }
    }
}
```

### Handling Different Index Types

glTF can use different integer types for indices (byte, short, or int):

```cpp
void Model::ModelLoader::LoadIndices(const tinygltf::Model& gltfModel,
    const tinygltf::Accessor& accessor,
    std::vector<unsigned int>& indices)
{
    const auto& bufferView = gltfModel.bufferViews[accessor.bufferView];
    const auto& buffer = gltfModel.buffers[bufferView.buffer];
    const void* dataPtr = buffer.data.data() + bufferView.byteOffset + accessor.byteOffset;

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
        default:
            VP_CORE_ERROR("Unsupported index component type: {}", accessor.componentType);
            break;
    }
}
```

> **Note:** We always convert to `unsigned int` since that's what OpenGL expects for `glDrawElements`.

---

## Loading Materials and Textures

### Extracting Material Properties

```cpp
void Model::ModelLoader::LoadMaterials(const tinygltf::Model& gltfModel)
{
    for (const auto& gltfMat : gltfModel.materials)
    {
        PBRMaterial material;
        material.Name = gltfMat.name.empty() ? "Material" : gltfMat.name;

        // PBR Metallic-Roughness core properties
        const auto& pbr = gltfMat.pbrMetallicRoughness;

        material.BaseColor = glm::vec4(
            static_cast<float>(pbr.baseColorFactor[0]),
            static_cast<float>(pbr.baseColorFactor[1]),
            static_cast<float>(pbr.baseColorFactor[2]),
            static_cast<float>(pbr.baseColorFactor[3])
        );

        material.Metallic = static_cast<float>(pbr.metallicFactor);
        material.Roughness = static_cast<float>(pbr.roughnessFactor);

        // Base color texture
        if (pbr.baseColorTexture.index >= 0)
        {
            material.BaseColorTexture = LoadTexture(gltfModel, pbr.baseColorTexture.index);
        }

        // Metallic-roughness texture (G=roughness, B=metallic)
        if (pbr.metallicRoughnessTexture.index >= 0)
        {
            material.MetallicRoughnessTexture = LoadTexture(gltfModel, pbr.metallicRoughnessTexture.index);
        }

        // Normal map
        if (gltfMat.normalTexture.index >= 0)
        {
            material.NormalTexture = LoadTexture(gltfModel, gltfMat.normalTexture.index);
        }

        // Occlusion texture (ambient occlusion)
        if (gltfMat.occlusionTexture.index >= 0)
        {
            material.OcclusionTexture = LoadTexture(gltfModel, gltfMat.occlusionTexture.index);
        }

        // Emissive texture and factor
        if (gltfMat.emissiveTexture.index >= 0)
        {
            material.EmissiveTexture = LoadTexture(gltfModel, gltfMat.emissiveTexture.index);
        }
        material.EmissiveFactor = glm::vec3(
            static_cast<float>(gltfMat.emissiveFactor[0]),
            static_cast<float>(gltfMat.emissiveFactor[1]),
            static_cast<float>(gltfMat.emissiveFactor[2])
        );

        // Alpha mode: OPAQUE (default), MASK, or BLEND
        if (gltfMat.alphaMode == "MASK")
        {
            material.Alpha = PBRMaterial::AlphaMode::Mask;
            material.AlphaCutoff = static_cast<float>(gltfMat.alphaCutoff);
        }
        else if (gltfMat.alphaMode == "BLEND")
        {
            material.Alpha = PBRMaterial::AlphaMode::Blend;
        }
        else
        {
            material.Alpha = PBRMaterial::AlphaMode::Opaque;
        }

        // Double-sided rendering
        material.DoubleSided = gltfMat.doubleSided;

        m_Model->m_Materials.push_back(std::move(material));
    }

    // Ensure at least one default material
    if (m_Model->m_Materials.empty())
    {
        m_Model->m_Materials.push_back(Model::s_DefaultMaterial);
    }
}
```

### Loading Textures

glTF textures can be embedded in the file or referenced externally. We cache by texture index to handle both cases:

```cpp
std::shared_ptr<Texture> Model::ModelLoader::LoadTexture(const tinygltf::Model& gltfModel, int textureIndex)
{
    // Bounds check
    if (textureIndex < 0 || textureIndex >= static_cast<int>(gltfModel.textures.size()))
    {
        return nullptr;
    }

    // Check cache first (keyed by texture index)
    if (m_TextureCache.find(textureIndex) != m_TextureCache.end())
    {
        return m_TextureCache[textureIndex];
    }

    const auto& texture = gltfModel.textures[textureIndex];

    // Validate image source
    if (texture.source < 0 || texture.source >= static_cast<int>(gltfModel.images.size()))
    {
        return nullptr;
    }

    const auto& image = gltfModel.images[texture.source];
    std::shared_ptr<Texture> tex;

    if (!image.image.empty())
    {
        // Embedded texture - data is already loaded by tinygltf
        tex = std::make_shared<Texture>(
            image.image.data(),
            image.width,
            image.height,
            image.component  // Number of channels (3 or 4)
        );
        VP_CORE_TRACE("Loaded embedded texture: {}x{}", image.width, image.height);
    }
    else if (!image.uri.empty())
    {
        // External texture - load from file
        std::string fullPath = m_Directory.empty()
            ? image.uri
            : m_Directory + "/" + image.uri;
        tex = std::make_shared<Texture>(fullPath);
        VP_CORE_TRACE("Loaded external texture: {}", image.uri);
    }

    // Cache the texture
    if (tex)
    {
        m_TextureCache[textureIndex] = tex;
    }

    return tex;
}
```

> **Texture Caching:** We cache by texture index rather than URI because embedded textures don't have URIs. This ensures we don't reload the same texture multiple times.

---

## Integration with Scene

### Using Model with SceneObject

```cpp
// Load a model
auto helmetModel = Model::LoadFromFile("assets/helmet.glb");

if (helmetModel)
{
    // Add each mesh to the scene
    for (size_t i = 0; i < helmetModel->GetMeshCount(); i++)
    {
        auto& obj = scene.Add(helmetModel->GetMeshes()[i]);
        obj.ObjectTransform.Position = glm::vec3(0.0f, 2.0f, 0.0f);
        
        // Store material reference for rendering
        // (You might extend SceneObject to include material)
    }
}
```

### Extended SceneObject (Optional)

To properly support materials, you might extend `SceneObject`:

```cpp
struct SceneObject
{
    std::shared_ptr<Mesh> MeshPtr;
    Transform ObjectTransform;
    glm::vec4 Color = glm::vec4(1.0f);
    bool Active = true;
    
    // NEW: Material support
    Material ObjectMaterial;  // Copy of material properties
    // Or: const Material* MaterialPtr;  // Reference to shared material
};
```

---

## What About PBR?

glTF uses **Physically-Based Rendering (PBR)** with the metallic-roughness workflow. Our engine uses **Blinn-Phong** shading (from Chapter 11) but with a **Roughness** parameter that maps directly from glTF:

| glTF PBR Property | How We Handle It |
|-------------------|------------------|
| `baseColorFactor` | Copied to `obj.Color` |
| `baseColorTexture` | Copied to `obj.TexturePtr` |
| `roughnessFactor` | Copied to `obj.Roughness` (shader converts to shininess) |
| `metallicFactor` | Stored but not used (needs proper PBR) |
| Normal/Occlusion/Emissive textures | Stored but not rendered |

### Material Integration

When loading a model, we copy material properties to each `SceneObject`:

```cpp
for (size_t i = 0; i < model->GetMeshCount(); i++)
{
    auto& obj = scene.Add(model->GetMeshes()[i], "Model");
    
    // Copy material properties from glTF
    const auto& material = model->GetMaterialForMesh(i);
    obj.Color = material.BaseColor;
    obj.Roughness = material.Roughness;
    if (material.BaseColorTexture)
    {
        obj.TexturePtr = material.BaseColorTexture;
    }
}
```

> [!NOTE]
> **Future Work:** Full PBR will be implemented in the **Advanced Lighting** chapter, including:
> - Image-Based Lighting (IBL) with environment maps
> - Proper metallic/roughness texture sampling
> - Normal mapping for surface detail
> - Ambient occlusion and emissive rendering

---

## Where to Find Test Models

Free glTF models for testing:

| Source | URL | Notes |
|--------|-----|-------|
| **Khronos Sample Models** | github.com/KhronosGroup/glTF-Sample-Models | Official test models |
| **Sketchfab** | sketchfab.com | Many free models (look for CC license) |
| **Poly Haven** | polyhaven.com | Free HDRIs, textures, and models |
| **glTF Viewer** | gltf-viewer.donmccurdy.com | Test models render correctly |

### Recommended Test Models

1. **Box** - Simplest possible model
2. **BoxTextured** - Box with a texture
3. **Suzanne** - Blender monkey (good for testing normals)
4. **DamagedHelmet** - PBR showcase model
5. **FlightHelmet** - Complex multi-mesh model

---

## Common Issues

### Model Appears Black

**Causes:**
1. Normals not loaded or inverted
2. Material not applied
3. Light not set up

**Debug:**
```cpp
// Temporarily use normal as color
FragColor = vec4(v_Normal * 0.5 + 0.5, 1.0);
```

### Model Has Wrong Scale

glTF uses meters. If your model is tiny or huge:
```cpp
transform.Scale = glm::vec3(0.01f);  // If model is in centimeters
transform.Scale = glm::vec3(100.0f); // If model is too small
```

### Textures Not Loading

**Causes:**
1. Wrong texture path (relative vs absolute)
2. Image format not supported
3. Texture index out of bounds

**Debug:**
```cpp
VP_CORE_INFO("Loading texture: {} ({}x{})", 
    image.uri, image.width, image.height);
```

### Performance Issues

**Symptoms:** Slow loading, stuttering

**Solutions:**
1. Use `.glb` instead of `.gltf` (single file, no extra I/O)
2. Cache textures across models
3. Load models asynchronously (future topic)

---

## Known Limitations

Our glTF loader has some limitations for simplicity:

### Interleaved Vertex Data

The loader supports **tightly-packed vertex attributes** but not true interleaved data. glTF allows interleaved vertex data where positions, normals, and UVs are woven together in memory:

```
Tightly-packed: [P0 P1 P2...] [N0 N1 N2...] [UV0 UV1 UV2...]
Interleaved:    [P0 N0 UV0] [P1 N1 UV1] [P2 N2 UV2]...
```

The loader accepts:
- `byteStride = 0` (default, tightly packed)
- `byteStride = elementSize` (e.g., 12 for vec3, 8 for vec2)

If a model uses true interleaved data with a stride larger than the element size, the primitive is **skipped** with an error:
```
glTF buffer has unsupported byteStride (32), expected 0 or 12
```

**In practice:** Standard exports from Blender, Maya, and most tools use tightly-packed buffers. The Duck and most Khronos sample models work correctly.

> **For Advanced Readers:** Supporting interleaved data requires iterating with the stride value instead of assuming contiguous layout. This is left as an exercise or future enhancement.

### Normalized Integer Vertex Colors

The loader only supports `COLOR_0` attributes with `FLOAT` component type. The glTF spec also allows `UNSIGNED_BYTE` and `UNSIGNED_SHORT` (normalized to [0, 1]). Models using these types will log a warning and fall back to white vertex colors.

### Buffer Validation

The loader includes defensive validation against malformed glTF files:

- **Accessor/BufferView/Buffer indices** are bounds-checked before access
- **Buffer data size** is validated against `accessor.count` before reading
- **Optional attributes** (NORMAL, TEXCOORD_0, COLOR_0) gracefully fall back if their buffers are too small

If a malformed file is detected, primitives or attributes are skipped with error/warning messages rather than crashing:

```
Accessor bufferView index 999 out of range
Buffer offsets (5000) exceed buffer size (4096)
Buffer data range (offset 4000 + 200 bytes) exceeds buffer size (4096)
```

This makes the loader safe to use with untrusted glTF files.

---

## Key Takeaways

1. **glTF is the modern standard** - PBR materials, compact, well-supported
2. **Accessors → BufferViews → Buffers** - The data access chain
3. **PBRMaterial struct** - BaseColor, Metallic, Roughness, Emissive, Alpha, DoubleSided
4. **tinygltf integration** - Use `TINYGLTF_NO_INCLUDE_STB_IMAGE` when stb_image is already compiled
5. **Handle all optional data** - POSITION is required, but NORMAL, TEXCOORD_0, COLOR_0 are optional
6. **Support non-indexed meshes** - Generate sequential indices when `primitive.indices < 0`
7. **Cache textures by index** - Works for both embedded and external textures
8. **Alpha modes** - Opaque (default), Mask (cutoff), Blend (transparency)
9. **Test with sample models** - Khronos provides official test assets

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Model is all white | Materials not applied | Materials are parsed but rendering requires PBR shader |
| "Failed to load" | Wrong file path | Use absolute path or verify relative path |
| Crash on load | Missing accessor/buffer | Check tinygltf error string |
| Model upside-down | Y-axis convention | Some tools export with Y-up, some Z-up |

---

## Checkpoint

This chapter covered loading external 3D models:

**Key Files:**
| File | Purpose |
|------|---------|
| `Model.h` | Public API (`LoadFromFile`, `GetMeshes`) |
| `Model.cpp` | Internal loader using tinygltf |
| `Material.h` | `PBRMaterial` struct |
| `TinyGLTF.cpp` | tinygltf implementation compilation |

**What's Loaded:**
- Meshes (geometry + normals + UVs)
- Materials (PBR properties, stored but not yet rendered)
- Textures (cached by index)

✓ **Checkpoint:** Add tinygltf as vendor dependency, add glTF-Sample-Assets as submodule, create `TinyGLTF.cpp` with implementation defines, create `Model.h/.cpp`, load the Duck.glb model, and verify it renders in the scene.

---

## Exercise

1. **Load a simple model** - Try the Box or BoxTextured sample
2. **Display model info** - Show mesh count, material names in ImGui
3. **Handle multi-mesh models** - Load FlightHelmet (multiple meshes)
4. **Implement texture caching** - Share textures across models
5. **Add model browser** - File picker to load any .glb file

---

> **Reference:** For the complete class diagram and file locations, see [Appendix A: Code Reference](A_Reference.md).


