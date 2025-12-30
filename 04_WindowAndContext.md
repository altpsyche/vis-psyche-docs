# Chapter 4: Window & Context

Every graphical application needs a window to display in and an OpenGL context to render with. Our `GLFWManager` class wraps GLFW to handle both, plus input handling.

## What is an OpenGL Context?

An **OpenGL context** is like a "connection" to the GPU. All OpenGL state (bound buffers, current shader, etc.) belongs to a context. Without one, OpenGL functions fail.

Think of it like a database connection:
- You can't run SQL without connecting first
- You can't call `glDrawElements()` without a context

GLFW creates both the window AND the context together.

---

## The GLFWManager Class

Here's our wrapper class:

```cpp
class VizEngine_API GLFWManager
{
public:
    GLFWManager(unsigned int width, unsigned int height, const std::string& title);
    ~GLFWManager();

    void ProcessInput();
    bool WindowShouldClose();
    void SwapBuffersAndPollEvents();
    GLFWwindow* GetWindow() const;

private:
    GLFWwindow* m_Window;
    static void FramebufferSizeCallback(GLFWwindow* window, int width, int height);
    static void KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods);
    void Init(unsigned int width, unsigned int height, const std::string& title);
    void Shutdown();
};
```

---

## Initialization: Creating Window and Context

### Step 1: Initialize GLFW

```cpp
if (!glfwInit())
{
    std::cerr << "Failed to initialize GLFW\n";
    exit(EXIT_FAILURE);
}
```

This must be called before any other GLFW function. It sets up the library.

### Step 2: Set Window Hints

Before creating the window, we tell GLFW what kind of OpenGL context we want:

```cpp
// Request OpenGL 4.6
glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);

// Core Profile (no deprecated functions)
glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

// macOS compatibility (not needed on Windows)
#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

// Enable debug context for error messages
glfwWindowHint(GLFW_OPENGL_DEBUG_CONTEXT, GLFW_TRUE);
```

#### Understanding Window Hints

| Hint | Values | Purpose |
|------|--------|---------|
| `CONTEXT_VERSION_MAJOR/MINOR` | 4.6, 3.3, etc. | OpenGL version |
| `OPENGL_PROFILE` | `CORE` / `COMPAT` | Core removes deprecated features |
| `OPENGL_DEBUG_CONTEXT` | `TRUE` / `FALSE` | Enables error callbacks |
| `RESIZABLE` | `TRUE` / `FALSE` | Can user resize window? |
| `DECORATED` | `TRUE` / `FALSE` | Show title bar? |

### Step 3: Create the Window

```cpp
m_Window = glfwCreateWindow(width, height, title.c_str(), NULL, NULL);
if (!m_Window)
{
    std::cerr << "Failed to create GLFW window\n";
    glfwTerminate();
    exit(EXIT_FAILURE);
}
```

The parameters:
- `width, height` - Window size in pixels
- `title` - Window title bar text
- `NULL` (monitor) - Windowed mode (fullscreen if you pass a monitor)
- `NULL` (share) - Context sharing for multi-window apps

### Step 4: Make Context Current

```cpp
glfwMakeContextCurrent(m_Window);
```

This activates the OpenGL context for this thread. A context can only be current in one thread at a time.

### Step 5: Set Up Callbacks

```cpp
glfwSetFramebufferSizeCallback(m_Window, FramebufferSizeCallback);
glfwSetKeyCallback(m_Window, KeyCallback);
```

Callbacks notify us when events happen. We'll cover these next.

---

## Framebuffer Callback: Handling Resize

When the user resizes the window, we need to update the OpenGL viewport:

```cpp
void GLFWManager::FramebufferSizeCallback(GLFWwindow* window, int width, int height)
{
    (void)window;  // Suppress unused parameter warning
    glViewport(0, 0, width, height);
}
```

### Why Framebuffer, Not Window?

On high-DPI displays (Retina, 4K), the framebuffer size differs from window size:

| Display | Window Size | Framebuffer Size |
|---------|-------------|------------------|
| Regular | 800×600 | 800×600 |
| Retina (2x) | 800×600 | 1600×1200 |

OpenGL renders to the **framebuffer**, so we use framebuffer callbacks.

---

## Key Callback: Single Key Events

For events that should trigger once per press (like opening a menu):

```cpp
void GLFWManager::KeyCallback(GLFWwindow* window, int key, int scancode, int action, int mods)
{
    (void)window;
    (void)scancode;
    (void)mods;
    
    if (key == GLFW_KEY_F1 && action == GLFW_PRESS)
    {
        // Toggle help menu
    }
}
```

The `action` parameter tells you what happened:

| Action | Meaning |
|--------|---------|
| `GLFW_PRESS` | Key was just pressed |
| `GLFW_RELEASE` | Key was just released |
| `GLFW_REPEAT` | Key is held (repeat events) |

---

## Input Polling: Continuous Input

For movement and other continuous input, we poll each frame:

```cpp
void GLFWManager::ProcessInput()
{
    if (glfwGetKey(m_Window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
    {
        glfwSetWindowShouldClose(m_Window, true);
    }
}
```

### Polling vs Callbacks

