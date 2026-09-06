# IC-050 · AI Native App / Agentic App 架构前沿（研究侧）

> 状态：RESEARCH-DONE（2026-09-04，研究侧资产；待 Contract 后评估生产落点）
> 依据：2026 年 AI Native / Agentic App 架构前沿研究（arXiv 2603.20300、Builder.io、SITS2026、Zylos AI 等）
> 边界：不推翻现有架构，不引入第三方框架；取架构思想适配序境 AI 独立 App
> 反哺对象：序境 AI 独立 App 架构（Zachary AI 产品域）

---

## 一、证据基线（核心发现）

| 范式 | 内容 | 来源 |
|---|---|---|
| Agent-Native 架构 | Agent 操作产品而非评论产品（agent-native email app：起草回复+检查线程+打标签+归档+路由+拉CRM，最终发送决策留给人） | Builder.io 2026-05 |
| One Shared Action Model | Agent UI 一致性只有在同一能力模型同时驱动人类 UI 和 Agent 操作时才成立 | Builder.io |
| Agent Interface | 从 Human Interface 到 Agent Interface 的范式转移：结构化输入、显式语义、确定性执行；优化可解释性/可靠调用/可组合性，而非导航/可用性 | arXiv 2603.20300 |
| SITS2026 标准分层 | 感知层（多模态输入轻量适配器）→ 推理编排层（声明式 DAG 调度，动态选模型/精度/部署位置）→ 状态协同层（向量+图谱+关系库，跨会话因果推理） | CSDN SITS2026 白皮书 |
| Graph-based orchestration | 复杂工作流用图编排（分支/循环/并行/错误恢复），而非线性链 | GitHub Best Practices 2026-09 |
| Layered Memory | 短期对话 + 长期向量/图谱 + 团队共享记忆 | GitHub Best Practices |
| Approval orchestration | LangGraph interrupts / framework-native gates：高风险动作 durable pause/resume 人工审批 | Zylos AI 2026-05 |
| Activity panel | 独立审计层，工作流视图与对话线程分离 | Zylos AI |
| Error surface | 结构化 3 段错误：What / Why / Next | Zylos AI |
| Resilience | retries + fallbacks + circuit breakers + reflection loops | GitHub Best Practices |

## 二、序境映射（研究侧建议）

| 架构要素 | 序境现有 | 建议适配 |
|---|---|---|
| Agent Interface | 现有 REST API（/api/ai/*） | 为 AI 独立 App 建立结构化 Agent Interface（显式 schema + 确定性执行），与人类 UI 共享同一 Action Model |
| 推理编排层 | ai_channel 模型路由 + 资源包 | 参考声明式 DAG 调度，复杂 AI 任务用图编排（现有 ic_routes/podcast_routes 可演进） |
| 状态协同层 | SQLite + 文件型记忆资产 | 向量+图谱+关系库融合（IC-049 Agentic KG 窄切片试点） |
| Approval gate | HCG 人工门控（GATED_ACTIONS） | 对齐 LangGraph interrupts 模式：高风险动作 durable pause/resume |
| Activity panel | 现有 Audit/Evidence | 独立工作流审计层（与对话分离） |
| Layered Memory | 文件型记忆（记忆/技能/契约） | 短期对话 + 长期知识资产分层（IC-037 记忆架构参考） |

### 红线
- 不推翻现有 ZBC 生产架构；AI 独立 App 是新产品域（Zachary AI），通过 Contract/API 与 ZBC 交换。
- 不引入 LangGraph 等第三方框架；取架构思想在现有 Flask + ai_channel 上增量实现。
- 不建第三核心库。

## 三、Gate
- 进入生产前需 Contract：定 AI 独立 App 的产品边界、Agent Interface schema、与 ZBC 的 Contract/API 边界、双跑验证、Evidence。

## 四、下一动作
- 与 SYSTEM_APP_PRODUCT_BOUNDARIES_V1 的 Zachary AI 域对齐，起草 AI 独立 App 架构 Contract。
