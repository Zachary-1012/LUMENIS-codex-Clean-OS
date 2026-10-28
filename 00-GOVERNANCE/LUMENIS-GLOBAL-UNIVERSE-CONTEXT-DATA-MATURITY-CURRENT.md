# OEVIRA Subject Scope / Focus Context / Data Quality — CURRENT

> Current subordinate contract, updated to direct PO correction on 2026-10-26.
> Product Architecture owns scope; the existing registry, Permission, Source/Evidence and database owners remain unchanged. The retained filename is a compatibility path, not a worldwide data programme.

## 1. Canonical model

当前主体范围是现有目录中有依据确认正在中国境内经营的商业主体和品牌主体，包含在境内实际经营的国际品牌；不以国籍或名称判断，不做全球主体扩库。设置 → 主体目录统一管理添加、移除和重新添加，新增也须符合境内经营范围；证据不足的登记显示待核，不进入已确认的活动目录。目录移除停止该主体的新任务使用及关联监测，历史资料、报告、行动和版本仍按原权限保留。

用户可直接开始问题或创作，不强迫先选主体。经营/品牌任务需要主体时，从当前任务复用，或识别后以可修正的明确名称显示；只有歧义才询问。未聚焦视图表示当前账号获准的境内经营目录，不表示全球主体。既有 `GLOBAL/ALL`、`GLOBAL_ALL` 等技术标识须按现有兼容入口解析，不作为跨范围权限或全球扩展指令；正式消费者在服务器端执行现行范围。

商业主体与品牌主体为两个目录分组。商业体/项目→场内门店/经营对象、品牌→境内网点，按已核关系展开；两种视角引用同一主体，禁止重复建库或凭名称推断隶属。城市、类型和经营状态用于筛选，不强迫用户逐级选择国家/地区/行业/品牌后才能提问。境内经营不是企业国籍或总部所在地；关闭/退出及未核状态须明确，不能自动当作当前经营。

## 2. Existing owners and compatibility boundary

原 subject_registry、context、Permission、Source/Evidence/Canonical、数据库及Surface消费者继续为唯一Owner。目录是身份与范围，资料是输入，结果是派生内容，选择不产生授权。广州太古汇等案例不是默认主体。用户移除主体时停止该主体后续任务引用与关联监测，已执行外部效果不撤销；重新添加沿原稳定身份、权限与历史恢复，不重复创建记录。删除资料/账号另走原明确操作，不能用目录移除级联抹掉作品。

## 3. Honest states and add/search semantics

主体目录提供搜索、添加、移除、重新添加和有据关系查看；默认仅现有且境内经营已核主体。新增信息先去重和核实，未知保留待核身份，不混入可确认经营名单，不自动采集。界面一次展示必要名称、类型、城市/经营范围及重名差异，已有字段不重复问。来源或经营状态更正传递到当前任务与监测，历史回执保留原时点事实。

`NOT_COLLECTED / NOT_CONFIGURED / BLOCKED / STALE / OFFLINE / ERROR / NULL` 与真实零分开。身份存在不证明数据齐全。添加/移除/恢复需要实际主体生命周期及读回证据，不能用清除筛选冒充移除。

## 4. DATA_MATURE minimum contract

数据质量面向当前任务：主体/关系无歧义；来源、许可、用途及原生时间可追溯；Source→Evidence→Canonical身份一致；指标口径/分母/窗口正确；来源缺失、失败、未知与零分开；材料能支持实际判断并说明不能得出的结论。记录数或国家/平台数量不作为质量替代。

采集是取得当前任务所需事实的数据能力。优先复用合法且仍适用的已有资料，再按问题、主体、时间和缺口选择相关来源、搜索/详情/评论/分页/媒体或当前浏览器上下文。取得足以支持当前结论的材料并覆盖关键反证后结束本轮，不用主体数量、平台全覆盖或无限翻页代替准确性。舆情监控、活动及营销监控是固定用户功能；用户设定对象、目的、时间和频率后，沿同一采集器持续检查新增变化，可暂停、调整或结束。普通提问、刷新和监测都有明确边界，不因打开产品、选择主体或登记目录而自动扩库。

默认按实际相关时间由近到远呈现，提供近一周、近一个月、近半年、近一年及自定义范围；明确用户日期优先。事件发生时间、原文发布时间、采集时间分列，不互相冒充；日期未知单列，历史类比与当前事件时间线分区。

## 5. SUBJECT SCOPE / TASK DATA QUALITY IMPACT

