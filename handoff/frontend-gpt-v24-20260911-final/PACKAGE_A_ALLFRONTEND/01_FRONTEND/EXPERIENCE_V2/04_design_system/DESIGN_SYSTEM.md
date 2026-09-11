# LUMENIS Design System (self-built)

Original visual language. No third-party UI kit, no copied visual. Machine form: `design-tokens.json` + `PATTERN_REGISTRY.json`; runtime: `10_prototype/assets/tokens.css`, `optical.css`.

> **v2.4 current —『序 · Editorial Lumen OS』(structural) + v2.3 metal monochrome**: see `LUMENIS_DESIGN_LANGUAGE.md`. Serif editorial display over sans body; the **Lumen Axis** (margin axis + index-catalog rail nodes + masthead rule); faint strata grid; de-boxed open-strata cards; **black-silver (light) / silver-white (dark, inverse), zero purple**; primary action = canvas inverse metal; self-rendered canvas **chaos orb** (no star); Icy only for data-viz/status. Research basis in `13_research/RESEARCH_FINDINGS.md`.

## Color (v2.3/v2.4 metal monochrome authority — supersedes warm-paper/indigo)
> Metal near-monochrome. Primary action is always the **canvas inverse** (light = near-black chrome, dark = silver with inverse dark text). **No indigo/purple anywhere.** Icy Cyan is demoted to data-visualization & status only — never a chrome fill.
### Light — Black on Silver
- canvas `#ECEDEF` (silver mist) · ambient `#E3E6EA` / `#DDE0E5` · surface `rgba(250,250,251,.86)` · raised `#FFFFFF` · subtle `#F1F2F4` · sunken `#E5E7EA`
- text `#16181D` / text-2 `#545963` / text-3 `#888D96` · hairline `rgba(20,22,28,.10)` / line-solid `#DCDFE3`
- primary metal `#1B1D23` · brand gradient `#3A3D45→#17191E→#05060A` + top metal sheen · **data-viz-only Icy `#4FC4E8`** · positive `#1F9D6B` · warning `#B07416` · critical `#C0414D` · info `#3A63A8`
### Dark — Silver on Black (inverse)
- canvas `#07080A` (near-black) · ambient `#10131A` / `#0E1016` · surface `rgba(18,19,23,.8)` · raised `#1F2128` · subtle `#181A20` · sunken `#0A0B0E`
- text `#F1F2F4` / text-2 `#AEB3BD` / text-3 `#7E848F` · hairline `rgba(255,255,255,.09)` / line-solid `#262930`
- primary silver `#E9EBEF` · silver gradient `#FFF→#D7DAE0→#A9AFB9` · **inverse text on silver button `#0E0F12`** · **data-viz-only Icy `#6FD6F2`** · positive `#43C68B` · warning `#F0B45B` · critical `#FF7A85` · info `#79A7FF`

### Material, axis & strata (v2.4)
- ultra-subtle grain (160px, .04 light / .06 dark) + a faint **strata baseline grid** (320px columns / 88px baselines) behind content
- outer `.lum-card` = open stratum: near-flat, hairline, **no shadow**, hover only deepens the rule; nested `.lum-card-solid` = solid evidence artifact with a flat top light → open-strata / solid-artifact depth
- metal sheen `--lum-metal-sheen` on the inverse primary button / logo; the **Lumen Axis/Line** (`--lum-lumen-line`, brand→slate→icy) is the only signature gradient, used for margin axis, rail nodes, KPI top edge, steps/evidence, masthead rule
- precision radius xs3/sm6/md10/lg14/xl18 (pill 999); literary whitespace via `--lum-editorial-gap: clamp(22px,2vw+14px,44px)`

Semantic rule: color always pairs with icon/text (never color alone) for accessibility; unknown is a real, neutral state.

## Typography (fluid, device-adaptive)
**v2.4 dual-voice**: body/controls sans — `system-ui, "PingFang SC", "Microsoft YaHei", "Apple SD Gothic Neo", sans-serif`; **display serif** `--lum-font-display` = `"Songti SC","STSong","Noto Serif SC","SimSun",Georgia,"Times New Roman",serif` for page mastheads / editorial section heads / KPI numerals (weight 600, tabular lining); mono `ui-monospace/Consolas` for evidence IDs, AI trace, eyebrow index. No webfont dependency.
**fluid scale via `clamp()` (360→1440+)** — body cluster near-constant for legibility, display cluster scales: fs-2xs..lg ≈11→16.5; fs-xl/2xl/3xl = 16→19 / 19→24 / 23→30; fs-4xl/5xl(display) = 28→38 / 32→48. Weights 400 body · 450 dense/nav · 600 UI/subhead · 650 display (no 700 except micro-badges). Tracking: display -0.022em, headings -0.012em, eyebrow 0.22em. Line-height 1.14/1.32/1.55. Tabular numerals for all metrics. Mono only for evidence IDs / AI trace / technical codes (never business chrome).

## Spacing / radius / elevation (fluid)
4-pt base scale; **fluid page pad `clamp(16px,2.1vw+9px,40px)`, section gap `clamp(14px,1.3vw+10px,30px)`, rail width `clamp(208px,15.4vw,248px)`**; radii control 10 / card 14 / panel 20 / pill 999. **Cards are near-flat (`--lum-sh-flat`: 1px top catch-light + 1px whisper shadow) — hierarchy comes from hairlines + whitespace; sh-2/sh-3 only for floating layers/drawers/OPT.** Glass uses backdrop-blur with a translucent surface token, not opacity hacks.

## Optical material tiers (self-built `optical.js`, 7 parameters)
- **A Truth surface — OPAQUE**: tables, evidence, canonical, metric, report, long reading. Always opaque for legibility/trust.
- **B Spatial surface — SOFT_GLASS / STANDARD**: rails, topbar, context drawer, cards (controlled blur).
- **C Optical surface — HIGH**: only AI Composer (OPT-01), active dock bubble (OPT-02), capability→task morph (OPT-03), transient tool dock (OPT-04).
Degradation chain HIGH → STANDARD → SOFT_GLASS → OPAQUE keeps 100% function on weak GPU / reduced-motion / small screens. Static scene captures once; dynamic per-frame with dirty-rect budget (research showed naive real-time refraction ~14 FPS — hence strict budget + mandatory fallback).

## Composition patterns (PATTERN_REGISTRY, PAT-*)
POINT (metric/state chip), LINE (evidence chain/timeline/step rail), SURFACE (card/split panel), SCREEN (overview/workbench/composer/entry), WORKFLOW (capability→task, upload pipeline, approval). Each pattern lists which screens consume it and its renderer, so Codex maps a pattern once and reuses it.

## 70 / 20 / 10
70% information clarity (density, hierarchy, evidence), 20% spatial material (depth/glass), ≤10% motion delight. A production tool first — never a "pretty AI demo".

## Theme
Light default; dark via `[data-theme="dark"]` on `.lum-app`; the QA control and SYS-05 toggle it. Tokens, not per-component hex, drive theme.
