# 序境 / LUMENIS｜开工前蓝图与采集源码审阅稿

> 状态：供 Product Owner 审核的单次证据报告；不是新的规则、产品架构、任务卡或执行队列。唯一执行路由仍为 `AGENTS.md`，唯一产品蓝图仍为 `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`。
> 报告时间：2026-10-06 00:05 +08。源码依据SHA：`52cd770cde458f73f99e4073014c90a9d850c3f4`；采集源码复核发生于2026-10-05 23:36 +08。
> 本报告把用户已批准的产品终态、当前责任、源码审计及尚未证明之处放在一个可审阅入口中。产品代码执行须依用户的“先审核蓝图、后正式开工”要求另行开始。

## 1. 范围、基线与边界

本次核对范围是本机 `D:\LUMENIS_REBUILD\序\序境` 和私库 `Zachary-1012/LUMENIS-codex-Clean-OS` 的 `main`，重点为唯一规则、C1/C6 采集调用链、已批准产品蓝图、材料责任和本地保护边界；不展开无关全产品源码审计。

2026-10-05 23:11:36 +08 基线初查时，本地 `main`、缓存 `origin/main` 和独立 `git ls-remote` 返回的 GitHub `refs/heads/main` 一致为 `52cd770cde458f73f99e4073014c90a9d850c3f4`，分歧 `0/0`。初查工作树已有16个tracked修改及三个受保护的untracked根（C1证据、私有训练配置、`work/`）；这些既有工作均被保留。准备收敛中形成18个tracked规则/工具差异；本报告是同批新增证据文件。2026-10-06 00:08 +08 发布前快照另出现一项未授权变更 `lumenis/system/collector/data/schedule_state.json`，初查时不存在；M未读取内容、未改动、未暂存，作为外部/运行态脏文件保护。此18个治理差异仍是LOCAL_ONLY，不能倒称线上已更新。发布与远端字节核对结果以本报告交付时的 `CURRENT` 和实际 main SHA 为准；C1证据、私有配置、`work/` 与该运行态文件不进入本批提交。

本轮只读了相关源码和治理/任务合同，未改产品运行源码、数据库、迁移、Runtime、采集任务、模型/GPU、部署或前端代码；没有读取 F 的独立材料或源文件，也没有发消息、启动或恢复其他窗口。未连接平台、打开生产数据库或重查运行进程。

### 权威文件及上下文

按仓库技能要求读取了 `.agents/skills/` 下的 `lumenis-current-truth`、`lumenis-task-router`、`lumenis-progressive-context` 与 `lumenis-github-mainline`，另读 Codex `codex-quality-guard`。本次依据的现行合同为：

- `AGENTS.md`：唯一执行路由、M-only 本轮范围、六个 C 完整成果、发布门槛。
- `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`：唯一产品蓝图，2026-10-04 已批准。
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §38：四端、原创手绘二维色彩风格、任务型交互、页面滚动与横向媒体时间轴。
- `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`：R/J/U 覆盖、唯一 Owner、源码调用者及 C1/C6 完整任务。
- `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md`：真实用户任务、结果、恢复、上线与商业准备边界。
- `00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md`：GLOBAL/ALL、六平台、词条、时间与持续采集合同。
- `00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`：唯一 Collector、来源准入、原生字段、权限与续采合同。
- `MATERIAL-OWNER-CONTRACT.md` 与当前 `MATERIAL-OWNER-MANIFEST.json`：材料主责与真实未读状态；Manifest 的 191 条是直接引用快照，不是全部历史资料。

## 2. 闭环后序境必须怎样工作

这部分是对已批准 Product Architecture 的执行摘要，不取代它。

用户给出商业/品牌目标、主体或市场、时间、预算、约束和已有资料后，序境沿同一上下文持续工作：

```text
真实 Brief / Subject 或 BrandFocus / 时间与预算 / 用户资料
→ 经授权的公开来源、产品导入或平台采集
→ Source → Evidence → Canonical Data / Content
→ CTH 运营或 BMP 品牌/市场研究与判断
→ 自有 AI 在 Gateway 内产出有来源、范围、时间、理由和不确定性的分析建议
→ 提案文稿、可编辑视频工程、可听播客工程及其正式 Artifact
→ 获准 Action → 真实 Outcome → Evaluation
→ 来源、预算或需求变化时定位受影响部分；用户明确采用新版本后只修相关内容
→ 保存旧版、父子关系、修改原因、未变内容和回滚点；关闭、换端、重开或中断后可恢复
```

研究进入制作时继承原 Brief、scope、Evidence、预算、选择理由和版本，不要求用户重复解释或重选同一组资料。来源撤回、授权变化和不确定外部效果不由 AI 自行改写为成功；Permission、Action Firewall、Effect Fence、Evidence、Canonical 与 Evaluation 仍由既有唯一 Owner 控制。

### 完整能力边界

