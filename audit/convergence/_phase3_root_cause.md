# Phase 3 趋势数据闭环 - 根因定位（groundwork 已完成）

## 基线
- 当前日期：2026-09-07
- trend_api.py 路径：D:\Taikoo-monitor-new\trend_api.py
- DB：data/monitor.db

## 1. Events 趋势 /api/trend/events — 契约错误（非真0）

### 根因
trend_events() 遍历的时间列白名单 `_EVENT_TIME_COLUMNS = {'start_time', 'discovered_at', 'created_at', 'first_seen_at'}` 中，**4列在 events 表中全部不存在**。每个查询都抛异常被 except 吞掉，最终返回全0。

### events 表实际时间列（PRAGMA 确认）
- `first_seen` TEXT — 格式 'YYYY-MM-DD'，示例 '2026-08-06'
- `last_seen` TEXT — 格式 'YYYY-MM-DD'
- `event_date` TEXT — 格式 'YYYY-MM-DD'，示例 '2026-08-03'
- `negative_confirmed_at` TEXT — 格式 'YYYY-MM-DD HH:MM:SS'

### 修复方向
1. 将 `first_seen`、`event_date` 加入 `_EVENT_TIME_COLUMNS` 白名单
2. 将列遍历顺序改为 `['event_date', 'first_seen', 'last_seen', 'negative_confirmed_at']`（优先 event_date）
3. 验证：461行events中 event_date 非空的应能聚合出近期数据

## 2. Risk 趋势 /api/trend/risk — 契约错误（非真0）

### 根因
trend_risk() 遍历的表 `_RISK_TABLES = {'risk_records', 'risks', 'note_risk_log'}` 三表**全部为空**（0行）。风险数据实际存储在：
- `events` 表：有 `risk_level`（TEXT, 'high'/'medium'/'low'）和 `risk_score`（INTEGER）列，461行
- `notes` 表：有 `risk_level` 和 `risk_score` 列，1020行
- `alert_configs` 表：13行（配置类，非记录）

### 修复方向
1. 增加从 `events` 表按 `event_date`/`first_seen` 聚合 risk_level 的查询
2. 可增加从 `notes` 表按 `publish_datetime` 聚合 risk_level 的查询（作为补充维度）
3. 保留对 risk_records/risks/note_risk_log 的尝试（向后兼容），但优先查 events
4. risk_level 值需确认：events 中实际值为 'high'/'medium'/'low'，与代码中 by_date 的 key 一致

## 3. KOS 趋势 /api/trend/kos — 过滤不足（接近真0但应修正）

### 根因
trend_kos() 用 `n.subject_type LIKE '%kos%' OR n.subject_type LIKE '%kol%' OR n.subject_type LIKE '%koc%'` 过滤，但 notes 表 subject_type 分布为：
- CTH: 489, unknown: 312, normal_user: 201, official: 14, **kos: 3**, media: 1

仅3条 notes 的 subject_type='kos'。但 `kos_profiles` 表有 **375个 is_kos=1 的达人**，这些达人发布的笔记 subject_type 可能是 CTH/unknown/official 等。

### 修复方向
1. 将查询改为 `notes n JOIN kos_profiles k ON n.author_id = k.author_id WHERE k.is_kos = 1`
2. 保留 subject_type LIKE 过滤作为 OR 补充（兼容未入 kos_profiles 但标记为 kos 的笔记）
3. 验证：JOIN 后应能聚合出 KOS 达人的笔记发布趋势

## 4. 其他趋势端点（已确认正常）
- /api/trend/notes：正常，按 publish_datetime 聚合 + 主体过滤
- /api/trend/engagement：正常，基于 notes 表
- /api/trend/sentiment：基于 notes 表 sentiment 列，需验证但逻辑正确
- /api/trend/overview：仅返回 notes+engagement，未包含 events/risk/kos（可后续增强）

## 验收标准
修复后用真实 DB + 运行中 Flask 验证：
- /api/trend/events?days=30 返回非全0 series（events 表有8月数据）
- /api/trend/risk?days=30 返回非全0 series（events 表有 risk_level 数据）
- /api/trend/kos?days=30 返回非全0 series（JOIN kos_profiles 后）
- 每个端点返回的总数与 DB 直接查询一致
- 0 值必须是真实无数据日期，而非契约错误
