\newpage

# Chapter 9: Shader & Renderer

## The Shader System

Shaders are programs that run on the GPU. We need to load, compile, and manage them.

> [!NOTE]
> **Prerequisites:** [Chapter 7](07_RAIIAndResourceManagement.md) (RAII) and [Chapter 8](08_BufferClasses.md) (Buffer classes).

---

## Combined Shader Files

We use a single file with both vertex and fragment shaders:

```glsl
// resources/shaders/basic.shader

#shader vertex
#version 460 core
layout (location = 0) in vec4 aPos;
layout (location = 1) in vec4 aColor;
layout (location = 2) in vec2 aTexCoord;

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

uniform sampler2D u_Texture;

void main()
{
    FragColor = texture(u_Texture, v_TexCoord) * v_Color;
}
```

**Why combined files?**
- Easy to see vertex/fragment together
- Single file to manage
- Clear separation with `#shader` tags

---

## The Shader Class

```cpp
// VizEngine/OpenGL/Shader.h

class VizEngine_API Shader
{
public:
    Shader(const std::string& filepath);
    ~Shader();
    
    // Rule of 5 (delete copy, allow move)
    
    void Bind() const;
    void Unbind() const;
    
    // Uniform setters
    void SetInt(const std::string& name, int value);
    void SetFloat(const std::string& name, float value);
    void SetVec3(const std::string& name, const glm::vec3& value);
    void SetVec4(const std::string& name, const glm::vec4& value);
    void SetMatrix4fv(const std::string& name, const glm::mat4& matrix);
    
private:
    unsigned int m_RendererID = 0;
    std::string m_FilePath;
    std::unordered_map<std::string, int> m_LocationCache;
    
    ShaderPrograms ParseShader(const std::string& filepath);
    unsigned int CompileShader(unsigned int type, const std::string& source);
    unsigned int CreateProgram(const std::string& vertexSrc, const std::string& fragmentSrc);
    int GetUniformLocation(const std::string& name);
};
```

---

## Shader Parsing

```cpp
struct ShaderPrograms
{
    std::string VertexSource;
    std::string FragmentSource;
};

ShaderPrograms Shader::ParseShader(const std::string& filepath)
{
    std::ifstream file(filepath);
    if (!file.is_open())
    {
        VP_CORE_ERROR("Failed to open shader: {}", filepath);
        return {};
    }
    
    std::stringstream ss[2];  // [0] = vertex, [1] = fragment
    enum class ShaderType { NONE = -1, VERTEX = 0, FRAGMENT = 1 };
    ShaderType type = ShaderType::NONE;
    
    std::string line;
    while (getline(file, line))
    {
        if (line.find("#shader") != std::string::npos)
        {
            if (line.find("vertex") != std::string::npos)
                type = ShaderType::VERTEX;
            else if (line.find("fragment") != std::string::npos)
                type = ShaderType::FRAGMENT;
        }
        else if (type != ShaderType::NONE)
        {
            ss[(int)type] << line << '\n';
        }
    }
    
    return { ss[0].str(), ss[1].str() };
}
```

---

## Shader Compilation

```cpp
unsigned int Shader::CompileShader(unsigned int type, const std::string& source)
{
    unsigned int id = glCreateShader(type);
    const char* src = source.c_str();
    glShaderSource(id, 1, &src, nullptr);
    glCompileShader(id);
    
    // Check for errors
    int success;
    glGetShaderiv(id, GL_COMPILE_STATUS, &success);
    if (!success)
    {
        char infoLog[512];
        glGetShaderInfoLog(id, 512, nullptr, infoLog);
        VP_CORE_ERROR("Shader compilation failed: {}", infoLog);
        glDeleteShader(id);
        return 0;
    }
    
    return id;
}

unsigned int Shader::CreateProgram(const std::string& vertexSrc, 
                                    const std::string& fragmentSrc)
{
    unsigned int program = glCreateProgram();
    unsigned int vs = CompileShader(GL_VERTEX_SHADER, vertexSrc);
    unsigned int fs = CompileShader(GL_FRAGMENT_SHADER, fragmentSrc);
    
    glAttachShader(program, vs);
    glAttachShader(program, fs);
    glLinkProgram(program);
    
    // Check link status
    int success;
    glGetProgramiv(program, GL_LINK_STATUS, &success);
    if (!success)
    {
        char infoLog[512];
        glGetProgramInfoLog(program, 512, nullptr, infoLog);
        VP_CORE_ERROR("Shader linking failed: {}", infoLog);
    }
    
    // Shaders are linked, can delete
    glDeleteShader(vs);
    glDeleteShader(fs);
    
    return program;
}
```