| 闭环组成 | 用户最终得到的能力 | 必须保留的证明 |
|---|---|---|
| GLOBAL / ALL 与商业主体 | 可新增并逐步完善国家、主体、品牌、门店、场内关系、别名、市场、城市与时间；Focus 是可选缩小范围。 | 关系有来源；同名/跨城不混同；数据覆盖、未知与未采集状态不造假。广州太古汇、罗湖万象城只是深度样例，不代表全球覆盖。 |
| 采集与研究 | 按业务目标编译词条查询，六个平台及其他已批准来源保留平台原生正文、作者、时间、指标、评论与获准媒体；趋势/热点、平台热榜和序境样本热度明确分开。 | 2026-01-01 起按原生发布时间/事件时间回溯并持续增量；来源、授权、capture time、identity、scope、cursor、失败与恢复可追溯。 |
| CTH | 监测、事件日历、消费者反馈、风险、Case/Insight/Decision、行动、结果与评价。 | 具体 Subject/scope 的真实结果；没有销售、客流、满意率或效果资料时不编造。 |
| BMP | 品牌组合、市场、竞品、消费者、创作者、传播、内容 Brief、Campaign、风险与对标。 | 币种、地区、时间窗、来源角色和指标定义可比较；广告与自然讨论区分。 |
| Shared 创作 | 资料理解、引用、研究、报告、原创提案、Word、视频和播客；结果可编辑、导出、搜索、修订、重开与恢复。 | 同一资料进入任务；正式 Artifact/hash/版本、父版本、Evidence 和业务消费者一致。计划或时间轴 JSON 不是成片/节目。 |
| 自有 AI / Agent | 使用许可允许商用的公开基础权重和自有训练/部署，独立承担序境推理；Agent/Skills/Memory/工具、上下文与恢复由唯一 Gateway/Runtime 执行。 | 实际 step/loss、checkpoint 字节、reload/resume、独立 held-out、真实 Gateway 业务输出、权限、失败恢复与受控晋升/回滚。无 Owned 推理时不能把摘录冒充分析完成；也不能因此把产品改成只会拒答。 |
| 四个产品入口 | Public Website、Web Workspace、Desktop App、Mobile Companion 共用同一 Product Core；Website 解释和引导，Web 做研究/方案/审阅/接续，Desktop 承担专业媒体/本地工作，Mobile 承担审阅/批准/通知/接续。 | 同一任务/版本跨端恢复；每端布局按任务设计。原创手绘二维水彩/版画纸感，角色遵循用户 Brief；线性功能 glyph、手绘 identity icon、第三方来源图标分层；颜色丰富但不滥用；有用交互保留。官网可按内容滚动，其他操作面避免无必要整页上下滚动；必要长内容与无障碍操作不能被截断。视频/播客时间轴可横向拖动/缩放/seek，并保持轨道、标尺、播放头同步。 |
| 独立运行与发布 | Developer/Codex 停止后，序境自有运行环境继续承诺的采集、AI、任务、恢复与用户工作。 | 同 SHA 源码、构建、依赖、DB、权限、运行和 Artifact 对齐；崩溃、取消、撤权、断网、重启、备份、回滚、可观测和跨端真实操作通过。 |

### J1–J8 产品能力映射

| Job | 产品能力与Owner | 完整结果 |
|---|---|---|
| J1 数据建设 | C1 / SYSTEM Collector | 主体、市场关系、词条、授权平台、来源、原生字段、持续更新与真实结果进入产品。 |
| J2 商业运营 | C3 / CTH | 监测→事件/消费者→风险/Case→Decision→获准 Action→Outcome/Evaluation。 |
| J3 品牌市场 | C3 / BMP | 品牌/竞品/消费者/创作者/传播/Campaign按可比口径分析，结果可进入SH-01和Brief。 |
| J4 原创提案 | C4 + C5 | 研究资料与引用继承到可编辑原创策略、预算与Word成品。 |
| J5 视频制作 | C4 + F + C6 | 真实可编辑工程、二维视觉/镜头/音频/字幕、渲染、保存、时间轴滑动、重开与恢复。 |
| J6 播客制作 | C4 + C2 + C6 | 可听节目、可编辑时间线、音频/语言理解、试听、分段修订和恢复。 |
| J7 材料与自有AI | C2 + C5 + 业务Owner | 经授权的资料检索、精确引用、Owned Gateway分析/建议和训练评价进入真实任务与保存链。 |
| J8 跨端与运行 | C6 + F + 所有能力Owner | 同一版本在四端按各自角色可操作；运行、恢复、打包、发布与持续独立执行成立。 |

### 六个 C 成果与验收要求

C1–C6 是六个完整用户成果责任，不等于六个零碎函数批次；F 独立负责四端，不由 M 接管。R01–R15 是验收/依赖覆盖，J1–J8 是用户 Job 映射，U01–U25 是全产品结果覆盖；均不是另起的 15 轮调度。六项专项及更深细项仍保留。

