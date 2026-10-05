# LUMENIS 44 个既有屏幕：逐屏文字视觉草图

与同目录《LUMENIS 前端最终目标与执行蓝图》1.5 逐项对应。本文件覆盖 44 个既有 Screen ID，作为完整业务能力的审查索引，不承诺最终产品固定恰好 44 个页面；适用时用当前页内抽屉、模态、播放器层、时间线状态表达，不复制造页。本文只用字符/区域说明目标形状、字段优先级、主次动作和关键状态；不是正式视觉稿，也不要求当前就编码。

## 当前状态读法

- 当前核对基线为 `main = origin/main = refs/heads/main = 0c9394ef442cc9ec40e65204c72afa8ad3557959`。`c7765b87`、`1b238c2f`和`0c9394ef`为治理/归档审阅提交，未修改前端Screen/API媒体/采集源码；当前静态源码快照有44个App Screen源文件；44份Screen-specific规范与ID对应。
- Binding registry 生成源早于该 HEAD，历史状态为 Acceptance Pending；本任务没有运行产品、读取生产 DB、重跑绑定或任何产品 E2E。
- 下方 `Screen Spec.status` 是屏幕规范/设计评审状态（例如 `DESIGN_READY` 或 `BLOCKED`），不是产品实现、服务可用或运行验收状态。每行同时保留源码/验收缺口与直接链接。
- R01–R15/J1–J8/U01–U25 到本产品屏幕/流程的审阅导航见同目录主方案 §6.7；这些代码不是新的页面标签，也不会自动标为通过。
- Website/Web/Desktop/Mobile与Windows/macOS/Linux、Android/iOS的职责和1920–360尺寸重组见主方案§4.3；本文件各屏线框为任务-specific形状，非操作系统通用模板。各ScreenSpec链接含当前Owner/状态/Binding及其实际提供的locale keys；主方案§3.4补足本目标中新增的字段、状态和辅助文案映射。
- 页面字段是语义槽位；owner 不返回或语义未知时保留未知/缺失，不自行发明值。真实数据、授权、失败恢复、保存/重开、跨端续接和用户结果仍需各自的真实验收。
- 以下每屏的字段都是语义槽位；若当前 owner 不返回或语义未知，显示缺失状态，不自行发明值。
- 逐Screen的zh-CN/en/ko-KR目标标题、主要动作及核心状态词映射见主方案 §3.4；本文件中的 `GLOBAL/ALL`、Owner、Evidence、Viewer 等是审核/字段 shorthand，不是要求直接显示为技术大字。

