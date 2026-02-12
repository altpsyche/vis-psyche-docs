\newpage

# Chapter 9: Buffer Classes

Apply the RAII patterns from Chapter 8 to create OpenGL buffer wrappers. By the end, you'll have `VertexBuffer`, `IndexBuffer`, `VertexArray`, and `VertexBufferLayout` classes.

---

## What We're Building

| Class | Purpose |
|-------|---------|
| `VertexBuffer` | Wraps VBO, stores vertex data |
| `IndexBuffer` | Wraps IBO/EBO, stores indices |
| `VertexBufferLayout` | Describes vertex attribute layout |
| `VertexArray` | Wraps VAO, links buffers to layout |

---

## Step 1: Create VertexBuffer

**Create `VizEngine/src/VizEngine/OpenGL/VertexBuffer.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/VertexBuffer.h

#pragma once

#include "VizEngine/Core.h"

namespace VizEngine
{
    class VizEngine_API VertexBuffer
    {
    public:
        VertexBuffer(const void* data, size_t size);
        ~VertexBuffer();

        // No copying
        VertexBuffer(const VertexBuffer&) = delete;
        VertexBuffer& operator=(const VertexBuffer&) = delete;

        // Allow moving
        VertexBuffer(VertexBuffer&& other) noexcept;
        VertexBuffer& operator=(VertexBuffer&& other) noexcept;

        void Bind() const;
        void Unbind() const;

        unsigned int GetID() const { return m_vbo; }

    private:
        unsigned int m_vbo = 0;
    };

}  // namespace VizEngine
```

**Create `VizEngine/src/VizEngine/OpenGL/VertexBuffer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/VertexBuffer.cpp

#include "VertexBuffer.h"
#include "Commons.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    VertexBuffer::VertexBuffer(const void* data, size_t size)
    {
        glGenBuffers(1, &m_vbo);
        glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
        glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
        VP_CORE_TRACE("VertexBuffer created: ID={}", m_vbo);
    }

    VertexBuffer::~VertexBuffer()
    {
        if (m_vbo != 0)
        {
            glDeleteBuffers(1, &m_vbo);
            VP_CORE_TRACE("VertexBuffer deleted: ID={}", m_vbo);
        }
    }

    VertexBuffer::VertexBuffer(VertexBuffer&& other) noexcept
        : m_vbo(other.m_vbo)
    {
        other.m_vbo = 0;
    }

    VertexBuffer& VertexBuffer::operator=(VertexBuffer&& other) noexcept
    {
        if (this != &other)
        {
            if (m_vbo != 0)
                glDeleteBuffers(1, &m_vbo);
            m_vbo = other.m_vbo;
            other.m_vbo = 0;
        }
        return *this;
    }

    void VertexBuffer::Bind() const
    {
        glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    }

    void VertexBuffer::Unbind() const
    {
        glBindBuffer(GL_ARRAY_BUFFER, 0);
    }

}  // namespace VizEngine
```

---

## Step 2: Create IndexBuffer

**Create `VizEngine/src/VizEngine/OpenGL/IndexBuffer.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/IndexBuffer.h

#pragma once

#include "VizEngine/Core.h"

namespace VizEngine
{
    class VizEngine_API IndexBuffer
    {
    public:
        IndexBuffer(const unsigned int* data, unsigned int count);
        ~IndexBuffer();

        // No copying
        IndexBuffer(const IndexBuffer&) = delete;
        IndexBuffer& operator=(const IndexBuffer&) = delete;

        // Allow moving
        IndexBuffer(IndexBuffer&& other) noexcept;
        IndexBuffer& operator=(IndexBuffer&& other) noexcept;

        void Bind() const;
        void Unbind() const;

        unsigned int GetCount() const { return m_Count; }
        unsigned int GetID() const { return m_ibo; }

    private:
        unsigned int m_ibo = 0;
        unsigned int m_Count = 0;
    };

}  // namespace VizEngine
```

**Create `VizEngine/src/VizEngine/OpenGL/IndexBuffer.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/IndexBuffer.cpp

#include "IndexBuffer.h"
#include "Commons.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    IndexBuffer::IndexBuffer(const unsigned int* data, unsigned int count)
        : m_Count(count)
    {
        glGenBuffers(1, &m_ibo);
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m_ibo);
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, count * sizeof(unsigned int), data, GL_STATIC_DRAW);
        VP_CORE_TRACE("IndexBuffer created: ID={}, Count={}", m_ibo, m_Count);
    }

    IndexBuffer::~IndexBuffer()
    {
        if (m_ibo != 0)
        {
            glDeleteBuffers(1, &m_ibo);
            VP_CORE_TRACE("IndexBuffer deleted: ID={}", m_ibo);
        }
    }

    IndexBuffer::IndexBuffer(IndexBuffer&& other) noexcept
        : m_ibo(other.m_ibo), m_Count(other.m_Count)
    {
        other.m_ibo = 0;
        other.m_Count = 0;
    }

    IndexBuffer& IndexBuffer::operator=(IndexBuffer&& other) noexcept
    {
        if (this != &other)
        {
            if (m_ibo != 0)
                glDeleteBuffers(1, &m_ibo);
            m_ibo = other.m_ibo;
            m_Count = other.m_Count;
            other.m_ibo = 0;
            other.m_Count = 0;
        }
        return *this;
    }

    void IndexBuffer::Bind() const
    {
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, m_ibo);
    }

    void IndexBuffer::Unbind() const
    {
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);
    }

}  // namespace VizEngine
```

