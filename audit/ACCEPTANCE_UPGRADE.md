# ZBC 验收机制增量升级 · 完整审计与交付报告 V2.0

> 日期：2026-09-07
> 分支：lumenis-dual-domain-v3
> 原则：先审计、再修改；先兼容、再重构；先旁路、再切换；先验证、再交付。
> 硬约束：×/✓、PARTIAL/VERIFIED、P0/P1、Git Commit、CI/Test 全部保留不重写；不删除历史状态；不改变已有 P0/P1 数据。

---

## 一、源码级审计结论

### 1.1 审计范围

| 检查项 | 位置 | 审计结果 |
|---|---|---|
| acceptance_gate.py | 根目录 | **已存在**，包含完整状态枚举+判定器（前序 shard 实现） |
| 验收矩阵 / 状态计算 | acceptance_gate.py | CIStatus / FunctionalStatus / Dimension / PartialReason 四套枚举 + judge() / judge_batch() |
| CI 状态 | acceptance_gate.CIStatus | PASS / FAILED / UNKNOWN 三态 |
| 功能核验 | acceptance_gate.FunctionalStatus | PLANNED / IMPLEMENTED / TESTED / VERIFIED / RELEASED / OPERATING / PARTIAL 七态 |
| 任务记录 UI | templates/system/evaluation.html | 已升级为三维卡片（CI STATUS / FUNCTION STATUS / EVIDENCE COVERAGE） |
| Evidence 关联位置 | evidence_chain.py + evidence_store.py + evidence_api.py | 完整证据链系统（zbc_evidence / zbc_canonical_data / zbc_lifecycle_tracking 独立表） |
| evidence_chain.py 能力 | EvidenceStore / CanonicalDataStore / LifecycleTracker / EvidenceChain | 原始证据不可变、AI/人工分离、hash 去重、13 阶段生命周期追踪 |
| 现有验收测试 | tests/test_acceptance_gate.py | 19 用例，覆盖状态分层、AI/Browser 特殊门控、批量判定 |
| API 集成 | app.py L3138-L3170 | GET /api/system/acceptance/dimensions + POST /api/system/acceptance/judge |
| permission_gate.py | 根目录 | 权限体系（验收 API 已加入只读豁免） |
| runtime_guardian.py | 根目录 | 运行时守护 |
| audit/ 目录 | audit/ | 已有 ACCEPTANCE_GATE_INCREMENT_V1.0.md 等审计记录 |

### 1.2 现有状态体系（必须保留）

| 状态体系 | 来源 | 保留策略 |
|---|---|---|
| × / ✓ | Git/CI 传统标记 | **全部保留**，映射为 CIStatus.FAILED / CIStatus.PASS |
| PARTIAL / VERIFIED | 现有验收关键字 | **全部保留**，作为 FunctionalStatus 的成员 |
| P0 / P1 任务 | 任务优先级体系 | **全部保留**，本次不触碰任何 P0/P1 数据 |
| Git Commit SHA | 版本血缘 | **全部保留**，作为 AcceptanceInput.commit_sha |
| CI / Test 结果 | 自动化检查 | **全部保留**，作为 ci_passed / test_passed 维度 |

### 1.3 需增量扩展点（本次完成）

| 扩展点 | 状态 | 实现方式 |
|---|---|---|
| 证据链构建器（Task→Commit→...→Final Status） | **本次新增** | acceptance_evidence_chain.py |
| AI/Browser 特殊验收链路（11节点） | **本次新增** | acceptance_evidence_chain.py AI_CHAIN_ORDER |
| 证据链可追溯 explain() | **本次新增** | AcceptanceEvidenceChain.explain() |
| 证据链→判定器自动映射 | **本次新增** | to_acceptance_input() + build_and_judge() |
| 可选 Evidence 持久化（复用 evidence_chain） | **本次新增** | build_and_judge(persist_evidence=True) |
| 集成测试（端到端） | **本次新增** | tests/test_acceptance_upgrade.py（33用例） |
| 审计文档（用户指定文件名） | **本次新增** | audit/ACCEPTANCE_UPGRADE.md（本文档） |

### 1.4 不重复建设声明

用户指令中提到"新增 acceptance_status.py（状态枚举+判定器）"。经审计，`acceptance_gate.py` 已完整承担此角色（CIStatus + FunctionalStatus + Dimension + PartialReason + judge() + judge_batch()）。依据 AGENTS.md "一套 Core，两个产品，不复制两套长期维护代码"原则，**不创建重复的 acceptance_status.py**，避免状态定义双源。acceptance_evidence_chain.py 作为桥接层复用 acceptance_gate.py。

