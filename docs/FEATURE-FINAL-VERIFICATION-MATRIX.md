# FEATURE-FINAL-VERIFICATION-MATRIX（Feature Final Verification 2.0）

> 初版 2026-08-31（main=`af28436`）；**刷新 2026-09-01，main=`580c2cf`（ui/staging-foundation Step1–Step5j 已并入 main，main=staging=origin 三线同点）**。**判定优先级：源码 > DB > Runtime > 测试 > Evidence > 文档。**
> 只读核验脚本：`scripts/inventory/feature_final_verify.py`；测试事实为**真实运行**：合并后规范用例 **80 passed**（test_ai/test_api/test_database/test_e2e/test_llm_gateway 50 + test_runtime_preflight 24 + test_workspace_keys 6），另 `tests/test_css_balance.py` CSS 结构平衡门禁全绿；**2026-09-01 晚统一入口 `pytest tests` = 151 passed（GAP-01 已解，conftest 智能收集纯脚本、pytest.ini/run_all 分层入口）**。
> 8301 合并版实测（ISOLATED_STAGING 副本库，生产 8201 未重启）：Preflight 总体 PASS/P0=0、CTH Home 侘寂壳、ZBMP 密钥门解锁、话题战役 120/6.1w、事件关系 16 节点三列四关系真实渲染、两只只读路由 file-tree/term 命中。
> 关键事实：pytest 可收集的 `test_*.py` 中多数为独立脚本（无 def test_、靠 __main__/sys.exit 运行），统一 `pytest tests` 仍被 `test_api_smoke.py` 顶层 `sys.exit` 打成 INTERNALERROR（**GAP-01 待清**）；`app_evidence_records` 仍 0 行（GAP-08）。
> **2026-09-01 晚二次刷新（main=`9092697`）：P1 全清（GAP-01/02/03/04/05/06/07 均 RESOLVED），统一 `pytest tests` 由 INTERNALERROR 收敛到 151 passed；新增调度三态门控(默认 shadow)、事件关系保守推断、report_center/Global BIL 只读旁路、adapter 韧性层测试、RedNote 策略 SoT。**
> **Status 列保留 FEATURE-REGISTRY 原值，不擅自升降级**；严格 ACTIVE 五要素=代码+Owner+运行路径+测试+Evidence，缺口写入 Gap 列与 FEATURE-GAP-REGISTER。本轮新增条目一律以合并后 main 实测/用例为据，不足五要素者不标 ACTIVE。

## 图例
- Asset：文件/模块真实存在（全部 Y，无 ASSET_MISSING）。API：Y=真实路由命中；`前缀*`=登记前缀不精确但功能在（GAP-14）；-=本就无独立 API。
- Runtime：主链=被 app 主链 import 可达（module_graph app_reachable）；旁路=v4/适配器/新一代未接管；- =无运行进程类。
- Test：**50✓**=被本轮 50 个 PASS 用例直接覆盖；脚=有对应脚本式验证（非 pytest、未统一执行）；无=缺。
- Evidence：**本轮 PASS**=50 用例实测通过覆盖；缺=无统一可归档运行证据（EVIDENCE_MISSING）。

