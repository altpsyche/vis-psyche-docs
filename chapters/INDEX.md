# VizPsyche Engine Book

A step-by-step guide to building a 3D rendering engine from scratch using C++ and OpenGL.

---

## Table of Contents

### Part I: Getting Started
- [Chapter 0: Introduction](00_Introduction.md)
- [Chapter 1: Environment Setup](01_EnvironmentSetup.md)
- [Chapter 2: Hello Triangle](02_HelloTriangle.md)
- [Chapter 3: Project Structure](03_ProjectStructure.md)
- [Chapter 4: DLL Architecture](04_DLLArchitecture.md)
- [Chapter 5: Logging System](05_LoggingSystem.md)

### Part II: OpenGL Foundations
- [Chapter 6: Window & Context](06_WindowAndContext.md)
- [Chapter 7: OpenGL Fundamentals](07_OpenGLFundamentals.md)
- [Chapter 8: RAII & Resource Management](08_RAIIAndResourceManagement.md)

### Part III: GPU Abstractions
- [Chapter 9: Buffer Classes](09_BufferClasses.md)
- [Chapter 10: Shader System](10_ShaderAndRenderer.md)
- [Chapter 11: Texture System](11_Textures.md)
- [Chapter 12: Renderer Class](12_Renderer.md)

### Part IV: Engine Architecture
- [Chapter 13: Transform & Mesh](13_TransformAndMesh.md)
- [Chapter 14: Camera System](14_CameraSystem.md)
- [Chapter 15: Scene Management](15_SceneManagement.md)
- [Chapter 16: Dear ImGui](16_DearImGui.md)

### Part V: Lighting
- [Chapter 17: Blinn-Phong Lighting](17_Lighting.md)

### Part VI: Asset Loading
- [Chapter 18: glTF Format](18_glTFFormat.md)
- [Chapter 19: Model Loader (Geometry)](19_ModelLoaderGeometry.md)
- [Chapter 20: Model Loader (Materials)](20_ModelLoaderMaterials.md)

### Part VII: Input & Controls
- [Chapter 21: Input System](21_InputSystem.md)
- [Chapter 22: Camera Controller](22_CameraController.md)

### Part VIII: Application Lifecycle
- [Chapter 23: Engine and Game Loop](23_EngineAndGameLoop.md)
- [Chapter 24: Sandbox Migration](24_SandboxMigration.md)
- [Chapter 25: Event System](25_EventSystem.md)
- [Chapter 26: Advanced Lifecycle](26_AdvancedLifecycle.md)

### Part IX: Advanced Techniques
- [Chapter 27: Framebuffers](27_Framebuffers.md)
- [Chapter 28: Advanced Texture Configuration](28_TextureParameters.md)
- [Chapter 29: Shadow Mapping](29_ShadowMapping.md)
- [Chapter 30: Cubemaps and HDR](30_CubemapsAndHDR.md)
- [Chapter 31: Skybox Rendering](31_SkyboxRendering.md)

### Part X: OpenGL Essentials
- [Chapter 32: Depth & Stencil Testing](32_DepthStencilTesting.md)
- [Chapter 33: Blending & Transparency](33_BlendingTransparency.md)
- [Chapter 34: Normal Mapping](34_NormalMapping.md)
- [Chapter 35: Instancing](35_Instancing.md)

### Part XI: Physically Based Rendering
- [Chapter 36: PBR Theory](36_PBRTheory.md)
- [Chapter 37: PBR Implementation](37_PBRImplementation.md)
- [Chapter 38: Image-Based Lighting](38_ImageBasedLighting.md)
- [Chapter 39: HDR Pipeline](39_HDRPipeline.md)
- [Chapter 40: Bloom](40_Bloom.md)
- [Chapter 41: Color Grading](41_ColorGrading.md)
- [Chapter 42: Material System](42_MaterialSystem.md)

### Part XII: Multi-Path Rendering & Screen-Space Effects
- [Chapter 43: Scene Renderer Architecture](43_SceneRendererArchitecture.md)
- [Chapter 44: Light Management & SSBOs](44_LightManagementSSBOs.md)
- [Chapter 45: Depth & Normal Prepass](45_DepthNormalPrepass.md)
- [Chapter 46: Forward+ Rendering](46_ForwardPlusRendering.md)
- [Chapter 47: Deferred Rendering](47_DeferredRendering.md)
- [Chapter 48: SSAO](48_SSAO.md)
- [Chapter 49: Screen-Space Reflections](49_ScreenSpaceReflections.md)
- [Chapter 50: Render Path Comparison](50_RenderPathComparison.md)

### Appendices
- [Appendix A: Code Reference](A_Reference.md)

---

## Dependencies Added By Chapter

| Chapter | Library | Method |
|---------|---------|--------|
| 2 | GLAD | Downloaded |
| 3 | GLFW, GLM, spdlog | Git submodules |
| 11 | stb_image | Downloaded |
| 16 | Dear ImGui | Git submodule |
| 18 | tinygltf | Git submodule |

---

## Build Instructions

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

## Requirements

- Windows 10/11
- Visual Studio 2022
- CMake 3.20+
- GPU with OpenGL 4.6 support
