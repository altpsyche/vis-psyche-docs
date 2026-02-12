\newpage

# Chapter 36: PBR Theory

Understand the physics and mathematics behind Physically Based Rendering—the foundation of modern real-time graphics.

---

## Introduction

In **Chapters 21-22**, we implemented Blinn-Phong lighting—a model that has served games and real-time graphics for decades. While Blinn-Phong produces reasonable results, it has fundamental limitations:

| Blinn-Phong Limitation | Physical Issue |
|------------------------|----------------|
| **Arbitrary shininess exponent** | No physical meaning; artists guess values |
| **No energy conservation** | Surfaces can reflect more light than received |
| **Inconsistent under lighting** | Materials look different under various light conditions |
| **Metal vs plastic indistinguishable** | Fresnel effect not modeled correctly |

**Physically Based Rendering (PBR)** solves these problems by grounding the lighting model in physics. Instead of ad-hoc parameters like "shininess," PBR uses physically meaningful properties:

- **Roughness**: How smooth or rough is the surface? (0 = mirror, 1 = matte)
- **Metallic**: Is it a metal or a dielectric? (0 = plastic/wood, 1 = metal)
- **Albedo**: What's the base color?

### Why PBR Matters

| Benefit | Impact |
|---------|--------|
| **Physical accuracy** | Materials behave correctly under all lighting |
| **Artist-friendly** | Intuitive parameters that work predictably |
| **Consistency** | Same material looks correct in any scene |
| **Industry standard** | Unreal Engine, Unity, Blender, glTF all use PBR |

> **What we'll learn**: This chapter establishes the mathematical foundation. In **Chapter 37**, we'll implement it in GLSL. In **Chapter 38**, we'll add Image-Based Lighting using the cubemap from Chapter 30.

---

## The Rendering Equation

All physically accurate lighting models derive from the **rendering equation**, introduced by James Kajiya in 1986:

$$L_o(\mathbf{p}, \omega_o) = L_e(\mathbf{p}, \omega_o) + \int_\Omega f_r(\mathbf{p}, \omega_i, \omega_o) L_i(\mathbf{p}, \omega_i) (\mathbf{n} \cdot \omega_i) \, d\omega_i$$

This looks intimidating, but let's break it down:

| Symbol | Meaning |
|--------|---------|
| $L_o$ | **Outgoing radiance**—light leaving the surface toward us |
| $L_e$ | **Emitted radiance**—light the surface generates (for now, 0) |
| $\omega_o$ | **View direction**—from surface point toward camera |
| $\omega_i$ | **Incident direction**—from surface point toward a light source |
| $f_r$ | **BRDF**—Bidirectional Reflectance Distribution Function |
| $L_i$ | **Incoming radiance**—light arriving from direction $\omega_i$ |
| $\mathbf{n} \cdot \omega_i$ | **Cosine term**—Lambert's law (light at grazing angles is weaker) |
| $\int_\Omega$ | **Integral over hemisphere**—sum contributions from all directions |

### Simplified for Real-Time

For direct lighting (point lights, directional lights), we replace the integral with a sum over discrete light sources:

$$L_o = \sum_{i=1}^{n} f_r(\omega_i, \omega_o) \cdot L_i \cdot (\mathbf{n} \cdot \omega_i)$$

This is what we'll implement: for each light, compute the BRDF, multiply by incoming radiance and the cosine term, and sum the results.

### The BRDF: Heart of PBR

The **Bidirectional Reflectance Distribution Function** (BRDF) describes how a surface reflects light. Given:
- Incoming light direction $\omega_i$
- Outgoing view direction $\omega_o$
- Surface properties (roughness, metallic, etc.)

The BRDF returns the **ratio** of outgoing radiance to incoming irradiance.

**Physical constraints on BRDFs**:

1. **Energy conservation**: A surface cannot reflect more light than it receives
   $$\int_\Omega f_r(\omega_i, \omega_o) \cos\theta_i \, d\omega_i \leq 1$$

2. **Reciprocity**: Swapping light and view directions gives the same result
   $$f_r(\omega_i, \omega_o) = f_r(\omega_o, \omega_i)$$

3. **Positivity**: BRDF values are never negative
   $$f_r \geq 0$$

