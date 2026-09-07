# 数据库深度数据审计报告（只读）

- **数据库**: `D:\Taikoo-monitor-new\data\monitor.db` (SQLite)
- **审计时间基准**: 2026-09-08 23:59:59 (Asia/Shanghai)
- **审计模式**: 只读 (`uri=True, mode='ro'`)，全程仅 SELECT / PRAGMA
- **脚本**: `audit/db_deep_audit/_run_audit.py`
- **表总数**: 129（来自快照，实时复核）

---

## 1. 空表与异常表清单

- **实时空表数量**: 64 / 129
- **潜在显示风险表数量**: 27

### 1.1 潜在显示风险空表（前端可能期望有数据）

| 表名 | 潜在影响的页面/模块 |
|---|---|
| `xhs_notes` | 小红书笔记采集（旧表/旁路表），笔记搜索页可能回退查询 |
| `xhs_note_comments` | 小红书评论（旧表/旁路表），笔记详情评论区 |
| `xhs_users` | 小红书用户表，创作者/主体画像 |
| `platform_contents` | 统一多平台内容表，多平台 Adapter 主表 |
| `platform_comments` | 统一多平台评论表 |
| `platform_accounts` | 平台账号中心，Auth 状态与账号管理 |
| `platform_evidence` | 平台证据链 |
| `brands` | 品牌主数据表，多品牌管理 |
| `creators` | 传播主体/KOL/KOC 表，主体画像页 |
| `content_analysis` | 内容分析结果表 |
| `evaluation_records` | 内容评测记录 |
| `event_graph_events` | 事件图谱节点，事件关系页 |
| `event_graph_relations` | 事件图谱关系，事件因果溯源 |
| `brand_propagation_entities` | 品牌传播主体表 |
| `brand_propagation_events` | 品牌传播事件表 |
| `brand_knowledge` | 品牌知识库 |
| `case_deep_analysis` | 案例深度分析，品牌营销案例库 |
| `historical_import_log` | 历史导入日志 |
| `professional_accounts` | 专业账号表 |
| `professional_metrics` | 专业账号指标 |
| `runtime_guardian_dlq` | 运行守护死信队列 |
| `token_stat` | Token 统计 |
| `user_nav_config` | 用户导航配置 |
| `notification_config` | 通知配置 |
| `swire_notes` | Swire 笔记表（多品牌旁路） |
| `collection_runs` | 采集运行记录 |
| `collection_quality_log` | 采集质量日志 |

### 1.2 全部空表清单（64 张）

```
  bilibili_comments                 bilibili_users                    bilibili_videos                   brand_knowledge                 
  brand_propagation_entities        brand_propagation_events          brands                            case_deep_analysis              
  channels_comments                 channels_videos                   collection_quality_log            collection_runs                 
  content_analysis                  creators                          douyin_comments                   douyin_users                    
  douyin_videos                     evaluation_records                event_graph_events                event_graph_relations           
  github_issues                     github_pull_requests              github_releases                   github_repositories             
  historical_import_log             instagram_comments                instagram_media                   instagram_users                 
  linkedin_posts                    linkedin_users                    notification_config               platform_accounts               
  platform_comments                 platform_contents                 platform_evidence                 podcast_ai_runs                 
  podcast_entities                  professional_accounts             professional_metrics              reddit_comments                 
  reddit_posts                      reddit_subreddits                 runtime_guardian_dlq              swire_notes                     
  tiktok_comments                   tiktok_users                      tiktok_videos                     token_stat                      
  user_nav_config                   v4_login_approvals                v4_product_protection             v4_verification_codes           
  x_posts                           x_users                           xhs_note_comments                 xhs_notes                       
  xhs_users                         youtube_channels                  youtube_comments                  youtube_videos                  
  zhihu_answers                     zhihu_articles                    zhihu_comments                    zhihu_questions                 
```

---

## 2. notes 表深度分析（核心业务表）

- **总行数**: 1020
- **字段数**: 70

### 2.1 时间范围

- `publish_datetime` MIN: ``
- `publish_datetime` MAX: `2026-09-07`
- `captured_at` MIN: `2026-08-24 11:25:24`
- `captured_at` MAX: `2026-09-07 12:26:16`

- `publish_datetime` 为 NULL 或空字符串: **1** 条

### 2.2 平台分布

| 平台 | 记录数 |
|---|---|
| xiaohongshu | 794 |
| xhs | 219 |
| xiaohongshu-cdp | 7 |

