# 寰意 · OEVIRA

Repository / 唯一仓库：[Zachary-1012/LUMENIS-codex-Clean-OS](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS)。

Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。

**An Open Space for Thought and Creation.**

围绕商业运营、品牌市场与原创创作，完成从真实问题到可用成果的工作。
A workspace for commerce operations, brand and market work, and original creation—from real questions to usable results.

[产品蓝图 / Product blueprint](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md) · [完整产品规划 / Full product plan](00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md) · [全产品草图 / Full-product sketches](00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md) · [体验规范 / Experience](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md) · [开发入口 / Contribution entry](CONTRIBUTING.md)

## 产品定位 / Product purpose

从使用者出发：为品牌方、商业运营者和代理机构连接可靠资料、判断、可修改成果与实际复盘；也支持个人研究关注的品牌、商业空间和公司。任务内研究、一份文稿、一段影像或一期播客都可从想法开始，不以先完成商业分析为前提。完整品牌陈述见[现行定位](00-GOVERNANCE/PRODUCT-POSITIONING-CURRENT.md)。

寰意将真实资料、分析、业务判断和可编辑成果连接起来。研究、文档和报告服务当前任务；原创创作、视频及播客后期可以直接开始，无需先建立业务任务。SYSTEM提供共同的采集、浏览器、权限、数据和恢复基础。

OEVIRA connects real materials, analysis, business decisions, and editable results. Research, documents, and reports support the current task. Original creation and video or podcast post-production can start directly without a prior business task. SYSTEM supplies shared acquisition, browsing, permissions, data, and recovery.

CTH · 商业运营围绕经营主体，BMP · 品牌市场围绕品牌与市场；Shared在同一工作中提供研究、原创创作、文档交付及视频/播客后期。主体目录面向在中国境内经营的商业主体与品牌，可添加、移除和重新添加。

CTH is Subject-first commerce operations; BMP is Brand/Market-first. Shared Capability provides research, original creation, document delivery, and video/podcast post-production within that work. The directory covers commercial entities and brands operating in China, with add, remove, and re-add controls.

产品交付按五轮推进：SYSTEM → CTH → BMP → Shared → Agent Groups / 自研 AI。这是研发与验收顺序，不是用户必须经过的流程。

Product delivery proceeds in five rounds: SYSTEM → CTH → BMP → Shared → Agent Groups / owned AI. This is the build and acceptance order, not a path users must follow.

AI 贯穿适用的工作环节，辅助理解、分析、建议和创作；正常业务、确定性分析、人工编辑、保存与恢复不以模型、外部 AI API 或 GPU 为前提。原始事实、计算结果、AI 建议与人工决定分别保留出处。

AI assists understanding, analysis, recommendations, and creation across applicable workflows. Ordinary business operations, deterministic analysis, manual editing, saving, and recovery do not require a model, external AI API, or GPU. Source facts, computed results, AI suggestions, and human decisions retain distinct provenance.

产品 AI 经唯一的 SYSTEM AI Gateway 调用。寰意行业AI通过获准预训练模型、行业知识、专业工具与受控学习提供完整能力，不以GPU训练为前提；Groq 是产品内置的外部连接，用户也可自带其他供应商 API，经同一 Gateway 的相应协议适配、安全目的地校验、明确选择及适用 Permission/SourceUse 使用。配置不等于可用或外发授权；旧退役路线不恢复、不探测，不自动切换或回退。AI 不可用时，只有依赖 AI 的增强动作不可用；正常业务、确定性分析、人工编辑、保存与恢复继续工作。

Product AI uses the single SYSTEM AI Gateway. OEVIRA combines approved pretrained inference, industry knowledge, professional tools, and controlled learning without requiring GPU training. Groq is the product-provided external connection; users may also bring other providers’ API credentials through supported adapters, validated destinations, explicit selection and applicable Permission/SourceUse in the same Gateway. Configuration proves neither availability nor permission to transmit. Retired routes are not revived or probed, and no automatic switching or fallback occurs. If AI is unavailable, ordinary business work, deterministic analysis, manual editing, saving and recovery continue.

## 用户如何工作 / User workflows