---

## Microfacet Theory

PBR models surfaces not as perfectly flat planes, but as collections of tiny **microfacets**—microscopic mirrors too small to resolve individually.

### The Microfacet Model

Imagine zooming into a "smooth" surface:

```
Macroscopic view:          Microscopic view:
    ___________               /\/\/\/\/\/\
                             /  \/  \/  \/\
   Looks smooth!            Individual facets
```

Each microfacet is a perfect mirror reflecting light in a single direction. The aggregate behavior of millions of microfacets produces the macro-scale appearance we see.

**Key insight**: Surface appearance depends on the **statistical distribution** of microfacet orientations.

### Roughness and Microfacet Alignment

| Roughness | Microfacet Distribution | Visual Result |
|-----------|------------------------|---------------|
| **Low (0.0)** | Most facets point the same direction | Sharp, mirror-like reflections |
| **High (1.0)** | Facets point in random directions | Broad, diffuse reflections |

### The Halfway Vector

For a microfacet to reflect light from direction $\mathbf{l}$ (light) into direction $\mathbf{v}$ (view), its normal must point exactly **halfway** between them:

$$\mathbf{h} = \frac{\mathbf{l} + \mathbf{v}}{|\mathbf{l} + \mathbf{v}|} = \text{normalize}(\mathbf{l} + \mathbf{v})$$

This **halfway vector** is central to microfacet BRDFs. A rough surface has many microfacets with normals deviating from $\mathbf{h}$; a smooth surface has most microfacets aligned with $\mathbf{h}$.

```glsl
// In shader code:
vec3 H = normalize(L + V);  // Halfway vector
```

---

## The Cook-Torrance BRDF

The industry-standard PBR model uses the **Cook-Torrance** specular BRDF combined with a Lambertian diffuse term.

### Complete PBR Equation

$$f_r = k_d f_{\text{lambert}} + k_s f_{\text{cook-torrance}}$$

Where:
- $k_d$ = diffuse contribution (1 for dielectrics, 0 for metals)
- $k_s$ = specular contribution (energy-conserving with diffuse)
- $f_{\text{lambert}} = \frac{\text{albedo}}{\pi}$ (Lambertian diffuse)
- $f_{\text{cook-torrance}}$ = specular term (see below)

### The Cook-Torrance Specular Term

$$f_{\text{cook-torrance}} = \frac{D \cdot F \cdot G}{4 (\mathbf{n} \cdot \omega_o)(\mathbf{n} \cdot \omega_i)}$$

Three functions combine to model specular reflection:

| Function | Name | Models |
|----------|------|--------|
| **D** | Normal Distribution Function | Microfacet alignment with halfway vector |
| **F** | Fresnel Equation | Reflectivity at different angles |
| **G** | Geometry Function | Self-shadowing of microfacets |

The denominator $4 (\mathbf{n} \cdot \omega_o)(\mathbf{n} \cdot \omega_i)$ is a **normalization factor** ensuring energy conservation.

Let's examine each component in detail.

---

## D: Normal Distribution Function (NDF)

The **Normal Distribution Function** approximates what proportion of microfacets are aligned with the halfway vector $\mathbf{h}$.

### GGX/Trowbridge-Reitz Distribution

The most widely used NDF is GGX (also called Trowbridge-Reitz):

$$D_{GGX}(\mathbf{n}, \mathbf{h}, \alpha) = \frac{\alpha^2}{\pi ((\mathbf{n} \cdot \mathbf{h})^2 (\alpha^2 - 1) + 1)^2}$$

Where:
- $\alpha = \text{roughness}^2$ (squared for perceptual linearity)
- $\mathbf{n} \cdot \mathbf{h}$ = cosine of angle between surface normal and halfway vector

### Visual Effect of Roughness on NDF

| Roughness | α = roughness² | NDF Behavior | Specular Appearance |
|-----------|----------------|--------------|---------------------|
| 0.0 | 0.0 | Infinite spike at h=n | Perfect mirror |
| 0.25 | 0.0625 | Narrow peak | Tight, bright highlight |
| 0.5 | 0.25 | Medium spread | Balanced highlight |
| 0.75 | 0.5625 | Wide distribution | Broad, soft highlight |
| 1.0 | 1.0 | Nearly uniform | Almost no highlight |