---

## 二、修改文件清单

### 2.1 新增文件

| 文件 | 行数 | 用途 |
|---|---|---|
| acceptance_evidence_chain.py | ~600 | 验收证据链构建器：9节点通用链路 + 11节点AI/Browser链路 + 证据链→判定器映射 + explain()可追溯 + 可选持久化 |
| tests/test_acceptance_upgrade.py | ~350 | 集成测试：7大类33用例，覆盖证据链构建、build_and_judge、PARTIAL原因分类、AI/Browser特殊验收、可追溯性、批量判定、最高原则 |
| audit/ACCEPTANCE_UPGRADE.md | 本文档 | 完整审计与交付报告 |

### 2.2 修改文件

**无。** 本次为纯增量扩展，未修改任何现有文件。
- acceptance_gate.py：未修改（前序已实现）
- app.py：未修改（API 端点前序已集成）
- templates/system/evaluation.html：未修改（三维卡片前序已实现）
- evidence_chain.py：未修改（通过延迟导入复用）
- 数据库：无迁移（acceptance_evidence_chain 持久化复用 evidence_chain 已有 zbc_evidence 表）

### 2.3 数据库变化

**无数据库迁移。** acceptance_evidence_chain.py 的可选持久化功能复用 evidence_chain.py 已有的 zbc_evidence 独立表（source_type="acceptance_chain"），不新增表、不新增字段、不触碰生产表。默认 persist_evidence=False，纯内存计算。

---

## 三、状态映射表

### 3.1 CI Status（独立维度，只回答"代码检查有没有通过"）

| 标记 | CIStatus | 含义 |
|---|---|---|
| ✓ | PASS | 当前 Commit/Check 通过 |
| × | FAILED | 未通过 |
| ? | UNKNOWN | 未提供 CI 结果 |

**硬规则：CI PASS ≠ VERIFIED。CI 状态与功能状态完全独立。**

### 3.2 Functional Status（6态状态机 + PARTIAL 修饰符）

| 状态 | 含义 | 判定条件 |
|---|---|---|
| PLANNED | 源码不存在 | source_exists ≠ True |
| IMPLEMENTED | 源码存在、调用链可定位，但链路未闭环 | source_exists=True, call_graph_closed≠True, test_passed≠True |
| TESTED | 自动化测试通过，但没有真实运行验证 | test_passed=True, runtime_evidence≠True |
| VERIFIED | 真实运行+调用链+Evidence+验收条件全部成立 | 8维全满足（AI/Browser还需ai_chain_closed=True） |
| RELEASED | 已进入正式发布 | is_released=True + 8维全满足 |
| OPERATING | 发布后实际运行持续有证据 | is_released=True + has_continuous_runtime=True + 8维全满足 |
| PARTIAL | 任一验收条件未完整闭环 | 其余未达 VERIFIED 的情况，携带具体原因 |

### 3.3 8 个验收维度（Functional Acceptance 构成）

| 维度 | 字段 | 含义 |
|---|---|---|
| source | source_exists | 真实源码存在 |
| call_graph | call_graph_closed | 调用链闭环可定位 |
| runtime | runtime_evidence | 真实运行证据 |
| test | test_passed | 自动化测试通过 |
| evidence | evidence_recorded | Evidence 链可追溯 |
| verification | verification_passed | 预期 vs 实际核验通过 |
| security | security_verified | 权限/安全核验通过 |
| regression | regression_passed | 回归无破坏 |

**VERIFIED 必须 8 维全部满足，缺一不可。**

### 3.4 Evidence Coverage（证据覆盖率）

- 计算方式：8 维中已满足的维度数 / 8 × 100%
- 范围：0.0% ~ 100.0%
- **禁止只显示百分比无法追溯**：必须同时展示 satisfied_dimensions / missing_dimensions / partial_reasons

---

## 四、PARTIAL 原因分类（12类）

| 原因 | 触发条件 |
|---|---|
| Missing Source | source_exists ≠ True |
| Call Graph Incomplete | call_graph_closed ≠ True |
| Missing Runtime Evidence | runtime_evidence ≠ True |
| Test Failed | test_passed = False（区分于 Missing Test） |
| Missing Test | test_passed ≠ True 且 ≠ False |
| Missing Evidence | evidence_recorded ≠ True |
| Missing E2E | runtime_evidence≠True 或 verification_passed≠True |
| Missing Verification | verification_passed ≠ True |
| Permission Not Verified | security_verified ≠ True（附加提示） |
| Security Not Verified | security_verified ≠ True |
| Regression Not Verified | regression_passed ≠ True |
| AI/Browser Chain Not Closed | is_ai_or_browser=True 且 ai_chain_closed≠True |

