# REQUIREMENT COVERAGE — 2026-10-04

> 本台账是 `USER-ADDITIONS-20261004.md` 的逐项溯源与交叉核对证据，不是执行路由、产品规则、任务队列或 R/J/U 编号。规则权威仍属于所列 CURRENT 文档；表中章节目标已落到本批现有领域合同，表示规则覆盖，不表示源码实现或运行验收。退出证据是要求达到的真实结果，不表示当前已经存在。

| # | 需求原文／条件（保留语义） | 现有负责 C 窗口 | 规则Owner与本批实际章节 | 必需真实退出证据 |
|---:|---|---|---|---|
| 1 | 更新相关规则并通知窗口；前端继续暂停，不因规则更新恢复执行；视频须等用户确认恢复后才分析 | C1、C2、C3+C5、C4、C6；F（暂停状态） | `AGENTS.md` — “Latest collection and result continuity”；各现有窗口状态记录 | 当前规则在线/本地字节一致；F仍暂停且无研究、代码、测试或新任务；无视频帧分析，直到明确恢复 |
| 2 | 产品除官网外的非必要操作不得要求上下滑动；官网豁免 | F；页面所属 C 窗口提供真实任务与交互 | Experience Constitution — §38 “Current frontend reference scope and scrolling” | 已恢复后在所有非官网运行表面以真实任务验证必要内容/操作可达且非必要纵向滚动不存在；Website单独记录豁免 |
| 3 | 按平台、品牌及商业主体相关话题建立对应话题词条库 | C1 | Global Universe Context & Data Maturity CURRENT — §10 “Task-semantic vocabulary and continuous acquisition” | 词条有平台、品牌/商业主体、来源及时间范围依据；真实采集/刷新结果能回指词条和主体，错误或未知范围明确呈现 |
| 4 | 按采集任务语义编写话题采集词条；禁止自行编造 | C1；C5（目的查询消费） | Global Universe Context & Data Maturity CURRENT — §10 “Task-semantic vocabulary and continuous acquisition” | 真实任务语义→可审阅词条→采集查询的来源链；无任务/Source语义依据的词条不进入正式查询；派生查询不冒充平台实测热词，范围外/歧义诚实处理 |
| 5 | 采集起点为 2026-01-01，按真实发布时间／事件时间持续采集，不得中断 | C1；C6（调度运行） | Global Universe Context & Data Maturity CURRENT — §10 “Task-semantic vocabulary and continuous acquisition”；AGENTS — “Latest collection and result continuity” | 以真实 publication/event time 证明从 2026-01-01 起的覆盖、游标/缺口/补采；产品自有 Scheduler 持续运行与断点恢复记录，不能以采集时间冒充发布时间 |
| 6 | 其他任务运行时采集仍持续；平台可依次轮换采集 | C1、C6 | AGENTS.md — “Latest collection and result continuity”；Global Universe Context & Data Maturity CURRENT — §10 “Task-semantic vocabulary and continuous acquisition” | 多任务负载下产品 Scheduler 的轮换、任务公平性、进度/延后状态和恢复记录；不能依赖 Codex/CUA/开发者触发 |
| 7 | 平台验证问题由产品/Owner研究解决，不应默认要求用户手动处理；不得伪造验证成功 | C1、C6 | AGENTS.md — “Latest collection and result continuity”；Security Boundary CURRENT — 平台授权与挑战边界 | 对真实账号授权/验证状态的机器可读核验、恢复或明确 BLOCKED；截图和口头“完成验证”不是机器凭证 |
| 8 | 不得绕过人机/身份/平台验证；通过合法会话、官方 API 和恢复机制减少重复人工操作 | C1、C6 | AGENTS.md — “Latest collection and result continuity”；Security Boundary CURRENT — 平台授权与挑战边界 | 官方 API/授权和允许的会话续接实际成功，挑战触发时安全停下并可恢复；不得绕过挑战或承诺免封 |
| 9 | 产品保持自研；旧有接入属于旧集成；AI GPU 训练是独立能力与证据链 | C2、C6；按旧集成归属的现有 Owner | AGENTS.md — “Latest collection and result continuity”；Source Owner Index — “Current combination acceptance” | 自研网关/模型、旧集成、GPU训练的Owner及数据/版本边界可追溯；各自独立真实运行证据，不以旧接入或训练准备替代新模型能力 |
| 10 | 真实材料进入真实任务，产生有用成果；成果可保存、修订、重开、恢复，运行版本与证据一致 | C1、C2、C3+C5、C4、C6 | REAL-DELIVERY Overlay — “Normal success and change continuity” | 同一真实材料贯穿入口、任务、可见成果、版本与Evidence；保存后重开/修订/恢复一致，断点后可复原，Evidence标识匹配实际运行版本 |
| 11 | 采集窗口同时提供符合要求的采集结果文字和图像示例，供未来前端参考；不是当前恢复F | C1；F（仅未来参考，现暂停） | AGENTS.md — “Latest collection and result continuity”；材料所有权合同 — “2026-10-04 updates” | 采集真实结果对应的文字、原始/许可图像、来源与范围标注及视觉示例；仅记录/保存，F未恢复前不执行前端研究、代码或测试 |
| 12 | 组合：采集＋主体＋Evidence＋事务应回答具体业务问题，不是帖子堆积 | C1、C5、C6 | Source Owner Index — “Current combination acceptance” | 真实目的查询→精确主体→Evidence→事务/正式记录→业务问题答案；相关性、刷新、失败和恢复均可读回 |
| 13 | 组合：Task＋Word制作＋SavedWork；重试不重复，取消不误提交，修改保留父版本 | C4、C3、C5、C6 | Source Owner Index — “Current combination acceptance”；REAL-DELIVERY Overlay — “Normal success and change continuity” | 同一真实Word任务实测重试幂等、取消无提交副作用、DOCX与SavedWork版本一致、编辑保留父版本且可独立重开；不能把链路缩成导出按钮 |
| 14 | 组合：研究资料＋多种创作格式；资料正常消费可用，不重复输入Brief/资料，修改约束后续作 | C3、C5、C4、C6 | Source Owner Index — “Current combination acceptance”；REAL-DELIVERY Overlay — “Normal success and change continuity” | 同一真实Brief及研究材料进入文稿/视频/播客等格式；约束修改后继承上下文继续创作、保存/重开/导出，来源可追溯 |
| 15 | 组合：训练＋权限＋远端进程＋Artifact；可重复训练、恢复、评估、晋升与回滚 | C2、C6 | Source Owner Index — “Current combination acceptance” | 授权远端作业真实执行、Artifact字节可取回且校验、断连/取消可恢复、重载评估有独立held-out及业务结果，受控晋升和回滚可操作 |
| 16 | 组合：编辑＋替换＋渲染＋保存；修改局部不破坏作品，成品继续可编辑 | C4、C6；F仅在恢复后 | Source Owner Index — “Current combination acceptance”；REAL-DELIVERY Overlay — “Normal success and change continuity” | 真实作品局部编辑/素材替换/渲染/保存后可继续编辑；失败、取消、恢复不丢失旧版本或破坏无关片段；F暂停期间不声称页面已验收 |
| 17 | 组合：来源更正＋判断＋成果版本；错误出现后定位并修订所有相关结论和成果 | C1、C3、C5、C6 | Source Owner Index — “Current combination acceptance”；REAL-DELIVERY Overlay — “Normal success and change continuity” | 更正来源可沿Evidence/父版本关系定位受影响判断和成果；逐项明确采用新来源、受影响修订、原因、旧版保留及回滚结果 |
| 18 | 非空 `brief_ref/evidence_refs` 当前触发 `INTERNAL_PITCH_SOURCE_BINDING_REQUIRED`；真实研究→AI提案正常路径仍是缺口 | C3、C5、C6 | Source Owner Index — “Current combination acceptance”；REAL-DELIVERY Overlay — “Normal success and change continuity” | 带真实非空Brief与Evidence的正常入口成功生成提案，来源绑定/引用/权限及保存重开一致；拒绝路径单独记录，不能代替成功路径 |
| 19 | `owned_model_execution=NOT_RUN` 不得被当作分析或AI成功 | C2、C3、C5、C6 | AGENTS.md — “Latest collection and result continuity”；Source Owner Index — “Current combination acceptance” | 成功状态要求实际调用受支持的自研模型并有运行版本/输入/输出/Evidence；NOT_RUN只能呈现未执行/不可用，不能记分析成功 |
| 20 | 国内语义必须区分同名商业主体、跨城门店、历史与当前、品牌自述与消费者反馈、广告与自然讨论 | C1、C3、C5 | Global Universe Context & Data Maturity CURRENT — §10 “Task-semantic vocabulary and continuous acquisition”；Source Owner Index — “Current combination acceptance” | 非参考商业/品牌及跨区域真实样本上，最终结果正确区分实体、地点、时态、主张来源与广告属性；歧义不静默合并 |
| 21 | 在材料、任务、预算相同条件下比较成果正确性、可编辑性及人工补救需求 | C2、C3、C4、C5、C6 | REAL-DELIVERY Overlay — “Normal success and change continuity”；Source Owner Index — “Current combination acceptance” | 固定同一组真实输入、任务和预算/资源约束，保存可复核的正确性、编辑操作完成度与人工修复次数/类型；不得选择性换输入 |
| 22 | 完整流程：品牌任务→定时限/范围资料→带预算资源约束方案→可编辑文稿/视频/播客 | C1、C2、C3、C4、C5、C6 | REAL-DELIVERY Overlay — “Normal success and change continuity”；Source Owner Index — “Current combination acceptance” | 一项真实商业/品牌任务贯穿来源时间与范围、预算约束方案、至少所需可编辑交付物；任务、Evidence、版本和预算关联可重开核对 |
| 23 | 来源或预算变化后定位受影响处，明确采用新版，只修改相关内容 | C1、C2、C3、C4、C5、C6 | REAL-DELIVERY Overlay — “Normal success and change continuity” | 变更触发影响图；用户/授权操作明确采纳新来源或预算版本，仅受影响内容被修订，未受影响内容保持不变并可核对 |
| 24 | 保留旧成果、修订原因与回滚能力 | C3、C4、C5、C6 | REAL-DELIVERY Overlay — “Normal success and change continuity” | 新旧成果与父版本、原因、Evidence/预算快照可读；执行回滚后实际恢复正确版本，审计记录可查 |
| 25 | 优先事项：远端训练正常链，证明实际加载、优化 step/loss、checkpoint 字节、重载、取消及断链结果 | C2、C6 | Source Owner Index — “Current combination acceptance”；AGENTS.md — “Latest collection and result continuity” | 唯一获批 RTX5090 路径的真实远端加载和优化步骤/loss；checkpoint原始字节/哈希、独立取回重载；取消与网络断连恢复结果；不得以本地检查或CPU演示替代 |
| 26 | 优先事项：训练与业务推理配方一致；同模型、配方、token预算下产生正常Gateway业务结果 | C2、C3、C5、C6 | Source Owner Index — “Current combination acceptance” | 训练、评估和Gateway推理的模型/配方/token预算版本对齐；真实业务输入经Gateway得到可用且有Evidence的结果，并保留配置与运行版本 |
| 27 | 优先事项：研究到创作来源传递；同一真实Brief和来源可继承、修改、保存、重开、导出 | C3、C5、C4、C6 | Source Owner Index — “Current combination acceptance”；REAL-DELIVERY Overlay — “Normal success and change continuity” | 同一Brief/来源跨研究到创作无重复录入；变更后关系正确，保存、重开、修改、导出内容与来源版本一致 |
| 28 | 优先事项：目的查询进入真实采集；正确范围、相关性、正式记录、刷新及恢复 | C1、C5、C6 | Source Owner Index — “Current combination acceptance”；Global Universe Context & Data Maturity CURRENT — §10 “Task-semantic vocabulary and continuous acquisition” | 真实目的查询在批准Subject/BrandFocus范围内采集；非参考样本相关性与主体识别正确；正式Source/Evidence记录、重复刷新幂等及失败恢复可验证 |
| 29 | 优先事项：同版本集成与环境复现；main、overlay、构建、加载、DB和任务成果一致 | C6及相关Owner | Source Owner Index — “Current combination acceptance” | 精确main提交/overlay/依赖/构建/模型加载/DB路径/任务成果指向一致版本；独立复现结果、迁移与运行证据可回读 |
| 30 | 优先事项：前端恢复后真实操作，覆盖AI提交、横向时间轴、来源与编辑；F恢复前不得擅自执行 | F（暂停）；C4、C6（提供业务结果/合同） | Experience Constitution — §38 “Current frontend reference scope and scrolling”；材料所有权合同 — “2026-10-04 updates” | 仅用户明确恢复后，按真实任务验收四端相应交互、AI提交、横向时间轴、来源、编辑、真实成品、保存重开；恢复前无代码/研究/测试 |
| 31 | 前端参考限定：当前两段视频＋此前五段＋已有分析资料＋OpenAI官网/官方当前规则 | F（暂停） | Experience Constitution — §38 “Current frontend reference scope and scrolling”；材料所有权合同 — “2026-10-04 updates” | 建立输入清单并保留出处；F明确恢复后才研究指定范围；旧档案留存但不继续扩展穷尽式历史视频研究；不得伪称已逐帧分析 |
| 32 | 两段新视频逐帧分析，历史其他视频不再额外耗时；此前五段与已完成分析作为范围内输入 | F（暂停） | Experience Constitution — §38 “Current frontend reference scope and scrolling”；材料所有权合同 — “2026-10-04 updates” | 仅恢复后对明确范围逐帧覆盖并记录帧时间/观察/设计映射；本轮不读帧、不补做历史视频分析 |
| 33 | Web Workspace、Desktop、Mobile及官网参考Manus；启动页参考对应录屏；官网增加Manus式创意操作视频 | F（暂停） | Experience Constitution — §38 “Current frontend reference scope and scrolling”；材料所有权合同 — “2026-10-04 updates” | 恢复后记录各表面的参考映射；启动页、官网文字/交互/操作视频分别落入屏幕规格；原创演示和参考原则不复制专有素材；实际流程/状态可核对，不仅静态叙事 |
| 34 | 图标兼具常规线性图标与彩色手绘质感图标；依照用户所示风格 | F（暂停） | Experience Constitution — §38 “Current frontend reference scope and scrolling” | 恢复后用指定图像/录屏建立风格依据与图标覆盖，检查线性和彩色手绘两类在实际任务中的层级/可辨识性及多端一致性 |
| 35 | 全产品覆盖视觉呈现、功能呈现、布局、UI/UX、AIGC，并合理规划UI与AIGC比例 | F（暂停）；各 C Owner给出真实能力合同 | Experience Constitution — §38 “Current frontend reference scope and scrolling”；Source Owner Index — “Current combination acceptance” | 恢复后覆盖Public Website、Web Workspace、Desktop App、Mobile Companion的屏幕规格、真实绑定/功能状态及UI/AIGC比例理由；单一Experience Constitution审批，四端实际操作验收 |
| 36 | 官网可纵向滚动；非官网产品表面的非必要纵向滚动禁止 | F（暂停） | Experience Constitution — §38 “Current frontend reference scope and scrolling” | 四端逐屏检查任务流程、滚动行为、键盘/触控/窗口尺寸；网站按其内容需要保留豁免；以真实页面运行证据确认 |
| 37 | 收到的抖音专用窗口验证截图与“已完成验证”回复不是当前登录、账号授权或平台验证机器凭证 | C1、C6 | AGENTS.md — “Latest collection and result continuity”；材料所有权合同 — “2026-10-04 updates” | 由现有会话Owner通过安全状态接口核验当前账号、授权、挑战状态并记录结果；无机器凭证标UNKNOWN/BLOCKED，不从截图推断PASS |
| 38 | 前端明确仍不执行代码、研究、测试或新任务，保留手选模型；无需额外ACK/核对/研究，等待明确恢复 | F（暂停） | Experience Constitution — §38 “Current frontend reference scope and scrolling”；材料所有权合同 — “2026-10-04 updates” | 当前无F实现/研究/测试或新任务；不改用户模型选择；只有直接、明确恢复指令才改变暂停状态 |
| 39 | 所有新增要求保持最大完整成果执行，不将完整用户结果缩成最小函数/阶段 | C1、C2、C3+C5、C4、C6；F依其暂停门 | REAL-DELIVERY Overlay — “Normal success and change continuity”；AGENTS.md — “Latest collection and result continuity” | 每个适用窗口以完整真实用户工作闭环、保存/重开/恢复及相应验收证据结束；不得用部分代码、测试或候选材料替代 |


