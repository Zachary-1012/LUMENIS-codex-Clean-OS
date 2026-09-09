# Heritage Asset Registry

Asset ID format: `HIA-YYYYMMDD-NNN`

| Asset ID | Asset Name | 中文名 | Category | Primary Source | Status | Current Relevance | Target / Notes |
|---|---|---|---|---|---|---|---|
| HIA-20260909-001 | Korean Content Intelligence Collection | 韩语内容语境与本地化研究集 | Language / Content | Z-Brand-Core research branches | INDEXED | P0 | 40 分支/3 尖端/16 唯一 Blob；重点资产部分核验，详见 Korean Report |
| HIA-20260909-002 | Historical Learning Registry | 历史学习资产总索引 | Research / Learning | Z-Brand-Core `docs/learning/LEARNING-REGISTRY.md` | VERIFIED | P0 | 作为历史研究总入口，需逐项映射当前状态 |
| HIA-20260909-003 | Platform Intelligence Collection | 平台研究与平台智能集 | Platform Intelligence | Z-Brand-Core docs/research/intelligence_library | INDEXED | P0 | 536 唯一 Blob；小红书子域 112；时效与合规待逐项验证 |
| HIA-20260909-004 | KOS DFS Data Presentation Baseline | KOS × DFS 数据呈现基线 | Data / Metrics / Tables | Z-Brand-Core DFS/KOS audit + contracts | VERIFIED | P0 | 成本/健康画像/KOC分层；Contract-first |
| HIA-20260909-005 | Contract-first Table Pattern | 契约优先业务表格模式 | Decision / Data Pattern | Research Hub learning-feed | VERIFIED | P0 | Research → Contract → Data → UI，禁止前端猜字段 |
| HIA-20260909-006 | KOS Domain Intelligence | KOS 业务智能方法集 | Domain Methodology | Z-Brand-Core KOS modules/docs/contracts | INDEXED | P0 | 137 唯一 Blob；意向、身份、Benchmark、归因、分层、执行 Gate |
| HIA-20260909-007 | Podcast Intelligence & Production Methodology | Podcast 智能与生产方法集 | Domain Methodology | Z-Brand-Core podcast + research + Research Hub | INDEXED | P0 | 61 唯一 Blob；Research / Entity / Intelligence / SOP / UI Data |
| HIA-20260909-008 | Evidence & Truth Pattern Collection | Evidence 与事实链模式集 | Evidence / Truth | Z-Brand-Core + GGI + Command | INDEXED | P0 | 567 唯一 Blob；Current Contract 与 Runtime Evidence 待绑定 |
| HIA-20260909-009 | AI & Agent Intelligence Collection | AI 与 Agent 研发智能集 | AI / Agent | Zachary-OS-AI | INDEXED | P0/P1 | 909 唯一 Blob；不恢复历史 Runtime |
| HIA-20260909-010 | Engineering Audit & Verification Memory | 工程审计与验证记忆集 | Engineering Governance | lumenis-command | VERIFIED | P0 | Audit/ADR/P0 Evidence/Verification/Deployment/Boundary |
| HIA-20260909-011 | Product UX Design Research Collection | 产品与设计研究集 | Product / UX | Z-Brand-Core learning/ui + governance | VERIFIED | P1 | IA/响应式/动效/数据交互/外部标杆，保留原则不强制恢复旧视觉 |
| HIA-20260909-012 | GGI Research Pipeline Pattern | GGI Research Pipeline 方法 | Research / Contract | global-growth-intelligence | REFERENCE_ONLY | P1 | 只提炼 Pattern/Contract，不复制独立产品 Runtime |
| HIA-20260909-013 | Regression Memory Collection | 历史回归与故障记忆集 | Test / Regression | old repo tests/audits/evidence | INDEXED | P0 | 683 唯一 Blob；待结构化 Failure→Invariant |
| HIA-20260909-014 | Decision Memory Collection | 历史产品与研发决策记忆 | Decision Memory | audits/dev logs/contracts/user corrections | INDEXED | P0 | 19 唯一 Blob；保留纠偏与 Do Not Regress |
| HIA-20260909-015 | K-drama Dialogue Craft | 韩剧对白表达机制 | Language / Content | Z-Brand-Core `docs/content-learning/KDRAMA_DIALOGUE_RESEARCH_2023_2026.md` | VERIFIED | P1 | Blob `9403f662...`；保留方法，不复制作品表达 |
| HIA-20260909-016 | Fansub Localization Method | 字幕与中文本地化方法 | Language / Content | Z-Brand-Core research fork + current | VERIFIED | P1 | 两 Blob 近似但有独有范围差异；MERGE KNOWLEDGE |
| HIA-20260909-017 | Korean NLP Landscape | 韩语 NLP 技术图谱 | AI / Language | historical research | REFERENCE_ONLY | P2 | 一手来源、性能与许可未核验，不驱动当前选型 |
| HIA-20260909-018 | Command Sidecar ADR Set | 序枢工程 ADR 集 | Engineering | lumenis-command ADR | VERIFIED | P0 | Independence/Evidence 方法保留；旧仓库白名单和旧 Provider 方向已被替代 |
| HIA-20260909-019 | Shared Intelligence Contract Pattern | 共享智能版本化产物契约 | Contract | Zachary-OS-AI + GGI | VERIFIED | P1 | 异步、可选、无共享 DB、无直接 Production Truth 写入 |
| HIA-20260909-020 | Negative Knowledge Collection | 历史失败与被否决方向 | Decision / Regression | five-repo audit | INDEXED | P0 | 旧产品命名、旧隐藏产品线、旧 Provider 决策等保留原因 |

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
