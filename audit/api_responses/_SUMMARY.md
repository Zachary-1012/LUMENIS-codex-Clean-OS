# CTH-POMS 后端 API 真实响应审计汇总

- 审计时间：2026-09-08T00:47:29
- Base URL：`http://127.0.0.1:8201`
- 调用方式：仅 GET，只读，未修改任何源码/配置/数据库
- 鉴权方式：首次无凭证调用时 13/23 返回 401 (`auth_required:true, error:需要登录`)；随后通过系统自带白名单端点 `/api/auth/config` 获取合法 Basic auth header（前端动态注入机制，非伪造凭证），带凭证重调后全部 200。
- API 总数：23
- 2xx 成功：23；非 2xx/异常：0

## 一、响应总表

| # | API 路径 | HTTP 状态 | 响应类型 | 顶层字段 | 关键数据值 | 异常标记 |
|---|----------|-----------|----------|----------|------------|----------|
| 1 | `/api/overview` | 200 | JSON | active_events, ok, recent_negative, trend | active_events=157; recent_negative=9; trend[0].negative=1; trend[0].total=9; trend[1].negative=1; trend[1].total=15; trend[2].negative=2; trend[2].total=27 | - |
| 2 | `/api/status` | 200 | JSON | ai_detail, ai_enabled, ai_model, ai_provider, analyzer, auto_interval_minutes, collector, company_domain, data_source, last_collection, ok, qian_gua_integration, rednote_cdp_enabled, server_time, s... | last_collection.error_msg=; last_collection.notes_count=60; last_collection.status=SUCCESS; total_notes=701; version=5.9.9 | - |
| 3 | `/api/viz/overview.stats` | 200 | JSON | data, success | data.items[0].active_brands=0; data.items[0].total=2; success=True | - |
| 4 | `/api/viz/risk.active` | 200 | JSON | data, success | data.record_count=1; success=True | - |
| 5 | `/api/viz/overview.trend` | 200 | JSON | data, success | data.items[0].negative_count=0; data.items[0].note_count=7; data.items[1].negative_count=0; data.items[1].note_count=7; data.items[2].negative_count=0; data.items[2].note_count=7; success=True | - |
| 6 | `/api/brand-stats` | 200 | JSON | categories, ok, pie_data, top_brands, total_brands, total_notes, trend_data, updated_at | categories.女装.brand_count=47; categories.女装.negative_count=0; categories.女装.note_count=12; categories.珠宝钟表.brand_count=27; categories.珠宝钟表.negative_count=0; categories.珠宝钟表.note_count=10; categories.生活时尚.brand_count=6; categories.生活时尚.negative_count=0; categories.生活时尚.note_count=1; categories.男装.... | - |
| 7 | `/api/notes/library` | 200 | JSON | notes, ok, page, per_page, total, total_pages | notes[0].negative_confirmed=0; notes[0].risk_level=low; notes[0].risk_score=8; notes[0].summary=中性｜停车/保安｜低风险｜以信息记录与趋势观察为主; notes[1].negative_confirmed=0; notes[1].risk_level=low; notes[1].risk_score=0; notes[1].summary=中性｜一般讨论｜低风险｜以信息记录与趋势观察为主; notes[2].negative_confirmed=0; notes[2].risk_level=l... | - |
| 8 | `/api/negative/pending` | 200 | JSON | items, notes, ok, page, per_page, total | items[0].negative_confirmed=0; items[0].risk_level=medium; items[0].risk_score=28; items[0].summary=负面｜方所闭店、文化艺术｜中风险｜建议核查原始经历与互动扩散; items[1].negative_confirmed=0; items[1].risk_level=medium; items[1].risk_score=20; items[1].summary=方所闭店负面信息; items[2].negative_confirmed=0; items[2].risk_level=medi... | - |
| 9 | `/api/cases/stats` | 200 | JSON | by_category, by_risk, by_type, ok, total | total=18 | - |
| 10 | `/api/cases/taikoo-hui` | 200 | JSON | cases, count, ok | cases[0].risk_level=medium; cases[0].summary=小红书用户反映太古汇客服体验"简直跌破眼镜"，"整个对话感觉不像在解决问题，更像在证明是我的错"，客服态度冷冰冰。也有用户吐槽停车系统难用，服务人员不专业，交费整整花了十分钟才搞好。; cases[1].risk_level=medium; cases[1].summary=猫途鹰用户评价太古汇香奈儿专卖店购物体验极其糟糕，销售人员态度粗鲁、冷漠，让消费者感觉被评判，仿佛已经认定买不起任何东西，态度显得不耐烦且漠不关心，完全没有服务意识或热情。; cases[2].risk_level=high; ... | - |
| 11 | `/api/brand-industry/stats` | 200 | JSON | categories, industries, negative, negative_brands, ok, positive, positive_brands, total, total_brands | negative=9; negative_brands=9; total=198; total_brands=198 | - |
| 12 | `/api/negative-review/stats` | 200 | JSON | confirmed, high_risk, ok, pending, rejected, total | high_risk=17; pending=9; total=51 | - |
| 13 | `/api/weekly/events` | 200 | JSON | events, general, ok, period_end, period_start, urgent | - | 空数据: events=[], general=[], urgent=[] |
| 14 | `/api/notes/publish-buckets` | 200 | JSON | counts, date, historical_collected_today, ok, published_today | - | 空数据: historical_collected_today=[], published_today=[] |
| 15 | `/api/trends/global` | 200 | JSON | data, days, ok | data[0].negative=1; data[0].negative_pct=11.1; data[0].total=9; data[1].negative=1; data[1].negative_pct=6.7; data[1].total=15; data[2].negative=2; data[2].negative_pct=7.4; data[2].total=27 | - |
| 16 | `/api/dashboard/changes` | 200 | JSON | ok, server_time, stats, version | stats.high_risk=22; stats.low_risk=643; stats.medium_risk=35; stats.negative=57; stats.official_count=38; stats.total=701; stats.total_comments=27065; stats.total_engagements=343243; stats.total_likes=179918; stats.verified_count=701; version=5.9.9 | - |
| 17 | `/api/health` | 200 | JSON | database, ok, pid, port, service, time, version | version=5.9.9 | - |
| 18 | `/api/system/health` | 200 | JSON | health, ok | health.version=5.9.9 | - |
| 19 | `/api/system/database` | 200 | JSON | core, empty, non_empty, ok, table_count, tables | table_count=129; tables[0].count=11; tables[1].count=51; tables[2].count=1020 | - |
| 20 | `/lumenis/healthz` | 200 | JSON | component, layer, status | status=ok | - |
| 21 | `/api/metrics/canonical` | 200 | JSON | context, date, lineage, metric_version, metrics, ok | context.effective_count=0; context.events_count=0; context.neutral_count=0; context.positive_count=0; context.risk_count=0; context.total_found=0; metric_version=UDIP-V1.0 | 空数据: context.effective_count=0, context.events_count=0, context.neutral_count=0, context.positive_count=0, context.risk_count=0, context.total_found=0 |
| 22 | `/api/collector/quality` | 200 | JSON | ok, recent, total | recent[0].collector_version=rednote-v1.0; recent[0].detail_status=failed; recent[0].status=unknown; recent[1].collector_version=rednote-v1.0; recent[1].detail_status=failed; recent[1].status=unknown; recent[2].collector_version=rednote-v1.0; recent[2].detail_status=success; recent[2].status=high;... | - |
| 23 | `/api/platform-health` | 200 | JSON | counts, generated_at, needs_attention, needs_human, ok, overall, platforms | platforms[0].recovery.consecutive_network_fail=0; platforms[0].risk_status=NORMAL; platforms[0].status=SUCCESS; platforms[1].risk_status=; platforms[1].status=DISABLED; platforms[2].risk_status=; platforms[2].status=DISABLED | - |

