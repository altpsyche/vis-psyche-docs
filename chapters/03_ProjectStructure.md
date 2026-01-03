\newpage

# Chapter 3: Project Structure & Dependencies

Restructure the Hello Triangle into a proper project layout with Git submodules for dependency management.

> [!NOTE]
> This chapter sets up the project structure and dependencies. Chapter 4 implements the engine/application architecture.

---

## What We're Building

| Component | Purpose |
|-----------|---------|
| **VizEngine/** | Engine source code |
| **Sandbox/** | Application that uses the engine |
| **Git submodules** | GLFW, GLM, spdlog dependencies |

---

## Step 1: Create Directory Structure

```bash
cd C:\dev\VizPsyche

# Create engine directories
mkdir -p VizEngine/src/VizEngine
mkdir -p VizEngine/include
mkdir -p VizEngine/vendor

# Create application directory
mkdir -p Sandbox/src

# Move GLAD to engine
move include VizEngine/include
move src/glad.c VizEngine/src/glad.c
```

After restructuring:

```
VizPsyche/
├── VizEngine/
│   ├── include/
│   │   ├── glad/
│   │   │   └── glad.h
│   │   └── KHR/
│   │       └── khrplatform.h
│   ├── src/
│   │   ├── VizEngine/          ← Engine source files go here
│   │   └── glad.c
│   └── vendor/                 ← Third-party libraries
├── Sandbox/
│   └── src/                    ← Application source files
└── CMakeLists.txt              ← Root build file
```

---

## Step 2: Add Git Submodules

Instead of manually downloading, use Git submodules:

### Add GLFW

```bash
git submodule add https://github.com/glfw/glfw.git VizEngine/vendor/glfw
```

### Add GLM (Math Library)

```bash
git submodule add https://github.com/g-truc/glm.git VizEngine/vendor/glm
```

### Add spdlog (Logging)

```bash
git submodule add https://github.com/gabime/spdlog.git VizEngine/vendor/spdlog
```

### Verify

```bash
git submodule status
```

> [!TIP]
> When cloning later:
> ```bash
> git clone --recursive <repo-url>
> ```
> Or if already cloned:
> ```bash
> git submodule update --init --recursive
> ```

---

## Step 3: Create Root CMakeLists.txt

**Replace `VizPsyche/CMakeLists.txt`:**

```cmake
cmake_minimum_required(VERSION 3.16)
project(VizPsyche VERSION 1.0.0 LANGUAGES C CXX)

# C++ Standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Output Directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Platform
if(WIN32)
    add_definitions(-DNOMINMAX)
    add_definitions(-DUNICODE -D_UNICODE)
endif()

# Auto-update submodules
find_package(Git QUIET)
if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
    option(GIT_SUBMODULE "Update submodules during build" ON)
    if(GIT_SUBMODULE)
        message(STATUS "Updating git submodules...")
        execute_process(
            COMMAND ${GIT_EXECUTABLE} submodule update --init --recursive
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
            RESULT_VARIABLE GIT_SUBMOD_RESULT
        )
    endif()
endif()

# GLFW options
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_INSTALL OFF CACHE BOOL "" FORCE)

# Subdirectories
add_subdirectory(VizEngine/vendor/glfw)
add_subdirectory(VizEngine)
add_subdirectory(Sandbox)

# IDE Configuration
set_property(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY VS_STARTUP_PROJECT Sandbox)
set_property(GLOBAL PROPERTY USE_FOLDERS ON)
set_target_properties(glfw PROPERTIES FOLDER "Dependencies")

message(STATUS "")
message(STATUS "=== VizPsyche Configuration ===")
message(STATUS "  Version: ${PROJECT_VERSION}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "")
```

---

## Project Structure After This Chapter

```
VizPsyche/
├── .git/
├── .gitignore
├── .gitmodules                    ← Submodule configuration
├── CMakeLists.txt                 ← Root build file
├── VizEngine/
│   ├── include/
│   │   ├── glad/
│   │   └── KHR/
│   ├── src/
│   │   └── glad.c
│   └── vendor/
│       ├── glfw/                  ← Git submodule
│       ├── glm/                   ← Git submodule
│       └── spdlog/                ← Git submodule
└── Sandbox/
    └── src/
```

---

## Commit Progress

```bash
git add .
git commit -m "Chapter 3: Project structure with Git submodules"
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Submodule folder empty | Run `git submodule update --init --recursive` |
| "glfw not found" | Ensure `add_subdirectory(VizEngine/vendor/glfw)` is before VizEngine |

---

## Milestone

**Project Structure Ready**

You have:
- Organized directory layout
- GLFW, GLM, spdlog as Git submodules
- Root CMakeLists.txt configured

---

## What's Next

In **Chapter 4**, we'll create the DLL architecture with export macros and the Application base class.

> **Next:** [Chapter 4: DLL Architecture](04_DLLArchitecture.md)

> **Previous:** [Chapter 2: Hello Triangle](02_HelloTriangle.md)
