# 前端字段期望审计 · brands（品牌目录）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/brands.html`（179 行）
- **路由**：`/lumenis/cth/brands`
- **初始化触发**：`DOMContentLoaded` → `loadBrands()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/brands/logos` | GET | brands.html:86 | 品牌列表 + Logo + 统计（唯一 API） |

**请求头**：`X-Domain-Id: cth`（硬编码，brands.html:86）

## 期望响应字段树

```
response
├── ok (bool)
├── error (string, 失败时)
├── brands[]
│   ├── brand_en (string) — 英文名
│   ├── brand_cn (string) — 中文名
│   ├── category (string) — 业态分类
│   ├── floor (string) — 楼层
│   ├── shop (string) — 铺位号
│   ├── has_logo (bool)
│   └── logo (string) — Logo URL
├── logo_stats
│   ├── total (number) — 品牌总数
│   └── coverage (number, %) — Logo 覆盖率
└── categories[] (string[]) — 业态分类列表
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| perPage=48 | brands.html:78 | 分页大小，硬编码 |
| X-Domain-Id: cth | brands.html:86 | 请求头，硬编码 |
| Logo 首字母回退 | brands.html:146-149 | 无 Logo 时显示首字母，硬编码样式 |
| 楼层标签配色 | brands.html:160 | rgba(0,212,170,0.1)，硬编码 |

## 渲染假设与字段缺失处理
- `d.ok` 为 false → throw error → catch 显示"加载失败"
- brands 缺失 → `[]` → empty 态
- logo 缺失或 has_logo=false → 显示品牌英文名首字母
- brand_cn 缺失 → 不渲染中文行
- floor 缺失 → 不渲染楼层标签
- 搜索/筛选/分页全在前端完成
- 楼层数由前端 `new Set(brands.map(b=>b.floor))` 计算

## 备注
- 单 API 页面，所有数据来自 `/api/brands/logos`
- 品牌卡片网格布局，支持搜索和业态筛选
- Logo 图片加载失败 onerror 回退到首字母
