# 序境/LUMENIS 多平台采集与广告投流 — UI 移交文档

> 版本：v1.0
> 日期：2026-09-05
> 归属：ZBMP（Z-Brand Monitoring Platform 多品牌母平台层），非 CTH 客户版
> 状态：功能开发完成，移交 UI 全权接管设计与前端实现

---

## 一、已完成采集端口（8 平台 + 1 广告后台）

| 平台 | 采集方式 | search | detail | comments | creator | 真实验证 | Cookie |
|------|----------|--------|--------|----------|---------|----------|--------|
| 小红书 xhs | 生产主链路 | ✅ | ✅ | ✅ | ✅ | ✅ 生产运行 | data/xhs_cookies.json |
| 抖音 douyin | CDP浏览器+API | ✅ | ⚠️ 需签名 | ✅ | ✅ | ✅ search+comments | data/cookies/douyin.json |
| B站 bilibili | API+cookie | ✅ | ✅ | ✅ | ✅ | ✅ 全功能 | data/bilibili_cookies.json |
| 微博 weibo | 移动端API | ✅ | ✅ | ✅ | ✅ | ✅ 全功能 | data/weibo_cookies.json |
| 知乎 zhihu | CDP浏览器优先+API fallback | ✅ | ✅ | ✅ | ✅ | ✅ 已去重 | data/zhihu_cookies.json |
| Instagram | CDP浏览器+代理 | ✅ | ✅ | ✅ | ✅ | ✅ 全功能 | data/cookies/instagram.json |
| X(Twitter) | CDP浏览器 | ✅ | ✅ | ✅ | ✅ | ✅ 刚验证 | data/cookies/x.json |
| Facebook | CDP浏览器+代理 | ✅ | ✅ | ✅ | ✅ | ⏳ 待登录 | 无cookie |
| 聚光(小红书广告) | 浏览器cookie | ✅ | — | — | — | ✅ cookie就绪 | data/cookies/jiguang.json |

### 各平台特色信息卡片字段（UI 设计参考）

**小红书**：标题/正文/作者/点赞/收藏/评论/分享/发布时间/封面图/笔记类型(图文/视频)/话题标签/地点

**抖音**：标题/作者/点赞/评论/收藏/分享/播放量/发布时间/封面/视频时长/音乐/BGM/话题

**B站**：标题/UP主/播放/弹幕/点赞/投币/收藏/评论/发布时间/封面/视频时长/分区

**微博**：正文/作者/点赞/评论/转发/发布时间/来源设备/话题/地点/图片数/视频

**知乎**：标题(问题)/回答摘要/作者/赞同/评论/发布时间/内容类型(回答/文章/问题)/问题ID

**Instagram**：caption/作者/点赞/评论/发布时间/封面/媒体类型(图/视频/轮播)/位置/hashtag

**X**：推文正文/作者/@handle/点赞/评论/转发/浏览量/发布时间/链接/媒体类型

**Facebook**：正文/作者/点赞/评论/分享/发布时间/链接/媒体类型/位置

---

## 二、广告投流模块（ad_intelligence/）

### 已落地子模块

| 模块 | 文件 | 能力 | 状态 |
|------|------|------|------|
| 基础数据类 | base.py | AdPlatform/AdCampaign/AdMetric/AdCreative | ✅ |
| 权限控制 | permission_gate.py | 4级权限(READ/ANALYZE/PREVIEW/EXECUTE)，EXECUTE默认关闭需人工确认 | ✅ |
| 平台商业属性 | platform_registry.py | 8平台画像(地区/币种/支付/最低充值/API权限/合规/代理商返点) | ✅ |
| 巨量引擎 | platforms/ocean_engine.py | 抖音广告数据只读采集+返点计算 | ✅ 框架 |
| 聚光 | platforms/jiguang.py | 小红书广告浏览器cookie采集(跳过OAuth) | ✅ cookie就绪 |
| Meta Ads | platforms/meta_ads.py | FB/IG广告数据只读采集 | ✅ 框架 |
| X Ads | platforms/x_ads.py | X广告数据只读采集(OAuth 1.0a) | ✅ 框架 |
| 采集器工厂 | platforms/factory.py | 统一工厂+环境变量配置+健康检查 | ✅ |
| CTR预测 | models/ctr_predictor.py | 规则基线+模型推理接口 | ✅ 框架 |
| 特征工程 | models/feature_engineer.py | 用户/广告/上下文/实时4类特征 | ✅ 框架 |
| 投流策略 | strategy/generator.py | 受众/预算/出价/时段/素材，AI辅助只建议不执行 | ✅ |
| 广告数据分析 | analytics/analyzer.py | ROAS/漏斗/素材分析(只读) | ✅ |

### 真实商业约束（已写入代码）

