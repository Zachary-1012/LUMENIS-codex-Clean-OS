# R-2026-0004 — 双端无公害采集策略：详情层字段、话题/舆情监测、双自有账号交叉与 Cookie 生命周期（服务 Z-Brand / SICI）

- **Research ID:** R-2026-0004
- **AI Agent:** 豆包（Engineering Execution）；ChatGPT 待独立复核
- **Created:** 2026-08-31T19:12:00+00:00
- **Source:** 用户直接决策（双端、双自有账号交叉、养号、常驻真人化、cookie 周期刷新、话题端/负面舆情监测、小火慢炖）+ 本轮真实浏览器只读探查
- **Repository:** Zachary-1012/AI-Development-Research-Hub
- **Lifecycle:** research（策略设计 + 详情层/真人节奏真实样本证据；账号与 cookie 策略的代码化留下一轮离线实现+测试，并待 ChatGPT/Human 复核，不自动晋级）
- **前置:** R-2026-0003（safe_collection 契约层，evidence）；遵循 CHATGPT-INTERVENTION-PROTOCOL 九阶段与永久基线「三方反哺、互相验证、边界不破、能力共享、责任分明」

---

## 1. Research Question

在 R-2026-0003 已建立「列表层只读 + 本地脱敏 + 采集审计」契约的基础上，回答四件事：

1. 详情层的**点赞/收藏/评论数、正文、笔记 id、作者昵称**到底能不能采、在哪采、怎么不被侧栏推荐流干扰；
2. 如何做**广州太古汇相关话题端监测与负面笔记识别**，并做到**自适应**（自动发现话题入口、按风控反馈调速）；
3. 在「无官方 API、后续上公网、只采集分析不发布」前提下，如何用**两个用户自有账号（rednote 国际版 + 内地小红书）交叉、养号、常驻内置浏览器真人化、cookie 周期刷新**来把风险降到最低（小火慢炖），同时**不削弱** R-0003「公网禁账号池/代理池」红线；
4. Hub 在其中只沉淀什么（策略/契约/schema），哪些必须留给 Z-Brand/SICI，避免重复造轮子。

## 2. Observed SHAs（本轮实时 Audit，非旧 SHA）

| 仓库 | 本轮 Audit 时 HEAD | 变化/备注 |
|---|---|---|
| Hub | `a016b2b` | 上一提交 `fb26ad9`(R-0003 收尾) 后新增 `a016b2b`「ZBIP unified architecture/mobile baseline」，**仅新增 1 份 docs，未触碰 records/research/shadow/src/tests，无冲突** |
| Z-Brand | `e23c5bc` | 采集后端/cookie 桥 Owner（较 R-0003 的 d16d000 已前进，本轮零改动） |
| SICI | `bb22dfa` | 移动面/横评/舆情 Owner（较 1bfda8e 前进，本轮零改动） |
| DDC | `a430ba9` | 工程治理/上线 gate（较 f38c5c6 前进，本轮零改动） |

## 3. 本轮真实探查事实（只读，人工浏览 + 豆包被动观察，未点赞/收藏/评论/发布）

### 3.1 详情层字段可达性（以 rednote 详情 `6a959633`《广州方所十五年闭店，往事如烟》当场取证）

主互动栏容器与选择器已**在真实页面钉死**（不是推测）：

| 字段 | 选择器（rednote web） | 实测值 | 说明 |
|---|---|---|---|
| 点赞数 | `.interact-container .like-wrapper` | 34 | 主笔记互动栏 |
| 收藏数 | `.interact-container .collect-wrapper` | 4 | 主笔记互动栏 |
| 评论数 | `.interact-container .chat-wrapper` | 4 | 主笔记互动栏 |
| 正文 | `.note-content .desc`（`.note-content` 含标题） | 389 字 | 末尾带「昨天 22:56 广东」时间+地区 |
| 笔记 id | URL `/discovery/item/<24hex>` | 6a959633… | 内容标识，按 R-0003 契约**刻意保留** |

- **关键坑（已实证）：** 侧栏/下方推荐笔记卡片只有 `.like-wrapper`、没有 `.collect-wrapper/.chat-wrapper`，且几何聚簇会把评论区某条评论的 `.like/.reply/.interactions` 也混进来。**唯一可靠判据 = 同时含 like/collect/chat 三个 wrapper 的 `.interact-container/.buttons.engage-bar-style`**；禁止用「页面上所有图标数字」或几何聚簇来猜赞藏评。
- `.like-wrapper` 上出现 `like-active` class 属组件类名，**不得据此推断用户点了赞**（本轮行为监测 write_action 全程为 0）。
- 证据：`data/shadow/detail_sample_6a959633_redacted.json`（单篇详情层可行性样本；作者昵称/作者 id/xsec_token 均未存储，正文经 redact_text，联系方式命中 0）。

### 3.2 真人浏览节奏基线（SICI 真实工作流反馈 + 拟人速率依据）

