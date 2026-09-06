# 序境 Language / Brand / Life Intelligence Research 知识库

**Status:** ACTIVE RESEARCH KNOWLEDGE BASE
**Authority:** 序境-Intelligence（Zachary-OS-AI）Research & Intelligence layer
**Repository:** `Zachary-1012/Zachary-OS-AI` / `03-RESEARCH/LANGUAGE-BRAND-LIFE/`
**Canonical Chinese Brand:** 序境
**Canonical Korean Brand:** 서경
**Canonical English Brand:** TBD（候选研究中）
**Core Philosophy:** 芥子纳须弥
**Canonical Definition:** 微小之中本身就包含通向整体的结构。

> 本库是「序境」语言 / 品牌 / 生命智能的系统性研究资产库。每一条知识记录都遵循统一字段：来源、证据等级 E0–E4、状态、适用语言/文化、时间与版本。研究结果用于反哺自研 AI，并服务舆情分析、内容理解、内容创作、创意营销、品牌研究、故事叙事及未来 AI/Agent/OS/Robotics 能力。
> **边界**：本库属于 Research 层，任何内容不得绕过 Contract / Evidence / Test / Audit / Release Gate 进入 Production Truth。

---

## 1. 证据等级（Evidence Level E0–E4）

| 等级 | 定义 | 示例 |
|---|---|---|
| E4 | 当前代码 / 仓库 / 官方一手材料已核实 | 本库 Canonical 定义、生产配置 |
| E3 | 多来源交叉核实的公开事实 | 品牌案例、获奖记录、已发表论文结论 |
| E2 | 单一可靠来源确认（学术/权威/一手） | 单篇论文、官方白皮书、佛典原文 |
| E1 | 推理 / 综合 / 概念延伸，未经独立验证 | 命名候选语义推演、方法论抽象 |
| E0 | 构想 / 假设 / 待验证 | 未来生命层系统构想 |

## 2. 记录状态机

| 状态 | 含义 | 迁移规则 |
|---|---|---|
| `FACT` | 当前代码 / 仓库 / 官方材料已核实 | 不可由研究层单方改写 |
| `VERIFIED` | 多来源交叉核实 | E3+ |
| `PENDING` | 尚需验证 | 可升 VERIFIED / 降 REJECT |
| `CONCEPT` | 哲学 / 架构 / 未来构想，不代表已实现 | 永久不冒充 FACT |
| `RECOMMENDATION` | 研究后的建议 | 需 Contract 后才可进生产 |
| `LEGAL REVIEW` | 需专业法律 / 商标审查 | 命名候选必经 |
| `LEGACY` | 历史资料，不作为当前规范 | 不自动失效 |
| `REJECT` | 已明确淘汰 | 记录淘汰原因，可复核重开 |

## 3. 命名研究协议（英文 / 韩文同一严格逻辑）

对英文与韩文 Canonical 候选均执行以下 8 步，缺一不可：

1. **候选生成**：由语义空间（Embedded Wholeness / Relation / Meaning / Life / Emergence…）+ 语言音韵特征生成候选集合。
2. **全球语言学负面含义**：跨主要语言（英/中/日/韩/西/法/德/意/葡/北欧/斯拉夫等）排查无负面或荒谬含义。
3. **中 / 英 / 韩音义联想**：三语发音、拼写、字形联想一致且可承载品牌语义。
4. **未来扩展领域同名冲突**：AI / Agent / OS / Robotics / Research / Life Science / Platform / SaaS 生态同名筛查。
5. **现实占用**：企业 / 产品 / GitHub 仓库 / 商标 / 域名 / 数字身份占用排查。
6. **Semantic Gravity（语义引力）**：名称自身携带的语义能否自然"吸附"品牌母题，而非依赖解释。
7. **生命层哲学测试**：候选是否与「芥子纳须弥 / Relation→Structure→Meaning→Intelligence→Action→Feedback→Evolution」兼容。
8. **十年生命周期测试**：能否承载十年后可能的品类 / 语言 / 文化扩展。

**报告门槛**：只有通过全部门槛、证据完整（含 LEGAL REVIEW 状态）的候选，才向产品 Owner 汇报完整证据与结论。普通候选、淘汰项、中间过程仅记录于本库，不打扰用户。

## 4. 研究主题索引

| 编号 | 文件 | 覆盖 |
|---|---|---|
| 00 | `00-PHILOSOPHY.md` | 哲学 / 世界观 / 芥子纳须弥 / Embedded Wholeness / Relational Becoming |
| 01 | `01-LIFE-SYSTEMS.md` | 生命系统 / 系统科学 / 复杂性 / 涌现 / 自组织 |
| 02 | `02-AI-AGENT.md` | AI / Agent / Reasoning / Memory / Robotics / Embodied AI / OS / Research |
| 03 | `03-LIFE-SCIENCE.md` | Life Science / 生命科学前沿 |
| 04 | `04-LINGUISTICS-NARRATIVE.md` | 语言学 / 中英韩文化语境 / 语义引力 / 品牌命名 / 内容创作 / 创意营销 / 故事叙事 / 舆情传播 |
| 05 | `05-NAMING-RESEARCH.md` | 命名候选登记 / 淘汰记录 / Nivellea 长期复核 |
| 06 | `06-MINIMAX-RESEARCH.md` | MiniMax 研究（模型/视频/语音/开源策略/采纳判定） |

> **并行基线**：`03-RESEARCH/LANGUAGE-BRAND-LIFE-INTELLIGENCE-RESEARCH-2026-09-04.md`（单文件外部核验研究，含 Relational Becoming 术语归属核验），与本多模块库互补，检索时两者并用。

## 5. 检索约定

- 每条记录以 `**[条目名]**` 开头，后接 `证据等级` / `状态` / `语言文化` / `时间版本` / `来源` 字段。
- 概念类条目必须标注 `CONCEPT`，不得冒充事实。
- 外部资料（论文/案例/开源项目）只作研究输入，进入生产前须经过适配、Contract、测试与审计。

## 6. 已确立不可变项（Zero Sequence 保护）

- 产品核心定位、序境品牌、서경、芥子纳须弥品牌哲学：**不可自行修改**。
- English Canonical Brand = TBD：在确认前不得改写正式 README 的 Canonical 英文名，不得修改仓库名。
- 双子库边界、Production Truth 所有权、Canonical 层级：**LOCKED**。
