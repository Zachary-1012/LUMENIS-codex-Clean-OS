# 序境-Core · 生产候选 IC 统一 Contract（IC-020/021/028/039/040）

> 状态：CONTRACT-DONE（2026-09-04；仅定义 Contract，不改生产代码）
> 依据：《AI 持续深度学习指令》反哺队列 → IC-020/021/028/039/040 由"待 Contract"晋级为正式契约
> 原则：能复用优先复用、不推翻现有生产、不建第三库、所有生产改动必须走 Release Gate（Contract→Test→Evidence→Audit）
> 说明：本文档为**生产侧契约基线**；研究侧详情见 OSAI 技术雷达 §24/§26/§23/§34/§35 与改进队列。每个 IC 均明确：现状事实（源码审计）→ 目标 → 数据/Metric/Function 映射 → Gate → 分阶段实施 → 验收 → 回滚。

---

## 一、IC-020 · 舆情危机告警阈值 + 情感调优

### 1.1 目标
为舆情系统提供可配置的危机告警阈值（提及暴涨/情绪骤降/负面数激增）与情感模型季度校准机制；告警走即时通知 + 升级流程（对接 HCG 门控），不伪造"已告警"状态。

### 1.2 现状事实（源码审计确认）
- **聚合风险（MET-RISK-01）**：`daily_report.py::calculate_risk_index`（L32，FUNC-RISK-01）— 5 维加权 0-100（neg_score+high_score+eng_score+event_duration_score+multi_source_score），消费 `canonical_metrics.sentiment_count/risk_count`（high 不含 critical 口径已统一）。
- **笔记级风险（MET-RISK-03）**：`ai_analyzer.py::assess_risk`（L258，FUNC-RISK-03）— high×25+med×10+主题+互动，写入 `notes.risk_score`；`risk_level` 映射 low/med/high。
- **情感分析双轨（已判定 RESOLVED）**：`ai_analyzer.analyze_sentiment`（L170）= 深度 AI 情感（CANONICAL 深度）；`topic_campaign._classify_note`（L215）= 轻量规则（CANONICAL 话题标注）。
- **风险语义分层**：已在 `RISK_METRIC_CONVERGENCE_CONTRACT.md` 固定（MET-RISK-03 单篇 → MET-RISK-01 聚合，层级关系非双真相）。
- **事件洞察**：`daily_report.py::generate_event_insight`（L229）已有 risk_level/sentiment_trend 判断。
- **模块**：MOD-INS-02 风险引擎（risk_engine.py 风险评分/日报风险口径）。

### 1.3 数据与 Metric 映射
| 项 | 定义 | 来源 |
|---|---|---|
| 告警输入 | MET-RISK-01 日值、MET-RISK-03 分布、negative 占比、风险事件数 | daily_report / canonical_metrics |
| 告警阈值 | 可配置：risk_index≥X / 负面占比≥Y% / 提及量环比≥Z% / 单日 high≥N | 新增告警配置表（设计） |
| 情感调优 | 季度校准情感关键词库/规则权重（对照人工标注集） | ai_analyzer 关键词库 + 校准样本 |

### 1.4 Gate
- 告警动作（通知/升级）必须真实可追踪：`DETECTED → NOTIFIED → ESCALATED → RESOLVED`，禁止"生成=已发送"。
- 阈值默认值先以静态配置落地并登记 Evidence；调优必须基于标注样本，禁止 AI 自评自调。
- 新阈值不得改动现有 MET-RISK-01/03 计算逻辑（防数字真相漂移）。

### 1.5 分阶段实施（本期不做）
- **P1**：告警配置表（thresholds 可配）+ 告警状态机 + 通知通道接入。
- **P2**：季度情感校准流程（标注样本集 → 校准关键词/权重 → 对比验证）。
- **P3**：反讽检测（研究侧先验证，见 Cycle K/IC-020 来源）。

### 1.6 验收与回滚
- 验收：同一时间窗告警结果与人工复核一致；阈值改配置即生效；告警状态全程可审计。
- 回滚：告警模块独立开关，异常可整体禁用回退到无告警基线。