| 核验对象 | 现行要求 |
|---|---|
| 主体范围 | 现有境内经营主体/品牌，来源可核；添加、移除和重加不重复身份或丢历史 |
| 针对性数据 | 问题、对象、时间、来源和结果一致；不用无限采集或全球目录完成作为产品前提 |
| 监控 | 用户明确范围与频率，真实新变化、失败/恢复、暂停/结束；不自动扩展到其他对象 |
| 业务使用 | 实际分析、判断、方案及成果能定位来源、修改、重开和恢复 |

全世界主体覆盖、国家配额、全球基线构建与全球全量成熟度不再属于本期目标或发布门槛。国外同类案例可作为当前任务的相关研究资料，不因此加入活动主体目录。已有境外历史资料和作品保留权限与原始身份，不迁移/删除生产数据以制造范围一致。

## 6. Per-round responsibility

C1负责原主体/来源/采集链；C3负责CTH/BMP专业语义和消费者；C5负责资料、引用与成果；C2负责适用AI增强；F消费同一范围与结果合同；C6协调运行、数据库和集成。原Owner不增加，本文件不派工。改变范围时同步搜索、选择、导入、采集、监测、分析、导出、恢复与撤权消费者；本次规划校准不宣称代码或运行已更新。

## 7. Per-round acceptance block

已有交付卡记录实际目录范围、任务问题/时间、实际源、来源不足及影响、用户可用结果和恢复。沿原发布门禁，不另建全球验收体系。默认无聚焦与聚焦同一主体/多主体比较都按服务器权限和境内范围校验，不能从UI筛选推导权限。

## 8. RANDOM ENTITY DATA ACCEPTANCE

抽样只针对已获准的境内经营目录及实际任务，包含商业体/门店/品牌和同名差异；样本不足如实记录。不能假定任一全球对象都有资料，也不能把没有数据填成零。验证目标是处理正确与真实可用，不是为凑样本扩大注册或采集。

## 9. Baseline-source research

原研究和原始材料按既有Evidence/采用记录用于开发校准。已有主体记录继续沿现有Owner核实境内经营与身份；无业务记录的新工作区不要求预置主体目录，也不把研究候选自动导入业务库。新主体从当前用户输入或已获准任务资料进入同一注册与核验路径；本文件不授权外部采集、训练或付费。历史全球覆盖研究不再作为当前执行指令。

## 10. Task-semantic vocabulary and targeted acquisition

Six primary platforms are Instagram, Facebook, WeChat Official Accounts,
RedNote (HK/intl account), Douyin and X. Existing Collector owners implement all six
eligible routes; user refresh or an explicitly requested current-context task initiates acquisition.
Names/registrations/imports are not proof of platform collection.
Keep other existing platforms. Every platform has its own native fields, access
state, permitted identity, exact entity/domain/market/purpose and Evidence path.
Missing access/binding blocks that portion honestly while available platforms
continue, without substituting a differently scoped account or fake zero.

Through existing SYSTEM Collector/registry/Source/Evidence/Canonical owners,
maintain versioned topic terms per platform and canonical brand/commercial
entity. Record observed tag/phrase, source URL/ID/Evidence, original language,
aliases, actual city/store/venue, source/observation times, applicable scope,
ad/organic and official/consumer distinctions, permitted use and review state.
One spelling never resolves same-named venues or cross-city stores by itself.
No second topic database, scheduler, registry or collector is authorized.

Compile purpose queries from the actual user task, accepted source vocabulary,
canonical aliases, topic dimensions, language, time and scope constraints, with
explainable inclusion/exclusion and disambiguation. A composed query is derived
task text, not an observed platform hashtag/hotspot/ranking. Do not invent terms
as platform facts or guess an entity, popularity, advertisement status or date.
Relevance and exact-scope checks must reach real capture/intake and the consumer
job, not stop at a query-plan candidate. Unknown/conflicting bindings stay honest
while the owner resolves them; useful authorized results remain the real exit.

Acquisition starts from explicit user refresh or a task requesting current context. A background schedule requires its own current explicit opt-in; historical internal AUTO receipts do not authorize collection on startup, entry, selection or registration.
The 2026-10-08 correction removes the former universal publication-start date.
Acquire by authorized subject/topic and task semantics with bounded budgets,
then classify/order/filter by genuine source publication and event time.
An explicit user/task time range still constrains its query; no global earliest
date is inferred when none was requested, and this is not unlimited historical crawling.
Retain source timezone/date precision and normalize by the current time owner;
capture/import/refresh time cannot replace source publication/event time.
Unknown publication/timezone and unsupported history windows remain explicit
coverage gaps, never in-window proof, all-zero buckets or silent omissions.
Keep all older evidence intact and eligible for its actual authorized task; historical
material is not excluded merely because it predates a global calendar cutoff.

