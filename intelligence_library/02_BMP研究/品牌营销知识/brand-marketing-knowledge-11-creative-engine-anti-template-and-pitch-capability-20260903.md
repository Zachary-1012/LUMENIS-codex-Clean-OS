# 品牌营销知识库 · 第十一期｜创意引擎 V2 反模板化 + 提案能力深度学习（4A deck / AI Slogan 前沿 / 戛纳2025）

- 日期：2026-09-03
- 触发：用户明确「引擎 slogan 禁止模板化，要自适应有新 idea；提案 PPT 能力按预算调需求，去深度学习」
- 性质：把一次"能力缺陷 → 工程重构 → 前沿研究 → 反哺落地"做成完整闭环

---

## 一、创意引擎 V2：反模板化重构（本段主体，已落地 ZBC）

### 1.1 V1 缺陷根因（诊断）
- `_slogan()` 是「机制→固定句式」填空：eventify 永远"「X节」把X变成一场X"、cocreate 永远"「X由你造」"。
- 本质：创意被"机制×主题词"两个维度锁死，主题一换、表达没换，就是模板循环。

### 1.2 V2 核心升级（反模板化 = 多维组合，而非加更多模板）
| 维度 | 作用 |
| --- | --- |
| 机制 mechanism | 事件化/参与/符号化/反差/共创/文化共识（不变） |
| **张力句式库 _HOOK** | 每个机制可命中多种句式类型：主张式/行动式/故事式/反转式/共创式/暗语式，每条是"有张力的表达"而非填空壳 |
| **角度 angle** | 消费者/品牌自省/圈层暗语/场景时间/反叛/共创——同一主题不同切入人设 |
| **语义角色 topic_role** | 中文主题词→空间/美食/服务/节点/IP/颜值/通用，选对应意象槽位（面包→"值得专程的味道"，积分→"体面省心的体验"） |
| **预算感知 budget** | low轻量(内容话题+UGC)/mid单点战役(事件+达人)/high全链路(事件+物料+媒体+私域)，同主题不同预算出不同档位 |
| **随机+seed** | 默认随机保证"新 idea"；seed 固定可复现（测试/评审用） |

### 1.3 反模板化工程要点（可复用）
- 维度组合 ≥ 3（机制×句式×角度×语义角色）才可能不重复；单靠加字符串数量仍会穷尽。
- **批次内去重**：slogan 集合去重 + 句式 key 去重（used_keys/used_slogans），用完重置桶。
- **重大坑：对共享 list 就地 shuffle 破坏 seed 可复现性**——`MECH_TO_HOOK.get(mech)` 返回的是 dict 里同一个 list 对象，`rng.shuffle` 就地修改、跨调用残留。必须 `list(...)` 副本再 shuffle。这是本次真实踩坑并修复的确定性 bug。
- 槽位渲染用全量 replace + 品牌兜底，杜绝 `{xxx}` 未填导致空口号。
- 契约保持：仍输出 meta/ideas，provenance（芥子→须弥、evidence_level/confidence 封顶/负样本待检）不变，只新增 angle/budget/tension_type。

### 1.4 名句重构 remix（研究落地，arXiv 2602.06049 范式）
- 前沿结论：slogan 应平衡"新颖×熟悉"，用**名人名言/文化共识重构**最有效（名言天然 slogan 长度、富修辞、有深度）。
- 已落地 culture 机制：`「吾日三省吾身：topic、topic、还是topic」`、`「山不在高，有仙则名」——brand 的 topic，不在多，在 img`；高奢版 `「大隐隐于市」`、`「无丝竹之乱耳，无案牍之劳形」`。
- 验证：太古汇真实信号跑出 6 条全不同、句式 3 类、角度全异（反叛/自省/暗语/共创/场景/消费者），质量脱离 V1 模板。

---

## 二、提案 deck 方法论深度学习（国际 4A 标准）

