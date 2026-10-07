# 序境全产品逻辑审阅与既有能力优化

日期：2026-10-08；性质：M的逻辑/源码审阅证据，不是第二产品蓝图或派工表。

## 1. 范围与冻结事实

- 覆盖现有J1–J8/U01–U25：数据/主体、CTH、BMP、提案、视频、播客、资料/自有AI、四端运行，以及权限、版本、恢复、设置通知和反馈学习的交接逻辑。
- 源码冻结于 `2d0f8d61aed85d073abef8f67752200503927d7b`，取证时local HEAD、origin/main、live main一致。逐项源码引用使用该固定提交；其后规则与Instagram边界修复为本次发布增量。
- 全部逻辑范围已梳理；源码检查集中于关键生产入口、调用方和交接，不是所有函数逐行审计，也未重读全部197项材料。保护中的18个tracked dirty及3个untracked原路径单列，不作已发布能力或删除对象。材料清单数量不证明全量阅读。
- 本轮未启动采集/训练，未探测平台身份、重载Core、写Production DB、生成真实媒体或执行客户任务。因此运行、DB及用户验收仍未重新核实；不得从源码或规则推断产品整体闭环。
- 同SHA App Gate成功；Product Gate 37686084801在Instagram外域URL异常合同失败。该具体问题已由原适配器修复，原5项隔离检查通过，最终CI以新提交实际结果为准。

## 2. 应保持的一条用户主线

```text
明确目标与约束（允许GLOBAL读取，具体动作再解析所需焦点）
  → 复用已有授权资料 / 按主体话题补采
  → Source / Evidence / Canonical，保留来源时间与实际缺口
  → 有依据的有用部分逐步呈现、比较与解释
  → 用户直接调整目标、预算、时间或选择
  → CTH/BMP判断 / 原创提案 / 视频 / 播客
  → 对应Owner保存可编辑成果、来源、父版本与回执
  → 重开 / 换端 / 中断恢复
  → 来源或约束改变：定位影响、明确采用、局部修订、保留旧版
  → 区分已执行Action、实际Outcome、Evaluation
  → 经准入的知识/模型/Skill/配置改进及回滚
```

产品代码控制采集、运行和持久任务。Codex是研发工具。完整维度与实际数据覆盖分开；未知显示“—”并解释，不能填0或假称能力已闭环。AI仅对已批准能力提供增强；读、筛、算、手工编辑、保存等确定性路径按自身依赖独立工作。

## 3. 全能力逻辑检查清单

下列“存在”只描述已发布source。除明确列明的既有工程检查，不声称本轮已运行。