- 中国大陆5平台：CNY结算、无需代理、最低充值5000-10000
- 海外3平台：USD结算、必须代理、信用卡后付费、无最低充值
- 代理商返点：实际成本 = 消耗 × (1 - 返点率)
- 写操作：EXECUTE权限默认关闭，必须人工确认+有时效
- 所有策略默认draft状态，需人工批准才能执行

---

## 三、账号保活系统（account_keepalive/）

### 能力

- 9平台账号状态监控（xhs/douyin/bilibili/weibo/zhihu/instagram/x/facebook/jiguang）
- cookie过期检测 / 即将过期预警(7天) / 失效检测
- 系统内置浏览器工作，默认不跳转站外，保留"去登录"跳转选项
- 状态：active / expiring / expired / need_verify / blocked / no_cookie

### UI 需要展示

- 各平台账号状态卡片（状态灯+cookie数量+过期时间）
- 过期预警列表
- "去登录"按钮（保留跳转选项）
- 保活日志

---

## 四、多平台分析方案（docs/MULTI_PLATFORM_ANALYSIS_PLAN.md）

### 4层数据层级

- **L1 概览**：全平台总量/趋势/风险
- **L2 平台**：单平台指标/特色卡片
- **L3 内容**：笔记/推文/视频详情
- **L4 事件**：跨平台事件聚合

### 分析逻辑（与小红书一致）

采集 → subject_hit主体过滤 → build_cross_platform_events跨平台事件聚合(risk取max+负面计数) → AI summarize增强 → 日报

### UI 设计工单（4个）

1. 多平台概览Dashboard（L1）
2. 平台特色信息卡片（L2，8平台不同卡片样式）
3. 跨平台事件时间线（L4）
4. 账号保活状态中心

---

## 五、测试覆盖

| 测试文件 | 数量 | 状态 |
|----------|------|------|
| test_bilibili_v4_adapter.py | 15 | ✅ |
| test_weibo_v4_adapter.py | 18 | ✅ |
| test_zhihu_v4_adapter.py | 13 | ✅ |
| test_instagram_main_adapter.py | 20 | ✅ |
| test_douyin_main_adapter.py | 15 | ✅ |
| test_secondary_platforms_main.py | — | ✅ |
| test_detail_comments_creator_delegation.py | 16 | ✅ |
| test_facebook_x_v4_adapter.py | 10 | ✅ |
| test_ad_intelligence.py | 13 | ✅ |
| test_platform_registry.py | 13 | ✅ |
| test_ad_platform_collectors.py | 14 | ✅ |
| test_ad_strategy_analytics.py | 13 | ✅ |
| test_account_keepalive.py | 10 | ✅ |
| test_collector_guard_integration.py | 9 | ✅ |

---

## 六、待完成项（UI 接管后可继续推进）

| 项 | 优先级 | 说明 |
|----|--------|------|
| Facebook真实采集 | P2 | 需用户登录后采集cookie |
| 聚光API端点调整 | P1 | 当前404，需探测实际API路径或用DOM采集 |
| 抖音detail签名 | P2 | search+comments已够用 |
| CTR/CVR模型训练 | P2 | 需积累广告数据 |
| 投流执行接口 | P1 | Permission Gate已建，默认关闭，需用户明确批准 |
| 广告数据真实采集 | P1 | 需用户提供各平台广告后台API凭证或登录态 |
| 多平台分析UI | P0 | 移交UI设计实现 |
| 账号保活UI | P0 | 移交UI设计实现 |
| 广告投流UI | P1 | 移交UI设计实现 |

---

## 七、关键代码位置

```
v4_upgrade/adapters/          # 8平台v4采集引擎
platform_adapters/            # 主链路薄封装（8平台注册）
ad_intelligence/              # 广告投流模块
account_keepalive/            # 账号保活系统
collector_guard/              # 采集韧性增强（已接入主链路）
collector_guard_integration.py # 多平台guard旁路集成
docs/MULTI_PLATFORM_ANALYSIS_PLAN.md  # 多平台分析方案
docs/AD_INTELLIGENCE_DESIGN.md       # 广告投流设计文档
```

---

## 八、Git 状态

- 仓库：Z-Brand-Core
- 分支：main
- 最新提交：0c1096f（账号保活+知乎去重+聚光+策略+分析）
- 已 Push 到 origin/main
- 前端 WIP（lumenis_frontend.py / static/ / templates/）未提交，由 UI 窗口接管

---

## 九、移交确认

功能开发侧已完成：
- ✅ 8平台采集端口（7个已真实验证可用）
- ✅ 广告投流模块框架（权限/平台属性/采集器/策略/分析）
- ✅ 账号保活系统
- ✅ 多平台分析方案
- ✅ 全部测试通过

UI 侧接管：
- ⬜ 多平台概览Dashboard设计
- ⬜ 8平台特色信息卡片设计
- ⬜ 跨平台事件时间线
- ⬜ 账号保活状态中心
- ⬜ 广告投流管理界面
- ⬜ 前端实现与联调

**移交完成，UI 全权接管。**
