# 前端字段期望审计 · weekly（周报）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/weekly.html`
- **路由**：`/lumenis/cth/weekly`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/weekly/events` | GET | weekly.html:31 (`data-api`) | 周报事件列表（唯一 API） |
| 2 | `{url}` (动态) | GET | weekly.html:160 | 面板内动态 URL fetch（通用逻辑） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → events / data / items / list / results / records / rows
```

列名动态推断。每条记录可能包含：
- id / event_id
- title / name
- range (string, 如 '7d')
- created_at / date
- file_size (number)
- file_path / url
- file_exists (bool)
- status (string: completed/generating/pending/failed)

## 硬编码数据
- 页面标题"周报"硬编码
- 六态面板 UI 结构硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑（见 evidence.md）
- 无固定字段契约

## 备注
- 与 reports.html / calendar.html 的 `/api/weekly/events` 调用相同端点
- reports.html 有专用渲染逻辑（聚合周报+专报），本页是通用动态表格
