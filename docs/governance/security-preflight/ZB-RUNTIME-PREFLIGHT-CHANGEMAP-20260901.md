# ZB-RUNTIME-PREFLIGHT · 工单-源码映射 / Effective Rules / Change Map

- TASK ID：ZB-RUNTIME-PREFLIGHT-001（含 ZB-DATA-BOUNDARY-001，关联 ZB-EVIDENCE-001 / ZB-REDNOTE-XHS-001）
- 产品：品牌业务生产平台（Z-Brand Business Production Platform, ZBP）下 **Z-Brand 品牌监测平台（Z-Brand Monitoring Platform, ZBMP）/ 广州太古汇舆情监测系统（CorTech Lab · Guangzhou Taikoo Hui Public Opinion Monitoring System, CTH-POMS）** 同仓代码库 Z-Brand-Core
- BASE COMMIT：`0d0a27da1c690b41e00ddc64c084afaf24cbb61d`（origin/main，施工前 fetch 锁定）
- 分支：`feat/zb-runtime-preflight`（独立 worktree `D:\Taikoo-security`，不触碰运行中的生产 8201 与 8301 Staging）
- 来源工单：《ZBIP_四产品_统一安全架构运行预检工单_v1-0901.xlsx》Sheet「Z-Brand」4 条 P0
- 施工原则：先盘点不改码 → 最小新增 → 复用既有能力 → 真实测试出 Evidence → 双 Push（Implementation / Audit）

---

## 1. 四条工单 → 源码映射与本轮状态

| 工单 | 要求 | 既有可复用资产（盘点结论） | 本轮落地 | 状态 |
|---|---|---|---|---|
| ① Runtime Preflight 启动预检 | 来源、权限、依赖、数据、能力、配置完整性 | `security_scanner.py`（手动全量扫描，非启动闸门）、`safety_boundary.py`（自动修复操作边界，域不同） | 新增 `runtime_preflight.py`，8 项启动检查 + Attestation；`app.py` 启动段最小接入 | **COMPLETED** |
| ② Data Boundary 数据边界 | 品牌数据/账号授权/Cookie-Token/运行数据严格分区 | `.gitignore` 已完善；`database.DB_PATH` 支持 `ZBC_DB_PATH` 隔离 | 新增 `data_boundary.py`：四分区定义、Git 跟踪面凭证断言、日志/证据脱敏 | **COMPLETED** |
| ③ RedNote/XHS 双账号采集 | 香港 RedNote 为主、国内暂缓；规划中，**本轮不实施自动采集** | `docs/XHS-REDNOTE-SAFE-ARCHITECTURE-V2-*`、`app_evidence.py`（App Evidence=1.0.0-shadow） | 仅在预检 capability 项断言「研究/shadow 不得标记为自动生产」，不写任何采集/逆向/抓包 | **RESERVED（规划门禁已建，自动采集不实施）** |
| ④ Evidence 证据链 | 采集→清洗→判断→风险→报告全过程可追溯 | `docs/audit_evidence/`、`app_evidence.py`（App 端证据采集，非运行证明） | 本轮先交付**启动运行证明 Attestation**（落 `data/security/`，脱敏、可回溯） | **PARTIAL**：启动证据 COMPLETED；逐业务阶段(stage)链路证据预留接口，后续随采集/报告节点接入，不在本轮伪造完成度 |

> 越权约束：DCC / SICI / AI-D 的工单不在本仓处理，本轮零改动。

## 2. Effective Rules（本任务生效规则）

1. 默认不阻断现网：预检 `enforce=False` 只记录+打印+写 Attestation；仅当 `ZBC_PREFLIGHT_ENFORCE=1`（CI/Staging/Docker）且存在 P0 时 `SystemExit(3)`。
2. 检查分级：P0 失败=blocker（依赖缺失、跟踪面混入凭证/库、跟踪源码含明文密钥、data 不可写、统一数据入口失效）；P1/P2 失败=warn，放行。
3. 分层判定，避免误报：文件名含 cookie/token 的**源码**（`xhs_cookie_bridge.py`、`cookie_vault.py`）与 CSS 设计 Token（`tokens.css`）路径层放行，由内容层扫描确认无明文；路径层只拦截凭证/数据**载体**（`.env`、`*.db`、`*.pem/*.key`、`cookies.json`、profile 目录文件）。
4. 内容层区分「真实硬编码密钥」与「读取/判断环境变量的代码」（如 `verify_system.py` 读取 `.env` 的检查语句不算泄露）；无捕获值的高特征规则（AKIA…）直接采信。
5. 任何 Attestation / 日志落盘前经 `data_boundary.sanitize_mapping` 脱敏；只记录路径/行号/类型/布尔/计数，**绝不记录 Cookie/Token/密钥值**。
6. 数据库只经 `database.DB_PATH`（支持 `ZBC_DB_PATH` 隔离），新代码不硬编码 `data/monitor.db`。
7. RedNote/XHS：只识别不绕过，不碰验证码/风控/逆向/高频；研究态不得伪装 production。
8. 最小修改：不重写、不删旧、不改业务口径、不改历史数据；无关问题只登记 Problem ID，不顺手改。

