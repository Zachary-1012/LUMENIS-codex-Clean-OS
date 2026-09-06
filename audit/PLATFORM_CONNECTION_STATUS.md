# ZBC 12平台接入状态审计报告

> 审计时间：2026-09-07
> 审计范围：platform_adapters/、collector_v2/、app.py路由、data/monitor.db数据
> 审计结论：1平台ACTIVE，2平台PARTIAL，9平台PLANNED

## 一、接入状态定义

| 状态 | 定义 | 前端可见 |
|------|------|----------|
| ACTIVE | 有完整Collector+API+真实数据入库 | 是 |
| PARTIAL | 有部分基础设施（登录/搜索/Adapter骨架）但无完整数据管道或无真实数据 | 是（缺失字段标unavailable） |
| PLANNED | 无采集端口/API/数据源，仅数据层+逻辑层 | 否 |

## 二、12平台逐项审计

### 1. 小红书 XHS — ACTIVE ✅

- **Collector**：完整Playwright/CDP采集链路（xhs_cdp_collector.py、xhs_p0_orchestrator.py、xhs_cookie_bridge.py）
- **API路由**：/api/xhs/* 完整（runtime-check、switch-account、accounts、login、p0/status、optimizer等）
- **DB数据**：notes表963条（xiaohongshu:949, xiaohongshu-cdp:8, xhs:6），note_comments 141条
- **Adapter**：platform_adapters/xhs.py 存在
- **登录管理**：双账号体系（XHS_CN_PRIMARY + XHS_RETINAUT），CDP 9222/9223
- **结论**：主力采集平台，全链路ACTIVE

### 2. 抖音 Douyin — PARTIAL ⚠️

- **Adapter**：platform_adapters/douyin.py（133行），引用v4_upgrade.adapters.douyin引擎
- **状态**：enabled=False，需cookie+浏览器环境，运行时检查后启用
- **API路由**：app.py中无独立抖音采集路由
- **DB数据**：无douyin_videos表，notes表无抖音数据
- **Collector**：collector_v2/无抖音目录
- **结论**：有Adapter骨架和v4引擎引用，但无运行中的采集管道，无真实数据。标记PARTIAL（基础设施存在，接入待完成）

### 3. B站 Bilibili — PARTIAL ⚠️

- **登录管理**：bilibili_login_manager.py 存在，有完整登录态管理
- **API路由**：/api/bilibili/login-status、/api/bilibili/search、/api/bilibili/clear-login
- **Adapter**：platform_adapters/bilibili.py（131行）
- **DB数据**：无bilibili_videos表，notes表无B站数据
- **Cookie导入**：支持ZBC_BILI_COOKIE_JSON环境变量导入
- **结论**：有登录+搜索API+Adapter，但搜索结果未入库（仅存topic_campaign），无完整采集管道。标记PARTIAL

### 4. 视频号 Channels — PLANNED 🔜

- **Adapter**：无platform_adapters/channels.py
- **API路由**：无
- **DB数据**：无
- **Collector**：无
- **结论**：完全未接入。视频号无公开API，需微信生态特殊入口。标记PLANNED，Raw表字段按可采集范围设计，不存在的公开字段标unavailable

### 5. YouTube — PLANNED 🔜

- **Adapter**：无
- **API路由**：无
- **DB数据**：无
- **结论**：未接入。有Data API v3可接入。标记PLANNED

### 6. TikTok — PLANNED 🔜

- **Adapter**：无
- **API路由**：无
- **DB数据**：无
- **结论**：未接入。标记PLANNED

### 7. Instagram — PLANNED 🔜

- **Adapter**：platform_adapters/instagram.py（235行，最完整的骨架）
- **API路由**：无
- **DB数据**：无
- **结论**：有较完整Adapter骨架，但无运行中采集。标记PLANNED

### 8. X/Twitter — PLANNED 🔜

- **Adapter**：platform_adapters/x_platform.py（95行）
- **API路由**：无
- **DB数据**：无
- **结论**：有Adapter骨架。标记PLANNED

### 9. Reddit — PLANNED 🔜

- **Adapter**：无
- **API路由**：无
- **DB数据**：无
- **结论**：未接入。标记PLANNED

### 10. LinkedIn — PLANNED 🔜

- **Adapter**：无
- **API路由**：无
- **DB数据**：无
- **结论**：未接入。标记PLANNED

### 11. GitHub — PLANNED 🔜

- **Adapter**：无
- **API路由**：无
- **DB数据**：无
- **结论**：未接入。有REST API v3可接入。标记PLANNED

### 12. 知乎 Zhihu — PLANNED 🔜

- **Adapter**：platform_adapters/zhihu.py（124行）
- **API路由**：无
- **DB数据**：无
- **结论**：有Adapter骨架。标记PLANNED

## 三、额外发现：微博（不在12平台列表但已存在）

- **状态**：PARTIAL
- **登录管理**：weibo_login_manager.py
- **API路由**：/api/weibo/login-status、/api/weibo/start-login、/api/weibo/clear-login、/api/weibo/cookies
- **搜索**：app.py中有微博搜索逻辑（/api/topic/multi-platform搜索）
- **DB数据**：无weibo_posts表
- **备注**：微博不在本次12平台数据字典范围内，但已有基础设施，后续可纳入

## 四、汇总表

| # | 平台 | 状态 | Adapter | 登录管理 | API路由 | Raw表 | 真实数据 | 前端可见 |
|---|------|------|---------|----------|---------|-------|----------|----------|
| 1 | 小红书 | ACTIVE | ✅ xhs.py | ✅ 双账号CDP | ✅ 完整 | 待建(映射notes) | ✅ 963条 | 是 |
| 2 | 抖音 | PARTIAL | ✅ douyin.py | ❌ | ❌ | 待建 | ❌ | 是(unavailable) |
| 3 | B站 | PARTIAL | ✅ bilibili.py | ✅ login_manager | ✅ 搜索/登录 | 待建 | ❌ | 是(unavailable) |
| 4 | 视频号 | PLANNED | ❌ 待建 | ❌ | ❌ | 待建 | ❌ | 否 |
| 5 | YouTube | PLANNED | ❌ 待建 | ❌ | ❌ | 待建 | ❌ | 否 |
| 6 | TikTok | PLANNED | ❌ 待建 | ❌ | ❌ | 待建 | ❌ | 否 |
| 7 | Instagram | PLANNED | ✅ instagram.py | ❌ | ❌ | 待建 | ❌ | 否 |
| 8 | X/Twitter | PLANNED | ✅ x_platform.py | ❌ | ❌ | 待建 | ❌ | 否 |
| 9 | Reddit | PLANNED | ❌ 待建 | ❌ | ❌ | 待建 | ❌ | 否 |
| 10 | LinkedIn | PLANNED | ❌ 待建 | ❌ | ❌ | 待建 | ❌ | 否 |
| 11 | GitHub | PLANNED | ❌ 待建 | ❌ | ❌ | 待建 | ❌ | 否 |
| 12 | 知乎 | PLANNED | ✅ zhihu.py | ❌ | ❌ | 待建 | ❌ | 否 |

## 五、前端数据中心展示策略

- **数据中心导航**：仅显示 ui_visible=true 的平台（小红书、抖音、B站）
- **小红书**：完整数据展示（notes表映射）
- **抖音/B站**：展示表结构和已有基础设施，数据列显示"暂无数据（采集端口待接入）"，不伪造
- **PLANNED平台**：不在前端导航出现，仅在系统设置/运营管理页显示接入状态
- **接入后自动显示**：platform_registry.status变为ACTIVE时，ui_visible自动为true，前端无需改代码

## 六、接入优先级建议

1. **P0**：B站（已有登录+搜索，补全入库管道即可ACTIVE）
2. **P1**：抖音（已有Adapter+v4引擎引用，补登录+采集管道）
3. **P2**：知乎、X/Twitter、Instagram（已有Adapter骨架）
4. **P3**：YouTube、GitHub（有公开API，接入成本低）
5. **P4**：TikTok、Reddit、LinkedIn
6. **P5**：视频号（无公开API，需特殊入口）