> **Why roughness²?** Artists prefer linear roughness (0.5 = half rough). Squaring converts this to the mathematically correct $\alpha$ for the GGX formula, matching perceptual expectations.

### GLSL Implementation

```glsl
float DistributionGGX(vec3 N, vec3 H, float roughness)
{
    float a = roughness * roughness;           // α = roughness²
    float a2 = a * a;                          // α²
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;
    
    float nom = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;
    
    return nom / denom;
}
```

---

## F: Fresnel Equation

The **Fresnel effect** describes how surfaces reflect more light at **grazing angles**. Stand by a lake: looking straight down, you see the bottom (low reflection). Looking toward the horizon, the water becomes a mirror (high reflection).

### The Fresnel-Schlick Approximation

The full Fresnel equations are complex. Christophe Schlick's approximation is nearly identical but much cheaper:

$$F_{Schlick}(\mathbf{h}, \mathbf{v}, F_0) = F_0 + (1 - F_0)(1 - (\mathbf{h} \cdot \mathbf{v}))^5$$

Where:
- $F_0$ = reflectance at normal incidence (looking straight at surface)
- $\mathbf{h} \cdot \mathbf{v}$ = cosine of angle between halfway vector and view

### F0: Base Reflectivity

The $F_0$ value depends on the material type:

| Material Type | F0 Value | Notes |
|---------------|----------|-------|
| **Dielectrics** (plastic, wood, fabric) | `vec3(0.04)` | ~4% reflectivity at normal incidence |
| **Water** | `vec3(0.02)` | 2% reflectivity |
| **Metals** | Use albedo color | Metals tint their reflections |

> **Key insight**: This is why metals and dielectrics look different! Metals use their albedo as F0 (tinted reflections), while dielectrics use 0.04 (colorless reflections).

### Metallic Workflow

In the metallic-roughness workflow (used by glTF, Unreal Engine 4+, etc.):

```glsl
// Interpolate between dielectric F0 and metal F0 (albedo)
vec3 F0 = vec3(0.04);
F0 = mix(F0, albedo, metallic);
```

When `metallic = 0`: F0 = 0.04 (plastic-like)
When `metallic = 1`: F0 = albedo (gold reflects gold, copper reflects copper)

### GLSL Implementation

```glsl
vec3 FresnelSchlick(float cosTheta, vec3 F0)
{
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}
```

---

## G: Geometry Function

The **Geometry function** models how microfacets **shadow** and **mask** each other, blocking light.

### Shadowing and Masking

```
Light →  /\        Viewer
        /  \    ←
       /____\
        ↑
    Hidden area (shadowed from light or masked from view)
```

At rough surfaces or grazing angles, some microfacets block:
- **Shadowing**: Light can't reach certain microfacets
- **Masking**: Reflected light can't reach the viewer

### Schlick-GGX Geometry Function

We use Smith's method, which separates shadowing and masking into two terms:

$$G(\mathbf{n}, \mathbf{v}, \mathbf{l}, k) = G_{sub}(\mathbf{n}, \mathbf{v}, k) \cdot G_{sub}(\mathbf{n}, \mathbf{l}, k)$$

Each sub-term uses Schlick-GGX:

$$G_{SchlickGGX}(\mathbf{n}, \mathbf{v}, k) = \frac{\mathbf{n} \cdot \mathbf{v}}{(\mathbf{n} \cdot \mathbf{v})(1 - k) + k}$$

### Remapping k for Direct Lighting

The $k$ parameter differs for direct lighting vs. IBL:

| Lighting Type | k Remapping |
|---------------|-------------|
| **Direct lighting** | $k = \frac{(\text{roughness} + 1)^2}{8}$ |
| **IBL** | $k = \frac{\text{roughness}^2}{2}$ |

> **Note**: We use the direct lighting formula in this chapter. Chapter 38 (IBL) uses the IBL formula.

### GLSL Implementation

