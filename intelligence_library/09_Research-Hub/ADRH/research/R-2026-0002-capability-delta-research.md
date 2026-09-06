# Research Record — R-2026-0002（研究部分）

> 本记录同时承载 R-2026-0002 的两条工作线：
> **(A) 工程线** Review enum 对齐（见提交说明与 tests/test_research_record.py）
> **(B) 研究线** DDC `capability_delta.py` 是否纳入 Hub Case Library（本文件）
>
> 流程遵循 `docs/protocols/CHATGPT-INTERVENTION-PROTOCOL.md` 九阶段；R-2026-0001 已经 ChatGPT APPROVED。

| 字段 | 内容 |
|---|---|
| Research ID | R-2026-0002 |
| AI Agent | 豆包（Engineering Execution / Research） |
| created_at | 2026-09-01（Asia/Shanghai） |
| source | ChatGPT R-2026-0001 Review 指令第 4–6 步 |
| repository | Zachary-1012/Development-Command-Console（研究对象）→ Hub（沉淀地） |
| observed_sha | DDC HEAD `60fbecc1d5f582080127516ea8b78f63df50d057`；文件 blob `069e416`；测试 blob `ed72236` |
| status | research → case-indexed（研究结论：纳入案例库，**不在 Hub 复制实现**） |

## 1. 案例来源（Provenance）

- 文件：`Development-Command-Console/tools/capability_delta.py`（schema `zachary.learning.capability-delta.v1`）
- 测试：`Development-Command-Console/tests/test_capability_delta.py`（13 个测试方法，静态读取确认）
- 最早引入：DDC commit `1643dd1`（7 gates / 13 tests）；本轮观察于 DDC HEAD `60fbecc`
- License：Internal（Zachary AI Platform），三仓内部资产

## 2. 它解决什么问题（Problem）

填补 **"我们已经有 Evidence"** 与 **"这次学习真的让系统变强了"** 之间的缺口：
一个能力即使攒了一堆 Evidence，也不代表它产生了**可量化的净改进**。capability_delta 在 promotion_candidate 之前加一道量化增量门禁。

## 3. 设计（Design，逐行读码结论）

`evaluate_delta(delta)` 计算 7 个 gate，**全部为 True 才输出 `promotion_candidate`，任一不过即 `hold`**：

| Gate | 通过条件 |
|---|---|
| before_has_evidence / after_has_evidence | before、after 各带非空 `evidence_refs`（且每项为非空字符串） |
| before_has_metrics / after_has_metrics | before、after 各带非空量化 `metrics` dict |
| delta_has_improvement | `delta.improvement` 为非空文本（必须显式描述改进） |
| side_effects_acknowledged | 每个副作用必须 acknowledged，或 status ∈ accepted/mitigated/accepted_with_risk |
| three_way_verified | DDC + Z-Brand + SICI 三仓均 verified **且**各自带 evidence_ref |

关键工程性质：
- **只产出 decision artifact（JSON），永不修改任何生产仓库**；
- 内置 `sanitize()`，凭证黑名单比 Hub 多一个 `authorization`；
- 输出 `missing_repositories`，显式暴露"哪一仓没验证"；
- policy 文案固定写明 **"AI confidence is not Evidence. Missing any gate forces hold."**

## 4. 与 Hub 现有能力的关系（重复性检查 — 不重复造轮子）

| 维度 | Hub `src/shared/capability_registry.py` `promote()` | DDC `capability_delta.py` |
|---|---|---|
| 核心问题 | 晋级**材料是否齐全/合规** | 能力是否产生**可量化净改进** |
| 检查内容 | origin_research_id / evidence_refs / contract / tests / 三仓 validation pass / rollback_plan | before/after 量化 metrics + 改进量 + 副作用确认 + 三仓 evidence |
| 判定 | 材料齐 → reusable | 7 gate 全过 → promotion_candidate，否则 hold |

**结论：互补，不重复。** registry 回答"手续全不全"，delta 回答"到底好了多少、有没有副作用、三仓是否都验证"。二者是晋级链路上前后相邻的两道门，不是同一份能力的两个实现。

## 5. 可复用性 / 适配成本 / 风险

- **可复用性：高。** "量化 before/after + 三仓 evidence + 副作用显式确认 + 缺一门禁即 hold" 的模型可直接作为 Hub reusable 晋级的引用标准。
- **适配成本：低-中。** Hub 未来可在能力进入 reusable 前**要求附一份 capability-delta decision artifact**；但评估实现仍由 DDC 作为 Owner 提供，Hub 通过 adapter/索引消费，不在 Hub 重写。
- **风险：低。** 只读、无外部依赖、不改生产、自带凭证过滤。
- **不能照搬的点：**
  1. DDC `REQUIRED_REPOS` 是 DDC 视角的三仓命名，Hub 引用时须经 `data/repository_matrix.json` 对齐，不硬编码；
  2. `metrics` 的量化口径必须由各产品按领域自定义，Hub 不设一刀切阈值；
  3. **不得把 DDC 代码复制进 Hub src/**（违反"不复制核心代码"，DDC 是该实现唯一 Owner）。

## 6. 是否值得写代码（本轮决策）

- **纳入 Case Library：是** → 登记 `CASE-2026-0012`（research_value=high / adaptation_value=high / risk=low）。
- **在 Hub 内再实现一份 delta 评估器：否（本轮 NOT PROMOTED as code）。** 理由：Hub capability_registry 已有晋级门禁，再实现一份评估器会形成双实现；正确路径是未来以 adapter 复用 DDC 实现或消费其 artifact。生命周期标记：**candidate for future adapter**，不进 Capability Registry 的 reusable。

## 7. 实验 / 验证结果（诚实标注边界）

- **静态验证（已做）：** 完整读取 `capability_delta.py` 与 `test_capability_delta.py`；确认 13 个测试方法覆盖全过路径、5 类 hold 路径、副作用确认、sanitize、文件加载、policy 文案，以及关键的 `test_hold_does_not_become_promotion_candidate`（10 次随机缺门，断言永不静默晋级）。
- **DDC 测试本地实际运行：NOT VERIFIED。** 本轮本地工作副本不含 DDC 仓库，未在本地执行 DDC 测试套件；"13 tests" 来自静态读取测试方法计数与 DDC commit `1643dd1` 记录，**不写成"我已运行通过"**。如需运行级证据，下一轮在 DDC 工作副本执行 `python -m unittest tests.test_capability_delta`。
- **Hub 侧真实运行（已做）：** 本轮 enum 对齐后 Hub 全套 **73 pass / 0 fail**（Python 3.12，Windows，退出码 0），与本研究无代码耦合，仅证明 Hub 未被研究工作破坏。

## 8. 三仓影响

- **Z-Brand：** 无改动。delta 模型未来要求 Z-Brand 提供业务侧 before/after metrics 与 evidence（引用关系，非依赖）。
- **SICI：** 无改动。未来提供移动端/真实工作流侧验证 evidence。
- **DDC：** 无改动。作为 capability_delta 实现 Owner 被研究、被索引，Hub 不修改其任何文件。

## 9. 结论（Classification / Lifecycle）

- Classification：internal reference case（互补能力，非重复、非 Hub 实现）
- Lifecycle：research → **case-indexed**；代码化候选 = candidate for future adapter（deferred，不自动 promotion）
- 下一步建议：R-2026-0003 在 DDC 工作副本运行级验证 capability_delta 13 tests，并设计 Hub 侧"晋级前要求 delta artifact"的 adapter 接口草案（仍不复制实现）。