| 覆盖 | 已有连接和源码证据 | 必须收敛的逻辑/断点 | 现有责任与完整出口 |
|---|---|---|---|
| J1 / U01–U03：主体、别名、关系及市场 | [acquisition_plan.py:304](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/system/collector/acquisition_plan.py#L304)消费subject_registry；编译查询要求已登记实体/话题 | 同名品牌、商业体、门店、总部/发源地/经营地和关系时点分别约束，不靠名字补事实；四参考主体不是上限。任务语义扩展字段在:785保存但未形成额外查询词 | C1主责、C3语义：真实实体关系可读、可选、可追来源，查询覆盖目标而非噪声；新增词保留旧版 |
| J1 / U04–U05：采集、时间及持续运行 | [acquisition_plan.py:740](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/system/collector/acquisition_plan.py#L740)和prelaunch_baseline:81仍写死日期；secondary_collection:2254有查询checkpoint | 按最新规则改可选明确时间范围，保留旧plan/hash；查询checkpoint与原生分页cursor分开。返回的coverage_complete/product_schedule_operation_proven仍false。持续采集能力不能由单次结果证明 | C1/C6：真实词条→查询→详情/评论/许可媒体→正式入库→按期增量→取消/重启恢复；缺值准确呈现且说明原因 |
| J1 / U04及J8运行：兼容采集入口 | [collector_service.py:69](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/adapters/collector_service.py#L69)仍走persist_result；业务路径另有secondary_collection Canonical/Evidence | 保留旧task/轮询/风险行为，把不同调用方汇入同一事务、Permission和receipt，不能存在一条成功仅写notes的平行完成口径；保护中已有修复应先比对采用 | C1/C6：同授权输入经各兼容入口得到同义Source/Evidence/Canonical，写失败诚实，旧worker不确认新attempt |
| J2 / U06–U09：运营、事件、消费者、风险和决策 | [api_dual_domain.py:497](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/api_dual_domain.py#L497)承接SourceBrief/证据及决策事件，按parent Evidence检查版本 | 源码reopen仍标owned_analysis不可用；render_result的W5_EXPORT_BINDING_REQUIRED说明正常决策成果到统一可保存制作输入仍缺连接。模型观点、操作者选择、真实行动效果保持分开 | C3、C5、C2/C6：有来源的真实运营问题→可用判断→保存/行动回执→Outcome（可确切未知）→重开/评价 |
| J3 / U10–U12及U07–U08：品牌、市场、竞品/创作者/传播、Campaign | [api_dual_domain.py:817](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/api_dual_domain.py#L817)把业务历史投影为带来源Markdown；架构/Owner保留BMP完整能力 | 同城市/期间/币种/分母才比较；热榜、样本热点和模型推断分开；范围不足不得推总体满意度/销售因果。当前未逐算法重验BMP所有统计；不得据此宣称全部真实结果可用 | C3主责、C1/C5输入：可调比较/预算/活动方案、明确约束→真实可保存版本→授权行动与观测效果分别核实 |
| J7 / U16–U17：资料、研究、引用和SavedWork | [saved_work.py:494](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/shared/reporting/saved_work.py#L494)保存不可变Artifact/parent/hash，:739修订；source_brief_job保存报告快照 | SourceBrief的artifact_hash是报告快照，不自动等于Shared Artifact；通用research/report修订不支持所有task-owned媒体。资料采用落实输入/处理/质检/结果，产品采用和MODEL_TRAIN准入独立 | C5：真实资料→可定位引用→研究结果→保存/修订/重开/导出/撤权；C3/C4消费同一固定上游 |
| J4 / U13：原创提案 | [contracts.py:241](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/shared/content_creation/contracts.py#L241)解析SavedWork或SourceBrief固定上游；[internal_pitch.py:158](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/shared/content_creation/internal_pitch.py#L158)继承document.citations并校验 | SourceBrief document没有该citations字段，source_records另存；来源绑定已存在，但正常逐条引用是否充分仍须明确投影并验。resolver不直接收business-work ID，应经现有SavedWork owner转换，不能用户重填决策 | C4/C5/C3：同Brief/证据/决策进入提案，实际Word、可编辑文本、预算/局部修订、父版本和恢复；owned参与必须真实 |
| J5 / U14：视频 | [video_editing.py:1159](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/shared/content_creation/video_editing.py#L1159)编辑Timeline的export请求仍blocked，声明renderer/Evidence/Permission未连接；rendering已有独立渲染能力 | 优先将编辑后的同一Timeline版本接现有renderer/Artifact，而非另做演示。内存undo不能当跨进程项目恢复；真实视频与项目分别保留 | C4/C6/F：导入→横向时间线完整编辑→可看预览→真实新渲染→保存工程与成片→重开再编辑；未改片段保持 |
| J6 / U15：播客 | [episode_runtime.py:191](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/podcast/intelligence/episode_runtime.py#L191)有计划、时间线转换；SavedWork支持podcast_plan | 计划可保存不等于实际录音/波形/混音/节目；定向API检查未找到build_timeline调用，需补原Owner正常绑定。ReadAloud不能替代节目音轨/ASR | C4/C5/C6/F：真实播放与Seek→样本波形→授权录音→剪辑混音→真实试听→保存/重开/局改导出；P1处理/转录完整保留 |
| J7 / U18–U19：Owned AI、Agent、Skills/Memory | [ai_gateway/core.py:73](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/system/ai_gateway/core.py#L73)仍无owned service executor；owned_training已有受控实际步骤/checkpoint路径 | 先分清训练执行、模型质量和业务Serving三个完成条件。当前无法从注册/文件或训练计划推出服务可用；模型分段结果先要有真实调用。Agent身份/恢复/Permission/effect仍走已有链 | C2/C6：获准真实GPU step/loss/checkpoint/重载，独立评价，Gateway正常业务推理和保存恢复；资源现有/免费优先，未经新批准不付费 |
| J7 / U20：Evaluation/Learning | [content_assets.py:268](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/lumenis/shared/learning/content_assets.py#L268)当前内容学习晋升入口抛CANONICAL_PROMOTION_GATE_NOT_CONNECTED；owned_evaluation产出观察/人审包 | 这条入口未接通，不推断所有学习能力不存在。Outcome、评价、受控晋升和回滚需各自证据，禁止从自报完成或界面漂亮直接学习成正例 | C2/Shared Learning：真实成功及失败/反例→独立评价→合法批准→版本采用→运行观测→回滚；不改源Evidence |
| J8 / U21–U22：浏览器、开放入口与权限 | [browser_runtime_api.py:22](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/browser_runtime_api.py#L22)有status/probe；现有SYS-06规范及SYSTEM浏览器owner | status/probe不证明完整可操作浏览器。保持Open Original与受控操作、来源保存、验证后健康回读分别处理；ACC-04旧sections并非typed guard。账号重设计/实时语音/开发者模式继续后置 | C6/F及Permission：准确scope下看原始来源/受控操作/必要人验→回原任务，不接触受保护私人profile，不新增登录墙 |
| J8 / U23：四端入口、智能UI与连续性 | [ai01_screen.dart:656](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/app/lib/features/ai01/ai01_screen.dart#L656)提交禁用；repository只load；普通Web transport:29收齐body；默认路由仍CTH-01 | 先绑定批准的Home/提交/恢复，再同链增量呈现。AI01拒绝文案不能强制GLOBAL先选Subject；ACC03/04元数据已校准存在但目标未完成。设计、组件、build均不是四端用户验收 | F/C6/C2：同任务有用内容→直接调整→保存/重开/换端，保留输入/焦点/版本；官网仅真实说明，媒体保持完整操作空间 |
| J8 / U24–U25：设置、通知、运行与发布 | [settings_module.py:167](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/blob/2d0f8d61aed85d073abef8f67752200503927d7b/settings_module.py#L167)等现有设置入口；已有Shared通知/Task和C6运行owner | 本次只核职责及入口，未深验每偏好/通知回原Task、当前supervisor/DB/发布恢复。规则发布与loaded runtime必须分层；历史health/CI不能移植到本次版本 | C5/C6/F：偏好真实生效、通知回原任务；同版本源码/配置/build/runtime/DB兼容及取消/重启/回滚；随后PO重复操作，再谈RELEASED/OPERATING |

## 4. 应采用的优化逻辑与顺序

### 第一组：让同一个目标一路可继续

1. 依已有Task/Brief传播明确actor/scope、原材料、用途、时间/预算和版本，自动复用可授权的已选来源；只在新的必要歧义或授权决策时再向用户确认。入口不默认广州或把GLOBAL改成无范围。
2. 资料查找按业务目的驱动；时间是可选任务约束和结果解释维度，不再固定全局起点。每个所需维度都有准确含义；对可得值、未采集、来源不提供、受限和失败分别展示，采集链本身仍须真实闭环。
3. 优先接研究/决策→原有SavedWork→制作的固定版本与引用，而非增加页面或再次导入。对source_records到citations的映射做完整例验，不能仅因上游hash在场就认为所有具体论断有引用。

### 第二组：普通操作与智能增强共同完整

4. 确定性搜索筛选、公式、文稿编辑、媒体时间轴/导出先沿现有owner真实可用；模型解释与生成使用实际Gateway。两条能独立工作的路径按依赖并行推进，最终同任务验收，不能把无AI当作最终Owned能力完成。
5. 智能UI按任务选择表达，先交付有依据的一部分、随后补充/必要更正；稳定组件和版本保护用户修改。按钮只绑定原有真实动作，partial不等于saved，取消/断线/恢复不重复效果。原文研究与规则在Experience §38，不新开UI框架。
6. 视频/播客优先接已编辑版本到已有renderer、真实播放和Artifact，而非重复建设计划/预览候选。普通编辑质量与来源/业务连续性分别通过，再作为同一可交付成果。

### 第三组：变化与反馈不破坏旧成果

7. 来源更正/预算变更沿已有引用与父链定位依赖；未记录到的依赖明确未知。用户明确采用后只修改受影响的正文、活动或媒体段；回滚由相应owner恢复旧内容为可追踪新版本，不覆盖历史。现saved_work的evidence_id检索声明uncited_dependencies=NOT_VERIFIED，不能称全产品影响分析已做成。
8. Action完成和Outcome尚未知允许同时成立。只把真实效果和约束满足送入Evaluation；学习候选与晋升分开，版本可回退。素材/方法用于改善产品处理、质量和交互，与模型训练授权独立。
9. C6在每个完整成果达到必要条件时同版本组合，不等所有候选积满；先比对并复用保护中的有效工作，再验证真实正常路径/改变/恢复。F与相关业务owner共验真实操作，M审完整结果而非每函数批复。

上述只增强已批准能力，没有新增产品/owner/数据真相；具体实施仍等待PO确认。不存在“一次规则更新即保证所有功能没问题”的声明。

## 5. 这轮能确认的收口与未核实项

已收录：取消全局日期、保留准确缺值维度、全产品任务连续性、成熟基础操作、智能UI分段/更正/直接编辑/等待质量、全部既有J/U范围和后续owner。

未完成：硬编码日期的产品源码改动、真实采集持续运行与数据准入、Gateway serving、完整媒体/影响传播、入口提交/四端Intelligent UI、运行加载、Production DB和PO操作验收。文档中的OPEN具体到已有source/caller，不能让下游自行猜测已经完成。

本记录不替代 `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`、Experience或OwnerIndex。历史材料、权重、失败证据与保护中工作仍保留；未读材料不会被本轮逻辑梳理自动标已采用。


### 本次提交前验证

精确暂存树隔离验证：6项宪章/机器治理/历史治理/Experience门禁通过；治理发布及Instagram受影响19项检查通过。没有运行无关全产品本地测试；新提交的线上CI另行核实。相关日志固定于本地semantic-repair-20261008-002702备份目录的FINAL-RULE-VERIFICATION.json。
