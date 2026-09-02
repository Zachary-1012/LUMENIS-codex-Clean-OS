# FEATURE-GAP-REGISTER（功能缺口总账）

> 2026-08-31，配合 FEATURE-FINAL-VERIFICATION-MATRIX。原则：宁可多记一个 Gap，不制造一个虚假 ACTIVE；只登记，本轮不改生产代码。
> 严重程度：P0 阻塞生产/数据正确性；P1 阻塞 Release Gate / 安全 / 验证闭环；P2 架构与可维护；P3 文档/口径/清理。
> 「阻塞上线」指阻塞 CTH-POMS 正式 Production Release；「阻塞 UI」指阻塞 UI 一次性施工。

| Gap ID | Feature | 问题（实测事实） | 级别 | 影响 | 原因 | 建议 | 阻塞上线 | 阻塞UI | 需代码 | 需测试 | 需Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GAP-01 ✅RESOLVED(2026-09-01) | 全局/测试体系 | ~~统一 pytest tests INTERNALERROR~~ **已建统一入口：test_api_smoke 转规范用例；conftest 智能忽略纯脚本式（无 def test 不 import 执行）；新增 pytest.ini + tests/run_all.py 分层入口（默认规范用例，--scripts 子进程隔离跑脚本）**；`pytest tests` 现 **110 passed** 不再炸 | P1→已闭 | 统一入口已打通 | 顶层 sys.exit/脚本副作用 | 后续逐步把脚本式迁为 def test（与 GAP-18 一并） | 否 | 否 | 是(已做) | 是(110✓) | 是 |
| GAP-02 🚧部分关闭(2026-09-01) | SUBJ/EVT/RISK/RPT 红线 | **新增 tests/test_redline_units.py 19 用例（函数级直测 subject_hit 跨城同名一票否决/多字段/大小写、_subject_sql_and_values 占位符↔参数自洽/alias、日报入口契约）全过**；aggregate_events 事件聚合已补函数级权威测试（tests/test_event_aggregation_authority 3 测，2026-09-02，见 GAP-23）；build_daily_report 纯函数拆分仍待补 | P1→部分 | 主体口径已有函数级硬证据 | 早期按链路写 | 继续补事件聚合/报告纯函数级（不连库部分） | 否 | 否 | 是(19✓) | 是 | 是 |
| GAP-03 ✅RESOLVED(2026-09-01) | CTH-AUTH-001 | ~~主 SPA static/index.html 未引~~ **Step1 已挂主 SPA 并随 main=`580c2cf` 合并，8301 实测统一弹窗正常**；残余：A/B/C 三分支 E2E 与规范 pytest 未补 | P1→残余P2 | 主 SPA 弹窗缺口已闭 | 已随 UI 合并解决 | 补三分支 E2E/pytest（不再阻塞 UI） | 否 | 否(已闭) | 是(测试) | 是 |
| GAP-04 ✅RESOLVED(2026-09-01) | ZBMP-SETT-001/安全 | ~~三套可执行代码入口并存未收口~~ **已统一走 `_dev_exec_guard`：生产默认 403（含 JS 写 static 分支），仅本地 ZBC_DEV_EXEC=1 放行且拦危险构造；路由保留不删**；新增 test_dev_exec_guard 9 用例 | P1(安全)→已闭 | RCE/持久化注入面已关 | 统一闸门收口 | 后续观察是否彻底退旧路由（当前保留兼容） | 否 | 否 | 是(已做) | 是(9✓) | 是 |
| GAP-05 ✅RESOLVED(2026-09-01,默认shadow) | CTH-SCHED | ~~动态调度仅 shadow 不门控~~ **新增 scheduling/gate.py 三态门控（ZBC_SCHED_GATE_MODE=shadow默认/canary/enforce；shadow 零行为变化、canary 仅门控 ZBC_SCHED_GATE_PLATFORMS 名单、enforce 全门控；只收紧不放松=hard_allow AND decision.allow，不弱化既有熔断；门控器异常 fail-open；非法值回退 shadow；改回 shadow 即回滚）；topic_campaign 触发点已挂 gate**；6 测试全过、全量127 | P1→已闭(默认shadow，灰度/全门控为运维开关，xhs 最后切) | 可灰度可回滚 | 此前固定时钟不看 allow | enforce 全量门控的真实灰度时点待运维按平台逐步开 | 否 | 否 | 是(6✓) | 是 | 是 |
| GAP-06 ✅RESOLVED(2026-09-01) | CTH-SUBJ-002 | ~~双维度列/写入/筛选未贯通~~ **已落地：notes 幂等加 subject_type/content_type 两列（NOTE_MIGRATIONS+migrations/010，纯增量默认空串）；insert_note 经 enrich_note_types 惰性单例标注、失败兜底空串不阻断采集；_apply_filters 固定枚举白名单筛选（拒绝任意列名/非法值、不接受旧 user_type=UGC）；/api/notes 透传 ?subject_type=&content_type=**；tests/test_subject_dual_dimension 6 测过、Staging 副本 957 历史不回填 | P1→已闭 | 双维度贯通且不伤主体口径 | 分类器此前仅 /types 暴露 | 细分内容类型(review/complaint 正文识别)为后续增强，现用 classifier 现有 content_type_hint | 否 | 否(向后兼容) | 是(6✓) | 是 | 是 |
| GAP-07 ✅RESOLVED(2026-09-01) | CTH-EVT | ~~三类四关系仅1条trigger~~ **字典本已齐（3事件类型/4关系）；新增 EventGraph.infer_and_link_relations 双证据保守推断器（时间+标题主题词，先剔除『广州太古汇』全域通用名与摘要样板词，无证据不连边、trigger强因果不自动造、[auto]关系可幂等重算且保留手工）；新增 POST /api/event-graph/rebuild-relations**；Staging 真实16事件得3条有证据并行(IWC/会员/漂亮饭)+原手工trigger，117无证据对不连 | P1→已闭 | 关系可解释、不伪造 | 此前只导节点不建关系 | derive/follow 待跨天强延续真实数据出现自然补全；前端图例已支持四类 | 否 | 否 | 是(5✓) | 是 | 是 |
| GAP-23 ✅RESOLVED(2026-09-02) | CTH-EVT-001/对账GAP-P0-01 | ~~全仓 grep 不到 def aggregate_events，最高保护层误判 MISSING~~ **只读定位：能力未丢，旧名重构更名为 reprocess.build_cross_platform_events（唯一实现，生产链 xhs_cookie_bridge 异步+app.py 两端点+full_refresh 共用，落库 database.upsert_event）；口径健康=只消费 verified、risk 取 max+负面计数、AI 仅 summarize 增强不改风险、发布/采集时间未混**。已恢复受保护兼容名 aggregate_events（转发同一权威、零口径分叉）+3 测锁定 | P0→已闭 | 消除红线函数名缺失隐患 | 重构改名未回写基线 | 最高保护层清单以 build_cross_platform_events 为权威名 | 否 | 否 | 是(薄别名) | 是(3✓) | 是 |
| GAP-24 ✅RESOLVED(2026-09-02) | 对账P1-4/风险权威 | ~~根 risk_engine 声明采集风险权威=RiskEngine，与运行时不符~~ 只读定位：现役熔断=CollectorGuard 七态+AdaptiveRateLimiter（默认启用），RiskEngine 连续分是已实现/已测/未接管备用件。已校正职责声明+3 测锁定归属，现役熔断零改动 | P1→已闭 | 消除文档误导、防误改备用件影响生产 | 重构后声明未随运行时更新 | 连续分未来旁路验证后再接入，不直接替换七态 | 否 | 否 | 否(仅注释) | 是(3✓) | 是 |
| GAP-08 | 全局/Evidence | app_evidence_records 为外部抓取表且 0 行；测试/运行 Evidence 无统一存储与 L0-L10 归档 | P2 | 「跑过/通过」无版本化证据可追 | 未建 Evidence 层 | 建 Evidence 记录(commit/version/result/artifact) | 否 | 否 | 是 | 是 | 是 |
| GAP-09 | CTH-EVT-003 | 负面评审两套 API（/negative/* 与 /negative-review/*+event-review）并存 | P2 | 状态可能双写不一致 | 新旧实现未退 | 定唯一 Owner，另一标 DUPLICATE→回归→退 | 否 | 否 | 是 | 是 | 是 |
| GAP-10 🚧部分推进(2026-09-01) | RPT | 报告多路由（12）+report_center 无路由 **→ 已挂只读旁路 GET /api/v2/report-center/preview（period/brand_mode/日期白名单校验、复用 database 尊重 ZBC_DB_PATH、不写库/不导出/不自动发送、不抢 RPT-001/002 Owner）；Staging cth/zbmp 双模式实测各18节、7测试过**；Word/PDF 导出与自动发送仍旁路未接管、12 旧路由收敛仍待做 | P2 | 标准化报告可读 | 导出接管/旧路由收敛有Owner冲突风险 | 导出(ReportExporter)挂路由前先与 RPT Owner 对齐 | 否 | 否 | 是(7✓) | 是 | 是 |
| GAP-11 | 跨仓/DCC | DCC 本地 77dd1e4 落后远程 023e2ba 27 提交，且脏 package.json/learning-store.js/persistence.js | P2 | 跨仓基线分叉 | 多窗口并行 | 需授权：先审本地 3 处去留→rebase→回 ZBC 升子模块指针 | 否 | 否 | 否 | 否 | 是 |
| GAP-12 | 治理/文档 | 多份并行基线（两份 PRODUCTION_BASELINE、PHASE1 与 UPA-PHASE1、consolidation-001/002） | P2 | 权威顺序易混 | 阶段叠加 | ADR 标注 Superseded，留一份权威 | 否 | 否 | 否 | 否 | 否 |
| GAP-13 | 数据库 | 51 表无可回滚迁移体系（Alembic 未引入） | P2 | schema 变更缺 Gate/回滚 | 一直 create-if-not-exist | Staging 副本先 baseline，再向后兼容迁移 | 否 | 否 | 是 | 是 | 是 |
| GAP-14 | MON-003/RISK-002/SYS-002/SETT | Feature 登记 API 前缀不精确（schedule/circuit/v4 前缀挂载），功能真实存在 | P3 | 文档与路由表对不上 | 蓝图 url_prefix 嵌套 | 校正 Registry 路径表述 | 否 | 否 | 否 | 否 | 否 |
| GAP-15 | CTH-SYS-002 | daily_git_sync.py:72 `current_version` 漏括号，自动提交标题卡 v5.8.9 | P3 | 版本标题不准(不影响运行) | 调用方笔误 | 改 current_version() 并加断言 | 否 | 否 | 是 | 是 | 是 |
| GAP-16 | CTH-SYS-003 | cloudflared 临时域名，未固化固定域名/HTTPS/断线自愈证据 | P3 | 公网地址会变 | 尚未上固定服务器 | 固定域名/隧道开机自启+健康探针 | 否 | 否 | 是 | 否 | 是 |
| GAP-17 | Runtime | 8200 两个重复 app.py 实例（pid 18852/19916） | P3 | 端口/资源重复 | 历史启动残留 | 授权后保留单一实例 | 否 | 否 | 否 | 是 | 是 |
| GAP-18 | 测试体系 | 31 个脚本式文件命名 test_ 但无 def test_，易被误读为「有测试」 | P3 | 假覆盖错觉 | 同 GAP-01 | 与 GAP-01 一并迁移/改名 | 否 | 否 | 是 | 是 | 是 |
| GAP-19 | Runtime/Browser | Selenium 0 真 import 待回归后退；Browser/Scheduler/Collector/AI 重复调用待按需启动验证（只审计不重构） | P2 | 运行时冗余 | 历史并存 | 引用/运行依赖分析→替代验证→回归→退 | 否 | 否 | 是 | 是 | 是 |
| GAP-20 | 工程清理 | .trae-cn IDE 目录忽略确认；根目录 start_*.bat/.bak/日志收敛 | P3 | 仓库噪声 | 长期堆积 | 分批登记后清理，不边开发边删 | 否 | 否 | 否 | 否 | 否 |
| GAP-21 | ZBMP-IMP-001 | importer 3 个 py 存在，但无前端入口/API/专表 | P2 | 有代码易被误判完成 | 后端先行 | UI 占位；补 API/专表后再升 DEVELOPING | 否 | 是(占位) | 是 | 是 | 是 |
| GAP-22 | ZBMP-BRAND-003 | swire_notes 空表，专题在建 | P2 | 功能无数据 | 尚未灌数 | 保留 UI 占位与空态 | 否 | 是(空态) | 否 | 是 | 是 |

## 汇总
- P0=**0**；P1=7（GAP-01/02/03/04/05/06/07）；P2=8（08/09/10/11/12/13/19/21/22 记 9 项，其中 22 偏 P2-P3）；P3=6（14/15/16/17/18/20）。
- 阻塞当前生产运行：无（8201 v5.9.9 在线、红线 50 用例 PASS）。
- 阻塞 UI 一次性施工：仅 **GAP-03 建议作为前置**，GAP-21/22 需在 IA 中占位（不阻塞，占位即可）。
- 阻塞正式 Release Gate：GAP-01/02（自动测试与红线直接证据）、GAP-04（安全收口）应在上线前关闭；GAP-05 门控可上线后按签字灰度。
