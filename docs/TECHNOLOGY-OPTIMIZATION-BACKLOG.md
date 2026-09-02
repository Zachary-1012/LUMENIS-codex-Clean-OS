# TECHNOLOGY-OPTIMIZATION-BACKLOG（技术最优解待办）

> 2026-08-31，依据 docs/learning/ 33 条 GitHub 一手研究（star/license 为 08-31 API 实测）。原则：**不因「新技术」换技术**；候选必须更稳/更轻/可回滚/与现栈兼容，且先 Staging 验证。现栈结论：Flask + SQLite + Playwright + APScheduler + 原生 JS/Jinja **保持不换**。
> 每项字段：当前方案 / 候选 / 为什么更好 / 性能收益 / 稳定性收益 / 复杂度变化 / 迁移成本 / 风险 / 现在是否做。

## P0 — 上线前必须处理（不是换栈，是把验证/运行底座补齐）
### T-P0-1 统一可重复测试入口（关联 GAP-01/02/18）
- 当前：36 个 test_ 仅 5 个规范 pytest（本轮实测 50 passed），31 个脚本；`pytest tests` 被顶层 sys.exit 打成 INTERNALERROR。
- 候选：pytest 为唯一入口（pytest-dev/pytest MIT 14462★，已在用），脚本迁 scripts/ 或加 test_ 函数；分层 L0 Syntax→L1 Import→L2 Startup→L3 Health→L4 API→L5 DB→L6 Page→L7 E2E→L8 Browser→L9 Restart→L10 Regression。
- 为什么：Release Gate 需要一条命令产出可归档证据。性能：无；稳定性：高（回归可重复）；复杂度：下降（入口统一）；迁移成本：中（改 31 个脚本形态，不改业务）；风险：低（只动测试）。
- **✅ 已落地（2026-09-03，ZELL 审计实证）**：pytest.ini 已配 GAP-01 统一入口（testpaths=tests / python_files=test_*.py / python_functions=test_*），tests/conftest.py 有 pytest_ignore_collect 自动跳过纯脚本式；全量回归 400 passed 一次命令产出可归档证据。INTERNALERROR 历史问题已消除（collect + 全量实测均通过）。**状态：✅ 完成。**

### T-P0-2 红线 Owner 函数级直接单测（关联 GAP-02）
- 当前：subject_hit 有 e2e 覆盖；根 risk_engine / aggregate_events / build_daily_report 仅集成级。
- 候选：纯函数 pytest 用例 + 黄金样例（含 publish_datetime/captured_at、主体边界、空输入、300012）。
- 收益：红线改动秒级回归；复杂度略增（只加测试）；迁移成本低；风险无（只读断言）。
- **✅ 已落地（2026-09-03，ZELL 审计实证）**：tests/test_redline_units.py（pytest.mark.redline）已覆盖 subject_hit 黄金样例（正向/跨城同名一票否决/混合优先/空输入/五字段/大小写）、_subject_sql_and_values 结构自洽与参数一致、subject_hit_note/canonical_text、risk_engine.build_daily_report 入口委托稳定；另有 tests/test_subject_redline.py（23 项脚本断言）+ test_subject_dual_dimension.py。**状态：✅ 完成。**

### T-P0-3 保持现栈的明确决定（防反复）
- Flask（BSD,72k★）/SQLite/APScheduler（MIT 7619★）/Playwright（Apache-2.0 14965★）继续；**显式拒绝**在此阶段迁移 FastAPI/Django/PostgreSQL/React/Celery/Scrapy。理由：迁移风险远大于收益，当前目标是稳定上线。**现在做：记录为架构决定（ADR），不写迁移代码。**

