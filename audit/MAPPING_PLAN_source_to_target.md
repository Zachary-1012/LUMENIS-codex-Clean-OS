# ZBC 历史数据适配性融合迁移 — 源表→目标表/字段映射方案

> 版本: v1.0 | 日期: 2026-09-06 | 旧库: monitor.staging.db (52表/13144行) | 新库: monitor.db (71表)

## 1. 总览

| 维度 | 旧库(staging) | 新库(monitor) | 适配策略 |
|------|---------------|---------------|----------|
| 表数 | 52 | 71 | 旧表字段映射到新表schema，不照搬 |
| notes | 957行/65列 | 6行→目标/69列 | 核心管线全适配，新增6列(content_hash/provenance/rule_version/product_id/subject_type/content_type) |
| 双时间 | publish_date+collected_at | publish_datetime+captured_at+collected_at | 严格分离，复用fix_publish_date.py归一化 |
| 主体判定 | 旧is_taikoo_verified标签 | subject_hit()重判 | 不沿用旧标签，SUBJECT_WORDS/EXCLUDE重判 |
| 域归属 | 无 | product_id(CTH/ZBMP/unknown) | 太古汇主体=CTH，web品牌传播=ZBMP，拿不准=unknown |

## 2. 核心表映射

### 2.1 notes (957→目标)

| 旧字段 | 新字段 | 映射规则 | 域/管线 |
|--------|--------|----------|---------|
| note_id | note_id | 直接映射，幂等键 | Shared |
| title | title | 直接映射，空则正文首句兜底 | Shared |
| content | content | 直接映射 | Shared |
| content | body | content兜底填充body | Shared |
| url/cover | url/cover | 直接映射 | Shared |
| author_id/nickname/avatar | 同 | 直接映射 | Shared |
| likes/comments/collects/shares | 同 | 直接映射，同时写metric_snapshots | Shared |
| note_type/xsec_token | 同 | 直接映射 | Shared |
| publish_date | publish_date | 归一化相对时间→绝对日期，100%回填 | Shared |
| publish_datetime | publish_datetime | 优先旧publish_datetime，其次publish_date，归一化 | **双时间铁律** |
| collected_at | collected_at | 直接映射(采集时刻旧列) | **双时间铁律** |
| captured_at | captured_at | 优先旧captured_at，其次collected_at，归一化 | **双时间铁律** |
| — | content_hash | md5(title\|body\|note_id)前16位，新增 | Canonical |
| — | provenance | "historical_import:staging_db_20260901"，新增 | Canonical |
| — | rule_version | "hist-v1.0"，新增 | Canonical |
| — | product_id | CTH/ZBMP/unknown，subject_hit判定，新增 | **双域归属** |
| is_taikoo_verified(旧) | is_taikoo_verified | **不沿用**，subject_hit()重判 | **subject红线** |
| verify_reason | verify_reason | subject_reason()生成，不沿用旧值 | subject红线 |
| sentiment/sentiment_score | 同 | 直接映射 | Shared |
| risk_level/risk_score | 同 | 直接映射 | Shared |
| summary/topics | 同 | 直接映射，topics保持JSON | Shared |
| ai_provider/ai_analyzed_at | 同 | 直接映射 | Shared |
| is_official/category/status | 同 | 直接映射 | Shared |
| last_seen_at | last_seen_at | 优先旧值，其次captured_at | Shared |
| relevance_status/verification_status | 同 | 直接映射 | Shared |
| verification_confidence/fact_basis | 同 | 直接映射 | Shared |
| ai_reason/event_hint | 同 | 直接映射 | Shared |
| translations | translations | 直接映射(JSON) | Shared |
| relevance_score/content_quality | 同 | 直接映射 | Shared |
| duplicate_of/ai_model | 同 | 直接映射 | Shared |
| last_reviewed_at | 同 | 直接映射 | Shared |
| ai_filter_status/reason/at | 同 | 直接映射 | Shared |
| content_quality_score/is_duplicate | 同 | 直接映射 | Shared |
| noise_type/ai_insight | 同 | 直接映射 | Shared |
| detail_fetched_at/comments_fetched_at | 同 | 直接映射 | Shared |
| comments_collected | 同 | 直接映射 | Shared |
| — | data_quality_status | 质量门禁自动判定(ok/warn/error)，新增 | 质量门禁 |
| — | data_quality_score | 质量门禁打分(0-100)，新增 | 质量门禁 |
| collector_version | collector_version | 旧值或"historical_import" | Shared |
| source_keyword/matched_keywords | 同 | 直接映射，参与subject_hit | subject红线 |
| negative_confirmed | 同 | 直接映射 | Shared |
| negative_confirmed_at/by | — | 旧库有，新库notes无此列，**丢弃**(审计信息存note_review_history) | — |
| source_platform | source_platform | 直接映射，默认xhs | Shared |

