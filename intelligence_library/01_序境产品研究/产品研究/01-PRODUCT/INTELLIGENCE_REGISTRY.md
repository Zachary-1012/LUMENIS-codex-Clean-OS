# 序境-Intelligence｜Module / Workflow / Data Registry

> Canonical Intelligence Baseline · 2026-09-04
> 依据：《序境｜双子库全量收敛与产品研发总执行指令》
> 说明：本 Registry 基于 OSAI 仓库真实源码盘点建立，映射到序境统一 IA。
> 状态：INVENTORY-DONE / CONTINUOUSLY-MAINTAINED
> 边界：Intelligence 掌握研究 / AI / 知识资产；生产业务真相由序境-Core 负责，跨库复用走 Contract / Adapter，不复制核心实现。

---

## 1. 信息架构（IA）

```
序境
├─ 观测  来源 / 采集 / 内容 / 舆情        （Core 生产）
├─ 洞察  趋势 / 事件 / 风险 / 机会        （Core 生产 + Intelligence 分析）
├─ 关系  品牌 / 创作者 / 内容 / 事件关系   （Core 生产）
├─ 行动  KOS / Campaign / 处置           （Core 生产 + Intelligence 建议）
├─ 研究  AI / 时尚 / 设计 / 高奢 / 重奢 / 创新品牌 / 技术   （Intelligence 主责）
├─ 创作  Podcast / Report                （Intelligence 内容 + Core 数据）
├─ 智能  AI / Search / Assistant / Analysis  （Intelligence 主责）
└─ 系统  Settings / Permission / Sources / Accounts / Runtime / Health  （Core 生产 + Intelligence 治理）
```

---

## 2. Module Registry（序境-Intelligence）

> Module ID 规则：`IMOD-<IA分组>-<序号>`。Owner 唯一；研究结论不得自动变成生产规则。

| Module ID | IA 分组 | 模块名 | 核心源码 | 职责 | 状态 |
|---|---|---|---|---|---|
| IMOD-INT-01 | 智能·Agent | 研发智能体 | osai_engine/agent.py · orchestrator.py | Intent→Planner→Policy→Tool→Evidence 研发编排 | PASS |
| IMOD-INT-02 | 智能·LLM | 大模型网关 | osai_engine/llm.py · config.py | 分级模型路由、预算、上下文管理 | PASS |
| IMOD-INT-03 | 智能·规则 | 规则与安全 | osai_engine/rules.py | 研发规则、安全 Gate、不可信输入防护 | PASS |
| IMOD-INT-04 | 智能·工具 | 类型化工具 | osai_engine/tools.py | 受控工具调用、Scoped Runtime | PASS |
| IMOD-INT-05 | 智能·证据 | 证据链 | osai_engine/evidence.py | Evidence 记录、可追溯 | PASS |
| IMOD-RES-01 | 研究·技术 | AI OS 研究 | ai-os-research/ | 能力雷达、竞品矩阵、架构研究、安全沙箱 | PASS |
| IMOD-RES-02 | 研究·行业 | 品牌营销知识 | learning-feed/brand-marketing-knowledge-*.md | 全球 4A / 时尚 / 高奢 / 重奢 / 创新品牌方法论沉淀 | PASS |
| IMOD-RES-03 | 研究·创意 | 创意引擎研究 | learning-feed/ 创意/文学/情感共鸣系列 | 反模板化创意、圈层符号、文学句库研究 | PASS |
| IMOD-CRE-01 | 创作·播客 | Podcast 方法论 | learning-feed/brand-marketing-knowledge-25-*podcast* | 播客动态模板、嘉宾/受众/议题适配研究 | PASS |
| IMOD-CRE-02 | 创作·报告 | 报告方法论 | ai-os-research/ · 报告研究 | 报告母模型、决策信息优先研究 | PASS |
| IMOD-SYS-01 | 系统·契约 | 双库契约 | contracts/ | HCG / Capability / 双库 Contract 治理 | PASS |
| IMOD-SYS-02 | 系统·审计 | 复盘与对账 | reconciliation/ · evidence/ | 工程复盘、Evidence 汇总 | PASS |
| IMOD-SYS-03 | 系统·UI 工具 | 智能工作台 | osai-ui/ | 内部研究/研发 UI 工具 | PARTIAL |
| IMOD-SYS-04 | 系统·脚本 | 研发脚本 | scripts/ · tests/ | 自动化、测试编排 | PASS |

---

## 3. Workflow Registry（Intelligence 关键流程）

| Workflow ID | 名称 | 触发 | 步骤链 | 状态 |
|---|---|---|---|---|
| IWF-RESEARCH-01 | 研究→代码 | 需求/持续 | Research→Finding→Decision→Architecture→Contract→Requirement→Evidence | PASS |
| IWF-LEARN-01 | 品牌营销学习 | 持续 | 全网/外网研究→提炼→脱敏→learning-feed 沉淀→可复用 | PASS |
| IWF-CREATE-01 | 创意/比稿生成 | 按需 | 需求→Context→Audience→Platform→Objective→Tone→Research→Generate→Review | PASS |
| IWF-DEBUG-01 | 工程回合闭环 | 任务 | Research→Minimal Patch→Test→Evidence→Continue | PASS |

---

## 4. Data Registry（Intelligence 关键数据对象）

| Data ID | 对象 | 位置 | 口径 | 备注 |
|---|---|---|---|---|
| IDAT-KNOWLEDGE | 品牌营销知识 | learning-feed/ | 脱敏、可溯源、方法论化 | 个人业务资料只存本地，不进入线上 |
| IDAT-RESEARCH | 研究报告 | ai-os-research/ | 结论分级 ADOPT/ADAPT/RESEARCH_MORE/REJECT/LEGACY | 研究不自动变成生产规则 |
| IDAT-EVIDENCE | 研发证据 | evidence/ | Task/Source/Time/Input/Result/Verification | 敏感信息不入库 |
| IDAT-CONTRACT | 双库契约 | contracts/ | HCG 状态机、能力归属 | 与序境-Core 同步 |

---

## 5. 维护规则

1. 新增研究/智能能力先在本 Registry 登记并判定 IA 归属，禁止直接新增一级入口。
2. 研究结论 → 生产必须走 `Research → Finding → Decision → Architecture → Contract → Implementation Requirement`，并标记 ADOPT / ADAPT / RESEARCH_MORE / REJECT / LEGACY。
3. 跨库能力复用走 Contract / Adapter，禁止复制生产核心实现。
4. 状态统一：`PASS / PARTIAL / BLOCKED / NOT_VERIFIED / FAILED / LEGACY / DEPRECATED`。
5. 本 Registry 随 OSAI 真实代码变更持续更新。
