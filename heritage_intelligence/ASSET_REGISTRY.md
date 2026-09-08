# Heritage Asset Registry

Asset ID format: `HIA-YYYYMMDD-NNN`

| Asset ID | Asset Name | 中文名 | Category | Primary Source | Status | Current Relevance | Target / Notes |
|---|---|---|---|---|---|---|---|
| HIA-20260909-001 | Korean Content Intelligence Collection | 韩语内容语境与本地化研究集 | Language / Content | Z-Brand-Core research branches | DISCOVERED | P0 | 汇总 kdrama/fansub/translation/i18n 全分支，不能只看 final |
| HIA-20260909-002 | Historical Learning Registry | 历史学习资产总索引 | Research / Learning | Z-Brand-Core `docs/learning/LEARNING-REGISTRY.md` | VERIFIED | P0 | 作为历史研究总入口，需逐项映射当前状态 |
| HIA-20260909-003 | Platform Intelligence Collection | 平台研究与平台智能集 | Platform Intelligence | Z-Brand-Core docs/research/intelligence_library | DISCOVERED | P0 | 小红书/抖音/微博/B站/快手/知乎/Podcast/跨平台 |
| HIA-20260909-004 | KOS DFS Data Presentation Baseline | KOS × DFS 数据呈现基线 | Data / Metrics / Tables | Z-Brand-Core DFS/KOS audit + contracts | VERIFIED | P0 | 成本/健康画像/KOC分层；Contract-first |
| HIA-20260909-005 | Contract-first Table Pattern | 契约优先业务表格模式 | Decision / Data Pattern | Research Hub learning-feed | VERIFIED | P0 | Research → Contract → Data → UI，禁止前端猜字段 |
| HIA-20260909-006 | KOS Domain Intelligence | KOS 业务智能方法集 | Domain Methodology | Z-Brand-Core KOS modules/docs/contracts | DISCOVERED | P0 | 意向分层、身份识别、Benchmark、归因、分层、执行 Gate |
| HIA-20260909-007 | Podcast Intelligence & Production Methodology | Podcast 智能与生产方法集 | Domain Methodology | Z-Brand-Core podcast + research + Research Hub | DISCOVERED | P0 | Research / Entity Model / Intelligence / 8-Step SOP / UI Data |
| HIA-20260909-008 | Evidence & Truth Pattern Collection | Evidence 与事实链模式集 | Evidence / Truth | Z-Brand-Core + GGI + Command | DISCOVERED | P0 | Evidence/Event/Case/Metric/Truth/Contracts |
| HIA-20260909-009 | AI & Agent Intelligence Collection | AI 与 Agent 研发智能集 | AI / Agent | Zachary-OS-AI | DISCOVERED | P0/P1 | Architecture/Agent/Memory/Learning/Evaluation/Research Adoption |
| HIA-20260909-010 | Engineering Audit & Verification Memory | 工程审计与验证记忆集 | Engineering Governance | lumenis-command | VERIFIED | P0 | Audit/ADR/P0 Evidence/Verification/Deployment/Boundary |
| HIA-20260909-011 | Product UX Design Research Collection | 产品与设计研究集 | Product / UX | Z-Brand-Core learning/ui + governance | VERIFIED | P1 | IA/响应式/动效/数据交互/外部标杆，保留原则不强制恢复旧视觉 |
| HIA-20260909-012 | GGI Research Pipeline Pattern | GGI Research Pipeline 方法 | Research / Contract | global-growth-intelligence | DISCOVERED | P1 | 只提炼 Pattern/Contract，不复制独立产品 Runtime |
| HIA-20260909-013 | Regression Memory Collection | 历史回归与故障记忆集 | Test / Regression | old repo tests/audits/evidence | DISCOVERED | P0 | JS fatal syntax、字段契约、权限污染、浏览器渲染、Truth Chain 等 |
| HIA-20260909-014 | Decision Memory Collection | 历史产品与研发决策记忆 | Decision Memory | audits/dev logs/contracts/user corrections | DISCOVERED | P0 | 记录原方向→问题→Evidence→纠偏→最终规则→Do Not Regress |

## Required fields for promoted entries

When an asset is promoted from collection-level to file-level inventory, record:

- Asset ID
- Asset Name / Chinese Name
- Category / Domain
- Source Repository / Branch / Path / SHA
- Original Date / Original Purpose
- Summary
- Evidence Level / Production Verified
- Current Relevance / Current Equivalent / Current Owner
- Dependencies
- Decision / Target Location
- Status / Supersedes / Superseded By
- Do Not Lose / Do Not Regress
- Notes

## Priority

P0 assets must be retrieved before implementing a related task. P1 assets are retrieved when they materially affect architecture/design/quality. P2 assets are archival/reference and should not dominate current decisions.