| 工作 / Work | 操作与成果 / Actions and outcomes |
| --- | --- |
| 工作区首页与聊天 / Workspace home and chat | 打开工作区即进入聊天/任务入口；可在同一入口提交多个彼此隔离的任务，长任务异步执行并把结果送回对应任务，不展示内部推理过程。侧边导航可进入 CTH、BMP、Shared 创作、视频/播客、内置浏览器和 SYSTEM。 / Open the workspace directly to its chat/task entry. Submit multiple isolated tasks through one entry; long tasks run asynchronously and return results to their task without exposing internal reasoning. Navigation opens CTH, BMP, original creation, video/podcasts, the in-product browser, and SYSTEM. |
| CTH · 商业运营 / Commerce operations | 围绕商业主体查看监测、事件、消费者反馈与风险，形成有依据的判断、行动和结果报告。 / Monitor a commercial subject, inspect events, consumer feedback and risks, and develop supported decisions, actions, and outcome reports. |
| BMP · 品牌市场 / Brand and market | 研究品牌、市场、竞品、创作者和传播，制定及评价 Campaign。 / Research brands, markets, competitors, creators, and communications; plan and evaluate campaigns. |
| 资料与依据 / Materials and evidence | 在当前工作附入资料，直接得到有依据的结果；需要时打开原文、引用和分析，资料卡可查找和重开。研究不另设必经工作区。 / Attach materials to the current task and receive grounded results. Open originals, citations, and analysis when needed; find and reopen material cards without a separate research workflow. |
| 提案与文稿 / Proposals and documents | 从空白、创作要求或已有资料开始，编写、编辑、审阅和导出。 / Start from a blank document, creative brief, or existing material; write, edit, review, and export. |
| 视频 / Video | 导入素材、编排与剪辑、调整声音和字幕、预览及渲染，保存成片与可编辑工程。 / Import and arrange media, edit clips, sound and captions, preview and render, and retain both the output and editable project. |
| 播客 / Podcasts | 编写脚本、导入或录制音频、剪辑混音、管理章节与转写、试听及导出。 / Write scripts, import or record audio, edit and mix, manage chapters and transcripts, listen, and export. |
| 内置浏览器 / In-product browser | 查看原帖和网页、进行获准操作，并返回原任务；人工接管必须明确发起。 / Inspect sources and webpages, perform permitted actions, and return to the original task; human takeover is explicit. |

说明目标，附入必要材料，系统完成适用的检索、研究、分析或创作；直接查看结果，按需局部修改和导出。视频和播客后期保留专业精细编辑。基础工作不依赖AI，模型专属能力有其实际可用性和权限边界。

Describe the goal and attach necessary inputs. The product performs applicable retrieval, research, analysis, or creation and presents the result for focused revision or export. Video and podcast post-production retain detailed editing. Basic work remains usable without AI; model-specific actions retain availability and permission boundaries.

## 数据与成果原则 / Data and deliverable principles

- **真实来源 / Real sources：** 所有平台与公开网页的来源类别基础权重相同，贯穿采集、分析、研究与成果使用；具体质量、时效、身份和使用权分别判断。 / All platforms and public webpages receive equal source-category weight throughout acquisition, analysis, research, and deliverable use; quality, freshness, identity, and usage rights are evaluated individually.
- **清楚呈现 / Clear presentation：** 资料保留原文、封面、作者、链接、原生时间和真实指标；缺失显示“—”，不填假零值。阅读、结果与操作采用寰意自己的视觉语言，不改写原始证据或网页。 / Materials retain source content, covers, authors, links, native timestamps, and observed metrics. Missing values are shown as “—”, never fabricated zeros. Product readers, results, and controls follow OEVIRA’s visual language without altering original evidence or webpages.
- **结果优先 / Results first：** 用户提出工作问题和业务约束，后台处理适用分析，报告呈现结论、依据、限制及下一步。 / Users provide the question and practical constraints; backend analysis produces conclusions, evidence, limitations, and next actions.
- **版本连续 / Version continuity：** 成果支持保存、局部修订、重开与恢复；旧版和修改原因保留。 / Work supports saving, local revision, reopening, and recovery, with prior versions and reasons retained.
- **主体与范围 / Subjects and scope：** 默认范围为 GLOBAL / ALL。用户可以搜索、新增、聚焦和清除商业主体与品牌；聚焦只缩小范围，不授予权限，也不启动采集。品牌名称以品牌官网的正式名称为准，并记录来源。 / The default scope is GLOBAL / ALL. Users can search, add, focus, and clear commercial subjects and brands; focus only narrows scope and neither grants permission nor starts collection. Brand names follow each brand's official website and record the source.
- **按需采集 / On-demand acquisition：** SYSTEM Collector 由用户刷新或当前浏览器上下文任务触发，定时采集需用户明确选择；按话题和任务语义、权限、身份与来源边界对主体执行采集；仅登记主体不授予采集权限，也不自动启动采集。当前主要平台为 Instagram、Facebook、微信公众号、小红书、抖音和 X，不设统一历史起点。采集在后台运行，不弹出窗口。平台登录失效时，在产品内打开统一的恢复面板（扫码、受控登录或验证），恢复后续跑原任务，不自动打开外部浏览器。单个平台不可用不影响其他平台。 / The SYSTEM Collector acquires sources when a user refreshes or requests current browser context; scheduled acquisition requires explicit opt-in. Topic and task semantics retain the applicable permission, identity, and source boundaries. Registration alone grants no collection permission and does not start acquisition. The primary platforms are Instagram, Facebook, WeChat Official Accounts, RedNote/XHS, Douyin, and X, with no universal start date. Collection runs in the background without pop-up windows. When a platform session expires, one in-product recovery sheet (QR, controlled login, or verification) restores it and resumes the original task; no external browser opens automatically. One unavailable platform does not stop the others.
- **权限明确 / Explicit permissions：** 浏览、引用、制作、导出、发布及模型训练遵循各自适用的授权。 / Browsing, citation, production, export, publication, and training follow their respective permissions.

