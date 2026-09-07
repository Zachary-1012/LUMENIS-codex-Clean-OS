# 阶段8 最终验收矩阵（草稿）

> 生成时间：2026-09-07
> 状态：草稿 — Tests 与 Final Status 留空，待全量测试实数填入后定稿
> 证据文件：audit/convergence/_phase8_db_trend_evidence.md、_phase8_product_evidence.md、_phase8_audit_branch_evidence.md

---

## 1. Repository（仓库状态）

| 维度 | 状态 | 证据 |
|------|------|------|
| 分支 | main | git branch |
| 本地HEAD | 3055918（前端数据渲染修复） | git log --oneline -1 |
| 基线后新增commit | 19个（含用户自动保存/功能commit） | git log d72153f..HEAD --oneline |
| 未push | 是（全部本地，尚未push origin/main） | git status |
| 工作区未提交 | ai_task_parser.py、app.py（用户进行中） | git status --short |
| 仓库规模 | 1333个.py文件，128业务表 | DB探针+代码扫描 |

---

## 2. Tests（测试体系）— ⏳ 待用户填入全量实数

| 维度 | 状态 | 备注 |
|------|------|------|
| 全量测试 pass/fail/skip/error | **待填** | 用户重跑中（ZBC_TEST_OFFLINE修复后） |
| 连续多次独立运行一致性 | **待填** | 用户要求2~3次+随机/逆序 |
| 总耗时 | **待填** | — |
| 阶段1修复项 | v4_upgrade懒加载(448→136ms)、collect_ignore列全8个sys.exit脚本、safe_collect 13.4s→1.1s、workspace_keys pbkdf2隔离、security_scanner范围(7232→1475文件)、ai_task_engine心跳泄漏try/finally、ZBC_TEST_OFFLINE云端短路 | commits a98bc5e/34811e0/7115f49 + 用户修复 |
| 全量冻结真根因 | test_l4_full_chain::test_step_10_report 真实云端AI HTTPS ssl.read阻塞90s×3=270s（非线程污染、非pbkdf2） | 用户定位，ZBC_TEST_OFFLINE=1修复 |
| Agent Runtime新测试 | 295个全通过（Core 167 + Memory 128），无线程泄漏 | commits c679dab/bcd1cd6 |
| 全量测试隔离结论 | **待填** | 稳定后标 VERIFIED / PARTIAL / NOT VERIFIED |

---

## 3. Runtime（运行时）

| 维度 | 状态 | 证据 |
|------|------|------|
| Flask服务 | 运行中，端口8201 | curl /healthz |
| debug模式 | False（改模板须重启） | app.py配置 |
| AI Gateway | Provider-Agnostic（智谱GLM主力+ARK/千问备用+Ollama本地兜底+确定性规则最终兜底） | AI_PROVIDER_RUNTIME_POLICY_V1 |
| Runtime Guardian | PARTIAL — lease/heartbeat/reaper/checkpoint实现完整(runtime_guardian.py 46.5KB)，但零外部调用，/api/system/runtime未注入guardian数据（前端字段映射已就绪） | _phase8_product_evidence.md |
| 31个daemon线程 | P1 — 无统一生命周期/shutdown hook | phase6_source_audit.md |
| 全局状态无锁 | P1 — collect_tasks写操作未持_task_lock、_brand_cache无锁 | phase6_source_audit.md |
| /api/collector/status双重注册 | P1 — collection_api.py:22与collector_status_api.py:142同路径 | phase6_source_audit.md |
| proxy_health_loop | 已修 — 幂等守卫+固定线程名 | app.py（用户修复） |
| AI云端同步最坏270s | P1建议 — post_with_retry(max_attempts=3,timeout=90)无全局deadline | ai_channel.py |

---

## 4. Database（数据库）

