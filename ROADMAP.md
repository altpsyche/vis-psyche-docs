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

At the end of Part VII, the engine contains:

| Layer | Components |
|-------|------------|
| **Core** | Camera, Input, Light, Material, Mesh, Model, Scene, Transform |
| **OpenGL** | Buffers, Shader, Texture, Renderer, GLFWManager |
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
| 2. Advanced OpenGL | OpenGL essentials, PBR, deferred, screen-space | IX–XII | 27–50 | In Progress
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

**Part X: OpenGL Essentials** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 32 | Depth & Stencil Testing | Depth functions, stencil buffer, outlines, mirrors | Planned
| 33 | Blending & Transparency | Alpha blending, sorting, order-independent transparency | Planned
| 34 | Normal Mapping | Tangent space, TBN matrix, surface detail without geometry | Planned
| 35 | Instancing | GPU instancing, instance buffers, rendering many objects | Planned

> **Why These Topics?** These foundational OpenGL techniques are prerequisites for production rendering. Stencil testing enables mirrors and outlines. Blending is essential for particles and UI. Normal mapping adds surface detail. Instancing is critical for performance.

**Part XI: Physically Based Rendering** In Progress

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 36 | PBR Theory | Energy conservation, microfacets | Complete
| 37 | PBR Implementation | Cook-Torrance, metallic-roughness | Complete
| 38 | Image-Based Lighting | Irradiance, prefiltered environment | Complete
| 39 | HDR Pipeline | Floating-point framebuffers, exposure, tone mapping | Complete
| 40 | Bloom | Bright pass, Gaussian blur, composite | Complete
| 41 | Color Grading | 3D LUT, parametric controls, saturation/contrast | Complete
| 42 | Material System | Material abstraction, parameter binding, shader variants | Complete

**Part XII: Deferred Rendering & Screen-Space** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 43 | Deferred Shading | G-buffer, geometry pass, lighting pass, many lights | Planned
| 44 | SSAO | Screen-space ambient occlusion, blur, depth reconstruction | Planned
| 45 | Screen-Space Reflections | Ray marching, hierarchical tracing, fallback to IBL | Planned
| 46 | Reflection Probes | Baked probes, probe blending, parallax correction | Planned

> **Why Deferred Before SSR?** SSR requires a G-buffer with world-space positions and normals. Deferred shading naturally provides this data. SSAO uses the same depth/normal information, making it a natural companion.

**Deliverable**: Production-quality rendering in OpenGL with deferred shading, material abstraction, and advanced screen-space techniques.

> **Transition Point**: Part XII completes the rendering foundation. Deferred shading enables efficient multi-light scenarios and provides the G-buffer infrastructure for screen-space effects. Part XIII introduces ECS to organize game objects using these rendering capabilities.

---

## Phase 3: Engine Systems

**Part XIII: Entity-Component System** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 47 | ECS with EnTT | Entities, components, iteration | Planned
| 48 | Core Components | Transform, MeshRenderer, Camera, Light | Planned
| 49 | Systems Architecture | Render system, scene renderer, hierarchy | Planned

> **Production Features**: The Material System (Ch 42) and Screen-Space Techniques (Ch 43-46) provide the rendering foundation. ECS organizes game objects to use these capabilities efficiently.

**Part XIV: Engine Infrastructure** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 50 | Debug Infrastructure | Conditional compilation (`VP_DEBUG`), debug framebuffers, GPU labels | Planned
| 51 | Resource Management | Asset manager, path resolution, hot-reload, shader caching | Planned
| 52 | Configuration System | Config files (JSON/YAML), quality settings, runtime parameters | Planned
| 53 | Serialization | JSON scene format, save/load, prefabs, component serialization | Planned
| 54 | Threading Fundamentals | Job system, thread-safe containers, async asset loading | Planned
| 55 | Error Handling & Logging | Error policies, log filtering, production builds | Planned

> **Production Features**: Asset Manager with hot-reload enables rapid iteration. Reference-counted resources prevent memory leaks.

**Part XV: Physics** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 56 | Physics World | Jolt setup, simulation loop, debug draw | Planned
| 57 | Collision System | Shapes, layers, filtering, triggers | Planned
| 58 | Queries and Raycasting | Ray/shape queries, object picking | Planned
| 59 | Character Controller | Kinematic body, ground detection, slopes | Planned
| 60 | Physics Debugging | Visualization, profiling, common issues | Planned

**Deliverable**: Complete engine with ECS, serialization, threading, physics.

---

## Phase 4: Modern Graphics

**Part XVI: Understanding Modern APIs** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 61 | GPU Architecture | Queues, command processors, async compute | Planned
| 62 | Vulkan Concepts | Instance, device, queues, command buffers | Planned
| 63 | D3D12 Concepts | Devices, command lists, descriptor heaps | Planned
| 64 | Memory Management | Heaps, allocation strategies, residency | Planned
| 65 | Synchronization | Fences, semaphores, barriers, hazards | Planned
| 66 | Pipeline State | PSOs, root signatures, descriptor sets | Planned

