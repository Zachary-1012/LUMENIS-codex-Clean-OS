# ZBC AI 舆情 Intelligence Upgrade 基线 v1.0

状态：研究转工程基线 / 不直接替换现有生产逻辑
日期：2026-09-02

## 1. 定位

ZBC 不升级为泛舆情平台。核心仍是以主体识别、主体硬过滤和广州太古汇业务边界为第一原则的小红书/社交传播情报系统。

本基线将“监测舆情”升级为“理解内容、情绪、立场、事件、人物、传播与变化，并输出可行动的传播情报”。

## 2. 研究依据

参考 2025-2026 年社交媒体 AI 研究与开源基准：
- AAAI 2026 SoMe benchmark：覆盖实时事件检测、流式事件摘要、错误信息检测、用户行为预测、用户情绪分析、媒体推荐和社交问答等任务，并提供约 924 万条数据和 1.78 万任务查询。
- COLING 2025 rumor detection：强调传播结构、root/branch/parent 关系以及 stance/sentiment 对社交媒体谣言分析的价值。
- NAACL 2025 RATSD：研究 claim 与 social post 的 truthfulness stance，并采用检索增强方法。
- ACL 2025 AIGT：研究社交平台 AI 生成文本的量化和监测。
- ACL 2025 PCoT：显示将 persuasion knowledge 纳入不实信息检测可以提升部分零样本检测表现。
- 2026 Information Fusion：研究多模态 misinformation 中的创作者认知/情绪策略与读者反应信号。

研究结论只作为设计输入，不直接视为 ZBC 生产规则；所有能力必须经过本系统 Evaluation 和 Evidence 验证。

## 3. Intelligence Object

未来统一分析对象：Content Intelligence Object（CIO）。

内容层：文本、图片、视频、评论、发布时间、来源、作者、链接。
语义层：主体、主题、情绪、立场、意图、对象、原因。
传播层：互动、增长速度、参与者、传播节点、关联内容、事件关系。
业务层：品牌/业态/活动/场景关联、风险、机会、客户行动建议。
证据层：原始内容引用、采集时间、解析器/模型、规则命中、Evidence。

## 4. 情绪 Intelligence

从单一 positive/neutral/negative 逐步升级为细粒度多标签情绪：愉悦、惊喜、治愈、松弛、兴奋、失望、不满、愤怒、焦虑、疑惑、嘲讽、混合等。

不得只输出情绪标签；优先形成：
Emotion + Target + Cause + Intent + Confidence + Evidence。

情绪是信号，不是业务结论。

## 5. Stance Intelligence

增加立场层：支持、认可、中立、质疑、反对、讽刺/复杂、未知等。

立场必须绑定 Target/Claim，避免把“对某一具体活动的质疑”错误理解为“对品牌整体负面”。

外部知识/RAG 不得默认增强 stance；研究表明外部信息在部分 LLM stance 任务中反而可能造成性能下降，因此必须经过 A/B Evaluation 后才能进入生产。

## 6. Advocacy Intelligence

从“正面内容”进一步识别真实品牌拥护行为：主动推荐、维护、复购表达、主动传播、为品牌辩护、持续正向表达等。

形成 Advocacy Signal/Score，不直接等同于用户价值或商业价值。

## 7. Event Intelligence

事件从静态聚类升级为生命周期：
Emerging → Growing → Peak → Stable → Declining → Closed。

事件对象至少记录：首次出现、最新更新时间、内容量、互动量、互动速度、参与作者、核心传播节点、情绪变化、立场变化、关联主题、风险与机会。

事件系统必须支持 Streaming Event Summary 与 Event Evolution。

## 8. Propagation Intelligence

重点从 Volume 升级到 Velocity + Structure：
- 总量
- 增长速度
- 互动速度
- 作者数量
- 核心作者
- KOL/KOC/UGC 分布
- 内容复用/相似传播
- 传播节点
- 事件关联

风险不能只由“负面互动 ≥ 某阈值”决定。

