> Status: **CURRENT SUBORDINATE REAL-DELIVERY OVERLAY / NOT A SECOND PRODUCT OR EXPERIENCE AUTHORITY**
>
> Authority boundary: this overlay adds delivery evidence and commercial-readiness gates to the fixed 15-round sequence. It does not add a sixteenth round, change dependency order, replace the sole Product Architecture or Experience Constitution, or erase correctly completed source work.
>
> Canonical path: `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md`.

序境 / LUMENIS
15 轮“真实交付约束”强制补充协议
REAL DELIVERY OVERLAY FOR ALL 15 ROUNDS

本协议是当前 15 轮计划的强制叠加约束。

它不增加第 16 轮，不改变现有 15 轮依赖顺序，不推翻已经批准的 Product Architecture。
它的目的只有一个：

禁止把“代码完成、测试通过、页面能打开、API 200、Adapter 注册、模型安装、健康检查正常”
误判为“产品已经能交付给真实用户”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
一、全 15 轮统一最高验收原则
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

任何一轮的 PASS，必须同时回答下面 8 个问题：

1. REAL INPUT
   本轮处理的输入是真实生产输入、真实业务输入，还是 fixture / mock / sample？

2. REAL OWNER
   本轮结果是否来自唯一 canonical owner？

3. REAL SCOPE
   是否绑定真实 Actor / Subject / BrandFocus / Product / Domain scope？

4. REAL EVIDENCE
   用户看到的事实、数字、结论和动作能否追溯到真实 Evidence？

5. REAL STATE
   缺失、失败、未配置、无权限、无新数据、未知是否被严格区分？

6. REAL ACTION
   如果有操作，它是否真的经过 Permission / Approval / Effect Fence，并产生真实结果？

7. REAL USER RESULT
   这一轮完成后，真实用户到底多完成了哪一件工作？

8. REAL OPERATING EVIDENCE
   本轮能力只是代码存在，还是已经在真实运行环境中验证？

如果上述任意问题无法回答，不得只写 PASS。

必须使用：

PASS
PARTIAL
BLOCKED
LIVE_UNVERIFIED
NOT_CONFIGURED
DEFERRED

之一。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二、全局禁止的“假完成”
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

以下任何情况都不得单独作为完成证据：

- HTTP 200
- bound=true
- registered=true
- adapter exists
- route exists
- model installed
- provider configured
- cookie file exists
- health_check success
- screenshot renders
- widget test passes
- fixture contains rows
- DB table exists
- API schema matches
- Flutter build succeeds
- CI green
- one manual request succeeds
- empty list returned
- zero returned
- fake demo data
- historical data snapshot
- generated report file exists
- AI produced an answer
- Agent completed a task object

这些最多只能证明 IMPLEMENTED / TESTED 的一部分。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
三、统一完成语义
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPLEMENTED
= 源码能力存在。

TESTED
= 隔离/自动测试通过。

LIVE_VERIFIED
= 当前环境下真实输入和真实调用验证成功。

USER_VERIFIED
= 真实用户可以完成目标工作，不依赖开发者解释。

RELEASED
= 安全、迁移、回滚、构建、部署、CI/Tier C 满足。

OPERATING
= 能力持续运行并持续产生真实结果。

COMMERCIAL_READY
= 用户、数据、权限、运行、支持、恢复和交付全部满足商业使用要求。

任何阶段都不得升级状态词。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
四、每轮必须生成 REAL DELIVERY CARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

每轮结束时，Sol 必须额外生成：

REAL DELIVERY CARD

ROUND：
CURRENT SHA：

GLOBAL UNIVERSE / DATA MATURITY IMPACT：
- GLOBAL CTH maturity impact：本轮责任、已验证、未成熟、后续 owner/round
- GLOBAL BMP maturity impact：本轮责任、已验证、未成熟、后续 owner/round
- Guangzhou Taikoo Hui reference-loop impact：本轮责任、已验证、未成熟、后续 owner/round
- `Global Commercial Coverage = YES / NO / PARTIAL / BLOCKED / LIVE_UNVERIFIED`
- `Global Brand Coverage = YES / NO / PARTIAL / BLOCKED / LIVE_UNVERIFIED`
- `Guangzhou Taikoo Hui Reference Coverage = YES / NO / PARTIAL / BLOCKED / LIVE_UNVERIFIED`
- `LUMENIS_INTERNAL_FULL_UNIVERSE_READY = YES / NO`

