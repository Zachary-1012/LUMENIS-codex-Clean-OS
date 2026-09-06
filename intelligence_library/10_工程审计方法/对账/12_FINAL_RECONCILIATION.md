# 12_FINAL_RECONCILIATION.md — 最终对账终表（双子星源码三方对账）

> 所属：SOURCE RECONCILIATION（架构 ↔ 工单 ↔ 本地源码三方对账）
> 审计日期：2026-09-02
> OSAI（研究侧）：`D:\Zachary OS AI`，branch main，HEAD `60af16a`
> ZBC（生产侧）：`D:\Taikoo-monitor-new`，branch main，基线 HEAD `545a3ab`（v5.9.9）

---

## 一、执行摘要

双子星双库架构在**代码级边界上合规**（无交叉 import、无反向生产写入、无 DB 乱连、无 UI 跨边界），但在**契约层与实现层之间存在系统性断裂**：OSAI 声明的 25 个 Contract 函数在 ZBC 零代码级落地，ZBC 203 个 API 路由零契约声明。最高保护层中 `aggregate_events()` 已从源码消失、`subject_hit()` 存在三处口径冲突，为最严重的 P0 缺口。生产库实际 53 张表（非基线 38 张），`publish_datetime`/`captured_at` 完整存在。P0 工单已基本落地，P1 部分完成，P2 几乎未启动。

## 二、12 份文档状态计数总表

| # | 文档 | EXISTS | PARTIAL | MISSING | UNKNOWN |
|---|------|--------|---------|---------|---------|
| 01 | SOURCE INVENTORY | 128 | 2 | 2 | 2 |
| 02 | ARCHITECTURE | 104 | 14 | 12 | 5 |
| 03 | CAPABILITY | 133 | 28 | 91 | 2 |
| 04 | FUNCTION | 191 | 28 | 24 | 2 |
| 05 | DATABASE | 18 | 9 | 5 | 0 |
| 06 | CONTRACT | 7 | 8 | 6 | 0 |
| 07 | OWNERSHIP | 12 | 5 | 2 | 0 |
| 08 | DEPENDENCY | 14 | 6 | 4 | 0 |
| 09 | UI/UX | 58 | 9 | 5 | 1 |
| 10 | TICKET | 7 | 16 | 1 | 1 |
| 11 | GAP REGISTER | — | — | — | — |
| 12 | FINAL | — | — | — | — |

## 三、四层对账矩阵

| 层 | 对应文档 | EXISTS | PARTIAL | MISSING | UNKNOWN | 关键结论 |
|----|----------|--------|---------|---------|---------|----------|
| SOURCE | 01 | 128 | 2 | 2 | 2 | 两仓库源结构清晰；OSAI 以文档/研究为主，ZBC 以生产代码为主 |
| ARCHITECTURE | 02 | 104 | 14 | 12 | 5 | 分层架构基本成立；上帝模块与 guardian 未接入为主要 PARTIAL |
| CONTRACT | 06 | 7 | 8 | 6 | 0 | **最薄弱层**：契约与实现全面脱钩，safe_collection 契约不可执行 |
| IMPLEMENTATION | 04+05+08 | 223 | 43 | 33 | 2 | 函数/数据库/依赖层实现度较高，但最高保护层有 P0 缺口 |

**UNKNOWN 残留（约 13 项，需后续消除）**：
- 02 架构层 5 项 UNKNOWN（运行时架构项，需运行时验证）
- 03 能力层 2 项 UNKNOWN
- 04 函数层 2 项 UNKNOWN
- 09 UI 层 1 项 UNKNOWN
- 10 工单层 1 项 UNKNOWN
- GAP-P1-12：3 个代码执行 API 的 Agent 权限绕过风险（需运行时审计）

**完成标准判定**：四层对账尚未达到"无 UNKNOWN"，主要阻塞在运行时验证类项与代码执行 API 安全审计。建议在 NEXT_ENGINEERING_QUEUE P1 中安排运行时审计消除。

## 四、双端边界合规结论

| 检查项 | 结论 | 证据 |
|--------|------|------|
| 越权调用 | ✅ PASS | OSAI 无 import ZBC，ZBC 无 import OSAI |
| 反向生产写入 | ✅ PASS | 无 ZBC→OSAI 写入代码路径 |
| 代码复制 | ⚠️ FAIL | OSAI `archive/desktop-legacy/taikoo-monitor-clean/` 含完整 ZBC v5.3.1 副本（GAP-P0-03） |
| DB 乱连 | ✅ PASS | OSAI 无生产 DB 连接；ZBC 仅连 `data/monitor.db` |
| UI 跨边界 | ✅ PASS | OSAI DCC/SICI-Core 为独立部署 UI，不接入 ZBC 生产路由、不直连生产 DB |
| Agent 绕过 Permission | ⚠️ UNKNOWN | 3 个代码执行 API 需运行时审计（GAP-P1-12） |

