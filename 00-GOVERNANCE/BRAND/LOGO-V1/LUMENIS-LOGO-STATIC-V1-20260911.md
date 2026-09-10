# LUMENIS / 序境 — Static Logo V1

> Status: **V1 / APPROVED DESIGN DIRECTION / IMPLEMENTATION REQUIRED**  
> Type: **STATIC BRAND IDENTITY**  
> Effective: 2026-09-11  
> Parent authority: `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`  
> Repository baseline audited before this addition: `4689070425161986019fee5ef1c051ee35c05acb`  
> Scope: logo mark, wordmarks, lockups, static color/material behavior, asset outputs.

---

## 0. Meaning of V1

This document defines the **first approved LUMENIS logo direction**. It is an implementation authority for the static identity, not a claim that final production SVG/PNG/ICO assets already exist.

Any implementation must preserve this semantic core unless a later explicit V2 authority replaces it.

---

## 1. Brand philosophy

Primary philosophy:

**芥子纳须弥**

Brand action phrase:

**一点开境**  
**A POINT OPENS A REALM**

Interpretation:

```text
Point / Seed
→ latent possibility
→ boundary
→ realm
→ expansion
→ return to one
```

The mark is **not** a literal water droplet, ocean, seed, flower, flame or globe. It is a restrained visual metaphor: a point/seed/droplet-like origin held by an opening boundary.

---

## 2. Approved mark geometry

### 2.1 Core shape

The V1 symbol is a vertically oriented, narrow, symmetric mark with four semantic parts:

1. **Origin Point** — a very small point on the vertical center axis.
2. **Central Core** — a thin, elongated inner axis / energy form.
3. **Boundary Pair** — two restrained outer curves that open and return around the core.
4. **Return Axis** — the lower convergence that resolves the expanded form back to order.

### 2.2 Proportion

- The mark must remain **narrow and vertical**. Do not widen it into a bulb, eye, lens or conventional droplet.
- The outer form is primarily negative space. Filled color area must remain minimal.
- The center axis must remain perceptible at small size.
- The upper point must remain visually distinct from the outer boundary.
- The mark must work at 24 / 32 / 64 px after optical simplification.

### 2.3 Shape prohibitions

Do not turn the V1 mark into:

- a realistic water droplet;
- a literal seed illustration;
- a lotus / leaf / flame;
- a globe or planet;
- a glass ornament;
- a thick 3D object;
- a wide eye-shaped symbol;
- a neon/cyber icon.

---

## 3. Static color philosophy

Only three identity color families are authorized for V1:

| Token | Meaning | Static use |
|---|---|---|
| `CLEAR` | air / possibility / negative space | dominant visual field; near-colorless |
| `SILVER_WHITE` | boundary / order / precision | outer contours, quiet highlights |
| `ICY_CYAN` | origin / activation / possibility | very small center/core accents only |

### 3.1 Rules

- **No purple.**
- **No amber/gold.**
- No rainbow gradient.
- No large cyan fill.
- Color lives mainly at the origin point, center core and boundary-edge transition.
- The background is a refined warm white / paper white / mist white, not gray and not pure clinical white.
- The mark must still be identifiable in monochrome.

### 3.2 Background principle

The background supports the mark; it never becomes a decorative scene.

Allowed qualities:

- warm white;
- subtle paper/mist texture;
- extremely low-contrast surface grain.

Disallowed:

- gray cast;
- colored ambient gradients;
- busy reflections;
- decorative light rays;
- large glass effects.

---

## 4. Wordmark system

### 4.1 Standard Chinese + English lockup

Primary production lockup:

```text
[SYMBOL]
序境
LUMENIS
```

Extended brand lockup may additionally include:

```text
一点开境
A POINT OPENS A REALM
```

The tagline is **not mandatory in every operational UI use**.

### 4.2 Chinese `序境`

- restrained custom handwritten / calligraphic-linear character;
- contemporary and quiet;
- thin, controlled stroke endings;
- not wild cursive, traditional calligraphy display, or decorative brush lettering.

Final production wordmark should be converted to original vector outlines; implementation must not depend on shipping an unapproved font file.

### 4.3 English `LUMENIS`

- uppercase wordmark;
- generous letter spacing;
- calm, precise, human-modern;
- no decorative script in this V1 reference direction;
- final production wordmark should be vectorized as an original/approved wordmark asset.

### 4.4 Korean version

```text
[SYMBOL]
서경
LUMENIS
```

- Hangul wordmark must be designed as its own optical composition, not mechanically scaled from Chinese metrics;
- it must preserve the same restrained, light, human quality;
- Korean display text must remain readable and contemporary.

---

## 5. Three official V1 static variants

| Variant | Required lockup | Primary use |
|---|---|---|
| `V1_STANDARD` | Symbol + `序境` + `LUMENIS` | main product / brand identity |
| `V1_KOREAN` | Symbol + `서경` + `LUMENIS` | Korean-language environment |
| `V1_SYMBOL_ONLY` | Symbol only | app icon, favicon, compact controls, motion return point |

All three are one identity family. Do not redesign the mark per locale.

---

## 6. Canonical V1 copy

| Semantic meaning | Canonical copy |
|---|---|
| Chinese product name | `序境` |
| English product name | `LUMENIS` |
| Korean product name | `서경` |
| Brand philosophy | `芥子纳须弥` |
| Philosophy translation | `A UNIVERSE WITHIN A MUSTARD SEED` |
| Brand action phrase | `一点开境` |
| Action phrase translation | `A POINT OPENS A REALM` |
| Brand positioning line | `TECHNOLOGY FOR A MORE HUMAN WORLD` |
| Secondary motif | `SMALL / DEEP / BOUNDLESS` |
| Color tokens | `CLEAR / SILVER WHITE / ICY CYAN` |

Do not copy OCR mistakes from visual reference boards into production copy.

---

## 7. Required production assets

When V1 is implemented, the handoff must contain at minimum:

```text
brand/logo/v1/static/
├── standard/
│   ├── lumenis-logo-v1-standard.svg
│   ├── lumenis-logo-v1-standard.png
│   └── lumenis-logo-v1-standard-monochrome.svg
├── korean/
│   ├── lumenis-logo-v1-korean.svg
│   └── lumenis-logo-v1-korean.png
├── symbol/
│   ├── lumenis-symbol-v1.svg
│   ├── lumenis-symbol-v1-24.png
│   ├── lumenis-symbol-v1-32.png
│   ├── lumenis-symbol-v1-64.png
│   └── lumenis-symbol-v1-512.png
├── lockups/
│   ├── lumenis-lockup-v1-with-tagline.svg
│   └── lumenis-lockup-v1-with-tagline.png
└── LOGO-V1-ASSET-MANIFEST.json
```

SVG must be the primary editable engineering asset. Raster outputs are derivatives.

---

## 8. Originality / implementation boundary

All final logo vectors, wordmark outlines and production assets must be original LUMENIS work.

External brands, logo galleries, UI libraries, shaders and design references may be studied for principles only. Do not trace, copy, import, or adapt their production assets.

---

## 9. V1 acceptance

Static V1 passes only if:

- the symbol remains narrow, vertical and recognizable;
- large negative space remains dominant;
- colors are limited to Clear / Silver White / Icy Cyan;
- no purple/amber/rainbow treatment enters the mark;
- the symbol is not read as a literal droplet or decorative glass object;
- Standard / Korean / Symbol-only versions are coherent;
- all production copy matches the canonical copy table;
- 24/32/64 px versions remain legible;
- final assets are original and versioned as V1.
