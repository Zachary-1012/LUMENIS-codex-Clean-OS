# OpenAI Math 定向深读与现有能力应用

## 2026-10-12 当前采用：后端分析、检索与自研模型分别验收

本节接续已批准 v2 与下面固定原文/实际有限实现，不替换附件、不把旧日期研究
当当前运行结论。数学用于 SYSTEM、CTH、BMP、Shared 和 Agent/自研 AI 的现有
后端能力及研发正确性；普通用户提供业务问题/条件，获得分析后的成果。源码、
有限例子、形式证明、求解器输出和模型收益各自记证据，不能互相替代。

### 现有检索入口与本轮具体接入

2026-10-12 只读源码定位基线为 `1fdb23d27da9f7f15d5dc0a2ab723e8befc371af`
及受保护本地工作树；以下描述是读取范围，不证明已发布或真实产品验收。

| 现有入口 / Owner | 已有能力与明确缺口 | 同一 Owner 内的下一动作与验收 |
| --- | --- | --- |
| C5 `lumenis/shared/reporting/saved_work.py::search_work`；C6 `experience_runtime.py` 调用 | 已有权限、scope、版本/引用读回；当前检索为标题/正文子串与有界记录扫描，不能叫 Hybrid | 复用原查询/结果身份与分页合同，补可重建派生词法索引及候选检索；证明历史成果可搜、来源撤回即拒绝、排序与分页稳定，再接向量/重排 |
| C5 `lumenis/shared/learning/content_assets.py::retrieve_pattern_candidates` | 有 scope/platform/format/audience/objective 筛选；按现有输入次序截取不能证明相关性 | 先保留已晋升/权限/用途筛选，接同一检索候选与明确打分，不把学习候选或排序写成 Canonical 事实 |
| C2 `lumenis/system/ai_gateway/core.py::local_embeddings/search_enhance` | 退役入口明确不可用；不能通过重新启用旧 Provider 获得向量或搜索 | 从现有获准模型/资源核实能力，再绑定同一 Gateway 的 embedding 与 cross-encoder；记录模型/分词/归一化/版本与真实推理；没有模型时保留正常词法业务，不能谎报完整 Hybrid |
| C3 领域查询；C1 来源；C6 API/持久化；F 用户操作 | 实际任务、来源身份/时间/权益、版本与成果链已各有 Owner | 冻结真实业务查询和许可语料；权限过滤后双召回、稳定身份融合去重、精排，再返回引用/正文与可继续成果；用真实保存/修改/重开/恢复验证接线 |

生产增强的完整次序为：actor/scope/rights 过滤 → 余弦向量召回 + BM25 →
按 Source/Evidence/Canonical/version/chunk 身份融合去重 → 已准入交叉编码模型
精排 → 原研究/分析/制作成果。身份/编号/别名的精确匹配另外保持，BM25 不是
字符串精确相等。不同分数不能直接相加；融合方法及参数以同语料独立查询对照
决定。SQLite FTS5 是可评估的现有库内派生索引路径，须验证实际运行可用性、
中英韩分词与安全迁移，不增加第二事实库；其 BM25 分数方向须按原文正确处理。
撤权同时约束两个召回与重排输入，不能先把越权正文送给模型再过滤输出。

验证在原 Evaluation 内比较 BM25、向量、融合、完整重排：相同语料/时间/scope、
独立查询与人工相关性标注，记录 Recall@k、MRR/NDCG@k、精确身份命中、引文
正确性、越权泄漏、P50/P95 延迟和资源。无有效比较基线不报提升百分比。
来源类别同权不取消真实性/时效/权益判断；结果空与检索故障保持区别。