RANDOM ENTITY DATA ACCEPTANCE：
- sample seed / sample count / sample IDs
- non-empty valid result rate
- stale / blocked / failed rate
- Evidence trace rate
- empty-state defects
- maturity delta since prior round

REAL USER：
本轮面向什么真实用户？

REAL USER JOB：
用户要完成什么实际工作？

REAL INPUT：
真实输入来自哪里？

REAL OUTPUT：
用户真正得到什么？

SOURCE：
数据/事实来源。

EVIDENCE：
如何追溯？

PERMISSION：
谁可以访问/执行？

FAILURE STATE：
失败时用户看到什么？

NOT_COLLECTED：
哪些东西当前真实没有？

LIVE TEST：
做了什么真实运行验证？

CONTINUOUS TEST：
是否证明连续运行？

USER ACCEPTANCE：
是否有人不看源码即可完成工作？

EXTERNAL DEPENDENCIES：
哪些依赖代码无法解决？

FINAL STATUS：
IMPLEMENTED / TESTED / LIVE_VERIFIED / USER_VERIFIED / OPERATING

NEXT GAP：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
五、ROUND 01 — Current Truth
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROUND 01 不只是“扫描仓库”。

必须最终回答：

- 当前真正存在什么能力？
- 当前真正运行什么？
- 当前哪些只是旧代码？
- 当前哪些只是 Adapter？
- 当前哪些只是 Contract？
- 当前哪些有真实数据？
- 当前哪些有真实用户入口？
- 当前哪些是假的 ready / bound？
- 当前哪些依赖外部凭证/接口？
- 当前哪些数据源完全缺失？

必须建立：

CURRENT CAPABILITY TRUTH MATRIX

每个能力至少标记：

SOURCE EXISTS
IMPLEMENTED
TESTED
LIVE VERIFIED
USER EXPOSED
OPERATING
EXTERNAL DEPENDENCY

禁止仅根据文件存在判定能力。

ROUND 01 EXIT：

必须能明确列出：

A. 真实存在且可运行
B. 源码存在但未运行验证
C. 只有接口/骨架
D. Historical
E. Missing
F. External blocked

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
六、ROUND 02 — Authority / Only-One / Compatibility
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只完成文档和命名统一。

必须证明：

- 每个重要能力只有一个 canonical owner
- 每个 compatibility caller 最终指向哪里
- 没有第二套业务真相
- 没有第二套 API owner
- 没有第二套数据 owner
- 没有第二套 Permission / Evidence
- 四 Surface 不复制业务逻辑
- 旧能力没有因为“清理”被删掉

必须生成：

OWNER → CALLER → USER CAPABILITY MATRIX

用户最终看到的每个能力必须可以回溯到一个 owner。

如果一个旧 caller 仍有唯一业务行为：
不得删除。

ROUND 02 EXIT：

不存在 UNKNOWN OWNER 的核心商业能力。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
七、ROUND 03 — Database / Canonical Truth
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只证明：

sqlite3.connect = 0
或者 tests passed。

必须证明：

真实数据：

Source
→ Write
→ Canonical DB
→ Read
→ ViewModel

没有出现：

- fixture 污染生产
- test 打开生产数据库
- silent migration
- missing → 0
- duplicated schema truth
- stale DB path
- runtime state 写源码目录
- 数据字段语义漂移

必须选择至少一条真实记录，证明：

RAW SOURCE
→ EVIDENCE ID
→ CANONICAL ROW
→ METRIC / OBJECT
→ USER READ

必须记录：

- DB path
- migration version
- row identity
- source identity
- timestamps
- rollback

ROUND 03 EXIT：

数据库不只是“干净”，而是能够承载真实业务事实。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
八、ROUND 04 — Identity / Context / Permission / Evidence
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须使用真实权限场景验证：

用户 A
→ 可以访问 Subject A
→ 不可访问 Subject B

用户 B
→ 权限不同

还必须证明：

选择 Subject ≠ 获得授权

选择 BrandFocus ≠ 获得授权

Client Header ≠ 权限

Cookie Session ≠ LUMENIS Actor

每个真实业务 read：

Actor
→ Permission
→ Scope
→ Data
→ Evidence

每个真实 action：

Actor
→ Permission
→ Approval
→ Effect
→ Evidence
→ Return

必须至少执行：

- authorized read
- unauthorized read
- cross-scope read
- missing actor
- missing scope
- permission backend failure
- Evidence lookup
- action denial

ROUND 04 EXIT：

