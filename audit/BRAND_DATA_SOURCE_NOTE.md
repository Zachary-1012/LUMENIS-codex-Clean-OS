# 品牌主数据源差异说明 (BRAND_DATA_SOURCE_NOTE)

> 版本: V1.0
> 日期: 2026-09-07
> 状态: 如实记录，不强行统一

## 一、两套品牌主数据现状

| 维度 | brand_directory.json | brand_industry_monitor 表 |
|------|---------------------|--------------------------|
| 品牌总数 | 199 | 198 |
| 业态数 | 9 | 8 |
| 业态命名 | 中文短名（女装/男装/餐饮/珠宝钟表/美容护理/运动休闲/鞋包皮具/童装玩具/生活时尚） | 中英长名（如 "女装 Ladies' Fashion"） |
| 数据格式 | JSON静态文件 | SQLite表 |
| 字段 | brand_en/brand_cn/shop/category/floor/is_taikoo_brand | id/brand_name/industry/source/mention_count/sentiment/last_mention_at/keywords/summary |
| 更新方式 | 手动维护 | 采集/重算更新 |
| 用途 | CTH overview业态分布、品牌匹配、/api/brand-stats | ZBMP活跃品牌KPI、/api/brand-industry/stats |

## 二、差异原因

1. **brand_directory.json** 是基于广州太古汇官方品牌名录的静态主数据，包含199个品牌（含文华东方酒店内品牌），9个业态分类。
2. **brand_industry_monitor** 是动态监测表，基于实际采集到的品牌建立，198个品牌（可能缺少1个未采集到的品牌），8个业态（缺少"生活时尚"或合并了某些业态）。
3. 命名差异：brand_industry_monitor使用中英长名是历史遗留，brand_directory.json使用中文短名是后来规范化的结果。

## 三、当前处理策略（不强行统一）

### CTH域（客户交付版）
- **使用 brand_directory.json（199品牌9业态）** — 正确，保持
- `/api/brand-stats` 端点基于此文件返回 `pie_data`、`trend_data`、`top_brands`
- CTH overview业态分布环形图使用 `/api/brand-stats.pie_data`

### ZBMP域（多品牌母平台）
- **活跃品牌KPI**：优先使用 `/api/brand-stats.total_brands`（199），降级使用 `brand_industry_monitor`（198）
- **业态分布**：已切换到 `/api/brand-stats.pie_data`（9业态中文短名），不再使用 `/api/brand-industry/stats`（8业态中英长名）或 `/api/stats.categories`（内容分类）
- **数据来源标注**：ZBMP页面业态分布tag显示 "数据来源 brand-stats"，KPI活跃品牌sub-label显示 "brand-stats"

## 四、统一建议（未来P2，不在本轮执行）

**建议以 brand_directory.json 为权威统一源**，理由：
1. 199品牌更完整（含文华东方内品牌）
2. 9业态分类更细（含"生活时尚"）
3. 中文短名更符合UI展示需求
4. 静态文件可控，不受采集状态影响

**统一路径建议**：
1. 将 brand_industry_monitor 表的 industry 字段迁移为中文短名
2. 补齐缺失的1个品牌到 brand_industry_monitor
3. 新增第9个业态"生活时尚"
4. 废弃 `/api/brand-industry/stats`，统一走 `/api/brand-stats`
5. 保留 brand_industry_monitor 作为动态监测指标表（mention_count/sentiment等），但业态分类以 brand_directory.json 为准

**风险**：迁移可能影响历史数据统计，需在P2阶段做向后兼容迁移，不在本轮收口执行。

## 五、本轮变更记录

| 文件 | 变更 |
|------|------|
| templates/zbmp/overview.html | renderIndustry() 切换到 /api/brand-stats.pie_data；9业态白名单改为中文短名；KPI活跃品牌优先brandStats；新增loadBrandStats()；reload tasks增加brandStats |
| audit/BRAND_DATA_SOURCE_NOTE.md | 本文件，记录差异与建议 |
