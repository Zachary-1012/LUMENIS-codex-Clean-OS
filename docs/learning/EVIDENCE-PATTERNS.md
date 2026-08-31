# EVIDENCE-PATTERNS · 证据与可验证机制

> 来源：in-toto attestation / SLSA 分级 / Playwright trace 思想（LR-003/004/014）。目标：每个"完成/DONE"都有可回放证据，禁止"写完=完成"。

## 1. 统一 Evidence 记录结构
建议字段（对应已有表 `app_evidence_records`，先对齐语义、不改表结构）：
`id, project(ZBP/DCC/SICI), product(CTH/ZBMP), feature_id, asset_id, commit, version,
env(local/staging/prod), level(L0-L10), test_name, result(PASS/FAIL/ENV/GAP/REGRESSION),
started_at, finished_at, inputs, outputs, expected, actual, log_path, screenshot, trace,
api_request, api_response, db_before, db_after, root_cause, resolution, created_at`
- 思想对应 in-toto：step（哪一步）+ materials（输入材料/commit）+ products（产物/响应/快照）+ 签名责任（谁/哪个任务）。

## 2. L0–L10 每级应产出的最小证据
| 级别 | 动作 | 最小证据 |
|---|---|---|
| L0 Syntax | py_compile/编译 | 通过/报错文件行 |
| L1 Import | import 全部模块 | 失败堆栈 |
| L2 Startup | 起 app | 启动日志 + 监听端口 |
| L3 Health | GET /healthz | 响应 JSON |
| L4 API Smoke | 关键 GET/POST | 请求+响应+状态码 |
| L5 DB | 只读关键表计数 | 前后计数、只读证明 |
| L6 Page | 页面渲染 | DOM snapshot/截图 |
| L7 E2E | 业务闭环 | Playwright trace + 截图 |
| L8 Browser | 9222/CDP 会话 | CDP target 列表、不读 cookie |
| L9 Restart | kill→自愈 | 重启前后 PID/healthz |
| L10 Regression | 红线回归 | 主体口径/时间口径/报告数值对比 |

## 3. 失败必留证据链（Playwright 模式）
- screenshots/、trace/、logs/、api/、db/、runtime/ 分目录，按 `taskid-level-timestamp` 命名；失败保留现场，成功可精简。
- Playwright：`--trace on`、video 按需、screenshot only-on-failure；trace.zip 可回放每步（LR-014）。

## 4. "事实 vs 声明"分离（防虚报）
- README/文档写"完成"不算证据；必须有对应 result=PASS 的 Evidence 记录。
- AI 产出单独标 model/prompt_version/confidence/human_override，不与系统事实混存。
- 采集异常（验证码/300012/IP风险/登录失效）必须落真实状态证据，**禁止以 0 条充当结果**。

## 5. Release Gate 证据清单（对齐任务书）
无 P0；核心业务/DB/API/页面/E2E/Browser/Restart/Backup/Rollback/Staging 全部 PASS 且证据可回放，才允许 PRODUCTION READY；P2/P3 不阻塞上线。

## 6. 统一 Evidence 库（三仓共用结构，各自独立存储）
- ZBP：运行/测试证据；DCC：Gate/Audit 证据；SICI：研究 VERIFIED 证据。结构一致、仓库独立，不做跨仓运行时依赖。