## 五位架构视觉角色索引（主方案 1.5 / §3.3）

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
| BMP-08 | Shared Audio / Artifact / AI Gateway when available | 文件音频、脚本、时码、speaker/track、render/export | screen/UI actions存在；文件播放/混音/版本E2E未完成于本轮；live mic后置 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-08.md](../../../../contracts/experience/screen-specifications/BMP-08.md) |
| BMP-09 | BMP Evaluation / Metric / Evidence | 品牌维度、基线、期间、coverage、confidence来源 | screen source存在；不可比和缺分母需验 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-09.md](../../../../contracts/experience/screen-specifications/BMP-09.md) |
| BMP-10 | BMP Brand Risk / Event / Permission | 事件证据、责任、response draft、Effect状态 | screen source存在；未批准的response不执行 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-10.md](../../../../contracts/experience/screen-specifications/BMP-10.md) |
| BMP-11 | BMP Benchmark / Metrics / Evidence | 对象集合、统一metric定义/期间和来源 | screen source存在；单位/口径不兼容时状态未知 | owner_domain=BMP; status=OWNER_REVIEW; no BACKEND-GAP ID in frontmatter; [BMP-11.md](../../../../contracts/experience/screen-specifications/BMP-11.md) |
| AI-01 | SYSTEM AI Gateway / Context / Source-Evidence / Artifact | 用户任务、许可材料、可调用能力/当前route | screen source存在；本轮未运行任何真实任务 | owner_domain=Shared Capability / AI Agent Groups; status=BLOCKED; BACKEND-GAP-029, BACKEND-GAP-030; [AI-01.md](../../../../contracts/experience/screen-specifications/AI-01.md) |
| AI-02 | SYSTEM Agent Runtime / Task Queue / Artifact | stage状态、step inputs/outputs、cancel/resume | screen source存在；真实runtime执行/恢复未验 | owner_domain=Shared Capability / AI Agent Groups; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [AI-02.md](../../../../contracts/experience/screen-specifications/AI-02.md) |
| AI-03 | AI Result + Shared Citation/Evidence | claim、citation anchor、版本、uncertainty | screen source存在；结果对每条source的真实绑定未验 | owner_domain=Shared Capability / Evidence-linked AI analysis; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [AI-03.md](../../../../contracts/experience/screen-specifications/AI-03.md) |
| AI-04 | SYSTEM Skill Registry / License / Permission | 已验证skill、license/trust、inputs/outputs/run history | screen source存在；Store lifecycle需逐条落实在现有owner | owner_domain=Shared Capability / Agent Skills registry; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [AI-04.md](../../../../contracts/experience/screen-specifications/AI-04.md) |
| AI-05 | SYSTEM AI Gateway / Provider Observation | 实际provider状态/策略/fallback/last check | screen source存在；current code已明示diagnostic fallback，不是独立能力 | owner_domain=SYSTEM AI Gateway / runtime diagnostics; status=BLOCKED; no BACKEND-GAP ID in frontmatter; [AI-05.md](../../../../contracts/experience/screen-specifications/AI-05.md) |
| SYS-01 | SYSTEM Runtime / Observability | 组件health/dependency/trace/recovery | screen source存在；当前运行 health未执行检查 | owner_domain=SYSTEM / RuntimeGuardian; status=APPROVED; BACKEND-GAP-036; [SYS-01.md](../../../../contracts/experience/screen-specifications/SYS-01.md) |
| SYS-02 | SYSTEM Collector / Scheduler / Session | 完整目标：计划/Schedule配置、单次/批次Task、逐平台状态、查询续页与native media cursor分别记录、取消/暂停/恢复回执 | 当前Screen Spec是只读状态面，目标写动作/分页/取消仍待C1/C6 Owner冻结；当前可见状态不冒绿灯、不把旧ACTIVE当新运行 | owner_domain=SYSTEM Collector; status=DESIGN_EXPLORATION; BACKEND-GAP-037; [SYS-02.md](../../../../contracts/experience/screen-specifications/SYS-02.md) |
| SYS-03 | SYSTEM Database / Integrity / Evidence Lineage | schema, version, readonly health, canonical integrity | screen source存在；本轮不读/改生产DB | owner_domain=SYSTEM / Canonical Data; status=DESIGN_EXPLORATION; BACKEND-GAP-038; [SYS-03.md](../../../../contracts/experience/screen-specifications/SYS-03.md) |
| SYS-04 | SYSTEM Permission / Audit / Effect Fence | actor/scope/action/approval/effect result | screen source存在；不能将屏幕中的UI grant当服务权限 | owner_domain=SYSTEM Permission; status=DESIGN_EXPLORATION; BACKEND-GAP-039; [SYS-04.md](../../../../contracts/experience/screen-specifications/SYS-04.md) |
| SYS-05 | SYSTEM Settings / Local Preferences | wallpaper/theme/contrast/motion/locale on current device | screen source存在；wallpaper's cross-surface adaptive result未跑实机 | owner_domain=SYSTEM Settings; status=DESIGN_READY; BACKEND-GAP-040 (read-only SYS-05 screen snapshot); [SYS-05.md](../../../../contracts/experience/screen-specifications/SYS-05.md) |
| SYS-06 | SYSTEM Controlled Browser / Authorization / Evidence | 当前任务授权内的 browser capability 与来源/证据 lineage | `IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED / BACKEND-GAP-041`；浏览器容量/状态不等于实际浏览、采集许可或Evidence | owner_domain=SYSTEM Browser / CDP; status=IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED; BACKEND-GAP-041; [SYS-06.md](../../../../contracts/experience/screen-specifications/SYS-06.md) |
| SYS-07 | SYSTEM Evaluation / Release Evidence | gate owner/assertion/current result/evidence | screen source存在；本轮未跑门禁 | owner_domain=SYSTEM Security / AI Gateway; status=DESIGN_EXPLORATION; BACKEND-GAP-042; [SYS-07.md](../../../../contracts/experience/screen-specifications/SYS-07.md) |
| SYS-08 | SYSTEM Observability / Logs | trace id/span/error/time context, sanitized fields | screen source存在；实机关联回路待验 | owner_domain=SYSTEM Observability; status=DESIGN_EXPLORATION; BACKEND-GAP-043; [SYS-08.md](../../../../contracts/experience/screen-specifications/SYS-08.md) |
| SH-01 | Shared Timeline/Media/Artifact | licensed source files, project, timeline, render/export/reopen | screen/media source存在；本轮未完成真实project E2E | owner_domain=Shared Capability; status=IMPLEMENTED_CATALOG_ONLY_EVIDENCE_SCOPE_BLOCKED; BACKEND-GAP-044, BACKEND-GAP-045, BACKEND-GAP-046, BACKEND-GAP-047, BACKEND-GAP-048, BACKEND-GAP-049; [SH-01.md](../../../../contracts/experience/screen-specifications/SH-01.md) |
| SH-02 | Shared Source/Evidence / Rights | originals, snapshots, captured/published times, citation link；按平台原生结构显示单帖 | `IMPLEMENTED_SCOPE_GUARDED_BACKEND_SCOPE_UNVERIFIED`；六个字符草图未正式登记Source/Evidence，媒体/全文和商业权利依 owner 返回 | owner_domain=Shared Capability; status=IMPLEMENTED_SCOPE_GUARDED_BACKEND_SCOPE_UNVERIFIED; no BACKEND-GAP ID in frontmatter; [SH-02.md](../../../../contracts/experience/screen-specifications/SH-02.md) |
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
│ 具体恢复原因    │ [打开来源/可用媒体]     │ [回列表] [回任务]      │
└───────────────┴────────────────────────┴──────────────────────┘