---

## 二、IC-021 · earned media value（EMV）+ agentic 监测闭环

### 2.1 目标
报告系统引入 earned media value（EMV）指标（替代 AVE 口径），纳入 METRIC_REGISTRY 与统一报告模板；长期目标=agentic 品牌监测闭环（检测→情感→危机告警→达人触达→ROI 报告），与 KOS 闭环融合。

### 2.2 现状事实（源码审计确认）
- **报告引擎**：`report_engine.py`（MOD-CRE-01）— period_for/generate_report/generate_all/get_bundle/export_csv/xlsx/docx；已消费 `canonical_metrics.sentiment_count/risk_count`（Canonical 口径）。
- **导出**：`export_report.py`（L133 generate_report_data，L157 Canonical P0 情感/风险分桶统一走 canonical_metrics）；`report_export/report_engine.py`（payload/export 通道）。
- **Metric Registry**：已含 MET-CONTENT-02（笔记互动量）、MET-CONTENT-03（数据质量分）等 13 项；**无 EMV**。
- **报告母模型**：`REPORT_MASTER_MODEL.md`（Decision Information First：问题中心→事件→影响→风险→证据→建议）。

### 2.3 数据与 Metric 映射
| 新 Metric | 名称 | 定义 | 建议 function_id | 单位 |
|---|---|---|---|---|
| **MET-CONTENT-04** | EMV（媒体价值） | 曝光×单位曝光价值（CPM 基准）加权互动修正；必须标注 CPM 口径来源 | FUNC-CONTENT-04（新增，需 Contract） | 元/周期 |

- **口径红线**：EMV 必须基于真实曝光/互动数据 + 明确 CPM 假设来源；无数据时返回 NOT_AVAILABLE，禁止估 0。
- **消费面**：日报/周报/月报/专题报告统一模板 + 导出（UI=Chart=Report=Export=AI 一致）。

### 2.4 Gate
- EMV 作为**展示性估算指标**，必须显式标注"估算口径 + CPM 来源"，不得伪装成官方媒体投放成本。
- agentic 闭环中所有"触达/合作/投流"动作走现有 HCG 状态机（kos_execution GATED_ACTIONS），禁止 agent 自动执行。

### 2.5 分阶段实施（本期不做）
- **P1**：FUNC-CONTENT-04 定义 + MET-CONTENT-04 登记 + 报告模板接入（先双跑对照）。
- **P2**：agentic 监测闭环编排（检测→情感→危机→触达→ROI 报告）与 KOS 融合。
- **P3**：历史数据回溯重算 + 对比验证。

### 2.6 验收与回滚
- 验收：EMV 在 UI/表/图/报告/导出/AI 全表面一致；CPM 口径可追溯。
- 回滚：EMV 计算为独立函数，可整体关闭回退 AVE 旧口径展示（数据保留）。

---

## 三、IC-028 · 营销日历节点库增强（marketing_nodes + hotspot）

### 3.1 目标
增强 `scripts/marketing_calendar.py`：节点分级（核心/节气/新兴高增长）、传播周期（长线预热 vs 短期爆发）、行业适配、六大趋势（时令叙事/反套路/搭子文化）驱动创意引擎 hotspot 自动增强；对接海外/区域节点能力。

### 3.2 现状事实（源码审计确认）
- **营销日历已存在且能力较全**：`scripts/marketing_calendar.py` — `suggest_hotspot`（L445）/`nodes_for_month`（L423）/`node_on`（L428）/`yearly_summary`（L479）/`industry_nodes`（L256，_V_NODES 垂直行业）/`region_nodes`（L315，_REGION_NODES 中东/拉美/北美等区域）/`global_nodes`（L339，_GLOBAL_NODES 海外）/`cross_industry_season`（L346）/`cross_global`（L390）/`marketing_matrix`（L372）。
- **节点类型**：K_SOLAR 节气 / K_FEST 节日 / K_EMC 电商大促 / K_INTL 国际节点 / K_MARK 营销节点；字段 name/date/kind/theme/cats。
- **API 已接入**：`app.py` L701 `/api/v2/marketing/overview`（调 suggest_hotspot/nodes_for_month/cross_industry_season/cross_global/global_nodes/region_nodes/marketing_matrix）。
- **模块**：营销日历属于创作·创意引擎侧（scripts/），非 MOD Registry 独立模块（作为创意引擎数据源）。