## 3. Change Map

### ADD（新增，均为独立模块/测试/文档，零外部新依赖，仅标准库）
- `data_boundary.py`：四数据分区、`assert_no_tracked_credentials()`、`current_db_zone()`、`sanitize_text()/sanitize_mapping()`、`assess()`。
- `runtime_preflight.py`：8 项检查、`run_preflight(enforce=)`、`format_summary()`、Attestation 写入、CLI（`python runtime_preflight.py [--enforce]`）。
- `tests/test_runtime_preflight.py`：24 个用例（脱敏/路径分层/当前仓库放行/真密钥vs代码语境/enforce 阻断/非 enforce 不抛/Attestation 脱敏）。
- 本文档。

### MODIFY（最小接入，2 处，均在 `app.py`）
- import 区：`import security_scanner` 后新增 `import runtime_preflight`（1 行）。
- 启动段（banner 之后、CDP/心跳/`app.run` 之前）：调用 `run_preflight()` 并打印摘要；`except SystemExit: raise`（保留 enforce 阻断语义），其余异常只打印不阻断。

### READ-ONLY（复用，不修改）
`security_scanner.py`、`database.py`、`config.py`、`safety_boundary.py`、`app_evidence.py`、`subject_rules.py`、`risk_engine.py`、`event_graph.py`、`daily_report.py`、`.gitignore`。

### DO NOT TOUCH
生产红线（`SUBJECT_WORDS`/`subject_hit`/`subject_sql_and_values`/`aggregate_events`/`build_daily_report`、`publish_datetime`/`captured_at` 时间口径、历史库与历史 Evidence）、运行中的 8201/8301/9222、采集实现、DCC/SICI/AI-D 仓库。

### 登记但不顺手改（Problem ID → backlog）
- P-ZB-001：`app_evidence.py` 存在硬编码 `data/monitor.db`（同类路径问题，属另一工单，本轮不改）。
- P-ZB-002：根目录 LEGACY/DEPRECATED 脚本与一次性 `check_*.py`（治理另线，不在本工单删除）。

## 4. 测试与真实 Evidence（均在隔离条件下实测）

1. 单元/回归：`pytest tests/test_runtime_preflight.py -q` → **24 passed**。
2. 独立运行：`python runtime_preflight.py` → 总体 **PASS**，P0 阻断=0、警告=0、耗时约 0.9–1.0s；Git 跟踪面 1036 文件无凭证/库、274 个被跟踪代码文件无明文密钥。
3. 精度回归：首跑曾误报 12 个「文件名含 cookie/token 的源码与 CSS 设计 Token」+ 2 处「读 .env 的检查代码」，按 Effective Rule 3/4 修正后归零，且真密钥/真载体仍可被检出（有对应用例）。
4. enforce 开关：干净仓库 `ZBC_PREFLIGHT_ENFORCE=1` 退出码 0（不误阻断）；注入 P0 fail 时 `SystemExit(3)`（单测覆盖）。
5. 真实启动冒烟（隔离副本库 `staging/preflight_smoke.db` + `127.0.0.1:8399` + `--no-scheduler` + `XHS_CDP_URL=''` + `XHS_PRODUCTION=false`）：启动日志打印预检 PASS（934ms）与 Attestation 路径，`GET /healthz` → **200** `{"ok":true,"version":"5.9.9"}`；验证后仅关闭本次进程（PID 已回收），未触碰 8201/8301/9222，临时库/日志已清理。
6. 不泄露验证：`git status --porcelain` 仅 4 个目标文件；`git check-ignore` 确认 `data/security/attestation_latest.json`、`staging/*.db`、`staging/*.log` 均被忽略，不入库。
7. 语法：`py_compile app.py runtime_preflight.py data_boundary.py tests/test_runtime_preflight.py` → COMPILE_OK。

## 5. 回滚

- 代码层：`git revert <Implementation SHA>`；新增模块删除即恢复，`app.py` 仅 2 处接入可直接还原。
- 运行层：默认不阻断，即使模块异常也被 try 包住，不影响现网启动；Attestation 仅写 `data/security/`（已 gitignore），删除无副作用。
- 无数据库结构变更、无数据迁移、无配置删除。

## 6. 后续（不阻塞本工单 Release）

- ZB-EVIDENCE-001 余下：在采集→清洗→主体→风险→事件→报告各节点接入 stage 级证据记录（复用本任务脱敏与 Attestation 落盘器）。
- ZB-REDNOTE-XHS-001：保持研究/shadow，待官方开放能力或人工证据链评审后再议，不进入自动生产采集。
- 统一 `/healthz` 与预检结果联动、Staging/Docker 以 `ZBC_PREFLIGHT_ENFORCE=1` 作为启动闸门（后续 Runtime 工单）。
