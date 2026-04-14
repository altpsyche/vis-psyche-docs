\newpage

# Appendix A: Code Reference

## What We've Built

As of Chapter 43, VizPsyche has:

### Core Systems
- CMake build system (cross-platform ready)
- DLL architecture with proper exports
- Logging system (spdlog wrapper)
- Entry point abstraction
- Window and context management (GLFWManager)
- Engine singleton with game loop
- Application lifecycle (OnCreate, OnUpdate, OnRender, OnImGuiRender, OnEvent, OnDestroy)
- Input system (keyboard, mouse, scroll polling with edge detection)
- Event system (window, key, mouse events with dispatcher)

### OpenGL Abstractions
- VertexBuffer, IndexBuffer, VertexArray, VertexBufferLayout — GPU buffer pipeline
- Shader — GLSL compilation, linking, uniform caching
- Texture — 2D image loading, HDR, cubemap, framebuffer attachment
- Texture3D — 3D LUT for color grading
- Framebuffer — off-screen render-to-texture
- Renderer — draw calls, viewport, depth/stencil/blend state, face culling, instanced drawing
- GLFWManager — window, context, event routing
- ErrorHandling — OpenGL debug callback
- CubemapUtils — equirectangular-to-cubemap, irradiance map, pre-filtered environment map, BRDF LUT generation
- FullscreenQuad — NDC-space quad for post-processing passes

### Engine Core
- Camera — view/projection matrices, FPS-style movement helpers
- Transform — position, rotation, scale with model matrix
- Mesh — geometry with factory shapes (Cube, Sphere, Plane, Pyramid); Vertex includes Tangent/Bitangent for TBN
- Scene — scene object collection with range-based iteration
- SceneObject — mesh + transform + material bundle; supports direct properties (Ch15) and MaterialRef (Ch42); InstanceCount for hardware instancing (Ch35)
- Model — glTF/GLB model loader (geometry and materials)
- Material — glTF material struct (baseColor, metallic, roughness, emissive, alpha, textures)
- Input — static keyboard, mouse, scroll polling

### Lighting
- DirectionalLight — parallel rays with ambient/diffuse/specular
- PointLight — positional light with distance attenuation

### Rendering Features
- Shadow mapping — directional light shadow maps at configurable resolution (Ch29)
- Skybox — HDR equirectangular environment loaded as cubemap (Ch31)
- Normal mapping — TBN matrix in vertex shader, tangent-space normal textures (Ch34)
- Hardware instancing — `SceneObject.InstanceCount` + `DrawInstanced` (Ch35)

### Physically Based Rendering
- Cook-Torrance BRDF — GGX/Smith microfacet model (Ch37)
- Image-based lighting — irradiance map (diffuse), pre-filtered env map (specular), BRDF LUT (Ch38)
- HDR pipeline — HDR framebuffer, tone mapping (ACES), gamma correction (Ch39)
- Bloom — threshold + dual kawase blur + additive composite (Ch40)
- Color grading — 3D LUT with contribution blend (Ch41)

### Material System (Ch42)
- RenderMaterial — base material: shader + typed parameter store + texture slots, single `Bind()` call
- PBRMaterial — extends RenderMaterial for the defaultlit.shader: albedo, metallic, roughness, AO, IBL maps, shadow map
- UnlitMaterial — flat color/texture material, no lighting
- MaterialFactory — creates named PBR presets (Gold, Chrome, Copper, Plastic) and handles shader caching
- MaterialParameter — variant type storing float/int/bool/vec2/vec3/vec4/mat3/mat4

### Scene Renderer Architecture (Ch43)
- SceneRenderer — frame orchestrator: shadow pass → render path → skybox → stencil outlines → post-processing
- RenderPath — abstract strategy interface (Forward, Forward+, Deferred)
- ForwardRenderPath — concrete forward rendering implementation
- ShadowPass — shadow map generation from directional light perspective
- PostProcessPipeline — composites Bloom → Tone Mapping → Color Grading from HDR buffer to screen
- RenderPassData — POD struct threading all per-frame data between passes
- ShadowData — depth texture + light-space matrix output from ShadowPass
- RenderPathType — enum for runtime render path switching (Forward / ForwardPlus / Deferred)

