# ZBIP 四仓库·五产品 统一收敛基线（Architecture + Rules + UI/UX）

> 状态：**母规范（Mother Spec）v1.0，2026-09-01 依据用户《ZBIP 四产品统一收敛指令》固化**。
> 性质：一套母规范 + 各产品按职责适配，**不是把多个产品做成相同页面**。本文件只定规范与边界，不直接改业务代码。
> 权威顺序：当前源码 / 数据库 / Runtime 实测 ＞ 本基线 ＞ MASTER_DEVELOPMENT_BASELINE ＞ 历史文档 ＞ 聊天结论。冲突不自行覆盖，按第 9 节登记。

---

## 1. 仓库与产品身份（4 仓库 / 5 身份）

统一平台层：**Z-Brand Intelligence Platform（ZBIP）**。注意是 **4 个 Git 仓库、5 个产品/系统身份**——CTH-POMS 与 ZBMP 同处 Z-Brand-Core 一个仓库。

| 产品身份 | 英文/全称 | 核心职责 | 所在仓库 | 布局气质 |
|---|---|---|---|---|
| **CTH-POMS** | 广州太古汇舆情监测系统 | 监测·采集·舆情·风险·事件·报告·生产数据 | Zachary-1012/**Z-Brand-Core** | 舆情驾驶舱：高密度、风险优先、状态清晰 |
| **ZBMP** | Z-Brand Monitoring Platform | 品牌·市场·传播·竞品·消费者·事件·洞察·报告 | Zachary-1012/**Z-Brand-Core**（与 CTH 同 Core/DB/Runtime，非第二套系统） | 品牌情报工作台：工作台化、探索/关系/分析化 |
| **DCC** | Development Command Console | 研发治理·任务·审计·Evidence·测试·Release·版本与风险 | Zachary-1012/**Development-Command-Console** | 研发控制中心：控制台化、操作精准、审计可追溯 |
| **SICI** | 手机端 AI 开发执行控制台 | Code·Run·Preview·Test·Git·Deploy·Browser Surface（**执行**） | Zachary-1012/**SICI-Core** | 手机执行环境：执行/编辑效率优先、路径短、Mobile-first |
| **AI-D** | AI 开发研究与学习中枢 | Research·Experiment·Benchmark·Shadow·Evidence·Case·Learning·Capability（**研究学习**） | 随 SICI/治理仓（**仓库归属待确认，见 §9 冲突 C3**） | 研究工作台：实验可追踪、证据可验证、知识可沉淀 |

**铁律**：视觉/交互原则/设计系统可统一；产品职责不混合、信息架构不强行相同、核心数据不互相复制、Owner 不混乱。共享能力确定唯一 Owner，他方通过 API / Contract / Adapter / Evidence / Capability Registry 使用，禁止复制核心实现。

> 用户既有指令：DCC、SICI **本轮不动**；当前只在 Z-Brand-Core 内执行属于 CTH-POMS / ZBMP 的部分。

---

## 2. 统一分层架构（所有产品一致）

```
UI Layer → Interaction Layer → Application/Feature Layer → Domain Layer
        → Data/Service Layer → Adapter/External Layer
```
- 禁止：UI 直连数据库；页面承担复杂业务逻辑；采集器决定品牌业务规则；AI 决定生产事实；研究代码进入生产 Runtime；DCC 承担业务生产；SICI 承担研究逻辑；AI-D 修改生产核心。

---

## 3. 统一执行阶段（禁止跳阶段大改 UI）

1. **Phase 1 读取**：README / 本基线 / 目录 / 路由 / 组件 / 数据模型 / DB / 测试 / 现有 UI → 输出当前架构图、功能/归属/页面总览、UI/交互问题、技术债。
2. **Phase 2 收敛（不改码）**：Architecture / Feature / Ownership / Data Flow / UI / Interaction / Motion / Design Token 八张 Map。
3. **Phase 3 UI/UX**：先 Design Tokens（Color/Type/Icon/Spacing/Radius/Border/Motion/**Light-Dark**），再 Navigation/Layout/Components/States，最后才到具体页面。
4. **Phase 4 开发**：只改必要文件，优先复用/抽象/Adapter/Token/Component，避免复制粘贴。
5. **Phase 5 测试**：启动/路由/组件/交互/Light-Dark/Responsive/Mobile/Error/Empty/Loading + 核心回归；有 Browser 做真实 E2E。
6. **Phase 6 交付**：完成 / 未完成 / NOT_VERIFIED / 修改文件 / 架构·UI·交互·动效变化 / 测试 / 风险 / Commit SHA / 下一步。

---

## 4. UI 视觉母规范（ZBIP Design System）

母风格取法 GPT/Codex + Apple + Linear，最终形成 ZBIP 自有语言；**只学交互与工程方法，不复制第三方页面/源码**。

### 4.1 色彩
- 主色 Black/White/Gray（Stone 暖灰，见 `static/css/zbip-tokens.css`）。
- 彩色仅承担 Status / Active / Risk / Progress / 重要 CTA。
- **「彩色小圆点」是 ZBIP 状态视觉签名**：●Success ●Active ●Warning ●Risk ●Offline ●Processing；颜色不得是唯一信息载体，必须同时有文字/图标。
- 禁：大量彩色卡片、大面积渐变、廉价发光、堆叠阴影；优先细 Border + 低对比 Surface 表达层级。

### 4.2 Typography / Radius / Border
- 统一 H1/H2/H3/Body/Caption/Label/Metric 层级，禁止逐页自定义字号（用 --zb-fs-* / --zb-fw-*）。
- 统一 Button/Card/Input/Sheet/Panel/Modal 圆角（--zb-r-*，偏小提密度）。
- 细边框、低对比、弱阴影（--zb-shadow-1/2/3）。

### 4.3 线性 Icon 系统
- 单色、统一 Stroke/Weight/Size、`currentColor`、状态靠颜色表达；正式 UI 不用 emoji 作 icon，不混风格。
- 统一 Icon Size / Stroke / Color Token（本轮在 token 层补齐，见 §7）。

### 4.4 Light / Dark 双主题（硬要求，非简单反色）
- **Light**：白/浅灰 Surface、黑字、低对比 Border、彩色状态点（现状，已验收）。
- **Dark**：黑/深灰 Surface、白字、低对比 Border、彩色状态点；必须重处理 Surface/Border/Text/Secondary/Input/Card/Sheet/Modal/Nav/Status，保证可读性、层级、对比度、触控可见。
- 实现约束：primitive 色阶不动，只在语义别名层按 `[data-theme="dark"]` 重映射；默认无属性 = Light，**零视觉变化**；业务页面不直接写死颜色，只引用 --zb-* 语义别名，Dark 才可能自动生效。

### 4.5 Mobile-first
- DCC/SICI/AI-D 优先手机端；CTH-POMS/ZBMP 采用统一 Responsive Design System，手机不是桌面缩小版。
- 必须考虑：单手操作、拇指热区、Bottom Navigation、Bottom Sheet、Swipe、Long Press、Pull Refresh、横向滚动、Keyboard、Safe Area。
- 断点：390 / 430 / 768 / 1024 / 1280 / 1440。

### 4.6 统一交互语言
- Tap/Long Press/Swipe/Drag/Pull Refresh/Bottom Sheet/Drawer/Context Menu/Command Menu/Progressive Loading/Skeleton/Infinite Scroll。
- 统一状态：Loading/Empty/Error/Offline/Retry/Success/Warning/Risk/Processing；**任何操作必有反馈**（visual feedback → processing → result）。

### 4.7 Motion Tokens（动效只服务反馈/层级/状态/空间/物理感）
- 快速反馈 100–180ms；普通状态 180–280ms；页面/Sheet 280–420ms；Sheet/Toggle/Panel/Drag 用 spring 物理曲线。
- 禁无意义动画、禁过度动画拖垮低端机；`prefers-reduced-motion` 一键关闭。

---

## 5. 页面架构（WHO / WHAT / WHY / ACTION）

每页顺序：Navigation → Context → Primary Information → Primary Action → Secondary → Detail → History/Evidence。
避免：所有东西堆 Dashboard、一页几十卡、功能无层级。五产品布局差异见 §1 右列。

---

## 6. 不可动摇的生产/AI/采集红线

- **CTH-POMS 主体口径 P0**：`SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` / `subject_hit()` / `_subject_sql_and_values()` / `aggregate_events()` / `build_daily_report()` 及 Dashboard/统计/事件/报告主体过滤不得被 UI/架构收敛削弱；广州太古汇继续严格排除异地同名场景。
- **时间口径**：`publish_datetime`（真实发布）≠ `captured_at`（采集时间），报告默认 publish_datetime。
- **AI 是增强层不是事实 Owner**：可做分类/语义/聚类/趋势解释/消费者需求/报告润色/研究建议；不得独自决定原始事实、统计数字、主体最终口径、风险事实、报告事实。正式 Runtime = Ollama-only，云端默认关。
- **采集（RedNote/XHS 归属 CTH-POMS/ZBMP，走 Adapter）**：Source→Raw Evidence→Normalize→Quality Gate→Subject Gate→Dedup→DB。当前策略：**RedNote 香港/国际入口为主采集源，国内 XHS 暂缓数日**，后续两授权源交叉。失败真实记录，**禁止把失败显示成 0 条、禁止伪装 SUCCESS**；验证码/300012/IP 风险只识别→停→熔断→冷却→合法人工验证→恢复，不破解不绕风控。
- **Browser Surface 边界**："模拟真人浏览"仅指 UI/UX（自然滚动/惯性/渐进加载/展开/点赞收藏反馈/返回刷新），**不得**用于绕过验证码/封禁/访问限制/平台风控。
- **数据库**：不删/清/覆盖/初始化生产库；改结构只做向后兼容迁移且先备回滚。

---

## 7. Z-Brand-Core 落地映射（只做 CTH-POMS / ZBMP 部分）

> 不重复已完成的盘点；以下为"现状资产 → 本母规范要求"的对齐结论。

| 母规范要求 | Z-Brand-Core 现状 | 结论 |
|---|---|---|
| Phase1/2 八张 Map | FEATURE-FINAL-VERIFICATION-MATRIX(34 Feature 九态)、CAPABILITY_BASELINE、UI-FINAL-CAPABILITY-MAP、page-maps/*、资产扫描矩阵 | 已具备，不重扫；增量随开发维护 |
| Design Tokens | zbip-tokens.css v1.0（Stone/六语义/字距/圆角/阴影/motion/z/布局） | 已具备 Light；**本轮补 Dark 别名 + spring + icon + safe-area 变量** |
| 统一组件 | zbip-components.css + Step5c workbench 组件（卡/行/Sheet/toggle/seg/空状态/状态点） | 已具备初版，持续复用 |
| 双工作区/IA | Step4 外壳 + Step5c ZBMP 工作台 6 分组、CTH 21 项 6 分组 | 已具备架构，模块接入中 |
| Light/Dark | 仅 Light | **本轮：Dark 语义别名层预留，默认 Light 不变，画廊验证** |
| Motion | micro120/state220/page320（落在新区间内） | 补 spring 曲线 + sheet 时长，不改已验收现值 |
| Icon Token | 组件内已用线性 SVG，缺统一 token | 补 --zb-icon-* 变量 |
| Mobile-first | 已做 390 适配与取图 | Bottom Nav/Sheet/Safe-area 变量预留，交互后续逐页 |
| 模块真实数据 | 连接器/设置为真实，其余 9 模块诚实占位 | 下一主线：逐块接真实 API，接入一个实测一个 |

---

## 8. Evidence 固定字段（每次交付必填）

任务 / Baseline / HEAD / Remote HEAD / 修改范围 / 未修改范围 / 文件清单 / Owner / 依赖 / 风险 / 测试 / 实际结果 / Evidence / NOT_VERIFIED / Commit SHA / 下一步。不得只说"完成/通过"，未实测必须标 **未实测**。

---

## 9. 已登记冲突（STOP，待用户拍板，本轮不自行改）

### 用户裁决（2026-09-01，本版起生效）

- **C2（SICI 职责迁移）→ 同步研究**：SICI 定位为「手机端 AI 开发执行控制台」（Code/Run/Preview/Test/Git/Deploy/Browser Surface）；原"研究学习"职能移交 AI-D。**迁移走研究路线、不立即改 SICI 现有代码**，产出迁移研究文档后再定切换。
- **C3（AI-D 归属）→ 裁决：独立仓库、AI 研发、重度深化**：AI-D 为第五身份，**独立 Git 仓库**（不并入 SICI/DCC），承担 Research/Experiment/Benchmark/Shadow/Evidence/Case/Learning/Capability；战略目标是让「Zachary」尽早成长为可独立工作的 AI。研究深化路线见 `docs/AI-D-RESEARCH-ROADMAP.md`。由此仓库关系确定为 **4 个 Git 仓库承载 5 个身份**：Z-Brand-Core（CTH-POMS+ZBMP）、Development-Command-Console、SICI-Core、AI-D（独立新仓，仓库英文命名待最终确认，建议 `AI-D-Core` 对齐既有命名）。
- **C4（ZBMP 中文名）→ 裁决：固定**：对外中文固定为「Z-Brand 品牌监测平台」，英文 Z-Brand Monitoring Platform，不再变更。
- **C1（中间层 ZBP 是否保留）→ 附功能盘点，建议保留为逻辑分组（待最终确认）**：经盘点，ZBP「品牌业务生产平台」当前涵盖的功能面 = Z-Brand-Core 内 CTH-POMS（已生产）+ ZBMP（在建增强层）的全部生产业务：
  - **CTH-POMS（生产）六域**：总览（舆情驾驶舱 KPI/趋势/风险/事件/话题/日历）；监测（看板/预警/负面确认/笔记库/官方账号/话题战役/话题）；分析（分析/事件/事件图谱/日历）；品牌资产（品牌/太古/案例库/案例分析/知识库/品牌报告/APP 证据）；产出（日/周/月/专题报告与导出）；系统（设置）。底层引擎：采集（小红书 PRIMARY、抖音 disabled 待验证）、动态调度/熔断/冷却、主体过滤红线、去重、风险引擎、事件聚合、AI 增强（Ollama-only）、代理池、健康检查、自动恢复、证据链、PDF/Word/Excel 导出。
  - **ZBMP（在建）六组**：概览 Home；品牌（品牌资产/竞品监控/案例库）；监测（内容监测/话题战役）；洞察（事件中心/事件关系/AI 评估）；产出（报告中心）；系统（连接器/工作区设置/密钥体系）。
  - **建议**：ZBP 不是运行时、不是第四个仓库，仅作为"业务生产平台"逻辑分组标签，正好容纳 CTH-POMS+ZBMP，与 DCC/SICI/AI-D 三个并列域同属 ZBIP；保留它成本为零且让五身份归属清晰。**最终是否保留该中间层名称待用户确认；确认前不做全局改名。**

> 已裁决项（C2/C3/C4）据此推进；C1 在最终确认前，代码/UI 仍以当前源码与现行命名基线为准，不做全局替换。任何改名必须引用分析 + 回归 + Evidence，不得整目录覆盖。

---

## 10. 本轮（Step5d）范围声明

- 做：固化本母规范；产出 ZBC 收敛对照；在 **token 层**补 Dark 语义别名（默认 Light 零变化）、spring/sheet motion、icon、safe-area 变量；组件画廊加主题切换验证；Staging 8301 实测 Light 不回归 + Dark 变量正确切换。
- 不做：不改业务/采集/DB/主体口径；不全局替换命名；不动 DCC/SICI；不把 Dark 强套到未迁移的旧业务页；生产 8201 冻结；仅 ui/staging-foundation 旁路。