豆包被动采样用户本人手动浏览（每 2s 只读路由/滚动/互动态，不替点不导航），两窗口合并，证据 `data/shadow/human_browse_behavior_session1.json`：

- 进入 **3 篇详情**，单篇停留 **min 4.1s / 中位 18.5s / max 26.3s / 均值 16.3s**；列表挑选停留 8.1–88.6s。
- 全程 `any_write_action_active_seen=false`：真人也是**纯只读**浏览。
- 结论：真人不是均匀机器节拍，而是「列表慢挑 → 进详情读 4–26s → 返回滚动 → 再进」。自动化详情间隔应对齐该量级（中位 ~18s），**显著松于** R-0003 列表层 ~3.6s/步；越快越像机器、风险越高。

### 3.3 双端差异与「问点点」（用户截图 s3–s5 实证）

- **rednote 国际版（www.rednote.com，HK/SG）：** 无官方「问点点」AI；搜索结果顶部为 笔记/用户 tab；详情互动栏=♡☆💬 横排。**主采集端。**
- **内地小红书（www.xiaohongshu.com，红色 logo）：** 搜索顶部有 **笔记 / 用户 / 问点点(ai)**；「问点点」可把某话题下 67/68 篇笔记**官方自动总结**成结构化要点（如「一方五境」展期/地点/门票、拍照机位攻略）。**辅助分析 + 交叉验证端。**
- 边界：「问点点」产出是**平台官方 AI 生成的二手总结**，只能作为话题理解/交叉参照，**不能当作我们自己采集的原始 Evidence**（AI 输出不是 Evidence，R-0003/介入协议一致）；原始笔记仍以只读采集为准。

## 4. 用户决策（Human Directive，只增不减）

1. **只读数、不点赞/不收藏/不评论/不发布**；采集回来在系统内做分析。
2. 分析目标：**赞藏评数 + 正文 + 负面笔记识别**，做广州太古汇**相关舆情 / 话题端监测**，并**自适应**找到话题端入口（话题标签聚合页、问点点入口）。
3. **Cookie 继续用**；最好**每天早上定时登录/保活**；小公司把 rednote **固定挂在内置浏览器常驻**，要采集就用、不采集时人也上去手动逛，**真人行为更强**。
4. **不频繁弹扫码、不大规模批量，小火慢炖**；**每隔 3 天更新一版 cookie**，直到彻底稳定或出现更合适方式。
5. **先把原账号养几天再回来**；**两个账号交叉进行**（rednote 国际版主采 + 内地小红书辅助），交叉降低单账号风险。
6. **硬限制：只允许这两个小红书账号被采集使用，并且交叉**——这是白名单上限，不是可扩张的账号池。

## 5. 关键设计（Hub 只做与实现解耦的策略/契约；代码化留下一轮）

### 5.1 字段可达性与采集分层

| 层 | 可取字段 | 请求成本 | 默认策略 |
|---|---|---|---|
| 搜索列表层 | note_id、标题、时间、**点赞数(仅这 1 个外露整数)**、作者昵称(脱敏) | 低（R-0003 已验证 20 条零风控） | 常规扫描/发现入口 |
| 详情层 | 赞/藏/评三数、正文、时间地区、note_id | 中（每篇一次详情请求） | 仅对命中话题/疑似负面的笔记**按需少量**进入，间隔对齐真人 ~18s 量级 |
| 评论层 | 评论数可留；评论正文/评论者=又一层 PII | 高（要展开评论区） | **本阶段不采评论内容**，只留评论数 |
| 作者侧 | 昵称/user_id/sec_uid/xsec_token | — | 昵称内部临时可见、落盘/公网前脱敏；user_id/sec_uid/xsec_token **不落地不外存** |

### 5.2 双端 + 双自有账号白名单交叉（增量，不削弱公网红线）

- **internal（本机/侧端、用户自有、只读出分析）：** 允许且仅允许 **2 个白名单自有账号**（A=rednote 国际版主采，B=内地小红书辅助+问点点交叉）；`AccountPlan` 为纯逻辑：白名单外账号一律拒绝、两账号**交替轮转**摊薄单账号频率、单账号日量/连续工作时长设硬上限、强制冷却。上限=2 写死，**禁止扩张成账号池**。
- **public_web（Z-Brand 公网链路）：** 维持 R-0003 红线不变——**禁止任何账号池/代理池/服务端囤登录态**，公网只出脱敏后品牌/舆情结论。internal 的双账号交叉**不得**平移到公网。
- 与 SICI `dual_pool.py` 的关系不变：双池仍是候选研究、不进公网；本轮 Human 明确的「2 自有账号交叉」仅在 internal 侧成立，需 ChatGPT/Human 在 Review 中确认该边界表述。

### 5.3 Cookie 生命周期契约（Hub 定节奏与状态，不碰凭证本体）

