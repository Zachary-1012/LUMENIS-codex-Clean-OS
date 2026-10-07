# LUMENIS 44 个既有屏幕：逐屏文字视觉草图

当前内部修订：1.6（沿用原 1.5 文件路径，避免制造第二份草图权威）。
与同目录《LUMENIS 前端最终目标与执行蓝图》1.6 逐项对应。本文件覆盖 44 个既有 Screen ID，作为完整业务能力的审查索引，不承诺最终产品固定恰好 44 个页面；适用时用当前页内抽屉、模态、播放器层、时间线状态表达，不复制造页。本文只用字符/区域说明目标形状、字段优先级、主次动作和关键状态；不是正式视觉稿，也不表示当前已经编码。

## 当前状态读法

- 1.6 审阅输入基线为 `bbe3310f095b788448a480c4615481bc5da029f8`；Universal Platform Acquisition 规则来源提交为 `3be8298a3ae853b98fde90b2fda943a5c9462a58`。该 SHA 仅冻结本轮审阅输入；实现/验收必须 fresh resolve 当前 main/runtime。原 1.5 的 `0c9394ef` 源码观察保留为 dated provenance；当前目标以 2026-10-07 权威规则与更新后的 Screen Spec 为准。`c7765b87`、`1b238c2f`和`0c9394ef`为治理/归档审阅提交，未修改前端Screen/API媒体/采集源码；当前静态源码快照有44个App Screen源文件；44份Screen-specific规范与ID对应。
- Binding registry 生成源早于该 HEAD，历史状态为 Acceptance Pending；本任务没有运行产品、读取生产 DB、重跑绑定或任何产品 E2E。
- 下方 `Screen Spec.status` 是屏幕规范/设计评审状态（例如 `DESIGN_READY` 或 `BLOCKED`），不是产品实现、服务可用或运行验收状态。每行同时保留源码/验收缺口与直接链接。
- R01–R15/J1–J8/U01–U25 到本产品屏幕/流程的审阅导航见同目录主方案 §6.7；这些代码不是新的页面标签，也不会自动标为通过。
- Website/Web/Desktop/Mobile与Windows/macOS/Linux、Android/iOS的职责和1920–360尺寸重组见主方案§4.3；本文件各屏线框为任务-specific形状，非操作系统通用模板。各ScreenSpec链接含当前Owner/状态/Binding及其实际提供的locale keys；主方案§3.4补足本目标中新增的字段、状态和辅助文案映射。
- 页面字段是语义槽位；owner 不返回或语义未知时保留未知/缺失，不自行发明值。真实数据、授权、失败恢复、保存/重开、跨端续接和用户结果仍需各自的真实验收。
- 以下每屏的字段都是语义槽位；若当前 owner 不返回或语义未知，显示缺失状态，不自行发明值。
- 逐Screen的zh-CN/en/ko-KR目标标题、主要动作及核心状态词映射见主方案 §3.4；本文件中的 `GLOBAL/ALL`、Owner、Evidence、Viewer 等是审核/字段 shorthand，不是要求直接显示为技术大字。

## 2026-10-07 跨屏终态收敛

以下是 1.6 必须贯穿相关屏幕/抽屉/Sheet 的共性结果，不新增 Screen ID，也不把内部技术名直接显示给普通用户：

- `PlatformManifest` 只负责内部平台真相；SYS-02把它投射成“该来源能提供什么 / 当前配置与验证到哪一步 / 哪些字段不可用”，而不是显示Manifest、Adapter类名或硬编码平台清单。
- `PlatformSession` 是平台连接状态唯一投影；用户看到 READY / 需要登录 / 需要验证 / 冷却 / Worker不可达 / 未配置 / 未知，不看到Cookie/CDP/profile路径。
- `LumenisPlatformRecoverySheet` 是唯一平台恢复层；QR、受控登录、VERIFY、BLOCKED/COOLDOWN四态分开。多个平台同时异常时在一个Sheet里排队，一次处理一个，不叠多层modal。
- RecoverySheet打开时焦点进入Sheet，关闭后返回触发控件或下一合理工作位置；扫码/验证等异步状态可被辅助技术播报但不抢焦点。
- `SourceTarget / Open Original / Return` 是所有重要Source-backed事实的统一来源动作：同一row lineage→查看来源→Open Original→诚实handoff状态→返回原route/Focus/filter/selection/scroll；普通打开原帖不启动采集或Evidence捕获。
- query continuation、平台native cursor和durable task receipt在视觉上分开；用户看到“从原任务继续、已完成来源不重复、终态重开返回原结果”，不看到attempt/lease/completion token。
- 平台扩展按原生内容类型与平台特有字段重组Reader；六个平台是当前验收基线，不是最终视觉平台上限。
- SYS-07终态按同一发布证据链显示 source/config → Product Gate → App Gate → Critical E2E → package/build（适用）→ loaded runtime → rollback/recovery → Product Owner repeat → RELEASED → OPERATING；不同SHA证据不合并冒绿。
- AI-05只显示产品AI服务诊断，不显示或选择Codex研发模型/provider。

## 五位架构视觉角色索引（主方案 1.6 / §3.3）

| 角色身份 | 对应既有能力屏幕 | 产品内显示边界 |
|---|---|---|
| CTH 商业运营 | CTH-01–10 | 仅在商业运营任务/对象语境提供识别；不替代真实商场、品牌或平台标识 |
| BMP 品牌市场 | BMP-01–11 | 仅在品牌、市场、创作者、内容/Campaign任务中提供识别；身份来自真实品牌/Brief |
| Shared Capability 共享能力 | SH-01–06及跨域成果接续处 | 仅解释来源到成果的共享链路；不冒充Source/Evidence事实 |
| System 系统 | SYS-01–08 | 只在真实服务状态、恢复、安全/运行说明等上下文；不作为普通用户角色选择或默认导航人格 |
| 序境自研AI | AI-01–05 | 仅在真实AI任务、来源说明、结果或不可用状态中；建议保持可查、可改、可拒绝 |

本产品视觉家族固定五位；Agent不是第六位，产品账号/Permission也不使用这些角色做权限或登录选择。线性icon继续承担实际控件功能，五位彩色手绘身份不表示成功、失败、授权或数据真假。1.5将1.4的通用角色/对象方向升级为架构对应关系；以后恢复美术/代码工作时，现有官网、Web、Desktop、Mobile角色图稿逐一映射并升级到这五位，未映射项保留历史并标为旧版/待替换。本次只更新方案，不表示实际图稿、图标资产或产品代码已更新。

## 页面 / owner / 接口验收映射

| Screen | 既有领域owner | 应由现有API/ViewModel提供的输入 | 需要验收的结果链 |
|---|---|---|---|
| ACC-01..04 | App Shell / optional Focus / task-local recovery | 启动状态、可选Scope、真实导航与当前任务恢复 | 直接进入开放工作区；无产品登录/账号/角色设置UI；具体外部动作仍由服务端Permission和原任务确认 |
| CTH-01..10 | CTH / Metrics / Source-Evidence / Case | GLOBAL或精确Subject、时间范围、来源、metric definitions、Case/Action；CTH-03现有只读搜索动作与逐条Source身份 | 真实材料→人工确认只读搜索→Source/Evidence/Canonical→单帖阅读→事件/决策/报告→Action/Outcome→Evaluation |
| BMP-01..11 | BMP / Brand-Market / Source-Evidence / Creation | 可核实品牌/市场/受众/竞品/创作者/活动/内容 | 研究→Brief→内容/Campaign→审核→真实结果/评价 |
| AI-01..05 | AI Gateway / Task / Agent / Skill / Evaluation | 当前调用范围、被允许的输入、实际能力、任务状态 | 输入→可执行检查→真实执行或真实失败→引用结果/Artifact→重开/评价 |
| SYS-01..08 | SYSTEM Runtime / Collector / DB / Permission / Settings / Browser | 实时检查、会话/范围、状态/时间/日志/偏好 | UI动作→真实owner→回执/错误→局部恢复和Trace |
| SH-01..06 | Shared Source/Evidence/Artifact/Reporting/Learning/Notifications | 原始材料、Discover结果、六平台单帖类型、权限/权利、Artifact版本、任务/提醒 | 有范围/来源的读取→SH-02原生单帖Reader→BMP/CTH/既有 Brief/创作→真实结果→保存/导出/重开→评价 |

App 页面按已有 screen repository/Client 读取；本任务不运行其中调用。单击动作的精确 callable、actor scope、Evidence lineage 和外部副作用以各自 Screen Spec 与当前服务合同为准，不从页面标题推断。

## 44屏实现/Owner/后端依赖映射

本表仅保留一份逐屏映射。接口列给出既有责任边界，不发明API URL/字段合同；最后一列直接链接当前Screen Spec并引用其owner_domain、status与binding gap ID。`status` 是屏幕规范/设计评审状态，不是实现或运行验收；具体 callable、ViewModel字段、Permission/Evidence和Recovery按链接中的当前合同读取。当前 Client 有按ScreenID的读取路径，但不据此推断业务绑定已闭环。