不能跨客户、跨 Subject、跨 BrandFocus 泄露。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
九、ROUND 05 — Runtime / Health / Recovery
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只证明 healthz = 200。

必须做真实 failure drill：

- Product Core 崩溃
- Worker 崩溃
- Queue backlog
- DLQ
- Browser 失联
- Collector 失败
- AI provider offline
- DB temporary failure
- Session expired

必须证明：

Failure
→ Detect
→ Honest State
→ Diagnose
→ Recovery
→ Return

并且：

失败不能显示为：

0 data
ready
healthy
empty success

必须生成：

RUNTIME FAILURE MATRIX

ROUND 05 EXIT：

至少一个完整失败恢复流程真实跑通。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十、ROUND 06 — Collector / Browser / Acquisition
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须生成：

PLATFORM LIVE CAPABILITY MATRIX

逐平台覆盖：

- 小红书
- 抖音
- 微博
- B站
- 知乎
- Instagram
- Facebook
- X
- 微信公众号公开文章 / Sogou WeChat
- 快手
- TikTok
- 视频号
- RSS
- Public HTTP
- Atom
- Sitemap
- 当前 main 中其他真实 Adapter

每个平台必须记录：

Adapter
Search
Detail
Comments
Creator
Auth
Cookie
Session
Proxy
Provider
Live Connectivity
Real Result
Evidence
Canonical Persistence
Scope
Rate Limit
Risk
Recovery
Continuous Operation

分类只能是：

OPERATING
LIVE_VERIFIED
IMPLEMENTED_LIVE_UNVERIFIED
PARTIAL
NOT_CONFIGURED
PLANNED
BLOCKED
ABSENT

至少所有已有真实实现的平台必须尝试授权 live acceptance。

禁止：

Adapter exists = working
Cookie exists = valid
Health OK = collection works
one success = operating

ROUND 06 EXIT：

必须明确知道“哪些平台现在真的能给客户数据”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十一、ROUND 07 — AI / Agent / Skill Store / Shared Engines
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只证明模型会回答。

必须选择真实业务输入：

真实 Subject / BrandFocus
+
真实 Evidence
+
真实用户任务

验证：

Intent
→ Task
→ Permission
→ Tool / Skill
→ Evidence
→ Artifact
→ Result
→ Evaluation

AI 不得：

- 编数据
- 修改 Evidence
- 修改 Canonical Truth
- 自行授权
- 自行执行高风险 effect
- 将 unknown 写成事实

Skill Store 必须真实走：

Discover
→ Inspect
→ Trust
→ Enable
→ Execute
→ Evidence
→ History
→ Update
→ Disable

至少一个 Skill 必须真实完成业务任务。

ROUND 07 EXIT：

AI / Agent 是业务增强，不是 Demo Chat。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十二、ROUND 08 — Cross-Surface Experience Foundation
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

不能只把四个 Surface 画出来。

必须证明：

Public Website
Web Workspace
Desktop
Mobile

共享：

- 一个 Product Core
- 一个 Permission
- 一个 Evidence
- 一个 Context
- 一个 State Meaning

同时明确：

什么能力：

WEB AVAILABLE
DESKTOP ONLY
MOBILE COMPANION
PUBLIC ONLY

例如：

Browser / CDP
Cookie / Session
Local AI
File System

不得在 Web 中伪装存在。

必须生成：

SURFACE CAPABILITY MATRIX

ROUND 08 EXIT：

同一业务事实跨 Surface 一致，但交互不复制。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十三、ROUND 09 — Golden Pages
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI-01
CTH-01
CTH-02
BMP-01
SH-01
SYS-01

不能以：

页面漂亮
Flutter test pass
截图正确

作为完成。

每个页面必须回答：

用户为什么打开它？
用户看到什么真实内容？
内容来源是什么？
能点击到哪条 Evidence？
能执行什么？
执行后发生什么？
失败显示什么？
下一步去哪？

至少一个真实用户必须完成：

进入
→ 找内容
→ Trace Evidence
→ 执行一个操作
→ Return

ROUND 09 EXIT：

Golden Pages 真正“可工作”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十四、ROUND 10 — CTH Monitoring / Analysis
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CTH-03..07 必须使用真实新数据。

必须验证：

实时流
事件关系
情绪日历
负面反馈
趋势

所有趋势必须记录：

numerator
denominator
time window
Subject
source
freshness

必须证明：

无数据
≠
采集失败
≠
未采集
≠
0

