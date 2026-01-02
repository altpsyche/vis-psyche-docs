\newpage

# Chapter 9: Editor I - Dear ImGui

## Why GUI in an Engine?

A game engine isn't just a renderer - it's a development tool. You need ways to:

- **Tweak parameters** - Adjust lighting, speeds, colors without recompiling
- **Debug state** - See object positions, camera angles, performance data
- **Build levels** - Place objects, configure scenes, test gameplay

This is where **Dear ImGui** shines. It's a lightweight, programmer-friendly GUI library designed for exactly this use case.

---

## What is Dear ImGui?

**Dear ImGui** (officially spelled "Dear ImGui", often just "ImGui") is an **immediate mode** GUI library by Omar Cornut. It's become the de-facto standard for debug/tool UI in game engines.

### Immediate Mode vs Retained Mode

This is the key concept to understand:

| Retained Mode (Qt, WPF, WinForms) | Immediate Mode (ImGui) |
|-----------------------------------|------------------------|
| Create widget objects once | Describe UI every frame |
| Widgets maintain their own state | You maintain state in your variables |
| Complex event callbacks | Simple if-statement logic |
| Heavy, feature-rich | Lightweight, programmer-friendly |
| Good for applications | Good for tools/debug |

### The Mental Model

In retained mode, you'd write:
```cpp
// Setup (once)
Button* btn = new Button("Click Me");
btn->OnClick([](){ DoSomething(); });
window->AddChild(btn);
```

In immediate mode, you write:
```cpp
// Every frame
if (ImGui::Button("Click Me"))
{
    DoSomething();
}
```

There's no "button object" to manage. Each frame, you describe what the UI should look like, and ImGui handles the rest.

---

## How ImGui Works

### The Frame Cycle

Every frame, you:

1. **Start a new frame** - Tell ImGui a new frame is beginning
2. **Describe widgets** - Call ImGui functions to build UI
3. **Render** - ImGui converts the description to draw calls

```cpp
// 1. Start frame
ImGui_ImplOpenGL3_NewFrame();
ImGui_ImplGlfw_NewFrame();
ImGui::NewFrame();

// 2. Describe widgets
ImGui::Begin("My Window");
ImGui::Text("Hello!");
ImGui::End();

// 3. Render
ImGui::Render();
ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
```

### Widget Return Values

ImGui widgets return useful information:

```cpp
// Buttons return true when clicked THIS frame
if (ImGui::Button("Save"))
{
    SaveFile();  // Only called when button is clicked
}

// Input widgets return true when VALUE CHANGED
if (ImGui::DragFloat("Speed", &speed, 0.1f))
{
    VP_CORE_INFO("Speed changed to: {}", speed);
}
```

---

## Essential Widgets

### Windows

Windows are containers for other widgets:

```cpp
// Basic window
ImGui::Begin("My Window");
// ... widgets ...
ImGui::End();

// Window with flags
ImGuiWindowFlags flags = ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse;
ImGui::Begin("Fixed Window", nullptr, flags);
ImGui::End();

// Window with close button
static bool showWindow = true;
if (showWindow)
{
    ImGui::Begin("Closeable", &showWindow);  // X button closes it
    ImGui::End();
}
```

### Text Display

```cpp
// Simple text
ImGui::Text("Hello, World!");

// Formatted text (printf-style)
ImGui::Text("FPS: %.1f", fps);
ImGui::Text("Objects: %d", objectCount);

// Colored text
ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "Error!");

// Wrapped text (auto line breaks)
ImGui::TextWrapped("This is a long text that will wrap to the next line.");
```

### Input Widgets

These directly modify your variables:

```cpp
// Float inputs
ImGui::DragFloat("Speed", &speed, 0.1f);              // Drag to change
ImGui::DragFloat("Angle", &angle, 1.0f, 0.0f, 360.0f); // With min/max
ImGui::SliderFloat("Volume", &volume, 0.0f, 1.0f);    // Slider bar

// Vector inputs (for positions, colors, etc.)
ImGui::DragFloat3("Position", &position.x, 0.1f);
ImGui::DragFloat3("Rotation", &rotation.x, 0.01f);

// Color editors
ImGui::ColorEdit3("Light Color", &color.x);     // RGB
ImGui::ColorEdit4("Material", &color.x);        // RGBA with alpha

// Integer inputs
ImGui::DragInt("Count", &count);
ImGui::SliderInt("Level", &level, 1, 10);

// Checkboxes
ImGui::Checkbox("Enabled", &isEnabled);
ImGui::Checkbox("Show Grid", &showGrid);
```

