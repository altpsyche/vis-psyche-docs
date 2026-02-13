\newpage

# Chapter 43: Scene Renderer Architecture

Extract the monolithic render pipeline from SandboxApp into a composable SceneRenderer with swappable render paths, preparing for Forward+, Deferred, and screen-space effects.

---

## Introduction

In **Chapter 42**, we built a Material System that encapsulates shaders, parameters, and textures. Our PBRMaterial provides a clean `Bind()` interface for surface properties. But there's a bigger problem: **SandboxApp.cpp is 1660 lines** and growing.

**The problem**: All rendering logic lives in one monolithic `OnRender()` method:

```cpp
void Sandbox::OnRender()
{
    // Shadow pass (~40 lines)
    m_ShadowFramebuffer->Bind();
    // ... shadow map generation ...

    // Main render pass (~80 lines)
    m_HDRFramebuffer->Bind();
    m_DefaultLitShader->Bind();
    // ... camera, lights, IBL, per-object uniforms ...

    // Skybox (~5 lines)
    m_Skybox->Render(m_Camera);

    // Stencil outlines (~50 lines)
    // ... two-pass stencil buffer technique ...

    // Post-processing (~30 lines)
    // ... bloom, tone mapping, color grading ...

    // Offscreen preview (~40 lines)
    // ... mini framebuffer for ImGui viewport ...
}
```

**Consequences**:
- **Can't swap rendering strategies**: Want to try Deferred shading? Rewrite everything.
- **Code duplication**: Forward+, Deferred, and Forward all need shadow passes and post-processing.
- **Scaling problems**: Adding SSAO, SSR, or depth prepass means more code in one giant function.
- **Testing difficulty**: Can't test individual passes in isolation.

**The solution**: A **SceneRenderer** orchestrator with a **Strategy Pattern** for swappable render paths:

```cpp
// Before: 1660 lines in SandboxApp
void OnRender() {
    // Shadow pass...
    // Main render...
    // Skybox...
    // Outlines...
    // Post-processing...
}

// After: SceneRenderer handles everything
void OnRender() {
    m_SceneRenderer->Render(m_Scene, m_Camera, renderer);
}
```

---

## What We're Building

By the end of this chapter, you'll have:

| Feature | Description |
|---------|-------------|
| **SceneRenderer** | Central orchestrator composing all rendering passes |
| **RenderPath** | Abstract base class for swappable rendering strategies |
| **ForwardRenderPath** | Concrete forward rendering path (refactored from SandboxApp) |
| **ShadowPass** | Extracted shadow map generation with its own FBO and shader |
| **PostProcessPipeline** | Composes Bloom + Tone Mapping + Color Grading |
| **RenderPassData** | Shared data structures for the multi-pass pipeline |
| **Framebuffer MRT Support** | `SetDrawBuffers()` for Multiple Render Targets |
| **Renderer const fix** | `Clear()` accepts `const float[]` for safe pass data usage |
| **Reduced SandboxApp** | From ~1660 lines to ~970 lines (scene setup + UI only) |

**Architectural Impact**: This chapter establishes the rendering architecture for all of Part XII. Every future rendering technique (Forward+, Deferred, SSAO, SSR) plugs into this framework as either a new `RenderPath` or a new pass in the `SceneRenderer` pipeline.

---

## Design Goals

### The Strategy Pattern

The core idea is **polymorphic render paths**. The SceneRenderer doesn't know *how* the scene is rendered—it delegates to whichever `RenderPath` is active:

```
SceneRenderer (orchestrator)
    │
    ├── ShadowPass::Process()           → ShadowData
    │
    ├── RenderPath::Execute(data)       → HDR framebuffer
    │       ├── ForwardRenderPath          (Chapter 43)
    │       ├── ForwardPlusRenderPath      (Chapter 46)
    │       └── DeferredRenderPath         (Chapter 47)
    │
    ├── Skybox::Render()                → Skybox on HDR buffer
    │
    ├── RenderStencilOutline()          → Stencil outlines
    │
    └── PostProcessPipeline::Process()  → Screen output
```

**Frame execution order**:
1. Shadow pass (shared across all paths)
2. Main render path (polymorphic dispatch)
3. Skybox
4. Stencil outlines
5. Post-processing (Bloom → Tone Mapping → Color Grading)

### Separation of Concerns

A key architectural decision: **materials own surface properties, renderers own transforms and lighting**.

| Concern | Owner | Set Via |
|---------|-------|---------|
| Albedo, metallic, roughness | `PBRMaterial` | `material->SetAlbedo()` |
| Texture bindings (IBL, shadow) | `PBRMaterial` | `material->SetIrradianceMap()` |
| Model, view, projection matrices | Renderer | `shader->SetMatrix4fv()` |
| Camera position | Renderer | `shader->SetVec3()` |
| Light positions and colors | Renderer | `shader->SetVec3()` |
| Light-space matrix | Renderer | `shader->SetMatrix4fv()` |

