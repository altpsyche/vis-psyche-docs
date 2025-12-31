\newpage

# Chapter 2: DLL Architecture

## What is a DLL?

**DLL** = Dynamic Link Library

When you build code, you have two choices:

### Static Linking (.lib)
```
[Your Code] + [Library Code] = [One Big Executable]
```
- Library code is copied INTO your .exe
- Larger executable
- No external dependencies at runtime
- Changes to library require full recompile

### Dynamic Linking (.dll)
```
[Your Code] = [Small Executable] ──loads──> [Library.dll]
```
- Library stays separate
- Smaller executable
- Can update DLL without recompiling app
- Multiple apps can share one DLL (memory efficient)

---

## Why VizEngine is a DLL

We chose DLL architecture because:

1. **Faster Iteration** - Change engine code, rebuild only the DLL
2. **Hot Reloading** (future) - Could reload DLL without restarting app
3. **Clear Separation** - Forces clean API design
4. **Industry Practice** - Most engines work this way

---

## The Export/Import Problem

When you compile a DLL, the compiler needs to know:
- **Which symbols to EXPORT** (make available to users)
- **Which symbols to IMPORT** (use from a DLL)

### The Windows Way

```cpp
// When BUILDING the DLL:
__declspec(dllexport) void MyFunction();

// When USING the DLL:
__declspec(dllimport) void MyFunction();
```

Same function needs different keywords depending on context!

### Our Solution: Core.h

```cpp
// VizEngine/src/VizEngine/Core.h

#pragma once

#ifdef VP_PLATFORM_WINDOWS
    #ifdef VP_BUILD_DLL
        #define VizEngine_API __declspec(dllexport)
    #else
        #define VizEngine_API __declspec(dllimport)
    #endif
#else
    #error VizEngine only supports Windows!
#endif
```

How it works:

1. **When building VizEngine.dll:**
   - CMake defines `VP_BUILD_DLL`
   - `VizEngine_API` becomes `__declspec(dllexport)`
   - Symbols are exported FROM the DLL

2. **When building Sandbox.exe:**
   - `VP_BUILD_DLL` is NOT defined
   - `VizEngine_API` becomes `__declspec(dllimport)`
   - Symbols are imported FROM the DLL

### Using the Macro

```cpp
// Any class/function that should be usable from outside the DLL:
class VizEngine_API Application { ... };
class VizEngine_API Camera { ... };
class VizEngine_API Renderer { ... };
```

---

## Namespaces

All engine code lives in the `VizEngine` namespace:

```cpp
namespace VizEngine
{
    class Camera { ... };
    class Mesh { ... };
    class Shader { ... };
}
```

Why?
- **Prevents name collisions** - Your `Texture` won't conflict with another library's `Texture`
- **Clear ownership** - `VizEngine::Renderer` vs `SomeOtherLib::Renderer`
- **Organization** - All engine symbols are grouped

---

## The Entry Point

Games have a special startup sequence. We handle this in `EntryPoint.h`:

```cpp
// VizEngine/src/VizEngine/EntryPoint.h

#pragma once

#ifdef VP_PLATFORM_WINDOWS

namespace VizEngine
{
    // Implemented by the client application (e.g., Sandbox)
    extern Application* CreateApplication();
}

int main(int argc, char** argv)
{
    VizEngine::Log::Init();
    auto app = VizEngine::CreateApplication();
    app->Run();
    delete app;
}

#endif
```

> **Note:** `CreateApplication()` is declared inside `VizEngine` namespace with `extern`. 
> The `extern` keyword tells the compiler "this function exists somewhere else" - in this 
> case, it will be defined by the user in their application (Sandbox).

### How It Works

1. **The engine defines `main()`** - Not the application!
2. **Application implements `CreateApplication()`** - Factory function
3. **Engine calls the factory** - Gets an Application instance
4. **Engine runs the app** - Calls `Run()` method

### In Sandbox (SandboxApp.cpp)

```cpp
#include <VizEngine.h>

class Sandbox : public VizEngine::Application
{
public:
    Sandbox() { }
    ~Sandbox() { }
};

// This is what the engine calls:
VizEngine::Application* VizEngine::CreateApplication()
{
    return new Sandbox();
}
```

### Why This Pattern?

1. **Engine controls initialization order** - Logging starts before app code
2. **Engine controls shutdown** - Cleanup happens correctly
3. **Application is decoupled** - Just implement the factory
4. **Extendable** - Sandbox can override Application methods (virtual)

---

## The VizEngine.h Public Header

```cpp
// VizEngine/src/VizEngine.h

#pragma once

#include "VizEngine/Application.h"
#include "VizEngine/Log.h"
#include "VizEngine/EntryPoint.h"
```

This is the **one header** users include. It pulls in:
- Application base class (to inherit from)
- Logging macros
- Entry point (defines `main()`)

Users just write:
```cpp
#include <VizEngine.h>
```

---

## File Organization