### GUI
- UIManager — Dear ImGui integration (begin/end frame, window management)

---

## Third-Party Libraries {#libraries}

| Library | Purpose | Added |
|---------|---------|-------|
| GLFW | Window, input, OpenGL context | Ch3 |
| GLAD | OpenGL function loading | Ch2 |
| GLM | Math (vectors, matrices, transforms) | Ch3 |
| Dear ImGui | Immediate mode GUI | Ch16 |
| spdlog | Fast, formatted logging | Ch3 |
| stb_image | Image loading (LDR + HDR) | Ch11 |
| tinygltf | glTF/GLB model loading | Ch18 |

---

## File Reference

### Public API

| File | Purpose |
|------|---------|
| `VizEngine.h` | Single include for users |
| `Core.h` | Export macros, platform detection |
| `EntryPoint.h` | Defines `main()`, calls `CreateApplication` |
| `Application.h` | Base class with lifecycle methods |
| `Engine.h` | Engine singleton, game loop, subsystem access |
| `Log.h` | Logging macros |

### Core

| File | Purpose |
|------|---------|
| `Core/Camera.h` | View/projection matrix management |
| `Core/Transform.h` | Position, rotation, scale struct |
| `Core/Mesh.h` | Geometry abstraction with factory shapes; Vertex includes Tangent/Bitangent (Ch34) |
| `Core/Scene.h` | Scene object collection manager |
| `Core/SceneObject.h` | Mesh + transform + material bundle; MaterialRef (Ch42), InstanceCount (Ch35) |
| `Core/Light.h` | DirectionalLight, PointLight |
| `Core/Model.h` | glTF/GLB model loader |
| `Core/Material.h` | glTF material struct (baseColor, metallic, roughness, textures) |
| `Core/Input.h` | Keyboard, mouse, scroll polling with edge detection |

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
| `OpenGL/VertexArray.h` | VAO wrapper; LinkInstanceBuffer for instancing (Ch35) |
| `OpenGL/VertexBufferLayout.h` | Vertex attribute configuration |
| `OpenGL/Shader.h` | Shader program wrapper; SetMatrix3fv for normal matrix (Ch37) |
| `OpenGL/Texture.h` | Texture wrapper; HDR and cubemap constructors (Ch30); CreateNeutralLUT3D (Ch41) |
| `OpenGL/Texture3D.h` | 3D LUT texture for color grading (Ch41) |
| `OpenGL/Framebuffer.h` | FBO wrapper; AttachDepthStencilTexture (Ch32) |
| `OpenGL/Renderer.h` | Draw calls, viewport, depth/stencil/blend/cull state, DrawInstanced (Ch35) |
| `OpenGL/GLFWManager.h` | Window, context, event routing |
| `OpenGL/ErrorHandling.h` | OpenGL debug output callback |
| `OpenGL/Commons.h` | Shared texture slot constants |
| `OpenGL/CubemapUtils.h` | EquirectangularToCubemap (Ch31); irradiance, pre-filtered env, BRDF LUT generation (Ch38) |
| `OpenGL/FullscreenQuad.h` | NDC-space quad for post-processing passes (Ch39) |

### Renderer