### 2.1 提案结构（可做成提案模板，随预算/场景自适应）
**4A 通用标准流程**：项目背景 → 需求拆解 → 市场分析 → 核心策略 → 创意方案详解 → 落地执行规划 → 预算明细 → 效果预估 → 风险预案。
**叙事弧（国际，Campbell 英雄之旅式）**：Setup 建立品牌世界 → Confrontation 揭示市场张力/痛点 → Resolution 创意解决 → Brighter Future 愿景收口，驱动行动（fMRI 研究：故事驱动多激活 22% 脑区）。
**不同 deck 类型不同结构**：
- New business pitch：Problem → Insight → Approach → Proof → Next step
- Strategy recommendation：Context → Tension → Options → Recommendation → Rationale
- 视频商业 pitch 五问：问题/机会？Big idea？为何打动受众？look & feel？为何由你们执行？

### 2.2 单页原则（One Slide One Job）
- 每页只回答一个问题，五类职责选一：Set context / Frame problem / Make recommendation / Prove point / Drive decision；一页想干三件事就拆页。
- **先写 slide 的 takeaway 观点句，再设计**——设计服务于观点，不是装饰（"Paid social drove reach, but search captured the highest-intent demand"）。
- 提案讲故事而非堆 slide；每页必须有存在理由。
- 结束别问"Any questions?"，给明确的 next action（book a call / 确认下次会议）。

### 2.3 预算感知（与引擎 V2 budget 打通）
- 行业共识：创意筛选结合"预算、落地难度、传播效果、品牌适配性"，主方案 1 套 + 备选 1–2 套。
- **低预算 ≠ 没创意**（戛纳低成本案例：Nutter Butter 55 年品牌靠 TikTok 荒诞宇宙重生；KitKat Phone Break 只做一个视觉替换创意投放场景）。预算维度决定"玩法与物料档位"，不决定创意品质。

---

## 三、AI Slogan 生成前沿（2025–2026）

1. **arXiv 2602.06049**：名言重构范式，novelty×familiarity 平衡，模块化 = 名言匹配→结构分解→词汇替换→remix。已落地（见 1.4）。
2. **slogan 记忆研究共识**：4–8 词最易记（各平台 8 词后截断）；五种高记忆风格 = Punchy declarative / Contrarian / Story fragment / Question / Command——与本引擎 tension_type（主张/反转/故事/设问/行动）一一对应，验证设计方向正确。
3. **prompt 质量决定成败**：详细 brief 把陈词滥调从 78% 降到 31%；同一 brief 跑两个模型取"发散处"找惊喜。
4. **文化适配**：中文 slogan 要"重构"而非直译（Think Different → "敢不同"）——本引擎坚持中国化原创，不做英文直译。

---

## 四、戛纳 2025 创意趋势（观察 + 反哺引擎）

1. **技术是手段不是信息**：AI 是叙事/功能的隐形集成，不当主角。→ 引擎 AI 只做信号/结构供给，文案由原创表达。
2. **目的被编码而非声明**：把价值观做进形式（AXA 把"家庭暴力"写进保险条款）。→ 高奢/品牌底色用"做出来"而非"喊出来"。
3. **分布式相关**：价值分布在界面/包装/街道/算法，spot 不是中心。→ 创意触点设计要跨场域（内容/线下/私域/算法承接）。
4. **粉丝圈层作为创意力量**：用户不是放大器，是意义起源（Tracking Bad Bunny 地理坐标解锁歌单；Mastercard 粉丝进叙事主体）。→ 对应 participate/cocreate 机制，设计"让用户成为创作者"的机制而非单向传播。
5. **幽默是批判立场**（解构/反讽，Cadbury "Erase Valentine's Day" 反文化空间）。→ 反差/反转机制的高阶用法。
6. **先解决问题再卖货**（Ziploc 过期券、Mibanco 搬运工广告位）。→ 服务体验官/明明白白消费指南类内容本质是"解决信任问题"。

---

## 五、下一轮候选（已登记，不在本次扩张）
- 引擎 V2 增加"设问式/清单式"张力类型（对齐记忆研究五种风格中的 Question）。
- 提案 deck 自动生成器：L3→L0 方案 → 按"背景/洞察/策略/创意/执行/预算/效果/风险"自动产出比稿 PPT 骨架（已具备结构方法论，等接 PPT 渲染通道）。
- 名句 remix 语料库扩充（跨品类：快消/3C/文旅/高奢），并做"重构原创性"校验（避免与原名言过度重叠）。