```glsl
float GeometrySchlickGGX(float NdotV, float roughness)
{
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;  // Direct lighting k
    
    float nom = NdotV;
    float denom = NdotV * (1.0 - k) + k;
    
    return nom / denom;
}

float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness)
{
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2 = GeometrySchlickGGX(NdotV, roughness);  // Masking
    float ggx1 = GeometrySchlickGGX(NdotL, roughness);  // Shadowing
    
    return ggx1 * ggx2;
}
```

---

## The Diffuse Term

Not all light is reflected—some enters the surface and scatters around before exiting. This creates the **diffuse** component.

### Lambertian Diffuse

The simplest physically plausible diffuse model is Lambertian:

$$f_{lambert} = \frac{\text{albedo}}{\pi}$$

**Why divide by π?** Energy conservation. A Lambertian surface scatters light uniformly over the hemisphere. Integrating over all outgoing directions must not exceed incoming energy; dividing by π ensures this.

### Energy Conservation with Fresnel

Light is either reflected (specular) or refracted (diffuse). The Fresnel term tells us how much is reflected, so:

$$k_d = 1 - F$$

But this is view-dependent. A simpler approximation uses the metallic parameter:

```glsl
// Metals have no diffuse (all light is reflected)
vec3 kD = vec3(1.0) - F;    // Diffuse coefficient
kD *= (1.0 - metallic);      // Metals have no diffuse
```

### Complete Diffuse + Specular

```glsl
// Combine diffuse and specular
vec3 diffuse = kD * albedo / PI;
vec3 specular = (D * F * G) / max(4.0 * NdotV * NdotL, 0.001);

vec3 Lo = (diffuse + specular) * radiance * NdotL;
```

---

## Material Parameterization

PBR uses a small set of intuitive, physically meaningful parameters.

### The Metallic-Roughness Workflow

| Parameter | Range | Meaning |
|-----------|-------|---------|
| **Albedo** (BaseColor) | RGB [0,1] | Base color (diffuse for dielectrics, F0 for metals) |
| **Metallic** | [0,1] | 0 = dielectric, 1 = metal |
| **Roughness** | [0,1] | 0 = mirror smooth, 1 = completely rough |
| **AO** (Ambient Occlusion) | [0,1] | Ambient light accessibility |

### Physical Plausibility Guidelines

To maintain realistic materials:

| Guideline | Reason |
|-----------|--------|
| **Avoid pure black albedo** (0,0,0) | Nothing absorbs 100% of light |
| **Avoid pure white albedo** (1,1,1) | Nothing reflects 100% of light |
| **Dielectric albedo range: 0.02–0.9** | Physical measurements |
| **Metal albedo > 0.5** | Metals are bright |
| **Metallic: 0 or 1 for most materials** | Few materials are in-between |

### Common Material Values

| Material | Albedo (sRGB) | Metallic | Roughness |
|----------|---------------|----------|-----------|
| **Plastic** | (0.8, 0.2, 0.2) | 0.0 | 0.5 |
| **Wood** | (0.6, 0.4, 0.2) | 0.0 | 0.8 |
| **Gold** | (1.0, 0.76, 0.33) | 1.0 | 0.1 |
| **Copper** | (0.95, 0.64, 0.54) | 1.0 | 0.2 |
| **Iron** | (0.56, 0.57, 0.58) | 1.0 | 0.4 |
| **Rubber** | (0.1, 0.1, 0.1) | 0.0 | 0.9 |

---

## Visual Intuition

Let's visualize how these parameters affect appearance.

### Roughness Progression (Dielectric, metallic=0)

Imagine a row of red spheres, albedo = (0.8, 0.1, 0.1):

| Roughness 0.0 | Roughness 0.25 | Roughness 0.5 | Roughness 0.75 | Roughness 1.0 |
|---------------|----------------|---------------|----------------|---------------|
| Perfect mirror | Tight highlight | Soft highlight | Broad glow | Almost matte |
| Sharp reflection | Visible Fresnel | Balanced | Diffuse-dominant | Fully diffuse |

### Roughness Progression (Metal, metallic=1)

Gold spheres, albedo = (1.0, 0.76, 0.33):

| Roughness 0.0 | Roughness 0.25 | Roughness 0.5 | Roughness 0.75 | Roughness 1.0 |
|---------------|----------------|---------------|----------------|---------------|
| Perfect gold mirror | Jewelry polish | Brushed metal | Satin finish | Rough gold |
| Environment visible | Environment blurred | Diffuse reflection | Broad highlight | Tinted diffuse |

