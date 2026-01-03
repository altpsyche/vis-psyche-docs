# VizPsyche: Master Roadmap

> **Vision**: Build a game engine, make a game with it, document the journey.

---

## Project Direction

| Aspect | Decision |
|--------|----------|
| **Game** | First-Person Puzzle (Papers Please inspired) |
| **Graphics API** | NVRHI (Vulkan, D3D12, OpenGL backends) |
| **Libraries** | Production libraries (EnTT, Jolt, miniaudio, NVRHI) |
| **Editor** | Featured but practical |
| **Audience** | Intermediate (assumes C++ and graphics fundamentals) |

---

## Current State

At the end of Part VII, the engine contains:

| Layer | Components |
|-------|------------|
| **Core** | Camera, Input, Light, Material, Mesh, Model, Scene, Transform |
| **OpenGL** | Buffers, Shader, Texture, Renderer, GLFWManager |
| **GUI** | UIManager (Dear ImGui) |
| **Assets** | glTF loader (tinygltf), stb_image |

**Problem**: All logic resides in a 377-line `Application::Run()` method.

**Goal**: Clean architecture supporting both Editor and Game applications.

---

## Key Libraries

| Purpose | Library | Part |
|---------|---------|------|
| Graphics Abstraction | NVRHI | IX |
| Entity-Component System | EnTT | XIII |
| Physics | Jolt Physics | XIV |
| Audio | miniaudio | XVI |
| Serialization | nlohmann/json | XIV |

---

## The Game: Checkpoint

**Genre**: First-Person Puzzle

**Inspiration**: Papers Please

**Concept**: The player is a bureaucrat in a surreal 3D checkpoint. Examine documents, inspect objects, interrogate visitors. Make decisions. Face consequences.

**Scope**: 5–10 minute experience

**Required Systems**:

- Object interaction (pick up, inspect, place)
- Document inspection UI
- Decision and consequence logic
- Atmospheric rendering (lighting, audio, post-processing)

---

## Development Phases

The book is organized into six phases spanning seventeen parts.

| Phase | Focus | Parts | Chapters |
|-------|-------|-------|----------|
| 1. Foundation | Engine/Application separation | VIII | 23–25 |
| 2. Graphics Abstraction | NVRHI, shader pipeline, render graph | IX–X | 26–33 |
| 3. Advanced Rendering | Shadows, PBR, HDR, post-processing | XI–XII | 34–40 |
| 4. Engine Systems | ECS, serialization, physics, threading | XIII–XIV | 41–49 |
| 5. Editor | Scene editor with tooling | XV | 50–54 |
| 6. Game Development | Checkpoint puzzle game | XVI–XVII | 55–62 |

---

## Phase 1: Foundation

**Part VIII: Application Lifecycle**

| Chapter | Title | Topics |
|---------|-------|--------|
| 23 | Application Lifecycle | Engine owns main(), virtual OnInit/OnUpdate/OnRender/OnShutdown |
| 24 | Engine Subsystems | Window, Renderer, Input as engine-owned modules |
| 25 | Event System | Event dispatcher, window and input events |

**Deliverable**: Engine as library; Sandbox as thin client.

---

## Phase 2: Graphics Abstraction

**Part IX: Render Hardware Interface**

| Chapter | Title | Topics |
|---------|-------|--------|
| 26 | Why Abstract | Motivation, API differences, NVRHI architecture |
| 27 | Device and Swapchain | Device creation, surface management, present modes |
| 28 | Command Lists | Recording, submission, synchronization |
| 29 | Buffers and Textures | NVRHI buffer/texture creation, memory management |
| 30 | Pipeline State | Graphics pipelines, input layouts, blend/depth state |

**Part X: Shader and Frame Management**

| Chapter | Title | Topics |
|---------|-------|--------|
| 31 | Shader Compilation | HLSL to SPIR-V, offline compilation, reflection |
| 32 | Shader Permutations | Variants, includes, defines, caching |
| 33 | Render Graph Basics | Frame graph concepts, resource transitions, barriers |

**Deliverable**: Portable renderer with Vulkan, D3D12, and OpenGL backends.

---

## Phase 3: Advanced Rendering

**Part XI: Rendering Techniques**

| Chapter | Title | Topics |
|---------|-------|--------|
| 34 | Framebuffers and MRT | Render targets, multiple outputs, depth/stencil |
| 35 | Shadow Mapping | Shadow maps, PCF filtering, cascaded shadows |
| 36 | Cubemaps and Skybox | Cubemap textures, environment mapping |

