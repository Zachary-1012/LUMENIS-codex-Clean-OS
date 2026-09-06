# 11_GAP_REGISTER.md — 缺口登记（双子星源码三方对账）

> 所属：SOURCE RECONCILIATION（架构 ↔ 工单 ↔ 本地源码三方对账）
> 审计日期：2026-09-02
> OSAI（研究侧）：`D:\Zachary OS AI`，branch main，HEAD `60af16a`
> ZBC（生产侧）：`D:\Taikoo-monitor-new`，branch main，基线 HEAD `545a3ab`（v5.9.9）

---

## P0 级缺口（最高保护层 / 生产阻断）

| ID | 标题 | 类别 | 状态 | 证据路径 | 影响 | 判定理由 |
|----|------|------|------|----------|------|----------|
| GAP-P0-01 | `aggregate_events()` 从源码消失 | 函数 | MISSING | ZBC 全仓无 `def aggregate_events`；事件聚合内联于 `database.py`/`app.py`/`event_graph.py` | ZBC | 属最高保护层函数清单，无法按函数名做交接与审计 |
| GAP-P0-02 | `subject_hit()` 三处副本口径冲突 | 函数 | 冲突 | 权威：`subject_rules.py` L38；替代：`app.py` L2743（AI `verify_taikoo_location`）；stub：`collector_v2/run_live_engine.py` L16/L20（`return False`） | ZBC | 最高保护层函数存在多入口，stub 恒返回 False 可致主题命中失效 |
| GAP-P0-03 | OSAI 归档含完整 ZBC v5.3.1 生产代码副本 | Ownership | 越界 | `D:\Zachary OS AI\archive\desktop-legacy\taikoo-monitor-clean\`（含 app.py、database.py、.env、.venv、node_modules） | 双端 | 研究侧仓库持有生产代码+环境+疑似密钥，违反双端所有权边界 |
| GAP-P0-04 | `requirements.txt` 缺失生产依赖 | 依赖 | MISSING | `requirements.txt` 声明 17 包；缺 `waitress`（`run_production.py` 生产 WSGI 用）、`beautifulsoup4`（`collector_v2/` 与 v4 adapters 用） | ZBC | 生产启动与采集解析在干净环境下直接失败 |
| GAP-P0-05 | 版本号五处不一致 | 架构 | 冲突 | `VERSION`=v5.9.9 / `package.json`=5.6.2 / `models.py`=v5.8.0 / `templates/base.html`=5.8.9 / bat 启动脚本=5.8.0 | ZBC | 生产版本口径分裂，影响发布与问题定位 |

## P1 级缺口（功能闭环 / 契约断裂）

| ID | 标题 | 类别 | 状态 | 证据路径 | 判定理由 |
|----|------|------|------|----------|----------|
| GAP-P1-01 | OSAI 25 个 Contract 函数 ZBC 零代码级落地 | Contract | MISSING | OSAI Contract 声明；ZBC 中 0 个同名实现（9 个概念对应 PARTIAL，16 个 MISSING） | 契约层与实现层完全脱钩 |
| GAP-P1-02 | ZBC 203 个 API 路由零 OpenAPI/Contract 声明 | Contract | MISSING | `app.py` 路由计数；OSAI 无任何 API Contract | 隐式契约无治理 |
| GAP-P1-03 | 10+ 核心子系统 OSAI 侧无契约 | Contract | MISSING | v4 auth、`topic_campaign.py`、`event_graph.py`、`swire_group.py` 等 | 子系统游离于契约治理外 |
| GAP-P1-04 | `safe_collection.py` 契约与 ZBC 实际采集根本性冲突 | Contract | 冲突 | OSAI 契约禁账号池/代理池/PII 脱敏；ZBC 实际多账号+代理池+无脱敏 | 契约不可执行，需二选一 |
| GAP-P1-05 | `risk_engine.py` 退化为 14 行纯委托层 | 能力 | PARTIAL | `risk_engine.py` 全文；无独立风险计算逻辑 | 最终风险口径名存实亡 |
| GAP-P1-06 | 无单一权威 DB Schema 源 | 数据库 | PARTIAL | `database.py` SCHEMA 覆盖 15/52 表；`models.py` 覆盖 25/52 表 | 53 张表的 schema 分散且不完整 |
| GAP-P1-07 | OSAI 无正式 DB Schema/Contract 声明 | Contract | MISSING | OSAI 仅历史对账文档，无现行 schema 契约 | 双端无数据契约锚点 |
| GAP-P1-08 | 头条（toutiao）采集适配器缺失 | 能力 | MISSING | 工单 P1-1 要求 8 平台，7 个已实现，头条无适配器 | 工单承诺未兑现 |
| GAP-P1-09 | guardian 三模块源码存在但未接入运行时 | 能力 | PARTIAL | `system_guardian.py`/`auto_recovery.py`/`data_feedback_loop.py`；`app.py` 未 import | 死代码，工单 P1-10 未完成 |
| GAP-P1-10 | ZBC→OSAI 证据流转为手动文件复制 | 架构 | PARTIAL | 双端无自动化管线；无代码级交叉调用（合规）但流转靠人工 | 双端协同效率低且易漏 |
| GAP-P1-11 | app.py（5131 行）/ database.py（968 行）上帝模块 | 架构 | PARTIAL | `app.py`、`database.py` 行数 | 可维护性与变更风险高 |
| GAP-P1-12 | 3 个代码执行 API + Agent 绕过 Permission 风险 | 安全 | UNKNOWN | `/api/config/run-code`、`/api/dev/run-code`、`/api/workspace/term` | 需运行时审计，静态无法判定 |

## P2 级缺口（一致性 / 清理 / 优化）

| ID | 标题 | 类别 | 状态 | 证据路径 |
|----|------|------|------|----------|
| GAP-P2-01 | P2 工单 10 项 0 个 EXISTS | 工单 | MISSING | `10_TICKET_RECONCILIATION.md` P2 区段 |
| GAP-P2-02 | static/css/ 6+ 套 UI 主题并存未统一 | UI | PARTIAL | `D:\Taikoo-monitor-new\static\css\` |
| GAP-P2-03 | `ZBIP_DESIGN_TOKENS.css` 双库三处重复 | UI | 冲突 | ZBC 根目录 + OSAI components/ 多处 |
| GAP-P2-04 | 临时脚本/备份文件未清理 | 架构 | PARTIAL | `app.py.bak_p0_*`、`app_backup_v589.py`、`_reanalyze.py` 等 |
| GAP-P2-05 | zbrand 目录未创建 | 工单 | MISSING | 工单 P2 要求，当前不存在 |