| Screen | 现有Owner边界 | 目标数据/后端依赖 | 当前源状态 / 尚欠 | 当前 Screen Spec（owner / status / binding gaps） |
|---|---|---|---|---|
| ACC-01 | App Shell / open product entry | 直接进入开放工作区；若底层核心不可用则保留返回路径；账号UI不进入当前目标 | 旧Screen Spec仍记录其历史设计状态，但Product Owner当前明确暂缓产品账号/登录设计；不得实现账户表单/占位菜单 | owner_domain=SYSTEM / Experience entry; source spec status=DESIGN_READY (prior contract provenance only); current user scope defers account UI; [ACC-01.md](../../../../contracts/experience/screen-specifications/ACC-01.md) |
| ACC-02 | App Context / Subject / BrandFocus | 当前身份允许范围、实体名/alias/region/source/relationships | 源码/路由存在；GLOBAL可进入；实体精确关系未逐项验 | owner_domain=SYSTEM settings / CTH Subject Registry / BMP BrandFocus; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [ACC-02.md](../../../../contracts/experience/screen-specifications/ACC-02.md) |
| ACC-03 | App Shell + ACC03 + AI01 | global context、真实task/restoration record、导航回调 | 源码存在；root目前CTH01冲突；主页接受和任务重开未验 | owner_domain=SYSTEM / Shared Capability presentation; status=DESIGN_READY; no BACKEND-GAP ID in frontmatter; [ACC-03.md](../../../../contracts/experience/screen-specifications/ACC-03.md) |
| ACC-04 | App Shell / Access Recovery | Core权限/Scope失败原因和可恢复动作 | 源码/路由存在；各类错误/返回E2E未验 | owner_domain=SYSTEM Permission / recovery boundary; status=DESIGN_READY; no BACKEND-GAP ID in frontmatter; [ACC-04.md](../../../../contracts/experience/screen-specifications/ACC-04.md) |
| CTH-01 | CTH / Metrics / Event & Case / Evidence | global或Subject过滤、指标、事件、来源、Case/Decision队列 | screen source存在；当前Scope/指标/E2E未验 | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-005, BACKEND-GAP-006, BACKEND-GAP-007; [CTH-01.md](../../../../contracts/experience/screen-specifications/CTH-01.md) |
| CTH-02 | CTH / Canonical Entity Registry / Evidence | 已有Subject查询；新增CTH company双语名称/industry/keywords走现有注册POST；Country/venue/brand关系走EntityRelation owner | ScreenSpec当前为读目录；注册API有CONFIG_MODIFY高风险人工审批；Country投影只读，Subject→unit→brand关系writer未确认；不能将created当已验证或自动采集 | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-008; [CTH-02.md](../../../../contracts/experience/screen-specifications/CTH-02.md) |
| CTH-03 | CTH + SYSTEM Collector / Source-Evidence | 现有GET：最多100条canonical row、scope projection、source_url/captured_at/time；现有人工只读POST：platform+keyword或已选business_requests | POST已存在但App没有调用；GET的来源/Evidence字段被Dart丢弃；通道items缺projection但Flutter要求v2；Dart未保留独立platform_id、通道/内容使用字符串匹配可能失配；固定Taikoo Hui keyword须移除；正文/媒体/互动不在当前row | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-009; [CTH-03.md](../../../../contracts/experience/screen-specifications/CTH-03.md) |
| CTH-04 | CTH Event / Case / Evidence | event time、关联规则、case link和来源引用 | screen source存在；因果/关联边界和保存位置需真实E2E | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-010; [CTH-04.md](../../../../contracts/experience/screen-specifications/CTH-04.md) |
| CTH-05 | CTH Feedback/Sentiment / Metric | 时间窗、分母、可读事件和来源列表 | screen source存在；日历度量口径未当前核验 | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-011; [CTH-05.md](../../../../contracts/experience/screen-specifications/CTH-05.md) |
| CTH-06 | CTH Feedback / Source-Evidence / Case | 实际反馈原文、类型、来源、重复/冲突关系 | screen source存在；各类反馈的真实来源范围未验 | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-012; [CTH-06.md](../../../../contracts/experience/screen-specifications/CTH-06.md) |
| CTH-07 | CTH Metric / Truth Table / Evidence | metric definitions、unit、period、comparison basis | screen source存在；Unknown与不可比行为需E2E | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-013; [CTH-07.md](../../../../contracts/experience/screen-specifications/CTH-07.md) |
| CTH-08 | CTH Case / Knowledge / Evaluation | case lifecycle、audit、reviewed knowledge inputs | screen source存在；创建/流转/知识提炼真实回执未验 | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-014; [CTH-08.md](../../../../contracts/experience/screen-specifications/CTH-08.md) |
| CTH-09 | CTH Decision / Risk + SYSTEM Permission/Effect | risk evidence、决策owner、Approval、Action/Outcome | screen source存在；Permission/Effect不由前端决定 | owner_domain=CTH; status=BLOCKED; BACKEND-GAP-015, BACKEND-GAP-016; [CTH-09.md](../../../../contracts/experience/screen-specifications/CTH-09.md) |
| CTH-10 | CTH Reporting / Shared Artifact | 报告范围、指标口径、Citation、生成的Artifact version | screen source存在；当前导出/重新打开链未验 | owner_domain=CTH / Shared Capability Reporting; status=BLOCKED; BACKEND-GAP-017; [CTH-10.md](../../../../contracts/experience/screen-specifications/CTH-10.md) |
| BMP-01 | BMP Brand/Market / Evidence | BrandFocus、市场/受众/竞品/渠道关系 | screen source存在；真实BrandFocus和总体覆盖未验 | owner_domain=BMP; status=REVIEWED_FOR_SCOPE_BLOCKED_SLICE; no BACKEND-GAP ID in frontmatter; [BMP-01.md](../../../../contracts/experience/screen-specifications/BMP-01.md) |
| BMP-02 | BMP Brand Registry / Competitor Data | 搜索现有BrandFocus；新增BMP brand基本身份复用Subject Registry；竞品/隶属关系单独验Source | Current ScreenSpec只读，不含创建/编辑；Add BrandFocus是已批准完整能力的目标差距，不能假称BMP-02已写入；不得从标识/名称自动建立竞争/所属关系 | owner_domain=BMP; status=BLOCKED; BACKEND-GAP-019; [BMP-02.md](../../../../contracts/experience/screen-specifications/BMP-02.md) |
| BMP-03 | BMP Market Research / Source-Evidence / Metrics | market topic、时间/平台、样本数、source/evidence；单帖只按单来源消费 | `BLOCKED / BACKEND-GAP-020`；无匹配指标/样本覆盖时不得从一帖推出市场总体/趋势 | owner_domain=BMP; status=BLOCKED; BACKEND-GAP-020; [BMP-03.md](../../../../contracts/experience/screen-specifications/BMP-03.md) |
| BMP-04 | BMP Propagation / Metric / Evidence | 内容、平台、阶段和有口径的实际互动 | screen source存在；不支持的传播/转化值不能补造 | owner_domain=BMP; status=BLOCKED; BACKEND-GAP-021; [BMP-04.md](../../../../contracts/experience/screen-specifications/BMP-04.md) |
| BMP-05 | BMP Creator / Source and Risk | 创作者身份、内容、真实表现、合作risk | screen source存在；推荐/fit没有该服务结果时保持Unknown | owner_domain=BMP; status=BLOCKED; BACKEND-GAP-022; [BMP-05.md](../../../../contracts/experience/screen-specifications/BMP-05.md) |
| BMP-06 | BMP Content / Brief / Permission / Artifact | Brief、内容版本、权利、review、发布handoff | screen source存在；对外Publish和回执未验证 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-06.md](../../../../contracts/experience/screen-specifications/BMP-06.md) |
| BMP-07 | BMP Campaign / Planning / Outcomes | objective、budget/target（若任务给定）、channel和实际结果 | screen source存在；计划、审批、发布、Outcome需连真实服务 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-07.md](../../../../contracts/experience/screen-specifications/BMP-07.md) |
| BMP-08 | Shared Audio / Artifact / AI Gateway when available | 文件音频、脚本、时码、speaker/track、render/export、授权本地录音 | screen/UI actions存在；文件播放/混音/版本E2E未完成于本轮；录音与各端运行态仍未验证 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-08.md](../../../../contracts/experience/screen-specifications/BMP-08.md) |
| BMP-09 | BMP Evaluation / Metric / Evidence | 品牌维度、基线、期间、coverage、confidence来源 | screen source存在；不可比和缺分母需验 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-09.md](../../../../contracts/experience/screen-specifications/BMP-09.md) |
| BMP-10 | BMP Brand Risk / Event / Permission | 事件证据、责任、response draft、Effect状态 | screen source存在；未批准的response不执行 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-10.md](../../../../contracts/experience/screen-specifications/BMP-10.md) |
| BMP-11 | BMP Benchmark / Metrics / Evidence | 对象集合、统一metric定义/期间和来源 | screen source存在；单位/口径不兼容时状态未知 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-11.md](../../../../contracts/experience/screen-specifications/BMP-11.md) |
| AI-01 | SYSTEM AI Gateway / Context / Source-Evidence / Artifact | 用户任务、许可材料、可调用能力/当前route | screen source存在；本轮未运行任何真实任务 | owner_domain=Shared Capability / AI Agent Groups; status=BLOCKED; BACKEND-GAP-029, BACKEND-GAP-030; [AI-01.md](../../../../contracts/experience/screen-specifications/AI-01.md) |
| AI-02 | SYSTEM Agent Runtime / Task Queue / Artifact | stage状态、step inputs/outputs、cancel/resume | screen source存在；真实runtime执行/恢复未验 | owner_domain=Shared Capability / AI Agent Groups; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [AI-02.md](../../../../contracts/experience/screen-specifications/AI-02.md) |
| AI-03 | AI Result + Shared Citation/Evidence | claim、citation anchor、版本、uncertainty | screen source存在；结果对每条source的真实绑定未验 | owner_domain=Shared Capability / Evidence-linked AI analysis; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [AI-03.md](../../../../contracts/experience/screen-specifications/AI-03.md) |
| AI-04 | SYSTEM Skill Registry / License / Permission | 已验证skill、license/trust、inputs/outputs/run history | screen source存在；Store lifecycle需逐条落实在现有owner | owner_domain=Shared Capability / Agent Skills registry; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [AI-04.md](../../../../contracts/experience/screen-specifications/AI-04.md) |
| AI-05 | SYSTEM AI Gateway / runtime diagnostics | 产品级Available/Not ready/Unavailable/Unknown、最后检查与安全调用观测；不显示/选择raw provider/model | 当前可有明确diagnostic fallback；诊断不等于独立AI能力，Codex研发模型选择不进入产品UI | owner_domain=SYSTEM AI Gateway / runtime diagnostics; status=BLOCKED; current spec禁止provider marketplace/model selection; [AI-05.md](../../../../contracts/experience/screen-specifications/AI-05.md) |
| SYS-01 | SYSTEM Runtime / Observability | 组件health/dependency/trace/recovery | screen source存在；当前运行 health未执行检查 | owner_domain=SYSTEM / RuntimeGuardian; status=APPROVED; BACKEND-GAP-036; [SYS-01.md](../../../../contracts/experience/screen-specifications/SYS-01.md) |
| SYS-02 | SYSTEM Collector / Scheduler / PlatformSession | 终态：PlatformManifest能力投影、PlatformSession、计划/Task、query continuation/native cursor/durable receipt、pause/cancel/resume/recovery | revision 2已承接最终目标；当前实现仍read-only，Manifest/Session/receipt与真实动作需C1/C6绑定；配置/注册不能冒充READY | owner_domain=SYSTEM Collector; status=DESIGN_EXPLORATION; revision=2; BACKEND-GAP-037; [SYS-02.md](../../../../contracts/experience/screen-specifications/SYS-02.md) |
| SYS-03 | SYSTEM Database / Integrity / Evidence Lineage | schema, version, readonly health, canonical integrity | screen source存在；本轮不读/改生产DB | owner_domain=SYSTEM / Canonical Data; status=DESIGN_EXPLORATION; BACKEND-GAP-038; [SYS-03.md](../../../../contracts/experience/screen-specifications/SYS-03.md) |
| SYS-04 | SYSTEM Permission / Audit / Effect Fence | actor/scope/action/approval/effect result | screen source存在；不能将屏幕中的UI grant当服务权限 | owner_domain=SYSTEM Permission; status=DESIGN_EXPLORATION; BACKEND-GAP-039; [SYS-04.md](../../../../contracts/experience/screen-specifications/SYS-04.md) |
| SYS-05 | SYSTEM Settings / Local Preferences | wallpaper/theme/contrast/motion/locale on current device | screen source存在；wallpaper's cross-surface adaptive result未跑实机 | owner_domain=SYSTEM Settings; status=DESIGN_READY; BACKEND-GAP-040 (read-only SYS-05 screen snapshot); [SYS-05.md](../../../../contracts/experience/screen-specifications/SYS-05.md) |
| SYS-06 | SYSTEM Controlled Browser / Authorization / Recovery support | 当前任务受控Browser；RecoverySheet当前项需要LOGIN_FORM/VERIFY时提供网页交互，再交回PlatformSession健康复核 | revision 4明确Browser不是Session owner/平台账号中心；QR与BLOCKED/COOLDOWN不强制开Browser；live/native recovery E2E未验 | owner_domain=SYSTEM Browser / CDP; status=IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED; revision=4; BACKEND-GAP-041; [SYS-06.md](../../../../contracts/experience/screen-specifications/SYS-06.md) |
| SYS-07 | SYSTEM Evaluation / Release Evidence | 终态same-release证据链：source/config→Product Gate→App Gate→Critical E2E→package/runtime→rollback→PO repeat→RELEASED→OPERATING | revision 2已批准终态；当前builder仍只有有限checks/skill light，完整C6/M release evidence未绑定 | owner_domain=SYSTEM Security / AI Gateway; status=DESIGN_EXPLORATION; revision=2; BACKEND-GAP-042; [SYS-07.md](../../../../contracts/experience/screen-specifications/SYS-07.md) |
| SYS-08 | SYSTEM Observability / Logs | trace id/span/error/time context, sanitized fields | screen source存在；实机关联回路待验 | owner_domain=SYSTEM Observability; status=DESIGN_EXPLORATION; BACKEND-GAP-043; [SYS-08.md](../../../../contracts/experience/screen-specifications/SYS-08.md) |
| SH-01 | Shared Timeline/Media/Artifact | licensed source files, project, timeline, render/export/reopen | screen/media source存在；本轮未完成真实project E2E | owner_domain=Shared Capability; status=IMPLEMENTED_CATALOG_ONLY_EVIDENCE_SCOPE_BLOCKED; BACKEND-GAP-044, BACKEND-GAP-045, BACKEND-GAP-046, BACKEND-GAP-047, BACKEND-GAP-048, BACKEND-GAP-049; [SH-01.md](../../../../contracts/experience/screen-specifications/SH-01.md) |
| SH-02 | Shared Source/Evidence / Rights / SourceTarget | originals/snapshots/time/citation/native Reader；同一row已验证时终态支持Trace→Open Original→Return | revision 3已承接SourceTarget终态；当前scope/Evidence envelope、typed target/launcher/Return仍未绑定，六样本仅作内部结构参考 | owner_domain=Shared Capability; status=IMPLEMENTED_SCOPE_GUARDED_BACKEND_SCOPE_UNVERIFIED; revision=3; [SH-02.md](../../../../contracts/experience/screen-specifications/SH-02.md) |
| SH-03 | Shared Canonical Data / Metric | field/schema owner/lineage/derived status | screen source存在；当前 binding/production schema未核实 | owner_domain=Shared Capability; status=IMPLEMENTED_SCOPE_GUARDED_BACKEND_SCOPE_UNVERIFIED; no BACKEND-GAP ID in frontmatter; [SH-03.md](../../../../contracts/experience/screen-specifications/SH-03.md) |
| SH-04 | Shared Artifact/Reporting/Export | output version/type/source links/export status | screen source存在；每种文件实际重开未验证 | owner_domain=Shared Capability; status=IMPLEMENTED_SCOPE_GUARDED_EFFECT_UNVERIFIED; no BACKEND-GAP ID in frontmatter; [SH-04.md](../../../../contracts/experience/screen-specifications/SH-04.md) |
| SH-05 | Shared Learning/Evaluation/Promotion | reviewed assets, evaluation, proposed versions, approval/rollback | screen source存在；自动Promotion不允许，流程未E2E | owner_domain=Shared Capability; status=IMPLEMENTED_SCOPE_GUARDED_PROMOTION_READ_ONLY; no BACKEND-GAP ID in frontmatter; [SH-05.md](../../../../contracts/experience/screen-specifications/SH-05.md) |
| SH-06 | Shared Notifications/Task/Approval | real pending/owned items, source task, outcome | screen source存在；通知来源和跨端一致性未验 | owner_domain=Shared Capability; status=IMPLEMENTED_SCOPE_GUARDED_OPERATIONAL_READ_ONLY; no BACKEND-GAP ID in frontmatter; [SH-06.md](../../../../contracts/experience/screen-specifications/SH-06.md) |

