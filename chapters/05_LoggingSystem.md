\newpage

# Chapter 5: Logging System

Logging is the engine developer's best friend. When something goes wrong (and it will), logs tell you what happened. Our logging system wraps spdlog to provide clean, categorized, performant logging.

## Why Not Just Use std::cout?

```cpp
// This works, but...
std::cout << "Loading texture: " << filename << std::endl;
std::cout << "ERROR: Failed to load texture!" << std::endl;
```

Problems with `std::cout`:

| Issue | Impact |
|-------|--------|
| No timestamps | When did it happen? |
| No log levels | Can't filter debug vs errors |
| No categories | Engine vs game messages? |
| Slow (synchronous) | Blocks while writing |
| No color | Errors look like info |

Our logging system solves all of these.

---

## Creating the Log Class

We need a static wrapper around spdlog with two separate loggers — one for engine internals, one for game code.

Create **`VizEngine/src/VizEngine/Log.h`**:

```cpp
#pragma once
#include <memory>
#include "Core.h"
#include "spdlog/spdlog.h"

namespace VizEngine
{
    class VizEngine_API Log
    {
    public:
        enum class LogLevel
        {
            Trace, Debug, Info, Warn, Error, Critical, Off
        };

        static void Init();
        static void SetCoreLogLevel(LogLevel level);
        static void SetClientLogLevel(LogLevel level);

        inline static std::shared_ptr<spdlog::logger>& GetCoreLogger() { return s_CoreLogger; }
        inline static std::shared_ptr<spdlog::logger>& GetClientLogger() { return s_ClientLogger; }

    private:
        static spdlog::level::level_enum EnumToLogLevel(LogLevel level);
        static std::shared_ptr<spdlog::logger> s_CoreLogger;
        static std::shared_ptr<spdlog::logger> s_ClientLogger;
    };
}

// Core logging macros
#define VP_CORE_TRACE(...)    ::VizEngine::Log::GetCoreLogger()->trace(__VA_ARGS__)
#define VP_CORE_INFO(...)     ::VizEngine::Log::GetCoreLogger()->info(__VA_ARGS__)
#define VP_CORE_WARN(...)     ::VizEngine::Log::GetCoreLogger()->warn(__VA_ARGS__)
#define VP_CORE_ERROR(...)    ::VizEngine::Log::GetCoreLogger()->error(__VA_ARGS__)
#define VP_CORE_CRITICAL(...) ::VizEngine::Log::GetCoreLogger()->critical(__VA_ARGS__)

// Client logging macros
#define VP_TRACE(...)    ::VizEngine::Log::GetClientLogger()->trace(__VA_ARGS__)
#define VP_INFO(...)     ::VizEngine::Log::GetClientLogger()->info(__VA_ARGS__)
#define VP_WARN(...)     ::VizEngine::Log::GetClientLogger()->warn(__VA_ARGS__)
#define VP_ERROR(...)    ::VizEngine::Log::GetClientLogger()->error(__VA_ARGS__)
#define VP_CRITICAL(...) ::VizEngine::Log::GetClientLogger()->critical(__VA_ARGS__)
```

### Two Loggers: Core vs Client

| Logger | Purpose | Prefix |
|--------|---------|--------|
| **Core** | Engine internals | `[VizPsyche]` |
| **Client** | Game/application | `[Client]` |

This separation matters:
- Engine developers see core messages
- Game developers see client messages
- You can filter each independently

```cpp
// In engine code:
VP_CORE_INFO("Shader compiled successfully");

// In game code:
VP_INFO("Player spawned at position {}", pos);
```

### Why Macros?

1. **Shorter code**: `VP_INFO("x")` vs `VizEngine::Log::GetClientLogger()->info("x")`
2. **Compile-time removal**: In release builds, we could `#define VP_TRACE(...)` to nothing
3. **Automatic file/line**: Could add `__FILE__` and `__LINE__` to the macro

The `__VA_ARGS__` is a special macro that captures "everything passed in":

```cpp
VP_INFO("Player {} scored {} points", name, score);
// Expands to:
::VizEngine::Log::GetClientLogger()->info("Player {} scored {} points", name, score);
```

---

## Initializing the Loggers

Create **`VizEngine/src/VizEngine/Log.cpp`**:

```cpp
#include "Log.h"
#include <spdlog/sinks/stdout_color_sinks.h>

namespace VizEngine
{
    std::shared_ptr<spdlog::logger> Log::s_CoreLogger;
    std::shared_ptr<spdlog::logger> Log::s_ClientLogger;

    void Log::Init()
    {
        // Set the global log pattern
        spdlog::set_pattern("%^[%T] %n: %v%$");

        // Initialize Core Logger
        s_CoreLogger = spdlog::stdout_color_mt("VizPsyche");
        s_CoreLogger->set_level(spdlog::level::trace);

        // Initialize Client Logger
        s_ClientLogger = spdlog::stdout_color_mt("Client");
        s_ClientLogger->set_level(spdlog::level::trace);
    }
}
```

### Understanding the Pattern

The pattern string `"%^[%T] %n: %v%$"` controls output format:

