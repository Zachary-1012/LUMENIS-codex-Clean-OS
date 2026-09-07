# Phase 6 — Z-Brand-Core 源码级最终审计报告

> **审计日期**: 2026-09-07
> **审计范围**: `D:\Taikoo-monitor-new` 全仓库只读审计
> **生产 Python 文件**: 805 个（排除 .venv / __pycache__ / .git / node_modules / audit / tests / archive 等）
> **数据库**: `data/monitor.db`（129 张表）
> **审计方法**: AST 语法全量解析 + Grep 调用点确认 + DB schema 比对 + 静态行为分析
> **pyflakes**: 未安装，undefined-name 维度标注 PARTIAL

---

## 摘要

| 维度 | P0 | P1 | P2 | 合计 |
|------|----|----|----|------|
| 1. dead code | 0 | 2 | 3 | 5 |
| 2. duplicate implementation | 0 | 3 | 1 | 4 |
| 3. undefined function | 0 | 0 | 1 | 1 |
| 4. API/UI mismatch | 0 | 1 | 0 | 1 |
| 5. DB schema drift | 0 | 1 | 1 | 2 |
| 6. auth boundary（三层叠加） | 0 | 1 | 1 | 2 |
| 7. permission boundary | 0 | 2 | 0 | 2 |
| 8. background task lifecycle | 0 | 2 | 1 | 3 |
| 9. race condition | 0 | 2 | 0 | 2 |
| 10. exception swallowing | 0 | 1 | 1 | 2 |
| 11. runtime recovery | 0 | 1 | 0 | 1 |
| 12. hardcoded paths | 0 | 1 | 1 | 2 |
| 13. Feature Registry | 0 | 1 | 1 | 2 |
| 14. configuration drift | 0 | 1 | 1 | 2 |
| 15. AI/Agent/Skill lifecycle | 0 | 1 | 1 | 2 |
| 16. truth boundary | 0 | 1 | 1 | 2 |
| **合计** | **0** | **21** | **15** | **36** |

> **关键结论**: 本仓库未发现 P0 级（生产崩溃/数据丢失/安全漏洞/核心链路中断）问题。权限体系采用三层叠加设计且 fail-closed 执行到位，主体口径硬过滤贯穿全链路。主要风险集中在 P1 级维护性与健壮性问题：全局状态竞态、后台线程生命周期缺失、重复实现、配置漂移、Feature Flag 散落。

---

## Top 5 关键发现

1. **[P1] 全局可变状态 `collect_tasks` / `_brand_cache` 存在无锁竞态** — `app.py:2950/2955/2958` 对 `collect_tasks` 写操作未持 `_task_lock`（同文件其他 10 处均持锁）；`_brand_cache` 在 7 处读写无任何锁。
2. **[P1] `/api/collector/status` 路由被两个 Blueprint 重复注册** — `collection_api.py:22` 与 `collector_status_api.py:142` 定义同路径同方法，Flask 路由表中后注册者覆盖前者，导致其中一个实现永久不可达。
3. **[P1] 31 个 daemon 线程无统一生命周期管理** — 覆盖心跳(1s)、调度器、自动恢复(60s)、数据反馈(6h)、AI channel 健康检查(24h)等，无 shutdown hook、无 join、无进程级 guardian，进程崩溃后无自动恢复。
4. **[P1] 配置漂移严重** — 代码读取约 130 个环境变量，`.env.example` 仅覆盖约 80 个，缺失 `ZBC_DB_PATH`(30处引用)、`XHS_CDP_URL`(17处)、`PROXY_*`(10项) 等关键变量；`.env.example` 文件本身为 GBK 编码导致中文乱码。
5. **[P1] 无统一 Feature Registry，14+ 个 Feature Flag 散落为独立 env 变量** — 无运行时切换、无审计、无依赖关系管理，与 AGENTS.md 要求的"Feature Flags 配置驱动"目标存在差距。

---

## 维度 1：Dead Code（死代码）

### 1.1 [P1] `app_refactor_blueprint.py` 定义 7 个 Blueprint 但从未注册

- **文件**: `app_refactor_blueprint.py:52-191`
- **证据**: 该文件定义 `notes_bp`(url_prefix=/api/notes)、`events_bp`、`reports_bp`、`ai_bp`、`collection_bp`、`settings_bp`、`web_bp`，并提供 `register_blueprints(app)` 函数（L185-191）。
- **调用点确认**: 全仓库 grep `app_refactor_blueprint` 和 `register_blueprints` 在 `app.py` 中 **0 匹配**。该模块从未被 import 或调用。
- **影响**: 约 140 行废弃重构代码，与 app.py 中内联路由形成维护分叉风险。
- **建议**: 确认无外部依赖后归档至 `99-ARCHIVE/`，或在 app.py 中显式 `# DEPRECATED` 标注。

### 1.2 [P1] AST 扫描发现 1785 个"定义后无外部引用"候选

- **方法**: 对 242 个核心生产模块做 AST 解析，提取 3259 个函数/类定义，交叉比对全量 Name/Attribute 引用。
- **确认死代码（0 引用，含自身文件内）**:
  - `Checkpoint` 类 — `runtime_guardian.py:177`（refs=0）
  - `CollectionQualityGate` 类 — `collection_quality_gate.py:125`（refs=0；但同模块 `ensure_quality_log_table()` 被 app.py:1177 调用，类本身未使用）
  - `ComplianceGate` 类 — `compliance_gate.py:42`（refs=0）
- **说明**: 1785 候选中大量为误报（通过 `import module` 后 `module.ClassName()` 调用的类不会被 Name 节点捕获），但 pattern 表明仓库存在大量"定义后未实例化"的类。需逐模块人工确认。
- **建议**: 优先清理上述 3 个 0 引用类；对其余候选按模块分批审计。

### 1.3 [P2] `web_monitor.py` 仅 793 字节，疑似占位/废弃

- **文件**: `web_monitor.py`（全文仅约 20 行）
- **证据**: 与 `web_monitor_v570.py`(6045字节) 并存，后者功能更完整。`web_monitor.py` 未在 app.py 中被 import。
- **建议**: 确认后归档。

