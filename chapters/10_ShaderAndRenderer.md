\newpage

# Chapter 10: Shader System

Create a `Shader` class that handles loading, compiling, and using GLSL shader programs.

---

## What We're Building

| Feature | Purpose |
|---------|---------|
| File parsing | Load vertex/fragment shaders from one file |
| Compilation | Compile and link shader program |
| Error reporting | Log detailed shader errors |
| Uniform caching | Cache uniform locations for performance |

---

## Shader File Format

Use a single file with markers:

## Step 1: Create Shader.h

**Create `resources/shaders/unlit.shader`:**

```glsl
#shader vertex
#version 460 core

layout (location = 0) in vec4 aPos;       // Position (w=1)
layout (location = 1) in vec3 aNormal;    // Normal (unused in unlit)
layout (location = 2) in vec4 aColor;     // Vertex color
layout (location = 3) in vec2 aTexCoord;  // Texture coords

out vec4 v_Color;
out vec2 v_TexCoord;

uniform mat4 u_MVP;

void main()
{
    gl_Position = u_MVP * aPos;
    v_Color = aColor;
    v_TexCoord = aTexCoord;
}

#shader fragment
#version 460 core

in vec4 v_Color;
in vec2 v_TexCoord;
out vec4 FragColor;

uniform vec4 u_ObjectColor;
uniform sampler2D u_MainTex;

void main()
{
    // Sample texture and multiply with vertex color and object color
    vec4 texColor = texture(u_MainTex, v_TexCoord);
    FragColor = texColor * v_Color * u_ObjectColor;
}
```

---

## Step 2: Create Shader.h

**Create `VizEngine/src/VizEngine/OpenGL/Shader.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Shader.h

#pragma once

#include <glad/glad.h>
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <unordered_map>
#include "glm.hpp"
#include "VizEngine/Core.h"

namespace VizEngine
{
    struct ShaderPrograms
    {
        std::string VertexProgram;
        std::string FragmentProgram;
    };

    class VizEngine_API Shader
    {
    public:
        Shader(const std::string& shaderFile);
        ~Shader();

        // No copying
        Shader(const Shader&) = delete;
        Shader& operator=(const Shader&) = delete;

        // Allow moving
        Shader(Shader&& other) noexcept;
        Shader& operator=(Shader&& other) noexcept;

        void Bind() const;
        void Unbind() const;

        // Validation
        bool IsValid() const { return m_program != 0; }

        // Uniform setters
        void SetBool(const std::string& name, bool value);
        void SetInt(const std::string& name, int value);
        void SetFloat(const std::string& name, float value);
        void SetVec3(const std::string& name, const glm::vec3& value);
        void SetVec4(const std::string& name, const glm::vec4& value);
        void SetColor(const std::string& name, const glm::vec4& value);
        void SetMatrix4fv(const std::string& name, const glm::mat4& matrix);

    private:
        std::string m_shaderPath;
        unsigned int m_program;
        std::unordered_map<std::string, int> m_LocationCache;

        ShaderPrograms ShaderParser(const std::string& shaderFile);
        unsigned int CompileShader(unsigned int type, const std::string& source);
        unsigned int CreateShader(const std::string& vert, const std::string& frag);
        int GetUniformLocation(const std::string& name);
        // Returns true on success, false on error
        bool CheckCompileErrors(unsigned int shader, std::string type);
    };
}
```

> [!NOTE]
> The main matrix uniform setter is `SetMatrix4fv()` (not `SetMat4`). Use `SetVec3` and `SetVec4` for vectors.

---

## Step 3: Create Shader.cpp

