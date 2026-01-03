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