Persistent product Scheduler/Collector own backfill cursors, per-platform window/
progress, incremental watermark, last attempt/success, next due cycle, bounded
Retry-After/backoff, idempotence and restart/overdue recovery. For a currently opted-in schedule, rotate eligible
platforms if needed and preserve its bounded continuation. Collection and recovery
execute in the product runtime, independently of Codex/CUA. Training, development
and rule publication neither start nor cancel a schedule. Source challenge/outage/revocation safely isolates only the
affected path; continue eligible others, retain pending gaps and resume it after
actual recovery. Never defeat access controls to satisfy 'continuous'.

MANUAL is the current default. Each optional AUTO schedule records the user's
explicit opt-in, exact scope, source identity and recovery contract; this document
grants no background execution consent. Protect the personal Mainland XHS profile;
resolve other platform sessions through registered secret-safe owners. Prefer
official permitted APIs/refresh/session continuity and researched legitimate
recovery to repeated human troubleshooting. Historical R-0003/R-0004 and their
MediaCrawler/xiaohongshu-mcp/Spider_XHS references are research inputs only;
recheck versions/licenses/current rules and do not activate legacy accounts,
rotating identities, CAPTCHA bypass or presumed immunity to platform bans.
After a user reports verification complete, the session owner reads back actual
authorized state and resumes only the pending scoped work.

Acceptance requires real topic/task coverage and explicit requested-window receipts/gaps,
topic/task→query→Capture→Evidence→Canonical→useful normal business result,
explicit refresh and current-context task execution, one-platform failure isolation and
restart recovery; opted-in schedules additionally require real repeated due cycles while another job runs. Mocks, replay clocks, a name search, raw posts, imported rows
or a live schedule registration alone cannot prove these. C1 retains continual
China/global brand/commercial-entity additions and relation review alongside
real task validation, without waiting for complete global directory coverage.


### User-reviewed foundation vocabulary seed

The user-reviewed xujing_topic_seed_100_4confirmed_20261004 XLSX/CSV/JSON may be
used as versioned test entity/topic inputs through existing Source/registry/
Evidence/Canonical ingestion, followed by real runtime queries. It is an optional,
explicitly selected input, not business data that must be bundled, imported into a
new workspace, or present for normal startup. A fresh workspace may have an empty
business registry; real task input enters through the existing registry and
Permission owners, while an unscoped collection request remains denied. JSON has100 topic
records and41 source records; four named entities have25 terms each. Its own
metadata remains4/6 entities confirmed,2 unnamed and100 heat UNKNOWN, with no
verified hotlist. User review approves this input, not fabricated platform
hotness, rankings, complete six-platform coverage or automatic MODEL_TRAIN use.
Preserve term IDs, entity/type, topic/observed_literal/term_type/association,
platform, source IDs/URLs/titles, publication literal/capture/review times,
evidence level, heat/null/rank, recommended use, notes and evidence locators.

Original files and original terms are immutable and never deleted. Add versioned
terms and associations based on actual time, commercial entity, brand, activity
and event changes, with reason/provenance/effective interval/parent version;
retain old terms for search/history/rollback. Active query views select applicable
versions and mark retired/expired/conflicting terms without destroying them.
C1/W6 store/resolve/import this reviewed source through current owners when an
authorized task explicitly uses it; any packaged/runtime path must resolve the
admitted version rather than a developer's attachment path or a fixture. This
does not make seed import a startup step or a prerequisite for other work.
Preserve current exact identity/source-use checks,
normal explicit authorization and honest unknowns without asking for another
manual review of the same100 terms. This seed does not limit ongoing entity/
source/topic growth or replace whole-universe data coverage.

### Topic growth and two heat meanings — latest C1 human correction, 2026-10-04

The Product Owner explicitly prioritizes sourced topic growth over current heat/
rank positions. Expand existing terms plus new time/entity/brand/activity/event
terms across additional brands, commercial entities and platforms. The four
entities in the reviewed seed are optional source-backed inputs, not a required
business-directory preload; the six primary platforms remain a capability
coverage baseline, not a startup data bundle. Use C1's newly sourced terms
through this same versioned owner chain. Hotlist verification is not a
prerequisite for vocabulary growth or actual collection.

