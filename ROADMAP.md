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

| Phase | Focus | Parts | Chapters |
|-------|-------|-------|----------|
| 1. Foundation | Engine/Application separation | VIII | 23–25 |
| 2. Advanced OpenGL | Framebuffers, shadows, PBR | IX–X | 26–33 |
| 3. Engine Systems | ECS, serialization, physics | XI–XIII | 34–44 |
| 4. Modern Graphics | Vulkan/D3D12 concepts, NVRHI, render graph | XIV–XVI | 45–57 |
| 5. Editor | Scene editor with tooling | XVII | 58–63 |
| 6. Game Development | Checkpoint puzzle game | XVIII–XIX | 64–71 |

---

## Phase 1: Foundation

**Part VIII: Application Lifecycle**

| Ch | Title | Topics |
|----|-------|--------|
| 23 | Engine and Game Loop | Engine class, main() ownership, game loop |
| 24 | Virtual Lifecycle | Application as abstract, OnCreate/Update/Render |
| 25 | Event System | Dispatcher, window/input events |

**Deliverable**: Engine as library; Sandbox as thin client.

---

## Phase 2: Advanced OpenGL

**Part IX: Advanced Techniques**

| Ch | Title | Topics |
|----|-------|--------|
| 26 | Framebuffers | Render targets, MRT, attachments |
| 27 | Shadow Mapping | Depth from light, PCF, cascades |
| 28 | Cubemaps and Skybox | Environment mapping, reflections |

**Part X: Physically Based Rendering**

| Ch | Title | Topics |
|----|-------|--------|
| 29 | PBR Theory | Energy conservation, microfacets |
| 30 | PBR Implementation | Cook-Torrance, metallic-roughness |
| 31 | Image-Based Lighting | Irradiance, prefiltered environment |
| 32 | HDR Pipeline | Floating-point framebuffers, exposure |
| 33 | Post-Processing | Bloom, tone mapping, color grading |

**Deliverable**: Production-quality rendering in OpenGL.

---

## Phase 3: Engine Systems

**Part XI: Entity-Component System**

| Ch | Title | Topics |
|----|-------|--------|
| 34 | ECS with EnTT | Entities, components, iteration |
| 35 | Core Components | Transform, MeshRenderer, Camera, Light |
| 36 | Systems Architecture | Render system, hierarchy, ordering |

**Part XII: Engine Infrastructure**

| Ch | Title | Topics |
|----|-------|--------|
| 37 | Resource Management | Handles, reference counting, hot-reload |
| 38 | Serialization | JSON scenes, save/load, prefabs |
| 39 | Threading Fundamentals | Job system, thread-safe containers |

**Part XIII: Physics**

| Ch | Title | Topics |
|----|-------|--------|
| 40 | Physics World | Jolt setup, simulation loop, debug draw |
| 41 | Collision System | Shapes, layers, filtering, triggers |
| 42 | Queries and Raycasting | Ray/shape queries, object picking |
| 43 | Character Controller | Kinematic body, ground detection, slopes |
| 44 | Physics Debugging | Visualization, profiling, common issues |

**Deliverable**: Complete engine with ECS, serialization, threading, physics.

---

## Phase 4: Modern Graphics

**Part XIV: Understanding Modern APIs**

| Ch | Title | Topics |
|----|-------|--------|
| 45 | GPU Architecture | Queues, command processors, async compute |
| 46 | Vulkan Concepts | Instance, device, queues, command buffers |
| 47 | D3D12 Concepts | Devices, command lists, descriptor heaps |
| 48 | Memory Management | Heaps, allocation strategies, residency |
| 49 | Synchronization | Fences, semaphores, barriers, hazards |
| 50 | Pipeline State | PSOs, root signatures, descriptor sets |

**Part XV: NVRHI Integration**

| Ch | Title | Topics |
|----|-------|--------|
| 51 | NVRHI Architecture | How it maps to Vulkan/D3D12/OpenGL |
| 52 | Porting Buffers and Textures | Resource creation, views, memory |
| 53 | Shader Compilation | HLSL to SPIR-V, DXC, offline compilation |
| 54 | Shader Permutations | Variants, defines, caching, reflection |
| 55 | Porting Pipelines | Graphics/compute PSOs, binding layouts |

**Part XVI: Frame Architecture**

| Ch | Title | Topics |
|----|-------|--------|
| 56 | Render Graph Concepts | Frame graphs, resource lifetimes, passes |
| 57 | Implementing Render Graph | Automatic barriers, resource aliasing |

**Deliverable**: Multi-API renderer with render graph and shader pipeline.

---

## Phase 5: Editor

**Part XVII: Editor Application**

| Ch | Title | Topics |
|----|-------|--------|
| 58 | Editor Architecture | EditorApp, docking, play mode |
| 59 | Scene Hierarchy | Entity tree, selection, parenting |
| 60 | Inspector and Properties | Component editing, add/remove |
| 61 | Viewport and Gizmos | Framebuffer viewport, transform handles |
| 62 | Asset Browser | File browsing, thumbnails, drag-and-drop |
| 63 | Undo System | Command pattern, history, macros |

**Deliverable**: Functional level editor with asset management.

---

## Phase 6: Game Development

**Part XVIII: Game Systems**

| Ch | Title | Topics |
|----|-------|--------|
| 64 | First-Person Controller | Movement, physics character |
| 65 | Object Interaction | Pick up, inspect, place |
| 66 | Document System | Inspection UI, stamps, decisions |
| 67 | Audio | miniaudio, ambience, 3D sound |
| 68 | Game State | State machine, transitions, persistence |

**Part XIX: Polish and Ship**

| Ch | Title | Topics |
|----|-------|--------|
| 69 | Visual Polish | Particles, atmosphere, tuning |
| 70 | Performance | Profiling, culling, optimization |
| 71 | Distribution | Release builds, packaging |

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
| VIII | Application Lifecycle | 23–25 | Next |
| IX | Advanced Techniques | 26–28 | Planned |
| X | Physically Based Rendering | 29–33 | Planned |
| XI | Entity-Component System | 34–36 | Planned |
| XII | Engine Infrastructure | 37–39 | Planned |
| XIII | Physics | 40–44 | Planned |
| XIV | Understanding Modern APIs | 45–50 | Planned |
| XV | NVRHI Integration | 51–55 | Planned |
| XVI | Frame Architecture | 56–57 | Planned |
| XVII | Editor | 58–63 | Planned |
| XVIII | Game Systems | 64–68 | Planned |
| XIX | Polish and Ship | 69–71 | Planned |

**Total**: 71 chapters across 19 parts

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

---

## Future Considerations

- **Scripting**: Lua or C# integration
- **Cross-Platform**: Linux and macOS support
- **Networking**: Multiplayer foundations
- **Ray Tracing**: NVRHI supports DXR and VK_KHR_ray_tracing
- **Mesh Shaders**: Modern geometry pipeline
- **Virtual Texturing**: Large world streaming
