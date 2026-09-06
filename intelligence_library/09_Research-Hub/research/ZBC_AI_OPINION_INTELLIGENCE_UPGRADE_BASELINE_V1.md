# ZBC AI 舆情 Intelligence Upgrade 基线 v1.0

本文件是 Zachary-OS-AI 对 ZBC AI 舆情 Intelligence Upgrade 的研究镜像与通用能力边界，不把 ZBC 业务规则写入 Zachary。

## 核心原则
ZBC 仍是主体过滤优先的专业传播情报系统，不升级为泛舆情平台。Zachary 只提供通用 AI、Reasoning、Resource、Evaluation、Tool 能力。

## Intelligence Object
统一 Content Intelligence Object：内容、作者、时间、来源、主体、主题、情绪、立场、意图、互动、速度、事件关系、风险/机会信号和 Evidence。

## 研究驱动能力
- 细粒度多标签 Emotion：Emotion + Target + Cause + Intent + Confidence + Evidence。
- Stance：必须绑定 Target/Claim，不能把局部活动态度误判为品牌整体态度。
- Advocacy：识别主动推荐、维护、持续正向传播等行为信号。
- Event Lifecycle：Emerging → Growing → Peak → Stable → Declining → Closed。
- Propagation：Volume + Velocity + Structure + Influence。
- Multimodal：Text/Image/Video/Comment/Context 统一进入 CIO。
- AIGC Signal：Human-likely / AI-likely / Mixed / Unknown，仅为辅助信号。
- Claim Intelligence：Claim → Evidence Retrieval → Stance → Propagation Context → Evaluation → Human Review。

## Hybrid Intelligence
确定性规则 + 统计 + 专用模型 + LLM + Evidence + 人工反馈。Zachary 不替代 ZBC SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit() 等主体 Truth。

## Evidence / Evaluation
所有高价值 Intelligence Signal 都应有 Evidence、模型/Prompt/规则版本和 Gold Set/Regression Set；评估 Precision、Recall、F1、Macro-F1、Calibration、误报/漏报、Latency、Evidence Completeness。

## Learning Boundary
ZBC 生产数据必须经过隔离、脱敏、Policy、Evaluation 后才可形成 Zachary Learning Signal。生产 Truth、产品业务规则、权限、私有数据、Runtime State 不进入 Zachary 全局记忆。

## Priority
P0：Emotion、Stance、Event Lifecycle、Velocity、Evidence、Evaluation、Hybrid Decision、CIO Contract。
P1：Advocacy、Propagation Graph、多模态一致性、AIGC Signal、Claim Intelligence、机会检测。
P2：因果分析、用户行为预测、长期传播预测、跨平台图谱。

## Gate
Research → Audit → Contract → Minimal Implementation → Gold Set → Evaluation → Regression → Evidence → Cross-Repo Audit → Release Gate。