### 1.4 [P2] `weekly_events.py` 仅 2170 字节，功能被 `daily_report.py` 覆盖

- **文件**: `weekly_events.py`
- **证据**: app.py:2561 路由 `/api/weekly/events` 内联实现，未 import `weekly_events.py`。

### 1.5 [P2] `check_system.py` / `check_warnings.py` / `check_logs.py` / `check_db_dates.py` / `check_empty_tables.py` / `quick_check.py` 为一次性脚本

- **证据**: 均为 `if __name__ == '__main__'` 入口的独立脚本，未被生产代码 import。属工具脚本，不算严格死代码，但应归入 `scripts/` 目录。

---

## 维度 2：Duplicate Implementation（重复实现）

### 2.1 [P1] `/api/collector/status` 路由双重注册

- **文件 A**: `collection_api.py:22` — `@bp.route('/api/collector/status', endpoint='api_collector_status')`
- **文件 B**: `collector_status_api.py:142` — `@collector_status_bp.route("/api/collector/status", methods=["GET"])`
- **注册点**: `app.py:182` (`collection_api.register_collection_api(app)`) 和 `app.py:218` (`app.register_blueprint(collector_status_bp)`) 均执行。
- **证据**: `system_features_api.py:197` 注释自相矛盾——"/api/collector/status 已在 app.py 中实现，此处不再重复注册"，但实际两个实现都在 Blueprint 中，app.py 本身没有该路由。
- **影响**: Flask URL Map 中同路径同方法的两条规则，先注册者命中（collection_api 先注册），`collector_status_api.py` 的实现永久不可达。
- **建议**: 保留 `collector_status_api.py`（统一信封 success/data/error 格式），删除 `collection_api.py` 中的重复定义，或反向操作。

### 2.2 [P1] `subject_hit()` 在 5 处局部重新定义，未复用 `subject_rules.py` 标准实现

- **标准实现**: `subject_rules.py:169` `def subject_hit(...)` — 系统唯一主体口径硬过滤
- **重复定义**:
  - `app.py:2931` — 局部函数 `def subject_hit(text):`
  - `collector_v2/run_profile.py:46` — 局部函数
  - `collector_v2/run_live_engine.py:17` — 局部函数
  - `collector_v2/run_live_engine.py:20` — `def subject_hit(_): return False`（直接返回 False，**违反主体口径 P0 红线**）
  - `data/test_persist.py:6` — 测试文件
- **风险**: `collector_v2/run_live_engine.py:20` 将主体过滤硬编码为 `return False`，意味着该采集路径下所有内容均通过主体过滤，可能引入非广州太古汇数据。
- **建议**: 全部替换为 `from subject_rules import subject_hit`；对 `run_live_engine.py:20` 立即修复。

### 2.3 [P1] 6 套 Guardian/Recovery 系统功能重叠

| 模块 | 职责 | 启动方式 | 线程 |
|------|------|----------|------|
| `auto_recovery.py` | 自动恢复监控 | app.py:6627 `start_background_monitor(60)` | daemon |
| `runtime_guardian.py` | 统一生命周期守护/reaper | app.py:6658 `start_reaper(30)` | daemon |
| `system_guardian.py` | 健康状态记录 | app.py:6649 `health_check()`（一次性） | 无 |
| `stability_monitor.py` | 稳定性/崩溃日志 | app.py:4372 单例 | 内部线程 |
| `resident_health.py` | 常驻健康检查 | app.py:2150 按需调用 | 无 |
| `system_watchdog.py` | 看门狗 | 未在 app.py 中发现启动调用 | 未知 |
- **证据**: `system_watchdog.py` 定义了 watchdog 逻辑但 app.py 中无 import/启动（grep `system_watchdog` 在 app.py 中 0 匹配）。
- **建议**: 按 AGENTS.md "一套 Core" 原则收敛至 `runtime_guardian.py` 统一入口，其余标记 Legacy。

### 2.4 [P2] `_subject_sql_and_values` 三处定义

- `app.py:979` — 委托给 `subject_rules.subject_sql_and_values`（正确）
- `risk_engine.py:292` — 独立实现
- `subject_rules.py:209` — 标准实现
- **建议**: `risk_engine.py` 应 import 标准实现，消除分叉。

---

## 维度 3：Undefined Function（未定义函数调用）

### 3.1 [P2] pyflakes 未安装，undefined-name 检查为 PARTIAL

- **状态**: venv 中无 pyflakes / pylint。AST 全量解析 1373 文件，仅发现 10 个 BOM 编码问题（均能正常 compile，非语法错误）。
- **BOM 文件（生产代码 5 个）**: `engineering_metrics.py`、`evaluation_system.py`、`populate_empty_tables.py`、`report_api.py`、`subject_rules.py` — 文件首字节为 U+FEFF，Python compile 可处理但不一致。
- **建议**: 安装 pyflakes 后做全量 undefined-name 扫描；统一去除生产文件 BOM。

---

## 维度 4：API/UI Mismatch（前后端 API 不匹配）

### 4.1 [P1] 前端模板调用 `/api/auth-recovery/summary`，Blueprint 注册路径需确认

- **前端**: `templates/auth_recovery_modal.html:387` — `fetch('/api/auth-recovery/summary')`
- **后端**: `auth_recovery_api.py:9` — `Blueprint('auth_recovery', __name__, url_prefix='/api/auth-recovery')`
- **状态**: Blueprint 已在 app.py:158 注册。需确认该 Blueprint 内是否定义了 `/summary` 路由（本次审计未逐行核对该文件全部路由）。
- **标注**: PARTIAL — 建议运行时 curl 验证该端点返回 200。

### 4.2 已确认匹配的前端调用（非问题，记录排除）