Keep LUMENIS corpus-derived heat separate from platform-provided heat/rank.
The former needs a declared corpus/window/scope/sample/metric/version and actual
data; the latter needs the actual platform-native field/source/window. They are
not interchangeable, and unknown remains unknown. Greater data volume alone
does not prove representative global demand. Retain original terms/versions,
sources/times and controlled updates; do not delete or invent heat values.


### Retained TopicCampaign safety parameters

The approved original 100-term/41-source seed is packaged unchanged at
`config/collection-topic-seed-20261004.json` (SHA256
`cfe3b6cb424ee0efe3d917479ba95db66f4ca9b8df32fa891fcf16fd6c576028`).
`acquisition_plan.load_approved_topic_seed` reads that product file, not a
developer attachment or work directory. Seed-bearing business requests must
match its topic ID, source ID/URL, original literal, term, platform and registered
entity. The explicit user task selects purpose and facets; packaging grants no
trend status, entity promotion, source-use permission or model training.
Retain this original when adding subsequent source-backed topic versions.

These seed checks apply to requests explicitly referencing that seed. They do
not require every subject-scoped collection batch to await all 100 terms or
post-intake keyword analysis; the current C1 priority below controls that order.

The existing platform-collection search API accepts task-selected
`business_requests`, bounded `max_queries` and a checked plan continuation.
It resolves the actual actor/scope; a client cannot upload a completed-checkpoint
claim to skip collection. Scheduled internal purpose requests use the existing
signed baseline loader, fresh Permission check of the whole query and request
bound, then the same Collector transaction. This is not a parallel scheduler or
an automatic grant to future-user AUTO. Live platform/session/continuity evidence
remains required separately from source integration.

The 2026-09-03 TopicCampaign exception remains source-specific history and
configuration: hours [9, 11, 13, 15, 17, 19], staggered execution, maximum eight
runs including manual on its own counter. Retiring TWIN_EXECUTION_GATE does not
change those code values or authorize unrestricted collection. These values do
not impose a universal twice-daily limit on the explicitly opted-in, task-scoped multi-platform
program. Current schedules require source identity, approved policy, bounded
retry/cooldown, observable outcomes and recovery through the existing Scheduler.
No new module starts collection implicitly; actual risk/authorization failures
stop only the affected path and preserve evidence for recovery.

### 2026-10-08 维度完整、真实缺失与采集能力闭环

Product Owner明确取消“所有数据必须采全”的要求。产品必须保留业务需要且定义准确的维度，但不承诺平台未提供、无权访问或客观不存在的数据。完整基线名录/主体关系与每个主体每个字段100%有值是不同要求；本节不取消已批准主体/品牌登记、真实采集能力、六平台接入责任、持续运行和有效业务成果。

维度沿现有Metric/Truth Table/ViewModel定义其名称、含义、单位、范围、时期、来源和可比条件；缺值仍展示该维度及“—”，可查看具体原因和最后实际核验时间。展示层横杠不进入Canonical作数值，API/存储保留null及当前状态/原因。真实0仍显示0，未采集、未提供、权限受限、失败、过期、部分、未知和不适用不能混成同一事实。不把缺值维度隐藏，不用抓取时间冒充发布时间，不以旧值冒充新值。

只有对应能力在真实授权来源上走通 query→fetch/parse→Source/Evidence/Canonical→用户可见结果→刷新/取消/恢复并有同版本回执，才能把仍缺失的字段归因于已核实的来源限制。对确实不可接入的平台保留BLOCKED/原因，不把其他平台成功当它的闭环。程序解析缺陷、接口未接、没有执行、权限过期或未知原因都仍是原Owner待办；横杠不能替代修复和能力验收。来源空结果可作为一次真实运行结果，不能单独证明所有能力已闭环。

成熟度分别记录能力状态、维度定义/展示覆盖、实际数据覆盖/时效和来源限制；不以100%非空为统一门槛，也不把允许缺失改成100%覆盖。保留真实分子/分母、受限/缺失/失败数和影响；业务问题所必需的证据不足时，相关结论仍未知或不可用，不能因为UI完整就通过业务结果。Global/Reference三项原验收维度采用已披露范围及可解释限制，不声称全球数据齐全。

时间排序保留原始出版、事件、采集/刷新三类时间、时区与精度；按任务选择对应时间轴，同源同精度可比较。未知时间单列“日期未知”，不得补造；只有日期精度不伪造秒级先后。明确用户时间筛选时，无法确认落入范围的项单独提示，不算已覆盖。无全局硬起点不等于无范围、无节流或无限回溯；Scheduler仅在明确启用的监控范围内沿现有预算、游标、水位与授权运行。

