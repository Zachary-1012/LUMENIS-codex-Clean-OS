# CTR-KOS-METRICS-P1-01｜KOS 三阶漏斗指标 + KOC 分层激励 施工契约

> 双子星 OSAI 研究侧产出 → 交付 Z-Brand-Core 施工
> 日期：2026-09-03 ｜ 状态：READY_FOR_IMPLEMENTATION ｜ Owner：ZBC（P1）
> 关联：CDF-HAILAN-DEEP-RESEARCH-20260903.md / KOS-BASELINE-HAILAN-CDF-20260903.md / KOS-INTEL-IMPLEMENTATION-EVIDENCE-20260903.md / CTR-XHS-LEADS-P1-01.md
> 边界：OSAI 仅出方案/契约；ZBC 施工。不保存任何 Cookie/Token/Session；不绕过平台风控

---

## 0. 结论速览（Gap → 方案）

| 问题 | 事实（DFS 真实标杆 Y26 H1） | ZBC 动作 |
|---|---|---|
| KOS 绩效怎么衡量 | 三阶漏斗 **Viewership → WeCom(加企微) → Sales**，外加 CPL/CPC/Boosting 预算 | KOS 报告补三阶指标 + 成本指标 |
| 头部集中度 | WJA Top5 KOS=94% 销售；BTY Top5=64% WeCom、61% Sales | KOS 分层看板（Top5/Top6-10/Top11-20/Others） |
| 高产出 KOS 画像 | 月均 post 10 + Boost ¥1,086 + WeCom 102 vs 低产出 4篇/¥420/11 | KOS 健康度画像（活跃/投入/产出） |
| KOC 转化核心指标 | High-intent comment 54-108/场（KOC campaign 北极星） | `kos_intel.classify_intent` 强意向分层（✅ 已实现）接入 KOC |
| KOC 激励体系 | Gold/Silver/Bronze + Coupon/Gift Card/QR 溯源；24h 达标 ¥300-800、7d ¥500+Coupon | 新增 KOC 分层激励模块（ZBC 暂无） |
| 渠道成本对比 | 微信 OA CPL ¥9.36 vs 小红书 Boosting ¥57.32 | 多渠道 KOS ROI 对比进报告 |

---

## 1. 背景（DFS 真实标杆 → 中免 KOS 测量体系）

DFS 澳门门店（Rhyme Reach Y26 H1 复盘）以 243 个 KOS 半年产出：
- 曝光 4M（+60%）、Boosting Inquiry 11.2K（+18.95%）、CPL ¥57.32（**-19.1%**，预算仅 +6%）
- 高产出 KOS：Boost ¥1,086/月、WeCom 102、Top post 25、月均 10 篇；低产出组 ¥420/11/3/4
- PS KOS 试点：9 号 5 周 Sales ¥166 万，per TXN ¥69,185（vs WJA ¥75,609，-8%）——增量引擎

**中免启示**：中免海南市占 85%，KOS 空间远大于 DFS，应先建完整 KOS 测量体系（本契约），再谈放量。

---

## 2. ZBC 施工项（NEXT_ENGINEERING_QUEUE 追加）

| 编号 | 施工项 | 说明 | 依赖 |
|---|---|---|---|
| ZBC-P1-KM-01 | **KOS 三阶漏斗指标** | Viewership → WeCom → Sales 逐级统计；KOS 维度 + 品牌维度 + 门店维度 | 现有采集/归因 |
| ZBC-P1-KM-02 | **KOS 成本指标** | CPL（进线）、CPC、Cost per WeCom、Boosting 预算归因到 KOS | 采集 boosting 数据 |
| ZBC-P1-KM-03 | **KOS 分层看板** | Top5/Top6-10/Top11-20/Others 集中度；高/低产出 KOS 画像对比 | KM-01/02 |
| ZBC-P1-KM-04 | **KOC 分层激励模块** | Gold/Silver/Bronze 分层 + Coupon/Gift Card/QR 溯源 + 24h/7d 达标奖励 | 新增 |
| ZBC-P1-KM-05 | **KOC campaign 复盘** | 按 campaign 统计 KOC 数/曝光/互动/High-intent comment/Sales | 现有采集 |
| ZBC-P1-KM-06 | **多渠道 KOS ROI 对比** | 小红书 Boosting vs 微信 OA vs 私域 WeCom 成本对比进报告 | 1-5 |

## 3. 数据契约（KOS Metrics Schema 草案）

