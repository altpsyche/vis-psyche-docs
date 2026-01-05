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
| 28 | Shadow Mapping | Depth from light, PCF, cascades | In Progress
| 29 | Cubemaps and Skybox | Environment mapping, reflections | (Not Started)

**Part X: Physically Based Rendering** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 30 | PBR Theory | Energy conservation, microfacets | (Not Started)
| 31 | PBR Implementation | Cook-Torrance, metallic-roughness | (Not Started)
| 32 | Image-Based Lighting | Irradiance, prefiltered environment | (Not Started)
| 33 | HDR Pipeline | Floating-point framebuffers, exposure | (Not Started)
| 34 | Material System | Material abstraction, parameter binding, shader variants | (Not Started)
| 35 | Post-Processing | Bloom, tone mapping, color grading | (Not Started)

**Deliverable**: Production-quality rendering in OpenGL with material abstraction.

> **Transition Point**: Ch 34 bridges manual rendering (Ch 1-33) to production ECS architecture (Ch 36+). Material System abstracts shader management, preparing for component-based rendering.

---

## Phase 3: Engine Systems

**Part XI: Entity-Component System** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 36 | ECS with EnTT | Entities, components, iteration | (Not Started)
| 37 | Core Components | Transform, MeshRenderer, Camera, Light | (Not Started)
| 38 | Systems Architecture | Render system, scene renderer, hierarchy | (Not Started)

> **Production Features**: Ch 38's Render System automates multi-pass rendering (shadows, post-processing) that was implemented manually in Chapters 28-35.

**Part XII: Engine Infrastructure** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 39 | Resource Management | Asset manager, handles, hot-reload, caching | (Not Started)
| 40 | Serialization | JSON scenes, save/load, prefabs | (Not Started)
| 41 | Threading Fundamentals | Job system, thread-safe containers | (Not Started)

> **Production Features**: Ch 39's Asset Manager with hot-reload enables rapid iteration. Reference-counted resources prevent memory leaks.

**Part XIII: Physics** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 42 | Physics World | Jolt setup, simulation loop, debug draw | (Not Started)
| 43 | Collision System | Shapes, layers, filtering, triggers | (Not Started)
| 44 | Queries and Raycasting | Ray/shape queries, object picking | (Not Started)
| 45 | Character Controller | Kinematic body, ground detection, slopes | (Not Started)
| 46 | Physics Debugging | Visualization, profiling, common issues | (Not Started)

**Deliverable**: Complete engine with ECS, serialization, threading, physics.

---

## Phase 4: Modern Graphics

**Part XIV: Understanding Modern APIs** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 47 | GPU Architecture | Queues, command processors, async compute | (Not Started)
| 48 | Vulkan Concepts | Instance, device, queues, command buffers | (Not Started)
| 49 | D3D12 Concepts | Devices, command lists, descriptor heaps | (Not Started)
| 50 | Memory Management | Heaps, allocation strategies, residency | (Not Started)
| 51 | Synchronization | Fences, semaphores, barriers, hazards | (Not Started)
| 52 | Pipeline State | PSOs, root signatures, descriptor sets | (Not Started)

**Part XV: NVRHI Integration** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 53 | NVRHI Architecture | How it maps to Vulkan/D3D12/OpenGL | (Not Started)
| 54 | Porting Buffers and Textures | Resource creation, views, memory | (Not Started)
| 55 | Shader Compilation | HLSL to SPIR-V, DXC, offline compilation | (Not Started)
| 56 | Shader Permutations | Variants, defines, caching, reflection | (Not Started)
| 57 | Porting Pipelines | Graphics/compute PSOs, binding layouts | (Not Started)

**Part XVI: Frame Architecture** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 58 | Render Graph Concepts | Frame graphs, resource lifetimes, render passes | (Not Started)
| 59 | Implementing Render Graph | Automatic barriers, resource aliasing, pass ordering | (Not Started)

> **Production Features**: Render Graph automates resource barriers, enables async compute, and optimizes resource memory usage through aliasing.

**Deliverable**: Multi-API renderer with render graph and shader pipeline.

---

## Phase 5: Editor

**Part XVII: Editor Application** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 60 | Editor Architecture | EditorApp, docking, play mode | (Not Started)
| 61 | Scene Hierarchy | Entity tree, selection, parenting | (Not Started)
| 62 | Inspector and Properties | Component editing, add/remove | (Not Started)
| 63 | Viewport and Gizmos | Framebuffer viewport, transform handles | (Not Started)
| 64 | Asset Browser | File browsing, thumbnails, drag-and-drop | (Not Started)
| 65 | Undo System | Command pattern, history, macros | (Not Started)

**Deliverable**: Functional level editor with asset management.

---

## Phase 6: Game Development

**Part XVIII: Game Systems** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 66 | First-Person Controller | Movement, physics character | (Not Started)
| 67 | Object Interaction | Pick up, inspect, place | (Not Started)
| 68 | Document System | Inspection UI, stamps, decisions | (Not Started)
| 69 | Audio | miniaudio, ambience, 3D sound | (Not Started)
| 70 | Game State | State machine, transitions, persistence | (Not Started)

**Part XIX: Polish and Ship** (Not Started)

| Ch | Title | Topics | Status |
|----|-------|--------|--------|
| 71 | Visual Polish | Particles, atmosphere, tuning | (Not Started)
| 72 | Performance | Profiling, culling, optimization | (Not Started)
| 73 | Distribution | Release builds, packaging | (Not Started)

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
| IX | Advanced Techniques | 27–29 | In Progress |
| X | Physically Based Rendering | 30–35 | Planned |
| XI | Entity-Component System | 36–38 | Planned |
| XII | Engine Infrastructure | 39–41 | Planned |
| XIII | Physics | 42–46 | Planned |
| XIV | Understanding Modern APIs | 47–52 | Planned |
| XV | NVRHI Integration | 53–57 | Planned |
| XVI | Frame Architecture | 58–59 | Planned |
| XVII | Editor | 60–65 | Planned |
| XVIII | Game Systems | 66–70 | Planned |
| XIX | Polish and Ship | 71–73 | Planned |

**Total**: 73 chapters across 19 parts

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

**Chapters 1-35** (Educational):
- Students implement techniques manually (shadow mapping, post-processing)
- Direct access to primitives (framebuffers, shaders, textures)
- Understand **how** rendering techniques work

**Chapters 36+** (Production):
- Abstractions automate what was learned manually
- SceneRenderer renders shadows in one line (Ch 38)
- Material System replaces manual shader binding (Ch 34)
- **Students appreciate automation because they built it first**

### Transition Example:

```cpp
// Chapter 28-33: Educational approach (manual)
void OnRender() {
    // Shadow pass
    m_ShadowFramebuffer->Bind();
    renderer.ClearDepth();
    m_ShadowShader->Bind();
    // ... 20 lines of manual setup ...
    
    // Main pass
    // ... 30 lines of lighting setup ...
}

// Chapter 38: Production approach (automatic)
void OnRender() {
    m_SceneRenderer->Render(m_Scene, m_Camera); // ONE LINE!
    // SceneRenderer internally does what you built in Ch 28-33
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