以下前端 fetch 均有对应 Blueprint 路由：
- `/api/data-center/stats/overview` → `data_center_api.py` (url_prefix=/api/data-center)
- `/api/internal-browser/screenshot` → `internal_browser.py:428`
- `/api/collector/status` → 存在但重复注册（见 2.1）
- `/api/content/evidence` → `content_generation.py:735`
- `/api/system/account/members` → `account/api.py` (url_prefix=/api/system/account)
- `/api/system/account/totp/verify` → `account/api.py`

---

## 维度 5：DB Schema Drift（数据库模式漂移）

### 5.1 [P1] `monitor.db` 129 张表，部分表无 ORM Model 定义

- **现状**: `models.py` 仅定义约 15 个 ORM 类（BaseModel, Note, Comment, DailyReport, DailyDigest, BrandIndustryMonitor, CollectionCounter, CollectionLog, CollectorQualityLog, AIFilterLog 等），但 DB 中有 129 张表。
- **证据**: 大量表（`xhs_notes`, `xhs_users`, `weibo_*`, `bilibili_*`, `douyin_*`, `tiktok_*`, `instagram_*`, `reddit_*`, `youtube_*`, `zhihu_*`, `linkedin_*`, `github_*`, `x_*`, `channels_*`, `platform_*`, `kos_*`, `podcast_*`, `swire_*`, `v4_*`, `zbc_*`, `ai_*`, `event_graph_*`, `brand_propagation_*`, `runtime_guardian_*`, `schedule_decisions`, `topic_campaign_*`, `professional_*`, `notification_*`, `alert_*`, `intelligence_*`, `skill_*`, `content_*`, `evaluation_*`, `web_*`, `metric_*`, `creators`, `feedback_keywords`, `rule_version_registry`, `schema_version`, `token_stat`, `user_nav_config` 等）通过原始 SQL 直接操作，无 ORM 层。
- **风险**: 无 ORM 意味着无迁移版本管理、无类型安全、schema 变更需手工同步。`database_migrations.py` 管理部分迁移，但 129 张表中大量由各模块独立 `CREATE TABLE IF NOT EXISTS` 创建（如 `platform_adapters/scheduling/store.py:18`, `evidence_chain.py init_db`, `canonical_data.py ensure_canonical_table`），迁移入口分散。
- **建议**: 建立表清单注册表（table registry），统一迁移入口；对核心业务表补充 ORM Model。

### 5.2 [P2] `schedule_decisions` 表创建入口在 `platform_adapters/scheduling/store.py`，非主迁移链

- **证据**: `store.py:18` `CREATE TABLE IF NOT EXISTS schedule_decisions`，由该模块自行建表，不经过 `database_migrations.migrate()`。
- **风险**: 新环境部署时若未触发该模块导入，表不会创建，导致运行时 `no such table` 错误。
- **建议**: 纳入 `database_migrations.py` 统一迁移。

---

## 维度 6：Auth Boundary（认证边界）— 三层叠加设计精确统计

### 设计架构

本系统认证为**三层叠加**，非单层装饰器模式：

```
请求 → [Layer 1] Basic Auth before_request (app.py:999)
       → [Layer 2] 写操作统一 PermissionGate (app.py:1100, fail-closed)
       → [Layer 3] 高风险端点 @require_permission 装饰器
       → 业务逻辑
```

### Layer 1：全局 Basic Auth（app.py:999-1027）

- **机制**: `@app.before_request` 中校验 `Authorization: Basic`，凭证来自 `TAIKOO_AUTH_USER` / `TAIKOO_AUTH_PASSWORD` 环境变量。
- **白名单路径**（无需登录，app.py:1004）:
  - 精确路径 15 个: `/healthz`, `/api/health`, `/api/collector-guard/status`, `/api/auth/config`, `/favicon.ico`, `/api/kos/report/view`, `/api/system/health`, `/api/system/health/summary`, `/api/system/status`, `/api/system/runtime`, `/api/risks/active`, `/api/risk/active`, `/cth/login`, `/zbmp/login`, `/system/settings`
  - 前缀: `/v4/*`（v4 独立 token 认证）, `/static/*`
  - CTH 只读 GET 前缀 20 个（`_CTH_READONLY_GET_PREFIXES`, app.py:953-964），**仅对 GET 生效**（`_is_cth_readonly_get` 显式检查 `method != 'GET' → False`）
- **统计**:
  - app.py 共 219 个路由装饰器
  - 白名单内路由约 20 个（全部为 GET 健康检查/登录页/静态资源）
  - **被 Basic Auth 覆盖的路由: ~199/219 (90.9%)**
  - **所有 89 个写路由(POST/PUT/DELETE/PATCH)均在 Basic Auth 保护内**（白名单不含任何写路径，CTH 前缀仅 GET）

### Layer 2：写操作统一 PermissionGate（app.py:1100-1148, fail-closed）

- **机制**: `@app.before_request` 中对 `_PG_WRITE_METHODS = {POST, PUT, DELETE, PATCH}` 统一拦截，调用 `_pg.check()` 判定权限。
- **fail-closed**: PermissionGate 未初始化 → 503 BLOCKED；任何异常 → 503 BLOCKED；权限拒绝 → 403 BLOCKED。
- **绕过路径**（`_PG_BYPASS_PATHS` 精确 30 个 + 前缀 7 个, app.py:1032-1118）:
  - 精确路径含: `/api/developer/run`, `/api/config/run-code`, `/api/dev/run-code`, `/api/system/acceptance/judge`, 以及 content/podcast 系列端点
  - 前缀: `/api/viz/`, `/api/system/account/`, `/v4/auth/`, `/api/auth/zbmp-entry/`, `/api/content/`, `/api/podcast/`, `/api/ic/`
- **统计**:
  - app.py 写路由 89 个
  - 被 Layer 2 覆盖（非 bypass）: 约 80 个
  - bypass 的写路由: 约 9 个（含 3 个代码执行端点、1 个纯内存计算、content/podcast/ic 蓝图写端点）

### Layer 3：高风险端点 @require_permission 装饰器（6 个）

