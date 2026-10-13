# LUMENIS 全产品用户操作与视觉参考
## 从属现有 Product Architecture / Experience · 文字视觉参考 1.7

初版日期：2026-10-06
当前参考校准日期：2026-10-11；原1.6收敛日期：2026-10-07
1.6 审阅输入基线：本轮最终交叉核对前，main、origin/main 与 live refs/heads/main 均为 `bbe3310f095b788448a480c4615481bc5da029f8`；Universal Platform Acquisition 规则来源提交为 `3be8298a3ae853b98fde90b2fda943a5c9462a58`。该 SHA 是审阅输入，不是永久 current 指针；实现/验收必须 fresh resolve 当前 main。
历史1.6审核记录：FINAL_TARGET_CONVERGENCE_APPROVED / 不等于实现或用户验收。1.7按已批准产品规则校正参考，不自动晋升设计或实现状态。
沿用原1.5文件路径；1.7只校正参考动线、原生范围及原件/派生呈现边界。唯一产品蓝图归Product Architecture，唯一视觉 authority 归Experience及其ScreenSpec，本文件不定义第二套执行规则。
本轮范围：研究综合、全产品最终目标态、操作流程、页面规格、五位架构角色视觉体系、文字视觉草图、当前状态与缺口映射，以及 2026-10-06—10-07 新批准的 SourceTarget、Universal Platform Acquisition、PlatformSession/Recovery、durable task 和 same-release evidence 规则。
本轮没有做：修改产品代码、正式视觉制作、产品构建/运行验收或部署。产品实现状态与最终目标继续分开记录。

> 这份从属视觉参考画的是：当前批准的序境完整产品范围全部实现并形成真实工作闭环之后，用户能够看见并使用的目标体验。它不是当前产品已全部完成的声明，也不是最终视觉定稿。
>
> 本文同时标出已有源码、候选/局部实现、尚缺接入、未验证和明确后置。没有数据、后端或接口的目标功能仍保留在蓝图中，但标成未完成或未知；不会用样例数值、动画或 AI 文案伪造已完成。

### 文档读法：最终目标与当前实现永远分开

- **FINAL PRODUCT TARGET**：描述完整产品闭环后用户应该看见和完成什么。除非 Product Owner 改变产品方向，它不因今天某个 API/模型/平台暂未接通而缩水。
- **CURRENT IMPLEMENTATION DELTA**：描述当前 main 已实现、部分实现、Blocked/Unverified 的真实状态。历史快照不代表此刻状态；每次实现须核对当前源码/运行，不能反向删除已经批准的终态。
- 原 1.5 中以 `0c9394ef` 为基线的源码/运行观察仍是 dated provenance；若与当前 main、Current Screen Spec 或本 1.6 收敛段冲突，以当前权威和 fresh evidence 为准。
- 文字视觉草图只定义用户可见结构、状态、动作与 Return；PlatformManifest、attempt token、lease、Cookie、CDP 等内部实现词不得直接变成普通用户界面。

---

## 0. 审核摘要

### 一句话定义

**序境把商业变化、市场材料、团队经验和创作任务组织成一条有证据、能继续、可复盘的工作路径。**

用户看到的是工作、内容、来源、判断、作品和后续动作。内部模型、Agent、工具、数据库和研究流程只在解释状态或帮助恢复时出现。

### 产品进入与范围

- 官网讲明白序境是谁、能帮助谁完成什么工作、实际产品怎样操作；官网演示必须如实反映当前已实现能力。
- Web Workspace、Desktop App、Mobile Companion 是同一个产品的不同工作面，不是官网的缩放版。
- 用户默认进入 ACC-03 任务主页，并从那里进入 AI-01 或其他真实工作路径。
- 未选择 Subject/BrandFocus 时是 GLOBAL/ALL；主体/品牌是可选的精确聚焦条件，不是打开产品、查看材料、开始研究或草拟工作的门槛。
- 默认主页承接“当前确实存在的任务、待用户确认结果、影响工作的已验证变化”；没有真实任务或待确认事项时不渲染虚构数字或占位任务。广州太古汇只有在用户当前确实选中了该 Subject 时才出现，不作默认主体。

### 1.5 dated evidence snapshot + 1.6 current contract delta

下表主要保留 2026-10-06 / `0c9394ef` 前后的只读源码观察作为 provenance；其中写“当前”的句子不得脱离日期继续当实时事实。1.6 目标与本轮合同差分以文件顶部 `bbe3310f` 审阅输入、Current Screen Spec 与本稿后续 `1.6 current overrides` 为准；任何实现/验收状态仍须 fresh resolve main/runtime。

| 项目 | 1.5 dated observation | 结论 / 1.6读法 |
|---|---|---|
| 44 个 App 屏幕 | `app/lib/features` 下有 44 个屏幕源码；44 份 `contracts/experience/screen-specifications/<ID>.md` 全部存在 | 页面入口存在不等于业务闭环；每份 screen spec 的状态、owner、binding gap、目标交互和验收边界见伴随草图的44行映射；`spec.status` 不是实现完成 |
| 默认入口 | 当前 root 与 Shell 初始屏幕指向 CTH-01 | 与目标主页 ACC-03/AI-01 冲突，待用户审核后由既有 owner 适配 |
| ACC-03 | 页面源码存在，当前构图含“当前视角”及启动检查面板与整页滚动 | 这类大块内部说明与 Product Owner 已明确纠正的任务优先、全球默认方向冲突，须列为目标态调整 |
| 账号门槛 | 当前 LaunchSurface 对 401/403 运行时身份读取失败仍允许显示 Shell，交由具体页面报告真实状态 | 这是开放产品入口的客户端路径证据；不代表各业务服务都可用 |
| AI-05 | 当前 Repository 在 AI-05 未独立绑定时读取 AI-01 诊断，并明确标成 fallback | 源码存在诊断；不代表 AI-05 有独立可执行 Provider/Gateway |
| Website | Astro 页面、样式、i18n、测试源文件存在 | 不代表含真实操作视频、当前在线、支持全部产品流程或已通过发布验收 |
| 屏幕绑定登记 | 1.5 时 `lumenis_app_binding_registry.json` 标为 SOURCE_MAPPED_ACCEPTANCE_PENDING，generated_from_head 早于当时main | 这是 dated snapshot；当前逐屏目标以 current Screen Spec + Experience contract 为准，不能继续用旧 generated_from_head 推断实现状态 |
| 产品蓝图基线 | 52cd770 更新 Product Architecture 与 takeover 文档，将已有 SH-01 Discover 纳入 J3/J7 闭环 | Discover 是既有 SH-01 子视图，无新增 Screen ID/Owner；其数据 callable 尚未冻结，仍属设计探索/待绑定 |
| 1.5治理主线 | `c7765b87`、`1b238c2f`、`0c9394ef`连续更新治理/归档处置；当时未改前端Screen/API、媒体运行或采集调用源码 | 仅用于解释1.5观察来源；自那以后CTH-03 SourceTarget、Collector治理、配置/Gate及多个合同已变化，1.6不得复用此行判断fresh main |
| 采集到单帖呈现的接线 | 2026-10-05 对当前 CTH-03、Collector API、SYS-02/SYS-06、SH-02、BMP-03 源码及现有六平台单帖草图做只读核对 | 已有人工只读采集 POST；CTH-03 前端当前只读 GET，未调用该 POST；列表丢失部分已返回字段，平台通道身份未按稳定 ID 保留；此项为源码事实，不是运行采集证明 |
| 本轮运行/验收 | 本轮未启动产品、未运行构建/测试/浏览器 E2E | 所有真实用户闭环与发布状态均需按当前 owner 和验收证据继续 |

### 状态词表

- **源码存在**：能找到 Widget、路由或素材实现；仅是源码事实。
- **部分实现/候选**：有局部能力或旧的候选/测试记录，但它与当前 HEAD、接口、权限或真实结果的关系未闭合。
- **未实现/明确缺口**：当前源码或用户纠正说明目标体验/绑定缺失或仍冲突。
- **待验证/未知**：本轮没有当前真实接口、环境、数据或端到端证据。
- **后置**：按 Product Owner 明确要求，等产品核心闭环后再单独审核，不在当前入口成为门槛。
- **已验收**：需要当前完整真实输入→真实结果→保存/重开/恢复→权限/证据→真实用户 E2E。页面文件、历史 build 或文档都不能单独升为已验收。

---

## 1. 唯一设计边界与终态产品结构

### 1.1 一套产品、四个工作面

~~~
                        LUMENIS 一个产品
                 Product Core / API / Data / Evidence
                               │
          ┌────────────────────┼───────────────────┐
          │                    │                   │
    Public Website       Flutter Workspace      Flutter Companion
    官网讲述/演示           Web / Desktop         Mobile
                               │
                 同一来源/事实/权限/Artifact owner
~~~

- Public Website 使用 Website 现有 Astro owner，负责产品理解、真实操作演示、文档/资源入口和进入工作区的链接；官网可以保留清楚的“进入工作区”入口，账号/登录具体方案按用户要求后置，不将其做成当前业务使用门槛。
- Flutter App 承载 Web Workspace、Desktop App、Mobile Companion 的产品页面。三个 App 工作面共享现有 Core/API/ViewModel，端侧交互按用户任务重组。
- CTH 负责 Subject-first 商业运营；BMP 负责 Brand/Market-first；Shared 提供采集内容阅读、Evidence、研究和创作交付；SYSTEM 负责 Collector/Runtime/DB/Security/Permission/Settings/Recovery/Observability；AI/Agent 作为这些流程中的增强能力。
- 这份稿不会另造产品、screen owner、Evidence store、AI Gateway、设计系统或媒体引擎。新能力缺口映射回现有 owner。

### 1.2 全局与焦点

- **GLOBAL/ALL 是无主体时的正常产品状态。**界面不把它做成警告、选择任务或超大范围提示。
- Subject/BrandFocus 仅用于当前任务的范围缩窄。切换焦点不改变用户身份，不扩大权限，不使其他路径不可达。
- 每条数据展示它自己的范围、时间和来源。全局视图不把一条单店、一个主体或一组已存事件包装成整个市场/所有消费者的统计。
- 任务的目标、预算、地区/品牌范围、材料和引用，若原任务/Owner 已有字段就随任务传递；不能在 UI 中创建另一个预算/Scope truth。未给出的值留空/UNKNOWN，不能自动补齐。

### 1.3 用户工作连续性

用户从工作主页选择一条适合当前目标的路径；下列链路可组合，但不构成每个任务都必须经过的统一流水线：

~~~
ACC-03 · 选择一项工作
   ├─ CTH/BMP 商业任务：业务问题 + 可选Subject/BrandFocus + 适用来源
   │    → 后端分析/证据核验 → 用户判断/决策/行动 → 保存与Outcome评价
   ├─ Shared 独立研究：网页/文件/图片/音视频/个人笔记
   │    → 阅读/比较/引用 → 可用研究笔记/报告 → 保存、重开、修订
   ├─ Shared 直接创作：空白/用户自写要求/获准素材
   │    → 提案/文稿/视频/播客编辑 → 预览/导出 → 保存、重开、修订
   └─ 产品内浏览器：从当前Task/Source进入真实网页 → 支持的页面操作
        → 停止或人工接管 → 返回原Task与已保存成果

跨路径连接为用户选择的可选接续：研究/CTH/BMP资料 ↔ Brief/作品；
接续时沿用已选来源、scope和版本，不强制每条路径汇合。
~~~

每个跨模块链接带回原任务/筛选/被选对象。需要变化时，先告诉用户哪些下游产物受影响，提供“保留旧版本 / 基于新要求生成版本 / 取消”路径；不会静默覆盖来源、事实、成果或已发布记录。提案、文稿、视频或播客可以从空白、自写创作要求或获准素材独立开始；CTH/BMP分析、Research、Subject/BrandFocus与SourceBrief仅在用户选择联动时进入。

### 1.4 当前实现/部分实现/未验证状态账本

| 功能能力 | 已有/候选证据 | 目标完成态 | 仍需证明的事项 |
|---|---|---|---|
| 全部 44 个应用页面 | 当前提交有 44 个 Screen 源文件及 44 份 Screen-specific 规范 | 本稿逐屏定义任务、形状、操作/返回，并列出当前规范状态与 owner | 逐页确认当前 API/ViewModel 字段、真实输入/结果、Permission、Evidence、保存/重开/恢复和 E2E；源码/`DESIGN_READY` 均不能代替真实验收 |
| 启动与产品主页 | LaunchSurface、ACC-03、AI-01 源码存在 | 所有当前桌面入口/Web/Mobile进入任务主页，GLOBAL/ALL；能开始或续接真实任务 | root 当前仍默认 CTH-01；四个桌面快捷方式的实际目标未在本轮验证；任务主页实际保存/恢复状态未在本轮操作 |
| ACC-03 主页面 | 当前源码存在当前视角、入口/启动面板、动态布局 | 低调任务优先；现有真实工作/待确认结果/影响当前工作变化有来源才显示 | 当前用户明确不接受大块范围/状态说明和传统入口卡片；需按第7.1完成目标重构并在各端真实验收 |
| 官网 | Astro的首页、中文/英文/韩文入口和样式/测试源码存在 | 官网具有 Cue 主视觉、产品解释、操作案例/视频、互动FAQ、进入工作区入口 | 当前页面的全部文案/操作视频/截图与能力一致性、官网部署/移动设备交互本轮没有验证 |
| CTH / BMP / Shared / SYSTEM | 各屏幕 Widget/路由/Repository/ViewModel 源码与屏幕规范存在，规范状态并不一致 | 完成每条业务工作闭环且不重复建立数据/服务所有者 | 不把 44 项混写成统一“未验证”：伴随逐屏表按源 spec 保留 `BLOCKED`、`OWNER_REVIEW`、`DESIGN_READY`、`IMPLEMENTED_*` 等状态；真实数据/Evidence/Permission/导出/E2E 均另列 |
| CTH-03 采集与单帖阅读 | 当前 Screen GET 返回最多 100 条 canonical 记录和平台状态行；人工确认只读搜索 POST 已存在，但 Flutter 源码没有调用者 | GLOBAL/ALL 下手动指定平台与查询条件，显式确认只读后发起；列表保留稳定平台 ID、来源、发布/采集时间和 Evidence 定位；单帖详情按平台原生内容形态呈现 | 当前 CTH row 的 `source_url`、`captured_at`、`projection/Evidence` 未进入 Dart row/UI；平台行缺 row projection 却被客户端按该投影筛选；标题关键词预填广州太古汇。正文、媒体、原生互动不在当前 CTH row schema 中，不能先画成已接入 |
| 采集运维与浏览器 | SYS-02 Screen Spec 是 Collector 状态只读面；SYS-06 是受控浏览器来源/会话边界；BMP-03/SH-02 是消费侧 | SYS-02 看真实任务状态与可恢复节点；SYS-06 只在授权/当前任务许可内读来源；SH-02 阅读有 lineage 的 Source/Evidence；BMP-03 解释有样本边界的市场信号 | 状态页不是启动/取消 API；浏览器会话不等于采集权限；单篇原帖不等于市场总体；每个页面仍按各自 Screen Spec 与真实运行证据验收 |
| AI 与 Agent | AI-01..05 源码与规范存在；AI-01..05 规范为 `BLOCKED`，AI-05 当前有诊断 fallback | AI能在可执行时提供可核对任务结果，在不可用时准确恢复/回退 | 当前屏幕 contract 记录 BACKEND-GAP-029/-030 等边界；AI真实结果、引用、Artifact保存/重开和评价仍未作用户 E2E |
| Shared / Discover / 视频 / 分镜 | SH-01当前安全能力目录；ScreenSpec `IMPLEMENTED_CATALOG_ONLY_EVIDENCE_SCOPE_BLOCKED`；媒体预览/TL与操作分镜分别已有源/设计合同 | Discover/Research 可选；提案、文稿、视频或播客可从空白、自写要求或许可素材直接开始；只有用户选择联动时才进入 Discover/Source→Brief→Artifact；叙事任务按需进入完整ShotPlan/线稿/彩稿/逐镜确认，素材任务进入全屏宽视频Timeline | Discover bindings和ShotPlan/媒体验收分开；来源许可/Evidence、媒体导入/渲染/版本/重开、逐镜确认变更失效等未通过真实任务前均未验收 |
| 播客 | BMP-08 有脚本/渲染相关 UI 源码，screen spec `OWNER_REVIEW` | 文件音频导入、理解、编辑、播放/试听、保存/渲染/重开；实时麦克风后置 | 文字脚本不能代替真实声音；文件级播放/混音/渲染/重开仍待真实 E2E |
| 外观/图标 | SYS-05 规范为 `DESIGN_READY`；`crimson-sunset.jpg` 与 `cobalt-dusk.jpg` 已随 app assets 捆绑，已有局部 Web/Windows 证据 | 线性功能 icon + 原创手绘色彩身份图标；强色壁纸上对比自适应，偏好留在当前设备 | Web 选择/重载/删除及若干外观检查有局部 PASS；这两张图在所有端/字号/裁切下的真实用户复核、原生材质渲染仍未全验 |
| 证据/绑定清单 | current binding registry 文件存在 | 每个输入/字段与 owner、权限、来源、口径和任务结果一致 | registry 生成于旧 HEAD 76fbe1af…，比当前快照早，不能代表当前完整绑定分布；后续须按当前源生成/readback |
| 用户验证与发布 | 本轮为方案/草图工作 | 同一版本通过真实业务任务、失败恢复、各端与发行门禁 | 本轮没有运行产品、浏览器、测试、构建或部署，不标用户验收/发布状态 |

**明确标为未/部分/未知是范围的一部分，不会因而从第6章或第7章删去功能。**

---

## 2. 输入资料与逐项研究落实

本次审计接续并修正本稿，不重做已记录的视频帧阅读。已分析的两段启动/官网录屏、319b创意视频、此前五条视频、Cue/Manus/OpenAI资料及历史研究继续以§2.1–2.3中的固定原件、读段和限制为准；本次没有重新解码/复看，不扩大至未定位旧视频。

### 2.1 既有稿件记录的逐帧复核：三个指定视频

下列观察和帧数沿用审核稿 1.3 的既有记录。前端交付审计及本次 1.5 修订没有重新解码或逐帧复看；这里不将历史记录写成此次审计新做的核验。

#### d16fc1c8ad774b0e950e3e7a4e444fe3.mp4

- Source：2,188 帧，30fps，72.933333 秒。SHA256：eccfcc6795874ce3a034fb4b3a151fc481f1e8ec0362fc24896f5d138af8c6a8。Manifest 记录抽取帧数与 ffprobe 一致、源 hash 解码前后不变。
- 连续抽取 73 张图表；审核稿 1.3 的记录称按序检查 sheet 1–73，对应 frames 1–2,188，期间未跳过区间；本次未重做该阅读。
- 审核稿1.3既有观察：手机浏览器录制中浏览 Cue 官网，同时展示站内 Agent/任务操作。站点由短主张、Hero/demo、分段能力故事、具体界面示例、群组/扫码、FAQ、下载入口和页尾组成。FAQ 项可展开并展示答案；滚动故事与演示片相互照应。
- 适配：官网用章节、实际任务动画、FAQ 展开和清楚 CTA 展示产品；支持锚点跳转和浏览器 Back。
- 不适配：不能由 Cue 的预约、邮件、电话、支付和社交能力推导序境已有相同功能，也不能照搬其产品文字和角色素材。

#### 7ac450632cf2611ee2ff3a6b29a41669.mp4

- Source：715 帧，约 21fps，34 秒。SHA256：dc7f78f562499306cd2d98c1cd058d1e004631112e2d0ef456ef7e81e365a8d2。Manifest 记录抽取帧数与 ffprobe 一致、源 hash 解码前后不变。
- 连续抽取 24 张图表；审核稿 1.3 的记录称按序检查 sheet 1–24，对应 frames 1–715；本次未重做该阅读。
- 审核稿1.3既有观察：打开应用→启动标记/载入→第三方登录/Apple 授权→生物识别→等待/完成→可跳过的岗位引导→订阅/paywall。视频不是官网教程，而是移动 App 启动/身份/引导状态流。
- 适配：启动标识短暂出现；读取状态后明确可用或问题；保留任务/当前页面；首次使用仅提供可跳过的小提示；异常时给重试和回退。
- 明确排除：登录墙、第三方账号选择、强制角色问卷、付费墙和订阅定价。账号/登录重新规划仍后置；产品正常使用不等用户先建账号。

#### 319b2b867ef23111e43246d4477c8cf3ed4cb2ac8da585ad3d544beed56a69aa.mp4

- Source：4,484 帧，60fps，74.716667 秒。SHA256：3339878d073e4b26121780479ae4c8e88c627de13a65af92fe323e2e55d0bc82。Manifest 记录抽取帧数与 ffprobe 一致、源 hash 解码前后不变。
- 150 张连续接触表记录覆盖 frame 1–4,484；审核稿 1.3 记载逐张核对 sheet 1–150，最后一张为 frame 4,471–4,484 的 14 帧；本次未重做该阅读。
- **审核稿1.3既有观察·图标程序**：多色几何角色第一次以简洁轮廓和眼神出现；QR进入取景框后像素拆解、变成红色小角色，角色名随之显现；后续角色与结果消息/操作卡并排；最终回到品牌标记。
- **审核稿1.3既有观察·操作程序**：具象能力→真实示例画面→授权卡的Deny/Allow→状态转换；能力列表→群组创建抽屉→结果消息/任务卡；外部应用小标与结果状态并置；扫码识别出现“creating”状态，然后角色/对象进入工作流。
- **审核稿1.3既有观察·视觉程序**：空白/浅底、短文字动画、角色尺度与颜色并用，变化有清楚开始/结束，画面从手作角色落到可辨认的操作结果；场景片段用真实空间营造人情感。
- **采用对象**：仅 Public Website 的序境原创操作影片、演示插图和手绘 icon 动效。序境自己的演示要从 Source/Brief 开始，展示真实可行的 Evidence/Result/Artifact，不展示 Cue 支付、QR 建 Agent、品牌 logo 或它的内容。
- **工作区的适配**：只把原创色彩身份图标用在真实对象/内容/成果，状态节点保持语义色与来源；不能让手绘角色盖住来源、播放头或编辑控制。
- Manifest 仍记录视觉状态 PENDING，因为抽帧工具没有对抽取记录写入“人工查看”。审核稿 1.3 记载的人工阅读与manifest状态并存；本次1.5沿用两者而不重写manifest或重新复核，不称其为OCR或原始分辨率逐像素识别。

### 2.2 此前五个视频：帧覆盖核验与适配

本稿仅涵盖用户指定的五个 Desktop MP4，不扩展到其他历史视频。审核稿 1.3 留有五个原件 SHA、连续解码索引、既有逐帧报告与联系表的阅读记录；本次1.5不重新打开/核验全部帧。旧 `reference-videos/index.md` 中的 `COMPLETE` 仅指稀疏采样提取完成，不能单独证明逐帧审阅；前三条此前已有独立逐帧报告。后两条的历史 handoff 状态仍记为未完成；审核稿1.3补充了联系人表人工查看记录，但本次审计不独立背书其全量帧覆盖。

**沿用记录的阅读口径与限制：**审核稿1.3称每个解码源帧由索引映射到唯一画面或精确重复帧，并记录了连续contact sheet逐页查看。对2601473与cb55，该稿分别记载查看82/82、117/117张表，覆盖1,305、1,865个唯一画面。当前历史`FRAME-COVERAGE.json`仍保留之前的`PARTIAL...` / `PENDING...`状态；本次不回写索引、不重看这些表，也不独立验证历史计数/完整性。联系表适合观察状态与布局变化，不能当作原分辨率逐像素检查或完整OCR；无法辨认的小字和后台网络行为仍为未知。

| 原件 / SHA256 | 解码与逐帧审阅证据 | 逐帧观察到的操作/呈现 | 序境映射与明确不采纳 |
|---|---|---|---|
| `28346dd9b6cbda22c59a9f13c6757b1b.mp4`<br>`36cf5faa224c709e0e31694a6288043f46bbc4e4a2d60ece55eaa2b40995b026` | 577 源帧 / 577 唯一帧；37 张连续表全部已读，9 张原分辨率关键帧；报告与覆盖索引在 `reference-videos-history-20261002/28346.../` | 搜索/主题入口进入图文详情；标题摘要后接作者、时间、正文、引用块、互动和媒体；顶部随阅读收缩，固定底部导航；体育页改为主题标签、主图和趋势清单；可见骨架到真实图文的渐进状态。页面转场触发未能确认。 | 用于 SH-01 Discover/SH-02 阅读的“来源与引用分层、清单类型随任务变形、可返回并保留位置”；不做社交无限流，不把画面中的帖子/账号/数字当作序境事实。 |
| `28d5aca3aaba2851b9a0f24f5c49f039.mp4`<br>`53a84b983045101a0d20d6a3315a1a37ce0a472bb11d16257ef247b5cd94504f` | 1,378 源帧 / 1,368 唯一帧 / 10 个精确重复；86 张连续表全部已读，10 张原分辨率代表帧；报告与覆盖索引在 `reference-videos-history-20261002/28d5.../` | 素材来源与媒体类型筛选、缩略图选择计数、底部“添加”确认；进入竖屏编辑后预览、时间线缩略帧、播放头、独立音轨、选择素材时的上下文工具、分割/变速/音量/动效和显眼导出；中途切到内容流、消息/主页，后续另有媒体加载状态。未验证导出是否真实完成。 | 用于 C4/SH-01 视频作业流与来源选择；桌面保留全尺寸 Timeline/Viewer/Inspector，移动端仅重组查看与轻操作；不可把手机剪辑器当 Premiere/FCP 桌面研究，也不借其 AI 按钮宣称序境已能生成。 |
| `a700b33f084a1601c9c98e5d5dc52264.mp4`<br>`03c9f84814aaf7d21000bbc0b86333e456c2d6a3f4a3f540bee5f3d03d02df74` | 1,116 源帧 / 1,115 唯一帧 / 1 个精确重复；70 张连续表全部已读，12 张原分辨率代表帧；报告与覆盖索引在 `reference-videos-history-20261002/a700.../` | 首页故事入口与大幅视频卡；持续信息流中混排帖子、视频和推广内容；原文/作者/互动元信息与媒体区分层；显示音频不可用提示、翻译提示及查看原文选项；资料页、Reels 播放器、消息、搜索网格、个人页各自切换到不同结构，部分页面先骨架后填充。手势触发和翻译质量不能由录屏确认。 | 用于 BMP-03/CTH-03/SH-02 多模态内容阅读与可逆详情层；来源状态、译文与原文分开；不复制社交 feed、账号、内容、推广标识或交互动作，也不推断真实翻译服务。 |
| `2601473a2d645d6250caede43c3486a6.mp4`<br>`54831c2c64e297aa7869625c3ba1250562a33686c095fdf37059156c12f12369` | 审核稿1.3记录：1,358源帧 / 1,305唯一帧 / 53个精确重复；82张连续表据称均已查看；旧覆盖索引状态仍为`PARTIAL_CHRONOLOGICAL_CONTACT_SHEET_REVIEW`。本次未重验。 | 历史观察记录：开始处于深色竖屏剪辑器，预览占主区、下方是带播放头的时间线与音轨。早期打开导出参数（画幅/分辨率、帧率、码率、HDR）层；系统控制中心一度覆盖并返回；分割动作遇到“当前位置不可分割”提示，后续出现撤销反馈；再进入变速曲线选择、工具栏横向换组、音乐/视频素材选择器与长时间导入进度。AI音乐面板可见输入、模型选择和开始操作，但没有产物完成证据。 | 供SH-01/Shared Timeline的具体操作层级、选中上下文、错误提示、工具滚动与中断恢复研究；演示素材、AI音乐能力、模型/会员权益、第三方配色和工具字样均不可直接变为序境承诺。 |
| `cb55b77feb25668ebdaea62e177adf1b.mp4`<br>`ee9a5f01bbf1f70f3f470f4f9cfada01d4b1a9537853dd904718a194eaf79faa` | 审核稿1.3记录：1,865源帧 / 1,865唯一帧；117张连续表据称均已查看；旧覆盖索引状态仍为`PENDING_CONTACT_SHEET_REVIEW`。本次未重验。 | 历史观察记录：先见移动端左侧空间/任务导航，再进入空间内容浏览：类型标签切换（推荐/收藏/文件/页面/图片等）、骨架加载、文档卡片、图文/媒体双栏阅读、搜索与新增动作固定在底部；随后进入自定义偏好、连接器/插件分类与详情页，图标有清晰身份色，列表分组与连接状态/权限说明可见，返回保持层级。 | 用于SH-02来源阅读与AI-04/能力目录的列表密度、分组、详情与返回位置；序境按真实Source/Evidence/Skill owner重组，不引入金融账户、第三方连接器、支付订阅、个人资料或通用社交工作台，也不复制第三方logo。 |

审核稿1.3声明的五条视频帧覆盖与已读报告属于历史记录，不由本次1.5逐帧复演或独立签收。已读报告中标记`DESIGN_EXPLORATION`的模式仍只是参考，不会自动提升任何SCREEN-ID为`DESIGN_READY`或实现完成。

已有AI-01视频研究：20261003-0145-11.4767587.mp4，SHA256 f15f2eca1b042a2ae29b718e85a578a025446319e5db24b4602df605585f2cbd；既有manifest/AI01-REFERENCE-AND-DESIGN记载 2,595 帧、87 张连续表、PTS 0–86.5s；本稿仅复用其已记录的任务入口、加载、浏览器/详情层和失败恢复观察，不重复播放。

已有的其他早期记录：