**源码责任与执行依据：** C1 保留采集及可选任务时间范围、Scope/授权、capture 上界与精度的源码责任；Core/runtime、Scheduler、Permission 依现有 Owner 和共享写入合同衔接。实际执行者和顺序由最新直接 PO 指令决定，本文不派工、暂停或恢复窗口。`2d0f8d61` 对 `acquisition_plan.py`、`adapters/scheduling/prelaunch_baseline.py` 硬编码起点的观察仅为历史定位，当前缺口以实际源码及执行回执核定。保留旧 plan/receipt、fingerprint 与历史失败；按根 AGENTS §14 运行适用的隔离回归，不删除断言或掩盖失败求绿。另以实际产品操作核验明确范围、未指定范围、未知日期、旧回执恢复、真实持久化与持续刷新；规则发布不等于运行通过。

### 当前采集顺序：问题优先、按需补足与明确监控

采集是取得当前任务所需事实的数据能力。优先复用合法且仍适用的已有资料，再按问题、主体、时间和缺口选择相关来源、搜索/详情/评论/分页/媒体或当前浏览器上下文。取得足以支持当前结论的材料并覆盖关键反证后结束本轮，不用主体数量、平台全覆盖或无限翻页代替准确性。舆情监控、活动及营销监控是固定用户功能；用户设定对象、目的、时间和频率后，沿同一采集器持续检查新增变化，可暂停、调整或结束。普通提问、刷新和监测都有明确边界，不因打开产品、选择主体或登记目录而自动扩库。

1. 从用户问题、当前主体、已知时间和已有材料识别精确缺口，选择相关平台能力，不运行“主体×别名×话题×平台”的无边界扩面。
2. 每批获准原文立即进入原Source/Evidence/Canonical链并供当前工作使用；检索摘要不冒全文，转载不重复算独立证据，平台失败只影响实际缺口。
3. 研究与分析使用实际已取材料核实问题和反证；根据必要缺口补查，达到任务范围/预算/足够证据条件后停止，未知仍明确，不以填满字段为目标。
4. 热路径只处理必要封面及原媒体定位；任务需要理解图片/视频时，由原媒体Owner处理对应内容，不把只取封面称为完整理解。
5. 舆情、活动、营销监控用同一能力和明确订阅范围运行；保存游标、变化与失败恢复，用户可暂停和结束。研发Agent代搜不算产品自主执行。

分析用途仍绑定实际actor、当前scope和SourceUse；采集回执不自动授予训练、发布、商业转载或新Provider权限。数学计算、关键词、AI推断和来源事实分开。当前仅更新规划，不启动采集或监控。

### 当前全产品数据到业务升级 — 2026-10-09 直接 PO 执行令

《C1 数据能力重构与全产品业务闭环升级执行令》的能力范围保留于既有 Collector/Shared/CTH/BMP/Research/Reporting/Evaluation/SYSTEM 及数据变化影响的 Web 调用方，不限于采集文档。C1–C6/F/M继续标记原源码责任与跨域依赖；实际执行者、顺序、窗口状态及模型选择只由最新直接PO指令决定。历史C1独立执行、M非C1候选范围及GPT-6.1 Sol/ultra选择不建立当前派工或持久配置；缺少当前实际读回时记录NOT_VERIFIED。

**五项职责分离。** 合法取得原始观察、来源有效性、访问/用途权限、主体身份候选及确认、业务分析是不同阶段。已在实际采集授权范围内取得且合法保留的观察，不得因业务关键词不匹配、相关性未知或未出现主体完整名称而丢失；它仍须经过来源完整性、权限、身份候选和处理去向检查。主体未绑定时沿现有 Source/隔离/待核验路径持久保留可定位、可恢复原件及状态，不写入该主体的正式事实。无效页面、来源身份冲突、无权访问/保留或超范围材料继续拒绝/隔离；名称命中不创造身份或授权。Canonical 正式准入与待核验原始观察保留分开，不建立另一个事实库。

