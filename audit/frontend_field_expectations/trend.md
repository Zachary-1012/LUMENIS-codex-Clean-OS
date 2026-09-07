# 前端字段期望审计 · trend（趋势分析）

> 审计时间：2026-09-08 · 只读静态分析 · **通用数据面板模板**

## 页面信息
- **模板文件**：`templates/cth/trend.html`
- **路由**：`/lumenis/cth/trend`
- **模板类型**：通用数据面板
- **初始化触发**：页面内 script 自动执行

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/trend/overview` | GET | trend.html (`data-api`) | 趋势概览（唯一 API） |

## 期望响应字段树

```
response
├── ok (bool)
├── data (任意结构)
│   ├── date_range (string)
│   ├── total_notes (number)
│   ├── trend_data[]
│   │   ├── date (string)
│   │   ├── note_count (number)
│   │   └── negative_count (number)
│   └── (其他动态字段)
```

## 硬编码数据
- 页面标题"趋势分析"硬编码

## 渲染假设与字段缺失处理
- 同通用数据面板逻辑（见 brand_industry.md）
- 无固定字段契约

## 备注
- 与 analysis.html 的 `/api/trend/overview` 调用相同端点
- analysis.html 是六态面板（动态表格），本页是通用数据面板（KPI + 原始渲染）