| # | 行号 | 路由 | 操作类型 | 风险等级 |
|---|------|------|----------|----------|
| 1 | 882 | `DELETE /api/event-graph/events/<event_id>` | DATA_DELETE | CRITICAL |
| 2 | 3342 | `POST /api/system/config` | CONFIG_MODIFY | HIGH |
| 3 | 3459 | `POST /api/config/run-code` | RUNTIME_OPERATION | HIGH |
| 4 | 3641 | `DELETE /api/brands/<brand_en>` | DATA_DELETE | CRITICAL |
| 5 | 5269 | `POST /api/dev/run-code` | RUNTIME_OPERATION | HIGH |
| 6 | 6274 | `POST /api/cookies/import` | DATA_IMPORT | HIGH |

### 真缺口分析（三层均无覆盖的写/高风险端点）

**结论: 不存在"三层均无覆盖"的写路由。** 所有写路由至少被 Layer 1 (Basic Auth) 保护。

**存在的缺口（有 Layer 1 但缺 Layer 2 + Layer 3）**:

| 端点 | Layer 1 | Layer 2 | Layer 3 | 实际写操作 | 风险 |
|------|---------|---------|---------|-----------|------|
| `/api/content/*` POST (8个) | ✅ Basic Auth | ❌ bypass 前缀 | ❌ 无 | 写 `content_generation_evidence` / `content_evaluation` 表 | P1 |
| `/api/podcast/entity` POST | ✅ Basic Auth | ❌ bypass 前缀 | ❌ 无 | 写 `podcast_entities` 表 | P1 |
| `/api/ic/alert/*` POST (6个) | ✅ Basic Auth | ❌ bypass 前缀 | ❌ 无 | 写 `alert_configs` / `alert_records` 表 | P1 |
| `/api/developer/run` POST | ✅ Basic Auth | ❌ bypass 精确 | ❌ 无 | **始终返回 403**（生产禁用，app.py:2380） | 已缓解 |
| `/api/system/acceptance/judge` POST | ✅ Basic Auth | ❌ bypass 精确 | ❌ 无 | 纯内存计算，不写 DB | 低 |

### 6.1 [P1] content/podcast/ic 蓝图写端点绕过 PermissionGate 且无装饰器

- **文件**: `content_generation.py:676-935` (16 路由, ~8 个 POST), `podcast_routes.py:87` (POST /entity), `ic_routes.py:9-204` (6 个 POST)
- **证据**: app.py:1118 `request.path.startswith('/api/content/') or ... or '/api/podcast/' or '/api/ic/'` 直接 return None（绕过 Layer 2）。这些蓝图无任何 `@require_permission` 装饰器。
- **注释依据**: app.py:1041-1047 注释称"仅写 content_generation_evidence/content_evaluation 表，不碰生产数据"，但 `podcast_entities` 和 `alert_configs/alert_records` 不在该注释范围内。
- **建议**: 对 `podcast/entity` 和 `ic/alert/*` 的 POST 端点补充 `@require_permission`，或从 bypass 前缀中移除并依赖 `_pg_resolve_operation_type` 自动映射。

### 6.2 [P2] `/system/settings` HTML 页面在 Basic Auth 白名单中

- **文件**: app.py:1004 白名单包含 `/system/settings`
- **证据**: 该路径返回设置页面 HTML（app.py:5680），无需登录即可访问。页面内的 API 调用（如 `/api/system/config`）仍需 Basic Auth，但页面本身暴露系统信息（版本号、AI 状态等）。
- **建议**: 评估是否将 `/system/settings` 移出白名单（与 `/system/skills`, `/system/runtime` 一致——这两个不在白名单中）。

---

## 维度 7：Permission Boundary（权限边界）

### 7.1 [P1] `_PG_BYPASS_PATHS` 包含 3 个代码执行端点，其中 1 个无 Layer 3 保护

- **文件**: app.py:1038 — `'/api/developer/run', '/api/config/run-code', '/api/dev/run-code'`
- **分析**:
  - `/api/config/run-code` (L3458): 有 `@require_permission(RUNTIME_OPERATION, HIGH)` ✅
  - `/api/dev/run-code` (L5268): 有 `@require_permission(RUNTIME_OPERATION, HIGH)` ✅
  - `/api/developer/run` (L2373): **无装饰器**，但函数体始终返回 403 `DEV_EXEC_DISABLED`（app.py:2380-2381），生产不执行代码 ✅（已缓解）
- **残留风险**: `/api/developer/run` 的 `_dev_exec_guard` 仅做危险模式检查（app.py:2377），若未来有人移除 403 返回，该端点将在无权限检查下执行代码。
- **建议**: 给 `/api/developer/run` 补充 `@require_permission` 作为纵深防御，即使当前返回 403。

### 7.2 [P1] `_pg_resolve_operation_type` 基于路径字符串匹配，存在映射遗漏风险

- **文件**: app.py:1051-1097
- **证据**: 该函数通过 13 组 `if any(k in p for k in (...))` 做路径→操作类型映射。未命中任何规则时默认 `OperationType.DB_WRITE`（fail-closed 兜底，L1097）。
- **风险**: 新写路由若路径不含任何关键词（如 `/api/foo/bar` POST），会被映射为 `DB_WRITE` 而非更精确的类型。虽然 fail-closed 不会放行，但权限粒度不准确。
- **建议**: 对新路由强制要求在 `_pg_resolve_operation_type` 中注册映射，或在路由装饰器中显式声明 operation_type。

---

## 维度 8：Background Task Lifecycle（后台任务生命周期）

### 8.1 [P1] 31 个 daemon 线程无统一 shutdown/join 机制

- **全量清单**（生产代码）:

