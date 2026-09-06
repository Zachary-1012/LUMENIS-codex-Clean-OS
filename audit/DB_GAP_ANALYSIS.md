# ZBC数据库差距分析报告 DB_GAP_ANALYSIS

> 审计时间：2026-09-07
> 数据库：data/monitor.db
> 现有表数：82张
> 数据字典版本：PLATFORM_DATA_DICTIONARY_V1.md

---

## 一、总体差距

| 层级 | 数据字典要求表数 | 现有表数 | 缺失表数 | 可映射复用 |
|------|----------------|---------|---------|-----------|
| Platform Raw (12平台) | 34 | 0 | 34 | notes≈xhs_notes(部分映射) |
| Platform Normalized | 3 | 0 | 3 | 无 |
| 采集Evidence层 | 2 | 0 | 2 | collection_logs≈collection_runs |
| 业务层 | 8 | 4 | 4 | events/event_mentions/note_review_history/metric_snapshots已存在 |
| **合计** | **47** | **4** | **43** | - |

> 注：现有82张表中，大部分为系统/AI/KOS/V4安全等辅助表，与本次数据字典无直接冲突。

---

## 二、Platform Raw层差距（34张全缺）

### 2.1 小红书 XHS（3张缺）
| 目标表 | 状态 | 现有可映射 | 说明 |
|--------|------|-----------|------|
| xhs_notes | MISSING | notes(963条) | notes表字段不完全对齐，需新建xhs_notes并保留notes做兼容 |
| xhs_note_comments | MISSING | note_comments(141条) | note_comments可映射，新建xhs_note_comments |
| xhs_users | MISSING | 无 | 全新建 |

### 2.2 抖音 Douyin（3张缺）
| 目标表 | 状态 | 现有可映射 | 说明 |
|--------|------|-----------|------|
| douyin_videos | MISSING | 无 | 全新建 |
| douyin_comments | MISSING | 无 | 全新建 |
| douyin_users | MISSING | 无 | 全新建 |

### 2.3 B站 Bilibili（3张缺）
| 目标表 | 状态 | 现有可映射 | 说明 |
|--------|------|-----------|------|
| bilibili_videos | MISSING | 无 | 全新建 |
| bilibili_comments | MISSING | 无 | 全新建 |
| bilibili_users | MISSING | 无 | 全新建 |

### 2.4 视频号 Channels（2张缺）
| 目标表 | 状态 | 说明 |
|--------|------|------|
| channels_videos | MISSING | 全新建，部分字段unavailable |
| channels_comments | MISSING | 全新建 |

### 2.5 YouTube（3张缺）
| 目标表 | 状态 |
|--------|------|
| youtube_videos | MISSING |
| youtube_comments | MISSING |
| youtube_channels | MISSING |

### 2.6 TikTok（3张缺）
| 目标表 | 状态 |
|--------|------|
| tiktok_videos | MISSING |
| tiktok_comments | MISSING |
| tiktok_users | MISSING |

### 2.7 Instagram（3张缺）
| 目标表 | 状态 |
|--------|------|
| instagram_media | MISSING |
| instagram_comments | MISSING |
| instagram_users | MISSING |

### 2.8 X/Twitter（2张缺）
| 目标表 | 状态 |
|--------|------|
| x_posts | MISSING |
| x_users | MISSING |

### 2.9 Reddit（3张缺）
| 目标表 | 状态 |
|--------|------|
| reddit_posts | MISSING |
| reddit_comments | MISSING |
| reddit_subreddits | MISSING |

### 2.10 LinkedIn（2张缺）
| 目标表 | 状态 |
|--------|------|
| linkedin_posts | MISSING |
| linkedin_users | MISSING |

### 2.11 GitHub（4张缺）
| 目标表 | 状态 |
|--------|------|
| github_repositories | MISSING |
| github_issues | MISSING |
| github_pull_requests | MISSING |
| github_releases | MISSING |

### 2.12 知乎 Zhihu（4张缺）
| 目标表 | 状态 |
|--------|------|
| zhihu_answers | MISSING |
| zhihu_questions | MISSING |
| zhihu_articles | MISSING |
| zhihu_comments | MISSING |

---

## 三、Platform Normalized层差距（3张全缺）