| 40 | Instagram、Facebook、微信公众号、小红书、抖音、X是六主平台；IG/FB/公众号现在开始，既有其他平台不删除 | C1+C5+C6 | AGENTS Latest collection and result continuity；Global§10 | 六平台逐项实际查询/访问/采集/正式入库/消费/刷新/恢复及真实缺口，非平台注册=开始；单平台受阻其余继续 |
| 41 | 三格式基础测试主体词条库以后进入序境运行，以附件原始版本为输入 | C1+C5+C6 | Global§10；Owner Index Current combination acceptance | XLSX/CSV/JSON实际shape/字段/确认状态/一致性/hash核对；现Source/registry/permission/intake路径进入可部署的正式任务，不依赖开发者附件路径、不能当作已采集覆盖 |
| 42 | 词条随时间、商业主体、品牌、活动、事件持续更新，原词条不删除 | C1+C5+C6 | Global§10 topic vocabulary versions；Real Delivery change continuity | 不可变原种子/既有词条，新增版本、变更原因/来源/有效区间和当前活跃视图；保留旧版本检索与回滚，失效词条不误用于当前范围 |

| 43 | 用户已核对词条，不重做人工确认；100词条/41源/4已列主体及UNKNOWN热度按原字段处理，不能当100主体或已核热榜/全平台覆盖 | C1+C5+C6 | Global§10 User-reviewed foundation vocabulary seed；本批SEED intake | 按原pins/schema/身份来源层级进入正式查询任务；保留原文件/旧词，版本增补与可部署入库；不自动入训练或冒称热度 |

## 覆盖计数与未决映射

- 共 **43 行**独立要求/组合/优先事项/前端范围约束；组合为6行，优先事项为6行，均逐项展开。
- 现有源码Owner映射在本批Source Owner Index组合表：SYSTEM Collector/Browser/Scheduler与subject_registry.py；Shared Evidence/Database；Shared Content/internal_pitch.py/Timeline/Artifact/Task；SYSTEM AI Gateway/owned training；Shared Evaluation/Learning/Reporting和现域工作流。缺少正常callable是该Owner的实现缺口，规则不能凭表造接口。
- 自研产品、旧集成、GPU训练分证据；公开基础权重与既有许可适配仍按当前Gateway/第三方登记，不能将其整体替代序境。具体运行材料/源/hash/入口由现Owner回执验证；本台账不把截图/准备/候选/检查升级为完成。
- 前端全部保留 F PAUSED；第31–36行仅记录未来明确恢复后的研究/验收范围，不构成本轮研究授权。
