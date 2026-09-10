# LUMENIS / 序境 — Logo V1 Registry

> Version: **Logo V1**  
> Effective: 2026-09-11  
> Status: **APPROVED DESIGN DIRECTION / ASSET IMPLEMENTATION PENDING**  
> Scope: Static identity + Motion identity  
> Parent authority: `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`

---

## 1. V1 files

### Static V1

`LUMENIS-LOGO-STATIC-V1-20260911.md`

Defines:

- mark geometry;
- three official static variants;
- Clear / Silver White / Icy Cyan color system;
- Chinese / English / Korean lockups;
- canonical brand copy;
- originality and production asset requirements.

### Dynamic V1

`LUMENIS-LOGO-MOTION-V1-20260911.md`

Defines:

- canonical 4.8s launch sequence;
- 01–05 within ~2 seconds;
- ripple → upward convergence → mark formation;
- continuous contraction → center point;
- white transition → white breath → final brand lockup;
- Standard / Korean / Symbol-only motion variants;
- reduced-motion and source-asset requirements.

### Machine-readable V1 manifest

`logo-v1-spec.json`

Provides stable IDs and implementation metadata for future Experience/Codex integration.

---

## 2. V1 visual direction

The approved direction is the narrow vertical seed/realm symbol established in the 2026-09-11 design discussion and approved reference boards.

Core philosophy:

```text
芥子纳须弥
一点开境

Point / Seed
→ Boundary
→ Realm
→ Expansion
→ Return to One
```

This is a **metaphoric form**, not literal water, ocean, glass or botanical illustration.

---

## 3. Official variants

| Stable ID | Variant | Lockup |
|---|---|---|
| `logo.v1.standard` | Standard | Symbol + `序境` + `LUMENIS` |
| `logo.v1.korean` | Korean | Symbol + `서경` + `LUMENIS` |
| `logo.v1.symbol` | Symbol-only | Symbol only |
| `motion.logo.v1.standard` | Standard launch | V1 motion → Standard lockup |
| `motion.logo.v1.korean` | Korean launch | V1 motion → Korean lockup |
| `motion.logo.v1.symbol` | Symbol launch | V1 motion → Symbol-only lockup |

---

## 4. Integration rule

Logo V1 is a brand/experience specification. It does **not** authorize backend, route, database, runtime, permission, Evidence or Production Truth changes.

When final assets are delivered, Codex/frontend integration should consume versioned brand assets and motion sources without redesigning the identity.

Recommended future implementation root:

```text
brand/logo/v1/
├── static/
├── motion/
├── source/
└── manifests/
```

Do not overwrite V1 in place when the brand direction materially changes. Create V1.1 for compatible refinements or V2 for a new identity direction.

---

## 5. Reference-board handling

The approved visual boards are design references for V1. They must not be treated as final vector engineering assets. Final production mark/wordmarks must be recreated as original editable vectors and validated at small sizes.

If reference images are later committed, place them under a clearly marked non-production reference path such as:

```text
00-GOVERNANCE/BRAND/LOGO-V1/reference-boards/
```

and label them `REFERENCE_ONLY`.

---

## 6. Read order for Codex / future AI

```text
1. README.md                  ← this file
2. LUMENIS-LOGO-STATIC-V1-20260911.md
3. LUMENIS-LOGO-MOTION-V1-20260911.md
4. logo-v1-spec.json
5. final brand/logo/v1 assets when implemented
```

This directory is the first formal repository record of **LUMENIS Logo V1 — Static + Dynamic**.
