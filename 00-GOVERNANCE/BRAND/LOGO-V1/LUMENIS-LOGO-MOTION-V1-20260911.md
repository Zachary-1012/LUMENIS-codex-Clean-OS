# LUMENIS / 序境 — Motion Logo V1

> Status: **V1 / APPROVED MOTION DIRECTION / IMPLEMENTATION REQUIRED**  
> Type: **DYNAMIC BRAND IDENTITY / LAUNCH ANIMATION**  
> Effective: 2026-09-11  
> Parent authority: `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`  
> Static companion: `00-GOVERNANCE/BRAND/LOGO-V1/LUMENIS-LOGO-STATIC-V1-20260911.md`

---

## 0. Motion meaning

The V1 launch animation is the dynamic expression of:

**芥子纳须弥 / 一点开境**

It must not behave like a literal droplet falling into a literal ocean.

The approved motion metaphor is:

```text
Point
→ descends
→ touches a boundary
→ boundary awakens
→ ripples open a realm
→ ripple boundary rises and converges
→ form appears
→ form contracts
→ all returns to the center point
→ white field
→ white breath
→ full brand lockup appears
```

The motion is about **a boundary being opened**, not a water-splash effect.

---

## 1. Master timing

Target duration: **approximately 4.8 seconds**.

Critical rhythm rule:

> Shots 01–05 must complete in approximately the first 2 seconds. The first half opens the realm quickly; the second half becomes progressively quieter and resolves the expansion back to one point before the brand appears.

### Canonical timeline

| Shot | Time | State | Motion | Non-negotiable rule |
|---|---:|---|---|---|
| 01 | `0.00–0.20s` | Center point appears | very small Icy Cyan point emerges from near-white | point is on the absolute visual center axis |
| 02 | `0.20–0.55s` | Point descends | point moves down with a very thin vertical trace | not realistic droplet physics |
| 03 | `0.55–0.85s` | Boundary touch | point touches an almost invisible curved boundary | no splash, no explosion |
| 04 | `0.85–1.30s` | Boundary awakens | boundary opens from the contact point left/right | restrained, geometric, quiet |
| 05 | `1.30–1.95s` | Ripple / realm opening | very thin concentric boundary ripples expand | shots 01–05 finish within ~2s |
| 06 | `1.95–2.45s` | Upward convergence | the ripple/boundary rises from sides and lower field, continuously converging upward into the mark pre-form | **05→06 must be a continuous morph; never hard cut** |
| 07 | `2.45–2.95s` | Form appears | the gathered boundary becomes the V1 seed/realm mark | same identity geometry as static V1 |
| 08 | `2.95–3.35s` | Form contracts | the mark slowly and continuously contracts toward the center | no sudden scale jump |
| 09 | `3.35–3.55s` | All returns to point | every remaining boundary resolves to one small point at the absolute image center | must echo Shot 01 |
| 10 | `3.55–3.72s` | White transition | point dissolves into the warm-white field | dissolve, not flash-cut |
| 11 | `3.72–3.92s` | White breath | clean white field holds briefly | silence/negative space is intentional |
| 12 | `3.92–4.35s` | Brand reveal | symbol → `序境` → `LUMENIS` → optional `一点开境` | no new complex effect |
| 13 | `4.35–4.80s` | Lockup hold | final lockup stabilizes then hands off to product UI | clean and short |

---

## 2. Transition continuity

### 2.1 03 → 04 → 05

Do not jump from a point on a line to a large ripple scene.

Required continuity:

```text
contact point
→ 1 small local wave
→ 2–3 faint expanding rings
→ boundary field widens
```

The line remains visually traceable through the transition.

### 2.2 05 → 06 — signature transition

This is the defining V1 brand motion.

```text
wide ripple field
      ↓
outer ripple arcs lift upward
      ↓
left/right boundaries bend inward
      ↓
central vertical core reappears
      ↓
V1 pre-form is assembled from the same geometry
```

The viewer must understand that the form is **made from the opened boundary**. The mark must not appear as a separate object.

### 2.3 06 → 07 → 08 → 09

This is one continuous contraction sequence:

```text
full pre-form
→ refined mark
→ smaller mark
→ reduced light/edge information
→ single center point
```

No shot may introduce a different symbol geometry.

### 2.4 09 → 10 → 11 → 12

