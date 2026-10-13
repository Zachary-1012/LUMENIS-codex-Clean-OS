# 序境 / LUMENIS — Codex Takeover CURRENT

Status: **CURRENT EXECUTION ENTRYPOINT / NO-REDISCOVERY**

## 2026-10-13 PO rules (binding; supersede conflicting text)

1. All collection platforms (RedNote, Douyin, X, Instagram, Facebook, WeChat OA, and any added later) collect in the product's built-in browser in the background by default. When a session is invalid, the product shows an in-product login popup inside the built-in browser. After login plus a session health check, the original task resumes automatically.
2. Never auto-open an external or visible browser window for collection. Headless background workers only. A visible window is only the HUMAN_INTERACTIVE login popup above.
3. The automatic collection scope is all active registered subjects (Subject/BrandFocus). `GUANGZHOU_TAIKOO_HUI` is one registered subject, not the scope or a default. No code may hardcode one subject as the filter, context or brand list; use `subject_registry.registered_subject_names()` and the acquisition plan.
4. R&D stage: agents change configs, keep-alive sessions and approvals directly, including subject registration and official-name writes via `subject_registry` / `import_subject_registry_seed.py --apply`. The agent grants the exact CONFIG_MODIFY approval in-process, takes a DB backup first and records the receipt; the PO is not asked. This supersedes "needs exact PO manual approval" wording below.
5. A PR whose required checks (Product Gate + App Gate) are all green, with review threads addressed, may be merged without waiting for PO approval.
6. For every newly added subject, developers run the end-to-end flow themselves: add_subject -> DB -> official name with source -> acquisition plan -> verified collection -> visible in product. The flow is kept in CI (`tests/test_e2e_new_subject_flow.py`).
7. Brand and subject names use the brand's own official-site spelling, with the source URL recorded (`record_official_name`). LUMENIS never renames a brand.

## 2026-10-13 Single product closed-loop entry (dated readback; start here)

This file is the one entry every agent (Codex, Akang, Akang1) starts from. Any other handoff/todo/progress note dated before 2026-10-13 is superseded where it conflicts and is kept only as history.

