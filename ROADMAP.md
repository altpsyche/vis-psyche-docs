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
| Entity-Component System | EnTT | XII |
| Physics | Jolt Physics | XIII |
| Graphics Abstraction | NVRHI | XV |
| Audio | miniaudio | XVII |
| Serialization | nlohmann/json | XIII |

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
| 2. Advanced OpenGL | Framebuffers, shadows, PBR, materials | IX–X | 27–35 | In Progress
| 3. Engine Systems | ECS, serialization, physics | XI–XIII | 36–46 | (Not Started)
| 4. Modern Graphics | Vulkan/D3D12 concepts, NVRHI, render graph | XIV–XVI | 47–59 | (Not Started)
| 5. Editor | Scene editor with tooling | XVII | 60–65 | (Not Started)
| 6. Game Development | Checkpoint puzzle game | XVIII–XIX | 66–73 | (Not Started)

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

**Part IX: Advanced Techniques** In Progress

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 27 | Framebuffers | Render targets, MRT, attachments | Complete
| 28 | Advanced Texture Configuration | Filtering, wrap modes, border colors | Complete
| 29 | Shadow Mapping | Depth from light, PCF, cascades | In Progress
| 30 | Cubemaps and HDR | Environment mapping, reflections | In Progress
| 31 | Skybox Rendering | Environment mapping, reflections | In Progress

**Part X: Physically Based Rendering** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 32 | PBR Theory | Energy conservation, microfacets | (Not Started)
| 33 | PBR Implementation | Cook-Torrance, metallic-roughness | (Not Started)
| 34 | Image-Based Lighting | Irradiance, prefiltered environment | (Not Started)
| 35 | HDR Pipeline | Floating-point framebuffers, exposure | (Not Started)
| 36 | Material System | Material abstraction, parameter binding, shader variants | (Not Started)
| 37 | Post-Processing | Bloom, tone mapping, color grading | (Not Started)

**Deliverable**: Production-quality rendering in OpenGL with material abstraction.

> **Transition Point**: Ch 34 bridges manual rendering (Ch 1-33) to production ECS architecture (Ch 36+). Material System abstracts shader management, preparing for component-based rendering.

---

## Phase 3: Engine Systems

**Part XI: Entity-Component System** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 38 | ECS with EnTT | Entities, components, iteration | (Not Started)
| 39 | Core Components | Transform, MeshRenderer, Camera, Light | (Not Started)
| 40 | Systems Architecture | Render system, scene renderer, hierarchy | (Not Started)

> **Production Features**: Ch 38's Render System automates multi-pass rendering (shadows, post-processing) that was implemented manually in Chapters 28-35.

**Part XII: Engine Infrastructure** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 41 | Debug Infrastructure | Conditional compilation (`VP_DEBUG`), debug framebuffers, GPU labels | (Not Started) |
| 42 | Resource Management | Asset manager, path resolution, hot-reload, shader caching | (Not Started) |
| 43 | Configuration System | Config files (JSON/YAML), quality settings, runtime parameters | (Not Started) |
| 44 | Serialization | JSON scene format, save/load, prefabs, component serialization | (Not Started) |
| 45 | Threading Fundamentals | Job system, thread-safe containers, async asset loading | (Not Started) |
| 46 | Error Handling & Logging | Error policies, log filtering, production builds | (Not Started) |

> **Production Features**: Asset Manager with hot-reload enables rapid iteration. Reference-counted resources prevent memory leaks.

**Part XIII: Physics** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 47 | Physics World | Jolt setup, simulation loop, debug draw | (Not Started)
| 48 | Collision System | Shapes, layers, filtering, triggers | (Not Started)
| 49 | Queries and Raycasting | Ray/shape queries, object picking | (Not Started)
| 50 | Character Controller | Kinematic body, ground detection, slopes | (Not Started)
| 51 | Physics Debugging | Visualization, profiling, common issues | (Not Started)

**Deliverable**: Complete engine with ECS, serialization, threading, physics.

---

## Phase 4: Modern Graphics

**Part XIV: Understanding Modern APIs** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 52 | GPU Architecture | Queues, command processors, async compute | (Not Started)
| 53 | Vulkan Concepts | Instance, device, queues, command buffers | (Not Started)
| 54 | D3D12 Concepts | Devices, command lists, descriptor heaps | (Not Started)
| 55 | Memory Management | Heaps, allocation strategies, residency | (Not Started)
| 56 | Synchronization | Fences, semaphores, barriers, hazards | (Not Started)
| 57 | Pipeline State | PSOs, root signatures, descriptor sets | (Not Started)

