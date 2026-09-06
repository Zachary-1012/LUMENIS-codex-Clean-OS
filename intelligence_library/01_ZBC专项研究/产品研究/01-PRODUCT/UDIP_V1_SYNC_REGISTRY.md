# 序境-Intelligence · UDIP V1.0 统一数据智能管线登记

> 状态：MIRROR-SYNC（2026-09-04）
> 本文件为 Research/Intelligence 侧登记，**Production Truth 以 ZBC（序境-Core）为准**，不复制实现、不建立第二套计算。

## 1. 双库边界（UDIP 语义）
- **序境-Core（ZBC）**：Canonical Table = 数字 Truth Surface；Function/Metric Registry；Data Quality Gate；Lineage；Visualization 只消费 Canonical。
- **序境-Intelligence（OSAI）**：研究/评估/建议；只通过 Semantic Layer 读业务数据，无 Production Write。
- 数据真相链：External Data → Ingestion → Raw/Evidence → Parse → Validate → Normalize → Canonical Data → Function → Metric → Canonical Table → View Model → Dynamic Visualization → UI/Report/Export/AI。

## 2. ZBC 侧已落地产物（引用锚点）
- `config/data-contracts/`：note / event / event_db / topic_snapshot / kos_profile / topic_campaign_note / web_topic / marketing_node（8 契约，DataQualityGate 全加载验证通过）
- `序境/01-PRODUCT/FUNCTION_REGISTRY.md`：FUNC-RISK-01~03 / KOS-01~04 / CONTENT-01~02 / OPS-01~02
- `序境/01-PRODUCT/METRIC_REGISTRY.md`：MET-RISK/KOS/CONTENT/OPS 唯一 Metric ID
- `序境/01-PRODUCT/DATA_CONTRACT_QUALITY_LINEAGE_V1.md`：五值语义（0/NULL/NOT_AVAILABLE/STALE/ERROR）、Lineage、Cross-Surface 一致性
- `序境/01-PRODUCT/RISK_METRIC_CONVERGENCE_CONTRACT.md`：MET-RISK-01（聚合）↔ MET-RISK-03（单篇）层级收敛
- `app.py /api/metrics/canonical`：统一指标出口（MET-RISK-01/02 消费 daily_report.generate_today_summary）
- 前端：Dashboard 增加 canonical 指标卡（mRiskIdx/mHealth），消费 `/api/metrics/canonical`

## 3. Intelligence 侧职责
- 研究新的数据质量/指标治理方法（含 DQ 框架、五值语义、Lineage 最佳实践）→ 作为 RECOMMENDATION 提交 Core。
- 不直接调用或重写生产计算；对指标口径有疑问 → 以 METRIC_REGISTRY.md 为准提问。
- 新品类/新平台接入前 → 先补 Data Contract（按 Core 侧 yaml 格式）再评估。