### 3.3 数据与映射
| 增强项 | 定义 | 落点 |
|---|---|---|
| 节点分级 | 核心（七夕/618/母亲节/520）/节气/新兴高增长（万圣节/二月二/世界小狗日） | marketing_calendar 节点加 `priority` 字段（设计） |
| 传播周期 | 长线预热 vs 短期爆发 | 节点加 `lead_days`/`burst` 字段（设计） |
| 行业适配 | 垂直行业×节点交叉（母婴/美妆/酒饮/文旅等） | 已有 `_V_NODES`/`cross_industry_season` 复用 |
| 海外/区域 | 全球节点 + 区域节点（对接序境出海方向） | 已有 `_GLOBAL_NODES`/`_REGION_NODES` 复用 |

### 3.4 Gate
- 节点数据必须标注来源与年份（智谱研究/官方日历），禁止无源猜测；农历/移动节日逐年校验。
- hotspot 增强只作用于"建议"，不自动改创意生成结果（创意输出仍走人工确认）。

### 3.5 分阶段实施（本期不做）
- **P1**：节点分级与传播周期字段建模 + 数据补齐（来源标注）。
- **P2**：hotspot 增强接入创意引擎（复用现有 suggest_hotspot 返回结构，向后兼容）。
- **P3**：垂直/区域/全球节点扩充入库 + yearly_summary 展示升级。

### 3.6 验收与回滚
- 验收：新增字段向后兼容（旧调用不破）；hotspot 建议含分级/周期信息；数据源可追溯。
- 回滚：字段为增量式（默认值兜底），删除增强不影响既有 suggest_hotspot 调用。

---

## 四、IC-039 · 跨文化本地化框架（序境中英韩 + 内容出海）

### 4.1 目标
为序境中英韩三语体系与内容出海建立本地化契约：灵魂全球统一（品牌/信任基石）+ 表达本地适配（语言/情绪/审美/合规）；沉淀文化禁忌/数字符号/平台行为库；AI 只做变体生成与初译，本地母语者把关（AI 不决策本地化）。

### 4.2 现状事实（源码审计确认）
- **语言体系**：序境命名体系支持中/英/韩（同一 ID 的多语言展示，非三套系统；见 PRODUCT_NAMING）。
- **品牌命名**：Cycle Z（IC-036）已沉淀命名评估方法论（英文 Canonical Brand TBD）。
- **内容侧**：创意引擎/营销日历已有海外节点（_GLOBAL_NODES）；内容出海尚未建本地化库。
- **红线**：外部内容不可信、AI 辅助不越权、个人业务资料只存本地不上线。

### 4.3 数据与映射
| 资产 | 定义 | 落点（设计） |
|---|---|---|
| 文化禁忌库 | 广告法绝对化用语（最/第一/领先）、清真/王室/宗教符号、数字 4/8、颜色语义（红/白/紫） | 新建 `scripts/localization_guard.py`（静态规则库） |
| 平台行为库 | 各国平台内容习惯（韩国长 caption、德国重技术事实等） | 同上，作为内容适配建议 |
| 本地化流程 | 策略师定核心信息 → AI 10 变体 → 本地专家选 3 精修 → A/B → 规模化 | 创意引擎工作流（研究侧先设计） |

### 4.4 Gate
- 本地化最终决策权在人工/母语者；AI 输出一律标记"初译/变体，待母语者确认"。
- 禁忌库命中必须 HOLD 并提示人工复核，禁止自动改写后直接发布。

### 4.5 分阶段实施（本期不做）
- **P1**：localization_guard.py 静态禁忌/合规库（中英韩）建设 + 接入创意引擎输出前检查。
- **P2**：AI 变体生成流程（10→3 筛选）+ 母语者确认工作流（对接 HCG）。
- **P3**：平台行为库扩充 + 出海内容模板适配。

