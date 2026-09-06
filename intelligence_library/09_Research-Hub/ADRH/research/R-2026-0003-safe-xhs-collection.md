# R-2026-0003 — 小红书「无公害采集」公共契约层（服务 Z-Brand）

- **Research ID:** R-2026-0003
- **AI Agent:** 豆包（Engineering Execution）
- **Created:** 2026-08-31T18:06:14+00:00
- **Source:** 用户直接决策（无官方 API / 只采集分析不发布 / 服务 Z-Brand / 后续上线公网）+ 四库 Audit
- **Repository:** Zachary-1012/AI-Development-Research-Hub
- **Lifecycle:** evidence（离线契约 + 真实移动网页 E2E 均已取证；待 ChatGPT/Human Review 后才进 verified/reusable）
- **遵循:** CHATGPT-INTERVENTION-PROTOCOL 九阶段；永久基线「三方反哺、互相验证、边界不破、能力共享、责任分明」

---

## 1. Research Question

在**没有小红书官方开放平台 API**、第一消费方为 **Z-Brand**、**只采集分析不发布**、且产品**后续要上线公网**的前提下，如何建立一套「无公害（低风控、合规、内部可用、公网安全）」的公共采集能力，且**不重复**三库已有的采集/学习实现。

## 2. Observed SHAs（本轮实时 Audit，非旧 SHA）

| 仓库 | Audit 时 HEAD | 备注 |
|---|---|---|
| Hub | `5918a67` | R-2026-0002 收尾，未变 |
| Z-Brand | `d16d000` | ZBIP 设计系统；采集后端所在仓库 |
| SICI | `0dc1885` → 审计时又前进到 `1bfda8e` | 小红书三工具横评 + 品牌舆情 8 项 + upgrade_modules |
| DDC | `f38c5c6` | CI 合并 Node+Python；`5de13d7` 点名补 Hub CI NOT_VERIFIED |

## 3. Audit：三库已有什么（避免重复造轮子）

**Z-Brand 已拥有完整采集后端（Owner，不复制）：** `collector.py`/`collector_v2/`、`rednote_collector.cjs`(Node Playwright)、`xhs_cdp_collector.py`(CDP)、`xhs_search.js`、cookie 桥（`import_xhs_cookies.py`/`xhs_cookie_bridge.py`）、`proxy_pool/`、`risk_engine.py`、`safety_boundary.py`、`security_scanner.py`、分析链 `ai_analyzer.py`/`subject_classifier.py`/`brand_report_generator.py`。
- 关键：`safety_boundary.py` 管的是「系统自愈操作的人工确认/备份/文件完整性」，**不覆盖采集内容 PII 脱敏、采集限速策略、采集 provenance 审计**——这正是缺口。

**SICI 已有的研究（只引用不重做）：**
- `shadow_run/xiaohongshu_bakeoff_report.md`：文档级横评 xiaohongshu-mcp / Spider_XHS / MediaCrawler，结论=参考 MediaCrawler 双池**架构思想**增强现有风控、不替换采集器；状态 researched，**未实际跑数**。
- `docs/research-learning/PLATFORM_LEARNING_LIBRARY_v3.md` PL-034~041：品牌/舆情 8 项（BrandShield、ai-social-listening、mcp-pr 等）。
- `upgrade_modules/dual_pool.py`（`1bfda8e`，399 行，候选未上生产）：Cookie+代理双池。

**DDC：** 工程治理/CI/Evidence Owner，本轮在补 CI。

## 4. 开源生态事实（2026 真实存在，Research Material）

- **官方开源模型（Apache-2.0，生成/理解层）：** rednote-hilab `dots.llm1`（1420 亿 MoE）、studio-dots-ai `dots3-note`、FireRedTeam `FireRed-Image-Edit/OpenStoryline`。
- **只读采集 MCP（无公害主攻形态）：** `KZI-22/xhs_mcp`（明确「本地单用户、只读」、读 `__INITIAL_STATE__`、扫码）、`Mol2017/rednote-mcp`、`J-ade-g/xiaohongshu-mcp`。
- **全链路 Agent（含发布，风险高，只学架构）：** xhs-ai-content-studio（人工确认+审计日志）、xhs_content_agent、xhs-workflow-skill、viral-note-agent。
- **风控事实（源码级综述）：** 升级链=验证码→限流/返回空→功能限制→封号；**低频克制只读最安全，高频写入才是封号重灾区**。合规通行原则：只采公开数据、遵守 robots、单 IP 间隔≥2–3s、个人信息脱敏、仅内部研究不售卖。
- 法律基线：平台 ToS 禁止自动化抓取；无官方授权时公网经营性服务风险显著高于内部研究。

## 5. Hypothesis

Hub 不写采集引擎，只提供与实现解耦的「**PII 脱敏 + 无公害策略 + 采集审计**」公共契约层并以离线测试锁定；Z-Brand/SICI 的既有采集器通过 adapter 接入该契约即可获得统一的合规/可追溯保证。这样既补齐 `safety_boundary.py` 的缺口，又不复制任何采集实现，且为公网阶段预留「采集侧端化、只输出脱敏后结论」的边界。

## 6. Findings 与关键设计决策