## 二、各 API 字段明细（顶层 + 嵌套关键字段）

### 1. `/api/overview`

- 状态：200；Content-Type：`application/json`；耗时：95ms
- 顶层字段：`active_events`, `ok`, `recent_negative`, `trend`
- 嵌套关键字段（depth<=2）：
  - `active_events` · `ok` · `recent_negative` · `trend`
  - `trend[].date` · `trend[].high` · `trend[].label` · `trend[].negative`
  - `trend[].total`
- 关键数值：`active_events=157`; `recent_negative=9`; `trend[0].negative=1`; `trend[0].total=9`; `trend[1].negative=1`; `trend[1].total=15`; `trend[2].negative=2`; `trend[2].total=27`

### 2. `/api/status`

- 状态：200；Content-Type：`application/json`；耗时：480ms
- 顶层字段：`ai_detail`, `ai_enabled`, `ai_model`, `ai_provider`, `analyzer`, `auto_interval_minutes`, `collector`, `company_domain`, `data_source`, `last_collection`, `ok`, `qian_gua_integration`, `rednote_cdp_enabled`, `server_time`, `system`, `total_notes`, `unanalyzed`, `verified_notes`, `version`, `web_sources`
- 嵌套关键字段（depth<=2）：
  - `ai_detail` · `ai_enabled` · `ai_model` · `ai_provider`
  - `analyzer` · `auto_interval_minutes` · `collector` · `company_domain`
  - `data_source` · `last_collection` · `last_collection.error_msg` · `last_collection.finished_at`
  - `last_collection.id` · `last_collection.keyword` · `last_collection.notes_count` · `last_collection.started_at`
  - `last_collection.status` · `ok` · `qian_gua_integration` · `rednote_cdp_enabled`
  - `server_time` · `system` · `total_notes` · `unanalyzed`
  - `verified_notes` · `version` · `web_sources`