至少一次真实新事件：

Source
→ Event
→ Evidence
→ Trend / Monitoring UI

ROUND 10 EXIT：

用户看到的是“现在真实发生的事情”。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十五、ROUND 11 — CTH Case / Risk / Decision / Report
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须真正闭合：

Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Report

不能只创建数据库记录。

至少选择一个真实 Case：

用户必须可以：

打开 Case
→ 看 Evidence
→ 做 Decision
→ 发起 Action
→ 等到 Outcome
→ 回来查看
→ 生成 Report

如果外部 Action 不能真实执行：
必须明确显示 approval / pending / blocked。

ROUND 11 EXIT：

至少一个 CTH business loop 真实闭合。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十六、ROUND 12 — BMP Market / Creator
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须选择一个真实 BrandFocus。

从真实来源完成：

Brand
→ Market Signals
→ Competitor
→ Creator
→ Content
→ Evidence

不得：

- 使用全局 aggregate 冒充品牌数据
- 用 Subject 数据改标签当 BMP
- 用测试 creator 冒充真实 creator
- 用不一致时间窗比较品牌

必须记录：

BrandFocus
Market
Competitor Set
Source
Time Window
Metric Definition
Evidence

ROUND 12 EXIT：

用户可以真正理解某品牌当前市场位置。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十七、ROUND 13 — BMP Content / Campaign / Podcast / Evaluation
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

必须证明：

Brief
→ Evidence
→ Content
→ Review
→ Approval
→ Campaign
→ Actual Result
→ Evaluation

不能只做“内容生成”。

Campaign 必须区分：

planned
budgeted
launched
observed
measured

Podcast 必须区分：

script
source
audio
version
publish
rights

Evaluation 必须基于实际结果，不是 AI 主观评分。

ROUND 13 EXIT：

至少一个真实内容/活动闭环有 Actual Result。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十八、ROUND 14 — Remaining ACC / AI / Shared / SYSTEM
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

80 个任务不能只批量套 UI。

每一个 Screen 都必须有：

USER JOB
REAL INPUT
OWNER
PERMISSION
EVIDENCE
ACTION
FAILURE
RETURN

如果 backend 尚不存在：

页面必须诚实显示 unavailable / blocked。

不得制作：

fake controls
fake charts
fake logs
fake AI thread
fake Evidence library
fake health

必须输出：

SCREEN DELIVERY MATRIX

44 Screens 每个分类：

USER_VERIFIED
LIVE_VERIFIED
TESTED
IMPLEMENTED
BLOCKED
DEFERRED

ROUND 14 EXIT：

不存在“看起来能用但其实不能用”的 Screen。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
十九、ROUND 15 — Internal Beta / Release / Operating
真实交付约束
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROUND 15 是最终“真假分界线”。

必须邀请真实用户或非开发参与者。

至少完成以下 Critical Journeys：

1. Public Website
→ Trial / Login
→ Web Workspace

2. Select Subject
→ Monitor
→ Evidence
→ Event
→ Case
→ Decision
→ Action
→ Outcome
→ Report

3. Select BrandFocus
→ Market
→ Creator / Content
→ Campaign
→ Result
→ Evaluation

4. AI Intent
→ Task
→ Evidence
→ Artifact
→ Action

5. Desktop
→ Local Runtime / Browser / Collector
→ Web Result

6. Mobile
→ Notification
→ Review
→ Approval
→ Return

必须使用：

REAL USER
REAL DATA
REAL CURRENT SHA
REAL PERMISSION
REAL SESSION
REAL FAILURE
REAL RECOVERY

不得使用：

demo-only fixture
manual DB injection
developer-only shortcut
pre-populated fake success

同时必须执行：

- clean clone
- install
- migration
- startup
- CI
- Tier C
- security
- backup
- rollback
- performance
- long-run
- device
- accessibility
- failure/recovery
- packaging

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十、最终必须输出 7 个最高状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

最后不得只写：

ROUND 15 PASS

必须输出：

Global Commercial Coverage =
Global Brand Coverage =
Guangzhou Taikoo Hui Reference Coverage =
LUMENIS_INTERNAL_FULL_UNIVERSE_READY =

ENGINEERING_READY =
REAL_DATA_READY =
USER_WORKFLOW_READY =
SECURITY_READY =
RELEASE_READY =
OPERATING =
COMMERCIAL_READY =