---

## Step 3: Create VertexBufferLayout

Describes vertex attributes without needing OpenGL calls.

**Create `VizEngine/src/VizEngine/OpenGL/VertexBufferLayout.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/VertexBufferLayout.h

#pragma once

#include "VizEngine/Core.h"
#include <vector>
#include <glad/glad.h>

namespace VizEngine
{
    struct VertexBufferElement
    {
        unsigned int type;
        unsigned int count;
        unsigned char normalised;

        static unsigned int GetSizeOfType(unsigned int type)
        {
            switch (type)
            {
                case GL_FLOAT:         return sizeof(float);
                case GL_UNSIGNED_INT:  return sizeof(unsigned int);
                case GL_UNSIGNED_BYTE: return sizeof(unsigned char);
            }
            return 0;
        }
    };

    class VizEngine_API VertexBufferLayout
    {
    public:
        VertexBufferLayout() : m_Stride(0) {}

        template<typename T>
        void Push(unsigned int count);

        const std::vector<VertexBufferElement>& GetElements() const { return m_Elements; }
        unsigned int GetStride() const { return m_Stride; }

    private:
        std::vector<VertexBufferElement> m_Elements;
        unsigned int m_Stride;
    };

    // Template specializations
    template<>
    inline void VertexBufferLayout::Push<float>(unsigned int count)
    {
        m_Elements.push_back({ GL_FLOAT, count, GL_FALSE });
        m_Stride += count * sizeof(float);
    }

    template<>
    inline void VertexBufferLayout::Push<unsigned int>(unsigned int count)
    {
        m_Elements.push_back({ GL_UNSIGNED_INT, count, GL_FALSE });
        m_Stride += count * sizeof(unsigned int);
    }

    template<>
    inline void VertexBufferLayout::Push<unsigned char>(unsigned int count)
    {
        m_Elements.push_back({ GL_UNSIGNED_BYTE, count, GL_TRUE });
        m_Stride += count * sizeof(unsigned char);
    }

}  // namespace VizEngine
```

---

## Step 4: Create VertexArray

**Create `VizEngine/src/VizEngine/OpenGL/VertexArray.h`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/VertexArray.h

#pragma once

#include "VizEngine/Core.h"
#include "VertexBuffer.h"
#include "VertexBufferLayout.h"

namespace VizEngine
{
    class VizEngine_API VertexArray
    {
    public:
        VertexArray();
        ~VertexArray();

        // No copying
        VertexArray(const VertexArray&) = delete;
        VertexArray& operator=(const VertexArray&) = delete;

        // Allow moving
        VertexArray(VertexArray&& other) noexcept;
        VertexArray& operator=(VertexArray&& other) noexcept;

        void Bind() const;
        void Unbind() const;

        void LinkVertexBuffer(const VertexBuffer& vb, const VertexBufferLayout& layout) const;

        unsigned int GetID() const { return m_vao; }

    private:
        unsigned int m_vao = 0;
    };

}  // namespace VizEngine
```

**Create `VizEngine/src/VizEngine/OpenGL/VertexArray.cpp`:**

```cpp
// VizEngine/src/VizEngine/OpenGL/VertexArray.cpp

#include "VertexArray.h"
#include "Commons.h"
#include "VizEngine/Log.h"

namespace VizEngine
{
    VertexArray::VertexArray()
    {
        glGenVertexArrays(1, &m_vao);
        VP_CORE_TRACE("VertexArray created: ID={}", m_vao);
    }

    VertexArray::~VertexArray()
    {
        if (m_vao != 0)
        {
            glDeleteVertexArrays(1, &m_vao);
            VP_CORE_TRACE("VertexArray deleted: ID={}", m_vao);
        }
    }

    VertexArray::VertexArray(VertexArray&& other) noexcept
        : m_vao(other.m_vao)
    {
        other.m_vao = 0;
    }

    VertexArray& VertexArray::operator=(VertexArray&& other) noexcept
    {
        if (this != &other)
        {
            if (m_vao != 0)
                glDeleteVertexArrays(1, &m_vao);
            m_vao = other.m_vao;
            other.m_vao = 0;
        }
        return *this;
    }