## 五、ZBC 最高保护层专项结论

| 项 | 状态 | 证据路径 |
|----|------|----------|
| SUBJECT_WORDS | ✅ EXISTS | `subject_rules.py`（唯一权威源） |
| SUBJECT_EXCLUDE_WORDS | ✅ EXISTS | `subject_rules.py`（唯一权威源） |
| `subject_hit()` | ⚠️ PARTIAL/冲突 | 权威 `subject_rules.py` L38；冲突副本 `app.py` L2743、`collector_v2/run_live_engine.py` L16/L20（GAP-P0-02） |
| `_subject_sql_and_values()` | ✅ EXISTS | `subject_rules.py`（app.py/risk_engine.py 纯委托） |
| `aggregate_events()` | ❌ MISSING | 全仓无 `def aggregate_events`（GAP-P0-01） |
| `build_daily_report()` | ✅ EXISTS | `daily_report.py` / `report_engine.py`；`report_engine.py` L48-63 强制 DB 统计口径写回报告 |
| `publish_datetime` | ✅ EXISTS | `notes` 表字段，957/957 非空 |
| `captured_at` | ✅ EXISTS | `notes` 表字段，957/957 非空 |
| Production DB | ✅ EXISTS | `data/monitor.db`，53 张表（根目录 `monitor.db` 仅 1 表残留 stub） |
| 生产数据 | ✅ EXISTS | notes 957 条、events 等表有数据 |
| 生产报告口径 | ✅ EXISTS | `report_engine.py` L48-63 强制 DB 口径防 AI 误写 |
| 最终风险口径 | ⚠️ PARTIAL | `risk_engine.py` 退化为 14 行委托层，无独立风险计算（GAP-P1-05） |

## 六、NEXT_ENGINEERING_QUEUE（按 P0/P1/P2 排序）

### P0 — 必须立即处理（最高保护层 / 生产阻断）

| # | 标题 | 关联 GAP | 修复目标 | 预估 | 依赖 | 验收标准 |
|---|------|----------|----------|------|------|----------|
| P0-1 | `aggregate_events()` 消失确认与恢复 | GAP-P0-01 | 确认事件聚合当前实际入口，恢复独立函数或正式声明替代方案并更新最高保护层清单 | 0.5 天 | 无 | 全仓有且仅有一个事件聚合权威函数，文档与代码一致 |
| P0-2 | `subject_hit()` 三处口径统一 | GAP-P0-02 | 废除 app.py L2743 替代规则与 collector_v2 stub，全部委托 `subject_rules.py` 权威实现 | 0.5 天 | 无 | 全仓仅 `subject_rules.py` 一处 `def subject_hit`，其余为 import 调用 |
| P0-3 | OSAI archive 中 ZBC v5.3.1 副本处置 | GAP-P0-03 | 从 OSAI 仓库移除或加密隔离生产代码副本（含 .env/.venv），确认无密钥泄露 | 0.5 天 | 无 | OSAI 仓库不含 ZBC 生产代码与环境；git history 评估是否需清理 |
| P0-4 | requirements.txt 补生产依赖 | GAP-P0-04 | 补 `waitress`、`beautifulsoup4` 及其他实际 import 但未声明的包 | 0.5 天 | 无 | 干净 venv 中 `pip install -r requirements.txt` 后 `run_production.py` 与 collector_v2 可正常 import |
| P0-5 | 版本号五处统一 | GAP-P0-05 | 以 `VERSION` 文件为唯一源，package.json/models.py/base.html/bat 全部对齐 v5.9.9 | 0.5 天 | 无 | 全局 grep 版本号仅一处定义，其余引用该源 |

### P1 — 功能闭环 / 契约断裂（建议 1–2 周）