- 关键数值：`last_collection.error_msg=`; `last_collection.notes_count=60`; `last_collection.status=SUCCESS`; `total_notes=701`; `version=5.9.9`

### 3. `/api/viz/overview.stats`

- 状态：200；Content-Type：`application/json`；耗时：11ms
- 顶层字段：`data`, `success`
- 嵌套关键字段（depth<=2）：
  - `data` · `data.items` · `data.items[].active_brands` · `data.items[].engagement`
  - `data.items[].total` · `data.time_range` · `success`
- 关键数值：`data.items[0].active_brands=0`; `data.items[0].total=2`; `success=True`

### 4. `/api/viz/risk.active`

- 状态：200；Content-Type：`application/json`；耗时：15ms
- 顶层字段：`data`, `success`
- 嵌套关键字段（depth<=2）：
  - `data` · `data.current_value` · `data.level` · `data.record_count`
  - `success`
- 关键数值：`data.record_count=1`; `success=True`

### 5. `/api/viz/overview.trend`

- 状态：200；Content-Type：`application/json`；耗时：7ms
- 顶层字段：`data`, `success`
- 嵌套关键字段（depth<=2）：
  - `data` · `data.days` · `data.items` · `data.items[].day`
  - `data.items[].negative_count` · `data.items[].note_count` · `success`
- 关键数值：`data.items[0].negative_count=0`; `data.items[0].note_count=7`; `data.items[1].negative_count=0`; `data.items[1].note_count=7`; `data.items[2].negative_count=0`; `data.items[2].note_count=7`; `success=True`

### 6. `/api/brand-stats`

- 状态：200；Content-Type：`application/json`；耗时：87ms
- 顶层字段：`categories`, `ok`, `pie_data`, `top_brands`, `total_brands`, `total_notes`, `trend_data`, `updated_at`
- 嵌套关键字段（depth<=2）：
  - `categories` · `categories.女装` · `categories.女装.brand_count` · `categories.女装.brands`
  - `categories.女装.engagement` · `categories.女装.negative_count` · `categories.女装.note_count` · `categories.珠宝钟表`
  - `categories.珠宝钟表.brand_count` · `categories.珠宝钟表.brands` · `categories.珠宝钟表.engagement` · `categories.珠宝钟表.negative_count`
  - `categories.珠宝钟表.note_count` · `categories.生活时尚` · `categories.生活时尚.brand_count` · `categories.生活时尚.brands`
  - `categories.生活时尚.engagement` · `categories.生活时尚.negative_count` · `categories.生活时尚.note_count` · `categories.男装`
  - `categories.男装.brand_count` · `categories.男装.brands` · `categories.男装.engagement` · `categories.男装.negative_count`
  - `categories.男装.note_count` · `categories.童装玩具` · `categories.童装玩具.brand_count` · `categories.童装玩具.brands`
  - `categories.童装玩具.engagement` · `categories.童装玩具.negative_count` · `categories.童装玩具.note_count` · `categories.美容护理`
  - `categories.美容护理.brand_count` · `categories.美容护理.brands` · `categories.美容护理.engagement` · `categories.美容护理.negative_count`
  - `categories.美容护理.note_count` · `categories.运动休闲` · `categories.运动休闲.brand_count` · `categories.运动休闲.brands`
  - `categories.运动休闲.engagement` · `categories.运动休闲.negative_count` · `categories.运动休闲.note_count` · `categories.鞋包皮具`
  - `categories.鞋包皮具.brand_count` · `categories.鞋包皮具.brands` · `categories.鞋包皮具.engagement` · `categories.鞋包皮具.negative_count`
  - `categories.鞋包皮具.note_count` · `categories.餐饮` · `categories.餐饮.brand_count` · `categories.餐饮.brands`
  - `categories.餐饮.engagement` · `categories.餐饮.negative_count` · `categories.餐饮.note_count` · `ok`
  - `pie_data` · `pie_data[].brand_count` · `pie_data[].category` · `pie_data[].negative_count`
  - `pie_data[].note_count` · `pie_data[].percentage` · `top_brands` · `top_brands[].brand`
  - `top_brands[].category` · `top_brands[].engagement` · `top_brands[].negative_count` · `top_brands[].note_count`
  - `total_brands` · `total_notes` · `trend_data` · `trend_data[].date`
  - `trend_data[].negative_count` · `trend_data[].note_count` · `updated_at`
