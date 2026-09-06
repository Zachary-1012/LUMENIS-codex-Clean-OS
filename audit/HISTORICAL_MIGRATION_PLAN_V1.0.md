# ZBC 历史数据与规则 · 适配融合迁移规划 V1.0（待你确认后全量）

> 方式：**适配融合，不是搬数**。以当前主库 71 表结构为唯一目标，历史数据过当前规则管线、重算治理字段、按双域打标后幂等并入。源只读、只增不删、可重跑。
> 源：`D:\Taikoo-staging-ui\staging\monitor.staging.db`（52 表）　目标：`D:\Taikoo-monitor-new\data\monitor.db`（71 表）。下列数字为两库真实盘点。

## 一、迁移分三类处理

### A 类：同名表，历史数据并入且需"补算当前新字段"（重点）
| 表 | 源→目标行数 | 适配动作 |
|---|---|---|
| notes | 957→6 | 并入；目标新增 `subject_type/content_type/rule_version/content_hash/provenance/product_id` 六字段**用当前函数重算**（subject_hit 重判、content_hash 重算、按域打 product_id、provenance=historical_staging、记 rule_version）；源多的 `negative_confirmed_at/by` 人工负面确认保留不丢 |
| note_comments | 141→0 | 全量并入；旧 `comments(2条)` 去重后并入此表 |
| events | 427→0 | 并入 CTH，重算 subject/风险状态枚举 |
| event_mentions | 562→0 | 随 events 并入，重建事件关联 |
| event_graph_events / relations / event_insights | 16 / — / 17→0 | 并入事件图谱，重连关系 |
| topic_campaign_notes | 120→0 | 并入；源多 media_json/comments_json/subject_hit/evidence_quality/detail_captured_at 保留并按新结构拆字段 |
| topic_campaign_snapshots | 325→65 | 增量并入缺的部分 |
| note_review_history | **8327→0** | **人工审核/修正历史全量保留**（人工修正可追溯红线），关联到新 note_id |
| collection_logs / collector_quality_log | 477 / 7→0 | 采集日志与质量记录并入 Shared |
| ai_filter_log | 827→3 | 并入 AI 过滤记录 |
| brand_knowledge / case_deep_analysis / feedback_keywords | 103/20/16→0 | 品牌知识库、深度案例、反馈词并入对应域 |
| web_mentions / web_runs | 79→13、28→4 | ZBMP 品牌传播，增量并入 |
| daily_reports / daily_digest | 29→15、5→3 | 历史报告并入；补目标新字段 report_id/artifact_hash/generator_version/data_version/source_snapshot |
| swire_events / swire_projects | 10→10、8→8 | 已齐，仅补缺、不覆盖 |
| v4_*（users/sessions/keys/audit/login…） | 目标更多 | **以当前账户体系为准，只补缺不覆盖、不回滚新结构**（TOTP/成员/产品保护新表不动） |
| schedule_decisions | 141 vs 10991 | 目标更全，不回灌 |

### B 类：源有、目标无的 9 张表 → 映射决策（不照搬建旧表）
| 源表 | 行数 | 处理 |
|---|---|---|
| brand_industry_monitor | 198 | **CTH 199 品牌/楼层铺位/正负声量/风险**，映射进当前品牌业态统计模型（缺结构则按当前规范建表），归 CTH |
| industry_stats | 8 | **CTH 9 业态统计**，并入当前业态聚合，归 CTH |
| web_events / web_topics | 20 / 96 | **ZBMP 网络传播事件/话题**，映射进当前 web 传播模型，归 ZBMP |
| weekly_events | 30 | 周报事件素材，映射进 CTH 事件/报告体系 |
| comments | 2 | 旧评论，去重并入 note_comments，不另建 |
| collection_counters | 1 | 每日采集计数，并入当前采集统计/日志 |
| system_config | 10 | 旧 KV 配置映射进当前配置体系（不覆盖现配置，冲突列出） |
| notification_logs | 3 | 并入当前通知记录 |
| v4_ai_shadow | 2 | AI 影子决策记录，映射进 AI 治理/审计 |

### C 类：目标新增、源没有的表 → 保留不动（当前架构新能力）
canonical_data / zbc_canonical_data / zbc_evidence、kos_*（executions481/operations225/paid90/rewards45）、runtime_guardian_*、evaluation_records、alert_*、intelligence_assets(711)、skills_registry、user_nav_config、v4_totp_secrets / v4_member_authorizations / v4_product_protection / v4_login_approvals / v4_verification_codes、podcast_*、professional_*、brand_propagation_*、metric_snapshots、ai_call_logs 等——迁移不触碰，后续由重算管线生成 canonical/evidence。

## 二、每条数据必过的规则管线（和功能结合）
Raw → 字段映射到当前 schema → **subject 红线重判(SUBJECT_WORDS/EXCLUDE/subject_hit，不沿用旧标签)** → 质量门禁 → **双时间校正** → content_hash+platform_id 精准去重 → Canonical → **双域打标** → 风险/证据 → 幂等 upsert → 函数驱动前端。
- **双时间铁律**：publish_datetime=平台发布、captured_at/collected_at=采集，严格分列；相对时间归一化为绝对时间；禁止 publish= captured。
- **治理字段重算不留空**：product_id/domain_id、content_hash、subject_type、rule_version、provenance 由当前函数计算。
- 缺失显式 null/unknown/missing，禁 0/"未知"填充、禁估算；评论/详情失败显式记录。
- 风险枚举：unknown 不并 negative、critical≠high、0/0≠0。

