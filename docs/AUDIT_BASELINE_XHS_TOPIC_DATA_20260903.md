# ZBC × Zachary-OS-AI 小红书数据真实性与话题监测审计基线

**日期：2026-09-03**  
**状态：Audit Baseline / Non-production**

## 1. 总原则

本基线不把“文档声明”视为“生产能力”。任何功能必须同时核验：需求 → 业务逻辑 → 数据模型 → Runtime → API Contract → UI/交互 → Evidence → 测试/验收。

验收状态：VERIFIED / PARTIAL / SOURCE-ONLY / COMPUTED / PLANNED / BLOCKED / REJECTED。

## 2. 小红书 Topic P0

客户要求的 Topic 核心指标必须继续保留并核验：

- topic_id
- topic_name
- topic_url
- view_count（浏览量）
- discussion_count（讨论量）
- note_count（话题覆盖笔记数）
- Topic → Note 关联
- 历史快照与趋势

注意：外部数据服务证明某指标存在，不等于 ZBC 当前 Runtime 已经可以稳定获得该指标。

## 3. Topic Snapshot

不得只覆盖 current value。建议保存：

- observed_at
- view_count
- discussion_count
- note_count
- source
- collection_method
- confidence

以此计算增量、增长率、增长速度、峰值和异常增长。

## 4. Topic 与 Note 分层

Topic Intelligence：指标、趋势、状态。  
Note Intelligence：内容、作者、发布时间、互动、情绪、风险。

Topic 通过 Topic Notes 与 Note 建立关联，不能把 Topic 监测等同于全量 Note 深度分析。

## 5. 采集/算力分层

L0：Topic existence / availability。  
L1：Topic Metrics（浏览量、讨论量、笔记数）。  
L2：Topic Feed 增量发现。  
L3：高价值 Note Deep Analysis。

默认不对全部 Topic Notes 做重复深度 AI 分析。

## 6. 动态熔断

现有 ZBC 已存在 Adaptive、Collector、Recovery、Stability 相关 API 入口。本基线要求继续核验其 Runtime 闭环，不重复造第二套采集控制系统。

目标状态：NORMAL → ADAPTIVE → COOLDOWN → FROZEN → RECOVERING → RECOVERED。

熔断应优先做分层降级：保留低成本 Topic Metrics，降低/暂停 Feed 与 Deep Note，而非异常时一刀切关闭全部 XHS 能力。

## 7. 时间真相

必须分离：event_at / published_at / collected_at / analyzed_at / detected_at / reported_at / notified_at。

尤其 Publish Time 与 Collect Time 不得混用。

## 8. 外部辅助数据源

外部平台只作为 External Evidence / Cross Validation，不得直接覆盖 ZBC Primary Data。

候选研究对象：

- 新榜/新红：公开话题榜、趋势及小红书相关数据服务。
- 千瓜：公开可见数据/榜单作为辅助研究对象；商业付费能力不得假设为免费 API。
- 星榜：公开能力与可访问数据作为研究对象；不得假设存在免费开放 API。
- 开源项目：研究数据结构、字段、增量、容错与可视化方法；不复制受许可证限制的代码或绕过访问限制。

只有在免费、合法、可持续访问的情况下，才进入生产候选辅助源；否则仅保留研究记录。

## 9. 外部源接入边界

External Source → External Evidence → Normalizer → Confidence → Cross Validation → Intelligence。

Primary Truth 仍由 ZBC 自己可验证的数据链负责。

外部源冲突时必须记录 source、timestamp、metric definition、collection method、confidence，不允许静默覆盖。

## 10. 报告体系

日报、独立日报弹窗、周报、月报、年报统一由 Report Engine 基于真实数据生成。模板只是 Renderer，不是 Intelligence。

链路：Raw Data → Temporal Alignment → Event Aggregation → Problem Detection → Evidence → AI Interpretation → Validation → Report Renderer。

## 11. 动态可视化

Problem Graph、Topic Trend、Temporal Overlay、Collection Stability 等均必须绑定真实 State/API，不允许静态假数据模板。

节点必须能够回溯真实 entity_id / evidence_ids / timestamp，并可点击打开具体详情。

## 12. 多端

Web / Mobile Web / App / Mini Program 保持 Capability Parity；不做功能减配，只调整信息密度、导航、交互和 Renderer。

## 13. Feature Reality Matrix

最终每项能力必须核验：需求、源码、API、数据库、Runtime、UI、交互、测试、Evidence，并给出明确状态。

## 14. 当前 P0

1. XHS Topic 浏览量
2. XHS Topic 讨论量
3. XHS Topic 笔记数
4. Topic Snapshot
5. Topic → Note
6. Publish / Collect 时间分离
7. Adaptive Collector Runtime 核验
8. 动态熔断 / 冷却 / Recovery

## 15. 算力原则

不是采集越多越好，而是以数据价值、获取成本、稳定性和 AI 成本共同决定任务优先级。规则过滤优先；高价值内容才进入 Zachary AI 深度分析；外部数据主要用于补充与交叉验证。

**本文件仅为审计基线，不代表所有能力已经实现。**
