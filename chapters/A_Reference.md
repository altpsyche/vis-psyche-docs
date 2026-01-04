\newpage

# Appendix A: Code Reference

## What We've Built

As of now, VizPsyche has:

### Core Systems
- CMake build system (cross-platform ready)
- DLL architecture with proper exports
- Logging system (spdlog wrapper)
- Entry point abstraction
- Window and context management (GLFWManager)
- Engine singleton with game loop
- Application lifecycle (OnCreate, OnUpdate, OnRender, OnImGuiRender, OnEvent, OnDestroy)
- Input system (keyboard, mouse, scroll polling)
- Event system (window, key, mouse events with dispatcher)

### Third-Party Libraries {#libraries}
- **GLFW** - Window creation, input, OpenGL context
- **GLAD** - OpenGL function loading
- **GLM** - Math library (vectors, matrices, transforms)
- **Dear ImGui** - Immediate mode GUI
- **spdlog** - Fast, formatted logging
- **stb_image** - Image loading
- **tinygltf** - glTF/GLB 3D model loading

### OpenGL Abstractions {#opengl}
- VertexBuffer (VBO wrapper)
- IndexBuffer (IBO wrapper)
- VertexArray (VAO wrapper)
- VertexBufferLayout (attribute configuration)
- Shader (compile, link, uniforms, caching)
- Texture (load images, bind to slots)
- Renderer (clear, draw)
- GLFWManager (window, context, input)
- ErrorHandling (OpenGL debug callbacks)

### Engine Core
- Camera (view/projection matrices)
- Transform (position, rotation, scale)
- Mesh (geometry with factory methods)
- Scene (object collection management)
- SceneObject (mesh + transform + color bundle)
- Model (glTF/GLB model loader with ModelLoader inner class)
- PBRMaterial (full PBR properties: baseColor, metallic, roughness, emissive, alpha, textures)

### Lighting
- DirectionalLight (sun-like parallel rays)

### GUI
- UIManager (ImGui integration)

---

## File Reference

### Build Files

| File | Purpose |
|------|---------|
| `CMakeLists.txt` | Root build config |
| `VizEngine/CMakeLists.txt` | Engine library config |
| `Sandbox/CMakeLists.txt` | Test app config |

### Public API

| File | Purpose |
|------|---------|
| `VizEngine.h` | Single include for users |
| `Core.h` | Export macros, platform detection |
| `EntryPoint.h` | Defines main(), calls CreateApplication |
| `Application.h` | Base class with lifecycle methods |
| `Engine.h` | Engine singleton, game loop, subsystem access |
| `Log.h` | Logging macros |

### Core

| File | Purpose |
|------|---------|
| `Core/Camera.h` | View/projection matrix management |
| `Core/Transform.h` | Position, rotation, scale struct |
| `Core/Mesh.h` | Geometry abstraction with factories |
| `Core/Scene.h` | Scene object collection manager |
| `Core/SceneObject.h` | Mesh + Transform + Color bundle |
| `Core/Light.h` | DirectionalLight, PointLight |
| `Core/Model.h` | glTF model loader (meshes + materials) |
| `Core/Material.h` | PBRMaterial struct (baseColor, metallic, roughness, emissive, alpha, textures) |
| `Core/Input.h` | Keyboard, mouse, scroll polling with edge detection |
| `Core/TinyGLTF.cpp` | tinygltf implementation (defines TINYGLTF_IMPLEMENTATION) |

### Events

| File | Purpose |
|------|---------|
| `Events/Event.h` | Base Event class, EventDispatcher, macros |
| `Events/ApplicationEvent.h` | WindowResize, WindowClose, Focus events |
| `Events/KeyEvent.h` | KeyPressed, KeyReleased, KeyTyped events |
| `Events/MouseEvent.h` | MouseMoved, MouseScrolled, MouseButton events |

### OpenGL