| 执行令章节 | 现有实现/Owner 的直接落实要求 |
|---|---|
| 0 当前准入与保护 | 当前时间/主机/项目/remote、local/cached/fresh/live main及 divergence/dirty，原 C1 在途任务、实际写入预约、进程/Checkpoint 分别取证；保护可恢复原件，不 reset/clean/未经核实 stash、覆盖或强杀未知进程，不重复启动任务。 |
| 1.1–1.2 原始观察与接收 | 用真实 Subject/BrandFocus/别名/平台/市场/地域/目标与现有许可采集；每条记录原生ID/URL/作者/标题正文/标签/实际指标/原发布时间和capture、原件指纹、候选关联/核验、use、Source/Evidence/Canonical refs/版本、去重/异常/恢复/下游去向。缺失保持NULL/UNKNOWN，字段不存在不造值。 |
| 1.3 媒体预算 | 初次每帖至多一张真实代表封面，无则给原因；不默认全图下载/OCR/视频下载/逐帧。保留获准可得其他原生媒体URL、类型、数量及定位。后续实际工作流按媒体用途处理，不删除多模态能力。 |
| 2.1 查询计划 | C1追实际 `acquisition_plan.py` 的 Registry、DEFAULT_QUERY_LIMIT/MAX_QUERY_LIMIT、next_cursor/input_fingerprint、`assess_query_relevance` 和 `build_observed_topic_catalog`；保留许可、边界与恢复。相关性、热点、词条/文本关联是可复核派生判断，不是合法原始观察持久化的前置门槛。 |
| 2.2 真实写入链 | C1追 `secondary_collection.py` 的 `collect_search`、`collect_business_queries`、`_business_source_reviews`、`_prelaunch_entity_mentions`、review_candidates/review_pending 至原 Source/Evidence/Canonical；每条来源可恢复、去向可查，不因业务筛选先缩小而丢原文。`_persist_post_intake_keyword_candidates` 若卡事务则移入已有后处理；分析失败不抹去已合法提交来源，可单独续跑。 |
| 2.3 有效吞吐 | 先测真实返回量、原生分页/cursor、计划连续执行、重复请求、同步分析/封面、DB写入/事务/去重、平台锁、风控/频率/session/冷却与跨平台隔离；通过分页、增量、批处理、持久checkpoint提速。不得粗删 MAX_RESULTS=20 等边界或无界并发。计划恢复回执、原生cursor和权限各自独立。 |
| 3 六平台 | RedNote（香港/国际账号）、抖音、公众号、Facebook、Instagram、X分别实证获准身份/范围、单帖详情/原生字段时间指标、分页回补、封面/元数据、Source/Evidence/Canonical、定时/取消/重启/续跑/重复处理。各平台分别保留真实任务、原帖及事务回执/计数/分母/时窗；BLOCKED路径不带停其他路径，不能被其他平台成功抵消。历史记录、打开页面、HTTP200不证实时可用。 |
| 4 全产品消费 | 按下表核对真实受影响 Shared、CTH、BMP、Research/Reporting/Evaluation、SYSTEM 调用方；已有数据与确定性合法业务不因 AI 不可用停下。跨 Owner 由 M 原预约有界交接，C1必要Core/runtime/Scheduler/Permission修复仍自己完成，不额外唤醒暂停窗口。 |
| 5 实际 Web | Web/Windows按当前设备范围实现并分别验收，官网只展示，macOS/iOS客户端与设备验收后置；当前用户工作同时完成视觉升级与数据链，主体选择/创建在权限内，真实范围/平台/时间/进度与状态、来源/业务关系/不确定性可查看，进入业务成果、保存/修订/重开，原帖在受控浏览器打开并返回原任务。不使用假数据墙、模拟后端或重复仪表盘；44屏不限制完整产品范围。 |
| 6 旧路径收敛 | 追真实caller后替换已证失效的耦合/重复入口/旧启动路径、错误GLOBAL默认、兼容映射、吞错假成功、未写Source/Evidence或提前checkpoint、重复拉取/无界重试/session反复启动；保留唯一能力、兼容迁移、原数据/研究/测试/失败/Git史，不因目录旧而删除。 |
| 7 真正闭环 | 至少一个实际获准平台或公开网页来源：选择主体→真实采集→原始来源保留→Evidence/Canonical核验→工作流分析/分类→CTH/BMP使用→真实成果→保存→关闭→重开→修订→来源追溯→中断恢复；来源类别基础权重相同，采集/入库/恢复已实证后优先接通已有获准数据的下游工具流，不等待全部平台完善。另记录六平台逐项实证/限制/硬阻塞，不把网页成果冒充其他平台已验收。实际重复不多计、身份不误绑、撤权不能继续使用。 |
| 8 同口径测量 | 真实合规观察/成功原始持久化数量比例、主体平台覆盖缺失、重复和无用请求、入库及分析可用延迟、来源完整/待核验/错误率、重启恢复和成果保存重开；保留真实时间/账号许可/平台任务口径。无有效旧基线写 BASELINE NOT VERIFIED，不造提升百分比。 |
| 9 精确集成 | C1完成本职改造/真实运行证据后M按原W6预约审查准确必要paths/config/deps/schema/启动入口，只暂存已验收所属文件，同一main发布并核本机/origin/live main及剩余dirty。源码同步不证明运行加载，无部署授权不部署。 |
| 10 最终成果 | 既有一份交付记录内提交A源码与旧路径替代、B脱敏原帖/Source/Evidence/Canonical/待核验/分析、C完整真实操作、D性能同口径或不可比说明、E本机GitHub/Runtime/DB/用户结果独立状态、F完整开放缺口及影响/恢复条件；OBSERVED/INFERRED/NOT VERIFIED，符合实际验收才ACCEPTED。不逐函数停工/审批或以文档代替成果。 |

