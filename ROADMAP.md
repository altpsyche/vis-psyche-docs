# VizPsyche: Master Roadmap

> **Vision**: Build a game engine, make a game with it, document the journey.

---

## Project Direction

| Aspect | Decision |
|--------|----------|
| **Game** | First-Person Puzzle (Papers Please inspired) |
| **Graphics API** | OpenGL for learning, then NVRHI for multi-API |
| **Libraries** | Production libraries (EnTT, Jolt, miniaudio, NVRHI) |
| **Editor** | Featured but practical |
| **Audience** | Intermediate (assumes C++ and graphics fundamentals) |
| **Learning Goal** | Deep understanding of modern graphics APIs |

---

## Current State

At the end of Part XI, the engine contains:

| Layer | Components |
|-------|------------|
| **Core** | Camera, Input, Light, Material, Mesh, Model, Scene, Transform |
| **OpenGL** | Buffers, Shader, Texture, Renderer, Framebuffer, GLFWManager |
| **Renderer** | PBRMaterial, RenderMaterial, MaterialFactory, Bloom, Skybox |
| **GUI** | UIManager (Dear ImGui) |
| **Assets** | glTF loader (tinygltf), stb_image |

---

## Key Libraries

| Purpose | Library | Part |
|---------|---------|------|
| Entity-Component System | EnTT | XIII |
| Physics | Jolt Physics | XV |
| Graphics Abstraction | NVRHI | XVII |
| Audio | miniaudio | XX |
| Serialization | nlohmann/json | XIV |

---

## The Game: Checkpoint

**Genre**: First-Person Puzzle
**Inspiration**: Papers Please
**Scope**: 5–10 minute experience

**Concept**: The player is a bureaucrat in a surreal 3D checkpoint. Examine documents, inspect objects, interrogate visitors. Make decisions. Face consequences.

---

## Pedagogical Approach

| Stage | API | Purpose |
|-------|-----|---------|
| **Learn** | OpenGL | Concrete, immediate feedback, understand GPU concepts |
| **Understand** | Vulkan/D3D12 theory | Explicit memory, command buffers, synchronization |
| **Abstract** | NVRHI | Production-ready, portable, informed abstraction |

---

## Development Phases

| Phase | Focus | Parts | Chapters | Status |
|-------|-------|-------|----------|--------|
| 1. Foundation | Engine/Application separation | VIII | 23–26 | Complete
| 2. Advanced OpenGL | OpenGL essentials, PBR, multi-path rendering, screen-space | IX–XII | 27–50 | In Progress
| 3. Engine Systems | ECS, serialization, physics | XIII–XV | 51–64 | (Not Started)
| 4. Modern Graphics | Vulkan/D3D12 concepts, NVRHI, render graph | XVI–XVIII | 65–77 | (Not Started)
| 5. Editor | Scene editor with tooling | XIX | 78–83 | (Not Started)
| 6. Game Development | Checkpoint puzzle game | XX–XXI | 84–91 | (Not Started)

---

## Phase 1: Foundation

**Part VIII: Application Lifecycle** Complete

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 23 | Engine and Game Loop | Engine class, main() ownership, game loop, virtual lifecycle | Complete |
| 24 | SandboxMigration | Refactoring Sandbox, Engine subsystems, CreateApplication | Complete |
| 25 | Event System | Dispatcher, window/input events, event callbacks | Complete |
| 26 | Advanced Lifecycle | Event propagation, Handled flag, ImGui event consumption | Complete |

**Deliverable**: Engine as library; Sandbox as thin client.

---

## Phase 2: Advanced OpenGL

**Part IX: Advanced Techniques** Complete

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 27 | Framebuffers | Render targets, MRT, attachments | Complete
| 28 | Advanced Texture Configuration | Filtering, wrap modes, border colors | Complete
| 29 | Shadow Mapping | Depth from light, PCF, cascades | Complete
| 30 | Cubemaps and HDR | Environment mapping, reflections | Complete
| 31 | Skybox Rendering | Environment mapping, reflections | Complete

