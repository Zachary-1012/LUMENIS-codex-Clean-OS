# ZBC 规则功能映射表 — 来源→当前模块函数→状态→适配动作→所属域

> 版本: v1.0 | 日期: 2026-09-06 | 覆盖: 双时间/subject/平台口径/去重/风险阈值与状态枚举/KOS/指标/报告/AI/证据/账户权限

## 1. 双时间规则

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| publish_datetime=平台发布时间 | 旧publish_date/publish_datetime | v4_upgrade/data_cleanup/fix_publish_date.py:parse_relative_date() | **已具备** | 复用，迁移时调用归一化相对时间 | Shared/CTH |
| captured_at=采集时刻 | 旧captured_at/collected_at | database.py:insert_note (captured_at字段) | **已具备** | 优先captured_at，回退collected_at | Shared |
| publish≠captured铁律 | 旧库可能混用 | migrate_historical_data.py:_normalize_publish_time() | **新增适配** | 严格分离两字段，不互相顶替 | Shared |
| 相对时间→绝对时间 | "N小时前"/"昨天"/"MM-DD" | fix_publish_date.py:parse_relative_date() | **已具备** | 复用，GDELT格式(20260826T003000Z)额外适配 | Shared |
| publish_date 100%回填 | 旧库957条均非空 | fix_publish_date.py:fix_publish_dates(apply=True) | **已具备** | 迁移后调用确保100%回填 | Shared/CTH |
| captured_at回填 | 旧captured_at可能为空 | fix_publish_date.py:backfill_captured_from_collected() | **已具备** | 迁移后调用 | Shared |

## 2. Subject主体规则

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| SUBJECT_WORDS正向词(17) | 旧库硬编码 | subject_rules.py:SUBJECT_WORDS | **已具备** | 复用，不修改 | CTH |
| SUBJECT_EXCLUDE_WORDS排除词(18) | 旧库硬编码 | subject_rules.py:SUBJECT_EXCLUDE_WORDS | **已具备** | 复用，排除词一票否决 | CTH |
| subject_hit()五字段判定 | 旧is_taikoo_verified标签 | subject_rules.py:subject_hit() | **已具备** | **重判不沿用旧标签**，迁移时每条调用 | CTH |
| subject_reason()可审计原因 | 旧verify_reason | subject_rules.py:subject_reason() | **已具备** | 迁移时重新生成，不沿用旧值 | CTH |
| subject_sql_and_values() SQL过滤 | 旧库SQL硬编码 | subject_rules.py:subject_sql_and_values() | **已具备** | 复用，查询时统一主体口径 | CTH |
| 多品牌配置(BRAND_PROFILES) | 旧库无 | subject_rules.py:BRAND_PROFILES | **已具备** | 广州太古汇为默认激活品牌，不切换 | CTH/KOS |
| rule_version快照 | 旧库无 | rule_version_registry表(hist-v1.0) | **已具备** | 迁移时写入rule_version="hist-v1.0" | Shared |

## 3. 平台口径

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| 小红书(xhs)默认平台 | 旧source_platform字段 | database.py:insert_note (默认xhs) | **已具备** | 直接映射source_platform | CTH |
| web多平台(gdelt/sogou等) | 旧web_mentions.source_platform | database.py:insert_web_mention | **已具备** | 直接映射，published_at归一化GDELT格式 | ZBMP |
| 平台唯一键(note_id/source_id) | 旧库同 | notes.note_id UNIQUE, web_mentions.source_id UNIQUE | **已具备** | 幂等upsert使用业务唯一键 | Shared |
| xsec_token | 旧库同 | notes.xsec_token | **已具备** | 直接映射 | CTH |

