# TECHNOLOGY-OPTIMIZATION-BACKLOG（技术最优解待办）

> 2026-08-31，依据 docs/learning/ 33 条 GitHub 一手研究（star/license 为 08-31 API 实测）。原则：**不因「新技术」换技术**；候选必须更稳/更轻/可回滚/与现栈兼容，且先 Staging 验证。现栈结论：Flask + SQLite + Playwright + APScheduler + 原生 JS/Jinja **保持不换**。
> 每项字段：当前方案 / 候选 / 为什么更好 / 性能收益 / 稳定性收益 / 复杂度变化 / 迁移成本 / 风险 / 现在是否做。

## P0 — 上线前必须处理（不是换栈，是把验证/运行底座补齐）
### T-P0-1 统一可重复测试入口（关联 GAP-01/02/18）
- 当前：36 个 test_ 仅 5 个规范 pytest（本轮实测 50 passed），31 个脚本；`pytest tests` 被顶层 sys.exit 打成 INTERNALERROR。
- 候选：pytest 为唯一入口（pytest-dev/pytest MIT 14462★，已在用），脚本迁 scripts/ 或加 test_ 函数；分层 L0 Syntax→L1 Import→L2 Startup→L3 Health→L4 API→L5 DB→L6 Page→L7 E2E→L8 Browser→L9 Restart→L10 Regression。
- 为什么：Release Gate 需要一条命令产出可归档证据，现状无法做到。性能：无；稳定性：高（回归可重复）；复杂度：下降（入口统一）；迁移成本：中（改 31 个脚本形态，不改业务）；风险：低（只动测试）。**现在做：是（上线前）。**

### T-P0-2 红线 Owner 函数级直接单测（关联 GAP-02）
- 当前：subject_hit 有 e2e 覆盖；根 risk_engine / aggregate_events / build_daily_report 仅集成级。
- 候选：纯函数 pytest 用例 + 黄金样例（含 publish_datetime/captured_at、主体边界、空输入、300012）。
- 收益：红线改动秒级回归；复杂度略增（只加测试）；迁移成本低；风险无（只读断言）。**现在做：是。**

### T-P0-3 保持现栈的明确决定（防反复）
- Flask（BSD,72k★）/SQLite/APScheduler（MIT 7619★）/Playwright（Apache-2.0 14965★）继续；**显式拒绝**在此阶段迁移 FastAPI/Django/PostgreSQL/React/Celery/Scrapy。理由：迁移风险远大于收益，当前目标是稳定上线。**现在做：记录为架构决定（ADR），不写迁移代码。**

## P1 — 建议处理（显著提升稳定性/安全/可维护）
### T-P1-1 Windows 生产 WSGI：waitress
- 当前：Flask dev server / 看门狗直接拉起。候选：Pylons/waitress（1598★，纯 Python、**Windows 可用**）。为什么：gunicorn(10663★)/supervisor(9111★)**不支持 Windows**，不能作为本机生产方案。性能：中；稳定性：高（成熟多线程 WSGI）；复杂度：低；迁移成本：低（改启动命令）；风险：低。**现在做：Staging 验证后做；上 Linux 云时再评估 gunicorn。**

### T-P1-2 网络/外部调用退避：tenacity（与 litl/backoff 二选一）
- 当前：自写重试。候选：jd/tenacity（Apache-2.0 8769★）统一退避/熔断前退避。收益：避免 NETWORK_ERROR 连续撞击；复杂度下降；成本低；风险低。**现在做：是（仅网络层，不碰平台风控决策）。**

### T-P1-3 可回滚 DB 迁移：Alembic
- 当前：51 表 create-if-not-exist，无版本化迁移。候选：sqlalchemy/alembic（MIT 4357★）。收益：schema 变更可追可回滚；复杂度上升（引入迁移链）；成本：中（先对 Staging 副本 autogenerate baseline，绝不对生产库重建）；风险：中（必须向后兼容、先备份）。**现在做：先 Staging baseline，生产切换走 Gate（关联 GAP-13）。**

### T-P1-4 结构化日志/可观测：structlog → Prometheus
- 当前：print/GBK 日志为主。候选：hynek/structlog（4937★）先统一结构化字段，后续 open-telemetry(2607★)/prometheus_client(4363★) 暴露 /metrics。收益：排障与「为什么没采集」可追溯；复杂度中；成本中；风险低（先只加不改日志消费）。**现在做：structlog 可做，OTel/Prom 观察。**

### T-P1-5 自身 API 限流：slowapi
- 当前：自实现安全。候选：laurentS/slowapi（MIT 2051★，Flask 适配）保护自身公网 API。收益：公网暴露面防刷；复杂度低；成本低；风险低。**现在做：公网固定化时一起做。**

### T-P1-6 文件变更触发自动版本保存：watchdog
- 当前：定时巡检 + 手动。候选：gorakhargosh/watchdog（Apache-2.0 7404★）监听源码变更触发版本中心快照。收益：版本闭环更及时；复杂度低；成本低；风险低（只触发 commit，不自动部署）。**现在做：修复 GAP-15 后做。**