建议形成 Signal：Volume、Velocity、Sentiment、Stance、Influence、Propagation、Novelty。

## 9. Risk / Opportunity 双轨

风险：负面情绪、负面立场、异常增长、集中传播、事实争议、安全/歧视等高风险信号。

机会：正向情绪、品牌拥护、内容增长、KOC 自发传播、潜在内容主题、用户需求、内容空白。

风险和机会均输出 Signal + Confidence + Evidence，不得把模型概率包装成事实。

## 10. Multimodal Intelligence

文字、图片、视频、评论等进入统一 CIO。图片/视频分析至少可输出场景、主体、物体/品牌、视觉情绪、内容意图、文字与画面一致性等信号。

多模态模型只负责观察和解释；主体硬过滤与业务 Truth 仍由确定性规则/契约控制。

## 11. AIGC Signal

增加 AI-generated content Signal：Human-likely / AI-likely / Mixed / Unknown。

只作为辅助信号，不作为事实认定。需要结合内容、作者、行为和传播模式；禁止仅凭文风给账号定性。

## 12. Misinformation / Claim Intelligence

不建立一个“AI 直接判真假”的黑盒。

采用：Claim → Evidence Retrieval → Stance → Propagation Context → Multimodal Signals → Evaluation → Human Review。

对事实性高风险结论必须提供证据链和人工复核入口。

## 13. Hybrid Intelligence

ZBC 采用：
确定性规则 + 统计特征 + 专用模型 + LLM + Evidence + 人工反馈。

主体识别优先：SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit() 等核心规则不得被 LLM 替代。

LLM 不得单独决定：是否属于广州太古汇、是否为事实、是否触发生产级高风险处置。

## 14. Evaluation

每个 Intelligence Signal 都必须有可评估指标：Precision、Recall、F1、Macro-F1、Calibration、False Positive、False Negative、Latency、Evidence Completeness。

建立 Gold Set / Hard Cases / Regression Set。

按版本记录：模型、Prompt、规则、数据集、时间、结果和人工修正。

## 15. Learning Loop

生产数据：
采集 → 过滤 → 分析 → 事件 → 风险/机会 → 报告 → 人工反馈 → Evaluation → 脱敏 Learning Signal → Zachary。

生产数据不得直接成为 Zachary 全局 Truth。

## 16. Zachary × ZBC

Zachary：通用 AI / Reasoning / Tool / Browser / Resource / Evaluation Runtime。

ZBC：太古汇专业业务 Runtime。

共享通用能力；隔离产品 Truth、业务规则、权限、私有数据和 Runtime State。

Zachary 可提供通用能力；ZBC 生产结果经隔离、脱敏、Policy、Evaluation 后才能成为学习信号。

## 17. 优先级

P0：细粒度情绪、Stance、Event Lifecycle、Velocity、Evidence、Evaluation、Hybrid Decision、CIO 数据契约。

P1：Advocacy、Propagation Graph、多模态一致性、AIGC Signal、Claim Intelligence、机会检测。

P2：复杂因果分析、用户行为预测、长期传播预测、跨平台图谱。

## 18. 生产安全边界

不使用研究组件直接覆盖生产逻辑。第三方代码进入生产前必须 License/Security/Dependency/Compatibility Audit。

涉及账号认证、Cookie/Session、CAPTCHA、DRM、付费权限或明确访问控制绕过时，必须 Safe Stop + Evidence + Human Review。

## 19. 最终目标

ZBC 的输出从：
“今天有多少篇正负面内容”
升级为：
“今天发生了什么、谁在表达、他们是什么情绪和立场、事件处于什么阶段、传播速度如何、风险在哪里、机会在哪里、为什么这样判断、证据是什么、客户下一步可以做什么”。

## 20. 工程 Gate

研究 → Capability Audit → Data Contract → Minimal Implementation → Gold Set → Evaluation → Regression → Evidence → Cross-Repo Audit → Release Gate。

未经 Evaluation 和 Regression，不进入生产默认路径。