手机： [已存记录] / [新建采集] → 一条任务条件与真状态 → 逐篇Reader
已存记录只过滤读取；新建采集才触发Collector。排程只在授权计划已有运行合同后单独确认，不与单次检索合并。
~~~

现有接口事实：CTH-03 GET最多返回100条且会报告 `partial`；现有人工只读 search POST 当前仅支持一个`platform+keyword`或`business_requests`批次；`continuation`只续查询计划，不是post/comment/media native cursor；App当前只有Screen GET。UI目标显示完整两种模式和计划/原生分页能力，当前模式没有实现的字段列为owner contract gap，不能发往旧Route。筛选主键必须为稳定 `platform_id`，显示名不可作身份键；不移除已有Evidence projection校验。固定“广州太古汇”查询预填须清空。未返回的全文/媒体/评论/原生互动标“未取得/未绑定”，不可借别帖补齐。

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
Mobile: 音频播放器/时码+脚本跟随视图→音轨列表→选轨细节；不是完整混音界面缩小。
~~~

音频文件导入、理解、播放、回听、编辑、导出和重开纳入目标。文本修订和音轨修订各自独立显示版本。实时录音/麦克风不纳入当前UI流程，保留后置标记。

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

### AI-05 AI Gateway/Provider

~~~text
PC: Task入口 → Gateway → 实际provider/已退役状态/失败路径
    右侧显示当前检查时间/用户可执行的诊断
Phone: Provider列表→选择详情→看错误、恢复或返回任务
~~~

状态不给星星评分或无来源的tokens指标；fallback显示实际路线。用户手动选模不被UI重写。

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
    计划编辑：目标/平台/授权Scope/用途/时间/频率/深度/停止条件
    执行列表：Task ID / 按平台结果 / 原生续接位置 / 失败原因
    操作：人工运行 / 开启已授权计划 / 暂停后续计划 / 取消待执行项
Phone: 计划卡或单次Task → 平台分行进展 → partial/回执/恢复说明
~~~

这是SYS-02最终操作工作面的目标，不是当前ScreenSpec现有可用控件。当前Spec只有只读状态，计划提交/启动/暂停/取消/任务续接若无owner callable与Permission都不得出现在可操作实现；但终态UI必须为C1/C6已有Collector/Scheduler合同保留此路径，不能因为today read-only而删除。能力状态分别呈现`已配置`、`会话已验证`、`执行器可达`、`上次实际尝试/成功`、`当前运行`、`Evidence/Canonical正式接收`；旧缓存/文件ACTIVE/配置存在都不得亮成“已连接”。人工搜索、自动计划、批次续接、媒体/评论native cursor各自标记，不用同一个业务checkpoint冒充四种完成度。服务端拒绝、限速、挑战、部分收录、cancel等待回执或结果未知保留task/scope/已接内容，安全返回来源工作。具体现状和字段Owner见主方案§5.1/§5.2.2。

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
    未授权→显示范围与正常授权入口→用户完成登录/授权→返回来源任务
Phone: 当前工作→授权边界→受控来源（若可用）→状态/返回任务
~~~

SYS-06展示的是浏览器能力与当前任务授权范围，不是Collector连接灯。只有被现有Browser/Permission owner绑定的真实viewport/action才能提供操作；没有时如实显示不可用并返回来源任务。会话失效/挑战/撤权说明影响与已有Evidence保留状态；重新授权后是否续接由原任务owner决定。challenge由人工解决，不绕过。敏感Cookie/password不显示/复制；开发边界内不碰个人Mainland XHS身份。

### SYS-07 Release/Evaluation

~~~text
PC: 当前产品能力/Owner → Acceptance criteria → source/test/live/user evidence
Phone: 单个验收项→所需证据→当前未通过项/返回owner
~~~

状态区分 source-present、tests、runtime/E2E、user-verified、released、operating；不以全部绿点或报告代替。

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

其它已批准Source按现有 `content_type` 复用对应长文、图集、视频、音频、讨论串或listing reader；未识别类型保留来源记录与明确“暂不可读”状态，不丢掉或伪造一个平台。

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
