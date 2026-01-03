\newpage

# Chapter 15: Dear ImGui

Add **Dear ImGui** for debug UI. ImGui is an immediate-mode GUI library.

---

## Adding Dear ImGui

### Step 1: Add Submodule

```bash
cd VizPsyche
git submodule add https://github.com/ocornut/imgui.git VizEngine/vendor/imgui
```

### Step 2: Update CMakeLists.txt

```cmake
set(VENDOR_SOURCES
    vendor/stb_image/stb_image.cpp
    # ImGui
    vendor/imgui/imgui.cpp
    vendor/imgui/imgui_demo.cpp
    vendor/imgui/imgui_draw.cpp
    vendor/imgui/imgui_tables.cpp
    vendor/imgui/imgui_widgets.cpp
    vendor/imgui/backends/imgui_impl_glfw.cpp
    vendor/imgui/backends/imgui_impl_opengl3.cpp
)

target_include_directories(VizEngine
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/vendor/imgui
        ${CMAKE_CURRENT_SOURCE_DIR}/vendor/imgui/backends
)
```

---

## Step 3: Create UIManager.h

**Create `VizEngine/src/VizEngine/GUI/UIManager.h`:**

```cpp
// VizEngine/src/VizEngine/GUI/UIManager.h

#pragma once

#include <iostream>
#include <string>
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include "VizEngine/Core.h"

namespace VizEngine
{
    class VizEngine_API UIManager
    {
    public:
        UIManager(GLFWwindow* window);
        ~UIManager();

        void BeginFrame();
        void EndFrame();
        void Render();
        void StartWindow(const std::string& windowName);
        void EndWindow();

    private:
        void Init(GLFWwindow* window);
        void Shutdown();
    };
}
```

> [!NOTE]
> UIManager is a **non-static class** with a constructor. Use `StartWindow()`/`EndWindow()` for panels, and `Render()` to draw the UI.

---

## Step 4: Create UIManager.cpp

**Create `VizEngine/src/VizEngine/GUI/UIManager.cpp`:**

```cpp
// VizEngine/src/VizEngine/GUI/UIManager.cpp

#include "UIManager.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
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
        IMGUI_CHECKVERSION();
        ImGui::CreateContext();

        ImGuiIO& io = ImGui::GetIO();
        io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
        io.ConfigFlags |= ImGuiConfigFlags_DockingEnable;

        ImGui::StyleColorsDark();

        ImGui_ImplGlfw_InitForOpenGL(window, true);
        ImGui_ImplOpenGL3_Init("#version 460");

        VP_CORE_INFO("ImGui initialized");
    }

    void UIManager::Shutdown()
    {
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplGlfw_Shutdown();
        ImGui::DestroyContext();
        VP_CORE_TRACE("ImGui shutdown");
    }

    void UIManager::BeginFrame()
    {
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();
    }

    void UIManager::EndFrame()
    {
        ImGui::EndFrame();
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

}  // namespace VizEngine
```

---

## Step 5: Integrate in Application

```cpp
#include "GUI/UIManager.h"
#include <imgui.h>

int Application::Run()
{
    GLFWManager window(1280, 720, "VizPsyche");
    // ... GLAD, renderer init ...

    UIManager uiManager(window.GetWindow());
    Renderer renderer;

    while (!window.WindowShouldClose())
    {
        window.ProcessInput();

        // Clear
        float clearColor[4] = { 0.1f, 0.1f, 0.15f, 1.0f };
        renderer.Clear(clearColor);

        // Begin ImGui
        uiManager.BeginFrame();

        // UI Panels
        uiManager.StartWindow("Debug");
        ImGui::Text("Hello, ImGui!");
        ImGui::Text("FPS: %.1f", ImGui::GetIO().Framerate);
        uiManager.EndWindow();

        // Render scene
        scene.Render(renderer, shader, camera);

        // Render ImGui
        uiManager.Render();

        window.SwapBuffersAndPollEvents();
    }

    return 0;
}
```

---

## Common ImGui Widgets

```cpp
// Text
ImGui::Text("Hello, World!");
ImGui::TextColored({1, 0, 0, 1}, "Red text");

// Inputs
static float value = 0.0f;
ImGui::SliderFloat("Value", &value, 0.0f, 1.0f);
ImGui::DragFloat("Position", &position.x, 0.1f);
ImGui::ColorEdit4("Color", &color.r);

// Buttons
if (ImGui::Button("Click Me"))
{
    // Do something
}

// Checkbox
static bool enabled = true;
ImGui::Checkbox("Enable Feature", &enabled);
```

---

## Example: Object Inspector

```cpp
void RenderObjectInspector(SceneObject& obj)
{
    ImGui::Begin("Inspector");

    ImGui::Text("Name: %s", obj.Name.c_str());
    ImGui::Separator();

    if (ImGui::CollapsingHeader("Transform", ImGuiTreeNodeFlags_DefaultOpen))
    {
        ImGui::DragFloat3("Position", &obj.ObjectTransform.Position.x, 0.1f);

        glm::vec3 rotDeg = obj.ObjectTransform.GetRotationDegrees();
        if (ImGui::DragFloat3("Rotation", &rotDeg.x, 1.0f))
            obj.ObjectTransform.SetRotationDegrees(rotDeg);

        ImGui::DragFloat3("Scale", &obj.ObjectTransform.Scale.x, 0.1f);
    }

    if (ImGui::CollapsingHeader("Material"))
    {
        ImGui::ColorEdit4("Color", &obj.Color.r);
        ImGui::SliderFloat("Roughness", &obj.Roughness, 0.0f, 1.0f);
    }

    ImGui::End();
}
```

---

## imgui.ini

Add to `.gitignore`:

```gitignore
imgui.ini
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| ImGui not visible | Render not called | Call `uiManager.Render()` after scene |
| Input not working | Backend not initialized | Ensure constructor called |
| Crash on shutdown | Wrong order | UIManager destructor handles cleanup |

---

## Milestone

**Dear ImGui Integrated**

You have:
- UIManager class (constructor-based)
- `StartWindow()`/`EndWindow()` for panels
- `Render()` method
- Object inspector example with Roughness

---

## What's Next

In **Chapter 16**, we'll add Blinn-Phong lighting.

> **Next:** [Chapter 16: Blinn-Phong Lighting](16_Lighting.md)

> **Previous:** [Chapter 14: Scene Management](14_SceneManagement.md)
