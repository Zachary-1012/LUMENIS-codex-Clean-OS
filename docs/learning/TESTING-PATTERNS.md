# TESTING-PATTERNS · 统一测试体系

> 来源：pytest（LR-024，MIT/14.5k★）+ Playwright（LR-014）。目标：一个统一入口跑 L0–L10，结果分级 PASS/FAIL/ENV/GAP/REGRESSION，失败必有 Evidence。

## 1. 统一入口
- Windows：`.\run.ps1 staging`（等价统一脚本）内部顺序：环境检查 → 构建/依赖 → 启动（独立端口/DB/profile）→ 等待 health → smoke → E2E → 产出 Evidence。
- 不再允许十几个零散 `python xxx.py` 启动（LAUNCHERS.md 已盘点，逐步收敛）。

## 2. pytest 分层（与 L0–L10 对应）
- tests/unit：纯函数与红线口径（subject_hit、_subject_sql_and_values、aggregate_events、build_daily_report、publish≠captured）。**红线回归集任何改动必跑**。
- tests/api：Flask test_client，关键路由 200/契约/错误码；异常状态不返回"0 条"。
- tests/db：对**只读副本/Staging 库**断言，绝不连生产库写。
- tests/e2e：Playwright 驱动 8301 Staging，trace + 截图。
- 用 fixture 提供 app/client/临时 db/临时 profile，测试间隔离、可重复。

## 3. Staging 绝对隔离（ZBC-STAGING-RUNTIME）
- 独立端口（8301）、独立 DB（ZBC_DB_PATH 覆盖）、独立 .env、独立日志、独立浏览器 profile、XHS_PRODUCTION=false；**不自动触发真实平台账号行为**，不影响 8201/8200/9222 与临时公网。

## 4. 必测业务场景（对齐采集最终口径 17 项）
正常采集 / NO_NEW_DATA / 网络异常 / Cookie 失效 / NEED_VERIFY / 300012 可观察 / 冷却 / 恢复 / 多平台独立 / Auth 弹窗 / 合法验证入口 / 验证后恢复 / 前端不把异常显示为 0 条 / 调度日志完整 / next_run_at 计算正确。

## 5. 恢复与重启
- L9：杀掉 worker → 看门狗/容器重启 → healthz 恢复 ok；记录前后 PID。
- 回滚演练：git revert + DB 迁移 downgrade（若用 alembic）+ 配置回退，形成可执行回滚记录。

## 6. 覆盖率与门槛
- 红线模块要求高覆盖并设回归门槛；新增功能"无测试不标 ACTIVE"（对应 Feature 全链路 Test/Evidence 列）。
- CI（GitHub Actions）至少跑 L0/L1/L4/L5；E2E 在本地/Staging 跑并归档 trace。

## 7. 不做的事
- 不为测试反复登录真实平台；不连生产库；不用"静态检查通过"替代运行测试；未实测必须显式标"未实测"。
