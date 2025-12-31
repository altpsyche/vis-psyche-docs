\newpage

# Chapter 1: The Build System

## Why CMake?

When you write C++ code, you need to:
1. **Compile** - Turn `.cpp` files into `.obj` (object) files
2. **Link** - Combine object files into an executable or library

You could do this manually with compiler commands, but that becomes impossible with hundreds of files. **Build systems** automate this.

### Build System Options

| Tool | Pros | Cons |
|------|------|------|
| **Make** | Simple, Unix standard | Windows unfriendly, manual |
| **MSBuild** | Visual Studio native | Windows only |
| **CMake** | Cross-platform, generates for any IDE | Learning curve |

We use **CMake** because:
- One `CMakeLists.txt` works on Windows, Mac, Linux
- Generates Visual Studio projects, Makefiles, Ninja, etc.
- Industry standard (Unreal, most game studios use it)

---

## Understanding CMakeLists.txt

### The Root CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.16)
project(VizPsyche VERSION 1.0.0 LANGUAGES C CXX)
```

- `cmake_minimum_required` - Ensures users have a compatible CMake version
- `project` - Names our project, sets version, declares we use C and C++

```cmake
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
```

- `CMAKE_CXX_STANDARD 17` - Use C++17 features
- `REQUIRED ON` - Fail if compiler doesn't support C++17
- `EXTENSIONS OFF` - Don't use compiler-specific extensions (keeps code portable)

```cmake
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
```

This organizes build outputs:
- `bin/` - Executables (.exe) and dynamic libraries (.dll)
- `lib/` - Static libraries (.lib) and import libraries

```cmake
add_subdirectory(VizEngine/vendor/glfw)
add_subdirectory(VizEngine)
add_subdirectory(Sandbox)
```

This tells CMake to process CMakeLists.txt in each subdirectory. Order matters - dependencies first!

---

## The VizEngine CMakeLists.txt

### Declaring Source Files

```cmake
set(VIZENGINE_SOURCES
    src/VizEngine/Application.cpp
    src/VizEngine/Log.cpp
    src/VizEngine/Core/Camera.cpp
    src/VizEngine/Core/Mesh.cpp
    # ... more files
)
```

We explicitly list files instead of using `file(GLOB ...)` because:
- CMake doesn't automatically detect new files with GLOB
- Explicit lists make dependencies clear
- Better for version control (you see what's added)

### Creating the Library

```cmake
add_library(VizEngine SHARED ${VIZENGINE_SOURCES} ${VIZENGINE_HEADERS})
```

- `add_library` - Creates a library target
- `VizEngine` - The target name
- `SHARED` - Build as a DLL (dynamic library), not static
- The source files to compile

### Include Directories

```cmake
target_include_directories(VizEngine
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/vendor/glfw/include
)
```

- `PUBLIC` - Both VizEngine AND anyone linking to it can use these headers
- `PRIVATE` - Only VizEngine can use these (internal implementation)

The `$<BUILD_INTERFACE:...>` is a "generator expression" - it only applies when building (not when installed).

### Compile Definitions

```cmake
target_compile_definitions(VizEngine
    PUBLIC
        $<$<PLATFORM_ID:Windows>:VP_PLATFORM_WINDOWS>
    PRIVATE
        VP_BUILD_DLL
)
```

These are preprocessor `#define`s:
- `VP_PLATFORM_WINDOWS` - Defined on Windows (used for platform code)
- `VP_BUILD_DLL` - Tells our code we're building the DLL (for export macros)

### Linking Libraries

```cmake
target_link_libraries(VizEngine 
    PRIVATE 
        glfw
        $<$<PLATFORM_ID:Windows>:opengl32>
)
```

- Links GLFW library
- On Windows, also links `opengl32.lib` (the Windows OpenGL library)

---

## The Sandbox CMakeLists.txt

```cmake
add_executable(Sandbox src/SandboxApp.cpp)
target_link_libraries(Sandbox PRIVATE VizEngine)
```

