# VizPsyche Book - Image Catalog

This document lists all diagrams that should be created as proper vector graphics using tools like **Excalidraw** or **draw.io**.

**Recommended Tools:**
- [Excalidraw](https://excalidraw.com) - Hand-drawn style (great for conceptual diagrams)
- [draw.io](https://app.diagrams.net) - Clean professional style (great for architecture)

**Export Settings:**
- Format: SVG (preferred) or PNG
- Background: Transparent or white
- Resolution: 2x for PNG

---

## Chapter 03: Third-Party Libraries

### `03-library-stack.svg`
**Description:** Stack diagram showing all libraries and their relationships  
**Style:** draw.io (layered boxes)  
**Content:**
```
┌─────────────────────────────────────────┐
│           VizEngine Application          │
├─────────────────────────────────────────┤
│  OpenGL Abstractions  │  GUI (ImGui)    │
├───────────────────────┼─────────────────┤
│  GLFW    │  GLAD     │  GLM  │ spdlog  │
├──────────┴───────────┴───────┴─────────┤
│              stb_image                   │
└─────────────────────────────────────────┘
```

---

## Chapter 04: Window & Context

### `04-initialization-sequence.svg`
**Description:** Flowchart of GLFW/OpenGL initialization sequence  
**Style:** Excalidraw (flowchart)  
**Content:**
```
glfwInit() → Window Hints → glfwCreateWindow() → glfwMakeContextCurrent() → gladLoadGL() → Ready!
```

### `04-double-buffering.svg`
**Description:** Animation/diagram showing front and back buffer swap  
**Style:** Excalidraw  
**Content:** Two rectangles (Front/Back buffer) with swap arrows

---

## Chapter 06: OpenGL Fundamentals

### `06-graphics-pipeline.svg`
**Description:** The OpenGL graphics pipeline stages  
**Style:** draw.io (horizontal flow)  
**Content:**
```
[Vertex Data] → [Vertex Shader] → [Rasterization] → [Fragment Shader] → [Screen]
```

### `06-coordinate-systems.svg`
**Description:** Object → World → View → Clip → Screen space transformation  
**Style:** Excalidraw  
**Content:** Show a cube being transformed through each coordinate system

### `06-vertex-buffer-layout.svg`
**Description:** How vertex data is laid out in memory (Position, Color, TexCoord)  
**Style:** draw.io  
**Content:** Memory layout with byte offsets marked

---

## Chapter 07: Abstractions

### `07-raii-lifecycle.svg`
**Description:** Constructor acquires resource, destructor releases  
**Style:** Excalidraw (timeline)  
**Content:**
```
Constructor ──────────────► Use ──────────────► Destructor
   │                                                │
   └── glGenBuffers()                   glDeleteBuffers() ──┘
```

### `07-rule-of-5.svg`
**Description:** The 5 special member functions for resource management  
**Style:** draw.io (table/diagram)  

---

## Chapter 08: Textures

### `08-uv-coordinates.svg`
**Description:** UV coordinate system with (0,0) at bottom-left  
**Style:** Excalidraw  
**Content:** 2D grid with U and V axes, sample texture mapped

### `08-texture-filtering.svg`
**Description:** GL_NEAREST vs GL_LINEAR comparison  
**Style:** Excalidraw  
**Content:** Side-by-side pixelated vs smooth texture

### `08-texture-wrapping.svg`
**Description:** GL_REPEAT, GL_MIRRORED_REPEAT, GL_CLAMP_TO_EDGE  
**Style:** Excalidraw  
**Content:** Three examples of same texture with different wrap modes

---

## Chapter 09: Engine Architecture

### `09-architecture-overview.svg`
**Description:** High-level engine component diagram  
**Style:** draw.io (architecture)  
**Content:**
```
Application
    ├── Window (GLFW)
    ├── Renderer
    ├── Camera
    ├── Scene
    │   └── Entities (Mesh + Transform)
    └── Assets (Shaders, Textures)
```

### `09-transform-order.svg`
**Description:** Scale → Rotate → Translate order visualization  
**Style:** Excalidraw  
**Content:** Show a cube going through S→R→T transformations

### `09-game-loop.svg`
**Description:** Input → Update → Render loop  
**Style:** Excalidraw (circular flow)  
**Content:**
```
    ┌──────────────┐
    │ ProcessInput │
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │    Update    │
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │    Render    │
    └──────┬───────┘
           │
           └──────────► (loop back)
```

---

## Chapter 10: Multiple Objects & Scene

### `10-shared-mesh-diagram.svg` ⭐ HIGH PRIORITY
**Description:** How multiple SceneObjects share a single Mesh via shared_ptr  
**Style:** draw.io  
**Content:**
```
┌────────────────────────────────────────────────┐
│                    Scene                        │
│  ┌─────────────┐  ┌─────────────┐              │
│  │ SceneObject │  │ SceneObject │              │
│  │ Transform A │  │ Transform B │              │
│  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼─────────────────────┘
          │ shared_ptr     │ shared_ptr
          └───────┬────────┘
                  ▼
            ┌───────────┐
            │   Mesh    │
            │ (shared)  │
            └───────────┘
```

### `10-ecs-comparison.svg` ⭐ HIGH PRIORITY
**Description:** Our approach vs ECS approach comparison  
**Style:** draw.io (side-by-side)  
**Content:** Left side shows SceneObject with all fields, right shows Entity with components

---

## Chapter 11: Lighting ⭐ HIGHEST PRIORITY

### `11-flat-vs-lit.svg`
**Description:** Before/after comparison - flat colored cube vs lit cube  
**Style:** Excalidraw  
**Content:** Two cubes side by side, one flat, one with shading

### `11-blinn-phong-components.svg` ⭐ HIGH PRIORITY
**Description:** Ambient + Diffuse + Specular = Final color  
**Style:** Excalidraw  
**Content:**
```
[Ambient]  +  [Diffuse]  +  [Specular]  =  [Final]
 (constant)   (angle-based)  (highlight)    (combined)
```

### `11-lambert-cosine.svg`
**Description:** Lambert's cosine law - surface angle affects brightness  
**Style:** Excalidraw  
**Content:** Light hitting surface at different angles, showing brightness difference

### `11-half-vector.svg` ⭐ HIGH PRIORITY
**Description:** Blinn-Phong half vector between Light and View  
**Style:** Excalidraw  
**Content:**
```
        Light       View
          ↓         ↑
           \       /
            \  H  /    ← Half vector
             \ ↑ /
    ──────────●──────────  Surface
```

### `11-normals-explained.svg`
**Description:** Surface normals pointing perpendicular to faces  
**Style:** Excalidraw  
**Content:** A cube with normal vectors drawn on each face

### `11-flat-vs-smooth-shading.svg`
**Description:** Flat shading (per-face normals) vs smooth shading (averaged normals)  
**Style:** Excalidraw  
**Content:** Two spheres showing the difference

---

## Appendix A: Code Reference

### `A-class-diagram.svg`
**Description:** Full class diagram of VizEngine  
**Style:** draw.io (UML)  
**Content:** All major classes with inheritance and relationships

### `A-memory-ownership.svg`
**Description:** Who owns what - ownership diagram  
**Style:** draw.io  

---

## README

### `00-reading-order.svg`
**Description:** Chapter dependency/reading order flowchart  
**Style:** draw.io (vertical flow)  
**Content:** Chapters 00→01→02→...→11 with arrows and descriptions

---

## Priority Order

1. **HIGH** - `11-blinn-phong-components.svg` (Most complex, most impactful)
2. **HIGH** - `11-half-vector.svg` (Key concept)
3. **HIGH** - `10-shared-mesh-diagram.svg` (Architecture understanding)
4. **HIGH** - `06-graphics-pipeline.svg` (Fundamental concept)
5. **MEDIUM** - `09-architecture-overview.svg`
6. **MEDIUM** - `08-uv-coordinates.svg`
7. **MEDIUM** - `11-lambert-cosine.svg`
8. **LOW** - Others as time permits

---

## Usage in Markdown

Once images are created, replace ASCII art with:

```markdown
![Blinn-Phong Components](images/11-blinn-phong-components.svg)
```

Or with sizing:

```markdown
<img src="images/11-blinn-phong-components.svg" alt="Blinn-Phong Components" width="600">
```

