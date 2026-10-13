# 序境 · LUMENIS

商业运营、品牌市场、独立研究与内容制作的一体化工作平台。
An integrated workspace for commerce operations, brand and market work, independent research, and content production.

[产品蓝图 / Product blueprint](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md) · [体验规范 / Experience](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md) · [开发规则 / Contributing rules](AGENTS.md)

## 产品定位 / Product purpose

序境将真实资料、分析、业务判断和可编辑成果连接起来。CTH 与 BMP 是两个业务领域；共享能力中的研究、提案、视频和播客可以独立使用，也可以与业务工作联动。SYSTEM 提供共同的采集、浏览器、权限、数据、调度和恢复基础。

LUMENIS connects real materials, analysis, business decisions, and editable deliverables. CTH and BMP are business domains. Shared research, proposals, video, and podcasts can be used independently or connected to business work. SYSTEM provides acquisition, browsing, permissions, data, scheduling, and recovery.

CTH 围绕商业主体工作，BMP 围绕品牌与市场工作，Shared Capability 提供独立、可复用的研究与制作能力。
CTH is Subject-first, BMP is Brand/Market-first, and Shared Capability provides independent, reusable research and production.

产品交付按五轮推进：SYSTEM → CTH → BMP → Shared → Agent Groups / 自研 AI。这是研发与验收顺序，不是用户必须经过的流程。

Product delivery proceeds in five rounds: SYSTEM → CTH → BMP → Shared → Agent Groups / owned AI. This is the build and acceptance order, not a path users must follow.

AI 贯穿适用的工作环节，辅助理解、分析、建议和创作；正常业务、确定性分析、人工编辑、保存与恢复不以模型、外部 AI API 或 GPU 为前提。原始事实、计算结果、AI 建议与人工决定分别保留出处。

AI assists understanding, analysis, recommendations, and creation across applicable workflows. Ordinary business operations, deterministic analysis, manual editing, saving, and recovery do not require a model, external AI API, or GPU. Source facts, computed results, AI suggestions, and human decisions retain distinct provenance.

产品 AI 只经过唯一的 SYSTEM AI Gateway 调用序境自有模型；已退役的外部或本地模型路线不调用、不探测、不作回退。模型不可用时如实显示不可用，基础功能照常工作。

Product AI runs only through the single SYSTEM AI Gateway to LUMENIS-owned models. Retired external or local model routes are never called, probed, or used as fallback. When no model is available the product says so, and basic functions continue to work.

## 用户如何工作 / User workflows

| 工作 / Work | 操作与成果 / Actions and outcomes |
| --- | --- |
| CTH · 商业运营 / Commerce operations | 围绕商业主体查看监测、事件、消费者反馈与风险，形成有依据的判断、行动和结果报告。 / Monitor a commercial subject, inspect events, consumer feedback and risks, and develop supported decisions, actions, and outcome reports. |
| BMP · 品牌市场 / Brand and market | 研究品牌、市场、竞品、创作者和传播，制定及评价 Campaign。 / Research brands, markets, competitors, creators, and communications; plan and evaluate campaigns. |
| 独立研究 / Independent research | 导入、查找、阅读、比较和引用资料，保存研究笔记、简报与报告。 / Import, find, read, compare, and cite materials; save research notes, briefs, and reports. |
| 提案与文稿 / Proposals and documents | 从空白、创作要求或已有资料开始，编写、编辑、审阅和导出。 / Start from a blank document, creative brief, or existing material; write, edit, review, and export. |
| 视频 / Video | 导入素材、编排与剪辑、调整声音和字幕、预览及渲染，保存成片与可编辑工程。 / Import and arrange media, edit clips, sound and captions, preview and render, and retain both the output and editable project. |
| 播客 / Podcasts | 编写脚本、导入或录制音频、剪辑混音、管理章节与转写、试听及导出。 / Write scripts, import or record audio, edit and mix, manage chapters and transcripts, listen, and export. |
| 内置浏览器 / In-product browser | 查看原帖和网页、进行获准操作，并返回原任务；人工接管必须明确发起。 / Inspect sources and webpages, perform permitted actions, and return to the original task; human takeover is explicit. |

独立研究与制作不要求先创建 CTH/BMP 任务、商业主体、品牌聚焦或业务研究报告。跨能力联动由用户选择，并传递所选来源、权限、约束和版本。产品内浏览器的范围为网页工作，不包含通用操作系统或任意桌面应用控制。

Independent research and production do not require a prior CTH/BMP task, commercial subject, brand focus, or business research report. Optional connections preserve the chosen sources, permissions, constraints, and versions. In-product browsing covers web work, not general operating-system or desktop-application control.

## 数据与成果原则 / Data and deliverable principles