**Part X: OpenGL Essentials** Complete

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 32 | Depth & Stencil Testing | Depth functions, stencil buffer, outlines, mirrors | Complete
| 33 | Blending & Transparency | Alpha blending, sorting, order-independent transparency | Complete
| 34 | Normal Mapping | Tangent space, TBN matrix, surface detail without geometry | Complete
| 35 | Instancing | GPU instancing, instance buffers, rendering many objects | Complete

> **Why These Topics?** These foundational OpenGL techniques are prerequisites for production rendering. Stencil testing enables mirrors and outlines. Blending is essential for particles and UI. Normal mapping adds surface detail. Instancing is critical for performance.

**Part XI: Physically Based Rendering** Complete

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 36 | PBR Theory | Energy conservation, microfacets | Complete
| 37 | PBR Implementation | Cook-Torrance, metallic-roughness | Complete
| 38 | Image-Based Lighting | Irradiance, prefiltered environment | Complete
| 39 | HDR Pipeline | Floating-point framebuffers, exposure, tone mapping | Complete
| 40 | Bloom | Bright pass, Gaussian blur, composite | Complete
| 41 | Color Grading | 3D LUT, parametric controls, saturation/contrast | Complete
| 42 | Material System | Material abstraction, parameter binding, shader variants | Complete

**Part XII: Multi-Path Rendering & Screen-Space Effects** In Progress

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 43 | Scene Renderer Architecture | SceneRenderer, RenderPath strategy, ShadowPass, PostProcessPipeline | Complete
| 44 | Light Management & SSBOs | Shader Storage Buffer Objects, dynamic light count, std430 layout, instanced shadow depth shader | Planned
| 45 | Depth & Normal Prepass | Multi-pass foundation, early-Z, depth+normal FBO | Planned
| 46 | Forward+ Rendering | Compute shaders, tile-based light culling, memory barriers | Planned
| 47 | Deferred Rendering | G-buffer, MRT, geometry pass, deferred lighting pass | Planned
| 48 | SSAO | Screen-space ambient occlusion, hemisphere sampling, bilateral blur | Planned
| 49 | Screen-Space Reflections | Ray marching, roughness-based blending, IBL fallback | Planned
| 50 | Render Path Comparison | Split-screen comparison, GPU timer queries, performance analysis | Planned

> **Why Scene Renderer First?** Before implementing new rendering techniques (Forward+, Deferred, SSAO, SSR), we extract the monolithic render code from SandboxApp into a composable SceneRenderer with swappable render paths. This architecture (Strategy Pattern) ensures each new technique plugs in cleanly without duplicating pipeline code.

> **Why Three Render Paths?** Each path has distinct strengths: Forward is simple and handles transparency well, Forward+ scales to hundreds of lights via compute shader culling, Deferred provides free depth+normals for screen-space effects. Comparing all three teaches when to use each in production.

**Deliverable**: Production-quality rendering in OpenGL with three swappable render paths, screen-space ambient occlusion, screen-space reflections, and a composable post-processing pipeline.

> **Transition Point**: Part XII completes the rendering foundation. The SceneRenderer architecture with swappable render paths provides the infrastructure for all future rendering features. Part XIII introduces ECS to organize game objects using these rendering capabilities.

---

## Phase 3: Engine Systems

**Part XIII: Entity-Component System** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 51 | ECS with EnTT | Entities, components, iteration | Planned
| 52 | Core Components | Transform, MeshRenderer, Camera, Light | Planned
| 53 | Systems Architecture | Render system, scene renderer, hierarchy | Planned

> **Production Features**: The Material System (Ch 42) and Multi-Path Rendering (Ch 43-50) provide the rendering foundation. ECS organizes game objects to use these capabilities efficiently.

**Part XIV: Engine Infrastructure** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 54 | Debug Infrastructure | Conditional compilation (`VP_DEBUG`), debug framebuffers, GPU labels | Planned
| 55 | Resource Management | Asset manager, path resolution, hot-reload, shader caching | Planned
| 56 | Configuration System | Config files (JSON/YAML), quality settings, runtime parameters | Planned
| 57 | Serialization | JSON scene format, save/load, prefabs, component serialization | Planned
| 58 | Threading Fundamentals | Job system, thread-safe containers, async asset loading | Planned
| 59 | Error Handling & Logging | Error policies, log filtering, production builds | Planned

> **Production Features**: Asset Manager with hot-reload enables rapid iteration. Reference-counted resources prevent memory leaks.