    void VertexArray::Bind() const
    {
        glBindVertexArray(m_vao);
    }

    void VertexArray::Unbind() const
    {
        glBindVertexArray(0);
    }

    void VertexArray::LinkVertexBuffer(const VertexBuffer& vb, const VertexBufferLayout& layout) const
    {
        Bind();
        vb.Bind();

        const auto& elements = layout.GetElements();
        size_t offset = 0;

        for (unsigned int i = 0; i < elements.size(); i++)
        {
            const auto& element = elements[i];
            glEnableVertexAttribArray(i);
            glVertexAttribPointer(
                i,
                element.count,
                element.type,
                element.normalised,
                layout.GetStride(),
                reinterpret_cast<const void*>(offset)
            );
            offset += element.count * VertexBufferElement::GetSizeOfType(element.type);
        }
    }

}  // namespace VizEngine
```

---

## Step 5: Update CMakeLists.txt

**Update `VizEngine/CMakeLists.txt` to add the new files:**

```cmake
set(VIZENGINE_SOURCES
    src/VizEngine/Application.cpp
    src/VizEngine/Log.cpp
    # OpenGL
    src/VizEngine/OpenGL/ErrorHandling.cpp
    src/VizEngine/OpenGL/GLFWManager.cpp
    src/VizEngine/OpenGL/VertexBuffer.cpp    # NEW
    src/VizEngine/OpenGL/IndexBuffer.cpp     # NEW
    src/VizEngine/OpenGL/VertexArray.cpp     # NEW
    src/glad.c
)

set(VIZENGINE_HEADERS
    src/VizEngine.h
    src/VizEngine/Application.h
    src/VizEngine/Core.h
    src/VizEngine/EntryPoint.h
    src/VizEngine/Log.h
    # OpenGL
    src/VizEngine/OpenGL/Commons.h
    src/VizEngine/OpenGL/ErrorHandling.h
    src/VizEngine/OpenGL/GLFWManager.h
    src/VizEngine/OpenGL/VertexBuffer.h       # NEW
    src/VizEngine/OpenGL/IndexBuffer.h        # NEW
    src/VizEngine/OpenGL/VertexArray.h        # NEW
    src/VizEngine/OpenGL/VertexBufferLayout.h # NEW
    include/glad/glad.h
    include/KHR/khrplatform.h
)
```

---

## Step 6: Usage Example

```cpp
// Create vertex data
float vertices[] = {
    // Position          Color
    -0.5f, -0.5f, 0.0f,  1.0f, 0.0f, 0.0f,
     0.5f, -0.5f, 0.0f,  0.0f, 1.0f, 0.0f,
     0.5f,  0.5f, 0.0f,  0.0f, 0.0f, 1.0f,
    -0.5f,  0.5f, 0.0f,  1.0f, 1.0f, 0.0f,
};

unsigned int indices[] = {
    0, 1, 2,
    2, 3, 0
};

// Create buffer objects
VertexBuffer vbo(vertices, sizeof(vertices));
IndexBuffer ibo(indices, 6);

// Define layout
VertexBufferLayout layout;
layout.Push<float>(3);  // Position
layout.Push<float>(3);  // Color

// Create and configure VAO
VertexArray vao;
vao.LinkVertexBuffer(vbo, layout);

// Later, to draw:
vao.Bind();
ibo.Bind();
glDrawElements(GL_TRIANGLES, ibo.GetCount(), GL_UNSIGNED_INT, 0);
```

---

## Project Structure After This Chapter

```
VizEngine/src/VizEngine/OpenGL/
├── Commons.h
├── ErrorHandling.cpp
├── ErrorHandling.h
├── GLFWManager.cpp
├── GLFWManager.h
├── IndexBuffer.cpp      # NEW
├── IndexBuffer.h        # NEW
├── VertexArray.cpp      # NEW
├── VertexArray.h        # NEW
├── VertexBuffer.cpp     # NEW
├── VertexBuffer.h       # NEW
└── VertexBufferLayout.h # NEW
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Nothing renders | VAO not bound | Call `vao.Bind()` before draw |
| Crash after move | Using moved-from object | Don't use object after `std::move` |
| Attributes wrong | Layout doesn't match data | Verify Push order matches vertex struct |

---

## Milestone

**Buffer Classes Complete**

You have:
- RAII-compliant `VertexBuffer`
- RAII-compliant `IndexBuffer`
- `VertexBufferLayout` for describing attributes
- `VertexArray` that links them together

---

## What's Next

In **Chapter 10**, we'll create a `Shader` class for compiling and managing GLSL programs.

> **Next:** [Chapter 10: Shader System](10_ShaderAndRenderer.md)

> **Previous:** [Chapter 8: RAII & Resource Management](08_RAIIAndResourceManagement.md)