| 文件 | 行号 | 线程名/用途 | daemon |
|------|------|------------|--------|
| app.py | 925 | proxy_health_loop | ✅ |
| app.py | 1919 | intelligence refresh worker | ✅ |
| app.py | 2507 | collect task worker | ✅ |
| app.py | 2959 | rednote collect worker | ✅ |
| app.py | 3584 | brand discover worker | ✅ |
| app.py | 4353 | scheduler_loop | ✅ |
| app.py | 4693 | weibo_login | ✅ |
| app.py | 5236 | update_web_topics | ✅ |
| app.py | 6601 | heartbeat_monitor (1s) | ✅ |
| app.py | 6643 | data-feedback-loop (6h) | ✅ |
| ai_api.py | 343 | ai worker | ✅ |
| ai_channel.py | 289 | ai-channel-health | ✅ |
| ai_channel.py | 438 | ai-channel-24h-heartbeat | ✅ |
| ai_task_engine.py | 1166 | ai_worker | ✅ |
| auth_recovery_api.py | 99 | recovery worker | ✅ |
| auto_recovery.py | 467 | auto-recovery-monitor (60s) | ✅ |
| browser_surface.py | 956 | listen_loop | ✅ |
| collector_automation.py | 371 | collector-heartbeat | ✅ |
| collector_automation.py | 573 | collection worker | ✅ |
| internal_browser_stream.py | 58 | screencast loop | ✅ |
| lifecycle_mixin.py | 300 | (未命名) | ✅ |
| memory_optimizer.py | 248 | (未命名) | ✅ |
| monitoring.py | 529 | monitor_loop | ✅ |
| run_production.py | 66,68 | (未命名) | ✅ |
| stability_monitor.py | 128,132,384 | (未命名) | ✅ |
| topic_campaign.py | 856,1056 | (未命名) | ✅ |
| xhs_cookie_bridge.py | 819,984 | (未命名) | ✅ |
| xhs_p0_orchestrator.py | 322 | (未命名) | ✅ |
| v4_upgrade/version_center/watcher.py | 39 | (未命名) | ✅ |

- **问题**:
  1. 无 `atexit` 或 Flask `teardown_appcontext` 中的线程停止逻辑
  2. 无 `thread.join()` 调用，进程退出时线程被强制杀死（daemon 特性），可能导致写入中断
  3. 多个线程无 `name` 参数（调试困难）
  4. 线程内 `while True` 循环无 `stop_event` 机制，无法优雅停止
- **建议**: 建立 `ThreadManager` 统一注册/启动/停止所有后台线程；在 `run_production.py` 的退出路径中调用 `stop_all()`。

### 8.2 [P1] `system_watchdog.py` 定义但未在 app.py 中启动

- **文件**: `system_watchdog.py`（12241 字节）
- **证据**: app.py 中 grep `system_watchdog` **0 匹配**。该模块定义了看门狗逻辑但从未被导入或启动。
- **建议**: 确认是否为废弃模块；若需使用，在 app.py guardian 区块（L6620-6662）中接入。

### 8.3 [P2] `threading.excepthook` 已设置（正向发现）

- **文件**: app.py:6615-6618
- **证据**: `threading.excepthook = thread_exception_handler` 捕获未处理线程异常并记录 CRITICAL 日志。这是良好实践。
- **不足**: 仅记录日志，不自动重启失败线程。

---

## 维度 9：Race Condition（竞态条件）

### 9.1 [P1] `collect_tasks` 在 rednote 采集路径中无锁访问

- **文件**: app.py
- **有锁访问（正确）**: L1258, L1264, L1289, L1297, L1315, L1323, L1325, L1327, L1911, L1915, L1917, L2506 — 均使用 `with _task_lock:`
- **无锁访问（竞态）**:
  - L2950: `collect_tasks[task_id] = {...}` （赋值）
  - L2955: `collect_tasks[task_id].update(...)` （更新）
  - L2958: `collect_tasks[task_id].update(...)` （更新）
- **证据**: L2949-2960 为 `rednote_collect` 路由处理函数，整段无 `with _task_lock:`。
- **风险**: 若 `/api/collect/status/<task_id>` 同时读取该 task_id，可能读到部分更新的字典（Python GIL 保证单字节码操作原子，但 `.update()` 非原子）。
- **建议**: L2950-2958 包裹 `with _task_lock:`。

### 9.2 [P1] `_brand_cache` 全局缓存在 7 处读写无锁

- **文件**: app.py
- **写位置**: L1530 (`= None`), L1539 (`= data.get(...)`), L1542 (`= []`), L1544 (`= []`), L3570 (`= None`), L3637 (`= None`), L3652 (`= None`)
- **读位置**: L1535 附近（`_load_brands` 函数内）
- **证据**: 无任何 `threading.Lock` 保护 `_brand_cache`。L3570/3637/3652 在品牌增删改路由中失效缓存，L1539 在读取时回填。
- **风险**: 品牌修改（POST/PUT/DELETE）与品牌读取（GET）并发时，读线程可能拿到 `None` 后触发重复 DB 查询，或拿到过期列表。
- **建议**: 引入 `_brand_cache_lock = threading.RLock()`，所有读写包裹。

### 9.3 正向发现：AI 模块全局状态有锁保护

- `ai_channel.py`: `_ENV_LOCK`, `_MONITOR_LOCK`, `_PROVIDER_LOCK`, `_FAILOVER_LOG_LOCK`（4 把锁）
- `ai_agent_registry.py`: `_lock`, `_registry_lock`
- `ai_call_logger.py`: `_WRITE_LOCK`（SQLite 多线程写保护）
- `ai_browser_runtime.py`: 6 个实例级 `_lock`
- `ai_task_engine.py`: 实例级 `_lock`

---

## 维度 10：Exception Swallowing（异常吞噬）

### 10.1 [P1] 13 处 `except: pass` / `except Exception: pass` 静默吞异常

| 文件 | 行号 | 代码 |
|------|------|------|
| `p2_memory_governance.py` | 76 | `except Exception: pass` |
| `skill_execution_chain.py` | 255 | `except Exception: pass` |
| `skill_execution_chain.py` | 384 | `except Exception: pass` |
| `skill_execution_chain.py` | 394 | `except Exception: pass` |
| `collector_v2/weibo/collector.py` | 190 | `except: pass` |
| `collector_v2/weibo/collector.py` | 195 | `except: pass` |
| `v4_upgrade/adapters/douyin.py` | 340 | `except Exception: pass` |
| `v4_upgrade/adapters/douyin.py` | 397 | `except Exception: pass` |
| `v4_upgrade/adapters/douyin.py` | 451 | `except Exception: pass` |
| `v4_upgrade/adapters/jiguang.py` | 127 | `except Exception: pass` |
| `scripts/audit_tools/scan_all.py` | 14 | `except Exception: pass`（脚本，非生产） |
| `scripts/audit_tools/scan_zbc_owned.py` | 49 | `except Exception: pass`（脚本） |
| `scripts/inventory/feature_final_verify.py` | 84 | `except: pass`（脚本） |