| 维度 | 状态 | 证据 |
|------|------|------|
| 业务表总数 | **128**（129含系统表sqlite_sequence） | sqlite_master实数 |
| 非空/空表 | **64 / 64**（V2记录63/65，数据实时增长1张） | SELECT COUNT(*)逐表 |
| 非空TOP3 | schedule_decisions(15147)、note_review_history(8387)、ai_task_trace(6176) | DB直查 |
| KEEP | **118** | phase2_db_lifecycle_v2.md |
| MIGRATE | **7** | 同上 |
| DEPRECATE | **3** | xhs_notes/xhs_comments/xhs_collections（已被notes/note_comments替代） |
| DELETE-CANDIDATE | **0** | 无一张表符合"无代码引用+无数据+无业务用途" |
| 单迁移文件创建46表 | migrate_platform_data_dict_v1.py（12平台Raw层35+Canonical 3+Evidence 2+Business 3+索引） | git历史 |
| 5组疑似重复表 | collection_runs→collection_logs、content_analysis→content_evaluation、token_stat→ai_call_logs、platform_*通用vs adapter专用、collector_quality_log vs collection_quality_log | phase2_v2 |
| 主体口径P0 | subject_rules.py四要素完整(SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS/subject_hit/subject_sql_and_values)，app.py 9处引用(1定义+8调用) | _phase8_audit_branch_evidence.md |
| 时间口径 | notes=publish_datetime+captured_at、events=event_date(无publish_datetime)、metric_snapshots=snapshot_at(无period_start/end) | DB schema |
| risk数据位置 | events.risk_level(high=8/medium=53/low=433) + notes.risk_level；risk_records/risks/note_risk_log三表实际不存在 | DB直查 |

---

## 5. Product（产品闭环）

### 5.1 趋势数据闭环

| 端点 | HTTP | 30天总条数 | 时间字段 | 结论 |
|------|------|-----------|----------|------|
| /api/trend/notes | 200 | 235 | publish_datetime | 契约修复后有数据 |
| /api/trend/events | 200 | 247 | event_date | 契约修复后有数据 |
| /api/trend/risk | 200 | 247 | events.risk_level | 数据源确认(risk_records不存在) |
| /api/trend/kos | 200 | 130 | notes.publish_datetime + LEFT JOIN kos_profiles | 契约修复后有数据 |

DB直查核对：notes=1020(1019有publish_datetime)、events=494(全部有event_date)、kos_profiles=375(全部is_kos=1)。

### 5.2 采集验证（阶段4）

| 项 | 状态 | 证据 |
|----|------|------|
| dual_account_rotation双账号轮换 | ✅ VERIFIED | collector_automation.py:1051真实调用 |
| XHSAppTopicAdapter话题APP | ⚠️ PARTIAL | 仅topic_campaign子系统消费，主采集链路走CDP |
| collect-resume断点续采 | ✅ VERIFIED | API端点+checkpoint模块齐全 |
| 内部浏览器默认strict可切外部 | ✅ VERIFIED | collector_browser_mode.py默认internal_cdp，collector.py读取，collector.html radio UI |
| auth_recovery系统内弹 | ✅ VERIFIED | base.html内联Modal，/api/auth-recovery/summary 200，真实证据collection_logs id=526→auth_recovery_tasks id=6 |
| 账号保活/限速熔断 | ⚠️ PARTIAL | 限速+熔断已在链路中，account_keepalive独立模块未接入主链路 |

### 5.3 产品页面（阶段5）

| 项 | 状态 | 证据 |
|----|------|------|
| ZBMP brand.html→/api/brands/logos | ✅ VERIFIED | 200，194品牌，logo覆盖率93.8%(182/194) |
| CTH brands.html | ✅ VERIFIED | 200，同样接入/api/brands/logos |
| Podcast 10维打分8 API | ⚠️ PARTIAL | 7/8可用(200)，**story-nodes端点HTTP 000超时**(podcast_routes.py:143，import路径问题) |
| Settings标准化 | ✅ VERIFIED | 200，平台开关(/api/data-center/platforms返回1平台=小红书)/系统模块入口/语言切换三组齐全 |
| 9级z-index token | ✅ VERIFIED | adaptive-layout.css 9变量全定义(--z-base=0到--z-auth-recovery=10000)，仅1处魔法数字残留(cth/realtime.html:618) |
| Motion覆盖 | ⚠️ PARTIAL | 3 JS全加载(motion-bridge/adaptive-motion/carousel)，14页COVERED(data-kpi)、4页PARTIAL(cth/evidence/industries/launch用不同class名)、10+页无KPI元素 |
| 前端auth时序修复 | ✅ VERIFIED | xjViz.api()/ZBCTrendLine/browser.js/settings平台开关均加await LUMENIS.Auth.getHeader()，解决页面加载时401空白 |
| 笔记详情弹窗 | ✅ VERIFIED | realtime.html +210行，点击弹出完整详情(标题/作者/封面/正文/话题/四宫格/时间/跳转原文)，ESC+遮罩关闭 |
| 风险列表字段 | ✅ VERIFIED | risk.html字段映射修复(source_platform/publish_date/source_keyword) |
| i18n | ✅ VERIFIED | nav.topics三语补全(zh-CN/en/ko)、settings.js titles字典补platforms/syslinks/zbmp-domain |
| KPI骨架屏 | ✅ VERIFIED | loadKPI从Promise.all(等最慢API 2125ms)重构为独立渲染(数据到达即显示) |
| Motion count-up双重bug | ✅ VERIFIED | motion-bridge.js修复data-kpi-value提前设为新值导致oldValue===newValue不触发动画 |
| 账号恢复转圈 | ✅ VERIFIED | fetchSummary无pending任务时调用close()隐藏弹窗+HTTP错误处理 |