### 2.3 主体命中字段分布

#### `is_taikoo_verified`

| 值 | 记录数 |
|---|---|
| 1 | 705 |
| 0 | 315 |

#### `subject_type`

| 值 | 记录数 |
|---|---|
| CTH | 489 |
| unknown | 312 |
| normal_user | 201 |
| official | 14 |
| kos | 3 |
| media | 1 |

#### `content_type`

| 值 | 记录数 |
|---|---|
|  | 801 |
| ugc | 202 |
| official | 14 |
| commercial | 3 |

#### `relevance_status`

| 值 | 记录数 |
|---|---|
| relevant | 704 |
| irrelevant | 316 |

#### `verification_status`

| 值 | 记录数 |
|---|---|
| review | 647 |
| rejected | 316 |
| verified | 57 |

#### `negative_confirmed`

| 值 | 记录数 |
|---|---|
| 0 | 955 |
| 1 | 54 |
| 2 | 11 |

### 2.4 最近 7 天记录数

#### 按 `publish_datetime`

| 日期 | 记录数 |
|---|---|
| 2026-09-01 | 7 |
| 2026-09-02 | 7 |
| 2026-09-03 | 2 |
| 2026-09-04 | 7 |
| 2026-09-05 | 7 |
| 2026-09-06 | 3 |
| 2026-09-07 | 2 |

#### 按 `captured_at`

| 日期 | 记录数 |
|---|---|
| 2026-09-04 | 3 |
| 2026-09-06 | 3 |
| 2026-09-07 | 57 |

### 2.5 标题/内容空值

- `title` 为 NULL 或空: **0** 条
- `content` 为 NULL 或空: **313** 条

---

## 3. events 表深度分析

- **总行数**: 494
- **字段数**: 26

### 3.1 事件类型分布 (`event_type`)

| 类型 | 记录数 |
|---|---|
| None | 494 |

### 3.2 严重程度分布 (`severity`)

| 严重程度 | 记录数 |
|---|---|
| None | 494 |

### 3.3 风险等级分布 (`risk_level`)

| 风险等级 | 记录数 |
|---|---|
| low | 433 |
| medium | 53 |
| high | 8 |

### 3.4 时间范围

- `first_seen` MIN: `2024-07-08`  MAX: `编辑于 2025-08-22`
- `last_seen` MIN: `2024-07-15`  MAX: `编辑于 2025-08-22`
- `event_date` MIN: `2024-07-08`  MAX: `2026-09-06`

### 3.5 关联笔记数统计 (`mention_count`)

- MIN: 1  MAX: 14  AVG: 1.23  SUM: 607

### 3.6 最近 30 天事件数

- 最近 30 天事件总数: **304**

| 日期 | 事件数 |
|---|---|
| 2026-08-10 | 6 |
| 2026-08-11 | 6 |
| 2026-08-12 | 9 |
| 2026-08-13 | 1 |
| 2026-08-14 | 15 |
| 2026-08-15 | 6 |
| 2026-08-16 | 14 |
| 2026-08-17 | 13 |
| 2026-08-18 | 10 |
| 2026-08-19 | 8 |
| 2026-08-20 | 5 |
| 2026-08-21 | 14 |
| 2026-08-22 | 5 |
| 2026-08-23 | 17 |
| 2026-08-24 | 13 |
| 2026-08-25 | 10 |
| 2026-08-26 | 14 |
| 2026-08-27 | 16 |
| 2026-08-28 | 26 |
| 2026-08-29 | 15 |
| 2026-08-30 | 19 |
| 2026-08-31 | 4 |
| 2026-09-01 | 10 |
| 2026-09-02 | 13 |
| 2026-09-03 | 3 |
| 2026-09-04 | 12 |
| 2026-09-05 | 11 |
| 2026-09-06 | 6 |
| 2026-09-07 | 3 |

---

## 4. daily_reports 表深度分析

- **总行数**: 39
- **字段数**: 35

- **报告日期范围**: `2026-08-27` ~ `2026-09-08`

### 4.1 日期断层

发现 **1** 处日期断层：

| 起始 | 结束 | 缺失天数 | 缺失日期 |
|---|---|---|---|
| 2026-08-31 | 2026-09-04 | 3 | 2026-09-01, 2026-09-02, 2026-09-03 |

### 4.2 每份报告关键指标

