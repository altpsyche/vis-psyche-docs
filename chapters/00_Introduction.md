\newpage

# VizPsyche Engine: A Technical Journey

## What is VizPsyche?

**VizPsyche** is a 3D rendering engine built from scratch using **C++17** and **OpenGL 4.6**. The name combines "Viz" (visualization) with "Psyche" (the mind/soul)—representing the goal of understanding the soul of graphics programming.

This book takes you from an empty folder to a working engine capable of:

- Rendering textured, lit 3D models
- Loading industry-standard glTF files
- Interactive camera controls
- Real-time debug UI

---

## Why Build an Engine from Scratch?

| Reason | Benefit |
|--------|---------|
| **Deep Understanding** | Using Unity or Unreal hides the fundamentals |
| **Complete Control** | Every line of code is yours to understand and modify |
| **Industry Knowledge** | Game studios value engineers who understand the "how" |
| **Problem Solving** | Debugging becomes easier when you know the internals |

> [!NOTE]
> This book is not about building a production-ready engine. It's about **learning** the concepts that power production engines.

---

## What You'll Build

By the end of this book, you will have built:

```
VizPsyche/
├── VizEngine/                 ← The engine (DLL)
│   ├── src/VizEngine/
│   │   ├── Core/              ← Camera, Mesh, Scene, Model
│   │   ├── OpenGL/            ← Buffer, Shader, Texture wrappers
│   │   └── GUI/               ← ImGui integration
│   ├── vendor/                ← Third-party libraries
│   └── resources/             ← Shaders, textures
├── Sandbox/                   ← Your application (uses the engine)
└── CMakeLists.txt             ← Build system
```

---

## What You'll Learn

### Foundation
- **Build Systems** — CMake project organization
- **DLL Architecture** — Separating engine from application
- **Logging** — Debugging with structured output

### Graphics
- **OpenGL Pipeline** — How pixels get from code to screen
- **Buffers & Shaders** — GPU memory and programs
- **Textures** — Image loading and mapping

### Engine Architecture
- **Transforms** — Position, rotation, scale
- **Camera** — View and projection matrices
- **Scene Management** — Managing multiple objects

### Advanced Topics
- **Lighting** — Blinn-Phong illumination model
- **Model Loading** — glTF format with PBR materials
- **Input** — Keyboard, mouse, camera controls

---

## Prerequisites

Before starting, ensure you have:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| **Windows** | 10 or 11 | – |
| **Visual Studio** | 2022 (17.0+) | Open VS Installer |
| **CMake** | 3.16+ | `cmake --version` |
| **Git** | 2.30+ | `git --version` |

> [!IMPORTANT]
> **Visual Studio Workload Required:** During installation, select **"Desktop development with C++"** workload.

If you're missing any of these, **Chapter 1** walks through installation.

---

## How to Use This Book

### For Those Building Along

Each chapter:
1. Explains the **concepts**
2. Shows **complete, copy-paste ready** code
3. Ends with a **milestone** you can verify
4. Lists **common pitfalls** and solutions

**Build and test after every chapter.** Don't skip ahead—each chapter builds on the previous.

### For Those Reading to Understand

Browse the documentation and reference it when modifying the existing codebase. Use **Appendix A** as a quick lookup for class structures and file locations.

> **Either path is valid.** The book enables; it doesn't demand.

---

## Milestones Overview

| After Part | What Works |
|------------|------------|
| **Part I** (Ch 0–4) | DLL compiles, logging works |
| **Part II** (Ch 5–7) | Window opens, understand OpenGL concepts |
| **Part III** (Ch 8–11) | Textured geometry renders |
| **Part IV** (Ch 12–15) | Multiple objects with ImGui controls |
| **Part V** (Ch 16) | Lit scene with Blinn-Phong shading |
| **Part VI** (Ch 17–19) | glTF models load and display |
| **Part VII** (Ch 20–21) | Fly-camera with WASD + mouse |

---

## Platform Note

> [!CAUTION]
> **This book targets Windows with Visual Studio 2022.** The engine architecture (CMake, OpenGL) supports cross-platform development, but platform-specific code is Windows-only for now. Future appendices may cover Linux and macOS.

---

## Reading Order

Chapters are designed to be read **in order**. Each builds on concepts from the previous:

```
Part I: Getting Started
├── Ch 0: Introduction (you are here)
├── Ch 1: Environment Setup
├── Ch 2: Hello Triangle
├── Ch 3: Project Structure
├── Ch 3b: DLL Architecture
└── Ch 4: Logging System

Part II: OpenGL Foundations
├── Ch 5: Window & Context
├── Ch 6: OpenGL Fundamentals
└── Ch 7: RAII & Resource Management

Part III: GPU Abstractions
├── Ch 8: Buffer Classes
├── Ch 9: Shader System
├── Ch 10: Texture System
└── Ch 11: Renderer Class

Part IV: Engine Architecture
├── Ch 12: Transform & Mesh
├── Ch 13: Camera System
├── Ch 14: Scene Management
└── Ch 15: Dear ImGui

Part V: Lighting
└── Ch 16: Blinn-Phong Lighting

Part VI: Assets
├── Ch 17: glTF Format
├── Ch 18: Model Loader (Geometry)
└── Ch 19: Model Loader (Materials)

Part VII: Input & Controls
├── Ch 20: Input System
└── Ch 21: Camera Controller

Part VIII: Application Lifecycle
├── Ch 22: Engine and Game Loop
└── Ch 23: Sandbox Migration
└── Ch 24: Event System

Appendices
└── A: Code Reference
```

---

## Conventions Used

### Code Blocks

Complete files are shown with the path as a comment:

```cpp
// VizEngine/src/VizEngine/Core.h

#pragma once

#ifdef VP_PLATFORM_WINDOWS
    // ...
#endif
```

### Incremental Changes

When modifying existing files, we show `diff` blocks:

```diff
 set(VIZENGINE_SOURCES
     src/VizEngine/Application.cpp
+    src/VizEngine/Log.cpp           # NEW: Added this chapter
 )
```

### Commands

Terminal commands are shown with the shell prompt:

```bash
cmake -B build -G "Visual Studio 17 2022"
cmake --build build --config Debug
```

### Callouts

> [!NOTE]
> Background information or helpful context.

> [!TIP]
> Performance advice or best practices.

> [!IMPORTANT]
> Critical information you shouldn't skip.

> [!WARNING]
> Potential issues that could cause problems.

> [!CAUTION]
> Dangerous operations that could break things.

---

## Let's Begin

You have everything you need to start. **Chapter 1** ensures your development environment is ready.

> **Next:** [Chapter 1: Environment Setup](01_EnvironmentSetup.md)