## 三、双域归属
- **CTH**：notes/note_comments、events 全族、topic_campaign_*、swire_*、brand_industry_monitor、industry_stats、weekly_events、case_deep_analysis、太古汇 feedback。
- **ZBMP**：web_mentions/runs/events/topics、brand_knowledge、brand_propagation、竞品/声量。
- **Shared**：collection_*、ai_filter_log、note_review_history、system_config、notification、v4_*、canonical/evidence/runtime。
- 199 品牌/9 业态只作用 CTH，不做 ZBMP 隐式过滤；拿不准归 unknown 列清单，不硬归。

## 四、业务规则同步找回（《规则功能映射表》，不丢不冲突）
双时间口径、subject 主体、平台采集口径、content_hash 去重、风险阈值与状态枚举、KOS 平台规则(官方+研究、不写死)、指标口径、报告结构、AI 判定/prompt、证据/评估、账户权限——每条记「来源→当前模块函数→已具备/缺失/冲突→适配动作→所属域」，已有保留不重写，缺的按双域补，冲突以当前规划为准。

## 五、执行步骤与对账（先小批后全量）
1. 整库备份当前 monitor.db（带时间戳）。
2. 固化《字段级映射 + 域归属 + 规则命中》代码化映射表（本规划为纲）。
3. 小批试迁：每表 20–50 条，校验字段/双时间/subject/hash/域标/去重/治理字段。
4. 对账通过后全量幂等迁移。
5. **逐表对账回报**：源数 / 新增 / 重复跳过 / 失败(原因) / 各域各表最终计数，对不上必须解释。
6. 迁完重算 canonical/evidence，由现有后端函数在 ZBMP/CTH 功能页真实读出，验证前后端契约一致、无 Mock/写死。

## 六、明确不做
不 raw dump、不照搬旧 schema、不恢复旧 UI/旧逻辑、不覆盖当前数据与新账户结构、不删任何源/备份、不动 C 类新表、不把 CTH 规则套到 ZBMP；代码废弃清理与数据迁移严格分开。

## 七、预计规模（真实）
需并入业务数据约：笔记 957、评论 143、事件族 1000+（events427+mentions562+graph/insights）、专题 445、审核历史 8327、web 200+、品牌业态 206、报告/日志/知识库等数百；以最终对账数为准。

## 八、本轮补充核实（真实代码/数据证据，约束执行）
1. **趋势按发布日——口径已正确，只需补全数据、不得改歪**：现有 `/api/trends/global`、`/api/overview`、subject 趋势均 `GROUP BY publish_date`（发布日）聚合，采集量/新鲜度才用 collected_at；两套口径分离保持。源库 957 条 notes 的 publish_datetime/publish_date/collected_at/captured_at **全部 957/957 非空**，按发布日 2026-08-21~08-30 每天 7~26 条连续可成图。迁移必须保证发布日 100% 回填，迁完 ZBMP/CTH 趋势图按发布日直接出曲线；双时间修复复用现成 `v4_upgrade/data_cleanup/fix_publish_date.py`，不另写。
2. **话题端监测与"用户任务"原样保全、可续跑**：源库 topic_campaigns 有真实任务 **taikoo_15th「广州太古汇十五周年」2026-08-28~10-07、status=paused、interval=240 分钟**；7 个监测话题词（十五周年/15周年/一方五境/广州太古汇/那年汇相遇/拾光五境/15周年促销）、topic_campaign_notes=120、snapshots=325。迁移须保留任务状态(paused)/起止/调度间隔/话题词启用态/笔记关联/快照时序，迁完当前话题监测功能能读到该任务并可继续，不丢任务、不重置状态。
3. **采集器与安全守卫已开发测试就绪——禁止重写/重复开发，只接入与修复阻断**：
   - collector_guard 15 模块齐全（guard/task_queue/queue_worker/runtime_guardian/checkpoint/dlq_replay/rate_limiter/resource_guard/risk_engine/state/metrics/analyzer/schedule_adapter/runtime_switch）。
   - v4_upgrade 65 模块：adapters 已覆盖 douyin/weibo/bilibili/zhihu/x/instagram/facebook/jiguang/微信搜狗/什么值得买/谷歌/点评/必应/百度/豆包搜索/human_browser/cookie_vault/dual_pool 等全平台，另有 collect/report_center/ai_hub/auth/importer/version_center/data_cleanup。
   - 主层 collector.py/collector_automation/xhs_cdp/collector_v2(xhs·weibo·scheduler)/collector_auto_start/status_api 齐全。
   - **采集规则全局通用、安全第一**：统一走 collector_guard + security 现有规则，不新建第二套；动作仅限接入主链、统一 cookie_vault、双域标识、修阻断问题。
4. **先全面本地审计再动手，禁止无意义开发**：对每个待补功能先查本地是否已有实现（主库/staging/security/OSAI/ADRH/backups），产出「已有可复用 / 需适配 / 真缺失」清单，已有直接复用或适配，不重复造轮子。
