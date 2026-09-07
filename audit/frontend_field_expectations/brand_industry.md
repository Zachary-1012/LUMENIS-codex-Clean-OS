# 前端字段期望审计 · brand_industry（品牌业态）

> 审计时间：2026-09-08 · 只读静态分析 · **通用数据面板模板**

## 页面信息
- **模板文件**：`templates/cth/brand_industry.html`
- **路由**：`/lumenis/cth/brand-industry`
- **模板类型**：通用数据面板（fetch + 原始 JSON/基础字段渲染）
- **初始化触发**：页面内 script 自动执行

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/brand-industry/overview` | GET | brand_industry.html (`data-api`) | 品牌业态概览（唯一 API） |

## 期望响应字段树

```
response
├── ok (bool)
├── data (任意结构)
│   ├── total_brands (number)
│   ├── industries[]
│   │   ├── name (string)
│   │   ├── brand_count (number)
│   │   └── note_count (number)
│   └── (其他动态字段)
```

**渲染方式**：通用面板尝试渲染 `data` 中的顶层字段为 KPI 卡片，数组字段为列表。无固定字段契约。

## 硬编码数据
- 页面标题"品牌业态"硬编码
- 面板 UI 结构硬编码

## 渲染假设与字段缺失处理
- fetch 失败 → error 态
- data 为空 → empty 态
- 字段缺失 → 不渲染对应卡片
- 未知字段 → 原始值 toString 渲染

## 备注
- 与 trend.html / topic_campaign.html 共享完全相同的通用数据面板模板，仅 `data-api` 不同
- 比六态面板更简单：无多状态管理，直接 fetch + 渲染
