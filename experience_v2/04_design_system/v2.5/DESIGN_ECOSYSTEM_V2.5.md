# LUMENIS Design Ecosystem V2.5 — 总纲
序境 / LUMENIS · Experience Layer · `a quiet instrument of truth`
版本 2.5.0 · 基线 HEAD `ab67612` · 呈现层唯一视觉真源 = `10_prototype/assets/*.css|js`

> 本文是 V2.5 的伞文档（umbrella）。V2.5 不重造设计系统，只把 Experience V2 / Design Language v2.4
> 已存在的资产 **Read → Audit → Normalize → Systematize → Calibrate → Validate → Package**。
> Legacy UI 永久 READ-ONLY，只作能力证据，不复刻、不回流覆盖新呈现层。

---

## 1. 一句话定位
让数据与证据当主角，界面后退。LUMENIS 不是通用 AI SaaS，而是一台「安静的真相仪器」：
金属单色、编辑式留白、序轴/境层、证据可追溯、AI 是增强层而非事实所有者。

## 2. 视觉 DNA（不可漂移项）
| DNA | 规定 | 禁止 |
|---|---|---|
| 材质 | 黑银（light）/ 白银（dark，精确反相）金属单色 | 紫/靛蓝 AI 模板、彩色英雄渐变 |
| 字体 | Geist 仪器体 + Geist Mono（ID）+ Fraunces/宋体（文学衬线 display） | 默认 Inter、全站无衬线平铺 |
| 结构 | Lumen Axis 序轴、Strata 境层、de-boxed 层级、发丝线 hairline、留白 | 白卡墙 card wall、装饰点/引导横线、侧边色条 |
| 终点色 | Icy Cyan 只用于「活数据 / processing / focus」 | 用青色做大面积 chrome 填充 |
| AI 球体 | 原创 Lumen Core（原生 WebGL1，球内混沌流转，无星星） | three.js 堆料、外部分形素材、星空粒子 |
| 深度 | 表面阶梯 + 发丝表达层级；仅浮层用阴影 | 卡片堆叠 drop shadow、阴影+边框叠加 |
| 动效 | 只动 opacity/transform，语义化、可中断、reduced-motion 降级 | `transition:all`、无意义装饰动画 |

## 3. 生态结构（本目录资产映射）
```
Foundations  → DESIGN_FOUNDATIONS_V2.5.md（color/material/type/grid/spacing/radius/hairline/icon/orb/motion/a11y/responsive）
Tokens       → DESIGN_TOKEN_SYSTEM_V2.5.json（从 tokens.css 确定性提取，light/dark/realm）
Components   → COMPONENT_REGISTRY_V2.5.json（Canonical/Variant/Domain/Deprecated/Legacy/Experimental）
Patterns     → PATTERN_REGISTRY_V2.5.json（Context→…→Provenance 11 类叙事模式）
Page Families→ PAGE_FAMILY_MATRIX_V2.5.json（AI Workspace/CTH/BMP/Shared/SYSTEM × 四域方言）
Responsive   → RESPONSIVE_SYSTEM_V2.5.md（8 断点，adaptive 而非缩放）
Motion       → MOTION_SYSTEM_V2.5.md（动词语义/token/时长/M01–M15/reduced-motion）
State        → STATE_SEMANTICS_V2.5.md（0/NULL/UNKNOWN/N-A/STALE/ERROR 严格区分）
A11y         → ACCESSIBILITY_RULES_V2.5.md
Calibration  → AI_01_CALIBRATION_V2.5.md / CTH_01_CALIBRATION_V2.5.md（两个校准母版）
Engineering  → DESIGN_ENGINEERING_ACCEPTANCE_V2.5.md（Codex 接入验收）
Changelog    → DESIGN_ECOSYSTEM_CHANGELOG_V2.5.md（v2.4→v2.5 差异）
```

## 4. 六个传播原语（Brand Research V1，编码进系统）
- **Point 点**：主体 / 焦点 / Lumen Core，一屏一个主焦点。
- **Axis 序轴**：阅读与因果的方向（Subject→…→Outcome），用空间与发丝表达，不画流程图。
- **Boundary 界**：容器与域的边界，优先发丝/留白，少用盒子。
- **Strata 境层**：信息层级像地层，靠表面阶梯与间距分层。
- **Trace 迹**：证据链 Claim→Evidence→Source，选中走极细 icy 路径。
- **Return 归点**：drill-down 后可回到主体与上下文，面包屑/context panel 常驻。

## 5. 四域方言（一个生态，四种口音，不是四个产品）
| Realm | 前缀 | 性格 | 轴强度 | 留白 | 数据表达 |
|---|---|---|---|---|---|
| Operational 商业运营 | CTH | 更密、更强秩序、Trace 优先 | 0.34 | 紧 | 表格/趋势/风险密度高，秩序网格 |
| Editorial 品牌市场 | BMP | 留白大、媒体叙事、策展节奏 | 0.13 | 大 | 开放版式、局部大尺度、边界切割 |
| Intent AI | AI | Core 前置、状态转化可读、Artifact 优先 | 0.18 | 中 | 对话+证据+工作区+行动 |
| Studio 共享内容 | SH | 内容主舞台、控件后退、Evidence 随叫随到 | 0.12 | 中大 | 近白场，创作工具克制 |
| System | SYS | 运维秩序、状态优先 | 0.30 | 紧 | 表格/状态机/健康度 |

方言变量由 `app.js` 按屏 ID 前缀写入 `.lum-app[data-realm]`，仅调 `--lum-editorial-gap / --lum-axis-strength / --lum-trace-strength`，不改语法。

## 6. Field System 取代 Card System
- 默认开放：内容浮在 canvas 上，靠 `surface ladder + hairline + spacing` 成组。
- `section.lum-grid-N > article.lum-card` 已全局字段化（透明、顶部 1px 发丝、hover 才起雾、图标去方框）。
- 只有「需要被 containment」的内容才用实体面：图表、证据原件、可拖拽上传、浮层。
- 阴影与边框二选一；内层半径永远小于外层；圆角卡禁止顶部色条。

## 7. Production Truth 红线
设计层**不发明** API/DB/Permission/Evidence/Metrics/Runtime/Agent 能力。
原型所有数据 `data-source="prototype"`、DESIGN_ONLY；需要但后端没有的能力一律标
`DESIGN_REQUIREMENT_ONLY / NOT_IMPLEMENTED / REQUIRES_BACKEND_CONFIRMATION`，见 `12_contracts/BACKEND_GAP.json` 与 `06_contracts/unknown-bindings.json`。EFFECT 类动作点击只弹 confirm（scope/target/permission），永不假成功。

## 8. 验收门（与 16 节一致）
NO_SECOND_DESIGN_SYSTEM / EXPERIENCE_V2_REUSED / AI_01_CALIBRATED / CTH_01_CALIBRATED /
DESIGN_TOKEN_CONSISTENCY / COMPONENT_DUPLICATION=CONTROLLED / PATTERN_DUPLICATION=CONTROLLED /
RESPONSIVE / STATE_SYSTEM / MOTION_SYSTEM / ACCESSIBILITY / LEGACY_BOUNDARY /
PRODUCTION_TRUTH_NOT_FABRICATED / GENERIC_SAAS_CHECK / CARD_WALL_CHECK / PURPLE_AI_TEMPLATE_CHECK。
判定证据与命令见 `DESIGN_ENGINEERING_ACCEPTANCE_V2.5.md`。
