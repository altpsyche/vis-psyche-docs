# VizPsyche Engine Technical Book

A hands-on guide to building a 3D rendering engine from scratch.

## Table of Contents

### Part 1: Foundation
1. **[Introduction](00_Introduction.md)** - What we're building and why
2. **[Build System](01_BuildSystem.md)** - CMake, project structure, building
3. **[DLL Architecture](02_DLLArchitecture.md)** - Exports, namespaces, entry points
4. **[Third-Party Libraries](03_ThirdPartyLibraries.md)** - GLFW, GLAD, GLM, ImGui, spdlog, stb_image

### Part 2: Infrastructure
5. **[Window & Context](04_WindowAndContext.md)** - GLFWManager, OpenGL context, input
6. **[Logging System](05_LoggingSystem.md)** - spdlog wrapper, log levels, macros

### Part 3: Graphics
7. **[OpenGL Fundamentals](06_OpenGLFundamentals.md)** - Pipeline, buffers, shaders, coordinates
8. **[Abstractions](07_Abstractions.md)** - RAII wrappers, Rule of 5, clean APIs
9. **[Textures](08_Textures.md)** - Image loading, GPU textures, UV mapping

### Part 4: Engine
10. **[Engine Architecture](09_EngineArchitecture.md)** - Camera, Transform, Mesh, separation of concerns
11. **[Multiple Objects](10_MultipleObjects.md)** - Scene management, shared resources, object selection

### Part 5: Graphics II
12. **[Lighting](11_Lighting.md)** - Blinn-Phong model, normals, directional lights

### Appendices
- **[Appendix A: Code Reference](A_Reference.md)** - Class diagrams, file reference, debugging tips

---

## Reading Order

Read chapters in order. Each builds on the previous:

```
00 Introduction
      ↓
01 Build System ←── Understand how we compile
      ↓
02 DLL Architecture ←── Understand how engine/app interact
      ↓
03 Third-Party Libraries ←── Know our building blocks
      ↓
04 Window & Context ←── Create window, OpenGL context
      ↓
05 Logging System ←── Track what's happening
      ↓
06 OpenGL Fundamentals ←── Understand graphics basics
      ↓
07 Abstractions ←── Understand our C++ patterns
      ↓
08 Textures ←── Add images to geometry
      ↓
09 Engine Architecture ←── Understand how it all fits
      ↓
10 Multiple Objects ←── Manage complex scenes
      ↓
11 Lighting ←── Make it look 3D
      ↓
Appendix A ←── Reference material
```

---

## How to Use This Book

### While Coding
Keep the book open alongside the code. When you see a class, find its section.

### To Learn
Work through exercises at the end of each chapter.

### To Review
Use [Appendix A](A_Reference.md) as a quick reference for class diagrams and file locations.

---

## Prerequisites

- Basic C++ (classes, templates, pointers)
- Basic linear algebra (vectors, matrices)
- Visual Studio 2022 or later
- CMake 3.16+

---

## Updates

This is a **living document**. As the engine grows, new chapters will be added:

- [ ] Model Loading
- [ ] Input System
- [ ] Audio
- [ ] Physics
- [ ] Entity Component System