**Part XV: Physics** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 60 | Physics World | Jolt setup, simulation loop, debug draw | Planned
| 61 | Collision System | Shapes, layers, filtering, triggers | Planned
| 62 | Queries and Raycasting | Ray/shape queries, object picking | Planned
| 63 | Character Controller | Kinematic body, ground detection, slopes | Planned
| 64 | Physics Debugging | Visualization, profiling, common issues | Planned

**Deliverable**: Complete engine with ECS, serialization, threading, physics.

---

## Phase 4: Modern Graphics

**Part XVI: Understanding Modern APIs** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 65 | GPU Architecture | Queues, command processors, async compute | Planned
| 66 | Vulkan Concepts | Instance, device, queues, command buffers | Planned
| 67 | D3D12 Concepts | Devices, command lists, descriptor heaps | Planned
| 68 | Memory Management | Heaps, allocation strategies, residency | Planned
| 69 | Synchronization | Fences, semaphores, barriers, hazards | Planned
| 70 | Pipeline State | PSOs, root signatures, descriptor sets | Planned

**Part XVII: NVRHI Integration** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 71 | NVRHI Architecture | How it maps to Vulkan/D3D12/OpenGL | Planned
| 72 | Porting Buffers and Textures | Resource creation, views, memory | Planned
| 73 | Shader Compilation | HLSL to SPIR-V, DXC, offline compilation | Planned
| 74 | Shader Permutations | Variants, defines, caching, reflection | Planned
| 75 | Porting Pipelines | Graphics/compute PSOs, binding layouts | Planned

**Part XVIII: Frame Architecture** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 76 | Render Graph Concepts | Frame graphs, resource lifetimes, render passes | Planned
| 77 | Implementing Render Graph | Automatic barriers, resource aliasing, pass ordering | Planned

> **Production Features**: Render Graph automates resource barriers, enables async compute, and optimizes resource memory usage through aliasing.

**Deliverable**: Multi-API renderer with render graph and shader pipeline.

---

## Phase 5: Editor

**Part XIX: Editor Application** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 78 | Editor Architecture | EditorApp, docking, play mode | Planned
| 79 | Scene Hierarchy | Entity tree, selection, parenting | Planned
| 80 | Inspector and Properties | Component editing, add/remove | Planned
| 81 | Viewport and Gizmos | Framebuffer viewport, transform handles | Planned
| 82 | Asset Browser | File browsing, thumbnails, drag-and-drop | Planned
| 83 | Undo System | Command pattern, history, macros | Planned

**Deliverable**: Functional level editor with asset management.

---

## Phase 6: Game Development

**Part XX: Game Systems** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 84 | First-Person Controller | Movement, physics character | Planned
| 85 | Object Interaction | Pick up, inspect, place | Planned
| 86 | Document System | Inspection UI, stamps, decisions | Planned
| 87 | Audio | miniaudio, ambience, 3D sound | Planned
| 88 | Game State | State machine, transitions, persistence | Planned

**Part XXI: Polish and Ship** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 89 | Visual Polish | Particles, atmosphere, tuning | Planned
| 90 | Performance | Profiling, culling, optimization | Planned
| 91 | Distribution | Release builds, packaging | Planned

**Deliverable**: Complete, polished, multi-API game.

---

## Book Structure

| Part | Title | Chapters | Status |
|------|-------|----------|--------|
| I | Getting Started | 0–5 | Complete |
| II | OpenGL Foundations | 6–8 | Complete |
| III | GPU Abstractions | 9–12 | Complete |
| IV | Engine Architecture | 13–16 | Complete |
| V | Lighting | 17 | Complete |
| VI | Asset Loading | 18–20 | Complete |
| VII | Input and Controls | 21–22 | Complete |
| VIII | Application Lifecycle | 23–26 | Complete |
| IX | Advanced Techniques | 27–31 | Complete |
| X | OpenGL Essentials | 32–35 | Complete |
| XI | Physically Based Rendering | 36–42 | Complete |
| XII | Multi-Path Rendering & Screen-Space Effects | 43–50 | In Progress |
| XIII | Entity-Component System | 51–53 | Planned |
| XIV | Engine Infrastructure | 54–59 | Planned |
| XV | Physics | 60–64 | Planned |
| XVI | Understanding Modern APIs | 65–70 | Planned |
| XVII | NVRHI Integration | 71–75 | Planned |
| XVIII | Frame Architecture | 76–77 | Planned |
| XIX | Editor | 78–83 | Planned |
| XX | Game Systems | 84–88 | Planned |
| XXI | Polish and Ship | 89–91 | Planned |

