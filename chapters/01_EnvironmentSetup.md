\newpage

# Chapter 1: Environment Setup

Before writing any engine code, we need a properly configured development environment. This chapter ensures you have all the tools installed and working.

---

## Required Tools

| Tool | Purpose | Minimum Version |
|------|---------|-----------------|
| **Visual Studio 2022** | C++ compiler and IDE | 17.0 |
| **CMake** | Build system generator | 3.16 |
| **Git** | Version control | 2.30 |

---

## Step 1: Install Visual Studio 2022

Visual Studio provides the C++ compiler (MSVC) and debugger.

### Download

1. Go to [visualstudio.microsoft.com](https://visualstudio.microsoft.com/)
2. Download **Visual Studio 2022 Community** (free)
3. Run the installer

### Select Workloads

In the Visual Studio Installer, check:

- [x] **Desktop development with C++**

This installs:
- MSVC compiler
- Windows SDK
- CMake tools (optional, we'll use standalone CMake)
- Debugging tools

### Verify Installation

1. Open **Developer Command Prompt for VS 2022** (search in Start menu)
2. Run:

```bash
cl
```

You should see output like:

```
Microsoft (R) C/C++ Optimizing Compiler Version 19.xx.xxxxx for x64
```

---

## Step 2: Install CMake

CMake generates Visual Studio project files from our `CMakeLists.txt`.

### Download

1. Go to [cmake.org/download](https://cmake.org/download/)
2. Download **Windows x64 Installer** (.msi)
3. Run the installer

### Important: Add to PATH

During installation, select:

- [x] **Add CMake to the system PATH for all users**

### Verify Installation

Open a **new** terminal (Command Prompt or PowerShell) and run:

```bash
cmake --version
```

Expected output:

```
cmake version 3.28.1
```

(Version should be 3.16 or higher)

---

## Step 3: Install Git

Git manages our source code and downloads dependencies via submodules.

### Download

1. Go to [git-scm.com](https://git-scm.com/)
2. Download **Git for Windows**
3. Run the installer with default options

### Verify Installation

Open a terminal and run:

```bash
git --version
```

Expected output:

```
git version 2.43.0.windows.1
```

---

## Step 4: Create Project Directory

Choose a location for your engine. Avoid paths with spaces.

**Good:**
```
C:\dev\VizPsyche
D:\Projects\VizPsyche
```

**Avoid:**
```
C:\Users\John Doe\My Projects\VizPsyche   ← Spaces cause issues
```

### Create the Directory

```bash
mkdir C:\dev
cd C:\dev
mkdir VizPsyche
cd VizPsyche
```

### Initialize Git Repository

```bash
git init
```

You should see:

```
Initialized empty Git repository in C:/dev/VizPsyche/.git/
```

---

## Step 5: Configure Git (Optional but Recommended)

Set your identity for commits:

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

## Step 6: Create .gitignore

Create a file to exclude build artifacts from version control.

**Create `C:\dev\VizPsyche\.gitignore`:**

```gitignore
# Build directories
build/
out/
cmake-build-*/

# IDE files
.vs/
.vscode/
*.user
*.suo

# Compiled files
*.obj
*.exe
*.dll
*.lib
*.pdb
*.ilk
*.exp

# OS files
Thumbs.db
.DS_Store

# ImGui settings (regenerated)
imgui.ini
```

### Add and Commit

```bash
git add .gitignore
git commit -m "Initial commit: Add .gitignore"
```

---

## Verification Checklist

Before proceeding, verify each tool:

| Check | Command | Expected Result |
|-------|---------|-----------------|
| MSVC compiler | `cl` (in Developer Command Prompt) | Shows compiler version |
| CMake | `cmake --version` | Version 3.16+ |
| Git | `git --version` | Version 2.30+ |
| Project directory | `cd C:\dev\VizPsyche` | Directory exists |
| Git initialized | `git status` | Shows "On branch main/master" |

---

## Common Issues

| Problem | Solution |
|---------|----------|
| `'cmake' is not recognized` | Restart terminal after CMake install, or add to PATH manually |
| `'git' is not recognized` | Restart terminal after Git install |
| `cl` shows error | Use **Developer Command Prompt**, not regular Command Prompt |
| Permission denied | Run terminal as Administrator, or use a directory you own |

---

## Milestone

**Milestone: Environment Ready**

You should have:
- Visual Studio 2022 with C++ workload
- CMake 3.16+ accessible from terminal
- Git 2.30+ accessible from terminal
- Empty `VizPsyche` project directory with Git initialized
- `.gitignore` committed

---

## What's Next

With the environment ready, we'll write our first graphics program in **Chapter 2**—a single-file "Hello Triangle" that gets pixels on screen as fast as possible.

> **Next:** [Chapter 2: Hello Triangle](02_HelloTriangle.md)

> **Previous:** [Introduction](00_Introduction.md)
