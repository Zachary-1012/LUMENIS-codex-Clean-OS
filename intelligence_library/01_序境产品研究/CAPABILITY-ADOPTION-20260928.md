# 能力原文的核对与执行映射

用户于 2026-09-28 提供《能力.docx》，并明确其中有过时描述，需要优化更新。
全文保存在 [带段落编号的原文](CAPABILITY-AUDIT-SOURCE-20260928.md)，不缩减能力范围。
本表是资料采用记录，不是新架构、Owner、Round 或完成证据。

## 已确认需要纠正的陈述

- 文档引用 `379772ff` 和动态 dirty 数量，是历史快照。采集短正文及页面身份修复
  已到 `86382707`；不能用旧数量作为当前进度，也不能把 dirty 源码算作已交付。
- 文档的 Context 已完成说法需区分 main 与本地候选：当前发布的国家关系投影
  不等于 GET/PUT/DELETE context 完整用户流程已发布。前端已收到纠正。
- Mapping、采集配置、DB registry、UI 可见数量不同，本身不证明有多个真相源；
  应沿现有平台目录分清字段支持、入口可用、运行健康、权限、实际字段覆盖，
  修正冲突的调用方，不新增第二个 Capability Authority。
- `SESSION_EXPIRED` 不能仅凭端口或缺少旧 Cookie 字段推断。当前专用浏览器的
  RedNote self 导航匹配批准香港账号，但旧校验要求 `x-user-id-pro`，产生误判。
  已在既有 Collector/Browser owner 修正候选；真实采集仍须完成。
- 8 类内容生成、9 个内存 Skill、API 数、ready、测试/build 数是资料中的陈述，
  不是已验收的原创新内容、视频、播客或报告。按真实 Job/Artifact/reopen 验收。
- 数据质量的缺失状态、AI accuracy 的标注分母、recovery_count 的指标含义需
  在对应能力执行时核实，不能复制旧阈值就宣称专业质量或运行完成。

## 全部 34 节的保留与执行位置

“当前”指本轮数据、前端、内容任务可直接推进；“后续”保留在原 15 轮，
没有删项或新增平行计划。具体源文件由 Source Owner Index/locator 定位。