1. **不重复：** 采集引擎归 Z-Brand、移动面归 SICI；Hub 只做契约。现有 `research_record.sanitize()` 是「凭证 key 脱敏」，与本次「采集内容 PII/联系方式脱敏」不同层，不冲突。
2. **无公害硬规则（可执行化进 policy）：** 只读默认、只采公开、本机单账号、禁账号池/代理池（公网路径）、间隔≥2s（默认3s）、日量/批量上限、遇风控信号即停、写入必须人工确认。
3. **对 SICI `dual_pool.py` 的独立 Review 意见（互相 Review，非互信）：** 双池作为**候选研究模块保留**（只增不减、不越权改 SICI），但其多账号 Cookie 池/代理池**不得进入 Z-Brand 公网链路**；本机单用户自有 cookie 存储（cookie_vault）合理，池化轮换多账号在公网是红线。分歧留 ChatGPT/Human 复核。
4. **公网两段式架构：** 采集/脱敏在本机或侧端完成；Z-Brand 公网只承载「品牌洞察结论」，不搬运原始笔记、不在服务端囤多账号登录态；上线前过 DDC 权限/验证/Release gate。
5. **AI 输出不是 Evidence：** 离线测试与真实运行结果才算数。「扫码→搜索→取回 20 条」的联网 E2E 已在本轮由人工扫码、豆包执行完成并取证（见第 8 节）；在其真正完成前状态曾为 NOT VERIFIED，未提前冒称通过。

## 7. Implementation（本轮新增，全部 Hub 内）

- `src/contracts/safe_collection.py`：
  - `redact_text/redact_record`：字段级 PII（作者ID/昵称/头像/联系方式/精确定位）+ 文本内手机/邮箱/微信/QQ 脱敏，不改原对象；
  - `CollectionHygienePolicy`：声明式无公害策略 + `validate()` 违规检查（含公网禁池化/禁写）；
  - `RateGovernor`：可注入虚拟时钟的纯限速/日量/批量/风控判定，不真实 sleep、不联网；
  - `build_collection_audit`/`validate_collection_audit`：采集 provenance 审计记录（zachary.hub.collection-audit.v1），凭证兜底脱敏；
  - `run_offline_pipeline`：已取回数据的离线 shadow 管线（限速判定→脱敏→审计）。
- `tests/test_safe_collection.py`：28 个离线单测。

## 8. Tests / Evidence

- 全套 **73 → 101 pass / 0 fail**（Python 3.13 Windows，exit 0；新增 28；管线 `extra` 透传增强后复跑仍 101 OK）。
- 离线管线测试 `test_twenty_notes_offline_full_pass`：20 条样例、虚拟时钟间隔 3.5s 全放行、每条 2 个 PII 字段共脱敏 40、审计 `completed` 且校验通过——这是离线数据处理测试。
- **真实移动网页 E2E（本轮已取证，原"联网 NOT VERIFIED"转为已验证）：** 人工扫码登录本人单账号 → rednote 移动网页（www.rednote.com；账号地区 HK/SG，只记地区不记账号 ID）→ 搜索「广州太古汇」→ **只读结果列表、不打开详情、不发布/点赞/评论/关注**、每屏间隔约 3.6–3.7s → 取回 **20 条真实笔记**，全程风控信号 = 0；本地经 safe_collection 管线：`status=completed`、作者昵称脱敏 20 处、note_id/title/date 保留、昵称 0 泄漏、审计校验通过、限速等待全 0。证据文件：`data/shadow/redacted_xhs_guangzhou_tgk_20notes.json`、`data/shadow/audit_xhs_guangzhou_tgk_20notes.json`（含 policy_snapshot 与 provenance）；含昵称的原始临时文件已按数据最小化删除，不落地留存 PII。
- **仍 NOT VERIFIED：** ① 详情页正文/评论级采集（本轮刻意只到搜索列表层，请求更少更安全）；② 换关键词/更大批量/长时间的稳定性与风控率；③ Hub GitHub Actions 真实 Run（MCP 无 list_workflow_runs）；④ DDC capability_delta 13 tests 本地运行（沿自 R-2026-0002）；⑤ 公网上线路径（须先过 DDC 权限/验证/Release gate）。

## 9. 三方验证、Lifecycle 与 NEXT

- **Z-Brand（业务/生产）：** 未来由 Z-Brand 采集器以 adapter 调用本契约；本轮零改动。公网只出脱敏后结论。
- **DDC（工程）：** 上线前需其权限/Evidence/Release gate；契约层测试可纳入 CI。
- **SICI（移动）：** 复用横评结论，移动侧端采集同样过此契约；dual_pool 待复核。
- **Classification:** hub-original reusable-contract **candidate**（evidence）。
- **Lifecycle:** research→candidate→shadow→**evidence（当前）**；已具备离线 + 真实移动网页 E2E 证据，待 ChatGPT/Human Review 后才进 verified/reusable，不自动晋级。
- **NEXT FOR CHATGPT:** 以本轮新 HEAD 独立复核；重点审 ①是否与 Z-Brand/SICI 重复 ②dual_pool 边界判断是否认同 ③公网两段式是否充分。下一轮 R-2026-0004：人工本机跑数取证 + 设计 Z-Brand 侧 adapter（仍不复制采集器）。