凡当前尚未验证的行都继续留在目标方案中；后端实现状态未确认不是从前端蓝图删屏的理由。

---

## ACC：入口和恢复

### ACC-01 产品入口直达（当前不绘制账号页）

~~~text
Desktop/Web/Mobile启动：
┌ 序境当前可用状态（只显示真实必要信息） ┐
│ LaunchSurface → ACC-03开放工作区        │
│ 若核心启动失败，在当前入口说明原因       │
│ [重试]（仅可安全重试时） [退出]          │
└────────────────────────────────────────┘
~~~

没有登录、注册、找回账号、角色问卷、账号菜单或未来占位。账号/登录是否重新规划等整体产品闭环后再由Product Owner决定。旧 ACC-01 Screen Spec 仍作为Source/历史合同状态记录，不构成当前前端账号页许可。

### ACC-02 可选范围选择

~~~text
Desktop:
┌搜索主体/品牌┐ ┌可用实体列表┐ ┌真实关系/范围/来源┐
│名称/地区    │ │名称+缩写    │ │Selected Focus   │
└─────────────┘ └────────────┘ └[聚焦] [保留全部]┘
Phone: [全部范围 chip] → 搜索/列表 → 对象详情 sheet
~~~

ACC-02只是可选Focus选择器，不是Add Subject/BrandFocus的注册表单。结果显示GLOBAL/ALL和现有登记项；选中后用户可继续当前任务，清空回全部范围不删历史。新增身份进入既有CTH/BMP Canonical registry，由其专属业务列表提供入口，不放进账号/登录页或全局权限设置页。当前POST的人工CONFIG_MODIFY审批在具体新增动作内呈现。

### ACC-03 产品任务主页

~~~text
PC:
┌序境     搜索     外观/语言┐
│今天接着做（真实任务才显示） [继续] [看变化]│
│目标/材料输入 [范围：全部 ▾] [开始一项任务]    │
│观察变化 → 商业现场                          │
│理解市场 → 品牌与竞品                        │
│读研究材料 → Source / Evidence               │
│完成创作 → Brief / 视频 / 播客 / 报告         │
│待确认的真实结果/影响（有数据才显示）          │
└─────────────────────────────────────────────┘
Phone: 任务输入与主按钮优先；四类工作入口短列表；待确认项单条进入。
~~~

无任务时不做虚构最近任务/数字。Focus只有当前任务确实选中时才出现小 chip；不使用大“当前查看范围/启动状态”说明。

### ACC-04 原任务内的失败恢复（不是登录/权限页面）

~~~text
PC: 当前任务中的 [失败对象] → [影响] → [可恢复步骤] [Retry*] [Back]
Phone: 原页面就地说明原因/影响 → [返回原任务] / [可用替代动作]
~~~

数据失败/服务端对某动作的实际拒绝/网络离线/上下文未知/数据过期状态分开；只说明本次任务动作的拒绝，不进入产品账号或角色设置。`Retry*` 仅在幂等且 owner 允许时显示；取消与回退保留原任务。服务端 Permission 不被前端文案绕过。

## CTH：商业运营路径

### CTH-01 商业现场概览

~~~text
PC: [全部/可选Subject] [时间窗/过滤]
    ┌时间带/真实信号┐ ┌事件Evidence/Case┐ ┌下一步/报告┐
Phone: 选日期范围 → 当前信号 → 原文/Case → 返回轴
~~~

显示真实信号时间、事件状态、对应指标口径；无样本给无采集/无记录状态，不能填0。

### CTH-02 主体/业务单元

~~~text
PC: [已登记主体/关系] [新增经营主体] │现有清单│选择对象/关系来源
Phone: [搜索主体] → 详情/关系sheet → [新增经营主体]

新增经营主体：
┌ 登记类型：商业主体(company) · Scope=CTH ────────┐
│ 中文名称* [____]   English name* [____]          │
│ 行业 [____]  可核实的关键词 [____]               │
│ [检查精确重名] [提交登记]                        │
│ 登记成功 ≠ 已验证关系/已经采集；单独显示状态     │
└─────────────────────────────────────────────────┘

关系区（单条Source-backed assertion；关系种类决定字段）
Country：ORIGIN/HQ/LEGAL_JURISDICTION/OPERATES_IN/
        VENUE_LOCATION/MARKET_ACTIVITY
        ISO alpha-2·声明/明确不存在·AS_OF_CAPTURE/INTERVAL/UNKNOWN
        有效起止时间·SourceEvidence/Source Note/语言
TENANT_OF (CTH)：租户名·楼层/类型/类别·listing URL·观察时间
        可选目标BrandFocus（只能选现有BMP品牌）·来源Evidence
review_status：未审/已接受/冲突/拒绝（仅Owner返回）
~~~

目标国家关系只用对应类型+ISO alpha-2+源Evidence/Note/语言/有效时间；不把国家缩写做成“覆盖完整”的标记。TENANT_OF必须绑定已验证Source内容、listing URL精确一致和可定位租户/楼层；没有命中就维持待核实。当前relation repository提供连接作用域writer，但用户-facing HTTP/Permission/Review流程未验证；当前页面不得声称关系已写入。旧CTH-02 Screen Spec仍把创建/关系编辑置于scope外，需将其目标交互在原Owner内复审，而不是新增登记产品或重写其既有GET。

当前 `/api/settings/subjects` 注册payload只接domain_id/subject_type/双语规范名/industry/keywords，且CTH必须company。精确双语重名会返回现有条目；不假称支持模糊别名merge。注册不自动选Focus、采集或证明地点/租户关系。关系写接口未核实时保留“关系未登记/待核实”状态并回到同一清单。选择实体和新建实体是不同动作；打开来源后Back回原列表。

### CTH-03 来源检索与单帖阅读

~~~text
桌面 / Web — CTH-03（无主体时直接走全部范围）
┌ [已存记录] [新建采集] · 当前任务/Scope                         ┐
│ 已存记录：平台 stable ID · 发布/事件时间 · 采集时间 · 状态     │
│ 新建采集：已批准平台 · 关键词 / 单帖URL导入（不同路径）       │
│            来源目的/时间窗/内容层级/人工或已授权计划           │
│ [确认本次只读/具体效果] [触发当前真实动作]                     │
├───────────────┬────────────────────────┬──────────────────────┤
│ 结果/平台lane  │ 单帖原生Reader           │ Scope / Source / Trace│
│ 同一请求ID      │ 实际图/视频/长文         │ 平台ID≠显示名         │
│ fetched/accepted│ 原文/派生译文分开        │ 发布时间/采集时间      │
│ 重复/部分/失败  │ 评论/互动按平台分页       │ Evidence/版本/关系     │
│ 具体恢复原因    │ [Trace] [Open Original] │ [回列表] [回任务]      │
└───────────────┴────────────────────────┴──────────────────────┘

手机： [已存记录] / [新建采集] → 一条任务条件与真状态 → 逐篇Reader
已存记录只过滤读取；新建采集才触发Collector。排程只在授权计划已有运行合同后单独确认，不与单次检索合并。
~~~

现有接口事实：CTH-03 GET最多返回100条且会报告 `partial`；现有人工只读 search POST 当前仅支持一个`platform+keyword`或`business_requests`批次；`continuation`只续查询计划，不是post/comment/media native cursor；App当前只有Screen GET。UI目标显示完整两种模式和计划/原生分页能力，当前模式没有实现的字段列为owner contract gap，不能发往旧Route。筛选主键必须为稳定 `platform_id`，显示名不可作身份键；不移除已有Evidence projection校验。固定“广州太古汇”查询预填须清空。未返回的全文/媒体/评论/原生互动标“未取得/未绑定”，不可借别帖补齐。

终态来源动作使用 `lumenis.source-target/v1`：Trace先显示同一row的Source/Evidence/时间/locator，再按 `READY / URL_MISSING / INVALID_URL / DENIED / UNSUPPORTED / SOURCE_WITHDRAWN / STALE / UNKNOWN` 决定是否提供 Open Original。打开后只把公开HTTPS交给系统浏览器，`HANDOFF_ACCEPTED`不等于页面加载成功；Return恢复原Scope、平台lane、筛选、选中项和滚动位置。六个平台是当前基线；新增平台沿相同稳定ID、SourceTarget和原生内容类型规则进入，不复制一个新CTH页面。

### CTH-04 事件关系

~~~text
PC: [时间范围] ──●Event──●Case──◇Evidence
                         └右侧:来源/关系/处理状态
Phone: 事件节点横向时间线 → 关系层 → 来源/Case
~~~

图中边只表示真实关系/规则关联；因果未知时保留“规则关联/待核实”文案。

### CTH-05 反馈/情绪日历

~~~text
PC: 期间/数据口径 ┌日期热区+图例┐ ┌选中日期原文列表┐
Phone: 期间picker → 日/周热区 → 日期详情列表
~~~

每种色/大小说明指标含义；键盘/表格列表提供非颜色和非手势入口。

### CTH-06 负面监测与反馈

~~~text
PC: 过滤/优先级 | 原始反馈/媒体 | [分类] [关联Case] [待核实]
Phone: 反馈待读列表 → 单条原文 → 处理sheet
~~~

原文为主，AI或人工分类与原文分开。错误分类可撤销（如果owner支持）并返回同一条。

### CTH-07 趋势分析

~~~text
PC: [指标] [窗口] [对比组] → 主趋势图 → 指标定义/数据表
Phone: 单主图 → 横向切指标 → 点数据节点看来源与分母
~~~

维度不兼容时不能只画在一起；选择范围/窗宽造成非可比时显示提示和取消操作。

### CTH-08 Case与知识

~~~text
PC: Case集合/真实状态 │选中Case事件与Evidence线 │责任/后续动作
    当前事实/来源 | 分析推断 | 审阅过的Knowledge版本（独立）
    [加已验证来源] [更新处理] [提出知识候选]
Phone: Case列表→影响/证据/责任→处理历史→已审Knowledge
~~~

每次处理显式填/选状态、责任Owner、期限/Outcome字段（仅Task/Case owner提供时）；改状态前显结果规则。Fact/推断/AI建议分开。Knowledge抽取是candidate，显示父Case、来源/方法/反例和评审状态；确认/提交由原Case/Knowledge owner回执。保存失败不改旧Case，Knowledge候选被拒也保留历史。

### CTH-09 风险与决策

~~~text
PC: 风险/影响范围和置信来源 | 事实/推断分栏 | 决策选项/理由/责任与审批
    [保存决策草稿] [请求该项批准] [查看实际执行/Outcome回执]
Phone: 风险/来源→选项差异→逐项审批/结果→回同一Case或来源
~~~

每个风险显示对象、时间窗、来源与限制；规则关联不作因果。仅在外部动作需要时解释其精确内容和影响；用户确认调用既有Approval/Effect Fence，拒绝、等待、超时及已执行回执各自呈现，不能用一次Risk颜色/按钮代表已发布/解决。颜色必须配文字。

### CTH-10 报告与周报

~~~text
PC: 章节/图表区 | 分页预览 | 口径、引用、来源和输出选项
Phone: 章节导航 → 单页预览 → 引用/方法抽屉 → Export
~~~

导出显示目标时间、范围和当前Artifact版本；失败时可回到正文修订。

## BMP：品牌/市场/创作路径

### BMP-01 品牌与市场概览

~~~text
PC: [可选Brand Focus] [期间]
    关系场：品牌 / 受众 / Creator / Channel / Competitor
    底边：来源口径与选中关系详情
Phone: 品牌pulse → 横向关系对象 → 当前证据/返回
~~~

无焦点时显示真实总体目录，不自动把一个品牌设为当前用户品牌。

### BMP-02 品牌组合/竞品

~~~text
PC: [当前BrandFocus可选] [已登记自有品牌] [竞品] [新增品牌身份]
    关系场/列表 │选中实体profile │Evidence/时间/可比维度
