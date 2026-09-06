# CTR-EVENT-CLUSTER-P1-01
## CTH-POMS 事件聚类升级 Contract（语义嵌入 + 增量聚类）

> **Producer**: Zachary OSAI（研究侧，形成 Contract）
> **Consumer**: Z-Brand-Core / Carter（生产侧，施工）
> **Status**: APPROVED（用户已确认执行）
> **Date**: 2026-09-02
> **Baseline**: 遵循《双子库第一梯队研发基线》研发原则（先审计→最小实现→Evidence→双库交叉验证）
> **上游研究**: `learning-feed/legacy-snapshot-vs-frontier-20260902.md`（OSAI 仓库）

---

## 0. 背景与动机

当前 CTH-POMS 事件聚合（`reprocess.py::build_cross_platform_events`）基于 **event_hint 关键词/_event_key 拼接分组**，属确定性规则聚合：
- 对同一事件的**同义异写**（"广州太古汇" vs "太古汇商场"）、**语义相近**、**跨平台不同表述**召回有限
- 事件分裂/合并依赖人为维护的关键词规则

**研究结论**：2026 年生产级舆情监控已普遍采用「语义嵌入 + 增量/密度聚类」替代纯规则分组（有完整开源参考 `chronicle` + arXiv 2601.20680 + BIRCH→HDBSCAN 150M 工业实践）。

**本 Contract 目标**：在**不触碰权威主体过滤红线**的前提下，将事件聚类升级为可召回、可验证、可增量、可审计的现代管线。

---

## 1. 范围（Scope）

### 1.1 包含（IN）
- 在 **已通过 subject_rules 验证** 的笔记/舆情上，叠加语义事件聚类
- 事件聚类结果写回现有 `events` / `event_mentions` 表（沿用既有 schema，不破坏）
- 事件摘要生成（聚类代表文档/语义摘要）
- 离线 Golden Dataset 重聚类验证 + 增量流式试点
- Evidence 记录（cluster_id → 成员 → 摘要 → 风险等级）

### 1.2 不包含（OUT）——红线，禁止触碰
- **不改动** `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` / `subject_hit()` / `_subject_sql_and_values()`
- **不改动** `aggregate_events()` / `build_daily_report()` / `publish_datetime` / `captured_at` 现有口径
- **不替换** 现有 AI Provider 选择逻辑
- **不引入** 重型 Agent 框架
- **不进入** App 开发阶段

---

## 2. 目标架构

```
验证通过的笔记流
       ↓
[1] 语义嵌入 (sentence-transformers 多语言模型)
       ↓
[2] MinHash LSH 去重 (可选，亚线性近似去重)
       ↓
[3] BIRCH 增量聚类 (CF-Tree, partial_fit 流式) ← 内存友好，增量
       ↓
[4] HDBSCAN 密度聚类 (叶节点) ← 自动簇数，离群点检测
       ↓
[5] 事件摘要 (聚类代表文档 / 语义摘要)
       ↓
[6] 写回 events / event_mentions (沿用现有表)
       ↓
[7] Evidence 记录
```

**两阶段策略**（参考 moda.dev 150M 实践）：
- **Phase A（离线重聚类验证）**：对历史验证通过的笔记做全量语义聚类，输出 Golden Dataset，与现有规则分组对比召回/精确率
- **Phase B（增量流式试点）**：BIRCH partial_fit 流式增量，定期 HDBSCAN 重聚类收敛

---

## 3. 技术选型（ADAPT，非全盘替换）

| 组件 | 选型 | 说明 |
|---|---|---|
| 嵌入模型 | sentence-transformers 多语言（如 paraphrase-multilingual-MiniLM） | 支持中英；可本地 CPU 推理；TF-IDF 兜底 |
| 增量聚类 | scikit-learn `Birch`（CF-Tree, partial_fit） | O(n)，流式，内存友好 |
| 密度聚类 | `hdbscan.HDBSCAN` | 自动簇数、离群点检测 |
| 去重（可选） | MinHash LSH（datasketch） | 亚线性近似去重 |
| 摘要 | 聚类内 TF-IDF 代表句 / 现有 AI 摘要 | 复用现有能力 |
| 存储 | 现有 events 表 + 新增聚类元数据字段 | 不破坏现有 schema |

