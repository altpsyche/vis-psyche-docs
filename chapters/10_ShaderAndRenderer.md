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

**Example: `resources/shaders/basic.shader`**

```glsl
#shader vertex
#version 460 core

layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;

out vec3 vertexColor;

uniform mat4 u_MVP;

void main()
{
    gl_Position = u_MVP * vec4(aPos, 1.0);
    vertexColor = aColor;
}

#shader fragment
#version 460 core

in vec3 vertexColor;
out vec4 FragColor;

void main()
{
    FragColor = vec4(vertexColor, 1.0);
}
```

---

## Step 1: Create Shader.h

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
        unsigned int m_RendererID;
        std::unordered_map<std::string, int> m_LocationCache;

        ShaderPrograms ShaderParser(const std::string& shaderFile);
        unsigned int CompileShader(unsigned int type, const std::string& source);
        unsigned int CreateShader(const std::string& vert, const std::string& frag);
        int GetUniformLocation(const std::string& name);
        void CheckCompileErrors(unsigned int shader, std::string type);
    };
}
```

> [!NOTE]
> The main matrix uniform setter is `SetMatrix4fv()` (not `SetMat4`). Use `SetVec3` and `SetVec4` for vectors.

---

## Step 2: Create Shader.cpp

**Create `VizEngine/src/VizEngine/OpenGL/Shader.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/Shader.cpp

#include "Shader.h"
#include "VizEngine/Log.h"
#include <gtc/type_ptr.hpp>

namespace VizEngine
{
    Shader::Shader(const std::string& shaderFile)
        : m_shaderPath(shaderFile), m_RendererID(0)
    {
        ShaderPrograms sources = ShaderParser(shaderFile);
        m_RendererID = CreateShader(sources.VertexProgram, sources.FragmentProgram);
        VP_CORE_INFO("Shader created: {} (ID={})", shaderFile, m_RendererID);
    }

    Shader::~Shader()
    {
        if (m_RendererID != 0)
        {
            glDeleteProgram(m_RendererID);
            VP_CORE_TRACE("Shader deleted: {}", m_shaderPath);
        }
    }

    Shader::Shader(Shader&& other) noexcept
        : m_shaderPath(std::move(other.m_shaderPath))
        , m_RendererID(other.m_RendererID)
        , m_LocationCache(std::move(other.m_LocationCache))
    {
        other.m_RendererID = 0;
    }

    Shader& Shader::operator=(Shader&& other) noexcept
    {
        if (this != &other)
        {
            if (m_RendererID != 0)
                glDeleteProgram(m_RendererID);

            m_shaderPath = std::move(other.m_shaderPath);
            m_RendererID = other.m_RendererID;
            m_LocationCache = std::move(other.m_LocationCache);
            other.m_RendererID = 0;
        }
        return *this;
    }

    void Shader::Bind() const { glUseProgram(m_RendererID); }
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
        unsigned int fs = CompileShader(GL_FRAGMENT_SHADER, frag);

        glAttachShader(program, vs);
        glAttachShader(program, fs);
        glLinkProgram(program);

        int success;
        glGetProgramiv(program, GL_LINK_STATUS, &success);
        if (!success)
            CheckCompileErrors(program, "PROGRAM");

        glDeleteShader(vs);
        glDeleteShader(fs);

        return program;
    }

    int Shader::GetUniformLocation(const std::string& name)
    {
        auto it = m_LocationCache.find(name);
        if (it != m_LocationCache.end())
            return it->second;

        int location = glGetUniformLocation(m_RendererID, name.c_str());
        if (location == -1)
            VP_CORE_WARN("Uniform '{}' not found", name);

        m_LocationCache[name] = location;
        return location;
    }

    void Shader::CheckCompileErrors(unsigned int shader, std::string type)
    {
        char infoLog[1024];
        if (type != "PROGRAM")
        {
            glGetShaderInfoLog(shader, 1024, NULL, infoLog);
            VP_CORE_ERROR("{} Shader Error:\n{}", type, infoLog);
        }
        else
        {
            glGetProgramInfoLog(shader, 1024, NULL, infoLog);
            VP_CORE_ERROR("Shader Linking Error:\n{}", infoLog);
        }
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
Shader shader("resources/shaders/lit.shader");

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
