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

## The Log Class

Here's our wrapper:

```cpp
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
    static std::shared_ptr<spdlog::logger> s_CoreLogger;
    static std::shared_ptr<spdlog::logger> s_ClientLogger;
};
```

---

## Two Loggers: Core vs Client

We have **two separate loggers**:

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

Output:
```
[2024-01-15 10:30:45.123] [VizPsyche] [info] Shader compiled successfully
[2024-01-15 10:30:45.456] [Client] [info] Player spawned at position (0, 0, 0)
```

---

## Initialization

The `Init()` function sets up both loggers:

```cpp
void Log::Init()
{
    // Set the global log pattern
    spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [thread %t] [%^%l%$] %v");

    // Initialize Core Logger
    s_CoreLogger = spdlog::stdout_color_mt("VizPsyche");

    // Initialize Client Logger
    s_ClientLogger = spdlog::stdout_color_mt("Client");

    // Default log level setup
    SetCoreLogLevel(LogLevel::Trace);
    SetClientLogLevel(LogLevel::Debug);
}
```

### Understanding the Pattern

The pattern string controls output format:

| Pattern | Meaning | Example |
|---------|---------|---------|
| `%Y-%m-%d` | Date | 2024-01-15 |
| `%H:%M:%S.%e` | Time (with ms) | 10:30:45.123 |
| `%t` | Thread ID | 12345 |
| `%^%l%$` | Log level (colored) | info, warn, error |
| `%v` | The actual message | Your text here |

### stdout_color_mt

`spdlog::stdout_color_mt("name")` creates:
- A logger that outputs to **stdout**
- With **color** support
- Thread-safe (**mt** = multi-threaded)
- Named "VizPsyche" or "Client"

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

## The Logging Macros

Instead of calling the loggers directly, we use macros:

```cpp
// Core logger macros
#define VP_CORE_TRACE(...)    ::VizEngine::Log::GetCoreLogger()->trace(__VA_ARGS__)
#define VP_CORE_INFO(...)     ::VizEngine::Log::GetCoreLogger()->info(__VA_ARGS__)
#define VP_CORE_WARN(...)     ::VizEngine::Log::GetCoreLogger()->warn(__VA_ARGS__)
#define VP_CORE_ERROR(...)    ::VizEngine::Log::GetCoreLogger()->error(__VA_ARGS__)
#define VP_CORE_CRITICAL(...) ::VizEngine::Log::GetCoreLogger()->critical(__VA_ARGS__)

// Client logger macros
#define VP_TRACE(...)    ::VizEngine::Log::GetClientLogger()->trace(__VA_ARGS__)
#define VP_INFO(...)     ::VizEngine::Log::GetClientLogger()->info(__VA_ARGS__)
#define VP_WARN(...)     ::VizEngine::Log::GetClientLogger()->warn(__VA_ARGS__)
#define VP_ERROR(...)    ::VizEngine::Log::GetClientLogger()->error(__VA_ARGS__)
#define VP_CRITICAL(...) ::VizEngine::Log::GetClientLogger()->critical(__VA_ARGS__)
```

### Why Macros?

1. **Shorter code**: `VP_INFO("x")` vs `VizEngine::Log::GetClientLogger()->info("x")`
2. **Compile-time removal**: In release builds, we could `#define VP_TRACE(...)` to nothing
3. **Automatic file/line**: Could add `__FILE__` and `__LINE__` to the macro

### The `__VA_ARGS__` Magic

`__VA_ARGS__` is a special macro that captures "everything passed in":

```cpp
VP_INFO("Player {} scored {} points", name, score);
// Expands to:
::VizEngine::Log::GetClientLogger()->info("Player {} scored {} points", name, score);
```

---

## Format Strings

spdlog uses the `{fmt}` library for formatting:

```cpp
// Basic substitution
VP_INFO("Value is {}", 42);                    // Value is 42

// Multiple values
VP_INFO("{} + {} = {}", 1, 2, 3);              // 1 + 2 = 3

// Named (positional)
VP_INFO("{1} before {0}", "second", "first");  // first before second

// Formatting
VP_INFO("Hex: {:x}", 255);                     // Hex: ff
VP_INFO("Float: {:.2f}", 3.14159);             // Float: 3.14
VP_INFO("Width: {:>10}", "hi");                // Width:         hi
```