**Create `VizEngine/src/VizEngine/OpenGL/Shader.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Shader.cpp

#include "Shader.h"
#include "VizEngine/Log.h"
#include <stdexcept>
#include <gtc/type_ptr.hpp>

namespace VizEngine
{
    Shader::Shader(const std::string& shaderFile)
        : m_shaderPath(shaderFile), m_program(0)
    {
        // Parse the shader file
        ShaderPrograms sources = ShaderParser(shaderFile);
        if (sources.VertexProgram.empty() || sources.FragmentProgram.empty())
        {
            VP_CORE_ERROR("Failed to parse shader file: {}", shaderFile);
            throw std::runtime_error("Failed to parse shader: " + shaderFile);
        }
        
        // Compile and link
        m_program = CreateShader(sources.VertexProgram, sources.FragmentProgram);
        if (m_program == 0)
        {
            VP_CORE_ERROR("Failed to compile/link shader: {}", shaderFile);
            throw std::runtime_error("Failed to compile shader: " + shaderFile);
        }
        
        VP_CORE_INFO("Shader created: {} (ID={})", shaderFile, m_program);
    }
```

> [!IMPORTANT]
> The Shader constructor throws `std::runtime_error` if parsing or compilation fails. This follows the RAII principle: an object should be valid if construction succeeds. Callers should use try-catch or let the exception propagate.

