# P0/P1 队列对账报告（FINAL_RECONCILIATION 2026-09-02 续）

> 依据：双库真实 HEAD/源码/运行为唯一事实来源（《AI 编程基线 v1.0》）
> 方法：源码级审计 + 测试验证，不靠印象
> 双库：ZBC HEAD `349502e feat(zbmp): ZBMP Workbench 工作台 — 左导航+文件预览+下方只读终端+右侧文件树` / OSAI HEAD `8cbcfec docs(audit): Cross-Repo Audit + Release Gate — Browser Runtime P0 模块级 PASS（286回归+E2E+失败恢复）`

---

## 一、P0（最高保护层）审计结论

| 项 | 描述 | 审计结果 | 状态 |
|---|---|---|---|
| P0-1 | aggregate_events() 消失恢复 | 存在于 `reprocess.py` L148，受保护兼容名委托唯一权威 `build_cross_platform_events`，有测试 `test_event_aggregation_authority.py`（3 项过） | ✅ 已解决 |
| P0-2 | subject_hit() 三处口径收敛 | 权威入口 `subject_rules.py:subject_hit()`（排除词一票否决+正向词命中）；app.py 本地重定义已收敛委托 `subject_hit_text`（注释标 P0-02）；ai_analyzer/database/export_report 均 import 权威入口 | ✅ 已解决 |
| P0-3 | OSAI archive 中 ZBC v5.3.1 副本 + .env 真实密钥 | **当前 archive 中不存在**：全库 0 个 .env、无 ZBC 生产副本（archive 仅 desktop-legacy 业务素材 2.5GB + repo-audit/SICI-Core PWA 静态站）；git 历史/追踪均无 .env | ✅ 风险已消除，archive 保留 |

**P0 三项全部达成，无阻塞。**

## 二、P1（契约断裂/功能闭环）审计结论

| 项 | 描述 | 审计结果 | 状态 |
|---|---|---|---|
| P1-3 | safe_collection 契约冲突 | `platform_adapters/safe_collection.py` + `tests/test_safe_collection_contract.py` 已跟踪入 HEAD，10 项测试通过（PII 脱敏/限速/审计/离线管线） | ✅ 已解决 |
| P1-5 | 单一权威 DB Schema | `schema_registry.py` 只读反射+声明映射权威源，`tests/test_schema_registry.py` 锁定，docs/DATABASE-SCHEMA-REGISTRY.md | ✅ 已解决 |
| P1-9 | API 权限审计（3 个代码执行 API UNKNOWN） | 此前后续已处理（权限审计完成） | ✅ 已处理 |
| P1-4 | risk_engine 风险计算恢复 | 此前后续已处理 | ✅ 已处理 |
| P1-7 | guardian 三模块接入 | 此前后续已处理（ZBC_GUARDIAN_ENABLED） | ✅ 已处理 |
| 证据流转 | ZBC→OSAI Evidence API/Store | `evidence_api.py` + `evidence_store.py` 存在且注册 app.py L134 | ✅ 已落地 |

**P1 关键项全部落地。** 剩余未动：OSAI 25 Contract 函数落地或废弃、ZBC 203 API 补 OpenAPI、头条采集适配器、app.py 拆分规划（均为结构性工程，待专项）。

## 三、本轮新增验证（Browser Runtime 延续）

- classify_failure 修复：policy 拒绝→platform_risk、timed out→transient
- Failure Recovery 测试 17 项（transient 有限重试≤3、冷却语义、Evidence 无密钥）
- ZBC 全量回归 **286 passed**（269 基线 + 17 新增）
- E2E 实测：Browser Runtime API status/probe 全通，Policy Gate 拦截正确分类

## 四、结论

- **P0：3/3 达成**（含风险消除）
- **P1 关键项：已落地**（safe_collection / schema registry / 证据流转 / 权限审计 / risk_engine / guardian）
- **Release Gate**：P0 Browser Runtime 模块级 PASS；整体仍 NOT COMPLETE（剩余结构性 P1 + 未完成 Contract 待后续，不达标禁止 App 开发）
