# ZBC V2.0 API 域归属清单 V1.0
> 生成时间：2026-09-06 | 分支：lumenis-dual-domain-v3
> 原则：/api/zbmp|cth|system 成体系；旧路由保留 deprecated 兼容，不断旧链。

## 一、双域命名空间 API（新，推荐使用）

### ZBMP 域（/api/zbmp/*）
| 端点 | 方法 | 功能 | 域标签 |
|---|---|---|---|
| /api/zbmp/overview | GET | ZBMP 品牌总览 | domain_id=zbmp, product_id=ZBMP |
| /api/zbmp/brands | GET | ZBMP 品牌列表 | domain_id=zbmp, product_id=ZBMP |
| /api/zbmp/metrics | GET | ZBMP 指标统计 | domain_id=zbmp, product_id=ZBMP |

### CTH 域（/api/cth/*）
| 端点 | 方法 | 功能 | 域标签 |
|---|---|---|---|
| /api/cth/overview | GET | CTH 太古汇总览 | domain_id=cth, product_id=CTH |
| /api/cth/events | GET | CTH 事件列表 | domain_id=cth, product_id=CTH |
| /api/cth/xiaohongshu | GET | CTH 小红书数据 | domain_id=cth, product_id=CTH |

### SYSTEM 域（/api/system/*）
| 端点 | 方法 | 功能 | 域标签 |
|---|---|---|---|
| /api/system/status | GET | 系统健康状态 | domain_id=system, product_id=SYSTEM |
| /api/system/runtime-workers | GET | Runtime worker 列表（按域分组） | domain_id=system, product_id=SYSTEM |
| /api/system/domains | GET | 域隔离总览 | domain_id=system, product_id=SYSTEM |

## 二、Deprecated 旧路由（保留兼容，响应带 X-Deprecated: true）

| 旧路由前缀 | 数量 | 建议迁移到 | X-Deprecated |
|---|---|---|---|
| /api/xhs/* | ~15 | /api/cth/xiaohongshu | true |
| /api/v4/* | ~3 | /api/system/api-keys | true |
| /api/notes/* | ~5 | /api/cth/overview or /api/zbmp/overview | true |
| /api/web/* | ~9 | /api/zbmp/brands or /api/cth/events | true |

## 三、域头契约

所有 API 请求应携带：
- `X-Domain-Id`: zbmp / cth / system
- `X-Product-Id`: ZBMP / CTH / SYSTEM

所有双域命名空间 API 响应携带：
```json
{
  "success": true,
  "data": {...},
  "error": "",
  "domain_id": "zbmp",
  "product_id": "ZBMP"
}
```

## 四、页面路由域归属

### ZBMP 页面
/lumenis/zbmp/overview, /lumenis/zbmp/brand, /lumenis/zbmp/content,
/lumenis/zbmp/kos, /lumenis/zbmp/competition, /lumenis/zbmp/risk, /lumenis/zbmp/reports

### CTH 页面
/lumenis/cth/overview, /lumenis/cth/realtime, /lumenis/cth/events,
/lumenis/cth/risk, /lumenis/cth/xiaohongshu, /lumenis/cth/reports

### SYSTEM 页面
/lumenis/system/runtime, /lumenis/system/collector, /lumenis/system/ai,
/lumenis/system/database, /lumenis/system/security, /system/settings
