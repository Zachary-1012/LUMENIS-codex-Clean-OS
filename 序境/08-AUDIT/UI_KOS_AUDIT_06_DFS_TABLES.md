# UI/KOS-AUDIT-06｜按 DFS 契约补齐 KOS 三张业务表（成本 / 健康画像 / KOC 分层）

> 日期：2026-09-03 ｜ 线：P1 KOS（序境-Core）｜ 状态：PRODUCTION-VERIFIED
> 触发：用户纠偏「表格用 DFS 那边研究优先，实际设计方向偏了」——业务表格字段/口径必须以 OSAI 契约 CTR-KOS-METRICS-P1-01（DFS Y26 H1 真实标杆）为 Canonical，前端只渲染、不自创业务字段。

## 1. 审计对照（先审计后施工，不重复造）
| KM 项 | Canonical 来源（OSAI 契约 Schema） | ZBC 后端 | 前端（改前） | 本次 |
|---|---|---|---|---|
| KM-01 三阶漏斗 | funnel.viewership/wecom_add/sales_amount | kos_metrics.funnel_metrics + /funnel | 已接 | 保留 |
| KM-02 成本 | cost.boosting_budget/cpl/cpc/cost_per_wecom/inquiry/clicks | cost_metrics + /cost | **缺表** | 补 |
| KM-03 分层+健康画像 | tiers(top5/6_10/11_20/others) + profile.high_avg/low_avg | tier_benchmark + /tier | 仅集中度条，**缺健康画像** | 补 |
| KM-04 KOC 分层 | Gold/Silver/Bronze（24h/7d 阈值可配） | koc_reward_tier + /koc-tier | **缺** | 补（规则表+实时判定器） |
| KM-05 Campaign 复盘 | koc_count/viewership/high_intent/tiers | koc_campaign_review + /campaign(POST) | 缺 | 标注待数据，不做无数据聚合 |
| KM-06 多渠道 ROI | channels[].cpl vs DFS 基准 57.32/9.36 | channel_roi + /channel-roi | 已接 | 保留 |

后端无需改动（10 函数 / 48 路由 / 5 张 kos 表已齐），本次仅补前端渲染层，严格复用既有 `ensureKosPanel`/`api` 模式，零新增后端、零新增定时请求（健康画像复用 loadKosFunnel 已发出的 /tier 响应）。

## 2. 改动（单文件：static/js/kos_dashboard.js）
- 新增 `loadKosCost()`：/api/kos/cost → 7 行结构化表格（Boosting 预算/进线/点击/WeCom/CPL/CPC/Cost-per-WeCom）。
- 新增 `renderKosHealth(tierData)`：由 /tier 回调驱动，高/低产出均值对照表（月均笔记/WeCom/Boosting）。
- 新增 `loadKosKoc()` + `window.kosJudgeTier`：Gold/Silver/Bronze 规则表 + 实时判定器（输入 24h/7d → 真实调 /koc-tier，不前端硬算）。
- loadAllKos 固定面板业务顺序：漏斗→成本→健康画像→KOC→ROI→投流候选→评论→手动回填→生命周期（同步占位，避免异步 append 乱序）。
- 视觉全部引用 Stone token 等价值（#1C1917/#44403C/#78716C/#A8A29E 分层、#E7E5E4 细线、tabular-nums 数字对齐），无 emoji、无裸装饰色。

## 3. 反造假（数据 Truth）
- cpl/cpc/cost_per_wecom 后端为 null 时前端显式「待回填」，绝不显示 0 或估算；展示 manual_pending 字段（inquiry/clicks）。
- profile.manual_data_kos=0 时显式「回填后生成画像（Sales≥1万为高产出，DFS 口径）」。
- Campaign 复盘在没有选定活动 KOC 数据前不聚合、不造数，仅留说明。

## 4. 真实验证（非自述）
- 接口实测：/cost 返回 cpl/cpc/cost_per_wecom=null + manual_pending=[inquiry,clicks]；/tier.profile 字段齐；/koc-tier 120/999→gold。
- Playwright 1440 真实 8201（Basic Auth）：成本表 7 行、健康表 4 行、KOC 表 4 行；判定器 120/999→Gold（金牌）、30/90→Bronze（参与）；面板 DOM 顺序严格为 Funnel→Cost→Health→Koc→Roi…；真实 pageerror=0（已过滤 credentials 噪声）。
- node --check 通过。

## 5. Backlog（不编造，待真实条件）
- KM-05 Campaign 复盘：选定活动并具备 KOC 明细（含 high_intent_comments）后接 POST /campaign 出复盘表。
- Phase B：聚光 Boosting/线索 API 认证后，成本/WeCom/Sales 由手动回填切换为自动归因（接口形状不变，juguang_api.py 已占位 pending）。