That's it! The Sandbox just:
1. Creates an executable
2. Links to VizEngine (which brings all its PUBLIC includes and dependencies)

### Copying Resources

```cmake
add_custom_command(TARGET Sandbox POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory 
        "${CMAKE_SOURCE_DIR}/VizEngine/src/resources" 
        "$<TARGET_FILE_DIR:Sandbox>/src/resources"
)
```

After building Sandbox, copy the `resources/` folder next to the .exe so shaders and textures are found at runtime.

---

## Building the Project

### First Time Setup

```bash
# Create build directory and generate project files
cmake -B build -G "Visual Studio 17 2022"
```

- `-B build` - Put generated files in `build/` folder
- `-G "Visual Studio 17 2022"` - Generate for Visual Studio 2022

### Building

```bash
# Build Debug configuration
cmake --build build --config Debug

# Build Release configuration
cmake --build build --config Release
```

### Running

The executable is at: `build/bin/Debug/Sandbox.exe`

---

## Key Takeaways

1. **CMake generates build files** - It doesn't compile code directly
2. **Targets are the building blocks** - Libraries, executables, custom commands
3. **PUBLIC vs PRIVATE** - Controls what consumers of your library see
4. **Generator expressions** - `$<...>` for conditional/platform-specific settings
5. **Order matters** - Dependencies must be defined before targets that use them

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "CMake Error: Could not find compiler" | Visual Studio not installed | Install VS 2022 with C++ workload |
| "Cannot find -lglfw" | Submodules not initialized | Run `git submodule update --init --recursive` |
| Build succeeds but .exe crashes | Resources not copied | Ensure `add_custom_command` copies `resources/` |

---

## Checkpoint

This chapter covered the build system that compiles VizPsyche:

**Files:**
- `CMakeLists.txt` (root) — Project setup, C++17, output directories
- `VizEngine/CMakeLists.txt` — Engine library with all sources
- `Sandbox/CMakeLists.txt` — Test application

**Building Along?**

Create the project structure from scratch:

1. Create the folder structure:
   ```
   VizPsyche/
   ├── CMakeLists.txt
   ├── VizEngine/
   │   ├── CMakeLists.txt
   │   └── src/
   │       └── VizEngine/
   │           └── (empty for now)
   └── Sandbox/
       ├── CMakeLists.txt
       └── src/
           └── SandboxApp.cpp
   ```

2. Create **root `CMakeLists.txt`**:
   ```cmake
   cmake_minimum_required(VERSION 3.16)
   project(VizPsyche VERSION 1.0.0 LANGUAGES C CXX)

   set(CMAKE_CXX_STANDARD 17)
   set(CMAKE_CXX_STANDARD_REQUIRED ON)

   add_subdirectory(VizEngine)
   add_subdirectory(Sandbox)
   ```

3. Create **`VizEngine/CMakeLists.txt`** (minimal for now):
   ```cmake
   add_library(VizEngine SHARED)
   ```

4. Create **`Sandbox/CMakeLists.txt`**:
   ```cmake
   add_executable(Sandbox src/SandboxApp.cpp)
   target_link_libraries(Sandbox PRIVATE VizEngine)
   ```

5. Create **`Sandbox/src/SandboxApp.cpp`**:
   ```cpp
   int main()
   {
       return 0;
   }
   ```

6. Generate and build:
   ```bash
   cmake -B build -G "Visual Studio 17 2022"
   cmake --build build --config Debug
   ```

**✓ Success:** Build completes. `Sandbox.exe` exists (does nothing yet).

---

## Exercise

Try modifying CMakeLists.txt:
1. Add a new source file and see if it compiles
2. Change from `SHARED` to `STATIC` - what happens?
3. Add a new compile definition and check it with `#ifdef` in code

---

> **Next:** [Chapter 2: DLL Architecture](02_DLLArchitecture.md) - How the engine and application interact.

