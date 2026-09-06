# GitHub 标杆学习记录 02 · Agent Skill 治理与安全 · 2026-09-02

> 学习来源：GitHub 搜索（prompt injection detection / agent skills / 舆情监测）
> 本轮主题：Agent Skill 治理范式 + AI 供应链安全 + OSAI/ZBC 落地映射

---

## 一、新学到的标杆

### 1. sickn33/agentic-awesome-skills (AAS Core, 45.8k★)
**核心范式**：本地 agent skill 目录 + agent 自主选择 + 可复现计划 + 人审
```
Project → 被 Codex/Claude 检查 → agent 搜索读取本地完整 catalog
→ AAS MCP（本地 stdio，只读）→ agent 选择精确 skill ID
→ compose_stack 在内存验证选择（只读）→ 持久化 aas-stack.json
→ validate + 不可变计划预览 → 人工审阅
```
**关键点**：
- catalog 2108 个 skills（v16.6.0），版本化 registry-sync
- `compose_stack` 是只读验证工具——**不排名不推荐，只校验 agent 的选择**
- 不可变计划（immutable plan）在任何目标变更前生成
- SKILL.md 是可复用 playbook，MCP 是内容分发层

### 2. VoltAgent/awesome-agent-skills (33.6k★)
- 1000+ agent skills，跨 Claude Code/Codex/Gemini CLI/Cursor
- 强调 SKILL.md 作为跨平台 agent 技能标准

### 3. affaan-m/ECC (246k★)
- agent harness 性能优化系统：skills/instincts/memory/security
- 与 ZBC security_scanner 思路同源（Agent 运行时安全）

---

## 二、对 OSAI 的落地映射（ADOPT/ADAPT）

| AAS Core 概念 | OSAI/ZBC 现状 | 落地建议 | 决策 |
|---|---|---|---|
| 本地 skill catalog + registry 版本化 | OSAI components/ 下 untracked 目录 | 建立 skills-catalog 清单（registry-sync 式） | **ADAPT** |
| compose_stack 只读验证 | ZBC 无对应 | 给 OSAI 技能接入加"只读验证"闸门（不直接写生产） | **ADOPT** |
| 不可变计划 + 人审 | OSAI FINAL-AUDIT 有冲刺计划 | 把 Sprint 计划改为"不可变 commit 前预览" | **ADAPT** |
| Skill 供应链风险（SkillSpector 思路） | ZBC S2 已加 Prompt injection 检测 | 已完成 ✅ | **DONE** |
| agent security 作为 harness 一等公民 | ZBC security_scanner | S2 增强已入库 | **DONE** |

---

## 三、沉淀结论

1. **OSAI 下一步高价值项**：为 OSAI 建一个轻量 `skills-registry.json`（版本化技能清单），对齐 AAS 的 registry 范式——让 OSAI 的研究能力可被 agent 检索、验证、复用。
2. **安全增强已闭环**：S2 已把 SkillSpector 的供应链风险检测落地到 ZBC security_scanner（7 条 Agent/AI 风险模式 + 5 项测试通过）。
3. **学习方式**：GitHub 搜索 → 读 README → 提取范式 → 映射到双库 → 落地成可验证功能。持续进行。

---
*本记录入库位置：D:\Zachary OS AI\learning-feed\*
