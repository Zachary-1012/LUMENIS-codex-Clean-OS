# Intelligent UI：序境采用判断与后续职责

取证日期：2026-10-08；状态：**研究已采用，实现等待后续派工**。
本文是研究证据；唯一设计规则仍为 Experience Constitution §38，执行路由仍为 AGENTS.md。

## 原文与证据边界

用户指定 [X 话题](https://x.com/i/trending/2107900056858722693)，直接读取返回 403，未登录或绕过访问限制，故没有声称已读该页正文。
随后实际阅读 OpenAI 2026-10-07 发布的 [GPT-6 and Intelligent UI for everyone](https://openai.com/index/gpt-6-for-everyone/)。
原文明确提出：根据任务组合文字、图形和交互，使用可逐步呈现的组件，并评估界面清晰度、实用性和完整性。该更新作用于 ChatGPT Chat，文中明确 Work/Codex 的模型不随此次发布改变。原文未提供可供序境直接安装的同款编译器或开源权重。

同时读取 [OpenAI Plugin UI guidelines](https://developers.openai.com/plugins/concepts/ui-guidelines)：轻量交互与复杂编辑应选择不同承载空间，直接编辑应保留状态，并遵守可访问性。它是 ChatGPT 内插件的规则，不能整体替代序境的四端设计、手绘水彩视觉或屏幕规范。

## 序境采用结论（本项目设计判断）

**ADAPT：任务决定结果的表现形式；同一个结果同时支持阅读、直接调整和后续工作。**
最有价值的应用是 C3+C5 的研究/方案连续性，以及 C4 的可编辑创作成果；C1供给可信字段，C2供给有依据的提案，C6维护真实执行，F负责实际界面。不能只让 F 画一组看起来智能的卡片。

- 品牌/商业体比较：实际可比时间、城市、币种、来源和样本范围先成立，再显示比较图和筛选控件；不把未知数补成零。
- 方案预算：调整金额或日期后，清楚显示哪些段落/活动受影响；通过已有修订合同采用新版本，保留原成果与回滚。
- 研究结果：从图表或结论直接回到相应来源；将同一 Brief 和已授权引用送入创作，不重复输入和选择。
- 视频/播客：选定镜头/音频段与脚本同步，局部修改不破坏其他内容；现有横向时间轴、预览、保存、重开和恢复要求保留。
- AI 交互：提示如何比较/调整，并生成已有动作合同支持的提案；API与 Permission 决定可执行性，模型不能靠生成按钮获得权限。
- 官网：只能讲述已验证能力或清楚标明示例，不把动画和演示当成产品运行证明。操作端依各自角色提供实用交互。

**不采用**：将序境全部改成聊天；重复模板页面；任意生成脚本后执行；为本项接入需用户第三方登录的新核心依赖；安装不明“Intelligent UI SDK”；换模型或偷偷开启加速；将插件组件的两按钮限制套到整套专业工作台。

## 后续直接执行入口

1. 既有 C1-C6/F 后续获派工时，读取 Experience §38 的职责与验收表及当前屏幕规范。
2. 优先在 C3/C5 研究→方案→修订链和 C4 编辑链采用，C1/C2/C6各补自己的合同，F实现页面。此排序不阻止已有独立闭环工作。
3. 复用 Source/Evidence/Task/Artifact/版本/Permission；不新增第二套注册表、运行时、数据存储、执行队列。
4. 先核实真实字段与动作，再更新具体 DESIGN_READY 规范；实现按既有主线规则进行。
5. 验收真实用户能否在同一任务里理解、调整、保存、重开、撤销；记录错误率、重复输入、有效结果等待时间和恢复，不以模型输出或视觉效果代替结果。

本次仅完成研究、规则与职责映射。未启动这些窗口、未修改 Intelligent UI 产品实现、未建立训练数据准入、未声明四端验收通过。

## Product Owner 全产品增补的落点（2026-10-08）

用户进一步要求把智能UI应用到产品每个角落并服务真实世界。本次因此同步细化唯一产品蓝图、Experience §38、四端决策、执行路由、Owner索引、44份既有屏幕规范及其README/模板、既有44屏文字草图和CURRENT。不是另建“智能UI平台”或仅给AI首页加卡片。

逐屏采用按现有任务区分：开放入口/范围选择/任务恢复；CTH运营、主体、采集、事件、日历、反馈、指标、案例、决策与报告；BMP市场/竞争/传播/创作者/内容/Campaign/播客/品牌评价/风险/标杆；AI任务/恢复/依据/Skill/诊断；SYSTEM运行/数据/安全/设置/浏览器/发布等；Shared创作/资料Reader/研究/成果/评价/通知。每屏需要真实输入与动作、可直接调整的交互、来源版本连续性、四端差异和适用恢复验收，具体入口保存在该屏原有规范。

视觉草图的旧版本保留为历史，本次追加具日期的任务动线设计。此次同步更新的是文字草图/设计输入；尚未重绘全部美术资产、视频或Figma文件，也未实现智能UI产品代码。新交互差异需要本屏Owner按实际合同完成DESIGN_READY审阅后实施；不得沿用旧规范状态自动冒充通过。当前C1–C6/F派工状态不因此改变。

完成判据进入已有Owner验收：在真实来源、许可、预算和设备条件下，用户能理解和调整结果、保留正确引用/父版本、保存重开，并在来源撤回/Scope切换/中断后安全继续。比较结果正确性、错误修改/重复输入与有效完成时间；目前没有基线实测，不能宣称提升百分比。

## 本轮用户前端审计的增量采用

附件全文已读。可编辑Figma工程、44屏及官网家族、五个Golden Pages顺序、主题/组件/变量映射、中英韩及完整状态、局部修改/回退均写入现有Experience、ScreenSpec/README和原蓝图草图，不创建第二设计权威。规则同步不创建Figma文件，不恢复F或C1-C6。

源码针对性复核：ACC-03已有页面但仍为旧三入口/启动状态面，未嵌入目标AI-01编辑器；root/router/Shell/Web manifest当前默认CTH-01，已批准目标ACC-03尚未实现。ACC-04已有return-only界面，返回固定ACC-03，未绑定原Task/scope/operation/恢复receipt。两处`NO_FLUTTER_SCREEN`旧登记已在BINDING_MATRIX及派生binding registry校准为真实源码存在、目标/运行未验收；原Permission/Truth状态不提升。ACC-04旧返回行为明确为历史实现，当前目标回可信原任务，缺安全origin时才回Home。

定位入口：`app/lib/navigation/lumenis_workspace_routes.dart`、`app/lib/navigation/lumenis_router.dart`、`app/lib/shell/lumenis_workspace_shell.dart`、`app/web/manifest.json`、`app/lib/features/account/acc03/`与`acc04/`。后续F负责呈现与任务连续性，C6负责启动/共享绑定，SYSTEM Permission/recovery负责真实恢复；本轮不替其他窗口改这些产品实现。

工具维护和10月1—8日官方证据见[维护记录](CODEX-MAINTENANCE-20261008.md)。未验证问题不借更新规则升级为PASS。

## 成熟软件两增补与操作对标研究（2026-10-08）

两份用户原文全文已读，逐项保留J1–J8/U01–U25基础操作与序境特色、视频九项/播客十项以及P0-A至P1-F次序、许可/版本/回退、Owner与实际验收要求。正文落回Architecture/Experience/Owner/Overlay和SH-01/BMP-08，未复制成新规划体系。附件中的main/dirty/CI是其时快照；本轮fresh远端仍为288f222d，但本地本批变化不以附件旧计数代表。

### 本次新增官方读取

- [Apple Undo and redo](https://developer.apple.com/design/human-interface-guidelines/undo-and-redo)：直接HTML需JavaScript，检索工具返回官方页面完整可见正文（包含Best practices/平台考虑），据此采用明确撤回对象、显示结果与系统操作习惯。未声称全HIG读完。
- [Apple Feedback](https://developer.apple.com/design/human-interface-guidelines/feedback)：同样通过官方页面检索正文读取；采用真实状态/结果反馈与按重要性选择中断强度。普通状态内联显示，阻止动作给具体原因。
- [Tesla Model 3 Driver Profiles（澳洲版）](https://www.tesla.com/ownersmanual/model3/en_au/GUID-A2D0403E-3DAC-4695-A4E6-DC875F4DEDC3.html)：本轮直接读取正文；有保存/恢复、停止调整、部分设置跨支持车辆同步及明确限制。只提炼序境现有设置与任务的保存、停止、恢复和适用边界，不采用车辆控制、自动驾驶或新增Tesla账号。
- GPT原文和Plugin UI指南已在上文核实，复用其版本证据，不重复研究不变内容。其任务适配的呈现与直接操作结合本次成熟基础能力，不能用智能卡片替代编辑器/播放器。

上述到序境的映射属于设计判断，不证明竞品性能或序境已有实现。其余指定竞品（Meltwater/Brandwatch/数说故事/识微、GenStudio、Descript、Dify/GPT Researcher/OpenManus）保留用户要求的机制研究方向，分别由C1/C3/C5、C4/C5、C4、C2/C5在获派工的同一成果中使用已有研究并定向核对最新原文、版本、许可及实际收益；本轮不冒称已完成这些产品的全量研究。

### 已解决的规则冲突

| 冲突 | 本次统一口径 |
| --- | --- |
| 附件要求M立即执行 vs 用户本次等待后续窗口 | M本轮更新规则、收尾原已授权修复和发布；后续F/C1-C6实施等待PO确认，能力要求完整保留 |
| 无AI就等 vs 普通编辑必须可用 | 确定性导入/编辑/保存/手工转录独立继续，AI相关路径真实标不可用，不伪造增强 |
| Read Aloud vs 播客录音/ASR/成品 | 本地文字预览与真实音频制作分别验收；脚本更改不自动改录音 |
| 复用成熟组件 vs 现有Timeline/Renderer唯一 | 先复用/修调用；真缺口通过原Owner适配；OTIO仅互通，OpenShot/MLT有证据才评估 |
| whisper.cpp vs 已停用本地LLM provider | 音频ASR候选须C2准入并走唯一Gateway，不激活llama.cpp/Ollama等LLM路由；本轮未安装/运行ASR |
| 不必要上下滚动 vs 横向时间线/必要长内容 | 保留横向精细操作、可访问的长内容；不以压缩布局减少功能 |
| 附件状态字段 vs 现有机器状态梯度 | capability_observation是原任务内检查字段，不改机器completion/dispatch/approval合同 |
| 旧文档F可继续/仅C暂停 vs 当前全部等确认 | README和Overlay去除过期即时派工句，AGENTS写明本次M限定任务，其他窗口待PO |
| 195/194材料计数并存 | 原191行保留，新增6份合计197；最新摘要与manifest统一，历史计数注明历史 |

没有宣称产品已无全部Bug或后续运行无冲突；本批统一了所读材料与现有规则的已识别矛盾。后续每Owner执行前以同一main+保护中的本地工作做fresh admission，并在原任务中解决新事实，不另开候选或反复交接。

ACC-04进一步只读追踪：`experience_runtime._all_builders()`会懒合并`experience_screens.SCREEN_BUILDERS`，因此不能断言接口必返`bound=false`。旧builder的`sections`/`bound=true`不提供Flutter期待的`guard/recovery_paths`，typed guard仍不可用。这是合同不匹配，既不能报页面不存在，也不能报恢复已绑定。此次仅校准四份绑定元数据；其余旧快照行保留原未验收证据，不冒称54行全部重新核实。