Common format specifiers:

| Specifier | Meaning | Example |
|-----------|---------|---------|
| `{:d}` | Decimal integer | 42 |
| `{:x}` | Hexadecimal | 2a |
| `{:f}` | Float | 3.140000 |
| `{:.2f}` | Float, 2 decimals | 3.14 |
| `{:>10}` | Right-align, width 10 | "        hi" |

---

## Color Output

spdlog automatically colors output by level:

| Level | Color |
|-------|-------|
| Trace | White/Gray |
| Debug | Cyan |
| Info | Green |
| Warn | Yellow |
| Error | Red |
| Critical | Red background |

This makes scanning logs much easier - errors jump out at you.

---

## Where to Log

### In Engine Code

Use `VP_CORE_*` macros:

```cpp
// GLFWManager.cpp
VP_CORE_INFO("Window created: {}x{}", width, height);
VP_CORE_ERROR("Failed to initialize GLFW");

// Shader.cpp
VP_CORE_TRACE("Compiling shader: {}", filepath);
VP_CORE_WARN("Shader uniform '{}' not found", name);
```

### In Game/Application Code

Use `VP_*` macros:

```cpp
// SandboxApp.cpp
VP_INFO("Game started");
VP_DEBUG("Current FPS: {:.1f}", fps);
VP_WARN("Health low: {}", health);
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

// Expensive formatting in hot path
VP_TRACE("Matrix: {}", expensiveToString(matrix));  // Bad: slow
```

### Log on State Changes

```cpp
// Good: log when something changes
if (newState != oldState)
{
    VP_INFO("State changed from {} to {}", oldState, newState);
}

// Bad: log every frame
VP_INFO("Current state is {}", state);  // Spammy
```

---

## Thread Safety

spdlog's `_mt` loggers are thread-safe:

```cpp
// Thread 1:
VP_CORE_INFO("From thread 1");

// Thread 2:
VP_CORE_INFO("From thread 2");

// Output is guaranteed to not be garbled
```

---

## Advanced: File Logging

You can add file output:

```cpp
#include <spdlog/sinks/basic_file_sink.h>

// Create a file sink
auto file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>("engine.log", true);

// Create logger with both console and file
auto console_sink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
std::vector<spdlog::sink_ptr> sinks {console_sink, file_sink};
auto logger = std::make_shared<spdlog::logger>("multi", sinks.begin(), sinks.end());
```

Now logs go to both console AND `engine.log`.

---

## The Static Logger Pattern

Notice our loggers are `static`:

```cpp
static std::shared_ptr<spdlog::logger> s_CoreLogger;
static std::shared_ptr<spdlog::logger> s_ClientLogger;
```

This means:
- One instance shared across all code
- Accessible without an object (`Log::GetCoreLogger()`)
- Lifetime managed by the static variable

This is a common pattern for global services like logging.

---

## Complete Usage Example

```cpp
// At engine startup
VizEngine::Log::Init();
VP_CORE_INFO("VizPsyche Engine v{}.{}", major, minor);

// During loading
VP_CORE_DEBUG("Loading shader: {}", shaderPath);
if (!shader.Compile())
{
    VP_CORE_ERROR("Shader compilation failed: {}", shader.GetError());
    return false;
}
VP_CORE_INFO("Shader compiled successfully");

// In game code
VP_INFO("Starting level {}", levelNumber);
for (auto& enemy : enemies)
{
    VP_TRACE("Spawning enemy at ({}, {}, {})", 
             enemy.pos.x, enemy.pos.y, enemy.pos.z);
}

// On error
VP_CRITICAL("Out of memory! Shutting down.");
```

---

## Key Takeaways