### Buttons and Selectables

```cpp
// Simple button
if (ImGui::Button("Do Thing"))
{
    DoThing();
}

// Button with size
if (ImGui::Button("Wide Button", ImVec2(200, 30)))
{
    DoThing();
}

// Selectable (for lists)
static int selected = 0;
const char* items[] = { "Option A", "Option B", "Option C" };
for (int i = 0; i < 3; i++)
{
    if (ImGui::Selectable(items[i], selected == i))
        selected = i;
}
```

### Layout Helpers

```cpp
// Horizontal layout
if (ImGui::Button("Left")) {}
ImGui::SameLine();                    // Next widget on same line
if (ImGui::Button("Right")) {}

// Separator line
ImGui::Separator();

// Spacing
ImGui::Spacing();                     // Small vertical space
ImGui::Dummy(ImVec2(0, 20));          // Custom vertical space

// Indent
ImGui::Indent();
ImGui::Text("Indented text");
ImGui::Unindent();

// Groups (for layout calculations)
ImGui::BeginGroup();
ImGui::Text("Group start");
ImGui::Button("In group");
ImGui::EndGroup();
```

---

## Our UIManager Wrapper

We wrap ImGui initialization and per-frame boilerplate in a `UIManager` class:

```cpp
// VizEngine/GUI/UIManager.h

class VizEngine_API UIManager
{
public:
    UIManager(GLFWwindow* window);
    ~UIManager();

    void BeginFrame();                              // Start new ImGui frame
    void EndFrame();                                // (unused, for symmetry)
    void Render();                                  // Render ImGui draw data
    void StartWindow(const std::string& windowName); // ImGui::Begin wrapper
    void EndWindow();                               // ImGui::End wrapper

private:
    void Init(GLFWwindow* window);
    void Shutdown();
};
```

### Implementation

```cpp
// VizEngine/GUI/UIManager.cpp

UIManager::UIManager(GLFWwindow* window)
{
    Init(window);
}

UIManager::~UIManager()
{
    Shutdown();
}

void UIManager::Init(GLFWwindow* window)
{
    // Setup ImGui context
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    
    // Setup Platform/Renderer backends
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 460");
    
    // Optional: Configure style
    ImGui::StyleColorsDark();
}

void UIManager::Shutdown()
{
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
}

void UIManager::BeginFrame()
{
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplGlfw_NewFrame();
    ImGui::NewFrame();
}

void UIManager::Render()
{
    ImGui::Render();
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}

void UIManager::StartWindow(const std::string& windowName)
{
    ImGui::Begin(windowName.c_str());
}

void UIManager::EndWindow()
{
    ImGui::End();
}
```

### Usage in Application

```cpp
// In Application::Run()

UIManager ui(window.GetWindow());

while (!window.WindowShouldClose())
{
    // ... input handling ...
    
    ui.BeginFrame();  // Start ImGui frame
    
    // Your UI code
    ui.StartWindow("Debug");
    ImGui::Text("FPS: %.1f", fps);
    ImGui::DragFloat("Speed", &speed);
    ui.EndWindow();
    
    // ... rendering ...
    
    ui.Render();  // Render ImGui on top
    window.SwapBuffersAndPollEvents();
}
```

---

## Building a Real UI

A practical example: building an object inspector.

### Object Selection List

```cpp
static int selectedObject = 0;

ui.StartWindow("Scene Objects");

// List all objects
ImGui::Text("Objects (%zu)", scene.Size());
ImGui::Separator();

for (size_t i = 0; i < scene.Size(); i++)
{
    bool isSelected = (selectedObject == static_cast<int>(i));
    if (ImGui::Selectable(scene[i].Name.c_str(), isSelected))
    {
        selectedObject = static_cast<int>(i);
    }
}

ui.EndWindow();
```

### Property Editor

```cpp
ui.StartWindow("Properties");

if (selectedObject >= 0 && selectedObject < static_cast<int>(scene.Size()))
{
    auto& obj = scene[selectedObject];
    
    ImGui::Text("Selected: %s", obj.Name.c_str());
    ImGui::Separator();
    
    // Transform
    ImGui::Text("Transform");
    ImGui::DragFloat3("Position", &obj.ObjectTransform.Position.x, 0.1f);
    
    glm::vec3 rotDegrees = obj.ObjectTransform.GetRotationDegrees();
    if (ImGui::DragFloat3("Rotation", &rotDegrees.x, 1.0f))
    {
        obj.ObjectTransform.SetRotationDegrees(rotDegrees);
    }
    
    ImGui::DragFloat3("Scale", &obj.ObjectTransform.Scale.x, 0.1f, 0.01f, 10.0f);
    
    ImGui::Separator();
    
    // Appearance
    ImGui::Text("Appearance");
    ImGui::ColorEdit4("Color", &obj.Color.x);
    ImGui::Checkbox("Active", &obj.Active);
}

ui.EndWindow();
```