| 下游现有上下文 | 必须保持的正常消费和边界 |
|---|---|
| Shared / Canonical / Database | 同一来源ID、实际主体/候选状态、用途权限、原时间、版本、处理状态和引用，未绑定与正式事实分开；来源版本、互动快照和派生可追溯，重复不增加事实或叠加指标。 |
| CTH | 有效主体/场所/门店数据进入既有事件、时地、消费者反馈、风险、Case/Insight/Decision/Reporting；普通名称命中不证明场内关系，消费者意见不冒充经营事实。 |
| BMP / SH-01 Discover | 品牌/市场/竞品/创作者/传播/内容/Campaign进入原研究与发现；话题/关联/趋势须有证据与口径，平台原生热度、序境样本表现和模型推断分开。 |
| Research / Reporting / Evaluation | 来源可检索、定位、引用、比较、修订；继续同一SourceBrief/SavedWork/Content Project/报告/Evaluation。可用的部分结果须说明样本/筛选/截断/方法与未知，不虚构趋势、营销转化或因果。源变更/撤销沿原引用触达受影响结果，旧版保留。 |
| SYSTEM / Web caller | 原Scheduler/ONE Runtime/Browser/Permission/Gateway/Agent维持调度与身份；界面只消费真实合同，呈现取得/待核验/正式接收/待分析/完成/失败恢复，不把状态相互覆盖。未获准的后续用途保持阻塞；已合法独立路径继续。 |

本条保留所有 R01–R15/J1–J8/U01–U25，既有编译/静态安全数据、真实用户E2E、保存重开恢复及三层Gate；按根AGENTS第14节执行受影响的隔离单元/集成回归，保留其真实类型，不替代真实用户E2E，不改写历史失败。零新费用/账号/GPU/Provider/环境/部署，受保护XHS身份及现行来源权益不变。旧前置“业务相关性/完整名称必须已证明”规则只控制业务派生或正式主体事实接收，不再让合法原始观察在取得阶段消失；来源有效性、权限和身份冲突保护不被削弱。

### 图片/视频理解保留与异步提速 — 2026-10-09 C1 需求澄清

C1 当前原窗口记录的直接 PO 澄清要求知道图片和视频实际讲什么，并能供产品其他流程使用，同时降低耗时。它补充上述单封面采集预算，不新增产品、模型、来源或权限。既有 J1/J7 的完整媒体理解要求继续有效，不能将封面、标题、原文摘要或分析状态登记冒充理解结果。