This separation prevents bugs (e.g., storing a `mat4` for a `mat3` uniform in the material's variant map) and keeps PBRMaterial focused on what it represents: surface appearance.

---

## Step 1: Create RenderPassData

The data structs define the contract between SceneRenderer and RenderPath. Everything a render path needs is packed into a single struct.

**Create** `VizEngine/src/VizEngine/Renderer/RenderPassData.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/RenderPassData.h
// Chapter 43: Shared data structures for the multi-pass rendering pipeline.

#pragma once

#include "VizEngine/Core.h"
#include "glm.hpp"
#include <memory>

namespace VizEngine
{
	class Scene;
	class Camera;
	class Renderer;
	class Framebuffer;
	class Texture;
	class Shader;
	class PBRMaterial;
	class Skybox;
	class FullscreenQuad;
	struct DirectionalLight;

	/**
	 * Output from the shadow mapping pass.
	 */
	struct ShadowData
	{
		std::shared_ptr<Texture> ShadowMap;
		glm::mat4 LightSpaceMatrix = glm::mat4(1.0f);
		bool Valid = false;
	};

	/**
	 * Output from the depth/normal prepass (used by Forward+ and screen-space effects).
	 */
	struct PrepassOutput
	{
		std::shared_ptr<Texture> DepthTexture;
		std::shared_ptr<Texture> NormalTexture;
		bool Valid = false;
	};

	/**
	 * Render path type enumeration for runtime switching.
	 */
	enum class RenderPathType
	{
		Forward,
		ForwardPlus,
		Deferred
	};

	/**
	 * All data needed by a render path to execute its main pass.
	 * Passed by the SceneRenderer orchestrator to the active RenderPath.
	 */
	struct RenderPassData
	{
		// Scene data
		Scene* ScenePtr = nullptr;
		Camera* CameraPtr = nullptr;
		Renderer* RendererPtr = nullptr;

		// Shared resources
		ShadowData Shadow;
		PrepassOutput* Prepass = nullptr;

		// Target framebuffer for HDR output
		std::shared_ptr<Framebuffer> TargetFramebuffer;

		// Shared rendering resources
		std::shared_ptr<PBRMaterial> Material;
		std::shared_ptr<Shader> DefaultLitShader;
		std::shared_ptr<Shader> InstancedShader;
		std::shared_ptr<FullscreenQuad> Quad;

		// IBL resources
		std::shared_ptr<Texture> IrradianceMap;
		std::shared_ptr<Texture> PrefilteredMap;
		std::shared_ptr<Texture> BRDFLut;
		bool UseIBL = false;
		float IBLIntensity = 0.3f;

		// Light data (forward path uses these directly)
		DirectionalLight* DirLight = nullptr;
		glm::vec3* PointLightPositions = nullptr;
		glm::vec3* PointLightColors = nullptr;
		int PointLightCount = 0;

		// Lower hemisphere fallback
		glm::vec3 LowerHemisphereColor = glm::vec3(0.15f, 0.15f, 0.2f);
		float LowerHemisphereIntensity = 0.5f;

		// Clear color
		float ClearColor[4] = { 0.1f, 0.1f, 0.15f, 1.0f };
	};
}
```

> [!NOTE]
> `RenderPassData` uses raw pointers for Scene, Camera, and Renderer because these are owned by SandboxApp with lifetimes that outlive any single frame. `shared_ptr` is used for GPU resources (textures, framebuffers) that need reference counting. `PrepassOutput` is a pointer because it's optional—only set when a depth/normal prepass has been run. `InstancedShader` is passed through so render paths can draw instanced objects (see `ForwardRenderPath::RenderInstancedObject`).

---

## Step 2: Create RenderPath Abstract Base Class

The abstract base defines the interface that all rendering strategies must implement.

**Create** `VizEngine/src/VizEngine/Renderer/RenderPath.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/RenderPath.h
// Chapter 43: Abstract base class for rendering strategies (Forward, Forward+, Deferred).

#pragma once

#include "VizEngine/Core.h"
#include "RenderPassData.h"

namespace VizEngine
{
	/**
	 * Abstract base class for rendering paths.
	 * Each derived class implements a different rendering strategy.
	 * The SceneRenderer orchestrator delegates the main render pass to the active path.
	 */
	class VizEngine_API RenderPath
	{
	public:
		virtual ~RenderPath() = default;

		/**
		 * Initialize path-specific resources.
		 * Called when the path becomes active.
		 * @param width Framebuffer width
		 * @param height Framebuffer height
		 */
		virtual void OnAttach(int width, int height) = 0;

		/**
		 * Clean up path-specific resources.
		 * Called when switching away from this path.
		 */
		virtual void OnDetach() = 0;

		/**
		 * Execute the main rendering pass.
		 * For Forward: renders all objects with full lighting.
		 * For Forward+: dispatches light culling, then renders with per-tile lights.
		 * For Deferred: fills G-buffer, then runs lighting pass.
		 * @param data All data needed for rendering (scene, camera, lights, etc.)
		 */
		virtual void Execute(const RenderPassData& data) = 0;

		/**
		 * Whether this path requires a depth/normal prepass.
		 * Forward: false (unless screen-space effects need it)
		 * Forward+: true (always, for tile-based light culling)
		 * Deferred: false (G-buffer provides depth/normals)
		 */
		virtual bool NeedsDepthPrepass() const = 0;

		/**
		 * Whether this path provides G-buffer depth (avoiding redundant prepass).
		 * Only Deferred returns true.
		 */
		virtual bool ProvidesGBufferDepth() const { return false; }

		/**
		 * Whether this path provides G-buffer normals (avoiding redundant prepass).
		 * Only Deferred returns true.
		 */
		virtual bool ProvidesGBufferNormals() const { return false; }

		/**
		 * Get the depth texture produced by this path (if any).
		 * Used by screen-space effects when no separate prepass is run.
		 */
		virtual std::shared_ptr<Texture> GetDepthTexture() const { return nullptr; }

		/**
		 * Get the normal texture produced by this path (if any).
		 * Used by screen-space effects when no separate prepass is run.
		 */
		virtual std::shared_ptr<Texture> GetNormalTexture() const { return nullptr; }

		/**
		 * Handle framebuffer resize.
		 * @param width New width
		 * @param height New height
		 */
		virtual void OnResize(int width, int height) = 0;

		/**
		 * Render path-specific debug UI (e.g., G-buffer visualization, tile heatmap).
		 */
		virtual void OnImGuiDebug() {}

		/**
		 * Get a human-readable name for this path (for UI display and logging).
		 */
		virtual const char* GetName() const = 0;

		/**
		 * Get the render path type enum.
		 */
		virtual RenderPathType GetType() const = 0;

		/**
		 * Check if the path is properly initialized and ready for rendering.
		 */
		bool IsValid() const { return m_IsValid; }

	protected:
		bool m_IsValid = false;
	};
}
```

**Design decisions**:
- `Execute()` receives all data via `RenderPassData`—no back-references to SceneRenderer.
- `NeedsDepthPrepass()` tells the orchestrator whether to run a depth/normal prepass before this path.
- `ProvidesGBufferDepth()`/`ProvidesGBufferNormals()` let the Deferred path skip the prepass since its G-buffer already contains this data.
- `OnAttach()`/`OnDetach()` manage path-specific resources when switching at runtime.

---

## Step 3: Create ShadowPass

Extract shadow map generation from SandboxApp into its own class. This follows the same ownership pattern as Bloom (Chapter 40): owns its FBO, textures, and shader, and exposes a `Process()` method that returns output data.

**Create** `VizEngine/src/VizEngine/Renderer/ShadowPass.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/ShadowPass.h
// Chapter 43: Encapsulates shadow map generation (extracted from SandboxApp).

#pragma once

#include "VizEngine/Core.h"
#include "RenderPassData.h"
#include <memory>

namespace VizEngine
{
	class Framebuffer;
	class Texture;
	class Shader;
	class Scene;
	class Renderer;
	struct DirectionalLight;

	/**
	 * Generates a shadow map from a directional light's perspective.
	 * Produces a ShadowData struct containing the depth texture and light-space matrix.
	 */
	class VizEngine_API ShadowPass
	{
	public:
		/**
		 * Create a shadow mapping pass.
		 * @param resolution Shadow map resolution (e.g., 2048)
		 */
		ShadowPass(int resolution = 2048);
		~ShadowPass() = default;

		/**
		 * Render the scene from the light's perspective to generate shadow map.
		 * @param scene The scene to render
		 * @param light The directional light to cast shadows from
		 * @param renderer The renderer for draw calls
		 * @return ShadowData with the depth texture and light-space matrix
		 */
		ShadowData Process(Scene& scene, const DirectionalLight& light, Renderer& renderer);

		bool IsValid() const { return m_IsValid; }
		int GetResolution() const { return m_Resolution; }
		std::shared_ptr<Texture> GetShadowMap() const { return m_ShadowMapDepth; }

	private:
		glm::mat4 ComputeLightSpaceMatrix(const DirectionalLight& light) const;

		std::shared_ptr<Framebuffer> m_ShadowMapFramebuffer;
		std::shared_ptr<Texture> m_ShadowMapDepth;
		std::shared_ptr<Shader> m_ShadowDepthShader;

		int m_Resolution;
		bool m_IsValid = false;
	};
}
```

**Create** `VizEngine/src/VizEngine/Renderer/ShadowPass.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/ShadowPass.cpp

#include "ShadowPass.h"
#include "VizEngine/OpenGL/Framebuffer.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/OpenGL/Renderer.h"
#include "VizEngine/Core/Scene.h"
#include "VizEngine/Core/SceneObject.h"
#include "VizEngine/Core/Light.h"
#include "VizEngine/Core/Mesh.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>

namespace VizEngine
{
	ShadowPass::ShadowPass(int resolution)
		: m_Resolution(resolution)
	{
		// Create depth texture for shadow map
		m_ShadowMapDepth = std::make_shared<Texture>(
			resolution, resolution,
			GL_DEPTH_COMPONENT24,
			GL_DEPTH_COMPONENT,
			GL_FLOAT
		);

		// Configure for shadow sampling
		m_ShadowMapDepth->SetWrap(GL_CLAMP_TO_BORDER, GL_CLAMP_TO_BORDER);
		float borderColor[] = { 1.0f, 1.0f, 1.0f, 1.0f };
		m_ShadowMapDepth->SetBorderColor(borderColor);

		// Create depth-only framebuffer
		m_ShadowMapFramebuffer = std::make_shared<Framebuffer>(resolution, resolution);
		m_ShadowMapFramebuffer->AttachDepthTexture(m_ShadowMapDepth);

		if (!m_ShadowMapFramebuffer->IsComplete())
		{
			VP_CORE_ERROR("ShadowPass: Framebuffer not complete!");
			m_IsValid = false;
			return;
		}

		// Load shadow depth shader
		m_ShadowDepthShader = std::make_shared<Shader>("resources/shaders/shadow_depth.shader");
		if (!m_ShadowDepthShader->IsValid())
		{
			VP_CORE_ERROR("ShadowPass: Failed to load shadow depth shader!");
			m_IsValid = false;
			return;
		}

		m_IsValid = true;
		VP_CORE_INFO("ShadowPass created: {}x{}", resolution, resolution);
	}

	ShadowData ShadowPass::Process(Scene& scene, const DirectionalLight& light, Renderer& renderer)
	{
		ShadowData result;

		if (!m_IsValid)
		{
			VP_CORE_ERROR("ShadowPass::Process called on invalid instance");
			return result;
		}

		glm::mat4 lightSpaceMatrix = ComputeLightSpaceMatrix(light);

		renderer.PushViewport();

		m_ShadowMapFramebuffer->Bind();
		renderer.SetViewport(0, 0, m_Resolution, m_Resolution);
		renderer.ClearDepth();

		// Enable polygon offset to reduce shadow acne
		renderer.EnablePolygonOffset(2.0f, 4.0f);

		m_ShadowDepthShader->Bind();
		m_ShadowDepthShader->SetMatrix4fv("u_LightSpaceMatrix", lightSpaceMatrix);

		// Render scene geometry (depth only)
		// Note: instanced objects are skipped — they use per-instance model matrices
		// from vertex attributes, not the u_Model uniform. Proper instanced shadow
		// casting would require a separate instanced shadow depth shader.
		for (auto& obj : scene)
		{
			if (!obj.Active || !obj.MeshPtr) continue;
			if (obj.InstanceCount > 0) continue;

			glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
			m_ShadowDepthShader->SetMatrix4fv("u_Model", model);

			obj.MeshPtr->Bind();
			renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(),
			              *m_ShadowDepthShader);
		}

		renderer.DisablePolygonOffset();
		m_ShadowMapFramebuffer->Unbind();
		renderer.PopViewport();

		result.ShadowMap = m_ShadowMapDepth;
		result.LightSpaceMatrix = lightSpaceMatrix;
		result.Valid = true;
		return result;
	}

	glm::mat4 ShadowPass::ComputeLightSpaceMatrix(const DirectionalLight& light) const
	{
		glm::vec3 lightDir = light.GetDirection();
		glm::vec3 lightPos = -lightDir * 15.0f;

		// Handle degenerate up vector
		glm::vec3 up = glm::vec3(0.0f, 1.0f, 0.0f);
		if (glm::abs(glm::dot(lightDir, up)) > 0.999f)
		{
			up = glm::vec3(0.0f, 0.0f, 1.0f);
		}

		glm::mat4 lightView = glm::lookAt(lightPos, glm::vec3(0.0f), up);

		float orthoSize = 15.0f;
		glm::mat4 lightProjection = glm::ortho(
			-orthoSize, orthoSize,
			-orthoSize, orthoSize,
			0.1f, 30.0f
		);

		return lightProjection * lightView;
	}
}
```

> [!TIP]
> This pattern — own FBO + textures + shader, expose `Process()` that returns output data — will repeat for DepthNormalPrepass (Chapter 45), SSAOEffect (Chapter 48), and SSREffect (Chapter 49).

---

## Step 4: Create ForwardRenderPath

The forward path extracts the main rendering logic from SandboxApp, including opaque/transparent separation and back-to-front sorting.

**Create** `VizEngine/src/VizEngine/Renderer/ForwardRenderPath.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/ForwardRenderPath.h
// Chapter 43: Forward rendering strategy (refactored from SandboxApp).

#pragma once

#include "RenderPath.h"
#include <memory>

namespace VizEngine
{
	struct SceneObject;
	/**
	 * Traditional forward rendering path.
	 * Each object is fully shaded in a single pass with all lights.
	 * Simple and correct, but scales poorly with many lights.
	 */
	class VizEngine_API ForwardRenderPath : public RenderPath
	{
	public:
		ForwardRenderPath() = default;
		~ForwardRenderPath() override = default;

		void OnAttach(int width, int height) override;
		void OnDetach() override;
		void Execute(const RenderPassData& data) override;
		bool NeedsDepthPrepass() const override { return false; }
		void OnResize(int width, int height) override;
		const char* GetName() const override { return "Forward"; }
		RenderPathType GetType() const override { return RenderPathType::Forward; }

	private:
		/**
		 * Setup the default lit shader with camera, lights, shadows, and IBL.
		 */
		void SetupLighting(const RenderPassData& data);

		/**
		 * Render all scene objects (opaque first, then transparent back-to-front).
		 */
		void RenderSceneObjects(const RenderPassData& data);

		/**
		 * Render a single object with PBR material.
		 */
		void RenderSingleObject(SceneObject& obj, const RenderPassData& data);

		/**
		 * Render an instanced object with the instanced shader.
		 */
		void RenderInstancedObject(SceneObject& obj, const RenderPassData& data);
	};
}
```

**Create** `VizEngine/src/VizEngine/Renderer/ForwardRenderPath.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/ForwardRenderPath.cpp

#include "ForwardRenderPath.h"
#include "VizEngine/OpenGL/Renderer.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/OpenGL/Framebuffer.h"
#include "VizEngine/Core/Scene.h"
#include "VizEngine/Core/SceneObject.h"
#include "VizEngine/Core/Camera.h"
#include "VizEngine/Core/Light.h"
#include "VizEngine/Core/Mesh.h"
#include "VizEngine/Renderer/PBRMaterial.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>
#include <algorithm>

namespace VizEngine
{
	void ForwardRenderPath::OnAttach(int /*width*/, int /*height*/)
	{
		m_IsValid = true;
		VP_CORE_INFO("ForwardRenderPath attached");
	}

	void ForwardRenderPath::OnDetach()
	{
		m_IsValid = false;
		VP_CORE_INFO("ForwardRenderPath detached");
	}

	void ForwardRenderPath::Execute(const RenderPassData& data)
	{
		if (!data.ScenePtr || !data.CameraPtr || !data.RendererPtr || !data.Material) return;
		if (!data.TargetFramebuffer) return;

		// Bind HDR framebuffer
		data.TargetFramebuffer->Bind();
		data.RendererPtr->Clear(data.ClearColor);

		// Setup per-frame lighting uniforms
		SetupLighting(data);

		// Render all objects
		RenderSceneObjects(data);
	}

	void ForwardRenderPath::SetupLighting(const RenderPassData& data)
	{
		auto& material = *data.Material;
		auto shader = material.GetShader();
		shader->Bind();

		// Camera matrices — set directly on shader (not through material parameter map)
		shader->SetMatrix4fv("u_View", data.CameraPtr->GetViewMatrix());
		shader->SetMatrix4fv("u_Projection", data.CameraPtr->GetProjectionMatrix());
		shader->SetVec3("u_ViewPos", data.CameraPtr->GetPosition());

		// Point lights (guard against null arrays)
		int lightCount = data.PointLightCount;
		if (lightCount > 0 && (!data.PointLightPositions || !data.PointLightColors))
			lightCount = 0;

		shader->SetInt("u_LightCount", lightCount);
		for (int i = 0; i < lightCount; ++i)
		{
			shader->SetVec3("u_LightPositions[" + std::to_string(i) + "]",
			                data.PointLightPositions[i]);
			shader->SetVec3("u_LightColors[" + std::to_string(i) + "]",
			                data.PointLightColors[i]);
		}

		// Directional light
		if (data.DirLight)
		{
			shader->SetBool("u_UseDirLight", true);
			shader->SetVec3("u_DirLightDirection", data.DirLight->GetDirection());
			shader->SetVec3("u_DirLightColor", data.DirLight->Diffuse);
		}
		else
		{
			shader->SetBool("u_UseDirLight", false);
		}

		// Shadow mapping — lightSpaceMatrix directly on shader, texture via material
		if (data.Shadow.Valid && data.Shadow.ShadowMap)
		{
			shader->SetMatrix4fv("u_LightSpaceMatrix", data.Shadow.LightSpaceMatrix);
			material.SetShadowMap(data.Shadow.ShadowMap);
		}

		// IBL — textures via material (texture slots), scalar uniforms directly on shader
		// Validate that all IBL textures are present before enabling
		bool iblValid = data.UseIBL && data.IrradianceMap && data.PrefilteredMap && data.BRDFLut;
		material.SetUseIBL(iblValid);
		if (iblValid)
		{
			material.SetIrradianceMap(data.IrradianceMap);
			material.SetPrefilteredMap(data.PrefilteredMap);
			material.SetBRDFLUT(data.BRDFLut);
			shader->SetFloat("u_MaxReflectionLOD", 4.0f);
			shader->SetFloat("u_IBLIntensity", data.IBLIntensity);
		}
		else
		{
			shader->SetFloat("u_IBLIntensity", 0.0f);
		}

		// Lower hemisphere fallback — via material (stored as vec3/float, no matrix risk)
		material.SetLowerHemisphereColor(data.LowerHemisphereColor);
		material.SetLowerHemisphereIntensity(data.LowerHemisphereIntensity);
	}

	void ForwardRenderPath::RenderSceneObjects(const RenderPassData& data)
	{
		auto& scene = *data.ScenePtr;
		auto& renderer = *data.RendererPtr;

		// Separate opaque, instanced, and transparent objects
		std::vector<size_t> opaqueIndices;
		std::vector<size_t> instancedIndices;
		std::vector<size_t> transparentIndices;

		for (size_t i = 0; i < scene.Size(); i++)
		{
			auto& obj = scene[i];
			if (!obj.Active || !obj.MeshPtr) continue;

			if (obj.InstanceCount > 0)
				instancedIndices.push_back(i);
			else if (obj.Color.a < 1.0f)
				transparentIndices.push_back(i);
			else
				opaqueIndices.push_back(i);
		}

		// 1. Render opaque objects (PBR material)
		for (size_t idx : opaqueIndices)
		{
			RenderSingleObject(scene[idx], data);
		}

		// 2. Render instanced objects (instanced shader)
		for (size_t idx : instancedIndices)
		{
			RenderInstancedObject(scene[idx], data);
		}

		// 3. Sort and render transparent objects back-to-front
		if (!transparentIndices.empty())
		{
			glm::vec3 camPos = data.CameraPtr->GetPosition();
			std::sort(transparentIndices.begin(), transparentIndices.end(),
				[&scene, &camPos](size_t a, size_t b) {
					float distA = glm::length(scene[a].ObjectTransform.Position - camPos);
					float distB = glm::length(scene[b].ObjectTransform.Position - camPos);
					return distA > distB;
				});

			renderer.EnableBlending();
			renderer.SetBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
			renderer.SetDepthMask(false);

			for (size_t idx : transparentIndices)
			{
				RenderSingleObject(scene[idx], data);
			}

			renderer.SetDepthMask(true);
			renderer.DisableBlending();
		}
	}

	void ForwardRenderPath::RenderSingleObject(SceneObject& obj, const RenderPassData& data)
	{
		auto& material = *data.Material;
		auto shader = material.GetShader();
		auto& renderer = *data.RendererPtr;

		// Set PBR properties via material (uploaded during material.Bind())
		material.SetAlbedo(glm::vec3(obj.Color));
		material.SetAlpha(obj.Color.a);
		material.SetMetallic(obj.Metallic);
		material.SetRoughness(obj.Roughness);
		material.SetAO(1.0f);

		if (obj.TexturePtr)
			material.SetAlbedoTexture(obj.TexturePtr);
		else
			material.SetAlbedoTexture(nullptr);

		// Bind material: shader + textures + PBR uniform upload
		material.Bind();

		// Set per-object matrices directly on shader (after Bind ensures shader is active)
		glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
		glm::mat3 normalMatrix = glm::transpose(glm::inverse(glm::mat3(model)));
		shader->SetMatrix4fv("u_Model", model);
		shader->SetMatrix3fv("u_NormalMatrix", normalMatrix);

		obj.MeshPtr->Bind();
		renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), *shader);
	}

	void ForwardRenderPath::RenderInstancedObject(SceneObject& obj, const RenderPassData& data)
	{
		if (!data.InstancedShader) return;

		auto& renderer = *data.RendererPtr;
		auto& shader = *data.InstancedShader;

		shader.Bind();
		shader.SetMatrix4fv("u_View", data.CameraPtr->GetViewMatrix());
		shader.SetMatrix4fv("u_Projection", data.CameraPtr->GetProjectionMatrix());
		shader.SetVec3("u_ViewPos", data.CameraPtr->GetPosition());

		if (data.DirLight)
		{
			shader.SetVec3("u_DirLightDirection", data.DirLight->GetDirection());
			shader.SetVec3("u_DirLightColor", data.DirLight->Diffuse);
		}

		shader.SetVec3("u_ObjectColor", glm::vec3(obj.Color));

		obj.MeshPtr->Bind();
		renderer.DrawInstanced(obj.MeshPtr->GetVertexArray(),
		                       obj.MeshPtr->GetIndexBuffer(),
		                       shader, obj.InstanceCount);

		// Restore PBR shader binding for subsequent objects
		if (data.Material)
			data.Material->GetShader()->Bind();
	}

	void ForwardRenderPath::OnResize(int /*width*/, int /*height*/)
	{
		// Forward path has no path-specific framebuffers to resize
	}
}
```

**Key patterns**:
1. **Material owns surface properties**: `material.SetAlbedo()`, `material.SetMetallic()`, `material.SetIrradianceMap()` — these go through the material's parameter map and are uploaded during `Bind()`.
2. **Renderer sets transforms directly on shader**: `shader->SetMatrix4fv("u_Model", ...)` — these bypass the material entirely. This is critical: `u_NormalMatrix` is a `mat3`, and the material's variant map stores `mat4` — mixing them would cause `GL_INVALID_OPERATION`.
3. **Transparency sorting**: `RenderSceneObjects()` separates opaque, instanced, and transparent objects. Instanced objects use the instanced shader with `DrawInstanced()`, while transparent objects are sorted back-to-front by distance to camera with alpha blending and disabled depth writes.

---

## Step 5: Create PostProcessPipeline

Compose the existing Bloom (Chapter 40), tone mapping (Chapter 39), and color grading (Chapter 41) into a single pipeline.

**Create** `VizEngine/src/VizEngine/Renderer/PostProcessPipeline.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/PostProcessPipeline.h
// Chapter 43: Composes Bloom + Tone Mapping + Color Grading (extracted from SandboxApp).

#pragma once

#include "VizEngine/Core.h"
#include <memory>

namespace VizEngine
{
	class Texture;
	class Texture3D;
	class Shader;
	class Bloom;
	class FullscreenQuad;
	class Renderer;

	/**
	 * Post-processing pipeline: Bloom -> Tone Mapping -> Color Grading.
	 * Reads an HDR color texture and renders the final LDR result to the screen.
	 */
	class VizEngine_API PostProcessPipeline
	{
	public:
		PostProcessPipeline(int width, int height);
		~PostProcessPipeline();

		/**
		 * Process the HDR buffer and render to the default framebuffer (screen).
		 * @param hdrColorTexture The HDR scene color texture
		 * @param renderer The renderer for state management
		 * @param windowWidth Window width for viewport
		 * @param windowHeight Window height for viewport
		 */
		void Process(std::shared_ptr<Texture> hdrColorTexture, Renderer& renderer,
		             int windowWidth, int windowHeight);

		/**
		 * Recreate internal resources on resize.
		 */
		void OnResize(int width, int height);

		bool IsValid() const { return m_IsValid; }

		// Bloom settings
		void SetEnableBloom(bool enable) { m_EnableBloom = enable; }
		void SetBloomThreshold(float threshold) { m_BloomThreshold = threshold; }
		void SetBloomKnee(float knee) { m_BloomKnee = knee; }
		void SetBloomIntensity(float intensity) { m_BloomIntensity = intensity; }
		void SetBloomBlurPasses(int passes) { m_BloomBlurPasses = passes; }

		bool GetEnableBloom() const { return m_EnableBloom; }
		float GetBloomThreshold() const { return m_BloomThreshold; }
		float GetBloomKnee() const { return m_BloomKnee; }
		float GetBloomIntensity() const { return m_BloomIntensity; }
		int GetBloomBlurPasses() const { return m_BloomBlurPasses; }

		// Tone mapping settings
		void SetToneMappingMode(int mode) { m_ToneMappingMode = mode; }
		void SetExposure(float exposure) { m_Exposure = exposure; }
		void SetGamma(float gamma) { m_Gamma = gamma; }
		void SetWhitePoint(float wp) { m_WhitePoint = wp; }

		int GetToneMappingMode() const { return m_ToneMappingMode; }
		float GetExposure() const { return m_Exposure; }
		float GetGamma() const { return m_Gamma; }
		float GetWhitePoint() const { return m_WhitePoint; }

		// Color grading settings
		void SetEnableColorGrading(bool enable) { m_EnableColorGrading = enable; }
		void SetLUTContribution(float contrib) { m_LUTContribution = contrib; }
		void SetSaturation(float sat) { m_Saturation = sat; }
		void SetContrast(float contrast) { m_Contrast = contrast; }
		void SetBrightness(float brightness) { m_Brightness = brightness; }

		bool GetEnableColorGrading() const { return m_EnableColorGrading; }
		float GetLUTContribution() const { return m_LUTContribution; }
		float GetSaturation() const { return m_Saturation; }
		float GetContrast() const { return m_Contrast; }
		float GetBrightness() const { return m_Brightness; }

	private:
		// Bloom processor
		std::unique_ptr<Bloom> m_Bloom;

		// Tone mapping
		std::shared_ptr<Shader> m_ToneMappingShader;
		std::shared_ptr<FullscreenQuad> m_FullscreenQuad;

		// Color grading
		std::unique_ptr<Texture3D> m_ColorGradingLUT;

		// Bloom parameters
		bool m_EnableBloom = true;
		float m_BloomThreshold = 1.5f;
		float m_BloomKnee = 0.5f;
		float m_BloomIntensity = 0.04f;
		int m_BloomBlurPasses = 5;

		// Tone mapping parameters
		int m_ToneMappingMode = 3;  // ACES
		float m_Exposure = 1.0f;
		float m_Gamma = 2.2f;
		float m_WhitePoint = 4.0f;

		// Color grading parameters
		bool m_EnableColorGrading = false;
		float m_LUTContribution = 1.0f;
		float m_Saturation = 1.0f;
		float m_Contrast = 1.0f;
		float m_Brightness = 0.0f;

		int m_Width, m_Height;
		bool m_IsValid = false;
	};
}
```

**Create** `VizEngine/src/VizEngine/Renderer/PostProcessPipeline.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/PostProcessPipeline.cpp

#include "PostProcessPipeline.h"
#include "Bloom.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/OpenGL/Texture3D.h"
#include "VizEngine/OpenGL/FullscreenQuad.h"
#include "VizEngine/OpenGL/Renderer.h"
#include "VizEngine/OpenGL/Commons.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>
#include <algorithm>

namespace VizEngine
{
	PostProcessPipeline::~PostProcessPipeline() = default;

	PostProcessPipeline::PostProcessPipeline(int width, int height)
		: m_Width(width), m_Height(height)
	{
		// Create Bloom processor (half resolution, clamped to minimum of 1)
		int bloomWidth = std::max(width / 2, 1);
		int bloomHeight = std::max(height / 2, 1);
		m_Bloom = std::make_unique<Bloom>(bloomWidth, bloomHeight);

		if (!m_Bloom || !m_Bloom->IsValid())
		{
			VP_CORE_ERROR("PostProcessPipeline: Failed to create Bloom processor!");
		}

		// Load tone mapping shader
		m_ToneMappingShader = std::make_shared<Shader>("resources/shaders/tonemapping.shader");
		if (!m_ToneMappingShader->IsValid())
		{
			VP_CORE_ERROR("PostProcessPipeline: Failed to load tone mapping shader!");
			m_IsValid = false;
			return;
		}

		// Create fullscreen quad
		m_FullscreenQuad = std::make_shared<FullscreenQuad>();

		// Create neutral color grading LUT
		m_ColorGradingLUT = Texture3D::CreateNeutralLUT(16);
		if (!m_ColorGradingLUT)
		{
			VP_CORE_WARN("PostProcessPipeline: Failed to create color grading LUT");
		}

		m_IsValid = true;
		VP_CORE_INFO("PostProcessPipeline created: {}x{}", width, height);
	}

	void PostProcessPipeline::Process(std::shared_ptr<Texture> hdrColorTexture,
	                                  Renderer& renderer,
	                                  int windowWidth, int windowHeight)
	{
		if (!m_IsValid || !hdrColorTexture) return;

		// Pass 1: Bloom processing
		std::shared_ptr<Texture> bloomTexture = nullptr;
		if (m_EnableBloom && m_Bloom && m_Bloom->IsValid())
		{
			m_Bloom->SetThreshold(m_BloomThreshold);
			m_Bloom->SetKnee(m_BloomKnee);
			m_Bloom->SetBlurPasses(m_BloomBlurPasses);

			bloomTexture = m_Bloom->Process(hdrColorTexture);
		}

		// Pass 2: Tone mapping + compositing to screen
		renderer.SetViewport(0, 0, windowWidth, windowHeight);
		float clearColor[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
		renderer.Clear(clearColor);
		renderer.DisableDepthTest();

		m_ToneMappingShader->Bind();

		// Bind HDR texture
		hdrColorTexture->Bind(TextureSlots::HDRBuffer);
		m_ToneMappingShader->SetInt("u_HDRBuffer", TextureSlots::HDRBuffer);

		// Tone mapping parameters
		m_ToneMappingShader->SetInt("u_ToneMappingMode", m_ToneMappingMode);
		m_ToneMappingShader->SetFloat("u_Exposure", m_Exposure);
		m_ToneMappingShader->SetFloat("u_Gamma", m_Gamma);
		m_ToneMappingShader->SetFloat("u_WhitePoint", m_WhitePoint);

		// Bloom (only enable if we actually have a bloom texture)
		bool enableBloom = m_EnableBloom && bloomTexture;
		m_ToneMappingShader->SetBool("u_EnableBloom", enableBloom);
		m_ToneMappingShader->SetFloat("u_BloomIntensity", m_BloomIntensity);
		if (bloomTexture)
		{
			bloomTexture->Bind(TextureSlots::BloomTexture);
			m_ToneMappingShader->SetInt("u_BloomTexture", TextureSlots::BloomTexture);
		}

		// Color grading (only enable if LUT is available)
		bool enableColorGrading = m_EnableColorGrading && m_ColorGradingLUT;
		m_ToneMappingShader->SetBool("u_EnableColorGrading", enableColorGrading);
		m_ToneMappingShader->SetFloat("u_LUTContribution", m_LUTContribution);
		m_ToneMappingShader->SetFloat("u_Saturation", m_Saturation);
		m_ToneMappingShader->SetFloat("u_Contrast", m_Contrast);
		m_ToneMappingShader->SetFloat("u_Brightness", m_Brightness);

		if (m_EnableColorGrading && m_ColorGradingLUT)
		{
			m_ColorGradingLUT->Bind(TextureSlots::ColorGradingLUT);
			m_ToneMappingShader->SetInt("u_ColorGradingLUT", TextureSlots::ColorGradingLUT);
		}

		m_FullscreenQuad->Render();

		renderer.EnableDepthTest();
	}

	void PostProcessPipeline::OnResize(int width, int height)
	{
		m_Width = width;
		m_Height = height;

		// Recreate Bloom at half resolution (clamped to minimum of 1)
		if (m_Bloom)
		{
			auto oldBloom = std::move(m_Bloom);
			m_Bloom = std::make_unique<Bloom>(std::max(width / 2, 1), std::max(height / 2, 1));

			if (m_Bloom && m_Bloom->IsValid())
			{
				m_Bloom->SetThreshold(m_BloomThreshold);
				m_Bloom->SetKnee(m_BloomKnee);
				m_Bloom->SetBlurPasses(m_BloomBlurPasses);
			}
			else
			{
				VP_CORE_ERROR("PostProcessPipeline: Failed to recreate Bloom on resize, restoring old");
				m_Bloom = std::move(oldBloom);
			}
		}
	}
}
```

---

## Step 6: Create SceneRenderer

The orchestrator ties everything together. It owns the HDR framebuffer, shadow pass, post-processing pipeline, and the active render path.

**Create** `VizEngine/src/VizEngine/Renderer/SceneRenderer.h`:

```cpp
// VizEngine/src/VizEngine/Renderer/SceneRenderer.h
// Chapter 43: Central orchestrator for the rendering pipeline.
// Composes shadow pass, render path, and post-processing into a single Render() call.

#pragma once

#include "VizEngine/Core.h"
#include "RenderPassData.h"
#include <memory>

namespace VizEngine
{
	class RenderPath;
	class ShadowPass;
	class PostProcessPipeline;
	class Scene;
	class Camera;
	class Renderer;
	class Shader;
	class Texture;
	class Framebuffer;
	class FullscreenQuad;
	class PBRMaterial;
	class Skybox;
	struct DirectionalLight;

	/**
	 * SceneRenderer orchestrates the full rendering pipeline:
	 *   1. Shadow pass (shared)
	 *   2. Main render path (Forward / Forward+ / Deferred)
	 *   3. Skybox
	 *   4. Stencil outlines
	 *   5. Post-processing (Bloom -> Tone Mapping -> Color Grading)
	 *
	 * SandboxApp creates a SceneRenderer and calls Render() each frame,
	 * reducing the application to scene setup and UI code.
	 */
	class VizEngine_API SceneRenderer
	{
	public:
		SceneRenderer(int width, int height);
		~SceneRenderer();

		/**
		 * Execute the full rendering pipeline for one frame.
		 */
		void Render(Scene& scene, Camera& camera, Renderer& renderer);

		/**
		 * Switch the active rendering path at runtime.
		 */
		void SetRenderPath(RenderPathType type);
		RenderPathType GetRenderPathType() const { return m_CurrentPathType; }
		const char* GetRenderPathName() const;

		/**
		 * Handle window resize.
		 */
		void OnResize(int width, int height);

		/**
		 * Render path-specific debug UI.
		 */
		void OnImGuiDebug();

		// =====================================================================
		// External resource setters (called by SandboxApp during OnCreate)
		// =====================================================================

		void SetDefaultLitShader(std::shared_ptr<Shader> shader) { m_DefaultLitShader = shader; }
		void SetPBRMaterial(std::shared_ptr<PBRMaterial> material) { m_PBRMaterial = material; }

		// IBL
		void SetIBLMaps(std::shared_ptr<Texture> irradiance,
		                std::shared_ptr<Texture> prefiltered,
		                std::shared_ptr<Texture> brdfLut);
		void SetUseIBL(bool use) { m_UseIBL = use; }
		void SetIBLIntensity(float intensity) { m_IBLIntensity = intensity; }

		bool GetUseIBL() const { return m_UseIBL; }
		float GetIBLIntensity() const { return m_IBLIntensity; }

		// Lights
		void SetDirectionalLight(DirectionalLight* light) { m_DirLight = light; }
		void SetPointLights(glm::vec3* positions, glm::vec3* colors, int count);

		// Lower hemisphere
		void SetLowerHemisphereColor(const glm::vec3& color) { m_LowerHemisphereColor = color; }
		void SetLowerHemisphereIntensity(float intensity) { m_LowerHemisphereIntensity = intensity; }

		glm::vec3 GetLowerHemisphereColor() const { return m_LowerHemisphereColor; }
		float GetLowerHemisphereIntensity() const { return m_LowerHemisphereIntensity; }

		// Skybox
		void SetSkybox(Skybox* skybox) { m_Skybox = skybox; }
		void SetShowSkybox(bool show) { m_ShowSkybox = show; }
		bool GetShowSkybox() const { return m_ShowSkybox; }

		// Stencil outlines
		void SetOutlineShader(std::shared_ptr<Shader> shader) { m_OutlineShader = shader; }
		void SetEnableOutlines(bool enable) { m_EnableOutlines = enable; }
		void SetOutlineColor(const glm::vec4& color) { m_OutlineColor = color; }
		void SetOutlineScale(float scale) { m_OutlineScale = scale; }
		void SetSelectedObject(int index) { m_SelectedObject = index; }

		bool GetEnableOutlines() const { return m_EnableOutlines; }
		glm::vec4 GetOutlineColor() const { return m_OutlineColor; }
		float GetOutlineScale() const { return m_OutlineScale; }

		// Instancing (Chapter 35)
		void SetInstancedShader(std::shared_ptr<Shader> shader) { m_InstancedShader = shader; }
		void SetInstancingEnabled(bool enable) { m_ShowInstancingDemo = enable; }

		// Clear color
		void SetClearColor(const float color[4]);
		const float* GetClearColor() const { return m_ClearColor; }

		// Post-processing access
		PostProcessPipeline* GetPostProcess() { return m_PostProcess.get(); }

		// Shadow pass access
		ShadowPass* GetShadowPass() { return m_ShadowPass.get(); }

		// HDR state
		std::shared_ptr<Texture> GetHDRColorTexture() const { return m_HDRColorTexture; }
		std::shared_ptr<Framebuffer> GetHDRFramebuffer() const { return m_HDRFramebuffer; }
		bool IsHDREnabled() const { return m_HDREnabled; }

	private:
		void CreateHDRFramebuffer(int width, int height);

		void RenderStencilOutline(Scene& scene, Camera& camera, Renderer& renderer);

		// Rendering pipeline components
		std::unique_ptr<RenderPath> m_ActivePath;
		std::unique_ptr<ShadowPass> m_ShadowPass;
		std::unique_ptr<PostProcessPipeline> m_PostProcess;

		RenderPathType m_CurrentPathType = RenderPathType::Forward;

		// HDR framebuffer (shared across all paths)
		std::shared_ptr<Framebuffer> m_HDRFramebuffer;
		std::shared_ptr<Texture> m_HDRColorTexture;
		std::shared_ptr<Texture> m_HDRDepthTexture;
		bool m_HDREnabled = true;

		// Shared rendering resources (set externally)
		std::shared_ptr<Shader> m_DefaultLitShader;
		std::shared_ptr<PBRMaterial> m_PBRMaterial;
		std::shared_ptr<FullscreenQuad> m_FullscreenQuad;

		// IBL
		std::shared_ptr<Texture> m_IrradianceMap;
		std::shared_ptr<Texture> m_PrefilteredMap;
		std::shared_ptr<Texture> m_BRDFLut;
		bool m_UseIBL = true;
		float m_IBLIntensity = 0.3f;

		// Lights (pointers to SandboxApp-owned data)
		DirectionalLight* m_DirLight = nullptr;
		glm::vec3* m_PointLightPositions = nullptr;
		glm::vec3* m_PointLightColors = nullptr;
		int m_PointLightCount = 0;

		// Lower hemisphere
		glm::vec3 m_LowerHemisphereColor = glm::vec3(0.15f, 0.15f, 0.2f);
		float m_LowerHemisphereIntensity = 0.5f;

		// Skybox (pointer to SandboxApp-owned)
		Skybox* m_Skybox = nullptr;
		bool m_ShowSkybox = true;

		// Stencil outlines
		std::shared_ptr<Shader> m_OutlineShader;
		bool m_EnableOutlines = true;
		glm::vec4 m_OutlineColor = glm::vec4(1.0f, 0.6f, 0.0f, 1.0f);
		float m_OutlineScale = 1.05f;
		int m_SelectedObject = 0;

		// Instancing
		std::shared_ptr<Shader> m_InstancedShader;
		bool m_ShowInstancingDemo = false;

		// Clear color
		float m_ClearColor[4] = { 0.1f, 0.1f, 0.15f, 1.0f };

		int m_Width, m_Height;
	};
}
```

**Create** `VizEngine/src/VizEngine/Renderer/SceneRenderer.cpp`:

```cpp
// VizEngine/src/VizEngine/Renderer/SceneRenderer.cpp

#include "SceneRenderer.h"
#include "RenderPath.h"
#include "ForwardRenderPath.h"
#include "ShadowPass.h"
#include "PostProcessPipeline.h"
#include "PBRMaterial.h"
#include "VizEngine/OpenGL/Renderer.h"
#include "VizEngine/OpenGL/Shader.h"
#include "VizEngine/OpenGL/Texture.h"
#include "VizEngine/OpenGL/Framebuffer.h"
#include "VizEngine/OpenGL/FullscreenQuad.h"
#include "VizEngine/Core/Scene.h"
#include "VizEngine/Core/SceneObject.h"
#include "VizEngine/Core/Camera.h"
#include "VizEngine/Core/Light.h"
#include "VizEngine/Core/Mesh.h"
#include "VizEngine/Renderer/Skybox.h"
#include "VizEngine/Log.h"

#include <glad/glad.h>

namespace VizEngine
{
	SceneRenderer::SceneRenderer(int width, int height)
		: m_Width(width), m_Height(height)
	{
		// Create HDR framebuffer
		CreateHDRFramebuffer(width, height);

		// Create shared fullscreen quad
		m_FullscreenQuad = std::make_shared<FullscreenQuad>();

		// Create shadow pass
		m_ShadowPass = std::make_unique<ShadowPass>(2048);

		// Create post-processing pipeline
		m_PostProcess = std::make_unique<PostProcessPipeline>(width, height);

		// Default to forward rendering
		m_ActivePath = std::make_unique<ForwardRenderPath>();
		m_ActivePath->OnAttach(width, height);
		m_CurrentPathType = RenderPathType::Forward;

		VP_CORE_INFO("SceneRenderer created: {}x{}, path={}", width, height, m_ActivePath->GetName());
	}

	SceneRenderer::~SceneRenderer()
	{
		if (m_ActivePath)
			m_ActivePath->OnDetach();
	}

	void SceneRenderer::Render(Scene& scene, Camera& camera, Renderer& renderer)
	{
		if (!m_HDREnabled || !m_HDRFramebuffer || !m_PBRMaterial || !m_DefaultLitShader)
			return;

		// =====================================================================
		// 1. Shadow Pass (shared across all render paths)
		// =====================================================================
		ShadowData shadowData;
		if (m_ShadowPass && m_ShadowPass->IsValid() && m_DirLight)
		{
			shadowData = m_ShadowPass->Process(scene, *m_DirLight, renderer);
		}

		// =====================================================================
		// 2. Main Render Path (polymorphic dispatch)
		// =====================================================================
		if (m_ActivePath && m_ActivePath->IsValid())
		{
			RenderPassData passData;
			passData.ScenePtr = &scene;
			passData.CameraPtr = &camera;
			passData.RendererPtr = &renderer;
			passData.Shadow = shadowData;
			passData.TargetFramebuffer = m_HDRFramebuffer;
			passData.Material = m_PBRMaterial;
			passData.DefaultLitShader = m_DefaultLitShader;
			passData.InstancedShader = m_InstancedShader;
			passData.Quad = m_FullscreenQuad;
			passData.IrradianceMap = m_IrradianceMap;
			passData.PrefilteredMap = m_PrefilteredMap;
			passData.BRDFLut = m_BRDFLut;
			passData.UseIBL = m_UseIBL && m_IrradianceMap && m_PrefilteredMap && m_BRDFLut;
			passData.IBLIntensity = m_IBLIntensity;
			passData.DirLight = m_DirLight;
			passData.PointLightPositions = m_PointLightPositions;
			passData.PointLightColors = m_PointLightColors;
			passData.PointLightCount = m_PointLightCount;
			passData.LowerHemisphereColor = m_LowerHemisphereColor;
			passData.LowerHemisphereIntensity = m_LowerHemisphereIntensity;
			std::copy(std::begin(m_ClearColor), std::end(m_ClearColor), std::begin(passData.ClearColor));

			m_ActivePath->Execute(passData);
		}

		// Re-bind HDR framebuffer to ensure skybox and outlines render to correct target
		// (in case Execute() unbound it or the main pass was skipped)
		m_HDRFramebuffer->Bind();

		// =====================================================================
		// 3. Skybox (rendered into HDR framebuffer, after main pass)
		// =====================================================================
		if (m_ShowSkybox && m_Skybox)
		{
			m_Skybox->Render(camera);
		}

		// =====================================================================
		// 4. Stencil Outlines (rendered into HDR framebuffer)
		// =====================================================================
		RenderStencilOutline(scene, camera, renderer);

		// Unbind HDR framebuffer
		m_HDRFramebuffer->Unbind();

		// =====================================================================
		// 5. Post-Processing (Bloom -> Tone Mapping -> to screen)
		// =====================================================================
		if (m_PostProcess && m_PostProcess->IsValid() && m_HDRColorTexture)
		{
			m_PostProcess->Process(m_HDRColorTexture, renderer, m_Width, m_Height);
		}

		// Re-enable depth test (post-processing disables it)
		renderer.EnableDepthTest();
	}

	void SceneRenderer::SetRenderPath(RenderPathType type)
	{
		if (m_CurrentPathType == type && m_ActivePath)
			return;

		if (m_ActivePath)
			m_ActivePath->OnDetach();

		switch (type)
		{
		case RenderPathType::Forward:
			m_ActivePath = std::make_unique<ForwardRenderPath>();
			break;
		case RenderPathType::ForwardPlus:
			// TODO: Chapter 46
			VP_CORE_WARN("Forward+ not yet implemented, falling back to Forward");
			m_ActivePath = std::make_unique<ForwardRenderPath>();
			type = RenderPathType::Forward;
			break;
		case RenderPathType::Deferred:
			// TODO: Chapter 47
			VP_CORE_WARN("Deferred not yet implemented, falling back to Forward");
			m_ActivePath = std::make_unique<ForwardRenderPath>();
			type = RenderPathType::Forward;
			break;
		}

		m_ActivePath->OnAttach(m_Width, m_Height);
		m_CurrentPathType = type;
		VP_CORE_INFO("Render path switched to: {}", m_ActivePath->GetName());
	}

	const char* SceneRenderer::GetRenderPathName() const
	{
		return m_ActivePath ? m_ActivePath->GetName() : "None";
	}

	void SceneRenderer::OnResize(int width, int height)
	{
		if (width <= 0 || height <= 0) return;

		int oldWidth = m_Width;
		int oldHeight = m_Height;

		m_Width = width;
		m_Height = height;

		// Recreate HDR framebuffer
		auto oldFB = m_HDRFramebuffer;
		auto oldColor = m_HDRColorTexture;
		auto oldDepth = m_HDRDepthTexture;

		CreateHDRFramebuffer(width, height);

		if (!m_HDREnabled)
		{
			// Restore old resources and dimensions on failure
			m_HDRFramebuffer = oldFB;
			m_HDRColorTexture = oldColor;
			m_HDRDepthTexture = oldDepth;
			m_HDREnabled = (m_HDRFramebuffer != nullptr);
			m_Width = oldWidth;
			m_Height = oldHeight;
			return;
		}

		// Resize render path
		if (m_ActivePath)
			m_ActivePath->OnResize(width, height);

		// Resize post-processing
		if (m_PostProcess)
			m_PostProcess->OnResize(width, height);
	}

	void SceneRenderer::OnImGuiDebug()
	{
		if (m_ActivePath)
			m_ActivePath->OnImGuiDebug();
	}

	void SceneRenderer::SetIBLMaps(std::shared_ptr<Texture> irradiance,
	                               std::shared_ptr<Texture> prefiltered,
	                               std::shared_ptr<Texture> brdfLut)
	{
		m_IrradianceMap = irradiance;
		m_PrefilteredMap = prefiltered;
		m_BRDFLut = brdfLut;
	}

	void SceneRenderer::SetPointLights(glm::vec3* positions, glm::vec3* colors, int count)
	{
		if (count > 0 && (!positions || !colors))
		{
			m_PointLightPositions = nullptr;
			m_PointLightColors = nullptr;
			m_PointLightCount = 0;
			return;
		}

		m_PointLightPositions = positions;
		m_PointLightColors = colors;
		m_PointLightCount = count;
	}

	void SceneRenderer::SetClearColor(const float color[4])
	{
		std::copy(color, color + 4, m_ClearColor);
	}

	void SceneRenderer::CreateHDRFramebuffer(int width, int height)
	{
		m_HDRColorTexture = std::make_shared<Texture>(
			width, height, GL_RGB16F, GL_RGB, GL_FLOAT
		);

		m_HDRDepthTexture = std::make_shared<Texture>(
			width, height, GL_DEPTH24_STENCIL8, GL_DEPTH_STENCIL, GL_UNSIGNED_INT_24_8
		);

		m_HDRFramebuffer = std::make_shared<Framebuffer>(width, height);
		m_HDRFramebuffer->AttachColorTexture(m_HDRColorTexture, 0);
		m_HDRFramebuffer->AttachDepthStencilTexture(m_HDRDepthTexture);

		if (!m_HDRFramebuffer->IsComplete())
		{
			VP_CORE_ERROR("SceneRenderer: HDR Framebuffer not complete!");
			m_HDREnabled = false;
			return;
		}

		m_HDREnabled = true;
	}

	void SceneRenderer::RenderStencilOutline(Scene& scene, Camera& camera, Renderer& renderer)
	{
		if (!m_EnableOutlines || !m_OutlineShader) return;
		if (m_SelectedObject < 0 || m_SelectedObject >= static_cast<int>(scene.Size())) return;

		auto& obj = scene[static_cast<size_t>(m_SelectedObject)];
		if (!obj.Active || !obj.MeshPtr) return;

		// Pass 1: Fill stencil buffer
		renderer.ClearStencil();
		renderer.EnableStencilTest();
		renderer.SetStencilFunc(GL_ALWAYS, 1, 0xFF);
		renderer.SetStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE);
		renderer.SetStencilMask(0xFF);
		renderer.SetDepthFunc(GL_LEQUAL);

		// Re-render selected object to stencil (using PBR material)
		if (m_PBRMaterial)
		{
			// Set PBR properties via material
			m_PBRMaterial->SetAlbedo(glm::vec3(obj.Color));
			m_PBRMaterial->SetAlpha(obj.Color.a);
			m_PBRMaterial->SetMetallic(obj.Metallic);
			m_PBRMaterial->SetRoughness(obj.Roughness);
			m_PBRMaterial->SetAO(1.0f);

			if (obj.TexturePtr)
				m_PBRMaterial->SetAlbedoTexture(obj.TexturePtr);
			else
				m_PBRMaterial->SetAlbedoTexture(nullptr);

			// Bind material (shader + textures + PBR uniforms)
			m_PBRMaterial->Bind();

			// Set matrices directly on shader (after Bind)
			auto shader = m_PBRMaterial->GetShader();
			shader->SetMatrix4fv("u_View", camera.GetViewMatrix());
			shader->SetMatrix4fv("u_Projection", camera.GetProjectionMatrix());
			glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
			glm::mat3 normalMatrix = glm::transpose(glm::inverse(glm::mat3(model)));
			shader->SetMatrix4fv("u_Model", model);
			shader->SetMatrix3fv("u_NormalMatrix", normalMatrix);

			obj.MeshPtr->Bind();
			renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), *shader);
		}

		renderer.SetDepthFunc(GL_LESS);

		// Pass 2: Render scaled-up outline where stencil != 1
		renderer.SetStencilFunc(GL_NOTEQUAL, 1, 0xFF);
		renderer.SetStencilMask(0x00);
		renderer.SetDepthMask(false);

		m_OutlineShader->Bind();
		m_OutlineShader->SetMatrix4fv("u_View", camera.GetViewMatrix());
		m_OutlineShader->SetMatrix4fv("u_Projection", camera.GetProjectionMatrix());
		m_OutlineShader->SetVec4("u_OutlineColor", m_OutlineColor);

		glm::mat4 scaledModel = glm::scale(
			obj.ObjectTransform.GetModelMatrix(),
			glm::vec3(m_OutlineScale)
		);
		m_OutlineShader->SetMatrix4fv("u_Model", scaledModel);

		obj.MeshPtr->Bind();
		renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), *m_OutlineShader);

		// Restore state
		renderer.SetDepthMask(true);
		renderer.SetStencilMask(0xFF);
		renderer.DisableStencilTest();
	}
}
```

> [!NOTE]
> The stencil outline pass explicitly sets `u_View` and `u_Projection` on both the PBR shader and the outline shader after `Bind()`. This prevents a subtle bug where residual GL uniform state from a previous frame could be used, causing incorrect outline positioning.

---

## Step 7: Update Existing Files

Two existing files need small modifications to support the new architecture.

### Update Renderer.h — const correctness

The `Clear()` method needs a `const` parameter so it can accept `RenderPassData::ClearColor` without implicit conversion issues.

**Update** `VizEngine/src/VizEngine/OpenGL/Renderer.h` — change the `Clear` declaration:

```cpp
// Change:
void Clear(float clearColor[4]);

// To:
void Clear(const float clearColor[4]);
```

**Update** `VizEngine/src/VizEngine/OpenGL/Renderer.cpp` — change the `Clear` definition:

```cpp
// Change:
void Renderer::Clear(float clearColor[4])

// To:
void Renderer::Clear(const float clearColor[4])
```

### Update Framebuffer — MRT support

Add `SetDrawBuffers()` to configure Multiple Render Targets. This is not used by the Forward path, but prepares for Deferred rendering (Chapter 47) which outputs to multiple color attachments simultaneously.

**Update** `VizEngine/src/VizEngine/OpenGL/Framebuffer.h` — add after `IsComplete()`:

```cpp
/**
 * Configure which color attachments are active for rendering (MRT).
 * Must be called after attaching multiple color textures.
 * @param attachmentCount Number of color attachments to enable (1-8)
 */
void SetDrawBuffers(int attachmentCount);
```

**Update** `VizEngine/src/VizEngine/OpenGL/Framebuffer.cpp` — add implementation:

```cpp
void Framebuffer::SetDrawBuffers(int attachmentCount)
{
	if (attachmentCount < 1 || attachmentCount > 8)
	{
		VP_CORE_ERROR("Framebuffer: Draw buffer count {} out of range [1-8]", attachmentCount);
		return;
	}

	GLenum attachments[8] = {
		GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1,
		GL_COLOR_ATTACHMENT2, GL_COLOR_ATTACHMENT3,
		GL_COLOR_ATTACHMENT4, GL_COLOR_ATTACHMENT5,
		GL_COLOR_ATTACHMENT6, GL_COLOR_ATTACHMENT7
	};

	Bind();
	glDrawBuffers(attachmentCount, attachments);

	VP_CORE_INFO("Framebuffer {}: Set {} draw buffers", m_fbo, attachmentCount);
}
```

---

## Step 8: Update Build Files

### Update CMakeLists.txt

**Update** `VizEngine/CMakeLists.txt` — add to `VIZENGINE_SOURCES` (Renderer subsection):

```cmake
    src/VizEngine/Renderer/ShadowPass.cpp
    src/VizEngine/Renderer/PostProcessPipeline.cpp
    src/VizEngine/Renderer/ForwardRenderPath.cpp
    src/VizEngine/Renderer/SceneRenderer.cpp
```

Add to `VIZENGINE_HEADERS` (Renderer subsection):

```cmake
    src/VizEngine/Renderer/RenderPassData.h
    src/VizEngine/Renderer/RenderPath.h
    src/VizEngine/Renderer/ShadowPass.h
    src/VizEngine/Renderer/PostProcessPipeline.h
    src/VizEngine/Renderer/ForwardRenderPath.h
    src/VizEngine/Renderer/SceneRenderer.h
```

### Update VizEngine.h

**Update** `VizEngine/src/VizEngine.h` — add after the Material System includes:

```cpp
// Scene Renderer Architecture (Chapter 43)
#include "VizEngine/Renderer/RenderPassData.h"
#include "VizEngine/Renderer/RenderPath.h"
#include "VizEngine/Renderer/SceneRenderer.h"
```

> [!NOTE]
> `ForwardRenderPath.h`, `ShadowPass.h`, and `PostProcessPipeline.h` are **not** included in the public API header. These are internal implementation details of SceneRenderer. Client code only needs `SceneRenderer.h` and `RenderPassData.h` (for `RenderPathType` enum).

---

## Step 9: Refactor SandboxApp

The key refactoring: replace the monolithic `OnRender()` with SceneRenderer delegation. SandboxApp shrinks from ~1660 to ~970 lines.

### What Gets Removed from SandboxApp

| Removed | Moved To |
|---------|----------|
| Shadow framebuffer, depth texture, shader | `ShadowPass` |
| HDR framebuffer creation | `SceneRenderer::CreateHDRFramebuffer()` |
| Per-frame light/camera uniform setup | `ForwardRenderPath::SetupLighting()` |
| Per-object PBR uniform setup | `ForwardRenderPath::RenderSingleObject()` |
| Opaque/transparent sorting | `ForwardRenderPath::RenderSceneObjects()` |
| Bloom processing | `PostProcessPipeline` |
| Tone mapping and color grading | `PostProcessPipeline` |
| Stencil outline rendering | `SceneRenderer::RenderStencilOutline()` |
| Light-space matrix computation | `ShadowPass::ComputeLightSpaceMatrix()` |

### What Stays in SandboxApp

| Kept | Reason |
|------|--------|
| Scene objects, meshes, textures | Application owns scene data |
| Camera and input handling | Application concern |
| Shader and material creation | Application chooses which assets to load |
| IBL map generation | One-time initialization |
| Skybox creation | Application owns skybox |
| ImGui panels | Application-specific UI |
| Offscreen preview (F2) | Separate from main pipeline |
| Instancing demo setup | Chapter 35 feature, scene-level integration |
| Event handling | Application concern |

### New Includes

```cpp
#include <VizEngine/Renderer/SceneRenderer.h>
#include <VizEngine/Renderer/PostProcessPipeline.h>
#include <VizEngine/Renderer/ShadowPass.h>
#include <VizEngine/Renderer/PBRMaterial.h>
#include <VizEngine/OpenGL/Commons.h>
```

### OnCreate — SceneRenderer Initialization

After creating shaders, materials, IBL maps, and skybox (unchanged from Chapter 42), add:

```cpp
// =========================================================================
// Create Scene Renderer (Chapter 43)
// =========================================================================
m_SceneRenderer = std::make_unique<VizEngine::SceneRenderer>(m_WindowWidth, m_WindowHeight);

// Wire up external resources
m_SceneRenderer->SetDefaultLitShader(m_DefaultLitShader);
m_SceneRenderer->SetPBRMaterial(m_PBRMaterial);
m_SceneRenderer->SetIBLMaps(m_IrradianceMap, m_PrefilteredMap, m_BRDFLut);
m_SceneRenderer->SetUseIBL(m_UseIBL);
m_SceneRenderer->SetIBLIntensity(m_IBLIntensity);
m_SceneRenderer->SetDirectionalLight(&m_Light);
m_SceneRenderer->SetPointLights(m_PBRLightPositions, m_PBRLightColors, 4);
m_SceneRenderer->SetSkybox(m_Skybox.get());
m_SceneRenderer->SetShowSkybox(m_ShowSkybox);
m_SceneRenderer->SetClearColor(m_ClearColor);

// Instanced shader (Chapter 35)
m_SceneRenderer->SetInstancedShader(m_InstancedShader);

// Outline settings
auto outlineShader = std::make_shared<VizEngine::Shader>("resources/shaders/outline.shader");
m_SceneRenderer->SetOutlineShader(outlineShader);
m_SceneRenderer->SetEnableOutlines(m_EnableOutlines);
m_SceneRenderer->SetOutlineColor(m_OutlineColor);
m_SceneRenderer->SetOutlineScale(m_OutlineScale);
m_SceneRenderer->SetSelectedObject(m_SelectedObject);

VP_INFO("Scene Renderer initialized: {}", m_SceneRenderer->GetRenderPathName());
```

### OnUpdate — Sync Settings

Because ImGui controls modify SandboxApp member variables each frame, sync them to the SceneRenderer:

```cpp
// =========================================================================
// Sync settings to SceneRenderer (in case ImGui changed them)
// =========================================================================
if (m_SceneRenderer)
{
    m_SceneRenderer->SetUseIBL(m_UseIBL);
    m_SceneRenderer->SetIBLIntensity(m_IBLIntensity);
    m_SceneRenderer->SetShowSkybox(m_ShowSkybox);
    m_SceneRenderer->SetClearColor(m_ClearColor);
    m_SceneRenderer->SetLowerHemisphereColor(m_LowerHemisphereColor);
    m_SceneRenderer->SetLowerHemisphereIntensity(m_LowerHemisphereIntensity);
    m_SceneRenderer->SetEnableOutlines(m_EnableOutlines);
    m_SceneRenderer->SetOutlineColor(m_OutlineColor);
    m_SceneRenderer->SetOutlineScale(m_OutlineScale);
    m_SceneRenderer->SetSelectedObject(m_SelectedObject);
}
```

### OnRender — The One-Line Pipeline

The monolithic `OnRender()` reduces to a single call:

```cpp
void OnRender() override
{
    auto& engine = VizEngine::Engine::Get();
    auto& renderer = engine.GetRenderer();

    // =========================================================================
    // Main Rendering Pipeline (Chapter 43: SceneRenderer)
    // =========================================================================
    if (m_SceneRenderer)
    {
        m_SceneRenderer->Render(m_Scene, m_Camera, renderer);
    }

    // Note: Instanced objects (Chapter 35) are now part of the Scene and rendered
    // inside the HDR pipeline by ForwardRenderPath::RenderInstancedObject().
    // They go through the same post-processing (bloom, tone mapping) as all objects.

    // Offscreen Preview (F2) — see below
    // ... rebinding pattern ...
}
```

### OnRender — Offscreen Preview (F2)

The offscreen preview renders independently from the main pipeline. After post-processing clobbers OpenGL texture state, we must rebind textures via the material for each object:

```cpp
if (m_Framebuffer && m_ShowFramebufferTexture && m_PBRMaterial)
{
    float windowAspect = static_cast<float>(m_WindowWidth) / static_cast<float>(m_WindowHeight);
    m_Camera.SetAspectRatio(1.0f);

    m_Framebuffer->Bind();
    renderer.SetViewport(0, 0, m_Framebuffer->GetWidth(), m_Framebuffer->GetHeight());
    renderer.Clear(m_ClearColor);

    // Set per-frame uniforms directly on shader (post-processing clobbers texture state)
    auto shader = m_PBRMaterial->GetShader();
    shader->Bind();
    shader->SetMatrix4fv("u_View", m_Camera.GetViewMatrix());
    shader->SetMatrix4fv("u_Projection", m_Camera.GetProjectionMatrix());

    for (auto& obj : m_Scene)
    {
        if (!obj.Active || !obj.MeshPtr) continue;
        if (obj.InstanceCount > 0) continue;  // Skip instanced objects in preview

        // Set PBR properties + rebind textures via material
        m_PBRMaterial->SetAlbedo(glm::vec3(obj.Color));
        m_PBRMaterial->SetAlpha(obj.Color.a);
        m_PBRMaterial->SetMetallic(obj.Metallic);
        m_PBRMaterial->SetRoughness(obj.Roughness);
        m_PBRMaterial->SetAO(1.0f);

        if (obj.TexturePtr)
            m_PBRMaterial->SetAlbedoTexture(obj.TexturePtr);
        else
            m_PBRMaterial->SetAlbedoTexture(nullptr);

        m_PBRMaterial->Bind();

        glm::mat4 model = obj.ObjectTransform.GetModelMatrix();
        glm::mat3 normalMatrix = glm::transpose(glm::inverse(glm::mat3(model)));
        shader->SetMatrix4fv("u_Model", model);
        shader->SetMatrix3fv("u_NormalMatrix", normalMatrix);

        obj.MeshPtr->Bind();
        renderer.Draw(obj.MeshPtr->GetVertexArray(), obj.MeshPtr->GetIndexBuffer(), *shader);
    }

    if (m_ShowSkybox && m_Skybox)
        m_Skybox->Render(m_Camera);

    m_Framebuffer->Unbind();

    m_Camera.SetAspectRatio(windowAspect);
    renderer.SetViewport(0, 0, m_WindowWidth, m_WindowHeight);
}
```

### OnEvent — Delegate Resize

```cpp
dispatcher.Dispatch<VizEngine::WindowResizeEvent>(
    [this](VizEngine::WindowResizeEvent& event) {
        m_WindowWidth = event.GetWidth();
        m_WindowHeight = event.GetHeight();

        if (m_WindowWidth > 0 && m_WindowHeight > 0)
        {
            float aspect = static_cast<float>(m_WindowWidth) / static_cast<float>(m_WindowHeight);
            m_Camera.SetAspectRatio(aspect);

            // Delegate resize to SceneRenderer
            if (m_SceneRenderer)
                m_SceneRenderer->OnResize(m_WindowWidth, m_WindowHeight);
        }
        return false;
    }
);
```

### OnImGuiRender — PostProcess and Shadow Access

The ImGui panels access SceneRenderer components through its getters:

```cpp
auto* postProcess = m_SceneRenderer ? m_SceneRenderer->GetPostProcess() : nullptr;

// In Engine Stats panel:
uiManager.Text("Render Path: %s",
    m_SceneRenderer ? m_SceneRenderer->GetRenderPathName() : "None");

// In Shadow Map preview (F3):
auto* shadowPass = m_SceneRenderer->GetShadowPass();
if (shadowPass && shadowPass->IsValid())
{
    auto shadowMap = shadowPass->GetShadowMap();
    // ... render to ImGui ...
    uiManager.Text("Shadow Map: %dx%d", shadowPass->GetResolution(), shadowPass->GetResolution());
}

// In HDR panel:
auto hdrFB = m_SceneRenderer->GetHDRFramebuffer();
if (hdrFB)
{
    uiManager.Text("HDR Buffer: %dx%d RGB16F", hdrFB->GetWidth(), hdrFB->GetHeight());
}

// Render path debug:
if (m_SceneRenderer)
    m_SceneRenderer->OnImGuiDebug();
```

### New Member Variable

```cpp
private:
    // Scene Renderer (Chapter 43)
    std::unique_ptr<VizEngine::SceneRenderer> m_SceneRenderer;
```

> [!NOTE]
> SandboxApp still owns scene objects, camera, shaders, IBL resources, and input handling. SceneRenderer receives pointers to these and orchestrates the rendering pipeline. The application remains the authority on *what* to render; SceneRenderer decides *how*.

---

## Testing and Validation

### Verify Identical Visual Output

The most important test: **the scene must look exactly the same after refactoring**.

1. Build and run
2. Compare with pre-refactor screenshots:
   - PBR materials render correctly (metallic spheres, rough surfaces)
   - IBL reflections present (irradiance + prefiltered)
   - Shadow mapping works (directional light shadows with PCF)
   - Bloom glow around bright surfaces
   - Tone mapping and color grading applied
   - Stencil outlines on selected object
   - Transparency sorting (back-to-front)
   - Offscreen preview (F2) renders correctly
   - Shadow map debug view (F3) shows depth texture

### No OpenGL Errors

With `GL_DEBUG_OUTPUT_SYNCHRONOUS` enabled, any errors will be caught immediately. Common issues during this refactor:

| Error | Cause | Solution |
|-------|-------|----------|
| `GL_INVALID_OPERATION: Uniform must be a matrix type` | Calling `SetMatrix4fv` for a `mat3` uniform (or vice versa) | Use `SetMatrix3fv` for `u_NormalMatrix` |
| Dark/black scene after post-processing | Post-processing clobbers OpenGL texture bindings | Call `material.Bind()` to rebind textures per object |
| Stencil outlines missing | View/projection not set on shader in stencil pass | Explicitly set `u_View`/`u_Projection` after `Bind()` |
| Compile error: no matching function `Clear(float[4])` | `RenderPassData::ClearColor` passed to non-const param | Update `Clear()` to take `const float[4]` |

### Runtime Path Switching

When the ImGui dropdown changes the render path, the scene should remain visually identical (since only Forward is implemented so far). Forward+ and Deferred print a warning and fall back to Forward.

---

## Best Practices

### Architecture Patterns

1. **Strategy Pattern for render paths**: New paths plug in by deriving from `RenderPath` and implementing `Execute()`. No changes to SceneRenderer or other paths required.
2. **Data-driven pass communication**: `RenderPassData` is a plain struct—no virtual calls, no back-references. Passes communicate through data, not inheritance.
3. **Shared resources, separate lifetimes**: The HDR framebuffer is owned by SceneRenderer and shared across paths via `RenderPassData`. Paths don't create or destroy shared resources.

### Resource Ownership

1. **SceneRenderer owns pipeline infrastructure**: HDR framebuffer, shadow pass, post-processing pipeline, active render path.
2. **SandboxApp owns scene data**: Meshes, textures, shaders, materials, camera, lights. SceneRenderer receives pointers.
3. **Render paths own nothing** (for now): ForwardRenderPath has no member state. All data comes through `RenderPassData`. Future paths (Forward+, Deferred) will own path-specific resources (compute shaders, G-buffers).

### Pass Ordering

1. **Shadow first**: Shadow maps are needed by all subsequent passes.
2. **Main render before skybox**: Skybox is rendered with `GL_LEQUAL` depth test, requiring existing depth data.
3. **Stencil after main render**: Re-renders the selected object to fill the stencil buffer, requiring existing depth.
4. **Post-processing last**: Reads the completed HDR buffer and outputs to screen.
5. **Never assume residual state**: Each pass explicitly sets all required GL state and shader uniforms.

### Future-Proofing

1. **`SetDrawBuffers()` is forward-looking**: Added now but first used in Chapter 47 (Deferred). Keeps the Framebuffer API complete.
2. **`PrepassOutput` is in `RenderPassData` already**: The depth/normal prepass (Chapter 45) plugs in via this field.
3. **`ProvidesGBufferDepth()`/`ProvidesGBufferNormals()`**: Let Deferred skip redundant prepasses.

---

## Cross-Chapter Integration

### Callbacks to Previous Chapters

> In **Chapter 42**, we built the Material System. This chapter separates material concerns (surface properties) from renderer concerns (transforms, camera, lights). The PBRMaterial keeps `SetAlbedo()`, `SetMetallic()`, `SetIrradianceMap()`, etc. Transform matrices are now set directly on the shader by the render path.

> The shadow mapping from **Chapter 29** is extracted into `ShadowPass`, which owns its framebuffer, depth texture, and shader—following the same pattern as `Bloom` (Chapter 40).

> The post-processing chain from **Chapters 39-41** (HDR, Bloom, Color Grading) is composed into `PostProcessPipeline`, which reads the HDR framebuffer and outputs the final LDR image to the screen.

> The stencil outline technique from **Chapter 32** is preserved in `SceneRenderer::RenderStencilOutline()`, with explicit view/projection matrix setup to avoid relying on residual GL state.

> The transparency sorting from **Chapter 33** is preserved in `ForwardRenderPath::RenderSceneObjects()`, separating opaque and transparent objects with back-to-front sorting for the transparent pass.

### Forward References

> **Chapter 44: Light Management & SSBOs** introduces Shader Storage Buffer Objects for dynamic light counts. The `LightManager` will replace the raw pointer arrays in `RenderPassData` with SSBO-backed light data.

> **Chapter 45: Depth & Normal Prepass** adds a `DepthNormalPrepass` class (same pattern as ShadowPass and Bloom) that the SceneRenderer calls when `m_ActivePath->NeedsDepthPrepass()` returns true.

> **Chapter 46: Forward+ Rendering** adds `ForwardPlusRenderPath` — a new strategy that plugs into `SetRenderPath(RenderPathType::ForwardPlus)` with compute shader light culling.

> **Chapter 47: Deferred Rendering** adds `DeferredRenderPath` with a G-buffer geometry pass and fullscreen lighting pass. This is where `Framebuffer::SetDrawBuffers()` is first used—configuring Multiple Render Targets for the G-buffer fill pass.

---

## Milestone

**Chapter 43 Complete — Scene Renderer Architecture**

At this point, your engine has:

**SceneRenderer orchestrator** that composes shadow, render path, skybox, outlines, and post-processing into a single `Render()` call.

**Strategy Pattern** for swappable render paths via `RenderPath` abstract base class and `ForwardRenderPath` concrete implementation.

**ShadowPass** extracted from SandboxApp with its own FBO, depth texture, and shader. Returns `ShadowData` struct.

**PostProcessPipeline** composing Bloom + Tone Mapping + Color Grading with full parameter control.

**ForwardRenderPath** with three-way object sorting (opaque → instanced → transparent), back-to-front sorting for transparent objects, PBR material binding, and instanced rendering via `RenderInstancedObject()`.

**RenderPassData** structs providing a clean contract between orchestrator and render paths.

**Material/Renderer separation**: PBRMaterial owns surface properties and texture slots; renderers set transforms and lighting directly on the shader.

**Framebuffer MRT support** via `SetDrawBuffers()`, preparing for Deferred rendering (Chapter 47).

**SandboxApp reduced** from ~1660 to ~970 lines — now focused on scene setup, camera control, and ImGui UI.

**New file count**: 10 new files (RenderPassData.h, RenderPath.h, ShadowPass.h/cpp, PostProcessPipeline.h/cpp, ForwardRenderPath.h/cpp, SceneRenderer.h/cpp) + 2 modified files (Renderer.h/cpp, Framebuffer.h/cpp).

This architecture is the foundation for every remaining chapter in Part XII. Each new rendering technique plugs in as either a new `RenderPath` implementation or a new pass in the SceneRenderer pipeline.

---

## What's Next

In **Chapter 44: Light Management & SSBOs**, we'll introduce Shader Storage Buffer Objects (SSBOs) to support dynamic light counts. The current pipeline hardcodes 4 point lights as uniform arrays—SSBOs remove this limit, enabling scenes with hundreds of lights (a prerequisite for Forward+ and Deferred rendering).

> **Next:** [Chapter 44: Light Management & SSBOs](44_LightManagementSSBOs.md)

> **Previous:** [Chapter 42: Material System](42_MaterialSystem.md)

> **Index:** [Table of Contents](INDEX.md)