## P2 — 后续优化
| ID | 当前 | 候选(参考案例) | 收益 | 复杂度 | 成本 | 风险 | 现在做 |
|---|---|---|---|---|---|---|---|
| T-P2-1 | 学习/语义检索靠 SQL like | asg017/sqlite-vec(Apache,8061★) 零服务向量扩展 | AI 检索增强、不引入独立向量库 | 中 | 中 | 中(扩展装载) | 评估后试点 |
| T-P2-2 | 环境复现靠口头 | astral-sh/uv(Apache,89277★) 锁定依赖 | 可重复构建 | 降 | 低 | 低 | 可做 |
| T-P2-3 | 浏览器 Playwright+Selenium 并存 | Playwright 为主，Selenium 经回归后退(0 真 import) | 去冗余 | 降 | 中 | 中 | 按 GAP-19 门槛 |
| T-P2-4 | 采集队列自管 | 参考 apify/crawlee(Apache,9479★) RequestQueue/自适应限速**思想**（不引依赖、不抄码） | 拟人化/队列稳 | 中 | 中 | 中 | 学习模式，不引包 |
| T-P2-5 | 设计 token 散落 | 参考 amzn/style-dictionary(Apache,4793★) 三层 token **思想**，用原生 CSS 变量实现 | UI 单一真相 | 降 | 低 | 低 | UI 施工时 |
| T-P2-6 | Evidence 无落库 | 参考 in-toto/slsa 证据结构，自建轻 Evidence 表 | 证据链 | 中 | 中 | 低 | 随 GAP-08 |
| T-P2-7 | 变更靠口头 | changesets(MIT,12344★) 变更单思想 + ADR(joelparkerhenderson 16778★) | 变更可追 | 降 | 低 | 低 | 可做 |

## P3 — 观察 / 暂不采用（明确拒绝，防反复讨论）
- **Celery（28842★）**：需 broker/重运维，单机场景 APScheduler 足够 → 不采用。
- **Nx（29285★）**：JS monorepo 编排，本项目 Python 单体 → 不采用。
- **Scrapy（64136★）**：重框架、与真人 CDP 路线冲突 → 不采用（仅学架构）。
- **独立向量库（如独立服务）**：当前量级 sqlite-vec 足够 → 不采用。
- **Backstage 本体（34283★）**：重平台，只借 Catalog 模型思想 → 不部署。
- **tree-sitter（26804★）**：代码图谱当前 pydeps(2105★,只读工具)+静态脚本足够 → 观察。
- **circuitbreaker 库（523★）**：现有 collector_guard 已实现三态，命名对齐即可，不新增依赖 → 不采用。
- **gunicorn/supervisor**：Windows 不可用 → 本机不采用（Linux 云再议）。

## P0-A 补充：智谱旗舰工程评审（2026-09-03，glm-5.3，per_call 1 次）
> 来源：docs/learning/ZHIPU-ENGINEERING-REVIEW-20260903.md。以下为「登记不施工」项，落地前需回归通过、生产窗口可控、走最小补丁。
### T-P0A-1 熔断状态崩溃持久化（生产安全基线）
- 当前：RiskEngine 全部状态内存态（score/opened_at/half_open/recovered_at），进程重启即丢→冷却契约违约（重启即恢复全速采集），风控风险。
- 候选：可选 state_file 持久化（同 checkpoint.py 模式，构造传参默认关闭），恢复时重建 opened_at/剩余冷却。
- 为什么：熔断是风控最后防线，跨重启必须连续。性能：无。稳定性：高。复杂度：低（可选参数+落盘）。迁移：低（生产仅 collector.py:90 一处实例化）。风险：需避免恢复后误判时间窗。**状态：✅ 已落地（3c9bf4c，2026-09-03）。**
### T-P0A-2 SQLite 备份与写放大治理
- 当前：单库 54 表 + 时序快照同库，无定期 VACUUM INTO 备份，RPO/RTO 未定义；Windows 文件锁下拷贝不可靠。
- 候选：每日 VACUUM INTO 到异盘/NAS + 恢复演练；metric 时序考虑独立 DB(attach)。**现在做：否（登记）。**
### T-P0A-3 CDP/沙箱/绑定攻击面收敛
- 当前：9222/9223 CDP 无鉴权、dev_exec 沙箱弱、8201 若绑 0.0.0.0 可远程触达。
- 候选：确认全部绑 127.0.0.1 + 防火墙规则 + dev_exec 白名单。**现在做：否（先核验实际绑定，再登记结论）。**

### T-P0A-4 生产进程链双层冗余观察（登记不施工）
- 现象：start_production 幂等拉起后，进程树呈 supervisor→supervisor→app→app 双层嵌套（不同批次均复现），但 healthz/接口全 200、功能正常。
- 判断：非错误、不影响功能；疑似 run_supervised 守护链历史叠加或 app 内多进程 exec。需一次专门核实再收敛为单链。
- **现在做：否（登记观察，避免反复重启中断生产）。**

## 结论
- 当前**没有任何一项要求更换核心技术栈**；P0 全部是「测试/证据/红线」底座，P1 是低风险增强，且都可在不动生产主链前提下旁路→Staging→灰度。
- 推荐落地顺序：T-P0-1/2 → T-P1-1(waitress,Staging) → T-P1-2(tenacity) → T-P1-3(Alembic Staging baseline) → 其余随 Release 节奏。