**Total**: 91 chapters across 21 parts

---

## Architectural Philosophy: Layered Learning

VizPsyche uses a **layered architecture** that maintains educational primitives while adding production features:

```
┌─────────────────────────────────────────────────┐
│  Production Layer (Ch 51+)                      │
│  - ECS organizes game objects                   │
│  - Asset Manager with hot-reload                │
│  - Render Graph automates pass ordering         │
└─────────────────────────────────────────────────┘
                     ↓ (uses)
┌─────────────────────────────────────────────────┐
│  Rendering Layer (Ch 43-50)                     │
│  - SceneRenderer orchestrates multi-pass        │
│  - Swappable render paths (Fwd/Fwd+/Deferred)  │
│  - Screen-space effects (SSAO, SSR)             │
│  - Material System manages shader parameters    │
└─────────────────────────────────────────────────┘
                     ↓ (uses)
┌─────────────────────────────────────────────────┐
│  Educational Layer (Ch 1-42) - Always Available │
│  - Direct Framebuffer, Shader, Texture access   │
│  - Manual render passes                         │
│  - Raw OpenGL understanding                     │
└─────────────────────────────────────────────────┘
```

### Design Principle: **Opt-In Complexity**

**Chapters 1-42** (Educational):
- Students implement techniques manually (shadow mapping, PBR, bloom)
- Direct access to primitives (framebuffers, shaders, textures)
- Understand **how** rendering techniques work

**Chapters 43-50** (Rendering Architecture):
- SceneRenderer automates multi-pass rendering
- Strategy Pattern enables swappable render paths
- Screen-space effects build on depth/normal prepass
- **Students appreciate architecture because they built the manual version first**

**Chapters 51+** (Production):
- ECS organizes game objects with rendering capabilities
- Asset Manager with hot-reload enables rapid iteration
- Render Graph automates resource barriers and pass ordering

### Transition Example:

```cpp
// Educational approach (manual, Chapters 1-42)
void OnRender() {
    // Shadow pass
    m_ShadowFramebuffer->Bind();
    renderer.ClearDepth();
    m_ShadowShader->Bind();
    // ... 20 lines of manual setup ...

    // Main pass
    // ... 30 lines of lighting setup ...
}

// Rendering Architecture (Chapter 43+)
void OnRender() {
    m_SceneRenderer->Render(m_Scene, m_Camera); // ONE LINE!
    // SceneRenderer internally does what you built
}
```

**Key Insight**: Both approaches coexist. Students can bypass SceneRenderer and use raw primitives when needed for custom effects or learning.

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| OpenGL before abstraction | Learn concretely before abstracting |
| OpenGL Essentials before PBR | Depth/stencil, blending, normal mapping are prerequisites |
| Scene Renderer before Deferred | Architecture enables clean render path plug-in |
| Forward+ before Deferred | Compute shaders + tile culling are simpler than full G-buffer |
| Deferred before SSR | G-buffer provides position/normal data for screen-space effects |
| Dedicated modern API theory | Deep understanding, not just NVRHI usage |
| Separate shader permutations chapter | Complex system affecting entire pipeline |
| Render graph as its own part | Modern architecture, enables async compute |
| Asset browser in editor | Essential for content creation workflow |
| Physics debugging chapter | Real projects need debugging tools |
| **Material System before Scene Renderer** | **Bridge manual rendering to composable architecture** |

---

## Also need to work on Cross-platform support
 - Start with the Build System
 - Add cross-platform support for debug break.
 - Etc

## Future Considerations

- **Scripting**: Lua or C# integration
- **Cross-Platform**: Linux and macOS support
- **Networking**: Multiplayer foundations
- **Ray Tracing**: NVRHI supports DXR and VK_KHR_ray_tracing
- **Mesh Shaders**: Modern geometry pipeline
- **Virtual Texturing**: Large world streaming