```json
{
  "period": "2026H1",
  "entity": {"type": "brand|store|kos", "id": "", "name": ""},
  "funnel": {
    "viewership": 0,
    "wecom_add": 0,
    "sales_amount": 0.0,
    "sales_qty": 0,
    "cod_amount": 0.0,
    "fs_amount": 0.0
  },
  "cost": {
    "boosting_budget": 0.0,
    "cpl_inquiry": 0.0,
    "cpc": 0.0,
    "cost_per_wecom": 0.0
  },
  "tier": "top5|top6_10|top11_20|others",
  "health": {
    "monthly_posts": 0,
    "avg_post_view": 0,
    "top_post_count": 0,
    "active_weeks": 0
  },
  "source_channel": "xhs|wechat_oa|private_domain"
}
```

## 4. KOC 分层激励（参考 DFS Gold/Silver/Bronze，可配置）

| 层 | 定义（示例，可配） | 激励（示例，可配） |
|---|---|---|
| Gold | 24h 内容 ≥100 互动 或 7d ≥500 | ¥300-800 消费券 / ¥500+Coupon+首发权 |
| Silver | 24h 50-99 或 7d 100-499 | ¥100-200 / ¥200 |
| Bronze | 达标参与 | 礼卡 ¥100（防流失） |
| 溯源 | Coupon/Gift Card 带 QR code，KOC→消费归因 | 归因进 KOC 报告 |

## 5. 合规红线（硬约束，写入测试）

1. 不采集/保存 Cookie/Token/Session；Boosting 预算数据走配置/手动录入或官方 API（如已认证）
2. 不 AI 自动评论；不托管养号；不绕过平台风控
3. KOC 激励发放需真实可溯源（QR code 归因），不做虚假互动
4. 指标口径与 DFS/行业可比时标注来源与口径；本地数据与公开数据分开
5. CPL/CPC 属经营数据，报告导出需权限控制

## 6. 验收标准（ZBC 测试）

- [ ] KOS 三阶漏斗：同一 KOS 能输出 Viewership/WeCom/Sales 三级（用例：中免 Top KOS）
- [ ] 成本指标：CPL/CPC/Cost per WeCom 计算正确（对照 DFS 口径回放）
- [ ] 分层看板：Top5 集中度、高/低产出画像可出图
- [ ] KOC 分层：Gold/Silver/Bronze 阈值可配、达标判定正确（单测）
- [ ] 多渠道 ROI 对比表进入报告中心
- [ ] 安全测试：无密钥泄漏（secret scanning 通过）

## 6.5 阶段化实施

> 与 CTR-XHS-LEADS-P1-01 Phase A 同步：当前无蓝V/聚光，公开数据采集不受影响。

### Phase A — 公开数据测量（NOW）
- [ ] 三阶漏斗：Viewership/WeCom 来自公开采集 + 手动回填 Sales；KOS 维度聚合
- [ ] 成本指标：Boosting 预算先手动录入/配置（官方 API 待认证）
- [ ] KOC 分层 + campaign 复盘：基于采集的 high-intent comment（classify_intent）与内容数据
- 交付：KOS 绩效看板、KOC 分层台账、多渠道 ROI 对比进 ZBC Event/Risk/Report

### Phase B — 官方数据打通（LATER，认证后启用）
- [ ] 聚光 Boosting 消耗/线索 API 直连（若认证）→ 成本自动归因
- [ ] 私域 WeCom/Sales 归因 API（若接入）→ 漏斗自动化
- [ ] KOC Coupon/QR 溯源系统对接

## 7. 分级决策
| 项 | 决策 |
|---|---|
| 三阶漏斗 + 成本指标进 KOS 报告 | ADOPT（P1） |
| KOS 分层看板（Top5 集中度） | ADOPT（P1） |
| KOC 分层激励模块 | ADOPT（P1，新增能力） |
| 多渠道 ROI 对比 | ADOPT（P1） |
| 官方 API 自动归因 | LATER（随 CTR-XHS-LEADS-P1-01 Phase B） |
| 自动评论/托管养号 | REJECT（平台红线） |

## 参考来源
- 内部：Rhyme Reach《DFS OA&KOS&KOC Project Y26 H1 Review - RR0902》（用户提供，仅内部对标）
- 公开：中免 2026H1 中报（新浪财经/同花顺/券商研报）、海南离岛免税数据（海关/中国日报）
- ZBC 现有：`kos_intel.py`（classify_intent/recognize_kos_identity/competitor_benchmark）、`kos_routes.py`、`kos_report`、`hainan_cdf.json`