## P1 — 建议处理（显著提升稳定性/安全/可维护）
### T-P1-1 Windows 生产 WSGI：waitress
- 当前：Flask dev server / 看门狗直接拉起。候选：Pylons/waitress（1598★，纯 Python、**Windows 可用**）。为什么：gunicorn(10663★)/supervisor(9111★)**不支持 Windows**，不能作为本机生产方案。性能：中；稳定性：高（成熟多线程 WSGI）；复杂度：低；迁移成本：低（改启动命令）；风险：低。**现在做：已落地（可配置化 ZB_WSGI=waitress，staging 8305 已验证 healthz 200，默认 Flask 零影响，可回滚）。上 Linux 云时再评估 gunicorn。**

### T-P1-2 网络/外部调用退避：tenacity（与 litl/backoff 二选一）
- 当前：自写重试。候选：jd/tenacity（Apache-2.0 8769★）统一退避/熔断前退避。收益：避免 NETWORK_ERROR 连续撞击；复杂度下降；成本低；风险低。**现在做：已落地（collector.py _cdp_online 指数退避，可选依赖缺省回落，单测通过，全量回归 479 passed）。**

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
- 候选：每日 VACUUM INTO 到异盘/NAS + 恢复演练；metric 时序考虑独立 DB(attach)。
- 已落地（部分）：scripts/backup_db.py 增强——sqlite backup API 在线一致性备份 + quick_check 完整性校验（校验失败删除假备份）+ 锁定异常才 fallback 文件拷贝 + 保留策略；新增 tests/test_backup_db.py 5 用例。**状态：✅ 备份校验已落地；VACUUM INTO/异盘/恢复演练仍为待办（P2 观察）。**
### T-P0A-3 CDP/沙箱/绑定攻击面收敛
- 当前：9222/9223 CDP 无鉴权、dev_exec 沙箱弱、8201 若绑 0.0.0.0 可远程触达。
- 候选：确认全部绑 127.0.0.1 + 防火墙规则 + dev_exec 白名单。**现在做：否（先核验实际绑定，再登记结论）。**


- **核验结论（2026-09-03，只读审计）：安全边界已达标，无需施工。** ①9222/9223 CDP 均已绑 127.0.0.1（不暴露网络）；②核心数据 API(/api/data/notes、/api/metric-trend 等)未认证 401；③v4 独立 token/session 认证（登录/过期/API Key 管理完整）；④dev_exec 三入口统一闸门 ZBC_DEV_EXEC 默认0禁用 + 危险构造拦截（GAP-04 已收口）；⑤Windows 防火墙三档全开。8201 绑 0.0.0.0 为设计（支持局域网/手机访问 v4 控制台），若改为纯单机使用可考虑绑 127.0.0.1（配置决策，未动）。
### T-P0A-4 生产进程链双层冗余观察（登记不施工）
- 现象：start_production 幂等拉起后，进程树呈 supervisor→supervisor→app→app 双层嵌套（不同批次均复现），但 healthz/接口全 200、功能正常。
- 判断：非错误、不影响功能；疑似 run_supervised 守护链历史叠加或 app 内多进程 exec。需一次专门核实再收敛为单链。
- **现在做：否（登记观察，避免反复重启中断生产）。**

## 结论
- 当前**没有任何一项要求更换核心技术栈**；P0 全部是「测试/证据/红线」底座，P1 是低风险增强，且都可在不动生产主链前提下旁路→Staging→灰度。
- 推荐落地顺序：T-P0-1/2 → T-P1-1(waitress,Staging) → T-P1-2(tenacity) → T-P1-3(Alembic Staging baseline) → 其余随 Release 节奏。

### T-P0B-2 AI 网关 intelligence 深度审查（智谱 glm-5.3，2026-09-03，per_call 1 次）
- **发现 P1 bug（已修复）**：`_provider_config` 中 `AI_PROVIDER=glm` 时 `configs[requested]` KeyError（configs 无 'glm' 键），且发生在 `_chat` 的 try 块外→直接崩溃而非降级 rule。已修复（lookup_key 映射 'glm'→'zhipu'）+ 4 个回归测试。
- **加固（已修复）**：`model.startswith('glm-5.3')` 大小写敏感→`.lower()`；glm-5.3-flash 变体正确跳过 thinking。
- **观察项（未改，登记）**：①glm-5.3 变体用 startswith 前缀匹配会 over-match（glm-5.30 等），建议未来改显式集合/环境变量；②未来 glm-5.4 若也是始终思考需更新集合；③reasoning_content 回退的 CoT 可能不是合法 JSON（下游解析风险）；④qwen/deepseek 的 reasoning 模型未单独处理 thinking。
- **沉淀**：`docs/learning/P0B2-AI-GATEWAY-REVIEW-20260903.md`
- **状态**：P1 bug 已修 + 测试；观察项登记。**现在做：修复完成。**