- **生产代码中 10 处**（排除 scripts/）。
- **风险**: 违反 AGENTS.md "数据失败必须显式，不得静默成 0 条" 原则。尤其 `collector_v2/weibo/collector.py:190,195` 在采集链路中静默吞异常，可能导致采集失败被伪装为成功。
- **建议**: 全部替换为 `except Exception as e: logger.warning(...)` 或至少 `print(...)`。

### 10.2 [P2] 全仓库 933 处 `except Exception:`（非 pass，但广泛存在）

- **统计**: grep `except Exception:` 在生产代码中匹配 933 处。
- **说明**: 大部分有 `logger.error` 或 `print` 记录，不属于静默吞噬。但 `except Exception` 过于宽泛，应尽量捕获具体异常类型。此为代码质量问题，不单独列为缺陷。

---

## 维度 11：Runtime Recovery（运行时恢复）

### 11.1 [P1] 无进程级 Guardian，Python 进程崩溃后无自动重启

- **现状**:
  - 进程内: `auto_recovery`(60s)、`runtime_guardian`(30s reaper)、`stability_monitor`、`heartbeat`(1s) — 均为 daemon 线程，进程死亡即全部停止
  - 进程外: `tunnel_guardian.py` 仅守护 cloudflared 隧道，不守护 Python 主进程
  - `run_production.py` 为启动脚本，无 supervisor/watcher 循环
- **证据**: 无 `supervisord.conf`、无 Windows Service 注册、无 `while True: subprocess.run(...)` 重启循环、无 systemd unit。
- **风险**: 未捕获异常导致进程退出后，系统完全不可用，需人工重启。
- **建议**: 在 `run_production.py` 中添加 watchdog 循环（`while True: try: run() except: wait 5s`），或配置 Windows Task Scheduler / NSSM 为服务。

### 正向发现：进程内恢复机制完善

- `auto_recovery.py:467` 后台监控线程每 60s 检查并恢复采集器
- `runtime_guardian.py` 提供 worker lease/checkpoint/DLQ 机制（3 张表: workers, checkpoints, dlq）
- `ip_risk_state_machine.py` 风控状态机支持熔断/冷却/恢复
- `auth_recovery_center.py` Auth 失效后系统内弹窗+二维码恢复

---

## 维度 12：Hardcoded Paths（硬编码路径）

### 12.1 [P1] 浏览器可执行文件路径硬编码为 Windows 绝对路径（6+ 处）

| 文件 | 行号 | 路径 |
|------|------|------|
| `cdp_helper.py` | 17-18,32-33,41-42,51-52 | Edge x86/x64, Chrome x86/x64, Firefox x86/x64 |
| `collector_automation.py` | 146-147 | Edge x86/x64 |
| `collector_auto_start.py` | 29-31 | Edge x86/x64 + `%USERNAME%` 路径 |
| `auto_recovery.py` | 295-296 | Edge x86/x64 |
- **证据**: 均为 `r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"` 形式。
- **风险**: 跨平台不可移植；浏览器安装路径变化时采集链路断裂。
- **正向**: `runtime_bin.py:52-53` 使用 `os.getenv("ProgramFiles", r"C:\Program Files")` 作为 fallback，是正确模式。
- **建议**: 统一通过 `runtime_bin.py` 查找浏览器路径，或使用 `shutil.which()` / Playwright 自带浏览器管理。

### 12.2 [P2] cloudflared 路径硬编码

- `start_tunnel.py:32-33`, `tunnel_guardian.py:50-51` — `r'C:\Program Files (x86)\cloudflared\cloudflared.exe'`
- **正向**: 已有 `CLOUDFLARED_BIN` 环境变量覆盖（`start_tunnel.py:29`），硬编码仅为 fallback。

---

## 维度 13：Feature Registry（功能开关注册）

### 13.1 [P1] 无统一 Feature Registry，14+ Feature Flag 散落为独立 env 变量

| Flag | 位置 | 控制范围 |
|------|------|----------|
| `ALLOW_CLOUD_AI` | .env.example | 云端 AI 总开关 |
| `ZBC_BROWSER_RUNTIME_XHS` | browser_runtime/adapters/xhs_collector_bridge.py:28 | 浏览器运行时 XHS |
| `XHS_APP_TOPIC_ENABLED` | platform_adapters/xhs_app_topic.py:29 | XHS App 话题采集 |
| `ZBC_REPORT_CENTER` | v4_upgrade/report_center/api.py:15 | 报告中心 |
| `ZBC_SCHED_GATE_MODE` | app.py:4209 | 调度门 (shadow/canary/enforce) |
| `GUARD_ENABLED` | collector_guard/__init__.py:24 | 采集守护 |
| `ZBC_GUARDIAN_ENABLED` | app.py:6622 | 三 guardian 总开关 |
| `ZBC_DEV_EXEC` | report_api.py:249 | 开发者代码执行 |
| `ZBC_TEST_MODE` | kos_routes.py:2123 | 测试模式 |
| `XHS_TEST_MODE` | xhs_cookie_bridge.py:689 | XHS 测试模式 |
| `ZBC_PREFLIGHT_ENFORCE` | runtime_preflight.py:283 | 启动前检查强制 |
| `ZBC_METRIC_SNAPSHOT` | database.py:488 | 指标快照 |
| `TAIKOO_WEB_DISCOVERY` | app.py:1267 | 全网发现 |
| `LOCALIZATION_GUARD_ENABLED` | scripts/localization_guard.py:20 | 本地化守护 |