---

## Uniform Caching

Getting uniform locations is expensive. We cache them:

```cpp
int Shader::GetUniformLocation(const std::string& name)
{
    // Check cache first
    if (m_LocationCache.find(name) != m_LocationCache.end())
        return m_LocationCache[name];
    
    // Not cached, query OpenGL
    int location = glGetUniformLocation(m_RendererID, name.c_str());
    
    if (location == -1)
        VP_CORE_WARN("Uniform '{}' not found in shader", name);
    
    m_LocationCache[name] = location;
    return location;
}

void Shader::SetMatrix4fv(const std::string& name, const glm::mat4& matrix)
{
    int location = GetUniformLocation(name);
    glUniformMatrix4fv(location, 1, GL_FALSE, glm::value_ptr(matrix));
}
```

---

## The Renderer Class

Centralizes all draw operations:

```cpp
// VizEngine/OpenGL/Renderer.h

class VizEngine_API Renderer
{
public:
    void Clear(const glm::vec4& color) const
    {
        glClearColor(color.r, color.g, color.b, color.a);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    }
    
    void Draw(const VertexArray& va, const IndexBuffer& ib, 
              const Shader& shader) const
    {
        shader.Bind();
        va.Bind();
        glDrawElements(GL_TRIANGLES, ib.GetCount(), GL_UNSIGNED_INT, nullptr);
    }
};
```

### Why a Renderer Class?

| Without Renderer | With Renderer |
|------------------|---------------|
| `glClearColor(...)` + `glClear(...)` | `renderer.Clear(color)` |
| Manual VAO bind + `glDrawElements(...)` | `renderer.Draw(vao, ibo, shader)` |
| OpenGL calls scattered everywhere | One place for all draw logic |

**Future benefits:**
- Draw call counting (profiling)
- Automatic state management
- Batching optimization

---

## Complete Usage Example

```cpp
// Setup
VertexArray vao;
VertexBuffer vbo(vertices, sizeof(vertices));
IndexBuffer ibo(indices, indexCount);

VertexBufferLayout layout;
layout.Push<float>(4);  // Position
layout.Push<float>(4);  // Color
layout.Push<float>(2);  // TexCoords
vao.LinkVertexBuffer(vbo, layout);

Shader shader("resources/shaders/basic.shader");
Renderer renderer;

// Render loop
while (!window.ShouldClose())
{
    renderer.Clear({ 0.1f, 0.1f, 0.1f, 1.0f });
    
    shader.SetMatrix4fv("u_MVP", camera.GetViewProjectionMatrix());
    renderer.Draw(vao, ibo, shader);
    
    window.SwapBuffers();
}
```

---

## Common Pitfalls

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Uniform not found" warning | Typo in uniform name | Match shader exactly |
| Black screen | Shader compile error | Check console for errors |
| Shader link failed | Mismatched in/out | Verify vertex→fragment flow |
| Performance issues | Querying uniforms every frame | Use location caching |

---

## Key Takeaways

1. **Combined shader files** - One file, `#shader` tags to separate
2. **Compile + Link** - Two-step process with error checking
3. **Uniform caching** - Cache locations for performance
4. **Renderer class** - Centralizes draw operations
5. **All use RAII** - Shader cleanup is automatic

---

## Checkpoint

**Files:**
| File | Purpose |
|------|---------|
| `VizEngine/OpenGL/Shader.h/.cpp` | Shader loading and uniforms |
| `VizEngine/OpenGL/Renderer.h/.cpp` | Draw call management |

**Checkpoint:** Create Shader and Renderer classes, render a textured triangle.

---

## Exercise

1. Add `SetVec2` and `SetMat3` uniform methods
2. Implement shader hot-reloading (detect file changes, recompile)
3. Create a `ShaderLibrary` class to cache loaded shaders by name

---

> **Next:** [Chapter 10: Textures](10_Textures.md) - Loading and using images on the GPU.

> **Previous:** [Chapter 8: Buffer Classes](08_BufferClasses.md)