| 原文节 | 保留的能力 | 当前采用/更新 | 现有负责域与检查点 |
|---|---|---|---|
| 1 | CTH/BMP/Shared/SYSTEM，AI/ACC 表面 | 保留双业务域，AI/ACC 不升格成新 Truth 域 | Product Architecture，R01–02 |
| 2 | 源码/API/表规模 | 仅历史观察，不以数量算完成 | Current truth，R01 |
| 3 | ACC身份、Global/Focus、恢复 | 当前上下文/国家角色/返回；账号密码后置 | Identity/Permission + Experience，R04/08/14 |
| 4 | CTH01–10，经营、反馈、事件、案例、风险、报告 | 当前真实数据可消费性；后续业务Job完整验收 | CTH，R10–11 |
| 5 | BMP01–11，品牌市场、传播、Creator、活动、播客、对标 | 当前 BrandFocus exact scope 和内容链；后续对应Job | BMP，R12–13 |
| 6 | AI01–05，任务、依据、进度、执行 | 当前仅接已拥有的任务/依据入口；非本轮Provider扩张 | AI表面/SYSTEM，R07/14 |
| 7 | Gateway发现、路由、本地推理、脱敏、缓存、预算、容错 | 保留；当前不因资料增加模型/云服务 | SYSTEM AI Gateway，R07 |
| 8 | Skill执行、跨源搜索、镜头、提炼、封面、最近变化 | 当前内容任务复用可执行Skill，逐个验证非计数验收 | Shared/SYSTEM Agent，R07/13 |
| 9 | SH01–06 创作、Evidence、Canonical、报告、学习、通知 | 当前真实数据/Artifact入口；其余后续验收 | Shared/Experience，R07/14 |
| 10 | Evidence完整性、签名、scope、失败、DLQ、lineage | 当前采集强制保留，不以重新签名掩盖旧证据缺失 | Shared Evidence，R04/06 |
| 11 | Canonical ID、去重、时间、scope、同步 | 当前更新、幂等、来源和缺失状态；不重建表 | Shared Canonical/DB，R03/06 |
| 12 | 地点、国家、实体、Tenant关系及有效时间 | 当前各国家50+50及真实关系；HQ/经营/所在地分开 | Shared DB/Registry，R03 |
| 13 | 20类字段、14类运行配置等层级 | 当前逐平台字段覆盖与入口状态核对；无效能力不假启用 | SYSTEM Collector，R06 |
| 14 | 采集、过滤、队列、风控、恢复、调度、健康 | 当前平台链与每天到期维护；无Cookie维度等价逐项验证 | SYSTEM Collector/Runtime，R05–06 |
| 15 | 8类创作、研究上下文、质量维度 | 当前原创Brief/方案/文案等真实交付，不只发Prompt | Shared Content，R13–14 |
| 16 | 叙事、白描、情绪体验、视觉母题、镜头 | 当前内容团队纳入学习/原创规则和审阅，保留来源边界 | Shared Content，R13 |
| 17 | 媒体指纹、Timeline、EDL、音轨、转场、叠层 | 当前沿原系统闭合render/Artifact/Evidence/reopen | Shared Content，R13–14 |
| 18 | Creator/KOS/KOL/KOC/UGC、合作、归因、成本、投放、奖励 | 当前保留真实输入维度；投流/奖励/邮件外部动作延期且须批准 | BMP/Permission，R12–13 |
| 19 | Topic/Campaign运行、恢复、回填、时间线、导出 | 当前采集数据入口及恢复；后续完整Campaign Job | BMP + SYSTEM，R06/13 |
| 20 | Podcast研究、实体、故事、选题、衍生内容 | 当前scope候选与原创音频Job；不能以研究接口代替成片 | Shared Content/BMP，R13 |
| 21 | PR案例、方法论、危机SOP、事件关系 | 数据层保留消费入口；当前不另建案例系统 | CTH/Shared，R10–11 |
| 22 | 周期/专项报告、导出、Artifact、stale、reopen | 当前数据闭环至少真实结果；内容复用既有输出 | Shared Reporting，R11–14 |
| 23 | 事件、风险、情感、传播主体、事实状态、周期分类 | 当前采集保留可依据事实；衍生判断需方法/版本 | CTH/BMP/Reporting，R10–13 |
| 24 | Data/AI/Collector/Report/Runtime评价 | 当前采集刷新/恢复验证；旧阈值与accuracy不盲采纳 | Shared Evaluation，R07/15 |
| 25 | Feedback/Pattern/Suggestion/Promotion/Rollback | 当前研究沉淀；后续按真实反馈晋升，不自动改Truth | Shared Learning，R07/15 |
| 26 | Permission、风险、资源、scope、Fence、幂等 | 当前采集/文件/效果边界不弱化；账号墙后置不等于取消授权 | SYSTEM Security，R04 |
| 27 | 浏览器标签、导航、下载、提取、受控任务 | 当前仅采集必需断点；完整内置浏览器保留后续既有owner | SYSTEM Browser，R06/14 |
| 28 | SYS01–08健康、采集、DB、安全、设置、验收、日志 | 当前可见真实健康/缺口与恢复；不可用不能写ready | SYSTEM/Experience，R05/14 |
| 29 | Guardian/worker/heartbeat/circuit/recovery/cache/alerts | 当前自运行持久状态；后续长期运行恢复验收 | SYSTEM Runtime，R05/15 |
| 30 | Website/Web/Desktop/Mobile | 当前已批准前端任务，四表面共享Core；平台build不等于实机验收 | Experience，R08–09/14–15 |
| 31 | Identity到Experience的语义维度全集 | 作为字段/能力回查入口保留；不并成单一country或source字段 | 现有各Owner，R03–15 |
| 32 | 不可误判完成的清单 | 保留；账号/订阅/模型扩张等当前延期，部署另验收 | 原依赖轮次/R15 |
| 33 | 真实资产与Events/Reports缺口 | 历史数值不继承；后续业务功能必须消费正式数据 | CTH/BMP/Reporting，R10–15 |
| 34 | 从来源到学习的全链 | 保留为业务验收路径，禁止仅因schema/接口存在宣布闭环 | 原15轮累计验收 |

## 当前任务反馈

前端与 Content & Creation 线程已收到按章节的精确增补，不要求重做总体规划。
采集的 GitHub/官方来源比较见
`../07_Data-Evidence-Evaluation/COLLECTOR-CONTINUITY-RESEARCH-20260928.md`。
后续进入任一能力时按上表回查完整原文及对应既有研究，再依据当前源码与
最新用户决定 ADOPT / ADAPT / DEFER / REJECT。延期能力尚未完成；本表不升格其状态。
