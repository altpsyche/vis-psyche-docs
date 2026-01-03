\newpage

# VizPsyche Engine Technical Book

A hands-on guide to building a 3D rendering engine from scratch.

## Table of Contents

### Part 1: Foundation
1. **[Introduction](00_Introduction.md)** - What we're building and why
2. **[Build System](01_BuildSystem.md)** - CMake, project structure, building
3. **[DLL Architecture](02_DLLArchitecture.md)** - Exports, namespaces, entry points
4. **[Third-Party Libraries](03_ThirdPartyLibraries.md)** - GLFW, GLAD, GLM, ImGui, spdlog, stb_image, tinygltf

### Part 2: Infrastructure
5. **[Logging System](04_LoggingSystem.md)** - spdlog wrapper, log levels, macros
6. **[Window & Context](05_WindowAndContext.md)** - GLFWManager, OpenGL context, input

### Part 3: C++ Patterns
7. **[RAII & Resource Management](07_RAIIAndResourceManagement.md)** - Constructor/destructor patterns, Rule of 5

### Part 4: OpenGL Wrappers
8. **[Buffer Classes](08_BufferClasses.md)** - VertexBuffer, IndexBuffer, VertexArray, Layout
9. **[Shader & Renderer](09_ShaderAndRenderer.md)** - Shader parsing, uniforms, draw calls
10. **[Textures](10_Textures.md)** - Image loading, GPU textures, UV mapping

### Part 5: Editor
11. **[Dear ImGui](11_DearImGui.md)** - Immediate mode GUI, widgets, UIManager wrapper

### Part 6: Engine Architecture
12. **[Transform & Mesh](12_TransformAndMesh.md)** - Position, rotation, scale, geometry factories
13. **[Camera System](13_CameraSystem.md)** - View/projection matrices, camera movement
14. **[Scene Management](14_SceneManagement.md)** - SceneObject, shared resources, object selection

### Part 7: Graphics II
15. **[Lighting](15_Lighting.md)** - Blinn-Phong model, normals, directional lights

### Part 8: Assets
16. **[Model Loading](16_ModelLoading.md)** - glTF format, tinygltf, PBR materials

### Part 9: Input
17. **[Input System](17_InputSystem.md)** - Keyboard, mouse, polling vs events, edge detection
18. **[Camera Controller](18_CameraController.md)** - WASD movement, mouse look, scroll zoom

### Part 10: Graphics III *(planned)*
19. **[Advanced OpenGL](19_AdvancedOpenGL.md)** - Framebuffers, depth/stencil, cubemaps
20. **[Advanced Lighting](20_AdvancedLighting.md)** - Shadows, PBR, HDR, bloom

### Part 11: Engine II *(planned)*
21. **[Entity Component System](21_ECS.md)** - Components, systems, queries

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
04 Logging System ←── Track what's happening
      ↓
05 Window & Context ←── Create window, OpenGL context
      ↓
06 OpenGL Fundamentals ←── Understand graphics basics
      ↓
07 RAII & Resource Management ←── C++ resource patterns
      ↓
08 Buffer Classes ←── Apply RAII to OpenGL
      ↓
09 Shader & Renderer ←── Compile shaders, centralize drawing
      ↓
10 Textures ←── Add images to geometry
      ↓
11 Dear ImGui ←── Debug UI for development
      ↓
12 Transform & Mesh ←── Geometry and positioning
      ↓
13 Camera System ←── View the 3D world
      ↓
14 Scene Management ←── Manage multiple objects
      ↓
15 Lighting ←── Make it look 3D
      ↓
16 Model Loading ←── Load external 3D models
      ↓
17 Input System ←── Handle user interaction
      ↓
18 Camera Controller ←── WASD movement, mouse look
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

- [x] Model Loading
- [x] Dear ImGui
- [x] Input System
- [x] Camera Controller
- [ ] Advanced OpenGL *(next)*
- [ ] Advanced Lighting
- [ ] Editor II (UI Framework)
- [ ] Entity Component System
- [ ] Animation
- [ ] Physics
- [ ] Audio