| Polling | Callbacks |
|---------|-----------|
| Check every frame | Called when event happens |
| Good for: movement, held keys | Good for: toggles, single actions |
| `glfwGetKey()` | `glfwSetKeyCallback()` |

### Common Input Checks

```cpp
// Keyboard
if (glfwGetKey(window, GLFW_KEY_W) == GLFW_PRESS)
    moveForward();

// Mouse buttons
if (glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS)
    shoot();

// Mouse position
double xpos, ypos;
glfwGetCursorPos(window, &xpos, &ypos);
```

---

## The Main Loop

Our main loop structure:

```cpp
while (!glfwWindowShouldClose(m_Window))
{
    // 1. Process input
    ProcessInput();
    
    // 2. Update game logic
    Update(deltaTime);
    
    // 3. Render
    Render();
    
    // 4. Swap buffers and poll events
    glfwSwapBuffers(m_Window);
    glfwPollEvents();
}
```

### Double Buffering

`glfwSwapBuffers()` implements **double buffering**:

```
Frame 1: [Draw to Back Buffer] → [Swap] → [Back becomes Front]
Frame 2: [Draw to Back Buffer] → [Swap] → [Back becomes Front]
...
```

We always draw to the "back" buffer (invisible), then swap it with the "front" buffer (visible). This prevents screen tearing.

### Polling Events

`glfwPollEvents()` processes all pending window events:
- Input (keyboard, mouse)
- Window resize, move, close
- Focus gained/lost

Without calling this, the window becomes unresponsive.

---

## Shutdown: Cleanup

```cpp
void GLFWManager::Shutdown()
{
    glfwDestroyWindow(m_Window);
    glfwTerminate();
}
```

- `glfwDestroyWindow()` - Destroys window and its context
- `glfwTerminate()` - Cleans up GLFW completely

Our destructor calls `Shutdown()`, so cleanup is automatic (RAII pattern).

---

## Complete Initialization Sequence

Here's what happens when our application starts:

```
1. GLFWManager constructor called
   └─ Init()
       ├─ glfwInit()                    ← Initialize library
       ├─ glfwWindowHint(...)           ← Configure context
       ├─ glfwCreateWindow(...)         ← Create window + context
       ├─ glfwMakeContextCurrent(...)   ← Activate context
       └─ glfwSet*Callback(...)         ← Register callbacks

2. Application loads GLAD
   └─ gladLoadGLLoader(...)             ← Load OpenGL functions

3. OpenGL is now ready!
   └─ glCreateShader(), etc. now work
```

---

## VSync

Vertical sync synchronizes frame swapping with your monitor's refresh rate:

```cpp
glfwSwapInterval(1);  // Enable VSync (1 = wait for refresh)
glfwSwapInterval(0);  // Disable VSync (swap immediately)
```

| VSync | Pros | Cons |
|-------|------|------|
| On | No tearing, consistent timing | Input lag, capped FPS |
| Off | Lower latency | Tearing, higher GPU usage |

---

## Error Handling

GLFW can report errors via callback:

```cpp
void ErrorCallback(int error, const char* description)
{
    std::cerr << "GLFW Error " << error << ": " << description << std::endl;
}

// In init:
glfwSetErrorCallback(ErrorCallback);
```

Common errors:
- **65543**: Platform error (graphics driver issue)
- **65542**: API unavailable (OpenGL version not supported)

---

## GLFW vs Our Wrapper

Why wrap GLFW instead of using it directly?

| Direct GLFW | GLFWManager |
|-------------|-------------|
| GLFW functions everywhere | Encapsulated in one class |
| Manual init/cleanup | RAII automatic cleanup |
| Exposed `GLFWwindow*` | Implementation detail hidden |
| Harder to change later | Could swap to SDL, etc. |

Our wrapper is thin - we don't hide GLFW completely (we expose `GetWindow()` for ImGui). But it gives us a clean interface.

---

## The `VizEngine_API` Macro

Notice the class declaration:

```cpp
class VizEngine_API GLFWManager { ... }
```

This macro is for DLL export/import. When building VizEngine.dll, it expands to `__declspec(dllexport)`. When using the DLL, it expands to `__declspec(dllimport)`. See [Chapter 2: DLL Architecture](02_DLLArchitecture.md).

---

## Key Takeaways

1. **Context before OpenGL** - Must have active context before calling GL functions
2. **Window hints before creation** - Configure before `glfwCreateWindow()`
3. **Framebuffer != Window size** - Use framebuffer size for high-DPI
4. **Polling vs Callbacks** - Polling for continuous input, callbacks for events
5. **Double buffering** - Draw to back buffer, swap to prevent tearing
6. **RAII cleanup** - Destructor handles `glfwDestroyWindow()` and `glfwTerminate()`

---

## Exercise

1. Modify `GLFWManager` to support fullscreen mode (pass a monitor to `glfwCreateWindow`)
2. Add a callback to print window size whenever it changes
3. Add mouse position callback and log the coordinates
4. Try disabling VSync - do you see any tearing?

---

> **Next:** [Chapter 5: Logging System](05_LoggingSystem.md) - How we track what's happening in the engine.