| File | Purpose |
|------|---------|
| `OpenGL/VertexBuffer.h` | VBO wrapper |
| `OpenGL/IndexBuffer.h` | IBO wrapper |
| `OpenGL/VertexArray.h` | VAO wrapper |
| `OpenGL/VertexBufferLayout.h` | Vertex attribute configuration |
| `OpenGL/Shader.h` | Shader program wrapper |
| `OpenGL/Texture.h` | Texture wrapper |
| `OpenGL/Renderer.h` | High-level render commands |
| `OpenGL/GLFWManager.h` | Window and context |
| `OpenGL/ErrorHandling.h` | Debug output handling |
| `OpenGL/Commons.h` | Shared OpenGL includes |

### GUI

| File | Purpose |
|------|---------|
| `GUI/UIManager.h` | ImGui wrapper |

### Resources

| File | Purpose |
|------|---------|
| `resources/shaders/unlit.shader` | Unlit shader (no lighting) |
| `resources/shaders/lit.shader` | Blinn-Phong lighting shader |
| `resources/textures/uvchecker.png` | Test texture |

---

## Class Diagram {#class-diagram}

VizEngine (namespace)
│
├── Engine (singleton)
│   ├── Get() → singleton access
│   ├── Run() → main game loop
│   ├── Quit() → request shutdown
│   ├── GetWindow(), GetRenderer(), GetUIManager()
│   ├── GetDeltaTime()
│   └── OnEvent() → routes to Application
│
├── Application (base class)
│   ├── OnCreate() → initialization
│   ├── OnUpdate(deltaTime) → game logic
│   ├── OnRender() → rendering
│   ├── OnImGuiRender() → UI
│   ├── OnEvent() → event handling
│   └── OnDestroy() → cleanup
│
├── Input (static)
│   ├── Init(), Update()
│   ├── IsKeyPressed/Held/Released()
│   ├── IsMouseButtonPressed/Held/Released()
│   ├── GetMousePosition(), GetMouseDelta()
│   └── GetScrollDelta()
│
├── Log (static)
│   ├── Init()
│   ├── SetCoreLogLevel(), SetClientLogLevel()
│   ├── GetCoreLogger()
│   └── GetClientLogger()
│
├── Camera
│   ├── SetPosition(), SetRotation()
│   ├── GetViewMatrix(), GetProjectionMatrix()
│   ├── GetViewProjectionMatrix()
│   └── Move*() helpers
│
├── Transform (struct)
│   ├── Position, Rotation, Scale
│   └── GetModelMatrix()
│
├── Mesh
│   ├── Bind(), Unbind()
│   ├── GetVertexArray(), GetIndexBuffer()
│   └── CreatePyramid(), CreateCube(), CreatePlane() [static factories]
│
├── Scene
│   ├── Add(), Remove(), Clear()
│   ├── operator[](), At(), Size(), Empty()
│   ├── begin(), end()  [enables range-based for]
│   ├── Update(), Render()
│
├── SceneObject (struct)
│   ├── MeshPtr, TexturePtr, ObjectTransform, Color, Active, Name
│   └── Bundles mesh + optional texture + transform for rendering
│
├── Model
│   ├── LoadFromFile() [static factory]
│   ├── GetMeshes(), GetMaterials()
│   ├── GetMaterialIndexForMesh(), GetMaterialForMesh()
│   ├── GetName(), GetFilePath(), GetMeshCount(), GetMaterialCount()
│   ├── IsValid()
│   └── Loads glTF/GLB files via tinygltf (ModelLoader inner class)
│
├── PBRMaterial (struct)
│   ├── BaseColor, Metallic, Roughness
│   ├── EmissiveFactor, AlphaMode, AlphaCutoff, DoubleSided
│   ├── BaseColorTexture, MetallicRoughnessTexture, NormalTexture
│   ├── OcclusionTexture, EmissiveTexture
│   └── Has*Texture() helpers
│
├── DirectionalLight (struct)
│   ├── Direction, Ambient, Diffuse, Specular
│   └── GetDirection() → normalized
│
├── OpenGL Wrappers
│   ├── VertexBuffer: Bind(), Unbind(), GetID()
│   ├── IndexBuffer: Bind(), Unbind(), GetCount()
│   ├── VertexArray: LinkVertexBuffer(), Bind(), Unbind()
│   ├── Shader: Bind(), Unbind(), Set*() uniforms
│   ├── Texture: Bind(), Unbind(), GetWidth(), GetHeight()
│   └── Renderer: Clear(), Draw()
│
├── GLFWManager
│   ├── PollEvents()
│   ├── ProcessInput()
│   ├── WindowShouldClose()
│   ├── SwapBuffers()
│   ├── SetEventCallback()
│   ├── GetWidth(), GetHeight()
│   └── GetWindow()
│
├── Events
│   ├── Event (base): GetEventType(), GetName(), IsInCategory(), Handled
│   ├── EventDispatcher: Dispatch<T>(handler)
│   ├── WindowResizeEvent, WindowCloseEvent, WindowFocusEvent
│   ├── KeyPressedEvent, KeyReleasedEvent, KeyTypedEvent
│   └── MouseMovedEvent, MouseScrolledEvent, MouseButtonPressed/Released
│
├── UIManager
│   ├── BeginFrame(), EndFrame()
│   ├── StartWindow(), EndWindow()
│   └── Render()
│
└── ErrorHandling (static)
    └── HandleErrors() → Sets up debug callback