Phone: 搜索/选择品牌 → profile → [新增BrandFocus] → 保存回执

新增品牌身份：domain=BMP · type=brand · 双语规范名* · industry · keywords
重复：显示精确重复/打开已有；不得按类似logo/作者/名称自动归并。
~~~

BMP的新BrandFocus和CTH Subject调用现有 canonical subject registry owner，brand_focus_id为不同稳定身份。当前BMP-02 Screen Spec是只读selection slice且禁止创建/竞品写入；本稿把“新增BrandFocus”作为已批准全域新增能力映射到现有Owner的目标差距，不宣称当前BMP-02能写入或要求该页拥有新注册表。预算/竞品范围还是不同对象；别名/关系和名称冲突依Canonical owner审阅。过滤：品牌、品类、时间；无法比较字段留空。

### BMP-03 市场情报

~~~text
桌面： [品牌/市场 Focus 可选] [平台 stable ID] [时间] → 主题地形/样本边界
     选中主题 → 来源列表 → 右侧该平台原生单帖Reader/lineage
Phone：主题/范围状态→单个来源行→全屏原帖→回同一主题/筛选
~~~

单帖显示平台/时间/scope/原生内容/真实取得的互动/来源版本；译文或AI摘要另标派生。按钮为[查看证据][标记待核实][带到研究]；一篇帖只是一条样本，不把它直接设置成趋势、品牌决策或消费者总体结论。只有现有metric/coverage owner提供可比时间序列、去重与分母时才显示聚合。

### BMP-04 媒体传播

~~~text
PC: 媒体/活动 | 渠道路径→内容→已观察互动 | 口径/Source Inspector
Phone: 传播阶段卡 → 具体渠道 → 指标定义和来源
~~~

未知阶段保持空/未知而不是用虚线装饰出完整漏斗。

### BMP-05 Creator生态

~~~text
PC: 有范围的候选列表 │单个Creator Identity/Dossier│比较维度/Evidence
    真实作品按图文/视频/直播回放各自Reader，指标带窗口/来源
    [选入当前Campaign草稿] [返回研究]
Phone: 候选行→本人资料/一条作品→依据/未知→带入既有Campaign
~~~

档案逐项显示唯一平台身份/作者源、可读作品、品牌/Brief需求对应的实际受众依据、原生指标窗口、合作权/报价/风险状态/最近观测。无真实样本/分母不画匹配得分；只取得一篇作品就按一篇呈现。所选对象带Source/Evidence和理由进入BMP-07草案；scope改变重新核查。未获许可不联系Creator、不谈合作或发布。

### BMP-06 内容中心

~~~text
PC: Draft/Review/Approved/Delivered轨道 | 原创提案编辑器 | 版本/来源/资源约束
Phone: Brief/版本摘要→对照可行方案→打开草稿/审阅历史→保存新版本
~~~

按钮：编辑、比较、送审、导出；发布仅在该动作真实有授权时开放。提案/预算编辑的双情境布局、字段、状态和恢复见主方案§7.11；它不是媒体工作台的子面板，也不触发支付。

### BMP-07 Campaign工作区

~~~text
PC: [目标/范围/期间] ┌方案A/B资源/渠道对照┐ ┌里程碑┐ ┌实际结果┐
Phone: Campaign目标摘要→可行方案差异→里程碑→结果 → [修订方案]
~~~

目标值、计划、估算/报价/承诺/实支与真实结果互相分层；预算变化显示具体被影响的策略、素材、人员、日程和版本。没有数据不显示金额或可行性徽标；Plan不是支付或发布回执。

### BMP-08 播客主工作台

~~~text
Desktop:
┌项目/版本  [保存] [撤销] [导出]────────────────────────────────┐
│ 脚本章节 | 段落文字/引用      │当前段落详细字段/声音处理检查器 │
├──────────────────────────────┴───────────────────────────────┤
│ 人声A ═══波形══════╦════波形════════════════════════════════  │
│ 人声B ───波形──────╫──────────────波形──────────────────────  │
│ 音乐  ▒▒波形/自动化╫▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒       │
│ 效果/环境音────────╫────────────────────────────────────────  │
│ 00:00       00:15  播放头  00:30       00:45     →横向时间轴  │
│ [选择轨道] [Solo] [Mute] [Loop区间] [监听] [混音器]             │
└───────────────────────────────────────────────────────────────┘
Mobile: 实际播放器/时码+脚本跟随→横向可操作波形与音轨→选轨细节；同样保留导入、录音授权、核心剪辑/混音、撤销/重做和版本恢复，以单个可逆工作区适配窄屏，不删减完整任务能力。
~~~

音频文件导入、实际播放与回听、由解码媒体生成的真实波形、授权本地麦克风录音、剪辑/混音、导出和重开纳入完整目标。文本修订和音轨修订各自独立显示版本；Read Aloud 只是脚本临时朗读，不是录音或节目音轨。图中波形是目标表达，不证明运行版已有波形。录音要求取代旧“后置”备注；具体设备、权限和平台能力仍逐端验证，不能将未验证平台从四端验收中删除。

预览分成实际原始/当前可播放内容、临时预览导出和正式保存的 SavedWork/Artifact。临时导出不能冒称正式成果；正式保存后必须按同一版本重开、播放、修改并产生保留父版本的新版本。脚本编辑不自动改写现有录音；ASR 可选并经现有 C2 Gateway，手工录入/修订转录必须在无 AI 时可用。降噪和响度要有真实处理结果及测量，不因按钮存在就显示完成。

### BMP-09 品牌评价

~~~text
PC: 品牌/期间 → 维度矩阵 → 单维小倍图 → 证据覆盖条
Phone: 维度列表→单项趋势/定义→证据来源
~~~

结果区显式标记 comparability 和 confidence 的来源，避免一个总分掩盖未知。

### BMP-10 品牌风险/事件

~~~text
PC: 严重度/范围时间轴 | 原文/图片/扩散证据 | 响应责任/确认/Outcome
Phone: 事件列表→原始材料→可批准的响应措施
~~~

没有 Permission 的写操作为局部未启用，不消除只读核查。

### BMP-11 竞品分析

~~~text
PC: 比较集合/期间 → 横向metric grid → 定义/来源 drawer
Phone: 横向比较行 → 选metric → 可比性/来源详情
~~~

选择/去除 competitor 时提示分析结果变更并保留旧版本。

## AI / Agent

### AI-01 AI任务入口

~~~text
PC: [目标文本/当前Task] ─────────────── [保存草稿] [开始分析*]
    已选材料/Scope/来源    [查看本次上下文与来源]
    Context panel:
      用户输入/Brief | 引用的Source/Artifact | Memory owner实际返回版本
      每项显示用途/时间/范围/证据链；未返回的部分不写“已使用”
Phone: 任务框→材料/Scope→上下文详情sheet→草稿/真实返回结果
~~~

`*`最终目标在真实自有Gateway/Agent与Server Permission binding后执行；当前屏仅有明确不可用状态，不自动切主体/换模型。Memory条目只在Task/Agent owner真实返回并被本次执行使用时显示版本和来源；用户可对当前run取消某项输入（若Owner支持），这不删除全局Memory或改Source。`No memory attached`是正常空状态；输入草稿、执行结果、Evidence已记录/未确认/Trace unavailable分开；错误/超时保留当前意图且不得自动重复提交。

### AI-02 任务执行台

~~~text
PC: step list │当前Stage输入/来源│真实Artifact输出/错误/等待用户
Phone: 步骤1已完成 → 步骤2执行中 → 步骤3等待用户
      [取消] [安全重试] [回到任务]
~~~

状态用文字+短图形同时显示；只能由真正的任务状态驱动。Cancelled与failed不等于completed。

### AI-03 有证据的分析

~~~text
PC: Claim 1 [Citation A] [不确定原因]  │ Source reader
    Claim 2 [Citation B] [修订/返回]
Phone: 结论块→点击引用编号→来源原文→[返回原结论位置]
~~~

用户可反馈某条结论、请求修订或创建owner支持的任务；编辑后保存新版本。

### AI-04 Skill Store/能力目录

~~~text
PC: Task分类/发现 │已验证Skill列表│选中Skill详情/Owner版本/License
     输入/输出/Risk/Permission/版本差异/评估与使用历史
     [从任务运行已批准能力] [查看来源] [检查更新差异]
Phone: 当前Task适用能力→来源/版本/输入输出→调用状态→返回Task
~~~

**目标生命周期**：发现→查看来源/信任/许可/版本/用途→在目标Task中批准使用→运行/失败/取消→保存真实结果/版本→比较更新差异→采用新版本或保留旧版→停用/卸载及恢复。**当前ScreenSpec是READ_ONLY目录**，Install/Enable/Update/Disable/Uninstall按钮尚未绑定，本方案不把它画成当前可操作；闭环终态必须由既有Skill Registry/Runtime owner补充对应操作/在途状态，不能另建Marketplace/Runtime。运行中的skill若版本将变，仅按owner返回的run-id/版本和安全退出状态处理；旧Artifact/Trace不随卸载删除。无license/owner/permission的条目显示不可运行和原因。

### AI-05 AI Gateway 诊断

~~~text
PC: 当前任务 → AI服务状态 → 最近检查/调用观测 → 错误或恢复说明
    [刷新诊断] [继续手动流程] [返回任务]
Phone: 服务状态→检查时间/错误原因→重试或返回原任务
~~~

AI-05只做产品级诊断，不是provider marketplace或模型选择器。产品UI不显示原始provider/model名称，也不展示Codex研发窗口的Astra/Sol/Luna等工程配置；服务状态只用可核验的Available / Not ready / Unavailable / Unknown及真实时间/延迟单位。fallback只能明确标为diagnostic fallback，不能把降级/未绑定状态包装成AI能力成功。

## SYSTEM

### SYS-01 Runtime健康

~~~text
PC: App→API→DB→依赖图 | Health Timeline | 选中节点的check/detail
Phone: 依赖状态列表→错误详情→返回当前任务
~~~

显示last checked时间；未知用Unknown，不做绿灯“正常”默认值。

### SYS-02 Collector状态

~~~text
PC: 采集计划 | 执行记录 | 来源能力
    来源能力：平台/来源 · 能提供的正文/详情/评论/媒体/跟踪 · 当前可用程度
    PlatformSession：可用 / 需登录 / 需验证 / 冷却 / Worker不可达 / 未配置 / 未知
    计划编辑：目标/平台/授权Scope/用途/时间/频率/深度/停止条件
    执行列表：Task / 按平台进展 / query续接 / native cursor / 恢复原因
    操作：人工运行 / 开启已授权计划 / 暂停后续计划 / 取消待执行项 / 恢复来源
Phone: 单个计划或Task → 来源lane → 能力/Session/进展 → 回执/恢复
~~~

SYS-02是一个Collector的产品投影，不是平台后台或第二平台注册表。内部PlatformManifest决定canonical platform ID、alias、字段、能力、provider和runtime registration；UI只显示“这个来源现在能提供什么、验证到哪一步、还缺什么”，不显示Manifest/Adapter类名。

能力状态必须分开：declared / implemented / registered / configured / session-verified / live-verified不能压成一个绿灯。PlatformSession只通过统一Owner返回 READY / AUTH_REQUIRED / VERIFY / BLOCKED_COOLDOWN / WORKER_UNAVAILABLE / NOT_CONFIGURED / UNKNOWN。Cookie文件、CDP在线或profile存在都不能直接显示“已连接”。

任务状态显示 planned / queued / running / partial / waiting-recovery / completed / failed / cancelled；query continuation、平台native cursor和durable receipt分别表示不同连续性。终态receipt重开不得画成新run；用户看到“已完成来源不会重复执行 / 从原任务继续 / 返回原结果”，内部attempt/lease/completion token不显示。

这是SYS-02最终操作工作面的目标，不是当前ScreenSpec现有可用控件。当前实现仍可保持只读直到real callable/Permission/receipt接通；但终态的manual run、已授权AUTO plan、pause/cancel/resume、RecoverySheet入口不因today read-only而从蓝图删除。一个平台被阻断时只隔离该lane，其他可用来源继续。

### SYS-03 Data/DB Truth

~~~text
PC: Schema/表树 → field/metric → Evidence/source lineage → integrity差异
Phone: 链路步骤 → field detail → 来源/计算定义
~~~

只读查看生产事实；待执行迁移/恢复由 owner 发起，页面不直接写 Canonical。

### SYS-04 Permission/Audit

~~~text
当前不呈现产品角色/账号/通用权限设置页。
具体业务动作 → 原任务内显示内容/影响 → 用户确认
→ 服务端返回允许/拒绝/待审批 → 原任务显示回执/原因/来源
~~~

