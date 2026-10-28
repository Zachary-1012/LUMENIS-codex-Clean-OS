# BMP-06 — 内容生产台

```yaml
screen_id: BMP-06
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-023]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to move an approved content idea through drafting, review and authorized release while retaining version and source context.
- BMP owns the brand/market workflow. A current BrandFocus or explicitly granted global range, actor read access, content lineage and action-specific approval are required before content is shown or released.
- Scope modes are explicit: an authorized `GLOBAL_ALL` response may show a global brand collection with verified lineage; `FOCUS` must match the selected BrandFocus. One mode is never presented as the other.
- Current backend gap `BACKEND-GAP-023` is unscoped and cannot supply a verified brand read. The implementation therefore renders only a scope guard until that contract exists.
- Out of scope: inferring a brand from a source record, showing product-wide content counts, directly publishing, or treating an AI draft as approved content.

## 2. Route, entry, exit and return

- Read callable: `LumenisCoreClient.screen('BMP-06')`, corresponding to `/api/experience/screen/BMP-06`.
- Required response envelope: `ok`, `screen`, `bound`, `source`, `focus_context`, `binding`, `truth`, and allowlisted `assets`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Exit and restoration remain Shell-owned. The page does not invent content deep links or a local brand selector.
- Current backend response is not sufficient for a real delivery loop; no content is displayed as brand truth until the binding is verified.

## 3. Verified data and callable bindings

| Field/action | Owner | Current contract | Missing behavior | Binding |
| --- | --- | --- | --- | --- |
| Asset title, kind, state | BMP Content | `assets[].title`, `kind`, `state` | Hide records without verified brand scope and lineage | BACKEND-GAP-023 |
| Version/review status | BMP Content | `version`, `review_state`, `approval_state` | Keep review and release distinct | BACKEND-GAP-023 |
| Source relationship | Shared source/content owner | `evidence_ref` is required as a gate, never shown as an implementation identifier | Withhold asset if absent | BACKEND-GAP-023 |
| New content | BMP Content | `content:draft` action contract | Save a local content draft only; do not write | BACKEND-GAP-023 |
| Submit review | BMP Content | `content:submit` action contract | Save a local review-request draft only; do not submit | BACKEND-GAP-023 |
| Publish | BMP Content + effect fence | `content:publish`, high-risk confirmation | Save a local publishing-request draft only; no effect without the canonical executor and result | BACKEND-GAP-023 |

## 4. State and recovery matrix

| State | User-visible behavior | Recovery |
| --- | --- | --- |
| Loading | Keep the production task identity and announce loading | Wait or refresh |
| Not collected | Explain that no source-backed content is ready | Refresh; do not show zero assets |
| Scope blocked / denied | Explain that the selected brand cannot be confirmed | Return through Shell context or retry |
| Offline / error | Explain that content production is temporarily unavailable | Retry without stale business records |
| Ready | Show only verified assets; review and publish remain separate | Refresh |
| Action staged | Confirm a local request draft was saved; nothing was written or published | Wait for the canonical executor, approval and action result |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-06)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：内容生产台 · 视频剪辑（规划 §14 E1–E11、G183/G64/G170/G171）


**4. States**
空 / 探测中 / 转写中 / 模型不可用（手动剪辑可用）/ 提议待确认 / 渲染中（可取消）/ 渲染失败（原因+重试）/ 版权未知 / 数据缺失 / 权限不足。

**9. Acceptance**
- 素材 100% 有哈希/时长/时基；VFR 标注；序列化无绝对路径。
- 成片可播放、可重开；工程交换先预检，取消不改项目。
- 产品演示片必须来自真实操作录屏；封面文案兑现正文；AI 素材标注。

**增补（2026-10-14）**
- 演示片模式（E10）：镜头表每行写「操作→状态→结果」；短版按动作闭环自动建议切点。
- 导出前预检条：逐项损失列表，取消即不改项目。

### Existing contract — Purpose-built desktop composition

- Use an editorial production board with six distinct lifecycle swimlanes: brief, draft, review, approved, scheduled and released. A version inspector sits beside the board for the selected asset.
- The primary question is “what is the next authorized production step for this brand asset?” The page is not a KPI dashboard and does not reuse a generic card grid.
- A compact action rail exposes “save ... draft” controls with the matching approval state; each control visibly remains local and non-executing.
- At narrow widths the board becomes a single production queue followed by the selected version detail; it is not a shrunken desktop board.



### 三语状态文案

| Key | zh-CN | en | ko |
|---|---|---|---|
| loading | 加载中 | Loading | 불러오는 중 |
| missing | 数据缺失 | Data unavailable | 데이터 없음 |
| unavailable | 暂不可用 | Currently unavailable | 현재 사용할 수 없음 |
| denied | 无权执行此操作 | This action is not permitted | 이 작업 권한이 없습니다 |
| retry | 重试 | Retry | 다시 시도 |
| cancel | 取消 | Cancel | 취소 |
| save | 保存 | Save | 저장 |
| revise | 修订 | Revise | 수정 |
| reopen | 重新打开 | Reopen | 다시 열기 |
| recover | 恢复 | Recover | 복구 |
| return | 返回原任务 | Return to task | 원래 작업으로 돌아가기 |

全部新增标签、说明、确认及读屏名称须沿现有三语键实现；上表仅通用状态，不证明全产品翻译/运行完成。逐屏验收覆盖 zh-CN/en/ko、200%字号、键盘/读屏和减少动态。

## 5A. Web Workspace composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：内容生产台 · 视频剪辑（规划 §14 E1–E11、G183/G64/G170/G171）

Web：稿件、预览、时间线按宽度重组；浏览器文件选择/上传与草稿分别呈现进度，支持刷新后恢复已保存工程，不虚报未上传素材可用。 大文件上传分片续传。


## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：内容生产台 · 视频剪辑（规划 §14 E1–E11、G183/G64/G170/G171）



### Existing contract — Actions, authorization and effects

- `content:draft`: save a local draft of the request; no content is created.
- `content:submit`: save a local review-request draft; no review is submitted.
- `content:publish`: save a local publishing-request draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no publish effect is attempted or reported.

## 7. Accessibility and localization

- Keyboard order is heading, scope context, lifecycle queue, selected version, then action rail. Each lane has a meaningful label.
- Screen-reader copy describes brand content status and next business step, not implementation diagnostics.
- Table/queue content has a linear mobile equivalent and action state announcements.
- Integration key inventory: `screen.BMP-06`, `bmp06.subtitle`, `bmp06.lane.*`, `bmp06.asset.*`, `bmp06.action.*`, `bmp06.state.*`, `bmp06.recovery.*` for `zh-CN`, `en`, and `ko`.

## 8. Executable acceptance

- An unscoped backend payload renders the scope guard and none of its asset titles, states or counts.
- A verified BrandFocus payload renders the six-lane workflow and preserves distinct draft/review/approval/release states.
- Missing lineage removes only the affected asset; it never becomes an empty success or zero count.
- A denied publish action remains blocked; an enabled local-draft action shows a non-executed state and never claims a successful write or publish.
- Desktop, compact and mobile widths expose the same state semantics with the purpose-built compositions above.

Current decision: `IMPLEMENTED / BLOCKED_FOR_BRAND_SCOPE`; backend owner must provide actor-to-BrandFocus read and action result contracts before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 把授权素材和内容想法推进为可审阅版本。
- **屏幕专属呈现：** Draft→Review→Approved→Delivered专属编辑流程，来源/rights贴近正文
- **来源、范围与版本连续性：** 继承同Brief/Evidence/品牌/语言；修改保存子版本和受影响片段
- **四端差异：** Web/Desktop正文与证据并读；Mobile聚焦待审与修订；官网不编辑内部稿件
- **失败与恢复：** rights未知/授权不足时阻止对应动作，离开保留草稿
- **补充验收：** 真实brief到修订子版本再重开；AI草稿不标批准或已发布。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。


## 2026-10-18 完整工作面细化：迁移、业务与内容模式

保留原状态/Owner/接口和完整终态；本文补足视觉交互，不宣称已接通或已验收。

### 内容模式候选与有据测量

创作工作中“整理为可复用模式”进入SH-05资产区，不替代“空白原创”入口。宽屏左列候选/已采用/退役模式，中列来源段落、适用条件、排除条件与模式结构，右列评价证据；选模式只形成当前作品的应用预览，原稿与建议稿并读，确认后保存实际应用痕迹及父版本。可忽略模式继续自由创作，取消不改变原稿；有声纹、授权素材等具体权利条件时沿原SourceUse，不因模式已保存视为通用许可。
测量页从模式详情进入：上方锁定基线稿与候选稿及版本，中间列真实要求短语覆盖等工程指标，下方列缺失独立留出任务/人工结果证据。标题明确“稿件工程测量”，不以覆盖增量画质量/商业提升绿箭头。重算按钮先核当前稿与原评价引用，旧稿/来源失效提示评价过期；批准撤回后既有应用历史仍可看，但新复用禁用并解释原因。退休确认列适用模式与真实已知影响，恢复需有效历史与权限，不能从任意备份复活。
规则建议在同一资产详情独立栏显示建议、来源任务、待审状态和明确应用范围；学习关闭仍保普通确定性创作。错误、未准备评价、缺权利与版本冲突分区，保人工输入并回当前作品；恢复需真实Owner读回。Web可按作品深链回原选区，Windows/macOS并读基线/候选并核冷开作品版本，iOS用模式摘要→应用前后逐段→确认/取消，评价详情可折叠但缺证据不隐藏；官网用获准例子解释可复用结构，不能把模板快路宣传成原创质量证明。
界面AIGC可按当前创作目标建议模式与稿件对照构图/局部动作，模式选择和应用由用户明确决定；保人工锁定段落，建议仅局部更新，可撤销布局或应用，生成不可用仍可写/读/比/保存。价值是减少重复组织同时保原创判断与可追溯应用。


### 全项具体工作合同：实验、概率校准和预测区间

增加实验启用开关与预登记规则的真实字段，不提供自动分发成功控件。校准/区间的分集不足、重复ID/已知泄漏、未知训练来源、无模型/依赖不可用、陈旧版本各保真实状态。撤销观察草稿不删除已提交观察；重复提交按原Owner幂等，取消后重开同版数据。验收无观察、0成功、有重复、改版后旧样本隔离、每集不足20、校准与区间结果不串用、断线后不重复计算/分发。

效果工作面三种任务按当前问题出现：变体比较表＋区间；可靠性曲线＋分箱表；预测值/区间＋保留集覆盖。顶部固定版本/窗口/观察出处，右侧仅展示当前任务的样本与假设检查；“补观察、比较版本、保留/停止、保存评价”靠近相应结果。Web/Desktop保同字段并列；iOS先每版/每组结论和缺口，点开语义表；官网只用已核案例。UI自身AIGC在三种原生构图中提出局部适配，不替用户改停止规则、不绘制假区间，不挤走正在填写的观察。

具体操作与恢复：实验从选定作品变体与真实观察进入：显示每版成功数/试验数、分配单位、观察窗口、用户预先声明的最少观察数及停止概率；“建议下一观察变体”是可选计算，开启不分发流量。结果列后验区间、停止建议及未满足条件；缺观察与真实0不同，改标题/封面后新建变体版本。
概率检查单独显示校准集/测试集样本数、标签来源、模型版本与分离声明，可靠性曲线与同源分箱表联动，ECE/Brier只说明此保留集上的经验校准；未独立验证训练隔离不得写概率已可信或模型已可上线。预测区间另用真实预测/观测和独立校准/测试集，显示目标覆盖、实际测试覆盖、样本量与宽度，不把校准曲线画成个体预测区间。用户面向“检查预测是否可靠/查看区间”操作，方法名仅在详情。


### 全项具体工作合同：参考视频测量、峰值与接触表

将草图旧“全帧数/已看帧数”改为上述四状态，现测量输出不具人工已读证明时保持未记录。取消只停分析与本任务临时文件，原片与已存审阅留存；source hash改变阻断旧坐标应用。验收全解码但仅抽样未审、峰值并非镜头、VFR PTS、120秒/7200帧边界、接触表分页、取消/失败及返回原格。

在原参考学习面板内，顶部四条覆盖状态；中部接触表分页＋原片播放器，右侧峰值候选/测量列。当前格标源PTS/实际帧号，工具为“打开原尺寸帧、回原片、标已核区间、记录镜头/交互观察、保存分析”。Desktop/Web接触表与播放器并读，iOS一次一格可切前后与返回页；官网仅真实例。UI适配峰值密集区建议放大相邻帧对照，但不替用户记已核、不自动选剪点。

具体操作与恢复：参考片检查明确分开“实际解码帧数”“测量覆盖”“抽样接触表”“人工已核范围”。当前有界测量最长120秒/7200帧、分析像素至160×90；0.5秒接触表为抽样，每页24格，不能从解码完成推定人工逐帧看完。页面提供亮度差、变化面积、边缘密度同源曲线及峰值候选表，点候选回真实原件PTS；候选不是确认镜头或语义理解。人工可记接受/排除理由和已核区间，读到多少写多少。超范围/时基未知/旋转或多视频流不支持/截断失败明确说明并保原素材，不自动裁掉超限段后称全片。


### 全项具体工作合同：转录与逐词/填充词/静音提议

绑定transcript artifact/hash、source hash、timeline revision、音轨及选中word IDs；精确审批另由原EDL/Permission owner核验。转录不可用保手工稿和剪辑；取消不提交新稿，恢复核同一音频。验收填充词误匹配、零时长/未对齐词、选流变化、静音穿词、边距、旧转录哈希、取消与迟到回调、采用/撤销/保存重开保持实际音画边界。

词稿保持主面，候选在右侧“待删”清单；点击候选只定位原音频和受影响轨道，底部固定“试听原段/试听提议、排除、采用所选、取消”。填充词栏与静音栏分开，未知词时用文字状态而非补时码。Desktop/Web多轨同步；iOS句/候选单项审阅与允许轻剪，精剪续接同版；官网只演示真实链。UI适配只把当前候选与上下文并读，不自动删词，不挤走当前选词/播放头。

具体操作与恢复：转录入口先选实际音轨、语言提示和已可用运行时，显示规范化音频与原PTS映射；转录完成只是派生词稿，不代表说话人分离、全语种质量或正式听审。源转录和已渲染工程转录各标输入媒体/工程版本，不能混用时间码。普通改字、仅删字幕、逐词删音视频三种动作分开。
逐词删除逐条给原词/起止/实际删去区间；填充词候选允许编辑本次词表、检查匹配词及排除；静音候选显示阈值/实际静音区间/保留边距及被影响片段。试听原版/提议版后明确选择采用范围；无词级对齐、跨词边界、过期转录或原稿变更拒绝采用并保用户选择。


### 全项具体工作合同：封面、B-roll及音频可视包装

取消候选生成/插入预览不改原Timeline，采用后原父版仍可重开；源变/字体缺失/文本溢出/无匹配/权利未知/复杂轨道拒绝/格式验证失败各有具体说明。验收真实取帧覆盖、文案子串但语义未核、零相似度、顺插导致时长增加、字幕或音轨存在时不误允、音频选段边界、取消/重开与字形检查。

封面台用候选图组＋当前正文与三要素输入，候选边注时点/方法/覆盖；B-roll用素材列表＋标注/命中词＋前后时间线对照，清楚写“总时长增加…，后续音画一起后移”；音频包装用选段播放器、起止控件、标题/引语和实际波形预览，再选保存/导出。Desktop/Web并读，iOS逐候选与单片段审阅；官网仅有证输出。UI可根据候选数/屏宽自动排比较构图，内容封面或波形成片本身不计UI AIGC；布局提议不变所选片段。

具体操作与恢复：封面候选展示真实取帧时点、场景变化或均匀时间候选来源及测量覆盖，三要素文案逐项可编辑并对照正文；精确子串匹配仅是文字检查，仍需人工确认兑现，不能称语义最佳封面或CTR预测。B-roll清单显示用户素材标注、命中词和词项相似度，明确未做视觉语义核验且不自动获权、不联网找片。
当前B-roll插入预览仅支持无叠层单视频轨的静音顺插：先显示插入位置、源入/出点、增加时长及后移的原片和原音频；它不是盖在旁白上的覆盖画面。复杂工程不支持时指出原因并保完整叠层目标OPEN。音频图/引语卡从用户选定0.2–180秒片段、标题、引语和真实音轨产生，波形来自实际音频；引语只按用户文字显示，不冒转录已核。


### 全项具体工作合同：多平台草稿与版本差异

状态区分DRAFT、TRANSLATION_UNAVAILABLE、NEEDS_EDIT、HUMAN_PENDING及未发布；旧hash编辑冲突保本地稿并提供重读比较，不能强覆。验收四稿型、平台/语言组合、缺译文、长度告警不截断、源引文错位、单变体修订不碰其余、完整改稿重新待审、保存冲突/取消和精确版本重开。

左列平台×稿型×语言变体，中间当前可编辑正文，右侧事实/引用/人工待核；切“比较修改”后中间变成旧/新对照，当前语言和版本固定可见。Web/Desktop可并读两版，iOS逐变体编辑与差异抽屉；官网展示同事实有据样例。UI自身适配依据用户正编辑还是审差异选择单稿或对照构图，不改正文、不自动翻译或采用。

具体操作与恢复：同事实草稿包按公关稿、媒体提案、文章、社媒稿及目标平台/内容语言分别列变体。事实墙中每条事实、引语和语言文本保来源；当前确定性重排不等原创增强或自动翻译。缺目标语言文本显示缺哪条事实的译文，不静默回退别的语言。平台长度提示保完整正文，不截字，不把保守字符数当平台已合规。
比较修订时并列所选变体旧稿/新稿和来源绑定，显示“语义差异尚未评估”；用户只改所选版本，整段替换后该版内容重新待核，不能继承旧引用已验证标签。保存/重开沿同一父包和实际版本，生成/保存/导出均不发布。


### 全项具体工作合同：裁切、字幕样式、精确审批与交换

保原格式/层叠/时基完整目标；当前支持枚举与未接线动作如实列。状态：裁切越界、样式越界/字形缺失、父版过期/批准过期、损失阻断/未知、素材映射缺失、导出验证失败；取消保持父版，重试先读原回执。验收3:4等实际枚举与规划预设一致显示、样式边界、引用文本转义、批准后改版拒绝、各交换格式损失、分数帧率、导入重链及保存重开。

预览旁裁切/字幕检查器显示实际控件；审批用“本次将改…”差异列表与旧/新试听；交换面为目标格式＋损失清单＋受影响时间线定位，导入后显示待重链素材而非空成功。Desktop/Web可并读，iOS安全区/字幕/批准差异审阅与允许轻改，复杂交换续接同版；官网只演示已验证格式。UI适配把当前裁切、字幕、审批或损失对象置于前景，播放头与文字不因布局变化移动；生成字幕内容不计UI AIGC。

具体操作与恢复：画幅检查器保原画与裁切框，用户拖拽或输入x/y/宽/高并看安全区；当前裁切是用户选择的固定区域，不能冒已自动追踪主体。字幕样式使用当前支持的字号16–96、前/背景色、透明度、行长/行数、顶部/底部和安全边距，字体/glyph不支持明确拒绝；样式预览与实际烧录结果分别验，ASS导出与SRT/VTT能保留的格式不同。
剪辑提议审批展示精确父工程版本、提议内容及受影响轨道；批准/拒绝/取消各有真实对象，父版或提议变化后原批准失效，用户无须手填hash。工程交换先选OTIO/FCPXML/CMX3600与实际时基，逐clip列保留/量化/烘焙/不支持/未知及重链映射；确认非阻断损失才导出新版本，导入交换文件仍需实际媒体映射和新工程读回，不以XML合法宣称宿主兼容。


### 全项具体工作合同：真实波形、显式母带/降噪与交付编码

状态区分源pre-mix已测、范围外未测、缺工具/音轨、线性目标不可行、降噪未开启、处理候选待采用、编码完成但校验失败。取消只当前处理，原音频/已保存输出不变；继续前核输入版本。验收60秒范围/多流选流、静音、不可行真峰、降噪主动启用与参数边界、AB停止/切版、重复处理不叠加、编码后重测失败、取消/冷开。完整长节目制作目标保留，局部波形/600秒分析不是全节目验收。

音轨顶栏选择“原源/处理候选/母带/交付副本”，真实波形区标源/范围；右侧响度检查器有目标、输入/输出值、试听原版/处理版及采用。降噪独立开关和两参数不与响度混成一键美化。交付区按编码→校验→文件读回逐步列结果。Desktop/Web并读检查器与音轨；iOS试听和已支持参数审阅，未实现处理明确续接；官网有证样例。UI适配因当前在听审或看失败而展开相应检查器，不能改变音量/参数或播放头。

具体操作与恢复：波形标实际源媒体、音轨和测量区间，当前PCM波形查询最多60秒；源pre-mix波形不冒最终混音或整节目已测。超出当前测量范围明示未测，保真实播放器和人工定位，不以装饰波形填满。
母带处理需用户明确选择当前支持的-16/-14/-23 LUFS目标，显示处理前后实测响度/真峰、目标与线性可行性；静音不可测、动态范围或真峰不允许线性达到目标时给具体失败原因，不暗改动态处理。FFT降噪单独默认关闭，启用后可调降噪量3–18dB和噪声底-80至-20dB，先AB试听，声学测量变化不等主观质量提高。原声、降噪、母带保持可辨版本，不重复叠增益。
MP3/M4A交付副本显示编码、全解码校验、时长、响度/真峰和文件读回各阶段；母带不被覆盖。编码成功但解码/峰值失败仍未可交付，保原母带和已存工程。


### 全项具体工作合同：自由原稿、逐主张九维审校与完整提案

明确稿件保存成功、人工审阅READY、独立事实核实与发布许可四种状态。主张坐标以原文版本/单位核，缺依据不能标有支持；九维全量字段与原因必须真实，role无权不提交，正文变化保旧审阅历史并标待重审。验证无模型空白写作、父版采用/过期冲突、漏主张、九维缺项/风险失败、保存中继续输入、10段/自由目录重排、取消与冷开；十段方案生成与八段分析目录分别保结构，检验所选十段/自由成稿实际进入编辑、保存及Word导出且读回一致；未替换预算X%/时长X周等占位逐项可见，不误作实际计划。当前状态为“双结构接线/内容质量待验”，不能靠任一目录长度测试裁定完成或改原需求。

成果文稿主区是正文，左侧完整可编辑目录，右侧按需切事实主张/九维审校/版本。点击主张在正文与原文依据同时定位，状态为文字+图标；审校填写不挤走段落，底部显示本版未核项和保存/提交审阅。提案目录显示完整10段与每段目的/事实/预算，用户可自由改结构，单页任务明确。Desktop/Web并读；iOS原稿轻改、单主张/单维审校及目录返回，复杂版式续接同稿；官网真实例。UI AIGC仅按写作/核实/比较任务重组原生编辑区，不能用生成正文或自动审校代替UI适配。

具体操作与恢复：用户可空白或自写稿进入并保存，不依赖模型、模板、模式采用或事实审批。父稿重用以准确版本预览并显式“采用为新修订”；遗留元数据保“历史上下文未核”，不补造旧Owner已执行证明。
审阅面沿正文选区逐条列事实主张及其准确原文坐标、依据定位和人工结论：有人工依据/需修改/未核，并要求审阅者确认已枚举本稿事实主张。九维为平台、时令、品牌、情绪一致、视觉叙事、题目、搜索适配、商业性和风险；每维通过/不通过/未核及理由，不用总勾或自动模板PASS。修改正文、主张或来源后旧审阅失效，普通写作/保存仍可继续；风险未过阻断相应交付而不清稿。
原G104的10段比稿骨架、4A叙事弧、One Slide One Job及三档预算完整保留。campaign_plan已有十段生成结构：Brief理解与重构、市场与消费者洞察、核心策略、Big Idea、创意落地、整合传播规划、媒介与资源、效果衡量、执行节奏、风险与合规；pitch_parser的八段是另一分析目录，不能误写产品只有八段或强改其目录。前端明确当前打开“十段方案骨架/方案拆解分析/用户自由成稿”哪种对象，可读、编辑、重排真实章节并预览实际导出正文。X%预算、X周时长和泛化提示以待补字段提示，用户补真实假设、依据及预算档后才可作为对应交付内容。十段生成、可编辑正文和Word导出是否端到端接通、占位是否被替换、内容能否形成完整提案继续标“双结构接线/内容质量待验”，不因十段数组或八段分析测试就升为完成。


### 原要求具体工作合同：成果研究采用、ApplicationTrace与生产准入分账

每项成果在版本/依据详情中提供“本版研究与制作依据”。先显示真实研究采用结论ADOPT/ADAPT/DEFER/REJECT及其人工/Owner出处、理由、未解决问题和具体应用位置；没有记录显示未记录，不由模型补一个采用决定。再按本版ApplicationTrace逐项列learning_asset、pattern、evidence、model_version、prompt_contract_version及准确版本，未使用、未记录和不可读取分开。用户从痕迹返回原件/方法和作品选区，不输入内部ID来完成普通工作。
研究资产的E0 Candidate→E1→E2→E3 Tested→E4 Validated及Production admitted依据原准入Owner原样投影；E1/E2的说明须来自原合同，不临时重定义。该研究阶段与ADOPT研究决定、本地RAW/REVIEWED/VALIDATED/ADOPTED候选状态、交接ACK分列，一者不自动推进另一者。撤回/更版时标受影响成果，旧版仍按当前权限读回；无准入回执不显示已生产采用。

SH-04当前成果右侧“版本与依据”增加可收起的研究采用行，点开后上部采用决定/理由/未知，中部五项制作血缘，底部源→应用段落的已知关系及返回。SH-05所选资产检查器并列“研究验证阶段”“本地参考状态”“生产准入”三条有文字的状态，不画一条自动进度跑道。Web/Windows/macOS并读成果和依据，iOS先成果后单层依据Sheet，保原选区；官网仅有权公开案例。UI自身AIGC可依据真实痕迹组织对读/局部关系图，允许锁定/撤销/简洁；不生成采用理由、未知版本或准入绿灯。

增加逐字段缺失/未使用/撤回/当前不可读、旧成果与新来源版不同的状态。查看/关闭详情无副作用；改变采用记录须用原Owner明确动作/精确版本，未绑定不造控件。验五字段不同版本、模型未参与、旧prompt合同、来源撤回、local ADOPTED但E4/Production未知、取消及冷开同版；研究卡存在不等G7/G11/G91运行完成。


### 原要求具体工作合同：类型化结构、八角标题与可编辑节奏

内容类型辅助提供种草、情绪、知识、活动、短视频及自由结构入口；选择只准备可编辑大纲，不自动生成或发布。按原结构展示Hook→场景→细节→判断→轻CTA，各段可删除、重排、改名与手写；短视频节奏先给0–3/3–10/10–25/25–40/40–60秒参考格，用户可改真实时长/目的，超长或空格给建议而非硬门。
标题工具按原Owner的八种角度分别列候选、表达意图、对应正文依据和采用理由；没有八类准确名称/版本时写该工具定义待接线，不用随造八个标题冒完整角度覆盖。选择一项仅替换当前标题，旧标题可撤销，正文变化使兑现检查重新待核。

稿件左侧“结构”列五段可拖/键盘重排，中心正文，右侧“标题角度”八个带真实角度名的候选行；分镜模式把节奏格放正文下方，每格有起止、任务和对应镜头，不与实际剪辑时间轴混同。Web/Windows/macOS并读，窄Web/iOS一段或一候选审阅并保父稿返回；官网展示可改结构的真实例。UI自身AIGC可随文章/分镜任务重排结构和候选对照，不生成式UI即自动采用文案；用户锁段与固定布局可用。

验取消生成保手稿、缺Brief只阻生成、八类缺定义、两角度同义重复、标题不兑现、修改节奏不改现有素材时基、章节键盘移动/撤销、未选候选不改稿、保存版本及重开；八角标题不是八种平台，新增四稿型不替代本原项。


### 原要求具体工作合同：Persona六字段、角色任务和四类回复

在当前账号/品牌或独立项目上下文中编辑Persona：受众、内容支柱、口吻、禁区、商业边界、CTA风格六项分别有原值、用户改动、来源/假设与版本；每条Brief明确采用哪一版。KOS/KOL/KOC/UGC为当前任务角色与适用约束，不因账号昵称或粉丝数自动赋类。修改Persona先列受影响未交付作品与已批准回复，用户选择采用范围，不改已发历史。
评论回复沿原Owner四类定义逐项显示实际类别名、原评论及必要上文、对应Persona约束和待审回复；四类定义尚缺时保持待接线，不临时换一套类型。Risk命中指出原文位置和原因并转人工，内容仍可手改保存，不能暗发或一键跳过人审。

BMP-06上下文边栏用六项折叠表单，顶部显示Persona版本和本Brief采用状态；BMP-05评论区为原评论→类别→回复草稿→风险与所用Persona的纵向阅读，主动作保存草稿/提交既有人工审阅。Web/Windows/macOS原评论与回复并读，iOS一条评论/回复与Persona Sheet，返回保未发稿；官网只授权去敏例。智能UI可按实际冲突把相关Persona字段与句子并读，不推断个人属性、不改角色/风险或自动代发。

状态区分Persona未保存、Brief未采用新版、角色未知、类别定义缺失、待人工、拒绝、草稿保存和外部未发送。当前没有真实回复executor时只给草稿动作；取消保原Persona/回复，旧审阅不能跟随改稿。验四角色、四类别、六字段完整、跨品牌拒绝、Risk转人工、改版影响、同一评论重复请求和冷开未发稿。


### 原要求具体工作合同：五维负样本复盘与BIL机制覆盖

复盘从准确作品/实验版本及允许观测进入，可按Topic、Hook、Persona、Template、CTA五维切换或并看；同时保普通、低表现、失败与高表现样本，缺样本类型明确提示，不能只显示胜出者。每条案例随行保原URL、日期、市场、平台、方法、分母和证据等级，分开原帖可核数据、部分访谈、行业假设、二手线索；生成例永不进入真实案例池。
BIL选例按机制覆盖展开品牌健康、社媒热度、UGC、触达质量、文化/购买意图、品牌DNA、本地执行、门店体验、增长、创作者归因、AI发现/传统曝光各自证据，不能合为品牌排行榜。用户可记录机制假设、反例、适用/不适用条件并采用为待验证Brief；旧案例正文/标签/日期/指标不自动复制到新ContentContext。

上部固定问题、样本窗与作品版，中部五维切片对照表，左侧样本类型及证据等级筛选，右侧所选案例原件/分母/机制笔记。BIL以覆盖矩阵显示哪些问题有何类证据，空格写未知；选择用于新Brief时预览“保留的机制/要重新核的事实”。Web/Windows/macOS并看正负例，iOS逐案例同字段对照，官网只给可核样例不排名。UI可按问题生成原创对照布局和缺口说明，不能挑选只剩好例、编分母或自动作因果结论；筛选和布局可锁定/复原。

筛选只改变阅读集合，不删失败记录；采用产生新任务引用和人工假设，不能自动晋升学习资产。验缺失败样本、相同标题不同版本、跨平台指标不可比、访谈不等原始数、生成例排除、风险因果措辞、取消采用和原筛选重开。新增统计区间和九维审阅不顶替本五维复盘要求。


### 原要求具体工作合同：可选表达机制与完整反模板质检

在原稿的可选风格工具中按既有Owner定义列八类表达机制与高奢克制六法则，显示实际名称、适用/禁用条件及所选稿段的候选差异。缺准确方法定义或版本时说明待接线，不拼六条常识冒原方法。用户可不选风格继续手写；应用只改所选段，保原意、事实及人工锁定内容。
保存/导出前可查看原六项质检：标题是否兑现、具体细节、未证实事实/夸大、语气一致、伪创新、同批重复。逐项定位受影响标题/句子或同批另一稿，显示依据、未知、人工处理与理由；普通保存保可用，不把未核全部等同禁止写作，实际发布/导出限制按原风险Owner。九维ContentReview与本六项清单相连但不互相替代。

正文右侧“表达/质检”切换，风格先展示选择与局部旧新差异；质检六行有状态文字与定位，重复项可并读同批准确版本，不只给一总分。Web/Windows/macOS审稿与依据并读，iOS一次一问题→原句→手改/保留理由→返回；官网只示有证问题。UI可按真正未核问题组织检查顺序和差异密度，不能替用户全勾通过、自动改事实或清掉未处理项；固定清单/无AI继续路径保留。

验八/六方法定义不足、拒绝建议不改正文、同义换词仍重复、不同批次不误判、标题/正文改版使旧质检陈旧、人工理由保留、风险失败只阻对应效果、取消与保存期间继续编辑。未接线的风格生成和语义质检标OPEN，不从现有字符重复检查推定全项质量。


### 原要求具体工作合同：Campaign-Series-Post结构与版本化选择依据

内容项目保Campaign→Series→Post父子导航，独立手稿可不挂Campaign先写，只有需要生成时检查当前Brief必需输入。选Post显示Title、Hook、Body、CTA、Hashtags、Visual Brief六项可编辑对象，字段缺失标未填；不把整个产线塞进一个不可检查Prompt。上层目标/人群/预算改动先列真实受影响Series/Post，人工选择采用，不覆盖其他稿。
模式/模板选择说明以原Owner实际计算拆开weighted performance、context fit、risk及权重配置版本，未知样本/风险不造分。允许用户改实际开放的业务偏好并生成新候选版本，默认不要求读算法参数。每版记录输入、模型/提示合同、模板、校验、人工修改和终稿身份，私有提示内容不展示，安全版本引用按需可读。

左目录是Campaign/Series/Post树及未提交标记，中间六项稿件编辑，右侧可选Brief/选择依据/版本。选节点不提交生成；底部生成预览、保存、比较版本分开。Web/Windows/macOS并读所选Post和父上下文，iOS先Post正文与必要字段、父项摘要可展开，复杂批量编辑续接同版；官网仅去敏例。UI自身AIGC可按稿型收放六字段/对比候选，不改权重、Brief、事实或批量采用，固定编辑器和锁段保留。

Brief不足只禁对应生成，不禁自写保存；换父上下文或模板版使旧候选待复核。权重读回失败保旧值及来源，不偷偷置默认。验删除/重排不丢子稿、同名Post、批量部分失败、人工锁定、生成旧响应、取消和父子版冷开；130新增多平台草稿不代表本三级生产链已闭合。


### 原要求具体工作合同：模板注册版本与稿型专属编辑器

模板工具先让用户看用途/适用输入/产生的可编辑对象和风险规则，详情保真实template_id、版本、状态与input_schema/output_schema的可理解字段说明；不让用户先填JSON或把注册项数当已可用。旧作品固定所用模板版，更新先预览输入/输出/风险规则变化，明确采用才生成新作品修订；退役版仍按权限可读历史。
小红书笔记提供所需文稿字段；海报并读文字/视觉Brief与实际画布；视频分镜逐镜编辑visual、台词、时长、目的、素材引用，可添加/重排并保父镜头；评论回复显示原评论/上下文、风险和原策略“自动/建议/必人审”的实际范围。当前只获准生成回复草稿时，自动只表示获准内部草稿步骤，绝不暗含发送；必要人审不能被模板选择跳过。

模板列表左、所选用途/输入字段中、版本差异与风险右；进入作品后切真正稿型编辑器，注册技术详情收起。分镜是逐镜可编辑表和对应素材预览，评论是原文/草稿并读而非同一通用文本框。Web/Windows/macOS完整编辑，iOS按一镜/一回复审阅与允许轻改、保模板版与返回；官网只真实样例。UI按真实schema和稿型组合原生字段/预览，不执行生成HTML/JS、不推断缺字段或批准状态；固定布局与无AI可用。

验模板缺版/退役/输入不匹配、风险规则更新、输出不全、单镜素材撤回、重排保时长和目的、评论人审未过、取消更新保旧工程及保存重开。实际权限/效果由原Owner，不因模板标自动就越权发送。模板注册、生成效果、保存和外部发布四种状态分别验。


### 原要求具体工作合同：L0至L3的可编辑下钻与上抽

创意工具在当前作品上下文内显示原L0芥子原子技巧、L1单线公式、L2多线战役、L3品牌世界观各层；每层是可编辑内容及其真实父引用、版本、上下文指纹/安全摘要。用户从任一层写作，不强制从L0爬到L3。L2分别编辑人群、内容、渠道、节奏、场域、预算六维，预算带单位/币种；每个判断可挂真实信号或明确未验证假设。
“展开为方案”先预览生成的下层节点/与原稿差异；“提炼为方法”只形成上层候选及反例/适用条件，学习晋升仍走原证据和批准门。修改一层先显示实际声明依赖影响，不画未实现的全图，用户逐项采用新版本，原人工稿与未选分支不被重算覆盖。

主区当前层内容，左侧L0–L3语义目录/真实父子路径，右侧来源与“此次改变影响”清单；L2打开六维表，底部下钻预览/上抽候选/保存分别有动作。Web/Windows/macOS可并读相邻两层，iOS一层主面、父路径和影响Sheet可逆展开，不把整个树缩小；官网以去敏例说明方法非证明。UI自身AIGC可根据真实层级提出原创路径或同源列表/六维矩阵，用户可锁定/撤销，不生成不存在父边或晋升绿灯。

验无父引用、父版变化、上下文相同但素材撤权、L2缺维度、真假信号分开、改上层仅重算实际依赖、取消不采用、上抽未满足原晋升条件和冷开同版。原L0–L3语义不被新标签/通用模板替代，不把一次生成算知识沉淀完成。

### 原G100/G101/G103/G121/G170/G171具体终态合同：三调性、机制组合与完整内容审校

从当前Brief的“创意方法”进入，保正文为主，不强制先选方法。调性必选mass/premium/luxury；同一Big Idea的三种执行以同事实并读，局部采用仅改选中段。luxury才展开已版本化六条克制规则：名词优于形容词、过程重于结果、传承与时间载体、留白不煽动、仪式与私密、文化识别线索；规则中的工艺、时间与历史仍需真实依据，不能据范例造事实。服务/功能主题仍按原白名单仅用写实。
机制面列本候选的机制、张力句式、角度、语义角色、预算组合，至少三维真实参与才作对应说明；保生成批次/可复现seed为只读详情，用户可按相同已存条件重做，不就地改共享候选。逐条显示同批重复、占位残留、适配冲突；可修改、排除或保草稿，不让“无警告”冒原创认证。原SIT六模板、文化连接/UGC产品反馈/世界观等4A机制按已登记方法解释“本案怎么用/为什么是我”，未有方法定义就标待核，不能补造名称。slogan显示词数、原句对照和重叠说明，4–8词是偏好不是所有语种硬门；L0→L1的N>10及显著条件在学习评价显示，不能因生成成功自动晋升。
甲/乙/丙视角选择先填明确使用者和决策责任，按收益、KPI、下一动作及依据比较章节变化；角色名称不改变授权或事实。内容模式可按Narrative/Copy/Visual/Motion/Campaign/Evaluation查看原资产；生产链保Brief→Context→Research/Evidence→Strategy→Narrative→Draft→Artifact→Review→Approval→Publish/Export→Measurement→Evaluation→Learning Asset十三阶段，每阶段可回父版、来源与受影响后续，允许跳过不需要的工作，不强迫一次跑完。
九维审校在现稿件检查器中延续；视觉素材逐项选择Hook/Emotion Establishment/Transition/Scene Reveal/Product-Proof/Detail/Closure角色及理由，话题按广泛入口、垂直兴趣、情绪生活方式、时令场景、品牌专属五层编辑。每次2–4候选并读专业理由/客户版说明/取舍，不能用标题热度保证流量池。

构图：左侧Brief/方法与十三阶段目录，中间当前稿件和选中候选，右侧按调性/机制/视角/九维切换检查器；候选表固定事实、预算和人工锁定段。七角色用素材顺序条，五层话题用层级列表，不混成一列热榜。

状态：必要调性未选、方法未核、证据不足、重复/占位待改、审校未核/需修/阻断/READY、来源过期分别说明。改Brief/预算/来源先列受影响候选和审校；取消保原稿，采用后存父版，旧回调不盖人工段；重开复核真实阶段而非模板进度。

Public Website仅用获准真实样例说明三调性、机制组合与完整内容审校及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI自身AIGC可以按“挑机制/改语气/审证据”建议候选并读和检查器层次，保用户锁列/简洁/撤销；正文生成、创意候选或合规分数不计UI自身生成。价值是方法真正指导作品而不把术语当成完整提案。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G102具体终态合同：原生主题与排除项核对

主题从已选择的真实原生标题/正文进入。主面将标题与正文分栏，主题词项点选后定位原文；标题权重单列并标版本。查询主体词和完整品牌名n-gram的stop_terms在“本次排除”展开，系统摘要/合成标记/互动指标及其标签词只在排除说明出现，不能参与原文词频。用户保留原文、派生主题及来源关系，不修改原Evidence。

构图：顶部来源/版本与标题权重，中间原生标题/正文对读，右侧主题词与点击定位，底部“已排除词/字段”明细和保存本分析；iOS先主题→原文命中→排除说明，返回保选词。

无原文、只有摘要、截断正文、标题缺失、语言不支持、权重未核分别呈现；取消分析保资料，改来源后旧词频标过期，重开绑定同原文版本。无合法原文不补造主题。

Public Website仅用获准真实样例说明原生主题与排除项核对及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按标题/正文命中关系重组语义高亮与对照；不生成不存在的词频、命中或高置信。可锁原文阅读布局，无AI仍可阅读和人工整理。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G104具体终态合同：营销方法连接事实与提案章节

在现十段方案/八段拆解/自由成稿的检查器内增加“这段策略依据什么”。按当前问题展开STP的细分/选择/定位、4P/4C/4R相关条目、CDV=TCV−TCC的价值/成本组成、品牌资产及营销5.0的长期指标。每一项显示本稿对应段落、已有输入/分析、策略选择和未证假设；适用项由问题决定，不强迫填满全部术语。low/mid/high预算档与真实金额/币种/来源分开，未给预算只留待补，不生成X%作实际计划。4A叙事弧与One Slide One Job显示每段/页的单一目的及原依据。txt/md/json/csv/docx/pptx的导入格式、解析缺段、原文与拆解分区；导出Word前预览实际完整正文和未替换占位。

构图：左目录明确“十段方案骨架/八段分析目录/自由稿”，中间可编辑成稿，右侧方法→原输入/分析→本段选择→长期观察表；点击条目同时定位正文与来源。方法层可关闭，不能挤走写作。

未知价值/成本不算CDV，未有长期观察不编百分比；切方法只提修改候选。取消保文稿，采用形成新父版，导入失败保原件，导出失败不删除编辑。验每种格式、目录重排、方法缺输入、占位提醒和Word冷开读回。

Public Website仅用获准真实样例说明营销方法连接事实与提案章节及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按写作/核实/比较目标提出正文与方法侧读的原创构图，保锁定和稳定目录；不把生成大纲或好看的图表认成完整内容质量。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G105/G120/G173具体终态合同：节点交叉、当月适配与跨市场稿件

现营销日历顶部依次选择日期/时区、行业、区域和平台；国内节气/节日/大促与海外/区域节点可交叉筛选。7行业与26海外节点沿原版本化数据读取，展示实际已载/缺项和来源，不按目标数造日期。建议结果列节点、真实适用期、情绪主题、调性及与当前Brief关联理由；当月自动绑定作为可检查提案，用户可改/忽略。报告保marketing_nodes的真实节点引用，CSV导出先预览日期、时区、区域、任务、平台和版本，排期导出不是发布。
出海视频从同日历选择7区域节点，脚本中标具体关联段及平台包装差异；TikTok/IG Reels/YT Shorts分别保原生版本。KOC层级与店铺承接是当前计划/链接和真实观察分区，缺授权、缺店铺或无转化观测不编闭环。

构图：月/周/列表主面，顶部交叉筛选，右侧节点/来源与加入计划；选中脚本段后同区域的平台稿并读，底部CSV预览与导出。iOS按日期→节点→关联脚本/计划逐层，不缩小整个日历。

日期未知、地区不适用、过期节点、日历年份未覆盖、缺来源和计划冲突分开；改区域/日期先列受影响稿件/排期，取消不改计划，重开保节点版本，旧建议不覆盖人工日期。

Public Website仅用获准真实样例说明节点交叉、当月适配与跨市场稿件及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按密度建议月历、顺序列表或平台差异对照，保同一节点/所选稿和撤销；生成营销创意不等UI AIGC。价值是节点有据可用且跨市场改写不丢事实。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G106具体终态合同：平台原生信号与改写依据

选定创意/内容版本后，原生信号面逐行列停留、完播、重看、私发转发、评论、收藏、点赞的值/单位/期间/分母/可得状态和来源。指标优先是原方法语境，不自动变跨平台统一权重；不可得不补0。ROI区域单列成本、实际收益、归因范围及缺项，不能由点赞计算。打开“据此改写”返回该平台可编辑草稿，保事实母版并显示钩子/结构/时长/包装改变理由。

构图：左内容与平台版本，中间同字段信号表，右原生来源与改写差异；ROI与互动反馈不同区域。iOS逐平台同字段切换，不用同一柱高冒同尺度。

平台字段缺失、定义不可比、费用/收益不足、数据过期各保文字；取消保原稿，重开原信号版本，采用改写只改该平台候选，不自动发布或恢复外部权限。

Public Website仅用获准真实样例说明平台原生信号与改写依据及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按可比字段优先安排证据列，用户锁列/简洁/撤销；不造指标或把版式重排当商业回报。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G119具体终态合同：KOS合规、矩阵差异与留资边界

三阶漏斗旁按选中内容/账号展开合规检查，保CPL、真实成本与场景分层来源。矩阵内容相似度>50%显示待审搬运预警及实际对照文本/方法，不直接判侵权；错峰与行为差异展示计划时间/平台规则和可编辑建议，不自动操纵账号。强监管绝对化用语逐处定位并给替换候选，原文保留。实际AI参与的披露按适用平台显示“AI辅助生成”说明/相应话题，可调整合规表达但不可删去必要披露；未参与不假打标。评论/私信只保存草稿；私信通仅在企业号及当前授权/合同真实可用时显示选择，缺条件说明未启用。

构图：创作者档案/漏斗为主，右侧选中内容的相似片段、风险词与披露检查器；计划表单与回复草稿编辑分别打开，底部保“仅草稿/未发送”。iOS单问题逐项修订，不把全部风险揉成总分。

缺费用/分母/平台规则/授权、检测失败、待人审和过期内容分开；改稿后相关检查失效，取消保原稿，保存/重开保披露与版本。没有真实执行合同绝不发评论/私信。

Public Website仅用获准真实样例说明KOS合规、矩阵差异与留资边界及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按需突出冲突片段和缺授权说明，保用户锁选区/撤销；不自动删除披露或把警告淡化成批准。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G122具体终态合同：跨市场命名与音义核查

从当前Brief“命名”进入原创作工作面，先目标、受众、产品特点和拟用市场，再编辑候选。候选每行按zh/en/ko等实际市场列发音/音译、字面及文化含义、谐音/负面联想、来源与待核问题；语言无依据就未知。Nova/Bing作为原反例测试，不把词条或模型意见当商标可注册/语言安全认证。用户对照证据修改、排除或选择并说明理由，选名只保存作品版本。

构图：左Brief与市场，中间候选命名矩阵，右所选语言证据/发音文字和风险，底部修改/保留/排除/保存；移动候选→市场逐项→同字段对比，有文本等价，不依赖自动朗读。

词典/语音未绑定、同音未知、来源过期、语言不支持和人工待核单列；取消保候选，改市场只复核受影响项，重开保原语言/来源版本，不自动外查或申请注册。

Public Website仅用获准真实样例说明跨市场命名与音义核查及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按风险语言或候选差异提出对照构图，用户锁列/简洁/撤销；生成名称不是UI AIGC，不能生成已核验标记。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G135/G181/G182具体终态合同：韩语分析、词典与本地化审校

原稿内容语言与界面语言分开；选择韩语后，在稿件检查器按实际能力显示分词/空格建议、命名实体、情感/主题及韩文风险片段。Kiwi/Okt等实际方法/版本放详情，未运行不写已分析；Naver Blog/Cafe、Daum材料保原平台/正文/可用状态并回统一来源，不因为ko文本推已取得平台授权。
词典侧读区区分国立国语院官方API释义与4704个CC BY 4.0词头资产：当前词、来源类型/链接/许可、更新时间、义项和可选采用范围；只有词头不能补造完整释义。API不可用保原稿/已有合法词表，密钥只走原服务端安全Owner。
可选韩剧式风格先核场景、潜台词、人物声音与留白。审校按自然度、具体性、潜台词、角色归属、节奏、情绪转折、记忆点、画面适配、余味、原创性十维逐条改写/理由；敬语与直译/意译/增省译选择记录语义、人物声音、自然表达、情绪等值、文化、节奏、校对七阶段证据和差异。35/42只是原编辑启发，不当验证阈值。缺音频标待核，不以文字已读冒听过，不复制受限整段字幕。

构图：左角色/场景与语言，中间原文/候选对照，右词典或十维/七阶段检查器；字幕选段同时定位实际时间，未经音频核验保文字审校标签。iOS单段→词典/维度→修订，韩文保30–50%长度空间。

语言未知、模型/词典不可用、词头无释义、音频缺失、风险待核、过期引用及版本冲突各保文字；逐条采用不改未选稿，取消/撤销保原文和人名/敬语选择，重开同版本。

Public Website仅用获准真实样例说明韩语分析、词典与本地化审校及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按语言长度、人物对话或字幕对照提出原生排版，保用户锁选区、简洁/撤销；内容翻译或模型生成不算UI AIGC，不能以漂亮韩文证明自然度。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 便利操作合同：CV04 结果旁修改、比较与导出

适用工作与省步目标：SavedWork正文/笔记/报告及原Owner允许修订的业务文稿；统计/媒体特有输入另走本Owner。

原Owner与真实接口边界：现POST /api/experience/saved-work/<artifact_id>/revise以expected_sha256/reason/edits提交新版本，GET /export?format=取真实文件和hash；现GET /saved-work/<artifact_id>?compare_to=<other_artifact_id>已交有界测试，两版各核现权限且同work；返回comparison_only/from/to/current/target_is_current/changed/changes，字符串ordered unified_diff，changed=false时changes为空。compare_to不混selection参数，GET无写；用户确认还原仍用当前CAS产生新修订。签名依赖文稿走work_dependencies，不能泛用JSON编辑绕Owner。

控件位置与四表面操作：结果顶部就近放“修改此处/比较版本/导出”，先选目标段或字段，右侧差异只按需展开，不先去另一模块；Web/桌面并读，iOS逐段切换差异与原稿，官网仅公开样例版本演示。导出可选合法格式但默认清楚显示当前artifact版本。免去重新贴全文、手工逐字找改动和跨页导出。

持久化、权限与错误恢复：无差异明确显示未更改；CAS冲突保本地编辑并读，不覆盖新稿。版本两侧各自权限必须有效；导出失败留原成果与格式，不假文件。就地撤销提交反向新修订，外部发布/发送不提供假撤销。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

### 便利操作合同：CV08 案例与方法随创作查用，也能拆开学习

适用工作与省步目标：内容创作的案例、方法、品牌理论与参考材料；用于选题、标题、结构、脚本、方案及用户自己的项目练习，不另造孤立案例库或方法库。

原Owner与真实接口边界：现resource_library的case_study/brand_theory等原分类、Intelligence Library来源绑定和SavedWork是复用起点；resource_library.search_resources函数存在不等外部安全查询入口已完备。实际可公开调用的检索/导入/引用与字段以原Owner完成的同版合同为准。学习练习写用户作品/自评，不将学习候选reference_only当教学训练完成，不自动标Truth或商业有效。

控件位置与四表面操作：创作问题/选区旁“找案例/找方法”打开同一资料抽屉，按当前任务主题、适用场景和内容类型筛选，列表标出处、日期、可用范围和全文/摘要可见性。详情先读原案例，再切“拆解学习”：目标与背景、方法为何适用/不适用、步骤、原文依据、练习题、我的尝试；不存在的字段明确未整理，可人工补充，不自动把AI拆解当原作者观点。“应用到当前项目”预览将带入的结构/步骤/引用，用户选择后进入当前稿可编辑差异，保原稿。“保存练习”形成用户自己的SavedWork版本，回看自评与后续真实观察分列。Web/桌面正文主区不被资料列表挤窄，按需侧读；iOS案例阅读/方法步骤/练习使用可逆单层Sheet并保原稿位置；官网只展示有权公开的样例与方法使用故事，不能泄私有项目。省去另开资料库搜索、抄方法再回稿件，以及学习笔记与实际项目分离的往返。

持久化、权限与错误恢复：空目录可继续创作并明确“尚无可用资料”；原文不可用只显示有权摘要及限制；来源许可UNKNOWN保持，不暗示可全文搬运/训练。选用前核当前版本和权限，撤权/原文变更令引用待重新确认；引用与练习分别保存，取消采用不改当前稿。AI拆解必须标用户/模型派生且保原文，当前无生成合同则手动整理；练习完成是用户记录，不等技能掌握或真实项目效果。具体案例和方法内容的导入数量/可检索性由同版实测给证据，不能拿空分类算内容齐备。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

### 便利操作合同：CV14 参考片峰值点一下，核前后真实原片

适用工作与省步目标：用户看到变化峰、候选镜头或接触表抽样帧，想核它究竟是切镜头、灯光变化还是动作，无需手抄时间码。 关联新增能力：C07, C08；细化J02原有减步与原工作面合同；不是新模块，不增批处理、比较导出、模式复用或独立快捷服务。

原Owner与真实接口边界：现参考分析报告有frame_index/pts/pts_sec、峰值和镜头候选、抽样接触表及源hash。限120秒/7200帧，接触表0.5秒采样；全帧测量不是人工看完。 待补：前端待接报告时间基→同一授权源播放器的可验证seek；不假定浏览器能逐帧精确停在requested PTS，显示实际到达时间/精度。持久人工核看记录须走原批注/工程合同，目前报告human_reviewed_*初值0，不靠一次点击自动改成全帧审完。 代码依据：lumenis/shared/content_creation/reference_analysis.py:26–38 bounded analysis constants；lumenis/shared/content_creation/reference_analysis.py:183–207 _peaks_and_shots；lumenis/shared/content_creation/reference_analysis.py:312–345 report timestamp/candidate/contact fields；shared_artifacts.py:2618–2624 reference_analysis artifact generation

控件位置与四表面操作：在峰值行/接触表格上点“看前后”，播放器定位到同一源并带可调前后窗口；顶部写源时间、实际到达时间与“测量候选”。播放后可明确记“已核本片段”及用户判断，不自动命名为真实镜头。保峰值排序/页码与返回选中格，支持前/后一候选而不重复开窗。 四表面：官网：真实可控短片演示峰值与上下文，不用装饰动画冒测量。；Web Workspace：BMP-06/SH-01图表或接触表旁展开同播放器。；Windows/macOS：宽屏可并读测量曲线和原片，仍用同一真实PTS。；iOS：点格进入播放器Sheet，返回原页原格，原来源不可播时保图片和真实限制。 省去：省去抄写时间码；省去播放器中反复手动寻找峰值；省去接触表翻页后重新找原选中格。UI自身AIGC：可按实际选中的帧/峰/前后区间组织并读，不生成未观察画面、语义镜头或已看标签。

持久化、权限与错误恢复：定位和试听不保存、不增加素材复用授权；明确批注按原actor/scope绑定源hash及区间保存，源变版旧记录保历史但不覆盖新版核看。只记用户实际选定区间。 源hash变更、PTS不稳定/无法seek或超限时保原报告并标不可定位，可手工原片阅读；不裁短冒全片完成。取消播放回原接触格；没有精确seek不得声称帧级编辑误差已验。 验收：采样格、全帧测量与人工核看三个账不串；显示requested PTS与实际播放定位不一致；一次播放不自动审核整片或提高素材授权。当前为研发合同，未实测减步数字，未宣称四端接线完成。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

### 便利操作合同：CV15 十段方案内逐处补待填值，保已写正文

适用工作与省步目标：方案已生成十段骨架，用户要把X%、X周和明确标记的待定事实补成自己确认的内容，不用全文查找和反复生成整稿。 关联新增能力：C01, C02, C06；细化J02原有减步与原工作面合同；不是新模块，不增批处理、比较导出、模式复用或独立快捷服务。

原Owner与真实接口边界：PLAN_SECTIONS已有准确十段；_human_intro含预算X%与节奏X周，generate_plan/render_text输出骨架。POST内容drafts是现手写/修订保存基础；八段pitch_parser分析结构是另一对象，不改成十段。 待补：原方案/ContentDraft Owner需把十段生成正文绑定到可编辑稿及保存/Word主链，并提供模板来源版本与placeholder标识或可核定位。仅凭任意正文出现X不能视为占位；旧稿无标识时只标候选、由用户确认。当前双结构接线/内容质量待验。 代码依据：scripts/campaign_plan.py:120–173 PLAN_SECTIONS / _human_intro / generate_plan；content_generation.py:1682–1773 POST drafts and immutable revision binding

控件位置与四表面操作：正文编辑区加一条可折叠“待填处 n / 已明确保留 m”，按现正文次序显示“下一处”。点条目定位确切章节/文本范围，旁露该处所需输入（如分配比例、阶段周数或事实依据），允许填值、标为暂未定或保留原文并写理由；不重生成整稿，不擅改十段目录。自动检查仅校验真实声明的结构规则，不替用户编预算或KPI。 四表面：官网：真实去敏十段样例显示从骨架补成正文过程。；Web Workspace：BMP-06/SH-01正文内下一待填，不离开当前插入点。；Windows/macOS：同Web可舒展编辑并读依据，Word导出只沿真实已接主链。；iOS：单处填写Sheet与原句并读，返回同章节；复杂排版续接同稿。 省去：省去全文搜索每个占位；省去为一处缺值整稿重生成；省去修改后重新核对已完成人工段落。UI自身AIGC：可把当前待填的上下文/依据与输入并读，用户可关；不能把随机猜测值写入正文，也不把生成正文当UI生成。

持久化、权限与错误恢复：所有修改先在当前草稿，明确保存沿POST drafts并绑定父版/来源/claim，改过的已审核claim按原合同重新待审。持久占位处置状态须进原草稿payload，缺合同前只显示本次未保存。导出沿原主链，提示未处理项不虚称正式完整提案；可保存未完成稿。 并发改稿使旧范围失效则重新定位，不覆盖新文字；删除某段后的占位不可跳到相似句；取消局部填写恢复该处改前值，全文其余已写内容保留。保存回执未知先查旧请求；不自动重跑生成或重复导出。 验收：数学变量X或品牌名含X不误列为模板占位；准确保十段生成结构与八段分析结构各自用途；未定值可保存但不伪装为已核真实数据，全文改稿审核状态正确失效。当前为研发合同，未实测减步数字，未宣称四端接线完成。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。
