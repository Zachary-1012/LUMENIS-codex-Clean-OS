# CTR-EVENT-CLUSTER-P1-01 · 事件聚类升级 Contract

> 双子星边界：本文档为 OSAI 研究侧产出的 Contract，**仅提供 Contract，不修改 ZBC 生产代码**。
> 由 Z Brand Core / Carter 负责 Audit → Implementation → Test → E2E → Evidence → Commit。
> 来源：`learning-feed/legacy-snapshot-vs-frontier-20260902.md`（commit 99a78f2，CTH 事件聚类升级方向 BIRCH+HDBSCAN+语义嵌入）。

## Contract

```yaml
Contract:
  contract_id: "CTR-EVENT-CLUSTER-P1-01"
  version: "1.0"
  status: "released"
  requirement:
    title: "事件图谱聚类升级：BIRCH + HDBSCAN + 语义嵌入"
    description: >
      将 ZBC event_graph 的事件关系推断从当前规则/词法匹配升级为
      BIRCH 粗聚类 + HDBSCAN 细聚类 + 语义嵌入三重机制，提升事件聚合精度与召回。
    background: "learning-feed 前沿研究：单一规则匹配对长尾/同义事件聚合不足，聚类可显著提升聚合纯度。"
    success_criteria:
      - "A1 聚类纯度/准确率不低于当前基线"
      - "A2 语义嵌入接入不破坏现有事件关系推断"
      - "A3 聚类结果可追溯（每事件归属簇 + 置信度）"
      - "A4 增量运行时性能可接受，不阻塞采集/报告主链"
      - "A5 通过端到端测试"
      - "A6 不改 subject_rules / DB 结构 / 报告口径"
  osai_deliverables:
    - research_report: "learning-feed/legacy-snapshot-vs-frontier-20260902.md（BIRCH+HDBSCAN+语义嵌入方向）"
  zbc_execution:
    assigned_team: "Z Brand Core"
    implementation_steps:
      - "审计 event_graph.py 当前事件关系推断逻辑"
      - "设计并接入 BIRCH+HDBSCAN+语义嵌入聚类管线"
      - "补端到端测试并回写验收证据"
  acceptance_criteria:
    quality:
      - "A1-A6 全部通过"
    evidence_required: ["端到端测试报告", "聚类纯度/准确率基线对比"]
  security_constraints:
    no_subject_rules_change: true
    no_db_schema_change: true
    no_report_caliber_change: true
  lifecycle:
    created_by: "OSAI"
    executed_by: "ZBC"
    verified_by: "OSAI+ZBC"
```

## 待 ZBC 决策/执行项

- [ ] ZBC Audit：event_graph.py 当前关系推断逻辑
- [ ] ZBC 执行：BIRCH+HDBSCAN+语义嵌入聚类管线接入
- [ ] ZBC 提供：端到端测试 + 聚类纯度/准确率对比
- [ ] OSAI 复核：Evidence 回收后更新基线

*本 Contract 不包含任何 Cookie/Token/Session/密钥。双子星边界保持。*