| 原件 | 当前定位状态 | 历史读取/结论 | 处理 |
|---|---|---|---|
| 20260924-0428-28.8331232.mp4 | 原TempState路径和Codex附件目录未找到 | 历史Round08记录13张三秒storyboard，PTS 0/18/36 原尺寸阅读，映射SYS-05字体；历史前缀0227d772…，当前完整hash未知 | 仅沿用“字体/外观偏好”结论；明确非全片逐帧；不重开历史分析任务 |
| f17b987d8584bb13b649187a9f5652f3.mp4 | 原WeChat临时路径和Codex附件目录未找到 | 历史PyAV decode记载1,133帧/37.733s，hash历史前缀3b65034d…；报道未证明每帧人工读 | 保留Public Website/SH-02抽象映射；源文件不在本轮读取范围 |
| 3e1067660c7223875e207df7661645e5.mp4 | 原WeChat临时路径和Codex附件目录未找到 | 历史PyAV decode记载4,477帧/154.308s，hash历史前缀5a24c491…；未证明每帧人工读 | 保留既有分析/待读区间标注，不推测缺失视频内容 |
| ff13000d9780cd5e4afca00af6556905.mp4、63ec6626fb6aca589c2071ef8d0caf06.mp4 | 原用户提供的WeChat临时路径及已查Codex附件目录当前未找到 | 没有可按 basename 精确归属的阅读/抽帧证据；Round08“3个视频各4帧”没有文件名，不把它们分配到这两条 | 记录“用户曾提供、当前源不可定位”；不猜画面、不再问用户重复发送 |

这些“未定位”描述指本轮检查的指定原路径/附件缓存，不是用户没发送。原路径、抽帧manifest和历史讨论保留为证据。本稿不扩展到其他历史视频重看。个人 Mainland XHS profile/cookie/session继续禁止读取或触碰。

依据与旧材料：work/frontend-2026-10-03/ALL-REFERENCE-VIDEO-INVENTORY.md 与 .json、CONTENT-READING-REFERENCE-ADAPTATION.md、AI01-REFERENCE-AND-DESIGN.md、MANUS-EDITOR-RESEARCH-20261003.md、MANUS-EDITABLE-TIMELINE-GAP-TRACE.md、MEDIA-REFERENCE-IMPLEMENTATION-TRACE.md、PODCAST-AUDIO-EDITOR-BINDING-PROPOSAL.md、LUMENIS-ICON-REVISION.md、NIELSEN-OPERATION-MAPPING.md 和 ACC03-PRODUCT-HOME-DESIGN.md。
- work/frontend-2026-10-03/ALL-REFERENCE-VIDEO-INVENTORY.md
- work/frontend-2026-10-03/CONTENT-READING-REFERENCE-ADAPTATION.md
- work/frontend-2026-10-03/AI01-REFERENCE-AND-DESIGN.md
- work/frontend-2026-10-03/MANUS-EDITOR-RESEARCH-20261003.md
- work/frontend-2026-10-03/MANUS-EDITABLE-TIMELINE-GAP-TRACE.md
- work/frontend-2026-10-03/MEDIA-REFERENCE-IMPLEMENTATION-TRACE.md
- work/frontend-2026-10-03/PODCAST-AUDIO-EDITOR-BINDING-PROPOSAL.md
- work/frontend-2026-10-03/LUMENIS-ICON-REVISION.md
- work/frontend-2026-10-03/NIELSEN-OPERATION-MAPPING.md
- work/frontend-2026-10-03/ACC03-PRODUCT-HOME-DESIGN.md

### 2.3 每项研究如何改变序境