## 4. 去重规则

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| note_id唯一去重 | 旧库同 | notes.note_id UNIQUE | **已具备** | INSERT/UPDATE幂等 | Shared |
| source_id唯一去重 | 旧库同 | web_mentions.source_id UNIQUE | **已具备** | INSERT/UPDATE幂等 | ZBMP |
| content_hash内容哈希 | 旧库无 | notes.content_hash (新增列) | **新增适配** | md5(title\|body\|note_id)前16位，用于精准去重 | Shared |
| 标题相似不误删 | 旧库无 | database.py:find_duplicate_notes() (相似度0.7) | **已具备** | 迁移不自动删，仅标记is_duplicate | Shared |
| 缺失显式null不填0 | 旧库可能填0 | 迁移脚本_safe_int/_safe_str | **新增适配** | 缺失字段保留空串/NULL，不填0 | Shared |

## 5. 风险阈值与状态枚举

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| risk_level枚举(low/medium/high/critical) | 旧库同 | notes.risk_level, events.risk_level | **已具备** | 直接映射 | Shared |
| risk_score整数 | 旧库同 | notes.risk_score, events.risk_score | **已具备** | 直接映射 | Shared |
| sentiment枚举(positive/neutral/negative) | 旧库同 | notes.sentiment, web_mentions.sentiment | **已具备** | 直接映射 | Shared |
| sentiment_score浮点 | 旧库同 | notes.sentiment_score | **已具备** | 直接映射 | Shared |
| negative_confirmed(0待/1确认/2驳回) | 旧库同 | notes.negative_confirmed, events.negative_confirmed | **已具备** | 直接映射，events迁移后init_db校正event_date | Shared |
| status枚举(active/disappeared) | 旧库同 | notes.status | **已具备** | 直接映射，默认active | Shared |
| relevance_status枚举(relevant/irrelevant) | 旧库同 | notes.relevance_status | **已具备** | 直接映射，默认relevant | Shared |
| verification_status枚举(review/verified/rejected) | 旧库同 | notes.verification_status | **已具备** | 直接映射，默认review | Shared |
| fact_status枚举(unconfirmed/confirmed) | 旧库同 | events.fact_status | **已具备** | 直接映射 | Shared |
| impact枚举(neutral/positive/negative) | 旧库同 | events.impact | **已具备** | 直接映射 | Shared |

## 6. KOS多品牌

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| 多品牌配置(7品牌) | 旧库无 | subject_rules.py:BRAND_PROFILES | **已具备** | 本次迁移仅广州太古汇，其他品牌不涉及 | KOS |
| 品牌切换(ZBC_ACTIVE_BRAND) | 旧库无 | subject_rules.py:get_active_brand() | **已具备** | 默认guangzhou_taikoo_hui，不切换 | KOS |
| 199品牌/9业态不隐式过滤ZBMP | 旧库无 | 迁移脚本_classify_domain() | **新增适配** | 小红书笔记默认CTH域，subject未命中标unknown | CTH/KOS |
| kos_profiles/kos_executions等 | 旧库无 | 新库已有数据(481/225行) | **已具备** | 不迁移，新库KOS数据独立 | KOS |

## 7. 指标

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| 互动量四列(likes/comments/collects/shares) | 旧库同 | notes四列 + metric_snapshots | **已具备** | 直接映射，同时写metric_snapshots快照 | Shared |
| metric_snapshots时序快照 | 旧库无此表 | database.py:record_note_metric_snapshot() | **已具备** | 迁移时为每条笔记写一条快照(source=historical_import) | Shared |
| topic指标(browse/discussion/note_count) | 旧topic_campaign_snapshots | database.py:record_topic_snapshot() | **已具备** | topic_campaign_snapshots直接迁移，不重复写 | CTH |
| 趋势按publish_date GROUP BY | 旧库同 | /api/trends/global, /api/overview | **已具备** | **不修改**，确保publish_date 100%回填 | CTH/ZBMP |
| 采集量按collected_at | 旧库同 | collection_logs | **已具备** | 直接迁移collection_logs | Shared |

## 8. 报告

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| daily_reports日报 | 旧29行 | database.py:save_daily_report() | **已具备** | 直接迁移，新库多5列(artifact_hash等)留空 | Shared |
| daily_digest每日摘要 | 旧5行 | database.py:save_daily_digest() | **已具备** | digest_date唯一键upsert | Shared |
| 报告artifact真实性字段 | 旧库无 | daily_reports.report_id/artifact_hash/generator_version | **已具备** | 旧数据留空，新报告生成时填充 | Shared |
| event_insights事件洞察 | 旧17行 | database.py:save_event_insight() | **已具备** | id主键INSERT OR IGNORE | Shared |