方法来源：[OpenAI Retrieval](https://developers.openai.com/api/docs/guides/retrieval)
（融合/过滤参考，不授权其托管服务）、[SQLite FTS5 BM25](https://www.sqlite.org/fts5.html#the_bm25_function)、
[Sentence Transformers Cross-Encoder](https://www.sbert.net/docs/cross_encoder/usage/usage.html)。
来源核查日 2026-10-12；新依赖/模型仍需版本、许可证、资源和既有准入。

### 数学驱动自研 AI：从正确任务到真实模型增益

`lumenis/system/ai_gateway/research/openai_math_papers/gibbs_policy.py`、
`train.py`、`evaluate.py` 是有限支持上的小型策略实验。其 JSON checkpoint、
精确求解和 held-out 不等于 gpt-oss 的训练、加载或生产推理；原实验未获准/未运行
的记录保留，本文不自动启动训练。

1. C3/C5 从固定论文及实际业务提炼问题、变量、假设、约束、反例、可核验答案与
   适用验证器；先核对原定理及修订/撤回，不把一般理论界强套 LLM。
2. C5 沿现有 Source/rights/privacy/quality 确认每项材料允许的产品/训练用途，
   去重并隔离训练、验证、独立新任务；求解器生成标签标明生成方式，不冒充观测。
3. C2 先复核已有免费 Kaggle 训练、step/loss、配方/data/model hash 与可取回的
   adapter/checkpoint，复用有效成果。仅在现有 MODEL_TRAIN 等授权及真实免费
   资源成立时继续；本研究不新增模型、数据、外部 API、费用或部署授权。
4. 在既有训练/学习入口采用已核验的约束、评分/奖励或任务样本；记录是论文原
   算法、有限子实现或原创教学适配。不能只改提示名称就称论文驱动训练。
5. 取回 checkpoint、校验并实际重载，用同基座/同任务/同预算的训练前后模型
   跑未泄漏新任务及真实业务对照；核对事实引用、约束、校准、质量与资源成本。
   模型独立结果与模型加求解器结果分别报告，工具收益不得计作模型能力。
6. 真实推理通过唯一 Gateway 进入正常产品成果，再做保存/修订/重开/恢复。
   loss 下降、checkpoint 存在、solver 正确或评估脚本成功均不单独关闭模型验收。

### 九项主算法与研发采用的未闭动作

下面完整主算法仍由 C2/C5 Math 与对应业务 Owner 保留原升级义务；表中动作补齐
原缺口的执行方向，不将它们降为可选项。输入假设不适用于某项业务时，改用
正确的已有确定性方法并记录理由，不能伪造适用性或宣称一般论文已实现。

| Family | 下一项必须核对/实现的原缺口 | 通过条件与误用防护 |
| --- | --- | --- |
| 102 | 固定归约、问题编码、承诺条件与主定理实际证明范围 | 合法/反例对照及证明重放；满足率不冒称困难性归约实现或求最优 |
| 103 | 一般机器/随机带、状态和空间资源模型及去随机化构造 | 与固定原算法同语义/资源界的重放；有限转移枚举不代表一般算法 |
| 104 | 获胜集算法、策略量词与随机复杂度链 | 验合法策略和反例、资源与误差；单策略循环收益不等于全局获胜集 |
| 107 | 原张量提取与实际乘法程序、算术/位成本及适用尺寸 | 输出精确核对与同负载成本；符号恒等或指数结论不自动提升业务计算 |
| 113 | 一般图 FPRAS、面结构/优化及精度/概率界 | 小规模精确基线、一般实现条件、正式命题重放分别验；熵不是业务质量分 |
| 114 | 一般独立性 oracle、公共基算法与完整随机带成本 | 验 oracle 前提、算法误差和实际总成本；分割拟阵枚举不代表一般实现 |
| 115 | model/graph/signatures/transport/dense/algorithm 链及采样器 | 验边际/可行域/分布/资源；合成条件表不补实际覆盖和未知事实 |
| 139 | 一般势/oracle 子算法与采样/误差/成本链 | 先证强凸/光滑等前提，再验独立采样和总成本；少查询不等于整体提速 |
| 140 | 条件标签/副本恒等、精度与有限内存模型的实际重放 | 严格区分固定模型下界与经验 LLM 对照；不宣称通用模型下界 |

研发使用同一方法：先冻结正常任务含义和独立验收，再实现/检查合法输入与
反例、跨域身份/版本/权限传递和恢复；只有数学条件实际匹配的代码才采用
对应算法或证明。不能声称每段产品源码都由论文证明。原文阅读、主算法、
形式证明、实际用户结果和训练收益分别补齐，未闭事项不以空白/DEFER消失。

## 2026-10-10 v2 源码采用与真实产品操作（当前增补）

用户指定 v2 ZIP SHA-256 `92e0d17982010b55d9043405164e9b5de79cab9ef053bdbb53ede1963d4607aa`，37 个清单文件经完整性核验，23 个 Python 文件已审查/编译；未使用 v1。原件/缓存/失败记录保留在受保护本机证据目录，不进入产品导航或再造候选实现。

本次固定上游 `openai/math@fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb`；12 个直接对应原文/声明源逐一核 Git blob，不把论文标题/引用数当实现。上游 Oct-7 撤回三份 Hodge/Weil/Kuga-Satake 稿件及其他修订已核；选中的九 family 未在该撤回名单中，不等于所有数学结论已由独立审查确认。末尾旧研究按其日期保留，不能覆盖此处当前有限源码状态。

| Family | 本轮真正实现 | 完整主算法未闭合项 |
| --- | --- | --- |
| 102 | 精确有限约束满足率，保留重复边 | 困难性归约/主定理，不是优化算法 |
| 103 | 固定转移表、时钟内的精确有理接受概率 | 一般 log-space 去随机化机器，不声称 L=RL=BPL 已进入产品 |
| 104 | 给定位置策略对的最终循环平均收益 | 随机准多项式获胜集算法与历史策略量词 |
| 107 | 除法无关算术程序语义和符号多项式恒等核验 | 9/4 张量提取及实测乘法程序，不替换 BLAS/CUDA |
| 113 | 有限完美匹配 Gibbs 分布、边际、协方差、数值熵；精确混合边际和原创有理 log 区间 | 一般图匹配 FPRAS、完整面结构/优化；实数定理重放不证明 Python Gibbs 数值等价 |
| 114 | 两个有效分割拟阵的精确公共基枚举 | 一般独立性 oracle FPRAS 及全随机带资源界 |
| 115 | 原式有理残差修正/首次成功律/平移/参数成本；有限均匀表枚举包装 | 完整 model-and-graph/signatures/transport/dense/algorithm 链及多项式采样器 |
| 139 | 有理二次势 I≤A≤2I 的精确合法性、值/梯度；数值密度 | 一般势/oracle 的次多项式查询采样器及独立成本测量 |
| 140 | 有理 Gram/投影/核与有限精度条件纤维抽样 | 等标签积分/副本恒等与样本-内存下界的实际解答重放，不能推广为 LLM 下界 |

以上是有限/公式实现与原创适配，不是九项主算法结项。精确有理数、数值 exp/log、严格区间和上游正式定理分别记录；113 的下界作用于具有同边际的最大熵，不能套给任意非最大熵分布。区间使用经典 atanh 展开及预先解析余项，明确非 OpenAI 新算法；Decimal Gibbs 概率不冒称得到 Lean 数值等价证明。

### 产品接入与实际证据

复用 Shared Evaluation → Task/API → 已保存 SourceBrief → Permission → SavedWork/Artifact。每次冻结声明问题、变量含义、输入 hash 和 SourceBrief hash；来源不是参数事实授权，情景计算不得写 Canonical。真实 CTH 来源简报包含 30 条核验记录/123 条候选，已截断，不声称全市场或随机代表性。API 已产生 v1 `ART-b005ab4593a14672`、修订 v2 `ART-8df1904fb6d54716`；同请求返回原 Task，旧/新版本可分别读回，JSON 导出 hash `db1a53f3b0f19b29afa27dd1e65ac2bce376c236d5f2d68a55cd208e42f58e62`，异域 BMP 读取 CTH 成果实际 403。AI 未调用。

Web 正常入口产生 `task_b1f7a984c05219ee` / `ART-b1ecdc9c91394d29`，暴露了执行 ACK 8 秒超时。已修为执行最多 60 秒、受权结果读回最多 30 秒，并把任务编号/重新打开移到失败时也保留的区域。原任务在页面刷新后已实际读回；最终修订/界面截图/恢复结果将在同一记录更新。当前 Runtime 入口仍包含受保护的原 C1 dirty，不冒称整个工作树为干净主线。

### 固定正式证明与模型边界

113 正在实际比较 `ComparatorChallenges.MatchingEntropyBounds` 与 `OAI.Combinatorics.MatchingEntropy.Main` 的 `OAI.MatchingEntropyBounds.Refined.pointwise_entropy`。允许公理仅 `propext`、`Quot.sound`、`Classical.choice`。工具为 Lean 4.34.1、Mathlib `d13f23b723b8a846827a245b89c10fc7d3f11612`、Comparator `d03acab154d269c06e60e4de7e4cc85deebff94b`、lean4export `076e8e57707e813375e8f9da8bf989799ace9680`，真实 Landrun 0.1.17，在非 root WSL/systemd AF_UNIX 隔离中运行。WSL Landlock ABI 7 与新版工具 ABI 9 的差异使用显式 best-effort 兼容并单列；不使用 fake-landrun。带 sorry 的 challenge 编译不是证明通过，重放最终日志尚待完成。

小型 Gibbs 参数策略：**已训练、未上线**（2026-10-14 只读核对本机既有回执，未启动新训练）。冻结合成有限图数据 24/6/8，数据 SHA-256 `aa72a7c3982da6fecfc55be3d06cf4c1041b7603ec7e07f5498d3f4f91dcf1f6` 已复算相符；跨 train/validation/holdout 使用不同图规模。既有日志记录 CPU 零费用预算内 5 epochs / 120 steps；checkpoint 120 的规范化 payload SHA-256 `1f5ff4874fa55c7fbf569d8025f188c98573afe0f3926312269ac0f913cf6f6d` 已独立复算相符。训练终态日志 FINISHED_NOT_EVALUATED 后另有 validation/holdout 回执，不能只读训练末行判定无评价。

既有独立评价日志：validation 6 项中 gold-match 5、约束有效 6，平均 NLL 0.4578612705730241250367291365（均匀基线 1.791759469228055000812477358）；holdout 8 项中 gold-match 6、约束有效 8，平均 NLL 0.9830274694911673753747682078（均匀基线 3.17805383034794561964694160）。这是合成有限图上的参数策略/精确枚举评价，不是行业数据收益、一般大图算法、形式证明或自研 LLM 增益；各行 business_result=NOT_EVALUATED。本轮仅读回并核对数据/产物完整性，未重新训练或重载模型执行。

回执目录 `D:/LUMENIS_REBUILD/gibbs-evidence-20261014`；同名 JSON 保留协议、同意记录、训练/评价日志 hash 及 checkpoint 文件 hash。PR #60 原始日志同步保存在 [训练](openai-math-gibbs-20261014/train.log.md)、[validation](openai-math-gibbs-20261014/eval-validation.log.md)、[holdout](openai-math-gibbs-20261014/eval-holdout.log.md)，不代表重新运行。consent.json 引用 PO-chat-approval2026-10-14T02:34+08:00；协议更早的待审批字段保留为历史，不重写历史材料，也不以回执产生新授权。实验代码 hash `adf1cdcbadf8a163bc4f593d5b7a55bcdf79ce6451e99ca52f128c4f411a7711` 由产物记录，当前主线训练入口与运行绑定未核实。不得修改或晋升 gpt-oss-20b；部署、业务结果和模型晋升未验收，G163 保持 OPEN。

九项一般主算法、全产品闭环、LLM 训练/新任务增益仍 OPEN。原批次未执行模块测试的事实保留；当前定向单元/集成回归按 2026-10-10 PO 恢复授权执行，同时保留编译、静态、安全、数学结果核验与实际产品操作。独立基础任务继续，不掩盖完整升级缺口；缺口沿原 Owner 继续解决。



本报告落实用户 2026-10-07 的 A/B/C 合并指令。它是现有 Product Architecture/Owner 的研究证据，不是新权威、模型训练许可或窗口派工。
固定上游：`openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a`；产品取证基线 `f6dac9216cbb331e730329a70513e0c90c306e73`。

## 结论与实施边界

研究覆盖指定的 102、103、104、113、114、115、139、140，107 的 DEFER 复核，以及 Lean/Comparator。复杂论文算法目前没有一项具备已证明的序境生产收益；ADAPT 针对问题定义、采样限制、成本口径、信息保持实验与语义验证纪律。ADAPT 不表示算法已经上线。
以下数学结果均为固定稿件中的作者主张及其证明路线；本轮研究不等于同行评审、独立证明复核或生产认证。形式化声明也仅对列明命题有效。

PRODUCT_ADOPTION 与 MODEL_LEARNING 分列；CANDIDATE 仅为待审方法卡，不是新的源代码候选树或获准训练集。现有材料、源码、状态机、Gateway、Permission/Evidence Owner 均保留。

## 跨 Owner 复用入口（修复已实施；其余业务执行仍按实际派工）

| Owner | 复用位置 | 下一步与通过条件 |
|---|---|---|
| C1 | acquisition_plan / canonical_data / task_queue | 把词条/查询覆盖与总体代表性分开，native cursor、server checkpoint、run/lease分别验证；真实来源进同一 Evidence链。 |
| C2 | owned Gateway / Agent / Memory / Evaluation | 固定模型、配方、Evidence、token预算，测记忆保持/引文/约束；owned未绑定则诚实不可运行，研究不代替训练。 |
| C3 | CTH/BMP决策、传播和业务流程 | 明确优化/可行性/计数目标，事实关联不升为因果；未知域与隐式Subject已沿现有调用链修复；复用本文末尾同版本验收，勿重建域规则。 |
| C4 | Timeline/Artifact/SavedWork | 复用同一来源/版本和约束；没有当前图计数或矩阵指数瓶颈，不引入数学框架；修订不得改来源身份。 |
| C5 | Source Brief/Research/citation/Evaluation | 保存原文假设、反例、时间/范围/rights；选中的最新8份资料不是市场概率样本；方法采用与训练准入分开。 |
| C6 | Scheduler/Permission/Gate/integration | 复用七项invariant、同版gate和恢复合同；不把随机博弈定理套作重试策略，不把schema有效当状态真实。 |
| F | Experience/现有ViewModel | 展示业务结果、采样范围、缺失、时间、来源与限定状态；配置READY/缓存VERIFIED不能显示业务完成；数学留在后端。实际开停由最新直接PO决定，本研究记录不调度窗口。 |

## 2026-10-09 数据分析无 AI 阻断与数学方法落实

依据最新 PO，数学研究首先增强序境的确定性数据分析、业务解释边界及研发正确性，不能只用于 GPU/训练，也不能把模型服务变成基础分析前置条件。本次复用上述固定上游与原文研究，不冒称新完成全部原文阅读、证明重放、算法上线或生产增益。

| 已核读方法 | 必须在现有能力中落实 | 原 Owner 与正常结果要求 | 当前证据/限制 |
| --- | --- | --- | --- |
| 102/113/114：可行性、优化、计数是不同目标；有解不等于最优，计数不等于推荐质量 | 既定业务任务写明目标、允许条件、输入身份/时间、预算与约束；复用现有确定性计算和人工决策，不用热度排名冒充最优分配 | C3 CTH/BMP 决策；C5报告/Brief引用其结果 | ADAPT 为现有分析与评价规则；复杂计数/oracle算法保持原 DEFER，未证明当前业务收益 |
| 115：固定边际的条件均匀表不等于真实来源总体代表性 | 真实来源按任务范围去重/分组/计数，记录分母、单位、来源与时段覆盖、遗漏/偏差；边际约束适用时核对总量。模拟或估计必须单列，不能补写未知事实 | C1 Source/Evidence/Canonical；C3分析；C5 `source_brief_job.py`/Reporting/SavedWork | PRODUCT method ADAPT；原 uniform sampler/FPRAS 算法 DEFER 不变；非概率选取资料不升级为随机代表样本 |
| 139/140：复杂度与信息保持结论依赖精确模型/资源假设 | 比较实际端到端耗时、输入/版本、记录覆盖与恢复后信息；区分查询数、计算/内存和模型请求；压缩/选取后明确遗漏 | C1增量采集；C3/C5统计/报告；C6运行/恢复与现有Evaluation | 方法 ADAPT，不能把理论查询界移用于社媒/API，也不宣称 LLM context/KV 下界或性能提升比例 |
| Lean/Comparator：声明通过不等于语义符合业务意图 | 核对源计算、接口、下游消费者和真实用户成果；基础分析完成状态与 AI 增强状态分开，使用真实失败/恢复证据 | C2 `ai_task_engine.py`；C6 Task/API；F显示原结果和增强可用性 | 当前 `_execute_analysis` 未产生有用基础计算，`_owned_ai_failure_code` 仍要求 AI 完成。OPEN；不靠删除失败判断或改标签冒称修好 |

产品链：获准真实来源 → Canonical 输入 → 既有确定性分析/人工判断 → CTH/BMP 使用 → 报告/Brief → SavedWork/Artifact → 保存、修订、重开、恢复、Evaluation。AI 的解释/关联/建议为可选增强，不覆盖输入事实，也不使这条基础链等待模型。缺少指标必需数据只限制相应结论，可完成的有用部分持续保存。

本次采用的是方法和可执行约束，实际算法/源码/Runtime/用户验收保持各自状态。此前研究正文的算法 DEFER、部分阅读、未重放证明和原失败证据保留；历史测试政策不是现行命令。当前沿根 AGENTS 的 2026-10-10 PO 授权执行必要定向单元/集成回归、编译/静态/安全/数据检查及真正用户级 E2E，孤立回归不能当业务验收。不新增数学框架、分析引擎、Provider、训练授权、开发窗口或独立验收体系。

## 深读与完整 Adoption Cards

每篇阅读范围、定理假设、证明机制、复杂度、对照、反例、形式化边界及完整卡片见以下合并正文；结构化字段同时保存在同名 JSON。PDF全页抽取不等于全页人工阅读，仓库声明形式化不等于本机重放证明。

正文中的缓存/manifest文件名指向本机总研究包；同名发布JSON嵌入原文清单。只引用公开原文和本库源码，不向仓库上传论文全文缓存。

---

## 研究正文：research-102-104-107

# OpenAI Math Families 102–104、107：深度原文研究与序境采用卡

**日期：** 2026-10-07
**研究源：** openai/math 固定提交 adc7f1241b42e322a6451854ab7e4b4c146bf78a，提交时间 2026-10-06 21:58:50 UTC。固定版本 README 列 722 篇 manuscripts、372 个 families，并明确不是所有结果都已形式化，未形式化结果可能仍有问题。
**输入：** C:\Users\28049\.codex\attachments\6736fa5d-c05d-4a83-b271-89d0a18b060f\已粘贴的文本.txt。
**产品基线：** checkout、origin/main、live refs/heads/main 为 f6dac9216cbb331e730329a70513e0c90c306e73。这是研究开始时的提交基线；源码阅读包含本地 owner/caller，app.py 等既有 dirty 文件不是线上发布证明。研究任务未修改任何 owner 文件或其他既有 dirty/untracked 项。
**范围：** 只研究 102、103、104、107 并映射现有 owner/caller。没有产品源码修改、产品测试、runtime/DB 探测、训练或 Lean 构建。

## 阅读覆盖与证据限制

全部 13 篇 PDF 按固定 commit 下载；用仓库 .venv Python 和 pdfplumber 记录页数及 SHA-256。以下页码为深入核读页；未列页面不代表逐行阅读。PDF 文本提取可能损失公式排版；这不是独立数学验证、proof replay、代码复现或性能实测。

| Family / 论文 | 页数；深入核读页 | SHA-256 | 未深入覆盖 |
|---|---:|---|---|
| 102 The Unique Games Theorem | 58；1–6、33–36 | 04d0290a9cb7ee815060f82cf556cee893d32b5255613160ca8b8d02a5fe1289 | 7–32、37–58 |
| 102 A Direct Proof of Optimal Max-Cut Hardness | 38；1–3；选读 27–37 相关定理/归约段 | 32a11e793f6e379c8d750f8f3560a6b0648bee56441efd25bceea9c2b7ffb849 | 4–26；27–37 非连续选段 |
| 102 The Factor-Two Hardness Threshold for Vertex Cover | 25；1–3 | 4c8faec31a1af3d0c640485e464ecedd99fb984f4a2c3b457f032685013804ab | 4–25 |
| 102 Constant-factor hardness of Min-UnCut | 38；1–3 | 3300408a7ae8900efc7ae23fc7ae3a4678750e57de9b5d89d063ff596c710100 | 4–38 |
| 102 Constant-factor hardness of directed feedback vertex set | 29；1–4 | 606657a956af61c2d133e59134ec98234d6e5386413ab601c1e7d493d1f0e4f2 | 5–29 |
| 103 Exact Derandomization of Logarithmic Space: L=RL=BPL | 108；1–7、92–98 | 15030fab23d31a4d91bd944100a547c3e9eff6da8330a4fb94ea999f071fadfc | 8–91、99–108 |
| 104 Deterministic quasipolynomial-time mean-payoff games | 27；2–4、16–24 | 5d8d8876fd2982fd3a1a1f751893b40d38f6d400b7d669cf3f49d920ae4193d0 | 1、5–15、25–27 |
| 104 Randomized quasipolynomial-time mean-payoff games | 41；1–7 | 4ab7552f58266134879a520c0d9a21a002438521e782418017ffe9bc1ecf23f3 | 8–41 |
| 104 Turn-Based Stochastic Mean-Payoff Games in Deterministic Quasipolynomial Time | 20；1–20 | 77e967a1db5965db666692bdd37226ed8eeb5223b8d355e614f23f0ebc0b007d | 全页文本核读，未独立推导 |
| 104 Mean-payoff parity games in quasipolynomial time | 14；1–14 | 78583f3170d29154e93c491ac9142abeb65bb45b6a0a5e8436fd30c5200fe3c4 | 全页文本核读，未独立推导 |
| 107 An Upper Bound of 9/4 for the Matrix Multiplication Exponent | 13；1–13 | 9c430672ddf2a1d0d2335c55c03b0b1fdea72f5a000c586bf130c2e984f19ae6 | 全页文本核读，未独立验证 |
| 107 Complex Matrix Multiplication Below 2.258 and Rectangular Bounds | 83；1–4 | 97ffc7fc55cae485ec1f001a6c4ece8a293215b1ecfc8f9ec50ef4913c8e9f0 | 5–83 |
| 107 Staggered extraction for exact matrix multiplication over every field | 35；1–3 | 85aa655473a156ad16db5bc59190d487a55db864d1014af0610c1c1f5b08490b | 4–35 |

[固定版本 README](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/README.md) · [固定版本 LICENSE](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/LICENSE)。仓库 LICENSE 为 Apache-2.0；索引未列逐篇额外许可。本轮仅做非逐字方法蒸馏；许可不自动赋予 MODEL_TRAIN 准入。没有论文全文、reasoning trace 或合成数据进入训练。

## 结论索引

| Family | PRODUCT_ADOPTION | 结论 |
|---|---|---|
| 102 | DEFER | 困难度下界不是求解算法；直接用作匹配/传播算法应拒绝。 |
| 103 | DEFER | 去随机化限定于 log-space、每条随机带 polynomial-time 的机器；未发现符合条件的现有子程序。 |
| 104 | ADAPT | 仅建议研究现有 Scheduler 的 shadow evaluator；目前没有校准概率/reward，不实施、不门控生产。 |
| 107 | DEFER | 9/4 是复数域渐近 arithmetic operation exponent，不是有限尺寸或 GPU 提速证据。 |
| 全部 | MODEL_LEARNING=CANDIDATE | 只表示可将非逐字方法/假设/反例卡另交 C2/C5 审查；未准入、未训练。 |

## Family 102 — Unique Games 与图近似困难度

### 原文结果、假设、构造和限制

Family 102 包含 Unique Games gap 与 Max-Cut、Vertex Cover、Min-UnCut、directed feedback vertex set 四个 hardness 结果。Lean 文档逐项列出这五篇及所声明范围。[Lean 范围说明](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/lean/docs/102.md)

- **Unique Games：** 对每个固定 ε、δ∈(0,1/2)，确定性多项式时间显式归约把二进制 3SAT 映射为非空、无权、简单、二分唯一游戏；SAT 值至少 1−ε，UNSAT 值至多 δ。字母表是依赖误差的固定 F₂^s，约束为平移。证明路线依赖 parity/3Lin gap、rank-one matrix shortcode、非线性 gadget、Fourier/低秩解码、Grassmann expansion/Khot–Minzer–Safra 逆定理与 alphabet-independent projection-game parallel repetition。参数需按证明顺序固定。
- **Max-Cut：** 对每个固定 α 高于 Goemans–Williamson 常数 α_GW（论文范围至 1），简单无权图上的 α-近似 NP-hard。论文构造 gap，不输出近似解。
- **Vertex Cover：** 对每个固定 m≥4，归约生成简单无权图；SAT 时 τ(G)<(1/2+1/m)|V|，UNSAT 时 τ(G)>(1−1/m)|V|，故任何固定 factor<2 均 NP-hard。构造用 Label Cover、Efron–Stein/product-space variance、resampling 与 derivative-list decoding；多项式常数依赖固定 m。
- **Min-UnCut：** 对每个固定 C>1，简单无权图上的 C-近似 NP-hard。证明使用 parity 起始 gap、Gaussian-sampled query、bit comparison、affine hint 与 soundness reduction。
- **Directed Feedback Vertex Set：** 对每个固定 A≥1，loopless 无权有向图上的 A-近似 NP-hard。证明用 2-to-1 game、拓扑序比较、Friedgut junta 列表、shared-prefix conditioning 与耦合比较，再转成无权图。

这些是困难度归约，不是 solver。它们约束普遍近似保证，不给具体产品数据上的最优候选、可行性、质量或运行时间。以 P≠NP 为前提的算法不存在性也不是“已证明 P≠NP”。

### Owner 映射、例子、基线

Source Owner Index 将品牌市场/creator/传播决策归 C3，要求基于真实来源判断 creator/channel fit，popularity 单独不够（J3/U10/U11，约 103–125 行）。当前 brand_propagation.py:136、305、351、433 定义查询和 heat_score 排序；experience_screens.py:1791–1828 的 BMP-04 读 dashboard。event_graph.py:548 是 topic-token/time-window relation heuristic；app.py:904–1000、1289–1298 暴露 graph stats/events/chain/create/rebuild。当前调用没有建立论文里的 SAT gap、Max-Cut、cover、Min-UnCut、DFVS 或 assignment 问题。

**具体条件例：** 如果已有 C3 job 明确要求把内容岗位分配给互不重复的授权 creator，C1/C5 需先提供逐边、时效与权限明确的 Evidence，C3 定义 one-to-one、排除条件和目标。小图先穷举建真值，再比较 heat ranking；若确为线性二分指派，再用相符的精确 assignment/min-cost-flow 方法。Family 102 仅提醒 hardness 结果不提供该 solver。当前没有对应真实输入。

**反例：** 用 Max-Cut hardness 推论“互动高的 creator 更适合品牌”，或用 DFVS hardness 决定 Collector 暂停/恢复。前者把 SAT-derived gap 混成 creator fit；后者把图删除目标混成 Permission/cooldown/human verify。

**算法比较：** heat_score 是展示排序，不满足 one-to-one assignment；小图穷举可作 oracle；满足线性一对一条件时精确 assignment/min-cost flow 更直接。Hardness paper 只说明通用保证边界。

### Adoption Card 102

- **source/family/version：** 五篇 Family 102，openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a。
- **formalized：** YES，Lean docs 声明五篇 gap/hardness scope；本轮未 replay。
- **problem solved：** Unique Games gap 及四类图优化近似困难度。
- **transferable principle：** 核对目标与图假设；hardness 不是 solver、ranking 或最优性证据。
- **LUMENIS owner：** C3 BMP；来源和资格边归现有 C1/C5 Source/Evidence owners。
- **current gap：** 已见源代码是热度排序/dashboard/启发式关系；未建立 matching/approximation job。
- **proposed adaptation：** 当前不接入产品算法；真实任务出现时再按当前 owner 定义证据图和目标匹配 solver。
- **required data：** 版本化实体/角色、逐边 Evidence/Permission、去重、范围时间、容量/排除约束、业务目标、完整度。
- **expected benefit：** 避免错误宣称 approximation/optimality；无当前算法收益。
- **computational cost：** 固定参数归约为多项式时间；论文未提供序境 solver 成本或 benchmark。
- **failure conditions：** 图义不符、来源缺失、热度被当成适配、hardness 被当算法、宣称 P≠NP 已证明。
- **rights/license：** repo Apache-2.0；仅非逐字方法卡。训练需 C2/C5 独立 gate。
- **validation method：** 将来在小图 oracle 对照，并用同一 source/evidence 比较 ranking、精确 solver 和 approved baseline；本轮未做。
- **PRODUCT_ADOPTION：** DEFER；直接当匹配/传播算法应 REJECT。
- **MODEL_LEARNING：** CANDIDATE，仅 theorem premise、限制、反例和评估标准；无训练准入。
- **concrete_example：** 经授权 creator 与岗位的一对一资格图，逐边 Evidence，先穷举小图再评估适配 solver。
- **counterexample：** 用 Max-Cut hardness 证明互动最高者更适配。
- **practical_baselines：** heat_score listing、小图穷举、假设吻合时精确 assignment/min-cost flow。
- **stop_conditions：** 没有真实 assignment job、证据边不全、目标不明或无同任务评估时停在 DEFER。

## Family 103 — log-space exact derandomization

### 原文结果与严格机器模型

Theorem 1.1 证明 L=RL=BPL。前提是固定 randomized machine：只读带端标记输入、O(log(n+2)) 工作空间、每条随机带最坏 polynomial time、独立公平随机位，且每一步遵守这些界。Theorem 1.2 对 unary 精度 q 给误差 ≤2^-q 的 dyadic probability estimate，空间 O(log n+q)、时间 (n+2)^O(1)·2^O(q)。固定 inverse-polynomial precision 仍是 polynomial time；高 q 有指数时间因子。

证明将计算分层为有限 substochastic configuration transition matrix，使用矩阵/逆表示、correction-copy hierarchy、sampled environments、retained sets、uniform moment bounds、conditional averaging/mixing、exact estimator/median；最后依赖 bounded-space fingerprints、recursive graph navigation、digit 查询终止性和完整空间会计。深入读 pp.1–7 与 pp.92–98；8–91、99–108 未深入阅读。

开放网络、Python、DB、文件系统和 model call 不满足该机器模型。去随机化不推出 source coverage、无偏总体估计或平台 challenge 不存在。

### Owner 映射、条件例、基线

Source Owner Index 把 Collector/Browser 归 C1/C6 的现有 SYSTEM owner。现有 acquisition 是网络和 durable state 驱动；未发现符合 log-space 假设的随机产品子程序。

**条件例：** 如果现有 C1/C5/Shared owner 有纯有限输入 randomized predicate，且能证明输入、工作空间、每条随机带时间、随机位和误差均符合 theorem，可研究 deterministic equivalent，并用穷举小输入比较。此例不包含真实网站调用。

**反例：** 随机挑网页并声称 L=RL=BPL 使采集完整/无偏；分页、缺失、身份、challenge、nonresponse 不在定理机器模型中。

**算法比较：** 小有限域用穷举 oracle；严格匹配 log-space decision 才评估论文式 deterministic compiler；其他算法需各自证明 PRG/derandomizer 假设。Collector 仍需来源、cursor 和 partial/unavailable 状态。

### Adoption Card 103

- **source/family/version：** Exact Derandomization of Logarithmic Space: L=RL=BPL，Family 103，固定 commit。
- **formalized：** NO_DECLARATION_FOUND；检查的 lean/docs 无该 family scope；formalization.yaml 是目录，不是形式化证明。
- **problem solved：** 特定 log-space、bounded-error、randomized polynomial-time decision machine 去随机化。
- **transferable principle：** 机器模型不匹配时不可迁移；reproducibility 不等于 representativeness。
- **LUMENIS owner：** 当前没有直接匹配；未来纯子程序归原 C1/C5/Shared owner，Collector 仍为 SYSTEM。
- **current gap：** 在线 Collector 有 network/persistent state，不满足 theorem 模型。
- **proposed adaptation：** 只保存适用性清单；符合全部前提的既有纯子程序才评估。
- **required data：** machine/input encoding、空间和每带时间证明、随机性/error contract、可枚举输入。
- **expected benefit：** 特定子程序可能更可复现；当前无受益 job。
- **computational cost：** estimator O(log n+q) space、(n+2)^O(1)·2^O(q) time；常数未测。
- **failure conditions：** 网络/I/O/持久状态、随机位不符、无 per-tape bound、超 logspace 或输出被说成 coverage。
- **rights/license：** repo Apache-2.0；只做非逐字卡，另需 C2/C5 训练审查。
- **validation method：** 将来穷举输入比对 exact probability、deterministic output 和资源界；本轮未执行。
- **PRODUCT_ADOPTION：** DEFER。
- **MODEL_LEARNING：** CANDIDATE，仅机器前提、保证和 failure boundary。
- **concrete_example：** 完全满足机器假设的既有有限输入 randomized predicate。
- **counterexample：** 认为定理能保证开放网页 collection 完整无偏。
- **practical_baselines：** 小域穷举、算法专用 PRG/derandomizer、现有 provenance/cursor。
- **stop_conditions：** 找不到满足完整机器模型的现有调用点时不为套 theorem 增加功能。

## Family 104 — mean-payoff、stochastic 与 parity games

### 普通算法与 10 月扩展

- **普通 deterministic（9/25）：** 有限 total digraph、Max/Min 顶点、signed binary rewards、任意历史策略，目标为路径 liminf 平均收益。求 zero-threshold winning set、exact values 和 optimal positional strategies；输入长度 L 上 2^O(log²(L+2)) bit time。证明用 potential box、sub/supersolution witnesses、mass reweighting 与递归 pivot/shrink。
- **普通 randomized（9/25）：** 输出完整 nonnegative liminf winning set，概率至少 7/8，每条 random tape 拟多项式 bit time；算法与 deterministic 版本不同。
- **Stochastic（10/05）：** finite total multigraph，Max/Min/chance 分区；chance 概率明确为 binary rational，rewards 为 signed binary integers；求 expected pathwise liminf mean payoff 的 exact value≥0 set。deterministic bit time 2^O(log²(L+2))。证明依赖 exact rational positional strategy/value-gap、discounted fixed point 与有限 box labeling recursion；概率是已知输入，不能把猜测的经验值当 exact。
- **Mean-payoff parity（10/05）：** deterministic total arena、signed binary rewards 与 binary priorities；目标同时要求非负 liminf mean-payoff 与“无限次出现的最小 priority 为偶数”。求 winning set，复杂度 2^O(log²(L+2))。证明组合 dominion/attractor recursion、ordinary mean-payoff 与 uniform all-prefix strategy bound；没有 stochastic chance vertices。

该界是 bit complexity，不是实际策略收益或运行时间。stochastic probabilities 若由历史估计，必须补充误差和漂移。无限期平均 reward 也不等于单次用户任务质量。

### Lean 范围与现有 Scheduler

lean/docs/104.md 的标题较广，但 Scope 只声明 Truffet two-step elimination 的 finite counterexample 和 randomized ordinary mean-payoff algorithm；列出的 accompanying papers 只有两篇 9 月普通结果。没有声明 deterministic solver 或 10 月 stochastic/parity 已形式化。[Lean 范围说明](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/lean/docs/104.md) 未跑 Lean。

现有 owner 为 lumenis/system/collector/adapters/scheduling/decision.py 与 planner.py。ScheduleDecider 是基于 canonical status 的 deterministic interval/backoff/cooldown/recovery/human pause 规则；planner.shadow_evaluate 只评估；gate 默认 shadow，生产固定 trigger 不变。当前没有校准的 transition probability 或 long-run numeric reward。NEED_VERIFY/SESSION_EXPIRED 是等人的硬状态。

**条件适配例：** 未来用现有 shadow path，把状态与动作建成有限图；只有同 owner 授权、来源明确、按平台/时间分层的执行历史支持概率校准后才评估。Reward 依据真实去重有效结果与明确成本；挑战/cooldown/人类验证仍是硬门。与现有规则回放并报告不确定性。当前这些数据没有，所以只是一条候选研究路径。

**反例：** 给 NEED_VERIFY 猜很小概率后让 expected reward 继续执行，或把 parity priority 当 Permission。

**现实基线：** 现有 deterministic rule Decider；无 chance 时 deterministic game；已知概率且无限均值目标时 stochastic game；概率不确定时 robust/finite-horizon replay。

### Adoption Card 104

- **source/family/version：** 四篇 Family 104，9/25 ordinary、10/05 stochastic/parity，固定 commit。
- **formalized：** PARTIAL；Lean Scope 仅声明 ordinary randomized algorithm 和 Truffet counterexample，未声明 deterministic solver/10 月扩展。
- **problem solved：** finite binary game 的 ordinary、known-probability stochastic 或 mean-payoff conjunction parity winning/value。
- **transferable principle：** 明确定义状态、动作、chance、reward 和目标；Permission/人工验证必须硬门。
- **LUMENIS owner：** C1 / SYSTEM Collector Scheduler；C6 仅做既有 integration。
- **current gap：** Scheduler 有 deterministic state rule，但无 Evidence 校准概率或长期 reward；未证实需要 game solver。
- **proposed adaptation：** ADAPT 为现有 planner 的 shadow-only evaluator 候选；需先有授权日志、概率校准和 uncertainty/drift；当前不实现。
- **required data：** 授权 action/state/outcome/time、identity/source scope、有效/重复结果、风险成本、人工验证状态、时间分层样本和校准/漂移。
- **expected benefit：** 若目标确为长期平均，可比较策略；当前无实测收益。
- **computational cost：** complete binary input L 上 2^O(log²(L+2)) bit operations；模型成本/隐藏常数未测。
- **failure conditions：** 概率臆造或漂移、缺日志、reward 变化、未建模状态、Chance/玩家混淆、Permission 软化。
- **rights/license：** repo Apache-2.0；生产日志继续受 Permission/privacy/Evidence 管理。
- **validation method：** 将来授权时间留出校准、确定性 rule replay、逐平台结果/风险/重复/不确定性比较；本轮未执行。
- **PRODUCT_ADOPTION：** ADAPT，仅研究 shadow 评估；无当前模型或产品变更。
- **MODEL_LEARNING：** CANDIDATE，仅非逐字状态/目标/边界卡；概率不自动成为 Canonical Truth。
- **concrete_example：** 用 planner shadow 对照经授权、时序分层历史校准出的同平台策略。
- **counterexample：** 对 NEED_VERIFY 猜概率并让奖励抵消人工验证。
- **practical_baselines：** 现行规则、ordinary deterministic game、known-probability stochastic game、不确定时 robust replay。
- **stop_conditions：** 无授权概率/reward、校准漂移、无同数据收益或任何硬门被软化时不推进。

## Family 107 — matrix multiplication exponent 9/4

### 主定理和同 family 扩展

10/02 论文 Theorem 1.1：对每个 ε>0，复数 n×n 方阵可用 Oε(n^(9/4+ε)) arithmetic operations 相乘，故 ω(C)≤9/4。论文第 2 页明确未给 competitive finite matrix size。该定理是 asymptotic arithmetic count，不是 bit complexity、数值稳定、显存或 GPU wall-clock。

证明把 finite trilinear tensors 放入 restriction semiring，用 Strassen asymptotic spectrum characters；detecting-character 结果将上界化为控制各 character。多项式乘法 tensor 的 profile P(a,b) 经插值有 P(a,b)≤(a+b−1)^(1/t)。有限群 addition tensor、Fourier projection、equal-norm tags、degeneration 分离共享 leg 标签；determinant filtration 与 three-sector decomposition 得到 P(a,3h+a−1)≥3P(a,h)。离散增长强迫 P(a,a)≥a^(4/3)，得 t≤3/4、指数≤9/4；最后固定有限 exact-rank base decomposition 递归成 arithmetic algorithm。全文 13 页核读但未独立重做证明。

同 family 另外两篇结果对象不同：

- **Complex Matrix Multiplication Below 2.258 and Rectangular Bounds（9/24）：** characteristic zero 的 square ω<2.258、dual α>0.465、k=.709 rectangular exponent<2.092；square/该矩形 bound 可迁移至 char0 与除有限正特征外的域。exceptional primes 未列，正特征 dual bound 未声称。补充矩形/dual 范围，但 square 不强于 9/4。
- **Staggered extraction over every field（9/24）：** 每个 fixed field（含正特征）square exponent<2.371054886006746。用 CW5、length-8 strands 拆为 4/2/1、shape restriction、跨深度 pooling、variable-deletion recovery、staggered lots 与 rational finite-parameter certificate。域更广但指数较弱；仍无实测 crossover。

lean/docs/107.md 声明 complex 9/4、dual、rectangular 与 all-field bounds，但 associated papers 列表只有 9/24 两篇，没有 10/02 paper。因此只能说文档声明 formalization scope 含 9/4 comparator statement；不能说 10/02 原论文逐步映射并已 proof replay。formalization.yaml 是文章目录，不是 proof status。未运行 Lean；状态为 PARTIAL / mapping unclear。

### Owner 映射、适配例、比较

C2 owns SYSTEM AI Gateway inference/training。owned_inference.py:27–48 报告 service_binding=NOT_BOUND，Gateway core.py:87–88、133–134 要求 BOUND。此为真实 service-binding gap，但 Family 107 没有 executor/binding，也没有 profile 显示 GEMM 瓶颈；现有路径使用 PyTorch/Unsloth/PEFT，不能据此推断需要自定义 GEMM。

**条件适配例：** 只有真实 Gateway 已绑定且 profile 表明 GEMM 主导，再在同设备、同模型/recipe、shape、batch、precision 比较成熟 PyTorch/vendor GEMM 与有许可边界的候选。记录 cold/warm、P50/P95、吞吐、显存、误差、编译/启动成本及端到端任务表现。当前不下载模型、不训练、不启服务。

**反例：** 从 exponent 2.25 推断当前小矩阵/transformer latency 更低。asymptotic bound 不给 crossover、memory traffic、accuracy 或 GPU 表现。

**现实基线：** 当前 PyTorch/Unsloth mature vendor GEMM；按真实 shape profile。2.258 rectangular 与 all-field 2.371 解的是不同 field/shape 范围，不能合并成同一 guarantee。service NOT_BOUND 与 matrix algorithm performance 是独立问题。

### Adoption Card 107

- **source/family/version：** 10/02 complex 9/4 + 9/24 rectangular + all-field papers，固定 commit。
- **formalized：** PARTIAL / mapping unclear；Lean docs 有 9/4 statement，但 associated list 未列 10/02 原文。
- **problem solved：** 指定 field/shape 的渐近 arithmetic exponent。
- **transferable principle：** 保留 field、shape、算术模型、ε、渐近限制；operation count 不是部署性能。
- **LUMENIS owner：** C2 / SYSTEM AI Gateway；Shared Evaluation 做未来候选比较。
- **current gap：** Gateway 未绑定；无 GEMM bottleneck profile，数学 theorem 不修 service binding。
- **proposed adaptation：** DEFER；仅真实绑定后 profile 显示 GEMM 主导时测候选。
- **required data：** same-SHA model/recipe/runtime/device、shape/batch、profile、precision/memory、P50/P95、吞吐、启动和端到端成本。
- **expected benefit：** 大尺寸理论算术操作数下降；finite workload benefit 未知。
- **computational cost：** Oε(n^(9/4+ε)) arithmetic operations；无 crossover、bit/memory/runtime bound；工程成本未计。
- **failure conditions：** GEMM 非主瓶颈、shape/field 不符、精度/内存不符、无稳定收益或 service 未绑定。
- **rights/license：** repo Apache-2.0；第三方 kernel 独立 license/maintenance 审查。
- **validation method：** 将来同设备/shape/precision 与 mature backend 比较 correctness、误差、warm/cold latency、吞吐、memory 和真实任务；本轮未测。
- **PRODUCT_ADOPTION：** DEFER。
- **MODEL_LEARNING：** CANDIDATE，仅渐近算术/有限硬件表现差别的非逐字卡。
- **concrete_example：** 绑定的 C2 workload profile 证明 GEMM 主导后在真实 shape benchmark。
- **counterexample：** 看到 2.25 指数就声称当前模型更快。
- **practical_baselines：** 当前 PyTorch/vendor GEMM、同 shape 实测、未 profile 前不加算法。
- **stop_conditions：** 未绑定/无 profile 保持 DEFER；GEMM 非主耗时或收益低于集成/数值/维护成本时停止。

## 总结

1. Family 102 是 hardness，不是优化算法；现有 BMP heat ranking/event graph 并非论文图问题。
2. Family 103 有严格 log-space 机器前提；L=RL=BPL 不推出线上采集完整或无偏。
3. Family 104 最接近现有 Scheduler，只建议研究 shadow evaluator；没有校准概率/reward 前不实施、不 gate。
4. Family 107 证明渐近算术上界，不证明有限硬件提速；C2 当前 service-binding gap 与矩阵瓶颈无关。
5. MODEL_LEARNING=CANDIDATE 只是非逐字卡的待审状态；无训练或 material admission。报告不是 M acceptance、PO approval、JOB_CLOSED、RELEASED 或 OPERATING evidence。

---

## 研究正文：research-113-115

# OpenAI Math Families 113–115：深度原文研究与序境采用准备

**日期：** 2026-10-07
**研究源：** [openai/math 固定提交](https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a)，SHA adc7f1241b42e322a6451854ab7e4b4c146bf78a；GitHub live main 核对为同一 SHA，提交时间 2026-10-06 21:58:50 UTC。
**输入：** C:\Users\28049\.codex\attachments\6736fa5d-c05d-4a83-b271-89d0a18b060f\已粘贴的文本.txt。
**范围：** Family 113、114、115 原文研究；只读 C1/C3/C5 owner source；不启动产品开发、产品测试、运行时/数据库探测、训练或 Lean 构建。

## 研究边界与复核方法

固定版本 README 将仓库描述为 722 篇 manuscripts、372 个 result families，并明确并非所有结果已经形式化，未形式化结果仍可能有问题。[仓库 README](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/README.md) 先对照 math-source/CONTENTS.md、selected-family-sections.json、selected-downloads.json 与固定 SHA 的论文及 Lean docs 核对 Family 范围；本报告分别处理定理、输入假设、复杂度模型、证明依赖、Lean 文档范围和序境 owner 映射；论文发表、Lean 文档或算法存在都不等于生产真理、可运行实现或适用性。

核读六篇 family 原文。全部 236 个 PDF 页均完成文本提取；各篇定理、算法框架、复杂度、关键假设和证明依赖按下表所列页码核读。页面提取和关键段核读不等于逐行证明检查、形式化构建、独立复现或性能基准。PDF 文本提取可能损失数学公式的布局；正式实现前仍需回到 PDF 原文核查推导和输入模型。

| Family / 论文 | 页数与深入核读页 | SHA-256 | 固定版本原文 |
|---|---:|---|---|
| 113 — A Fully Polynomial Randomized Approximation Scheme for Perfect Matchings in General Graphs | 45；1–9、10–16、17–27、28–40、41–45（§1–10） | 1510b15725ee7e92a6c543484c6c02ce7f26347a32c1a11cd66c5890b94c6de1 | [PDF](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/A-Fully-Polynomial-Randomized-Approximation-Scheme-for-Perfect-Matchings-in-General-Graphs-September-23-2026/main.pdf) |
| 113 — Entropy and Face Dimension of the Perfect-Matching Polytope | 45；1–4（定理、计数推论、几何论证依赖） | c0b726a089502900b6b0c6b26b3d024cc55c440ce5d4abc71584b2c9ffe2fae4 | [PDF](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Entropy-and-Face-Dimension-of-the-Perfect-Matching-Polytope-September-23-2026/main.pdf) |
| 114 — An FPRAS for Common Integer Polymatroid Bases with Binary Capacities (2026-10-05) | 42；1–4、7–20、22–41（定理、oracle/秩假设、signature、凸体体积、两重提升/transport/annealing/有限位复杂度） | c14d087890444879a1ff0d492e8cfc3fdb976af562c966ee5c5bd3c3e2ade2e8 | [PDF](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/An-FPRAS-for-Common-Integer-Polymatroid-Bases-with-Binary-Capacities-October-5-2026/polymatroid-fpras.pdf) |
| 114 — Approximate counting of common bases of two matroids | 26；1–6、7–19、20–25（oracle 定理、配对元素构造、defect/transport/trace、扩展） | 7ed3dfdefcfa677a2b06e7fcde5efefc1a26d3ff774a4b604166e21082ac2607 | [PDF](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Approximate-counting-of-common-bases-of-two-matroids-September-23-2026/main.pdf) |
| 115 — Exact Uniform Sampling of Contingency Tables with Arbitrary Margins | 31；1–7、8–24、25–30（定理、completion chain、repair/mixing、有界近似与精确修正） | be1d677ab515ceb23e7ee9fd369d705345ec0c9254585ac96ded3aa97732cd89 | [PDF](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Exact-Uniform-Sampling-of-Contingency-Tables-with-Arbitrary-Margins-September-24-2026/main.pdf) |
| 115 — An FPRAS for Cell-Bounded Contingency Tables | 47；1–9、10–17、18–47（定理、输入/flow corollary、cell 分解、signature/volume/annealing/位复杂度证明路线） | 10bad4277d11b9d1c69842fd8e9028c67edb9ebce6092ad6332703975c8fd7e7 | [PDF](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/An-FPRAS-for-Cell-Bounded-Contingency-Tables-September-24-2026/main.pdf) |

逐页字符计数与下载/SHA 清单保存在同目录的 source-pdf-page-coverage-113-115.json 和 source-pdfs-113-115-manifest.json。仓库 LICENSE 为 Apache-2.0；论文 README 提供作者、日期和引用信息，但未另列 manuscript-specific terms。[固定版本 LICENSE](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/LICENSE) 因此本报告只做非逐字方法蒸馏，不把论文全文或合成结果送入训练；任何学习候选仍需 C2/C5 独立 rights/privacy/quality/held-out gate。

## Family 113 — 匹配计数与熵界

### 原文结果、算法与依赖

**一般图 perfect-matching FPRAS。** 输入是显式有限简单无向图；计数对象是无权完美匹配集合。先用多项式时间精确最大匹配检查可行性；无 perfect matching 时每次返回 0。否则以相对误差 ε、失败率 δ 估计计数，最坏 bit time 为输入长度、ε⁻¹、log δ⁻¹ 的多项式，并对每个随机带有界。论文第 5 页明确说参数常数为透明证明估计选取，不以实际效率为目标；这是复杂度保证，不是实际 LUMENIS 速度或质量实测。

主要证明链（§1–10）：从完全图逐步压低非目标边活动率，乘接续配分函数比值；利用删去两点后的 partition ratio 更新 vertex scales，使 row-wise balance 维持在常数范围；把逻辑边细分成加权路径，再在重叠 tree-bag 加入弱 clique 边，借助 balance 把辅助边造成的配分函数膨胀控制在 2 倍以内；标记边提供两洞配分函数比值的事件恒等式。混合证明不是简单套用单坐标更新：quadrangulation 的有符号整环恒等式与双匹配编码给出 pair-coordinate energy 界；坐标正交分解对任意函数仍不够，必须复制相邻 tiers 才推出完整产品链谱隙。单位活动率底层用树结构精确刷新。最后用采样估计分阶段比值，再以有限位随机选择、截断 phase 和 median amplification 给出每次执行都有界的 bit-time 界。

关键假设是图及候选边完整显式、边无权、目标是一对一覆盖所有顶点的完美匹配；内部使用活动率/权重是算法构造，不把定理扩成任意业务权重 perfect-matching 计数。它也不求最佳 matching，不评分 creator，不推断消费者偏好。

**熵与 face dimension。** 对有 2m 个顶点的无 loop 标号多重图，给定 feasible perfect-matching edge marginal x，H(x) 是满足这些边边际的匹配分布中最大熵。论文给出全 polytope（包括边界）上的 F(x) − (2−2/m)B(x) ≤ H(x) ≤ F(x)，其中 F=−Σxₑlogxₑ、B=−Σ(1−xₑ)log(1−xₑ)。证明的重要依赖包括 minimal face 的几何/紧奇割、将 tight odd cuts 收缩、支撑数与最小面的 codimension 估计、在最小面内的 exponential-family/covariance-Hessian 关系，以及迹估计矛盾。此熵是给定边际的可行匹配分布组合熵，不是效用、质量或推荐可信度。

计数推论中，log N ≤ max(F+B) ≤ log N + 3m−2；配套确定性下界只有 N/512^n ≤ A ≤ N（单点 loop 约定的附录另有 2^(18n) 因子）。指数级因子不是 (1±ε) 近似，也不是实用候选排序。熵界与 face 结构结论不能被解读为“高热度即适配”。

### 到序境的映射、例子与基线

现有 C3 BMP BusinessDecisionWorkflow（api_dual_domain.py:100）在 Shared report artifacts 上记录 operator proposals；proposal 必须归因到现有 source IDs，并包含 assumptions/unknowns/check；它不执行 campaign。当前 source role 还要求品牌官方身份/任务、可比市场时段、授权 creator 内容及 consumer feedback（约 506、640–649 行）。这是候选接入边界，不证明系统已有匹配算法。

可审议的具体例子：某个已有 BMP 任务已经定义 3 个独立内容角色和一组经授权 creator；只有当官方/授权来源能逐条证明 creator 可承接 role 时，才得到 role ↔ creator 二分图。若任务恰要求每 role 一人且每 creator 至多一次，可先用精确最大匹配回答可行性；若产品任务真的还要估计符合约束的组合总数，再评估 FPRAS 作为“可行方案空间大小”指标。业务选择仍要看品牌任务、受众证据、内容质量、渠道限制、预算和用户决定，算法只数边集结构。

反例：把 creator 的公开互动量、粉丝数或传播热度当作边权，然后声称 F113 证明热度最高者最合适。论文的定理不做加权最优，不建立“热度→受众匹配/ROI”的因果关系；Source Owner Index 明确规定 popularity alone 不是 creator/channel fit。若一个 creator 可承担多个角色，或存在跨 creator 预算、时段、互斥约束，简单完美匹配模型也不符。

**实用基线比较：** 若问题是“是否有可行的一对一分配”，先用精确最大匹配；若问题是“在证据和成本目标下选哪一种”，用当前受控业务约束下的精确可行性/最优化方法（简单分配可用 min-cost matching/flow），而不是估计解数。FPRAS 只有在真实任务提出“有多少可行选择/空间是否脆弱”且图模型通过 owner 审核时才有增量价值。

**AdoptionCard。**

- **source / family / version：** 两篇 Family 113 论文；openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a。
- **formalized?：** PARTIAL。Lean docs 声明 FPRAS 与点态熵界；若干确定性估计和 triangle expansion face correspondence 也在选定范围内；论文 sharp global face-dimension bound 明确不在该 formalization statement。[Lean 范围说明](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/lean/docs/113.md)
- **problem solved：** 一般简单无向图 perfect matching 数的相对近似；给定 feasible edge marginal 时最大匹配熵界。
- **transferable principle：** 先验证可行性；保持 sampler 必需的 balance invariant；说明计数目标、输入单位和抽样误差；区分组合熵与业务价值。
- **LUMENIS capability owner：** C3 BMP 现有决策 workflow；必要的候选/source vocabulary 仍归 C1 Collector 与 Shared Source/Evidence；不新建 math/optimizer owner。
- **current gap：** 未见真实 job 需要估计一对一方案总数，也没有适用的已验证候选图或权重定理。
- **proposed adaptation：** 当前只登记方法卡；未来若真实需求成立，用来源支持的 eligibility graph + 精确可行性检查，再比较计数的增量用途；绝不将计数作为推荐。
- **required data：** 候选及角色身份、逐边有效来源和 Permission、明确一对一语义、范围/时段、平行边约定、排除条件、完整度和过期策略。
- **expected benefit：** 可能量化可行组合数量及决策脆弱性；当前没有已证实收益。
- **computational cost：** 定理为多项式输入长度、ε⁻¹、log δ⁻¹ 最坏位复杂度；证明常数偏保守，未测本地实现性能。
- **failure conditions：** 无权/一对一结构不符、来源证据缺失、欲做 ranking/weighted optimization、用热度代替适配或把不完整边集合的计数当覆盖结论。
- **rights/license：** 仓库 LICENSE Apache-2.0；论文 README 无单独 manuscript-specific 条款；衍生卡而非全文进入学习审查。
- **validation method：** 未来在小图穷举对照、零解/解数对照、不同 ε/δ 多随机带，并在同一真实任务与精确可行性/业务基线比较；本轮未执行。
- **PRODUCT_ADOPTION：** DEFER，直到 C3 有明确 count 型 Job 和经过审核的图输入。
- **MODEL_LEARNING：** CANDIDATE，仅限非逐字方法、假设、反例和评估卡；未入库、未训练。
- **stop conditions：** 没有真实 count 问题、逐边 Evidence 不完整、任务实为优化/排序、图语义不符或对现有决策无可测改善时停止。

## Family 114 — common bases 与 binary-capacity polymatroid 扩展

### 两篇论文的对象必须分开

**2026-10-05 新扩展：** 计数 Ω={x∈Z^E≥0 : x(E)=R, x(A)≤rᵢ(A) 对所有 A、i=1,2} 中的整数向量，每个向量计一次。两个 rank function 必须是 integral、normalized、nondecreasing、submodular 且总 rank 相等；输入提供精确 rank-value oracle，容量/rank 二进制编码。FPRAS 对 ε、δ 返回相对近似，零解总返回 0，低维可行集允许；oracle 调用数和外部 bit operations 对 ground set、输入编码、ε⁻¹、log δ⁻¹ 多项式且每个随机带有界。oracle 内部计算成本不在外部 bit-op 多项式中，不能把 oracle 当作免费；论文也没有大规模现实 benchmark。

证明路线（重点 pp.1–4、7–20、22–41）：将二进制大坐标切成多项式范围的部分总量；用软 penalty 处理高维 free 区域，再以 log-concavity / Prékopa 和有理凸体体积估计连接积分与格点计数；用平滑权重、曲率和离散 quadratic signatures 控制离散变化；两次 factorial lift 处理标号乘数；依赖 companion work 的 paired chain/transport/trace 建立抽样和比值控制；最后实现有限位/有限区间算法。论文 p.41 说明显式构造的是多项式大小的 port pairing；巨大的扩展 matroid/flow 主要用于证明，不应误说产品可直接构造它们。

**旧论文：** 两个 equal-rank matroid 在显式枚举有限 ground set 上的 common bases，给 independence oracle。把 M1 ⊕ M2* 构造成 2n 元素、rank n 的 matroid，将 common bases 对应为特定 transversal bases；增加 defect states/multipliers，靠删除/添加两元素的 quadratic signature、Brändén–Huh/Lorentzian 型性质、paired transport、observable/trace mixing 与 annealing 得出 FPRAS。§9 另以 truncation/self-reduction 扩展到 common independent sets 的指定、任意或最大基数；这仍不等于新整数 polymatroid theorem。

### Lean 范围、序境差距与基线

这是本 family 的关键版本差异：lean/docs/114.md 只声明**旧 equal-rank matroid common-bases** FPRAS + independence oracle。它没有声明 10 月 5 日的 **binary-capacity common integer polymatroid bases** theorem。旧结果已形式化不能用来证明新扩展也已形式化，也不能据此称多态约束计数已复现。[Lean 范围说明](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/lean/docs/114.md)

当前读到的 C1/C3/C5 source 没有两个精确 polymatroid rank oracle、equal-total-rank 约束、整数 base 结构证明或对可行分配**计数**的真实需求。BMP 的多个 source-bound operator proposals 也不是 matroid/polymatroid 本身。不能从“有容量约束/多对多匹配”就把业务问题数学化成该定理。

**实用基线比较：** 若只要一组可行方案，按真实约束用精确 feasibility、max-flow/min-cost flow 或已有 owner 的 allocation logic；若要最优，使用相应精确目标优化并保留来源/决策。FPRAS 针对“有多少共同 bases”，不返回最优方案。对小实例可用穷举/精确计数做参考；oracle 本身仍须有可审计实现和复杂度。

反例：把固定人数、预算、creator 资格写成一些集合条件，就直接断言约束是 normalized monotone submodular rank function。若约束有非次模相互作用、总 rank 不一致、非整数/非单调，或者要最大化消费者匹配质量，均超出定理。另一个反例是以 Lean 旧 matroid formalization 作为新 polymatroid FPRAS 的证明证据；当前 Lean docs 明确没有该扩展。

**AdoptionCard。**

- **source / family / version：** Family 114 两篇论文，固定在 openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a；区分 2026-09-23 matroid theorem 与 2026-10-05 binary-capacity polymatroid theorem。
- **formalized?：** PARTIAL；Lean 文档仅覆盖旧 matroid 情形，新扩展不在其列明范围。
- **problem solved：** 通过 independence/rank oracle 计数共同 matroid bases / common integer polymatroid bases。
- **transferable principle：** oracle 的精确接口和成本是 theorem 前提；需先证明输入结构及 submodularity/integrality，再谈计数复杂度。
- **LUMENIS capability owner：** 如有合法需求归现有 C3 BMP 决策能力；当前没有独立 optimizer/计数服务 owner。
- **current gap：** 没有 rank oracle、基集语义或 count 型用户问题。
- **proposed adaptation：** DEFER；仅在现有 C3 task 经严格建模为两个 polymatroid base 交集后，考虑对大二进制容量空间估计解数；不用于优化/排名。
- **required data：** 有限 E、两个 exact rank functions、normalized/monotone/integral/submodular 的构造根据、相等总 rank、二进制编码、oracle 输入/输出与可审计成本、真实 scope/Evidence。
- **expected benefit：** 在以上极窄前提成立时，估计不能直接枚举的大整数分配可行解数；当前无实际受益证据。
- **computational cost：** 对 n、编码长度、ε⁻¹、log δ⁻¹ 多项式 oracle calls + 外部位操作；oracle 内部运算未纳入该 bound，论文不提供实用 benchmark。
- **failure conditions：** oracle 不存在或复杂度未界定、函数不满足前提、业务约束不是 base intersection、目标是优化、误把旧 Lean scope 当新扩展证明。
- **rights/license：** 仓库 Apache-2.0；无单独论文条款记录；仅衍生方法卡，学习前另审。
- **validation method：** 未来小 ground set 枚举精确对照；验证 rank-oracle 构造与定理前提；统计 oracle call/运行成本；在同一真实 job 与精确分配/优化 baseline 比较。未运行。
- **PRODUCT_ADOPTION：** DEFER。
- **MODEL_LEARNING：** CANDIDATE，只考虑非逐字的条件、反例和评估卡；不能给新 polymatroid 定理贴上 Lean verified 标记。
- **stop conditions：** 不能证明两个 rank oracle 和同总 rank，或真实需求是最优解/候选 ranking，或方法对现有 job 无显著改进时停止。

## Family 115 — 固定边际列联表的抽样与计数

### 两篇论文解决的是不同任务

**无 cell bound 的 exact uniform sampler。** 对所有非负整数 m×n 表 X，给定等总和 row/column margins，允许每格任意非负整数，没有禁止格/格上限。存在：

1. 有界时间近似 sampler，输出可行表且总变差距离 TV ≤ 2⁻ᵏ，时间关于 m、n、log(N+1)、k 多项式；
2. 精确均匀 sampler，几乎必然终止、期望 bit time 关于维度和 margins 二进制长度多项式。

证明把小 margin 相邻 cell 作为显式状态，给大 rectangle padding；以 completion-count law 加入一对正负单位 defect；repair map 控制 defect 质量，再用相邻条件 fiber 的 quadratic form、带权 telescoping 和 conditional variance 得到 Poincaré/mixing 界。大块 completion 通过有限网格/有理运算近似。近似版本增加固定时间 fallback，所有输出可行并保有 TV bound。精确版本把有限 sampler 实际分布表列清楚，以极罕见的 exhaustive correction branch 消除剩余偏差，保持精确均匀；该分支意味着**精确版只有期望时间界，不是每次运行都有界时延**。论文特别强调指数只为理论多项式；两行/固定行已有专门算法，但不覆盖联合随两维增长的统一界。

**每格有二进制上限的 counting FPRAS。** 约束是任意 row/column margins 和每个 cell 的 0≤Xᵢⱼ≤uᵢⱼ，可以含零上限/结构零；两个维度共同变化、数值二进制编码。算法零解时总返回 0，否则给 (1±ε) 近似、失败率 δ，最坏 bit-time 对完整输入编码、ε⁻¹、log δ⁻¹ 多项式。它把 cell tightened bounds 分成 small/large，large cells 用容量 spanning forest 与自由坐标，small cells 用配对 binary 表示/defects；以 factorial lifts、quadratic signatures、transport/trace/annealing 和分箱的有理 convex-volume 近似控制计数。论文另给受限整数网络 flow 计数 FPRAS 与 almost-uniform sampling 推论；这不是无上限列联表 exact sampler 的 cell-bounded 版本。多项式指数大、无序境基准。

### 序境数据代表性边界与实用基线

Family 115 是很好的**防误用**研究。固定 margins 的 uniform law 表示：在选定 feasible integer-table 集合上每个表同概率。它条件于给定 margins 和允许格集合；它没有定义真实帖子/消费者/品牌/地区/平台的总体框、来源进入概率、响应偏差、漏采、时间窗、权限或平台覆盖。相同边际可对应大量不同表，给这些表均匀概率也不等于真实业务生成过程的 likelihood。

现有 C1 acquisition_plan.py 标注 coverage_basis=registered_entries_only、world_completeness=NOT_ASSERTED；observed topic catalog 明确 platform_heat=null、representative_demand=null、automatic_adoption=false、admitted=false（约 174–179、847–941 行）。C5 source_brief_job.py 使用显式 operator-selected verified source IDs 或 latest verified nonempty bodies，最多 8 个、每项 task-term window 最多 1200 字符，记录 omitted count 并标记 coverage=PARTIAL（约 410–417 行）。这是按任务相关度、证据和来源可读性选择材料，**不是随机抽样**；列联表 uniform sampler 不会把它变成 representative sample，也不能通过 C1 全域随机实体数据验收。

可审议的具体例子只是统计模型内的 synthetic null：研究者已经定义一张“月份 × 渠道”聚合表的真实 margins 和 permitted cells，要计算“在这些 margins 条件下随机均匀表”的极端程度。输出必须标成模拟/null 表，不得伪装成观测计数。

反例是把生成的“国家 × 平台”表解释成真实覆盖率、用它补齐未采集国家，或拿它当正向训练数据。uniform 是数学可行集的均匀，不是世界样本代表性。

**实用基线比较：** 要判断是否有一张可行表或有边界的分配，先用精确 max-flow/可行性算法；要选最低成本方案，做相应 min-cost flow。IPF 是边际拟合/估计工具，不等于均匀随机 sampler。若问题是对真实记录做代表性推断，应先定义总体框、分层/概率抽样和 inclusion probabilities，分析未响应/来源缺口与平台时段覆盖；列联表算法不替代这些设计。对小 margins 可穷举作核对，对约束复杂的有限问题可用精确整数流基线；是否需要新增库由其 owner 再评估，本轮不引入依赖。

**AdoptionCard。**

- **source / family / version：** Family 115 两篇原文，固定 openai/math@adc7f1241b42e322a6451854ab7e4b4c146bf78a。
- **formalized?：** YES（Lean docs 声明这些结果；本轮未运行 Lean 构建或 proof replay）。Lean docs 声明无界表 exact/TV sampler 和有界表计数 FPRAS。[Lean 范围说明](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/lean/docs/115.md)
- **problem solved：** 给定固定边际的无界整数表均匀采样；有 cell bounds 时近似计数。
- **transferable principle：** 先定义目标总体/条件分布，再谈抽样；数学上条件均匀不等于经验世界代表性。
- **LUMENIS capability owner：** 采集归 C1 SYSTEM Collector + Shared Source/Evidence；研究分析归 C5 Reporting/Research；不创建通用 sample store。
- **current gap：** 现有 C1/C5 没有把列联表定义为真实用户 Job 的目标，也没有代表性 sample frame；已有 NOT_ASSERTED/PARTIAL 等诚实边界。
- **proposed adaptation：** DEFER 产品采用；未来只可为已批准的条件 null model 生成清晰标注 synthetic 表或估计有界聚合表数量，不写 Canonical/Evidence，不据此推断真实覆盖。
- **required data：** 数学输入需等总 margins 和允许格；exact sampler 无 cell caps，cell-bounded 计数需各 cell 二进制上限。真实推断另需总体框、unit IDs、inclusion probabilities、platform/source/time coverage、nonresponse、rights/Permission 和谱系。
- **expected benefit：** 在模型适用时量化可行聚合表数量或提供 synthetic null；不提供真实数据代表性/覆盖结论。
- **computational cost：** exact sampler 期望多项式但无 worst-case 时延；bounded sampler 对 k 有界多项式；cell-bounded count 对完整二进制输入、ε⁻¹、log δ⁻¹ 最坏多项式；论文给出很大的固定复杂度指数。
- **failure conditions：** 边际总量不等、cell set/caps 错、误把表当观测、将均匀表当 empirical likelihood/representativeness、FPRAS 被说成 exact sampler、或合成值混入事实链。
- **rights/license：** 仓库 Apache-2.0；论文 README 未单列 manuscript terms。无全文训练；synthetic data 和方法卡另走 C2/C5 权限/评估。
- **validation method：** 未来对 tiny margins 穷举所有表，核对可行性、频率/误差、TV 和 exact-zero；有界计数用可穷举实例校验。真实代表性另审 frame/inclusion/nonresponse/source coverage，不能以算法采样测试替代。
- **PRODUCT_ADOPTION：** DEFER。
- **MODEL_LEARNING：** CANDIDATE，限非逐字算法知识卡，显式保留“均匀条件表≠世界代表性”的反例；无数据/文本入训。
- **stop conditions：** 目标是实际帖子/来源/用户/品牌/国家覆盖而非条件表空间；缺 frame/inclusion probabilities；caps/零格未建模；生成表可能被当作事实或训练正例时停止。

## 现有 owner 只读接入检查

| Owner / 源码 | 当前实际边界 | 本研究的采用约束 |
|---|---|---|
| C1 lumenis/system/collector/acquisition_plan.py:174-179, 847-941 | 注册表覆盖不等于世界完整；topic catalog 保留 source/time/rights 等 provenance，但热度和代表需求为空、不会自动采纳。 | Family115 不得升级采集覆盖、hotness 或代表性；Family113/114 计数不能替代 Collector 数据。 |
| C3 api_dual_domain.py:100-115, 506, 640-649 | BMP/CTH 操作者决策基于既有 Shared report 和来源绑定 options；不是模型推断事实，也不执行 campaign；对品牌任务/身份、可比市场、creator 内容和 consumer feedback 有 source-role 要求。 | F113 仅是严格一对一输入下的可行空间计数候选；不能做排序/选择。F114 当前没有 oracle/数学语义证据。 |
| C5 lumenis/shared/reporting/source_brief_job.py:410-417 | 取明确选中的 verified sources，或最新 verified nonempty sources；最多 8、任务词窗口最多 1200 字符，记录 omitted source count、PARTIAL。 | 这不是概率 sample。F115 无权改变其任务语义或声称代表性。 |

Source Owner Index 仍指定现有 C1 Collector、C3 BMP、C5 Shared Reporting/Research owner；无新 owner。C3 api_dual_domain.py 与 C5 source_brief_job.py 在本轮读取时属于 dirty working tree，报告按本地当前文本注明，不把未提交改动升级为线上/main 证据。读取 C1/C3/C5 owner source 的快照时，local HEAD、cached origin/main、live refs/heads/main 都为 f6dac9216cbb331e730329a70513e0c90c306e73，树上有 21 个 modified 与 3 个 untracked 路径。写报告后的共享工作区状态复核为 26 modified 与 5 untracked；较后新增的状态只通过 git status 观察，未在本子任务中阅读或修改。两次快照中的 dirty/untracked 路径都未被本子任务触碰。本报告只读这三个 owner slice 和当前 Source Owner Index，没有启动 runtime、读写业务 DB、跑测试或编辑 checkout。

## 最终采用结论

| Family | PRODUCT_ADOPTION | MODEL_LEARNING | 理由 |
|---|---|---|---|
| 113 | DEFER | CANDIDATE | 有严格的一对一无权图计数方法，但现有 C3 任务需要有证据的业务选择和理由，尚无 count 型 Job；熵和计数都不是质量/推荐分。 |
| 114 | DEFER | CANDIDATE | 现有 owner 未显示 polymatroid rank oracle、equal-rank 交集或 count 需求；最新 binary-capacity 扩展不在 Family 114 Lean 声明范围。 |
| 115 | DEFER | CANDIDATE | 条件表空间可用于专门统计 null model；不能代表实际来源/世界。C1/C5 当前 contracts 对 coverage/sample selection 有明确且诚实的语义。 |

MODEL_LEARNING=CANDIDATE 只表示可把非逐字的“问题定义 + 假设 + 证明依赖 + 反例 + 验收方法”整理为待审卡片；不是已收录、已授权或已训练。学习候选须由 C2/C5 分别经过 rights、privacy、quality、held-out、Evaluation、版本、promotion 和 rollback gate。PRODUCT_ADOPTION 和 MODEL_LEARNING 相互独立。

### 后续验证设计（本轮不执行）

- **113：** 小图精确枚举、FPRAS 相对误差/零解/固定随机带成本检查；真实 BMP job 对比精确匹配/业务基线的结果质量与决策耗时；输入边逐条回连 Evidence。
- **114：** 先从规范化构造证明 oracle 的 normalized/monotone/integral/submodular 和同总 rank；小 ground set 枚举精确对照，记录 oracle 自身运行成本；与现有精确 feasibility/optimization 价值比较。缺任何 rank premise 就停止。
- **115：** 小边际穷举表，对照 sampler law/TV 或 bounded FPRAS error；验证每张表 margins 和 cell bounds。若真实 Job 涉及代表性，单独审 sampling frame、inclusion probability、nonresponse、来源和时段覆盖；这些条件缺失时不能通过代表性验收。

## 状态与可复核材料

- 研究包在外部目录 D:\LUMENIS_REBUILD\序\序境-audit-reports\20261007-semantic-math，PDF/逐页提取物和 SHA 清单保留。
- 结构化卡片在 research-113-115.json。
- 未修改 LUMENIS checkout；未跑产品测试、运行时/数据库操作、训练或 Lean 构建；未复现 FPRAS/sampler；没有把 PDF 声称为训练资料。
- 任何产品侧采用仍需现有 owner 的真实 Job、输入 Evidence、Permission 与相应执行/恢复/评估证据；本报告本身不通过产品 gate。

---

## 研究正文：research-139-140-formal

# Family 139、140 与 Comparator：原文定向深读

日期：2026-10-07。研究基于用户同日合并指令。Math 固定提交 `adc7f1241b42e322a6451854ab7e4b4c146bf78a`；Comparator 固定提交 `ca04cfc72b550331658ec314bf47685281bfd4bf`。这是研究与采用准备，不是论文算法的产品实现或训练准入。

## 1. 原文与阅读边界

| 原文 | PDF 页数 | 本轮实际重点阅读 |
|---|---:|---|
| Subpolynomial query complexity for well-conditioned log-concave sampling | 55 | 1–9、38–39、43–44、46–49：问题、定理、oracle 模型、递归查询计数、上下界机制 |
| Memory and precision in noiseless Gaussian regression | 42 | 1–6、12–13、18–19：有限状态模型、主定理、后验局部化与分块证明 |
| Posterior replicas and conditional information in Gaussian regression | 60 | 1–5 的问题/比较恒等式与条件信息机制；不是全部证明核验 |
| Localization costs and information growth for exact Gaussian observations | 93 | 前 3 页方法/定理定位；辅助证明未深读 |
| Projection moments, positive cap domination, and Riesz estimates on the sphere | 29 | 前 3 页方法定位，部分公式抽取不完整；辅助证明未深读 |
| Replacing Gaussian observations in memory-constrained inference | 52 | 前 3 页方法定位，部分抽取不完整；辅助证明未深读 |
| Subsphere methods for memory–sample lower bounds in noiseless Gaussian regression | 25 | 前 3 页模型/定理定位；辅助证明未深读 |

本组 7 篇 PDF 全页文本已抽取，共 356 页。抽取不等于阅读；上述范围是针对定理假设、算法、证明依赖和可迁移性的研究，**没有逐行独立验证数学证明**。PDF 数学排版可能损失。原文 SHA256/页数见 `pdf-139-140-manifest.json` 与 `pdf-formal-supplement-manifest.json`。本轮未运行 Lean、未复现算法、未做产品 benchmark。Family 140 六篇不能笼统写成六篇已全部深读。

固定原文入口：

- [Family 139 论文](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Subpolynomial-query-complexity-for-well-conditioned-log-concave-sampling-September-26-2026/article.pdf)
- [Family 140 主论文](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Memory-and-precision-in-noiseless-Gaussian-regression-September-27-2026/paper.pdf)
- [Posterior replicas](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Posterior-replicas-and-conditional-information-in-Gaussian-regression-September-27-2026/paper.pdf)
- [139 形式化范围](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/lean/docs/139.md)、[140 形式化范围](https://github.com/openai/math/blob/adc7f1241b42e322a6451854ab7e4b4c146bf78a/lean/docs/140.md)

## 2. Family 139：小的是查询复杂度，不是总执行成本

### 定理真正解决什么

输入是已知极小点在原点、`V(0)=0`、`∇V(0)=0`，并满足 `I ≤ ∇²V ≤ 2I` 的二阶光滑势函数；目标分布密度正比于 `exp(-V)`。Oracle 精确返回函数值和梯度。对于每个固定 ε>0，最坏情形查询次数上界为 `Cε d^ε`，总变差误差至多 1/10；同时下界为 Ω(log d)。因此多项式指数的下确界为零，**不能读成已经给出 polylog(d) 上界**。

模型允许查询间不受限的实数运算，**没有算术复杂度和 bit complexity 的实用上界**。常数、精确积分/采样、精度与维度都不能从 oracle 次数中消失。商业帖子不是已知归一化、强凸光滑势函数，HTTP/LLM 请求也不是该精确 oracle。

### 方法和证明为何成立

论文先研究强高斯调制下的近二次条件分布：概率流输运、条件梯度均值、混合 cumulant 的 Poincaré 控制、平稳中心化，以及固定深度 Picard/多项式近似，把高维量的误差转成受控的低阶操作。递归均值估计的深度、精度和参数顺序必须事先固定；平移与相关随机种子的构造保持查询数受控，不能把每层算法分别成立直接相乘。

外层用 proximal/noised chain 与逐次缩小方差的过程；内层近高斯采样控制误差累积。小维度分支有截断拒绝采样和显式失败概率预算。论文中的失败时输出固定点是构造总变差误差的数学步骤，**不是产品缺失数据可以填零的依据**。

下界限制到随机旋转的良态高斯族：oracle 暴露矩阵向量乘积，延迟抽取旋转使自适应算法的信息落在可控 Krylov 结构中，再通过分布统计分离推出 Ω(log d)。所以它不是对任何业务检索算法的通用下界。

### 序境采用判断

- **现有 Owner**：C1 acquisition/evaluation，C5 Research，C2 如确有概率模型采样任务。
- **当前缺口**：没有证明当前业务输入满足该分布/oracle 假设，也没有确定瓶颈属于这种采样。
- **PRODUCT_ADOPTION=DEFER（具体算法）**；成本口径原则可 **ADAPT** 到现有 Evaluation：分别记网络/模型调用次数、CPU/GPU 时间、内存、传输、预处理、精度与尾延迟，不让一种成本替代总成本。
- **需要数据**：真实待采样分布及其假设证据、维度、可访问 oracle、相同误差标准、真实端到端成本记录。
- **比较基线**：当前任务选样/检索；只有形成合法连续分布采样任务时，才比较普通 rejection/MCMC 等适配基线。
- **收益**：先消除“查询更少就更快”的错误采用；没有可承诺的序境提速百分比。
- **验证**：先验证模型假设，再在相同目标误差下比较全成本、混合/偏差和失败恢复。前提不成立立即停止算法引入。
- **MODEL_LEARNING=CANDIDATE**：仅新写的方法、假设与反例卡；C2/C5 独立 rights/quality/held-out 审查，不是论文全文训练。

## 3. Family 140：有限 bit、一次遍历、精确高斯观测

### 模型边界不能省略

未知信号是单位球面均匀先验；每步观察独立标准高斯行向量与无噪声精确内积。学习器只有至多 `2^M` 个持久状态，随机种子/初始状态不能预带信号；不能选择或重访观测行，输出依赖最终状态、允许的停止信息与新随机性。

固定 A 且 `M ≤ A d²` 时，对足够大 d、角误差 `0<ε≤0.1`、成功率至少 2/3，需要 `c_A d log(1/ε)` 个观测。`o(d²)` 内存有统一常数版本。量词“固定 A”“足够大维度”“平均球面先验”有实际作用；不能把 A 随维度任意增长，也不能把 M 直接等同于 GPU 显存、KV cache 或 token context。

### 证明机制与两个不能混淆的上界

Memory/precision 主线跟踪球面后验的小球质量：若半径 r 的局部质量至多约 `(Rr)^(d-1)/2`，则 Θ(d) 个新观测的一块只能把局部化尺度 R 提升有限倍。反向 continuation functions、精确投影密度、Lq/Hölder 与椭球体积因子抵消共同控制更新。有限状态并合付出 `N^(1/q)`，再取与维度相关的根，将代价压成约 `log N/d²`。达到 ε 精度需要多块，因此出现对数精度因子。

实数寄存器 Kaczmarz 的均方误差收缩 `(1−1/d)^t` 是对照，**不是有限 bit 学习器同复杂度上界**；它不受相同有限状态约束。

Posterior replicas 把同一精确标签下的独立条件信号作为比较对象，建立条件信息界。典型项是 `H(W)/t + C d + C log(2+log L)`；必须核对等标签比较和独立侧随机性，并扣除比较后仍存的相关性 `K−K′`。直接只上界 K 会丢失关键抵消。辅助论文提供局部化信息收费、投影矩/球冠控制、观测替换、subsphere 等证明路径，并不意味着更一般的有噪声、主动采样、可重访训练也满足同一结论。

### 序境可以怎么用

- **Owner**：C2 existing Agent/Memory/context/Evaluation；C5 methodology/rights；C3 使用任务结果，F 只消费已有真实性状态。
- **PRODUCT_ADOPTION=ADAPT（实验设计原则），数学下界直接套 LLM=REJECT**。不据此承诺加大 context 必然解决问题，也不据此确定训练样本量。
- **当前缺口**：尚无同模型、同任务、同 Evidence 版本下的记忆压缩/检索对照，无法区分信息丢失和模型能力不足。
- **准备好的下一步**：获准恢复后，在现有 Evaluation 对同一真实 Brief 比较完整可用资料、压缩记忆、压缩加可回溯检索；固定模型/配方/输出预算/来源截止时点，记录跨重开后事实保持率、引文正确率、预算/范围约束违反、错误自信、延迟和资源成本。检索恢复真实来源，不把压缩总结提升为 Evidence。
- **数据**：许可材料的不可变版本、独立 held-out 问题/答案核验、故意改变的时间/预算/来源、相同用户任务。
- **收益**：找到真实产品的信息损失位置；不是证明模型更强或训练完成。
- **代价/失败**：context 方案比较消耗真实推理资源；未绑定 owned service 时只保留设计，禁止外部工程模型代跑冒充产品。题目泄漏、任意改 token 预算、混合模型版本、缺失原始资料都使比较失效。
- **MODEL_LEARNING=CANDIDATE**：问题形式化/反例/评价标准，独立走 C2/C5 准入。

## 4. Lean / Comparator：先冻结语义，再检查实现是否证明同一命题

读取了 Math 的 Lean README、formalization.yaml、139/140 scope、三组 challenge/config 和实际 solution `Main.lean`，并读取 [Comparator 官方 README](https://github.com/leanprover/comparator/blob/ca04cfc72b550331658ec314bf47685281bfd4bf/README.md)。

`ComparatorChallenges/*.lean` 中的 `sorry` 是期望命题占位；要与 solution 模块及导入依赖区分，不能仅看到 challenge 的 sorry 就判定 solution 未证明。本轮对 LogConcaveQuery、NoiselessRegression、MemoryPrecision 的配置看到明确 theorem_names，definition_names 为空，允许 axioms 为 propext、Quot.sound、Classical.choice，`enable_nanoda=false`。因此不能声称这些配置已经做了 Nanoda 二次复核。

Comparator 核对期望声明与提交声明的一致性、许可公理和内核可接受性；信任仍包括 challenge/imports/构建配置和执行隔离。若允许 definition holes，即便形式证明通过也可能证明错的业务定义，官方强调需要额外语义审查。把全部业务改写为 Lean 本轮不具备收益证据。

**形式化状态**：139 所选查询复杂度命题由仓库声明已形式化；140 family 是 PARTIAL——主定理有声明，但 stronger 3/5 成功阈值、部分辅助/streaming 变体不在同一形式化范围。本地统一为 `FORMALIZATION_DECLARED / NOT_REPLAYED`，不能写成独立 proof PASS。

### 七项现有 Owner 的可执行约束映射

| Invariant | 现有落点 | 精确验证问题 / 未证明部分 |
|---|---|---|
| UNKNOWN 不静默变0 | canonical_data.py、database.py、Collector transaction tests | 生成 missing/null/unknown/真实0 输入，经相同写读/API后保持区别；实际源已存在，未重跑或修改保护文件 |
| terminal 不重执行 | collector/acquisition_plan.py、tests/test_acquisition_plan.py | 保存 terminal 后重复 continuation 只读同一结果；副作用计数不增长，checkpoint 不充当授权 |
| stale attempt 不 ack 新lease | guard/task_queue.py、tests/test_task_queue.py | 旧run/worker/lease组合对 ack/fail/heartbeat/checkpoint 都无写效果；已有本地修复受保护，未冒称线上 |
| Permission 不由 Context 推导 | security/permission.py、exact_resource_scope/scope_approval_binding tests | 任意合法 context 切换不能扩大 actor 被授权资源；未知域回退要另修，不能靠命名证明安全 |
| Evidence 不变身份 | Shared Evidence owner、test_evidence_chain / test_live_evidence_source_identity | 相同文本不同source仍不同来源；修改分析不覆盖原始Source identity；修订保留parent |
| RELEASED 前有必需同版Gate | governance machine contract / verifier / tests | 缺少任一必需gate、SHA不匹配或仅有旧成功不得判RELEASED；批准/发布/运行层次分开 |
| WAITING 恢复不扩scope | lumenis_live_dispatch.py + structured governance | 结构校验存在≠resume条件真实满足；比较恢复前后原批准scope/Job/owner，不能从ELIGIBLE自动派工 |

上述路径是已有验证的加固方向，**不是七项已经新实现或本轮跑过**。先复用现有测试，缺失 invariant 再补定向 property/state-machine 检查；只有传统检查表达不足且代价合理才评估 Lean。

**PRODUCT_ADOPTION=ADAPT**：冻结语义/假设/目标，再验证实现、版本和允许效果。**MODEL_LEARNING=CANDIDATE**：可审阅的反例与检查方法；没有训练许可。

## 5. 权利、可靠性与停止

Math 和 Comparator 采用仓库明确许可证约束；Math 根 LICENSE 为 Apache-2.0，引用的第三方作品不因被引用自动获得再分发/训练许可。方法卡应原创概括、保留归属和固定版本；不复制全文训练，不复制未公开推理。

本轮成果是原文的定向深读、假设审计、采用准备和代码 Owner 对应。没有证明序境采样、记忆、训练或业务能力获得某个数值提升。这是 10 月 7 日研究时点的原结论；10 月 8 日已获准并完成的研究方法应用见后续补录，其他任务仍遵守各自实际派工。无当前任务收益、假设不成立、资源不具备或需第二权威时 DEFER/REJECT。


---

## 10 月 7 日历史收口

当时仅做安全语义校准、源文研究和采用准备。没有运行论文算法、训练、真实业务推理、生产数据准入、UI开发或发布上线。现有未发布代码保持保护。完整产品能力及R/J/U验收要求均未缩减。完成总包后等待 Product Owner 审批。

## 2026-10-08 研究方法实际应用补录

**本节是 10 月 8 日的后续记录，更新 10 月 7 日收口时的状态。** Product Owner 随后明确要求把研究应用到实际产品缺陷，并批准本轮修复。本轮修复从 `6ff2cc0b68d8b9c3ae8ea658678242df8deac7dc` 开始；本节与修复源码同提交发布。精确提交和线上状态由 Git 查询确认，不使用历史基线冒充当前 HEAD。

### 把“声明检查通过”收紧为“实际语义成立”

Comparator 的官方说明指出：声明/常量图检查和内核接受不能自动证明业务定义符合意图，允许定义空洞时尤其要做额外语义审查。本轮没有运行 Comparator，也没有把 Lean 用作序境运行时验证器；采用的是其可迁移的审查方法：先固定状态语义，再用会区分相邻状态的真实调用链反例验证消费者。

在 Shared Learning 中复现并修复了一个违反现有生命周期合同的问题：人工把模型输出标为接受或拒绝后，记录仍是 `RAW`，旧实现却立即放进进程内正/负样本列表；`get_positive_samples()` 不检查 lifecycle，导致 `build_prompt_context()` 可消费未经晋级的样本；进程重启后样本列表又消失。现在样本类型随既有 `agent_learning_records` 修正记录保存，读取端只接受 `PROMOTED`；若 SQLite 中存在该记录，以持久化 lifecycle 为准，`ARCHIVED` 会从旧进程缓存和重启后结果中移除。普通 `accepted=true` 只标记类型，不再自动晋级，也不生成第二套授权或审批。

落点：`lumenis/shared/learning/loop.py` 的 `record_ai_correction()`、`lumenis/shared/learning/memory.py` 的样本/规则读取和 `promote_record()`，以及 `tests/agent_memory/test_learning_loop.py`、`test_learning_memory.py`、`test_memory_integration.py`。隔离 SQLite 回归现为 **39 项通过**，覆盖 RAW 不进入 prompt、完成 RAW→REVIEWED→VALIDATED→PROMOTED 后可消费、重启后相同样本可用、持久化归档覆盖旧进程缓存并移除样本。新增反例先通过第二个真实 DB 连接归档样本/规则，再模拟 `sqlite3.OperationalError("database is locked")`：旧进程不得复活缓存样本/规则，也不得仅凭缓存报告晋级成功；另验证 DB 有配置但记录已缺失时不得从缓存晋级。仅显式 `db_path=None` 的 memory-only 模式允许使用本地生命周期状态。错误注入模拟连接读取失败，不等同于操作系统文件锁压力测试。测试使用临时 seeded DB；没有读取或写入产品数据库。

### 收紧采集状态的来源语义

另一处已完成的定向修复统一了旧 `/api/collector/status` 注册入口，使路由注册顺序不再决定含义，并把凭据元数据 `NEED_VERIFY` 与历史平台验证/挑战结果分开。历史结果保留原检查时间并标为缓存来源、当前新鲜度未知；仅配置元数据没有证明平台已验证，故保持未核验。对应两个定向 API 用例 **2 项通过**。它不读取 Cookie/session、不发平台请求、不启动服务；现有 Collector Owner、原响应兼容字段和状态枚举保留。

本次复核的同一隔离测试批次合计 **41 项通过**（Learning 39 项 + Collector 状态 2 项），且未检测到后台线程泄漏。

### 研究范围与限制

- Family 140 的“有限持久状态、单遍观测和明示假设”提醒我们把记忆预算和数据来源写入比较条件；它**不是** LLM context/KV cache 的数学下界。这里修复的是已存在的 lifecycle 语义漏洞，并未声称提升模型准确率。
- Family 139 的查询复杂度不适用于社媒/API 请求；本轮没有引入其算法。
- 没有运行 Lean/Comparator、GPU训练、真实 Owned AI 推理、网络采集、生产 DB、服务重启或用户验收。真实运行是否把已提升样本绑定到生产 AI Gateway，仍需现有 Runtime/Evaluation Owner 的集成证据。
- 交付状态为源码实现与隔离组合验证；发布边界及精确测试见同目录语义校准 JSON 的 repair_verification。不能称为生产进程已加载、Owned AI 训练成果或全产品闭环。研究原件、历史材料和旧失败证据保留。

本轮报告中的“等待审批”仅记录 10 月 7 日研究时点；Product Owner 后续授权的范围是上述定向研究应用与缺陷修复，不自动恢复或派发 C1–C6、F 或 J1–J8。


### 对产品、研发和真实业务的现行应用

| 层次 | 已采用方法及现有落点 | 直接效果与限制 |
|---|---|---|
| 产品请求 | 将意图与实现分开核验；`domain_isolation`/`subject_context`统一身份，HTTP/API/Permission/Evidence consumers共享解析 | 未选焦点保持GLOBAL；非法焦点/域不会变成合法CTH或全局读取。合法身份仍须真实Scope授权。 |
| 真实业务 | 受控参考主体与一般商业体分开；CTH和风险读取复用签名Canonical，已驳回风险保留原状态判断 | 同一请求不会借默认广州或遗留notes读取代替目标主体；隔离数据库证明正常成功与拒绝，不替代客户实际重复验收。 |
| 反馈学习 | 生命周期的声明与消费者一起验：RAW→REVIEWED→VALIDATED→PROMOTED，归档/持久化失败不能借缓存复活 | 已进入Learning源码和重启验证；不是模型训练或质量提升百分比。 |
| Codex研发 | 先固定意图、列可区分的反例，再核对真实调用组合；本轮用独立期望的有限身份枚举、数据库权限组合、源版本隔离和共享调用回归 | 修复与入口文档同提交；后续窗口读取本记录与现有owner即可复用，不重新建研究表、候选目录或重复运行不变证据。 |

以上应用来自对假设、声明一致性、状态持久性和验证方法的适配。复杂图计数、随机博弈或渐近矩阵算法只有当现有任务确实满足假设且有可测收益时采用；保持既有DEFER结论，避免把论文名称变成实现理由。
