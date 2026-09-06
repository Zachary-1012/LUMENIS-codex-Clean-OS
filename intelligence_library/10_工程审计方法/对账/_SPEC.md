# 双子星架构 SOURCE RECONCILIATION — 统一规范

> 本文件是 01–12 所有对账文档的硬约束。所有子代理必须严格遵守。

## 0. 任务性质
- **READ ONLY**：禁止删除/移动/重命名/重构/修改数据库/修改 Contract/修改配置/修改生产数据。只允许读源码、读 Git、读文档、写本目录下的对账 markdown。
- 对账对象：双子星双库。
  - **OSAI（研究侧）** = `D:\Zachary OS AI`，branch main，HEAD `60af16a`。职责：AI / Research / Learning / Architecture / Contract / Capability。
  - **ZBC（生产侧）** = `D:\Taikoo-monitor-new`，branch main，HEAD `545a3ab`，版本 v5.9.9。职责：Production Code / DB / Collection / Runtime / Test / E2E / Release。
- 旧"三库/四库"矩阵（SICI/DCC/AIDRH 等）仅作历史审计资料，**不得**作为当前架构判断依据。最终以【本地当前源码】为准。

## 1. 事实优先级（强制）
本地当前源码 > 当前可运行状态 > 当前测试结果 > 当前 Git Commit > 当前有效 Baseline > 历史文档。
- 禁止根据 README / 历史文档 / 模型记忆判断"存在"。
- 必须给出真实文件路径作为证据。

## 2. 状态四分类（每项必须标注）
| 状态 | 含义 |
|------|------|
| EXISTS | 本地源码中可定位到完整实现/文件/函数/表/Contract，路径真实可查 |
| PARTIAL | 存在但不完整：仅有声明/骨架/部分实现/历史残留，或与 Baseline 描述不符 |
| MISSING | Baseline/工单/架构要求存在，但本地源码中找不到 |
| UNKNOWN | 无法从本地源码判定（缺证据、被混淆、路径不存在）；**禁止把 UNKNOWN 强行判为 EXISTS** |

每项必须附：`状态 | 证据路径 | 备注`。

## 3. 双端边界检查（强制纳入每份相关文档）
- 合法流向：OSAI → Contract/Plan → ZBC；ZBC → Result/Evidence → OSAI。
- 检查项：越权调用、反向生产写入、代码复制、DB 乱连、UI 跨边界、Agent 绕过 Permission。
- 发现违规必须记录到 11_GAP_REGISTER。

## 4. ZBC 最高保护层（绝不能因研究/AI 建议改变）
SUBJECT_WORDS、SUBJECT_EXCLUDE_WORDS、subject_hit()、_subject_sql_and_values()、aggregate_events()、build_daily_report()、publish_datetime、captured_at、Production DB、生产数据、生产报告口径、最终风险口径。
- 对账时这些项若状态为 PARTIAL/MISSING，必须在 11_GAP_REGISTER 标 P0。

## 5. 安全红线
- 不允许把模拟真人、代理/IP 切换、账号轮换作为绕过平台安全的方案。
- 不保存/不上传任何真实 Cookie/Token/Session/密钥。对账文档中出现密钥必须打码。

## 6. 文档命名与落盘
- 全部输出到 `D:\Zachary OS AI\reconciliation\`，文件名严格为：
  `01_SOURCE_INVENTORY.md` / `02_ARCHITECTURE_RECONCILIATION.md` / `03_CAPABILITY_RECONCILIATION.md` / `04_FUNCTION_RECONCILIATION.md` / `05_DATABASE_RECONCILIATION.md` / `06_CONTRACT_RECONCILIATION.md` / `07_OWNERSHIP_RECONCILIATION.md` / `08_DEPENDENCY_RECONCILIATION.md` / `09_UI_UX_RECONCILIATION.md` / `10_TICKET_RECONCILIATION.md` / `11_GAP_REGISTER.md` / `12_FINAL_RECONCILIATION.md`。
- 每份文档头部必须含：审计日期 2026-09-02、两仓库 HEAD、状态统计（EXISTS/PARTIAL/MISSING/UNKNOWN 计数）。

## 7. 完成标准
- 四层对账（SOURCE → ARCHITECTURE → CONTRACT → IMPLEMENTATION）无 UNKNOWN。
- 12_FINAL_RECONCILIATION 必须输出 NEXT_ENGINEERING_QUEUE，按 P0/P1/P2 排序。
- 对账完成后才允许提出工程队列；本阶段不做任何代码改动。