现有 SYS-04 规范/源码状态仍保留在映射表中作为合同/历史事实；本目标不设计新角色、权限矩阵或授权管理。任务级外部动作只显示现有 Permission/Approval owner 的真实决定，拒绝时无 Effect；页面不能授予或绕过权限。

### SYS-05 Appearance

~~~text
PC: 本地偏好与预设图片列表│样式控制│白/黑/两张壁纸页面预览
Phone: 主题/图片缩略图→裁切&对比预览→[本机应用]
~~~

壁纸和偏好按设备本地使用，不跨端同步原始图片或增加云文件服务。

### SYS-06 Controlled Browser/会话流程

~~~text
PC: [当前任务/允许域/可用浏览器状态] | 实际viewport（若绑定）|来源状态
    普通来源阅读→受控浏览，不等于采集/登录
    RecoverySheet请求LOGIN_FORM/VERIFY→进入受控平台页面→完成合法人工步骤→返回RecoverySheet
Phone: 当前工作→授权边界→受控来源（若可用）→状态/返回任务
~~~

SYS-06展示的是浏览器能力与当前任务授权范围，不是Collector连接灯，也不是平台账号管理中心。LumenisPlatformRecoverySheet负责恢复编排；只有当前恢复项需要网页交互时才调用SYS-06。QR可直接在Sheet显示；BLOCKED/IP风险/COOLDOWN不为了“有动作”而打开浏览器。

用户完成登录表单或验证后，SYS-06只把控制权/安全状态交回SYSTEM Session owner；必须由PlatformSession重新检查真实auth/verify/risk/worker健康，健康后RecoverySheet才能恢复原Collector task。多个平台异常时SYS-06只服务Sheet当前选中的一个恢复项，不叠平台窗口。敏感Cookie/token/password/profile/CDP/session ID不显示/复制；开发边界内不碰个人Mainland XHS身份。

### SYS-07 Release/Evaluation

~~~text
PC: 当前候选SHA
    source/config/DB/Experience
        ↓
    Product Gate
        ↓
    App Gate
        ↓
    Critical E2E
        ↓
    package/build（适用Surface）
        ↓
    loaded runtime identity / rollback
        ↓
    Product Owner重复核心任务
        ↓
    RELEASED
        ↓ real elapsed operation evidence
    OPERATING

Phone: 单个验收阶段→SHA/时间/证据→FAIL / NOT_RUN / UNKNOWN原因→返回owner
~~~

每一阶段都独立显示 PASS / FAIL / NOT_RUN / UNKNOWN / STALE 和证据SHA；不同SHA的Product/App/E2E不能拼成一条假绿线。source-present、build成功、HTTP 200、报告或某个本地Gate都不能单独变成RELEASED。官网/Web/桌面/移动各自只显示实际承诺的package/runtime状态；未发布安装包就明确未发布。

### SYS-08 Logs/Traces

~~~text
PC: 查询时间/trace filters | request waterfall | sanitized error detail
Phone: trace摘要→span顺序→错误原因/回到origin
~~~

可按 task, timeframe, component筛选；秘钥/令牌/个人cookie在显示层不输出。

## Shared

### SH-01 Discover 与共享内容创作

SH-01 属于 Shared Capability，不是第三个业务域。它与 SH-02 的原始资料阅读、BMP-03 的市场解释、BMP-07 的 Campaign 计划及 BMP-08 的 Podcast 编辑各有边界。规范目标是在同一 SH-01 内由持久的小导航切换“发现”与当前创作活动；切换不丢目标、筛选、来源定位和返回位置。

~~~text
桌面 / Web — Discover
┌ SH-01 发现与创作   [当前目标/Brief]       [返回原任务] ┐
│ [趋势] [观察热点] [相似作品]   GLOBAL/Focus · 平台 · 时间 │
├ 真实结果序列/作品缩略图区 ─────┬ 选中项的来源与解释 ─────┤
│ 作者/来源/发布时间/观察值(如有) │ 相关性依据/不匹配维度     │
│ 缺失字段明确未知/未采集         │ Citation/原文/媒体定位    │
│ [选入当前Brief/创作]             │ [打开原始来源]             │
└──────────────────────────────┴──────────────────────────┘

移动端 — 同一任务的焦点重组
┌ Discover [趋势|热点|相似作品] ┐
│ 范围/平台/时间（可改）          │
│ 一条结果：内容类型 + 来源 + 时间 │
│ [查看依据] [选入当前Brief]      │
└ 点选→可返回的详情层/页面；Back恢复筛选、选中项和位置 ┘

桌面 / Web — 当前创作活动
┌ [Discover] [当前创作]  Brief/输入来源  版本/回执 ┐
│ 内容画布 / 当前选择 / 可编辑产物 / 来源抽屉       │
│ 若活动是视频：上方 Viewer + Inspector；下方完整轨道、播放头、时间尺 │
└ 保存版本 / 撤销重做 / 导出状态 / 重开回同一工程 ┘
~~~

趋势只回答可比较观测期内发生了什么；热点只表示已知来源语料的观察，不伪称平台总榜或消费者总体；相似作品说明它与当前任务相合/不合的具体维度，不能只按热度排序。每个结果带真实 scope/platform/time、来源和可定位引用、方法/分母（若有）、相关性解释及缺失/部分状态。选取素材进入现有 Brief/视频创作 Owner，并执行新的 source-use/permission check；不强制创建空 Brief，不静默带入未授权全文/媒体。当前 callable 未冻结的操作必须显示不可用及原因，不能做假按钮或造推荐。

**现状：**Screen Spec `SH-01.md` 当前明确为 `IMPLEMENTED_CATALOG_ONLY_EVIDENCE_SCOPE_BLOCKED`：安全目录已实现；全局 Evidence route 不具备 actor/domain/object scope，App不得调用；运行/写入也不能从目录状态推断。视频媒体工作台有源文件与已批准的局部交互设计，但完整真实项目仍待 E2E。Discover 的字段/视觉候选仍为 `DESIGN_EXPLORATION`，须等现有 callable 和 owner binding 冻结后才可实现/验收。

#### SH-01 ShotPlan 与逐镜确认（叙事任务才进入）

~~~text
Desktop / Web
┌ Brief/脚本版本 [从当前脚本继续] [回工作] ┐
│ 01 未绘制 │ 02 待彩稿 │ 03 审阅中 │ 04 已确认 vN │
├───────────┬───────────────────┬────────────────────────┤
│ 镜头顺序  │ 当前镜头线稿→彩稿 │ 脚本/场景/人物服装     │
│ 拖动重排* │ 实际空间/动作      │ 道具/摄影/声音字幕/时长│
│ 返回原段  │ 批注/修改          │ [确认此镜] [下一镜]    │
└───────────┴───────────────────┴────────────────────────┘
```

`*` 重排仅在Timeline/ShotPlan owner返回且Permission允许时可提交；始终有精确键盘/菜单动作。确认绑定用户正在看的ShotPlan/脚本版本/Scope。修改剧本或场景后显示受影响镜头的旧/新差异，未变化镜头的确认保留；需要人工重看时状态回到待审。纯音频不强制分镜。

#### SH-01 宽屏素材与Timeline编辑

~~~text
┌ 项目版本 [保存] [Undo/Redo] [导出当前版本] [回任务] ┐
│ 工具：选择 / 修剪 / 分割 / 吸附↔定位 / 替换 / 文本 / 音频 │
├──────────────┬──────────────────────┬───────────────────────┤
│ 素材箱/来源   │ Viewer实际渲染画面    │ Inspector当前片段属性  │
│ 搜索/类型/时长│ 播放/逐帧/入出点       │ 画面/音频/文字参数     │
├─────────────────────────────────────────────────────────────┤
│ 共用时间尺 / 播放头 / 横向平移与缩放                         │
│ 主画面轨 ─镜头A─[B]─C────────                               │
│ B-roll/画面叠加轨 ─D────E───                                 │
│ 字幕/文字轨         ─标题────                                 │
│ 对白/旁白轨 ─真实媒体────────                                 │
│ 音乐/音效轨       ─真实媒体───                                │
└─────────────────────────────────────────────────────────────┘
~~~

目标状态覆盖精确选择、切分/修剪/重排、已批准的吸附与定位、轨道/字幕/音频处理、实际预览、导出后播放/重开。波形/缩略帧只用实际媒体。当前源代码/processor未绑定的项仍是目标缺口，不从目标图删除，也不在当前运行版假称可用。主方案§7.6是完整宽屏+手机构图的展开稿，§8.1是对应正常结果和恢复验收。

版本与真实验收：视口横向平移/缩放不改项目数据；播放头与真实 Viewer/时码对应；选取素材及操作轨道均保留来源、范围、rights 和父版本。Undo/Redo 恢复实际编辑快照。使用真实授权多轨素材完成编辑与同步检查，分别回放当前实际预览、临时导出和正式 Artifact；正式保存后重开同一项目，改动一处保存成子版本，验证旧版仍可播放并能恢复。Web Workspace、Desktop App、Mobile Companion 和 Public Website 按现有角色分别保留适用验收；未运行的设备/平台记为 `NOT_VERIFIED`，不代表省略目标。当前单视频轨限制需按多层画面目标实查：若妨碍 B-roll/叠加层，记录为能力缺口，不能将它固化成产品上限。

状态关系：选中clip后稳定clip identity与区间突出显示，Inspector切到该对象；播放头拖动/逐帧只更新Viewer与时码，不自动换选中对象。变更对象前若有未应用属性，先给Apply/Discard/Cancel。时间尺横向平移、缩放、seek与trim是四种独立动作；键盘/菜单提供选择、逐帧、入出点、播放头分割、修剪、缩放/横移及撤销/重做。正式快捷键必须由Editor owner冻结后才显示；在此之前不照搬Final Cut/Premiere键位。

#### SH-01 已有材料导入与处理确认（同一Owner）

~~~text
┌ 选择材料 → 文件概览 → 本次用途与范围 → 确认使用 ┐
│ 文件名/实际格式/字节（仅按picker/owner返回）       │
│ [在当前任务使用] [查看范围]                       │
│ 需要批准：具体内容、任务范围、用途/到期            │
│ [确认这份材料用于当前任务] [取消并保留项目]         │
├ 取得字节/解析进度（实际操作状态） ────────────────┤
│ 类型/时长/页数/streams/缺失或部分（只显示实际值） │
│ [打开当前素材] [回原任务]                          │
└───────────────────────────────────────────────────┘

首次CONTENT_SOURCE_APPROVAL_REQUIRED → owner确认 → ready_for_retry
→ 只重试同一 bytes + confirmation binding；不换文件/范围/用途
~~~

源文件选择、具名confirmation、重试与inspect复用SH-01现有Source/Artifact API；文件选择成功不等于入Evidence、解析完成或能训练。Cancel保留打开的项目/当前工作；超大/损坏/离线/不支持/partial需返回具体原因，不造页面数、duration、track或preview。Web/Desktop按各自已绑定picker运行；Mobile若未能传入真实byte则给出向桌面/Web继续入口，不模拟导入成功。

### SH-02 Evidence Library

~~~text
PC: Search/Source/日期filters | identity rows | platform-native Reader | Evidence chain
Phone: 搜索→来源列表→单篇原生Reader→来源/版本与返回
~~~

列表只显示真实取得的来源时间、采集时间、平台稳定ID、内容类型和可验证品牌关系。六种来源使用不同阅读结构，不能共用一张标题换皮卡片。点击作者/实体必须有真实relation；引用定位到原文/媒体可读位置。未登记/无正式 Evidence ref 的内部单帖草图只能作研究材料，不能显示成产品已经接入的记录。筛选空、未采集、仅预览、部分、过期、权利未知与服务错误分别呈现。

#### 六平台单帖阅读形态

下列六个截面承接 六平台单帖字符草图-v3.md（LOCAL_ONLY：`work/c1-w1-20261002/current-purpose-collection-outcome/per-post-character-sketches-v3/六平台单帖字符草图-v3.md`；未随本次归档发布）；每份原型只含一帖，不作为生产数据。视觉差异来自内容原生结构，而不是换色：

```text
小红书 · 多图笔记
┌ 当前图 03 / 图片序列 ← 横向滑动 → ┐
│ 标题 / 作者 / 时间（年份未知就写未知）│
├ 正文 + 原生话题 ───────┬ 赞藏评转原生计数 │
│ 图片序列/当前图说明     │ 评论→回复关系     │
└ source版本 / 图数冲突 / Evidence ───┘

