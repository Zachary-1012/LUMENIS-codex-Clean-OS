# 线上仓库优化点落实评估清单 V1.0（2026-09-06，不丢任何一项）

> 方法：git fetch 全部分支→盘点101个远程分支→仅6个领先main→排除当前分支与无关研究分支→对3个有价值未合分支(feat/zbc-full-upgrade-v1、feat/lumenis-p0-p1-source-convergence、feat/lumenis-product-convergence)逐项diff本地源码实测。线上main=0dca073，本地=1085104(领先9commit)。

## 一、已落实（线上优化点本地已有，不用动）
| 线上优化点 | 来源分支 | 本地落实证据 |
|---|---|---|
| Repository Registry+Runtime Guardian+PermissionGate+DB空表分类 | zbc-full-upgrade | permission_gate 50文件463处、runtime_guardian.py、repository_registry |
| Collector+Risk+AI+Evidence+Report+Evaluation六阶段审计加固 | zbc-full-upgrade | 各模块齐全，evidence_chain 1167行 |
| PermissionGate接入app.py写操作+Evidence链完善+历史数据导入 | zbc-full-upgrade | 已接入；历史迁移12353条完成 |
| 20+套批量验证测试(permission/runtime_guardian/ui_view_model/evidence_chain/evaluation/collector_audit/risk_audit/report_audit/historical/source_provenance/repository_registry/skill_agent_boundary/code_quality/api_audit/ai_evaluation) | zbc-full-upgrade | 本地tests/共222套，上述15套全部存在且字节数匹配 |
| ui_view_model.py函数驱动可视化(824行) | zbc-full-upgrade | 本地已有824行 |
| 移除auth_recovery_center硬编码个人路径 | product-convergence | 本地grep无D:\C:\Users硬编码 |
| ZBC→OSAI Cross-Core Skill Adapter(只读、OSAI不可用PARTIALLY_CONNECTED、不硬编码路径) | p0-p1-source | lumenis_skill_adapter.py已实现，符合三仓规则(OSAI可调用但非运行时依赖) |
| 6个LUMENIS页面绑定真实API+reports绑daily_reports DB | p0-p1-source | 旧IA页面不恢复；新三域页面真实绑定由前后端契约对账覆盖(进行中) |

## 二、真正遗漏（需补入，3项）
M1. **CI未真正执行pytest**：.github/workflows/platform-verify.yml 当前只 pip install + compileall，缺 `python -m pytest`。需补CI执行pytest(选可在ubuntu-latest无浏览器环境跑的子集，标记需Playwright/DB的测试为本地环境，避免CI假失败)。
M2. **缺test_osai_boundary_audit.py**(347行，OSAI边界与启动审计TEST-01/02/05/06/07/09/10/20)：验证"本仓库独立启动""无OSAI时正常启动""outbox异常隔离""OSAI不能成为启动依赖(源码级import审计)"。从origin/feat/lumenis-p0-p1-source-convergence取文件，适配本地import路径后跑通。
M3. **event_graph.infer_and_persist_relations缺生产状态文档**：线上分支给该函数补了文档说明(O(n²)全量扫描、未接入自动调度、通过POST /api/event-graph/rebuild-relations手动触发、未来接入需try/except隔离+限频+性能压测)。本地函数能力已有，仅补这段文档注释。

## 三、不采纳（有理由）
- p0-p1分支对production/intelligence/operations旧IA模板的UI改动：**不恢复旧UI**，只提取"绑定真实API"逻辑适配到新三域页面；用户明确禁止旧UI带回。
- 线上其余95个分支：均已合入main或无新commit，本地(领先main)已包含。

## 四、补入验证要求
- M1补后CI配置语法校验；pytest选tests/下无浏览器依赖子集先本地跑通再入CI。
- M2取文件后 `python -m pytest tests/test_osai_boundary_audit.py -v` 本地跑通，import错误则适配不删测试。
- M3仅加文档不改逻辑。
- 三项补入后commit push，在本清单标记VERIFIED。
