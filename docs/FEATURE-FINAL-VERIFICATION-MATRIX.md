# FEATURE-FINAL-VERIFICATION-MATRIX（Feature Final Verification 2.0）

> 生成 2026-08-31，ZBP / Z-Brand-Core main=`af28436` 工作区。**判定优先级：源码 > DB > Runtime > 测试 > Evidence > 文档。**
> 只读核验脚本：`scripts/inventory/feature_final_verify.py`；测试事实为本轮**真实运行**：规范用例 **50 passed in 16.06s**（test_ai/test_api/test_database/test_e2e/test_llm_gateway）。
> 关键事实：pytest 可收集的 `test_*.py` 共 36 个，其中**仅 5 个含 `def test_`（=50 用例），另 31 个为独立脚本（无 def test_、靠 __main__/sys.exit 运行）**；统一 `pytest tests` 被 `test_api_smoke.py` 顶层 `sys.exit` 打成 INTERNALERROR（仅收集到 26）。`app_evidence_records` 为外部抓取表且 **0 行**，无统一测试 Evidence 落库。
> **Status 列保留 FEATURE-REGISTRY 原值，不擅自升降级**；严格 ACTIVE 五要素=代码+Owner+运行路径+测试+Evidence，缺口写入 Gap 列与 FEATURE-GAP-REGISTER。

## 图例
- Asset：文件/模块真实存在（全部 Y，无 ASSET_MISSING）。API：Y=真实路由命中；`前缀*`=登记前缀不精确但功能在（GAP-14）；-=本就无独立 API。
- Runtime：主链=被 app 主链 import 可达（module_graph app_reachable）；旁路=v4/适配器/新一代未接管；- =无运行进程类。
- Test：**50✓**=被本轮 50 个 PASS 用例直接覆盖；脚=有对应脚本式验证（非 pytest、未统一执行）；无=缺。
- Evidence：**本轮 PASS**=50 用例实测通过覆盖；缺=无统一可归档运行证据（EVIDENCE_MISSING）。