| File | Purpose |
|------|---------|
| `Renderer/RenderMaterial.h` | Base material: shader + parameter store + texture slots (Ch42) |
| `Renderer/PBRMaterial.h` | PBR material with IBL, shadow map, metallic-roughness workflow (Ch42) |
| `Renderer/UnlitMaterial.h` | Flat color/texture material, no lighting (Ch42) |
| `Renderer/MaterialFactory.h` | Creates PBR and Unlit materials with presets; shader cache (Ch42) |
| `Renderer/MaterialParameter.h` | Variant type for typed shader parameters (Ch42) |
| `Renderer/Skybox.h` | HDR cubemap skybox rendering (Ch31) |
| `Renderer/Bloom.h` | Threshold + dual kawase blur + composite (Ch40) |
| `Renderer/SceneRenderer.h` | Frame orchestrator: shadow → render path → skybox → outlines → post-process (Ch43) |
| `Renderer/RenderPath.h` | Abstract rendering strategy interface (Ch43) |
| `Renderer/ForwardRenderPath.h` | Forward rendering implementation (Ch43) |
| `Renderer/ShadowPass.h` | Directional light shadow map generation (Ch43) |
| `Renderer/PostProcessPipeline.h` | Bloom → Tone Mapping → Color Grading composition (Ch43) |
| `Renderer/RenderPassData.h` | RenderPassData, ShadowData, PrepassOutput structs; RenderPathType enum (Ch43) |

### GUI

| File | Purpose |
|------|---------|
| `GUI/UIManager.h` | Dear ImGui integration |

### Resources (shaders)

| File | Purpose |
|------|---------|
| `resources/shaders/unlit.shader` | Flat color / texture, no lighting |
| `resources/shaders/defaultlit.shader` | Cook-Torrance PBR with IBL and shadows |
| `resources/shaders/depth.shader` | Shadow map depth-only pass |
| `resources/shaders/outline.shader` | Stencil-based object outline |
| `resources/shaders/instanced.shader` | Hardware-instanced PBR variant |
| `resources/shaders/equirect_to_cube.shader` | Equirectangular HDR → cubemap |
| `resources/shaders/irradiance_convolution.shader` | Diffuse IBL irradiance map generation |
| `resources/shaders/prefilter.shader` | Specular IBL pre-filtered environment map |
| `resources/shaders/brdf.shader` | BRDF integration LUT generation |
| `resources/shaders/skybox.shader` | Cubemap skybox rendering |
| `resources/shaders/bloom.shader` | Threshold + blur passes |
| `resources/shaders/tonemapping.shader` | Tone mapping, gamma correction, color grading |

---

## Class Diagram {#class-diagram}