1. **先入库，再处理。** 明确用户刷新或当前上下文任务通过 C1 既有 Owner 执行获准只读采集和 Source/Evidence/Canonical 事务；后台日程需当前显式 opt-in。保留实际原媒体 URL/native ID、来源版本/hash、图序/时长及可取得状态；没有原文件字节时不能虚构文件 hash。由既有 SYSTEM TaskQueue/Worker、AI Gateway 与 Shared Artifact/Reporting 承接媒体用途，不另建队列、数据库或分析 Owner。只有真实 handler 注册、用途准入且持久入队后才能报 QUEUED；仅新增元数据仍是 NOT_RUN。
2. **图片分析不是只有 OCR。** 对实际获准图片分别记录可读文字及位置、可见场景/对象、商品/活动/品牌线索和不确定性。OCR 文本、视觉观察、模型解释与来源主张保持区分；封面第一遍分析不代表完整图集已读。当前任务确需其他图时按真实原件定位补取与处理，不能用单封面预算缩减已批准任务。
3. **视频结合声音与时间画面。** 在既有媒体工具/许可和资源边界内，音轨实际转写一次，保留原时段、说话/语言不确定性和字幕来源；超过现有适配长度时由原 Owner 有界分段并正确重组，不静默截断。场景变化与时间覆盖的关键画面只作为有覆盖记录的分析输入；对重要/歧义区间补读，未取到或未看区间明确列出。不能以抽样帧宣称全片逐帧理解，也不能以无声音的画面推造话语。
4. **复用结果仍要复核用途。** 按既有来源字节/版本、处理配方/模型版本、实际 scope/purpose 保留可复用派生结果，读取时重查当前 actor、来源权益/可用性与撤销状态。每项媒体 READ/ANALYZE/派生保存分别通过现有用途与写入合同；DATA_IMPORT 或内部关键词许可不自动授权媒体分析。原 UNREVIEWED/allowed_uses 不改，不隐含商业引文、导出、训练、发布或新 Provider 准入。
5. **结果真实接到下游。** 通过现有 SourceBrief/Research/Artifact 引用输出原帖、图片位置或视频时间码、派生版本/hash、实际方法/模型、覆盖和置信限制，供已准入的 CTH/BMP/创作任务消费。允许的确定性处理与 Owned 推理分别记录；执行器未绑定为 UNAVAILABLE/NOT_RUN，不伪造标签或切退役 Provider。失败、断链、取消、重开和源变更沿原合同恢复。媒体处理使用有界并发、预算、背压和可恢复任务，不能挤占采集或触发平台越权访问。

**历史观察与当前验收责任。** 固定源码 `560c4f3f` 当时观察到：`media_brief.py` 调用单一 Gateway 多模态入口，视觉执行器未建立真实绑定；`owned_speech.transcribe_audio` 无生产外部调用，采集 Worker 无媒体后处理消费路径。这是该版本的历史记录，不能直接断定当前 main 仍有相同缺口。执行者按最新直接 PO 指令，通过现有采集、媒体、AI、Runtime Owner 核实当前调用链并补齐实际缺口；本文不规定窗口启停或旧分工。接口存在、工具安装或规则发布不等于媒体语义运行通过。真实图片/视频输入、时间/图定位、用途核验、保存/重开/恢复、下游可用性及吞吐/语义损失仍须对应版本的实际产品证据。

### 已核读资料进入 C1 当前闭环 — 2026-10-08

下列要求适配已读本地内容/平台研究原件及现有 RC-03/04/08/13 路由，增强同一 J1/U01–U05，不新增采集器、资料库、任务卡或统一数据模型。当前直接 PO 指派的执行者在既有 C1 Owner 内落实，不从历史窗口记录推断派工；独立可用工作不等待全球材料全齐或 GPU。

1. **保留原件与实际覆盖。** 经现有 Source/Evidence/Canonical 保存原始身份、URL、版本/hash、发布/事件/capture 时间及现有精确 locator。全文、摘要、截断正文、封面、视频区间、转录和音频实际读取分别记录；元数据/标题/封面不能写成原文或全片已读。分页失败、缺图、媒体不可得等保留具体原因和可恢复位置，不能用成功的 HTTP 或总条数冲抵。
2. **去重不丢来源。** 复用当前去重/版本接口；同文转载仍保留各来源身份、时间、链接和引用关系。前缀相同或长度接近只可作相似候选，不能静默删除独有材料或认定版本等价。原件读取只证明内容取得，不自动验证其主张、代表性、商业复用或训练资格。
3. **采集事实可供研究比较。** 原文明确提供的地区/门店、适用时期、主体关系、内容角色、广告/赞助披露及指标定义，经现有 provenance/原文定位传递；未披露保持未知。KOS/KOL/KOC/UGC、付费关系或受众身份不能仅凭粉丝量/互动量推定。样本/总体、分母、对照及结论由 C3/C5 在相应研究任务中解释，C1 不凭抓到的热帖代替完整市场或因果判断。
4. **保持闭环接线。** 给既有下游真实 source/evidence/canonical refs、完整或部分覆盖状态、版本和可用动作；真实任务检索/打开原文/刷新/重开时能够回到同一来源。原文部分缺失与产品解析缺陷分开处理；不得因界面可显示“—”而跳过可修复缺陷。源变化沿现有引用传递，历史版本保留。

以上是当前执行与质量要求，不宣称所有字段或消费者已经实现。C1 将实际缺口与采用结果更新到自己已有任务/回执，M 只审查完整成果和跨边界冲突；不增加逐函数报告或重复 ACK。身份、访问政策、来源用途、速率和生产数据边界保持。
