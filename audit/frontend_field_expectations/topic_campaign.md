# 前端字段期望审计 · topic_campaign（话题活动）

> 审计时间：2026-09-08 · 只读静态分析 · **通用数据面板模板**

## 页面信息
- **模板文件**：`templates/cth/topic_campaign.html`
- **路由**：`/lumenis/cth/topic-campaign`
- **模板类型**：通用数据面板
- **初始化触发**：页面内 script 自动执行

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/topic-campaign/overview` | GET | topic_campaign.html (`data-api`) | 话题活动概览（唯一 API） |

## 期望响应字段树

```
response
├── ok (bool)
├── data (任意结构)
│   ├── campaign_key (string)
│   ├── status (string)
│   ├── total_notes (number)
│   ├── topics[]
│   │   ├── topic (string)
│   │   └── note_count (number)
│   └── (其他动态字段)
```

## 硬编码数据
- 页面标题"话题活动"硬编码

## 渲染假设与字段缺失处理
- 同通用数据面板逻辑（见 brand_industry.md）
- 无固定字段契约

## 备注
- 与 topics.html 是不同端点：topics.html 调用 4 个细分 API（stats/topics/timeline/notes），本页只调用 overview