**Part XV: NVRHI Integration** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 58 | NVRHI Architecture | How it maps to Vulkan/D3D12/OpenGL | (Not Started)
| 59 | Porting Buffers and Textures | Resource creation, views, memory | (Not Started)
| 60 | Shader Compilation | HLSL to SPIR-V, DXC, offline compilation | (Not Started)
| 61 | Shader Permutations | Variants, defines, caching, reflection | (Not Started)
| 62 | Porting Pipelines | Graphics/compute PSOs, binding layouts | (Not Started)

**Part XVI: Frame Architecture** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 63 | Render Graph Concepts | Frame graphs, resource lifetimes, render passes | (Not Started)
| 64 | Implementing Render Graph | Automatic barriers, resource aliasing, pass ordering | (Not Started)

> **Production Features**: Render Graph automates resource barriers, enables async compute, and optimizes resource memory usage through aliasing.

**Deliverable**: Multi-API renderer with render graph and shader pipeline.

---

## Phase 5: Editor

**Part XVII: Editor Application** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 65 | Editor Architecture | EditorApp, docking, play mode | (Not Started)
| 66 | Scene Hierarchy | Entity tree, selection, parenting | (Not Started)
| 67 | Inspector and Properties | Component editing, add/remove | (Not Started)
| 68 | Viewport and Gizmos | Framebuffer viewport, transform handles | (Not Started)
| 69 | Asset Browser | File browsing, thumbnails, drag-and-drop | (Not Started)
| 70 | Undo System | Command pattern, history, macros | (Not Started)

**Deliverable**: Functional level editor with asset management.

---

## Phase 6: Game Development

**Part XVIII: Game Systems** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 71 | First-Person Controller | Movement, physics character | (Not Started)
| 72 | Object Interaction | Pick up, inspect, place | (Not Started)
| 73 | Document System | Inspection UI, stamps, decisions | (Not Started)
| 74 | Audio | miniaudio, ambience, 3D sound | (Not Started)
| 75 | Game State | State machine, transitions, persistence | (Not Started)

**Part XIX: Polish and Ship** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 76 | Visual Polish | Particles, atmosphere, tuning | (Not Started)
| 77 | Performance | Profiling, culling, optimization | (Not Started)
| 78 | Distribution | Release builds, packaging | (Not Started)

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
| IX | Advanced Techniques | 27–31 | In Progress |
| X | Physically Based Rendering | 32–37 | Planned |
| XI | Entity-Component System | 38–40 | Planned |
| XII | Engine Infrastructure | 41–46 | Planned |
| XIII | Physics | 47–51 | Planned |
| XIV | Understanding Modern APIs | 52–57 | Planned |
| XV | NVRHI Integration | 58–62 | Planned |
| XVI | Frame Architecture | 63–64 | Planned |
| XVII | Editor | 65–69 | Planned |
| XVIII | Game Systems | 70–74 | Planned |
| XIX | Polish and Ship | 75–77 | Planned |

**Total**: 78 chapters across 19 parts

---

## Architectural Philosophy: Layered Learning

VizPsyche uses a **layered architecture** that maintains educational primitives while adding production features:

```
┌─────────────────────────────────────────────────┐
│  Production Layer (Ch 36+)                      │
│  - SceneRenderer automates multi-pass rendering │
│  - Material System manages shader parameters    │
│  - Asset Manager with hot-reload                │
│  - ECS organizes game objects                   │
└─────────────────────────────────────────────────┘
                     ↓ (uses)
┌─────────────────────────────────────────────────┐
│  Educational Layer (Ch 1-35) - Always Available │
│  - Direct Framebuffer, Shader, Texture access   │
│  - Manual render passes                         │
│  - Raw OpenGL understanding                     │
└─────────────────────────────────────────────────┘
```

### Design Principle: **Opt-In Complexity**

**Chapters 1-36** (Educational):
- Students implement techniques manually (shadow mapping, post-processing)
- Direct access to primitives (framebuffers, shaders, textures)
- Understand **how** rendering techniques work

**Chapters 37+** (Production):
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
