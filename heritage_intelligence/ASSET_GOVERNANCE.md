# Heritage Asset Governance

## 1. 核心红线

任何历史资产在完成 `Source Trace + Semantic Compare + Current Equivalent Verification` 之前，禁止因为文件旧、分支落后、路径异常、当前 Runtime 未引用、当前 UI 已重做或看起来重复而直接删除或判定无用。

## 2. 资产决策

允许：
- KEEP
- MERGE
- PROMOTE
- REFERENCE_ONLY
- SUPERSEDED
- ARCHIVE
- REJECTED_WITH_REASON

禁止无依据 DELETE。

## 3. 生产边界

Heritage Knowledge ≠ Production Runtime。

任何历史资产重新进入当前产品，必须走：
`Research → Evidence → Decision → Current Architecture Fit → Implementation → Test → Verification → Release Gate`

## 4. 第三方研究与许可

仅迁移自有研究结论、架构思想、方法、数据结构、验证方法和合法可复用内容；不得将第三方受限许可源码包装为自研。依赖引入必须继续经过 License / SBOM / Security 审计。

## 5. Codex 检索规则

执行任务前按域检索：
- UI/UX → `07_product_ux_design` + `04_data_metrics_presentation` + `10_decision_memory`
- 数据/表格/指标 → `04_data_metrics_presentation` + `06_evidence_truth_contracts` + `10_decision_memory` + `12_tests_regression_memory`
- 平台 → `02_platform_intelligence` + 对应 Domain + 合规/Contract
- 韩语/内容/i18n → `03_language_content_intelligence`
- KOS/Podcast/舆情/Campaign/Research/Operations → `05_domain_methodologies` + 相关 Data/Contract
- AI/Agent → `08_ai_agent_intelligence` + `09_engineering_governance`
- Runtime/Security/Release → `09_engineering_governance` + `12_tests_regression_memory`

检索后必须回到当前源码和当前 Production Truth 做核验，历史结论不得直接覆盖当前事实。