**解决"19 VERIFIED / 14 PARTIAL"问题**：每个 PARTIAL 任务都携带具体原因列表，点击状态即可看到"为什么 PARTIAL"，不再是无法追溯的统计数字。

---

## 五、AI/Browser 特殊验收规则（硬要求）

### 5.1 规则

AI 和 AI Browser **不允许仅凭单元测试判定 VERIFIED**。必须至少验证完整闭环：

```
AI Task → Agent → Skill → Permission → Browser/Tool → Action → Result → Evidence → Verification → Trace
```

全部真实闭环后才 VERIFIED，否则 PARTIAL（原因：AI/Browser Chain Not Closed）。

### 5.2 实现

- acceptance_gate.py：AcceptanceInput.is_ai_or_browser + ai_chain_closed 字段；_dimension_evidence() 中 AI 链路未闭环时强制加入 call_graph/runtime 缺失维度 + AI_CHAIN_NOT_CLOSED 原因
- acceptance_evidence_chain.py：AI_CHAIN_ORDER 11节点定义；build_chain() 中 AI 扩展节点（agent/skill/permission/browser_tool/action/result/trace）；to_acceptance_input() 中 AI 链路闭环判定

### 5.3 测试覆盖

- test_ai_cannot_verify_by_unit_test_only：8维齐全但AI链路未闭 → PARTIAL
- test_ai_verified_when_full_chain_closed：11节点全过 → VERIFIED
- test_ai_partial_when_one_node_missing：缺一个节点 → PARTIAL
- E2E API 实测：AI 8维齐但 ai_chain_closed=False → PARTIAL 75%

---

## 六、证据链（Evidence Chain）

### 6.1 通用功能验收链路（9节点）

```
Task → Commit → Source → Call Graph → Test → Runtime → Evidence → Verification → Final Status
```

### 6.2 AI/Browser 特殊验收链路（11节点）

```
AI Task → Agent → Skill → Permission → Browser/Tool → Action → Result → Evidence → Verification → Trace → Final Status
```

### 6.3 可追溯性

用户点击 VERIFIED/PARTIAL 时可看到**为什么**得到这个状态：
- AcceptanceEvidenceChain.explain()：生成人类可读的完整链路状态报告
- 每个节点显示：✓ PASS / ✗ FAIL / ⚠ MISSING + 证据指针 + 详情
- 末尾列出 PARTIAL reasons + 缺失维度 + 已满足维度
- **禁止只显示百分比无法追溯**

### 6.4 与 evidence_chain.py 的关系

- acceptance_evidence_chain.py 是**逻辑层**：构建验收证据链、映射到判定器、生成可追溯报告
- evidence_chain.py 是**存储层**：EvidenceStore / CanonicalDataStore / LifecycleTracker
- 桥接方式：build_and_judge(persist_evidence=True) 时，将整条链的摘要作为一条 Evidence 写入 zbc_evidence 表（source_type="acceptance_chain"），复用 evidence_chain 的不可变存储和生命周期追踪
- 默认 persist_evidence=False，纯内存计算，零副作用

---

## 七、UI 卡片格式（已升级）

`templates/system/evaluation.html` 已实现三维卡片：

```
┌─────────────────────────────────────────────┐
│ 功能验收判定器 · Acceptance Gate              │
├─────────────────────────────────────────────┤
│ 任务ID: TASK-001  CI: ✓PASS  [AI/Browser开关] │
│ [全选8维] [判定] [清空]                        │
├─────────────────────────────────────────────┤
│ ☑ Source  ☑ Call Graph  ☑ Runtime  ☑ Test   │
│ ☑ Evidence  ☑ Verification  ☑ Security  ☑ Regression │
├─────────────────────────────────────────────┤
│ CI STATUS          FUNCTION STATUS    EVIDENCE COVERAGE │
│ ✓ PASS             VERIFIED           [██████████] 100%  │
├─────────────────────────────────────────────┤
│ 8 维证据全部成立，无缺失项                       │
│ 已满足: source,call_graph,... ｜ 缺失: 无       │
└─────────────────────────────────────────────┘
```

或 PARTIAL 状态：

