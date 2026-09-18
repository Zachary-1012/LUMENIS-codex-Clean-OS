# 序境-Core · Function Registry（Canonical 业务计算统一注册）

> 状态：P0-REGISTRY-DONE（基于真实源码盘点，2026-09-04）
> 依据：《Unified Data Intelligence Pipeline V1.0》
> 规则：同一业务计算只存在一个 Canonical Function；旧代码正确则 KEEP/WRAP/ADAPT，不删旧实现；本 Registry 为注册层，不改变任何生产代码。
> 复用：已有正确实现直接登记为 Canonical，不重写。

---

## 命名规范

- `FUNC-<域>-<序号>`；version 语义化；status ∈ {CANONICAL, CANDIDATE, LEGACY, SUPERSEDED}
- 任何页面/图表/报告/导出/AI 不得重复计算已登记的 Canonical Function。

## 1. 风险与品牌（域 RISK）

### FUNC-RISK-01 · 风险指数 risk_index（0-100）
- function_id: FUNC-RISK-01 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `daily_report.py::calculate_risk_index(notes, events, period_days=1)`
- 输入: notes（含 risk_level/sentiment/likes/comments）、events（含 status/source_count/first_seen/last_seen）
- 公式（5 维加权，上限 100）：
  1. 负面占比 0-30：`min(30, neg_ratio*60)`
  2. 高风险数量 0-25：`min(25, high*5 + med*1.5)`
  3. 传播互动 0-20：`min(20, neg_engagement/50)`
  4. 事件持续 0-15：`min(15, Σ min(5, days*0.5))`
  5. 多来源 0-10：`min(10, multi_source*3)`
  - `risk_index = clamp(round(Σ,1), 0, 100)`
- time_window: 默认 1 日 ｜ unit: 分（0-100） ｜ dimensions: 品牌/日期
- error_policy: 空 notes → 0 不冒充；无数据返回 None 由调用方判空
- tests: tests/test_daily_report_redline*（已存在）
- evidence: 日报/周报消费此指标

### FUNC-RISK-02 · 品牌健康度 brand_health_score（0-100）
- function_id: FUNC-RISK-02 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `daily_report.py::calculate_brand_health_score(notes, risk_index)`
- 公式：正面占比 0-40 + 风险反向 0-30（`max(0,30-risk_index*0.3)`）+ 互动质量 + 官方声量
- 空 notes → 50.0（中性基准，非 0 伪装）
- unit: 分（0-100，越高越健康）

### FUNC-RISK-03 · 单笔记风险分 notes.risk_score（0-100）
- function_id: FUNC-RISK-03 ｜ version: 1.0.0 ｜ status: CANONICAL（raw 信号）
- 位置: `ai_analyzer.py::assess_risk`（high_hits*25 + med_hits*10，封顶/降档规则）
- 说明: 与 FUNC-RISK-01 口径不同（笔记级 vs 聚合级），**登记为双真相风险点**；保留为 notes 表 raw 信号，供负评确认流/事件关联使用；日报聚合消费 FUNC-RISK-01。下一阶段统一映射，不删。

## 2. KOS 域（域 KOS）

### FUNC-KOS-01 · KOS 综合评分 kos_score
- function_id: FUNC-KOS-01 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `kos_engine.py::refresh_profiles`（品牌相关度×内容质量×互动×持续性等，落 kos_profiles.kos_score）
- 输出: kos_score + kos_tier（S/A/B/C）+ lifecycle_stage
- 前置: 主体归属 Gate（kos_attribution），content 相关 ≠ 主体归属

### FUNC-KOS-02 · KOS 主体归属（Ownership Gate）
- function_id: FUNC-KOS-02 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `kos_engine.py::refresh_profiles` + `kos_attribution.py`
- 输出: ownership_type（TARGET_ENTITY/BRAND/MERCHANT/INDEPENDENT_KOL_KOC/UGC/MEDIA/OFFICIAL/UNKNOWN）+ ownership_confidence + ownership_evidence_ids
- 硬规则: 商户/品牌/合作过 ≠ 目标主体 KOS；AI 判断 ≠ Ownership Evidence

### FUNC-KOS-03 · KOS 漏斗/成本/分层基准
- function_id: FUNC-KOS-03 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `kos_metrics.py`（funnel_metrics / cost_metrics / tier_benchmark）

### FUNC-KOS-04 · 投流 ROI
- function_id: FUNC-KOS-04 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `kos_paid.py` ｜ 公式: `ROI = (conversions*50 - spend) / spend`
- HCG 门控: paid_media / reward_issue 须 HUMAN_APPROVED

## 3. 内容与质量（域 CONTENT）

### FUNC-CONTENT-01 · 数据质量校验
- function_id: FUNC-CONTENT-01 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `data_quality_gate.py::DataQualityGate.validate(contract_name, record)`
- 契约: config/data-contracts/{note,event,event_db,topic_snapshot}.yaml
- 输出: {"valid": bool, "errors": [], "warnings": []}
- 语义: 0 / NULL / NOT_AVAILABLE / STALE / ERROR 必须显式区分，禁止伪装 0

### FUNC-CONTENT-02 · 情感分析 sentiment
- function_id: FUNC-CONTENT-02 ｜ version: 1.0.0 ｜ status: CANDIDATE
- 位置: `ai_analyzer.py`（写 notes.sentiment）+ `topic_campaign.py`（campaign 情感）
- 说明: 存在两处口径，登记待核验统一（双真相待办）

## 4. 工程与运营（域 OPS）

### FUNC-OPS-01 · 研发效率指标
- function_id: FUNC-OPS-01 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `engineering_metrics.py`（task_closed_loop / collector_performance / scheduling_health / system_health）

### FUNC-OPS-02 · 采集健康（last_success_at / 熔断 / 冷却）
- function_id: FUNC-OPS-02 ｜ version: 1.0.0 ｜ status: CANONICAL
- 位置: `collector_automation.py` + `collector_guard/` + `adaptive_engine.py`
- 约束: 自动每日 ≤2 次、手动每次 ≤30min、异常 STOP→COOLDOWN→HUMAN REVIEW、熔断上限

---

## 待注册（下一阶段）

- 话题热度/浏览-讨论-笔记-快照（topic_campaign_snapshots 的派生率）
- 事件传播链（event_graph）
- Campaign 效果（topic_campaign_notes 聚合）
- 报告聚合（daily/weekly/monthly/annual 全消费上述 FUNC）

> 本 Registry 与 `序境/01-PRODUCT/MODULE_PAGE_WORKFLOW_DATA_REGISTRY.md`（MOD-xxx）互补：MOD=模块/能力，FUNC=业务计算。同一计算只登记一次。