抖音 · 竖屏长视频
┌ 9:16 Viewer · 时码 · 未完整观看状态 ┐
├ 作者/原始Caption                      │
│ 原生章节 | 已验证字幕/转写（若有）     │
│ 评论线程 | 指标版本 | 来源/Evidence    │
└ 不把平台AI章节当原文或转写 ──────────┘

微信公众号 · 长篇原文
┌ 文章题名 / 公众号 / 可得发布时间      ┐
├ 段落目录 │ 正文按原段落阅读与引用定位   │
│         │ 原图未取得/页面尾部保留状态  │
└ 原文版本 / 来源 / Evidence / 日期未知 ┘

Instagram · Reel + Caption
┌ 竖屏 Reel / 当前时码 / 原媒体状态      ┐
├ 原文Caption / 可切换的明确标注译文      │
│ 评论样本与总量分开 | 互动计数及版本     │
└ 作者/发布时间/来源与Evidence ──────────┘

X · 原语言短帖 + 多片段
┌ 原语言正文（主体） | 翻译辅助切换       ┐
├ clip 1 时码/海报 ─ clip 2 ─ clip 3      │
│ 单片段未观看状态 | 分版本指标           │
└ 来源/引用锚点/语言状态 ────────────────┘

Facebook · 完整帖子目标形态
┌ 作者/真实发布时间/完整原文 ─────────────┐
│ 真实返回的帖子媒体与原生顺序              │
│ 原生互动/回复 + 来源版本/Evidence         │
└──────────────────────────────────────────┘
当前样本预览态：
┌ 仅取得公开meta预览 · 全帖暂不可读         ┐
│ 正文/媒体/时间/互动分别标未取得           │
│ [打开原来源] [回列表]                     │
└ 不借用其他平台同品牌内容补齐 ─────────────┘
```

观测边界：XHS参考草图的已读图片数与 `image_count`/绑定链接数有冲突；Douyin全视频未观看；公众号原生页遇challenge，文本含页面尾部且图片/时间/计数未取得；Instagram Reel未完整观看；X的视频片段仅检查海报；Facebook只有meta预览。这些样本只说明partial/preview状态，不能取代上图对应的完整正常目标。

| 平台 | 完整正常结果 | 部分/权限/源失败的独立表现 |
|---|---|---|
| 小红书 | 全部真实返回图片、正文/作者/话题、评论回复和时间版本 | 实得图片保持可看；缺图/计数冲突不补造；评论样本、年份未知分别标 |
| 抖音 | 可播放完整竖屏视频与时码、caption、已核验转写/章节、评论回复 | caption可读但媒体/转写缺失时不隐藏正文，也不假称看完 |
| 微信公众号 | 全文与章节目录、内嵌图/链接和来源时间实际返回 | 摘录/页尾/challenge/图片缺失分开呈现，可回原来源 |
| Instagram | 完整Reel和caption，原生评论/指标与作者来源 | caption-only或评论抽样标明范围，媒体和总体互动未知不填充 |
| X | 原文与每个可用视频片段/时码对应，翻译分开且标来源 | poster-only时逐片段标未播放，不拼画面补内容 |
| Facebook | 完整帖子正文/媒体/发布时间/评论按真实响应布局 | meta预览仅作为预览状态，完整文本和媒体缺失字段逐项显示 |

六个平台只是当前验收基线，不是Reader视觉上限。其它已批准Source按原生内容类型与平台特有字段组合Reader，而不是“新增一个平台就复制一页”：

```text
Gallery / Image Post
Short Video
Long Video
Long Article
Short Text Post
Thread / Discussion
Audio
Listing / Page
Unknown / Unsupported
```

平台自己的author/native ID/topic/location/metric/reply等字段作为typed extension进入对应Reader；未识别类型保留来源记录与明确“暂不可读”状态，不丢掉或伪造一个平台。

每个正式Evidence item的来源动作统一为：`Trace → SourceTarget availability → Open Original → handoff state → Return`。如果 `URL_MISSING / INVALID_URL / DENIED / UNSUPPORTED / SOURCE_WITHDRAWN / STALE / UNKNOWN`，Reader只显示真实原因；不放裸URL按钮。`HANDOFF_ACCEPTED`不等于来源页已成功加载。Return恢复SH-02原Space/List模式、query/filter、选中item、scroll/camera和键盘焦点。

该参考集的 `source_scope=UNASSIGNED`、正式 Source/Evidence/Canonical refs 为空，commercial=`UNKNOWN`、`TRAIN=NOT_GRANTED`、design_state=`DESIGN_EXPLORATION`、frontend_implemented=`false`。只采用内部阅读层级，不复制正文、账号或媒体到产品/官网，不作训练输入。

### SH-03 Canonical Data/Metric browser

~~~text
PC: Registry/schema tree │按字段搜索 │field definition/metric/lineage
Phone: 搜索字段或metric→定义→逐级来源链
~~~

显示owner、period、unit、derived/observed区别、source IDs和unknown原因；浏览是只读的。

### SH-04 Artifact/Export center

~~~text
PC: Task/类型/状态filters │已保存版本序列│文件专属Viewer │父版本/Source/状态
    选中版本→对比变化/受影响的下游→保留/另存新版本/打开原件
Phone: Task成果列表→版本/差异全屏→回原任务/继续编辑
~~~

视频/音频/文档/研究成果各有自己的预览。显示当前版本、父Brief/task、Source locator、更新时间、保存状态与设备归属；原始用户文件路径不跨设备暗同步。重开失效时保留条目和错误原因。

未保存草稿与服务端版本冲突时进入可撤回比较态：左边当前草稿、右边已保存版、中央逐项差异/来源/被改动的预算或媒体位置；提供“打开已保存版”“把本机稿另存为独立版本”“稍后处理”，不自动覆盖/合并。超时后回查同一Artifact/Task id；效果回执未知不得重复发送外部操作。源被撤回/权限过期时旧版本保留并标记当前不可用/待复核。

### SH-05 Evaluation/Learning

~~~text
PC: 结果/Outcomes | 待评估候选 | 已验证/拒绝/退休版本
选择一项→评估数据/方法/样本范围/反例→父版本/差异/审批/回滚状态
Phone: 候选/版本状态→证据与评估依据→可执行回原Owner的审阅动作
~~~

AI/系统提出变更仍是candidate；展示使用的Source/Outcome/Evaluation版本、样本分母、失败/反例和目标变化；区分shadow通过、需复核、Rejected、Promoted、Rollback。当前SH-05是scope-guarded read-only shelf；终态审阅/推广必须通过Existing Learning/PROMOTION owner和服务端批准，当前不画能直接改规则的写按钮。原Evidence/Canonical及旧版本不自动改写。

### SH-06 Inbox/Notifications

~~~text
PC: 待我处理 | 运行中的Task | 新结果/提醒 | 阻断/延期
列表行：真实来源/范围/发起时间/到期/状态 · 选择→右侧任务详情
Phone: 分lane通知列表→原Task/Approval/Artifact全屏→Return回原条目
~~~

目前Inbox为只读且要求verified origin；不显示无来源徽标/虚构总数。打开审批项回到原始业务操作让原Owner作决定；SH-06本身不Approve/Assign/Snooze/Retry。如果将来已有通知owner返回具体允许动作，则按钮/撤销方式由该action在原Task的Effect boundary控制，返回同一Task/状态；未接入时只可标“打开原任务”，不把卡片点开等同处理完成。

## 全局逐屏验收绑定

以下记录用于后来把文字草图转成实机验证卡。OWNER由既有边界决定，不以本文新造服务：

| 屏组 | 具体用户目标 | 真实操作 | 回执/恢复 |
|---|---|---|---|
| ACC | 打开/切Focus/回到入口 | LaunchSurface和持久化任务/筛选 | 失效不锁整个应用；返回路径保留 |
| CTH | GLOBAL/可选Focus中人工搜索来源、打开单帖、推进Case/Decision/Report | CTH-03只读确认→现有POST→按稳定platform_id筛选→Reader→原来源返回 | 接线真实、Scope/Evidence完整、原文缺件诚实、100条partial不冒充全量；失败/撤权安全恢复 |
| BMP | 从Market/Brand Evidence到Campaign/成品 | Brief、Creator和内容版本编辑 | 保存、Review、Effect approval和Outcome |
| AI | 从用户目标到有引用Artifact | 真实能力调用、任务阶段、人工修订 | cancel/failure/unknown分开，草稿/引用仍在 |
| SYS | 身份授权、采集状态、浏览器边界、日志和恢复 | SYS-02真实只读状态；SYS-06按许可来源动作；跳回原任务 | 不从状态页造控制；会话失效/撤权不越权、不抹Evidence |
| SH | 搜索/阅读六平台单帖来源，进入既有研究或创作 | SH-02类型化Reader→引用锚点→BMP/CTH/Brief→保存/重开 | 六平台各自保持原生结构；未获Source refs/权利不作生产/官网/训练材料 |

每次上线审核需将此表具体化为当前ScreenSpec/Test ID/真实输入/服务返回及各端设备操作。该文件仅构成设计和流程输入，不会自动把设计状态提升为DESIGN_READY或用户验收。

## 2026-10-08 Intelligent UI 逐屏视觉与动线增补

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

本节追加在历史草图之后，不覆盖旧修订或逐屏内容。每屏使用任务适配的组合式布局，避免统一卡片模板。序境二维手绘、水彩与版画色彩感仍是视觉语言，线性控件保持功能含义；角色依用户当前Brief/脚本描述创作，只借鉴手绘平面笔触与色彩，不复制参考人物，不用3D质感。色彩可丰富但不滥用，插画不表示数据真假、风险或授权状态。

以下图示是文字视觉草图。字段与操作仍由对应Spec已绑定Owner提供；缺失项如实显示UNKNOWN/UNAVAILABLE。Web、Desktop、Mobile共享Product Core和上下文、按端侧任务重排；Public Website只承载已验证的公开能力或标记示例。非官网避免无必要纵向滚动，保留可访问性和长内容所需滚动；视频/播客Timeline横向拖动。

### ACC-01

**任务：** 确认内部工作区入口可用并继续宿主指定目标。

~~~text
主路径: 显示入口状态与宿主提供的继续动作；无 callback 不伪造路由或账户流程
延续: 传递宿主实际 route 与原任务位置，失败时保留入口
端侧: Web接浏览器route；Desktop回原窗口；Mobile恢复原任务；官网只说明公开入口
失败恢复: 身份失败、离线、callback缺失分别标识；重试仅读取identity
验收: 有/无真实callback分别验证；只有真实导航成功才报告继续
~~~

### ACC-02

**任务：** 查看当前GLOBAL_ALL或明确选择一个可访问Subject视角。

~~~text
主路径: 列表、当前视角和确认预览并置；说明选择不授予业务读取权限
延续: 只有服务端确认的scope envelope传递给下游，切换后回原工作
端侧: Web/Desktop提供目录与预览；Mobile逐项选择；官网不展示私有目录
失败恢复: 拒绝/目录错误保留原scope与草稿，不本地切换
验收: 无选择为GLOBAL_ALL；合法FOCUS服务器确认；拒绝无业务读取
~~~

### ACC-03

**任务：** 从首页开始真实工作或继续原任务。

~~~text
主路径: 以任务、草稿、已访问页面和既有工作流组织，不做KPI营销模板
延续: 恢复Task/Brief/scope/Artifact版本，建议只开草稿不触发效果
端侧: Web多区并读；Desktop快捷续接；Mobile突出一个待续任务；官网只作公开介绍
失败恢复: 空、失效链接、离线、权限过期独立呈现，保留原任务状态
验收: 新建/续接/空记录三路径；不会强迫选择焦点或误报恢复
~~~

### ACC-04

**任务：** 理解一项真实阻断并沿已有恢复路径返回。

~~~text
主路径: 展示发生了什么、影响哪个任务、已绑定的恢复路径
延续: 关联原Task、请求scope、operation与恢复receipt，保留未提交内容
端侧: Web/Desktop并列工作与受控说明；Mobile按阻断→影响→恢复；官网不显示内部诊断
失败恢复: unbound明确unavailable，不跳到AI或其他页绕权限
验收: 拒绝、重试、恢复后均回原任务；无receipt不称恢复
~~~

### AI-01

**任务：** 把用户目标、当前资料与约束组成可检查的执行意图。

~~~text
主路径: 自然语言目标与现有Brief/Evidence/scope/Budget/缺项并列；建议可编辑拒绝
延续: 沿用同一Task/Brief/引用/Actor/scope；真实结果返回execution ID及Evidence状态
端侧: Web/Desktop并看输入与资料；Mobile逐项确认；官网仅公开且标注示例
失败恢复: 未绑定、拒绝、部分、取消、效果未知分开；未知时查同ID不自动重提
验收: 复用资料不要求重选；无授权或服务时无伪造Evidence
~~~

### AI-02

**任务：** 跟踪真实任务阶段与持久化产物。

~~~text
主路径: 按服务端实际状态组合阶段轴、当前输出和Evidence/Artifact检视
延续: 同一run/model/recipe/input scope版本贯穿恢复与保存
端侧: Web/Desktop阶段轴加检视；Mobile聚焦当前阶段；官网不呈现内部运行
失败恢复: 取消/失败/等待/效果未知分开，断线后按原run ID查询
验收: 阶段只能随真实回执推进；无action binding按钮不可用
~~~

### AI-03

**任务：** 逐条核验分析结论的来源并继续修订。

~~~text
主路径: Claim—Citation—不确定性阅读，围绕一个结论局部修订
延续: 保留Evidence ID、source locator、scope和父版本；下游复用同Brief
端侧: Web/Desktop消息与引用并读；Mobile先结论后引用；官网不显示私有讨论
失败恢复: 撤源时对应结论需复核，草稿可恢复，未绑定Case/发布不显示
验收: 结论可回源；撤回标记准确；修订保存新版本而不覆盖事实
~~~

### AI-04

**任务：** 查找适合当前任务的已验证能力，并按现有 Owner 合同完成已批准的使用与生命周期操作。

~~~text
主路径: 呈现能力输入/输出、版本、许可、风险与评估；当前目录只读，已批准的启用/运行/更新/停用等操作按现有 Skills owner 补齐，缺口保持 OPEN
延续: 保留既有 skill ID/version、输入和原 Task；每个生命周期/运行操作单独经过既有 Permission，不因选择而授权
端侧: Web/Desktop目录与详情；Mobile显示当前Task可用能力；官网只列已验证能力
失败恢复: 退役/未绑定/风险未知项不可执行，旧信息标stale
验收: 条目状态真实；选择能力不产生权限或安装效果
~~~

### AI-05

**任务：** 查看AI服务真实状态和延迟样本。

~~~text
主路径: 脱敏状态、采样时间及有界延迟；不显示原始provider/model
延续: 诊断与具体业务任务版本分开，不把诊断数据写回任务
端侧: Web/Desktop状态与样本；Mobile显示当前状态；官网不暴露拓扑
失败恢复: 缺失不为0，fallback仅按现有明确合同，过期/离线分开
验收: 验证安全投影和fallback条件；不宣称模型质量或业务可用
~~~

### BMP-01

**任务：** 回答授权品牌的市场信号与值得关注的趋势。

~~~text
主路径: 市场脉冲、趋势候选和证据抽屉；给时间窗、样本与来源覆盖
延续: 品牌/global scope、Evidence、采集时间和指标版本随同一Brief进入方案
端侧: Web/Desktop信号与来源并读；Mobile先优先信号再证据；官网只讲已验证能力
失败恢复: 未授权、样本不足、撤源时隐藏结论，unknown不补零
验收: 从信号回源并继承资料；推荐不能直接成为决策
~~~

### BMP-02

**任务：** 理解品牌组合、子品牌与竞品关系。

~~~text
主路径: 带来源关系图加选中实体档案，明确已核实/推断/未知
延续: 每条边保留BrandFocus、entity ID、关系来源和版本
端侧: Web/Desktop图和档案；Mobile可展开关系列表；官网不展示私有谱系
失败恢复: 跨焦点、来源缺失或过期关系不显示为事实
验收: GLOBAL/FOCUS授权分别成立；本地选择不改谱系/授权
~~~

### BMP-03

**任务：** 识别需要进一步验证的机会信号。

~~~text
主路径: 置信/动量图、排序清单和来源简报并置，解释排名依据
延续: 信号ID/来源/窗口/scope/评分版本随同一Brief传给提案
端侧: Web/Desktop图、列表、简报并读；Mobile排序原因后详情；官网仅公开审定案例
失败恢复: 窗口不可比不画坐标，失效候选保留旧版并提示复核
验收: 信号回源且不执行推荐；无owner动作不新增提案
~~~

### BMP-04

**任务：** 看品牌传播链哪些阶段实际有观测。

~~~text
主路径: 左到右渠道路径与定义矩阵，每阶段区分observed/unavailable
延续: 渠道、单位、来源、时间和品牌范围绑定；选中渠道不改归因事实
端侧: Web/Desktop河流和矩阵；Mobile逐阶段下钻；官网不呈私有数据
失败恢复: 缺阶段不为零、不同比较窗不合并；scope变化清旧缓存
验收: 同窗口切换渠道可回位；不从相关性宣称因果
~~~

### BMP-05

**任务：** 比较创作者匹配度和风险依据。

~~~text
主路径: 按已返回KOS/KOL/KOC/UGC类别呈列表和来源档案
延续: 指标定义、时间、BrandFocus、来源及评估版本进入后续任务
端侧: Web/Desktop列表与档案；Mobile先理由后样本；官网仅授权案例
失败恢复: 同名和跨焦点隔离，样本不足未知；无联系/支付动作
验收: 候选逐项可追来源，切scope后旧档案不残留
~~~

### BMP-06

**任务：** 把授权素材和内容想法推进为可审阅版本。

~~~text
主路径: Draft→Review→Approved→Delivered专属编辑流程，来源/rights贴近正文
延续: 继承同Brief/Evidence/品牌/语言；修改保存子版本和受影响片段
端侧: Web/Desktop正文与证据并读；Mobile聚焦待审与修订；官网不编辑内部稿件
失败恢复: rights未知/授权不足时阻止对应动作，离开保留草稿
验收: 真实brief到修订子版本再重开；AI草稿不标批准或已发布
~~~

### BMP-07

**任务：** 连接活动目标、预算、里程碑和实际结果。

~~~text
主路径: 目标→受众→渠道→预算→Outcome时间线；估算/承诺/实支各自分层
延续: 预算/日期变化定位受影响活动段、素材、资源和日程，父版可回滚
端侧: Web/Desktop编辑计划和影响预览；Mobile逐项审预算；官网仅公开示例
失败恢复: 无真实活动不造ROI；预算变化不触发付款/发布，冲突可回父版
验收: 修改后只有受影响内容变化，新旧版本可重开比较
~~~

### BMP-08

**任务：** 把授权来源变成可审阅脚本及可编辑播客音轨。

~~~text
主路径: 脚本、来源、rights、音轨和发布状态分层；横向拖动时间轴
延续: 同Brief/来源/audio version连续；本地Read Aloud不等于成片
端侧: Web/Desktop脚本与音轨并列；Mobile分段查看；官网只放授权成片
失败恢复: 源/版权未知不导出；scope/文本变更停止本地朗读
验收: 保存重开实际工程，改一段不损其它段；无回执不称完成
~~~

### BMP-09

**任务：** 理解品牌评估变化、置信和覆盖情况。

~~~text
主路径: 维度、真实Outcome、置信、分母和方法并列，文本意见不冒充分数
延续: 绑定原Outcome/Evidence/评估方法与版本，不改写源事实
端侧: Web/Desktop可比较维度和周期；Mobile逐维度和来源；官网只发布审核结果
失败恢复: 未评估/样本不足为UNKNOWN；历史版本保留但可标stale
验收: 分数可回样本和方法，结果变化生成新版本，不自动Promotion
~~~

### BMP-10

**任务：** 按严重性、扩散和时效处理有证据的品牌风险。

~~~text
主路径: 风险队列、原始依据、派生判断、后续状态分开
延续: 绑定品牌scope、Evidence、判断版本与决策receipt
端侧: Web/Desktop队列和详情；Mobile先风险依据和原文；官网不呈私有风险
失败恢复: 笔记不升级成事件；来源撤回保留历史并停止当前效果
验收: 观察与判断分开；无批准/Effect receipt不称已响应
~~~

### BMP-11

**任务：** 在口径一致时比较品牌基准。

~~~text
主路径: 先展示币种/期间/口径/分母，再显示可比矩阵和差距
延续: 每格保留定义、币种、样本、来源、范围、计算版本
端侧: Web/Desktop多品牌矩阵；Mobile逐项查看口径；官网不公开客户比较
失败恢复: 不一致即待核而不排名，未知值不补零
验收: 条件变化使旧排名stale；无可比数据明确说明
~~~

### CTH-01

**任务：** 查看商业运营活动并检视单个事件。

~~~text
主路径: Subject/context、运营脉冲、事件流和选中详情组合
延续: 保留scope、时间窗、event ID和来源锚点；下游继承相同范围
端侧: Web/Desktop流和详情并读；Mobile按脉冲→事件；官网不显示私有运营
失败恢复: 无权限、空、未采集和错误分开；切主体清除旧数据
验收: 事件返回同一位置；不从时间顺序推因果
~~~

### CTH-02

**任务：** 浏览商业主体目录与已核实关联。

~~~text
主路径: 主体列表和有证关系档案；资料暂缺不能由名称猜补
延续: 目录选择元数据不更改live Subject；正式切换经ACC-02确认
端侧: Web/Desktop列表和关系档案；Mobile搜索展开；官网不公开内部名录
失败恢复: 关系无source则资料暂缺；读权失败不推断主体不存在
验收: 目录读与主体业务权限分开；不借静态目录授权
~~~

### CTH-03

**任务：** 查看监测变化、平台lane并阅读一条信号。

~~~text
主路径: 时间窗脉冲+Collector lane+单条reader；平台热度与自有样本分开
延续: 原始platform ID、发布时间、采集时间、scope、Evidence进入Research
端侧: Web/Desktop流与lane检视；Mobile先变化后单条；官网只讲已验证采集
失败恢复: 验证码/登录墙/限流仅阻断对应lane；保持原帖定位
验收: 允许时打开原文并返回同信号；无授权不得起采集/导出
~~~

### CTH-04

**任务：** 理解事件先后和证实的关系边而不推因果。

~~~text
主路径: 实际时间轴与有证关系图切换；选节点看原来源
延续: 保留事件ID、源时间/capture time、relation version
端侧: Web/Desktop时间轴/关系图；Mobile按时间下钻；官网无内部事件图
失败恢复: 部分返回标partial；缺证据不画边；scope切换清旧图
验收: 节点回源且返回定位准确；不做因果或写入动作
~~~

### CTH-05

**任务：** 寻找真实变化日期并查看当日样本。

~~~text
主路径: 真实日密度与当日列表关联，标记分子/分母/窗口
延续: 保留scope、日期、时区、metric定义和source
端侧: Web/Desktop日历+列表；Mobile日期摘要后列表；官网不显示内部日历
失败恢复: 零/无数据/未采集/失败区分，缺分母不画热度
验收: 点日准确过滤当日样本；缺失日期不自动为0
~~~

### CTH-06

**任务：** 分拣反馈并读原始措辞。

~~~text
主路径: triage队列加原文Reader；派生类别可编辑且不等于事故/Case
延续: 保留原文、平台时间、Evidence、scope及人工/AI分类版本
端侧: Web/Desktop队列与原文并读；Mobile逐条打开再回队列；官网不呈私密反馈
失败恢复: 未分类保持待分类；撤源标需复核，不删原文
验收: 分类与原文可分别核对；无Case receipt不称已建Case
~~~

### CTH-07

**任务：** 解读有定义指标在特定窗口内的变化。

~~~text
主路径: 图表、表格、分母/定义/单位/时间/来源并列
延续: 同指标和scope进入分析；解释带同一Evidence版本
端侧: Web/Desktop图与定义表并读；Mobile看变化再展开数据点；官网只用核准公开数
失败恢复: 空值/缺分母/stale/error不转0；不同比较窗阻止趋势
验收: 图表表格一致可回源；没有归因证据不解释原因
~~~

### CTH-08

**任务：** 追踪真实Case到Outcome并区分复用知识。

~~~text
主路径: Case→Insight→Decision→Action→Outcome泳道；知识独立显示审阅状态
延续: 所有节点绑定同一canonical Case/scope/来源和版本；知识不覆盖事实
端侧: Web/Desktop全链和知识并看；Mobile逐阶段返回；官网不露私有Case
失败恢复: 没有canonical Case不以note替代；receipt未知留待核
验收: 父子阶段可追踪，未发生步骤不显示完成，知识有审阅依据
~~~

### CTH-09

**任务：** 区分风险依据、决策状态、审批和实际动作。

~~~text
主路径: 风险、Decision ledger、Action receipt分区显示提案到执行状态
延续: 沿用已有Actor/scope/approval/effect ID，不为风险创建平行任务
端侧: Web/Desktop并列风险与账本；Mobile先状态再依据；官网不露内部审批
失败恢复: 未经批准无执行控制；effect UNKNOWN禁止重试并保留上下文
验收: 服务端状态一致；真实Outcome/Evaluation才能称闭环完成
~~~

### CTH-10

**任务：** 创建或重开有来源的运营简报并检查结论。

~~~text
主路径: 正文/方法/引用/Action-Outcome分页阅读；从同一SourceBrief Job重开
延续: 沿用job/report/hash/brief/evidence/scope/父版；源失效局部复核
端侧: Web/Desktop正文与来源栏；Mobile逐页返回；官网仅审批公开版；朗读限当前绑定文本
失败恢复: ACK丢失查询同ID；无导出回执不称导出成功；换scope/hash停止朗读
验收: 保存重开后逐条回源；段落修改成子版本，不丢方法引用
~~~

### SH-01

**任务：** 发现共享能力并进入当前研究/创作/媒体工作。

~~~text
主路径: 当前Task→已绑定能力→原生Reader/编辑器；Timeline/ShotPlan保留专用工作区
延续: 沿用Brief/SourceTarget/Evidence/Artifact/timeline版本，目录本身不执行
端侧: Web/Desktop承担并读与复杂编辑；Mobile任务摘要后打开素材；官网只列已证能力
失败恢复: 能力未绑定不运行；时间轴冲突可撤回；取消保留未应用编辑；朗读只预览当前字幕
验收: 同源进入后保存/重开；timeline横向拖动，未授权Action不可执行
~~~

完整媒体结果补充：继承同一 Task/Brief/Source/Evidence/rights，进入原生视频 Viewer 与可横向平移/缩放的 Timeline；支持真实素材选择、拖放、修剪、分割、删除、重排、字幕与多层画面/声音编辑；检验单视频轨是否阻断 B-roll/overlay，不能把实际限制写成产品目标。时间轴编辑后的实际 Viewer/时码、临时预览导出、正式 SavedWork/Artifact 和重开后的确切版本必须分开标识；Undo/Redo 恢复实际编辑，正式子版本保留并可回放父版本。真实授权媒体完成端到端操作；四端按现有产品角色逐一验收，未验证端保持 `NOT_VERIFIED`。

### SH-02

**任务：** 检索并阅读同一组有来源研究材料。

~~~text
主路径: 按平台原生形态组合图文/长文/短视频/线程/音频Reader
延续: 保留Source/Evidence/platform ID/scope/time/rights；进入Brief不重搜
端侧: Web/Desktop列表与Reader并行；Mobile搜索→列表→单篇→原位返回；官网不载内部资料
失败恢复: 缺字段留unknown；poster-only与完整视频分开；撤源留历史并标不可用
验收: 六平台显示原生结构且字段诚实；跨到Research/Creation引用不丢
~~~

### SH-03

**任务：** 理解Canonical指标定义、成熟度和Source链。

~~~text
主路径: Schema/Metric树加逐级lineage，不展示原始DB表/路径
延续: 查询沿用GLOBAL/FOCUS读权，Metric版本和Evidence引用可带入分析
端侧: Web/Desktop树+关系；Mobile搜索→定义→来源；官网仅展示公开核准口径
失败恢复: 链路断点指出具体层；未授权不读全局计数；不提供修复
验收: 值/单位/定义/来源一致，页面保持只读
~~~

### SH-04

**任务：** 重开真实Artifact、比较版本并回到原Task。

~~~text
主路径: 类型化Viewer和版本序列展示父版、来源、局部diff
延续: Artifact ID/hash、父Brief/Task、scope、source refs保持一致；本地朗读只读READY重开文本
端侧: Web/Desktop专属Viewer；Mobile成果→差异→原任务；官网不提供私有Artifact
失败恢复: 超时查询同ID；失效来源保留旧版本；非persisted/blocked不下载或朗读
验收: 重开版本与差异准确，回原Task；无Effect receipt不报导出成功
~~~

### SH-05

**任务：** 审阅学习资产的样本、方法、反例和生命周期。

~~~text
主路径: candidate/verified/rejected/promoted/rollback证据流，页面只读
延续: 引用Outcome/Evidence/Evaluation及父版；Promotion回Learning owner审批
端侧: Web/Desktop候选和版本差异；Mobile状态→依据→原Owner；官网无内部资产
失败恢复: 样本不足不显示通过；权限/范围缺失保持阻断
验收: 每个状态有可定位证据；本页不能自主推广或改写源
~~~

### SH-06

**任务：** 从任务/通知/警报返回原业务工作。

~~~text
主路径: 任务、通知、警报分lane，选中呈来源/scope/状态/下一步
延续: 保留原Task/Notification/Artifact ID和origin，打开回原任务
端侧: Web/Desktop列表+详情；Mobile lane→原工作→返回同一条；官网无内部通知
失败恢复: 来源或actor range不明不显示；无owner支持不提供审批/重试
验收: 完整往返同一条目，真实授权计数；失败不变0/已处理
~~~

### SYS-01

**任务：** 读RuntimeGuardian状态和Worker/DLQ保护指标。

~~~text
主路径: health snapshot按整体→队列→防护解释，采样时间在场
延续: 同一guardian/source/timestamp；业务指标不得混入
端侧: Web/Desktop状态脊柱；Mobile故障优先；官网不承诺内部健康
失败恢复: offline/degraded/partial分开；无操作绑定不显示重启
验收: 真实采样值和时间一致；旧快照不充当前状态
~~~

### SYS-02

**任务：** 查Collector各平台lane和进入Evidence的真实状态。

~~~text
主路径: 平台manifest/lane/attempt/receipt显示configured/active/partial/blocked
延续: 关联真实Collector task与Source/Evidence receipt，不伪造覆盖率
端侧: Web/Desktop矩阵和单lane详情；Mobile按平台读；官网只讲验证过能力
失败恢复: 挑战/身份/限流阻断单lane，刷新失败标stale
验收: 读出与receipt一致；页面不查看Cookie或触发无绑定重试
~~~

### SYS-03

**任务：** 核对schema、integrity、readability与Truth chain层次。

~~~text
主路径: 分别呈schema、自检、应用读取、链路阶段，不给总绿灯掩盖缺口
延续: 绑定实际check/time/chain ref；不泄漏DB路径/业务行
端侧: Web/Desktop分层检查；Mobile阻断优先；官网不呈系统诊断
失败恢复: 数据库不可读或检查失败只读报告，不执行迁移
验收: PASS/UNKNOWN/ERROR各自有证据；无误报健康
~~~

### SYS-04

**任务：** 安全理解允许范围和审计可用性。

~~~text
主路径: allowlisted安全级别、控制化scope与audit状态，不显示策略细节
延续: 真实permission仍按Actor/scope/operation服务端判定，本页不授予权限
端侧: Web/Desktop访问姿态+审计；Mobile逐行展示；官网不露策略
失败恢复: scope未知为未确认；鉴权错不泄漏敏感原因；不提供写操作
验收: 任何画面交互均不改变权限；无证据不显示audit ready
~~~

### SYS-05

**任务：** 调整设备外观并返回相同工作状态。

~~~text
主路径: 本地偏好预览/对照/撤销，配色和壁纸只影响本端呈现
延续: 保持route/scroll/selection/draft；偏好使用现有本地owner，不变业务数据
端侧: Web按网页本端；Desktop适配窗口；Mobile适配触摸；官网使用公开品牌视觉而非用户私有壁纸
失败恢复: 持久化失败不称已保存；撤销回旧偏好；壁纸不上传、不写Evidence
验收: 四端偏好不串scope，预览保存重启恢复分别可验证
~~~

### SYS-06

**任务：** 在原任务授权范围内读取和操作受控来源，完成必要的验证并返回原任务。

~~~text
主路径: 按真实 capability 显示地址、当前来源、页面与允许操作；RecoverySheet 需要 LOGIN_FORM/VERIFY 时承接受控交互，再交还 PlatformSession 健康复核；不露账号/profile/port/path
延续: 保留 Task/来源/target/page revision，返回恢复草稿和选择；来源保存经既有 Evidence owner，浏览画面不自动成为 Evidence；不接触私人 profile
端侧: Web/Desktop 承接授权浏览与原 Task；Mobile 适配已批准的阅读/验证/返回流程，能力不具备时保留 OPEN 而非永久只读；官网不执行内部浏览
失败恢复: 不可用即明确提示，不用外部个人浏览器伪装；人机验证走现有受控流程
验收: 不泄密、无未绑定打开动作；失败回原Task并保留原因
~~~

### SYS-07

**任务：** 检查实际Evaluation gate证据和未完成项。

~~~text
主路径: check→scope→run version→Evidence→状态，分开blocked/unknown/pass
延续: 关联实际Evaluation版本；审批推广由相应owner执行
端侧: Web/Desktop检查与证据；Mobile先阻断；官网只讲真实验证能力
失败恢复: 无样本/证据不足非通过；本页不启动测试或发布
验收: 状态可追到证据；空清单不显示pass
~~~

### SYS-08

**任务：** 查看脱敏日志目录和可追溯Trace。

~~~text
主路径: 仅呈实际inventory/时间/结构化trace；无trace不画假图
延续: trace绑定合法Task/run ID后回原任务；路径和秘密在投影前脱敏
端侧: Web/Desktop摘要与trace；Mobile按Run查看；官网不公开日志
失败恢复: 文件损坏/权限不足不导出原始日志；旧数据标stale；不清理
验收: 真实trace存在才呈现且可回Task；无绝对路径/秘密
~~~

### 跨屏视觉与任务连续性

```text
真实任务 → 同一 Task / Brief / Actor / Scope → Source / Evidence / 版本
→ 适配本屏的文字/图表/阅读器/编辑器/时间轴 → 可检查、可编辑、可拒绝的建议
→ 现有服务端 Owner + Permission + Effect Fence → Action / Artifact / Outcome / Evaluation
→ 保存新版本 → 原任务重开 → 仅修订受影响内容 → 恢复或回滚
```

研究进入制作时继续使用同一批资料和约束，不让用户重述目标、重选来源或重复核查。预算、来源或scope改变后，应指出具体受影响内容，显式采用新版本并保留父版本、修订原因和回滚。部分、失败、拒绝与效果未知不能被成功动画覆盖。此草图是设计输入，不改变ScreenSpec review status，也不证明实现、四端运行或用户验收。

### 2026-10-08 前端审计与工具维护增补

采用用户本轮前端审计中的可编辑设计→屏幕规范→真实源码→验收证据链，细则归 Experience §38 及原44份ScreenSpec/README。保持原 Blueprint、Owner、DESIGN_EXPLORATION→DESIGN_READY→IMPLEMENTED→ACCEPTED，不建立第二设计真相。Figma实际文件/节点/版本本轮 NOT_VERIFIED；不以本地无 .fig 推断云端无工程。此段原审批时的等待状态已被2026-10-08直接恢复指令取代；当前窗口按AGENTS实际派工继续。草图自身不控制全局暂停或恢复。

工具维护保护现有模型/effort/tier、登录方式、权限、网络/代理及会话；只更新核实的稳定兼容版本，开发插件不变成产品依赖。需要中断桌面/会话、重启、扩大权限或新增登录/费用时等待精确批准。既有未发布源代码、私有配置及生产DB保持原边界。

## 2026-10-08 逐步呈现动线补充（文字设计输入）

用户提交同一目标→先出现可信摘要/已核实比较项→原位置逐块补充来源、分析与可操作参数→用户调整时保留输入与选区→只更新相关内容→明确采用保存版本→关闭重开。屏幕不整体闪烁/抢焦点/强制滚动，阶段性内容及未完成处清楚分层；日期未知与缺数值“—”保留维度和原因。图表/计算器/时间轴/阅读器或纯文本按本屏任务选，不画第二套通用模板。

这些是原草图的动线说明，未重绘美术资产、未创建Figma版本、未自动晋升DESIGN_READY。准确规则唯一归Experience §38；适用全部既有屏幕，复杂视频/播客仍使用完整编辑工作区。

### 2026-10-08 SYS-06 视频适配动线（非独立设计权威）

手机：[返回当前任务｜任务名称｜更多/外部打开] → [安全网址与目标状态] → [真实受控页面，占主要可用空间] → [接管操作｜停止任务] → [实际当前动作｜Live或历史时间｜事件条]。键盘弹起/横屏保留返回与控制，允许页面内容必要滚动。回到任务保留原Brief、来源、草稿和位置。

桌面/Web：[原任务/返回 + 来源工具栏] → [产品内真实页面 + 可收起的操作/证据侧栏]；用户可选外部打开，失败不自动弹出。电脑任务显示真实获准设备/应用范围；浏览页面与OS操作分别证明。颜色、图标、动效使用序境既有风格，不能照抄视频品牌外壳。视频只观察到任务切换、浏览器页面、操控入口和Live/事件条，未演示外部打开、恢复或OS应用控制；上述完整要求来自用户及当前规范。
