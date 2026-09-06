# 三仓库协同 · 双产品供养 OSAI 权威规则 V1.0

> 落盘：2026-09-06｜事实来源：线上 GitHub Zachary-1012/Zachary-OS-AI main README（SHA 2b469d5，在线核对，非本地副本）
> 用户原话纠正：三仓库 = ZBC（含 CTH+ZBMP）+ GGI 两个产品供养 OSAI；本批 OSAI 资料均为 ZBC 可用、不涉红线

## 一、三仓库定位（线上权威）
| 仓库 | 线上名 | 角色 |
|---|---|---|
| OSAI | Zachary-OS-AI | **LUMENIS Intelligence / Shared Intelligence Growth Layer** 共享智能成长核心：Agent/Skill/Reasoning/Evidence/Evaluation/Memory/Learning/Trace/Capability/安全执行；**不是任何产品的运行时依赖** |
| 产品一 | Z-Brand-Core（ZBC/序境 Production Core） | 生产核心，**内部含 ZBMP + CTH 两个产品域** |
| 产品二 | global-growth-intelligence（GGI） | 全球作品增长智能平台，**独立产品**，拥有自己的 Product/Research Truth |

供养方向（双向但受控）：
```
 ZBC(ZBMP+CTH) ┐ validated Contract/Artifact ┌→ OSAI Admission → Learning Asset/Skill/Memory/Capability
 GGI(独立产品) ┘───────────────────────────┘            │
                        版本化、可追溯回供 ←─────────────┘
```
**注意：供养 OSAI 的"两个产品"是 ZBC 与 GGI（不是 ZBMP 与 CTH；ZBMP/CTH 是 ZBC 内部两个域）。**

## 二、OSAI 六条硬边界（红线，整合资料时必须守）
1. 不拥有序境(ZBC) Production Truth
2. 不拥有 GGI Product/Research Truth
3. 不直接修改两个产品的生产数据库
4. **不成为两个产品启动/采集/分析/报告/核心业务的前置（runtime）依赖**——OSAI 不可用时 ZBC、GGI 必须能各自独立运行
5. 不复制两个产品的业务代码
6. 共享只能通过**版本化、可追溯的 Contract / Artifact**

## 三、Intelligence Admission 准入链（研究/贡献不得直接变生产能力）
Task/Result → Evidence → Evaluation → Human Feedback → Contribution → Validation → Generalization → Admission → Learning Asset → Skill/Memory/Capability
生命周期状态：CANDIDATE → VALIDATED → GENERALIZABLE → ADMITTED
- 未经验证的产品数据/AI输出/研究结论/经验，不得直接成为共享能力资产，更不得自动变 ZBC 生产规则
- 生产写入由目标产品(ZBC)最终控制，OSAI 不绕过 ZBC 权限/Approval/安全边界

## 四、对本次 ZBC 资料库整合的具体约束
1. 用户已授权：本批 OSAI 研究资料 ZBC 可用、不涉红线，可整合进 ZBC intelligence_library（受治理副本+元数据索引）
2. 但 ZBC 只整合**与 ZBC（ZBMP/CTH）相关**的 OSAI 研究资产；**GGI 专属的 Product/Research Truth 不混入 ZBC**（GGI 是独立产品），在索引中标 product 归属：ZBC / GGI / SHARED
3. OSAI 代码/能力进入 ZBC 必须走 Admission 链并在"12_研究→ZBC落地索引"标五态（已落地/已实现待验证/可直接复用/建议转化/仅研究不应转化），**禁止 import OSAI 作为 runtime 依赖、禁止拷贝其业务代码**
4. ZBC 生产 Evidence/Evaluation 反哺 OSAI 时，只通过版本化 Contract/Artifact，不直连 OSAI 库、不共享生产凭据
5. AI Gateway 策略沿用：Zhipu + Local AI → Explicit Failure → Safe Degradation；Provider 异常不得吞成"成功但空结果"
6. 能力完成标准（防止文件存在=完成）：Source+Call Graph+Contract+Runtime+Permission+Data/Evidence+Tests+Verification 全成立；状态严格 PLANNED/IMPLEMENTED/TESTED/VERIFIED/RELEASED/OPERATING

## 五、其他线上仓库（Zachary-1012 名下共10个，避免混淆）
- lumenis-command：LUMENIS 私有研发指挥台；Development-Command-Console(DCC)：AI 软件工程指挥台（独立）；SICI-Core：研究学习平台（独立）
- siji / siji-driver / "-"：ZBC 移动端驾驶舱与手机开发控制台（公开）；NSFW：性心理学研究（与 ZBC 无关，不纳入）
- 本次只整合与 ZBC 相关资产；DCC/SICI 平台独立不并入，仅其研究文档按规则入资料库
