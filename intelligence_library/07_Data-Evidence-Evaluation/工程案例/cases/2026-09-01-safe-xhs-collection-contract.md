# CASE-2026-0013 — 小红书无公害采集公共契约层（Hub 原创候选能力）

- **case_id:** CASE-2026-0013
- **origin_research_id:** R-2026-0003
- **source_repo:** Zachary-1012/AI-Development-Research-Hub（hub-original；外部研究对象见第 3 节）
- **license:** Internal (Zachary AI Platform)；外部开源模型以各项目 Apache-2.0 为准
- **maintenance_status:** active
- **research_value:** high　**adaptation_value:** high　**risk:** medium
- **lifecycle:** evidence（candidate reusable contract；离线 + 真实移动网页 E2E 已取证，待双 AI Review）
- **created:** 2026-08-31T18:06:14+00:00

## 1. 案例来源
用户决策（无官方 API、只采集不发布、服务 Z-Brand、后续公网）+ 四库 Audit + 2026 开源生态调研。对应实现 `src/contracts/safe_collection.py`。

## 2. 为什么值得研究
「采集→分析」是 Z-Brand 品牌/舆情业务的入口，但无官方 API 时采集天然带账号与合规风险；且三库已有大量采集/学习资产，重复写采集器既浪费又制造耦合。值得研究的是：**如何把"无公害/合规/可追溯"沉淀成与采集引擎解耦、三库可共用的契约层。**

## 3. 原项目/现状分别解决什么问题
- **Z-Brand（Owner）：** `rednote_collector.cjs`/`xhs_cdp_collector.py`/`collector_v2` 负责真实采集；`risk_engine` 风控、`safety_boundary` 操作级人工确认、`proxy_pool` 代理、cookie 桥。
- **SICI：** `xiaohongshu_bakeoff_report.md` 横评 xiaohongshu-mcp/Spider_XHS/MediaCrawler（researched，未跑数）；`upgrade_modules/dual_pool.py` 双池候选。
- **外部只读 MCP（KZI-22/xhs_mcp 等）：** 本机单账号、扫码、只读、读页面结构化状态，是无公害形态样板。
- **官方模型 dots.llm1/FireRed（Apache-2.0）：** 负责生成/理解，不负责采集。

## 4. 我们可以吸收什么
- 只读 MCP 的「本机单账号 + 人工扫码 + 只读」形态；
- 风控综述的「低频克制只读、遇验证码即停、高频写入才高危」结论；
- Z-Brand 既有采集能力（通过 adapter 复用，不重写）；
- 将其上升为**可执行 policy + PII 脱敏 + provenance 审计**三件套。

## 5. 哪些不能照搬
- **不照搬** MediaCrawler/dual_pool 的多账号 Cookie 池 + IP 代理池到公网链路（ToS/个保法/封号高风险）；
- 不照搬全链路 Agent 的「自动发布/自动评论」（本需求只采集不发布，写入必须人工门禁）；
- 不做验证码/签名/设备指纹绕过；不把社区 license 不明的爬虫代码拷进产品。

## 6. License / Provenance
- Hub 契约代码：Internal。
- dots.llm1 / dots3-note / FireRed：Apache-2.0（可商用友好，仍需逐仓复核 LICENSE 与模型使用条款）。
- 社区采集 MCP/Agent：多数 license 不明确，**只学设计、不抄代码**。
- 本案例所有外部事实均为 Research Material，不直接成为生产事实。

## 7. 如何适配三方平台
- **Z-Brand：** 采集器在本机/侧端产出原始记录 → 过 `safe_collection` 脱敏与审计 → 仅把脱敏后分析结论送入公网产品；通过 adapter 调用，不复制契约实现。
- **SICI：** 移动/侧端触发同样走该契约，横评结论作为采集通道选型输入。
- **DDC：** 把契约测试与审计记录纳入验证/Evidence/Release gate；公网上线前强制校验 policy.is_safe()。

## 8. 是否值得写代码 / 实验结果
**值得，但只写契约层。** 已实现并离线实验：
- `src/contracts/safe_collection.py` + `tests/test_safe_collection.py`（28 测试）；
- 全套 73→**101 pass/0 fail**（Python 3.13 Windows exit 0）；
- 离线 20 条 shadow 管线：限速判定、40 处 PII 脱敏、审计记录 completed 全部验证。
- **真实移动网页 E2E（2026-08-31 已取证）：** 人工扫码单账号登录 rednote 移动网页，搜索「广州太古汇」，只读结果列表、不进详情、不发布、约 3.6s/步，取回 20 条真实笔记、零风控信号；本地脱敏 20 处作者昵称、0 泄漏、审计 completed，证据存 `data/shadow/redacted_xhs_guangzhou_tgk_20notes.json` 与 `audit_xhs_guangzhou_tgk_20notes.json`（含昵称的原始临时文件已删除）。
- **仍 NOT VERIFIED：** 详情正文/评论级采集、换词与大批量稳定性、公网上线路径（须过 DDC gate）。

## 9. 风险与回滚
- 风险：平台 ToS/账号风控（以只读低频+人工触发+公网不囤登录态缓解）；PII 脱敏正则漏网（以字段级+文本级双保险并持续补样例）；dual_pool 越界进入公网（policy.validate 硬性拦截 + Review）。
- 回滚：本能力为独立新增契约模块，三产品仅通过 adapter 引用；移除引用即完全回滚，不改任何既有采集器与生产代码。