## 全量矩阵（48 条 = 原 34 + 09-01 补登 10 + 09-01 晚补登 4）
| ID | Feature | Product | Asset | Owner | API | DB | UI | Runtime | Test | Evidence | Status | Gap | Risk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CTH-MON-001 | 关键词笔记采集(真人CDP) | CTH | Y | collector.py/xhs_cdp_collector | Y /api/collect* | notes,collection_logs | Y collect | 主链 | 脚(collect_state/collection_full/browser_e2e) | 缺(不能在CI打真实平台,需mock) | ACTIVE | 采集链无规范pytest；当前 BLOCKED 熔断 | 账号/IP 风控(非代码缺陷) |
| CTH-MON-002 | 15周年专题监测 | CTH | Y | topic_campaign.py | Y | topic_campaign_notes(120) | Y 专题页 | 主链 | 脚(test_topic_port) | 缺 | ACTIVE | 缺规范用例 | 窗口至 10-07 |
| CTH-MON-003 | 采集调度(固定→动态) | CTH | Y | platform_adapters/scheduling | 前缀 /api/collect|/api/collect/status/<id>|/api/collect/tasks|/api/collector/browser/start|stop | schedule_decisions | Y console | 旁路(影子) | 脚(test_scheduling) | 影子日志 | ACTIVE(默认shadow) | **GAP-05 已落地(ea3143d)：scheduling/gate.py 三态 shadow/canary/enforce，默认 shadow 零行为变化、只收紧不放松、fail-open、env 回滚；6 测**；灰度时点为运维开关；GAP-14 | enforce 全量门控待逐步开 |
| CTH-MON-004 | 采集健康/六态 | CTH | Y | health_center.py | Y /api/platform-health | collection_logs | Y 健康点 | 主链 | 脚(test_health_center) | 缺 | ACTIVE | 缺规范用例 | 低 |
| CTH-MON-005 | 全网搜索采集 | CTH | Y | web_monitor/v4 adapters | Y /api/web-* | web_*(5表) | Y | 旁路 | 无 | 缺 | EXPERIMENTAL | 无测试 | 中转链稳定性 |
| CTH-SUBJ-001 | 广州太古汇主体过滤🔴 | CTH | Y | subject_rules.py | 内部 | notes.subject_hit | Y | 主链 | **50✓** test_e2e::subject_filter + 脚 redline | **本轮 PASS** | ACTIVE | 可补函数级边界用例 | 红线，禁弱化 |
| CTH-SUBJ-002 | 主体/内容双维度 | CTH | Y | subject_classifier.py | Y /api/subject-classifier/types | 落库列未建 | Y | 旁路 | 50✓(AI/e2e 间接) | 部分 | ACTIVE | **GAP-06 已落库(87274ff)：notes 增 subject_type/content_type 两列(幂等迁移、默认空串不回填)、insert 计算、白名单筛选、/api/notes 透传；6 测**；禁 user_type=UGC | 低 |
| CTH-EVT-001 | 事件聚合🔴 | CTH | Y | aggregate_events() | Y /api/events* | events(427) | Y | 主链 | **50✓** test_e2e::events_aggregation | **本轮 PASS(集成级)** | ACTIVE | GAP-02 缺函数级直接单测 | 红线 |
| CTH-EVT-002 | 事件关系图谱 | CTH | Y | event_graph.py | Y /api/event-graph/* | event_graph_events(16)/relations(1) | Y | 主链 | 无 | 缺 | ACTIVE | **GAP-07 已补(f413548)：infer_and_link_relations 时间+标题双证据保守推断(无证据不连边、trigger 不自动造)+POST rebuild-relations；Staging 16 事件得 3 条有证据并行、117 对不连；5 测** | derive/follow 待真实跨天数据 |
| CTH-EVT-003 | 负面确认/评审 | CTH | Y | events 评审流 | Y negative/event-review | note_review_history(8327) | Y | 主链 | 脚(negative_event_api) | 缺 | ACTIVE | GAP-09 两套并存 DUPLICATE_CANDIDATE | 双写状态不一致 |
| CTH-RISK-001 | 风险判定/等级🔴 | CTH | Y | 根 risk_engine.py | Y /api/risk* | events | Y | 主链 | **50✓** test_e2e::risk_level | **本轮 PASS(集成级)** | ACTIVE | GAP-02 test_risk_engine 实参测 collector_guard，根 risk_engine 无直接单测 | 红线 |
| CTH-RISK-002 | 熔断/冷却/300012 | CTH | Y | collector_guard/xhs_cookie_bridge | 前缀 无独立API(熔断在collector_guard内部, 状态文件xhs_circuit.json) | xhs_circuit(json) | Y | 主链 | 脚(guard_wiring/risk_engine) | 缺 | ACTIVE | GAP-14 登记口径；只识别不破解 | 合规红线 |
| CTH-NOTE-001 | 笔记库/详情/评论/去重 | CTH | Y | database.py+collector | Y notes*/comments* | notes(957) | Y | 主链 | **50✓** test_database 6 用例 | **本轮 PASS** | ACTIVE | — | 低 |
| CTH-NOTE-002 | 空正文 CDP 回填 | CTH | Y | backfill_detail_cdp | - | notes | 预留 | 旁路 | 脚(title_fallback) | 缺 | PLANNED | 253 条待稳定网络 | PLANNED 正确 |
| CTH-RPT-001 | 日/周/月/专题报告🔴 | CTH | Y | daily_report.build_daily_report | Y /api/report* | events,notes | Y | 主链 | **50✓** test_e2e::daily_reports | **本轮 PASS(集成级)** | ACTIVE | GAP-02 build_daily_report 无直接单测(test_report_periods 测 export) | 红线/publish 时间口径 |
| CTH-RPT-002 | 报告导出 pdf/xlsx/docx | CTH | Y | report_export/* | Y | - | Y | 主链 | 无 | 缺 | ACTIVE | GAP-10 多实现待收敛 | 统计必须来自 Owner |
| CTH-AUTH-001 | 统一平台 Session/Auth 恢复 | SYSTEM / C1 C6 F | Y | auth_recovery_center + SYSTEM Browser；`auth_global.js` 仅历史 SPA 证据 | Y `/api/auth-recovery/*` + 平台登录/保活兼容端点 | auth_recovery_tasks（当前过渡表） | **CURRENT FLUTTER UNBOUND**；历史 SPA 挂载不等于当前四端实现 | 后端能力存在，F 统一恢复消费者待绑定 | 当前 scoped Browser/Auth tests PASS；四端 Recovery E2E 未验证 | 历史 8301 弹窗仅 provenance | CODEX_BINDING_REQUIRED | 收敛到 `COLLECTOR-FND-02 PlatformSession` + `COLLECTOR-FND-03 LumenisPlatformRecoverySheet`；QR/Login/VERIFY/BLOCKED 分态并在健康回读后恢复原任务 | 不跳出序境产品；不得暴露 Cookie/CDP/profile；不得把平台连接器恢复误称 LUMENIS 产品登录 |
| CTH-AUTH-002 | 登录/权限/安全问答 | CTH | Y | v4 auth + Basic | Y /v4/auth/* | v4_users/sessions/security_questions | Y | 主链 | **50✓** test_api::TestAuthAPI×2 | **本轮 PASS** | ACTIVE | 三级权限仅 1 owner | 安全 |
| CTH-SYS-001 | 系统健康/看门狗/自愈 | CTH | Y | system_health_api/guardian | Y /healthz,/api/system/health | - | Y | 主链 | **50✓** test_api::System×2 +脚 auto_recovery | **本轮 PASS** | ACTIVE | — | 低 |
| CTH-SYS-002 | 版本中心/Git 自动同步 | CTH | Y | version_center/git_manager | 前缀 /v4/api/status|/v4/api/history|/v4/api/save|/v4/api/push|/v4/api/check|/v4/api/pull|/v4/api/rollback | - | Y | 主链 | 脚(version_api) | 缺 | ACTIVE | GAP-15 标题括号 bug | 低(不影响运行) |
| CTH-SYS-003 | 临时公网隧道 | CTH | Y | tunnel_guardian(cloudflared) | - | - | 无 | 进程 | 无 | 缺 | ACTIVE | GAP-16 域名未固化/无测试 | 公网暴露面 |
| ZBMP-BRAND-001 | 品牌增删/管理 | ZBMP | Y | brand_knowledge_base | Y /api/brand* | brand_knowledge | Y | 主链 | 脚(brand_library,偏 swire) | 缺 | ACTIVE | 缺直接用例 | 低 |
| ZBMP-BRAND-002 | 品牌营销案例库 | ZBMP | Y | case_deep_analysis | Y /api/cases* | case_deep_analysis | Y | 主链 | 脚(brand_library) | 缺 | ACTIVE | 更新/下钻待完善 | 低 |
| ZBMP-BRAND-003 | 太古/怡和专题 | ZBMP | Y | swire_group/swire_brand_mapper | Y /api/swire* | swire_notes(空)/events/projects | Y | 旁路 | 脚(brand_library→swire_group) | 缺 | DEVELOPING | GAP-22 空表 | 在建 |
| ZBMP-COLL-001 | 抖音适配器(XHR) | ZBMP | Y | v4/adapters/douyin.py | registry(无独立REST) | - | 预留 | 旁路 | 脚(douyin_adapter) | 真出10条(手工) | DEVELOPING | 未接管，不标 ACTIVE | 未验证不接管 |
| ZBMP-COLL-002 | Instagram 适配器 | ZBMP | Y | v4/adapters/instagram.py | registry | - | 预留 | 旁路 | 脚(instagram_adapter) | 缺 | DEVELOPING | 待真机复验 | 同上 |
| ZBMP-COLL-003 | Google 海外采集 | ZBMP | Y | v4/adapters/google.py | registry | - | 预留 | 旁路 | 无 | 手工 8 真结果 | EXPERIMENTAL | 3 中转链；无测试 | 付费代理 |
| ZBMP-COLL-004 | 统一 Cookie 保险库 | ZBMP | Y | cookie_vault.py | - | data/cookies/*.json(非库) | 隐式 | 主链 | 间接 | 缺 | ACTIVE | 合规✓不入库不入源码 | 凭证安全 |
| ZBMP-AI-001 | Zachary 机器人/AI 抽屉 | ZBMP | Y | intelligence+ai_analyzer | Y /api/ai* | ai_*/v4_ai_shadow | Y | 主链 | **50✓** test_ai+llm_gateway(兜底/安全/优先级) | **本轮 PASS** | ACTIVE | Ollama-only,规则兜底✓ | AI 仅增强 |
| ZBMP-AI-002 | AI Web Worker | ZBMP | 研究稿 | 研究稿 | - | - | 预留 | 无 | 无 | 无 | PLANNED | 仅架构 Cookie≠API | PLANNED 正确 |
| ZBMP-IMP-001 | 外部数据导入 | ZBMP | 部分(3py) | v4_upgrade/importer | - | 无专表 | 无 | 旁路 | 无 | 缺 | PLANNED | GAP-21 无前端/API/专表 | 已有部分代码,勿误判完成 |
| ZBMP-SETT-001 | 苹果风设置/密钥解锁 | ZBMP | Y | settings_module | 前缀 /api/settings/*|/v4/* | system_config | Y | 主链 | 脚/smoke | 缺 | ACTIVE | GAP-04 高危 run-code 在本域；GAP-14 | **安全 P1** |
| ZBMP-WS-001 | 工作区/项目/活动层级 | ZBMP | Y(外壳) | zbip-shell.js/zbmp-workbench.js | 内部切换 | - | Y CTH/ZBMP 切换器 | 主链(外壳) | 8301 实测 | 8301 实测 | DEVELOPING | Step4/5 已建工作台外壳+CTH/ZBMP 切换+Home；项目/活动完整层级未建 | IA 演进中 |
| ZBMP-FUT-001 | 微博/B站/快手/贴吧/知乎 | ZBMP | 占位 | platform_adapters(enabled=false) | registry | - | 预留 | 不运行 | 脚(bilibili_login) | 缺 | RESERVED | RESERVED 正确 | 不启用 |
| ZBMP-AUTH-002 | ZBMP 正式 API Key+用户体系(方案②) | ZBMP | Y | v4_upgrade/auth/workspace.py+blueprint | Y /v4/auth/workspace/{status,unlock,keys,revoke} | workspace_keys/grants(2幂等表) | Y 密钥门弹窗 | 主链 | **6✓** test_workspace_keys | **80 用例 PASS+8301 解锁实测** | ACTIVE | 12h grant；三级权限仍仅 1 owner | 凭证安全/合 main |
| ZBMP-WB-001 | ZBMP 六组工作台(12模块/8接真实API) | ZBMP | Y | zbmp-workbench.js v1.1.0 | Y 复用 Core /api/events,notes,overview,event-graph,reports,brands,brand-stats,topic-campaign | 复用生产表 | Y 六组侧栏+面板 | 主链(前端) | 8301 逐模块实测 | 8301 实测(120/6.1w,16节点) | DEVELOPING | cases/ai-eval 待接、compete 规划；内容监测仅首30条 | 只读优先 |
| ZBIP-UI-001 | ZBIP 侘寂设计系统(Token/组件/换肤/壳) | 平台 | Y | zbip-{tokens,components,theme-override}.css | - | - | Y Stone 黑白灰+六语义点 | 主链(样式) | css_balance 门禁 | 1066/390 实测 | ACTIVE | 430/768/1024/1280/1440 断点待补；少量写死色待 Dark 迁移 | 可回滚(删 link) |
| CTH-DEV-001 | 只读工程面板(底部终端+右侧文件树) | CTH | Y | zbip-panels.{css,js}+app.py 两只读路由 | Y GET /api/workspace/file-tree,POST /api/workspace/term | - | Y Codex 式面板 | 主链 | 8301 实测+白名单单测待补 | 8301 实测(file-tree 21KB) | DEVELOPING | term 白名单缺 pytest；↑↓历史/Tab/文件预览待补 | 只读/shell=False/拒写命令 |
| CTH-SYS-004 | Runtime 启动完整性预检+数据边界 | CTH | Y | runtime_preflight.py+data_boundary.py | 启动闸门(默认记录,P0+ENFORCE 才阻断) | attestation json | - | 主链(app.py:78/5129) | **24✓** test_runtime_preflight | **80 用例 PASS+启动 PASS** | ACTIVE | 默认 Attestation 不阻断为有意设计 | 启动安全 |
| CTH-SYS-005 | 统一日志 patch_logging | CTH | Y | v4_upgrade/unified_logger.py | - | - | - | 主链(app.py:48) | 间接(启动验证) | 启动无重复日志 | ACTIVE | — | 低 |
| CTH-SYS-006 | 键盘快捷键帮助+弹窗精简 | CTH | Y | static/js/keyboard_shortcuts.js+modal_simplify.js | 前端 | - | Y Ctrl+/ 帮助 | 主链(前端) | 8301 加载实测 | 8301 实测 | DEVELOPING | 缺规范用例 | 低 |
| CTH-COL-001 | 适配器基座(限流/降级/指标/safe_collect)+dual_pool | CTH | Y | v4_upgrade/adapters/base.py+dual_pool.py | registry | - | - | 旁路增强(未改主链) | 脚 | 缺 | DEVELOPING | 未接管主采集链 | 稳定性增益 |
| ZBMP-RPT-003 | 新一代报告中心 report_center | ZBMP | Y | v4_upgrade/report_center/*(generator/taxonomy/phrases/word_pdf_export) | **未挂路由** | 无专表 | 无 | 旁路(未接管) | 无 | 缺 | EXPERIMENTAL | 代码入库 app.py 无路由=未接管；接管前须 Staging | 勿与 RPT-001/002 抢 Owner(GAP-10) |
| ZBMP-BIL-001 | Global BIL 全球品牌智能体系 | ZBMP | Y | docs 13 篇+data/global_bil_*_v1.json(3 seed)+migrations/009(隔离) | **未挂路由** | 009 隔离迁移(未上生产) | 无 | 研究/数据准备 | 无 | 研究稿 | EXPERIMENTAL | 研究态；迁移隔离不碰生产库；无 app 路由 | 研究→候选须 VERIFIED |

## 状态分组（A–I，按 Registry 原值 + 2026-09-01 合并后实测，不擅自升级）
- **【A】ACTIVE（25）**：原 21（MON-001/002/004，SUBJ-001，EVT-001/002/003，RISK-001/002，NOTE-001，RPT-001/002，AUTH-002，SYS-001/002/003，BRAND-001/002，COLL-004，AI-001，SETT-001）**+ 本轮 4：ZBMP-AUTH-002（6✓）、ZBIP-UI-001（css 门禁）、CTH-SYS-004（24✓）、CTH-SYS-005（启动验证）**。
  - 其中**规范 pytest 直接覆盖（证据最硬）**：SUBJ-001、EVT-001、RISK-001、NOTE-001、RPT-001、AUTH-002、SYS-001、AI-001 + AUTH-002(6)、SYS-004(24)；EVT/RISK/RPT 仍为集成级，函数级直接单测欠=GAP-02。
  - 其余 ACTIVE 在生产运行、有真实数据/路由，但部分仅脚本式验证或无统一 Evidence，按严格五要素仍欠 Test/Evidence（不降级，Gap 标注）。
- **【B】DEVELOPING（11）**：原 6（MON-003、SUBJ-002、AUTH-001、BRAND-003、COLL-001、COLL-002）+ WS-001（由 PLANNED 转入，外壳已建）**+ 本轮 4：ZBMP-WB-001、CTH-DEV-001、CTH-SYS-006、CTH-COL-001**。
- **【C】EXPERIMENTAL（4）**：原 2（MON-005、COLL-003）**+ 本轮 2：ZBMP-RPT-003（report_center 未挂路由）、ZBMP-BIL-001（Global BIL 研究态）**。
- **【D】NOT_VERIFIED（0）**：当前无（凡证据不足的在建能力已落在 DEVELOPING/EXPERIMENTAL/PLANNED，未虚高 ACTIVE）。
- **【E】PLANNED（3）**：NOTE-002、AI-002、IMP-001（WS-001 已转入 DEVELOPING）。
- **【F】RESERVED（1）**：FUT-001。
- **【G】DUPLICATE（0 条 Feature 级）**：重复在能力/实现层以 DUPLICATE_CANDIDATE 登记（EVT-003 两套负面、RPT 系列多报告实现、SETT/高危三入口），未删，见 GAP-04/09/10。
- **【H】MIGRATION_REQUIRED（0 条 Feature 级）**：高危三运行入口在 GAP-04 单列迁移。
- **【I】LEGACY（0 条 Feature 级）**：LEGACY 实现在 CAPABILITY-OWNERSHIP（**云端 ark/ai_gateway 经评估保持 Legacy 默认关，仅公开非敏感内容未来可作可选 Provider、客户数据永不过云**、旧 JS 采集、v570、Selenium 等）登记，不在 Feature 总账虚列。

## 计数汇总
| CTH-MON-006 | RedNote 运行策略 SoT | CTH | Y | platform_adapters/rednote_policy.py | -(纯策略) | - | 无 | 旁路(默认不自动跑) | **4✓** test_rednote_policy | 本轮 PASS | DEVELOPING | intl 为主/cn 暂停/三端开关已固化；国际站选择器、真人频率实测值、保活调度待真实窗口 | 真实平台风控 |
| CTH-RPT-003 | 标准化报告只读预览 | CTH/ZBMP | Y | v4_upgrade/report_center | Y GET /api/v2/report-center/preview | notes/events(只读) | 待接 | 旁路只读 | **7✓** test_report_center_route | 本轮 PASS(Staging 18节) | EXPERIMENTAL | 导出/自动发送未接管，不抢 RPT-001/002 Owner(GAP-10) | Owner 冲突 |
| ZBMP-INTEL-001 | Global BIL 全球品牌智能(研究) | ZBMP | Y | v4_upgrade/global_bil.py | Y GET /api/v2/global-bil/* | seed JSON(不建表) | 待接 | research 只读 | **4✓** test_global_bil_read | 本轮 PASS(19基准/16机制/10案例) | EXPERIMENTAL | bi_* 表仅隔离库 009 迁移；不参与生产口径 | 研究阶段 |
| CTH-SYS-004 | 采集 Adapter 韧性层(熔断/限流/双池) | CTH | Y | v4_upgrade/adapters(base,dual_pool) | -(未挂主链) | - | 无 | 旁路(增强未接主链) | **9✓** test_adapter_resilience | 本轮 PASS | EXPERIMENTAL | 主采集链当前不经过，接入另评估 | 低 |
ACTIVE 27 / DEVELOPING 10 / EXPERIMENTAL 7 / NOT_VERIFIED 0 / PLANNED 3 / RESERVED 1 / DUPLICATE 0 / MIGRATION_REQUIRED 0 / LEGACY 0（合计 48，基线 main=`9092697`；ACTIVE 含 GAP-05 默认 shadow 门控、GAP-06 双维度，状态升级均有测试+Staging 证据）。
ASSET_MISSING=0；Owner 冲突=0 新增（重复候选见 GAP）；合并后真实测试 **80 passed / 0 failed** + CSS 平衡门禁全绿；统一 Evidence 落库=0（体系缺口 GAP-08）。
**本轮关键集成**：ui/staging-foundation Step1–Step5j 已并入 main（main=staging=origin=`580c2cf`），GAP-03 主 SPA 挂载随之解决；report_center/Global BIL 已于 09-01 晚挂**只读旁路路由**（/api/v2 前缀，不抢生产 Owner、不写库），状态仍 EXPERIMENTAL；adapter 韧性层经 9 测验证但未接主采集链；RedNote 策略 SoT 默认不自动跑。统一测试 **151 passed**。
