# F. Promotion Candidates

本轮 Promotion 数：`0`。以下均只是候选，尚未进入 Production。

| Priority | Candidate | Owner | Required Gate |
|---|---|---|---|
| P0 | Contract-first Tables | Shared / Data | 当前 Metric、API、DB、View Model 与真实页面贯通测试 |
| P0 | Evidence-driven Engineering ADR Pattern | SYSTEM / Engineering | 当前工具执行、Evidence Store、审计与回归验证 |
| P0 | Collector explicit-state / no-silent-zero pattern | SYSTEM / Collector | 真实采集、Auth、失败状态与恢复 E2E |
| P0 | Regression Memory structured registry | SYSTEM / Test | 根因和防回归测试逐项绑定当前源码 |
| P1 | Korean Content Intelligence methods | Shared Content | 许可、人工语境评测、i18n 渲染与内容安全 |
| P1 | KOS/KOL/KOC methodology | BMP primary / CTH consumer | 主体与内容属性分离、指标契约、权限、真实数据 |
| P1 | Shared Intelligence versioned artifact contract | Cross-repo Contract | 无共享 DB、异步可选、签名/版本/回滚验证 |
| P1 | Podcast research-to-production method | Shared / BMP | Entity、Evidence、指标、授权与产品边界验证 |
| P2 | Historical design interaction patterns | Product UX | 按 LUMENIS 新设计语言重构，不复制旧页面 |

标准流程：`Historical Asset → Current Equivalent Audit → Requirement → Architecture Fit → Evidence → Candidate → Implementation → Test → Regression → Production Acceptance`。
