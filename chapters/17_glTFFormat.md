\newpage

# Chapter 17: glTF Format

Add **tinygltf** to load 3D models in the glTF format. This chapter covers the format and integration.

---

## Adding tinygltf

### Step 1: Add Submodule

```bash
cd VizPsyche
git submodule add https://github.com/syoyo/tinygltf.git VizEngine/vendor/tinygltf
```

### Step 2: Create TinyGLTF.cpp

tinygltf is header-only but needs implementation defines in one file.

**Create `VizEngine/src/VizEngine/Core/TinyGLTF.cpp`:**

```cpp
// VizEngine/src/VizEngine/Core/TinyGLTF.cpp

// Silence MSVC warnings in vendor code
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4018 4267 4244 4706)
#endif

#define TINYGLTF_IMPLEMENTATION
#define TINYGLTF_NO_INCLUDE_STB_IMAGE
#define TINYGLTF_NO_STB_IMAGE_WRITE
#define TINYGLTF_NO_INCLUDE_STB_IMAGE_WRITE

#include "stb_image.h"  // We already have this
#include "tiny_gltf.h"

#ifdef _MSC_VER
#pragma warning(pop)
#endif
```

### Step 3: Update CMakeLists.txt

```cmake
set(VIZENGINE_SOURCES
    # ... existing ...
    src/VizEngine/Core/TinyGLTF.cpp    # NEW
)

target_include_directories(VizEngine
    PRIVATE
        # ... existing ...
        ${CMAKE_CURRENT_SOURCE_DIR}/vendor/tinygltf
)
```

---

## Understanding glTF

glTF (GL Transmission Format) is an open standard for 3D models.

### File Types

| Extension | Description |
|-----------|-------------|
| `.gltf` | JSON text + external binary/textures |
| `.glb` | Single binary file (embedded data) |

### Structure

```
glTF Document
├── scenes[]         ← Scene hierarchy
├── nodes[]          ← Transform nodes
├── meshes[]         ← Geometry data
│   └── primitives[] ← Draw calls
├── materials[]      ← Material definitions
├── textures[]       ← Texture references
├── images[]         ← Image data
├── accessors[]      ← Data layout descriptions
├── bufferViews[]    ← Buffer chunks
└── buffers[]        ← Raw binary data
```

### Key Concepts

**Accessor** — Describes how to read data:
- Type (SCALAR, VEC2, VEC3, VEC4)
- Component type (FLOAT, UNSIGNED_INT, etc.)
- Count
- Byte offset

**BufferView** — Points to a range within a buffer

**Primitive** — A single draw call with:
- Vertex attributes (POSITION, NORMAL, TEXCOORD_0)
- Index accessor
- Material index

---

## Loading with tinygltf

```cpp
#include "tiny_gltf.h"

tinygltf::Model model;
tinygltf::TinyGLTF loader;
std::string err, warn;

// Load GLB (binary)
bool success = loader.LoadBinaryFromFile(&model, &err, &warn, "model.glb");

// Or load GLTF (text)
// bool success = loader.LoadASCIIFromFile(&model, &err, &warn, "model.gltf");

if (!warn.empty())
    VP_CORE_WARN("glTF warning: {}", warn);

if (!err.empty())
    VP_CORE_ERROR("glTF error: {}", err);

if (!success)
    return;

// Access data
for (const auto& mesh : model.meshes)
{
    for (const auto& primitive : mesh.primitives)
    {
        // Get position accessor
        const auto& posAccessor = model.accessors[primitive.attributes.at("POSITION")];
        // ...
    }
}
```

---

## Extracting Vertex Data

```cpp
const unsigned char* GetBufferData(const tinygltf::Model& model, int accessorIndex)
{
    const auto& accessor = model.accessors[accessorIndex];
    const auto& bufferView = model.bufferViews[accessor.bufferView];
    const auto& buffer = model.buffers[bufferView.buffer];

    return buffer.data.data() + bufferView.byteOffset + accessor.byteOffset;
}

// Usage
const float* positions = reinterpret_cast<const float*>(
    GetBufferData(model, primitive.attributes.at("POSITION"))
);
```

---

## Sample Models

Add the Khronos glTF sample repository:

```bash
git submodule add https://github.com/KhronosGroup/glTF-Sample-Assets.git VizEngine/assets/gltf-samples
```

Good starter models:
- `Duck.glb` — Simple textured model
- `Box.glb` — Minimal cube
- `Lantern.glb` — Multiple materials

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "Failed to load" | Wrong path | Check file path relative to exe |
| Missing textures | Textures not embedded | Use .glb or fix paths |
| Wrong scale | Model units | Scale transform (glTF uses meters) |

---

## Milestone

**tinygltf Integrated**

You have:
- tinygltf submodule added
- TinyGLTF.cpp implementation file
- Understanding of glTF structure

---

## What's Next

In **Chapter 18**, we'll create a `Model` class to load glTF geometry.

> **Next:** [Chapter 18: Model Loader (Geometry)](18_ModelLoaderGeometry.md)

> **Previous:** [Chapter 16: Blinn-Phong Lighting](16_Lighting.md)