```
VizEngine/src/
├── VizEngine.h              ← Public API (users include this)
└── VizEngine/
    ├── Core.h               ← Export macros, platform detection
    ├── Application.h/cpp    ← Base application class
    ├── EntryPoint.h         ← Defines main()
    ├── Log.h/cpp            ← Logging system
    ├── Core/                ← Engine core systems
    │   ├── Camera.h/cpp
    │   ├── Mesh.h/cpp
    │   └── Transform.h
    ├── OpenGL/              ← Graphics abstractions
    │   ├── Shader.h/cpp
    │   ├── Texture.h/cpp
    │   └── ...
    └── GUI/                 ← UI system
        └── UIManager.h/cpp
```

---

## What Gets Built

After building:

```
build/bin/Debug/
├── Sandbox.exe         ← Your application (small)
├── VizEngine.dll       ← The engine (most of the code)
├── VizEngine.pdb       ← Debug symbols (for debugging)
└── src/resources/      ← Shaders, textures (copied)

build/lib/Debug/
├── VizEngine.lib       ← Import library (tells linker what's in the DLL)
├── VizEngine.exp       ← Export file (linker intermediate)
└── glfw3.lib           ← GLFW static library
```

---

## Key Takeaways

1. **DLLs separate code** - Engine and app are different files
2. **Export/Import macros** - `VizEngine_API` handles the switching
3. **Namespaces prevent collisions** - Everything in `VizEngine::`
4. **Engine owns main()** - Applications just implement a factory
5. **Single public header** - Users include one file

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Unresolved external symbol" | Missing `VizEngine_API` on class/function | Add `VizEngine_API` to declaration |
| "DLL not found" at runtime | DLL not next to .exe | Copy VizEngine.dll to output folder |
| Linker errors about `CreateApplication` | Function not implemented | Define `VizEngine::CreateApplication()` in your app |

---

## Checkpoint

This chapter covered how VizEngine uses DLL architecture:

**Key Files:**
- `VizEngine/Core.h` — Export/import macro (`VizEngine_API`)
- `VizEngine/EntryPoint.h` — Defines `main()`, calls your factory
- `VizEngine.h` — Single public header users include

**Pattern:**
```cpp
// Your app implements this:
VizEngine::Application* VizEngine::CreateApplication()
{
    return new YourApp();
}
```

**Building Along?**

Create the DLL architecture files:

1. Create **`VizEngine/src/VizEngine/Core.h`**:
   ```cpp
   #pragma once

   #ifdef VP_PLATFORM_WINDOWS
       #ifdef VP_BUILD_DLL
           #define VizEngine_API __declspec(dllexport)
       #else
           #define VizEngine_API __declspec(dllimport)
       #endif
   #else
       #error VizEngine only supports Windows!
   #endif
   ```

2. Create **`VizEngine/src/VizEngine/Application.h`**:
   ```cpp
   #pragma once
   #include "Core.h"

   namespace VizEngine
   {
       class VizEngine_API Application
       {
       public:
           Application() = default;
           virtual ~Application() = default;
           virtual int Run() { return 0; }
       };

       // Implemented by client
       extern Application* CreateApplication();
   }
   ```

3. Create **`VizEngine/src/VizEngine/EntryPoint.h`**:
   ```cpp
   #pragma once
   #ifdef VP_PLATFORM_WINDOWS

   int main(int argc, char** argv)
   {
       auto app = VizEngine::CreateApplication();
       app->Run();
       delete app;
       return 0;
   }

   #endif
   ```

4. Create **`VizEngine/src/VizEngine.h`** (public header):
   ```cpp
   #pragma once
   #include "VizEngine/Application.h"
   #include "VizEngine/EntryPoint.h"
   ```

5. Update **`VizEngine/CMakeLists.txt`**:
   ```cmake
   add_library(VizEngine SHARED
       src/VizEngine/Application.h
       src/VizEngine/Core.h
       src/VizEngine/EntryPoint.h
   )

   target_include_directories(VizEngine PUBLIC src)
   target_compile_definitions(VizEngine
       PUBLIC VP_PLATFORM_WINDOWS
       PRIVATE VP_BUILD_DLL
   )
   ```

6. Update **`Sandbox/src/SandboxApp.cpp`**:
   ```cpp
   #include <VizEngine.h>

   class Sandbox : public VizEngine::Application
   {
   public:
       Sandbox() { }
       ~Sandbox() { }
   };

   VizEngine::Application* VizEngine::CreateApplication()
   {
       return new Sandbox();
   }
   ```

7. Rebuild and run:
   ```bash
   cmake --build build --config Debug
   .\build\bin\Debug\Sandbox.exe
   ```

**✓ Success:** Application runs (exits immediately since `Run()` is empty).

---

## Exercise

1. Add `VP_CORE_INFO("Hello from Application constructor!")` and see it in console
2. Try removing `VizEngine_API` from a class - what error do you get?
3. Create a second application class and switch `CreateApplication()` to use it

---

> **Next:** [Chapter 3: Third-Party Libraries](03_ThirdPartyLibraries.md) - The libraries we use and why.