| report_date | report_type | total_notes | positive_count | neutral_count | negative_count | high_risk_count | medium_risk_count | low_risk_count | total_likes | total_comments | total_engagements | risk_index | brand_health_score | generated_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-27 | monthly | 88 | 15 | 61 | 12 | 2 | 4 | 82 | 3438 | 1649 | 10460 | 0.0 | 0.0 | 2026-08-27 23:55:18 |
| 2026-08-27 | yearly | 211 | 38 | 132 | 41 | 11 | 9 | 191 | 90466 | 8586 | 135865 | 0.0 | 0.0 | 2026-08-27 23:55:18 |
| 2026-08-28 | daily | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 5 | 4 | 32 | 0.0 | 0.0 | 2026-08-28 12:47:24 |
| 2026-08-29 | daily | 5 | 0 | 5 | 0 | 0 | 0 | 5 | 57 | 24 | 132 | 0.0 | 0.0 | 2026-08-29 23:55:57 |
| 2026-08-29 | weekly | 67 | 27 | 35 | 5 | 0 | 3 | 64 | 1515 | 720 | 3326 | 0.0 | 0.0 | 2026-08-29 23:55:58 |
| 2026-08-29 | monthly | 171 | 87 | 71 | 13 | 2 | 10 | 159 | 5891 | 2499 | 15534 | 0.0 | 0.0 | 2026-08-29 23:55:58 |
| 2026-08-29 | yearly | 372 | 205 | 135 | 32 | 14 | 17 | 341 | 102095 | 11864 | 163420 | 0.0 | 0.0 | 2026-08-29 23:55:58 |
| 2026-08-30 | daily | 15 | 0 | 12 | 3 | 0 | 2 | 13 | 685 | 205 | 3116 | 0.0 | 0.0 | 2026-08-30 23:55:22 |
| 2026-08-30 | weekly | 104 | 31 | 65 | 8 | 0 | 5 | 99 | 5729 | 1275 | 15949 | 0.0 | 0.0 | 2026-08-30 23:55:24 |
| 2026-08-30 | monthly | 221 | 93 | 112 | 16 | 2 | 13 | 206 | 12932 | 3307 | 32043 | 0.0 | 0.0 | 2026-08-30 23:55:24 |
| 2026-08-30 | yearly | 444 | 216 | 193 | 35 | 14 | 21 | 409 | 113459 | 13418 | 188359 | 0.0 | 0.0 | 2026-08-30 23:55:24 |
| 2026-08-31 | daily | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-08-31 23:55:19 |
| 2026-08-31 | weekly | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-08-31 23:55:24 |
| 2026-08-31 | monthly | 221 | 95 | 110 | 16 | 2 | 13 | 206 | 12932 | 3307 | 32043 | 0.0 | 0.0 | 2026-08-31 23:55:24 |
| 2026-08-31 | yearly | 444 | 218 | 191 | 35 | 14 | 21 | 409 | 113459 | 13418 | 188359 | 0.0 | 0.0 | 2026-08-31 23:55:25 |
| 2026-09-04 | daily | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-04 23:55:04 |
| 2026-09-04 | weekly | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-04 23:55:05 |
| 2026-09-04 | monthly | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-04 23:55:05 |
| 2026-09-04 | yearly | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-04 23:55:05 |
| 2026-09-04 | special | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-04 23:55:05 |
| 2026-09-05 | daily | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-05 23:55:19 |
| 2026-09-05 | weekly | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-05 23:55:20 |
| 2026-09-05 | monthly | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-05 23:55:20 |
| 2026-09-05 | yearly | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-05 23:55:20 |
| 2026-09-05 | special | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-05 23:55:20 |
| 2026-09-06 | daily | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 2026-09-06 23:55:58 |
| 2026-09-06 | weekly | 3 | 0 | 3 | 0 | 0 | 0 | 3 | 1750 | 374 | 2689 | 0.0 | 0.0 | 2026-09-06 23:56:01 |
| 2026-09-06 | monthly | 3 | 0 | 3 | 0 | 0 | 0 | 3 | 1750 | 374 | 2689 | 0.0 | 0.0 | 2026-09-06 23:56:01 |
| 2026-09-06 | yearly | 474 | 245 | 194 | 35 | 14 | 21 | 439 | 118158 | 14678 | 196509 | 0.0 | 0.0 | 2026-09-06 23:56:02 |
| 2026-09-06 | special | 200 | 92 | 94 | 14 | 2 | 10 | 188 | 14867 | 3635 | 34221 | 0.0 | 0.0 | 2026-09-06 23:56:02 |
| 2026-09-07 | daily | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 10 | 2 | 24 | 0.0 | 0.0 | 2026-09-07 23:59:59 |
| 2026-09-07 | weekly | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 10 | 2 | 24 | 0.0 | 0.0 | 2026-09-07 23:59:16 |
| 2026-09-07 | monthly | 35 | 2 | 30 | 3 | 0 | 4 | 30 | 3743 | 811 | 6718 | 0.0 | 0.0 | 2026-09-07 23:59:18 |
| 2026-09-07 | yearly | 527 | 250 | 239 | 38 | 14 | 25 | 487 | 120322 | 16407 | 203332 | 0.0 | 0.0 | 2026-09-07 23:59:19 |
| 2026-09-07 | special | 242 | 94 | 131 | 17 | 2 | 14 | 225 | 15320 | 5119 | 38078 | 0.0 | 0.0 | 2026-09-07 23:59:20 |
| 2026-09-08 | weekly | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 10 | 2 | 24 | 0.0 | 0.0 | 2026-09-08 00:00:05 |
| 2026-09-08 | monthly | 35 | 2 | 30 | 3 | 0 | 4 | 30 | 3743 | 811 | 6718 | 0.0 | 0.0 | 2026-09-08 00:00:06 |
| 2026-09-08 | yearly | 527 | 250 | 239 | 38 | 14 | 25 | 487 | 120322 | 16407 | 203332 | 0.0 | 0.0 | 2026-09-08 00:00:07 |
| 2026-09-08 | special | 235 | 93 | 128 | 14 | 1 | 12 | 221 | 14408 | 4838 | 34573 | 0.0 | 0.0 | 2026-09-08 00:00:07 |