```
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
│   ├── GetCoreLogger(), GetClientLogger()
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
│   └── CreateCube(), CreatePlane(), CreatePyramid(), CreateSphere() [static factories]
│
│   Vertex (struct)
│   ├── Position, Normal, TexCoords   [Ch9]
│   ├── Tangent, Bitangent            [Ch34 — TBN normal mapping]
│
├── Scene
│   ├── Add(), Remove(), Clear()
│   ├── operator[](), At(), Size(), Empty()
│   ├── begin(), end()  [range-based for]
│   └── Update(), Render()
│
├── SceneObject (struct)
│   ├── MeshPtr                        [Ch15]
│   ├── ObjectTransform                [Ch15]
│   ├── Color, TexturePtr              [Ch15] — direct material (Option 1)
│   ├── Roughness, Metallic            [Ch17] — PBR direct properties
│   ├── MaterialRef (shared_ptr)       [Ch42] — production material (Option 2)
│   ├── InstanceCount                  [Ch35] — 0 = normal, >0 = instanced
│   ├── Active, Name
│   └── HasMaterialRef()
│
├── Model
│   ├── LoadFromFile() [static factory]
│   ├── GetMeshes(), GetMaterials()
│   ├── GetMaterialIndexForMesh(), GetMaterialForMesh()
│   ├── GetName(), GetFilePath(), IsValid()
│   └── (ModelLoader inner class drives tinygltf)
│
├── Material (struct) — glTF material data
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
├── PointLight (struct)
│   ├── Position, Color
│   └── Constant, Linear, Quadratic attenuation
│
├── OpenGL Wrappers
│   ├── VertexBuffer: Bind(), Unbind(), GetID()
│   ├── IndexBuffer: Bind(), Unbind(), GetCount()
│   ├── VertexArray: LinkVertexBuffer(), LinkInstanceBuffer(), Bind(), Unbind()
│   ├── VertexBufferLayout: Push<T>(), GetElements()
│   ├── Shader: Bind(), Unbind(), Set*() uniforms, GetUniformLocation() cached
│   ├── Texture: Bind(slot), Unbind(), GetWidth(), GetHeight()
│   │     + HDR constructor (stbi_loadf), empty cubemap constructor
│   │     + CreateNeutralLUT3D() [Ch41]
│   ├── Texture3D: Bind(slot), Unbind() [Ch41 — 3D color grading LUT]
│   ├── Framebuffer: Bind(), Unbind(), AttachColorTexture(),
│   │     AttachDepthTexture(), AttachDepthStencilTexture(), IsComplete()
│   ├── Renderer: Clear(), Draw(), DrawInstanced(), SetViewport(),
│   │     SetDepthFunc(), SetStencilTest(), SetBlend(), SetFaceCulling()
│   ├── GLFWManager: PollEvents(), SwapBuffers(), WindowShouldClose(),
│   │     SetEventCallback(), GetWidth(), GetHeight(), GetWindow()
│   ├── ErrorHandling: HandleErrors() → debug callback
│   ├── CubemapUtils: EquirectangularToCubemap(), GenerateIrradianceMap(),
│   │     GeneratePrefilteredMap(), GenerateBRDFLUT() [Ch38]
│   └── FullscreenQuad: Bind(), Draw() [Ch39 — NDC quad for post-process]
│
├── Material System
│   ├── RenderMaterial
│   │   ├── Bind(), Unbind()
│   │   ├── SetFloat/Int/Bool/Vec2/Vec3/Vec4/Mat3/Mat4()
│   │   ├── SetTexture(name, texture, slot)
│   │   ├── GetParameter<T>(), HasParameter()
│   │   ├── GetName(), GetShader(), IsValid()
│   │   └── UploadParameters() [virtual, override in derived]
│   │
│   ├── PBRMaterial : RenderMaterial
│   │   ├── SetAlbedo/Metallic/Roughness/AO/Alpha()
│   │   ├── SetAlbedoTexture/NormalTexture/MetallicRoughnessTexture/AOTexture/EmissiveTexture()
│   │   ├── SetIrradianceMap/PrefilteredMap/BRDFLU()
│   │   ├── SetUseIBL(), SetLowerHemisphereColor/Intensity()
│   │   └── SetShadowMap()
│   │
│   ├── UnlitMaterial : RenderMaterial
│   │   ├── SetColor(), SetTexture()
│   │   └── SetUseTexture()
│   │
│   └── MaterialFactory (static)
│       ├── CreatePBR(name), CreatePBR(shader, name)
│       ├── CreateUnlit(name), CreateUnlit(shader, name)
│       ├── CreateGold(), CreateChrome(), CreateCopper(), CreatePlastic()
│       └── ClearCache()
│
├── Scene Renderer
│   ├── SceneRenderer
│   │   ├── SceneRenderer(width, height)
│   │   ├── Render(scene, camera, renderer)
│   │   ├── SetRenderPath(type), GetRenderPathType(), GetRenderPathName()
│   │   ├── OnResize(width, height), OnImGuiDebug()
│   │   ├── Set*() — shader, material, IBL, lights, skybox, outlines, post-process
│   │   ├── GetPostProcess() → PostProcessPipeline*
│   │   └── GetShadowPass() → ShadowPass*
│   │
│   ├── RenderPath (abstract)
│   │   ├── OnAttach(width, height), OnDetach()
│   │   ├── Execute(data), OnResize(width, height)
│   │   ├── NeedsDepthPrepass(), ProvidesGBufferDepth/Normals()
│   │   ├── GetDepthTexture(), GetNormalTexture()
│   │   ├── GetName(), GetType()
│   │   └── IsValid()
│   │
│   ├── ForwardRenderPath : RenderPath
│   │   └── (implements all RenderPath pure virtuals)
│   │
│   ├── ShadowPass
│   │   ├── ShadowPass(resolution = 2048)
│   │   ├── Process(scene, light, renderer) → ShadowData
│   │   ├── IsValid(), GetResolution(), GetShadowMap()
│   │
│   └── PostProcessPipeline
│       ├── PostProcessPipeline(width, height)
│       ├── Process(hdrColorTexture, renderer, width, height)
│       ├── OnResize(width, height)
│       ├── SetEnableBloom/Threshold/Knee/Intensity/BlurPasses()
│       ├── SetToneMappingMode/Exposure/Gamma/WhitePoint()
│       └── SetEnableColorGrading/LUTContribution/Saturation/Contrast/Brightness()
│
├── Renderer Features
│   ├── Skybox
│   │   ├── Skybox(hdrPath)
│   │   ├── Draw(camera, renderer), IsValid()
│   │   └── GetCubemapTexture()
│   │
│   └── Bloom
│       ├── Bloom(width, height)
│       ├── Process(sourceTexture, renderer) → brightTexture
│       └── OnResize(width, height)
│
├── Events
│   ├── Event (base): GetEventType(), GetName(), IsInCategory(), Handled
│   ├── EventDispatcher: Dispatch<T>(handler)
│   ├── WindowResizeEvent, WindowCloseEvent, WindowFocusEvent, WindowLostFocusEvent
│   ├── KeyPressedEvent(keycode, isRepeat), KeyReleasedEvent, KeyTypedEvent(codepoint)
│   └── MouseMovedEvent, MouseScrolledEvent, MouseButtonPressedEvent, MouseButtonReleasedEvent
│
├── UIManager
│   ├── BeginFrame(), EndFrame()
│   ├── StartWindow(), EndWindow()
│   └── Render()
│
└── ErrorHandling (static)
    └── HandleErrors() → sets up OpenGL debug callback
```

