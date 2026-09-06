# S｜最终 P0/P1/P2 Roadmap

> 交付物 S · 所属：OSAI P0 三位一体研究体系 · 综合判断层
> 状态：P0 25项 + P1 18项 + P2 11项 + 依赖关系图 + 23个里程碑 + 资源估算（约96人月）

## 奠基期里程碑（2026 Q3-Q4）

| 里程碑 | 时间 | 核心交付 |
|--------|------|---------|
| M1 架构共识 | 2026.09 | 三位一体架构文档、组件规范(Contract+Experience DNA+MCP)、插件规范 |
| M2 OSAI P0能力PoC | 2026.10 | Skeptic Agent、Permission & Evidence OS、Evaluation Framework、Experience Engine、记忆管理、编排器、Proactive L2、Human-led协作 共8项PoC |
| M3 ZBMP核心能力MVP | 2026.11-12 | 数据采集框架、基础NLP引擎、多租户运行时、实时预警引擎、插件运行时 |
| M4 CTH垂直聚焦完成 | 2026.12 | 功能删除/降级执行完毕、活动ROI量化模块v1.0、危机预警重构v1.0、AI报告引擎v1.0、竞品对比体系v1.0 |
| M5 第一个闭环验证 | 2026.12 | Skeptic Agent组件工程化→集成ZBMP→CTH危机预警验证→反馈回流OSAI |

## P0 优先级 Top 10

| # | 任务 | 负责层 | 人月 | 依赖 |
|---|------|--------|------|------|
| 1 | 三位一体架构设计与规范建立 | 跨层 | 3 | 无 |
| 2 | Permission & Evidence OS PoC | OSAI | 5 | 架构规范 |
| 3 | Skeptic Agent 第一层 PoC | OSAI | 4 | 架构规范 |
| 4 | ZBMP 数据采集框架 MVP | ZBMP | 6 | 架构规范 |
| 5 | ZBMP 多租户运行时 MVP | ZBMP | 6 | 架构规范 |
| 6 | CTH 活动传播ROI量化模块 v1.0 | CTH | 5 | 数据采集+NLP |
| 7 | CTH 危机预警体系重构 v1.0 | CTH | 4 | Skeptic+预警引擎 |
| 8 | CTH 功能删除/降级计划执行 | CTH | 4 | 架构规范 |
| 9 | Evaluation Framework PoC | OSAI | 3 | 架构规范 |
| 10 | Skeptic Agent 组件工程化+集成+CTH验证 | 跨层 | 3 | Skeptic PoC+插件运行时+危机预警 |

## P1（18 项，摘要）

Proactive 引擎、Experience Engine 增强、AI Browser 研究框架、World Model 初版、市场情报周报自动化、ZBMP 插件生态、CTH 竞品对比体系 v2、OSAI 组件 MCP 化、…

## P2（11 项，摘要）

商业综合体知识图谱、Autonomous Experiment Lab、跨项目经验共享、OSAI 认知闭环、ZBMP 外部客户拓展、…

## 团队配置建议（第一年 18-20人）

AI研究工程师3-4、后端工程师（平台）4-5、后端工程师（应用）3-4、前端2、数据工程师2、产品经理2、商业地产行业专家1-2、测试/运维1。

## 依赖关系原则

- OSAI 组件 → ZBMP 插件运行时 → CTH 垂直应用
- 安全与证据 OS 为一切前置
- 每个里程碑产出 Evidence 回流 OSAI