- **真实来源 / Real sources：** 所有平台与公开网页的来源类别基础权重相同，贯穿采集、分析、研究与成果使用；具体质量、时效、身份和使用权分别判断。 / All platforms and public webpages receive equal source-category weight throughout acquisition, analysis, research, and deliverable use; quality, freshness, identity, and usage rights are evaluated individually.
- **清楚呈现 / Clear presentation：** 资料保留原文、封面、作者、链接、原生时间和真实指标；缺失显示“—”，不填假零值。阅读、结果与操作采用序境自己的视觉语言，不改写原始证据或网页。 / Materials retain source content, covers, authors, links, native timestamps, and observed metrics. Missing values are shown as “—”, never fabricated zeros. Product readers, results, and controls follow LUMENIS’s visual language without altering original evidence or webpages.
- **结果优先 / Results first：** 用户提出工作问题和业务约束，后台处理适用分析，报告呈现结论、依据、限制及下一步。 / Users provide the question and practical constraints; backend analysis produces conclusions, evidence, limitations, and next actions.
- **版本连续 / Version continuity：** 成果支持保存、局部修订、重开与恢复；旧版和修改原因保留。 / Work supports saving, local revision, reopening, and recovery, with prior versions and reasons retained.
- **主体与范围 / Subjects and scope：** 默认范围为 GLOBAL / ALL。用户可以搜索、新增、聚焦和清除商业主体与品牌；聚焦只缩小范围，不授予权限，也不启动采集。品牌名称以品牌官网的正式名称为准，并记录来源。 / The default scope is GLOBAL / ALL. Users can search, add, focus, and clear commercial subjects and brands; focus only narrows scope and neither grants permission nor starts collection. Brand names follow each brand's official website and record the source.
- **持续采集 / Continuous acquisition：** SYSTEM Collector 按话题和任务语义，为全部已登记主体持续采集。当前主要平台为 Instagram、Facebook、微信公众号、小红书、抖音和 X，不设统一历史起点。采集在后台运行，不弹出窗口。平台登录失效时，在产品内打开统一的恢复面板（扫码、受控登录或验证），恢复后续跑原任务，不自动打开外部浏览器。单个平台不可用不影响其他平台。 / The SYSTEM Collector continuously acquires sources for all registered subjects by topic and task semantics. The primary platforms are Instagram, Facebook, WeChat Official Accounts, RedNote/XHS, Douyin, and X, with no universal start date. Collection runs in the background without pop-up windows. When a platform session expires, one in-product recovery sheet (QR, controlled login, or verification) restores it and resumes the original task; no external browser opens automatically. One unavailable platform does not stop the others.
- **权限明确 / Explicit permissions：** 浏览、引用、制作、导出、发布及模型训练遵循各自适用的授权。 / Browsing, citation, production, export, publication, and training follow their respective permissions.

## 产品表面 / Product surfaces

| 表面 / Surface | 用途 / Purpose |
| --- | --- |
| Public Website | 产品介绍、使用说明、帮助与工作区入口。 / Product information, guidance, help, and workspace entry. |
| Web Workspace | 浏览器中的业务、研究与制作工作区。 / Browser-based business, research, and production workspace. |
| Desktop · Windows / macOS | 原生桌面工作区。 / Native desktop workspace. |
| Mobile Companion · iOS | 移动查阅、审阅与工作接续。 / Mobile reading, review, and work continuation. |

四类表面按各自角色并行建设、独立验收，共用同一 Product Core、权限、资料和成果版本。Workspace、Windows/macOS与iOS复用同一Flutter实现；语言、视觉与无障碍归唯一体验规范。README不派工，也不把单端通过算成全产品完成。

Build the four surfaces in parallel and accept each independently over one Product Core, permissions, materials and result versions. Workspace, Windows/macOS and iOS reuse one Flutter implementation. Language, visual and accessibility requirements belong to the sole Experience Constitution; this README neither dispatches work nor treats one surface as full-product acceptance.

## 工程结构 / Repository structure

| 路径 / Path | 职责 / Responsibility |
| --- | --- |
| [`app/`](app/) | Flutter Web、Windows/macOS 与 iOS 客户端。 / Flutter Web, Windows/macOS, and iOS clients. |
| [`website/`](website/) | Astro 官网。 / Astro public website. |
| [`lumenis/`](lumenis/) | 业务、共享能力和 SYSTEM 实现。 / Business, Shared, and SYSTEM implementation. |
| [`contracts/`](contracts/) | 接口、体验与能力合同。 / Interface, experience, and capability contracts. |
| [`scripts/`](scripts/) | 运行、维护、构建和验证工具。 / Runtime, maintenance, build, and verification tools. |
| [`tests/`](tests/) | 工程回归与历史验证记录。 / Engineering regressions and retained verification records. |
| [`config/`](config/) | 运行配置、配额与种子。 / Runtime configuration, quotas, and seeds. |
| `data/` | 本地运行数据；唯一业务库 `data/monitor.db`，不提交到 Git。 / Local runtime data; the single business database `data/monitor.db` is never committed. |
| [`intelligence_library/`](intelligence_library/) | 研究与学习资料（出处材料，不作执行规则）。 / Research and learning materials (provenance, not execution rules). |
| [`00-GOVERNANCE/`](00-GOVERNANCE/) | 产品蓝图、Owner、体验、安全和验收要求。 / Product blueprint, ownership, experience, security, and acceptance requirements. |