---

## Key Design Patterns

### RAII (Resource Acquisition Is Initialization)
All OpenGL wrappers acquire resources in constructor, release in destructor. No manual `glDelete*` calls in application code.

### Factory Method
`Mesh::CreateCube()`, `MaterialFactory::CreateGold()`, `Model::LoadFromFile()`.

### Strategy (Ch43)
`RenderPath` is an abstract strategy. `SceneRenderer` holds a `unique_ptr<RenderPath>` and delegates `Execute()` to whatever path is active. Switching paths at runtime: `SetRenderPath(RenderPathType::Deferred)`.

### Template Method (Ch42)
`RenderMaterial::Bind()` calls the virtual `UploadParameters()`. Derived classes override `UploadParameters()` to add custom uniform logic without reimplementing the bind sequence.

### Singleton
`Engine` uses a Meyer's singleton. `Log` uses static methods over a static logger instance.

### State Machine Wrapper
All OpenGL wrappers have `Bind()`/`Unbind()` to manage OpenGL's global state machine.

### Rule of 5
Resource-owning classes delete copy operations and implement move semantics.

---

## Memory Management {#memory}

### Ownership Rules

| Object | Owned By | Smart Pointer | Lifetime |
|--------|----------|---------------|----------|
| VertexBuffer, IndexBuffer, VertexArray | Mesh | `unique_ptr` | Until Mesh destroyed |
| Shader | SandboxApp / MaterialFactory cache | `shared_ptr` | Until last reference gone |
| Texture (scene textures) | SandboxApp | `shared_ptr` | Until scope ends |
| Texture (IBL maps) | SandboxApp → SceneRenderer | `shared_ptr` | Until scope ends |
| Mesh | Scene / SandboxApp | `shared_ptr` | Until last reference gone |
| SceneObject | Scene | value | Until Scene cleared |
| Camera | SandboxApp | stack/member | Until SandboxApp destroyed |
| Transform | SceneObject | value | Until SceneObject destroyed |
| Model | SandboxApp | `unique_ptr` | Until scope ends |
| Material (glTF) | Model | value (vector) | Until Model destroyed |
| RenderMaterial / PBRMaterial | SandboxApp / Scene | `shared_ptr` | Until last reference gone |
| RenderPath | SceneRenderer | `unique_ptr` | Until SceneRenderer destroyed or path switched |
| ShadowPass | SceneRenderer | `unique_ptr` | Until SceneRenderer destroyed |
| PostProcessPipeline | SceneRenderer | `unique_ptr` | Until SceneRenderer destroyed |
| Bloom | PostProcessPipeline | `unique_ptr` | Until PostProcessPipeline destroyed |
| SceneRenderer | SandboxApp | stack/member | Until SandboxApp destroyed |
| Skybox | SandboxApp | stack/member | Lifetime of SandboxApp |

