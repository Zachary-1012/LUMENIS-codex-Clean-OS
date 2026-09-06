# 验收机制增量升级 · 修改前后对照 V1.0（2026-09-07）

> 依据用户《ZBC｜验收机制增量升级指令》。原则：保留现有 ×/✓、PARTIAL/VERIFIED、P0/P1、Commit、CI/Test，**不重写、不删历史状态、不改 P0/P1 数据**，只做最小增量。

## 一、修改前（现状盘点）

| 现有机制 | 位置 | 能力边界（问题） |
|---|---|---|
| 模块静态状态判定 | `audit/_determine_status.py` | 只看源码静态特征（函数数/import/try-except/有无测试）判 VERIFIED/PARTIAL，**无 Runtime/Evidence/Security/Regression 维度**；代码存在就可能被判 VERIFIED |
| 数据质量评估 | `evaluation_system.py` / `evaluation_recorder.py` | 评估采集/分析/报告**数据质量**，不是功能验收 |
| 人工核销台账 | `audit/TODAY_REQUIREMENT_STATUS_LEDGER_V1.0.md` | Markdown 人工维护，无机器判定、无证据覆盖率、PARTIAL 原因不可点查 |
| 前端页面 | `templates/system/evaluation.html`（109 行） | 仅一个通用六态表格面板，无 CI/Function 分离展示 |
| CI ×/✓ | Git/CI | 容易被误读为「功能验收完成」 |

核心缺口：**CI PASS、代码存在、AI 声称完成 都可能被当成 VERIFIED；缺统一判定器、缺证据覆盖率、PARTIAL 原因不可见。**

## 二、修改后（本次增量，纯新增不破坏旧机制）

### 1. 新增生产级判定器 `acceptance_gate.py`（纯逻辑、零副作用、可单测）
- **CI Status**：`PASS / FAILED / UNKNOWN` —— 只回答「代码检查有没有通过」，与功能状态独立。
- **Functional Status** 状态机：
  `PLANNED → IMPLEMENTED → TESTED → VERIFIED → RELEASED → OPERATING`，任一验收条件未闭环 = `PARTIAL`。
  - 源码不存在 → PLANNED
  - 源码在、调用链未闭环 → IMPLEMENTED
  - 测试通过但无真实运行 → TESTED
  - 8 维全成立 → VERIFIED（AI/Browser 还要求完整链路闭环）
  - 已发布 → RELEASED；发布后持续运行证据 → OPERATING
- **8 个验收维度**：source / call_graph / runtime / test / evidence / verification / security / regression。
- **Evidence Coverage**：8 维中已成立占比（0–100%），不允许只给百分比不给依据。
- **PARTIAL 原因枚举（12 类）**：Missing Source、Call Graph Incomplete、Missing Runtime Evidence、Test Failed、Missing Test、Missing Evidence、Missing E2E、Missing Verification、Permission Not Verified、Security Not Verified、Regression Not Verified、AI/Browser Chain Not Closed。
- **AI/Browser 特殊门控**：不允许仅凭单测判 VERIFIED，必须 `ai_chain_closed=True`（Task→Agent→Skill→Permission→Browser/Tool→Evidence→Verification→Trace 闭环）。
- `judge()` 单个判定、`judge_batch()` 批量汇总（含 by_functional_status 统计、平均覆盖率、未达 VERIFIED 明细+原因）。

### 2. API（`app.py`，最小增量，兼容优先）
- `GET /api/system/acceptance/dimensions`：返回 8 维 / CI 状态 / 功能状态 / PARTIAL 原因枚举与判定原则。
- `POST /api/system/acceptance/judge`：单个或 `{tasks:[...]}` 批量判定；**纯内存计算不读写 DB/文件/网络**，已加入 PermissionGate 只读豁免（等同 run-code 类纯计算），非法字段返回 400 而非静默通过。

### 3. 前端 `templates/system/evaluation.html`
- **保留**原运行质量六态面板（Loading/Empty/Error/Success/Degraded/Permission）。
- 新增「功能验收判定器 · Acceptance Gate」工作台：任务 ID、CI 状态下拉、AI/Browser 开关、8 维证据勾选、判定/全选/清空；结果区按用户第八节规格展示三列卡片：
  - `CI STATUS`（✓PASS/×FAILED/UNKNOWN，独立配色）
  - `FUNCTION STATUS`（七态配色）
  - `EVIDENCE COVERAGE`（进度条+百分比）
  - 下方展示 PARTIAL 原因标签 + 已满足/缺失维度清单（可追溯，不只给百分比）。

### 4. 三语 i18n
- `static/locales/{zh-CN,en,ko}.json` 补 `nav.evaluation`：验收评估 / Evaluation / 평가（修复页面标题显示 raw key）。

### 5. 测试 `tests/test_acceptance_gate.py`（19 用例全通过）
- CI PASS 但功能 PARTIAL 二者独立；CI FAILED 但功能证据可齐全；PLANNED/IMPLEMENTED/TESTED/VERIFIED 各态；8 维任一缺失都阻断 VERIFIED（参数化 8 例）；RELEASED→OPERATING；AI/Browser 单测不能 VERIFIED、链路闭环才 VERIFIED；批量汇总+PARTIAL 原因；Test Failed 与 Missing Test 区分。

## 三、关键语义对照（修改前 → 修改后）

| 场景 | 修改前容易误判 | 修改后判定 |
|---|---|---|
| CI 通过但没真实运行 | 可能被当 VERIFIED | CI=PASS，Function=TESTED/PARTIAL，列出 Missing Runtime Evidence/E2E |
| 代码刚写完、链路没闭环 | 静态扫描可能给 VERIFIED | Function=IMPLEMENTED，Call Graph Incomplete |
| 8 维证据齐全 | —— | Function=VERIFIED，Coverage=100%，无缺失 |
| AI 功能只有单测通过 | 可能被当 VERIFIED | PARTIAL，AI/Browser Chain Not Closed |
| 任一维度缺失 | 只看到一个百分比/对勾 | 显式 PARTIAL + 具体原因标签 + 缺失维度列表 |
| CI 失败 | × 被读成「功能失败」 | CI=FAILED 与 Function 状态并列、各自独立 |

## 四、验证结果（真实证据）
- 单测：`tests/test_acceptance_gate.py` 19 passed；连同 rednote 轮换、skill 边界共 **108 passed / 0 failed**。
- API 实测（服务 v5.9.9，真实 HTTP）：
  - C1 全 8 维 → `VERIFIED / coverage 100% / 无缺失`；
  - C2 CI PASS 仅源码+链路+测试 → `TESTED / 37.5% / 7 项原因`；
  - C3 AI 8 维齐但链路未闭 → `PARTIAL / 75% / AI/Browser Chain Not Closed`。
- 前端实测（内置浏览器）：全选 8 维→判定，三列卡片正确渲染 CI ✓PASS / Function VERIFIED / Evidence 100%。

## 五、未改动 / 保留项（合规声明）
- 未删除任何历史状态、未改 P0/P1 台账数据、未改 evaluation_system/evaluation_recorder/audit/_determine_status 任何一行；旧 ×/✓、PARTIAL/VERIFIED 全部保留。
- 未新增重型状态体系，只增加 CI Status + Functional Status + Evidence Coverage 三个维度。
- 判定器为依赖注入的纯函数，不耦合具体 DB；后续各模块把真实证据（源码/调用链/测试/运行/Evidence/核验/安全/回归）聚合后注入即可批量出验收结论。