- **问题**:
  1. 无中心注册表，无法枚举所有 flag
  2. 无运行时切换（改 env 需重启）
  3. 无依赖关系管理（如 `ALLOW_CLOUD_AI=false` 时各 AI flag 的行为）
  4. 无审计日志（谁在何时切换了什么 flag）
- **与 AGENTS.md 差距**: AGENTS.md 第 2 节明确要求"Feature Flags"作为产品差异控制手段，但当前实现为散落 env 变量。
- **建议**: 建立 `feature_registry.py` 统一注册所有 flag，提供 `is_enabled(name)` / `set_enabled(name, value)` / `list_all()` API，支持 DB 持久化和运行时切换。

### 13.2 [P2] `ZBC_SCHED_GATE_MODE` 三态模式（shadow/canary/enforce）实现良好但未纳入 Registry

- **文件**: app.py:4209, `platform_adapters/scheduling/gate.py`
- **说明**: 这是仓库中最完善的 Feature Flag 实现（有模式语义、有平台白名单），但仍是独立 env 变量，未与其他 flag 统一管理。

---

## 维度 14：Configuration Drift（配置漂移）

### 14.1 [P1] 代码读取约 130 个 env 变量，`.env.example` 仅覆盖约 80 个

- **代码中高频引用但 `.env.example` 缺失的关键变量**:

| 变量 | 代码引用数 | 用途 |
|------|-----------|------|
| `ZBC_DB_PATH` | 30 | 数据库路径（最关键） |
| `XHS_CDP_URL` | 17 | 小红书 CDP 端点 |
| `PROXY_*` | 10 | 代理池配置（PROXY_POOL_MODE, PROXY_HTTP, PROXY_SOCKS, PROXY_HEALTHCHECK_URL, 等） |
| `ZBC_DATA_DIR` | 4 | 数据目录 |
| `OSAI_ROOT` | 6 | OSAI 仓库路径 |
| `ZHIPU_API_KEY` | 6 | 智谱 AI key（.env.example 有但 .env 实际未设置值） |
| `TAIKOO_RISK_ENGINE` | 1 | 风险引擎开关 |
| `TAIKOO_COLLECTOR_GUARD` | 1 | 采集守护开关 |
| `XHS_COOKIE_FILE_OVERRIDE` | 2 | Cookie 文件覆盖 |
| `XHS_COOKIES_JSON` | 2 | Cookie JSON |
| `XHS_COOKIE_HEADER` | 2 | Cookie Header |
| `XHS_LOGIN_KEEPALIVE_FILE` | 1 | 登录保活文件 |
| `XHS_PROFILE_DIR` | 1 | 浏览器 Profile 目录 |
| `XHS_APP_API_ENDPOINT` | 1 | XHS App API |
| `ZBC_DOMAIN` | 2 | 域隔离 |
| `ZBC_ENV` | 1 | 运行环境 |
| `ZBC_RUNTIME_GUARDIAN_DB` | 1 | Guardian DB |
| `ZBC_COLLECTOR_DOMAIN` | 1 | 采集器域 |
| `ZBC_NODE_PATH` / `NODE_EXE` | 4 | Node.js 路径 |
| `GUARD_BASE_INTERVAL` / `GUARD_MIN_INTERVAL` | 2 | 守护间隔 |
| `SMS_API_KEY` / `SMS_API_SECRET` | 2 | 短信服务 |
| `JUGUANG_*` / `JIGUANG_*` | 5 | 巨量引擎广告 |
| `META_*` / `OCEAN_ENGINE_*` / `X_ADS_*` | 9 | 广告平台 |
| `V4_ACCESS_KEY` | .env.example 有 | .env 实际缺失 |

- **建议**: 以代码实际读取为准，重新生成 `.env.example`；建立 `config.py` 集中声明所有 env 变量及默认值，消除散落读取。

### 14.2 [P2] `.env.example` 文件为 GBK 编码，中文注释全部乱码

- **证据**: 读取 `.env.example` 时中文显示为乱码（如 "骞垮窞澶..."），表明文件保存为 GBK 而非 UTF-8。
- **风险**: 跨平台/跨工具打开时编码不一致；Linux/Mac 环境下乱码。
- **建议**: 转换为 UTF-8 编码。

---

## 维度 15：AI / Agent / Skill Lifecycle（AI 调用生命周期）

### 15.1 [P1] AI 输出直接进入日报正文，边界标注不足

- **文件**: `daily_report.py:297-308`, `daily_report.py:599-604`
- **证据**:
  - L300: `ai_result = _ai_summarize_event(event, event_notes)` → L302: `ai_summary = ai_result.get('summary', '')` → 写入报告
  - L601: `ai_summary = _ai_generate_daily_summary(...)` → L604: `ai_summary = executive`（AI 生成的摘要被赋值给 executive_summary）
- **AGENTS.md 红线**: "AI 不得单独决定...报告周期、原始数据真实性、最终核心风险口径"；"AI 输出必须可记录、可追溯、可人工修正"
- **现状**: AI 摘要存储在 `daily_reports.ai_summary` 字段（独立字段，有 `executive_summary` 区分），但 L604 将 AI 输出直接赋给 `executive` 变量，语义上模糊了"AI 建议"与"人工确认"边界。
- **建议**: 日报中 AI 生成内容必须标注 `[AI生成]` 前缀；`executive_summary` 字段应仅在人工确认后填充，AI 输出存 `ai_summary`。

### 15.2 [P2] AI 调用有超时/降级/熔断，但 Skill 执行无超时隔离

- **正向（AI Channel）**:
  - 超时: `AI_TIMEOUT_SECONDS=90`（.env.example）
  - 重试: `ai_channel.py` RETRYABLE_KINDS 机制
  - 熔断: `_PROVIDER_BREAKERS` 断路器（有锁保护）
  - 降级链: 智谱 GLM → ARK/千问 → Ollama 本地 → 确定性规则（Provider-Agnostic）
  - 日志: `ai_call_logs` 表记录每次调用（28 字段）