---

## 5. note_comments 表

- **总行数**: 141
- **字段数**: 11

### 5.1 关联笔记分布（Top 20）

| note_id | 评论数 |
|---|---|
| 69a7f7980000000015031ecc | 20 |
| 6a7f084d000000002c005fe1 | 20 |
| 6a8861f30000000023013f59 | 19 |
| 6a5e02eb000000001102e16c | 17 |
| 6a7c2ee9000000002403ef20 | 16 |
| 69ab034c000000001d025bd8 | 15 |
| 6a11757f0000000035021f45 | 12 |
| 6a83060b0000000028008e31 | 11 |
| 68a5bdbd000000001d02f02e | 5 |
| 6a68290900000000010338cb | 4 |
| 69d24830000000002202bbb5 | 2 |

- **有评论的笔记数（DISTINCT note_id）**: 11

### 5.2 时间范围

- `publish_time` MIN: `03-04上海`  MAX: `昨天 09:45浙江`
- `fetched_at` MIN: `2026-08-27 01:50:12`  MAX: `2026-08-29 17:15:01`

---

## 6. event_mentions 表

- **总行数**: 789
- **字段数**: 6

### 6.1 事件分布（Top 20）

| event_id | mention 数 |
|---|---|
| 3 | 29 |
| 20 | 22 |
| 150 | 22 |
| 156 | 15 |
| 1 | 12 |
| 153 | 10 |
| 219 | 9 |
| 220 | 9 |
| 7 | 8 |
| 221 | 7 |
| 354 | 7 |
| 223 | 6 |
| 355 | 6 |
| 2 | 5 |
| 53 | 5 |
| 162 | 5 |
| 222 | 5 |
| 230 | 5 |
| 284 | 5 |
| 10 | 4 |

- **涉及事件数（DISTINCT event_id）**: 484


### 6.2 source_type 分布

| source_type | 记录数 |
|---|---|
| xiaohongshu | 562 |
| xhs | 227 |

### 6.3 时间范围

- `created_at` MIN: `2026-08-26 18:27:59`  MAX: `2026-09-07 18:03:09`

---

## 7. brand_industry_monitor 表

- **总行数**: 198
- **字段数**: 12

### 7.1 品牌分布（Top 20）