```
┌─────────────────────────────────────────────┐
│ CI STATUS          FUNCTION STATUS    EVIDENCE COVERAGE │
│ × FAILED           PARTIAL            [█████░░░░░] 62%  │
├─────────────────────────────────────────────┤
│ 未验收原因:                                      │
│ [Missing Runtime Evidence] [Missing E2E]        │
│ 已满足: source,test ｜ 缺失: call_graph,runtime,... │
└─────────────────────────────────────────────┘
```

**保留**原运行质量六态面板（Loading/Empty/Error/Success/Degraded/Permission），不删除任何现有 UI。

---

## 八、验收最高原则（已写入代码注释）

```
CI PASS ≠ VERIFIED
代码存在 ≠ VERIFIED
AI说完成 ≠ VERIFIED
只有：真实源码 + 真实调用链 + 真实测试 + 真实运行 + 真实Evidence + 真实验证 = VERIFIED
```

- 代码位置：acceptance_evidence_chain.py ACCEPTANCE_PRINCIPLE 常量
- API 返回：/api/system/acceptance/dimensions 的 principle 字段
- 前端展示：evaluation.html 页面描述

---

## 九、修改前后状态对照

| 场景 | 修改前（容易误判） | 修改后（正确判定） |
|---|---|---|
| CI 通过但没真实运行 | 可能被当 VERIFIED | CI=PASS，Function=TESTED/PARTIAL，原因：Missing Runtime Evidence / Missing E2E |
| 代码刚写完、链路没闭环 | 静态扫描可能给 VERIFIED | Function=IMPLEMENTED，原因：Call Graph Incomplete |
| 8 维证据齐全 | —— | Function=VERIFIED，Coverage=100%，无缺失 |
| AI 功能只有单测通过 | 可能被当 VERIFIED | Function=PARTIAL，原因：AI/Browser Chain Not Closed |
| 任一维度缺失 | 只看到一个百分比/对勾 | Function=PARTIAL + 具体原因标签 + 缺失维度列表 + 可追溯 explain() |
| CI 失败 | × 被读成"功能失败" | CI=FAILED 与 Function 状态并列、各自独立 |
| 源码不存在 | 可能显示空白 | Function=PLANNED，原因：Missing Source |
| 已发布 + 持续运行 | 无区分 | Function=OPERATING（最高态） |
| 批量统计"19 VERIFIED / 14 PARTIAL" | 无法追溯为什么 | 每个 PARTIAL 携带原因列表 + missing_nodes，点击可看 explain() |

---

## 十、测试结果

### 10.1 本次新增测试

| 测试文件 | 用例数 | 结果 |
|---|---|---|
| tests/test_acceptance_upgrade.py | 33 | **33 passed** |
| tests/test_acceptance_gate.py（前序） | 19 | **19 passed** |
| **验收相关合计** | **52** | **52 passed / 0 failed** |

### 10.2 测试覆盖分类

| 分类 | 用例数 | 覆盖点 |
|---|---|---|
| 证据链构建 | 5 | 9节点通用链路、11节点AI链路、缺失证据显式标记、状态映射、覆盖率计算 |
| build_and_judge 集成 | 7 | VERIFIED/PLANNED/IMPLEMENTED/TESTED 各态、CI/Function独立、CI FAILED但Function VERIFIED、final_status回填 |
| PARTIAL 原因分类 | 6 | Missing Runtime、Test Failed vs Missing、Missing E2E、Security/Permission、Call Graph、Regression |
| AI/Browser 特殊验收 | 4 | 单测不能VERIFIED、全链路闭环VERIFIED、缺一个节点PARTIAL、11节点定义 |
| 可追溯性 | 4 | explain()含任务/状态、缺失节点可见、PARTIAL原因可见、to_dict()完整字段 |
| 批量判定 | 2 | 批量汇总+原因、平均覆盖率 |
| 最高原则&保留机制 | 5 | ACCEPTANCE_PRINCIPLE定义、×/✓/PARTIAL/VERIFIED保留、6态实现、PARTIAL原因7类覆盖、P0/P1数据不触碰 |

### 10.3 E2E API 实测（8201 重启后真实 HTTP）

