# 前端字段期望审计 · official（官方动态）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/official.html`
- **路由**：`/lumenis/cth/official`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/official-info` | GET | official.html:31 (`data-api`) | 官方动态列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → data / items / list / results / records / notes / posts / events / rows
```

列名动态推断。每条记录可能包含：
- id / post_id
- title / content
- platform (weibo/xiaohongshu/wechat)
- publish_datetime / created_at
- likes / comments / shares / reposts
- url / link
- account_name / official_account

## 硬编码数据
- 页面标题"官方动态"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 展示广州太古汇官方账号在各平台的发布动态
- 遵循 AGENTS.md 官方账号只读保护红线