### 5.4 已知产品限制

| 项 | 状态 | 说明 |
|----|------|------|
| 业态分布全0 | ⏳ 后端待修 | /api/brand-stats pie_data全0，需修复brand→industry匹配（不可用content categories冒充） |
| Runtime Guardian全UNKNOWN | ⏳ 后端待修 | runtime_guardian.py零外部调用，需注入guardian数据到/api/system/runtime |
| /api/xhs/p0/status超时 | ⏳ 后端待修 | 有三级fallback链不影响核心功能 |
| Podcast story-nodes HTTP 000 | ⚠️ 待修 | podcast_routes.py:143端点存在但调用挂起，需排查import story_nodes路径 |
| cache_manager.py:241真实bug | ⚠️ 未修 | `SELECT * FROM events ORDER BY created_at`，events表26列中无created_at，运行时必报错 |
| report_api.py:493口径不一致 | ⚠️ 未修 | 用first_seen而非event_date，first_seen含脏值"编辑于2025-08-22" |
| 平台开关写接口 | ⚠️ 待确认 | POST /api/data-center/platforms/<id>/visibility后端可能未实现，前端优雅降级UI预览模式 |
| 趋势图平滑过渡 | ⚠️ P1后续 | ZBCMotion.updateChart()已就绪但xjViz现有渲染函数尚未全部改为调用此API |

---

## 6. Security（安全）

| 维度 | 状态 | 证据 |
|------|------|------|
| Auth三层设计 | ✅ VERIFIED | Layer1 Basic Auth覆盖199/219路由(所有89写路由均在保护内)、Layer2写操作统一门覆盖80/89、Layer3 @require_permission 6个高风险端点 |
| 真缺口 | ✅ 无 | 不存在"三层均无覆盖"的写路由；仅content/podcast/ic蓝图~15个POST有Layer1缺Layer2+3 |
| COMMIT/PUSH默认DENY | ✅ VERIFIED | permission_gate fail-closed，Agent自动化上限VERIFY |
| API Key管理 | ✅ VERIFIED | 仅.env注入，严禁写入源码/前端/Git |
| 小红书账号只读 | ✅ VERIFIED | 一切自动化对账号一律只读，永久禁止关注/点赞/评论/发布/退登/切换 |
| AI是增强层非Production Truth | ✅ VERIFIED | 系统生命线不绑定单一AI Provider，断网降级本地模型+确定性规则 |
| security_scanner扫描范围 | ✅ 已修 | exclude_dirs增补IDE/浏览器profile/归档+max_scan_file_bytes=1MiB，7232→1475文件/5s |
| ai_task_engine心跳泄漏 | ✅ 已修 | execute_task try/finally lifecycle_stop，修复前泄漏8线程修复后0泄漏 |
| report_engine心跳泄漏 | ✅ 已修(复核修正) | generate_report() L270 lifecycle_start已有L381-389 finally配对，非"待修" |
| 硬编码产品口令1012Zzh | ⚠️ P2建议 | app.py:6046硬编码，建议移.env |
| 配置漂移 | ⚠️ P1 | 代码读130个env变量，.env.example仅80个且GBK乱码 |
| 无统一Feature Registry | ⚠️ P1 | 14+ Feature Flag散落为独立env变量 |

---

## 7. Branches（分支收敛）