- 关键数值：`categories.女装.brand_count=47`; `categories.女装.negative_count=0`; `categories.女装.note_count=12`; `categories.珠宝钟表.brand_count=27`; `categories.珠宝钟表.negative_count=0`; `categories.珠宝钟表.note_count=10`; `categories.生活时尚.brand_count=6`; `categories.生活时尚.negative_count=0`; `categories.生活时尚.note_count=1`; `categories.男装.brand_count=8`; `categories.男装.negative_count=0`; `categories.男装.note_count=0`

### 7. `/api/notes/library`

- 状态：200；Content-Type：`application/json`；耗时：22ms
- 顶层字段：`notes`, `ok`, `page`, `per_page`, `total`, `total_pages`
- 嵌套关键字段（depth<=2）：
  - `notes` · `notes[].author_nickname` · `notes[].collected_at` · `notes[].collects`
  - `notes[].comments` · `notes[].likes` · `notes[].negative_confirmed` · `notes[].note_id`
  - `notes[].publish_date` · `notes[].risk_level` · `notes[].risk_score` · `notes[].sentiment`
  - `notes[].shares` · `notes[].source_platform` · `notes[].summary` · `notes[].title`
  - `notes[].url` · `ok` · `page` · `per_page`
  - `total` · `total_pages`
- 关键数值：`notes[0].negative_confirmed=0`; `notes[0].risk_level=low`; `notes[0].risk_score=8`; `notes[0].summary=中性｜停车/保安｜低风险｜以信息记录与趋势观察为主`; `notes[1].negative_confirmed=0`; `notes[1].risk_level=low`; `notes[1].risk_score=0`; `notes[1].summary=中性｜一般讨论｜低风险｜以信息记录与趋势观察为主`; `notes[2].negative_confirmed=0`; `notes[2].risk_level=low`; `notes[2].risk_score=0`; `notes[2].summary=广州太古汇韩料探店分享`

### 8. `/api/negative/pending`

- 状态：200；Content-Type：`application/json`；耗时：13ms
- 顶层字段：`items`, `notes`, `ok`, `page`, `per_page`, `total`
- 嵌套关键字段（depth<=2）：
  - `items` · `items[].author_nickname` · `items[].collected_at` · `items[].collects`
  - `items[].comments` · `items[].likes` · `items[].negative_confirmed` · `items[].note_id`
  - `items[].publish_date` · `items[].risk_level` · `items[].risk_score` · `items[].shares`
  - `items[].source_platform` · `items[].summary` · `items[].title` · `items[].url`
  - `notes` · `notes[].author_nickname` · `notes[].collected_at` · `notes[].collects`
  - `notes[].comments` · `notes[].likes` · `notes[].negative_confirmed` · `notes[].note_id`
  - `notes[].publish_date` · `notes[].risk_level` · `notes[].risk_score` · `notes[].shares`
  - `notes[].source_platform` · `notes[].summary` · `notes[].title` · `notes[].url`
  - `ok` · `page` · `per_page` · `total`