CTH/BMP 负责各自业务规则；Shared 提供独立和复用能力；SYSTEM 提供共同运行边界。前端消费真实合同，不另建业务、数据或权限系统。

CTH/BMP own their business rules, Shared provides independent and reusable capabilities, and SYSTEM supplies common runtime boundaries. Frontends consume these contracts without introducing parallel business, data, or permission systems.

## 本地开发 / Local development

开发阅读顺序 / Contributor reading order:

```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ 00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md
→ 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
→ 00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md
→ 00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md
→ 00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md
→ 对应能力合同与源码 / Relevant capability contracts and source
```

`LUMENIS-CODEX-TAKEOVER-CURRENT.md` 是所有开发者唯一的闭环接续入口。流程为：规则 → CURRENT → 工作分支 → 测试 → PR → 必需检查全绿 → 合并 → 本地主路径与 `origin/main` 一致。只使用一个本地主路径，不另建 worktree 或副本。

`LUMENIS-CODEX-TAKEOVER-CURRENT.md` is the single closed-loop entry for every contributor: rules → CURRENT → work branch → tests → PR → all required checks green → merge → local main path aligned with `origin/main`. Use one local main path; do not create extra worktrees or copies.

首先阅读 [`AGENTS.md`](AGENTS.md)、对应源码 Owner 和能力合同；核对已有实现与调用关系，复用正确能力、修复冲突，只为确认的缺口补实现。所需 Python 依赖以仓库的 `requirements*.txt` 为准；Flutter/Dart 版本以 [`app/toolchain.json`](app/toolchain.json) 为准；官网使用 [`website/package.json`](website/package.json) 与锁文件。不要为阅读本说明而自动安装、升级或启动服务。

Read [`AGENTS.md`](AGENTS.md), the relevant source owner, and capability contracts. Inspect existing implementations and callers, reuse correct behavior, resolve conflicts, and add implementation only for verified gaps. Use the repository's `requirements*.txt` for Python dependencies, [`app/toolchain.json`](app/toolchain.json) for Flutter/Dart, and [`website/package.json`](website/package.json) with its lockfile for the website. Reading this guide does not trigger installation, upgrades, or service startup.

在仓库根目录核对本地修改和版本： / Inspect revisions and local changes from the repository root:

```powershell
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
```

获准启动本机 Core 时使用既有入口；不要重复启动已在运行的实例： / When local Core startup is authorized, use the existing entry point without duplicating a running instance:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_production.ps1
```

该入口幂等启动本机 Core（端口 8201）及其后台采集与浏览器常驻进程。Core 默认地址为 `http://127.0.0.1:8201`，健康检查路径为 `/healthz`，工作区路径为 `/workspace`。客户端与官网的构建配置见各自目录说明。采集、训练、部署及生产数据操作各自需要适用授权。

The entry point idempotently starts the local Core on port 8201 together with its background collector and browser residents. Core listens on `http://127.0.0.1:8201` and exposes `/healthz` for health checks and `/workspace` for the workspace. Refer to each package's guide for client and website build configuration. Collection, training, deployment, and production-data operations require their applicable authorization.

## 贡献与验证 / Contributing and verification

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。
Coding agents must read the repository execution rules before making changes.

源仓库 / Source repository: [`Zachary-1012/LUMENIS-codex-Clean-OS`](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS).

使用有界工作分支与 PR 合入 `main`，必需检查全部通过即可正常合并，不绕过检查。保留其他人的未提交修改，逐项暂存本次文件；不要强推、批量覆盖或删除历史证据。依变更范围进行适用的编译、静态、安全和隔离回归验证，并通过真实用户操作验证成果与恢复。

Use scoped branches and pull requests into `main`; merge normally once all required checks pass, without bypassing them. Preserve unrelated uncommitted work, stage exact paths, and avoid force pushes, broad overwrites, or deletion of historical evidence. Run applicable build, static, security, and isolated regression checks, and verify results and recovery through actual user operations.

产品定义、实现和验收是不同记录。动态进度、提交与运行取证统一见 [CURRENT 接续记录](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md) 和 [真实交付要求](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)；不把快照复制到 README。

Product definition, implementation, and acceptance are separate records. Dated progress, revision, and runtime observations belong in the [CURRENT handoff](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md) and [real delivery requirements](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md), rather than being copied into this README.

## 安全与许可 / Security and license

遵循 [安全边界](00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md)。凭据、Cookie、私人会话、生产数据库和受限原始材料不得提交到仓库或发送给未获准的服务。

Follow the [security boundary](00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md). Do not commit credentials, cookies, private sessions, production databases, or restricted raw materials, or send them to unapproved services.

仓库源码采用 [Apache License 2.0](LICENSE)。第三方软件、数据、模型、字体和媒体保留其各自许可与使用限制。

Repository source is licensed under [Apache License 2.0](LICENSE). Third-party software, data, models, fonts, and media retain their own licenses and usage restrictions.