```

---

## Key Design Patterns Used

### RAII (Resource Acquisition Is Initialization)
All OpenGL wrappers acquire resources in constructor, release in destructor.

### Factory Method
`Mesh::CreatePyramid()`, `Mesh::CreateCube()` create preconfigured objects.

### Singleton-ish
`Log` and `Engine` use static methods / Meyer's singleton pattern.

### State Machine Wrapper
All OpenGL wrappers have `Bind()`/`Unbind()` to manage OpenGL's state machine.

### Rule of 5
Resource-owning classes delete copy operations and implement move operations.

---

## Memory Management {#memory}

### Ownership Rules

| Object | Owned By | Lifetime |
|--------|----------|----------|
| VertexBuffer | Mesh | Until Mesh destroyed |
| IndexBuffer | Mesh | Until Mesh destroyed |
| VertexArray | Mesh | Until Mesh destroyed |
| Shader | Application | Until scope ends |
| Texture | Application/Model | Until scope ends or last reference gone |
| Mesh (shared_ptr) | Scene/Application/Model | Until last reference gone |
| Camera | Application stack | Until function returns |
| Transform | SceneObject | Until SceneObject destroyed |
| Model (unique_ptr) | Application | Until scope ends |
| PBRMaterial | Model | Until Model destroyed |
| Texture (in Model) | Model's TextureCache | Until Model destroyed |

### No Raw `new`/`delete`

We use:
- Stack allocation for small objects
- `std::unique_ptr` for owned heap objects
- `std::shared_ptr` for shared resources (Mesh)
- RAII classes that clean up in destructors

---

## Logging Quick Reference

### Core Logger (Engine)

```cpp
VP_CORE_TRACE("Detailed debug info");
VP_CORE_INFO("General info");
VP_CORE_WARN("Something unexpected");
VP_CORE_ERROR("Error occurred");
VP_CORE_CRITICAL("Fatal error");
```

### Client Logger (Application)

```cpp
VP_TRACE("Detailed debug info");
VP_INFO("General info");
VP_WARN("Something unexpected");
VP_ERROR("Error occurred");
VP_CRITICAL("Fatal error");
```

### Format Strings

```cpp
VP_INFO("Value: {}", 42);
VP_INFO("{} + {} = {}", 1, 2, 3);
VP_INFO("Float: {:.2f}", 3.14159);
```

---

## Performance Notes

### Current Optimizations
- Uniform location caching in Shader
- Move semantics prevent unnecessary copies
- Index buffers reduce vertex duplication
- Shared mesh geometry via shared_ptr

### Current Limitations (OK for learning)
- Single draw call per mesh
- No batching
- No frustum culling
- No LOD
- No instancing

---

## Debugging Tips {#debugging}

### OpenGL Errors
Debug output is enabled. Check console for messages like:
```
OpenGL Debug Message:
  Source:   API
  Type:     Error
  Severity: HIGH
  Message:  ...