先按 `LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md` 判断同一内部全量版的三个支撑维度。只有 `Global Commercial Coverage`、`Global Brand Coverage` 与 `Guangzhou Taikoo Hui Reference Coverage` 全部为 `YES`，唯一顶层结论 `LUMENIS_INTERNAL_FULL_UNIVERSE_READY` 才能为 `YES`。三项不得产生独立产品、版本、仓库、入口、发布轨道或 Data/Evidence/Permission/API/Context；广州太古汇单点成功、页面非空、目录存在或几个平台有数据都不能替代全球覆盖证明。

随后只有最终七状态全部 YES：

才允许写：

LUMENIS CLOSED-LOOP DELIVERY = COMPLETE

如果任意一个 NO：

必须输出具体 blocker。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十一、最终真实数据标准
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

至少一条真实数据必须完整证明：

External Source
→ Raw Capture
→ Evidence
→ Canonical Data
→ Subject / BrandFocus
→ Function
→ Metric / Event
→ ViewModel
→ User Surface
→ User Action
→ Outcome
→ Evaluation
→ Learning

每一步必须能定位：

owner
ID
timestamp
permission
source
state

否则不得称为 Production Truth。

本节的真实数据链必须同时服从 `LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md`。每个相关 Round 持续建设并分别报告 `GLOBAL CTH maturity impact`、`GLOBAL BMP maturity impact` 与 `Guangzhou Taikoo Hui reference-loop impact`；ROUND 15 只在当前 SHA 复验，不接收前序轮次积压实现。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十二、最终商业交付标准
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

最终商业能力清单只能包含：

OPERATING 或 LIVE_VERIFIED 且已通过 USER_VERIFIED 的能力。

不能把：

PLANNED
IMPLEMENTED_LIVE_UNVERIFIED
NOT_CONFIGURED
BLOCKED
DEFERRED

写入销售可用功能列表。

每个数据源、平台、AI Provider、Skill、Screen、Workflow 都必须有真实状态。

继续执行当前 15 轮，不新增第 16 轮。

从当前正在执行的 Round 开始立即应用本协议。
已完成的前序 Round，在后续 Sol acceptance 时补做 REAL DELIVERY CARD；
无需推倒重做已经通过的正确源码工作。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二十三、全局商业交付补充红线
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

以下六项作为全 15 轮横向约束，不新增 Round。它们不耽误与其无冲突的当前产品开发；每轮在相关 canonical owner 范围内逐步建设、记录差距和证据。外部账号、商业授权、合规确认或上线前运营准备尚未完成时，必须记录为 `COMMERCIAL READINESS GAP / BLOCKED FOR COMMERCIAL_READY`，不得误写成当前工程能力失败。最终在 ROUND 15 正式上线前由 Product Owner 审核。

1. DATA GOVERNANCE / COMPLIANCE

每个外部 Source 必须记录合法来源、授权方式、允许用途、数据保留期限、删除/退出路径和合规边界。“技术可采”不得自动等于“商业可用”。

2. SECRET / CREDENTIAL GOVERNANCE

不得存在生产默认密钥、固定个人凭证、真实 Cookie/Token 入库或入 Git。必须具备注入、轮换、失效、恢复和审计路径。

3. CONTRACT / VERSION COMPATIBILITY

每个 Web/Desktop/Mobile consumer-facing API/ViewModel 只能有一个 canonical owner/schema/error/state contract。升级必须验证 backward compatibility 或明确 migration。

4. DATA RETENTION / BACKUP / DISASTER RECOVERY

必须验证 retention → backup → restore → rollback → deletion，且恢复后 Evidence / Canonical lineage 不断裂。

5. TENANT / WORKSPACE LIFECYCLE

商业化前必须验证 Customer/Workspace 创建 → Subject/BrandFocus 配置 → Member 加入 → Permission → 使用 → Member 移除 → Access Revoke → Customer Exit / Data Cleanup。

6. COMMERCIAL OPERATIONS

`COMMERCIAL_READY=YES` 前必须存在并验收 onboarding、support/escalation、upgrade/migration policy、service status、usage/quota/entitlement、release communication、rollback/support path。

上述任一项为 BLOCKED，最终不得输出 `COMMERCIAL_READY=YES`。任何一项未闭合，只能令 `COMMERCIAL_READY=NO`，不能由 `ENGINEERING_READY`、`RELEASE_READY`、CI 绿色或其他状态替代。不得把真实密钥、Cookie、Token 或个人凭证复制进协议、日志、源码、测试、Evidence 或提交历史。
