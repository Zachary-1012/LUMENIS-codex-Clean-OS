# 2026-10-20 Erratum — Global Data Source Research 2026-10-13

本勘误按 FIX-002、FIX-003 更正原报告的来源指针和内部口径。原报告
[GLOBAL-DATA-SOURCE-RESEARCH-20261013.md](GLOBAL-DATA-SOURCE-RESEARCH-20261013.md)
作为 2026-10-13 历史记录保留，不覆盖、不把本勘误解释为新一轮数据源调查或产品采集。
下列官方页面仅用于核对链接指向；可用性标签沿用原报告在 2026-10-13 的报告值，
不表示 2026-10-20 的实时可用承诺，也不证明产品已接入。

## FIX-002 — 来源指针与可用性列

已逐项检查原报告 §6–§8 中被清单指出的指针。可确认的官方入口如下：

| 原报告 ID | 更正后的官方入口 | 原报告可用性标签 | 更正说明 |
| --- | --- | --- | --- |
| B-007 | [J-PlatPat Trademark Search — Japan Patent Office](https://www.jpo.go.jp/e/support/j_platpat/trademark_search.html) | VERIFIED_PUBLIC | 原 URL 被截断；替换为日本特许厅商标检索官方说明页。 |
| B-008 | [Madrid Monitor — WIPO](https://www3.wipo.int/madrid/monitor/en/) | VERIFIED_PUBLIC | 原 URL 被截断；替换为 Madrid Monitor 官方入口。 |
| B-012 | [Find and update company information — Companies House](https://find-and-update.company-information.service.gov.uk/) | VERIFIED_PUBLIC | 原 URL 被截断；替换为英国公司注册查询官方入口。 |
| B-019 | [Top Ads — TikTok Creative Center](https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en) | CONDITIONAL | 原 URL 被截断；替换为 TikTok 官方 Top Ads 页面。原条件性标签保留。 |
| C-009 | [Apple Store 零售店，中国大陆](https://www.apple.com.cn/retail/storelist/) | VERIFIED_PUBLIC | 原 sitemap 地址拼写/路径不完整；改为当前官方门店列表页，不声称它是 sitemap。 |
| D-003 | [Places API (New) overview — Google Maps Platform](https://developers.google.com/maps/documentation/places/web-service/overview) | VERIFIED_AUTHORIZED | 原 API 文档 URL 被截断；更正为当前官方概览页。 |
| D-009 | [Consumer Sentinel Network — FTC](https://www.ftc.gov/enforcement/consumer-sentinel-network) | RESTRICTED | 原 URL 被截断；官方说明页指出访问限于获准的执法机构成员，保留原受限标签。 |
| D-010 | [Safety Gate: the EU rapid alert system for dangerous non-food products](https://ec.europa.eu/safety-gate-alerts/screen/search) | VERIFIED_PUBLIC | 原 URL 截断为 `/screen/sea`；更正为官方检索入口 `/screen/search`。原可用性标签保留。 |
| D-019 | 无可确认入口 | NOT VERIFIED | 原链接实际指向 Trustpilot 上的 Amazon 评论，与“黑猫投诉企业舆情/数据服务”不符；删除错链，不拿 D-006 黑猫公开投诉页替代该商业服务。 |
| F-006 | [Eurostat Database](https://ec.europa.eu/eurostat/web/main/data/database) | VERIFIED_PUBLIC | 原 URL 被截断；更正为 Eurostat 官方数据库页。 |
| F-016 | [Euro foreign exchange reference rates — ECB](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.eu.html) | VERIFIED_PUBLIC | 原 URL 被截断；更正为 ECB 官方参考汇率页。 |
| F-021 | [国家公共数据资源登记平台](https://sjdj.nda.gov.cn/) | CONDITIONAL | 原 URL 被截断；更正为国家数据局登记平台入口。原条件性标签保留；本勘误不声称它提供无条件公开数据/API。 |

§8.2 的表头应读作“Source ID｜来源名称｜来源入口”，不是“可用性”。该表第三列列出的是 URL，没有列出任何可用性值。列出的 G-004、G-005、G-006、G-008、G-010、G-011、G-013、G-014、G-015、G-016、G-018、G-019、G-022 在本仓库内均**缺少可用性证据（REPOSITORY EVIDENCE MISSING）**。这是本仓库证据层面的限定，不是对其可用性分类的改写，也不计入下文 227 条来源可用性分布中的 12 条 `NOT VERIFIED`；不得从 URL 存在推断其公开、获准或可接入。研究方的 G.md 未入库，剩余类别记录也未在此表展示，不能据此补写状态。

上述来源页面核对日期为 2026-10-20。除明确为官方入口核对外，本勘误未访问其业务数据、未执行采集、未检查凭证/授权，也未验证适配器或生产调用链。

## FIX-003 — 汇总统计与主体条目口径

1. 原报告 §1.1 的“150 条（66%），109 公开 + 41 授权”与修订表/§15 的 `104 + 41 + 48 + 18 + 12 + 4 = 227` 冲突。按修订表内部算术，已标为公开或授权的合计是 `104 + 41 = 145`，`145 / 227 ≈ 63.9%`（约 64%），不是 150 或 66%。12 条“未核实”是研究方修订表中的可用性分类，继续保持未核实，不升级为已核实；上文 §8.2 的 G 条目证据缺失限定与本条 D-019 的错链更正不改变这一分类计数，本勘误未重算该分布。
2. 该算式只统一原报告内部的汇总口径，不证明 227 个来源或 244 个目标的明细完整。原报告 §1.3、§15 说明除 C 类外的逐项分类文件未入库，因此这些分类及全量统计在仓库中不能独立复核，也不得作为生产覆盖分母或产品验收证据。
3. §20.1 汇总称商业主体 499、品牌 136、场内关系 133，合计 768；但 §20.2 商业主体表末尾明确记为“共 445 条商业主体”。按报告实际列出的详情口径，`445 + 136 + 133 = 714` 条混合记录单位，商业主体详情相较汇总少 54 条。原文没有给出这 54 条的身份，不能补造或推断已在种子文件/生产库中存在。
4. 499 + 136 + 133 的 768 是跨公司、品牌和关系的混合记录汇总，不是 768 个已核验的不同主体，也不证明生产注册表覆盖。关系记录不应按独立主体计数；报告中的 445 条详情与 499 条汇总差异保持 **UNRECONCILED / NOT VERIFIED**，不据此改写数据或生产分母。

本勘误仅纠正读者对原报告内部数字、链接和状态列的解释；没有重算研究分类文件、扩充采集目标或宣称任何业务来源已接入。
