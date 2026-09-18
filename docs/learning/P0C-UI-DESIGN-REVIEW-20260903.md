# P0-C UI 设计系统一致性审查（glm-5.3）

> 日期：2026-09-03 | 模型：glm-5.3 | 消耗：per_call 1次
> 目的：审查 ZBIP 设计系统与 token 一致性 + 增量收敛闭环

---

Let me carefully analyze the materials provided.

The task: Review ZBIP design system consistency and convergence. Compare the desensitized design document against zbip-tokens.css (first 167 lines).

Key checks requested:
1. Document vs Token consistency — especially semantic colors (doc says Success #22C55E, CSS has #16A34A?), radius (doc 8px buttons vs CSS --zb-r-md:6px), shadows.
2. Visual mother-spec self-consistency
3. Incremental convergence safety (Strangler pattern)
4. Executable optimization list (5-8 items)
5. Interaction/motion loop

Let me do detailed comparison:

**1. Color tokens:**

Stone scale:
- Doc: stone-0 #FFFFFF, 50 #FAFAF9, 100 #F5F5F4, 200 #E7E5E4, 300 #D6D3D1, 400 #A8A29E, 500 #78716C, 600 #57534E, 700 #44403C, 800 #292524, 900 #1C1917
- CSS: identical values.
- BUT: usage annotations differ! Doc says stone-700 = 主文本, stone-800 = 强调文本/按钮. CSS says stone-800 = 主文本, stone-900 = 标题/最强文本/品牌主操作. And semantic alias: --zb-text: var(--zb-stone-900), --zb-text-secondary: stone-600. So doc's semantic usage mapping (700 = 主文本) conflicts with CSS alias (900 = 主文本). This is an inconsistency in role mapping, though primitive values match. Also doc doesn't define --zb-text alias layer. Actually doc says "700 主文本" and "800 强调文本/按钮". CSS: --zb-text = stone-900. So main text in doc is stone-700 but CSS alias uses stone-900. Inconsistent role mapping.

Semantic colors:
- Doc: Success #22C55E, Warning #F59E0B, Danger #EF4444, Info #3B82F6, Idle #D6D3D1
- CSS: --zb-success #16A34A, info #2563EB, attention #D97706, risk #EA580C, danger #DC2626, unknown #78716C
- All six differ from doc. Also naming differs: Warning→attention, Idle→unknown; CSS adds risk (orange #EA580C) which doc doesn't have. Doc has 5 semantic colors; CSS has 6. Also Idle #D6D3D1 (stone-300) vs unknown #78716C (stone-500) — quite different.
- Rationale: CSS values are darker (600-level Tailwind colors) — better for text/fg contrast on white; doc values are 500-level, better as fills/status dots. Since CSS defines fg/bg/border triples, choosing darker fg is reasonable for contrast/readability (Readable principle). But doc not updated = inconsistency. Whether "合理" — partially: for fg usage the darker values are more accessible; but the doc declares only single values. The mismatch should be resolved by updating doc or noting fg vs dot usage. Status dots might want brighter #22C55E.

Radius:
- Doc: 4px small elements (标签、状态点), 8px 按钮/输入框/卡片, 12px 弹窗/抽屉/大卡片. 禁止超过16px.
- CSS: --zb-r-sm 4px (Badge/小标签/输入), --zb-r-md 6px (按钮/控件默认), --zb-r-lg 8px (卡片/弹窗), --zb-r-xl 12px (大面板，少用), pill 999px.
- Differences: input radius — doc 8px, CSS puts 输入 at r-sm 4px (comment says "Badge/小标签/输入"). Doc says input 8px. Buttons: doc 8px, CSS 6px. Cards: doc 8px ✓ (r-lg 8px). Modal: doc 12px, CSS comment says 卡片/弹窗 at r-lg 8px, xl 12px 大面板. So modal radius mismatch: doc 12px vs CSS lg(8px) for 弹窗.
- Also doc 4px for 状态点 — status dots are circles, so pill 999px makes sense; doc "圆角4px 状态点" is odd for a 7px dot (round). Minor conflict: StatusDot 7px round with glow — a 7px circle needs 50%/999 radius not 4px. Doc self-inconsistency there.
- Is 6px vs 8px difference reasonable? CSS comment says "偏小提密度" — smaller radius for density, consistent with Dense principle. But it contradicts doc's stated 8px for buttons. Needs alignment: either update doc or tokens. This is a real inconsistency.

Shadows:
- Doc: card default `0 1px 3px rgba(28,25,23,0.04), 0 4px 12px rgba(28,25,23,0.03)`; hover `0 2px 8px rgba(28,25,23,0.06), 0 8px 24px rgba(28,25,23,0.05)`; button `0 1px 2px rgba(28,25,23,0.15)`.
- CSS: shadow-1 `0 1px 2px rgba(28,25,23,.06)`, shadow-2 `0 4px 12px rgba(28,25,23,.08)`, shadow-3 `0 12px 32px rgba(28,25,23,.12)`.
- All differ in values and structure (doc has two-layer shadows; CSS single layer). Opacity higher in CSS (.08/.12 vs .03/.05). Doc forbids "无意义阴影" and says 极弱; CSS shadow-3 .12 is stronger but used only for Modal. Button shadow in doc (rgba .15) doesn't exist in CSS — no button shadow token. Inconsistency.
- Reasonableness: CSS 3-tier elevation is more systematic; doc values are dimmer. The doc's button shadow .15 is quite strong relative to "微光银" — CSS dropping button shadow aligns with 边框优先. But doc not updated.

Typography: doc doesn't fully specify (Metric 24-32px, labels 11px). CSS has fs-12 min — no 11px token. Doc mentions 11px label text; CSS min font token is 12px. Inconsistency (minor). Doc Metric big number 24-32px → CSS fs-24, fs-30 (no 32). fs-30 vs doc 32 — approximate mismatch.

Spacing: doc 4/8/12/16/24/32/40; CSS adds sp-8 48px. Doc says 组件内边距8-16 etc. 48px addition beyond doc's list — doc's list didn't include 48. Minor: CSS extends; not conflict per se but doc's "只允许这些值" comment vs doc list differs. Actually the CSS comment says "只允许这些值" including 48. Doc doesn't include 48. Minor divergence.

Motion:
- Doc: micro 100-150ms ease-out; state 180-280ms ease-in-out; page 280-400 (truncated). 
- CSS: 120/220/320 with cubic-bezier(.16,1,.3,1) standard etc. 120/220/320 all fall within doc ranges (100-150, 180-280, 280-400). ✓ Consistent. Plus additions: quick 140ms, sheet 360ms — the CSS comment explicitly says these align with 母规范区间 (100-180/180-280/280-420) — hmm, doc says micro 100-150 but CSS comment mentions 快速100-180. Slight discrepancy between doc ranges and CSS comment's claimed ranges (100-180 vs 100-150). The doc excerpt is truncated at "280-400" so page transition range is 280-400; CSS sheet 360 falls within. The comment mentions 280-420 which differs from doc's 280-400. Minor inconsistency in the comment.
- Multiple ease sets: standard/in/out + emil-out/emil-inout/drawer + spring. Redundancy: three overlapping curve systems (10.1 basic, 10.2 spring, 10.5 emil). Potential conflict: which to use? CSS says emil is 权威, but old variables retained. Risk: developers use different curves for same interaction. Also --zb-ease-in exists but comment says "UI 绝不用 ease-in" — token defined but forbidden; contradiction-ish (defining a token you forbid). Actually ease-in might be for exit animations — the comment says 进/出场→out. Hmm, emil guidance: enter/exit → out. So ease-in token is vestigial. Flag it.

Icons:
- Linear icon 1.75px stroke, currentColor, sizes 14/18/20. Doc mentions icons but not stroke spec in excerpt. Doc's "大彩色语义 icon" vs Linear Icon token says 单色/currentColor — potential conflict: how do "large colorful semantic icons" coexist with single-color currentColor icons? The mother spec includes both: Linear icons for UI chrome (monochrome) and large colorful semantic icons for status/empty states. Need clear rule for when color is allowed. The token layer only defines monochrome icon tokens; colorful semantic icons would use semantic colors. Not a token conflict per se but governance rule needed. The doc 1.2 says "大型状态点（彩色圆点）" wait it says "小型状态点（彩色圆点）作为视觉签名" and design language "大彩色语义 icon". So both exist. CSS tokens don't define 大 icon size (only up to 20px lg). "大彩色语义icon" — EmptyState icon needs larger size (e.g., 24-32px). Token gap: no --zb-icon-size-xl. Flag as gap.

z-index: doc doesn't specify z-index in excerpt; CSS defines. Fine.

StatusDot: doc says 7px with 发光效果. But doc 1.2 禁止 "发光阴影"? Shadow section forbids "发光阴影". StatusDot glow conflicts with "禁止发光阴影" — though that's about shadows; dot glow may be an exception. Also CSS has no glow token. Minor self-contradiction in doc: "状态点带发光效果" vs "禁止发光阴影" — arguably different things (glow on dot vs shadow glow). Worth flagging as ambiguity. Also no token for status dot size/glow in CSS.

Semantic alias layer: --zb-surface-raised: #FFFFFF same as surface — fine. --zb-brand = stone-900 (近黑主操作) — consistent with doc "主按钮近黑渐变". Wait doc says Button "主按钮近黑渐变" — gradient! But design language forbids "大面积渐变". 近黑渐变 on button — small gradient allowed? CSS has no gradient token. Doc self-tension: 禁止大面积渐变 but button uses 近黑渐变. CSS defines brand as flat stone-900. Inconsistency: doc says gradient, tokens imply flat. Flag.

**2. Visual mother-spec self-consistency:**

- Stone 10-step warm gray: complete, monotonically darkening, includes pure white. OK.
- Six semantic (fg/bg/border three layers): CSS has success/info/attention/risk/danger/unknown — six. Each with bg/border. Check contrast: fg #16A34A on bg #F0FDF4 — contrast ratio? #16A34A on white ~ 3.3:1 — for text that's below 4.5:1 (WCAG AA for normal text). As fg for icons/dots ok; for text borderline. unknown fg #787