**Part XII: Physically Based Rendering**

| Chapter | Title | Topics |
|---------|-------|--------|
| 37 | PBR Fundamentals | Metallic-roughness, Cook-Torrance BRDF |
| 38 | Image-Based Lighting | Environment probes, irradiance, prefiltered maps |
| 39 | HDR Pipeline | High dynamic range, exposure, tone mapping |
| 40 | Post-Processing | Bloom, color grading, film effects |

**Deliverable**: Production-quality visuals with PBR, shadows, HDR, and post-processing.

---

## Phase 4: Engine Systems

**Part XIII: Entity-Component System**

| Chapter | Title | Topics |
|---------|-------|--------|
| 41 | ECS with EnTT | Integration, entities, components, iteration |
| 42 | Core Components | Transform, MeshRenderer, Camera, Light |
| 43 | Systems Architecture | Render system, transform hierarchy, ordering |
| 44 | Threading Fundamentals | Job system, task graphs, thread-safe containers |

**Part XIV: Engine Infrastructure**

| Chapter | Title | Topics |
|---------|-------|--------|
| 45 | Resource Management | Asset handles, reference counting, hot-reload |
| 46 | Serialization | JSON scene format, save/load, prefabs |
| 47 | Physics World | Jolt initialization, simulation stepping, debug draw |
| 48 | Collision and Queries | Shapes, layers, filtering, triggers |
| 49 | Raycasting and Picking | Ray queries, object selection, interaction |

**Deliverable**: Complete engine with ECS, serialization, physics, and threading.

---

## Phase 5: Editor

**Part XV: Editor Application**

| Chapter | Title | Topics |
|---------|-------|--------|
| 50 | Editor Architecture | EditorApp vs RuntimeApp, docking layout |
| 51 | Scene Hierarchy | Entity tree view, selection, parenting |
| 52 | Inspector Panel | Component properties, add/remove components |
| 53 | Viewport and Gizmos | Framebuffer viewport, transform gizmos, picking |
| 54 | Undo System | Command pattern, history stack, macro commands |

**Deliverable**: Functional level editor for scene authoring.

---

## Phase 6: Game Development

**Part XVI: Game Systems**

| Chapter | Title | Topics |
|---------|-------|--------|
| 55 | First-Person Controller | Mouse look, movement, physics character |
| 56 | Object Interaction | Pick up, inspect, place; hand system |
| 57 | Document System | Inspection UI, stamps, approval/rejection |
| 58 | Audio with miniaudio | Ambience, sound effects, 3D positional audio |
| 59 | Game State | State machine, scene transitions, save/load |

**Part XVII: Polish and Ship**

| Chapter | Title | Topics |
|---------|-------|--------|
| 60 | Visual Polish | Particles, atmosphere, post-processing tuning |
| 61 | Performance | Profiling, culling, batching, optimization |
| 62 | Distribution | Release builds, asset packaging, installer |

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
| IX | Render Hardware Interface | 26–30 | Planned |
| X | Shader and Frame Management | 31–33 | Planned |
| XI | Rendering Techniques | 34–36 | Planned |
| XII | Physically Based Rendering | 37–40 | Planned |
| XIII | Entity-Component System | 41–44 | Planned |
| XIV | Engine Infrastructure | 45–49 | Planned |
| XV | Editor | 50–54 | Planned |
| XVI | Game Systems | 55–59 | Planned |
| XVII | Polish and Ship | 60–62 | Planned |

**Total**: 62 chapters across 17 parts

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| NVRHI before rendering | All rendering code written once, portable from start |
| Shader compilation chapter | Non-trivial system affecting entire renderer |
| Render graph included | Modern pattern, teaches resource management |
| Physics split into 3 chapters | World setup, collision, queries each deserve coverage |
| Threading in ECS section | Natural fit with systems architecture |
| Undo as separate chapter | Command pattern is significant architecture |

---

## Future Considerations

Topics for appendices or follow-up material:

- **Scripting**: Lua or C# integration
- **Cross-Platform**: Linux and macOS support
- **Networking**: Multiplayer foundations
- **Ray Tracing**: NVRHI supports DXR and VK_KHR_ray_tracing
- **Asset Pipeline**: Offline processing, compression, streaming