## 全量矩阵（34 条）
| ID | Feature | Product | Asset | Owner | API | DB | UI | Runtime | Test | Evidence | Status | Gap | Risk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CTH-MON-001 | 关键词笔记采集(真人CDP) | CTH | Y | collector.py/xhs_cdp_collector | Y /api/collect* | notes,collection_logs | Y collect | 主链 | 脚(collect_state/collection_full/browser_e2e) | 缺(不能在CI打真实平台,需mock) | ACTIVE | 采集链无规范pytest；当前 BLOCKED 熔断 | 账号/IP 风控(非代码缺陷) |
| CTH-MON-002 | 15周年专题监测 | CTH | Y | topic_campaign.py | Y | topic_campaign_notes(120) | Y 专题页 | 主链 | 脚(test_topic_port) | 缺 | ACTIVE | 缺规范用例 | 窗口至 10-07 |
| CTH-MON-003 | 采集调度(固定→动态) | CTH | Y | platform_adapters/scheduling | 前缀*(实际 /api/collect/schedule-status) | schedule_decisions | Y console | 旁路(影子) | 脚(test_scheduling) | 影子日志 | DEVELOPING | GAP-05 门控待签字；GAP-14 | 未门控，不控生产 |
| CTH-MON-004 | 采集健康/六态 | CTH | Y | health_center.py | Y /api/platform-health | collection_logs | Y 健康点 | 主链 | 脚(test_health_center) | 缺 | ACTIVE | 缺规范用例 | 低 |
| CTH-MON-005 | 全网搜索采集 | CTH | Y | web_monitor/v4 adapters | Y /api/web-* | web_*(5表) | Y | 旁路 | 无 | 缺 | EXPERIMENTAL | 无测试 | 中转链稳定性 |
| CTH-SUBJ-001 | 广州太古汇主体过滤🔴 | CTH | Y | subject_rules.py | 内部 | notes.subject_hit | Y | 主链 | **50✓** test_e2e::subject_filter + 脚 redline | **本轮 PASS** | ACTIVE | 可补函数级边界用例 | 红线，禁弱化 |
| CTH-SUBJ-002 | 主体/内容双维度 | CTH | Y | subject_classifier.py | Y /api/subject-classifier/types | 落库列未建 | Y | 旁路 | 50✓(AI/e2e 间接) | 部分 | DEVELOPING | GAP-06 落库贯通；禁 user_type=UGC | 枚举口径 |
| CTH-EVT-001 | 事件聚合🔴 | CTH | Y | aggregate_events() | Y /api/events* | events(427) | Y | 主链 | **50✓** test_e2e::events_aggregation | **本轮 PASS(集成级)** | ACTIVE | GAP-02 缺函数级直接单测 | 红线 |
| CTH-EVT-002 | 事件关系图谱 | CTH | Y | event_graph.py | Y /api/event-graph/* | event_graph_events(16)/relations(1) | Y | 主链 | 无 | 缺 | ACTIVE | GAP-07 三类四关系未全；无直接测试 | 关系数据极少 |
| CTH-EVT-003 | 负面确认/评审 | CTH | Y | events 评审流 | Y negative/event-review | note_review_history(8327) | Y | 主链 | 脚(negative_event_api) | 缺 | ACTIVE | GAP-09 两套并存 DUPLICATE_CANDIDATE | 双写状态不一致 |
| CTH-RISK-001 | 风险判定/等级🔴 | CTH | Y | 根 risk_engine.py | Y /api/risk* | events | Y | 主链 | **50✓** test_e2e::risk_level | **本轮 PASS(集成级)** | ACTIVE | GAP-02 test_risk_engine 实参测 collector_guard，根 risk_engine 无直接单测 | 红线 |
| CTH-RISK-002 | 熔断/冷却/300012 | CTH | Y | collector_guard/xhs_cookie_bridge | 前缀*(无独立 /api/circuit*) | xhs_circuit(json) | Y | 主链 | 脚(guard_wiring/risk_engine) | 缺 | ACTIVE | GAP-14 登记口径；只识别不破解 | 合规红线 |
| CTH-NOTE-001 | 笔记库/详情/评论/去重 | CTH | Y | database.py+collector | Y notes*/comments* | notes(957) | Y | 主链 | **50✓** test_database 6 用例 | **本轮 PASS** | ACTIVE | — | 低 |
| CTH-NOTE-002 | 空正文 CDP 回填 | CTH | Y | backfill_detail_cdp | - | notes | 预留 | 旁路 | 脚(title_fallback) | 缺 | PLANNED | 253 条待稳定网络 | PLANNED 正确 |
| CTH-RPT-001 | 日/周/月/专题报告🔴 | CTH | Y | daily_report.build_daily_report | Y /api/report* | events,notes | Y | 主链 | **50✓** test_e2e::daily_reports | **本轮 PASS(集成级)** | ACTIVE | GAP-02 build_daily_report 无直接单测(test_report_periods 测 export) | 红线/publish 时间口径 |
| CTH-RPT-002 | 报告导出 pdf/xlsx/docx | CTH | Y | report_export/* | Y | - | Y | 主链 | 无 | 缺 | ACTIVE | GAP-10 多实现待收敛 | 统计必须来自 Owner |
| CTH-AUTH-001 | 统一 Auth 恢复弹窗 | CTH | Y | auth_recovery_center+auth_global.js | Y /api/auth-recovery/*(蓝图) | auth_recovery_tasks | 部分(4 v4子页) | 主链(后端) | 脚(auth_api) | 缺 | DEVELOPING | **GAP-03 主 SPA 未挂**；A/B/C 无 E2E | 不跳页红线 |
| CTH-AUTH-002 | 登录/权限/安全问答 | CTH | Y | v4 auth + Basic | Y /v4/auth/* | v4_users/sessions/security_questions | Y | 主链 | **50✓** test_api::TestAuthAPI×2 | **本轮 PASS** | ACTIVE | 三级权限仅 1 owner | 安全 |
| CTH-SYS-001 | 系统健康/看门狗/自愈 | CTH | Y | system_health_api/guardian | Y /healthz,/api/system/health | - | Y | 主链 | **50✓** test_api::System×2 +脚 auto_recovery | **本轮 PASS** | ACTIVE | — | 低 |
| CTH-SYS-002 | 版本中心/Git 自动同步 | CTH | Y | version_center/git_manager | 前缀*(页面在,API 口径) | - | Y | 主链 | 脚(version_api) | 缺 | ACTIVE | GAP-15 标题括号 bug | 低(不影响运行) |
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
| ZBMP-SETT-001 | 苹果风设置/密钥解锁 | ZBMP | Y | settings_module | 前缀*(/api/settings/*+v4页面) | system_config | Y | 主链 | 脚/smoke | 缺 | ACTIVE | GAP-04 高危 run-code 在本域；GAP-14 | **安全 P1** |
| ZBMP-WS-001 | 工作区/项目/活动层级 | ZBMP | 无(待建) | 待建 | - | - | 预留 | 无 | 无 | 无 | PLANNED | IA 占位 | PLANNED 正确 |
| ZBMP-FUT-001 | 微博/B站/快手/贴吧/知乎 | ZBMP | 占位 | platform_adapters(enabled=false) | registry | - | 预留 | 不运行 | 脚(bilibili_login) | 缺 | RESERVED | RESERVED 正确 | 不启用 |

## 状态分组（A–I，按 Registry 原值，不擅自升级）
- **【A】ACTIVE（21）**：MON-001/002/004，SUBJ-001，EVT-001/002/003，RISK-001/002，NOTE-001，RPT-001/002，AUTH-002，SYS-001/002/003，BRAND-001/002，COLL-004，AI-001，SETT-001。
  - 其中**本轮 50 PASS 直接覆盖（证据最硬，8）**：SUBJ-001、EVT-001、RISK-001、NOTE-001、RPT-001、AUTH-002、SYS-001、AI-001（EVT/RISK/RPT 为集成级，仍缺函数级直接单测=GAP-02）。
  - 其余 13 个 ACTIVE 在生产运行、有真实数据/路由，但**仅有脚本式验证或无统一 Evidence**，按严格五要素仍欠 Test/Evidence（不降级，Gap 标注，供你独立核对）。
- **【B】DEVELOPING（6）**：MON-003、SUBJ-002、AUTH-001、BRAND-003、COLL-001、COLL-002。
- **【C】EXPERIMENTAL（2）**：MON-005、COLL-003。
- **【D】NOT_VERIFIED（0）**：当前无（凡证据不足的在建能力已落在 DEVELOPING/EXPERIMENTAL/PLANNED，未虚高 ACTIVE）。
- **【E】PLANNED（4）**：NOTE-002、AI-002、IMP-001、WS-001。
- **【F】RESERVED（1）**：FUT-001。
- **【G】DUPLICATE（0 条 Feature 级）**：重复在能力/实现层以 DUPLICATE_CANDIDATE 登记（EVT-003 两套负面、RPT-002 多导出、SETT/高危三入口），未删，见 GAP-04/09/10。
- **【H】MIGRATION_REQUIRED（0 条 Feature 级）**：高危三运行入口在 GAP-04 单列迁移。
- **【I】LEGACY（0 条 Feature 级）**：LEGACY 实现在 CAPABILITY-OWNERSHIP（云端 AI、旧 JS 采集、v570、Selenium 等）登记，不在 Feature 总账虚列。

## 计数汇总
ACTIVE 21 / DEVELOPING 6 / EXPERIMENTAL 2 / NOT_VERIFIED 0 / PLANNED 4 / RESERVED 1 / DUPLICATE 0 / MIGRATION_REQUIRED 0 / LEGACY 0（合计 34）。
ASSET_MISSING=0；Owner 冲突=0 新增（重复候选见 GAP）；本轮真实测试 **50 passed / 0 failed**；统一 Evidence 落库=0（体系缺口 GAP-08）。