- 关键数值：`items[0].negative_confirmed=0`; `items[0].risk_level=medium`; `items[0].risk_score=28`; `items[0].summary=负面｜方所闭店、文化艺术｜中风险｜建议核查原始经历与互动扩散`; `items[1].negative_confirmed=0`; `items[1].risk_level=medium`; `items[1].risk_score=20`; `items[1].summary=方所闭店负面信息`; `items[2].negative_confirmed=0`; `items[2].risk_level=medium`; `items[2].risk_score=20`; `items[2].summary=负面｜一般讨论｜中风险｜建议核查原始经历与互动扩散`

### 9. `/api/cases/stats`

- 状态：200；Content-Type：`application/json`；耗时：6ms
- 顶层字段：`by_category`, `by_risk`, `by_type`, `ok`, `total`
- 嵌套关键字段（depth<=2）：
  - `by_category` · `by_category.会员服务` · `by_category.品牌经营` · `by_category.品牌质量`
  - `by_category.售后服务` · `by_category.商户经营` · `by_category.安全事件` · `by_category.服务态度`
  - `by_category.环保安全` · `by_category.行业趋势` · `by_category.设施安全` · `by_category.谣言事件`
  - `by_category.餐饮服务` · `by_risk` · `by_risk.high` · `by_risk.low`
  - `by_risk.medium` · `by_type` · `by_type.brand` · `by_type.other_mall`
  - `by_type.taikoo_hui` · `ok` · `total`
- 关键数值：`total=18`

### 10. `/api/cases/taikoo-hui`

- 状态：200；Content-Type：`application/json`；耗时：4ms
- 顶层字段：`cases`, `count`, `ok`
- 嵌套关键字段（depth<=2）：
  - `cases` · `cases[].brand_name` · `cases[].case_id` · `cases[].case_type`
  - `cases[].category` · `cases[].created_at` · `cases[].date` · `cases[].id`
  - `cases[].impact` · `cases[].keywords` · `cases[].lessons` · `cases[].mall_name`
  - `cases[].platform` · `cases[].response` · `cases[].risk_level` · `cases[].sentiment`
  - `cases[].source_url` · `cases[].summary` · `cases[].title` · `cases[].updated_at`
  - `count` · `ok`
- 关键数值：`cases[0].risk_level=medium`; `cases[0].summary=小红书用户反映太古汇客服体验"简直跌破眼镜"，"整个对话感觉不像在解决问题，更像在证明是我的错"，客服态度冷冰冰。也有用户吐槽停车系统难用，服务人员不专业，交费整整花了十分钟才搞好。`; `cases[1].risk_level=medium`; `cases[1].summary=猫途鹰用户评价太古汇香奈儿专卖店购物体验极其糟糕，销售人员态度粗鲁、冷漠，让消费者感觉被评判，仿佛已经认定买不起任何东西，态度显得不耐烦且漠不关心，完全没有服务意识或热情。`; `cases[2].risk_level=high`; `cases[2].summary=2026年3月，网友发文称在广州太古汇Sushi Hanzo Pro鮨·半藏寿司餐厅用餐时遭到一名男子当众性骚扰，事件引发广泛热议。品牌发布致歉声明称已协助报警并配合调查。`; `count=9`

### 11. `/api/brand-industry/stats`

- 状态：200；Content-Type：`application/json`；耗时：7ms
- 顶层字段：`categories`, `industries`, `negative`, `negative_brands`, `ok`, `positive`, `positive_brands`, `total`, `total_brands`
- 嵌套关键字段（depth<=2）：
  - `categories` · `industries` · `industries[].cnt` · `industries[].industry`
  - `negative` · `negative_brands` · `ok` · `positive`
  - `positive_brands` · `total` · `total_brands`
- 关键数值：`negative=9`; `negative_brands=9`; `total=198`; `total_brands=198`

### 12. `/api/negative-review/stats`

- 状态：200；Content-Type：`application/json`；耗时：36ms
- 顶层字段：`confirmed`, `high_risk`, `ok`, `pending`, `rejected`, `total`
- 嵌套关键字段（depth<=2）：
  - `confirmed` · `high_risk` · `ok` · `pending`
  - `rejected` · `total`
- 关键数值：`high_risk=17`; `pending=9`; `total=51`

### 13. `/api/weekly/events`

