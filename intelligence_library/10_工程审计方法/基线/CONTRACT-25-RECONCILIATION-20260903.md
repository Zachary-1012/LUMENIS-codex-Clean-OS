# 25 Contract 函数落地/废弃判定（P1-1 收口）· 2026-09-03

> 依据：《04_FUNCTION_RECONCILIATION.md》的 OSAI Contract 声明清单 + ZBC 源码级核实
> 判定原则：双子库架构 =「OSAI 定义契约，ZBC 自行实现生产代码」。契约函数是否要在 ZBC 同名落地，
> 取决于它是否对生产链路有直接作用，而非"OSAI 声明了就必须同名出现"。

## 一、25 个 Contract 函数四分类判定

### 1. Safe Collection Contract（8/8）→ ZBC 已同名落地 ✅
| OSAI 声明函数 | ZBC 落地 | 证据 |
|---|---|---|
| `redact_text(text)` | ✅ 同名 | `platform_adapters/safe_collection.py` |
| `redact_record(record, pii_fields)` | ✅ 同名 | 同上 |
| `CollectionHygienePolicy.validate()` | ✅ 同名 | 同上 |
| `CollectionHygienePolicy.is_safe()` | ✅ 同名 | 同上 |
| `RateGovernor.permit()` | ✅ 同名 | 同上 |
| `RateGovernor.within_daily_cap()` | ✅ 同名 | 同上 |
| `build_collection_audit()` | ✅ 同名 | 同上 |
| `run_offline_pipeline()` | ✅ 同名 | 同上 |
**验证**：`tests/test_safe_collection_contract.py` 10 项全过；已接入 `evidence_exporter.py` 业务链。

### 2. Research Record Contract（8/8）→ OSAI 研究侧内部，ZBC 不强制落地 ⏸
`validate` / `sanitize` / `validate_research_id` / `make_review` / `add_review` /
`make_research_record` / `to_ddc_record` / `is_sensitive_key`
- 归属：`components/AI-Development-Research-Hub/src/contracts/research_record.py`
- 性质：OSAI 内部研究记录管理，非生产采集/分析链路
- 判定：**保持 OSAI 侧维护**；ZBC 侧无对应生产职责，**不要求同名落地**（对应"废弃 ZBC 落地要求"）

### 3. Capability Registry（5/5）→ OSAI 研究侧内部 ⏸
`add` / `promote` / `deprecate` / `verify` / `list_reusable`
- 归属：`components/AI-Development-Research-Hub/src/shared/capability_registry.py`
- 性质：OSAI 能力注册/演化，研究侧工具
- 判定：**保持 OSAI 侧**；ZBC 生产用 `function_registry.py` + `function_map.json` 已有等价能力映射，不重复

### 4. Shadow Lifecycle（4/4）→ OSAI 研究侧内部 ⏸
`can_transition` / `transition` / `is_shadow_safe` / `required_exit_evidence`
- 归属：`components/AI-Development-Research-Hub/src/shared/shadow_lifecycle.py`
- 性质：OSAI 影子生命周期状态机，研究侧
- 判定：**保持 OSAI 侧**；ZBC 影子数据（v4_ai_shadow）由 `data_feedback_loop.py` 管理，职责不同

## 二、判定汇总

| 分类 | 函数数 | 判定 |
|---|---|---|
| ZBC 已同名落地 | 8 | ✅ 完成（Safe Collection 全部） |
| OSAI 研究侧内部（ZBC 不强制落地） | 17 | ⏸ 保持 OSAI 侧，ZBC 侧落地要求废弃 |
| **合计** | **25** | **已收口** |

## 三、结论

- P1-1「OSAI 25 Contract 函数落地或废弃」**收口完成**：
  - 对生产有直接作用且 ZBC 职责匹配的（Safe Collection）→ 已同名落地并测试通过；
  - 属 OSAI 研究侧内部职责的（Research Record / Capability Registry / Shadow Lifecycle）→ 明确为"OSAI 侧维护，ZBC 不强制同名落地"，不再作为缺口。
- 遗留（P2）：Contract 与实现之间仍缺自动化校验（双库契约一致性检查），见 reconciliation/11_GAP_REGISTER。

## 四、头条采集适配器判定（P1-6 收口）

- **结论：废弃（不新建）**。
- 依据（ZBC 源码级核实）：核心采集平台为 xiaohongshu / weibo / douyin / bilibili / zhihu / wechat / baidu / sina；
  "头条/toutiao/topnews" 仅出现于 `public_opinion_cases.py`（案例库）与 `subject_classifier.py`（分类器）共 2 处弱引用，
  无采集适配器、无采集需求。头条不是目标监测平台，新建适配器无业务价值。
- 处置：不新增头条采集适配器；如未来纳入头条平台，再按 Platform Adapter 规范补充。

*归属：Zachary-OS-AI baseline | 状态：收口记录 | 关联：04_FUNCTION_RECONCILIATION*