| 目标表 | 状态 | 现有可映射 | 说明 |
|--------|------|-----------|------|
| platform_accounts | MISSING | professional_accounts/kos_profiles(部分) | 全新建，统一跨平台账号 |
| platform_contents | MISSING | notes(部分) | 全新建，统一跨平台内容 |
| platform_comments | MISSING | note_comments(部分) | 全新建，统一跨平台评论 |

---

## 四、采集Evidence层差距（2张缺）

| 目标表 | 状态 | 现有可映射 | 说明 |
|--------|------|-----------|------|
| collection_runs | MISSING | collection_logs(7列，简化版) | collection_logs字段：id/keyword/notes_count/status/error_msg/started_at/finished_at。新建collection_runs为增强版，保留collection_logs兼容 |
| platform_evidence | MISSING | browser_evidence/app_evidence_records(部分) | 全新建，统一平台证据链 |

---

## 五、业务层差距

| 目标表 | 状态 | 现有表 | 说明 |
|--------|------|--------|------|
| brands | MISSING | brand_knowledge/brand_industry_monitor | 新建标准brands表，现有表保留 |
| events | EXISTS | events | 已存在，需向后兼容扩展字段(event_type/severity/growth_rate/confidence) |
| event_mentions | EXISTS | event_mentions | 已存在，基本对齐 |
| content_analysis | MISSING | ai_call_logs/case_deep_analysis(部分) | 新建标准内容分析表 |
| note_review_history | EXISTS | note_review_history | 已存在，保留不动 |
| creators | MISSING | kos_profiles/professional_accounts | 新建标准创作者表，现有表保留 |
| metric_snapshots | EXISTS | metric_snapshots | 已存在，基本对齐 |

**业务层差距汇总**：4张新建(brands/content_analysis/creators + events扩展)，4张已存在复用。

---

## 六、现有表与数据字典映射关系

| 现有表 | 数据字典映射 | 映射类型 | 处理方式 |
|--------|------------|---------|---------|
| notes | xhs_notes / platform_contents | 部分映射 | 保留，新数据双写或迁移视图 |
| note_comments | xhs_note_comments / platform_comments | 部分映射 | 保留 |
| collection_logs | collection_runs | 简化版映射 | 保留，新表增强 |
| events | events | 已存在 | 扩展字段(向后兼容) |
| event_mentions | event_mentions | 已存在 | 复用 |
| metric_snapshots | metric_snapshots | 已存在 | 复用 |
| note_review_history | note_review_history | 已存在 | 复用 |
| browser_evidence | platform_evidence | 部分映射 | 保留，新表统一 |
| brand_knowledge | brands | 部分映射 | 保留，新表标准化 |
| kos_profiles | creators | 部分映射 | 保留，新表标准化 |
| professional_accounts | platform_accounts/creators | 部分映射 | 保留 |

---

## 七、迁移策略

### 7.1 新建表（43张）
- 全部使用 `CREATE TABLE IF NOT EXISTS`
- 不修改现有表结构（events扩展除外，且只加字段不删改）
- 不删除/清空任何现有表
- 新建表通过迁移脚本 `migrations/001_platform_data_dictionary_v1.sql` 执行

### 7.2 现有表扩展（1张）
- `events`表：增加 `event_type`, `severity`, `growth_rate`, `confidence` 字段
- 使用 `ALTER TABLE events ADD COLUMN` 向后兼容
- 不修改现有字段

### 7.3 数据迁移（不执行，仅预留）
- notes → xhs_notes / platform_contents：预留迁移脚本，不自动执行
- note_comments → xhs_note_comments / platform_comments：预留
- 需用户授权后执行数据迁移

### 7.4 兼容视图（可选，后续）
- 可创建VIEW将notes映射为platform_contents，不影响现有查询

---

## 八、风险与约束

1. **数据库最高保护**：所有操作CREATE TABLE IF NOT EXISTS，不DROP不DELETE
2. **现有数据不动**：notes(963条)/note_comments(141条)等现有数据完整保留
3. **向后兼容**：events表只加字段，不改现有字段
4. **命名不冲突**：新表名与现有82张表无冲突
5. **索引**：新建表均创建唯一索引(platform, content_id)和时间索引
6. **JSON字段**：列表/对象字段用TEXT存储JSON，不使用SQLite JSON类型（兼容性）
