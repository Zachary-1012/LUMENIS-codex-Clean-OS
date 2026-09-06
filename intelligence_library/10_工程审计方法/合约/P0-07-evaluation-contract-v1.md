# LUMENIS Evaluation Contract — 序境评估契约（P0-07）

> 版本：V1.0 ｜ 生效：2026-09-05 ｜ 归属：LUMENIS Intelligence OS / Shared Contracts

## 1. 目的
对 AI / Skill / Agent / 补丁 / 研究成果做统一、可复现、有证据的评估。

## 2. 评估对象与维度
| 对象 | 核心维度 |
|---|---|
| AI 输出 | 正确性 / 置信度 / 预算 / 时延 / 可追溯 |
| Skill | 成功率 / 使用量 / 成本 / 证据 / Lifecycle |
| Agent | 任务完成率 / 权限合规 / 失败自愈率 / 证据完整度 |
| 补丁 | 编译 / 单测 / 回归 / 需求一致性 / 最小性 |
| 研究 | 证据强度 / 可落地性 / 与产品目标对齐 |

## 3. 流程
`Research → Evidence → Finding → Internal Proposal → Human Review → Implementation`
评估结论必须附：输入摘要、方法、结果、置信度、是否采纳、人工修正。

## 4. 判定纪律
- AI 不是业务事实最终裁判（红线④）：业务口径评估必须回到 ZBC 规则/数据/证据链。
- 不通过 = 不进入下一步；禁止删测试/屏蔽异常/伪造结果"修复"。

## 5. 落点
- 评估记录进入 `evidence/`；Skill 成功率进入 `skill_registry`（success_rate/usage）。