- Hub 只定义**与凭证解耦**的纯逻辑：健康状态枚举（fresh/aging/expired/relogin_required）、`refresh_interval_days=3`、每日早上保活检查点、到期判定（可注入时钟，离线可测）；**绝不存储 cookie/token/密码明文，也不进 git**（沿用 .gitignore 与 secret 扫描）。
- cookie 的实际存储/桥接/刷新执行归 **Z-Brand（cookie_vault/xhs_cookie_bridge）与 SICI**；需要人工扫码时按 browser-use 规则交回用户，且**避免频繁弹扫码**（常驻保活 + 3 天周期刷新正是为了减少打断）。
- 养号期：账号先自然养几天，期间只被动观察/极少量只读，不做批量。

### 5.4 话题端监测、负面标注与自适应

- **话题入口发现（自适应）：** 从搜索结果/笔记正文识别话题标签 `#…`、话题聚合页、问点点入口，建立「话题→入口 URL 形态→笔记集合」的索引（只记录入口与 note_id，不搬运作者 PII）。
- **负面笔记标注：** 对已脱敏的标题+正文做情感/风险标注（如 negative / complaint / risk_topic：闭店、差评、拥挤、安全、投诉等），输出**标签与证据 note_id**，不发布、不互动；标注属分析结论，可追溯到原始脱敏样本。
- **自适应调速：** 复用 R-0003 `RateGovernor` 与 RISK_STOP_SIGNALS——出现验证码/限流/空结果即降速或停，真人节奏为上限基线；不硬闯。
- 问点点总结作为**辅助交叉**：与我们只读采集的原始结论比对一致性，但单独标记 `source=official_ai_summary`，不算原始 Evidence。

## 6. 四库边界（责任分明，不复制核心代码）

- **Hub（本仓）：** 只新增策略/契约/schema 与离线纯逻辑（字段选择器文档、AccountPlan 白名单交叉、CookieHealth 状态机、TopicIndex/Sentiment 标注契约）、脱敏后证据；**不写采集引擎、不存凭证、不变成运行时**。
- **Z-Brand：** 采集器/CDP/Playwright、cookie vault、分析链与公网结论发布；以 adapter 调 Hub 契约。
- **SICI：** 移动交互/设备约束/真人工作流与双端 App 雏形；提供移动面反馈。
- **DDC：** 权限、测试、Evidence、Rollback、公网上线 gate。
- 三产品**不复制同一份核心实现**；Hub 不拥有三仓库，只记录验证关系。

## 7. 本轮 Evidence

- `data/shadow/detail_sample_6a959633_redacted.json`：详情层赞 34/藏 4/评 4、正文 389 字、选择器 provenance；作者/token 未存。
- `data/shadow/human_browse_behavior_session1.json`：真人浏览节奏（详情停留中位 18.5s、write=0）。
- 选择器与双端「问点点」由真实页面/用户截图当场确认；未使用任何模拟值冒充真实采集。

## 8. 仍 NOT VERIFIED / 风险

- **NOT VERIFIED：** ① AccountPlan/CookieHealth/TopicIndex/Sentiment 的代码与离线单测（本轮只做设计，留下一轮）；② 详情层连续多篇、换关键词、长时间的风控率与稳定性（养号期不压测）；③ 内地小红书端只读采集与问点点入口的稳定 URL 形态；④ 双账号交叉长期是否真能降风险（需数周观察，不可提前下结论）；⑤ Hub GitHub Actions 真实 Run；⑥ 公网上线路径（须过 DDC gate）。
- **合规风险：** 平台 ToS 仍原则禁止自动化抓取；双账号交叉、养号、常驻登录只在「用户自有账号 + 本机内部 + 只读 + 小火慢炖」下作为内部研究降险手段，**不改变 ToS 灰色性质**，公网经营化必须另走授权/过 DDC；绝不做账号买卖、代理池、绕验证码/签名、规模化批量。

## 9. Lifecycle 与 NEXT

- **Classification:** hub strategy/contract **candidate**（research 阶段，含真实样本证据）。
- **Lifecycle:** research（当前）→ 下一轮离线实现 AccountPlan/CookieHealth/TopicIndex/Sentiment 纯逻辑 + 单测进 candidate/shadow → 养号数日后小样本真实详情取证进 evidence → 双 AI Review 后才 verified/reusable，不自动晋级。
- **NEXT FOR CHATGPT:** 重点审 ①internal「2 自有账号交叉」与 public_web「禁池化」红线的边界表述是否严密、有无被扩张解释的空间；②Cookie 生命周期只定状态不碰凭证的切分是否足够；③问点点官方 AI 总结定位为辅助交叉、非 Evidence 是否认同。
- **NEXT FOR DOUBAO（下一轮，养号期不批量）：** 以离线纯逻辑实现并单测化 5.2/5.3/5.4，跑全套测试，真实详情只在用户自然浏览时被动取极少量样本。
