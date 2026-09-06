# OSAI 第二十一期 · 海外节点接入报告+三维交叉+CSV 排期导出+海外社媒算法研究

日期：2026-09-03
定位：营销日历能力从"国内节点"扩展到"国内+海外×节气×行业"三维矩阵，并支持排期导出；海外社媒算法研究沉淀。

---

## 一、海外节点接入 overview 端点与报告 ✅
- `/api/v2/marketing/overview?global=1`：返回 `global_cross`（海外×当月节气）+ `global_nodes`（26 个海外节点全量）。
- `report_engine` 报告 `marketing_nodes` 新增 `global`（海外×节气建议）+ `global_nodes`（当月海外节点名）。
- 实测 daily 报告：global=[Labor Day (US)遇白露…, NY Fashion Week遇白露…]，global_nodes=[Labor Day (US), NY Fashion Week]。

## 二、三维交叉（行业×海外×节气）✅
- `marketing_calendar.cross_global(month)`：海外节点 × 当月节气交叉建议（面向出海/高端商业体国际叙事时机）。
- 三维矩阵：行业节点（国内垂直）× 海外节点 × 节气 —— 一个营销时点可从三个坐标系定位。

## 三、CSV 排期导出 ✅
- `overview?export=csv`：全年 12 月国内节点 + 海外节点合并 CSV（月/名称/日期/类型/主题/品类/来源），供排期工作流直接使用。
- 前端报告中心新增「⬇ 全年排期CSV」按钮（fetch+blob 带鉴权下载）。

## 四、海外社媒算法研究（智谱联网）✅
- 落地 `research-inbox/overseas-social-algorithm-20260903.md`：
  - 算法信号：完播/长停留优先，收藏/分享权重升，搜索意图是新入口；TikTok Shop 闭环信号直接分流量；去重升级，First-Party Content 高权重，AI 滤镜/机械配音降权。
  - 内容启示：前 3 秒法则进化（避免标题党）；内容"可收藏化"（教程/攻略）；搜索思维埋关键词；原生 UGC 风替代 TVC 精致感。
  - 投放：TikTok 娱乐化原生广告 / IG Reels+Stories+美学；KOC 金字塔 + Spark Ads/Partnership Ads；CPA/ROAS 而非 CTR；小店站内闭环。
- 芥子→须弥：海外知识（须弥）→ 未来出海能力层（新能力）→ 真实投放反馈（芥子）。

## 五、验收
- 相关测试全绿；overview?global=1 与 ?export=csv 在线（csv 200）；现网 8201 已重启。
- 全量回归 reg52 见日志（EXIT=0 判定）。

## 六、下一轮候选
1. 前端卡片移动端适配 + 海外/行业下拉到 mobile 端（capability parity）。
2. 海外社媒策略落地创意引擎（virality/touchpoints 加出海策略层）。
3. 营销日历三维矩阵可视化（热力矩阵：行业×海外×节气）。
4. 更多垂直行业（电竞/宠物医疗/文旅大省）+ 东南亚/欧洲本地节点。
5. 报告弹窗接入 marketing_nodes（决策信息优先）。
