# F｜Research → Code 技术方案

> 交付物 F · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## 七层 Research-to-Code Layer

```
Layer 1: Research（文献检索、案例分析、证据收集）
Layer 2: Architecture（技术方案设计、选型决策）
Layer 3: Decision（Build/Integrate/Adapt、风险评估）
Layer 4: Contract（标准化 Execution Contract 生成）
Layer 5: Plan（Implementation Plan、任务分解、依赖管理）
Layer 6: Evidence（执行证据收集、测试结果验证）
Layer 7: Learning（从执行结果中学习、更新经验）
```

## 核心决策：不自建 Coding Agent

- **国内首选**：Trae（免费+多模型+SOLO 主-子 Agent+MCP 原生）
- **国际首选**：Claude Code（SWE-bench 88.6%+CLI-first+强推理）
- **OSAI 角色**：Research→Architecture→Decision→Contract→Plan，不直接编码
- **MCP 集成**：OSAI 自身能力封装为 MCP Server，供 Trae/Claude Code 调用

## Execution Contract 模板

包含：需求描述、架构决策、技术选型、任务分解、验收标准、Evidence 要求、安全约束、回滚方案、ZBC 执行要求。