| 研究 | 观察/结论 | 映射到序境能力 | 页面/交互变化 | 如何验证 |
|---|---|---|---|---|
| [Cue 官网](https://cue.im/) 与 d16 录屏 | 官网由短表达、真实界面操作、分段故事、具体问答和真实入口组成 | Public Website | 章节叙事 + 实际产品演示 + 可展开 FAQ；主页不是 SaaS dashboard | 在网站上操作 CTA/FAQ/视频，检查键盘、手机、Reduced Motion、播放失败回退和所有文字所述能力 |
| 319b 视频 | 角色从对象像素生成；动作前有许可卡；操作结果进入同一列表 | Public Website 自有演示 / ICON visual family | 采用原创来源符号→角色/成果对象的渐变；工作区对外部动作显示明确待批准/批准/拒绝 | 每个宣传片步骤由当前真实功能 owner 对表；权限拒绝不产生效果，批准状态只由真实服务回执决定 |
| 7ac 启动视频 | 首次开屏、等待、失败返回、可跳过可选引导 | Launch / ACC-03 | 以“恢复工作→到主页”为主，引导不阻挡使用 | API/服务不可用时可进入开放产品壳层；重试/取消保留入口，不加登录墙 |
| [Manus 2.0 官方发布页](https://manus.im/zh-cn/blog/introducing-manus-2-0) | Cascade 将页面/视频/自动化视作项目产物；Studio 的编辑器让片段、图像、文字、动态图形、音频可以逐项修改；操作/自动化有输入与任务关系 | SH-01/BMP-08 与跨域工作衔接 | 适配为可编辑 Artifact、具体对象级改动、返工后形成新版本；AI建议和人工调整在同一作品工作链 | 不增加 Cloud Computer、外部自动化、独立Agent、账户/支付或视频生成后端；官方所述云能力不是序境的实况 |
| [OpenAI 中文官网](https://openai.com/zh-Hans-CN/) | 顶部Research/Product/Enterprise/Developers/Company的直达结构，主任务入口，最新动态/客户案例/研究分区与详细资源/帮助脚注 | Public Website 信息架构参考；产品内部任务/结果信息组织参考 | 官网把首页使命/主CTA和具体内容目录分层；产品工作区用清楚的来源、成果、支持与状态位置 | 只借信息层次和导航明晰，不复制 OpenAI 视觉、品牌内容、客户案例或AI产品承诺 |
| 当前 Product Architecture + SH-01 screen contract §11 | 把趋势、观察热点与相似作品接入现有 SH-01 Discover；默认 GLOBAL/ALL；按具体 task optional Focus/platform/time | SH-01 Discover → 现有 Brief/creation owners | 三个任务视图分别呈现 series/observed corpus/native metrics/comparable dimensions；每项提供来源、时间、scope、coverage、relevance与可定位引用 | 当前 Discover callable/字段未冻结，spec 仍 `DESIGN_EXPLORATION`；不画出虚构推荐或把热点说成总体/因果事实 |
| 此前五个作品/资讯/编辑视频 | 五条用户指定原件均有连续全帧解码索引；前三条既有完整逐帧报告，后两条已在本轮读完全部帧联系表 | CTH-03、BMP-03、SH-02、SH-01、BMP-08 | 每种内容与创作任务使用自身结构：来源阅读/社交动态/素材选择/时间线/作者作品，按既有 owner 衔接 | 实际覆盖、hash、原件路径和细节见§2.2；仅采纳交互层级，第三方画面/账号/音乐/Logo和宣传能力不作为序境资产或承诺 |
| FCP 12/Resolve 培训 | 主故事线、连接片段、磁性吸附/定位工具、检查器、预览、轨道与输出是互相关联工作台 | SH-01 | Viewer/Timeline/Source/Inspector 明确同步；操作有精度、撤销和效果预览 | 真实项目导入、编辑、保存、导出、关闭后重开，并校验项目文件/媒体引用 |
| Logic/REAPER 手册 | 波形、编辑器、Mixer、track stack、效果和 automation 是多轨音频创作骨架 | BMP-08 | Script 与多轨波形双向定位；Mixer/Inspector 只针对选中轨道/片段 | 真正操作一段录音/脚本/多个轨道，渲染并重开；失败保存源音频与草稿 |
| Nielsen 十原则 | 运行状态可见、现实用语、用户控制、一致性、错误预防、少记忆、效率、克制、恢复、帮助 | 所有页面/特别是编辑/恢复/外部动作 | 每个动作旁显结果和返回路径；颜色不是唯一信号；状态不是装饰 | 每一条 E2E 记录成功/拒绝/取消/失败/恢复操作，检查误操作和可逆性 |
| 鲜艳夕霞照片与手绘人像 | 强色背景、纸感、手作不应破坏信息对比；图标应小而有身份，排齐真实边缘 | SYS-05、Website/icon、所有四端 | 背景对比按区域调整；客体缩略图/小标记紧凑；手绘只放在有身份的对象 | 两张照片随机裁切，在多主题/200%字号/色弱或高对比环境下检查文本与焦点 |

补充蓝图和先前讨论中出现的 Apple、ChatGPT、TRAE 等只作为交互/质量启发；用序境自己的任务路径和视觉语言表达。官网导航只保留直达“进入工作区”的产品入口，不显示登录、注册、账号菜单或未来占位；产品闭环后是否规划账号由 Product Owner 另行决定。

---

## 3. 统一视觉和状态规范

### 3.1 主页/工作区的独特外形

- 工作区不是一套“欢迎大标题 + 四个大卡片 + 一侧当前范围面板”。首页是一个能接着做事的页面。
- 首页大区：真实待处理结果/工作任务（若 Core 有）在首屏较上；一条 AI-01 任务编辑入口作为主行动；其次是用于进入 CTH/BMP/Shared 的短任务路径。
- 若当前没有可用任务，首页不做“暂无数据”排行榜或假活动。仍允许开始一个任务、打开素材或导航到现存模块；“没有记录”和“尚未采集”的含义分别显示在相应业务页。
- “未选择主体”没有告警标识、设置页或巨型标签；使用当前全球范围读取。如果某任务已经有精确 focus，用轻量 chip 显示真实名称，可关闭回全局。
- 头部尽量薄。任务页用与它有关的可见操作，不出现“服务检查清单”“查看入口状态”一类工程文案。

### 3.2 信息密度和字形

- 先对齐各块外缘，再决定线条/留白；视觉层次让人扫读，不用多个浮卡与分割线叠加。
- 原始资讯页缩小账号/品牌标志，主视觉是原文/图片/视频；出处和时间齐头或齐边，动作沿阅读块底缘对齐。
- 键盘焦点、图标和文字共用同一基线；图标在导航、动作栏、数据行中的比例按用途不同。
- 信息层级依靠位置、字重和间距；颜色辅助而不单独表达状态。
- 标题与数据刻度有区别；品牌主张不在每个内页重复显示。

### 3.3 颜色与对象

#### 序境原创标记、角色与状态点

- 序境主标识继续围绕当前批准的“点 + 开放轮廓/场”母题重塑；左上不放一个难辨认的超大“序”字。以一个被轮廓承接的点和短字标组成，确保在 18–24 px 导航尺寸、网站 Hero、启动画面和小图标中分别都读得清楚。设计含义是“以微小线索进入有边界的场，再由人决定下一步”，不是齿轮/星芒/机器人脸。
- 五位角色是序境架构的原创视觉身份，不是登录/权限角色、五个Agent、独立服务或新产品域；名称先用架构名，不编造角色姓名、背景故事或自主行为。只保留以下五位：

| 角色 | 对应架构职责 | 中 / EN / 한국어显示名 | 序境原创的手绘识别线索（共同采用水彩/彩铅/印刷颗粒语汇） | 可见时机 |
|---|---|---|---|---|
| CTH 商业运营 | 商业主体、业务单元、业态、事件、决策和运营结果 | CTH · 商业运营 / CTH · Commerce operations / CTH · 상업 운영 | 由场所结构、空间边界与经营路径形成稳固、落地的轮廓；暖土色中留一处克制的鲜明观察色，不画成购物者/商场吉祥物 | CTH任务入口或需要理解商业对象/运营链时；不替代商场、品牌或平台的真实标志 |
| BMP 品牌市场 | 品牌、市场、消费者需求、竞品、创作者、传播与Campaign | BMP · 品牌市场 / BMP · Brand and market / BMP · 브랜드 및 시장 | 从品牌表达材料、色样与市场信号形成更有表现力的组合；可丰富用色但层级明确，不画成广告喇叭或凭空生成的品牌人设 | BMP任务入口或研究/内容工作确需领域提示时；身份仍须有真实品牌/Brief来源 |
| Shared Capability 共享能力 | Source/Evidence、研究、创作、Artifact、报告、评价与学习等共享能力 | Shared · 共享能力 / Shared · Shared capability / Shared · 공유 기능 | 以可追溯的连接、汇合与交付层次表现材料如何进入结果；不使用通用“网络球”或伪造数据流 | 跨域工作或成果接续确需提示时；不取代业务对象或Evidence标识 |
| System 系统 | Runtime、数据、采集、安全、Permission、恢复与运行支持 | System · 系统 / System · System / System · 시스템 | 以框架、层次、边界与秩序表现稳定性；冷中性色与人文纸感平衡，不画成机器人/电路板/监控塔 | 只在真实服务状态、恢复、安全/运行解释等上下文中；不做用户的默认导航人格 |
| 序境自研AI | 由唯一AI Gateway承载的序境自研模型/推理/多模态理解与受控学习 | 序境自研AI / LUMENIS-owned AI / LUMENIS 자체 AI | 以阅读、标注、归纳和逐层形成判断的手作线索表达；有生命感但保持用户掌舵，不用魔法星芒、通用脑袋或自主执行人格 | 仅在真实AI任务、来源说明或结果/不可用状态中出现；建议须能查看来源、修改或拒绝 |

这五位共享同一原创造型语法，但轮廓、姿态和一处主要材料线索可辨；不是五套互不相关的画风。Agent是执行协作方式，不另设第六位；AI角色代表序境自研AI能力的用户侧可见身份，不另建AI Gateway、模型服务或自治权限。各类来源/市场对象/作品可有手绘身份图标或插画，但不新增角色人格。既有功能控件继续用清晰线性glyph；五位彩色身份图只在对应架构语境、适当的说明/入口/空状态或获准的官网演示中使用，不铺满工具栏、列表或每张卡，也不代表状态、权限或数据事实。

**版本升级规则：**本稿1.6保留1.5已经取代1.4的“五位架构角色”裁决，并继续吸收2026-10-07批准的跨屏闭环；1.5以前未分架构的泛化“角色/对象家族”描述继续只作历史。旧版`LUMENIS-ICON-REVISION.md`保留为历史研究，不再作为五位角色数量/分配的当前依据；唯一正式规则由总控写回Experience Constitution。现有官网、Web、Desktop、Mobile中的角色草案和已登记角色资产，在后续获准设计/实现时全部按这五位重新归类与升级；不匹配者标为旧版/待替换，保留原始文件、来源和版本记录，不覆盖历史或谎称已完成图稿替换。当前升级的是方案规则，尚未生成/替换实际产品图标和角色美术。
- 任务状态点可以参考 Cue/OpenAI Dot 的“轻、小、略有材质、正在运动时能被察觉”的质感，但形状、节奏与色谱均需序境原创。规则：静止=可用（小实点）、执行中=短行/缓慢聚拢、待人确认=开放圆点+停顿、部分可用=半闭合轮廓、阻断/失败=断开的轮廓并配原因文字。全部状态都须显示文本标签或可访问名称；不能只靠点的颜色或动画表达。
- 官网演示中可展示标记/对象从线性识别→彩色手绘 identity→回到真实证据/成果的变化。App工作页只在对象变更、待确认等有意义时有一次短动作；不把角色放在每个工具按钮或每一条数据前。

| 颜色角色 | 用途 |
|---|---|
| 画布底色 | 透明/淡白/纯白/浅灰/纯黑/选定壁纸，按外观设置和当前设备能力提供 |
| 内容底板 | 局部阅读和操作表面，背景越复杂则实底/模糊遮罩越强 |
| 事实主色 | 文字、来源线和真实指标，保证可读性 |
| 语义色 | 成功/提醒/风险/阻断/过期/加载按真实状态，文字或形状重复说明 |
| 手绘色 | 原创角色和对象身份，颜色指向对象而非状态、权限、市场结果 |
| 平台原色 | 保持平台自己的品牌色/形状，不融入序境角色色 |

对比度验收：一般文本至少 4.5:1，大字至少 3:1；焦点框在壁纸和内容底板上均可见。具体材质值由实际设备和图片测试确定。

### 3.4 文字与术语

- 主标题描述任务，例如“市场情报”“剪辑”“证据来源”，不写“您的数据/AI 已为您准备好”等未经验证口号。
- 结果按钮具体描述动作：“把此来源加入 Brief”“保存为新版本”“打开原始片段”“导出当前混音版本”。
- 不将“查看”“完成”“成功”用于无法说明对象或状态的动作。
- 未运行的按钮写真实状态，如“尚未连接可执行能力”或“当前只能查看诊断”。
- 三语言 zh/en/ko 目标必须贯穿官网、Workspace、Desktop、Mobile；未翻译项不能以英文占位当作可发布。

#### 目标态核心文案映射（zh-CN / en / ko-KR）

下表是审核稿里的实际目标态屏幕标题/主要动作，不代表这些屏已实现。`GLOBAL/ALL` 是合同/范围 shorthand，面向用户的短标签使用“全部范围 / All available scope / 전체 범위”；不得将技术名写成大标题或要求先选择 Subject。

| Screen | 中文标题 · 主动作 | English title · primary action | 한국어 제목 · 주요 동작 |
|---|---|---|---|
| ACC-01 | 序境已就绪 · 进入工作区 | LUMENIS is ready · Enter workspace | LUMENIS 준비 완료 · 작업 공간으로 |
| ACC-02 | 工作范围（可选） · 继续使用全部范围 | Work scope (optional) · Continue across all available scope | 작업 범위(선택) · 전체 범위로 계속 |
| ACC-03 | 你的工作 · 开始一项工作 | Your work · Start a task | 내 작업 · 새 작업 시작 |
| ACC-04 | 此项操作暂不可用 · 查看当前恢复方式 | This action is unavailable · View recovery options | 이 작업을 사용할 수 없음 · 복구 방법 보기 |
| CTH-01 | 商业运营 · 查看变化 | Commerce operations · Review changes | 상업 운영 · 변화 보기 |
| CTH-02 | 经营主体 · 查找或新增 | Business subjects · Find or add | 사업 주체 · 검색 또는 추가 |
| CTH-03 | 来源与观测 · 只读搜索 | Sources & observations · Search read-only | 출처 및 관측 · 읽기 전용 검색 |
| CTH-04 | 事件关系 · 查看来源链 | Event relations · View source trail | 이벤트 관계 · 출처 흐름 보기 |
| CTH-05 | 反馈日历 · 打开日期 | Feedback calendar · Open a date | 피드백 캘린더 · 날짜 열기 |
| CTH-06 | 消费者反馈 · 阅读原文 | Customer feedback · Read the source | 소비자 피드백 · 원문 읽기 |
| CTH-07 | 运营趋势 · 查看指标口径 | Operating trends · View metric definitions | 운영 추세 · 지표 기준 보기 |
| CTH-08 | 问题案例 · 更新处理进展 | Cases · Update case progress | 사례 · 처리 진행 업데이트 |
| CTH-09 | 风险与决策 · 查看依据 | Risks & decisions · Review the evidence | 위험 및 결정 · 근거 검토 |
| CTH-10 | 运营报告 · 打开报告 | Operations reports · Open a report | 운영 보고서 · 보고서 열기 |
| BMP-01 | 品牌与市场 · 查看品牌关系 | Brand and market · View brand relationships | 브랜드 및 시장 · 브랜드 관계 보기 |
| BMP-02 | 品牌身份 · 查找或新增BrandFocus | Brand identity · Find or add a BrandFocus | 브랜드 정체성 · BrandFocus 검색 또는 추가 |
| BMP-03 | 市场情报 · 查看来源 | Market intelligence · View sources | 시장 인텔리전스 · 출처 보기 |
| BMP-04 | 媒体传播 · 查看互动口径 | Media and propagation · View engagement definitions | 미디어 및 확산 · 참여 지표 기준 보기 |
| BMP-05 | 创作者研究 · 打开作品 | Creator research · Open a work | 크리에이터 조사 · 작품 열기 |
| BMP-06 | 内容中心 · 编辑新版本 | Content studio · Edit a new version | 콘텐츠 스튜디오 · 새 버전 편집 |
| BMP-07 | Campaign计划 · 查看进度 | Campaign plan · View progress | 캠페인 계획 · 진행 상황 보기 |
| BMP-08 | 播客工作室 · 打开节目 | Podcast studio · Open a project | 팟캐스트 스튜디오 · 프로젝트 열기 |
| BMP-09 | 品牌评价 · 比较时段 | Brand evaluation · Compare periods | 브랜드 평가 · 기간 비교 |
| BMP-10 | 品牌风险 · 查看响应进展 | Brand risks · View response progress | 브랜드 위험 · 대응 진행 상황 보기 |
| BMP-11 | 竞品分析 · 查看可比项 | Competitor analysis · View comparable items | 경쟁사 분석 · 비교 가능한 항목 보기 |
| AI-01 | 开始一项工作 · 保存草稿 | Start a task · Save draft | 작업 시작 · 초안 저장 |
| AI-02 | 执行进度 · 查看结果 | Task progress · View the result | 작업 진행 · 결과 보기 |
| AI-03 | 结论与来源 · 核对引用 | Findings and sources · Check citations | 결과 및 출처 · 인용 확인 |
| AI-04 | 能力目录 · 查看适用范围 | Capabilities · View supported use | 기능 목록 · 지원 범위 보기 |
| AI-05 | AI状态 · 查看诊断 | AI status · View diagnostics | AI 상태 · 진단 보기 |
| SYS-01 | 运行状态 · 查看依赖 | Runtime status · View dependencies | 실행 상태 · 의존성 보기 |
| SYS-02 | 采集状态 · 查看真实运行 | Collection status · View actual runs | 수집 상태 · 실제 실행 보기 |
| SYS-03 | 数据完整性 · 查看字段来源 | Data integrity · View field lineage | 데이터 무결성 · 필드 출처 보기 |
| SYS-04 | 当前操作记录 · 查看决定 | Current action history · View a decision | 현재 작업 기록 · 결정 보기 |
| SYS-05 | 外观 · 预览此设备 | Appearance · Preview on this device | 화면 모양 · 이 기기에서 미리보기 |
| SYS-06 | 受控浏览器 · 返回当前来源 | Controlled browser · Return to the source | 제어된 브라우저 · 현재 출처로 돌아가기 |
| SYS-07 | 验收状态 · 查看未完成项 | Acceptance status · View remaining items | 검수 상태 · 남은 항목 보기 |
| SYS-08 | 日志与追踪 · 打开任务记录 | Logs and traces · Open task details | 로그 및 추적 · 작업 기록 열기 |
| SH-01 | 发现与创作 · 打开来源/制作镜头 | Discover and create · Open a source / build shots | 발견 및 제작 · 출처 열기 / 장면 구성 |
| SH-02 | 来源与证据 · 阅读单篇 | Sources and evidence · Read one item | 출처 및 증거 · 항목 읽기 |
| SH-03 | 数据定义 · 查看来源链 | Data definitions · View lineage | 데이터 정의 · 출처 흐름 보기 |
| SH-04 | 成果与导出 · 打开版本 | Deliverables and export · Open a version | 결과물 및 내보내기 · 버전 열기 |
| SH-05 | 评估与学习 · 查看审核结果 | Evaluation and learning · View review results | 평가 및 학습 · 검토 결과 보기 |
| SH-06 | 通知与任务 · 继续处理 | Notifications and tasks · Continue work | 알림 및 작업 · 계속 처리 |

#### Public Website 核心文案（不含账号/登录入口）

| 中文 | English | 한국어 |
|---|---|---|
| 产品 | Product | 제품 |
| 案例 | Stories | 사례 |
| 资源与帮助 | Resources & help | 자료 및 도움말 |
| 从真实材料出发 | Start with real materials | 실제 자료에서 시작합니다 |
| 把来源、判断与行动连成可复核的工作 | Connect sources, decisions, and actions in work you can review | 출처, 판단, 행동을 검토 가능한 작업으로 연결합니다 |
| 一次真实工作怎样走完 | Follow one real task from start to finish | 실제 작업이 처음부터 끝까지 이어지는 과정 |
| 从空白开始创作：提案、文稿、视频或播客 | Create a proposal, document, video, or podcast from a blank start | 빈 화면에서 제안서, 문서, 영상 또는 팟캐스트 만들기 |
| 研究与业务联动是可选路径 | Connect research to business work when it helps | 필요할 때 조사 결과를 비즈니스 작업에 연결 |
| 常见问题 | Frequently asked questions | 자주 묻는 질문 |
| 进入工作区 | Enter the workspace | 작업 공간으로 이동 |
| 播放演示 | Play the demonstration | 시연 재생 |
| 暂停演示 | Pause the demonstration | 시연 일시 정지 |
| 静音 | Mute | 음소거 |
| 开启声音 | Turn sound on | 소리 켜기 |
| 查看文字步骤 | View the written steps | 단계 설명 보기 |
| 本演示对应序境在[版本/日期]实际可操作能力。 | This demonstration shows capabilities available in LUMENIS [version/date]. | 이 시연은 LUMENIS [버전/날짜]에서 실제로 사용할 수 있는 기능을 보여줍니다. |
| 演示暂不可播放；查看文字步骤。 | The demonstration can't play right now. View the written steps. | 지금은 시연을 재생할 수 없습니다. 단계 설명을 확인하세요. |

Public Website 页头不显示“账号入口·后置”、登录、注册或账号占位。视频任何版本/日期和值仅在实录已对应线上真实功能时替换占位；无障碍字幕/静音/播放失败回退是实际控制，不可只画装饰按钮。

**跨屏按钮/状态词：**

| 中文 | English | 한국어 |
|---|---|---|
| 全部范围 | All available scope | 전체 범위 |
| 打开原文 | Open original | 원문 열기 |
| 查看来源与证据 | View source and evidence | 출처 및 증거 보기 |
| 返回原任务 | Return to original task | 원래 작업으로 돌아가기 |
| 保存为新版本 | Save as a new version | 새 버전으로 저장 |
| 尚未采集 | Not collected yet | 아직 수집되지 않음 |
| 未取得 | Not retrieved | 가져오지 못함 |
| 部分结果 | Partial result | 일부 결과 |
| 仅有公开预览 | Public preview only | 공개 미리보기만 있음 |
| 未验证 | Unverified | 검증되지 않음 |
| 暂不可读 | Not currently readable | 현재 읽을 수 없음 |
| 需要授权 | Authorization required | 권한 필요 |
| 本次只读，不对外写入或发布 | Read-only this time; no external writes or publishing | 이번에는 읽기 전용이며 외부 쓰기나 게시를 하지 않습니다 |
| 暂无新记录 | No new records | 새 기록 없음 |
| 未完整观看 | Not fully viewed | 끝까지 시청하지 않음 |

**失败/恢复消息模板（仅在对应owner返回该状态时使用）：**

| 中文 | English | 한국어 |
|---|---|---|
| 检索未完成。已保存的来源与原任务仍保留。 | Search didn't finish. Saved sources and the original task are still here. | 검색을 완료하지 못했습니다. 저장된 출처와 원래 작업은 그대로 있습니다. |
| 访问被拒绝；没有执行外部操作。 | Access was denied. No external action was performed. | 접근이 거부되었습니다. 외부 작업은 실행되지 않았습니다. |
| 来源需要人工验证；其他可用来源不受影响。 | This source needs human verification. Other available sources are unaffected. | 이 출처는 사람의 확인이 필요합니다. 다른 사용 가능한 출처에는 영향이 없습니다. |
| 媒体暂不可用；仍可阅读已取得的文字。 | Media is unavailable right now. Retrieved text is still available. | 현재 미디어를 사용할 수 없습니다. 가져온 텍스트는 계속 볼 수 있습니다. |
| 保存未完成；当前草稿仍保留。 | Save didn't finish. The current draft is still here. | 저장을 완료하지 못했습니다. 현재 초안은 그대로 있습니다. |
| 已取消本次操作；未确认内容不会继续执行。 | This action was cancelled. Unconfirmed work won't continue. | 이 작업이 취소되었습니다. 확인되지 않은 작업은 계속 실행되지 않습니다. |
| 资料有更新；旧版本已保留，请选择如何继续。 | The source has changed. The previous version is preserved; choose how to continue. | 자료가 변경되었습니다. 이전 버전은 보존되어 있습니다. 계속할 방법을 선택하세요. |

**预算/资源可行性文案：**

| 中文 | English | 한국어 |
|---|---|---|
| 方案A / 方案B | Option A / Option B | 안 A / 안 B |
| 此任务未提供预算/资源数据 | No budget or resource data was provided for this task | 이 작업에는 예산 또는 자원 정보가 제공되지 않았습니다 |
| 估算 / 报价 / 确认承诺 / 实际支出 | Estimate / Quote / Confirmed commitment / Actual spend | 추정 / 견적 / 확정 약정 / 실제 지출 |
| 超出硬上限 | Exceeds the hard cap | 상한 예산 초과 |
| 当前不可行 | Not feasible under current constraints | 현재 조건에서는 실행 불가 |
| 查看受影响内容 | Review affected work | 영향을 받는 작업 보기 |
| 保留旧版本 | Keep the previous version | 이전 버전 유지 |
| 编辑所选方案 | Edit the selected option | 선택한 안 편집 |
| 采用此方案 | Adopt this option | 이 안 채택 |

**逐屏线框中的通用控件与媒体术语：**

| 中文 | English | 한국어 |
|---|---|---|
| 搜索 | Search | 검색 |
| 筛选 | Filter | 필터 |
| 全部 | All | 전체 |
| 查看 | View | 보기 |
| 查看变化 | View changes | 변화 보기 |
| 打开 | Open | 열기 |
| 返回 | Back | 뒤로 |
| 关闭 | Close | 닫기 |
| 重试 | Retry | 다시 시도 |
| 打开原帖 | Open post | 게시물 열기 |
| 查看原来源 | Open original source | 원본 출처 보기 |
| 回列表 | Back to list | 목록으로 돌아가기 |
| 回到原任务 | Return to original task | 원래 작업으로 돌아가기 |
| 继续 | Continue | 계속 |
| 取消 | Cancel | 취소 |
| 保存 | Save | 저장 |
| 保存草稿 | Save draft | 초안 저장 |
| 编辑 | Edit | 편집 |
| 比较版本 | Compare versions | 버전 비교 |
| 撤销 | Undo | 실행 취소 |
| 重做 | Redo | 다시 실행 |
| 只读搜索 | Read-only search | 읽기 전용 검색 |
| 进入任务编辑 | Open task editor | 작업 편집 열기 |
| 添加现有材料 | Add existing materials | 기존 자료 추가 |
| 选入当前Brief | Add to the current Brief | 현재 Brief에 추가 |
| 查看证据 | View evidence | 증거 보기 |
| 带到已有Brief | Add to existing Brief | 기존 Brief에 추가 |
| 标记待核实 | Mark for verification | 검증 필요로 표시 |
| 采用本段 | Keep this passage | 이 단락 채택 |
| 拒绝本段 | Reject this passage | 이 단락 거부 |
| 播放头 | Playhead | 재생 헤드 |
| 时间线 | Timeline | 타임라인 |
| 时间范围 / 时间窗 | Time range / time window | 기간 / 시간 범위 |
| 工作范围 | Work scope | 작업 범위 |
| 检查器 | Inspector | 인스펙터 |
| 混音器 | Mixer | 믹서 |
| 循环区间 | Loop range | 반복 구간 |
| 独奏 | Solo | 솔로 |
| 静音 | Mute | 음소거 |
| 播放 | Play | 재생 |
| 暂停 | Pause | 일시 정지 |
| 前一帧 / 后一帧 | Previous frame / Next frame | 이전 프레임 / 다음 프레임 |
| 试听所选区间 | Preview selected range | 선택 구간 미리 듣기 |
| 本机应用 | Apply on this device | 이 기기에 적용 |
| 恢复默认 | Restore defaults | 기본값 복원 |
| 上传新壁纸 | Upload a wallpaper | 새 배경 이미지 업로드 |
| 纯白 / 纯黑 / 纯色 | Pure white / Pure black / Solid color | 순백 / 순흑 / 단색 |
| 恢复上次值 | Restore previous setting | 이전 설정 복원 |
| 任务关键词 | Task keywords | 작업 키워드 |
| 任务菜单 | Task menu | 작업 메뉴 |
| 任务目标/受众/市场 | Task goal / audience / market | 작업 목표 / 대상 / 시장 |
| 保留此预览状态 | Keep this preview state | 이 미리보기 상태 유지 |
| 打开本篇 | Open this item | 이 항목 열기 |
| 回商业运营 | Return to commerce operations | 상업 운영으로 돌아가기 |
| AI建议 | AI suggestion | AI 제안 |
| 已证实来源 | Verified source | 확인된 출처 |
| 规则关联/待核实 | Rule-based relation / needs review | 규칙 기반 연결 / 검토 필요 |
| 引用A / 引用B | Citation A / Citation B | 인용 A / 인용 B |
| 发现 | Discover | 발견 |
| 成果文件 | Deliverable | 결과물 |
| 结果阶段 | Result stage | 결과 단계 |
| 媒体查看器 | Media viewer | 미디어 뷰어 |
| 字幕 | Captions | 자막 |
| 导出 | Export | 내보내기 |
| 应用到所选片段 | Apply to selected clip | 선택한 클립에 적용 |
| 应用到此轨道 | Apply to this track | 이 트랙에 적용 |
| 选择轨道 | Select a track | 트랙 선택 |
| 未知原因 | Reason unknown | 원인 알 수 없음 |

**新增操作与无障碍语义词条（定位到现有Shared zh-CN/en/ko locale owner；未实现的key只表示目标文案）：**

| Semantic role / copy key | 中文 | English | 한국어 |
|---|---|---|---|
| `collection.saved_records` | 已存记录 | Saved records | 저장된 기록 |
| `collection.new_request` | 新建采集 | New collection request | 새 수집 요청 |
| `collection.plan` | 采集计划 | Collection plan | 수집 계획 |
| `collection.search_manual` | 发起一次人工搜索 | Start a manual search | 수동 검색 시작 |
| `collection.auto_optin` | 启用已授权计划 | Enable the authorized schedule | 승인된 일정 사용 |
| `collection.pending_cancel` | 取消待执行项 | Cancel pending items | 대기 중인 항목 취소 |
| `collection.pause_future` | 暂停后续计划 | Pause future runs | 이후 실행 일시 중지 |
| `collection.partial_result` | 部分完成 · 已保留已取得内容 | Partially complete · Retrieved items are preserved | 일부 완료 · 가져온 항목은 보존되었습니다 |
| `collection.result_unknown` | 执行结果待确认；请先查看原任务 | Result unconfirmed; check the original task first | 실행 결과가 확인되지 않았습니다. 먼저 원래 작업을 확인하세요 |
| `collection.publish_time` | 发布时间/事件时间 | Published / event time | 게시 / 이벤트 시간 |
| `collection.capture_time` | 采集时间 | Capture time | 수집 시간 |
| `registry.add_cth_subject` | 新增经营主体 | Add a commercial entity | 사업 주체 추가 |
| `registry.add_bmp_brand` | 新增品牌身份 | Add a brand identity | 브랜드 정체성 추가 |
| `registry.name_zh` | 中文名称（必填） | Chinese name (required) | 중국어 이름(필수) |
| `registry.name_en` | English name（必填） | English name (required) | 영어 이름(필수) |
| `registry.industry` | 行业 | Industry | 업종 |
| `registry.keywords` | 已核实关键词 | Verified keywords | 확인된 키워드 |
| `registry.exact_duplicate` | 已有精确匹配的登记 | An exact registry match already exists | 정확히 일치하는 등록 항목이 있습니다 |
| `registry.relationship_unverified` | 主体已登记，关系尚未核实 | The entity is registered; relationships are not verified | 주체는 등록되었지만 관계는 아직 확인되지 않았습니다 |
| `registry.permission_denied` | 本次登记未获批准；没有创建主体 | This registration was not approved; no entity was created | 등록이 승인되지 않아 주체를 만들지 않았습니다 |
| `import.choose_file` | 选择文件 | Choose a file | 파일 선택 |
| `import.use_purpose` | 此材料用于 | Use this material for | 이 자료의 사용 목적 |
| `import.confirm_named_use` | 确认此文件用于当前任务 | Confirm this file for the current task | 이 파일을 현재 작업에 사용한다고 확인 |
| `import.approval_required` | 需要确认本次材料使用 | Confirm use of this material | 이 자료의 사용 확인 필요 |
| `import.ready_for_retry` | 已确认；可用同一文件继续 | Confirmed; continue with the same file | 확인되었습니다. 같은 파일로 계속 진행하세요 |
| `import.partial_media` | 部分媒体/文字已取得 | Some media or text was retrieved | 일부 미디어 또는 텍스트를 가져왔습니다 |
| `import.invalid_file` | 文件无法读取；现有项目未更改 | The file can't be read; the current project is unchanged | 파일을 읽을 수 없습니다. 현재 프로젝트는 변경되지 않았습니다 |
| `shotplan.line_state` | 线稿完整 | Line drawing complete | 선화 완료 |
| `shotplan.color_state` | 彩色分镜完整 | Colored storyboard complete | 컬러 스토리보드 완료 |
| `shotplan.review_state` | 待逐镜审阅 | Awaiting shot-by-shot review | 컷별 검토 대기 |
| `shotplan.confirmed_version` | 已确认此版本 | This version is confirmed | 이 버전이 확인되었습니다 |
| `shotplan.confirmation_stale` | 脚本/场景已变化；受影响镜头需要重新确认 | Script or scene changed; affected shots need renewed confirmation | 대본 또는 장면이 변경되었습니다. 영향을 받은 컷을 다시 확인해야 합니다 |
| `version.conflict` | 本机草稿与已保存版本不同；尚未覆盖 | The local draft differs from the saved version; nothing was overwritten | 로컬 초안이 저장된 버전과 다릅니다. 덮어쓰지 않았습니다 |
| `version.keep_local` | 将本机稿另存为独立版本 | Save the local draft as a separate version | 로컬 초안을 별도 버전으로 저장 |
| `version.source_changed` | 来源已变化；查看受影响内容 | Source changed; review affected work | 출처가 변경되었습니다. 영향을 받은 작업을 확인하세요 |
| `memory.context_used` | 本次任务使用的上下文 | Context used for this task | 이번 작업에 사용된 컨텍스트 |
| `memory.not_returned` | 当前没有可确认的记忆来源 | No memory source was returned for this task | 현재 확인할 수 있는 메모리 출처가 반환되지 않았습니다 |
| `skill.read_only` | 当前只可查看已验证能力 | Only verified capabilities can be viewed at this time | 현재는 검증된 기능만 볼 수 있습니다 |
| `skill.update_in_flight` | 能力正在运行；版本切换由Owner安全处理 | The capability is running; its owner manages a safe version change | 기능이 실행 중입니다. 안전한 버전 변경은 담당자가 처리합니다 |
| `evaluation.candidate` | 待评估候选 | Evaluation candidate | 평가 후보 |
| `evaluation.verified` | 已验证版本 | Verified version | 검증된 버전 |
| `evaluation.rollback` | 恢复到已确认的旧版本 | Restore a previously confirmed version | 이전에 확인된 버전으로 복원 |
| `inbox.open_origin` | 打开原任务 | Open the originating task | 원래 작업 열기 |
| `a11y.clip_label` | `{track}轨道，{clip}，从{start}到{end}，{state}` | `{track} track, {clip}, {start} to {end}, {state}` | `{track} 트랙, {clip}, {start}부터 {end}까지, {state}` |
| `a11y.source_row` | `{platform}，{title}，发布时间{published}，采集时间{captured}，{state}` | `{platform}, {title}, published {published}, captured {captured}, {state}` | `{platform}, {title}, 게시 {published}, 수집 {captured}, {state}` |
| `validation.required` | 必填项尚未完成；请检查标记字段 | Required fields are missing; check the marked fields | 필수 항목이 입력되지 않았습니다. 표시된 항목을 확인하세요 |
| `validation.invalid_field` | 输入格式不正确；请检查标记字段 | The value is invalid; check the marked field | 입력 형식이 올바르지 않습니다. 표시된 항목을 확인하세요 |
| `permission.waiting` | 正在等待这项操作的批准 | Waiting for approval for this action | 이 작업의 승인을 기다리는 중입니다 |
| `permission.denied` | 此操作未获批准；没有产生外部影响 | This action was not approved; no external effect occurred | 이 작업은 승인되지 않았으며 외부 영향은 발생하지 않았습니다 |
| `collection.rate_limited` | 来源暂时限流；已取得内容仍保留 | The source is rate-limited; retrieved content is preserved | 출처 요청이 제한되었습니다. 가져온 콘텐츠는 보존됩니다 |
| `collection.cancelled` | 已取消后续执行；已取得内容仍保留 | Future execution was cancelled; retrieved content is preserved | 이후 실행이 취소되었습니다. 가져온 콘텐츠는 보존됩니다 |
| `import.too_large` | 文件超过当前可处理范围；现有项目未更改 | The file exceeds the current processing limit; the project is unchanged | 파일이 현재 처리 한도를 초과했습니다. 기존 프로젝트는 변경되지 않았습니다 |
| `import.offline` | 文件当前不可读取；请重新选择或返回 | The file is currently unavailable; choose it again or return | 파일을 현재 읽을 수 없습니다. 다시 선택하거나 돌아가세요 |
| `import.parse_failed` | 文件未能解析；现有项目未更改 | The file could not be parsed; the project is unchanged | 파일을 해석하지 못했습니다. 기존 프로젝트는 변경되지 않았습니다 |
| `a11y.field_error` | `{field}：{error}` | `{field}: {error}` | `{field}: {error}` |
| `a11y.focus_return` | 已关闭详细信息，焦点回到原操作 | Details closed; focus returned to the previous control | 세부 정보가 닫혔으며 초점이 이전 컨트롤로 돌아갔습니다 |
| `locale.text_unavailable` | 此内容暂无法以所选语言显示 | This content is not available in the selected language | 선택한 언어로 이 콘텐츠를 표시할 수 없습니다 |

`Screen ID`行与已链接ScreenSpec的locale key list构成既有引用；上表Semantic role则将本稿新画控件/状态精确落到同一Shared localization registry，不建立feature-local字典。平台身份、数字、日期/时区、原生平台内容和产品专名不翻译或擅自重排。窄屏/200%字号时文字可换行、错误仍与字段关联、焦点顺序保持可预测；语言变化不得改变platform_id、Task Scope、metric口径、Evidence身份或动作权限。zh-CN/en/ko-KR任一必要译文缺失都是发布前修复项；若运行时意外缺词，只显示Shared locale owner定义的同语言通用回退文案，不得露出内部key/空白控件，且不得改变Task/动作状态。上述字符串是目标稿件而不是已有运行文案，接受稿与当前localized build状态分开。

### 3.5 AIGC与3D动效的合适出场比例

界面里的“AIGC/3D”指帮助用户理解真实工作对象的视觉和交互层，不替代序境已批准的AI/Agent/创作能力，也不表示当前模型、采集数据或业务功能已经可用。没有一个适用于所有页面的固定百分比；按用户任务控制出场：

- **Public Website：**保留完整文字叙事和帮助导航；用一段来自真实可运行路径的操作影片说明 Source→Evidence→工作→可编辑结果。手绘色彩图标/小型对象动效仅用于识别对象或说明许可→处理→结果的状态转换，不循环播放虚构生成内容。
- **Web Workspace / Desktop：**工作区主面积属于当前任务、真实材料和可编辑结果。AI建议只在相关段落、片段或决策处出现，附来源/不确定性/可编辑状态；用户可直接走手动路径。AI执行状态如等待、被拒、失败、部分结果只在owner实际返回时显示。
- **内容创作面：**AI辅助落在被选中的文本段、时间线片段、轨道或音频区间；用户逐条采用/拒绝，预览反映实际工程。播放器、Timeline、Inspector/Mixer等常驻功能不得被聊天面板挤走，也不以波形/发光效果伪造已经生成音画。
- **Mobile Companion：**围绕一个可续接任务显示结果、引用与确认项；不缩放桌面工作台，也不另造无状态聊天页。AI建议可收起，手动阅读/返回/允许的轻操作始终可达。
- **CTH/BMP/数据与SYSTEM页面：**对象标记、线性glyph和颜色只服务于识别与工作状态；报告、证据、数据完整性、授权/错误区域不放装饰性角色或生成式摘要。

3D只在真实空间关系或专业媒体对象能由空间层次更快解释时使用，例如时间线深度/前后关系的可选预览；不得用来代替筛选、证据链接、原生时间/指标或编辑精度。所有非必要运动可关闭并尊重Reduced Motion；核心动作有静态/键盘/触控等价入口。动效和手绘图标不编码权限、成功或覆盖事实，真实状态须有文本/可访问标签。

### 3.6 动作层级与层级切换

- **点击**：主要动作；可键盘焦点。
- **悬浮**：只在桌面提供额外说明/轻微动效，不藏唯一功能。
- **拖拽**：编辑素材、调整片段或网格交互；每个拖拽动作同时有键盘/菜单替代入口。
- **滑动**：切换多图/横向时间线/轻量卡片浏览；显示当前位置并提供显式前后按钮。
- **详情抽屉**：只放当前对象补充信息；支持 Close/Escape/Back 且焦点回到 opener。
- **模态确认**：仅适用于会丢编辑、改变范围或产生外部写入的明确动作；不拿弹窗当页面导航。
- **页面滚动**：网站长叙事/长材料必须可用；桌面工作区靠 pane/层级/横向时间轴解决过长，不通过剪掉功能强行塞一屏。
- **磁吸按钮/自定义光标/图像拖尾/3D**：不全产品打开。网站可对 Hero CTA 有微弱磁吸，桌面仅在高精度时间轴/物件控件做吸附。禁止光标拖尾式图片特效；3D 仅当它解释空间关系/实际作品，必须能关、可降级和支持键盘。

| 交互/控件 | 前态→触发→后态 | 键盘/读屏/Reduced Motion |
|---|---|---|
| 详情抽屉/Sheet | opener保留→详情标题获焦→关闭后焦点回opener；筛选、选择与位置不变 | Escape、系统Back、明确关闭键等价；Reduced Motion直接换态，不用方向暗示重要性 |
| 多图/章节轮播 | 当前第n项/共m项→前后一步→更新原文定位和序号 | 前后按钮与读屏序号并存；键盘可达；滑动不是唯一操作 |
| Timeline片段/轨道 | 选clip→同一clip ID定位；Inspector显示该clip；播放头控制Viewer帧与时码 | `a11y.clip_label`播报轨道/片段/起止/状态；拖拽有键盘/菜单替代；播放头移动不暗中改选中对象；横移≠seek≠trim |
| Timeline键盘编辑 | 选择/逐帧/入出点/分割/修剪/缩放/横移/撤销重做可从键盘或菜单调用 | 只显示当前Editor owner实际注册的快捷键；未冻结键位时提供有名称的命令项，不猜Final Cut/Premiere键码；方向键与时码精度不冲突 |
| ShotPlan确认 | 待审版本→逐镜查看/批注/确认→当前版本已确认；脚本/场景变化仅使受影响镜头过期 | 读屏播报镜号/版次/改变范围；Reduced Motion保留即时文本状态 |
| 加载/部分/字段错误/材料导入 | 保留输入→Owner实际回执→逐字段错误、重复/拒绝、受理/部分/解析失败及下一步 | 错误通过`aria-describedby`关联字段；LiveRegion仅播报真实状态；失败不清表单/旧项目，焦点转错误摘要并可回原字段 |
| 版本冲突/断网/未知回执 | 草稿保留→回查同一Task/Artifact→比较→用户决定保存/返回；不盲重发外部动作 | 播报保存成功/待确认/未知回执；Reduced Motion直接显示差异与可执行动作 |
| 外观/壁纸/时间轴滑杆 | 当前值→键盘/触控调整→预览→应用或取消 | 显示单位/范围/当前值；高饱和背景上仍有焦点框；无闪烁/循环动画，尊重Reduced Motion |

### 3.7 权限和结果

普通前端没有登录/角色拦截页。任何会对外产生影响的动作在**用户已经选择该动作时**才进入实际权限链：

~~~text
选择明确动作 → 显示目标/内容/对象/影响 → 检查 Permission/Approval
→ 允许：请求真实 Effect → 显示实际回执/Trace
→ 拒绝/超时/未知：不产生伪效果 → 回到原任务
~~~

“按钮已点”“Agent 已建议”“服务 200”都不等于 Effect 已完成。回执、来源、保存版本和具体状态按 SYSTEM/Evidence/Core 所有者响应。

---

## 4. 四端功能版图

| 能力 | 官网 | Web Workspace | Desktop App | Mobile Companion |
|---|---|---|---|---|
| 了解产品/流程 | 品牌、能力、合法示例、实际操作影片、FAQ；唯一 CTA 为直达工作区，不放账户/登录入口 | 产品入口后的真实任务选择 | 产品入口后的真实任务选择 | 产品入口/任务续接 |
| 经营与品牌研究 | 解释真实功能；不显示私有实时数据 | 完整筛选、对比、来源阅读和报告 | 多区域研究、持续监控/任务接续 | 读、通知、聚焦详情、轻编辑/确认 |
| 全域/焦点 | 展示能力边界；不请求用户选择经营实体 | 全局默认，任务可选 narrowing | 全局默认，任务可选 narrowing | 全局默认，任务可选 narrowing |
| Source/Evidence | 以经许可示例和操作视频展示 | 多窗/阅读与筛选 | 资料组织、阅读、导出、重开 | 原文/媒体和来源时间线阅读 |
| 视频创作 | 官网只实录当前真实可用并获准的操作 | 终态完整项目/素材/ShotPlan（适用时）/Viewer/Inspector/多层Timeline/B-roll/字幕与音轨/已批准效果/导出与重开；实现缺口另列，不缩减终态 | 专业素材箱、多轨时间线、键鼠精编、画面/音频检查器、实际渲染与工程恢复 | 预览/逐帧/时码/逐镜审阅/来源字幕/适用轻操作；密集Timeline接续Web/Desktop，不缩成桌面界面缩图 |
| 播客 | 官网只实录当前真实可播放的文件音频/脚本/编辑路径 | 终态文件音频/脚本/时码/波形/多轨Mixer/已批准Effects与Automation/分段修订/试听/导出/重开；当前Owner字段/Renderer缺口另列 | 专业Podcast工作台含章节/Script/音轨同步、逐轨控制、自动化、效果、监听、混音版本与工程恢复 | 播放/试听/章节和脚本接续/轻量审阅修订；完整混音工程接续Web/Desktop |
| AI/Agent | 展示可复现的实际操作与产物 | 任务起点、引用阅读、审批与版本 | 工作流、创作辅助、文件入口 | 接续、提醒、轻编辑与人工确认 |
| 设置/恢复 | 下载入口/可用性说明/帮助 | 浏览器本机偏好、壁纸和当前任务恢复入口；不假装访问OS桌面壁纸 | 设备本地偏好/本地媒体/深度恢复入口 | 设备本地偏好、读屏、触控、通知和任务跟进 |
| 滚动/布局 | 可以跟随故事章节自然纵向滚动 | 小页面滚动，主要靠分栏/抽屉 | 编辑时间线横向拖动/缩放；编辑器内控件按需滚 | 每页围绕一个任务；长文独立滚动；媒资/卡片可横滑 |
| 当前未实现的批准能力 | 官网只实录真实可用能力 | 当前版本在原任务中显示准确的未接通/阻断与恢复状态；终态正常操作仍保留，不以Unavailable页面替代设计 | 依赖/运行状态与真实结果分开；不拿配置替代成功 | 只呈现当前端实际可用动作，但跨端任务和移交目标不删减 |

---

### 4.1 全产品用户流程与跨能力衔接

下列流程覆盖当前批准的工作目标；它们不是新增服务或额外 Screen ID。每一步都由既有 CTH/BMP/Shared/SYSTEM/AI Owner 提供真实数据和动作。缺少服务时，目标能力仍保留在产品范围里并标明缺口；正常路径不能被单一 unavailable 状态取代。

#### 流程 A：从四个产品入口接续同一个工作

~~~text
Public Website 的“进入工作区” → Web Workspace
Web Workspace / Desktop App / Mobile Companion
              └──── 同一Product Core与跨端Task/Artifact ────┐
                   有可恢复的Task/Artifact → 续接原工作      │
                   没有目标Task/返回历史 → ACC-03/全部范围   │
                                                             │
用户报告的桌面快捷入口A/B/C/D → 当前接受版Desktop App       │
   每个入口保留实际深链/任务目标；无有效目标才落ACC-03       │
                                                             ↓
                       工作结果/返回原来源/继续下一步
~~~

四个产品面是Public Website、Web Workspace、Desktop App、Mobile Companion；四个桌面快捷入口是主机侧启动方式，不是另外四个产品表面，也不表示把所有任务强制重定向到一个首页。目标是四个入口都打开同一当前接受版Desktop App，并保留各自实际深链/任务目的；本机四个快捷方式具体名称和目标尚未在本轮运行核对，不能擅自统一改成ACC-03。无Task/深链才进入ACC-03且默认全部范围；有可恢复任务就优先续接。当前源码root仍CTH-01是另一项独立现状缺口。官网CTA直达开放工作区，不经过产品登录页。

#### 流程 B：全局发现 → 阅读来源 → 研究/决策 → 交付报告

~~~text
ACC-03 GLOBAL/ALL
  → 选择 SH-01 Discover（目标能力、callable 待绑定）或进入已有 CTH-03 人工只读检索 / SH-02 / BMP-03 阅读入口
  → GLOBAL/ALL 默认；平台以稳定 platform_id 选择；时间与关键词只取用户/当前任务给定值，不预填特定商场
  → CTH-03 只有在用户明确确认本次只读检索后，才调用已有 collector search POST；普通页面打开仍只是读取当前绑定数据
  → 返回记录保留原始身份、source URL、发布时间/采集时间、scope 与 Evidence 投影；点击进入同一条原帖详情/SH-02 reader
  → CTH-04 事件/Case 或 BMP-03 市场判断
  → CTH-09 决策 / BMP-07 Campaign / SH-01 Brief
  → CTH-10 / SH-04 报告或Artifact
  → 保存新版本 → 重新打开 → 依据最新的真实结果评价
~~~

保存用户的目标、预算（仅任务已有字段）、范围、时间窗、材料、引用和版本。跨到下一页不重复输入已经绑定的对象；改变一个上游条件时提示受影响的后续产物，并允许保留旧版。每个数值和总结都能回到相同 source scope；不知道实际市场覆盖时保留 unknown/partial。

##### 从本机材料进入已批准工作（SH-01/Shared Source owner）

```text
现有任务/全部范围 → [添加现有材料] → 系统文件选择器
→ 预览真实文件名/类型/大小及可检测页数/时长/轨道（未知则不显示）
→ 选当前Task/Scope和用户用途；不选用途即不能确认
→ 若需要批准，显示“使用哪份材料/用于哪个范围”的确认单
→ 现有批准读回 ready_for_retry 后以同一文件字节/绑定重试
→ inspect 返回真实介质类型/时长/stream后进入当前项目或Research
→ 保存来源/Artifact引用 → 打开SH-02阅读/制作 → 回原工作
```

当前界面接 SH-01 已有`POST /api/experience/content-sources?filename=...`、`POST /api/experience/content-source-confirmations/<id>`和实际inspect owner；首发若回`CONTENT_SOURCE_APPROVAL_REQUIRED`则显示具体材料/范围/用途，确认收到`ready_for_retry`后只重试同一文件绑定，不换字节不重复确认。后续状态逐项表达取消、非法/过大、离线、解析失败、缺失音视频轨、部分可读、scope过期和重试失败；旧项目和已接收文件不会被新选择覆盖。文件“被读取”、被Insight引用、入Evidence/Canonical和成为可训练材料是不同状态，按对应既有owner回执显示。此处不推导或添加任意URL Import API；网页URL只能从经批准的既有Importer/Collector工作入口进入。

#### 流程 C：商业问题从观察进入处置

~~~text
CTH-03 变化/来源
 → 用户指定平台/关键词/任务范围，并确认“仅只读搜索；不会发布或对外写入”
 → 现有 `/api/experience/cth/platform-collection/search`（只允许 human/human_ui；现有服务端 scope/Permission 生效）
 → 以实际返回状态回显成功、无新数据、部分、限速、需授权、阻断或错误；失败保留已入库证据并可返回原任务
 → CTH-04 事件关系和时间线
 → CTH-06 读反馈/核实原文
 → CTH-08 创建/更新 Case
 → CTH-09 有依据的决策和责任
 → Permission / Approval / Effect Fence（如有外部动作）
 → 真实 Action 回执与 Evidence
 → CTH-10 报告 / SH-05 评价材料
~~~

拒绝、撤销、权限过期或外部失败不得产生“完成”的 Case/Action 回执；返回原始事件时保留选中事件、过滤器和阅读位置。

#### 流程 D：品牌洞察进入 Campaign 与内容

~~~text
BMP-03 市场来源/主题
 → BMP-01/02 聚焦已授权品牌和竞品关系
 → BMP-05 创作者比较 / BMP-04 传播观察
 → SH-01 Discover：按该 Brief 的 Subject/BrandFocus（可空）、平台和时间读趋势/样本热点/相似作品
 → 用户选择有来源定位、相关性说明和实际使用授权的参考
 → 单篇帖子只作为一条有时间/平台/样本边界的来源；只有符合现有 metric/coverage 合同的集合才能形成趋势或市场结论
 → BMP-06 内容 Brief 和版本
 → BMP-07 目标、受众、渠道、里程碑
 → BMP-08 播客 / SH-01 视频 / 其它已支持内容成果
 → 审核、授权、实际交付
 → BMP-09/10/11 评价 / 风险 / 对标
 → 归档可复核 Artifact 并返回 Campaign
~~~

简报中的品牌、来源、客群、时间窗和引用沿用当前任务的精确上下文；换 BrandFocus 后明确提示，不把不同品牌的材料静默混到一个产物里。

Discover 不是综合热榜、独立市场事实页或社交媒体复刻。趋势须有可比时间序列/观察窗口；热点只说明所见语料与平台口径；相似作品显示匹配维度、差异、来源、时间和证据定位。结果进入既有 Brief/创作 Owner，不能被直接写成消费者总体需求、品牌绩效或因果结论。当前 SH-01 细化和绑定仍待 Owner 冻结。

#### 流程 E：AI/Agent 是工作中的可见助手

~~~text
AI-01 编辑任务/来源范围
 → 校验当前真实可用能力与 Evidence
 → AI-02 显示真实的任务阶段和产生物
 → AI-03 逐条核对结论及引用
 → 用户编辑/拒绝/补料/采纳
 → 保存为新 Artifact/Case/Brief 版本
 → 后续修改/导出/Outcome 评价
~~~

若 Gateway / model / tool 真实不可用，用户仍可保存任务草稿并进入可用手动路径；不自动切换已退役 Provider、不伪造生成文本。工具调用拒绝、等待授权和运行失败各自有明确返回。

#### 流程 F：视频编辑完整交付

~~~text
真实目标/已有脚本 →（需镜头规划时）ShotPlan续接
→ 完整线稿 → 完整彩色分镜 → 逐镜批注/确认当前版本 → 进入剪辑时间线
或：无分镜要求的素材任务 → 导入/选择真实媒体 → 查看来源/格式 → 建立/打开工程
→ 主故事线粗剪 → B-roll/字幕/音轨 → 精剪/变换/调色/混音
→ AI 建议（可选）/人工检查 → 预览
→ 保存工程版本 → 选择可用导出设置 → 导出
→ 重新打开成果 → 修订或评价
~~~

ShotPlan只用于确有逐镜构思的故事/广告任务，不强塞给纯素材粗剪、Podcast或其他不需要分镜的工作。每个确认绑定当前脚本/分镜版本；变更脚本/场景后按既定Owner判定影响镜头并要求其重新审阅，未变部分保留原确认。拖入/替换素材前显示会影响的片段和源文件，确认前可取消；剪辑采用非破坏版本。失败渲染保留工程和素材定位，不得显示成功的导出文件。目标态仍完整包含已批准的效果/声轨/字幕与导出能力；当前codec/processor/Renderer未绑定的细节在“当前差距”单列，不能因此把最终工作台缩水。

#### 流程 G：播客制作与交付

~~~text
用户自写创作要求/已有文字或获准素材（可空白直接开始；研究/业务Brief可选带入）→ 脚本段落和出处（若适用）→ 导入已有音频文件
→ 脚本/波形对齐 → 多轨剪辑/淡入淡出/混音/监听
→ AI 建议（可选并逐项确认）→ 预听
→ 保存项目版本 → Render/导出 → 重开音频与脚本
→ Outcome/反馈评价 → 返修版本
~~~

本产品闭环继续完成文件音频导入、理解、编辑、真实播放/试听和输出；文字修改与音频/声音修改作为独立对象和版本，明确哪一个发生了变化。实时录音/麦克风采集按用户明确后置边界保留：它不出现在本轮默认工作流/按钮，恢复条件是整体产品闭环后由 Product Owner 另行授权。文件格式不支持、媒体解码失败、音频服务离线和渲染失败仍有局部恢复。

#### 流程 H：外观和创作偏好

~~~text
SYS-05 外观入口 → 选白/黑/纯色/壁纸/模糊选项
→ 预览文字、工具、统计、媒体控制多种表面
→ 在当前设备保存已有偏好/取消 → 回正在处理的页面
~~~

移动端读取无障碍字号/浅深模式时覆盖默认预览；Web 不假装能读到 OS 桌面底图。外观偏好和用户壁纸文件按当前设备的外观/文件 owner 本地使用；不擅自跨设备同步原图或产生新云存储。用户可在另一个设备重新选择相同预设或自己的文件。上传图像失败、取消和撤销不改变当前偏好。

#### 流程 I：平台接入、会话复用、恢复与继续任务

~~~text
用户先选择“查看已存记录”或“新建来源任务”
 → 已存记录：按 stable platform_id / 发布时间 / 采集时间过滤，不发采集请求
 → 新任务：选择真实已登记平台/来源与任务目的；六平台只是当前验收基线，新增平台沿同一PlatformManifest/Adapter合同接入
 → MANUAL为普通用户默认；最终用户AUTO计划需单独设置/确认；Owner批准的产品自有公开基线AUTO另行标识
 → 显示任务Scope/允许来源/目的/时间语义/内容深度/触发频率/到期/停止方式（只显示现有Owner真实提供的字段）
 → PlatformSession返回真实状态
    ├ READY → 正常执行
    ├ AUTH_REQUIRED → LumenisPlatformRecoverySheet
    ├ LOGIN_FORM_REQUIRED → RecoverySheet调用受控SYS-06
    ├ VERIFY / CAPTCHA → 明确人工验证，不伪装成普通登录
    ├ BLOCKED / COOLDOWN → 停止该来源请求，其他来源继续
    ├ WORKER_UNAVAILABLE / NOT_CONFIGURED / UNKNOWN → 明确原因
 → 用户完成合法平台步骤后，服务端重新读取真实Session/Worker/Risk健康
 → 只有健康回读通过才恢复原Collector Task
 → Collector沿同一Task/attempt/receipt继续，已完成来源不重复执行
 → Source/Evidence/Canonical接收真实结果
 → 按平台显示待执行/运行/已接收/重复/部分/等待恢复/失败/完成与真实回执
~~~

屏幕对应 CTH-03（具体来源任务）、SYS-02（平台能力/Session/计划/执行/receipt）、SYS-06（需要受控网页交互时的Browser capability）、SH-02/CTH/BMP来源消费者，以及跨这些工作面的统一 `LumenisPlatformRecoverySheet`。这里的登录/授权只指第三方平台连接器，不是序境产品账号或登录墙。

##### 统一恢复Sheet：一个恢复层，不叠平台弹窗

~~~text
当前任务被局部暂停
┌ 序境 · 恢复数据源 ───────────────────────────┐
│ 3 个来源需要处理                             │
│ ● 小红书      需要扫码                       │
│ ○ 抖音        需要重新登录                   │
│ ○ Instagram  需要安全验证                   │
├──────────────────────────────────────────────┤
│ 当前：小红书                                 │
│ [真实平台二维码 / 受控登录区域 / 验证说明]   │
│ 状态：等待扫码 → 已扫描 → 正在验证 → 已恢复  │
│ [稍后处理] [取消本来源]                      │
└──────────────────────────────────────────────┘
完成一个 → health readback → 恢复该来源Task → 自动切到下一项
~~~

同时出现多个平台问题时只使用一个 RecoverySheet 和一个当前恢复项；不叠多层 modal/alert。Sheet 标明被暂停的是哪个来源/任务，允许在安全时“稍后处理”，其它可用来源继续。打开时焦点进入Sheet；键盘焦点保持在活动Sheet内；可安全取消时 Escape/系统返回关闭；关闭后焦点回触发控件或下一合理任务位置。扫码等待、已扫描、验证中、恢复完成、冷却等异步状态通过辅助技术播报，但不抢走用户当前焦点。

QR、登录表单、VERIFY 和 BLOCKED/COOLDOWN 是四种不同视觉状态：

~~~text
QR              → 平台二维码 + 等待状态
LOGIN FORM      → SYS-06受控网页区域 + 返回
VERIFY          → “需要完成平台安全验证” + 实际验证入口
BLOCKED/COOLDOWN→ 说明系统已停止该来源请求 + 下次检查/继续其它来源
~~~

前端永远不显示 Cookie、Token、CDP、profile路径、lease/attempt/completion token；这些只属于SYSTEM实现。用户只看见“数据源能否继续、缺什么、当前任务怎样恢复”。

`continuation`、native cursor 和 durable task receipt 三者必须在目标体验中分开：query continuation只表示业务查询计划继续位置；帖子/评论/媒体分页使用平台native cursor；durable receipt代表原任务的服务端连续性。终态receipt重开只能返回原结果或明确拒绝，不得在UI上伪装成“又启动一次”。

需要时按现有Owner显示外部平台、授权身份/范围/到期/撤销方式；敏感凭据只留在现有secret/session owner。普通用户MANUAL默认；AUTO必须逐平台/Scope/用途确认频率、时间、深度和停止入口。当前开发/测试只允许批准的香港/国际XHS身份；个人Mainland XHS账号/Cookie继续禁止触碰。Focus选择或清除都不会自动开始采集。

会话撤销后停止后续请求并停止创建新的计划任务。若已有部分结果，记录准确PARTIAL及真实continuation/native cursor/receipt状态；重新授权后由原任务续接，不创建重复 Source/Evidence，也不把半次运行显示为成功。

#### 流程 J：Skill Store 能力发现到停用

~~~text
AI-04 能力目录 → 搜索名称/任务/owner → 打开能力详情
 → 查技能来源、作者/owner、版本、许可证/信任、输入/输出/权限
 → 启用或停用（现有设置/Skill owner）→ 针对安全输入试运行
 → 显示每次运行、来源、输出Artifact、错误和执行历史
 → 更新前看版本差异/兼容/权限变化 → 确认采用或保持当前版本
 → 停用/卸载后停止新调用、保留历史；需要时可恢复既有版本
~~~

该流程复用现有 AI-04/Skill/License/Permission/Evaluation owner，不另建第二个Store、skill registry或执行runtime。无许可证/责任人/输入输出范围的 skill 只能标作不可启用；卸载不删除已生成Artifact或Evidence。

#### 流程 K：新增 Subject/BrandFocus、别名去重与采集入口

~~~text
CTH-02主体目录 / BMP-02品牌组合里的“新增” → 不放进ACC-02焦点选择器
 → 选择经营主体（CTH company）或品牌主体（BMP brand）
 → 选择/查看该主体身份来源（已有Source/Evidence或可验证的原始来源）；输入双语名称、industry、经核实的keywords（现有POST字段）
 → 检查精确重名 → [打开已有] / [创建不同实体] / [返回修改]
 → 按实际高风险配置审批流程提交给现有Canonical registry
 → created / exact duplicate / invalid / denied / registry unavailable真实回执
 → 只登记身份：不自动选Focus、不采集、不把configured当已验证；created不代表identity Evidence已关联
 → 由现有Source/Evidence与EntityRelation owner补身份来源和有日期的国家/城市/HQ/发源/法域/市场/场内关系
 → 用户选择是否显式发起MANUAL采集；AUTO另行明确opt-in
~~~

新增表单不是新的目录或写入Owner。当前 `POST /api/settings/subjects` 可接受 `domain_id`、`subject_type`、`name_en`、`name_zh`、`industry`、`keywords`；CTH只允许company，BMP只允许brand；创建走现有高风险CONFIG_MODIFY/人工审批，精确中英规范名重复时返回duplicate和既有登记。当前payload不含身份Source/Evidence引用，故返回configured/created仍不能称来源验证或许可准入；身份Source/Evidence必须由既有owner绑定和核实。别名、ISO关系、场内租户、法域和有效期不得塞入此payload；关系使用下述现有EntityRelation语义，用户界面显示人类可读来源/关系而非内部ID。关系HTTP/Permission绑定未知时按缺口列出，不伪造已保存回执。

关系终态使用现有EntityRelation数据库/仓储语义，而不自造relation API：国家关系可选`ORIGIN/HQ/LEGAL_JURISDICTION/OPERATES_IN/VENUE_LOCATION/MARKET_ACTIVITY`，按source owner返回的字段录stable entity、ISO alpha-2国家、ASSERTED/EXPLICIT_ABSENCE、AS_OF_CAPTURE/INTERVAL/UNKNOWN、valid_from/to以及真实SourceEvidence/Note/locale。`review_status`由原Owner审核回执决定，不是用户直接填写的selector。CTH `TENANT_OF`单独记录来源内可核验的租户名、场地/楼层/类别、listing/detail URL、observed_at和可选target BrandFocus。当前有connection-scoped repository writer，但没有已验证的用户-facing permission/HTTP binding；关系编辑仍是目标界面/Owner接线差距，不得画成当前可保存。

名称相似不能自动合并。平台/别名、国家/市场和主体关系由现有 registry/source owner 管理；未验证对象标为候选或Unknown。没有材料/没有采集/过期/部分覆盖是不同状态；不能因新增主体而自动补热度或虚构完整覆盖。

#### 流程 L：原创提案、资源选项和预算变化影响

~~~text
用户创作目标/自写 Brief（可空白开始；研究结果、参考材料或CTH/BMP内容可选带入）
 → 生成可编辑 Brief（目标、受众、范围、材料、来源）
 → 多个真实策略概念/说明（用户可编辑，不以AI结论当事实）
 → 预算/人力/时间等资源备选（字段由现有owner返回，来源和假设可追）
 → 完整可编辑成稿/方案 → 用户审阅/批注/修改 → 新版本
 → 按真实许可导出文档/演示/内容Artifact
 → 目标/预算/来源或范围改变
 → 影响图列出受影响章节/时间线/内容/视频/播客/预算项
 → 用户决定“保留旧版 / 修订所选部分 / 创建分支版本 / 取消”
~~~

入口归 BMP-06/BMP-07、AI-01/02 和 SH-01/SH-04 现有 owner；不新建 Proposal产品。预算和资源数如果当前真实任务未提供，展示“未给出”，不得生成数字填版面。更新必须说明修改原因、新旧差异和下游需重新审阅的成果。外部发布、预算支付等仍须原有 Permission/Approval，不因方案页完成而触发真实副作用。

### 4.2 每种能力在四端各自承诺什么

| 用户能力 | Public Website | Web Workspace | Desktop App | Mobile Companion |
|---|---|---|---|---|
| 首页、导航与工作续接 | 产品叙述和直达“进入工作区”；不放账号/登录入口、菜单或占位 | ACC-03默认首页、完整工作导航、任务/最近保存成果 | 与Web相同的产品范围，外加本机工作连续性 | ACC-03任务接续、待确认事项、原任务返回；不复制首页Hero |
| CTH/BMP研究与管理 | 说明正常操作，不访问/显示私有生产数据 | 完整搜索、筛选、对象关系、趋势、Case/Campaign、报告流程 | Web目标范围 + 大屏并列Evidence/Reader/编辑窗 | 来源阅读、范围/信息查看、标记/审批/轻量录入，逐项依权限/接口 |
| Source/Evidence/采集 | 只演示已实现且许可的操作；不展示私有Production Data | CTH-03明确分“读取已存”和“一次人工只读搜索”；SYS-02终态编辑已批准计划/管理批次与恢复；SH-01接收文件/SH-02读已入库Source | Desktop可并列计划/平台lane/Source Reader；Mobile接收任务状态、可批准操作并回来源；URL输入/计划/pagination字段只经各自现有Owner合同 | 平台筛选→单帖Reader全屏→返回原滤镜；撤权/失败保留Source/Task，不自动重提 |
| Subject/BrandFocus/市场身份 | 解释对象类型及范围含义 | 新建/选择/去重/关系管理的主操作面；重复候选由用户确认 | 深层实体关系核查、Evidence定位、已有采集方式管理 | 搜索/选择Focus、查看关系与成熟度，不在狭屏批量合并 |
| Skill Store | 真实能力介绍与合法文档链接 | 发现/许可/启用/试用/查看历史/更新/停用/卸载，接现有AI04和Skill owner | 大屏审查输入输出、版本变化和运行记录；本地安装仅限已批准支持 | 查看已启用能力、接续/通知和允许的轻确认，不在无许可时运行 |
| Brief/提案/研究 | 展示真实产品案例及相应工作影片 | 全 Brief/策略概念/预算资源备选/可编辑文档/审阅/导出 | 增强长文和本地资料编辑、版本对比、恢复 | 查看方案/批注/轻量修订/审批；预算/目标变化由同一Task记录 |
| 视频工作台 | 官网只演示已真实可用的操作；不向访问者展示私有生产数据 | 完整项目/素材箱/Viewer/Inspector/多层Timeline/ShotPlan与逐镜确认/字幕与音轨/修订/导出/重开；实现缺口单独列账，不缩减终态 | 完整素材库、桌面精准键鼠、多轨/B-roll、画面/音频检查器、时间线横移缩放、实际渲染与工程恢复 | 预览/逐帧/时码、逐镜审阅、来源/字幕和允许的轻量修订/返回；密集Timeline由Web/Desktop完成，不画成缩小控制台 |
| Podcast Studio | 展示真实文件音频/脚本/编辑/试听闭环，实录按当前运行状态说明 | 文件音频/脚本/时码/真实波形、多轨/Mixer/Effects/Automation/分段修订/导出/重开；缺Owner/Renderer字段时作为当前差距，不从目标删除 | 专业Podcast主工作台：章节/Script/音轨同步、声道/音量/声像/自动化/降噪等已批准操作、监听、混音版本/工程恢复 | 播放/试听、章节/脚本校对、逐段审阅与可恢复的轻量文字修订；完整混音工程接续Web/Desktop |
| 实时/麦克风录制 | 不在站点宣传为已支持 | 当前明确后置，不显示当前可用麦克风入口 | 同左；后置恢复时单独检查设备权限与录音路径 | 同左；不能从参考音频软件推断现有麦克风能力 |
| AI/Agent工作 | 只展示当前真有的AI操作，写明版本/状态 | AI-01起任务；AI-02阶段/结果；AI-03证据；AI-04 Skill；AI-05服务诊断 | 同一能力 + 文件任务/编辑器协助；产品不暴露或选择Codex研发模型/provider，AI-05只显示可核验服务状态 | 查看运行进度/结果、通知、人工选择或授权；不把手机聊天当作另一个Agent后台 |
| Report/Artifact/Evaluation | 提供真实示例/帮助/下载入口 | Artifact类型阅读、审阅、历史、导出、评价反馈 | 多文档/媒体对比、文件版本/恢复 | 查看、批注、下载/确认等服务真的支持的动作 |
| 设置/壁纸/恢复 | 产品说明链接 | Web本机偏好/任务返回 | Desktop设备本机偏好/本地媒体恢复 | 手机本地偏好/通知/易读性；壁纸原图不跨端同步 |
| SYSTEM浏览器/权限/Runtime | 解释使用边界；不展示真实私有运行状态 | Controlled Browser、权限提示、工具/采集状态与恢复可见 | 大屏日志、会话选择/媒体文件/状态恢复入口 | 轻量Runtime状态、授权状态/待审批提醒/安全回退 |

当前Public Website不展示登录入口，ACC-01不绘制账号流程；整体产品闭环后是否需要账号/登录由Product Owner重新决定。上表中的 Web/桌面/移动操作不是“只对有数据的一端画个Unavailable页面”；真实正常路径仍属于目标承诺，要由现有服务Owner接通并验收。只有实测缺服务时才可在该条运行结果上标不可用，而不能从产品蓝图删去正常任务。

---

### 4.3 四端、操作系统与窗口尺寸如何重组

四端由当前唯一Multi-Surface Decision定义；不是将一张Web图缩小/放大。按Experience §20的验收宽度`1920 / 1440 / 1280 / 1024 / 768 / 430 / 390 / 360`逐类审，断点由内容和可用窗口决定，不把像素序列误写成8个固定模板。

| Surface / runtime | 主任务与布局 | 输入/返回/媒体边界 |
|---|---|---|
| Public Website（窄屏/宽屏浏览器） | 长叙事章节、产品/业务解释、真实操作视频、帮助/FAQ/联系/已发布下载；网站导航与Workspace入口独立 | Anchor与浏览器Back返回原章节；视频字幕/静音/Reduced Motion/失败文字回退；不读取生产Core、文件系统或User scope |
| Web Workspace（浏览器） | 浏览器内完成研究、Brief、来源阅读和可授权编辑；≥1120逻辑像素可并列Reader/Inspector/TL，760–1119收窄成可逆抽屉，<760转任务列表→全屏详情 | 使用已绑定的浏览器文件/选择接口，不猜客户端路径、不具备Desktop CDP/本地模型/本机目录能力；刷新/Back恢复route、Task、筛选、Selection |
| Desktop App（Windows/macOS） | Website/Web完成后进入原生专项；宽屏多源对照，长时间线/多轨/检查器，获准的本机文件与专业编辑；在窄窗口时折叠导航/Inspector而保留主工作面 | Windows/macOS按各自实际键盘菜单习惯（如Ctrl/Cmd）映射到相同行为；只用现有native picker/路径owner；标题栏关闭、任务退出和媒体路径失效按实际host状态恢复 |
| Mobile Companion（iOS） | Website/Web完成后进入原生专项；通知/真实任务/审核/来源Reader/单镜预览/轻操作；平板可以双区比较，手机一次集中一个任务 | iOS导航、键盘弹起和分享/文件选择只按真实Flutter能力适配；竖屏/横屏保存焦点与timecode；完整多轨编排转续到Web/Desktop，不伪称手机是完整桌面剪辑台 |

| 参考尺寸 | 推荐核对的构图变化（各Screen仍保留自己的构图） |
|---|---|
| 1920 / 1440 / 1280 | 领域导航+任务主面+可收起的Evidence/Inspector；视频/播客实际时间线横跨底部 |
| 1024 | 领域导航缩紧，三栏改为主工作区+可逆Source/Inspector面板；不把一行压成小卡片 |
| 768 | 平板允许List+Detail双区；媒体轨道/列表可横向浏览；保持明确Return，不裁工作按钮 |
| 430 / 390 / 360 | 单任务层级跳转；列表→Reader/Editor sheet；Sticky关键动作不遮原文/键盘；长文只在阅读容器滚动，时间轴水平滚动 |

四个用户桌面快捷入口是Host的启动方式，不等于上述四种产品Surface。每个入口须保留真实已验证的destination/deep link；若有该快捷入口的接受目标，全部更新到同一最新Desktop build，但不可把所有不同任务深链强制改成ACC-03。当前未在OS运行核对四个快捷方式名和目标；后续验收逐个记录其原目标、实际结果和失败恢复，不凭入口图标猜功能。

系统读屏顺序、200%字号、键盘焦点与Escape/Back恢复、44×44或平台允许的实际触控目标、减少动效、横竖屏/窄窗均映射到每个目标端。以上是终态设计与验收路径，不表示本轮已跑过8种宽度或多个OS。

Android/Linux原生客户端不属于当前交付目标；Linux服务端/CI、Linux或Android设备上的支持浏览器访问以及窄屏Web测试仍适用。Website + Web Workspace先闭环，之后才进行Windows/macOS Desktop与iOS Mobile专项实现、打包和设备验收；本行目标不表示这些原生端已实现或已验收。

## 5. 采集结果进入产品后的单帖呈现与跨屏闭环

本节把已有六平台单帖字符草图接回 CTH / SYSTEM / Shared / BMP 既有页面。它是 CTH-03、SYS-02、SYS-06、SH-02、BMP-03 的同一来源工作链，不新增平台中心、采集后台、Screen ID、Evidence 库或采集器。目标画面表达的是完整能力实现后的体验；源码栏只说当前静态事实。

### 5.1 1.5 dated source baseline + 1.6 current contract delta

下表保留 1.5 在 `52cd770c`—`0c9394ef` 期间的源码观察作为 dated provenance，用于解释为什么终态视觉需要这些状态；它不再等于当前 main。1.6 审阅输入基线是 `bbe3310f095b788448a480c4615481bc5da029f8`；`3be8298a` 是 Universal Platform Acquisition 规则来源提交。实现/验收不使用这里的 SHA 代替 fresh main。自 1.5 冻结后，CTH-03 SourceTarget 合同、Collector治理、配置/Gate和若干兼容测试已经变化；当前实现结论必须读取 fresh main / current Screen Spec / runtime，而不能继续引用下表中的“当前”字样作为实时事实。

| 现有位置 | 当前源合同 / 调用事实 | 尚未成立的产品事实 |
|---|---|---|
| CTH-03 读取 | `GET /api/experience/screen/CTH-03` 的 builder 读取 scope 内 Canonical rows，当前调用 `list_scoped_canonical(..., limit=100)`。每行可带 `note_id/subject_id/title/date/captured_at/platform/source_url/quality_status/scope_mode/canonical_scope/read_allowed/projection`；projection 含 canonical reference、Evidence ID、source ID 和 integrity。`truncated` 会把页面 Truth 标为 `partial`。 | 最多100条不是全量市场覆盖；分页/继续读取必须由现有 owner 提供真实 cursor 与状态。当前 row 不含已核实全文、媒体、原生评论或平台互动指标，不允许草图把这些画成已绑定字段。 |
| CTH-03 Flutter | Repository 只调用 settings context 与 CTH-03 Screen GET；`app/lib` 当前没有 `/api/experience/cth/platform-collection/search` 调用。解码器先校验 row projection；之后 Dart `Cth03Record` 只保留 date/title/channel/sentiment/risk，行控件未提供打开来源/证据的操作。 | 当前页面尚未真正发起采集；已由 API 返回的 `source_url`、`captured_at`、`projection/Evidence` 在 UI 模型中丢失，也不能点开同一 Source。把 UI 改成读取未知字段或直接放行不带 Evidence 的行都不合格。 |
| 既有采集动作 | `POST /api/experience/cth/platform-collection/search` 已存在。需 `operator=human` 或 `human_ui` 且 `confirm_read_only=true`，通过既有 `_content_project_scope(..., module="collector")`；可以是一个显式 platform+keyword，或已选业务批次 `business_requests`，两种模式不可混用。接口可走既有 Evidence/Canonical 写入，明确无外部写入/发布路径，并与 Scheduler 控制分开。 | API 存在不代表 CTH-03 已接入、不代表平台已登录/可用、不代表运行成功。状态必须按 Collector 实际返回呈现；未经真实 job/run contract 不显示“已排队/运行中”，也不把读页面等同触发采集。 |
| 平台/会话状态可信度 | 当前治理证据报告对固定main `52cd770`的只读审阅记录了状态API可把无cache文件`ACTIVE`显为会话`ACTIVE`并生成当前`last_check`；部分health只查本地配置即可`SUCCESS/READY`，cache也未按年龄判断。`c7765b87`、`1b238c2f`、`0c9394ef`均未改这些Collector源码路径。 | 未有真实session/worker/endpoint探测时只写“已配置”或“未验证”；不显示绿灯已连接、伪造当前检查时间、last success、覆盖率或真正采集运行。对应状态语义缺陷由C1/C6唯一Collector owner修复，不由前端颜色掩盖。 |
| 平台能力与ID | 当前审计发现 Facebook/X 状态行缺 `manual_collection_enabled`；XHS adapter alias、canonical platform、session owner与独立平台状态表存在命名交叠。 | 列表不可用展示名推断身份、别名或触发资格；不批量开启 X/Facebook，也不制造第二平台注册表。筛选始终用 Canonical 稳定 platform_id，真实可用动作由现有 Collector/Permission 结果决定。 |
| 原生分页与续接 | 当前搜索业务批次的 `continuation` 不等于平台帖子/详情/评论/作者的 native cursor；已有 `checkpoint` 合同字段与 route 也未闭合；同一结果有 CTH search 与 legacy `/v4/adapters/collect` 两个调用路径。 | 普通检索不得承诺完整评论/媒体/创作者数据或断点续采。尚无真实平台cursor时标部分/不可续接；前端只用统一后的现有 Collector/Task owner，不直调第二写入路径、不拼接不同ID的分页结果。 |
| Adapter真实失败 | 同一只读源码审计记录 `CollectionResult.platform` 必填，而 Facebook 多个返回/异常分支当前漏传该字段，可能在适配器构造或异常回退时报错。详情见[2026-10-06开工前审阅证据 §3](../M-PRESTART-BLUEPRINT-AND-COLLECTOR-REVIEW-20261006.md)。 | 这属于真实采集 owner 修复项，不是 UI 伪装“Facebook已连接”或假结果的理由。操作中若返回失败，只显示真实错误状态/受影响范围/可恢复动作；不能让旧V4旁路绕过正式 Source/Evidence/Canonical 链。 |
| 平台通道 / 筛选 | `experience_screens._platform_collection_section()` 当前返回平台 `items`，含 `platform_id`/展示名及返回的状态字段，但没有 row `projection`；同一 Flutter Repository 却对通道 item 使用 v2 projection 校验。`_channel` 将 `platform/name` 映成字符串；Dart 通道/内容模型都没有独立 `platform_id` 字段，ViewModel 以字符串比较 platform/channel。 | stable `platform_id` 才是筛选和回传的键，三语名称只展示。当前模型未区分稳定身份和展示名/原始键，存在不一致失配；须由现有 screen/API owner 正常修合同。绝不可删除 Evidence 投影校验、猜显示名别名或把 UNKNOWN 平台硬匹配。 |
| 查询默认值 | 当前共享平台 helper 把 `default_keyword` 设为“广州太古汇”。 | 与 GLOBAL/ALL 产品默认不相容。未来 UI 清空固定关键词，不自动选该商场或其品牌；用户可在任务里显式输入关键词，Focus 仍为可选筛选。 |
| SYS-02 / SYS-06 | 终态SYS-02是Collector计划/任务/平台lane与恢复工作面；SYS-06是在授权Scope下访问受控来源/Browser的独立工作面。Browser会话、平台能力、Task状态和正式Evidence是不同事实。 | 当前SYS-02 ScreenSpec只读且计划/动作API未冻结；终态计划控制依原Collector/Scheduler Task+Permission；SYS-06显示内容不自动成为Collector source或许可。撤权/失效/挑战按原Owner恢复且影响面有限，不接触个人Mainland XHS身份。 |
| SH-02 / BMP-03 | SH-02 是既有 Source/Evidence 阅读/检索面；BMP-03 解释 Brand/Market 信号。两者消费既有来源，不另建 Collector。 | 单帖不是趋势/总体；只有已有 metric、时间窗、去重和覆盖分母支持时才形成汇总。引用一个市场线索不等于获得消费者总体需求或 BrandFocus 归属。 |

**1.6 current overrides（supersede上表中过时的“当前”描述）：**

- Facebook `CollectionResult.platform` 合同缺失已在后续 main 修复；不要继续把该旧缺陷当当前阻塞。
- 平台状态已收敛到“配置≠验证≠READY”的更诚实口径，但统一 `PlatformManifest` / `PlatformSession` 仍是批准目标，不能把分散列表继续当最终真相。
- 业务query checkpoint 已能沿当前接口传递；durable server receipt、attempt fencing和platform-native pagination仍是独立未闭合能力。终态视觉按三者分开设计，不恢复旧的“一种checkpoint代表全部进度”。
- `canonical_data` 是唯一当前业务Canonical；旧 `zbc_canonical_data` 不再作为采集双写成功条件。
- CTH-03 已批准 `lumenis.source-target/v1` / Open Original / Return 目标，当前Flutter typed target / launcher / Return仍未绑定；SH-02等来源消费者共用同一SourceTarget语义。
- Universal Platform Acquisition 已批准：六平台只作为当前验收基线，新增平台必须走同一Manifest/Session/Recovery/Source/Evidence/Canonical链，不增加第二平台中心或第二采集器。

CTH-03 当前真实记录 UI 应先完整呈现其已有且受验证的标题、平台 ID/三语名、发布时间、采集时间、来源链接、质量/完整性、scope 和 Evidence 状态。若正文、图像、视频、评论、章节/字幕或平台原生互动不在所选 owner 返回中，显示对应“未取得 / 未验证 / 不适用 / 部分”及可采取动作；不得以 AI 摘要冒充原文、用封面冒充视频已观看或借别帖补图。

`POST /api/experience/cth/platform-collection/search` 当前top-level allowlist仅含 `operator`、`confirm_read_only`、`platform`、`keyword`、`max_results`、`business_requests`、`max_queries`、`continuation`。单平台+关键词与业务批次互斥；`max_queries/continuation`仅属批次模式。目标表单中的独立`时间范围`、`内容深度`、评论/媒体/作者native cursor、`AUTO`频率计划、pause/cancel是已批准终态需求，但不是当前route字段/UI动作；须由原Collector/Scheduler/Task owners冻结真实合同后接入，不能把界面变量当成已发送参数。

### 5.2 CTH-03 两种任务：读已有记录 / 明确发起采集

**模式 A：已采集记录。**打开页面只读取当前真实范围，按稳定 `platform_id`、发布时间/事件时间、采集时间、质量状态和来源类型过滤；这里的时间窗只影响已存记录的读取。搜索清空可返回原列表，不发起Collector。

```text
Desktop / Web — 已有来源与单帖阅读
┌ 来源与观测 · [全部范围/当前任务Focus]              [返回任务] ┐
│ [平台身份ID] [已采集时间] [发布/事件时间] [内容状态]            │
├───────────────┬────────────────────────┬──────────────────────┤
│ 已存记录流     │ 单篇原生Reader          │ Source / Evidence     │
│ 标题/来源ID    │ 图文/视频/长文实际内容  │ 发布/采集时间分开     │
│ 时间/质量状态  │ 派生译文/摘要分开       │ URL/版本/权限状态     │
│ [打开详情]     │ 评论/原生指标按返回显示 │ [回列表] [返回任务]   │
└───────────────┴────────────────────────┴──────────────────────┘
```

**模式 B：新采集请求。**用户显式点“新建采集”，再选平台、当前Scope/可选Focus、查询词、内容请求等级与真实支持的时间范围；每个来源的能力/授权、最大深度、计划方式和回执独立呈现。`关键词搜索`与`粘贴一条来源URL并打开/导入`是两种不同操作：现有 CTH search POST 只接收 platform+keyword 或 business_requests，当前没有独立 `url` 字段/URL resolver，故目标UI不可把URL悄悄塞到keyword；单条URL走现有Importer/Source owner，若没有获准解析途径就显示当前 unavailable，同时保留目标入口/Owner依赖，不发伪请求。

```text
Desktop / Web — 新建采集（从列表中的真实动作进入）
┌ 采集请求  [回到已存记录]                                  [关闭] ┐
│ Scope：全部范围 / 当前任务已选Focus                         │
│ 平台与来源能力：逐平台勾选（显示原生身份及当前真实授权/未验证）  │
│ 查询方式：关键词搜索  [输入……]  时间窗：[发布/事件时间]         │
│ 内容层级：搜索结果 / 详情 / 评论回复 / 作者 / 可用媒体          │
│ [该平台不支持的项明确灰显+原因；不移除已批准目标能力]           │
│ 本次方式：[人工运行] [计划运行：MANUAL默认 / 用户明确opt-in AUTO]│
│ [□本次只读，不会外部写入/发布] [检查本次范围] [提交请求]          │
├─────────────────────────────────────────────────────────────┤
│ 确认摘要：平台/查询/Scope/时间/内容层级/触发方式/将保留的版本     │
└─────────────────────────────────────────────────────────────┘

Mobile：结果列表 → “新建采集” → 全屏条件/授权核对 → 明确确认 →
       每个平台一条状态结果 → 选一条读原帖/回原任务
```

现有当前接线与终态分开：当前CTH-03只读GET且App无POST调用；人工POST已存在但没有已验证的Scheduler计划编辑/通用Start/Stop/cancel UI或platform-native page cursor合同。未接通的最终项仍保留在这张目标表单及下面的差距/验收里；开发中的UI不得谎称提交成功。审批只针对这次只读/调度/平台会话动作，不做通用产品账号/角色权限页。

### 5.2.1 请求计划、批次、AUTO与续接状态

```text
SYS-02 / 来源任务 · 目标排程和结果状态
┌ Filter [平台] [用户/任务范围] [时间] [状态] [查询计划] ┐
│ 计划名称/触发方式/开始结束/到期/下一次 (只显示Owner返回值)│
├───────────────────────────────────────────────────────┤
│ 平台A · 本批完成/部分/需人工/限速/未开始              │
│ 平台B · …                                             │
│ query continuation | 原帖详情/评论/media native cursor│
│ durable task receipt：原任务/终态回执/精确恢复          │
│ 三种连续性分开；失败平台隔离；终态重开不生成新run      │
│ [暂停未来计划] [取消待执行] [检查在途状态] [恢复来源]   │
└───────────────────────────────────────────────────────┘
```

前端将任务区分为：①只读打开已存结果；②一次人工 query；③`business_requests`批次；④明确配置计划/AUTO；⑤帖子/评论/媒体等平台原生分页；⑥服务端 durable task/result receipt。`continuation`只表示查询计划继续位置，native cursor表示平台原生分页，receipt表示原任务身份/终态/恢复语义；三者不得互相冒充。终态receipt再次打开只返回原结果或明确terminal状态，绝不在视觉上变成“又启动一次”。计划/批次来自真实task id和已有cursor/receipt时才画真实排队、暂停、取消、失败/部分接受、可恢复状态；未知接口字段保留在本稿目标合同清单并由原SYS Collector/Scheduler及C1/C6 owner补充，不作为当前请求体字段或新Owner。

AUTO全局产品自有公开基线依当前批准Global合同单独标识；普通用户新建任务默认MANUAL，AUTO前显示平台、Focus/全部范围、purpose、内容深度、频率/到期、通知、停用/撤权方式与将要影响的数据。未明确授权不开始排程，选Focus或打开页面不自动采集。待取消与在途取消分别显示，撤权后停新的请求，已发生/未知的外部执行按同一task id查询回执，不自动二次提交。重新授权只由原task/scheduler owner安全续接；native cursor缺失时说明不能无损续接，保留已收部分及未完成范围，不冒称成功。

### 5.3 六平台验收基线与可扩展原生Reader（不复制平台Feed/Chrome）

| 平台 / 原生内容形态 | 完整正常结果的Reader | 部分/授权/来源不可用时的保留表现 | 当前参考资料的真实边界 |
|---|---|---|---|
| 小红书 / 图文与多图 | 全部真实取得图片的横向序列/当前图号，标题/作者/正文/原生话题，取得的原生指标版本，以及独立评论/回复线程；入口保持官方来源标识 | 实际返回的图片照常可读并列出缺件数/计数依据；原记录`image_count`与绑定图数冲突时只显示冲突，不猜缺图；日期缺年不补年；评论仅部分分页时标样本/未完成 | `NATIVE_DETAIL_BODY_OBSERVED`；参考草图已读14张图片，但`image_count=32`与14个绑定链接冲突 |
| 抖音 / 竖屏视频帖 | 9:16实际视频Viewer、真实时长/播放头；Caption/原文、真实可定位字幕/转写/章节、作者/时间、平台互动、评论回复各自成层 | 媒体不可读时仍可读真实caption/已得metadata并明确“视频未取得/未完整观看”；AI章节或海报不得代替视频、原生字幕或转写；分页/时码缺失不画连续结果 | `NATIVE_CAPTION_OBSERVED; FULL_VIDEO_NOT_WATCHED`；样本全文媒体尚未完整观看 |
| 微信公众号 / 长篇文章 | 原文章题名/来源/实际发布时间、段落目录、全正文与按原顺序真实返回的内嵌图片/链接；Citation锚点可定位段落，已取得互动指标分开 | 原生HTML挑战、文本节选/页尾、附图缺失、日期/计数未知分别显示；读到的文字仍可回来源，不能把截取文本当完整文章或编活动图 | `PUBLIC_TEXT_RECEIVED; NATIVE_HTML_CHALLENGE; PAGE_TAIL_RETAINED`；已有2447字符含页尾，原图、日期、计数未取得 |
| Instagram / Reel 与 Caption | 竖屏Reel实际播放/时码、Caption原文、作者/发布时间、取到的音轨信息、原生指标版本和完整可读评论关系；翻译/AI说明单独标派生 | Caption可读而Reel不可读时保留Caption、预览与播放失败原因；样本评论写明抽取数/总体未知；播放/时长指标未返回即显示未取得 | `NATIVE_CAPTION_OBSERVED; FULL_REEL_NOT_WATCHED`；参考Reel未完整观看 |
| X / 原语言文字与媒体片段 | 原始语言正文优先；翻译/平台翻译可切换且标注来源；每条真实视频片段有独立时长、播放状态、帖子/回复关系和按观测版本记录的互动 | 只得poster时明确“片段未播放”；不得拼贴多个海报冒充播放内容；不同时间指标不覆盖原值，不把平台显示时间改成采集时间 | `ORIGINAL_LANGUAGE_DETAIL_OBSERVED`；参考帖三个短片只读了poster，片段未完整观看 |
| Facebook / 帖子与附件 | owner返回完整授权帖子时，正常Reader展示全文、媒体/附件、作者/时间、原生互动/回复和来源版本，不借其他站点资料补字段 | 只有OpenGraph/meta时明确“仅公开预览”；正文、媒体、时间或互动分别缺失；原站403/撤权显示来源不可读并可回列表，不能永远以预览态当正常全帖布局 | `PUBLIC_META_PREVIEW_ONLY; FULL_POST_UNAVAILABLE`；当前样本正文、媒体、时间、互动均未取得 |

上述完整正常布局是目标状态，允许字段必须来自当次真实Source/Evidence/平台返回；样本表最后一栏是研究观察，不是批准的内容集/商业素材。Reader差异只反映原生内容结构，不给平台或公开网页来源类别排高低；类别基础权重相同，具体Source质量、身份、时间、权益与用途仍按同一标准逐条核验。其它已经批准来源按相同的**原生内容类型**（长文、图集、视频、音频、讨论串、listing）选阅读器，不排除它们，也不复制社交平台Feed模板或新增平台中心。

完整单帖阅读参考位于 六平台单帖字符草图-v3.md（LOCAL_ONLY：`work/c1-w1-20261002/current-purpose-collection-outcome/per-post-character-sketches-v3/六平台单帖字符草图-v3.md`；未随本次归档发布），其索引 SHA256 为 `7ec2fbed1d85b8168170d2517bef274df896bf78aa9388fda0f13af1ff78e3e0`。该材料的六个文件各仅含一帖，`source_scope=UNASSIGNED`、正式 Source/Evidence/Canonical 引用为空、商业使用权 `UNKNOWN`、`TRAIN=NOT_GRANTED`、设计状态为 `DESIGN_EXPLORATION`、前端未实现。它只获准作为内部结构研究参考；本蓝图不复制其中原帖正文/账号信息，不把它们放进官网演示、生产结果或训练集。

### 5.4 页面分工、失败恢复与来源验收

| Screen / owner | 承接动作 | 不承担的动作 / 状态 |
|---|---|---|
| CTH-03 | 用户任务里的显式人工只读检索、来源流、Scope/平台过滤、单帖入口及返回业务链 | 不把打开页面当采集；不把100条上限当全量；不将平台状态当 Evidence；未绑定正文/媒体时不伪造详情 |
| SYS-02 | 目标态显示PlatformManifest投影、PlatformSession、真实计划/手动run、逐来源lane、durable task receipt、query continuation与native cursor，并在真实callable存在时提供pause/cancel/resume/recovery | 当前实现仍可read-only；declared/registered/configured/session-verified/live-verified分开，终态动作不因当前未绑定而从蓝图删除；一个来源失败不阻断其它可用lane |
| SYS-06 | 在授权范围内查看受控来源；当RecoverySheet的当前恢复项需要LOGIN_FORM/VERIFY时提供受控Browser交互并返回Session owner | Browser打开/表单完成不等于Session恢复；必须PlatformSession健康回读后才续原Task；QR与BLOCKED/COOLDOWN不强行进入Browser；隐藏Cookie/token/profile/CDP且不触碰个人Mainland XHS账号 |
| SH-02 | 查看已登记Source/Evidence、原件/文本可用性、引用定位、版本/来源时间；按原生内容类型进入Reader；同一row可用时在LUMENIS Browser内Open Original→Return | 不补造缺失原文、不另建Evidence、不暴露裸URL；外部打开由用户明确选择，不启动采集/登录/Evidence写入，Return恢复原筛选/选中/位置 |
| BMP-03 | 从已有来源做品牌/市场研究，以样本/范围/期间/指标定义解释主题，逐条回 CTH/SH-02 Source | 不发起另一个采集器；单帖不能代表市场或消费者总体；没有可比时间序列不称趋势 |

CTH-03来源检索路径的闭环为：明确任务与 GLOBAL/可选 Focus → 输入来源条件 → 服务端照常校验 Permission → 确认只读并由 CTH Collector 执行 → 真实 Source/Evidence/Canonical 回执 → 在LUMENIS Browser内打开原帖（或由用户明确选择外部打开）→ 可选加入有范围的 BMP/CTH/Research/Brief → 保存、重开、修改与回溯同一 Source。授权失效、限速/挑战、部分接受、拒绝归属、媒体缺失和撤权分别显示原因/已保留内容/可恢复动作；绝不重复外部效果或把“下载到文件”当成正式入库。研究、文稿、视频、播客等独立路径不要求先经过此采集链。

未来验收最少覆盖：GLOBAL 下不选 Subject 仍可完成手动搜索；不自动填太古汇；六平台 stable ID 筛选与显示别名一致；每条记录来源、发布/采集时间与 Evidence 投影可追；平台来源行通过正确 Scope 合同而不绕过现有 projection 校验；结果详情 Back 能恢复过滤/列表位置；限速/授权失败/部分结果/失效会话不清除既有证据；帖子样本不被显示成市场覆盖或消费者总体。方案阶段未执行这些操作或产品验收。

## 6. 44 个既有 Screen ID 的能力覆盖映射（不是固定页数）

**现状共通说明：**当前 App 有 44 个 screen source files 和 44 个路由/屏幕 ID。这里把 44 个历史 Screen ID 当作已批准能力范围的覆盖索引，用来证明没有漏掉一类用户工作；不是承诺产品必须有 44 个固定页面。某项流程适合在 drawer、modal、split view、播放器层或返回态呈现时就留在现有 Screen 下；不能为了凑页数复制画面，也不能借“非固定页面数”删掉真实任务。下面的设计是目标态而非视觉套版。对所有行，“源码入口存在”不代表功能绑定、权限、Evidence、保存/恢复、离线状态、E2E 已验证。准确完成状态要在未来逐屏读当前 Core/ViewModel 并依 Real Delivery Card 操作验证。页面形状和移动重排的逐屏文字草图见[44项能力覆盖文字视觉草图](LUMENIS-44-SCREEN-TEXT-WIREFRAMES-1.5.md)，按ID对应本表。

### 6.1 ACC — 进入、上下文与恢复（4 屏）

| 屏幕 | 完整任务与字段/内容 | 页面形状/优先级 | 操作与转移 | 当前状态/缺口 |
|---|---|---|---|---|
| ACC-01 | 当前不呈现产品账户/登录界面；启动后直接到ACC-03，是否重规划留待闭环后由Product Owner另行决定 | 不绘制账户表单、OAuth按钮、角色选择、找回流程或占位入口 | LaunchSurface→开放工作区；真实底层能力异常时在原位置就地恢复 | 旧 Screen Spec 的 `DESIGN_READY` 仅作为既有规范状态；当前用户方向明确暂缓账户UI，不作为当前设计/实现 |
| ACC-02 | 可选选择现有 Subject 与 BMP BrandFocus，显示合法对象来源/名称 | 搜索→对象列表→一个对象关系细节；Default GLOBAL 保持第一选择 | 选取后确认焦点；取消/清空回 GLOBAL；跨域不改身份 | 源码存在；主体选择不得变成入口限制 |
| ACC-03 | 真实待处理任务、待确认动作、重要变化、上次工作（需真有记录）、任务起点 | 上方任务入口；中段是有意义的工作路径/真实任务条；不做四个大卡和侧边状态栏 | 开始 AI-01、打开任务，或进入 CTH/BMP 业务、Shared 研究/直接创作；返回保留当前真实任务 | 源码存在但现有首屏内容和 CTH-01 默认与目标冲突，需重组 |
| ACC-04 | 某项任务/读取失败时说明对象、影响和真实恢复动作 | 原任务中的局部恢复提示；不跳转到登录/通用权限页面 | 仅在owner许可时重试；否则返回/改用现有可用路径；恢复后回原任务 | 服务端真实拒绝仍不可伪造通过；产品账户与通用权限配置UI暂缓 |

### 6.2 CTH — 商业运营（10 屏）

| 屏幕 | 完整任务与字段/内容 | 页面形状/优先级 | 操作与转移 | 当前状态/缺口 |
|---|---|---|---|---|
| CTH-01 | 全局或特定商主体视角下发现、判断、Case/Action及报告 | 时间信号带 + 当前事件/证据 + 待办/决策 | 时间 Scrub→事件→Evidence/Case/Action→Trace/Return | 源码存在；Global 口径和实际运营 Outcome 待验 |
| CTH-02 | 查找/新增CTH商业主体company；核实企业→主体→门店/品牌/业态的来源关系 | 目录/关系分面 + 业务主体新增表单；只录入现有POST支持的双语名/industry/keywords；关系字段另用EntityRelation owner | [查找登记] [新增经营主体]→双语名/类型校验→精确重复/创建回执→补已证关系→用户另选采集 | 现ScreenSpec是只读目录，新增由全域J1/U01批准但UI与关系写合同未绑定；ADD主体不自动选Focus/采集，关系未验不展示成事实 |
| CTH-03 | 在GLOBAL/当前精确 Focus 中搜索并审阅有 Scope/Evidence 的采集结果 | 宽屏为平台/时间/关键词 + 来源流 + 原生单帖 Reader + lineage；窄屏列表↔全屏 Reader | 显式确认只读→走既有人工 search POST→按真返回状态打开原帖→回同一筛选/位置；稳定 `platform_id` 做过滤键 | `BLOCKED / BACKEND-GAP-009`；接口存在但 Flutter 当前只调用 Screen GET、没调用搜索 POST；最多100条且只报告 partial；source/captured/Evidence 字段未到 UI；Dart模型未独立保留 platform_id；固定太古汇关键词须清除 |
| CTH-04 | 查看事件、Case、来源之间的链接和时间顺序 | 时间轴+事件连线，节点有状态文字与引用计数 | 选节点显示来源和判定；跳 Case后回到节点/缩放 | 源码存在；规则关联不等于因果 |
| CTH-05 | 查看日/时段的反馈/情绪变化并定位真实事件 | 月/周热区与日期列表，而非色块墙；无样本日期为空而不是 0 | 日期选择→相关事件/原文；可切表格 | 源码存在；指标分母、窗口需真实口径 |
| CTH-06 | 阅读原始差评/反馈并确认问题类型/状态 | Source first 读者 + 原文/媒体 + 事件处理轨 | 人工判定/链接 Case/标记需核查；原文保存 | 源码存在；不能混合客户反馈、公开舆情、已确认事故 |
| CTH-07 | 对某指标、时期和样本做可复核的趋势解释 | 一个主图+指标口径层+分解视图/原始数据表 | 选期间/对比项→看定义/证据→创建问题或导报告 | 源码存在；不兼容指标阻止比较；Unknown 不填 0 |
| CTH-08 | 推进事件/问题Case并将已审结论沉淀为派生Knowledge | Case时间/来源/事实与推断/责任与due/下一步分轨；Knowedge候选有独立父Case与Review状态 | 加来源→核实事实→负责人/状态转换→审Case→提交知识候选；失败时保留原Case | 当前Case行为/Evidence绑定需核验；知识candidate不得自动Promotion；详见§7.14 |
| CTH-09 | 评估风险/处置方案，形成审批过的决策与结果闭环 | 影响对象/时间窗/来源/不确定性/责任人；方案差异与实际Permission/Effect回执 | 保存决策草稿→用户选具体外部动作→请求approval→看允许/拒绝/未知回执→记录Outcome/回Case | Effect不得由前端伪造或超时重放；审批/结果数据需真实owner返回；详见§7.14 |
| CTH-10 | 把研究期/事件做成报告或周报 | 章节结构+现场预览+逐点引用和口径 | 选已确认指标/期间→预览→导出→从成果中心重开 | 源码存在；不得用来源数假装报告已覆盖市场 |

### 6.3 BMP — 品牌/市场（11 屏）

| 屏幕 | 完整任务与字段/内容 | 页面形状/优先级 | 操作与转移 | 当前状态/缺口 |
|---|---|---|---|---|
| BMP-01 | 以品牌为焦点理解品牌/受众/竞品/内容和市场关系 | Brand relation field；主品牌居中但指标和证据在各边可回溯 | 点击关系→研究/内容/创作者/传播详情→回品牌 | 源码存在；品牌焦点非全球默认 |
| BMP-02 | 查找/新增BMP BrandFocus品牌身份并理解自有/子品牌/竞品关系 | BrandFocus为独立身份；[新增品牌主体]复用Canonical registry的BMP brand路径；关系与竞品比较仍各有Owner | 双语身份/industry/keywords登记→精确重复回已有项→Evidence-backed关系另行核验→回组合/当前任务 | 现BMP-02规范当前只读且未授权写品牌/竞品；Global J1/U01要求Add BrandFocus目标路径保留；注册写有高风险CONFIG_MODIFY人工审批，当前UI/关系写/read contract需补 |
| BMP-03 | 对真实来源做细分市场研究，把单篇作为有边界样本 | 主题地形/类别轴+选中信号 dossier，单帖返回 SH-02 原生 Reader | 筛选市场/时间/平台→核实范围和样本→开原帖/lineage→标线索待评估 | `BLOCKED / BACKEND-GAP-020`；不可将单篇或截断前100条包装为趋势、总体需求或品牌热度 |
| BMP-04 | 解释平台、素材、传播节点和互动指标关系 | 来源/内容 → 渠道 → 观察到的结果的流程河流 | 选择节点、查看口径/时间窗/来源；回上游节点 | 源码存在；不支持的曝光或转化不出现 |
| BMP-05 | 基于真实Creator身份/作品/受众样本比较品牌适配、真实性与风险 | 可筛选候选线+单Creator作品dossier+来源/互动口径/权利/风险；不强造fit分 | 选择某作品/证据→解释为何匹配/不匹配→带入已有Campaign草案→回研究 | 当前Creator身份/作品/推荐接口依赖需核验；无样本/分母/授权不编造；详见§7.14 |
| BMP-06 | 拟稿、审阅和版本管理内容，并承接独立可编辑提案 | Brief、策略、提案版本/引用/预算约束与审阅位置；§7.11两方案对照 | 编辑→比较差异→确认受影响下游→送审/导出/重开；不触发付款/发布 | Screen source存在；proposal editor/资源合同/现实报价和权限仍需Owner绑定 |
| BMP-07 | Campaign计划、资源、进度和Outcome；预算/资源变化会实际改变可行执行方案 | 目标/受众/渠道/里程碑/真实结果 + 同一Brief约束情境A/B的策略、交付、人员和日程变化 | 编辑所选方案→核对口径与硬上限→保存新版本→审阅实际结果 | Screen source存在；未提供价格/资源显示未知，不把计划里程碑算完成或发起采购 |
| BMP-08 | 播客脚本、已有音频文件理解/编辑/真实播放、混音与版本交付 | 章节脚本与同步时间码在上/侧；多音轨波形在中；Mixer Inspector 针对选中轨 | 导入文件→编辑文字或声音（分开记录）→回听→导出/重开；AI只给可编辑建议 | 源码存在；文件编辑/渲染/真实播放闭环待 E2E；实时麦克风录制后置 |
| BMP-09 | 以同口径看品牌表现变化、证据充分程度 | 品牌维度矩阵+时间趋势小倍数+覆盖/来源说明 | 选维度看定义/证据→对齐期间→报告 | 源码存在；不可比较时置 unknown/unavailable |
| BMP-10 | 品牌事件/风险与响应工作 | 按来源与传播顺序排列的 incident lane，展示实际响应人 | 复核事件→起草回应→审批→观察实际结果→再评估 | 源码存在；未有实际外部效果时保留未执行状态 |
| BMP-11 | 对标品牌、品类/时期差异与证据 | 可比字段的多列画布；不兼容值分开，不缩成奖牌榜 | 配比较集/期段→看口径/来源→导出可信差异 | 源码存在；归一化算法与字段不在 UI 里猜 |

### 6.4 AI / Agent（5 屏）

| 屏幕 | 完整任务与字段/内容 | 页面形状/优先级 | 操作与转移 | 当前状态/缺口 |
|---|---|---|---|---|
| AI-01 | 编辑任务，查看上下文、允许材料和当前可用能力 | 单一任务编辑区为主；Evidence/能力放在可关闭的详情层 | 保存草稿/选材/开始；运行不可用时保留草稿和真实原因 | Screen spec `BLOCKED / BACKEND-GAP-029/-030`；屏幕路由/Permission 有 source 依据，但 Evidence Trace/scope 与真实任务结果未完整验收 |
| AI-02 | 审查真实任务分步执行、取消/重试和 Artifact | 阶段层与输入/结果文件横向关联，执行/等待/失败各自标注 | 每步打开产物/来源，取消或安全重试，审批节点需要用户操作 | 源码存在；不能仅凭阶段动画声称任务成功 |
| AI-03 | 逐条核对分析结论、来源与不确定性 | 结论流由引用脚注连到来源，未核实项保持独立标志 | 点引用原文、请求修订、加入已有 Case/报告 | 源码存在；模型内容不替代 Production Truth |
| AI-04 | 在当前任务中查找真正已验证/许可的Skills并理解用途 | source/owner/version/license/trust/input/output/risk/permission/evaluation一屏详情与update diff | 仅在目标生命周期动作已由Owner绑定时启用/运行/更新；否则只读显示现状/缺口；结果回原Task | 当前 ScreenSpec是BLOCKED read-only catalog；完整Enable/Update/Disable/Uninstall是C2 existing Skills owner依赖，不另造marketplace/runtime；见§7.14 |
| AI-05 | 查看当前AI服务是否可用、为什么不可用、是否能重试或继续手动流程 | Available/Not ready/Unavailable/Unknown、最近检查与安全调用观测；错误不藏进聊天 | 查看诊断→重试或返回AI任务；不提供provider/model选择 | 源码存在；当前未绑定时显示AI-01 diagnostic fallback；raw provider/model名称不进入产品UI |

### 6.5 SYSTEM（8 屏）

| 屏幕 | 完整任务与字段/内容 | 页面形状/优先级 | 操作与转移 | 当前状态/缺口 |
|---|---|---|---|---|
| SYS-01 | 查应用、API、数据库、依赖和适配器实时状态 | 有向拓扑+更新时间+当前失败层；不是业务 KPI | 点依赖看 trace/错误→授权恢复→原任务返回 | 源码存在；具体现场健康需运行 |
| SYS-02 | 终态：查看来源能力、PlatformSession、现有计划/新增获准计划、真实Task结果及精确可恢复位置 | Plans / Runs / Sources三块互相联动：Scope/模式/时间/来源深度；逐平台lane；declared→live-verified能力层级；query/native/receipt进度分开 | manual start / 用户opt-in plan / pause future / cancel pending / RecoverySheet / resume same Task；运行回执定位Source/Evidence | revision 2已承接最终目标；当前实现仍是read-only，Manifest/Session/receipt/动作绑定与runtime E2E待C1/C6完成 |
| SYS-03 | 看 Schema、数据库健康、证据/Canonical链 | DB层级与字段 lineage/Integrity error列关系 | 检查错误、导出审计/按owner恢复，不直接改业务 truth | 源码存在；本轮不读生产 DB |
| SYS-04 | 当前不提供产品角色/账户/通用权限配置页；仅呈现已有动作本身的审批/回执 | 不绘制全局角色矩阵；审批细节留在发起动作的业务页面，系统审计仅保留当前真实只读回执 | 用户在业务页确认具体动作；服务端Permission决定允许/拒绝，SYS-04界面不能授予权限 | 通用账号/权限UI按用户指令待整体产品闭环后再决定；Effect Fence继续有效 |
| SYS-05 | 外观、壁纸、主题、对比、字体与动效偏好 | 即时预览；壁纸控制在当前工作旁的抽屉/面板，内容按设备重排 | 预览→仅在当前设备应用/取消→回原任务；无服务端/跨设备壁纸同步 | Screen spec `DESIGN_READY`；两张用户照片已捆绑。局部 Web 选择/重载/移除及纯黑/字号检查有 PASS；两张原图全端/极端裁切验收和原生材质实绘仍未完成 |
| SYS-06 | 在当前任务的已授权边界中访问受控网页；当RecoverySheet当前项需要LOGIN_FORM/VERIFY时提供Browser交互 | 来源/允许域/浏览器状态/当前恢复项并置；Cookie/token/profile/CDP等敏感信息永不显示 | 普通受控阅读→Return；RecoverySheet→受控登录/验证→交回PlatformSession健康复核→恢复原Task | revision 4明确它不是Session owner/平台账号中心；`IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED / BACKEND-GAP-041`，浏览器online/表单完成都不等于Session或Evidence成功 |
| SYS-07 | 看同一候选发布链的source/config、Product Gate、App Gate、Critical E2E、package/runtime、rollback、PO repeat、RELEASED/OPERATING证据 | 以SHA绑定的纵向证据链为主，不用一组绿灯卡片；不同SHA证据并排标明不合并 | 打开精确证据/回对应Owner；本屏不自己执行Gate或宣告release | revision 2已批准最终release-evidence目标；当前builder仍只返回有限checks/skill light，完整C6/M release contract和real-user E2E待绑定 |
| SYS-08 | 查任务 trace、请求、失败日志及影响 | 真实 Trace waterfall 与 Error Inspector；有频率筛选 | 由任务跳 Trace，返回同一 task/result | 源码存在；事件关联需同一 trace id |

### 6.6 Shared（6 屏）

| 屏幕 | 完整任务与字段/内容 | 页面形状/优先级 | 操作与转移 | 当前状态/缺口 |
|---|---|---|---|---|
| SH-01 | 当前安全能力目录；完整目标为Discover、Source→Brief→Artifact、可规划叙事的ShotPlan/逐镜审阅与专业视频编辑 | 同屏在Discover/当前创建活动间切换；视频活动包含媒体Source、ShotPlan(适用时)、完整Viewer/Inspector/Timeline、字幕与音轨、版本/导出/重开 | 选择真实来源→选片段/剧本段→按需做线稿/彩稿并逐镜确认→进入Timeline→导出/试听/重开/恢复 | `IMPLEMENTED_CATALOG_ONLY_EVIDENCE_SCOPE_BLOCKED`；Discover callable/Evidencescope、storyboard draw/confirm bindings及完整Timeline媒体E2E各自未验；不将未绑定能力删出终态 |
| SH-02 | 搜索并阅读已有Source/Evidence及lineage；对same-row已验证来源提供SourceTarget→Open Original→Return | 平台/内容类型原生Reader；原文、译文、媒体、评论、指标版本、SourceTarget状态和来源链各自分层，仅按实际返回开放 | 搜→Reader/Trace→Open Original（可用时）→Return恢复Space/List/query/filter/item/focus→按权利/权限带入Research或回CTH/BMP | revision 3已批准SourceTarget终态；当前scope/Evidence envelope、typed target/launcher/Return仍未绑定；六样本仅作内部布局参考、未正式登记 |
| SH-03 | 检查 Canonical字段/Metric定义和取值来源 | Schema tree → field/metric inspector → records table | 追到 Source/Event/Evidence/Calculation→原始任务返回 | 源码存在；不开放直接编辑 Canonical truth |
| SH-04 | 管理真实报告、视频/音频和Artifact输出版本 | 文件类型/来源/版本列表+对应真实预览 | 预览/比较/下载/重开/导出新的版本 | 源码存在；每种格式对应的真实服务待验证 |
| SH-05 | 复核Outcome/Evaluation与版本化Learning候选 | Parent/Scope/Evidence/评价口径/样本/反例及candidate差异；promotion与rollback史分别呈现 | 逐项查看来源→请求现有审批/测试→仅回Owner真实promotion/rollback状态 | 当前面板read-only且全局Envelope未绑定；不自动Promotion/重写Evidence；详见§7.14 |
| SH-06 | 定位需处理任务/通知/告警并继续原流程 | Task/Notification/Alert分lane，来源/范围/创建/截止/状态在同条展示 | 点击回原Task/Case/Artifact；审批在原行动页完成；仅运行中Owner支持的通知动作可用 | 当前inbox只读、origin/scope必须verified；不在通知卡片模拟approve/snooze/retry或假计数；详见§7.14 |

---

### 6.7 已批准需求追溯：R01–R15 / J1–J8 / U01–U25

本表只作审核导航。R/J/U完整定义和当前唯一Owner以[Source Owner Index](../../../LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)及[Real Delivery Overlay](../../../LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md)为准；覆盖映射不代表测试通过或能力已验收。

#### R01–R15：保留接受/依赖覆盖

| ID | 当前Owner（Source Owner Index） | 本方案查看位置 |
|---|---|---|
| R01 | M / W6 | §§0、10、12：产品真相、验收、同版本发布 |
| R02 | M / W6 | §§1、4、10：完整业务工作与多端验收 |
| R03 | C1 / C6 | §§4.1(I/K)、5、6.2/6.5：主体、来源、采集 |
| R04 | C1 / C2 / C5 / C6 | §§2、4.1(B/E/I)、5、6.4/6.6：材料/AI/Evidence |
| R05 | C1 / C2 / C6 | §§4.1(E/I/K)、5、6.4/6.5：采集进入真实任务 |
| R06 | C1 / C6 / F | §§2.2、5.3、6.2/6.5/6.6、7.10：来源阅读和单帖 |
| R07 | C2 / C4 / C5 | §§4.1(E/F/G/L)、5.4、8：AI与可交付成果 |
| R08 | C6 / F | §§1.1、4.2、7、10：四端职责/操作验收 |
| R09 | C1 / C2 / C3 / C5 / C6 / F | §§4.1(B–E)、5、6.2–6.6：研究进入业务和创作 |
| R10 | C1 / C3 | §§4.1(C/K)、5、6.2：CTH业务路径 |
| R11 | C2 / C3 / C4 / C5 | §§4.1(D/F/G/L)、8：品牌内容与创作 |
| R12 | C1 / C2 / C3 | §§4.1(B/C/I/K)、5：来源和业务接续 |
| R13 | C2 / C3 / C4 / C5 | §§4.1(D/E/F/G/L)、8：AI和不同成果交付 |
| R14 | C1 / C2 / C5 / C6 / F | §§2、4.1、5、6.4/6.5/6.6：研究材料、共享成果与界面 |
| R15 | C6 / M / Product Owner | §§10、12：真实发布、用户验收和运行证据分开 |

#### J1–J8：用户工作包

| ID | 必须完成的工作 | 本方案入口与目标结果 |
|---|---|---|
| J1 | 建立、选择并持续维护真实数据宇宙 | Flow I/K；ACC-02、CTH-02/03、SYS-02/06、SH-02；全球覆盖和Focus/Clear均由来源/数据状态证明 |
| J2 | 完成商业主体运营决策 | Flow C；CTH-01–10、SH-02/03/04；真实Evidence→Case/Decision→授权Action→Outcome/Evaluation |
| J3 | 完成品牌市场、内容与Campaign决策 | Flow D；BMP-01–11、SH-01/02/04；市场来源→可编辑Brief/Campaign→实际结果/评估 |
| J4 | 产出并修订原创专业提案 | Flow L、§7.11；BMP-06/07、AI-01/02、SH-04；真实Brief/约束→同一Brief两组预算资源约束下有实质差异的可编辑方案→审阅/导出/重开 |
| J5 | 产出并修订可编辑视频 | Flow F；SH-01/04；真实素材→时间线→可播放渲染→工程重开/修订/取消/恢复 |
| J6 | 产出并修订可用播客 | Flow G；BMP-08、SH-01/04；研究/脚本/音频→编辑/试听→导出/重开/评价 |
| J7 | 将材料与目标转为可复用知识和有用自有AI工作 | Flow B/E/J；SH-01–06、AI-01–05及真实CTH/BMP消费者；保存/检索/评价不替代训练许可 |
| J8 | 在批准的四端间接续、恢复并发布 | Flow A/H/I；Website、ACC-03/04、SH-04/06、SYS-01–08；一套Core与同版本真实验收 |

#### U01–U25：既有产品能力主张

| ID | 能力主张 | 前端入口/关键控件（连接到现有Screen） | 成功回执、错误状态与Return |
|---|---|---|---|
| U01 | GLOBAL宇宙、国家类别、实体持续新增 | 全部范围搜索；CTH-02 `[新增经营主体]` / BMP-02 `[新增品牌身份]` | created/duplicate/permission denied分别呈现；新增不自动Focus/采集，覆盖度仍由真实全域审计证明 |
| U02 | 精确身份、别名与场内/租户关系 | 输入双语名称/行业/keywords→检查精确重复→打开已有/创建不同；关系详情按Evidence日期定位 | 精确重复回原记录；疑似冲突不自动合并；关系Writer不可用时状态待核实，不伪建边 |
| U03 | 总部/发源/法域/运营/营销/所在地关系 | 选关系语义→查看Subject/BrandFocus、国家/市场、Source/Evidence与有效期；只由EntityRelation owner负责写 | 每个关系独立显示已验证/待审/撤回/未知；无关系Source则保留未关联并回原实体 |
| U04 | 经批准的平台采集与原生观察 | CTH-03 `[已存记录] / [新建采集]`; 按stable platform ID选平台/来源类型/授权范围；SH-02开原文 | 搜索回执按平台/字段分别接收/拒绝/重复/部分；Source/Evidence缺失仍标未接收；失败回同一Task |
| U05 | 历史指标、新鲜度与增量维护 | CTH-03区分发布/事件时间和采集时间；SYS-02打开真实计划、上次attempt/success/next due | `STALE/NOT_COLLECTED/NO_NEW_DATA/UNKNOWN`分开；断点只有真实cursor/task id才恢复，不重复页/不写假零 |
| U06 | 商业监测、事件与日历 | CTH-01/03 filter scope+time→CTH-04 event lane→CTH-05 calendar day | 真实日期/事件/Source定位，空样本、未采集、partial分开；Back保留日期/缩放/selection |
| U07 | 消费者/媒体/情绪/趋势 | CTH-05/06/07、BMP-03/04、SH-01/02选观察窗/样本/原帖/指标口径 | 单帖/样本/总体与因果分离；分母/coverage不可用时显示原因，不生成热度/总体需求 |
| U08 | CTH/BMP 风险识别与响应 | CTH-09/BMP-10选择风险→Evidence依据→草拟响应→明确同意具体外部动作 | Pending/approved/denied/effect unknown/complete按Server回执；拒绝不执行，回Case/Origin |
| U09 | 运营Case、决策、行动与Outcome | CTH-08打开Case→责任/时间/证据→审决策→批准Action→CTH-10/SH-05看Outcome | 每步保留owner、原文和状态；proposal不算action，action不算outcome；失败返回同一Case |
| U10 | 品牌组合、市场及竞品情报 | BMP-01/02选可核BrandFocus与竞品→BMP-03比市场窗→BMP-11选兼容benchmark | 每项比较显示身份/市场/期间/单位/分母；不兼容时取消比较并可回对象 |
| U11 | 创作者、渠道与传播情报 | BMP-05打开具体Creator/作品→证据/受众匹配/权利状态→选入BMP-07 | 没有作品/观众或来源不显示fit分；取样数和互动版本有边界；授权未知不送Campaign |
| U12 | 品牌内容/Campaign生命周期和评价 | BMP-06编辑Brief内容→BMP-07方案/里程碑→批准→执行回执→BMP-09/10复盘 | 草稿/审阅/批准/计划/已发布/实测Outcome分态；版本保留、Effect拒绝返回草稿 |
| U13 | 原创提案 | BMP-06/07或AI-01入口→真实Brief→§7.11同Brief预算A/B方案比较/编辑 | 给出资源差异/硬上限/Unknown；过高/不可行有修改路径；保存新版本并返回原Brief |
| U14 | 视频创作 | SH-01 `[ShotPlan]`（仅适用叙事）→逐镜确认→Viewer/Inspector/多轨Timeline→导出/重开 | 镜头确认绑定版本；素材缺失/草稿变更/渲染失败保留可恢复工程，只有真实可播放文件才是成片 |
| U15 | 播客创作 | BMP-08章节脚本/Source→真实音频导入→多轨Mixer/效果/试听→导出/重开 | 文本与声音分版；每轨状态真实；实时麦克风独立后置；失败保留原音轨与工程 |
| U16 | 材料导入、搜索、精确引用 | SH-01 `[选择材料]`→文件详情/Scope/use→具名confirmation→同bytes retry→inspect；SH-02定位 | approval required/ready_for_retry/partial/unsupported/offline真实返回；取消保留旧项目；页段/帧/时码Citation可返回 |
| U17 | 研究、报告、版本Artifact与导出 | CTH-10/SH-04/AI-02选择范围与引用→编辑→保存版本→预览/导出/重开 | 导出/下载与存档分开；保存回执未知先查同Artifact ID；原件不覆盖，来源撤回标依赖复核 |
| U18 | 序境自有模型/推理/多模态理解 | AI-01提交Task→AI-02查看steps→AI-03核证引用→BMP-08/SH-01接创作 | 未接通时保留草稿并说明analysis unavailable；真实模型输出可编辑、引用/uncertainty可查、失败不换退役Provider |
| U19 | Agent、Skills、工具发现与Memory | AI-04读已验证能力详情；AI-01查看本Task实际使用的Memory/context版本；SH-06回运行结果 | 当前AI-04 read-only时不模拟启用/更新；无Memory回执不写“已使用”；选择排除仅针对当前Task并返回来源 |
| U20 | Evaluation、反馈与受控学习 | SH-05打开具体Outcome/candidate→比较source/model/metric/version→原Owner review | Candidate/validated/rejected/promoted/rollback分别标记；无实测样本时不可评分/晋升，不改Source/Canonical |
| U21 | 产品浏览器与采集接续 | SYS-06当前Task内打开受控Source；SYS-02查看同一Task运行；从CTH-03/SH-02回原页 | Session expired/challenge/denied/partial分别呈现；不能碰个人浏览器或Cookies；仅原Task Owner能续接cursor |
| U22 | 开放入口、Scope、服务端Permission与Effect | ACC-03默认全部范围、可选Focus/Clear；每个外部动作在Origin出现范围/内容确认 | 无账号墙；focus不授权；拒绝/撤权/未知保持原状态、无外部effect并回原任务 |
| U23 | 四端Experience与工作连续性 | 同一Task/Artifact在Web/Desktop/Mobile打开；Website仅解释并进入；窗口按尺寸重排 | 任务/过滤/播放头/Focus按已有scope恢复；不可用平台端状态单列，不把快捷方式当新产品Surface |
| U24 | 设置、共享偏好与通知 | SYS-05调本机外观/可逆预览；SH-06分lane读真实任务通知并打开Origin | Wallpaper本机保留；Snooze/Approve等无owner handler不在Inbox模拟；不发假未读数 |
| U25 | Runtime、安全、打包、发布与持续运行 | SYS-01/02/03/04/06/07/08读真实component、DB、Permission、Browser、Release/Trace状态 | Build/test/live/PO repeat/released/operating依证据分态；故障限影响路径，保留数据/Task并实际Rollback |

#### U01–U25：关键控件与每项回执/恢复

| ID | 关键前端控件/输入 | 结果与必须保留的状态/Return |
|---|---|---|
| U01 | `[全部范围搜索] [新增Subject] [新增BrandFocus]` | 已登记/新建/精确重复/审批拒绝分别呈现；新增后不自动选择或采集；返回原目录 |
| U02 | `[检查重名] [打开已有] [创建不同]` | exact duplicate回现有ID；相似项需逐项证据比较；不自动alias/merge |
| U03 | `[关系类型] [来源Evidence] [有效期]` | 每条关系有ISO/tenant/role/source/time/review状态；缺source或writer留待核，返回当前实体 |
| U04 | `[已存记录] / [人工搜索] / [计划任务]` | 每平台显示fetched/accepted/partial/denied/duplicate；失败平台不清成功平台结果 |
| U05 | `[发布/事件时间] [采集时间] [仅刷新到期]` | 显示上次真实尝试/成功/新鲜度；未知不是0，fail/checkpoint丢失不冒充续采成功 |
| U06 | `[时间轴事件] [日历日期]` | 选中事件/日返回实际Source/Case；无数据/未采集/零样本分开，Back保留时间位置 |
| U07 | `[打开样本] [查看分母/期间]` | 显示源贴及样本范围；缺分母不画趋势/总体满意度，不可比时退出比较 |
| U08 | `[查看风险依据] [起草回应] [请求此Action审批]` | 事实/推断分列；审批/Effect拒绝无副作用，超时未知不重复提交 |
| U09 | `[更新Case] [记录决定] [打开Outcome]` | case status/owner/due和Action/Outcome分开；保存失败留旧值并回来源 |
| U10 | `[选可比品牌/期间/指标]` | compatible unit/period/denominator显示对照；不兼容保持分列/unknown，可回组合 |
| U11 | `[Creator作品] [加入Campaign草稿]` | 显示作品/实际表现/权利依据；无真实合约、受众或费用时为unknown，不发外部联系 |
| U12 | `[编辑Brief/内容] [送审] [查看已发布回执]` | Draft/Review/Approved/Scheduled/Published/Measured分态；拒绝返回可编辑版本 |
| U13 | `[比较方案A/B] [检查硬上限] [采用所选]` | 资源实际改变方案；估价未知/超cap/不可行显原因；采用生成新版本，不触发支付 |
| U14 | `[ShotPlan] [逐镜确认] [编辑Timeline] [导出]` | 确认绑定具体版本；文本变化仅使相关shot重审；媒体/导出失败保留工程与旧成片 |
| U15 | `[导入音频] [改脚本/改声音] [试听]` | Script与Sound各自版本；缺音轨/不能试听不伪装完成，Back回原时间段 |
| U16 | `[选文件] [确认用途/范围] [inspect]` | approval-required/ready_for_retry/partial/invalid分别呈现；同bytes安全重试，cancel保留旧项目 |
| U17 | `[保存版本] [导出] [重开]` | Artifact ID和父版本可回查；timeout先查回执；Source撤回标记影响，不覆盖原件 |
| U18 | `[开始分析] [查看步骤] [核对引用]` | 真实Gateway结果/权限拒绝/待审批/Evidence未确认分态；timeout按同Execution查询 |
| U19 | `[查看Skill详情/使用] [查看本次Memory]` | 仅展示真实Owner返回的version/license/context；当前只读目录不模拟install/disable；无Memory则明确未用 |
| U20 | `[检查评估依据] [比较candidate] [请求review]` | source/sample/method/held-out and approval state visible；promotion/rollback需Owner返回 |
| U21 | `[开受控来源] [回采集Task]` | 来源浏览和平台授权分别显示；session失效/挑战保留已得证据，不动个人浏览器 |
| U22 | `[全部范围] [可选Focus] [清除] [确认外部Action]` | Scope切换不改保存对象；auth denied没有效果；无账号墙，返回原Task |
| U23 | `[在Web/Desktop/Mobile继续]` | 回同一Task/Artifact/selection；缺本地media提示选择现有Relink路径，不能声称自动同步 |
| U24 | `[预览] [本机应用] [打开通知来源]` | 偏好明确本机保存；Inbox按owner只读/操作状态返回，不造未读数或外部审批 |
| U25 | `[查运行状态] [打开trace] [恢复原Task]` | health与可执行动作分列；故障范围、真实回滚与同SHA发布状态如实标示 |

上述ID都保留完整范围，并把用户可见主动作绑定到结果与恢复；Owner合同、依赖状态和真实验收仍由当前Source Owner Index/Overlay决定，不能由本方案升为PASS。R/J/U不是前端页面标签，也不产生第二套研发队列。

## 7. 关键页面的目标视觉线框

本节线框直接实例化上表。下面的数字/名称若出现，仅表示字段类型或按钮文案，不假设任何实际观测数据。

### 7.1 产品主页与实际待办

~~~text
Desktop / 16:9

┌ 序境  ○                          搜索     主题/外观     语言 ┐
│                                                                  │
│ 今天要继续的工作                                                  │
│   [有真实任务时] 真实任务名 · 当前阶段 · 最近保存时间             │
│   [继续工作] [查看变化]                                            │
│                                                                  │
│ 开始一项任务                                                      │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ 写下目标，或打开一份已有材料……                               │  │
│ │ [添加现有材料] [范围：全部 ▾]             [进入任务编辑 →] │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ 工作入口       商业现场 →     市场与品牌 →     研究素材 →         │
│                内容创作 →     报告与成果 →                           │
│                                                                  │
│ [待确认的真实动作/有影响变化：若无即不占位]                        │
└──────────────────────────────────────────────────────────────────┘
~~~

主页信息顺序是：真正要接续的事情→开始任务→工作入口→待确认动作/变化。没有当前任务就直接给任务入口；不显示“0 个任务”或假内容。若实际 task 当前 Focus 是广州太古汇，入口用精简标签显示它；无 Focus 时是全局，不显示选择障碍。

### 7.2 Web Workspace——阅读与任务接续

~~~text
宽屏工作区

┌ 序境 · 资料阅读 / 某来源标题             [返回来源] [任务菜单 ⋯] ┐
│ 主题：仅当前任务已有时显示   范围：GLOBAL/ALL或精确Focus   时间：已知时显示 │
├───────────────┬─────────────────────────┬──────────────────────┤
│ 资料列表       │ 原文/媒体阅读区           │ 来源与引用             │
│ 原生标题       │ 按单篇内容类型自适应       │ stable platform_id     │
│ 小型来源标记   │ 原文/媒体状态与原始比例    │ 发布/采集时间分列       │
│ 真实品牌缩写*  │ 轮播/视频/长文各自布局     │ Source/Evidence lineage|
│ 未知/部分状态  │ 原生评论/互动仅在实际返回  │ 指标口径/缺失字段      │
│               │                            │ [引入研究]             │
└───────────────┴─────────────────────────┴──────────────────────┘
~~~

`*` 只有身份经过现有 Owner 核实才显示品牌缩写。选条目后，右侧联动，不滚动到底找正文；来源原生内容与派生摘要/翻译分开。窄 Web 窗口采用来源列表→单条 reader→右侧细节抽屉的层级跳转；顶部 Back 让位置回来并保留来源 ID、过滤与阅读位置。

### 7.3 商业事件层级弹出

~~~text
CTH-04 事件线

主线： 09:00 ●──────● 10:20 ──────○ 12:00
             │        │
             │        └─ [规则关联/待核实] Event B
             └─ [已证实来源] Event A ─ Case-123

点击 Event A
┌ 当前事件 / 10:20 / 来源数（只计真实来源） ───────────┐
│ 事实：原始来源陈述……                                 │
│ 推断：规则提示需核实，不能写作因果                    │
│ Evidence [原帖] [图片] [采集元信息]                  │
│ [打开来源] [加入已有 Case] [返回时间轴]              │
└──────────────────────────────────────────────────────┘
~~~

### 7.4 BMP-03 市场主题证据侧层

~~~text
BMP-03 市场情报

┌ 主题集合/市场范围 ┐┌ 主题地形（趋势/样本/口径）┐
│ 品类/词项/时间   ││ 真实观察主题─────────●     │
│ 平台（若有数据） ││ 其他主题─────────●         │
│ [筛选]           │└───────────────────────────┘
└──────────────────┘
选中主题：
┌ “主题标题/时间窗” | 当前来源量及完整度说明 |
│ 原文来源列表/趋势材料/缺失来源说明          │
│ 单篇详情显示平台形态/发布时间/采集时间/来源   │
│ “机会假设”只能标作待复核，不是市场事实       │
│ [查看来源] [带到已有 Brief] [返回图面]        │
└─────────────────────────────────────────────┘
~~~

主题 dossier 内的单帖入口回到 SH-02/CTH-03 同一条 Source；BMP-03 不复制正文或建立新 Evidence，也不把一条帖子转成趋势、品牌表现或消费者总体结论。

### 7.5 AI-02 成果/阶段阅读

~~~text
任务：为一个真实 Brief 形成可审阅的内容提案

已确认输入
  • brief/目标/预算（仅原任务提供才显示）
  • Evidence：来源 A、来源 B
  • 口径和时间窗

阶段
  已完成：阅读输入 → 解析来源
  当前：形成建议（真实任务状态）
  待用户：核对依据 / 选择其中一项
  未运行：外部行动

结果面板
  结论/草稿正文 + 每段引用来源
  [查看来源] [编辑草稿] [采用本段] [拒绝本段]
  [保存为新版本] [回任务]
~~~

主区的结果可继续编辑。右侧分阶段视图可以收起；手机端是一条任务步骤线加一条当前产物，错误时仍留着已有草稿和引用。

### 7.6 视频编辑器（SH-01）

SH-01内有两条适用路径：需要先规划镜头的叙事任务先走ShotPlan；素材已确定或任务是直接剪辑时进入素材箱和Timeline。两者共用当前Brief、来源、项目和版本，不新建Storyboard产品或重复存储。

#### 叙事项目的分镜生产与逐镜确认

~~~text
Desktop / Web — ShotPlan进入剪辑前
┌ 项目/Brief/脚本版本    [返回任务] [后续：剪辑台] [版本状态] ┐
│ 镜头清单                │ 当前镜头画板       │ 镜头信息 / 连续性 │
│ 01 未绘制                │ 完整线稿           │ 脚本段落/时长      │
│ 02 待彩稿                │ 完整彩色分镜       │ 场景/人物/服装     │
│ 03 审阅中                │ 实际动作/空间路线  │ 道具/摄影/声音字幕 │
│ 04 已确认 vN             │ 前后镜/时代光线    │ [批注] [确认此镜]  │
├────────────────────────┴──────────────────┴───────────────────┤
│ [线稿] [彩稿] [上一镜] [下一镜] [显示确认差异] [保存版本]      │
└───────────────────────────────────────────────────────────────┘

确认状态：未开始 → 线稿完整 → 彩稿完整 → 逐镜审阅 → 已确认此版本
修改脚本/场景 → 列出受影响镜头；只撤销这些镜头的确认，其余确认保留
~~~

每镜对应原脚本段落、场景空间/入口动作、人物与服装、道具、摄影构图、声音/字幕和计划时长。批注与“确认此镜”绑定用户看到的镜头/脚本版本及任务范围；变化后展示旧新差异、需重审项与未变化项，不能把旧确认复制到新镜头。完成后从已确认镜头跳入下方剪辑台并保持镜头顺序/定位。原始素材直接剪辑可以略过分镜；纯音频Podcast不自动生成镜头。AI可给具体镜头/脚本建议但必须可查看、编辑、拒绝并在得到真实结果后才进入画板。

#### 专业视频桌面 / Web 剪辑工作台

~~~text
Desktop / Web — 16:9 宽屏，Timeline使用下方完整工作宽度
┌ 项目/版本 [保存] [撤销] [重做] [恢复草稿] [导出当前版本] ┐
│ 工具：选择 / 修剪 / 分割 / 吸附↔定位 / 替换 / 字幕 / 音频   │
├──────────────┬──────────────────────────┬────────────────────┤
│ 素材箱/来源   │ Viewer · 实际当前画面     │ Inspector          │
│ 库/项目/类型  │ 原画幅/实际媒体预览       │ 选中片段属性       │
│ 缩略图/元数据 │ 播放/逐帧/入点/出点       │ 变换/裁切/颜色/音效│
│ 真实时长/状态 │ 播放头/当前时间码         │ 应用/取消/撤销     │
├─────────────────────────────────────────────────────────────┤
│ 共用时间尺 00:00 ───────────── 当前时码 ───────────────→   │
│ 轨道名/锁定  主画面      ─片段A─[片段B]──片段C─────────      │
│             画中画/B-roll    ─镜头D────镜头E──────────        │
│             字幕/图文             ─文本范围───────             │
│             对白/旁白       ─真实音频媒体────────────          │
│             音乐/音效           ─真实片段────────────          │
├─────────────────────────────────────────────────────────────┤
│ 00:18.240 [逐帧←] [播放/暂停] [逐帧→]  Timeline缩放/横移条   │
└─────────────────────────────────────────────────────────────┘

导入→选择媒体→剪辑/修订→预览→导出→播放实际成片→保存工程→重开
~~~

主布局依照已批准的SH-01层级：素材清单、真实渲染预览、所选片段属性在上方可逆区域；Timeline占完整下方宽度，轨道标签固定、共用时间尺，片段几何对应真实顺序/时长。目标Timeline保留用户已批准的多画面层、字幕/文字层、对白/旁白/音乐/音效轨道、精确修剪/分割/重排、吸附与定位模式、撤销/重做；已批准的转场/画面/音频效果继续列作终态操作，不因当前processor或字段未绑定而从方案删去。控件的参数/生效范围在Inspector明确；用户查看另一个面板不改播放头、选中对象或未应用的字段。

选择与播放头使用不同状态：点选片段后其稳定clip identity/区间突出显示，Inspector切到该对象并提供“定位播放头”；拖动/逐帧播放头只更新Viewer帧和时码，不悄悄改变当前选中对象。更换对象时，未应用参数先提供Apply/Discard/Cancel，不静默带到新片段。底部时间尺的水平滚动条只横移视口，缩放控件只改变可见时间跨度，播放头 seek 与剪辑修边各有独立抓手/命令。选择、逐帧前后、设置入/出点、在播放头分割、修剪、撤销/重做、缩放/横移都提供键盘或可见菜单动作；快捷键名只有在Editor owner冻结真实keymap后才显示，未绑定的键位不猜用FCP/PR快捷键。

显示来自真实媒体的帧和音频波形；没有数据就给媒体未解析/轨道无源的明确状态，绝不画假波形。`SH-01.md` §10.10当前DESIGN_READY层级不授权伪造实时草稿预览、链接播放头或磁性拖放；完整目标保留这些功能需求，当前实现与目标差异记为SH-01既有Owner需重审/绑定，而不是提前宣称已有。

状态与操作：导入等待/取消/损坏/过大/离线 → 保留旧素材与工程；媒体缺失 → 保留轨道占位、显示来源和重链动作；未应用属性 → 显示Apply/Cancel与差异；导出进行中/未知完成 → 保留真实operation状态、不因关闭面板重复提交；导出失败/时间窗不合法 → 保留工程、定位和旧版本；成功 → 只有得到实际可播放文件后才标记已导出，工程重开后回同一项目/时间码。

#### 手机 / 窄窗专注剪辑

~~~text
┌ 项目/版本 [返回] [导出] ┐
│ Viewer · 真实当前画面   │
│ 播放头 / 逐帧 / 播放器  │
├ 可选片段轨道（横向平移）┤
│ 主画面/B-roll/字幕/音频  │
│ [素材] [选中片段属性]   │
└ 返回原编辑任务与选择位置 ┘
~~~

手机保留预览、定位、选段、字幕/来源查看、审阅和用户明确允许的轻操作；不把所有桌面属性挤进垂直长页，跨端编辑意图保存后到Web/Desktop继续。屏幕尺度和系统支持能力进入§4.3端侧矩阵。

### 7.7 播客混音检查器弹层

~~~text
选中轨道：对白 A                  关闭 ×
文件/证据：原始音频 / 关联脚本段

音量     ─────●────────  当前值（从 owner 返回）
声像     ───●──────────
均衡/降噪 [已批准目标控件] · 当前Owner/参数状态另行标记
自动化曲线  需要时展开

变化预览：[试听所选区间]   [恢复上次值]
版本提示：当前还未保存 / 已保存版本标识
[应用到此轨道] [应用到所选片段] [取消]
~~~

音频轨道中的人声、音乐、环境音效果分离显示；区域选择可精确拖动并可用时码编辑。混音器选择通道与时间线选择同步。输出前能试听、取消、保存新版本、回听或重新打开工程。

### 7.8 网站操作视频章节

~~~text
Public Website Header  [序境]  [产品]  [工作方式]  [创作]  [案例]  [资源/帮助]  [进入工作区]

Web section：选择一条真实工作路径；章节可独立播放，不把路径串成必经流程

[商业运营] [品牌市场] [独立研究] [直接创作：提案/文稿/视频/播客]
               ↓ 用户选择一条路径
[当前任务/目标] [实际操作视频/字幕] [真实结果/来源与版本]
  路径相关输入      暂停/章节/文字步骤     只显示实际可得的Evidence/Artifact

段落 1  选择业务任务、独立研究或直接创作
段落 2  显示该路径所需输入；创作可从空白/自写要求/获准素材开始
段落 3  按需查看原始 Evidence、时间、范围与缺失状态
段落 4  查看真实分析结果或真实可编辑作品
段落 5  编辑所选内容并保留用户修改
段落 6  查看真实保存/版本/重开/返回路径

视频下方：
“本演示对应序境在 [版本/日期] 实际可操作能力。”
[版本仍 unavailable 的能力在这里不演示成功]
[打开工作区]
~~~

本图是官网视频的目标视觉与交互参考，不是已制作成片或当前派工状态。实际影片只能以当前真实可运行版本现场采集；若页面文案对应的能力尚未可用，片中要标出实际状态或删去声明，不能预录假的成功画面。

导航不显示账号入口、登录或占位；“进入工作区”直达开放产品，不得跳进登录墙。业务路径与独立研究/创作路径可分别进入和观看，演示不暗示全部用户都要先做商业分析或来源采集。

官网影片分镜预估（目标 60–75 秒，可随真实可用功能调整；绝不为凑镜头发明功能）：

| 时段 | 原创画面与文案 | 要拍的真实用户动作 |
|---|---|---|
| 0–4s | 手绘点线形成序境原创标记，短句“从真实目标开始” | 仅品牌动效；无商业数据 |
| 4–10s | 真实 ACC-03 工作主页，展示商业、研究、直接创作入口 | GLOBAL/ALL可开始；不强制选择主体或品牌 |
| 10–19s | 明确选一条实际可用路线及其真实输入 | 业务/研究路线按需选Source；创作路线可用空白、自写要求或获准素材 |
| 19–29s | 展示该示例路线对应的真实阅读/编辑页面 | 仅在业务示例中显示CTH/BMP；独立研究/创作不被重定向到业务页 |
| 29–39s | 展示该路线真实分析结果或真实作品 | 来源、原生/采集时间、缺失值与版本按实际状态显示；不配伪数字 |
| 39–51s | 编辑示例中的真实报告、文稿、视频或播客片段 | 展示相应编辑器实际返回的变化，不强制所有类型串行 |
| 51–62s | 保存一个新版本并重新打开 | 只在得到存储/打开回执后显示“已保存/已打开” |
| 62–72s | 展示同一路线下一步与“进入工作区” | 回到原任务或成果列表，明确返回位置 |

如果其中一项在当前 build 中尚未可用，该分镜延期到对应能力实际可操作后拍摄，不以画面、模型或人工音画合成假装上线。

### 7.9 壁纸和高饱和背景

~~~text
外观预览

左：底图候选                  右：对比样例
[纯白] [纯黑]                  正文 16 px
[纯色选择]                    真实平台图标/作者名
[照片1 夕霞]                   标题/数据/阅读区
[照片2 深蓝晚霞]               播放/选择/错误/焦点
[上传新壁纸]                   遮罩与模糊是实时对比结果

控制：
背景模糊  ━━━━━●━━━━
内容底板  透明 — 淡 — 实
文字保护  自动
[应用] [取消] [恢复默认]
~~~

右侧预览场景要跨过两张照片的鲜红/洋红/深蓝/黑色区域；移动端也可裁切查看全画幅并检验文字对比。纯白/纯黑不要求额外状态图片才能读清楚。

两张照片由 Product Owner 明确表示为本人所有，并允许作为预置壁纸；目标态保留这两张作为内置预设。本轮不改包、不复制附件文件，不触发训练或云端上传；后续入包仅作为 wallpaper assets 并记录原始文件/hash。用户上传壁纸默认保留在当前设备，不扩展成跨端壁纸同步功能。

---

### 7.10 CTH-03 采集入口与单帖详情

~~~text
桌面 / Web · CTH-03
┌ 来源与观测 · GLOBAL / ALL [仅用户当前任务有Focus时才显示] ┐
│ 平台：[全部] [小红书] [抖音] [公众号] [Instagram] [X] [Facebook] │
│ 关键词：[输入来源主题/原始链接________________] 时间：[范围]  │
│ 平台连接/授权状态按真实返回；不把平台注册显示成“已连接”      │
│ [□ 本次只读，不执行外部写入或发布] [开始检索]                  │
├─────────────────────┬────────────────────┬────────────────────┤
│ 来源结果            │ 单篇原生阅读       │ 来源 / 范围 / Evidence│
│ 平台小标 + 标题      │ 多图/竖视频/长文   │ platform_id稳定不变  │
│ 发布时间（未知则说明）│ 仅显示实际取得正文 │ URL / 版本 / scope   │
│ 采集时间（独立显示） │ 派生摘要单独标注   │ Evidence完整性状态   │
│ 平台原标志/质量与部分 │ 原生评论/指标分栏  │ [回CTH] [引入已有研究]│
└─────────────────────┴────────────────────┴────────────────────┘

选中 Facebook 预览记录：
┌ 仅取得公开预览 · 完整帖子暂不可读 ─────────────────────┐
│ 不显示伪造正文、媒体、时间或互动数字                  │
│ [查看原来源] [保留此预览状态] [回筛选结果]             │
└──────────────────────────────────────────────────────┘

手机 · 先读列表，再打开一篇
┌ GLOBAL / ALL · [平台筛选] · [时间] ┐
│ 本次检索：只读 / 已确认             │
│ 〈平台官方/规范来源标识·原形与原色〉原生标题 │
│ 发布时间 · 采集时间 · 部分/未知状态 │
│ [打开原帖]                          │
└─────────────────────────────────────┘
             ↓ 层级跳转
┌ 单篇原生 Reader       [来源与证据] ┐
│ 该平台自己的媒体/正文/评论层级      │
│ 原文与翻译/AI摘要分开展示           │
│ 缺件原因和返回筛选状态              │
└─────────────────────────────────────┘
~~~

按钮只在现有人工只读 API、真实 Scope 与 Permission 通过时可执行；结果状态逐项对应实际返回。平台筛选用稳定 ID，翻译/缩写只做标签，不作为查询键。当前代码存在的固定广州太古汇关键词在目标态移除；保持 GLOBAL/ALL 可用。点击单篇后不得丢失输入、筛选、结果位置；媒体未完整读取时明确标未看完/未取得，不做循环自动播放。

**SourceTarget / Open Original 正式终态：**来源列表、Reader、Event、Case、Risk、Report、Artifact引用等只要显示了重要 Source-backed 事实，都复用同一来源动作语法，而不是各屏自造裸 URL：

~~~text
Trace / 查看来源
→ Source/Evidence detail
→ Open Original（仅当same-row SourceTarget可用）
→ OS / system browser handoff
→ HANDOFF_ACCEPTED只表示系统接收了打开请求
→ 返回序境
→ 恢复route / GLOBAL或FOCUS / Subject或BrandFocus / filters / selection / scroll
~~~

可见状态至少区分 `READY / URL_MISSING / INVALID_URL / DENIED / UNSUPPORTED / SOURCE_WITHDRAWN / STALE / UNKNOWN` 与 `LAUNCH_REJECTED / LAUNCH_FAILED / HANDOFF_ACCEPTED / RETURNED`。普通 Open Original 不读Cookie、不静默登录、不启动采集、不创建Evidence、不改Canonical、不执行外部写入；需要受控网页交互/采集时进入独立SYS-06/Collector路径。当前 CTH-03 已有正式 SourceTarget 合同目标，SH-02/SYS-06 等消费面按各自 Screen Spec 接同一合同。

### 7.11 原创提案与预算资源编辑器（BMP-06/07 + Shared Artifact）

这是BMP/Shared现有创作工作面的独立可审核区域，不由SH-01一句话、Campaign状态表或视频/播客页面代替；不新增Proposal产品、第二预算库或付款功能。目标是让同一Brief下的资源变化真正改变方案，而不是只改一个总数。

~~~text
桌面 / Web · 同一Brief下的两种可行性对照
┌ 提案  [Brief目标/受众/市场] [引用来源] [版本] [返回原任务] ┐
├───────────┬─────────────────────┬──────────────────────────┤
│ Brief约束  │ 方案A（约束组合A）   │ 方案B（约束组合B）        │
│ 固定目标   │ 策略与概念           │ 策略与概念                │
│ 已知范围   │ 镜头/渠道/人员/日程   │ 镜头/渠道/人员/日程        │
│ 不可改约束 │ 工作量/交付物         │ 工作量/交付物              │
│ 硬上限     │ 币种/税基/单价来源    │ 币种/税基/单价来源         │
├───────────┴─────────────────────┴──────────────────────────┤
│ 硬上限 / 目标 / contingency / quote-estimate-commitment-actual│
│ 来源日期/不确定性/未知价格 · 与约束变化关联的交付章节/镜头/周期 │
│ [采用A] [采用B] [编辑所选项] [保存新版本] [预览/导出]          │
└─────────────────────────────────────────────────────────────┘

窄屏：方案A/B并排改为可切换比较页；显示差异摘要、资源影响和来源，
       用户可审阅/批注/作轻量修订；完整编辑返回Web/Desktop。
~~~

**预算状态与操作反馈：**每个方案沿用同一个Brief/Scope/时间/资料和版本基线，只改变用户明确选择的预算/人力/时间/资源约束。数量、单位、币种、税基、hard cap与target、contingency、来源日期和置信度来自现有owner；报价、估算、确认承诺和实际支出分栏，未知绝不补零。超出硬上限时指出受影响资源/交付项，给“修改方案 / 调整可变约束 / 保留旧版”；资源实际不可取得时标“当前不可行”及缺口，不把优化主张冒充价格或ROI。更新提案先显示哪些Brief段落、镜头/播客段落、日程和报告需复核，用户采用后另存新版本；旧版本和选择理由保留。

真实付款、采购、发布或对外承诺不从此编辑器触发；仍由原Permission、Approval、Effect Fence处理。没有实际预算字段/报价source时不画具体金额或“可行”徽标，而是显示“此任务未提供预算/资源数据”；方案分析与预算支付不是同一动作。

### 7.12 来源变更、版本冲突与跨端恢复

本页面作为现有Task/Artifact/SavedWork/Timeline owners的可逆决策层，不增加协作、版本库或文件同步服务。每个待处理变化让用户看清来源版本、受影响对象、可以继续的操作和旧内容保留方式。

~~~text
来源/Brief/预算/脚本出现新版本
┌ 当前任务：Campaign / 提案 / 视频项目                 [回原任务] ┐
│ 变更来源：新Source版本 / Scope变化 / Brief约束 / 文件不可用      │
│ 旧版 vN → 新源 vN+1  | 影响：策略章节/镜头/脚本/渠道/预算条目   │
├────────────────────────┬────────────────────────────────────┤
│ 受影响（原因与定位）     │ 未受影响（保留原值）                  │
│ [段落/镜头/指标] old→new │ [来源/章节/片段] 不需返工              │
│ 校验/权利/时间变化       │ 上游选择理由与父版本                  │
├────────────────────────┴────────────────────────────────────┤
│ [检查差异] [保留当前版本] [采用所选变化并新建版本] [取消]     │
└──────────────────────────────────────────────────────────────┘

发现离线草稿与已保存版本不同：
┌ 本机草稿 vN+1 | 已保存版本 vN+2 | 不能覆盖 ┐
│ [对照差异] [打开已保存版] [保留本机为独立新版本] [稍后处理] │
└ 保存回执未知→先查询原Task/Artifact，不重复提交外部动作 ┘

跨设备打开项目：
┌ 任务与版本可读 | 源媒体在另一设备/当前设备不可用 ┐
│ 不丢Timeline/时码/文本草稿；标出确切缺失文件和Source│
│ [打开阅读结果] [按已有允许流程重新定位文件] [返回]  │
└ 不假装已同步原文件或在新设备可播放 ───────────────┘
~~~

触发包括Source撤回/许可变化、上游关系更正、Brief/预算约束改变、脚本/场景修改、同一Artifact并发版本冲突、离线或“提交后无回执”。影响清单必须连接父版本、Source/Evidence定位、受影响子产物与不受影响项；用户明确采用后才创建新派生版本。跨端继承同一任务/版本和阅读/选中位置，但不继承权限、不复制本机壁纸/未共享文件、不重放外部Effect。保存结果未知时通过原Owner读取同一task/artifact id确认状态，禁止盲目重新发起付费/发布/采集操作。

尚未有并发写/合并route的对象显示“无法自动合并，请保留副本或稍后处理”，不得设计出服务端没有的合并成功按钮。真实保存、比较、撤回与重开callable未绑定的能力仍保留正常目标流程，当前实现状态在§1.4/§12单独记录。

### 7.13 Public Website完整站点信息架构与FAQ

官网是产品理解与获客入口，不是Dashboard、不持有业务流程/Production Truth。Cue只提供主视觉/节奏参考，OpenAI只启发内容导航层级；所有可操作视频、案例和下载必须对应已核验能力/权利，不复制厂商角色或页面。

```text
Public Website · 首页叙事
Header: 序境字标 | 产品 | 工作方式 | 创作 | 案例 | 资源与帮助 | 语言 | [进入工作区]
01 Hero：一句产品任务主张 + [真实操作视频播放] + [进入工作区]
02 工作入口：商业运营 / 品牌市场 / 独立研究 / 直接创作（提案/文稿/视频/播客）
03 可选择的工作路径：CTH/BMP问题分析；Shared资料研究；Shared从空白/自写要求/获准素材直接创作
   业务来源、CTH/BMP研究与SourceBrief仅在用户选择联动时进入创作路径
04 按任务展示的实际操作影片：字幕/分段/暂停/静音/文字步骤
05 四端职责：官网解释；Website/Web优先承载当前闭环；后续Windows/macOS Desktop与iOS Mobile专项接续
06 真实案例/应用：仅显示已获公开许可且可追溯版本的案例
07 资源与帮助：使用指南、能力/兼容范围、数据状态说明、FAQ
08 联系/试用入口和下载区：只接已配置的正规Destination
Footer：正式隐私/条款/支持链接与版本日期；不出现注册/登录占位
```

每页章节都由产品任务组织，而非堆“功能卡”：Home负责主张/导航；Product与Workflows分别说明CTH/BMP商业工作、Shared独立研究和Shared直接创作，创作可从空白、用户Brief/文字或获准素材开始，不要求先完成商业分析；Creator/Video/Podcast展示相应操作而不做孤立生成按钮；Resources/Help提供可读说明和当前能力范围，Stories/Case只展示许可证据。业务分析链与独立研究/创作链并列呈现，箭头只表示用户选择的可选联动，不画成人人必经流程。点击章节能定位到实际内容并支持键盘/浏览器Back；“进入工作区”直达开放产品，不经过账号墙。

| 站点模块 | 目标布局/用户动作 | 正常结果与当前状态 |
|---|---|---|
| Hero / 产品介绍 | 左侧一句任务主张/关键行动，另一侧为原创对象/实际操作视频；视频下有静态说明与章节入口 | 不写不经证据支持的市场领导/准确率/ROI；版本/日期仅在真实录屏能力可核验时显示 |
| 产品与行业流程 | CTH/BMP业务任务、Shared独立研究、Shared直接创作以并列章节呈现；说明各自输入/动作/结果/边界及可选联动 | 官网只读解释，不能创建Subject/Case/Campaign/Artifact或调用Collector；不暗示所有创作都先有业务任务/SourceBrief |
| 操作演示 | Video player + 可跳段目录 + 字幕/转录 + Mute/Play/Pause + [查看文字步骤] | 播放失败/Reduced Motion/离线时仍可读文字步骤和产品边界；无真实产品操作录像时不冒充实拍 |
| 案例/作品 | 卡片及详细来源、Scope、版本/授权说明 | 仅公布有明确展示权和来源状态的真实案例；否则整体隐藏该案例区，不用用户历史社交帖子填版 |
| Resources / Help / FAQ | 目录/搜索/问题分组；答案可展开并链接对应产品操作 | 文字完整、可键盘展开、状态留在当前问题；深链接返回原章节 |
| Contact / Trial | 联系/申请入口说明要处理什么需求和将发生什么 | 链接/表单Destination由现有Website owner提供；当前未配置就显示“联系入口暂不可用”及公开帮助路径，不收集未授权字段，也不转成账号墙 |
| Download / Platform | Web Workspace直达；原生包仅列实际签名/发布的Windows/macOS Desktop与iOS Mobile版本；其他支持OS按浏览器兼容性进入Website/Web | 当前无对应包显示未发布/暂不可下载；Android/Linux原生包不属于交付目标；不得伪造安装文件、扫码入口或支持版本 |
| Workspace entry unavailable | “工作区暂不可达，官网内容仍可浏览” + 真正安全的重试/返回 | 不把Web入口失败解释为需要注册/购买/选主体；状态和可继续访问范围准确 |

#### 官网FAQ实际文案（zh-CN / en / ko-KR）

| 问题/答复 | English | 한국어 |
|---|---|---|
| 序境帮助我完成什么？｜把经许可的商业/品牌资料、团队判断和创作成果连成可追溯、可继续的工作。 | What does LUMENIS help me do? It connects permitted business and brand material, team decisions, and creative deliverables into work you can trace and continue. | LUMENIS는 어떤 일을 돕나요? 사용이 허가된 비즈니스·브랜드 자료, 팀의 판단, 창작 결과물을 추적하고 이어갈 수 있는 작업 흐름으로 연결합니다. |
| 必须先完成商业分析才能创作吗？｜不必。可在Shared从空白、自写创作要求或获准素材直接开始提案、文稿、视频或播客；研究和CTH/BMP内容只在你选择时接入。 | Do I have to finish a business analysis before creating? No. Start a proposal, document, video, or podcast in Shared from a blank page, your own brief, or permitted materials. Research and CTH/BMP work connect only when you choose. | 창작 전에 비즈니스 분석을 끝내야 하나요? 아니요. Shared에서 빈 화면, 직접 작성한 요구사항 또는 허가된 자료로 제안서, 문서, 영상, 팟캐스트를 바로 시작할 수 있습니다. 조사와 CTH/BMP 작업은 원할 때만 연결됩니다. |
| 没有AI时还能继续工作吗？｜可以。可用的阅读、筛选、确定性分析、手动编辑、保存和恢复继续按各自路径工作；只有依赖AI的具体动作显示真实不可用状态。 | Can I keep working without AI? Yes. Available reading, filtering, deterministic analysis, manual editing, saving, and recovery continue on their own paths. Only a specific AI-dependent action shows its actual unavailable state. | AI를 사용할 수 없어도 계속 작업할 수 있나요? 네. 사용 가능한 읽기, 필터링, 결정론적 분석, 수동 편집, 저장, 복구는 각 경로에서 계속할 수 있습니다. AI에 의존하는 작업만 실제 사용할 수 없는 상태로 표시합니다. |
| 必须先选主体或品牌吗？｜不必。可从全部范围开始；具体任务需要时再聚焦。聚焦不等于获得权限，也不会自动开始采集。 | Do I have to choose an entity or brand first? No. Start in the all-available scope and narrow only when a task needs it. A focus selection grants no permission and starts no collection. | 먼저 사업체나 브랜드를 선택해야 하나요? 아니요. 전체 범위에서 시작하고 작업에 필요할 때만 범위를 좁히면 됩니다. 초점 선택은 권한을 부여하거나 수집을 시작하지 않습니다. |
| 数据代表整个市场吗？｜不一定。页面会按实际来源、范围、时间和样本覆盖说明观测；未取得字段保持未知，不推成消费者总体。 | Does the data represent the whole market? Not automatically. Observations are labeled with their actual source, scope, time, and coverage; missing fields remain unknown rather than becoming a population claim. | 데이터가 시장 전체를 대표하나요? 자동으로 그렇지는 않습니다. 관측은 실제 출처, 범위, 시간, 표본 범위와 함께 표시하며, 없는 값은 소비자 전체에 대한 주장으로 바꾸지 않고 미확인으로 둡니다. |
| AI会替我作最终决定或发布吗？｜AI可在实际接通的任务里协助整理、分析和创作；用户审阅来源、修改结果并决定后续动作，外部影响仍需现有审批。 | Does AI make the final decision or publish for me? AI can assist with connected research and creation tasks. You review sources, edit results, and choose next steps; external effects retain their existing approval gates. | AI가 최종 결정을 내리거나 게시하나요? 연결된 조사와 제작 작업에서 AI가 도울 수 있지만, 출처를 검토하고 결과를 수정하며 다음 단계를 결정하는 것은 사용자입니다. 외부 효과에는 기존 승인 절차가 적용됩니다. |
| 手机版能完成全部桌面剪辑吗？｜手机用于查看、通知、审阅和适合触控的轻操作；密集多轨编辑可在Web/桌面任务中继续。 | Can the mobile app do all desktop editing? Mobile supports viewing, notifications, review, and bounded touch actions; dense multi-track editing continues in the Web or Desktop workspace. | 모바일 앱에서 데스크톱 편집을 모두 할 수 있나요? 모바일은 보기, 알림, 검토와 터치에 적합한 제한된 작업을 지원하며, 복잡한 멀티트랙 편집은 웹 또는 데스크톱 작업 공간에서 이어갑니다. |
| 如何下载或联系团队？｜只显示当前已发布的安装包与已配置的联系渠道；如果暂不可用，会说明状态并提供仍可访问的帮助内容。 | How do I download the app or contact the team? The site shows only released installers and configured contact channels. If one is unavailable, it says so and keeps available help content accessible. | 앱을 다운로드하거나 팀에 문의하려면 어떻게 하나요? 사이트에는 실제 출시된 설치 파일과 설정된 문의 경로만 표시됩니다. 사용할 수 없는 경우 그 상태를 알리고 이용 가능한 도움말은 계속 제공합니다. |

FAQ不是虚构功能承诺。部署时逐条与实际Main版本、公开案例授权、下载Destination和联系Owner校验；语言字段和真实页面菜单同源，不重复硬编码。产品闭环前无登录/注册/账号菜单或占位。

### 7.14 业务决策、Skills/Memory、复盘与通知的具体操作面

这些是现有 CTH/BMP/AI/Shared Screen 的不同用户工作，不合成通用列表模板。以下是审核用目标态；按钮状态、保存回执与当前阻断必须由本Screen关联Owner返回。

**CTH-08 Case 与 CTH-09 决策：**

```text
CTH-08 · Case dossier
┌ Case状态/对象/责任/期限 ───────────────────────────────┐
│ 左：来源事件顺序/冲突        中：已核事实/待核判断       │
│ 右：Evidence与定位/权限      下：处理历史/责任与下一步   │
│ [加入已存在来源] [记录调查结果] [打开影响它的决策]     │
└ 状态 Draft→已核实/处理中/已关闭；Knowledge提炼另行审核 ┘

CTH-09 · 决策与效果
┌ 决策目标/理由/可选方案/不确定性/责任人 ────────────────┐
│ 每个事实链接Evidence；相关≠因果；计划≠已执行           │
│ 预计影响/风险 | 权限/审批/实际回执 | Outcome/Review     │
│ [保存决策草稿] [请求本动作审批] [返回Case]              │
└ 只按Owner真实返回显示已批准/执行/失败/待回执            ┘
```

Case关闭需具体结论和后续行动；知识资产来自已审Case并保留被拒/过时状态。外部回应不得从草稿状态跳成已发布。服务端拒绝、超时/效果未知和用户取消分别反馈；有不确定回执时查询同一Action ID，不重复执行。

**BMP-05 创作者研究：**

```text
左：有来源的Creator名单/筛选条件/样本范围
中：选中Creator的身份与真实作品序列（按原生类型展示）
右：品牌/brief适配证据 · audience/费用/合作权利/风险/日期
底：对比所选对象 → [加入当前Campaign草稿] [返回研究]
```

没有真实Creator identity、作品、互动分母、费用或合作权利时各自Unknown；不得让生成式图片、审美标签或统一“fit score”替代来源。加入Campaign只带有正式locators/版本的选择，scope或授权变化时保留旧brief并要求重审。

**AI-01上下文/Memory与AI-04 Skill：**

```text
AI-01 主编辑面：用户目标/当前task → 可加入真实材料 → 草稿/结果
┌ 当前任务使用的上下文 [展开] ──────────────────────────┐
│ 来源/Brief/Scope/版本 | Memory条目（仅实际被Owner返回时）│
│ 何时/为何纳入、来源版本、允许范围、待核项               │
│ [打开来源] [本次不使用该条] [编辑任务草稿]             │
└ 无返回Memory时不显示“已记住”；对当前任务的排除不删除Memory ┘

AI-04 Skill目录 → 选中能力详情
│ 名称/Owner/版本/来源/许可证/信任/输入/输出/风险/政策 │
│ 验证与适用的消费流程 / 可调用状态 / 最近真实结果      │
│ 查看运行历史/结果来源 → 返回调用任务                  │
└ 未验证/许可未知/未绑定Skill不标可运行                  ┘
```

AI-01上下文按Task/Agent/Memory Owner回执显示，不在屏幕建立第二Memory库；每次使用都给用户核对输入和来源、编辑/拒绝草稿的路径。AI-04当前ScreenSpec是只读Skill目录，无Install/Enable/Disable/Update/Uninstall按钮；产品已批准的Skill生命周期属于完整目标和C2现有Owner后续合同，当前只读App不能模拟这些写动作。正在运行的能力更新需显示运行版本并由Owner决定安全切换；旧Artifact/Trace始终可查，不自动删记录。

**SH-05 Evaluation / Learning 与 SH-06 Inbox：**

```text
SH-05：真实任务与Outcome → 证据/定义/分母 → 评价结果 → 候选版本对照
      [查看反例] [保留候选] [回到Owner任务] [申请正式评审]
      VERIFIED / CANDIDATE / REJECTED / RETIRED / UNKNOWN分开显示

SH-06：通知 | 任务 | 警示 分lane；每行展示来源、范围、时间、状态
      点击→打开原始Case/Approval/AI result/Artifact + Return
      当前Screen只读；任何批准/重试/分配都必须回发起动作页执行
```

评价阈值、Held-out结果、Approval、Promotion和Rollback的每一步显示真实版本与来源；候选不是已验证方法，评分也不改写Production Truth。Inbox不把来源不明事项变“红色未读”；打开错误/过期通知说明影响并指向可恢复的原任务。屏幕当前只读时，保留这套目标工作链但不画可写按钮作为当前能用。

## 8. 创作工作台的完整目标与现状边界

### 8.1 SH-01 视频功能应覆盖

- 新建/打开真实工程；用户能够知道媒体是原位引用还是副本，源文件可读不可读。
- 素材选择：按文件夹/类型/来源分类、筛选、搜索；缩略图/首帧必须来自真实媒体。
- Viewer：画幅/分辨率/帧率、播放/暂停、逐帧步进、入点/出点、比例/裁切、安全框/字幕预览。
- Timeline：尺、播放头、选中片段、独立轨道、波形/缩略帧、磁性/定位间隙、拖拽/修剪/分割/复制/撤销/重做。
- Inspector：根据当前选择出现，不显示与当前对象无关的数百个参数；媒体类别/作用范围/关键帧有效与否写清楚。
- Effects/Color/Audio：终态界面完整呈现用户已批准的效果链、适用范围、before/after、参数/强度、关键帧/自动化、Apply/Cancel/Reset/Undo和预览结果。当前Processor/参数/渲染器缺口另列为Owner依赖；能力未接通时当前构建明确 unavailable，不得让最终方案只剩“以当前processor为准”或删除正常路径。
- AI assist：来自当前材料/研究/brief 的可选建议；显示建议文本/剪辑点/用料出处，用户可逐条修改/拒绝。
- Export: 终态包含预设、格式、分辨率、帧率、音轨、字幕、输出目录、估计大小/时间与版本选择；每个字段由现有Renderer/Artifact owner给真实值，当前未绑定时在差距栏标出。导出失败保留工程和源文件；只有实际返回可读成片时才显示成功版本。
- 用户离开项目时保留选择、播放头、zoom、工具和未保存更改处理。

### 8.2 BMP-08 Podcast 功能应覆盖

- 项目与节目/章节目录。
- 导入/读取用户提供的音频文件、可授权的音频理解/脚本对齐、Source与Brief 引用；音频读取/真实播放/试听/文件编辑不能因为麦克风功能后置而一起延期。
- Script cue 与证据引用；不同角色/段落可按真实脚本解析标记。文字改写与声音编辑是两个独立修改对象：先显示被改的是脚本文字还是波形/音轨参数。
- 导入文件的真实回听、时码对齐、波形预览、定位/循环选段、片段级操作；削波/静音提示只按真实信号处理。
- 剪切/拼接/淡入淡出/空隙插入/移动/分轨。
- Voice choice/语速/音量/文本或参考音频/生成试听属于已批准的音频创作目标，最终控件由既有AI Gateway/Audio owner给字段；当前模型/调用未绑定时明示Unavailable与依赖，但不从终态方案删除。
- 终态Mixer保留选中轨道的channel strip、mute/solo/pan/gain、automation与已批准effects；具体值、单位、效果链和输出由既有Audio owner定义。当前路径未接通时不可假装已处理，也不能以“当前系统没支持”替换用户已批准的专业工作流。
- Mixdown/导出格式和输出版本；支持项目保存、关闭后重开、版本比较和回滚。
- AI 协助：研究→提纲→脚本→标注→可选配音/声音建议→混音建议→人审→导出→评价。所有 AI 内容都可编辑/可删除/回溯引用。
- 实时录音/麦克风输入是用户明确后置项，不进入当前默认产品操作流程，直到整体产品闭环结束且 Product Owner 另行批准。后置不影响音频文件的导入、理解、播放、试听、剪辑和导出。

---

## 9. 十项 Nielsen 原则落实到序境操作

| 原则 | 序境中用户能直接看到的行为 | 验收场景 |
|---|---|---|
| 系统状态可见 | 真实加载、保存、导出、等待授权、失败、过期数据在当前任务区显示 | 进行一次真实素材读取/导出，等待和终态都不丢上下文 |
| 现实世界匹配 | 页面使用“来源、品牌、事件、素材、剪辑、导出”等业务词，不暴露内部 API/gateway 抽象 | 用户从真实问题顺着页面字段完成一项工作 |
| 用户掌控自由 | Back、Close、撤销/取消、离开未保存提醒均回原对象 | 打开原文、详情、参数，再退回同一滚动/选择/播放头 |
| 一致性 | 同一动作/来源/状态跨端用一致语义和品牌语言，四端排版可不同 | 同一 Evidence 在 Web/桌面/手机来源信息一致 |
| 错误预防 | 导入前确认来源/替换范围；外部写入前明确对象和影响；禁用操作旁说明原因 | 故意选择无效文件或拒绝许可，不形成伪操作记录 |
| 识别而非记忆 | 近期素材、来源平台、Focus、所选时间窗、可用动作可见 | 用户返回时不必记住来源ID/任务号 |
| 灵活高效 | 键盘快捷键、列表搜索、时间轴跳转和拖拽可并用 | 不依赖长滚动/重复填入 Brief 内容 |
| 克制与审美 | 信息精简但口径、来源、可恢复路径不被删掉 | 复杂高饱和壁纸上主任务保持可读；不靠3D装饰掩盖空功能 |
| 错误恢复 | 失败解释具体原因，保留草稿和有效材料，允许局部重试 | 模拟断网/AI route unavailable/export error 后修复或继续手动完成 |
| 就地帮助 | 操作旁提供短说明或对应帮助，不跳往泛化教程 | 选到未知字段/不兼容指标时能在当前视图打开解释 |

可用性测试以“用户是否完成工作并能继续”记录，而不是页面满意度打分或动效偏好投票替代真实任务。

---

## 10. 上线前目标态验收清单

每个端到端功能都必须通过其当前 owner 契约，包括：

### 真实工作

- 用户实际目标明确，输入是合法的真实材料而非测试 fixture。
- 页面中能看见材料、来源和时间；摘要/数字能追 Evidence 与口径。
- 有真实服务能完成正常路径，不以 disabled control/“可稍后使用”替代产品目标。

### 结果和继续工作

- 用户看见真实结果、可以修改并保存到既有 Artifact/Case/Brief/Decision。
- 完成后重新打开，来源/任务/版本一致。
- 更改输入条件、范围或任务目标后提示受影响对象，旧结果仍可复查、对比和回滚。
- 输出到真实文件时回显最终路径/Artifact，而非只有按钮或 Toast。

### 恢复与权限

- 加载/空/无数据/采集未开始/部分覆盖/过期/离线/错误/拒绝/待审批各自清楚。
- 权限拒绝/取消后没有外部副作用；审批授权与用户点击分开验证。
- 搜索过滤、开侧层、媒体播放、timeline 编辑、离开页面再回来不会让焦点/草稿/范围丢失。
- Scope/Permission/Evidence/Source 身份要被现有 owner 验证。当前 registry 为旧快照，正式实现必须重新核对当前生成版本。
- CTH-03 真实用户可以在 GLOBAL/ALL 下显式确认只读检索；平台展示名与稳定 `platform_id` 完全分离，所选通道能定位到同 ID 的内容行。
- 每条来源能从列表打开原文/可用媒体和 Evidence lineage，再返回原任务与过滤位置；未知发表时间、未取得正文、预览态、部分媒体和未完整观看都如实呈现。
- 单帖观测不会自动变成趋势/市场总体；100条截断、样本评论和互动计数保留来源/窗口/分母边界。
- 授权失效、限速、挑战、撤权或部分入库不能触发假成功；已保存 Evidence 可继续，重试仍经过既有 owner 与幂等路径。

### 四端、视觉和多语言

- Website：真实操作视频、字幕/静音/暂停/Reduced Motion/失败状态/跳转入口。
- Web/desktop：实际窗口宽高、键盘、鼠标、密集编辑和简短垂直页面。
- Mobile：触摸、狭窄空间、音频/视频、工作接续、关键动作可达。
- 中文/英语/韩语；200%文本、可访问标签、可见焦点、色彩不单独携带状态。
- 两张高饱和壁纸随机裁切测试；深浅主题、纯白/纯黑、透明底板。
- 工具栏、菜单、抽屉和错误文案与 screen 当前任务一致；没有无意义大字号或表面装饰。
- AIGC/Agen behavior physically tested with real allowed inputs, source/citation/result/revision and failure. 无服务真实路径时标 blocked/unavailable，不跳用被退役的模型路径。

### 发布证据

最终发布证据按同一 release composition 展示，不把不同时间/不同 SHA 的绿项拼成“全绿”：

```text
candidate source SHA
→ source/config/DB/Experience checks
→ Product Gate
→ App Gate
→ Critical E2E
→ package/build artifact（该Surface有承诺时）
→ loaded runtime identity / version readback
→ rollback/recovery proof
→ Product Owner重复核心工作
→ USER_VERIFIED / RELEASED
→ real elapsed operating evidence
→ OPERATING
```

- 每一步显示 `PASS / FAIL / NOT_RUN / UNKNOWN / STALE`、证据时间与SHA；早一步PASS不能遮住后一步未运行。
- 当前 HEAD 下所有变更后运行规定的 current-snapshot static checks，后续修改都要重测相应内容。
- 按 affected source 做必要测试；按用户承诺端运行真实 E2E；触发安全/数据/权限门禁。
- 所有上线文件、规则与状态对应到同一接受版本并经 GitHub main verification；不把本审核文档、截图、source存在、build成功或HTTP 200当部署/Release证据。
- Public Website、Web Workspace、Desktop、Mobile按各自真实承诺核对；未发布安装包就显示未发布，不能用另一个Surface的build代替。
- Product Owner 最终完成重复核心工作的端到端审查后再标 USER_VERIFIED / RELEASED；OPERATING还需要真实运行周期证据。

**本轮未执行以上产品测试或运行验收。**它们作为目标完整性条件保留，不声称通过。

---

## 11. 范围后置事项与恢复条件

| 后置事项 | 当前处理 | 恢复条件 | 不得导致什么 |
|---|---|---|---|
| 任何新付费/外部服务/授权 | 仍按既有 external-effect 和商业授权 owner | 有真实服务、明确范围和用户授权 | 不可在 UI 设计中假装 provider 已接入 |
| Cue/Manus 角色图形/第三方应用 logo | 仅作研究样本，不能直接复制到商用产品 | 获得正式可用授权或改用序境原创设计 | 不可将第三方 icon 变成序境标识 |
| 其他未定位的历史视频附件 | 不属于本次指定的五条 Desktop MP4 + 三条新视频范围；只保留既有可定位/缺件状态，不重看 | 不缩减当前八条已指定视频的完整研究；不作为本稿缺件门槛 | 用户发过但本机当前定位不到的文件仍记录为未定位；不反推用户没发送，不虚报已分析 |
| 两张高饱和自有壁纸 | 已在 `app/assets/wallpapers/crimson-sunset.jpg` 与 `cobalt-dusk.jpg`；资源 README 记录用户来源、大小与未修改 | 继续由 SYS-05 现有本地偏好路径选择/预览/恢复；本稿只核对，不改包或复制附件 | 视觉验收仍须覆盖强红/洋红/深蓝/黑区域、裁切、焦点、字号和动效；其他用户壁纸不自动上传或跨设备同步 |

---

## 12. 方案追溯与最终审核结论

### 当前能力状态总表

| 能力族 | 当前快照静态观察 | 目标态完整结果 | 尚缺/待验证 |
|---|---|---|---|
| 44 个工作区页面 | 44 个 Screen 文件和 44 份当前 Screen-specific 规范存在 | 本稿逐页定义任务、形状、操作/返回，并指向真实规范状态 | 逐页核对当前 Field/API/Permission/Evidence 与完整真实 E2E；spec.status 是设计/合同状态，不是实现验收 |
| 产品主页/启动 | ACC-03 / LaunchSurface 源码有入口；root 默认 CTH-01；ACC-03 当前有当前视角/启动状态/滚动呈现 | 开放产品后默认全局任务主页→AI-01；登录方案后置 | 修复错误默认；主页重新按本稿设计；各桌面入口回验 |
| 官网页面 | Astro 页面和 zh/en/ko 页面源码存在 | Cue 基调 + OpenAI 信息层级 + 真实操作影片/FAQ/入口 | 逐条官网声明和现状能力核对；公开视频、控制、降动效和部署 E2E |
| CTH | 各屏 widget/repository classes 存在；CTH-03 GET 读取最多100 Canonical rows；人工只读 search POST 已存在但 App 当前不调用；GET row 的部分字段在 Dart 丢失 | GLOBAL/可选Focus → 人工只读搜索 → 稳定平台ID过滤 → 打开真实单帖/Evidence → CTH业务流/保存重开 | CTH-03 `BACKEND-GAP-009`；source/captured/projection未进UI；平台lane缺projection与客户端校验不匹配；固定关键词预填Taikoo Hui；原文/媒体/互动字段未由该row提供 |
| BMP | 各 screen source 存在 | 品牌/市场/内容/创作者/Campaign/Podcast/评估连贯；BMP-03将单帖视为有明确边界的一条来源 | BrandFocus/竞品/Creator/真实评价字段和原生结果；没有兼容的覆盖/样本/时间序列不能由单帖推出趋势或消费者总体 |
| AI/Agent | AI-01..05 屏源码存在；AI-05 明确有诊断 fallback | grounded task/result/artifact/evidence/permission/evaluation闭环 | AI-01真实执行/取消/revision，AI-05独立能力；provider/model退役边界 |
| Shared/Evidence/Media | SH-01 当前安全目录实现；另有 media project/preview/timeline 源码；SH-02..06 各有独立 read-only/scope-guarded 实现状态 | Source阅读/Discover/Brief/视频/音频/成果保存与重开 | Evidence scope、Discover callable、真实素材链、Timeline导出/重开/版本/字幕/播客闭环分别验收 |
| SYSTEM | SYS-01..08 源码及不同状态的屏幕规范存在；SYS-05 `DESIGN_READY`，SYS-06 `IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED`；SYS-02 当前 Screen Spec 是状态只读面 | Runtime/Collector/DB/Permission/Settings/Browser/Eval/Log的真实状态与恢复；设备偏好保持本地 | 每屏按规范继续验收；SYS-02不凭UI加未绑定动作；壁纸不做跨端/云同步，真实权限数据和运行时恢复另需 E2E |
| 单帖参考 | 六平台单帖草图-v3有六个来源各一帖，QA只证明字符草图结构；source scope未分配、正式 refs 为空 | 六个平台的原生图文/视频/长文/语言/评论层级不同；有真实来源和权限后接到 CTH-03/SH-02/BMP-03 | 不是生产 Canonical 记录、不是全平台覆盖、不是商业展示许可、不是训练授权；原文/媒体缺件状态不能从草图升级 |
| 品牌/图标/壁纸 | SYS-05 规范和外观源码存在；两张夕霞照片已随 app assets 捆绑；局部 Web/Windows 证据已记录 | 原创手绘彩色身份图标 + 功能线 icon；两张照片在支持表面自适应呈现 | 完整原创 icon family 的全端验收、两张照片的各种裁切/文字焦点场景以及原生材质实绘仍未完成 |
| 真实 E2E 和发布 | 本轮未启动/测试/部署 | 每个 owner 走真实 input/result/save/reopen/error/recovery/evaluate | 按当前 main 完整验收并同版本验证上线 |

### 当前确认的差距（不删除产品能力）

1. 默认工作区路由还是 CTH-01，与主页目标不一致。
2. ACC-03 规范 `DESIGN_READY`，但实际 root 初始路由仍为 CTH-01；页面当前含当前视角/启动检查和整页滚动。目标按 ACC-03 task-first/global composition 重组，root binding 与所有入口 E2E 尚未验收。
3. AI-05 source 自己说明无独立绑定时 fallback 到 AI-01 diagnostics。诊断屏幕不等于 AI 功能完成。
4. 44 个屏幕组件存在，不等于所有功能正常使用；本轮还没有重跑数据库绑定、用户数据读取和完整 E2E。
5. 绑定登记表 generated_from_head 旧于当前提交；逐项状态不能用其旧分布当作 current status。
6. 审核稿1.3引用了五条Desktop视频的帧阅读报告/联系表阅读记录；本次1.5未重新逐帧复看，也不独立背书覆盖结论。历史JSON对2601473与cb55仍保留PARTIAL/PENDING状态；本稿保留该差异，不做逐像素检查或全帧OCR声明。
7. Website Astro 源码存在，但官网当前真实操作视频/部署/产品 claim 没有在本轮运行验证。
8. 媒体/播客组件和操作按钮源码存在，不意味着真实项目从素材导入到导出、重开和评价已经用户验证。
9. CTH-03 的采集 POST 接口存在，但 App 未调用；screen GET 的平台 lane 缺 row projection、Flutter 又据此筛选；Dart模型没有独立 `platform_id`，当前以 `platform/channel` 字符串筛选，通道展示值与原始内容key可能不一致；这是实际接线/字段缺口，不是“平台 API 不存在”。
10. CTH-03 当前把“广州太古汇”设为默认查询关键词，与用户要求的 GLOBAL/ALL 默认不一致；必须清空预填值，不能把选择该主体变成进入或使用产品的门槛。
11. CTH-03 GET 读取上限为100且可标 `partial`；当前字段不能显示完整帖子内容/媒体/评论/平台指标；六平台结构稿的 source scope/formal refs/商业权利状态仍不足以构成生产证据或官网展示素材。
12. Collector当前核心缺口已从旧Adapter小修收敛为五个P0与三个共性底座：XHS HK/International recovery fence、Task attempt fencing、durable terminal receipt、兼容采集统一进Source/Evidence/Canonical、sole Canonical gate，以及PlatformManifest / PlatformSession / LumenisPlatformRecoverySheet。已修掉的历史Facebook result-contract/旧双写测试不得重新当当前问题。
13. SYS-02 revision 2已经承接最终Manifest/Session/task连续性目标，但当前实现仍是read-only；PlatformManifest、PlatformSession、durable receipt及真实计划/暂停/取消/恢复callable仍需C1/C6代码和runtime E2E。
14. SYS-06 revision 4已经明确受控Browser只服务RecoverySheet需要的LOGIN_FORM/VERIFY或普通受控阅读；QR、BLOCKED/COOLDOWN与Session健康真相不归Browser UI。当前live/native recovery E2E仍未验收。
15. SH-02 revision 3已承接SourceTarget/Open Original/Return最终目标；当前scope/Evidence envelope、typed SourceTarget、platform launcher与Return绑定未完成，不能把裸URL当替代。
16. SYS-07 revision 2已承接same-release证据链；当前builder仍只有有限security/skill checks，Product/App/Critical E2E/package/runtime/rollback/PO repeat的真实聚合合同未绑定。
17. AI-05正式Screen Spec禁止provider marketplace/model selection和raw provider/model名称；旧草图里“用户手动选模”属于Codex研发配置，1.6已移除，不得进入序境产品UI。
18. 本轮1.6只收敛权威文字合同、Screen Spec和文字视觉目标，不修改产品代码、资源、运行或部署；上述实现缺口仍由F/C1/C6及对应Owner按现行规则完成。

### 最终审核范围

- 全部四个前端工作面；
- CTH、BMP、Shared、SYSTEM、AI/Agent；
- 现有 44 屏和跨域路径；
- 正常流程与主要异常/取消/授权/撤权/恢复状态；
- 图标、字体、壁纸、透明底板、动效、AI交互与媒体编辑视觉；
- 所有参考资料按“观察→适配→能力→交互→验证”的链条说明；
- 当前源码、历史候选、未知状态、后置边界、缺失验证分别标明。

本稿 1.6 已经 Product Owner 批准为当前产品闭环的完整文字目标态与视觉审查基线；它仍不是产品代码实现、正式美术稿或用户验收完成证明。后续实现不得因为当前接口缺失而缩减目标，也不得因为本稿存在就把未核验工作写成完成。

### 前端目标收敛处置索引（F-01—F-18）

F-01—F-12对应 `Frontend_Delivery_Audit.md` 的原12项发现；F-13—F-18记录 2026-10-06—10-07 权威规则继续演进后，本稿 1.6 对 SourceTarget、Universal Platform Acquisition、Recovery、release evidence 与 AI-05 边界的二次收敛。“已补入方案”只表示当前目标文字/草图/Screen Spec已同步，不代表产品代码、运行/E2E或用户验收完成。

| 审计项 | 文档处置 | 主稿位置 | 配套文字草图 |
|---|---|---|---|
| F-01 | 补完整桌面/Web剪辑区、轨道、播放头/选中对象/Inspector关系、时间轴横移缩放、键鼠替代及失败恢复；手机独立重组 | §3.6、§7.6、§8.1 | SH-01宽屏Timeline与媒体状态 |
| F-02 | 增加叙事任务的完整ShotPlan线稿→彩稿→逐镜审阅/批注/确认与变更后局部重审 | §4.1流程F、§7.6 | SH-01 ShotPlan |
| F-03 | 将批准的终态能力与当前接口/processor缺口分列，不以Unavailable替代正常目标操作 | §1.4、§4.2、§8.1–§8.2、§12 | 相关页面保留目标动作并标出现行绑定差距 |
| F-04 | 分清已存记录、一次搜索、业务批次、AUTO计划、查询续页和平台原生分页；列出旧route可接字段与缺少的Owner合同 | §4.1流程I、§5.1–§5.4、§7.10 | CTH-03、SYS-02 |
| F-05 | 六个平台均分别呈现完整正常Reader与部分/权限/失效状态，并说明其它获准来源按原生内容类型进入 | §5.3 | SH-02六平台单帖形态 |
| F-06 | 明确CTH主体/BMP品牌登记字段、去重、来源证据、关系有效期和未验证关系；补实际文件导入/批准/重试/解析状态 | §4.1流程B/K、§7.10、§5.4 | CTH-02、BMP-02、SH-01导入 |
| F-07 | 补来源/Brief/预算/脚本变化影响图、受影响与保留项、版本冲突、未知回执和跨设备缺失媒体恢复 | §1.3、§4.1流程L、§7.12 | SH-04成果/冲突状态 |
| F-08 | 补官网任务导向IA、操作视频控制/失败回退、具体FAQ、案例授权、联系/下载与工作区入口不可达态 | §2.3、§3.4、§7.8、§7.13 | 官网职责在ACC/网站文案引用中保留 |
| F-09 | 补Case/决策、Creator进Campaign、Memory上下文、Skill生命周期、Learning候选与只读通知返回的独立交互 | §6.7、§7.14 | CTH-08/09、BMP-05、AI-01/04、SH-05/06 |
| F-10 | 明确四个产品Surface与桌面快捷方式不同，并补OS、尺寸、键盘/返回/触控/媒体边界 | §4.1流程A、§4.3 | ACC入口与逐屏任务重组 |
| F-11 | 将字段/权限/导入/采集错误、A11y语义、焦点返回、200%文字、缺词回退、图标层级及五位架构角色纳入三语目标 | §3.3–§3.6、§7.10 | 逐屏标题/动作映射与操作状态 |
| F-12 | 将25项既有U能力逐项连到关键控件、用户可见结果、异常/恢复与原Owner，不把Screen ID或状态当作验收通过 | §6.7、§12 | 全44屏Owner/合同表与逐屏草图 |
| F-13 | 把六平台采集扩展为Universal Platform Acquisition终态：PlatformManifest能力投影、PlatformSession真状态、来源失败隔离，不新增平台后台 | §4.1流程I、§5.4、§6.5 | SYS-02、CTH-03、SH-02 |
| F-14 | 补唯一LumenisPlatformRecoverySheet：QR/Login Form/VERIFY/BLOCKED四态、多平台单Sheet队列、health readback、焦点/读屏/Return | §4.1流程I、§6.5、§10恢复验收 | SYS-02、SYS-06及跨屏Sheet |
| F-15 | 把query continuation、native cursor、durable receipt/terminal replay分成三种用户连续性，禁止终态重开伪装新run | §5.2.1、§5.4 | SYS-02任务/恢复状态 |
| F-16 | 将SourceTarget正式合同扩到CTH-03、SH-02及所有重要Source-backed事实：Trace→Open Original→诚实handoff→Return | §5.4、§7.10 | CTH-03、SH-02、相关Evidence drawer |
| F-17 | 补same-release发布证据链：Product/App/Critical E2E/package/runtime/rollback/PO repeat/RELEASED/OPERATING，证据按SHA分开 | §6.5、§10发布证据 | SYS-07 |
| F-18 | 清除研发配置泄漏：AI-05只做产品AI服务诊断，不暴露/选择Codex的Astra/Sol/Luna或raw provider/model | §4.2、§6.4 | AI-05 |

审计中的通用权限UI边界按本会话Product Owner直接指令处理：整体账号/登录/通用角色配置留待完整产品闭环后重新规划；本稿继续保留原业务动作内的服务端Permission、明确批准/拒绝、来源授权、Effect回执与审计，不恢复登录墙。审计未复演全部视频帧；本稿只沿用已有的指定视频覆盖记录/观察和对应采用点，不声称本轮重新逐帧观看。


## 2026-10-08 Intelligent UI 任务适配与全屏索引

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

本次增补依据 [Intelligent UI 采用研究](../INTELLIGENT-UI-ADOPTION-20261008.md) 与现行 Experience Constitution §38，将“任务决定呈现形态、同一结果可阅读/调整/继续使用”逐屏映射到现有44份ScreenSpec。此处是1.6蓝图的日期增补，保留原始1.5/1.6内容、审阅状态和历史草图，不创设第二设计权威。每项的详细交互、四端差异、来源/版本连续性、失败恢复和补充验收见链接Spec末尾及[ScreenSpec README逐屏映射](../../../../contracts/experience/screen-specifications/README.md#intelligent-ui-全屏语义映射2026-10-08)；对应字符视觉草图见同目录44-screen wireframe增补。

### 全屏索引

| Screen | 本屏 Intelligent UI 用户任务 | 屏幕规范 |
|---|---|---|
| ACC-01 | 确认内部工作区入口可用并继续宿主指定目标 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/ACC-01.md#intelligent-ui-逐屏采用项2026-10-08) |
| ACC-02 | 查看当前GLOBAL_ALL或明确选择一个可访问Subject视角 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/ACC-02.md#intelligent-ui-逐屏采用项2026-10-08) |
| ACC-03 | 从首页开始 CTH/BMP 业务、Shared 研究或直接创作，或继续原任务 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/ACC-03.md#intelligent-ui-逐屏采用项2026-10-08) |
| ACC-04 | 理解一项真实阻断并沿已有恢复路径返回 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/ACC-04.md#intelligent-ui-逐屏采用项2026-10-08) |
| AI-01 | 把用户目标、当前资料与约束组成可检查的执行意图 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/AI-01.md#intelligent-ui-逐屏采用项2026-10-08) |
| AI-02 | 跟踪真实任务阶段与持久化产物 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/AI-02.md#intelligent-ui-逐屏采用项2026-10-08) |
| AI-03 | 逐条核验分析结论的来源并继续修订 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/AI-03.md#intelligent-ui-逐屏采用项2026-10-08) |
| AI-04 | 查找适合当前任务的已验证能力，并按现有 Owner 合同完成已批准的使用与生命周期操作 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/AI-04.md#intelligent-ui-逐屏采用项2026-10-08) |
| AI-05 | 查看AI服务真实状态和延迟样本 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/AI-05.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-01 | 回答授权品牌的市场信号与值得关注的趋势 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-01.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-02 | 理解品牌组合、子品牌与竞品关系 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-02.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-03 | 识别需要进一步验证的机会信号 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-03.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-04 | 看品牌传播链哪些阶段实际有观测 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-04.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-05 | 比较创作者匹配度和风险依据 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-05.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-06 | 把授权素材和内容想法推进为可审阅版本 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-06.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-07 | 连接活动目标、预算、里程碑和实际结果 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-07.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-08 | 把授权来源变成可审阅脚本及可编辑播客音轨 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-08.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-09 | 理解品牌评估变化、置信和覆盖情况 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-09.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-10 | 按严重性、扩散和时效处理有证据的品牌风险 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-10.md#intelligent-ui-逐屏采用项2026-10-08) |
| BMP-11 | 在口径一致时比较品牌基准 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/BMP-11.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-01 | 查看商业运营活动并检视单个事件 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-01.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-02 | 浏览商业主体目录与已核实关联 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-02.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-03 | 查看监测变化、平台lane并阅读一条信号 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-03.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-04 | 理解事件先后和证实的关系边而不推因果 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-04.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-05 | 寻找真实变化日期并查看当日样本 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-05.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-06 | 分拣反馈并读原始措辞 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-06.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-07 | 解读有定义指标在特定窗口内的变化 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-07.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-08 | 追踪真实Case到Outcome并区分复用知识 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-08.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-09 | 区分风险依据、决策状态、审批和实际动作 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-09.md#intelligent-ui-逐屏采用项2026-10-08) |
| CTH-10 | 创建或重开有来源的运营简报并检查结论 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/CTH-10.md#intelligent-ui-逐屏采用项2026-10-08) |
| SH-01 | 发现共享能力并进入当前研究/创作/媒体工作 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SH-01.md#intelligent-ui-逐屏采用项2026-10-08) |
| SH-02 | 检索并阅读同一组有来源研究材料 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SH-02.md#intelligent-ui-逐屏采用项2026-10-08) |
| SH-03 | 理解Canonical指标定义、成熟度和Source链 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SH-03.md#intelligent-ui-逐屏采用项2026-10-08) |
| SH-04 | 重开真实Artifact、比较版本并回到原Task | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SH-04.md#intelligent-ui-逐屏采用项2026-10-08) |
| SH-05 | 审阅学习资产的样本、方法、反例和生命周期 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SH-05.md#intelligent-ui-逐屏采用项2026-10-08) |
| SH-06 | 从任务/通知/警报返回原业务工作 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SH-06.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-01 | 读RuntimeGuardian状态和Worker/DLQ保护指标 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-01.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-02 | 查Collector各平台lane和进入Evidence的真实状态 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-02.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-03 | 核对schema、integrity、readability与Truth chain层次 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-03.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-04 | 安全理解允许范围和审计可用性 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-04.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-05 | 调整设备外观并返回相同工作状态 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-05.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-06 | 在原任务授权范围内读取和操作受控来源，完成必要的验证并返回原任务 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-06.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-07 | 检查实际Evaluation gate证据和未完成项 | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-07.md#intelligent-ui-逐屏采用项2026-10-08) |
| SYS-08 | 查看脱敏日志目录和可追溯Trace | [打开逐屏规范](../../../../contracts/experience/screen-specifications/SYS-08.md#intelligent-ui-逐屏采用项2026-10-08) |

### 跨屏闭环要求

- **同一任务连续性：** 用户从研究进入分析、业务决策或创作，继续使用原 Task/Brief/Actor/Scope/时间窗/预算约束、Source/Evidence及其版本；不要要求重复解释目标、重选同一批材料或重核同一来源。
- **有影响的变化：** 来源、范围、预算或内容变化时，显示受影响对象及保留项；只有经用户明确采用的新版本才成为当前版本，父版本、变更原因与回滚路径仍可查。
- **智能呈现的权力边界：** 模型可以提出有依据且可检查、编辑、拒绝的呈现/行动建议；当前Owner、服务端Permission和Effect Fence继续决定数据及执行，建议本身不能成为授权或成功回执。
- **四端与视觉：** Public Website讲已验证公开能力或明确标记示例；Web Workspace/Desktop承载并读和精细编辑；Mobile以任务聚焦、触控、返回和恢复适配。四端保持同一业务语义、各自适配。二维手绘水彩/版画可丰富用色但不滥用；人物根据用户的具体脚本描述原创呈现，不复制参考照片人物，也不做3D AI质感。
- **状态与验收：** unknown/not collected/stale/partial/denied/error/blocked分别表达；只运行真实绑定的动作。本次只是蓝图/文字草图/ScreenSpec补充，不改变已有 review status，不代表DESIGN_READY、实现、运行、四端验收或USER_VERIFIED。

### 2026-10-08 前端审计与工具维护增补

采用用户当时前端审计中的可编辑设计→屏幕规范→真实源码→验收证据链，细则归 Experience §38 及原44份ScreenSpec/README。保持原 Blueprint、Owner、DESIGN_EXPLORATION→DESIGN_READY→IMPLEMENTED→ACCEPTED，不建立第二设计真相。Figma实际文件/节点/版本在该日期 NOT_VERIFIED；不以本地无 .fig 推断云端无工程。此 dated review 不记录或决定当前窗口的派发、开工、暂停或恢复；本稿不是实时调度来源。

工具维护保护现有模型/effort/tier、登录方式、权限、网络/代理及会话；只更新核实的稳定兼容版本，开发插件不变成产品依赖。需要中断桌面/会话、重启、扩大权限或新增登录/费用时等待精确批准。既有未发布源代码、私有配置及生产DB保持原边界。

### 2026-10-08 两份成熟能力增补的审阅落点

本审阅草图继续从唯一Product Architecture和Experience§38派生，不成为第二蓝图。该日期的44屏智能交互输入复用，并对SH-01视频制作与BMP-08播客的真实编辑/播放/波形/录音/保存重开动线作了细化（见原44屏文字草图对应增补）。其他J1–J8基础操作与序境特色按Real Delivery Overlay双层验收，GPT/Apple/Tesla启发的任务适配、反馈、可撤回和偏好恢复适用于原有屏幕。新组件仅条件评估，Figma/美术稿未因本文更新自动完成。本段记录历史审阅范围，不定义当前窗口派发或实施状态。

## 2026-10-08 逐步呈现动线补充（文字设计输入）

用户提交同一目标→先出现可信摘要/已核实比较项→原位置逐块补充来源、分析与可操作参数→用户调整时保留输入与选区→只更新相关内容→明确采用保存版本→关闭重开。屏幕不整体闪烁/抢焦点/强制滚动，阶段性内容及未完成处清楚分层；日期未知与缺数值“—”保留维度和原因。图表/计算器/时间轴/阅读器或纯文本按本屏任务选，不画第二套通用模板。

这些是原草图的动线说明，未重绘美术资产、未创建Figma版本、未自动晋升DESIGN_READY。准确规则唯一归Experience §38；适用全部既有屏幕，复杂视频/播客仍使用完整编辑工作区。
