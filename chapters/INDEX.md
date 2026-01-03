# VizPsyche Engine Book

A step-by-step guide to building a 3D rendering engine from scratch using C++ and OpenGL.

---

## Table of Contents

### Part I: Getting Started
- [Chapter 0: Introduction](00_Introduction.md)
- [Chapter 1: Environment Setup](01_EnvironmentSetup.md)
- [Chapter 2: Hello Triangle](02_HelloTriangle.md)
- [Chapter 3: Project Structure](03_ProjectStructure.md)
- [Chapter 4: Logging System](04_LoggingSystem.md)

### Part II: OpenGL Foundations
- [Chapter 5: Window & Context](05_WindowAndContext.md)
- [Chapter 6: OpenGL Fundamentals](06_OpenGLFundamentals.md)
- [Chapter 7: RAII & Resource Management](07_RAIIAndResourceManagement.md)

### Part III: GPU Abstractions
- [Chapter 8: Buffer Classes](08_BufferClasses.md)
- [Chapter 9: Shader System](09_ShaderAndRenderer.md)
- [Chapter 10: Texture System](10_Textures.md)
- [Chapter 11: Renderer Class](11_Renderer.md)

### Part IV: Engine Architecture
- [Chapter 12: Transform & Mesh](12_TransformAndMesh.md)
- [Chapter 13: Camera System](13_CameraSystem.md)
- [Chapter 14: Scene Management](14_SceneManagement.md)
- [Chapter 15: Dear ImGui](15_DearImGui.md)

### Part V: Lighting
- [Chapter 16: Blinn-Phong Lighting](16_Lighting.md)

### Part VI: Asset Loading
- [Chapter 17: glTF Format](17_glTFFormat.md)
- [Chapter 18: Model Loader (Geometry)](18_ModelLoaderGeometry.md)
- [Chapter 19: Model Loader (Materials)](19_ModelLoaderMaterials.md)

### Part VII: Input & Controls
- [Chapter 20: Input System](20_InputSystem.md)
- [Chapter 21: Camera Controller](21_CameraController.md)

### Appendices
- [Appendix A: Code Reference](A_Reference.md)

---

## Dependencies Added By Chapter

| Chapter | Library | Method |
|---------|---------|--------|
| 2 | GLAD | Downloaded |
| 3 | GLFW, GLM, spdlog | Git submodules |
| 10 | stb_image | Downloaded |
| 15 | Dear ImGui | Git submodule |
| 17 | tinygltf | Git submodule |

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