---

## Styling and Customization

### Built-in Styles

```cpp
ImGui::StyleColorsDark();   // Default dark theme
ImGui::StyleColorsLight();  // Light theme
ImGui::StyleColorsClassic(); // Classic ImGui look
```

### Custom Colors

```cpp
ImGuiStyle& style = ImGui::GetStyle();

// Window background
style.Colors[ImGuiCol_WindowBg] = ImVec4(0.1f, 0.1f, 0.1f, 0.95f);

// Title bar
style.Colors[ImGuiCol_TitleBg] = ImVec4(0.2f, 0.2f, 0.5f, 1.0f);
style.Colors[ImGuiCol_TitleBgActive] = ImVec4(0.3f, 0.3f, 0.7f, 1.0f);

// Buttons
style.Colors[ImGuiCol_Button] = ImVec4(0.3f, 0.3f, 0.3f, 1.0f);
style.Colors[ImGuiCol_ButtonHovered] = ImVec4(0.4f, 0.4f, 0.4f, 1.0f);
style.Colors[ImGuiCol_ButtonActive] = ImVec4(0.5f, 0.5f, 0.5f, 1.0f);
```

### Custom Padding and Rounding

```cpp
ImGuiStyle& style = ImGui::GetStyle();

style.WindowRounding = 5.0f;       // Rounded window corners
style.FrameRounding = 3.0f;        // Rounded widget corners
style.WindowPadding = ImVec2(10, 10);
style.FramePadding = ImVec2(5, 5);
style.ItemSpacing = ImVec2(8, 4);
```

---

## imgui.ini - Persistent Layout

ImGui automatically saves window positions/sizes to `imgui.ini`:

```ini
[Window][Debug]
Pos=100,100
Size=300,200
Collapsed=0

[Window][Scene Objects]
Pos=10,10
Size=250,400
```

This file is created in the working directory. You can:
- Delete it to reset layouts
- Check it into source control for consistent defaults
- Disable it: `ImGui::GetIO().IniFilename = nullptr;`

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| UI not appearing | Forgot `ImGui::Render()` | Call render after describing UI |
| UI not responding to clicks | Wrong ImGui frame order | BeginFrame → Widgets → Render |
| Window always resets position | Not loading imgui.ini | Check working directory |
| Crash on widget | Passing null pointer | Ensure variables exist |
| Widget shows wrong value | Stale pointer | Don't store pointers to scene objects after resize |

---

## Key Takeaways

1. **Immediate mode** - Describe UI every frame, no widget objects to manage
2. **Return values** - Buttons return click state, inputs return change state
3. **Direct modification** - Input widgets modify your variables directly
4. **UIManager wrapper** - Hides ImGui initialization boilerplate
5. **imgui.ini** - Saves window layouts automatically
6. **Styling** - Customizable colors, padding, rounding

---

## Checkpoint

This chapter covered Dear ImGui for debug/editor UI:

**Key Concepts:**
| Concept | Description |
|---------|-------------|
| Immediate Mode | Describe UI every frame |
| Widgets | Button, DragFloat, ColorEdit, Selectable, etc. |
| Windows | Containers with Begin/End |
| UIManager | Our wrapper for init/frame/render |

**Files:**
- `VizEngine/GUI/UIManager.h`
- `VizEngine/GUI/UIManager.cpp`

**Checkpoint:** Create UIManager class, add ImGui initialization/frame code, render a test window with text and sliders, verify it appears over your 3D scene.

---

## Exercise

1. Add a button that changes the clear color to a random value
2. Create a "Camera" window with DragFloat3 for position
3. Use `ImGui::ShowDemoWindow()` to explore all available widgets
4. Customize the style colors to create a unique theme

---

> **Next:** [Chapter 10: Engine Architecture](10_EngineArchitecture.md) - Separating concerns with Transform, Camera, and Mesh classes.

> **Reference:** For the complete UIManager implementation, see [Appendix A: Code Reference](A_Reference.md#gui).