- 状态：200；Content-Type：`application/json`；耗时：16ms
- 顶层字段：`events`, `general`, `ok`, `period_end`, `period_start`, `urgent`
- 嵌套关键字段（depth<=2）：
  - `events` · `general` · `ok` · `period_end`
  - `period_start` · `urgent`

### 14. `/api/notes/publish-buckets`

- 状态：200；Content-Type：`application/json`；耗时：8ms
- 顶层字段：`counts`, `date`, `historical_collected_today`, `ok`, `published_today`
- 嵌套关键字段（depth<=2）：
  - `counts` · `counts.historical_collected_today` · `counts.published_today` · `date`
  - `historical_collected_today` · `ok` · `published_today`

### 15. `/api/trends/global`

- 状态：200；Content-Type：`application/json`；耗时：9ms
- 顶层字段：`data`, `days`, `ok`
- 嵌套关键字段（depth<=2）：
  - `data` · `data[].date` · `data[].high` · `data[].high_pct`
  - `data[].negative` · `data[].negative_pct` · `data[].total` · `days`
  - `ok`
- 关键数值：`data[0].negative=1`; `data[0].negative_pct=11.1`; `data[0].total=9`; `data[1].negative=1`; `data[1].negative_pct=6.7`; `data[1].total=15`; `data[2].negative=2`; `data[2].negative_pct=7.4`; `data[2].total=27`

### 16. `/api/dashboard/changes`

- 状态：200；Content-Type：`application/json`；耗时：462ms
- 顶层字段：`ok`, `server_time`, `stats`, `version`
- 嵌套关键字段（depth<=2）：
  - `ok` · `server_time` · `stats` · `stats.high_risk`
  - `stats.low_risk` · `stats.medium_risk` · `stats.negative` · `stats.neutral`
  - `stats.official_count` · `stats.positive` · `stats.total` · `stats.total_comments`
  - `stats.total_engagements` · `stats.total_likes` · `stats.verified_count` · `version`
- 关键数值：`stats.high_risk=22`; `stats.low_risk=643`; `stats.medium_risk=35`; `stats.negative=57`; `stats.official_count=38`; `stats.total=701`; `stats.total_comments=27065`; `stats.total_engagements=343243`; `stats.total_likes=179918`; `stats.verified_count=701`; `version=5.9.9`

### 17. `/api/health`

- 状态：200；Content-Type：`application/json`；耗时：28ms
- 顶层字段：`database`, `ok`, `pid`, `port`, `service`, `time`, `version`
- 嵌套关键字段（depth<=2）：
  - `database` · `ok` · `pid` · `port`
  - `service` · `time` · `version`
- 关键数值：`version=5.9.9`

### 18. `/api/system/health`

- 状态：200；Content-Type：`application/json`；耗时：469ms
- 顶层字段：`health`, `ok`
- 嵌套关键字段（depth<=2）：
  - `health` · `health.ai` · `health.ai.base_url` · `health.ai.detail`
  - `health.ai.enabled` · `health.ai.hints` · `health.ai.installed` · `health.ai.model`
  - `health.ai.provider` · `health.ai.running` · `health.ai.runtime` · `health.database`
  - `health.latest_data` · `health.service` · `health.time` · `health.verified_notes`
  - `health.version` · `health.web_discovery_enabled` · `ok`
- 关键数值：`health.version=5.9.9`

### 19. `/api/system/database`

- 状态：200；Content-Type：`application/json`；耗时：33ms
- 顶层字段：`core`, `empty`, `non_empty`, `ok`, `table_count`, `tables`
- 嵌套关键字段（depth<=2）：
  - `core` · `core.daily_reports` · `core.events` · `core.kos_operations`
  - `core.notes` · `empty` · `non_empty` · `ok`
  - `table_count` · `tables` · `tables[].count` · `tables[].name`
- 关键数值：`table_count=129`; `tables[0].count=11`; `tables[1].count=51`; `tables[2].count=1020`

### 20. `/lumenis/healthz`

- 状态：200；Content-Type：`application/json`；耗时：19ms
- 顶层字段：`component`, `layer`, `status`
- 嵌套关键字段（depth<=2）：
  - `component` · `layer` · `status`
- 关键数值：`status=ok`

### 21. `/api/metrics/canonical`

