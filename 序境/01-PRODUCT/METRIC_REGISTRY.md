# 序境-Core · Metric Registry（唯一业务指标 ID）

> 状态：P0-REGISTRY-DONE（2026-09-04）
> 依据：《Unified Data Intelligence Pipeline V1.0》
> 规则：相同 Metric ID 必须代表完全相同的业务语义；禁止不同页面对同一指标使用不同算法；同一 Metric 在相同时间/维度/过滤/权限下必须 UI=Table=Chart=Report=Export=AI。
> 复用：全部登记自真实 Canonical Function（见 FUNCTION_REGISTRY.md），不重算。

---

## 命名规范

- `MET-<域>-<序号>`；每条绑定唯一 function_id；version；owner；evidence。

## 1. 风险与健康（域 RISK）

| Metric ID | 名称 | 定义 | function_id | 单位 | time_window | owner | 状态 |
|---|---|---|---|---|---|---|---|
| MET-RISK-01 | 风险指数 | 舆情风险 5 维加权 0-100 | FUNC-RISK-01 | 分 | 日/周/月 | 舆情 | CANONICAL |
| MET-RISK-02 | 品牌健康度 | 品牌健康 0-100（越高越健康） | FUNC-RISK-02 | 分 | 日/周/月 | 品牌 | CANONICAL |
| MET-RISK-03 | 单笔记风险分 | 笔记级风险 0-100（raw 信号） | FUNC-RISK-03 | 分 | 实时 | 舆情 | CANONICAL(双真相登记) |

## 2. KOS（域 KOS）

| Metric ID | 名称 | 定义 | function_id | 单位 | time_window | owner | 状态 |
|---|---|---|---|---|---|---|---|
| MET-KOS-01 | KOS 评分 | 综合 0-100 分 | FUNC-KOS-01 | 分 | 实时 | KOS | CANONICAL |
| MET-KOS-02 | KOS 分层 | S/A/B/C | FUNC-KOS-01 | 枚举 | 实时 | KOS | CANONICAL |
| MET-KOS-03 | 主体归属置信度 | ownership 0-100 | FUNC-KOS-02 | % | 实时 | KOS | CANONICAL |
| MET-KOS-04 | 投流 ROI | (conv*50-spend)/spend | FUNC-KOS-04 | 倍率 | 按计划 | KOS | CANONICAL |
| MET-KOS-05 | 粉丝/互动/互动率 | 账号表现 | FUNC-KOS-01/03 | 数/% | 实时 | KOS | CANONICAL |

## 3. 内容（域 CONTENT）

| Metric ID | 名称 | 定义 | function_id | 单位 | time_window | owner | 状态 |
|---|---|---|---|---|---|---|---|
| MET-CONTENT-01 | 情感分布 | pos/neu/neg 计数与占比 | FUNC-CONTENT-02 | 数/% | 日/周 | 舆情 | CANDIDATE(口径待统一) |
| MET-CONTENT-02 | 笔记互动量 | likes/comments/collects/shares | FUNC-CONTENT-01 后直读 notes | 数 | 实时 | 内容 | CANONICAL |
| MET-CONTENT-03 | 数据质量分 | quality_status/score | FUNC-CONTENT-01 | 0-100/枚举 | 实时 | 系统 | CANONICAL |

## 4. 工程与运营（域 OPS）

| Metric ID | 名称 | 定义 | function_id | 单位 | time_window | owner | 状态 |
|---|---|---|---|---|---|---|---|
| MET-OPS-01 | 采集健康 | last_success_at/freshness | FUNC-OPS-02 | 时间戳 | 实时 | 系统 | CANONICAL |
| MET-OPS-02 | 研发闭环效率 | 平均研发时间/回归/复用 | FUNC-OPS-01 | 多指标 | 任务 | 研发 | CANONICAL |
| MET-OPS-03 | Runtime 健康 | CPU/RAM/队列/恢复 | FUNC-OPS-01 | 多指标 | 实时 | 系统 | CANONICAL |

---

## 双真相登记（待收敛，不删除）

- MET-RISK-01（聚合风险） vs MET-RISK-03（笔记级风险）：**不同层级口径**，各自有效，但须在 Lineage 中显式标注关系，禁止混用为同一指标。
- MET-CONTENT-01 情感（2026-09-04 已判定，CANDIDATE→RESOLVED）：
  - `ai_analyzer.analyze_sentiment`（L170）= 深度 AI 情感分析（标题+正文加权、话题印证、澄清/褒义抵消），定位=完整情感分析 → **CANONICAL（深度）**
  - `topic_campaign._classify_note`（L215）= 轻量规则分类（关键词计数，明确"不依赖AI、可解释"），定位=话题监测快速标注 → **CANONICAL（轻量规则）**
  - **判定：指令四节 C（分别对应不同业务含义）**，非重复。两者均产出 `sentiment` 字段，消费方必须按定位选择（深度分析用 ai_analyzer，话题实时标注用 _classify_note），禁止混用为同一指标口径。
- 任何页面若出现同一 MET-xxx 但算法不同 → 判定违规，走 V1.0 收敛流程。

## 追踪要求

- 每个 Metric 必须可下钻：Result → MET → FUNC → Table → Canonical Data → Raw/Evidence → Source/Run。
- metric_snapshots 表复用为指标历史 Truth（entity_type/entity_key/raw_json/snapshot_at）。
