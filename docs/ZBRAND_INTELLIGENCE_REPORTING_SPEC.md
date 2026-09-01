# Z-Brand Intelligence Reporting Specification

> 生效：2026-09-01
> 性质：增量报告规范；不改变 CTH-POMS 现有业务逻辑，不替换现有报告实现。
> 目标：为 CTH-POMS、ZBMP 及后续研究输出建立统一、可复用、可审计的 Intelligence 报告内容模型。

## 1. 设计原则

1. **CTH-first**：本规范不得阻塞 CTH-POMS 当前生产上线。
2. **增量融合**：优先复用现有数据、查询、事件、风险和报告链路；禁止为了模板重构生产主链。
3. **结论先行**：先回答发生了什么、为什么重要、是否需要行动，再展开证据和细节。
4. **Evidence-first**：事实、发现、分析判断、商业影响和建议动作分层表达，不把 AI 推测伪装成事实。
5. **可追溯**：关键判断尽量关联来源、时间、数据范围、规则/模型和置信度。
6. **多层深度**：同一底层 Intelligence Model 支持即时卡片、简约、标准、精细、深度研究、白皮书，不建立六套互相独立的报告系统。
7. **AI 非事实生命线**：没有 AI 时报告仍必须能够基于规则和数据库事实生成；AI 只能增强分析。

## 2. 统一内容模型

所有报告、弹窗、详情页和分析页逐步统一为：

`Evidence → Finding → Assessment → Implication → Action`

- **Evidence / 证据**：可核验的原始数据、内容、时间、来源、指标。
- **Finding / 发现**：从证据直接归纳出的客观模式。
- **Assessment / 分析判断**：基于证据与方法形成的判断；必须与事实区分。
- **Implication / 商业影响**：对品牌、消费者、传播、运营或招商可能意味着什么。
- **Action / 建议动作**：建议观察、核实、响应或进一步研究什么。

### Confidence / 置信度
关键 Assessment 可标记：High / Medium / Low，并说明依据。置信度不是事实正确性的替代品。

## 3. 六级输出体系

### L0 即时
用途：风险弹窗、首页卡片、消息中心、实时事件。
结构：`事件/异常 + 规模 + 风险/趋势 + 一句话判断 + 查看入口`。
阅读目标：数秒内判断是否需要点击。

### L1 简约
用途：AE 快速浏览、日报摘要。
结构：`Executive Summary → Key Metrics → Key Findings → Attention/Action`。

### L2 标准
用途：日报、周报、月报、常规客户汇报。
结构：`Executive Summary → Key Metrics → Key Findings → Trends → Events → Risk → Recommendations → Sources/Notes`。

### L3 精细化
用途：专报、品牌分析、Campaign 分析、品牌对标、招商专题。
增加：`时间线、传播主体、内容主题、情绪、用户类型、扩散路径、历史对比、相似案例、证据详情`。

### L4 深度研究
用途：消费者洞察、市场情报、品牌研究、重要招商研究。
结构：`Research Question → Scope → Data Sources → Methodology → Findings → Evidence → Alternative Explanations → Assessment → Business Implications → Recommendations → Limitations → Appendix`。

### L5 白皮书
用途：年度研究、行业研究、品牌/消费者白皮书。
结构：`Executive Summary → Research Questions → Methodology → Market Context → Consumer Signals → Brand Landscape → Trend Analysis → Case Studies → Strategic Implications → Outlook → Appendix`。

## 4. 报告类型映射

- **日报**：L1/L2；重点是当天发生什么、异常是什么、是否需要关注。
- **专报**：L3；由风险/事件触发，不是日报加长版。
- **周报**：L2/L3；强调趋势、变化原因和下一周期关注点。
- **月报**：L2/L3；强调消费者、品牌、传播和事件的月度结构。
- **年报**：L3/L5；强调年度趋势、案例、风险与机会。
- **案例库**：结构化保存 Evidence/Finding/Assessment/Action 与结果。
- **案例对标**：当前事件 → 相似案例 → 过去处理 → 结果 → 当前启示。
- **深度研究**：L4。
- **白皮书**：L5。

## 5. 页面与报告共享组件

优先建设可复用内容组件，而不是分别设计页面和 PDF：

- Executive Summary / 结论摘要
- KPI / 核心指标
- Finding Card / 关键发现
- Evidence Card / 证据卡
- Assessment Card / 判断卡
- Risk Card / 风险卡
- Event Timeline / 事件时间线
- Trend / 趋势
- Entity/Brand Profile / 主体或品牌画像
- Benchmark / 对标
- Case Reference / 案例引用
- Recommendation / 建议动作
- Confidence / 置信度
- Source & Method / 来源与方法
- Limitations / 局限性

同一组件应能够在弹窗、详情页、Dashboard、HTML 报告和 PDF 输出之间复用。

## 6. CTH-POMS 适配边界

当前只允许在现有报告链路上增量适配。不得：

- 改写 `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS`；
- 弱化 `subject_hit()` 或主体 SQL 过滤；
- 改变 `publish_datetime` / `captured_at` 语义；
- 让 AI 决定事实、主体、时间或最终风险；
- 让报告模板反向改变生产数据；
- 为模板引入新的生产运行时依赖。

报告只能消费经过现有业务边界确认的数据与事件。

## 7. ZBMP 适配方向

ZBMP 后续逐步承载 L3-L5 能力：

- Brand / Competitor / Campaign intelligence
- Brand Profile
- Consumer Insight
- Benchmark
- Event Relation / Lifecycle
- 多平台分析
- 深度研究与白皮书

这些能力继续留在 Z-Brand-Core 内，通过 Feature Gate / License 控制；不得拆成第二套 Core。

## 8. 质量门禁

任何新报告/页面实现进入主线前，至少检查：

1. 数据来源是否真实可追溯；
2. 主体过滤是否保持原有边界；
3. 时间语义是否正确；
4. 事实与 AI 判断是否分层；
5. 风险是否有证据；
6. 置信度是否合理；
7. 空数据/采集失败是否不会被渲染成“无舆情”；
8. 移动端与桌面端可读性；
9. PDF/HTML 输出一致性；
10. 不影响 CTH-POMS 当前生产链路；
11. 相关测试、E2E、安全检查通过后再进入主分支。

## 9. 当前实施顺序

`CTH-POMS Release Gate → L0/L1/L2 最小适配 → L3 专报/案例 → ZBMP L3/L4 → L5 研究/白皮书`。

本规范本身只定义统一模型和边界，不要求立即实现所有页面或报告。
