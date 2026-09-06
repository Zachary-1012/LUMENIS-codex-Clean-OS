# OSAI 第十七期 · 营销节点芥子须弥 + 科特勒×库克增长知识 + 工程四升级

日期：2026-09-03
定位：研究自循环（不再等指令学什么）+ 四项工程升级全部落地。

---

## 一、营销节点日历：芥子（数据）→须弥（适配逻辑）
- 研究：智谱 web_search 全年营销节点（24 节气/传统节日/电商大促 618·双11/国际节点），落盘 research-inbox/marketing-calendar-2026-20260903.md。
- 落地：ZBC 新增 `scripts/marketing_calendar.py` —— 12 月 55+ 节点数据（name/date/kind/theme/cats）+ 品类适配逻辑：
  - `suggest_hotspot(date, category)`：日期+品类 → 命中节点 + 情感主题 + 建议调性（核心芥子→须弥函数）；
  - `nodes_for_month` / `node_on`：排期与当日参考；
  - `_CAT_ALIAS`：品类→泛化关键词（触类旁通，商业地产关联零售/餐饮/亲子/跨年活动）；
  - `_THEME_TO_TONALITY`：情感主题→调性（狂欢→mass，浪漫→premium，仪式→luxury）。
- 接入方案拆解：pitch-analyze 返回新增 `marketing` 字段（当月节点+主题+建议调性），方案自动带出"节点适配"。
- 自循环延伸已建立：OSAI 可继续扩充垂直节点（母婴/美妆/酒类/文旅行业节点）。

## 二、科特勒（Kotler）营销理论 → ZBC 落地映射
研究落盘 kotler-marketing-theory-20260903.md，贯通到现有架构：
| 科特勒框架 | 本质 | ZBC 落地 |
|---|---|---|
| STP（细分/目标/定位） | 为谁服务、如何差异化 | pitch-analyze 的圈层识别+调性检测+定位建议（extracted 字段） |
| 4P→4C→4R | 产品导向→顾客导向→关系导向 | 渠道检测、参与式/共创机制（4R 的关系回报） |
| 顾客让渡价值 CDV=TCV-TCC | 提高价值/降低成本 | 报告"决策信息优先"+真实数据不造假（降低用户决策成本） |
| 品牌资产（知名度/忠诚/感知质量/联想） | 长期附加价值 | 符号化机制（symbolize）、情感共鸣→品牌联想 |
| 营销5.0（人本化科技/AI） | 预测性·个性化·敏捷 | Zachary AI 用 ZBC 真实数据做预测性创意与个性化方案 |

## 三、蒂姆·库克（Tim Cook）商业可成长性 → ZBC 落地映射
研究落盘 timcook-business-growth-20260903.md：
- "运营即战略"：库存即魔鬼/JIT → 对应采集稳定性/数据新鲜度（last_success_at/Retry/Backoff/熔断），系统可靠性是底座；
- 生态+服务第二曲线 → 对应跨端（Web/App/Mobile/小程序）+ 报告体系 + 创意引擎服务化；
- 品牌溢价+社会责任护城河 → 对应合规 Gate/证据可追溯/用户信任；
- 用户价值锁定（14 亿安装基数网络效应）→ 对应圈层语言（CIRCLE_SYMBOLS）与情感共鸣留人。

## 四、本轮工程四升级（全部落地+验证）
1. **工程回合最小 diff**：`run_engineering_round(mode="edit")` 支持修改现有文件（scripts/tests 白名单、old_snippet 唯一校验、应用前备份 .bak、py_compile 验证、回归失败回滚 .bak；new 模式保留且纠正重试仅 new 触发）。OSAI 测试 8 项全绿。
2. **pitch 抽取 pptx/docx**：`analyze_pitch_file` 新增 `.pptx`（每页标题/正文/表格）/`.docx`（段落+表格）抽取；前端上传 accept 扩展；实测抽取成功。
3. **品类/圈层符号扩充**：语义角色 +4（beauty 美妆悦己/family 母婴家庭/sport 户外运动/wine 酒饮社交）+ 意象槽位 + _EMO_ROLE_COMPAT；圈层 +3（疗愈系/露营旷野/夜生活）。
4. **小程序端创意引擎**：新增 `static/creative-mobile.html`（移动端优先、响应式、web-view 可嵌入、凭证动态注入零硬编码），复用 /api/creative/ideas 真实数据。

## 五、验收
- ZBC 新增测试 12 项全绿（营销日历 6 + pitch marketing/新角色 2 + 引擎类既有全绿）；现网 8201 mobile/workbench 200、pitch-analyze 返回 marketing 字段。
- 全量回归 reg47 结果见日志（EXIT=0 判定）。
- 双库推送 commit 见本轮 git log。

## 六、下一轮候选
1. 营销日历接创意引擎 hotspot 自动增强（idea_generator 自动带出当月节点主题）。
2. 报告体系消费 topic_label+营销节点（日报/月报带"本月节点适配"）。
3. 垂直行业节点扩充（母婴/美妆/酒类/文旅）+ 圈层符号持续研究。
4. 工程回合 edit 模式真实跑一轮（智谱改现有文件→回归→推送）验证闭环。
5. 移动端→真小程序（web-view 嵌入文档/指引）。