**不引入**：重型 Agent 框架、向量数据库（当前规模 SQLite 足够）。

---

## 4. Contract 约束（Implementation Requirements）

- **R1**：Collector / reprocess 不允许在聚类之前跳过 subject_rules 验证（红线）。
- **R2**：事件聚类只作为**增强**，不作为替代——规则聚合结果保留，二者可对照（A/B）。
- **R3**：`identity_id` 必须绑定 `browser_profile_id`（沿用 P0-XHS-Runtime 约束）。
- **R4**：聚类参数（min_cluster_size / 阈值）必须可配置，禁止硬编码。
- **R5**：嵌入模型本地化或可配置云端，禁止强制 GPU。
- **R6**：所有聚类结果必须可回溯（记录 model_version / embedding_model / 参数快照 / 输入时间窗）。
- **R7**：写入 events 表必须幂等（cluster_id 唯一，重复运行不产生重复行）。
- **R8**：**禁止**将任何 Cookie/Token/Session/密钥写入事件或 Evidence。

---

## 5. 验收标准（Test Requirements / Acceptance）

| # | 验收项 | 标准 |
|---|---|---|
| T1 | 主体过滤红线不破坏 | 现有 subject_rules 相关测试全绿，A/B 对照 subject_hit 结果一致 |
| T2 | 事件召回提升 | 在 Golden Dataset 上，语义聚类事件召回 ≥ 现有规则分组（目标 +20%），精确率 ≥ 现有 |
| T3 | 跨平台同一事件合并 | 同一事件在笔记+web_mentions 不同表述能聚为一类（抽样验证 ≥ 90%） |
| T4 | 增量正确性 | BIRCH partial_fit 增量结果与全量重聚类一致率 ≥ 95%（Kappa） |
| T5 | 幂等性 | 同一输入两次运行，events 表无重复行 |
| T6 | 性能 | 单日 1 万条笔记聚类耗时 ≤ 现有全量聚合的 1.5 倍；内存 ≤ 2GB |
| T7 | Evidence | 每个 cluster 可输出 cluster_id/member_count/summary/embedding_model/参数快照/risk 等级 |
| T8 | 回归 | 现有全量测试 + E2E 全绿，报告口径不变 |
| T9 | 安全 | secret_scanning 无新命中；无密钥入 Git |

---

## 6. 施工顺序（遵循第一梯队研发原则）

1. Repository Audit（ZBC 现有 reprocess.py / database.py / events schema）
2. Architecture Audit（确认嵌入→聚类插入点）
3. Contract Audit（对照本 Contract 与现有契约）
4. Test Baseline（锁定现有全绿基线）
5. Minimal Implementation（新增 `event_cluster/` 模块，不侵入现有管线）
6. Unit Test → Integration Test → E2E
7. Golden Dataset 离线验证（Phase A）
8. 增量流式试点（Phase B，feature flag 默认关）
9. Evidence + Regression + Cross-Repo Audit
10. Release Gate

---

## 7. 双库分工

| 层 | Owner | 动作 |
|---|---|---|
| 研究/基线/Contract | Zachary OSAI | 本文件 + 前端研究 |
| 生产实现/测试/E2E/Release | Z-Brand-Core | 按本 Contract 施工 |
| Evidence 反哺 | ZBC → OSAI | 聚类质量数据回流，更新基线 |

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 语义聚类误合并（不同事件聚一起） | 保留规则分组对照；HDBSCAN 离群点不强制归类；人工 Review 入口 |
| 嵌入模型漂移 | 记录 model_version；重聚类可复现 |
| 增量漂移累积 | 定期全量重聚类收敛（可配置周期） |
| 性能回退 | feature flag 默认关；阈值可调；离线验证先行 |
| 红线被触碰 | R1/R2 硬约束 + 回归测试守护 |

---

## 9. 完成定义（DoD）

- [ ] Golden Dataset 建立（≥ 30 天历史验证通过笔记）
- [ ] 语义聚类模块落地（`event_cluster/`），默认关闭
- [ ] T1–T9 验收全绿
- [ ] Evidence 文档产出
- [ ] feature flag 默认 OFF，可平滑回退
- [ ] 双库交叉验证通过

---

*本 Contract 由 Zachary OSAI 形成，供 Z-Brand-Core 施工；不构成生产业务 Truth 修改。*