| 品牌 | 记录数 |
|---|---|
| - | 1 |
| 1730 MUSEE DU PAIN | 1 |
| A BATHING APE、I.T | 1 |
| ACQUA DI PARMA | 1 |
| Acne Studios | 1 |
| Aesop | 1 |
| Ah Ma Hand made | 1 |
| Alexander McQueen | 1 |
| American Vintage | 1 |
| Arc'teryx | 1 |
| BALENCIAGA GUANGZHOU TAIKOO HUI STORE | 1 |
| BERLUTI | 1 |
| BONPOINT | 1 |
| BOTTEGA VENETA | 1 |
| BUCCELLATI | 1 |
| BURBERRY | 1 |
| BVLGARI | 1 |
| BYREDO | 1 |
| Bang & Olufsen | 1 |
| Blancpain | 1 |


### 7.2 行业分布

| 行业 | 记录数 |
|---|---|
| 女装 Ladies' Fashion | 48 |
| 餐饮 Food & Beverages | 41 |
| 珠宝/钟表/饰品 Jewellery/Watches/Accessories | 36 |
| 保健/美容护理 Health/Beauty | 27 |
| 休闲服/运动用品 Casual Wear/Sports | 25 |
| 鞋/包/皮具用品 Shoes/Bags/Leather Goods | 8 |
| 男装 Men's Fashion | 8 |
| 生活时尚 Life Style | 5 |

### 7.3 时间范围

- `last_updated` MIN: `2026-08-29 13:15:09`  MAX: `2026-08-29 13:15:10`

### 7.4 关键字段 NULL/空值率

| 字段 | NULL/空值数 | NULL率 |
|---|---|---|
| `brand_name` | 0 | 0.0% |
| `industry` | 0 | 0.0% |
| `floor` | 0 | 0.0% |
| `shop_number` | 6 | 3.03% |
| `note_count` | 0 | 0.0% |
| `negative_count` | 0 | 0.0% |
| `positive_count` | 0 | 0.0% |
| `total_engagement` | 0 | 0.0% |
| `risk_level` | 0 | 0.0% |
| `last_updated` | 0 | 0.0% |

---

## 8. metric_snapshots 表

- **总行数**: 1087
- **字段数**: 14

### 8.1 指标类型分布 (`entity_type`)

| entity_type | 记录数 |
|---|---|
| note | 1087 |

### 8.2 时间范围

- `snapshot_at` MIN: `2026-08-24 11:25:24`  MAX: `2026-09-07 12:26:16`

### 8.3 最新一条快照

```json
{
  "id": 1084,
  "entity_type": "note",
  "entity_key": "68fb7a02000000000703811f",
  "likes": 170,
  "comments": 14,
  "collects": 44,
  "shares": 67,
  "browse_count": null,
  "discussion_count": null,
  "note_count": null,
  "raw_json": "{}",
  "source": "live",
  "collector_version": "",
  "snapshot_at": "2026-09-07 12:26:16"
}
```

---

## 9. 时间口径专项检查（notes 表）

### 9.1 `publish_datetime` 与 `captured_at` 差异超过 7 天

- **差异 > 7 天的记录数**: 826

差异最大的 20 条样本：

