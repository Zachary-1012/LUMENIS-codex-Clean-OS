# 可复用学习单元登记（Learning Units Registry）

> 来源：P0 自主研究总指令「本轮已形成的可复用学习单元 A-D」+ 落库结论。
> 状态：OSAI 研究侧知识框架登记；进入生产必须经证据门（E0-E4）+ Release Gate。
> 关联：`00-GOVERNANCE/AUTONOMOUS-RND-DIRECTIVE-P0-P1-2026-09-04.md`、`03-RESEARCH/LANGUAGE-BRAND-LIFE/`。

## A. 语言智能单元（Linguistics）
Lexeme（词位）· Phonology（音系）· Morphology（词法）· Connotation（内涵）· Register（语域）· Slang（俚语）· Cultural Association（文化联想）· Pronunciation（发音）· Translation Drift（翻译漂移）· Semantic Gravity（语义引力，CONCEPT/筛选框架）

应用：命名筛选（候选词→音系→中/英/韩联想→俚语双关→占用→Agent/OS/机器人冲突→Semantic Gravity→长期扩展）、品牌落地（序境/서경）。

## B. 叙事智能单元（Narrative）
微小事件 → 情绪 → 关系 → 冲突 → 场景 → 记忆 → 价值 → 传播 → 反馈

应用：内容创作（微小细节承载完整故事世界）、创意营销（局部生活经验→品牌整体价值）、KOS 内容策略。

## C. 舆情智能单元（Public Opinion）
内容表层 → 情绪层 → 语义层 → 关系层 → 叙事层 → 群体层 → 风险层 → 决策层

应用：从单条笔记识别更大情绪/叙事/群体变化；**关键原则**："用户说了什么" / "系统推测用户想表达什么" / "模型建议怎么回应" 必须分开存储（证据边界）。

## D. AI 学习单元（AI Learning）
Observation（观察）→ Interpretation（解读）→ Hypothesis（假设）→ Action（行动）→ Feedback（反馈）→ Revision（修正）→ Consolidation（巩固）

应用：Agent 经验形成（Problem→Context→Attempt→Action→Failure→Solution→Evidence→Result→Evaluation）、ZELL 闭环（Learning 阶段复用）。

---

## 知识证据等级（E0-E4）与状态
- 证据等级：E0 未验证线索 ｜ E1 单源可复核 ｜ E2 多源一致 ｜ E3 权威/原始研究 ｜ E4 经测试审计运行验证
- 状态：FACT / VERIFIED / PENDING / CONCEPT / RECOMMENDATION / LEGAL REVIEW / LEGACY / REJECT
- 每条知识保留字段：source / source_type / evidence_level / status / language / culture / time / version / claim / interpretation / application / risk

## 落库结论登记（2026-09-04）
| 名称 | 状态 |
|---|---|
| 序境 / 서경 | CANONICAL / LOCKED |
| 英文名 | TBD / OPEN RESEARCH |
| Nivellea | RESEARCH CANDIDATE / LONG-TERM REVIEW ONLY（不得进入 Canonical/仓库命名/生产） |
| Embedded Wholeness | CONCEPT / INTERNAL THEORY |
| Relational Becoming | CONCEPT / INTERNAL THEORY |
| Semantic Gravity | CONCEPT / SCREENING FRAMEWORK |
| 芥子纳须弥 | PHILOSOPHICAL PRINCIPLE / DESIGN AXIOM（建模为结构原则：局部证据→整体状态/小样本→关系结构/单条→系统性情绪/单行动→长期策略/单 Agent→共享世界模型） |
| 生产架构 | LOCKED |
| 研究成果 | 可进入 Research/Knowledge/Evaluation 层；不得未经 Gate 进入 Production Truth |

## 25 个真实实验 TEST ↔ 指令文件验收条款映射
指令文件 `AUTONOMOUS-RND-DIRECTIVE` 的 23 条 acceptance tests 覆盖用户 TEST 01-25（部分合并）：

| TEST | 指令条款 | TEST | 指令条款 |
|---|---|---|---|
| 01 单Agent | 1 | 14 新证据改变结论 | 5 |
| 02 多Agent | 2 | 15 失败自动恢复 | 15 |
| 03 观点冲突 | 3 | 16 长时间保持状态 | 16 |
| 04 发现错误 | 4 | 17/18 真改码+跑测 | 17 |
| 05 历史经验复用 | 6 | 19 新Experience | 18 |
| 06 共享验证经验 | 7 | 20/21 新Skill+Sandbox | 19 |
| 07 不同用户不同Agent | 8 | 22 Human随时介入 | 20 |
| 08 共同项目 | 9 | 23 Human否决 | 21 |
| 09 私人Memory隔离 | 10 | 24 关键操作审计 | 22 |
| 10 自主拆解 | 11 | 25 解释决策 | 23 |
| 11 找专业Agent | 12 | — | — |
| 12 多轮讨论 | 13 | — | — |
| 13 反方质询 | 14 | — | — |