```

### Shader Errors
Compilation errors print to console:
```
SHADER ERROR::COMPILATION ERROR: VERTEX
error: ...
```

### Logging
Use the logging macros:
```cpp
VP_CORE_INFO("Engine message");
VP_INFO("Application message");
VP_CORE_ERROR("Something went wrong!");
```

### Common Issues

| Symptom | Likely Cause |
|---------|--------------|
| Black screen | Shader not bound, or MVP wrong |
| Black texture | Texture not loaded, wrong path |
| Upside-down texture | Missing `stbi_set_flip_vertically_on_load(1)` |
| Nothing renders | Forgot to call Draw(), or indices wrong |
| Crash on exit | Double-delete (check Rule of 5) |

---

## Building & Running

```bash
# Generate project (first time)
cmake -B build -G "Visual Studio 17 2022"

# Build
cmake --build build --config Debug

# Run
./build/bin/Debug/Sandbox.exe
```

---

## Chapter Cross-Reference

| Topic | Chapter |
|-------|---------|
| CMake, build system | [01 Environment Setup](01_EnvironmentSetup.md) |
| GLFW, GLAD, GLM, spdlog | [03 Project Structure](03_ProjectStructure.md) |
| DLL exports, __declspec | [04 DLL Architecture](04_DLLArchitecture.md) |
| Log class, VP_* macros | [05 Logging System](05_LoggingSystem.md) |
| GLFWManager, context | [06 Window & Context](06_WindowAndContext.md) |
| Buffers, shaders, pipeline, GPU architecture | [07 OpenGL Fundamentals](07_OpenGLFundamentals.md) |
| RAII, Rule of 5, move semantics | [08 RAII & Resource Management](08_RAIIAndResourceManagement.md) |
| VertexBuffer, IndexBuffer, VertexArray, Layout | [09 Buffer Classes](09_BufferClasses.md) |
| Shader class, uniform caching, Renderer | [10 Shader & Renderer](10_ShaderAndRenderer.md) |
| Texture class, stb_image, mipmaps | [11 Textures](11_Textures.md) |
| Renderer class, simplified API | [12 Renderer](12_Renderer.md) |
| Transform, Vertex, Mesh, factory methods | [13 Transform & Mesh](13_TransformAndMesh.md) |
| Camera, view/projection matrices | [14 Camera System](14_CameraSystem.md) |
| Scene, SceneObject, shared resources | [15 Scene Management](15_SceneManagement.md) |
| UIManager, ImGui widgets | [16 Dear ImGui](16_DearImGui.md) |
| DirectionalLight, Blinn-Phong, normals | [17 Lighting](17_Lighting.md) |
| glTF format, tinygltf integration | [18 glTF Format](18_glTFFormat.md) |
| Model, PBRMaterial, glTF geometry | [19 Model Loading (Geometry)](19_ModelLoaderGeometry.md) |
| Material textures, PBR properties | [20 Model Loading (Materials)](20_ModelLoaderMaterials.md) |
| Input class, keyboard, mouse, edge detection | [21 Input System](21_InputSystem.md) |
| WASD movement, mouse look, zoom | [22 Camera Controller](22_CameraController.md) |
| Engine class, game loop, lifecycle methods | [23 Engine and Game Loop](23_EngineAndGameLoop.md) |
| Sandbox refactoring, CreateApplication | [24 Sandbox Migration](24_SandboxMigration.md) |
| Event dispatcher, window/input events | [25 Event System](25_EventSystem.md) |

---

## Exercises for Practice

1. **Add a second object** - Create another Mesh and Transform, draw both
2. **Keyboard camera** - Move camera with WASD
3. **Mouse look** - Rotate camera with mouse
4. **New shader** - Create a wireframe shader
5. **New mesh** - Implement `Mesh::CreateSphere()`
6. **Point light** - Implement a point light with attenuation
7. **Multiple lights** - Support an array of lights in the shader
8. **Load a glTF model** - Use `Model::LoadFromFile()` with a sample model
9. **Model browser** - Add ImGui file picker to load models at runtime
10. **PBR rendering** - Upgrade shader to use full PBRMaterial properties (emissive, occlusion, alpha)


