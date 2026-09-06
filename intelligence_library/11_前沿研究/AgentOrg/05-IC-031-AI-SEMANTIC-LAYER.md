# IC-031 · AI Semantic Layer 运行时拦截（AI 数据访问治理）

> 状态：RESEARCH-DONE（2026-09-04，研究侧资产；不新建重型平台，先评估再设计）
> 依据：Cycle U（数据治理/数据工程，Unity AI Gateway 思想）技术雷达 §26
> 边界：序境规模小，取"治理内建+lineage+quality 前置"核心机制，不引入重型数据平台、不建第三库
> 反哺对象：AI/Canonical 体系（Canonical Capability Convergence V1）

---

## 一、证据基线（Cycle U 核心发现）

| 范式 | 内容 |
|---|---|
| Canonical Data Mesh | 数据作为产品、ownership 靠近业务域、共享自助平台、联邦化治理；治理内建全链路并携带 context（ownership/lineage/quality/access/operational visibility）贯穿 ingestion→orchestration/quality→discovery/lineage→access policy→serve trusted data |
| Unity AI Gateway | 从被动"system of record"进化为**主动运行时决策引擎**——拦截裁决每个模型调用、工具调用、agent 行为 |
| Agentic 时代 | 数据全生命周期收敛进单一平台（LTAP 打破操作/分析分离） |
| OpenSharing | Delta Sharing 扩展到 agent skills/AI models 统一交换协议 |

## 二、序境落点建议（研究侧）
| 能力 | 建议 |
|---|---|
| AI 数据访问运行时裁决 | 对 AI/Agent 的 Canonical 数据访问做拦截裁决：**读查允许、改禁**（AI 不得直接修改 Production Truth） |
| 治理内建 | 数据访问携带 context（ownership/lineage/quality），与现有 Canonical Function/Metric Registry 对齐 |
| 不建重型平台 | 在现有 ai_channel/权限体系上增量设计，不引入 Unity 类平台 |

### 红线
- AI/Agent 只能通过 Semantic Layer→Metric→Canonical Dataset→Evidence 获得业务数据（对应 UDIP 第十一阶段）。
- 不新建第三核心库；不改现有生产架构。

## 三、Gate
- 进入生产前需 Contract：定拦截规则（读/改边界）、落点（ai_channel 或权限层）、双跑验证、Evidence。

## 四、下一动作
- 与现有 ai_channel 权限/安全边界对照（agent_security.py/ai_governance.py），评估运行时拦截落点。