```text
center point
→ dissolves into white
→ white field breathes
→ full brand lockup appears
```

The logo reveal is intentionally separated from the transformation by a white breath. This prevents the launch from becoming a decorative effect reel.

---

## 3. Motion color behavior

V1 uses only:

- `CLEAR`
- `SILVER_WHITE`
- `ICY_CYAN`

### Dynamic rule

- `CLEAR` dominates the frame.
- `SILVER_WHITE` describes boundaries and traces.
- `ICY_CYAN` appears at the origin point, contact point and center core.
- No purple.
- No amber/gold.
- No rainbow dispersion.
- No broad cyan wash.

Color is a **signal of activation**, not the background theme.

---

## 4. Material / motion quality

The V1 motion should feel:

- precise;
- light;
- restrained;
- organic without literal nature simulation;
- spatial without 3D spectacle;
- human, quiet and contemporary.

Avoid:

- glass-object advertising aesthetics;
- photoreal water;
- large bloom;
- particles;
- lens flares;
- neon;
- heavy blur;
- cinematic camera movement;
- decorative reflection environments.

---

## 5. Motion easing guidance

| Segment | Guidance |
|---|---|
| Point emergence | soft ease-out |
| Downward motion | controlled ease-in |
| Touch / boundary wake | ease-in-out |
| Ripple opening | ease-out with decreasing amplitude |
| Upward convergence | continuous ease-in-out / shape morph |
| Form contraction | slow ease-in-out, no bounce |
| White dissolve | linear-soft / opacity dissolve |
| Brand reveal | low-amplitude fade with slight optical settling |

No spring overshoot is required for the master launch animation.

---

## 6. Three official V1 motion variants

### A. `V1_STANDARD_MOTION`

End lockup:

```text
[SYMBOL]
序境
LUMENIS
```

Optional extended lockup:

```text
一点开境
A POINT OPENS A REALM
```

### B. `V1_KOREAN_MOTION`

End lockup:

```text
[SYMBOL]
서경
LUMENIS
```

### C. `V1_SYMBOL_ONLY_MOTION`

End state: V1 symbol only.

All three must use the **same 01–11 motion geometry**. Only the final lockup changes.

---

## 7. Reduced-motion / performance behavior

Launch animation must never block application truth or runtime readiness.

If `prefers-reduced-motion` is active, or motion assets fail:

```text
warm-white field
→ static corresponding V1 lockup
→ product UI
```

Do not substitute a fake loading animation.

For repeat visits, the product may use a short variant; however the master V1 timeline above remains the canonical full launch sequence.

---

## 8. Required production motion assets

```text
brand/logo/v1/motion/
├── master/
│   ├── lumenis-logo-motion-v1-standard.mp4
│   ├── lumenis-logo-motion-v1-standard.webm
│   ├── lumenis-logo-motion-v1-standard.gif
│   └── motion-v1-timeline.json
├── korean/
│   ├── lumenis-logo-motion-v1-korean.mp4
│   └── lumenis-logo-motion-v1-korean.webm
├── symbol/
│   ├── lumenis-logo-motion-v1-symbol.mp4
│   └── lumenis-logo-motion-v1-symbol.webm
├── source/
│   ├── scene-v1.json
│   ├── source.svg
│   ├── source.mjs
│   └── capture.mjs
├── reduced-motion/
│   └── reduced-motion-spec.md
└── LOGO-MOTION-V1-ASSET-MANIFEST.json
```

Editable source must accompany previews. MP4/GIF alone is not an engineering source.

---

## 9. Originality boundary

The V1 motion implementation must be original LUMENIS work.

External brands, motion galleries and UI/Shader libraries may be studied for pacing, continuity and material principles only. Do not copy motion source, shader code, vector paths, assets or branded transitions.

---

## 10. V1 acceptance

Motion V1 passes only if:

- shots 01–05 complete within approximately 2 seconds;
- 03→04→05 is continuous and understandable;
- 05→06 visibly converts the ripple/boundary into the mark pre-form;
- 06→07→08→09 is one uninterrupted contraction toward the center point;
- the return point is at the absolute visual center;
- white transition and white breath both exist before the final lockup;
- final lockup matches Static Logo V1;
- no purple, amber, rainbow, realistic ocean or glass spectacle appears;
- reduced-motion fallback remains usable;
- final motion source is versioned as V1 and is reproducible.
