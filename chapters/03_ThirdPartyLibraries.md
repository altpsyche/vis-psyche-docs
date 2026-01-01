\newpage

# Chapter 3: Third-Party Libraries

Before we dive into graphics programming, let's understand the building blocks we're standing on. VizPsyche uses several third-party libraries, each solving a specific problem so we don't have to reinvent the wheel.

## Why Use Third-Party Libraries?

Writing everything from scratch is educational but impractical:

| Task | DIY Time | Library |
|------|----------|---------|
| Window creation | Weeks | GLFW |
| OpenGL function loading | Days | GLAD |
| Math (vectors, matrices) | Weeks | GLM |
| Immediate mode GUI | Months | Dear ImGui |
| Logging | Days | spdlog |
| Image loading | Days | stb_image |
| 3D model loading | Weeks | tinygltf |

Using battle-tested libraries lets us focus on what matters: **learning the engine architecture**.

---

## GLFW - Window & Input

**What it does:** Creates windows, handles input, manages OpenGL contexts.

**Why we need it:** OpenGL is just a graphics API - it doesn't know how to create windows. That's OS-specific (Win32 on Windows, Cocoa on Mac, X11 on Linux). GLFW abstracts this.

### What GLFW Provides

```cpp
// Create a window with an OpenGL context
GLFWwindow* window = glfwCreateWindow(800, 600, "My Window", NULL, NULL);

// Handle input
if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
    glfwSetWindowShouldClose(window, true);

// Main loop
while (!glfwWindowShouldClose(window))
{
    // Render...
    glfwSwapBuffers(window);
    glfwPollEvents();
}
```

### Key Features We Use

- **Window creation** - Platform-independent window with OpenGL context
- **Input polling** - Keyboard and mouse state
- **Callbacks** - Respond to resize, key presses, mouse clicks
- **Context management** - OpenGL context creation and activation

> **Location:** `VizEngine/vendor/glfw/`

---

## GLAD - OpenGL Loader

**What it does:** Loads OpenGL function pointers at runtime.

**Why we need it:** OpenGL functions aren't directly available on most platforms. The OS provides a way to query for them, but doing this manually is tedious. GLAD generates the loading code for us.

### The Problem GLAD Solves

```cpp
// Without GLAD, you'd have to do this for EVERY OpenGL function:
typedef void (*PFNGLbindvertexarrayproc)(GLuint array);
PFNGLBINDVERTEXARRAYPROC glBindVertexArray = 
    (PFNGLBINDVERTEXARRAYPROC)wglGetProcAddress("glBindVertexArray");

// With GLAD, just include the header and call:
glBindVertexArray(vao);  // Works!
```

### How GLAD Was Generated

