# FRONTEND_REMAINING_GAPS_V2.5

Experience Layer 完成后仍存在的缺口，按要求分级。**所有后端/模型/运行时接入一律为 Codex task，豆包不实现、不伪造。**

## P0 blocker（阻断 Production）
| ID | Gap | 现状（真实） | Owner | 说明 |
|---|---|---|---|---|
| P0-BE-01 | 54 项 ViewModel→后端未绑定 | 06_CONTRACTS/unknown-bindings.json，全部 UNBOUND_REQUIRES_BACKEND_CONFIRMATION | CODEX | 前端 viewmodel READY，缺真实 endpoint/permission/evidence；禁止补假接口 |
| P0-BE-02 | 28/29 动作 target/scope=UNKNOWN | PAGE_DELIVERY_REGISTRY actions_unbound=28 | CODEX | 需接真实 Command/Permission 后才是可点动作 |
| P0-RT-01 | 未接真实 Runtime/Identity | /api/runtime/identity 未对接，原型为静态 | CODEX | 前端不得自造运行身份 |
| P0-E2E-01 | 无生产级 Critical E2E | 当前仅有设计层渲染/交互证据，无对真实后端 E2E | CODEX | 需后端就绪后补，禁止用原型录屏冒充 E2E |

## P1 before production
| ID | Gap | 现状 | Owner |
|---|---|---|---|
| P1-FE-01 | 原型为零构建原生静态实现（10_prototype：index.html+20 assets+4 data），非 React/Vue 工程 | 无 package.json/lock/build/lint/单测（设计原型刻意零构建，契约钩子稳定） | CODEX（移植到生产前端栈：路由/Store/API client/types/工程化） |
| P1-FE-02 | i18n 目前为前端内置三语（zh/en/ko 各164 key） | 未接生产 i18n 服务 | CODEX |
| P1-A11Y-01 | 需在真实工程补键盘焦点陷阱/屏幕阅读器走查 | 设计层已修表单名/对比/reduced-motion | CODEX |
| P1-PERM-01 | Permission/Approval 仅前端状态呈现 | 无真实权限网关 | CODEX |

## P2 optimization
| ID | Gap | 现状 | Owner |
|---|---|---|---|
| P2-PERF-01 | 冷启~1306ms（本地 file:// 含本地字体） | 暖~403ms；工程化后做 bundle/code-split | CODEX |
| P2-MOTION-01 | M01–M15 覆盖核心交互，长尾微交互可继续补 | 已建 motion token 与 reduced 兜底 | DOUBAO(后续设计) / CODEX(实现) |
| P2-ICON-01 | 69 图标覆盖当前 44 屏；新增能力需补图标 | lum-icons-sprite | DOUBAO |

## Design gap（设计层，豆包可继续）
| ID | Gap | 现状 |
|---|---|---|
| DG-01 | 四域方言已建 token（operational/editorial/intent/studio），深度页面可继续强化差异但不破坏统一生态 | DESIGN token READY |
| DG-02 | 平板 1024/768 已自适应，复杂表格在小屏的卡片化可逐表精修 | 已无横向溢出 |
| DG-03 | 本次已清除“内部流程外显”（SH-01/AI-02 等）；如新增页面须继续遵守：流程入底层、仅 AI 对话显思考 | 已加 sections.internal 机制 |

## Backend dependency / Data dependency / Runtime dependency
- Backend：54 绑定 + 28 动作 + 真实 API schema（request/response/error）全部 CODEX，见 06_CONTRACTS/BACKEND_GAP.json。
- Data：原型使用 DESIGN_ONLY fixtures（5 个示例 Subject，data-source=prototype）；真实 Canonical/Evidence/Metric 数据由后端提供，前端不造数。
- Runtime：启动链 scripts/start_production.ps1 → run_supervised.py → app factory（host 0.0.0.0 port 8201）为后端事实；前端只消费，不持有。

## Codex task（明确不属于豆包，禁止豆包实现）
- 第三方模型 / 开源模型接入（OCR/NLP/ASR/Vision/Embedding/Reranker）
- Vector Database、OSS Agent Runtime / Framework、Provider Adapter 后端实现
- AI_OFF 后端工程、Shadow Mode 后端、OSS License 集成决策
- Backend Production Convergence、真实 Permission/Evidence/Metric/Runtime 对接
- 将 10_prototype 移植为生产前端工程（含 API client/store/types/单测/E2E/CI）

## 不属于缺口（已完成，避免重复劳动）
- 自有设计语言/token/组件/模式/页面族/状态语义/动效/响应式/触感/品牌图标：14+ 份 V2.5 治理资产齐备。
- 8 断点×双主题×44 屏视觉基线、console=0、溢出=0、a11y 表单名=0 缺失、外部运行时请求=0。
- 稳定契约：35 个 data-* 钩子、全局 LumUI/LumShell/LumOrb/LumBrand/LumLaunch/LumHaptics、sections 渲染器，供 Codex 直接绑定。