### T-P0C-1 采集链合规+稳定性深度审查（智谱 glm-5.3，2026-09-03，per_call 1 次）
- **结论**：时间模型/主体过滤/熔断联动/合规边界 4 维核实——**红线均未弱化**（智谱"疑点"多为证据边界，非真实 bug）：
  - 时间模型：captured_at 在 insert_note 有 `or now` 兜底（database.py:420），publish_date 独立来自平台 → 无混淆；但采集层 _norm_cdp_note 原不显式传 captured_at，依赖下游隐式兜底。
  - 主体过滤：app.py:730 → ai_analyzer.verify_taikoo_location → **subject_hit() 硬规则优先**（ai_analyzer.py:141），AI 仅增强 → 红线未弱化。
  - 熔断联动：RiskEngine→CollectorGuard→AdaptiveRateLimiter 链路完整，恢复安全（on_success 收敛10%非立即全速）。
  - 合规：六态归一化 + 硬信号分类（BLOCKED/AUTH_REQUIRED/NEED_VERIFY），不绕过风控。
- **加固（已落地）**：collector.py `_norm_cdp_note` 显式落 `captured_at`（datetime.now），使双时间铁律在采集层即明确，不依赖下游兜底；新增 tests/test_collector_dual_time.py 3 用例（双时间分离/publish缺失/字段透传）。
- **观察项（未改，登记）**：①EMPTY 空结果走 record_success 让风险分衰减，无法区分"真无内容"与"软风控空响应"，软空响应可能提前解除熔断；②RiskEngine 熔断未写入 limiter.force_pause（联动单向），跨轮次依赖自身持久化状态；③冷却到期无 half-open 探测（直接按 interval 发首请求，可接受非最优）。
- **沉淀**：`docs/learning/P0C-COLLECTOR-REVIEW-20260903.md`
- **状态**：✅ 加固已落地；观察项登记。**现在做：完成。**

### T-P0C-2 UI 设计系统一致性审查（智谱 glm-5.3，2026-09-03，per_call 1 次）
- **结论**：审查 ZBIP 脱敏设计文档 vs zbip-tokens.css 一致性，发现 **8 处文档/token 不一致 + 2 个 token 缺口**。
- **已收敛（纯文档/增量，不推翻）**：
  - 脱敏文档 8 处修正使其与 token 完全一致：语义色值（Success #16A34A 等 600 级深色，对比度更好）、三层语义（fg/bg/border）、主文本角色映射（--zb-text=stone-900）、圆角（--zb-r-md=6px 按钮）、主按钮近黑纯色（非渐变）、状态点发光歧义消除、动效唯一权威曲线（emil-out/inout/drawer，禁 ease-in）。
  - zbip-tokens.css 追加 2 个缺口 token：`--zb-icon-size-xl`(28px 大彩色语义icon) + `--zb-status-dot/status-dot-lg/status-glow`（状态点签名）。
- **观察项（登记，未改）**：①动效三套曲线（basic/spring/emil）并存有开发者混用风险，建议后续收敛到 emil 权威+旧变量标记 deprecated；②语义色 fg 对比度 #16A34A≈3.3:1 对正文临界，图标/状态点可用、正文建议用深一档；③`--zb-ease-in` 定义但禁用，后续可移除或标注 exit-only。
- **沉淀**：`docs/learning/P0C-UI-DESIGN-REVIEW-20260903.md`
- **状态**：✅ 已收敛；观察项登记。**现在做：完成。**