- Loop path: `AGENTS.md` rules -> this CURRENT -> branch -> tests -> PR -> Product Gate + App Gate green -> normal merge -> local `D:/LUMENIS_REBUILD/序/序境` equals `origin/main`, clean status. One local path only; no extra worktrees.
- Rule entry points: `AGENTS.md`; this file; governance machine contract (`scripts/audit_tools/verify_governance_machine_contract.py`); PO decisions in `00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/USER-ADDITIONS-20261004.md`; approvals in `00-GOVERNANCE/evidence/approvals/`.
- Current progress: local work-in-progress (170 files) is preserved unmerged on branch `akang/wip-business-decision` (draft PR #31; it breaks `tests/test_business_decision_workflow.py`; owner to finish) and in `D:/LUMENIS_AUDIT/20261013_akang_governance/pre-sync.patch`. PO role names (Pim/Bram/Ness/Jas/Aris, English only) and the AI watermark are recorded in USER-ADDITIONS.
- Next steps (nothing dropped; in order):
  1. Rule updates: §23 hand-drawn colour mark, §33 adapter-bounded open source, and flutter_quill register entry are applied (2026-10-13). Still open: the 3 Codex doc fixes (items not yet identified in the repo; owner Codex).
  2. Core collection: `ZBrand-HealthGuard` reinstalled 2026-10-13 17:16 and 8201 healthy; first manual RedNote run `collect_20261013_172257` started 17:22 with `http_state=BLOCKED` and 0 inserted (RedNote identity scope unbound), the 9223 HK/intl RedNote session is now AUTH_VALID (18:2x health check); X/IG/FB/Douyin sessions AUTH_VALID. Notes by source on 2026-10-13: x 763, public_http 225, douyin 66, web_atom 30, xhs 3 (last 2026-09-30), instagram 1, po_provided 1. `COLLECTOR_ENDPOINT` unset (Akang1). Auto-collection scope (PR #36, PO 2026-10-13): all registered subjects; `GUANGZHOU_TAIKOO_HUI` is one subject, not the scope. Collection workers run headless in the background (BACKGROUND mode); a visible window opens only as the HUMAN_INTERACTIVE login popup when a session is invalid.
  3. Subject registry: `subject_registry.record_official_name` (official-site source URL required; no renaming; stable subject_id) and `import_subject_registry_seed.py --official-names FILE` (dry-run default; `--apply` uses the exact CONFIG_MODIFY approval granted by the agent in R&D stage, see PO rule 4) are published (2026-10-13); then the 8 held Taikoo Hui subjects; reconcile the 78 held rows; ingest the 133 relation candidates (GLOBAL-DATA-SOURCE-RESEARCH-20261013.md §20.4) per rules.
  4. Draft PR #31 (business-decision WIP): owner to finish and pass both gates.
  5. Cleanup: stale worktrees (`D:/LUMENIS_AUDIT/20261012_rules_publish/*`, `序境-runtime-03dc8d93`, leftover `rea-merge-wt` folder), temp files, stale branches/docs, stash `akang-pre-dd0-merge`.
  6. Akang1: browser migration (WIP in the main working tree), `COLLECTOR_ENDPOINT`, tasks 1-3 (Gateway executor stub, AI-01 submit chain, stop/resume, SH-06 inbox, decision-card receipts).
  6b. Collection follow-ups (2026-10-13, tracked from PR #36 review): XHS search returns EMPTY_NO_API with a valid 9223 session (run 18:27, 3/28 keywords, 0 inserted; diagnose the rednote.com search API interception); BMP typed persistence for XHS (BMP queries currently deferred); default background run per platform; WeChat OA background worker registration (recovery returns RECOVERY_WORKER_NOT_REGISTERED until then); shared-alias disambiguation across subjects; desensitizer refresh on registry change; full registry cycle is 91 plan pages (cadence 720 min) - raise throughput.
  7. After the loop closes: logo r5 (named/unnamed + 16px), 5 role images + stickers, analysis of ~290 PC images + 47 WeChat videos, frontend. 阿康（bot）

## 2026-10-13 SYS-06 built-in browser live stream (dated readback, PR #35)

Root internal_browser_stream.py moved to the single owner lumenis/system/browser/runtime/screencast_stream.py; new rame_stream.py streams frames of the isolated /api/browser/sessions/<id> page over SSE (/frames/stream, /stream-policy). PO defaults: page AI-readable OFF and nothing to Evidence unless registered; leaving the view pauses the agent on sensitive/logged-in pages (unknown login = logged in); during human takeover no frames to AI and none stored, only action receipts; isolated sessions without personal cookies. SYS-06 shows pushed frames with gaplessPlayback; human-control actions still use lease-bound single frames. Runtime load and user acceptance: NOT_VERIFIED. 阿康1（bot）

## 2026-10-13 AI-01 submit receipt read-back (dated readback)

AI-01 submit receipt: `POST /api/experience/ai/intent` reports `evidence_recorded` only after the Evidence owner reads back the record written for that exact `execution_id` (skill_execution source, source/task/trace bound to the execution, intact content hash, payload naming the execution). The execution chain's own ok flag alone is no longer trusted. No AI output, trace route or Evidence item is fabricated; the owned Gateway stays UNAVAILABLE, so real executions can still end not-completed. Runtime load and user acceptance: NOT_VERIFIED. 阿康1（bot）

## 2026-10-13 SH-06 read-only inbox backend (dated readback)

SH-06 read-only inbox backend: `GET /api/experience/screen/SH-06` now returns items only for a signed-in actor with a verified `operational_inbox` read grant (GLOBAL_ALL needs CTH and BMP global grants; FOCUS needs the exact Subject/BrandFocus). Each TaskEngine task must carry a matching stored row scope and a fully recomputed TaskEngine Evidence hash chain; it is emitted as row projection v2 (read_allowed, scope, evidence.canonical_reference, integrity v2 content-integrity-only, lineage_verified). Unverified tasks are dropped; the legacy global task/DLQ/health shape and all approve/assign/snooze/retry controls are gone. Without a grant the screen shows "通知与待办暂不显示". Notifications/alerts lanes stay empty until an owner emits verified items. Runtime load and user acceptance: NOT_VERIFIED. 阿康1（bot）

## 2026-10-13 PO agent-role change (dated readback, not dispatch)

The direct PO clarified: Codex and Akang (GrokBot) are equal-level product-development agents; the PO alone partitions and dispatches their work. Brio (Muse) is the PO-only global-data-source research and verified acquisition-target inventory contributor, delivering one Markdown research handoff and then acting only on direct PO instructions. The operative routing is in `AGENTS.md` and the machine/source-owner contracts; this dated handoff is neither a new agent authority nor permission to run research, collection, code, training, payment, deployment or PR merge automatically.

## 2026-10-13 AGENTS LF pin and T04 structured red lines (dated readback)

`AGENTS.md` is pinned to LF in `.gitattributes`, so the Codex `project_doc_max_bytes` budget (131072, with 16384 headroom) is measured on the same bytes on Windows and in CI; the text did not change. The six T04 historical PO prohibitions are structured `red_lines` keys in the governance machine contract. The blocking validator `verify_governance_machine_contract.py` rejects dropping or allowing any of them. The PR #24 prose-anchor test has been replaced. AGENTS.md carries a one-line LF note so existing Windows clones rewrite it on update (PR #28 review). PO receipt: `PO-20261013-AGENTS-LF-AND-T04-STRUCTURED-RED-LINES`. 阿康（bot）

## 1. Online reader's current-state snapshot

Implementation publication state: `PUBLISHED_SOURCE_VERIFIED`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`

本文件只呈现当前有效的交接入口和未闭要求，不保留按日期堆叠的旧指令、旧运行快照或旧完成声明。当前用户要求是让线上与本地研发只读取同一套有效规则；本次在原文件内清理重复规则正文和旧入口，不启动Brio产品开发，不修改F/M原生Goal，不接入dot。

本次修改范围：移除经全文核对的退役执行正文、嵌套副本与活动引用，包含旧ZBC/OSAI执行基线及双仓库硬门；有效安全、复用、资料采用与验收要求由原AGENTS/Architecture/Experience/Owner承接。原缺口清单及绑定镜像纠正CTH-09已有Decision Owner与Flutter reader却标ABSENT的失真，并纠正已见Widget和Shell入口的屏幕不存在声明；汇总由同一批原记录计算。44份实际屏幕规范中的全局二维/禁3D旧限制已在原段纠正，未以模板更新代替消费者修正。屏幕存在、字段接线、动作、权限和用户验收分开，PENDING不改成通过，其余源码/运行语义不由存在性检查升级。 旧蓝图55章中的有效差异/置信度/配置管理/服务与采集诊断/格式失败边界已回填原Owner职责，旧Provider配方与示例值不恢复；这是要求承接而非11个新项目或实现完成。Shared目录仅按当前架构和真实Python绑定读取。原源码、未完成候选、研究原件、审批、业务数据与失败结果不因清理规则删除。

当前发布（PR SH-06 收件箱，阿康1（bot））：SH-06 只读收件箱后端产品源码发布；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。此前发布（PR AI-01 回执，阿康1（bot））：AI-01 提交回执校验产品源码发布；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。此前发布（PR #35，阿康1（bot））为 SYS-06 内置浏览器实时画面流产品源码发布；`PUBLISHED_SOURCE_VERIFIED`只表示源码与 CI 已核实，不代表生产已加载或用户验收。此前规则型发布：AGENTS.md 固定 LF 换行（内容不变），T04 历史禁止项迁入机器合同 red_lines，由阻塞校验器结构化检查；不含产品源码。`RULES_ONLY_PUBLICATION`不代表生产已加载、真实用户任务验收或产品功能完成。下段 PR #25 主体登记源码已按源码口径发布。

当前发布包含主体登记种子的产品源码：`scripts/import_subject_registry_seed.py`（默认 dry-run；`--apply` 经既有 PermissionGate 的 CONFIG_MODIFY 精确审批（研发阶段由开发代理直接授予并留回执，见 2026-10-13 PO 规则 4），且只经既有 `subject_registry.add_subject` 幂等写入）与已在线核实的种子 `scripts/data_candidates/subject_registry_seed_20261013.jsonl`（610条，清单固定sha256），并登记全球数据源研究现行版；场内 TENANT_OF 关系仍为候选、未写入。`PUBLISHED_SOURCE_VERIFIED`不代表生产已加载、种子已写入生产库、真实用户任务验收或产品功能完成。此前 AGENTS.md 重复叙述精简（PR #26）与 T04 历史禁止项锚点（PR #24）按规则型发布，第7节复用诊断源码已由 PR #23 按源码口径发布；结果以实际Git对象和Actions核实，不在文档中冻结“当前main”的SHA。

本轮在现有规则型提交的精确文件白名单内，原位降级四份存活旧执行语义：历史 ADR、两份内容制作母指令与 AI 编程旧基线，均只保留归档研究身份；有效 J6/C4 的 Daily/Weekly/Monthly 播客选题与可编辑成品要求已在现有 Owner 保留。此项来源清理不等于开发、运行或产品验收完成。

2026-10-13 REA 媒体/办公接入（PO 授权逐段合并）：把 `D:/REA-Review/2026-10-11/product-patch` 的12个文件补丁在当前 main 上逐段接入原 Owner——C4/C6 `shared_artifacts.py`/`experience_runtime.py` 与 SH-01 正常制作不再要求 demo 勾选（旧参数仅可选兼容，`rights=unknown` 不升级）；C5 `lumenis/shared/reporting/saved_work.py` 增加 DOCX/XLSX/PPTX 精确 OOXML 校验与回读；F `app/lib/features/shared/sh01` 视频/播客共用 Timeline。FFmpeg 继续由 `LUMENIS_FFMPEG_PATH`/`LUMENIS_FFPROBE_PATH` 配置，不硬编码研究目录；REA 适配 wheel 未作为产品依赖。运行加载与真实用户验收仍为 NOT_VERIFIED。

2026-10-13 广州太古汇场内分布入库（PO 批准 PO-20261013-TKH-DIRECTORY-INGEST，原话：“这个表格是最新的，最准的，直接入库，然后数据源闭环，闭环前这些数据就ok，以后就只是新增主体，官网没更新”）：新增来源类别 `PO_PROVIDED_AUTHORITATIVE`，PO 提供的文件以 sha256 固定、以 `po-provided://` URI 标识、清单记录批准号；经既有采集持久化 Owner 写一条来源笔记、既有 Evidence Owner 签名、`persist_existing_note_scope` 绑定精确 CTH 场所范围后，才由 `record_venue_tenant_claim` 写 TENANT_OF（一律 UNREVIEWED）。`scripts/import_tkh_directory_relations.py` 与 `scripts/import_subject_registry_seed.py --seed tkh`（137个新 BMP 品牌）均默认 dry-run，`--apply` 须经 PermissionGate 精确人工审批；种子导入新增同名异体保护（英文或中文单边同名即暂缓，不建近似重复）。文华东方（MOH）铺位及酒店餐饮/水疗不属商场铺位，不写入。顺带修复 `persist_social_note` 25列/24占位符缺陷。闭环前数据源规则：闭环前数据源 = PR #25 的610条主体种子 + 本场内分布；闭环后只做新增主体，不替换既有基线。生产库写入与用户验收另行取证。

运行与结果：RUNTIME、DATABASE、USER OUTCOME均须独立取证。未取得本轮证据时标记NOT_VERIFIED，不复制旧进程、端口、账号状态、测试数、模型状态或历史PASS。

## 2. 唯一有效入口 — CURRENT CONFIGURATION / TOOLCHAIN CONVERGENCE

| 事项 | 原有权威位置 |
|---|---|
| 仓库执行路由 | `AGENTS.md` |
| 产品原则 | [The Product Owner's lightweight AI-native constitution](AI-NATIVE-PRODUCT-CONSTITUTION.md) |
| 配置示例 | `.env.example` is documentation only；不以示例覆盖实例私有配置。 |
| Flutter工具链 | `app/toolchain.json`与已有依赖锁文件为实际构建输入，不在接续文档复制版本常量。 |
| C2实例配置 | local private C2 runtime specification 保持实例私有，加载/权利/权限依据实际读取，不能由文档推定已部署。 |
| 机器治理语义 | `00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json` |
| 产品范围与五轮交付 | `00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` |
| 用户体验与四表面 | `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` |
| 完整源码职责和R/J/U要求 | `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` |
| 真实成果与退出条件 | `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md` |
| 主体、范围、来源和数据成熟度 | `00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md` |
| 来源返回合同 | `contracts/experience/source-target-contract-v1.json` |
| 跨仓约定 | `00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md`、`00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json` |
| 任务与协作索引 | 本仓库Issue #17及其原任务/PR，不构成第二套产品规则 |

跨仓机器合同固定协议指纹：`68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f`。协议版本标识不同于实时产品版本。

当前明确PO要求确定目标与授权，源码/运行证据说明已经实现和证明了什么；不能用缺少实现取消需求。规则冲突在原权威位置修正，不把冲突双方一起复制到本文件。

## 3. Current owner continuation

以下是职责与未闭验收，不是窗口开停、模型配置或执行中的状态表。具体目标以Source Owner Index的原完整成果卡为准；需要执行时读取原任务的当前准入和最后有效回执。

| 原源码职责 | 完整工作与待核结果 |
|---|---|
| C1 / W1 | 主体/品牌/关系、原生采集、来源时间与字段、Source/Evidence/Canonical、持续供料和恢复；按真实任务范围、合法会话和原权限验证，不用来源数量代表覆盖。 |
| C2 / W2 | 当前Owned Gateway、Agent任务、上下文、取消/恢复、评价与受控学习；与C5完成cosine/BM25/融合/cross-encoder完整合同，训练、模型绑定、重载、语义质量和晋升各自验收。 |
| C3 / W3 | CTH/BMP完整问题驱动分析与业务对象、可用判断、获准动作及真实结果；基础业务无AI运行，来源/预算变化、保存、修订、重开和恢复必须连续。 |
| C4 / W4 | 独立提案/文稿、视频、播客的完整编辑与交付；保留用户原稿、原素材、方法、项目版本、实际媒体输出、回读、视听检查和恢复，计划不替代成品。 |
| C5 / W5 | 资料原件、检索、引用、SavedWork、报告/导出、版本、通知与Shared独立工作空间；现行来源用途和对象权限贯穿所有入口，复用已有底座。 |
| C6 / W6 | 同版本集成、Core与依赖、运行身份、数据库迁移/恢复、打包、各端真实操作与发布；保护其他候选，分清Change、Owner Closure和Release。 |
| F | 官网、Web、Windows/macOS与iOS按各自角色并行建设、独立验收；完整任务交互、三语、无障碍、原研究采用和真实成果接续，不以页面数或视觉草图结项。 |
| M | 当前授权范围内的跨Owner协调、源码判断、整合与最终工程验收；不凭本文件自动启动/暂停其他Agent，不重建用户管理的原生Goal。 |

## 4. 必须带入接续的完整要求

- 产品按SYSTEM、CTH、BMP、Shared、Agent Groups/自研AI五轮组织完整交付。工程职责不是额外轮次；当前任务依赖不得推给后轮。独立Shared研究、文稿/提案、视频和播客不要求先建立CTH/BMP主体、任务或SourceBrief。
- 四表面依角色并行，不让一端未完成暂停其他端独立工作。Windows/macOS和iOS是原生目标；Linux服务、CI与浏览器工作不因原生目标而受限。44份屏幕规范是能力覆盖，不是页面上限。
- AI横向增强既有领域，保留聊天；基础业务、确定性分析、人工创作、保存和恢复不依赖模型/API/GPU。数学方法在原后端Owner适用执行，普通用户输入真实问题与约束，不被要求组装内部算法或ID。
- Hybrid要求保留余弦向量召回、BM25、融合及真实cross-encoder重排。配置或论文记录不能证明已接通；精确模型、数据、权利、资源和授权按现有合同核验。
- 彩绘用于图标及适合的局部元素，整体空间、层级、动效与交互按原批准研究和真实任务设计；不把全产品收窄为二维水彩/纸感，也不统一为3D或卡片模板。研究原件、逐帧/页面范围、采用结论与对应实现不得遗漏。
- 数据按主体/品牌/任务和明确时间窗处理，各来源类别等权不等于每条证据同可信。原生时间、正文、封面、作者、链接、缺失和真实零值分别保留；来源引用不替代事实验证或行动授权。
- 平台账号、来源用途和训练/发布权利按原授权逐项核实。不得因为开发、审计或资料共享授权就自动开展账号操作、采集、模型调用、训练、付费、生产写入或部署。
- 所有R01–R15、J1–J8、U01–U25及未撤回的研究/素材采用要求留在原Owner合同，移除旧规则文件不撤销其中仍有效的用户能力要求。历史证据通过原证据和Git历史追溯，不重新成为执行正文。

## 5. 版本与保护边界

操作前记录当前时间、实际项目根、本地HEAD、分支、origin/main、独立GitHub main、divergence和dirty。分别使用`git rev-parse HEAD`、`git rev-parse origin/main`和`git rev-list --left-right --count HEAD...origin/main`核对本地提交、已获取远端引用及分歧，并区分其与本地未提交候选、运行进程身份。不得以固定旧SHA、旧窗口状态或已有截图代替本轮取证。

在原分支/任务中保留已完成成果、失败、未完步骤和精确输入版本。共享候选只证明他方可见；未提交代码与仅本机研究不等于不存在。按原资料权限提供必要内容，不整包公开Cookie、密钥、生产数据库或私人会话。

受保护流程为开发分支、针对性验证、独立实质审阅、必需CI、PR合并和合并版读回。GitHub同账号下不同工具的署名评论可以记录真实交叉审阅，但不能冒充两个审批身份。测试/CI通过不代替真实用户结果或整个产品闭环。

## 6. 本次完成边界

本次已核规则删除及原入口修复，必须通过原治理门、退役文件重现拒绝回归、当前Shared目录引用和线上线下字节/删除状态核对。旧工作树、仓库外规则副本、活跃会话注入与应用端缓存尚未独立核实前，不能由这批根目录清理宣称整个研发环境全部清空。

不创建旧规则备份目录或替代权威文件，不自动删除承载独有未提交代码、研究材料或活跃进程的工作树。先判断独有内容和消费者，再清理对应旧规则入口；不以加“历史”标签冒充已移除。

## 7. 独立复用接入

- 抖音响应结构诊断与可选静态DLL导入观察：源码来自 `codex/reuse-diagnostics-20261013`（`72db140a`），经 PR #23 发布，按用户直接批准的复用ZIP有界接入，不从ZIP重新覆盖；原生指标、风控失败、来源和权限语义保留，无新增采集器、数据真相、模型或运行依赖；值隔离，失败恢复沿原适配器合同。
- 现有证据为隔离工程回归（本地82项、隔离main候选59项适配器回归、各5+5项构建辅助回归），不是实际采集、新版本App构建、加载运行或真实用户验收；这些仍须各自核验。精确输入、哈希、失败恢复与未闭项见 [本批原位证据](evidence/round-15/REUSE-DIAGNOSTICS-20261013.md)。