### 2.2 note_comments (141→目标)

schema完全兼容(11列)，直接映射。幂等键: comment_id。

| 旧字段 | 新字段 | 规则 |
|--------|--------|------|
| comment_id | comment_id | 幂等键 |
| note_id | note_id | 外键关联notes |
| content/author_id/author_nickname | 同 | 直接映射 |
| likes/publish_time/parent_id | 同 | 直接映射 |
| raw_json/fetched_at | 同 | 直接映射 |

### 2.3 events (427→目标)

schema完全兼容(22列)，直接映射。幂等键: event_key。
事件主体过滤由get_events()在查询时通过subject_hit()完成，迁移时不过滤。

### 2.4 web_mentions (79→目标)

schema完全兼容(24列)，直接映射。幂等键: source_id。
- published_at: GDELT格式(20260826T003000Z)归一化为标准时间
- fetched_at: 采集时刻，不与published_at混淆
- 域归属: web来源非CTH主体→ZBMP

### 2.5 topic_campaign系列 (硬约束#2)

| 表 | 旧行数 | 新行数(迁移前) | 映射策略 | 关键保留 |
|----|--------|---------------|----------|----------|
| topic_campaigns | 1 | 1 | campaign_key upsert，**强制保留旧status** | paused/2026-08-28~10-07/240min |
| topic_campaign_topics | 7 | 7 | id INSERT OR IGNORE | 7个topic全部enabled=1 |
| topic_campaign_snapshots | 325 | 65 | id INSERT OR IGNORE | 完整时间线，新增260条 |
| topic_campaign_notes | 120 | 0 | campaign_key+note_id upsert，24→16列适配 | 120条笔记关联 |

**topic_campaign_notes 列适配(24→16)**:
- 保留: campaign_key, topic, note_id, title, content, author, publish_datetime, likes, comments, collects, shares, note_url, first_seen_at, last_seen_at, raw_json
- 丢弃: media_json, comments_json, subject_hit, content_type, sentiment, risk_level, evidence_quality, detail_captured_at (新库无此列)

### 2.6 event_mentions (562→目标)

schema兼容(6列)，(event_id, source_type, source_id)组合唯一键。

### 2.7 审计表 (append-only, INSERT OR IGNORE by id)

| 表 | 旧行数 | 说明 |
|----|--------|------|
| note_review_history | 8327 | 审核历史，id主键，INSERT OR IGNORE |
| ai_filter_log | 827 | AI过滤日志，id主键，INSERT OR IGNORE |

### 2.8 运营/报告表

| 表 | 旧行数 | 幂等键 | 说明 |
|----|--------|--------|------|
| collection_logs | 477 | id | 采集日志 |
| daily_reports | 29 | id | 日报，新库多5列(artifact_hash等)留空 |
| daily_digest | 5 | digest_date | 每日摘要 |
| event_insights | 17 | id | 事件AI洞察 |
| collector_quality_log | 7 | id | 采集质量日志 |
| feedback_keywords | 16 | keyword | 反馈关键词 |
| web_sources | 1 | source_key | web采集源 |
| web_runs | 28 | id | web采集运行记录 |

## 3. 双时间铁律执行

```
publish_datetime = 平台发布时间
  来源优先级: 旧publish_datetime > 旧publish_date
  处理: 相对时间("N小时前"/"昨天"/"MM-DD")归一化为绝对时间
  工具: 复用 v4_upgrade/data_cleanup/fix_publish_date.py:parse_relative_date()
  回填: 迁移后调用 fix_publish_dates(apply=True) 确保100%回填

captured_at = 采集时刻
  来源优先级: 旧captured_at > 旧collected_at
  处理: 归一化，绝不与publish_datetime互相顶替

collected_at = 旧采集列(保留兼容)
  直接映射旧值

铁律校验: publish_datetime ≠ captured_at (来源不同字段)
```