### No Raw `new`/`delete`

- Stack allocation for small, local objects
- `std::unique_ptr` for single-owned heap objects
- `std::shared_ptr` for resources used by multiple owners (textures, meshes, shaders)
- RAII classes that clean up OpenGL resources in destructors

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

### Optimizations in Place
- Uniform location caching in Shader (no `glGetUniformLocation` per frame)
- Index buffers reduce vertex duplication
- Shared mesh geometry via `shared_ptr` (multiple objects, one GPU upload)
- Hardware instancing for large object counts via `SceneObject.InstanceCount` (Ch35)
- HDR framebuffer avoids precision loss in intermediate render passes (Ch39)
- PBR material system eliminates redundant shader state changes via `Bind()` (Ch42)

### Current Limitations (appropriate for learning)
- Single directional light shadow map (no point light shadows, no cascades)
- No frustum culling (all scene objects submitted every frame)
- No draw call batching
- No LOD (Level of Detail)
- One active render path at a time (Forward only at Ch43 boundary; Forward+ and Deferred come in Part XII)

---

## Debugging Tips {#debugging}

### OpenGL Errors
Debug output is enabled by default. Check the console for:
```
OpenGL Debug Message:
  Source:   API
  Type:     Error
  Severity: HIGH
  Message:  ...
```

### Shader Errors
Compilation failures print to console:
```
SHADER ERROR::COMPILATION ERROR: VERTEX
error: ...
```

### Shadow Artifacts
- **Peter Panning** — bias too high; reduce `ShadowPass` bias
- **Shadow Acne** — bias too low; increase bias slightly
- **Hard cutoff** — object outside the light frustum; adjust near/far planes

### HDR / Post-Processing
- **Overexposed scene** — reduce `SceneRenderer::SetExposure()`
- **No bloom** — threshold too high; lower `PostProcessPipeline::SetBloomThreshold()`
- **Washed-out colors** — LUT contribution too high; `SetLUTContribution(0.0f)` to disable grading

### Common Issues

| Symptom | Likely Cause |
|---------|--------------|
| Black screen | Shader not bound, or MVP wrong |
| Black texture | Texture not loaded, wrong path |
| Upside-down texture | Missing `stbi_set_flip_vertically_on_load(1)` |
| Nothing renders | Forgot `Draw()`, or indices wrong |
| Crash on exit | Double-delete (check Rule of 5) |
| IBL too bright | `IBLIntensity` too high (default 0.3) |
| No shadows | `ShadowPass` not initialized or light direction is zero |

---

## Building & Running

```bash
# Clone with submodules
git clone --recursive https://github.com/yourusername/VizPsyche.git
cd VizPsyche

# Configure
cmake -B build -G "Visual Studio 17 2022"

# Build
cmake --build build --config Debug

# Run
.\build\bin\Debug\Sandbox.exe
```

---

## Chapter Cross-Reference

