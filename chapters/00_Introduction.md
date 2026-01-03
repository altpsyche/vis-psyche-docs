\newpage

# VizPsyche Engine: A Technical Journey

## What is VizPsyche?

VizPsyche is a 3D rendering engine built from scratch using C++17 and OpenGL 4.6. The name combines "Viz" (visualization) with "Psyche" (the mind/soul) - representing the goal of understanding the soul of graphics programming.

## Why Build an Engine from Scratch?

1. **Deep Understanding** - Using Unity or Unreal hides the fundamentals
2. **Complete Control** - Every line of code is yours to understand and modify
3. **Industry Knowledge** - Game studios value engineers who understand the "how"
4. **Problem Solving** - Debugging becomes easier when you know the internals

## What You'll Learn

By the end of this book, you'll understand:

- **Build Systems** - CMake, DLLs, linking, and project organization
- **Third-Party Libraries** - GLFW, GLAD, GLM, ImGui, spdlog, stb_image, tinygltf
- **Graphics Pipeline** - How pixels get from code to screen
- **OpenGL** - Modern OpenGL 4.6 with VAOs, VBOs, shaders
- **Engine Architecture** - How professional engines are structured
- **Memory Management** - RAII, move semantics, resource lifetime
- **Lighting** - Blinn-Phong lighting model
- **Model Loading** - Loading 3D assets from glTF files with PBR materials

## Prerequisites

- Basic C++ knowledge (classes, pointers, references)
- Basic math (vectors, matrices - we'll explain as we go)
- A Windows PC with Visual Studio 2022+

## Project Structure Overview

```
VizPsyche/
├── CMakeLists.txt          ← Root build configuration
├── VizEngine/              ← The engine (compiled as DLL)
│   ├── CMakeLists.txt
│   ├── src/
│   │   ├── VizEngine.h     ← Public API header
│   │   └── VizEngine/      ← Engine source code
│   ├── include/            ← Third-party headers (GLAD)
│   └── vendor/             ← Dependencies (GLFW, GLM, ImGui, spdlog)
├── Sandbox/                ← Test application (uses the engine)
│   ├── CMakeLists.txt
│   └── src/
│       └── SandboxApp.cpp
└── build/                  ← Generated build files
```

## How to Use This Book

This book is a **companion**, not a prescription. It explains how VizPsyche works so you *can* build along if you choose.

### Two Paths

**Reading to Understand:**
Browse the documentation, understand how the engine works, and reference it when modifying the codebase. No need to type anything.

**Building Along:**
Follow chapter by chapter, implementing each piece. Each chapter ends with a **Checkpoint** section listing the files you should have and what you should see running.

> **Either path is valid.** The book enables; it doesn't demand.

### Reading Order

Each chapter builds on the previous. The concepts stack:

### Part 1: Foundation
1. **[Build System](01_BuildSystem.md)** - CMake and project setup
2. **[DLL Architecture](02_DLLArchitecture.md)** - Why we separate engine and app
3. **[Third-Party Libraries](03_ThirdPartyLibraries.md)** - The libraries we use and why

### Part 2: Infrastructure
4. **[Logging System](04_LoggingSystem.md)** - Tracking what happens in the engine
5. **[Window & Context](05_WindowAndContext.md)** - GLFW and OpenGL context
6. **[OpenGL Fundamentals](06_OpenGLFundamentals.md)** - The graphics pipeline

### Part 3: C++ Patterns
7. **[RAII & Resource Management](07_RAIIAndResourceManagement.md)** - Constructor/destructor patterns

### Part 4: OpenGL Wrappers
8. **[Buffer Classes](08_BufferClasses.md)** - VBO, IBO, VAO wrappers
9. **[Shader & Renderer](09_ShaderAndRenderer.md)** - Shader compilation, draw calls
10. **[Textures](10_Textures.md)** - Loading and using images

### Part 5: Editor
11. **[Dear ImGui](11_DearImGui.md)** - Debug UI for development

### Part 6: Engine Architecture
12. **[Transform & Mesh](12_TransformAndMesh.md)** - Position, rotation, scale, geometry
13. **[Camera System](13_CameraSystem.md)** - View and projection matrices
14. **[Scene Management](14_SceneManagement.md)** - Managing multiple objects

### Part 7: Graphics II
15. **[Lighting](15_Lighting.md)** - Blinn-Phong lighting model

### Part 8: Assets
16. **[Model Loading](16_ModelLoading.md)** - Loading glTF models with PBR materials

### Part 9: Input
17. **[Input System](17_InputSystem.md)** - Keyboard, mouse, polling
18. **[Camera Controller](18_CameraController.md)** - WASD movement, mouse look

### Appendices
- **[Appendix A: Code Reference](A_Reference.md)** - Class diagrams, file reference

Ready to start.

