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

On Windows, the same function needs different keywords depending on context:

```cpp
// When BUILDING the DLL:
__declspec(dllexport) void MyFunction();

// When USING the DLL:
__declspec(dllimport) void MyFunction();
```

### Creating Core.h

We solve this with a macro that automatically switches based on context.

Create **`VizEngine/src/VizEngine/Core.h`**:

```cpp
#pragma once

#ifdef VP_PLATFORM_WINDOWS
    #ifdef VP_BUILD_DLL
        #define VizEngine_API __declspec(dllexport)
    #else
        #define VizEngine_API __declspec(dllimport)
    #endif
#else
    #error VizEngine only supports windows!
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

Any class or function that should be usable from outside the DLL needs this macro:

```cpp
class VizEngine_API Application { ... };
class VizEngine_API Camera { ... };
class VizEngine_API Renderer { ... };
```

---

## The Application Base Class

Games need a base class to inherit from. The engine controls the lifecycle, but games customize behavior.

Create **`VizEngine/src/VizEngine/Application.h`**:

```cpp
#pragma once
#include "Core.h"

namespace VizEngine
{
    class VizEngine_API Application
    {
    public:
        Application();
        virtual ~Application();
        int Run();
    };

    // Implemented by client
    Application* CreateApplication();
}
```

All engine code lives in the `VizEngine` namespace to prevent name collisions and clearly indicate ownership.

---

## The Entry Point

Games have a special startup sequence. The engine defines `main()`, not the application — this lets the engine control initialization order.

Create **`VizEngine/src/VizEngine/EntryPoint.h`**:

```cpp
#pragma once
#ifdef VP_PLATFORM_WINDOWS

namespace VizEngine
{
    extern Application* CreateApplication();
}

int main(int argc, char** argv)
{
    auto app = VizEngine::CreateApplication();
    app->Run();
    delete app;
}

#endif
```

> **Note:** `extern` tells the compiler "this function exists somewhere else" - it will be defined by the user in their application (Sandbox).

### The Pattern

1. **Engine defines `main()`** - Not the application!
2. **Application implements `CreateApplication()`** - Factory function
3. **Engine calls the factory** - Gets an Application instance
4. **Engine runs the app** - Calls `Run()` method

---

## The Public Header

Users need a single header that includes everything they need.

Create **`VizEngine/src/VizEngine.h`**:

```cpp
#pragma once
#include "VizEngine/Application.h"
#include "VizEngine/EntryPoint.h"
```

Users just write `#include <VizEngine.h>` and get access to the Application base class and entry point.

---

## CMake Configuration

Update **`VizEngine/CMakeLists.txt`** to build as a DLL with the correct macros:

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

Key points:
- `SHARED` creates a DLL (not static library)
- `PUBLIC VP_PLATFORM_WINDOWS` - defined for engine AND users
- `PRIVATE VP_BUILD_DLL` - defined ONLY when building VizEngine.dll

---

## Creating Your Application

Now create the Sandbox application that uses the engine.

Create **`Sandbox/src/SandboxApp.cpp`**:

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

Build and run:

```bash
cmake --build build --config Debug
.\build\bin\Debug\Sandbox.exe
```

The application runs (exits immediately since `Run()` is empty for now).

---

## File Organization

```
VizEngine/src/
├── VizEngine.h              ← Public API (users include this)
└── VizEngine/
    ├── Core.h               ← Export macros, platform detection
    ├── Application.h/cpp    ← Base application class
    ├── EntryPoint.h         ← Defines main()
    └── ...
```

## What Gets Built

After building:

```
build/bin/Debug/
├── Sandbox.exe         ← Your application (small)
├── VizEngine.dll       ← The engine (most of the code)
└── VizEngine.pdb       ← Debug symbols

build/lib/Debug/
├── VizEngine.lib       ← Import library (tells linker what's in the DLL)
└── VizEngine.exp       ← Export file (linker intermediate)
```

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Unresolved external symbol" | Missing `VizEngine_API` on class/function | Add `VizEngine_API` to declaration |
| "DLL not found" at runtime | DLL not next to .exe | Copy VizEngine.dll to output folder |
| Linker errors about `CreateApplication` | Function not implemented | Define `VizEngine::CreateApplication()` in your app |

---

## Checkpoint

✓ Created `Core.h` with export/import macro  
✓ Created `Application.h` with base class  
✓ Created `EntryPoint.h` with `main()`  
✓ Created `VizEngine.h` as public header  
✓ Created `SandboxApp.cpp` with factory function  

**Verify:** Run Sandbox.exe — it should start and exit cleanly.

---

## Exercise

1. Add a print statement in `Application::Run()` and see it execute
2. Try removing `VizEngine_API` from Application class - what error do you get?
3. Create a second application class and switch `CreateApplication()` to use it

---

> **Next:** [Chapter 3: Third-Party Libraries](03_ThirdPartyLibraries.md) - The libraries we use and why.