| Pattern | Meaning | Example |
|---------|---------|---------|
| `%T` | Time | 10:30:45 |
| `%n` | Logger name | VizPsyche |
| `%^`...`%$` | Colored section | (colors the level) |
| `%v` | The actual message | Your text here |

### stdout_color_mt

`spdlog::stdout_color_mt("name")` creates:
- A logger that outputs to **stdout**
- With **color** support
- Thread-safe (**mt** = multi-threaded)
- Named "VizPsyche" or "Client"

---

## Adding Logging to EntryPoint

Now we need to initialize the logging system before anything else runs.

Update **`VizEngine/src/VizEngine/EntryPoint.h`**:

```cpp
#pragma once
#ifdef VP_PLATFORM_WINDOWS

namespace VizEngine
{
    extern Application* CreateApplication();
}

int main(int argc, char** argv)
{
    VizEngine::Log::Init();  // Initialize logging first
    auto app = VizEngine::CreateApplication();
    app->Run();
    delete app;
}

#endif
```

Also add `Log.cpp` to **`VizEngine/CMakeLists.txt`**:

```cmake
add_library(VizEngine SHARED
    src/VizEngine/Log.cpp
    # ... other files
)
```

---

## Log Levels

Not all messages are equal:

| Level | Use For | Example |
|-------|---------|---------|
| **Trace** | Very detailed debug info | "Entering function X" |
| **Debug** | Developer info | "Loaded 42 textures" |
| **Info** | General information | "Engine started" |
| **Warn** | Something unexpected | "Texture not found, using default" |
| **Error** | Errors that were handled | "Failed to open file" |
| **Critical** | Fatal errors | "Out of memory, shutting down" |

### Filtering by Level

Setting a log level filters out less severe messages:

```cpp
Log::SetCoreLogLevel(LogLevel::Warn);

VP_CORE_TRACE("This won't appear");
VP_CORE_DEBUG("This won't appear");
VP_CORE_INFO("This won't appear");
VP_CORE_WARN("This WILL appear");     // ✓
VP_CORE_ERROR("This WILL appear");    // ✓
VP_CORE_CRITICAL("This WILL appear"); // ✓
```

Common configurations:
- **Development**: `Trace` - see everything
- **Testing**: `Debug` - skip trace spam
- **Release**: `Warn` - only problems

---

## Format Strings

spdlog uses the `{fmt}` library for formatting:

```cpp
// Basic substitution
VP_INFO("Value is {}", 42);                    // Value is 42

// Multiple values
VP_INFO("{} + {} = {}", 1, 2, 3);              // 1 + 2 = 3

// Formatting
VP_INFO("Hex: {:x}", 255);                     // Hex: ff
VP_INFO("Float: {:.2f}", 3.14159);             // Float: 3.14
```

| Specifier | Meaning | Example |
|-----------|---------|---------|
| `{:d}` | Decimal integer | 42 |
| `{:x}` | Hexadecimal | 2a |
| `{:.2f}` | Float, 2 decimals | 3.14 |

---

## Using Logging in Your Game

Test the logging system in your Sandbox application:

```cpp
// Sandbox/src/SandboxApp.cpp
#include <VizEngine.h>

class Sandbox : public VizEngine::Application
{
public:
    Sandbox()
    {
        VP_INFO("Sandbox application created!");
    }
    
    ~Sandbox()
    {
        VP_INFO("Sandbox shutting down");
    }
};

VizEngine::Application* VizEngine::CreateApplication()
{
    return new Sandbox();
}
```

Rebuild and run. You should see colored output:

```
[10:30:45] VizPsyche: Engine initialized
[10:30:45] Client: Sandbox application created!
```

---

## Best Practices

### Do Log
```cpp
VP_CORE_INFO("Loaded {} textures in {:.2f}ms", count, time);
VP_CORE_ERROR("Failed to compile shader: {}", errorMessage);
VP_CORE_WARN("Deprecated function called: {}", funcName);
```

### Don't Log
```cpp
// Too spammy - every frame!
VP_CORE_TRACE("Rendering frame...");  // Bad: thousands per second

// Sensitive data
VP_INFO("User password: {}", password);  // Bad: security issue
```

### Log on State Changes
```cpp
if (newState != oldState)
{
    VP_INFO("State changed from {} to {}", oldState, newState);
}
```

---

## Checkpoint

✓ Created `Log.h` with Log class and macros  
✓ Created `Log.cpp` with initialization  
✓ Updated `EntryPoint.h` to call `Log::Init()`  
✓ Tested with VP_INFO in Sandbox  

**Verify:** Rebuild and run. Colored log messages appear in console.

---

## Exercise

1. Add a new log level macro `VP_CORE_DEBUG` that's removed in release builds
2. Add file logging to capture errors to `error.log`
3. Add a timestamp to the log pattern showing milliseconds
4. Create a custom logger for a subsystem (e.g., "Physics", "Audio")

---

> **Next:** [Chapter 6: OpenGL Fundamentals](06_OpenGLFundamentals.md) - Understanding the graphics pipeline.
