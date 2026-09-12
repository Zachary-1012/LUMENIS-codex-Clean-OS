# Text expansion budget
Latin (en) typically expands ~1.15-1.3x vs zh-CN; Korean ~1.05-1.2x. Layout rules:
- nav labels use min-width tokens, never fixed px truncation at 1440+.
- buttons allow wrap up to 2 lines under 390; icon-only fallback at 360.
- table headers scroll/reflow rather than clipping; CJK keeps same glyph count budget.
- wordmark LUMENIS uses Geist Mono with letter-spacing; do not localize the Latin wordmark (locale only swaps the CJK/Korean companion: 序境 / 서경).
Key counts: zh-CN=164, en=164, ko=164.