### 4.6 验收与回滚
- 验收：禁忌库命中率（对照已知违规案例）与误报率可测；AI 输出均带待确认标记。
- 回滚：localization_guard 为独立检查层，可开关，不影响原内容生成路径。

---

## 五、IC-040 · KOS/内容运营兴趣图谱信号

### 5.1 目标
KOS 与内容运营从"粉丝数导向"转向"兴趣图谱信号"：完播率/停留时长/DM 分享/搜索命中；小红书式内容资产化（搜索索引+长尾）与平台差异适配。只做认知与策略适配，不碰黑产刷量/绕过风控。

### 5.2 现状事实（源码审计确认）
- **KOS 评分**：`kos_engine.py::refresh_profiles`（L86）— score=eng_score(log)+vol_score+brand_rel+q_score−risk_pen；TIER_THRESHOLDS 按百分位 S/A/B/C；`list_profiles` 排序支持 kos_score/total_engagement/note_count/total_likes/avg_engagement。
- **KOS 资产字段**：kos_profiles 59 字段（含 content_tags/ownership_confidence/lifecycle_stage/is_potential/is_risk）。
- **评论智能**：`kos_engine.py::analyze_comments`（L273）+ `_comment_sentiment`/`_purchase_signal`/`_cooperation_signal`；kos_routes 有 api_content_dna/api_intent_analysis。
- **平台分发认知**：Cycle DD 已沉淀（TikTok 70% 完播触发分发、IG DM 分享/停留、小红书内容资产化长尾）。

### 5.3 数据与映射
| 新信号 | 定义 | 数据来源（设计） |
|---|---|---|
| 完播率/停留 | 内容观看深度信号 | 视频/图文平台 API（如可得）或代理指标（互动时长） |
| DM 分享/关系信号 | 私信分享/关系传播 | 平台 API（如可得） |
| 搜索命中 | 内容被搜索索引命中 | 小红书等搜索索引化内容 |
| 内容资产化 | 中腰部内容长尾价值 | 内容生命周期留存（12-18 个月窗口） |

- **口径红线**：所有平台信号必须标注来源与可得性；不可得信号不编造，用现有代理（engagement_rate 等）标注"代理指标"。

### 5.4 Gate
- 新信号不改变现有 kos_score 主计算（防数字真相漂移）；作为**附加评估维度**进入运营建议。
- 禁止通过刷量/模拟点击/绕过平台风控获取信号（采集安全红线）。

### 5.5 分阶段实施（本期不做）
- **P1**：兴趣图谱信号模型设计（字段 + 来源/代理映射）+ 报告呈现（作为附加维度）。
- **P2**：内容资产化评估（长尾留存指标）接入 KOS/内容报告。
- **P3**：平台差异适配策略库（Cycle DD 认知沉淀为可配置策略）。

### 5.6 验收与回滚
- 验收：新信号字段增量加入（旧消费不破）；来源可追溯；无黑产路径。
- 回滚：新字段/维度独立，可整体移除，不影响现有 KOS 评分与分层。

---

## 六、总 Gate 与完成定义

- 本文档仅**登记契约**，不涉及生产代码改动（CONTRACT-DONE）。
- 任一 IC 进入实施前，必须先满足：
  1. 通过本契约评审（产品 Owner 确认）；
  2. 建 Contract Test（口径/阈值/边界）；
  3. 双跑验证（新旧对照）→ 一致才 PROMOTE；
  4. 生成 Evidence + Audit 记录；
  5. 走 Release Gate 后才允许 Deploy。
- 任何"完成"必须有真实验证证据；禁止假状态、假告警、假 EMV、假本地化确认。

## 七、后续推进建议（下一轮）
- IC-020/021 优先（舆情/报告是生产核心），先做 P1 最小化落地并留 Evidence。
- IC-028 增量字段（向后兼容）可低风险快速推进。
- IC-039/040 为内容/出海侧，研究原型先行（localization_guard.py 原型、兴趣图谱模型设计）。