```cpp
    Shader::~Shader()
    {
        if (m_program != 0)
        {
            glDeleteProgram(m_program);
            VP_CORE_TRACE("Shader deleted: {}", m_shaderPath);
        }
    }

    Shader::Shader(Shader&& other) noexcept
        : m_shaderPath(std::move(other.m_shaderPath))
        , m_program(other.m_program)
        , m_LocationCache(std::move(other.m_LocationCache))
    {
        other.m_program = 0;
    }

    Shader& Shader::operator=(Shader&& other) noexcept
    {
        if (this != &other)
        {
            if (m_program != 0)
                glDeleteProgram(m_program);

            m_shaderPath = std::move(other.m_shaderPath);
            m_program = other.m_program;
            m_LocationCache = std::move(other.m_LocationCache);
            other.m_program = 0;
        }
        return *this;
    }

    void Shader::Bind() const { glUseProgram(m_program); }
    void Shader::Unbind() const { glUseProgram(0); }

    ShaderPrograms Shader::ShaderParser(const std::string& shaderFile)
    {
        std::ifstream file(shaderFile);
        if (!file.is_open())
        {
            VP_CORE_ERROR("Failed to open shader: {}", shaderFile);
            return {};
        }

        enum class ShaderType { None = -1, Vertex = 0, Fragment = 1 };
        ShaderType type = ShaderType::None;

        std::stringstream ss[2];
        std::string line;

        while (std::getline(file, line))
        {
            if (line.find("#shader") != std::string::npos)
            {
                if (line.find("vertex") != std::string::npos)
                    type = ShaderType::Vertex;
                else if (line.find("fragment") != std::string::npos)
                    type = ShaderType::Fragment;
            }
            else if (type != ShaderType::None)
            {
                ss[int(type)] << line << '\n';
            }
        }

        return { ss[0].str(), ss[1].str() };
    }

    unsigned int Shader::CompileShader(unsigned int type, const std::string& source)
    {
        unsigned int shader = glCreateShader(type);
        const char* src = source.c_str();
        glShaderSource(shader, 1, &src, nullptr);
        glCompileShader(shader);

        int success;
        glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
        if (!success)
        {
            CheckCompileErrors(shader, type == GL_VERTEX_SHADER ? "VERTEX" : "FRAGMENT");
            glDeleteShader(shader);
            return 0;
        }
        return shader;
    }

    unsigned int Shader::CreateShader(const std::string& vert, const std::string& frag)
    {
        unsigned int program = glCreateProgram();

        unsigned int vs = CompileShader(GL_VERTEX_SHADER, vert);
        if (!CheckCompileErrors(vs, "VERTEX"))
        {
            glDeleteShader(vs);
            glDeleteProgram(program);
            return 0;
        }

        unsigned int fs = CompileShader(GL_FRAGMENT_SHADER, frag);
        if (!CheckCompileErrors(fs, "FRAGMENT"))
        {
            glDeleteShader(vs);
            glDeleteShader(fs);
            glDeleteProgram(program);
            return 0;
        }

        glAttachShader(program, vs);
        glAttachShader(program, fs);
        glLinkProgram(program);

        // Cleanup shader objects (attached to program, no longer needed)
        glDeleteShader(vs);
        glDeleteShader(fs);

        if (!CheckCompileErrors(program, "PROGRAM"))
        {
            glDeleteProgram(program);
            return 0;
        }

        return program;
    }

    int Shader::GetUniformLocation(const std::string& name)
    {
        auto it = m_LocationCache.find(name);
        if (it != m_LocationCache.end())
            return it->second;

        int location = glGetUniformLocation(m_program, name.c_str());
        if (location == -1)
            VP_CORE_WARN("Uniform '{}' not found", name);

        m_LocationCache[name] = location;
        return location;
    }

    // Returns true on success, false on error
    bool Shader::CheckCompileErrors(unsigned int shader, std::string type)
    {
        int success;
        char infoLog[1024];
        if (type != "PROGRAM")
        {
            glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
            if (!success)
            {
                glGetShaderInfoLog(shader, 1024, NULL, infoLog);
                VP_CORE_ERROR("{} Shader Error:\n{}", type, infoLog);
                return false;
            }
        }
        else
        {
            glGetProgramiv(shader, GL_LINK_STATUS, &success);
            if (!success)
            {
                glGetProgramInfoLog(shader, 1024, NULL, infoLog);
                VP_CORE_ERROR("Shader Linking Error:\n{}", infoLog);
                return false;
            }
        }
        return true;
    }

    void Shader::SetBool(const std::string& name, bool value)
    {
        glUniform1i(GetUniformLocation(name), (int)value);
    }

    void Shader::SetInt(const std::string& name, int value)
    {
        glUniform1i(GetUniformLocation(name), value);
    }

    void Shader::SetFloat(const std::string& name, float value)
    {
        glUniform1f(GetUniformLocation(name), value);
    }

    void Shader::SetVec3(const std::string& name, const glm::vec3& value)
    {
        glUniform3fv(GetUniformLocation(name), 1, glm::value_ptr(value));
    }

    void Shader::SetVec4(const std::string& name, const glm::vec4& value)
    {
        glUniform4fv(GetUniformLocation(name), 1, glm::value_ptr(value));
    }

    void Shader::SetColor(const std::string& name, const glm::vec4& value)
    {
        SetVec4(name, value);
    }

    void Shader::SetMatrix4fv(const std::string& name, const glm::mat4& matrix)
    {
        glUniformMatrix4fv(GetUniformLocation(name), 1, GL_FALSE, glm::value_ptr(matrix));
    }

}  // namespace VizEngine
```

---

## Usage Example

```cpp
Shader shader("resources/shaders/defaultlit.shader");

// In render loop
shader.Bind();
shader.SetMatrix4fv("u_MVP", mvpMatrix);
shader.SetVec4("u_Color", glm::vec4(1.0f));
shader.SetInt("u_UseTexture", 0);
shader.SetVec3("u_LightDirection", light.GetDirection());

// Draw calls...
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "Shader not found" | Wrong filepath | Use path relative to executable |
| Uniform warning | Typo in uniform name | Check shader source matches C++ |
| Black output | Shader not bound | Call `shader.Bind()` before draw |

---

## Milestone

**Shader System Complete**

You have:
- Combined shader file format
- Shader parsing and compilation
- Uniform location caching
- `SetMatrix4fv`, `SetVec3`, `SetVec4`, etc.

---

## What's Next

In **Chapter 11**, we'll add texture support with `stb_image`.

> **Next:** [Chapter 11: Texture System](11_Textures.md)

> **Previous:** [Chapter 9: Buffer Classes](09_BufferClasses.md)