| 成果 | 既有责任 | 完整退出条件 |
|---|---|---|
| C1 数据与采集 | 现有 SYSTEM Collector、平台/Subject/Source/Evidence/Canonical/Scheduler owners。 | 六主平台和其他已批准来源按 exact purpose/scope/auth 正常工作；真实采集、原生字段、正式准入、查询/刷新、后台持续运行及恢复闭环；新主体与词条增量有依据；真实 CTH/BMP 任务有用。 |
| C2 自有 AI 与 Agent | 唯一 AI Gateway、Owned training/inference、Agent/Skills/Memory/Evaluation/Learning。 | 按已批准模型/样本/许可与可用资源训练，step/loss、checkpoint、恢复、held-out、正常自有 Gateway 业务结果和受控回滚成立；Codex/GPU临时环境不能冒充线上服务。 |
| C3 CTH/BMP 工作流 | 现有领域服务、业务指标/Case/Decision/Campaign/Outcome/Evaluation。 | 同一来源与scope可以形成真实研究/方案/行动/结果；来源、预算、约束变更后只改受影响内容，并留下可追溯 Decision→Action→Outcome→Evaluation。 |
| C4 提案、视频、播客 | 原创提案、既有 Timeline、编辑器、Renderer、Audio/Podcast、Artifact。 | 提案可编辑可导出；视频真正渲染且工程可重开；节目能播放/试听且分段可编辑；各自验收，不以复用文件或计划表替代。 |
| C5 Import/Research/Shared deliverables | 现有资料导入、研究、引用、Reporting、Artifact、通知/偏好 owners。 | 真实材料按许可和范围进入可定位 Evidence；正常创作/业务消费者可继承、保存、查找、修改、导出、重开、恢复；未读/未采用研究仍有主责与去向。 |
| C6 集成、运行与发布 | Shared API composition、唯一正式 DB 变更协调、Core、Browser、FFmpeg、Supervisor、Recovery、main 发布。 | 同 SHA 接通 C1–C5 与四端；真实运行/取消/撤权/重启/回滚、同版本 Artifact/DB/Evidence、合规/安全/可访问性门禁与 Product Owner 可重复真实任务成立。 |

## 3. 当前采集源码堵塞（固定 main 源码事实）

本节独立核对的源码基线固定为 GitHub main `52cd770cde458f73f99e4073014c90a9d850c3f4`；以下是源码缺口，不代表线上当前运行状态。固定链接使用完整 commit SHA，便于回查。