## 产品表面 / Product surfaces

| 表面 / Surface | 用途 / Purpose |
| --- | --- |
| Public Website | 产品、场景、制作好的演示、帮助及产品/下载链接；不提供在线功能体验。 / Product and scenario presentation, prepared demonstrations, help, and product/download links; no embedded product trial. |
| Web Workspace | 浏览器中的业务、研究与制作工作区。 / Browser-based business, research, and production workspace. |
| Desktop · Windows / macOS | 原生桌面工作区。 / Native desktop workspace. |
| Mobile Companion · iOS | 移动查阅、审阅与工作接续。 / Mobile reading, review, and work continuation. |

四类表面按各自角色独立验收，实际开工端由当前PO指令决定，共用同一 Product Core、权限、资料和成果版本。Workspace、Windows/macOS与iOS复用同一Flutter实现；语言、视觉与无障碍归唯一体验规范。README不派工，也不把单端通过算成全产品完成。

Accept each surface independently, following the current PO instruction for execution order over one Product Core, permissions, materials and result versions. Workspace, Windows/macOS and iOS reuse one Flutter implementation. Language, visual and accessibility requirements belong to the sole Experience Constitution; this README neither dispatches work nor treats one surface as full-product acceptance.


产品采用像素赛博＋植物生态＋复古未来主义视觉，满天星Logo与五植物角色沿现行体验规范统一；保留任务专属布局、原创图标、可选动效和三语无障碍。
The pixel-cyber, botanical-ecology and retro-futurist visual language uses a Gypsophila logo and five botanical characters, with task-specific layouts, original icons, selectable motion and accessible Chinese/English/Korean operation.

## 工程结构 / Repository structure

| 路径 / Path | 用途与唯一入口 / Purpose and entry |
| --- | --- |
| [`AGENTS.md`](AGENTS.md)、[`00-GOVERNANCE/`](00-GOVERNANCE/) | AGENTS 是仓库开发路由；当前产品与工程权威按其中的读取路径查找。 / AGENTS is the repository development router; follow its reading route for current product and engineering authorities. |
| [`lumenis/`](lumenis/) 与既有根级 Python 模块/包 | 后端 Owner 源码与既有调用接口；具体文件位置以[源码 Owner Index §3](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md#3-fixed-source-lookup-map)为准，不为统一目录外观整体迁移。 / Backend owner source and existing caller interfaces; use [Source Owner Index §3](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md#3-fixed-source-lookup-map) for exact paths, without wholesale moves for a uniform layout. |
| [`app/`](app/) | Flutter 应用及平台工程；开发说明见 [`app/README.md`](app/README.md)。 / Flutter application and platform projects; see [`app/README.md`](app/README.md). |
| [`website/`](website/) | Astro Public Website 工程；开发说明见 [`website/README.md`](website/README.md)。 / Astro Public Website project; see [`website/README.md`](website/README.md). |
| [`contracts/`](contracts/) | 产品接口、数据与 Experience 合同；能力源路径仍以 Owner Index §3 为准。 / Product interface, data, and Experience contracts; the Owner Index §3 remains the source for implementation paths. |
| [`scripts/`](scripts/) | 现有工程与运行工具；说明见 [`scripts/README.md`](scripts/README.md)。 / Existing engineering and runtime tools; see [`scripts/README.md`](scripts/README.md). |
| [`tests/`](tests/) 与 `app/test/` | Python 与 Flutter 工程回归；测试分类见 [`tests/CI_TEST_TIERS.md`](tests/CI_TEST_TIERS.md)。 / Python and Flutter engineering regressions; see [`tests/CI_TEST_TIERS.md`](tests/CI_TEST_TIERS.md) for test tiers. |
| [`docs/`](docs/)、[`research/`](research/)、[`intelligence_library/`](intelligence_library/) | 技术参考、研究原件与采用证据；活动规则和产品权威以 AGENTS 指向的现行文档为准。 / Technical references, research originals, and adoption evidence; active rules and product authorities are the current documents routed by AGENTS. |
| [`config/`](config/)、[`alembic/`](alembic/)、[`migrations/`](migrations/)、[`deployment/`](deployment/)、[`docker/`](docker/) | 配置、数据库迁移与运行包装；数据和权限 Owner 不随目录改变。 / Configuration, database migrations, and runtime packaging; directories do not change data or permission ownership. |
| `data/`, `work/`, `output/`, `tmp/` | 本地运行数据、受保护工作区与临时输出；按忽略与数据边界保管，不作为源码入口。 / Local runtime data, protected workspace, and temporary output; preserve their ignore and data boundaries, and do not treat them as source entry points. |
| [`vendor/`](vendor/) | 保留第三方代码及其许可/NOTICE；边界见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。 / Vendored third-party code and its licenses/notices; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). |
| [`.codex/`](.codex/) | 仓库受控的工程工具实现与工具接口说明，见 [`.codex/README.md`](.codex/README.md)；不替代 AGENTS 路由。 / Repository-controlled engineering tools and their interface guide; see [`.codex/README.md`](.codex/README.md). It does not replace the AGENTS router. |

