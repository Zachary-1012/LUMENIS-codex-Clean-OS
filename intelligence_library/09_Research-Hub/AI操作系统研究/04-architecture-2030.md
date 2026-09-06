# D｜OSAI 2026–2030 Architecture（14 层）

> 交付物 D · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## Layer 1: Identity（身份层）— P0
- **职责**：Agent 身份管理、用户身份、权限主体、审计追踪
- **核心组件**：Identity Provider、Agent Registry、User Profile、Audit Log
- **优先级**：现在做（基础依赖）

## Layer 2: Memory（记忆层）— P0
- **职责**：分层记忆存储（工作记忆/情景记忆/语义记忆/程序性记忆）、检索、遗忘
- **核心组件**：Working Memory、Episodic Store、Semantic Store、Procedural Store、Vector Retriever（Qdrant/Milvus）
- **技术选型**：MemGPT 分层策略 + 自研检索优化
- **优先级**：P0（Experience Engine 前置依赖）

## Layer 3: Experience（经验层）— P0（核心差异化）
- **职责**：Experience DNA 存储、Reflection、Learned Pattern 提取、规则引擎、可靠性评分、版本管理、Memory Poisoning 防御
- **核心组件**：Experience DNA Store、Reflection Agent、Pattern Extractor、Rule Engine、Reliability Scorer、Version Manager、Poisoning Detector（六层防御）
- **优先级**：P0（OSAI 最核心差异化能力）

## Layer 4: Research（研究层）— P0
- **职责**：文献检索、案例分析、证据收集、假设生成、研究流程管理
- **核心组件**：Search Orchestrator、Evidence Collector、Hypothesis Generator、Research Pipeline Manager
- **优先级**：P0

## Layer 5: World Model（世界模型层）— P2
- **职责**：Cognitive Map（Entity+Temporal+Causal 三层融合）、实体关系管理、时序知识、因果推理
- **核心组件**：Entity Graph、Temporal KG、Causal Graph、Cognitive Map Builder
- **优先级**：P2（依赖 Experience DNA 积累后构建）

## Layer 6: Planning（规划层）— P1
- **职责**：任务分解、长程规划、Checkpoint/Restore、动态调整、依赖管理
- **核心组件**：Task Decomposer、Long-Horizon Planner、Checkpoint Manager、Dependency Resolver
- **优先级**：P1

## Layer 7: Policy（策略层）— P0
- **职责**：决策策略、Interruption Policy、权限策略、行为约束、规则执行
- **核心组件**：Decision Engine、Interruption Policy Engine、Policy Engine、Rule Executor
- **优先级**：P0（与 Permission OS 协同）

## Layer 8: Tools（工具层）— P0
- **职责**：工具注册、工具调用、MCP Server/Client、工具安全沙箱
- **核心组件**：Tool Registry、MCP Server（OSAI 能力封装）、MCP Client、Tool Sandbox
- **优先级**：P0（基础能力）

## Layer 9: Browser / Computer Use（浏览器/计算机使用层）— P1
- **职责**：AI Browser Research Framework、Hybrid 感知（Vision+DOM+State）、Persistent Browser、Action Space
- **核心组件**：BrowserGym Adapter、Browser Run Runtime、Vision Perception、DOM Parser、State Manager、Action Executor
- **技术选型**：BrowserGym（框架）+ Browser Run（运行时）
- **优先级**：P1（集成而非自建）

## Layer 10: Coding / Development（编码/开发层）— P0（集成）
- **职责**：Research-to-Code 七层管道、Execution Contract 生成、Coding Agent 集成、代码审查
- **核心组件**：Research-to-Code Pipeline、Contract Generator、Trae Connector、Claude Code Connector、Code Reviewer（Skeptic）
- **优先级**：P0（集成 Trae/Claude Code，不自建）

## Layer 11: Evaluation（评估层）— P0
- **职责**：12 维评估矩阵、Benchmark 集成、持续评估、回归检测、能力趋势追踪
- **核心组件**：Evaluation Matrix Engine、Benchmark Integrator、Regression Detector、Trend Tracker
- **优先级**：P0

## Layer 12: Evidence（证据层）— P0
- **职责**：全链路证据收集、证据分级、证据存储、不可篡改审计
- **核心组件**：Evidence Collector、Evidence Classifier、Evidence Store、Audit Trail
- **优先级**：P0（安全基石）

## Layer 13: Learning（学习层）— P0
- **职责**：从结果中学习、经验更新、规则优化、能力进化、Learning Lift 测量
- **核心组件**：Outcome Analyzer、Experience Updater、Rule Optimizer、Learning Lift Measurer
- **优先级**：P0（与 Experience Engine 协同）

## Layer 14: Proactivity（主动性层）— P1
- **职责**：信号检测、Insight Engine、五阶段 Interruption Policy、通知分级、用户偏好学习
- **核心组件**：Signal Detector、Insight Engine、Interruption Policy Engine、Notification Manager、Preference Learner
- **优先级**：P1

## 架构演进路线图

| 阶段 | 时间 | 核心目标 | 关键层 |
|------|------|---------|--------|
| **Foundation** | Q4 2026 | 身份、记忆、工具、证据、安全基础 | L1, L2, L7, L8, L12, L10(集成) |
| **Core Differentiation** | Q1-Q2 2027 | Experience Engine、Research、Evaluation、Learning | L3, L4, L11, L13 |
| **Expansion** | Q3-Q4 2027 | Planning、Browser、Proactivity、Human Collaboration | L6, L9, L14 |
| **Cognitive** | 2028 | World Model、Cognitive Map、Autonomous Lab | L5, L6(增强) |
| **Maturity** | 2029-2030 | 全链路闭环、持续进化、OSAI 2.0 | 全部 14 层优化 |