**Part XVII: NVRHI Integration** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 67 | NVRHI Architecture | How it maps to Vulkan/D3D12/OpenGL | Planned
| 68 | Porting Buffers and Textures | Resource creation, views, memory | Planned
| 69 | Shader Compilation | HLSL to SPIR-V, DXC, offline compilation | Planned
| 70 | Shader Permutations | Variants, defines, caching, reflection | Planned
| 71 | Porting Pipelines | Graphics/compute PSOs, binding layouts | Planned

**Part XVIII: Frame Architecture** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 72 | Render Graph Concepts | Frame graphs, resource lifetimes, render passes | Planned
| 73 | Implementing Render Graph | Automatic barriers, resource aliasing, pass ordering | Planned

> **Production Features**: Render Graph automates resource barriers, enables async compute, and optimizes resource memory usage through aliasing.

**Deliverable**: Multi-API renderer with render graph and shader pipeline.

---

## Phase 5: Editor

**Part XIX: Editor Application** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 74 | Editor Architecture | EditorApp, docking, play mode | Planned
| 75 | Scene Hierarchy | Entity tree, selection, parenting | Planned
| 76 | Inspector and Properties | Component editing, add/remove | Planned
| 77 | Viewport and Gizmos | Framebuffer viewport, transform handles | Planned
| 78 | Asset Browser | File browsing, thumbnails, drag-and-drop | Planned
| 79 | Undo System | Command pattern, history, macros | Planned

**Deliverable**: Functional level editor with asset management.

---

## Phase 6: Game Development

**Part XX: Game Systems** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 80 | First-Person Controller | Movement, physics character | Planned
| 81 | Object Interaction | Pick up, inspect, place | Planned
| 82 | Document System | Inspection UI, stamps, decisions | Planned
| 83 | Audio | miniaudio, ambience, 3D sound | Planned
| 84 | Game State | State machine, transitions, persistence | Planned

**Part XXI: Polish and Ship** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 85 | Visual Polish | Particles, atmosphere, tuning | Planned
| 86 | Performance | Profiling, culling, optimization | Planned
| 87 | Distribution | Release builds, packaging | Planned

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
| X | OpenGL Essentials | 32–35 | Planned |
| XI | Physically Based Rendering | 36–42 | In Progress |
| XII | Deferred Rendering & Screen-Space | 43–46 | Planned |
| XIII | Entity-Component System | 47–49 | Planned |
| XIV | Engine Infrastructure | 50–55 | Planned |
| XV | Physics | 56–60 | Planned |
| XVI | Understanding Modern APIs | 61–66 | Planned |
| XVII | NVRHI Integration | 67–71 | Planned |
| XVIII | Frame Architecture | 72–73 | Planned |
| XIX | Editor | 74–79 | Planned |
| XX | Game Systems | 80–84 | Planned |
| XXI | Polish and Ship | 85–87 | Planned |

**Total**: 87 chapters across 21 parts

---

## Architectural Philosophy: Layered Learning

VizPsyche uses a **layered architecture** that maintains educational primitives while adding production features:

```
┌─────────────────────────────────────────────────┐
│  Production Layer (Ch 47+)                      │
│  - SceneRenderer automates multi-pass rendering │
│  - Material System manages shader parameters    │
│  - Asset Manager with hot-reload                │
│  - ECS organizes game objects                   │
└─────────────────────────────────────────────────┘
                     ↓ (uses)
┌─────────────────────────────────────────────────┐
│  Educational Layer (Ch 1-46) - Always Available │
│  - Direct Framebuffer, Shader, Texture access   │
│  - Manual render passes                         │
│  - Raw OpenGL understanding                     │
└─────────────────────────────────────────────────┘
```

### Design Principle: **Opt-In Complexity**

**Chapters 1-46** (Educational):
- Students implement techniques manually (shadow mapping, deferred shading, SSR)
- Direct access to primitives (framebuffers, shaders, textures)
- Understand **how** rendering techniques work

**Chapters 47+** (Production):
- Abstractions automate what was learned manually
- SceneRenderer renders shadows in one line
- Material System replaces manual shader binding
- **Students appreciate automation because they built it first**

### Transition Example:

```cpp
// Educational approach (manual)
void OnRender() {
    // Shadow pass
    m_ShadowFramebuffer->Bind();
    renderer.ClearDepth();
    m_ShadowShader->Bind();
    // ... 20 lines of manual setup ...
    
    // Main pass
    // ... 30 lines of lighting setup ...
}

// Production approach (automatic)
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
| Deferred Shading before SSR | G-buffer provides position/normal data for screen-space effects |
| Dedicated modern API theory | Deep understanding, not just NVRHI usage |
| Separate shader permutations chapter | Complex system affecting entire pipeline |
| Render graph as its own part | Modern architecture, enables async compute |
| Asset browser in editor | Essential for content creation workflow |
| Physics debugging chapter | Real projects need debugging tools |
| **Material System before ECS** | **Bridge manual rendering to component-based architecture** |

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
