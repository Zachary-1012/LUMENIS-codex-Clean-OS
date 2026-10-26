# LUMENIS AI Product Closure Checklist V1

## Purpose

用于 LUMENIS 从 AI Runtime 接入到 GPT-level Product Experience 收口阶段的验收清单。

原则：Owned inference, Evidence-backed, Replaceable。C2 执行，C5 资料成果，C3/C4 消费，C6 部署恢复。旧本地模型/智谱停止、接口保留；免费/已有资源优先。

## 1. Chat Memory

- 项目上下文记忆
- 用户可控记忆
- 历史任务状态
- 记忆更新与删除

## 2. Context Manager

- 长对话压缩
- 多文档上下文
- Token预算管理
- 重要信息优先级

## 3. Tool Calling Framework

支持：

- 文件
- 数据库
- Git
- 浏览器
- 产品已批准的文件/媒体程序（不恢复通用OS控制）
- 外部API

要求：权限、日志、Evidence、可回放。

## 4. Prompt / Skill Registry

- Skill注册
- Prompt版本管理
- 能力模块
- 任务模板

## 5. Evaluation System

- 正确率
- 幻觉率
- 稳定性
- Benchmark
- 回归测试
- 模型对比

## 6. Model Routing

SYSTEM AI Gateway 统一管理产品运行模型：

- 获批固定预训练推理、行业工具和受控策略学习；GPU训练撤销；可选CPU专用参数仅在独立收益成立时准入
- 停用 provider 接口/历史（不可调用/探测/自动发现/fallback）
- 新模型须批准、真实评估与晋升回滚

原则：保留用户显式选择；仅在已批准能力/资源集合内优化调度，不能自动换模型、回退外部API或用更强模型补答案。

Canonical owner：`lumenis/system/ai_gateway/`。`local_ai_client.py` 和现有 `/api/local-ai/*` 是需保留行为后收敛的兼容调用路径，不得形成第二或第三个 AI Gateway。

## AI Runtime Target Architecture

```
User
 ↓
LUMENIS Chat Interface
 ↓
Intelligence Router
 ↓
Owned inference / Deterministic functions / explicit failure recovery
 ↓
Agent + Tools
 ↓
Evidence
 ↓
Response
```

## Owned AI Independence Gate

必须验证：

- 旧本地模型与智谱停用
- 外部模型 API 关闭，开发助手不代分析
- 自有推理实际运行，部署资源有证据
- 真实业务分析完成
- Evidence生成
- 结果返回产品层

## Engineering AI Boundary

Codex（包括 Cloud）仅作研发：

用于：

- 研发
- 审计
- 测试
- 自动化

OpenCode 历史配置 .opencode/opencode.json 保留、模型调用停止。Codex Cloud 是研发环境，不是序境生产推理服务；不能绕过 Permission/Evidence。

## Historical source disposition (not current runtime proof)

- 默认只用序境自有模型；Ollama/LM Studio/llama.cpp/Zhipu/OpenCode/Ark 调用代码已删除；仅保留一个 OpenAI 兼容通用接口供用户自选接入自购 API，不得探测、保活或自动 fallback。
- OpenCode 历史配置保留，不构成当前执行资源。
- AI-01：当前 App 只显示 provider/能力状态，真实意图提交与 Evidence Trace 尚未闭环；不得把状态页写成完成的 AI workflow。

## Research Optimization Layer

包含：

- Auto Research
- Performance Race
- Execution Efficiency

定位：持续优化系统，不直接成为Production Truth。

## 专业任务与资源验收

同任务/同输入/同预算的模型直答、检索、工具、策略、可选专用模型及完整组合分别评价；按主体/品牌/时间/来源族隔离最终留出，多次运行、原件数值引用核对、人工盲审与p50/p95/峰值内存/调用成本；关键事实、否定、身份、权限或重复效果错误不能由均分抵消。

CTH经营判断/行动取舍、BMP品牌市场/创意/Campaign、Shared多源反证与原创修改，分别使用真实来源、业务工具、可编辑结果、v1/v2、独立重开导出、取消/断线/撤权/冲突恢复。多模态/十二语逐项验，不以文本接口代替。完整上下文保存与真实token预算分验；BM25_ONLY不算神经Hybrid，inactive学习候选不算激活或收益。必要条件不可被摘要或检索内容覆盖。

## Production Closure Gate

进入 GPT-Level Experience Ready 前必须通过：

- Chat Memory PASS
- Context PASS
- Tools PASS
- Skills PASS
- Evaluation PASS
- Routing PASS
- Fixed pretrained inference / actual business consumers / independent held-out professional evaluation PASS
- GPU training route WITHDRAWN_BY_PO; optional CPU specialist parameter learning has its own approval, reload and benefit gate, not a universal prerequisite
- Bounded failure / recovery / rollback PASS without retired providers
- Evidence PASS
- Security PASS

## Status

当前：Governance Requirement

最终状态：

- SHADOW_READY
- READY_FOR_AUDIT
- PRODUCTION_CANDIDATE
- PRODUCTION_APPROVED

禁止未验证声明完成。

## C2 research-to-product obligations

OpenAI、Codex、ChatGPT、Claude、Meta Muse 五个学习对象全部保留。学习公开文档和
可观察行为，不声称拿到私有推理、专有权重或未许可标签。理解、分析判断、
原创修改、工具执行、上下文/长任务/恢复、受控评价学习六类能力及产品交互必须验证。

OSAI 独特有效资产按来源/许可适配现有 Gateway/Agent/Memory/Retrieval owners，
不复制平行runtime/资料库。固定预训练推理、策略配置与可选CPU参数按Architecture §6/J27分类准入；GPU训练撤销。CPU参数若获准，才要求真实数据/留出、版本、参数重载及业务收益；分类模型不能替代行业推理和创作。

Source Brief、文档表格、图片、视频分镜和音频必须实际解析并进入 CTH/BMP/创作。
文本模型不自动具备多模态。Realtime 仅实时对话语音后置，音频文件、视频音轨
及播客保留。精确 scope、来源真实性、事实/推断/创意、引用、有用性、改稿前后
评价、工具效果边界、中断续跑、授权撤销和晋升回滚分别证明。

Codex 补足公开取材走 Source/Import → Evidence → Canonical，标明 assisted discovery，
不冒充产品自主采集。保存报告不是训练，只有审阅且许可合格目标可进入训练。
摘录、“分析不可用”和非空回复均不能通过 C2。C3/C4 产生真实 Outcome/Feedback，
C2 通过既有 Evaluation/Learning 做真实对照后晋升，C6 验证独立运行、重载和恢复。