| # | 标题 | 关联 GAP | 修复目标 | 预估 | 依赖 |
|---|------|----------|----------|------|------|
| P1-1 | OSAI 25 Contract 函数落地或正式废弃 | GAP-P1-01 | 逐项决定：在 ZBC 实现 / 修订 Contract 签名 / 正式声明废弃 | 3 天 | P0-2 |
| P1-2 | ZBC 203 API 路由补 OpenAPI 声明 | GAP-P1-02 | 生成 OpenAPI 3.0 spec 纳入 OSAI Contract 治理 | 3 天 | 无 |
| P1-3 | safe_collection 契约冲突解决 | GAP-P1-04 | 二选一：修订契约允许账号池/代理池（加安全约束），或 ZBC 改造为合规采集 | 2 天 | 安全评审 |
| P1-4 | risk_engine 独立风险计算恢复或降级声明 | GAP-P1-05 | 恢复独立风险逻辑，或正式声明其为纯委托层并更新最高保护层清单 | 1 天 | 无 |
| P1-5 | 单一权威 DB Schema 源建立 | GAP-P1-06 | 以 models.py 或独立 schema 文件覆盖全部 53 表，database.py SCHEMA 对齐 | 2 天 | 无 |
| P1-6 | 头条采集适配器补全 | GAP-P1-08 | 实现 toutiao 平台采集适配器 | 1 天 | P0-4 |
| P1-7 | guardian 三模块接入运行时 | GAP-P1-09 | app.py import 并启用 system_guardian/auto_recovery/data_feedback_loop | 1 天 | 无 |
| P1-8 | ZBC→OSAI 证据流转自动化 | GAP-P1-10 | 建立自动化证据同步管线（文件钩子或 CI） | 2 天 | 无 |
| P1-9 | 代码执行 API 运行时权限审计 | GAP-P1-12 | 运行时验证 3 个代码执行 API 的 Permission 校验，消除 UNKNOWN | 1 天 | 运行环境 |
| P1-10 | app.py/database.py 拆分规划 | GAP-P1-11 | 产出拆分方案（不立即执行），按子系统模块化 | 2 天 | 无 |

### P2 — 一致性 / 清理 / 优化（按排期推进）

| # | 标题 | 关联 GAP | 修复目标 | 预估 |
|---|------|----------|----------|------|
| P2-1 | P2 工单 10 项逐项推进 | GAP-P2-01 | 按工单列表逐项落地 | 5–7 天 |
| P2-2 | UI 主题统一 | GAP-P2-02 | 6+ 套 CSS 主题合并为 ZBIP 设计令牌驱动 | 2 天 |
| P2-3 | ZBIP_DESIGN_TOKENS.css 去重 | GAP-P2-03 | 双库三处重复合并为单一源 | 0.5 天 |
| P2-4 | 临时脚本/备份文件清理 | GAP-P2-04 | 清理 .bak/_reanalyze/旧版备份，纳入 .gitignore | 0.5 天 |
| P2-5 | zbrand 目录创建 | GAP-P2-05 | 按工单要求创建并初始化 | 0.5 天 |

## 七、未决事项（OPEN ITEMS）

1. **ZBC HEAD 差异**：01–08 组以 `545a3ab`（v5.9.9）为基线勘察；09–10 组发现实际当前 HEAD 已前移至 `a4adf70`。需用户确认以哪个为准。若以 `a4adf70` 为准，01–08 需做增量复核（重点核对新增 commit 是否影响最高保护层函数与表结构）。
2. **3 个代码执行 API 权限风险**：`/api/config/run-code`、`/api/dev/run-code`、`/api/workspace/term` 的 Agent 绕过 Permission 风险为 UNKNOWN，需运行时审计确认（已列入 P1-9）。
3. **OSAI archive 中 .env 密钥**：GAP-P0-03 涉及的 `taikoo-monitor-clean/.env` 可能含真实密钥，处置前需确认是否已泄露、是否需要轮换（安全红线：不保存/不上传真实 Cookie/Token/密钥）。

## 八、合规与自检声明

- **全程 READ ONLY**：未修改/删除/移动任何源码、配置、数据库。10 份 markdown 写入 `D:\Zachary OS AI\reconciliation\` 为唯一写操作。
- **事实优先级**：所有状态判定以本地当前源码为准；OSAI 根目录旧 01–22 文档仅作历史参考，未作为当前架构判断依据。
- **状态四分类**：每项均标注 EXISTS/PARTIAL/MISSING/UNKNOWN + 真实文件路径；UNKNOWN 未强行判为 EXISTS。
- **ZBC 最高保护层**：12 项逐项核对（见第五节），其中 `aggregate_events()` MISSING、`subject_hit()` 冲突、最终风险口径 PARTIAL 已标 P0/P1。
- **双端边界**：代码级合规，仅 OSAI archive 生产代码副本为越界 FAIL（GAP-P0-03）。
- **安全红线**：未涉及模拟真人/代理切换/账号轮换方案；未保存/上传任何真实 Cookie/Token/密钥。