- 状态：200；Content-Type：`application/json`；耗时：52ms
- 顶层字段：`context`, `date`, `lineage`, `metric_version`, `metrics`, `ok`
- 嵌套关键字段（depth<=2）：
  - `context` · `context.collection_health` · `context.collection_health.complete` · `context.collection_health.detail`
  - `context.collection_health.state` · `context.effective_count` · `context.events_count` · `context.neutral_count`
  - `context.positive_count` · `context.risk_count` · `context.total_found` · `date`
  - `lineage` · `lineage.function` · `lineage.registry` · `lineage.source`
  - `metric_version` · `metrics` · `metrics.MET-RISK-01` · `metrics.MET-RISK-01.function`
  - `metrics.MET-RISK-01.name` · `metrics.MET-RISK-01.unit` · `metrics.MET-RISK-01.value` · `metrics.MET-RISK-02`
  - `metrics.MET-RISK-02.function` · `metrics.MET-RISK-02.name` · `metrics.MET-RISK-02.unit` · `metrics.MET-RISK-02.value`
  - `ok`
- 关键数值：`context.effective_count=0`; `context.events_count=0`; `context.neutral_count=0`; `context.positive_count=0`; `context.risk_count=0`; `context.total_found=0`; `metric_version=UDIP-V1.0`

### 22. `/api/collector/quality`

- 状态：200；Content-Type：`application/json`；耗时：5ms
- 顶层字段：`ok`, `recent`, `total`
- 嵌套关键字段（depth<=2）：
  - `ok` · `recent` · `recent[].checked_at` · `recent[].collector_version`
  - `recent[].comments_collected` · `recent[].detail_status` · `recent[].id` · `recent[].note_id`
  - `recent[].reason` · `recent[].score` · `recent[].status` · `total`
- 关键数值：`recent[0].collector_version=rednote-v1.0`; `recent[0].detail_status=failed`; `recent[0].status=unknown`; `recent[1].collector_version=rednote-v1.0`; `recent[1].detail_status=failed`; `recent[1].status=unknown`; `recent[2].collector_version=rednote-v1.0`; `recent[2].detail_status=success`; `recent[2].status=high`; `total=7`

### 23. `/api/platform-health`

- 状态：200；Content-Type：`application/json`；耗时：6ms
- 顶层字段：`counts`, `generated_at`, `needs_attention`, `needs_human`, `ok`, `overall`, `platforms`
- 嵌套关键字段（depth<=2）：
  - `counts` · `counts.disabled` · `counts.idle` · `counts.incident`
  - `counts.needs_human` · `counts.ok` · `counts.stop` · `generated_at`
  - `needs_attention` · `needs_human` · `ok` · `overall`
  - `platforms` · `platforms[].cooldown_until` · `platforms[].current_interval_sec` · `platforms[].enabled`
  - `platforms[].last` · `platforms[].last.at` · `platforms[].last.msg` · `platforms[].last.notes`
  - `platforms[].last.state` · `platforms[].message` · `platforms[].name` · `platforms[].needs_human`
  - `platforms[].next_run_at` · `platforms[].platform` · `platforms[].priority` · `platforms[].priority_label`
  - `platforms[].recovery` · `platforms[].recovery.consecutive_network_fail` · `platforms[].recovery.consecutive_no_new` · `platforms[].risk_status`
  - `platforms[].session_valid` · `platforms[].status` · `platforms[].stop_request` · `platforms[].triage`
  - `platforms[].verification_required`
- 关键数值：`platforms[0].recovery.consecutive_network_fail=0`; `platforms[0].risk_status=NORMAL`; `platforms[0].status=SUCCESS`; `platforms[1].risk_status=`; `platforms[1].status=DISABLED`; `platforms[2].risk_status=`; `platforms[2].status=DISABLED`

## 三、异常与空数据清单

| API 路径 | 状态 | 异常/空数据说明 |
|----------|------|-----------------|
| `/api/weekly/events` | 200 | 空数据: events=[], general=[], urgent=[] |
| `/api/notes/publish-buckets` | 200 | 空数据: historical_collected_today=[], published_today=[] |
| `/api/metrics/canonical` | 200 | 空数据: context.effective_count=0, context.events_count=0, context.neutral_count=0, context.positive_count=0, context.risk_count=0, context.total_found=0 |

---
本审计全程只读，未调用任何 POST/PUT/DELETE，未触发采集/备份/重建，未修改源码、配置或数据库。