# ZBC × Zachary-OS-AI 联合审计基线：小红书 Topic 数据与外部辅助源

**日期：2026-09-03**  
**状态：Audit Baseline / Non-production**

## 目标

ZBC 负责 Primary Data Truth；Zachary-OS-AI 负责研究、智能分析、Evidence/学习闭环与外部信息辅助。外部数据源不得替代 ZBC Primary Truth。

## 数据真实性原则

文档声明 ≠ 源码实现 ≠ Runtime 实现 ≠ 实际数据。每项能力必须沿需求、数据模型、Runtime、API、UI、Evidence、测试完整核验。

## XHS Topic P0

必须核验：topic_id、topic_name、topic_url、view_count、discussion_count、note_count、Topic→Note、历史快照与趋势。

历史快照必须保留 observed_at、指标值、source、collection_method、confidence，以支持趋势和异常增长判断。

## 外部辅助源策略

研究对象包括新榜/新红、千瓜、星榜以及合法可访问的开源/公开数据项目。

外部源定位为 External Evidence / Cross Validation：

External Source → Normalizer → Confidence → Cross Validation → Zachary AI → ZBC。

不得绕过登录、付费墙、验证码、访问控制或服务条款；不得把商业平台的付费能力假设成免费 API。只有免费、合法、可持续访问的数据，才可进入生产候选辅助源。

## 算力治理

外部辅助数据以补缺和交叉验证为主，不应触发全量重复 AI 分析。任务优先级综合数据价值、获取成本、系统稳定性和 AI 成本。

## 研究输出要求

对每个外部源记录：可访问性、免费范围、登录后可见范围、可验证字段、数据更新时间、稳定性、授权/使用限制、是否适合人工辅助、是否适合自动化、是否进入生产候选。

## 与 ZBC 的边界

ZBC：采集、Primary Data、业务规则、生产 API、报告生产。  
Zachary-OS-AI：研究、模型编排、Evidence、学习、评测、外部数据辅助分析。

任何外部数据进入分析前必须带 source/timestamp/metric definition/confidence 等 provenance。

**本文件为联合审计基线，不代表外部平台已接入，也不代表相关数据已获得。**