| note_id | title | publish | captured | 差异天数 |
|---|---|---|---|---|
| 5a539803eb00f31709eb1351 | 广州太古汇网红厕所踩点 | 2018-01-08 | 2026-08-24 16:51:51 | 3150.7 |
| 5adb663b910cf64bffce6dd1 | 无标题笔记 | 2018-04-21 | 2026-08-24 16:52:39 | 3047.7 |
| 5b753791672e147958777e85 | 无标题笔记 | 2018-08-16 | 2026-08-24 16:51:49 | 2930.7 |
| 5bce5f45910cf646de1d30be | 无标题笔记 | 2018-10-22 | 2026-08-24 16:51:55 | 2863.7 |
| 5c64cfcb000000000d00bf53 | 无标题笔记 | 2019-02-14 | 2026-08-24 16:52:44 | 2748.7 |
| 5d91a9b7000000000401d826 | 宝格丽换包售后 | 2019-09-30 | 2026-08-24 16:52:40 | 2520.7 |
| 5e8195940000000001000967 | 广州太古汇厕所 | 2020-03-30 | 2026-08-24 16:51:47 | 2338.7 |
| 5f01ad6d00000000010027ee | 宝格丽质量太差，修理需要2个月，坐标伦敦 | 2020-07-05 | 2026-08-24 16:52:44 | 2241.7 |
| 5f95ca9e0000000001005969 | 广州太古汇控诉 | 2020-10-25 | 2026-08-27 11:46:13 | 2132.5 |
| 616d7184000000000102e48c | 来自太古汇保安叔叔的关爱 | 2021-10-18 | 2026-08-27 13:01:53 | 1774.5 |
| 61811f24000000002103b9b9 | 广州太古汇安保工作人员真的太赞👍🏻 | 2021-11-02 | 2026-08-27 11:46:13 | 1759.5 |
| 628a2faa000000000102a443 | 求助贴！怎么投诉太古汇爱马仕销售！ | 2022-05-22 | 2026-08-27 11:46:13 | 1558.5 |
| 62c582ce0000000021038139 | 服了 才带一周的宝格丽 | 2022-07-06 | 2026-08-24 16:52:40 | 1510.7 |
| 634810c10000000008017595 | 太古汇 | 2022-10-13 | 2026-08-27 11:46:13 | 1414.5 |
| 63639f1b000000000703493a | 广州太古汇🚾·假装在看展 | 2022-11-03 | 2026-08-24 16:51:49 | 1390.7 |
| 6448dc030000000013005cf3 | 广州太古汇viviennewestwood | 2023-04-26 | 2026-08-27 11:46:13 | 1219.5 |
| 6447a263000000000800c417 | 打卡太古汇的厕所 | 2023-04-25 | 2026-08-24 16:51:47 | 1217.7 |
| 64cbafbd0000000017018155 | 广州太古汇 天河城今日消费账单 | 2023-08-03 | 2026-08-24 16:51:29 | 1117.7 |
| 64e4d27a000000001700ce54 | 神奇太古汇，大家去的时候注意⚠️一下 | 2023-08-22 | 2026-08-24 16:51:47 | 1098.7 |
| 659946f9000000000f031d31 | 广州太古汇 | 2024-01-06 | 2026-08-27 11:46:13 | 964.5 |

### 9.2 未来时间异常（`publish_datetime` > 当前时间）

- **未来时间记录数**: 0

### 9.3 异常旧数据（`publish_datetime` < 2020-01-01）

- **早于 2020-01-01 的记录数**: 6

| note_id | title | publish_datetime |
|---|---|---|
| 5b753791672e147958777e85 | 无标题笔记 | 2018-08-16 |
| 5a539803eb00f31709eb1351 | 广州太古汇网红厕所踩点 | 2018-01-08 |
| 5bce5f45910cf646de1d30be | 无标题笔记 | 2018-10-22 |
| 5adb663b910cf64bffce6dd1 | 无标题笔记 | 2018-04-21 |
| 5d91a9b7000000000401d826 | 宝格丽换包售后 | 2019-09-30 |
| 5c64cfcb000000000d00bf53 | 无标题笔记 | 2019-02-14 |

---

## 10. 主体口径专项检查（notes 表）

- **总行数**: 1020

### `is_taikoo_verified`

- NULL/空值数: **0**

| 值 | 记录数 |
|---|---|
| 1 | 705 |
| 0 | 315 |

### `subject_type`

- NULL/空值数: **0**

| 值 | 记录数 |
|---|---|
| CTH | 489 |
| unknown | 312 |
| normal_user | 201 |
| official | 14 |
| kos | 3 |
| media | 1 |

### `content_type`

- NULL/空值数: **801**

| 值 | 记录数 |
|---|---|
|  | 801 |
| ugc | 202 |
| official | 14 |
| commercial | 3 |

### `relevance_status`

- NULL/空值数: **0**

| 值 | 记录数 |
|---|---|
| relevant | 704 |
| irrelevant | 316 |

### `verification_status`

- NULL/空值数: **0**

| 值 | 记录数 |
|---|---|
| review | 647 |
| rejected | 316 |
| verified | 57 |

---

## 附录：输出文件清单

| 文件 | 内容 |
|---|---|
| `empty_tables.json` | 空表清单与潜在风险表 |
| `notes_detail.json` | notes 表全部查询结果 |
| `events_detail.json` | events 表全部查询结果 |
| `daily_reports_detail.json` | daily_reports 表全部查询结果 |
| `note_comments_detail.json` | note_comments 表全部查询结果 |
| `event_mentions_detail.json` | event_mentions 表全部查询结果 |
| `brand_industry_monitor_detail.json` | brand_industry_monitor 表全部查询结果 |
| `metric_snapshots_detail.json` | metric_snapshots 表全部查询结果 |
| `time_consistency.json` | 时间口径专项检查结果 |
| `subject_consistency.json` | 主体口径专项检查结果 |
| `_run_audit.py` | 只读审计脚本（可复跑） |