CTH/BMP 负责各自业务规则；Shared 提供独立和复用能力；SYSTEM 提供共同运行边界。前端消费真实合同，不另建业务、数据或权限系统。

CTH/BMP own their business rules, Shared provides independent and reusable capabilities, and SYSTEM supplies common runtime boundaries. Frontends consume these contracts without introducing parallel business, data, or permission systems.

## 本地开发 / Local development

开发规则的唯一入口是 [`AGENTS.md`](AGENTS.md)，并沿该路由读取 [`LUMENIS-CODEX-TAKEOVER-CURRENT.md`](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)、[`AI-NATIVE-PRODUCT-CONSTITUTION.md`](00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md) 和 [`LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)。本 README 只提供这些现行权威的稳定导航，不复写规则正文、任务分派或开发流程；准确源码归属见[源码 Owner Index §3](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md#3-fixed-source-lookup-map)。

[`AGENTS.md`](AGENTS.md) is the sole development instruction entry; follow its route to [`LUMENIS-CODEX-TAKEOVER-CURRENT.md`](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md), [`AI-NATIVE-PRODUCT-CONSTITUTION.md`](00-GOVERNANCE/AI-NATIVE-PRODUCT-CONSTITUTION.md), and [`LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md). This README links to those current authorities without copying their rules, task routing, or development procedure. Use [Source Owner Index §3](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md#3-fixed-source-lookup-map) for exact source ownership.

仓库工程工具的稳定用法见 [`.codex/README.md`](.codex/README.md)；它只说明现有工具接口，不另设产品或任务规则。

For repository engineering tools, see [`.codex/README.md`](.codex/README.md). It documents existing tool interfaces without creating separate product or task rules.

包级开发命令与依赖清单统一从 GitHub 贡献入口 [`CONTRIBUTING.md`](CONTRIBUTING.md) 进入。

The GitHub contribution entry, [`CONTRIBUTING.md`](CONTRIBUTING.md), is the single navigation point for package-specific commands and dependency manifests.

## 安全与许可 / Security and license

遵循 [安全边界](00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md)。凭据、Cookie、私人会话、生产数据库和受限原始材料不得提交到仓库或发送给未获准的服务。

Follow the [security boundary](00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md). Do not commit credentials, cookies, private sessions, production databases, or restricted raw materials, or send them to unapproved services.

仓库源码采用 [Apache License 2.0](LICENSE)。第三方软件、数据、模型、字体和媒体保留其各自许可与使用限制。

Repository source is licensed under [Apache License 2.0](LICENSE). Third-party software, data, models, fonts, and media retain their own licenses and usage restrictions.

## 研究与业务采用 / Research and business use

用户可以在 Shared 中独立导入、阅读和研究资料，将结果保存、修订、重开，并按实际来源权限采用到 CTH、BMP 或独立创作。原件、研究推导和业务事实保持区分；历史参考有其日期、来源与适用边界。研究、决策、评价和学习复用既有产品能力与版本链。

Users can independently import, read and research materials in Shared, save and revise results, reopen earlier versions, and use permitted results in CTH, BMP or independent creation. Originals, derived findings and business facts remain distinct. Historical references retain their dates, sources and applicable limits. Research, decisions, evaluation and learning reuse the existing product capabilities and version chain.

完整要求与来源对应见[唯一规划](00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md)、[产品架构](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)和[来源采用记录](00-GOVERNANCE/LUMENIS-SOURCE-ADOPTION-V1.json)。

See the [complete plan](00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md), [product architecture](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md) and [source adoption record](00-GOVERNANCE/LUMENIS-SOURCE-ADOPTION-V1.json) for requirements and source mappings.