| Topic | Chapter |
|-------|---------|
| CMake, build system | [01 Environment Setup](01_EnvironmentSetup.md) |
| GLFW, GLAD, GLM, spdlog | [03 Project Structure](03_ProjectStructure.md) |
| DLL exports, `__declspec` | [04 DLL Architecture](04_DLLArchitecture.md) |
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
| Model, glTF geometry loading | [19 Model Loader (Geometry)](19_ModelLoaderGeometry.md) |
| Material textures, PBR properties from glTF | [20 Model Loader (Materials)](20_ModelLoaderMaterials.md) |
| Input class, keyboard, mouse, edge detection | [21 Input System](21_InputSystem.md) |
| WASD movement, mouse look, zoom | [22 Camera Controller](22_CameraController.md) |
| Engine class, game loop, lifecycle methods | [23 Engine and Game Loop](23_EngineAndGameLoop.md) |
| SandboxApp refactoring, CreateApplication | [24 Sandbox Migration](24_SandboxMigration.md) |
| Event dispatcher, window/input events | [25 Event System](25_EventSystem.md) |
| Engine lifecycle, OnEvent routing | [26 Advanced Lifecycle](26_AdvancedLifecycle.md) |
| Framebuffer, render-to-texture, offscreen rendering | [27 Framebuffers](27_Framebuffers.md) |
| Texture wrapping, filtering, mipmaps, anisotropy | [28 Advanced Texture Configuration](28_TextureParameters.md) |
| Shadow maps, depth FBO, PCF | [29 Shadow Mapping](29_ShadowMapping.md) |
| Cubemaps, HDR loading, equirectangular conversion | [30 Cubemaps and HDR](30_CubemapsAndHDR.md) |
| Skybox rendering, HDR environment | [31 Skybox Rendering](31_SkyboxRendering.md) |
| Depth test, stencil test, face culling | [32 Depth & Stencil Testing](32_DepthStencilTesting.md) |
| Blending, transparency, depth sorting | [33 Blending & Transparency](33_BlendingTransparency.md) |
| Normal maps, TBN matrix, Tangent/Bitangent in Vertex | [34 Normal Mapping](34_NormalMapping.md) |
| Hardware instancing, DrawInstanced, InstanceCount | [35 Instancing](35_Instancing.md) |
| Microfacet theory, Cook-Torrance BRDF | [36 PBR Theory](36_PBRTheory.md) |
| PBR shader, GGX, Smith, u_NormalMatrix | [37 PBR Implementation](37_PBRImplementation.md) |
| IBL, irradiance map, pre-filtered env, BRDF LUT | [38 Image-Based Lighting](38_ImageBasedLighting.md) |
| HDR framebuffer, tone mapping, FullscreenQuad | [39 HDR Pipeline](39_HDRPipeline.md) |
| Bloom, threshold, dual kawase blur | [40 Bloom](40_Bloom.md) |
| Color grading, 3D LUT, Texture3D | [41 Color Grading](41_ColorGrading.md) |
| RenderMaterial, PBRMaterial, MaterialFactory | [42 Material System](42_MaterialSystem.md) |
| SceneRenderer, RenderPath, ShadowPass, PostProcessPipeline | [43 Scene Renderer Architecture](43_SceneRendererArchitecture.md) |

---

## Exercises for Practice

### Foundations (Ch1-15)
1. Add a second object — create another Mesh and Transform, draw both
2. Implement `Mesh::CreateSphere()` with configurable segments
3. Implement a simple scene serializer — save/load SceneObject positions to JSON

### Rendering (Ch17-35)
4. Add a point light — upload position and attenuation to the defaultlit shader
5. Support multiple point lights — use a uniform array, loop in the shader
6. Load a glTF model and render all its meshes with their materials
7. Add a normal map to a loaded model using the existing TBN pipeline
8. Render 1000 trees with hardware instancing and measure the frame time difference

### PBR & Post-Processing (Ch36-41)
9. Add a roughness slider in ImGui and see the GGX highlight change in real time
10. Toggle IBL off and compare the scene — note what diffuse and specular lose without it
11. Tune Bloom threshold until only the brightest specular highlights glow
12. Create a sepia color grade by modifying a 3D LUT and applying it at 50% contribution

### Material System (Ch42-43)
13. Create a `MaterialFactory::CreateRustedIron()` preset with an albedo, normal, and metallic-roughness texture
14. Add a second `SceneObject` that shares the same `PBRMaterial` — change the material and watch both update
15. Add a `RenderPathType` selector to the ImGui debug panel and measure the per-frame cost of switching
