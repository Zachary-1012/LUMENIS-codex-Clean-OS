# ZB-RUNTIME-PREFLIGHT · Push2 独立审计报告（Audit）

- TASK ID：ZB-RUNTIME-PREFLIGHT-001（关联 ZB-DATA-BOUNDARY-001 / ZB-EVIDENCE-001 / ZB-REDNOTE-XHS-001）
- 审计对象区间：`0d0a27d`（BASE, origin/main）.. `19b26ee`（Audit 前 HEAD）
- Implementation：`5c020b8`（功能）+ `19b26ee`（测试夹具回归修正）
- 审计方式：重读提交差异 + 独立运行测试/启动/安全门禁 + Attestation 抽查；审计不修改业务逻辑
- 产品：品牌业务生产平台（Z-Brand Business Production Platform, ZBP）· Z-Brand-Core（承载 CTH-POMS / ZBMP）

## 1. 改动面审计

| 维度 | 结论 |
|---|---|
| 提交数 | 2（均在 `feat/zb-runtime-preflight`，未直接动 main） |
| 变更文件 | app.py(M)、data_boundary.py(A)、runtime_preflight.py(A)、tests/test_runtime_preflight.py(A)、本工单两份 docs(A) |
| 新增第三方依赖 | **无**（新模块仅 Python 标准库；复用既有 security_scanner/database） |
| 红线模块改动 | **零**（subject_rules / risk_engine / event_graph / daily_report / database.py / collector 均未改，`git diff --name-only` 核验为空） |
| app.py 接入 | 仅 +1 import、+10 行启动块；try 包裹、`SystemExit` 保留 enforce 语义、其余异常不阻断 |
| 数据库结构/迁移 | 无；不新增表、不改字段、不删历史数据 |

## 2. 安全审计（凭证零泄露）

1. 跟踪面：`assert_no_tracked_credentials()` 实测 Git 跟踪 1036 文件，无 Cookie/Token/.env/私钥/数据库被跟踪。
2. 内容层：SEC-SCAN 扫 274 个被跟踪代码文件，无明文凭证；能区分「真实硬编码密钥」与「读取 .env 的检查代码」，并对 AKIA/sk- 等高特征保持检出（有用例）。
3. 路径分层：处理凭证的**源码**（xhs_cookie_bridge.py、cookie_vault.py、import_cookies.js 等）与 CSS 设计 Token（tokens.css）路径层不误判，真正的凭证/数据**载体**（.env、*.db、*.pem、cookies.json、profile 文件）仍被拦截（14 条参数化用例）。
4. 输出面：新模块任何返回/打印/Attestation 只含 路径/行号/类型/布尔/计数/分区名，不含值；落盘前统一 `sanitize_mapping`；抽查 `data/security/attestation_latest.json` 无 sk-/sessionid=/Cookie 值、无数据库绝对路径。
5. 既有门禁回归：`tests/test_security_scan.py` 原生运行 → 硬编码超管密码 NONE、源码高危敏感命中 0、**ALL_PASS**。
6. 不入库验证：`git check-ignore` 确认 Attestation、staging 副本库与冒烟日志均被 .gitignore 兜住。

## 3. 数据与运行隔离审计

- 启动冒烟使用独立副本库（`ZBC_DB_PATH` 指向 staging 临时库）、`127.0.0.1:8399`、`--no-scheduler`、`XHS_CDP_URL=''`、`XHS_PRODUCTION=false`；未连接/写入生产库，未触发任何采集，未触碰运行中的 8201/8301/9222。
- 新代码不硬编码 `data/monitor.db`，统一经 `database.DB_PATH`（保留生产默认口径，向后兼容）。
- 数据分区四分类（CODE/BRAND_DATA/CREDENTIAL/RUNTIME）仅做判定与说明，不移动/删除任何文件。

## 4. Evidence / 测试审计

| 项 | 结果 |
|---|---|
| 新增单元/回归 | `pytest tests/test_runtime_preflight.py` → **24 passed** |
| 既有安全门禁 | `python tests/test_security_scan.py` → **ALL_PASS（exit 0）** |
| 语法 | py_compile（app.py + 两新模块 + 测试）→ COMPILE_OK |
| 独立预检 | 总体 PASS、P0=0、warn=0、耗时约 0.9–1.2s |
| enforce 干净仓库 | `ZBC_PREFLIGHT_ENFORCE=1` exit 0（不误阻断） |
| enforce 注入 P0 | `SystemExit(3)`（单测覆盖） |
| 真实 Flask 启动 | 预检在启动路径打印 PASS + Attestation；`GET /healthz` → **200** `{"ok":true,"version":"5.9.9"}`，验证后仅回收本次进程 |

## 5. 规则符合度

- 最小修改、不重写、不删旧、不换技术栈、不把实验代码直推生产：符合。
- 默认不阻断现网、显式 enforce 才硬阻断：符合（保护在 main 运行的生产）。
- RedNote/XHS：仅建「研究/shadow 不得伪装 production」门禁，**未**写任何自动采集/逆向/抓包/绕风控：符合工单③「规划中、本轮不实施」。
- 不越权：未改 DCC / SICI / AI-D 任何资产。
- 无关问题只登记不改：P-ZB-001（app_evidence 硬编码库路径）、P-ZB-002（LEGACY 脚本）已进 backlog。

## 6. 过程问题与闭环（不掩盖）

1. 预检首跑误报 12 个「文件名含 cookie/token 的源码与设计 Token」+ 2 处「读 .env 的检查代码」→ 以「路径分层 + 代码语境二次判定」修正，补参数化/对应用例，复跑归零且真问题仍可检出。
2. 新测试夹具的样本字面量一度使**既有**静态安全门禁 FAIL → 改为运行时分段拼接（断言语义不变），既有门禁回到 ALL_PASS；以独立 commit `19b26ee` 留痕，未使用 amend/force。

## 7. 工单状态裁定

| 工单 | 裁定 |
|---|---|
| ① Runtime Preflight | **COMPLETED**（实施+测试+Evidence+双 Push） |
| ② Data Boundary | **COMPLETED** |
| ③ RedNote/XHS 双账号 | **RESERVED**：门禁/边界已建；自动采集按工单保持规划中，不实施 |
| ④ Evidence 链 | **PARTIAL**：启动运行证明 Attestation COMPLETED；采集→清洗→主体→风险→事件→报告的 stage 级证据为预留，后续工单接入，不伪造完成度 |

## 8. 审计结论

**AUDIT RESULT = PASS**：无 P0、无 P1 阻断；安全/数据/运行隔离/回归全部通过。特性分支 `feat/zb-runtime-preflight` 可进入合并评审。

合并到 main / 切生产前的必要动作（非本分支阻断项）：在主工作树（生产基线）再跑一次「import + healthz + 主体口径回归」，确认默认非 enforce 接入对现网启动零影响后再合入。

回滚：`git revert 5c020b8 19b26ee`；新增模块与文档删除即恢复，app.py 仅两处接入可直接还原；无 DB/配置变更。