## 9. AI

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| ai_filter_log AI过滤日志 | 旧827行 | database.py:update_note_ai_filter() | **已具备** | id主键INSERT OR IGNORE | Shared |
| ai_provider字段 | 旧库同 | notes.ai_provider (默认rule) | **已具备** | 直接映射 | Shared |
| ai_model/ai_reason/ai_insight | 旧库同 | notes对应列 | **已具备** | 直接映射 | Shared |
| 双域AI上下文隔离 | 旧库无 | ai_domain_context.py:CTH_CONTEXT/ZBMP_CONTEXT | **已具备** | 迁移不涉及AI调用，数据标注product_id | CTH/ZBMP |
| ai_call_logs | 旧库无 | 新库已有36行 | **已具备** | 不迁移，新库AI调用独立 | Shared |

## 10. 证据(Evidence)

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| canonical_data规范化数据 | 旧库无 | canonical_data.py + canonical_data表 | **已具备** | 迁移后可由canonical模块从notes生成，不自动生成 | Shared |
| zbc_evidence证据链 | 旧库无 | zbc_evidence表(新库6行) | **已具备** | 不迁移，新库证据独立 | CTH |
| zbc_lifecycle_tracking | 旧库无 | zbc_lifecycle_tracking表(新库8行) | **已具备** | 不迁移 | Shared |
| app_evidence_records | 旧0行 | app_evidence_records表 | **已具备** | 空表不迁移 | Shared |
| provenance溯源标记 | 旧库无 | notes.provenance (新增列) | **新增适配** | 所有迁移数据标"historical_import:staging_db_20260901" | Shared |

## 11. 账户权限

| 规则 | 来源(旧) | 当前模块函数 | 状态 | 适配动作 | 所属域 |
|------|----------|-------------|------|----------|--------|
| v4_users/v4_sessions | 旧1/31行 | 新库9/54行 | **已具备** | **不迁移**，账户系统独立，新库已有用户 | SYSTEM |
| v4_workspace_grants/keys | 旧3/2行 | 新库51/256行 | **已具备** | **不迁移**，权限独立 | SYSTEM |
| 双域权限(ZBMP≠CTH) | 旧库无 | account/authorization.py:check_dual_domain_permission() | **已具备** | 迁移数据标product_id，权限由运行时校验 | CTH/ZBMP |
| v4_audit_logs | 旧45行 | 新库15行 | **已具备** | 不迁移，审计日志独立 | SYSTEM |
| v4_login_attempts | 旧29行 | 新库3行 | **已具备** | 不迁移 | SYSTEM |

## 12. 状态汇总

| 状态 | 数量 | 说明 |
|------|------|------|
| 已具备(复用) | 52 | 当前模块已有函数/表，直接复用 |
| 新增适配 | 6 | content_hash/provenance/双时间分离/域归属/质量门禁/缺失null |
| 不迁移 | 12 | 账户/权限/KOS/AI调用/证据链等系统级数据，新库独立 |
| 冲突 | 0 | 无规则冲突 |

## 13. 本地审计结论(Reusable/Adapt/Missing)

| 类别 | 清单 |
|------|------|
| **Reusable(直接复用)** | subject_rules.py全套, fix_publish_date.py, database.py所有CRUD, canonical_data.py, ai_domain_context.py, account/authorization.py, metric_snapshots机制 |
| **Adapt(适配改造)** | 旧53表→新71表字段映射, 旧is_taikoo_verified→subject_hit重判, 旧publish_date相对时间→绝对时间, 旧24列topic_campaign_notes→新16列, 旧id主键表→INSERT OR IGNORE |
| **Missing(新增)** | notes.content_hash, notes.provenance, notes.rule_version, notes.product_id, 迁移脚本migrate_historical_data.py, 质量门禁自动判定 |