GLAD is code-generated from the OpenGL specification. We used the [GLAD web generator](https://glad.dav1d.de/):

- **Language:** C/C++
- **Specification:** OpenGL
- **API:** gl Version 4.6
- **Profile:** Core

This generated `glad.h` and `glad.c` which we include in our project.

### Initialization

```cpp
// After creating GLFW window and context:
if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
{
    std::cerr << "Failed to initialize GLAD" << std::endl;
    return -1;
}
// Now all OpenGL functions are available!
```

> **Location:** `VizEngine/include/glad/glad.h`, `VizEngine/src/VizEngine/OpenGL/glad.c`

---

## GLM - OpenGL Mathematics

**What it does:** Provides vector and matrix types matching GLSL, plus transformation functions.

**Why we need it:** 3D graphics is all math - positions, rotations, projections. GLM gives us:

- Types that match shader types (`vec3`, `mat4`)
- Transform functions (`translate`, `rotate`, `perspective`)
- No OpenGL dependency (pure math)

### Common Types

```cpp
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

glm::vec3 position(0.0f, 1.0f, 0.0f);    // 3D position
glm::vec4 color(1.0f, 0.0f, 0.0f, 1.0f); // RGBA color
glm::mat4 transform(1.0f);                // 4x4 identity matrix
```

### Transformations

```cpp
// Create a model matrix
glm::mat4 model = glm::mat4(1.0f);
model = glm::translate(model, glm::vec3(1.0f, 0.0f, 0.0f));  // Move right
model = glm::rotate(model, glm::radians(45.0f), glm::vec3(0, 1, 0));  // Rotate
model = glm::scale(model, glm::vec3(2.0f));  // Scale up

// Create view matrix (camera)
glm::mat4 view = glm::lookAt(
    glm::vec3(0, 0, 3),   // Camera position
    glm::vec3(0, 0, 0),   // Look at origin
    glm::vec3(0, 1, 0)    // Up vector
);

// Create projection matrix
glm::mat4 projection = glm::perspective(
    glm::radians(45.0f),  // Field of view
    800.0f / 600.0f,      // Aspect ratio
    0.1f,                 // Near plane
    100.0f                // Far plane
);
```

### Sending to Shaders

```cpp
// GLM matrices are compatible with OpenGL
glm::mat4 mvp = projection * view * model;
glUniformMatrix4fv(location, 1, GL_FALSE, &mvp[0][0]);

// Or using glm::value_ptr
#include <glm/gtc/type_ptr.hpp>
glUniformMatrix4fv(location, 1, GL_FALSE, glm::value_ptr(mvp));
```

> **Location:** `VizEngine/vendor/glm/`

---

## Dear ImGui - Immediate Mode GUI

**What it does:** Creates debug/tool UI with minimal code.

**Why we need it:** For debugging and editor tools, we need sliders, buttons, and windows. ImGui lets us create UI with just a few lines:

```cpp
// Create a window with controls
ImGui::Begin("Debug");
ImGui::SliderFloat("Speed", &speed, 0.0f, 10.0f);
if (ImGui::Button("Reset"))
    ResetGame();
ImGui::Text("FPS: %.1f", fps);
ImGui::End();
```

### Immediate Mode vs Retained Mode

| Retained Mode (Qt, WPF) | Immediate Mode (ImGui) |
|------------------------|------------------------|
| Create widget objects | Describe UI each frame |
| Manage widget state | State is your data |
| Complex hierarchies | Simple function calls |
| Good for apps | Good for tools/debug |

### Integration

ImGui needs a backend for your platform. We use:
- **GLFW backend** - For input and window events
- **OpenGL3 backend** - For rendering

```cpp
// Setup
ImGui_ImplGlfw_InitForOpenGL(window, true);
ImGui_ImplOpenGL3_Init("#version 460");

// Each frame
ImGui_ImplOpenGL3_NewFrame();
ImGui_ImplGlfw_NewFrame();
ImGui::NewFrame();

// Your UI code here...

ImGui::Render();
ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
```

> **Location:** `VizEngine/vendor/imgui/`

---

## spdlog - Fast Logging

**What it does:** High-performance logging with formatting, colors, and multiple outputs.

**Why we need it:** `std::cout` is fine for small projects, but real engines need:

- **Log levels** - Filter out debug messages in release
- **Formatting** - Timestamps, thread IDs, colored output
- **Performance** - Asynchronous logging, no bottlenecks
- **Multiple sinks** - Console, file, network

### Basic Usage

```cpp
#include <spdlog/spdlog.h>

spdlog::info("Hello, {}!", "World");           // Hello, World!
spdlog::warn("Something might be wrong");
spdlog::error("Value {} is invalid", 42);
```

### Log Levels

| Level | Use For |
|-------|---------|
| `trace` | Very detailed debugging |
| `debug` | Developer information |
| `info` | General information |
| `warn` | Something unexpected |
| `error` | Errors that were handled |
| `critical` | Fatal errors |

### Multiple Loggers

spdlog supports named loggers - we use this to separate engine messages from game messages:

```cpp
auto core_logger = spdlog::stdout_color_mt("VizPsyche");
auto client_logger = spdlog::stdout_color_mt("Client");

core_logger->info("Engine started");    // [VizPsyche] Engine started
client_logger->info("Game loaded");     // [Client] Game loaded
```

> **Location:** `VizEngine/vendor/spdlog/`

---

## stb_image - Image Loading

**What it does:** Loads image files (PNG, JPG, etc.) into memory.

**Why we need it:** OpenGL doesn't load images - it just takes raw pixel data. stb_image handles the file format decoding.

### Single-Header Library

stb_image is a "single-header" library. The entire implementation is in one `.h` file:

```cpp
// In ONE .cpp file:
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

// In other files, just:
#include "stb_image.h"
```

### Loading an Image

```cpp
int width, height, channels;
unsigned char* data = stbi_load("texture.png", &width, &height, &channels, 4);

if (data)
{
    // Upload to OpenGL
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, 
                 GL_RGBA, GL_UNSIGNED_BYTE, data);
    stbi_image_free(data);  // Free CPU memory
}
```

### Flip for OpenGL

OpenGL expects textures with origin at bottom-left, but most images are top-left:

```cpp
stbi_set_flip_vertically_on_load(1);  // Flip Y axis when loading
```

> **Location:** `VizEngine/vendor/stb_image/`

---

## tinygltf - 3D Model Loading

**What it does:** Loads glTF and GLB 3D model files.

**Why we need it:** Artists create 3D models in tools like Blender, Maya, or 3ds Max. We need to load these models into our engine. glTF ("GL Transmission Format") is the modern standard for 3D assets - often called the "JPEG of 3D".

### Why glTF?

| Format | Pros | Cons |
|--------|------|------|
| **OBJ** | Simple, text-based | No materials, no animations, outdated |
| **FBX** | Industry standard, full-featured | Proprietary (Autodesk), complex |
| **glTF** | Open standard, PBR materials, compact | Newer (less legacy support) |

glTF is designed for real-time rendering with:
- **PBR materials** - Physically-based rendering properties
- **Binary format** - `.glb` files are compact and fast to load
- **Extensible** - Supports custom extensions
- **Web-friendly** - Used by Three.js, Babylon.js, etc.

### Single-Header Library

Like stb_image, tinygltf is a single-header library. However, since we already have stb_image implemented elsewhere, we need to tell tinygltf not to redefine it:

```cpp
// In TinyGLTF.cpp (the ONE file with the implementation):

// Silence MSVC warnings in vendor code
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable: 4018)  // signed/unsigned mismatch
#pragma warning(disable: 4267)  // conversion from size_t
#pragma warning(disable: 4244)  // conversion from double to float
#pragma warning(disable: 4706)  // assignment within conditional
#endif

#define TINYGLTF_IMPLEMENTATION

// We already have stb_image implemented in vendor/stb_image/stb_image.cpp
// So we tell tinygltf to NOT define STB_IMAGE_IMPLEMENTATION again
// but still use stb_image functions (which are already available)
#define TINYGLTF_NO_INCLUDE_STB_IMAGE
#define TINYGLTF_NO_STB_IMAGE_WRITE
#define TINYGLTF_NO_INCLUDE_STB_IMAGE_WRITE

// Include our stb_image header (which has the function declarations)
#include "stb_image.h"

#include "tiny_gltf.h"

#ifdef _MSC_VER
#pragma warning(pop)
#endif
```

```cpp
// In other files that need tinygltf (e.g., Model.cpp):
// Must match the defines used in TinyGLTF.cpp
#define TINYGLTF_NO_INCLUDE_STB_IMAGE
#define TINYGLTF_NO_STB_IMAGE_WRITE
#define TINYGLTF_NO_INCLUDE_STB_IMAGE_WRITE
#include "tiny_gltf.h"
```

> **Important:** The `TINYGLTF_NO_*` defines prevent duplicate symbol errors when stb_image is already compiled elsewhere in your project.

### Loading a Model

```cpp
tinygltf::Model model;
tinygltf::TinyGLTF loader;
std::string err, warn;

// Load binary glTF (.glb)
bool success = loader.LoadBinaryFromFile(&model, &err, &warn, "model.glb");

// Or load JSON glTF (.gltf)
// bool success = loader.LoadASCIIFromFile(&model, &err, &warn, "model.gltf");

if (!warn.empty())
    VP_CORE_WARN("glTF warning: {}", warn);

if (!err.empty())
    VP_CORE_ERROR("glTF error: {}", err);

if (!success) {
    VP_CORE_ERROR("Failed to load model");
    return nullptr;
}
```

### glTF Structure

A glTF file contains:

```
model
├── scenes[]          ← Collection of nodes
├── nodes[]           ← Transform hierarchy
├── meshes[]          ← Geometry data
│   └── primitives[]  ← Actual vertex/index data
├── materials[]       ← PBR material properties
│   ├── pbrMetallicRoughness
│   ├── normalTexture
│   ├── occlusionTexture
│   ├── emissiveTexture
│   ├── emissiveFactor
│   ├── alphaMode
│   └── doubleSided
├── textures[]        ← Texture references
├── images[]          ← Embedded or external images
├── accessors[]       ← How to read buffer data
├── bufferViews[]     ← Slices of buffers
└── buffers[]         ← Raw binary data
```

### Extracting Geometry

```cpp
// Access mesh primitives
for (const auto& mesh : model.meshes)
{
    for (const auto& primitive : mesh.primitives)
    {
        // Get position accessor
        const auto& posAccessor = model.accessors[primitive.attributes.at("POSITION")];
        const auto& posView = model.bufferViews[posAccessor.bufferView];
        const auto& posBuffer = model.buffers[posView.buffer];
        
        const float* positions = reinterpret_cast<const float*>(
            posBuffer.data.data() + posView.byteOffset + posAccessor.byteOffset
        );
        
        // Now 'positions' points to vertex position data
        // Similar process for NORMAL, TEXCOORD_0, COLOR_0, indices...
    }
}
```

### Accessing Materials

```cpp
for (const auto& gltfMat : model.materials)
{
    // PBR Metallic-Roughness workflow
    const auto& pbr = gltfMat.pbrMetallicRoughness;
    
    glm::vec4 baseColor(
        static_cast<float>(pbr.baseColorFactor[0]),
        static_cast<float>(pbr.baseColorFactor[1]),
        static_cast<float>(pbr.baseColorFactor[2]),
        static_cast<float>(pbr.baseColorFactor[3])
    );
    
    float metallic = static_cast<float>(pbr.metallicFactor);
    float roughness = static_cast<float>(pbr.roughnessFactor);
    
    // Emissive factor
    glm::vec3 emissive(
        static_cast<float>(gltfMat.emissiveFactor[0]),
        static_cast<float>(gltfMat.emissiveFactor[1]),
        static_cast<float>(gltfMat.emissiveFactor[2])
    );
    
    // Alpha mode: "OPAQUE", "MASK", or "BLEND"
    if (gltfMat.alphaMode == "MASK") {
        float alphaCutoff = static_cast<float>(gltfMat.alphaCutoff);
    }
    
    // Double-sided rendering
    bool doubleSided = gltfMat.doubleSided;
    
    // Textures (check index >= 0 before accessing)
    if (pbr.baseColorTexture.index >= 0) { /* load texture */ }
    if (pbr.metallicRoughnessTexture.index >= 0) { /* load texture */ }
    if (gltfMat.normalTexture.index >= 0) { /* load texture */ }
    if (gltfMat.occlusionTexture.index >= 0) { /* load texture */ }
    if (gltfMat.emissiveTexture.index >= 0) { /* load texture */ }
}
```

### Why tinygltf Over Alternatives

| Library | Description |
|---------|-------------|
| **tinygltf** | Header-only, C++11, uses stb_image (we already have it) |
| **cgltf** | Single-header C library, very fast, but C API |
| **fastgltf** | Modern C++17, fastest, but newer/less tutorials |
| **Assimp** | Supports 40+ formats, but heavy dependency |

tinygltf fits our engine because:
- Header-only (like stb_image)
- Uses stb_image for image loading (we already use it)
- Well-documented with many examples
- Battle-tested in production

> **Location:** `VizEngine/vendor/tinygltf/`
> 
> **Implementation:** `VizEngine/src/VizEngine/Core/TinyGLTF.cpp`

---

## How the vendor/ Folder is Organized

```
VizEngine/vendor/
├── glfw/           ← Window, input, context
├── glm/            ← Math library
├── imgui/          ← GUI library
├── spdlog/         ← Logging
├── stb_image/      ← Image loading
└── tinygltf/       ← 3D model loading
```

Each folder contains:
- The library source/headers
- Its own `CMakeLists.txt` (if it uses CMake)
- License file

### Integration in CMake

Some libraries have CMake support, others we add manually:

```cmake
# GLFW has CMake support - just add it
add_subdirectory(vendor/glfw)
target_link_libraries(VizEngine PRIVATE glfw)

# GLM is header-only
target_include_directories(VizEngine PUBLIC vendor/glm)

# stb_image is a single header - we wrap it
# (see stb_image.cpp for the implementation)
```

---

## Git Submodules

Large projects use **git submodules** to manage dependencies. This means the library is a separate git repository linked into yours.

### Adding a Submodule

```bash
git submodule add https://github.com/glfw/glfw.git VizEngine/vendor/glfw
```

### Cloning with Submodules

```bash
git clone --recursive https://github.com/you/vis-psyche.git
# Or after cloning:
git submodule update --init --recursive
```

### Updating Dependencies

```bash
cd VizEngine/vendor/glfw
git checkout 3.3.8  # Specific version
cd ../..
git add vendor/glfw
git commit -m "Update GLFW to 3.3.8"
```

---

## Library Versions

It's important to know what versions we're using:

| Library | Version | Notes |
|---------|---------|-------|
| GLFW | 3.3+ | Stable, widely used |
| GLAD | Generated | OpenGL 4.6 Core |
| GLM | 0.9.9+ | Header-only |
| Dear ImGui | 1.89+ | Docking branch available |
| spdlog | 1.11+ | Fast, feature-rich |
| stb_image | 2.28+ | Single header |
| tinygltf | 2.8+ | Header-only, glTF/GLB loading |

---

## Key Takeaways

1. **Each library solves one problem well** - Don't reinvent the wheel
2. **GLFW + GLAD = OpenGL setup** - Window creation and function loading
3. **GLM matches GLSL** - Same vector/matrix types as shaders
4. **ImGui is immediate mode** - Describe UI every frame
5. **spdlog is production-ready logging** - Fast, flexible, formatted
6. **stb_image is simple** - One header, loads common formats
7. **tinygltf loads 3D models** - glTF/GLB format, PBR materials
8. **vendor/ folder keeps dependencies organized** - Each library in its own folder

---

## Checkpoint

This chapter introduced the third-party libraries in VizPsyche:

**Library Summary:**
| Library | Purpose | Location |
|---------|---------|----------|
| GLFW | Window, input, context | `vendor/glfw/` |
| GLAD | OpenGL function loading | `vendor/glad/` |
| GLM | Math (vectors, matrices) | `vendor/glm/` |
| Dear ImGui | Immediate-mode GUI | `vendor/imgui/` |
| spdlog | Logging | `vendor/spdlog/` |
| stb_image | Image loading | `vendor/stb_image/` |
| tinygltf | glTF/GLB model loading | `vendor/tinygltf/` |

✓ **Checkpoint:** Create `VizEngine/vendor/` folder, add GLFW/GLM/spdlog as git submodules, download GLAD, update CMakeLists.txt files, and verify the build links all libraries.

---

## Exercise

1. Look at `VizEngine/vendor/` and find the license file for each library
2. Read GLFW's `README.md` - what platforms does it support?
3. Try the GLAD web generator - generate a loader for OpenGL 3.3 Core
4. Open ImGui's `imgui_demo.cpp` - run it to see all available widgets

---

> **Next:** [Chapter 4: Window & Context](04_WindowAndContext.md) - How GLFWManager wraps GLFW for our engine.