| 优先级/分类 | 本地源码位置与固定提交链接 | 引用/调用证据 | 准确结论与现有 Owner 的下一步 |
|---|---|---|---|
| P0，已核实源码缺陷 | `lumenis/system/collector/adapters/base.py:25-33`；[`facebook.py:69-119`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/facebook.py#L69-L119)；[`base.py:24-34`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/base.py#L24-L34) | `CollectionResult.platform` 是必填；Facebook search、exception、delegate/detail/comment/creator 和 health 返回都未提供该参数。 | 普通 Adapter 调用会因构造 `TypeError` 失败，异常回退也可能再次失败。C1 修 shared wrapper 的真实所有返回路径及用户可见 error；C6 接回正常调用。验收应走 adapter→canonical task，而不是只绕过旧 V4 engine。 |
| P0，错误状态 | [`collector_status_api.py:51-66`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/collector_status_api.py#L51-L66)、[`collector_status_api.py:102-138`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/collector_status_api.py#L102-L138)、[`facebook.py:105-119`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/facebook.py#L105-L119) | `app.py:542-543` 注册 status blueprint；无 cache 时文件状态 `ACTIVE` 会被输出成 `cookie_status=ACTIVE`、`last_check=now`，错误文本又说未做真实连通验证，汇总仍计入 active。Cache reader 没做 age/freshness裁决。Facebook health 只查本地 cookie 文件和 proxy 环境却能回 `SUCCESS`；`get_collection_surface` 将无 config-only scope 的成功状态映为 `READY`。 | `CONFIGURED`、SESSION/permission 验证、worker可达、上次真实运行、当前采集、正式准入必须分开；无实测不得生成 connected 状态/时间。C1 修真实 Adapter/status owner；C6 绑定消费者并按实际检查时效显示。不能把这种误报用 blanket enable 修掉。 |
| P0，平台能力与身份表不一致 | [`config.py:142-173`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/config.py#L142-L173)、[`registry.py:22-35`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/registry.py#L22-L35)、[`platform_naming.py:23-32`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/platform_naming.py#L23-L32)、`collector_status_api.py:31-49` | Facebook/X capability rows have no `manual_collection_enabled` although both appear in the secondary list. XHS adapter key (`xhs`), canonical content ID (`xiaohongshu`), cookie owner and independent 17-platform status list contain overlapping alias ownership. | C1 reconciles exact alias, allowed methods, identity and manual scope through current owners; preserve old stored `platform` for reads. Do not blindly set true flags or create a new registry/status source. |
| P0，正常任务不能完整接续 | [`experience_runtime.py:847-919`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/experience_runtime.py#L847-L919)、[`secondary_collection.py:2186-2271`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/system/collector/adapters/secondary_collection.py#L2186-L2271) | Route allowlist accepts `business_requests`/`continuation`, not `checkpoint`, and does not pass the returned checkpoint. `collect_business_queries` accepts input fingerprint/completed query keys but calls `collect_search`; its plan checkpoint is not platform-native page/detail/comment/reply/creator cursor. | C1 specifies complete platform-level collection semantics; C6 binds the same typed checkpoint to existing durable Task/Scheduler. Preserve partial results, per-platform native cursor, idempotence, exact auth, cancellation/revocation, restart and no duplicate accepted pages. Search-only cannot satisfy a request promising detail/comments/media/creator data. |
| P0，两个调用入口需归一但不得破坏兼容 | [`experience_runtime.py:825-919`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/experience_runtime.py#L825-L919)、[`app.py:6267-6270`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/app.py#L6267-L6270)、[`lumenis/blueprint.py:254-275`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/lumenis/blueprint.py#L254-L275) | Canonical CTH search route and registered `/v4/adapters/collect`/task polling use distinct orchestration callers; legacy persistence is in `lumenis/adapters/collector_service.py` and `lumenis/adapters/persist.py`. | C1/C6 preserve unique legacy task-id/polling/risk/platform behavior and make both call paths delegate to one Collector/Task/Permission/Source/Evidence/Canonical write contract. Retire only exact duplicate behavior after its mapped acceptance; no bulk deletion, parallel queue or second truth owner. |
| F-owned / report-only; not verified by M | Backend [`experience_screens.py:377-439`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/52cd770cde458f73f99e4073014c90a9d850c3f4/experience_screens.py#L377-L439); UI source not read. | Backend canonical row returns date, capture time, platform, source URL and nested Evidence lineage. Supplied audit asserts Flutter drops some fields and has no POST wire; M did not inspect Flutter per scope. | F independently validates its source under Experience; C1/C6 provide the exact canonical DTO/call contract. This report does not accept the Flutter result. |
| DB / historical data assertions not live-verified | Supplied file `C:\Users\28049\.codex\attachments\d30e7dc6-911d-4606-b95d-c809e736ef0b\已粘贴的文本.txt`; no live DB was opened. | Supplied audit mentions historical native-row/body/media/metric discrepancies. No rows, source hashes or current DB snapshot were reread in this prep. | Keep as report-snapshot evidence; do not call data loss or repair by aggregate count. A future authorized C1/C6 read-only path must bind each exact row to source version and media/source material before correction. |

### 实际验收不是“status green”

实际闭合需同一授权业务 Task：输入词条/实体/市场/日期 → resolve 已批准 identity 和权限 → task plan → 真实 search + 各平台可用的 detail/comments/replies/creator/native pagination → 保留部分结果和cursor → 失败平台隔离 → Source/Evidence/Canonical 正式接收 → CTH/BMP 可按来源打开正文/指标/媒体 → 保存、重开、刷新、撤权、取消和断线恢复 → 真实业务结果与 Evaluation。页面 status、HTTP 200、配置存在、adapter 注册、测试 fixture 或一次 `search` 都不构成该任务完成。

本轮没有运行这个验收链。测试、运行、DB 和用户操作均继续标 `NOT VERIFIED`；上述源码修复必须由现有 C1/C6 在正式启动后实施，不是报告已修复。

## 4. 已纠正的明确规则冲突

| 条目 | 当前结论/分类 | 证据、替代来源与建议 |
|---|---|---|
| 49条处置编号与R验收编号冲突 | **已纠正；历史需保留。** `D01–D49` 才是处置ID；旧文件里的 `R01–R49` 仅存为 `prior_audit_disposition_id`，明确非产品验收。 | `APPROVED-CONVERGENCE-20261004.json` 49行唯一映射；MD表格共49行；`AGENTS.md`、Source Owner Index、Overlay 以 R01–R15 表示产品验收，不按序号连接。Git历史原报告/49行结论保留。 |
| “APP ONLY”压掉官网/Web/四入口 | **已解决；现有引用属历史解释，不是活动规则。** | `README.md` 明确 `website/` 是官网，Flutter `/workspace`、Desktop/Mobile共Core；Product Architecture §6 说明旧 APP ONLY 只作历史证据；Owner Index 旧覆盖组02已重写为保留已批准四端。删除唯一蓝图中的历史说明会失去纠错背景，故不删。 |
| “15轮/15阶段”与六个C窗口混淆 | **本轮已纠正活动路由；细项作为历史验收覆盖保留。** | Source Owner Index 表1–15已改为 Historical coverage groups；Real Delivery Overlay旧ROUND02–14标题改为历史覆盖组，卡字段改为 C Window / Delivery，当前分派仅AGENTS里的C1–C6。Overlay完整闭环条件沿用旧ROUND15唯一验收内容，不再是一个执行窗口。 |
| 固定RTX5090/4090旧方案 | **历史需保留，不再活动。** | `AGENTS.md`、Takeover CURRENT、Material Owner Contract以现有/免费资源优先，旧租赁和GPU预算仅历史证据；不删除step=0与付费损耗记录，不把模型硬件选择写入当前路由。 |
| reporting locator的不存在根目录 | **已替代并修正本地导航实现。** | `scripts/audit_tools/locate_capability_context.py`移除不存在的裸 `reporting/` 根，保留 `lumenis/shared/reporting/`。Cited check at earlier pin reported `missing_owner_roots=[] / ROUTED_NOT_VERIFIED`;不代表报告行为已验收。 |
| Guardian `thread_context`废弃键 | **配置范围已核对为不存在；无需再写设置。** | 已检查目标用户/项目 `config.toml` 中没有该键或 `[features.guardianv2]`；本轮未改全局或项目配置。现有CURRENT有核验说明；不再把它作为等待用户操作的bug。 |
| 本地重复实现候选与 `work/` 归档 | **尚未完成逐项去重/处置；全部受保护。** | 原记录的43,381是Git untracked路径计数，不是文件内容或唯一实现数。2026-10-06 00:32的路径名元数据扫描（排除F与敏感路径，不读内容）找到31个外层候选/候选产物标签目录；W2/W4/C3+C5中含大量validation-source、依赖、生成产物，不能把路径/源码扩展名数当独立实现。D44回执17个after hash中6/17匹配当前c776 main、11/17不匹配；保留的base/ours/owner triplets 可重构11个after hash，另6个无法由这组输入重构。D45回执3/3匹配。当前main在[`internal_pitch.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/c7765b87fee1d524f17ddc1661976f0ea83fd799/lumenis/shared/content_creation/internal_pitch.py#L29-L33)、[`lumenis_app_api.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/c7765b87fee1d524f17ddc1661976f0ea83fd799/lumenis_app_api.py#L147-L153)、[`api_dual_domain.py`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/c7765b87fee1d524f17ddc1661976f0ea83fd799/api_dual_domain.py#L168-L174)和对应route test能定位source-bound/v3；这是源码存在证明，不是正常业务E2E。11个字节差异尚未语义判定，不能推断功能丢失或某副本可删。 | 后续由现有C3/C5/C6 Owner逐条比较那些历史输入与当前主线，只在证明完全重复且已有等价主线替代时才处理单项归档；保留全部receipt和不同postimage。不读F、不清理、不移动/删除。 |

## 5. 规则、资料、代码与验收的唯一去向

当前完整资料快照记录 191 条 direct refs：C1=4、C2=2、C3+C5=32、C4=70、F=83；其中185 `ASSIGNED_INCOMPLETE`、3 `PAUSED_PENDING_USER_RESUME`、3 `USER_REVIEWED_PENDING_PRODUCT_INTAKE`。这不是历史资料全集，也不证明已阅读或被采用。官方站点索引有4,797条URL；723篇正文和18篇短正文仍按逐篇责任留存。F的83项与稿件仍由F独立处理，M没有检查内容。

现有研究路线 RC-01–RC-14 对应到已有能力如下；材料保存、提取、完整阅读、使用授权、纳入产品、实现、验收是不同状态：

| 研究路线 | 已有Owner与应改善的产品能力 | 尚缺凭证，不许写成“已训练/已吸收” |
|---|---|---|
| RC-01 OpenAI/Codex/ChatGPT/Claude/Muse；RC-02用户增补 | C2 Gateway/Agent/Skills/Memory；每项原始需求进入J/U/R现有Owner。 | 文档阅读覆盖、合法来源、真实推理行为与实际业务结果。 |
| RC-03 采集OSS；RC-13主体/品牌词条 | C1 SYSTEM Collector/registry/Scheduler；按事实扩充词条、时间、来源和目的查询。 | 当前版本/许可、授权通路、native fields、真实六平台持续采集和准入。 |
| RC-04 新闻/传播；RC-05广告法/专业规范；RC-06 SNU课程 | C3/C5 Research + CTH/BMP/Content/Evaluation；改进事实、样本代表性、反例、主张与法律适用。 | 逐文/逐章阅读范围、来源时间、jurisdiction和专业审查；不把摘要或课纲称学完。 |
| RC-07 Baseten推理工程；RC-14治理/结果研究 | C2/C6 Gateway、训练、Runtime、Evaluation；成本、延迟、恢复与结果保真。 | 真实已许可组件版本、硬件、step、loss、checkpoint/reload、held-out和正常服务。 |
| RC-08剪辑/视听/V2；RC-09中英韩音频/音乐；RC-10官网/说明/支持/日志 | C4/F Timeline、Renderer、Podcast、Experience与现有操作页。 | 视频/音频已读区间、试听、人类审阅、版权；F本轮未检查，官方站点逐篇责任未完成。 |
| RC-11原始公众材料；RC-12来源连续修订 | C1/C5 Importer/Evidence/SavedWork/Artifact与CTH/BMP/C4消费者。 | 原件、source/use/scope/version、真实引用消费、只修改受影响结果、重开及回滚。 |

训练版权和正常产品使用权分别审批；产品资料不能默认放入训练集。仅存仓库中的手册/网址/课程/视频不能提高产品能力；采用时必须指出改变的现有处理逻辑、质量标准、用户行为或已有AI recipe，并由对应C Owner给出真实任务结果。

## 6. 文件与规则逐项清单

本清单是在 `52cd770c` 线上基线上的本地审定差异。采样时这些修改尚未到GitHub；同一交付发布后应以新的 `main` SHA 和本地文件为准。历史改动并非全部由本轮新写。

| 路径/行号 | 本地与线上差异 | 用途与分类 | 现行替代/引用检查证据 | 建议/最终去向 |
|---|---|---|---|---|
| `AGENTS.md:12-75, 361-430, 1169-1195` | 相对52cd为本地治理差异 | **仍有效/唯一执行路由**：M仅做准备；六个C保留责任不自动激活；候选政策、账号/模型手动选择与采集边界。 | 同步 CURRENT、Source Owner Index；不恢复旧窗口模型、云端拆分和固定5090。 | 保留并同一批发布；产品运行变更另按正式启动批准。 |
| `README.md:1-50` | 相对52cd本地变更 | **仍有效/人类入口**：唯一蓝图、四入口和开工约束。 | 与AGENTS及Product Architecture一致；明确Public Website与三种Flutter运行端的职责。 | 保留；不把README当唯一执行权威。 |
| `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md:1-82` | 相对52cd本地变更 | **CURRENT**：本轮范围、真实时间快照、Owner状态和来源审计摘要。 | 第17/22行标明last-receipt时间；第32项区分源码已复核与Runtime/DB未重查。 | 保留；有新源码/运行证据时只更新对应事实，不把历史记录当当前状态。 |
| `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md:114` | 现有52cd蓝图已明确历史APP ONLY和四入口，未改 | **仍有效/唯一产品蓝图**。 | 主体、创作、AI、四面、研究去向与同版本用户闭环；由Experience负责视觉细则。 | 原文保留；只在用户审核后改变产品范围。 |
| `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md:12-38, 188, 501-520` | 相对52cd本地变更 | **已纠正仍有效/Owner索引**：旧15轮作为覆盖，C1/C6任务列出确证缺口；D编号与R验收分开。 | 精确引用固定main 52cd源码；locator返回collector唯一owner root；source audit表里F/DB未核实的部分单独标记。 | 保留，作为C1/C6后续Task Card；不得在本准备任务直接改采集源码。 |
| `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md:1-160, 242-930, 997-1100` | 相对52cd本地更新旧标题/格式 | **已替代为六C执行口径，验收内容保留**。 | 移除“Round 01–15”作为派工含义；旧内容改历史覆盖组；`C WINDOW / DELIVERY`、当前R/J/U保持。 | 整份内容不删除；用R01–R15作为验收要求，不作为额外轮次。 |
| `scripts/audit_tools/verify_codex_takeover_governance.py:633-637, 786` | 相对52cd本地更新门禁 | **已替代的调度校验引用**。 | 门禁由要求旧`ROUND 01–15`字面标记，改为逐项要求 `HISTORICAL COVERAGE 01–15 ACCEPTANCE`；六个C成果和各项验收均保留。治理门禁现通过。 | 保留更精确的新标记，不把旧轮次名补回Overlay。 |
| `00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md:115-190` | 本轮本地新增明确语义条件 | **仍有效/Collector专业合同**：状态真实性、alias、query checkpoint和native pagination、旧入口兼容。 | 与Owner Index §11同向：一个Collector/Task/Permission/Source/Evidence/Canonical写入Owner。 | 保留为能力合同；真正源码修复由C1/C6后续执行。 |
| `00-GOVERNANCE/evidence/round-15/APPROVED-CONVERGENCE-20261004.json:1-719` | 本轮本地更正字段语义并加入2026-10-06 D44/D45重核 | **历史处置记录、非路由**：49行D01–D49，旧审计标签另名。 | 49个D ID/旧审计标签均唯一、无`legacy_id`；D43/D44/D45都有 current recheck；差异未冒充语义结论。 | 保留原发现及回执；差异交C3/C5/C6现Owner核语义后再决定单项归档；R验收编号不与旧标签关联。 |
| `00-GOVERNANCE/evidence/round-15/APPROVED-CONVERGENCE-20261004.md:1-79` | 本轮本地更正表头和介绍，补D44/D45当前差异状态 | **历史证据/逐条处置表**。 | 49行齐全；原审计ID明确“非验收项”；固定历史提交链接留存。 | 保留，不把它升级成第二套规则。 |
| `00-GOVERNANCE/evidence/round-15/CURRENT-PROTECTED-LOCAL-BOUNDARIES-20261005.json:1-161` | 此次未改；历史快照 | **保护记录、非候选准入表**。 | 记录`work/` Git untracked 计数为43,381及23个直接子目录；未逐项内容检查。本次path-only复核另见D44/D45 current_recheck及本报告。 | 保留快照原貌；不得将其历史观察时间冒充本次盘点。 |
| `00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/MATERIAL-OWNER-CONTRACT.md:1-77` | 相对52cd本地改当前暂停/资料责任口径 | **仍有效/材料分工合同，不激活窗口**。 | 191直接引用快照及URL/未读数明确非完整全集；F稿件M不读。 | 保留；Owner后续逐篇/逐项落实且给出采用/实现结果。 |
| `00-GOVERNANCE/LUMENIS-ROUND-03-CHARTER-CURRENT.md`; `00-GOVERNANCE/LUMENIS-ROUND-03-FIRST-TASK-CARD-CURRENT.md`; `00-GOVERNANCE/LUMENIS-ROUND-03-B001A-TASK-CARD-CURRENT.md`; `00-GOVERNANCE/LUMENIS-ROUND-03-B001B-TASK-CARD-CURRENT.md`; `00-GOVERNANCE/LUMENIS-ROUND-03-B001C-TASK-CARD-CURRENT.md`; `00-GOVERNANCE/LUMENIS-ROUND-03-B001D-TASK-CARD-CURRENT.md` | 六个本地文件增加历史/当前状态提示 | **历史验收/约束证据，不是当前任务**。 | 共同Banner指向最新AGENTS；原保护DB、测试和source证据仍保留。 | 不删历史内容；不让旧task card重新激活。 |
| `scripts/audit_tools/locate_capability_context.py:96` | 相对52cd本地改owner root | **仍有效/导航工具**：仅移除不存在的裸`reporting/`，保留共享canonical根。 | `--capability reporting --query citation`的既有定向回执为 `missing_owner_roots=[] / ROUTED_NOT_VERIFIED`。 | 保留；导航成功不是报告能力验收。 |
| `lumenis/system/collector/data/schedule_state.json` | 2026-10-06 00:08 +08看到的tracked dirty；不在本批暂存/提交 | **证据不足/疑似运行状态数据**；内容未读。 | 只确认该路径从初查后变dirty；不能推断写入者或语义。 | 保持原样和unstaged；由真实运行/Collector Owner单独核来源与状态，不重置或覆盖。 |
| `config/ai-owned-training-runtime.json`、`work/`、`00-GOVERNANCE/evidence/round-06/C1-W1-DATA-COLLECTION-2026-10-02.md` | 本地untracked，不推送 | **私有/未分类历史与材料**。 | 保护边界JSON标明私有配置不提交；C1记录为local receipt；43,381条work path未逐项分类。 | 不stage/不删除/不迁移；由确切Owner逐个处置。不称为唯一工作已经整理完毕。 |

### 6.1 `work/`候选命名根路径盘点（路径元数据，不是内容验收）

2026-10-06 00:32 +08扫描了非F、非敏感子树中的最外层“candidate”命名目录，共31项。表内“直接文件/代码”只计该目录本层，不包括子目录；Validation Source、依赖和产物内容没有因此被读取或认定为产品源码。所有项当前均为 `LOCAL_ONLY / PATH_ONLY / CONTENT_AND_UNIQUENESS_OPEN`；属于哪个Owner依据归档根路径推定，不能据此自动移交、清理或合入。唯一活动实现仍是main；这张表仅帮助后续逐项认领既有资产，不是第二任务队列。

| 现有Owner线索 | 本地 work 路径 | 本层文件 / 源码类文件 | 分类与接续 |
|---|---|---:|---|
| C1 | `work/c1-w1-20261002/six-platform-safe-routing-candidate-20261003` | 4 / 0 | 路径像采集研究/材料包；需C1核原件、来源/许可与main替代关系。 |
| C3+C5 | `work/c3-c5-local-continuation-20261003/candidate` | 234 / 192 | 源码快照标签；内容/版本尚未与main逐项比对。 |
| C3+C5 | `work/c3-c5-local-continuation-20261003/candidate-v2` | 234 / 192 | 同一C3+C5线的第二个快照标签；不得仅据版本号删除。 |
| C3+C5 | `work/c3-c5-local-continuation-20261003/candidate-v3` | 234 / 192 | 同一C3+C5线的第三个快照标签；需比较唯一改动/来源输入/回执。 |
| C3+C5 / C6 | `work/c3-c5-local-continuation-20261003/integration-validation/candidate` | 1 / 1 | 集成验证材料；验收输出不等产品实现。 |
| C3+C5 / C6 | `work/c3-c5-local-continuation-20261003/integration-validation/candidate-owned-output-bytes` | 0 / 0 | 字节输出子包标签；内容位于子目录，未读。 |
| C3+C5 / C6 | `work/c3-c5-local-continuation-20261003/received-transaction/candidate` | 1 / 1 | transaction/receipt相关快照；需确认主线引用。 |
| M / C3+C5 | `work/m-controller-20261002/w5-final-source-boundary-reception-20261003/inputs/candidate-owned-output-bytes` | 0 / 0 | W5接收包的输出字节目录；不是M新建的业务Owner。 |
| C2 | `work/osai-resume-candidate-20261001-211338` | 4 / 2 | OSAI/恢复材料名；仅路径标签，不证明当前模型/训练。 |
| C3 | `work/w3-business-continuation-20261002/action-outcome-candidate-20261003` | 41 / 0 | Action/Outcome业务产物候选名；需读其现有回执/owner映射后归类。 |
| C4 | `work/w4-creation-20261002/brief-ingestion-complete-candidate-03` | 3 / 0 | Brief导入/创作材料标签；需核文件类型与版本。 |
| C4 | `work/w4-creation-20261002/candidate-01` | 2 / 0 | 内容未知；保留。 |
| C4 | `work/w4-creation-20261002/candidate-02` | 1 / 1 | 内容未知；保留。 |
| C4 | `work/w4-creation-20261002/candidate-03` | 2 / 1 | 内容未知；保留。 |
| C4 | `work/w4-creation-20261002/candidate-04` | 1 / 1 | 内容未知；保留。 |
| C4 | `work/w4-creation-20261002/caption-owner-candidate-v1` | 1 / 0 | 版本化字幕/编辑证据标签；嵌套验证源码未读。 |
| C4 | `work/w4-creation-20261002/caption-owner-candidate-v2` | 1 / 0 | 版本化字幕/编辑证据标签；嵌套验证源码未读。 |
| C4 | `work/w4-creation-20261002/caption-owner-candidate-v3` | 7 / 2 | 版本化字幕任务，存在嵌套源快照；尚未唯一性核对。 |
| C4 | `work/w4-creation-20261002/caption-owner-candidate-v4` | 7 / 2 | 版本化字幕任务，存在嵌套源快照；尚未唯一性核对。 |
| C4 | `work/w4-creation-20261002/caption-owner-candidate-v5` | 11 / 2 | 版本化字幕任务，存在嵌套源快照；尚未唯一性核对。 |
| C4 | `work/w4-creation-20261002/manuscript-only-candidate-v1` | 11 / 0 | 文稿来源版本标签；嵌套内容/权利状态未核。 |
| C4 | `work/w4-creation-20261002/manuscript-only-candidate-v2` | 7 / 0 | 文稿来源版本标签；嵌套内容/权利状态未核。 |
| C4 | `work/w4-creation-20261002/manuscript-only-candidate-v3` | 12 / 0 | 文稿来源版本标签；嵌套内容/权利状态未核。 |
| C4 | `work/w4-creation-20261002/original-general-pitch-intake-v1/inputs/brief-ingestion-complete-candidate-03` | 2 / 0 | 提案输入候选标签；需确认与现行Source/Brief contract关系。 |
| C4 | `work/w4-creation-20261002/original-general-pitch-intake-v1/inputs/pitch-source-quality-v4/layout-candidate-v1` | 2 / 1 | 提案版式/来源质量标签；不等最终Screen或产物接受。 |
| C4 | `work/w4-creation-20261002/original-preparation/audio-candidate03-verification-v1` | 1 / 0 | 音频验证材料标签；音频/权利未复核。 |
| C4 | `work/w4-creation-20261002/original-preparation/audio-candidate03-verification-v2` | 2 / 0 | 第二版音频验证材料标签；不得与v1按名字推定优劣。 |
| C4 | `work/w4-creation-20261002/pitch-category-candidate-01` | 9 / 3 | 提案类别候选名；代码/策略语义未读。 |
| C4 | `work/w4-creation-20261002/pitch-input-truth-candidate-02` | 4 / 1 | 提案输入真值候选名；需校验Evidence/Source lineage。 |
| C4 | `work/w4-creation-20261002/pitch-source-quality-v4/layout-candidate-v1` | 6 / 1 | 提案版式/质量候选名；需与上方相似路径分别核hash，不能按名称合并。 |
| C4 | `work/w4-creation-20261002/podcast-plan-candidate-02` | 12 / 0 | 播客计划候选名；计划不等真实节目/Timeline/Artifact验收。 |

此盘点不包含被过滤的F或敏感子树，不展开任何子目录文件正文；相同路径名、文件数或源码后缀都不是重复证明。下一步需沿各Owner的精确receipt/manifest和当前main逐项判断 `KEEP / MERGE / RESTORE / MIGRATE / DELETE / RESEARCH`。当前没有任何一项因本元数据扫描被删除、搬移或宣称完成。

## 7. 开工准备与产品状态清单

| 检查项 | 状态 | 证据/备注 |
|---|---|---|
| 本地与GitHub main基线、remote、分支、初始dirty/untracked状态 | **本轮已核/发布前须fresh复核** | `git remote -v` 指向指定私库；主线 `52cd770c...`；本轮增量发布前再次 fetch + live ls-remote。 |
| 唯一执行口径与六个完整成果责任 | **已收敛到现有AGENTS/Owner Index** | C1–C6及独立F；paused与责任未丢失；本轮没有启动窗口。 |
| APP ONLY/四入口错读 | **已在当前路由纠正** | `website/`仅官网；Flutter的Web Workspace/Desktop/Mobile共用同一Core。历史原文保留。 |
| 49处置ID与验收ID | **已修复本地** | D01–D49；原标签另存；与R01–R15不再按序号对应。 |
| 旧15轮/固定5090/模型分配是否活动 | **现行规则已改为历史覆盖** | 单一执行仍由AGENTS决定；可用资源优先，模型按人工当前选择，不借本准备启动付费计算。 |
| C1/C6 Collector堵塞点与接收任务 | **源码已核、任务已写；产品bug仍未修** | §3精确到当前main调用者、状态错误、HTTP续接和双入口集成。 |
| CTH03 / Flutter交互 | **M未核Flutter源码** | F独立；仅核对服务端projection字段，UI/POST断言仍来自用户报告，未签收。 |
| 数据库所述历史行差异/当前runtime/scheduled采集 | **NOT LIVE-VERIFIED** | 本轮没打开数据库、没发平台请求、没探Runtime；用户旧报告不提升为当前事实。 |
| 研究材料全文阅读/产品采用 | **尚未全部完成；责任保留** | 191 direct refs不是全集；未读与未获授权内容留给对应Owner，不强行称已吸收。 |
| `work/`唯一化与旧候选逐项清理 | **未完成，受保护** | D44回执17个after hash有6匹配/11不匹配，D45为3/3匹配；metadata-only扫描找到31个外层候选标签目录（含验证快照/产物，不等于独立实现）。43,381是Git untracked计数；完整内容/权利/唯一性仍未逐项核实。现行规则禁止再造候选；历史资产仍须按Owner和精确内容区分，不能整树删除。 |
| 全产品实现、Owned推理、四端E2E、发布和用户接受 | **未完成/本轮未执行** | 本报告只是产品蓝图与执行准备，不代表任一实现态升级。 |

## 8. 产品 Owner 审核点与后续边界

请审核本文件第2节的结果闭环与六个C成果退出口，以及第3节C1/C6已定位缺陷是否完整表达你的目标。审核后，正式产品执行仍只走 `AGENTS.md` 的C1–C6完整任务卡与独立F责任；研究、候选、旧窗口/云环境和历史验收报告不能另起路线。普通错误由对应Owner直接研究并修复，只有真实的权限/成本/产品裁决才上报。

当前新增源代码修复、真实采集、GPU训练、Runtime/DB改动、前端执行、产品E2E和发布均未执行。完整闭环仍要求许可材料和真实有效数据进入真实任务，得到专业、可编辑、可保存、可修订、可重开、可恢复并带Outcome/Evaluation的成果；在你审核和正式启动之前，本报告不授权上述产品实现。
