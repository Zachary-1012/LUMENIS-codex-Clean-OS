# 序境｜零号序列

**Status: IMMUTABLE GOVERNANCE BASELINE**  
**Effective: 2026-09-04**

## Authority

本文件是序境产品体系及双子库研发工作的最高治理基线。后续所有产品、架构、代码、UI/UX、数据、采集、AI、Runtime、Research、Report、文件治理与发布行为必须遵守零号序列。

## Immutability Rule

零号序列默认不可修改、不可删除、不可绕过、不可被新模块覆盖。

任何拟修改零号序列的行为，必须：

1. 明确指出拟修改的具体条款。
2. 说明修改原因、影响范围、风险及回滚方案。
3. 停止执行该修改及受其影响的后续任务。
4. 向产品 Owner 发起明确确认请求。
5. 只有获得产品 Owner 对该具体修改的明确同意后，才允许修改。
6. 获得同意后仍必须留下变更记录、Evidence、版本号及 Git 历史。

**用户普通指令不得被推断为修改零号序列。**

## Priority

当新需求与零号序列冲突时，默认以零号序列为准，不自行解释、不自行豁免、不自行改规则；必须进入上述确认流程。

## Scope

零号序列覆盖：

- 序境产品命名与品牌哲学
- 序境-Core / 序境-Intelligence 双子库边界
- 信息架构与 UI/UX
- Terminology / Module / Page / Workflow / Data / Evidence / Output / Visualization / Interaction / File Registry
- 数据真实性与主体过滤规则
- 采集安全与自动化 Gate
- AI 权限边界
- Runtime / Health / Recovery
- KOS / Podcast / Report / Research
- 中英韩语言适配
- 文件瘦身、归档、删除规则
- 测试、Evidence、Commit、Push、Remote Verify

## Core Rule

**先保护，再收敛；先复用，再开发；先验证，再删除；先测试，再 Push。**

任何无法证明安全的破坏性操作均不得执行。