## 4. subject_rules红线重判

```
不沿用旧库 is_taikoo_verified 标签
每条笔记调用 subject_hit(title, body, content, source_keyword, matched_keywords)
  - SUBJECT_WORDS (17词): 广州太古汇/太古汇/太古仓/汇悦台/LV太古汇/香奈儿太古汇...
  - SUBJECT_EXCLUDE_WORDS (18词): 上海太古汇/兴业太古汇/成都太古汇/三里屯...
  - 排除词一票否决 → 正向词任一命中
verify_reason = subject_reason() 生成可审计原因
```

迁移结果: 957条中 645条CTH主体命中, 312条unknown(非太古汇主体，保留但标unknown)

## 5. 双域归属

| product_id | 判定条件 | 数量 |
|------------|----------|------|
| CTH | subject_hit=True (太古汇/199品牌/9业态/太古汇事件) | 645 |
| ZBMP | web来源(gdelt/sogou_search/baidu/weibo等)且非CTH主体 | 0(旧库web均为CTH查询) |
| unknown | 非CTH主体且非明确ZBMP来源 | 312 |

199品牌/9业态不做隐式ZBMP过滤——所有小红书笔记默认CTH域，subject_hit未命中的标unknown。

## 6. 幂等upsert策略

| 表 | 幂等键 | 机制 |
|----|--------|------|
| notes | note_id | SELECT+INSERT/UPDATE (空值COALESCE不覆盖) |
| note_comments | comment_id | SELECT+INSERT/UPDATE |
| events | event_key | SELECT+INSERT/UPDATE |
| web_mentions | source_id | SELECT+INSERT/UPDATE |
| topic_campaigns | campaign_key | SELECT+INSERT/UPDATE (强制更新status) |
| topic_campaign_notes | campaign_key+note_id | SELECT+INSERT/UPDATE |
| event_mentions | event_id+source_type+source_id | SELECT+INSERT/UPDATE |
| id主键审计表 | id | INSERT OR IGNORE |
| daily_digest | digest_date | SELECT+INSERT/UPDATE |
| feedback_keywords | keyword | SELECT+INSERT/UPDATE |
| web_sources | source_key | SELECT+INSERT/UPDATE |

## 7. 对账口径

```
源计数 = 旧库 SELECT COUNT(*)
成功新增 = INSERT行数
重复跳过/更新 = UPDATE行数 (已存在幂等键)
失败原因 = 异常记录(前10条)
各域各表最终计数 = 迁移后新库 SELECT COUNT(*) + product_id GROUP BY

PASS: 失败=0
PARTIAL: 失败<5%
BLOCKED: 失败≥5%
```

## 8. 不迁移的旧库表(只读参考，不写入新库)

| 旧库表 | 行数 | 原因 |
|--------|------|------|
| brand_industry_monitor | 198 | 新库无对应表，属旧UI模块 |
| brand_knowledge | 103 | 新库有brand_knowledge(0行)但schema不同 |
| case_deep_analysis | 20 | 新库有对应表(0行)，schema待验证 |
| comments | 2 | 旧评论表，已被note_comments替代 |
| industry_stats | 8 | 新库无对应表 |
| schedule_decisions | 141 | 新库有schedule_decisions(10997行)，运营数据不覆盖 |
| swire_events | 10 | 新库有swire_events(10行)，已存在 |
| swire_projects | 8 | 新库有swire_projects(8行)，已存在 |
| v4_* (users/sessions/audit等) | — | 账户/安全系统数据，不迁移 |
| web_events/web_topics | 20/96 | 旧web模块，新库无对应表 |
| weekly_events | 30 | 旧周报模块，新库无对应表 |
| app_evidence_records | 0 | 空表 |
| notification_* | 0/3 | 新库有alert_*替代 |
| review_* | 0 | 空表 |
| token_stat | 1 | 运营统计，不迁移 |
| collection_counters | 1 | 运营计数器，不迁移 |
| schema_version | 7 | 版本元数据，不迁移 |
| v4_ai_shadow | 2 | AI影子数据，不迁移 |
