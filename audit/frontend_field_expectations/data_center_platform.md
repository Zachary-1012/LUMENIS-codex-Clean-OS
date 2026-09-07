# 前端字段期望审计 · data_center/platform（数据中心-平台详情）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/data_center/platform.html`
- **路由**：`/lumenis/cth/data-center/platform`
- **初始化触发**：页面内 script，支持 URL 参数 `?platform=xxx`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/data-center/platform/{id}` | GET | platform.html (script) | 平台元数据 + 表列表 |
| 2 | `/api/data-center/table/{table}` | GET | platform.html (script) | 单表数据预览 |

## 期望响应字段树

### API 1: 平台详情
```
response
├── ok (bool)
├── platform
│   ├── id / name (string)
│   ├── display_name (string)
│   ├── total_records (number)
│   ├── tables[]
│   │   ├── name (string)
│   │   ├── record_count (number)
│   │   └── last_updated (string)
│   └── fields[] (string[]) — 可用字段
```

### API 2: 表数据
```
response
├── ok (bool)
├── columns[] (string[])
├── rows[] (object[]) — 动态字段
├── total (number)
└── page (number)
```

## 硬编码数据
- 搜索框 placeholder、筛选框 placeholder 为硬编码
- 分页大小硬编码

## 渲染假设与字段缺失处理
- 表数据列名由 `columns` 动态推断
- 行数据为动态对象，按 columns 渲染
- 支持关键词搜索和作者筛选（前端过滤）

## 备注
- 数据中心平台详情页，展示原始数据表
- 支持表切换、搜索、筛选
