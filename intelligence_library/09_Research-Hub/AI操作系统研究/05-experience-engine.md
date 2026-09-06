# E｜Experience Engine 技术方案

> 交付物 E · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## 核心设计：从"弱改变"到"强改变"

| 维度 | 普通聊天记忆（弱改变） | Experience Engine（强改变） |
|------|------------------------|------------------------------|
| 存储形式 | 自然语言文本 | 结构化 Learned Pattern + 规则 |
| 生效方式 | 检索后注入 Prompt | 注册到规则引擎，决策时强制匹配 |
| 置信度 | 无区分 | 三级可靠性分级 |
| 可执行性 | 模型自行解读 | 可被规则引擎直接执行的条件-动作对 |
| 防污染 | 依赖模型判断 | 六层防御 + 写入审批 + 版本回滚 |

## 核心流程

```
Task → Decision → Action → Outcome → Evidence → Failure/Success
  → Reflection → Experience → Learned Rule → Future Behavior
```

## 可靠性分级

- **硬约束（≥0.8）**：直接排除违反规则的动作，不可覆盖。需至少 3 条独立证据。
- **软引导（0.5-0.8）**：作为决策偏好注入，可被更高优先级规则覆盖。
- **参考信息（<0.5）**：作为上下文补充，不影响动作空间。

## Memory Poisoning 六层防御

1. **来源标记**：每条经验标记来源（human_input > evaluation_result > agent_self_reflection > external_data）
2. **写入审批**：自动审批/人工审批/影子模式/拒绝写入
3. **可靠性评分**：硬约束需 ≥3 条独立证据，单条证据最高 0.7
4. **记忆隔离**：项目隔离、安全域隔离、敏感信息隔离、临时经验区
5. **投毒检测**：异常频率/语义异常/来源异常/模式异常/分数异常
6. **版本回滚**：投毒确认后自动回滚到干净快照，24 小时冷却期

## P0 实现范围

Experience DNA 存储、Reflection→Learned Pattern 提取、规则引擎基础、可靠性三级分级、基础去重、版本快照+手动回滚、防御第一/二/三层、与 Decision Module 接口。

---

## 2026-09-02 学习进化更新（Learning Evolution Update）

> 来源：OSAI 持续学习进化摘要 `learning-feed/learning-20260902.md`（commit eda890f）

### Experience DNA 存储层参考（ADAPT｜P1）

参考 **HORMA**（arXiv 2606.11680）层级组织-检索记忆设计：
- Experience DNA 采用**文件系统式层级结构**：高层为摘要化 Learned Pattern，底层链接到原始经验轨迹
- 兼顾检索效率与细节保留（不丢失关键上下文）

### 回写机制参考（ADAPT｜P1）

参考 **ReasoningBank**（arXiv 2509.25140）：
- 从 agent 自我评判的成功/失败经验中蒸馏**可泛化的推理策略**
- 测试时检索相关经验 → 指导交互 → 完成后再回写新学习，形成持续增强

### 记忆效果基准化（ADAPT｜P1）

- 纳入 **Agent Memory Leaderboard**（136 支队伍/69 个记忆系统）与 **MemoryArena**（多会话基准）作为 OSAI Experience Engine 的记忆系统对标评测
- 评估"经验学习是否真正改变下一次行为"（Learning Lift）

### 方向确认

CaveAgent（港科大，"Code as Action, State as Memory"，永远在线的 Python 运行时）与 OSAI 的 Runtime 化思路一致，作为 RESEARCH_MORE 参考。
