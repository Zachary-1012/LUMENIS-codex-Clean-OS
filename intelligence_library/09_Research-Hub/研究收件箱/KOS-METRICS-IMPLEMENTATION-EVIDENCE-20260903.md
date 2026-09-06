# KOS Metrics Phase A 施工证据（CTR-KOS-METRICS-P1-01）

> 双子星施工证据 ｜ 2026-09-03
> OSAI 契约 → ZBC 施工：三阶漏斗 / 成本指标 / KOS 分层 / KOC 分层判定
> 契约：docs/reference/CTR-KOS-METRICS-P1-01.md（双库镜像）

## 一、施工内容
| 施工项 | 文件 | 说明 |
|---|---|---|
| 新增 `kos_metrics.py`（12KB） | `kos_metrics.py` | funnel_metrics / cost_metrics / tier_benchmark / koc_reward_tier / koc_campaign_review / set_manual |
| 新增 4 路由 | `kos_routes.py` | `/api/kos/funnel` `/api/kos/cost` `/api/kos/tier` `/api/kos/koc-tier` |
| 工单登记 | `迭代工单与时间评估.md` §八 | ZBC-P1-KM-01~06（3 项施工中 / 3 项待启动） |

## 二、验证结果
- py_compile：kos_metrics.py / kos_routes.py / kos_intel.py 通过
- KOC 分层判定 6 用例全过（对齐 DFS 规则）：
  - (120,999)→gold、(60,200)→silver、(80,400)→silver、(30,90)→bronze、(10,60)→bronze、(0,0)→none
- campaign 复盘：CNY 2 KOC → viewership 1500 / high-intent 25 / gold 1 + silver 1 ✓
- 真实 DB 只读冒烟（data/monitor.db，未写库）：
  - funnel all：50 个 KOS，累计曝光 304,896；WeCom/Sales 0 → manual_pending（Phase A 手动回填）
  - tier 分层：Top5 集中度 45.2%、Top6-10 24.1%、Top11-20 30.7%
  - cost：boosting 0 → pending（待手动回填/官方 API）

### 追加：KM-06 多渠道 ROI + 链路开发完（ce3f917 / a8d5ddd）
- KM-06：channel_roi() + /channel-roi 路由 + 动态报告 ROI 卡片；基准=DFS 实测（小红书 CPL 57.32 / 微信 OA 9.36），覆盖用例 CPL 精确对齐
- 前端挂载：kos_dashboard 动态注入漏斗/分层/ROI 卡片 + 手动回填表单（不动 index.html）
- **链路开发完（只差用户给聚光 API）**：
  - subject_rules 品牌化：subject_sql_and_values_for/collect_keywords_for（ACTIVE_BRAND=hainan_cdf）
  - collector_v2/run_profile.py：profile 驱动采集入口（--dry-run 验证：5 中免关键词）
  - juguang_api.py：聚光 Phase B 对接占位（JUGUANG_* 环境变量，未配置 pending，不阻塞手动回填）
  - /api/kos/profile：激活品牌/关键词/聚光状态
  - 验证：品牌化 SQL 105 参数中免口径 / subject_hit_text 命中排除 OK / 聚光 pending / dry-run OK

## 三、设计要点
- **只读现有 DB**（notes/kos_profiles/note_comments），不建新表、不写生产库
- **三阶漏斗**：Viewership = notes 曝光聚合（likes+comments+collects+shares）；WeCom/Sales 走手动回填层 `data/kos_metrics_manual.json`（接口形状固定，认证后可换聚光 API 自动归因）
- **KOC 分层**：Gold=24h≥100 或 7d≥500；Silver=24h≥50 或 7d≥100；Bronze=参与；未达标返回 none（可发参与奖防流失）——阈值可配
- **红线**：无 Cookie/Token 入库；不自动评论；不托管养号；不绕过平台风控

## 四、边界与学习点
- 严守 OSAI 只出契约 / ZBC 施工边界；本次为契约落地首批实现
- 分层看板用真实 exposure 出值，证明 Phase A 公开数据可立即跑通（无需蓝V/聚光）
- 后续 Phase B：聚光 Boosting/线索 API 认证后 → 成本/WeCom/Sales 自动归因（接口形状不变）

## 参考
- 契约：CTR-KOS-METRICS-P1-01.md
- 研究：CDF-HAILAN-DEEP-RESEARCH-20260903.md（DFS Y26 H1 真实标杆：三阶漏斗/CPL/高意向评论）

---

## 追加 2026-09-03：前端三表按契约补齐（ZBC a70e8fc，PRODUCTION-VERIFIED）
- 纠偏：用户明确「表格用 DFS 研究优先」。审计确认后端 KM-01~06 函数/路由已齐，前端此前只接漏斗/分层条/ROI，缺 KM-02 成本表、KM-03 高/低产出健康画像、KM-04 KOC 分层。
- 落地（仅 static/js/kos_dashboard.js，零后端改动、零新增定时请求）：
  - 成本表 /api/kos/cost：Boosting/进线/点击/WeCom/CPL/CPC/Cost-per-WeCom；null 显式「待回填」+ manual_pending。
  - 健康画像复用 /api/kos/tier 的 profile.high_avg/low_avg（不新增请求）；manual_data_kos=0 时提示回填后生成。
  - KOC Gold/Silver/Bronze 规则表 + 实时判定器（调 /api/kos/koc-tier，不前端硬算；实测 120/999→gold、30/90→bronze）。
  - 面板顺序按业务漏斗固定：漏斗→成本→健康画像→KOC→ROI。
- 验证：Playwright 真实 8201，三表 7/4/4 行、0 真实 pageerror、node --check 通过；Evidence：ZBC 序境/08-AUDIT/UI_KOS_AUDIT_06_DFS_TABLES.md。
- 原则沉淀：learning-feed/pattern-contract-first-tables-20260903.md（契约 Schema 为业务表格唯一 Canonical，前端只渲染不自创字段）。
- 仍待：KM-05 Campaign 复盘需选定活动 KOC 明细；Phase B 聚光 API 认证后成本/WeCom/Sales 自动归因。