- **不足（Skill）**:
  - `skill_execution_chain.py` 中 3 处 `except Exception: pass`（见 10.1）
  - 无 Skill 执行超时配置（AI Task Engine 有任务超时，但 Skill 链本身无 per-skill timeout）
  - `skill_registry.py` 有注册但无健康检查/版本管理
- **建议**: 为 Skill 执行添加 `signal.alarm` 或 `threading.Timer` 超时；Skill 失败时记录到 `skill_executions` 表而非静默 pass。

### 正向发现：AI 输出不覆盖 Source Truth

- `zbc_canonical_data` 表: `ai_analysis`（AI 建议）与 `human_correction`（人工修正）为独立字段，`normalized_content`（计算真值）不被 AI 直接覆盖
- `notes` 表: `sentiment`/`risk_level` 等字段由规则引擎+AI 辅助，但 `subject_hit` 由确定性规则决定
- `content_analysis` 表: AI 分析结果独立存储，不回写 notes 原始字段
- `ai_call_logs` 表: 完整记录 input/output/confidence/failure_reason，可追溯

---

## 维度 16：Source Truth / Computed Truth / AI Suggestion / Human Decision 边界

### 16.1 [P1] 四层真值边界在 Schema 中清晰，但代码中存在混用

| 层级 | 存储位置 | 字段示例 | 边界状态 |
|------|----------|----------|----------|
| Source Truth（原始采集） | `notes`, `xhs_notes`, `platform_contents` | `title`, `content`, `author_id`, `publish_time`, `url` | ✅ 清晰，仅采集链路写入 |
| Computed Truth（计算得出） | `canonical_data`, `zbc_canonical_data` | `normalized_content`, `subject_hit`, `content_hash`, `rule_version` | ✅ 清晰，规则引擎写入 |
| AI Suggestion（AI 建议） | `content_analysis`, `zbc_canonical_data.ai_analysis`, `daily_reports.ai_summary` | `ai_sentiment`, `ai_risk`, `ai_summary`, `ai_analysis` | ✅ 独立字段 |
| Human Decision（人工确认） | `note_review_history`, `zbc_canonical_data.human_correction`, `negative` 确认表 | `human_correction`, `old_relevance`→`new_relevance` | ✅ 有审计轨迹 |

- **混用点**:
  1. `daily_report.py:604` — AI 输出赋给 `executive` 变量（见 15.1）
  2. `evidence_chain.py:758` — `UPDATE zbc_canonical_data SET ai_analysis = ?` 直接写入，无 `needs_human_review` 标记
  3. `ai_filter.py:219` — `ai_result = _ai_deep_review(note, quality_score)` 结果用于过滤决策，需确认是否有规则兜底
- **建议**: 在 `zbc_canonical_data` 中增加 `ai_analysis_status` 字段（pending/confirmed/rejected），AI 写入后默认 pending，人工确认后才进入计算真值。

### 16.2 [P2] `collector_v2/run_live_engine.py:20` 主体过滤硬编码为 `return False`

- **证据**: 见维度 2.2。该路径下 Source Truth 的主体归属判定被绕过，所有内容标记为"命中主体"。
- **影响**: 违反 AGENTS.md 第 5 节"广州太古汇主体口径 P0 不得弱化"红线。
- **建议**: 立即修复为 `from subject_rules import subject_hit`。

---

## 附录 A：审计方法与工具

1. **AST 全量语法检查**: 1373 文件解析，0 语法错误（10 个 BOM 文件可正常 compile）
2. **死代码扫描**: 242 核心模块 AST 分析，3259 定义，1785 候选（含误报）
3. **DB Schema 比对**: 129 表枚举，与 242 模块代码中 SQL 引用交叉比对
4. **路由计数**: app.py 219 路由装饰器，89 个写路由
5. **Env 变量扫描**: 全仓库 `os.environ.get` / `os.getenv` 提取，约 130 个独立变量
6. **线程扫描**: 全仓库 `daemon=True` 线程 31 个
7. **异常扫描**: `except: pass` 13 处，`except Exception:` 933 处

## 附录 B：未完成项 / PARTIAL 标注

| 项 | 状态 | 原因 |
|----|------|------|
| undefined function 全量扫描 | PARTIAL | venv 无 pyflakes/pylint，AST 只能查语法不能查未定义名 |
| Blueprint 内路由与前端 100% 匹配验证 | PARTIAL | 未逐行核对所有 Blueprint 路由，仅抽样确认 |
| DB 表字段级漂移 | PARTIAL | 未做 129 表 × 字段的全量代码引用比对 |
| 竞态条件动态验证 | PARTIAL | 静态分析只能发现无锁访问，无法证明实际触发 |
| AI 输出是否进入风险口径最终判定 | PARTIAL | `risk_engine.py` 未逐行审计 AI 参与度 |

## 附录 C：AGENTS.md 合规性检查

| AGENTS.md 要求 | 现状 | 合规 |
|----------------|------|------|
| 一套 Core，不复制两套 | 存在 `collector_v2` 与 `collector` 并行，`platform_adapters` 与 `adapters` 并行 | ⚠️ 部分 |
| 主体口径 P0 硬过滤 | `subject_rules.py` 标准实现存在，但 5 处局部重定义（含 1 处 return False） | ⚠️ 部分 |
| AI 不单独决定核心口径 | Schema 分层清晰，但日报 executive_summary 混用 | ⚠️ 部分 |
| 数据失败不得静默成 0 条 | 10 处生产代码 `except: pass` | ❌ 违规 |
| Cookie/session 失效系统内可见 | `auth_recovery_center.py` + 全局 Auth 状态中心 | ✅ |
| 新能力先旁路验证 | `ZBC_SCHED_GATE_MODE=shadow` 默认，content/podcast 旁路表 | ✅ |
| API Key 不写入源码 | 全部通过 `.env` 注入，grep 未发现硬编码 key | ✅ |
| 官方账号只读保护 | `ai_browser_runtime.py:380 _READONLY_BLOCKED_ACTIONS` | ✅ |
| Feature Flags 配置驱动 | 14+ 散落 env 变量，无统一 Registry | ⚠️ 部分 |