### Metallic Transition

Spheres at roughness=0.3, transitioning metallic 0→1:

| Metallic 0 | Metallic 0.5 | Metallic 1 |
|------------|--------------|------------|
| Plastic with Fresnel | Halfway (rare) | Metal with tinted reflections |
| Colorless highlights | Mixed behavior | Albedo-colored reflections |

### Fresnel at Grazing Angles

On any sphere (especially visible with low roughness):
- **Center** (normal incidence): Low reflection, surface color visible
- **Edge** (grazing angle): High reflection, approaching pure white/mirror

This is the Fresnel effect in action—all materials do this!

---

## Summary: The PBR Pipeline

```
For each pixel:
├── Get material properties (albedo, metallic, roughness, AO)
├── Calculate view direction V = normalize(camPos - worldPos)
├── For each light:
│   ├── Calculate light direction L and radiance
│   ├── Calculate halfway vector H = normalize(V + L)
│   ├── D = DistributionGGX(N, H, roughness)      // Microfacet alignment
│   ├── F = FresnelSchlick(max(dot(H, V), 0), F0) // Angle-dependent reflection
│   ├── G = GeometrySmith(N, V, L, roughness)     // Self-shadowing
│   ├── specular = (D * F * G) / (4 * NdotV * NdotL)
│   ├── kD = (1 - F) * (1 - metallic)
│   ├── diffuse = kD * albedo / PI
│   └── Lo += (diffuse + specular) * radiance * NdotL
├── Add ambient term (ambient * albedo * AO)
└── Output final color
```

---

## Key Equations Reference

For quick reference, here are the core PBR equations:

**GGX Normal Distribution:**
$$D = \frac{\alpha^2}{\pi((\mathbf{n} \cdot \mathbf{h})^2(\alpha^2 - 1) + 1)^2}$$

**Fresnel-Schlick:**
$$F = F_0 + (1 - F_0)(1 - (\mathbf{h} \cdot \mathbf{v}))^5$$

**Geometry (Smith/Schlick-GGX):**
$$G = G_1(\mathbf{n}, \mathbf{v}) \cdot G_1(\mathbf{n}, \mathbf{l})$$
$$G_1 = \frac{\mathbf{n} \cdot \mathbf{x}}{(\mathbf{n} \cdot \mathbf{x})(1-k) + k}$$

**Cook-Torrance Specular:**
$$f_{spec} = \frac{D \cdot F \cdot G}{4(\mathbf{n} \cdot \mathbf{v})(\mathbf{n} \cdot \mathbf{l})}$$

**Lambertian Diffuse:**
$$f_{diff} = \frac{\text{albedo}}{\pi}$$

---

## Milestone

**Chapter 36 Complete - PBR Theory**

You now understand:
- The rendering equation and how BRDFs work
- Microfacet theory and the halfway vector
- The Cook-Torrance specular BRDF (D, F, G terms)
- GGX distribution for normal distribution
- Fresnel-Schlick approximation for angle-dependent reflection
- Schlick-GGX geometry function for self-shadowing
- Lambertian diffuse with energy conservation
- The metallic-roughness material workflow

This theoretical foundation is essential for understanding **why** PBR looks correct. In the next chapter, we'll translate this into working GLSL code.

---

## References

This chapter draws from authoritative sources:

1. **LearnOpenGL PBR Theory** - Joey de Vries
2. **"Real Shading in Unreal Engine 4"** - Brian Karis, SIGGRAPH 2013
3. **"Physically Based Shading at Disney"** - Brent Burley, SIGGRAPH 2012
4. **glTF 2.0 PBR Specification** - Khronos Group
5. **"Microfacet Models for Refraction"** - Walter et al., 2007 (GGX origin)

---

## What's Next

In **Chapter 37: PBR Implementation**, we'll translate this theory into a complete PBR shader, implementing all the equations we've learned in GLSL.

> **Next:** [Chapter 37: PBR Implementation](37_PBRImplementation.md)

> **Previous:** [Chapter 35: Instancing](35_Instancing.md)

> **Index:** [Table of Contents](INDEX.md)
