# CoALA 记忆分层索引（OSAI 研究侧）

> 依据：CoALA（arXiv 2309.02427，E3）+ P0 指令"Agent Memory"（Private/Shared/Episodic/Semantic/Procedural…）。
> 作用：把 OSAI 研究侧已沉淀资产按认知记忆分层登记，**不移动文件**（防破坏引用），提供"分层视图"供检索与复用。
> 关联：IC-006（Improvement Queue）、02-PAPER-TRACKING PT-015。
> 更新：2026-09-04（Round 2）

## 四层记忆定义（CoALA）
| 层 | 定义 | 本侧对应 |
|---|---|---|
| Working | 当前决策周期活跃信息 | research-inbox/（进行中）+ 本会话上下文 |
| Episodic | 带时间戳的过往经历（闭环/轮次） | ZELL-LOOP-*、learning-*、github-benchmarks-*、brand-marketing-knowledge-*（按日序列） |
| Semantic | 稳定、去时间化的世界与自身知识 | contract-updates、CTR 契约、migration、report-convergence、seed-sumeru |
| Procedural | 技能/怎么做（权重内隐 + 代码显式） | ZELL-LOOP-TEMPLATE（方法论）、pattern-*、agent-skills benchmark、P0-AGENT-ORG 研究体系 |

## Episodic（经历/闭环，带日期）
- `learning-feed/ZELL-LOOP-001-*` — P0-B 自动对账闭环（2026-09-04）
- `learning-feed/zell-p0-loop-*`、`learning-20260902.md`
- `learning-feed/github-benchmarks-02/03/04-*` — 2026-09-02/03 前沿扫描
- `learning-feed/INDUSTRY-CASE-STUDY-MULTIAGENT-OS-*` — 多智能体 OS 行业案例
- `learning-feed/brand-marketing-knowledge-01~25-*` — 品牌营销知识序列（2026-09-03）
- `learning-feed/legacy-snapshot-vs-frontier-*`、`report-convergence-gap10-*`

## Semantic（稳定知识/契约/迁移）
- `learning-feed/contract-updates-20260902.md`
- `learning-feed/CTR-EVENT-CLUSTER-P1-01.md` — 事件聚类契约
- `learning-feed/sqlite-alembic-migration-20260903.md`
- `learning-feed/seed-sumeru-taiji-mapping-AQ-20260903.md` — 芥子纳须弥结构原则映射
- `03-RESEARCH/LEARNING-UNITS-REGISTRY.md` — 学习单元登记（语义）
- `00-GOVERNANCE/CANONICAL_REGISTRY.md` — 落库结论（语义）

## Procedural（技能/方法论）
- `learning-feed/ZELL-LOOP-TEMPLATE.md` — 闭环方法论（含 Evaluation 归因分层）
- `03-RESEARCH/P0-AGENT-ORG/` — P0 研究体系（研究地图/案例库/雷达/队列= 过程技能）
- `learning-feed/pattern-data-driven-motion-20260903.md`
- `learning-feed/github-benchmarks-02-agent-skills-20260902.md` — 外部技能标杆

## Working（当前活跃）
- `research-inbox/`（25 个进行中证据/报告）
- `03-RESEARCH/P0-AGENT-ORG/04-IMPROVEMENT-QUEUE.md` — 待办候选（当前决策）
- `baseline/MASTER-ENGINEERING-MATRIX-20260903.md` — 工程矩阵（当前执行）

## 分层读写规则（反哺 IC-001 写路径）
- **写**：新资产落盘前先归层（episodic 带日期 / semantic 去时间化 / procedural 可复现）→ 命中"写路径先校验"
- **读**：检索按"先 working → 再 semantic/procedural → 最后 episodic"（预测性预取思想）
- **过期/纠错**：semantic 层若被新证据推翻，标注 RECONCILED 并链旧条目（不静默删除）
