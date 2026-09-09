# LUMENIS Heritage Intelligence Library
## 序境 · 历史研发与知识资产库

本目录用于保护 LUMENIS 及其关联研发体系在历史仓库、研究分支、实验、案例、平台研究、语言研究、数据设计、产品设计、AI/Agent 研发、工程审计和生产验证中形成的长期知识资产。

## 定位

- 本目录不是 Production Runtime。
- 本目录不覆盖当前 Production Truth。
- 历史资产进入本目录，不代表旧代码、旧 API、旧数据库、旧 UI、旧 Provider 自动恢复到生产。
- 它负责：发现历史资产、解释历史资产、判断当前价值、为当前研发提供可检索的工程记忆，并防止重构/迁移时发生知识丢失。

## 使用原则

每次 Codex / Agent 执行产品任务前，必须先按任务域检索本目录，而不是无差别全文阅读。标准链路：

`Task → Domain Detection → Heritage Retrieval → Current Source Audit → Current Truth Check → Decision → Implement → Test → Evidence → Regression → Release Gate`

优先级始终是：

`Current Production Truth > Current Verified Architecture > Applicable Heritage Asset > Superseded / Reference-only Asset`

历史资产只能影响设计与决策，不能绕过当前源码核验、测试、Evidence 和 Release Gate。

## 一级资产域

1. `01_research_learning/` — 研究与学习资产
2. `02_platform_intelligence/` — 平台研究与平台智能
3. `03_language_content_intelligence/` — 语言、语境与内容表达智能
4. `04_data_metrics_presentation/` — 数据、指标与呈现资产
5. `05_domain_methodologies/` — 业务领域方法论
6. `06_evidence_truth_contracts/` — 证据、事实、模型与契约
7. `07_product_ux_design/` — 产品、信息架构与设计知识
8. `08_ai_agent_intelligence/` — AI 与 Agent 研发智能
9. `09_engineering_governance/` — 工程治理与验证知识
10. `10_decision_memory/` — 产品与研发决策记忆
11. `11_cases_benchmarks/` — 案例与标杆
12. `12_tests_regression_memory/` — 测试与回归记忆
13. `99_archive_reference/` — 归档与历史参考

## 关键保护资产

P0：Korean/K-drama/Fansub/Translation/i18n、Platform Research、Data/Metrics/Tables、Evidence/Truth/Contracts、Domain Methodology、Decision Memory、Regression Memory、Audit/Engineering Governance。

## 资产状态

`DISCOVERED / INDEXED / VERIFIED / DEDUPED / PROMOTED / REFERENCE_ONLY / SUPERSEDED / ARCHIVED / REJECTED_WITH_REASON`

禁止以“旧”“当前未引用”“分支落后”“不在 Runtime”为理由直接删除知识资产。

## 2026-09-09 P0 全量回收输出

- [A. Heritage Recovery Report](HERITAGE_RECOVERY_REPORT.md)
- [B. Asset Coverage Matrix](ASSET_COVERAGE_REPORT.md)
- [C. Missing Asset Report](MISSING_ASSET_REPORT.md)
- [D. Duplicate & Superseded Report](DUPLICATE_SUPERSEDED_REPORT.md)
- [E. Knowledge Gap Report](KNOWLEDGE_GAP_REPORT.md)
- [F. Promotion Candidates](PROMOTION_CANDIDATES.md)
- [G. Korean Collection Report](KOREAN_COLLECTION_REPORT.md)

机器可读证据位于 `_inventory/`。来源索引覆盖率 100% 只表示 5,449 个唯一知识 Blob 均有来源关系，不表示全部已验证、采用、发布或运行。
