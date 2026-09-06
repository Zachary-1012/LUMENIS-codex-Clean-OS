# CASE-2026-0012: DDC Capability Delta 量化增量门禁研究

## 案例来源
- **来源仓库：** Zachary-1012/Development-Command-Console
- **来源文件：** `tools/capability_delta.py`（schema `zachary.learning.capability-delta.v1`）
- **测试文件：** `tests/test_capability_delta.py`（13 个测试方法，静态读取确认）
- **来源 SHA：** 最早引入 `1643dd1`；本轮观察于 DDC HEAD `60fbecc1d5f582080127516ea8b78f63df50d057`；文件 blob `069e416`、测试 blob `ed72236`
- **License：** Internal (Zachary AI Platform)
- **维护状态：** active

## 为什么值得研究
学习系统最容易自欺的一点是：攒了一堆 Evidence，就默认"能力变强了"。DDC 的 capability_delta 正好补上这道门——**在 promotion_candidate 之前，强制要求量化的 before/after 对比、非空改进、副作用显式确认、三仓各自带证据验证**，并且把"AI confidence is never Evidence"写进了输出 policy。这与 Hub"AI 输出不能当 Evidence、禁止自动晋级"的永久原则高度一致，是能力晋级链路上稀缺的"净改进量化层"。

## 原项目解决什么问题
1. **有证据 ≠ 有改进：** 分别要求 before、after 两个状态都带 `evidence_refs` 和非空量化 `metrics`
2. **改进必须显式：** `delta.improvement` 非空才放行，禁止"说不清哪里变好"却晋级
3. **副作用不允许被隐藏：** 每个 side effect 必须 acknowledged / accepted / mitigated / accepted_with_risk
4. **三仓缺一不可：** DDC + Z-Brand + SICI 必须都 verified 且各自带 evidence_ref，并输出 `missing_repositories`
5. **永不静默晋级：** 7 个 gate 任一不过即 `hold`；只产出 decision artifact，**绝不修改生产仓库**

### 7 个 Gate（逐行读码）
| Gate | 通过条件 |
|---|---|
| before/after_has_evidence | 两状态各带非空 evidence_refs（每项为非空字符串） |
| before/after_has_metrics | 两状态各带非空 metrics dict |
| delta_has_improvement | improvement 为非空文本 |
| side_effects_acknowledged | 全部副作用已确认 |
| three_way_verified | 三仓均 verified 且带 evidence |

## 我们可以吸收什么
| 模式 | Hub 适配方式 |
|---|---|
| before/after 双状态量化 | 未来 Hub reusable 晋级前，要求附一份 capability-delta decision artifact |
| 缺一门禁即 hold | 与 Hub shadow_lifecycle / registry 的 evidence-gated 设计同源，强化"不静默晋级" |
| missing_repositories 显式暴露 | 与 `data/repository_matrix.json` 结合，明确指出哪一仓尚未验证 |
| policy 自描述 | decision artifact 内嵌判定原则，便于审计追溯 |
| sanitize 凭证过滤 | 参考其把 `authorization` 也纳入黑名单（Hub 当前黑名单可在后续评估是否补齐） |

## 哪些不能照搬
1. **不得复制代码进 Hub src/。** DDC 是 capability_delta 的唯一实现 Owner，Hub 复制会形成双实现，违反"不复制核心代码"。
2. **不硬编码三仓名。** DDC `REQUIRED_REPOS` 是 DDC 视角；Hub 引用时必须经 `data/repository_matrix.json` 对齐。
3. **不设一刀切指标阈值。** metrics 的量化口径由各产品按领域自定义，Hub 不规定具体数值。
4. **不把它当成第二套晋级器。** Hub `capability_registry.promote()` 已存在，delta 是其**上游补充门**（回答"好了多少"），不是替代。

## 如何适配三方平台
- **Z-Brand：** 未来提供业务/生产侧 before/after 指标与 evidence（如准确率、人工干预率），作为三仓验证之一
- **SICI：** 提供移动端/真实用户工作流侧指标与设备约束下的 evidence
- **DDC：** 作为 capability_delta 实现 Owner 持续维护；Hub 通过 adapter 复用其评估或消费其 artifact
- **Hub：** 只登记本案例、沉淀门禁标准；代码化候选标记为 candidate for future adapter（本轮 deferred）

## 是否值得写代码
**纳入案例库：值得（本文件即结论）。**
**在 Hub 内再实现一份评估器：当前不值得。**
- ❌ Hub `capability_registry.py` 已有晋级门禁，再写一份 delta 评估器会重复
- ❌ 复制 DDC 实现违反"不复制核心代码"
- ✅ 登记为 CASE-2026-0012，作为未来 adapter 的设计输入
- ✅ 等真正出现"需要量化净改进才能晋级"的 Hub 能力时，再以 adapter 方式复用 DDC 实现（R-2026-0003 草案）

## 实验结果
- **静态实验（已做）：** 完整读取实现与测试，确认 13 个测试覆盖全过路径、5 类 hold 路径、副作用确认、sanitize、文件加载、policy 文案，以及关键的 `test_hold_does_not_become_promotion_candidate`（10 次随机缺门断言永不静默晋级）
- **DDC 测试本地运行：NOT VERIFIED**（本地无 DDC 工作副本，未执行其测试套件；"13 tests"为静态方法计数 + commit 1643dd1 记录，不冒称运行通过）
- **Hub 侧回归（已做）：** 本轮研究未改 Hub 运行时代码；同期 enum 对齐后 Hub 全套 73 pass / 0 fail（Python 3.12 / Windows / 退出码 0）
- **Evidence：** DDC 文件 blob `069e416`、测试 blob `ed72236`、DDC HEAD `60fbecc`；研究全文见 `research/R-2026-0002-capability-delta-research.md`

## 适配判断
- **研究价值：** high
- **适配价值：** high（作为晋级门禁标准 / 未来 adapter）
- **风险：** low（只读、产出 artifact、不改生产、自带凭证过滤）
- **分类：** internal reference case（互补能力，非重复、非 Hub 实现）
- **生命周期：** research → case-indexed；代码化候选 = candidate for future adapter（deferred，不自动 promotion）
- **下一步：** R-2026-0003 在 DDC 工作副本运行级验证其 13 tests，并设计 Hub 侧 adapter 接口草案（仍不复制实现）