1. **Two loggers**: Core (engine) and Client (game)
2. **Log levels filter noise**: Use Trace/Debug in dev, Warn+ in release
3. **Macros simplify usage**: `VP_INFO("...")` is clean and short
4. **Format strings are powerful**: `{:.2f}` for floats, `{:x}` for hex
5. **Color helps scanning**: Errors are red, warnings are yellow
6. **Thread-safe by default**: `_mt` loggers handle concurrency
7. **Don't over-log**: State changes yes, every frame no

---

## Checkpoint

This chapter covered our logging system:

**Key Class:** `Log` — Static wrapper around spdlog

**Pattern:** Two loggers, two macro sets
- `VP_CORE_*` — Engine messages (internal)
- `VP_*` — Game messages (your code)

**Log Levels:** `Trace < Debug < Info < Warn < Error < Critical`

**Files:**
- `VizEngine/Log.h` — Declaration + macros
- `VizEngine/Log.cpp` — Logger initialization

**Building Along?**

Create the logging system:

1. Create **`VizEngine/src/VizEngine/Log.h`**:
   ```cpp
   #pragma once
   #include "Core.h"
   #include <spdlog/spdlog.h>
   #include <memory>

   namespace VizEngine
   {
       class VizEngine_API Log
       {
       public:
           static void Init();
           static std::shared_ptr<spdlog::logger>& GetCoreLogger() 
               { return s_CoreLogger; }
           static std::shared_ptr<spdlog::logger>& GetClientLogger() 
               { return s_ClientLogger; }
       private:
           static std::shared_ptr<spdlog::logger> s_CoreLogger;
           static std::shared_ptr<spdlog::logger> s_ClientLogger;
       };
   }

   // Core logging macros
   #define VP_CORE_INFO(...)  VizEngine::Log::GetCoreLogger()->info(__VA_ARGS__)
   #define VP_CORE_WARN(...)  VizEngine::Log::GetCoreLogger()->warn(__VA_ARGS__)
   #define VP_CORE_ERROR(...) VizEngine::Log::GetCoreLogger()->error(__VA_ARGS__)

   // Client logging macros
   #define VP_INFO(...)  VizEngine::Log::GetClientLogger()->info(__VA_ARGS__)
   #define VP_WARN(...)  VizEngine::Log::GetClientLogger()->warn(__VA_ARGS__)
   #define VP_ERROR(...) VizEngine::Log::GetClientLogger()->error(__VA_ARGS__)
   ```

2. Create **`VizEngine/src/VizEngine/Log.cpp`**:
   ```cpp
   #include "Log.h"
   #include <spdlog/sinks/stdout_color_sinks.h>

   namespace VizEngine
   {
       std::shared_ptr<spdlog::logger> Log::s_CoreLogger;
       std::shared_ptr<spdlog::logger> Log::s_ClientLogger;

       void Log::Init()
       {
           spdlog::set_pattern("%^[%T] %n: %v%$");
           s_CoreLogger = spdlog::stdout_color_mt("VIZENGINE");
           s_CoreLogger->set_level(spdlog::level::trace);
           s_ClientLogger = spdlog::stdout_color_mt("APP");
           s_ClientLogger->set_level(spdlog::level::trace);
       }
   }
   ```

3. Add to **`VizEngine/CMakeLists.txt`**:
   ```cmake
   add_library(VizEngine SHARED
       src/VizEngine/Log.cpp
       # ... other files
   )
   ```

4. Call `Log::Init()` in **`EntryPoint.h`**:
   ```cpp
   int main(int argc, char** argv)
   {
       VizEngine::Log::Init();  // Add this line
       auto app = VizEngine::CreateApplication();
       // ...
   }
   ```

5. Use logging in Sandbox:
   ```cpp
   Sandbox()
   {
       VP_INFO("Sandbox created!");
   }
   ```

6. Rebuild and run.

**✓ Success:** Colored log output appears in the console.

---

## Exercise

1. Add a new log level macro `VP_CORE_DEBUG` that's removed in release builds
2. Add file logging to capture errors to `error.log`
3. Add a timestamp to the log pattern showing milliseconds
4. Create a custom logger for a subsystem (e.g., "Physics", "Audio")

---

> **Next:** [Chapter 6: OpenGL Fundamentals](06_OpenGLFundamentals.md) - Understanding the graphics pipeline.