| 分类 | 数量 | 说明 |
|------|------|------|
| A 已完整进入main | 28 | 功能分支，无独有资产 |
| B main部分吸收 | 2 | feat/lumenis-p0-p1-source-convergence、origin/feat/lumenis-product-convergence |
| C 未吸收但有有效资产 | 1 | origin/feat/lumenis-product-convergence-docs-final3（文档） |
| D research/experimental | 3 | kdrama韩剧字幕研究系列 |
| E stale重复变体 | 62 | final2/final3/v2/v3等冗余分支 |
| F conflict/risk | 1 | **feat/zbc-full-upgrade-v1**（P0主体口径弱化） |
| 唯一分支总数 | 97 | git branch -a去重 |

**F类禁合并理由**：feat/zbc-full-upgrade-v1移除app.py中9处_subject_sql_and_values()调用，分布在5个核心统计函数(api_dashboard_all/api_global_trends_v570/api_notes_library_v571/api_negative_stats/api_publish_buckets_v570)，主体过滤从"is_taikoo_verified=1 AND relevance_status!='irrelevant' AND {主体词SQL}"弱化为仅"is_taikoo_verified=1"。主体过滤相关代码一律不得回收进main，仅允许capability-level selective recovery。

**main主体链路验证**：subject_rules.py四要素完整，app.py _subject_sql_and_values()共9处(1定义L992+8调用)✓

---

## 8. Agent Runtime（新增能力）

| 模块 | Commit | 测试 | 核心能力 |
|------|--------|------|----------|
| Runtime Core | c679dab | 167 pass | 9状态状态机/Agent Loop(预算控制max_steps=20/max_time=300s/max_cost=$2)/Observation Layer/Planner(智谱GLM)/Replanning(5触发6策略)/轨迹评估(4维评分)/Durable Adapter |
| Memory+Learning+Router | bcd1cd6 | 128 pass | 6层记忆(Working/Task/Episodic/Semantic/Skill/Learning)复用10张现有表/Learning Loop(反馈→规则→prompt)/Capability Router(首批12个Tool)/Skill升级Capability |

**复用7个现有模块**：permission_gate/AI Gateway/ai_task_engine/runtime_guardian/skill_execution_chain/evidence_chain/ai_channel。零生产代码修改，Feature Flag默认关闭(AGENT_RUNTIME_ENABLED=0)。

**能力审计**：ZBC 36项(EXISTS=26/PARTIAL=7/MISSING=3)、OSAI 50项(EXISTS=28/PARTIAL=14/MISSING=8)、10个Contract接口定义。

---

## 9. Final Status（最终结论）— ⏳ 待全量测试实数后填入

| 维度 | 结论 |
|------|------|
| 总体状态 | **待填**（READY / CONDITIONAL READY / NOT READY） |
| 阶段1测试隔离 | **待填**（VERIFIED / PARTIAL / NOT VERIFIED） |
| 阶段2 DB生命周期 | ✅ VERIFIED |
| 阶段3趋势闭环 | ✅ VERIFIED |
| 阶段4采集验证 | ⚠️ PARTIAL（4/6 VERIFIED，XHSAppTopicAdapter+账号保活PARTIAL） |
| 阶段5产品闭环 | ⚠️ PARTIAL（前端11项全修，后端3项待接入：业态/Guardian/xhs-p0，Podcast story-nodes待修） |
| 阶段6源码审计 | ✅ VERIFIED（P0=0/P1=27/P2=17，含本轮新增8项） |
| 阶段7分支收敛 | ✅ VERIFIED（97分支A-F分类，F类禁合并） |
| Agent Runtime | ✅ VERIFIED（Core+Memory，295测试全通过，Feature Flag默认关闭） |
| push main | ⏳ 未执行（19个本地commit待push） |

### 阻塞项（影响READY结论）
1. **全量测试实数** — 待用户填入（决定阶段1是否VERIFIED）
2. **cache_manager.py:241真实bug** — events表ORDER BY不存在的created_at列，运行时必报错
3. **Podcast story-nodes HTTP 000** — 端点挂起需排查import路径
4. **后端3项待接入** — 业态匹配/Runtime Guardian注入/xhs-p0/status
5. **push main** — 19个本地commit待push

### 建议下一步
1. 全量测试稳定通过后，阶段1标VERIFIED
2. 修cache_manager.py:241（改为ORDER BY event_date）和Podcast story-nodes
3. 后端接入业态匹配+Runtime Guardian数据
4. push origin/main
5. 产出阶段8定稿验收矩阵
