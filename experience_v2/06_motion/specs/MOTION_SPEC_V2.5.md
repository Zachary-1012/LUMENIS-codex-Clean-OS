# LUMENIS Motion Spec V2.5 (engineering)
Source of truth: `../source/MOTION_SOURCES_V2.5.json` (M01–M15). Reproducible capture: `../capture/capture_motion.mjs` (Playwright + system Chrome, real interactions) → webm, then `convert_motion.py` (ffmpeg) → mp4/gif; reduced-motion clips go to `../reduced-motion/`.

## Rules
- Animate `opacity`/`transform` only; never `transition: all`; never animate width/height/padding/margin.
- Scale: micro 100–200ms (standard ease), content 200–300ms, layout 250–400ms; press scale(.97).
- Every motion has a `prefers-reduced-motion` fallback (instant/static/final value) — see each source row.
- Motion is semantic (Touch/Open/Trace/Shift/Settle/Return), paired with LumHaptics verb; never decorative loops.
- GSAP/Lenis are engines only; Lenis inertial scroll is disabled under reduced motion.

## Clip list (what each recorded demo proves)
| File | Sources | Proves |
|---|---|---|
| M01-M04_ai-composer-enter-press | M01,M04 | page enter stagger + composer send press (.97) |
| M03_tab-shift | M03 | tab indicator shift + panel cross-fade |
| M06-M08_modal-toast | M06,M08 | EFFECT confirm modal in + outcome toast |
| M12_orb-flow | M12 | Lumen Core processing→done flow (no stars) |
| reduced-motion_composite | all | reduced-motion: no transform animation, content present |

## Reproduce
```
node capture/capture_motion.mjs        # writes capture/webm/*.webm
python capture/convert_motion.py       # writes mp4/ gif/ reduced-motion/
```
Chrome must be the system build with swiftshader flags (already set in the script); ffmpeg at D:/lum-toolchain/ffmpeg.