| 测试 | 端点 | 结果 |
|---|---|---|
| dimensions 返回 | GET /api/system/acceptance/dimensions | ok=True, 3 CI状态, 7功能状态, 12 PARTIAL原因, 8维度 |
| VERIFIED 判定 | POST /api/system/acceptance/judge | ci=PASS, function=VERIFIED, coverage=100%, 无原因 |
| AI PARTIAL 判定 | POST /api/system/acceptance/judge | ci=PASS, function=PARTIAL, coverage=75%, 原因=AI/Browser Chain Not Closed |
| acceptance_evidence_chain 模块 | Python import + build_and_judge | 通用VERIFIED 100%、AI全链路VERIFIED 100%、explain()正常输出 |

### 10.4 全量测试回归

- 执行：`.venv\Scripts\python.exe -m pytest tests/ --capture=no -q`
- 本次新增/修改的验收相关测试：**全部通过**
- 其他域（KOS/runtime/frontend/login/repository_registry等）存在预存失败，与本次变更无关（本次仅新增2个文件，未修改任何现有代码）
- 未引入任何新的测试失败

---

## 十一、8201 重启验证

| 步骤 | 操作 | 结果 |
|---|---|---|
| 1 | netstat :8201 查 PID | PID=21568 |
| 2 | taskkill /F /PID 21568 | SUCCESS |
| 3 | Start-Process .venv\Scripts\python.exe app.py | 启动成功 |
| 4 | netstat :8201 验证监听 | PID=25628, LISTENING |
| 5 | API smoke test（dimensions + judge × 2） | 全部通过（见 10.3） |
| 6 | 模块 import + build_and_judge 实测 | 全部通过（见 10.3） |

**结论：8201 重启后无回归，验收机制正常运行。**

---

## 十二、未完成项与风险

### 12.1 未完成项（非本次范围，建议后续迭代）

| 项 | 说明 | 优先级 |
|---|---|---|
| 各业务模块自动聚合证据注入 | 当前判定器为依赖注入纯函数，需各模块（采集/分析/报告/AI/Browser）自动聚合真实证据后调用 build_and_judge() | P1 |
| 证据链持久化默认开启 | 当前 persist_evidence=False（纯内存），后续可在各模块验收时默认开启并写入 zbc_evidence | P1 |
| 任务详情页点击状态跳转 explain() | 当前 evaluation.html 有三维卡片，但点击状态弹出完整 explain() 报告的交互可进一步增强 | P2 |
| 与 audit/_determine_status.py 静态扫描的融合 | 现有静态状态判定器可作为 source/call_graph/test 维度的自动证据来源 | P2 |
| RELEASED/OPERATING 状态的自动检测 | 当前需手动设置 is_released/has_continuous_runtime，后续可对接发布系统和运行时监控自动判定 | P2 |

### 12.2 风险与已知限制

| 风险 | 缓解措施 |
|---|---|
| 判定器为纯逻辑，证据真实性依赖调用方注入 | 设计上接受：AI 是增强层，规则与数据是业务最终真值；证据需可追溯（evidence_ref），后续可对接 evidence_chain 做真实性校验 |
| 全量测试中其他域存在预存失败 | 与本次变更无关（仅新增文件），已确认验收相关52用例全通过 |
| AI/Browser 链路闭环判定依赖 ai_chain_closed 字段 | 需 AI Core / AI Browser shard 在完成真实闭环后设置该字段为 True；当前已通过测试验证门控生效 |
| 不创建 acceptance_status.py 可能与用户指令字面表述不同 | 已在 1.4 节声明：acceptance_gate.py 已完整承担此角色，重复创建违反"不复制两套Core"原则；acceptance_evidence_chain.py 作为桥接层补齐证据链能力 |

---

## 十三、Git 状态

- 分支：lumenis-dual-domain-v3
- 本次变更：新增 3 个文件（acceptance_evidence_chain.py、tests/test_acceptance_upgrade.py、audit/ACCEPTANCE_UPGRADE.md）
- 修改文件：0
- 数据库迁移：0
- **merge/push 由 organizer 在所有 shard 完成后统一执行**

---

## 十四、交付物清单

1. **修改/新增文件清单**：见第二节（新增3文件，修改0文件）
2. **数据库迁移**：无（向后兼容，复用已有 zbc_evidence 表）
3. **测试结果**：验收相关 52 passed / 0 failed；E2E API 全部通过
4. **8201 重启验证结果**：无回归，API 正常
5. **修改前后状态对照表**：见第九节
6. **audit/ACCEPTANCE_UPGRA.md 路径**：`D:\Taikoo-monitor-new\audit\ACCEPTANCE_UPGRADE.md`（本文档）
7. **未完成项和风险**：见第十二节

---

*文档结束 · ZBC 验收机制增量升级 V2.0 · 2026-09-07*
