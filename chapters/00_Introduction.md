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
4. **[Window & Context](04_WindowAndContext.md)** - GLFW and OpenGL context
5. **[Logging System](05_LoggingSystem.md)** - Tracking what happens in the engine

### Part 3: Graphics
6. **[OpenGL Fundamentals](06_OpenGLFundamentals.md)** - The graphics pipeline
7. **[Abstractions](07_Abstractions.md)** - Wrapping OpenGL in clean C++
8. **[Textures](08_Textures.md)** - Loading and using images

### Part 4: Engine
9. **[Engine Architecture](09_EngineArchitecture.md)** - Proper game engine structure
10. **[Multiple Objects & Scene](10_MultipleObjects.md)** - Managing complex scenes

### Part 5: Advanced Graphics
11. **[Lighting](11_Lighting.md)** - Blinn-Phong lighting model
12. **[Model Loading](12_ModelLoading.md)** - Loading glTF models with PBR materials

### Appendices
- **[Appendix A: Code Reference](A_Reference.md)** - Class diagrams, file reference

Let's begin!

