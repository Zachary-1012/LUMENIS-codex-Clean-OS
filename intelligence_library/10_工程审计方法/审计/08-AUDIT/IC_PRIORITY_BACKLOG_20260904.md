# 序境-Core · IC 改进队列分级盘点与实施优先级（2026-09-04）

> 状态：INVENTORY-DONE（2026-09-04）
> 依据：OSAI `03-RESEARCH/P0-AGENT-ORG/04-IMPROVEMENT-QUEUE.md`（IC-001~049）+ ZBC `PRODUCTION_CANDIDATE_CONTRACTS_20260904.md`
> 目的：对改进队列做分级盘点，排定实施优先级；区分"已 Contract-DONE / 已实施 / 待 Contract / 研究侧"。

---

## 一、IC 状态总览（按实施状态分级）

### 1.1 已 Contract-DONE + 已实施（本轮完成 3 项）
| IC | 主题 | Contract | 实施状态 | 落点 |
|---|---|---|---|---|
| **IC-020** | 舆情危机告警阈值+情感调优 | ✅ PCCC §一 | ✅ **IMPLEMENTED（P1 告警配置表+状态机）** | `alert_engine.py` + `/api/ic/alert/*` + 8 测试 |
| **IC-028** | 营销日历节点分级+传播周期 | ✅ PCCC §三 | ✅ **IMPLEMENTED（P1 字段建模）** | `marketing_calendar.py` priority/lead_days/burst + 5 测试 |
| **IC-047** | 免税 KOS 场景标注 | 待 Contract（本轮补实施） | ✅ **IMPLEMENTED（场景标注）** | `kos_scenarios.py` + `/api/ic/kos-scenario` + 4 测试 |
| IC-021 | EMV + agentic 监测闭环 | ✅ PCCC §二 | ⬜ 未实施（P1=FUNC-CONTENT-04 待 Contract） | 报告系统 |
| IC-039 | 跨文化本地化框架 | ✅ PCCC §四 | ⬜ 未实施（P1=localization_guard.py） | scripts/ |
| IC-040 | KOS 兴趣图谱信号 | ✅ PCCC §五 | ⬜ 未实施（策略适配） | kos_engine |

### 1.2 待 Contract（未定契约，需先对齐再实施）
| IC | 主题 | 优先级 | 反哺对象 |
|---|---|---|---|
| IC-029 | NPS/DRI 评价维度 | 中 | KOS/报告 |
| IC-030 | 播客八步 SOP 资产化 | 中 | Podcast |
| IC-031 | AI Semantic Layer 运行时拦截 | 中 | AI/Canonical |
| IC-032 | 模型压缩候选评估 | 中 | ai_channel |
| IC-033 | 情绪唤醒度维度 | 中 | KOS/舆情 |
| IC-034 | 视觉分级模型选型 | 低 | ai_channel |
| IC-035 | OWASP Agentic Top10 安全清单 | 高 | AI 治理/审计 |
| IC-036 | 品牌命名评估管线 | 中 | 英文 Brand 研究 |
| IC-037 | 记忆架构参考 | 低 | 自进化 Agent |
| IC-038 | 奖励设计参考 | 低 | OSAI 评估 |
| IC-041 | 达人分层运营策略 | 中 | KOS 分层 |
| IC-042 | 定制说服故事线 | 中 | 创意引擎 |
| IC-043 | 长任务可靠性方法论 | 中 | 自研 AI |
| IC-044 | 耸动/合成内容风险信号 | 中 | 舆情告警 |
| IC-045 | 品牌叙事世界建设 | 中 | 品牌/播客 |
| IC-046 | 复杂系统/涌现体系观 | 低 | 产品哲学 |
| IC-048 | 可视化质量门清单 | 中 | 可视化/UI |
| IC-049 | Agentic 知识图谱检索 | 低 | 自研 AI |

### 1.3 研究侧（不碰生产，先原型/文档化）
| IC | 主题 | 阶段 |
|---|---|---|
| IC-001 | 写路径优先校验 | 研究侧原型 |
| IC-002 | Supervisor 拓扑确认 | ✅ 已文档化 |
| IC-003 | ZELL 错误归因分层 | ✅ 已落地模板 |
| IC-004 | Skill 生命周期元模型 | 研究侧 |
| IC-005 | AI 日报 Critic 双审 | 研究侧原型（5 约束） |
| IC-006 | 记忆分层（CoALA） | ✅ 已落地 COALA-INDEX |
| IC-007 | Handoff 精简 recap | DEFER |
| IC-008 | 防 Sycophancy 设计原则 | ✅ 已落库 |
| IC-009 | Skill 版本化/回滚 | ✅ 已同步 ZBC |
| IC-010 | 编排升级判据 | ✅ 已同步 ZBC |
| IC-011 | 多用户记忆隔离原则 | 设计层落库 |
| IC-012 | Agent Identity 复合身份 | 设计层落库 |
| IC-013 | 代码库持久索引 | 研究侧原型 |
| IC-014 | 知识资产渐进式披露 | 研究侧 |
| IC-015 | MCP/Tool Schema 体积治理 | 研究侧 |
| IC-016 | 多模型路由增强 | 研究侧 |
| IC-017 | 回归测试自动生成 | 研究侧评估 |
| IC-018 | 知识资产整理机制 | 研究侧 |
| IC-019 | AI 输出过滤 | 研究侧设计 |
| IC-022 | 内容跨媒介转译 | 研究侧 |
| IC-023 | 多 Agent 有状态图 | 研究侧 |
| IC-024 | 推理预算最优分配 | 研究侧 |
| IC-025 | 播客视频化+分发 | 研究侧 |
| IC-026 | 情感浓度文案手法库 | 研究侧 |
| IC-027 | 文学叙事技巧库 | 研究侧 |

---

## 二、实施优先级排定（P0/P1/P2）

### P0（本轮已实施，海南中免第一验收主体直接相关）
1. **IC-020** 告警阈值+状态机 ✅ 已实施
2. **IC-028** 营销节点分级 ✅ 已实施
3. **IC-047** 免税 KOS 场景 ✅ 已实施

### P1（高价值 + 已 Contract-DONE，下轮优先）
4. **IC-035** OWASP Agentic 安全清单（高优先级，AI 治理红线）→ 先对照盘点再定改动
5. **IC-021** EMV 指标（FUNC-CONTENT-04 定 Contract → 登记 MET-CONTENT-04 → 报告接入）
6. **IC-039** localization_guard.py（中英韩禁忌库，内容出海安全）
7. **IC-040** KOS 兴趣图谱信号（策略适配，配合 IC-021 闭环）

### P2（中优先级，待 Contract 后再评估）
8. IC-030 播客八步 SOP / IC-031 AI Semantic Layer / IC-033 情绪唤醒度 / IC-041 达人分层
9. IC-042 说服故事线 / IC-043 长任务可靠性 / IC-044 耸动信号（与 IC-020 联动）/ IC-045 品牌叙事
10. IC-029 NPS / IC-032 模型压缩 / IC-036 命名管线 / IC-048 可视化质量门

### P3（低优先级 / 研究侧沉淀）
11. IC-034 / IC-037 / IC-038 / IC-046 / IC-049（研究侧）
12. 研究侧 IC-001~028（除已 Contract 项）按原型优先级推进

---

## 三、决策原则（守住红线）
- **先 Contract 再实施**：IC-020/028 走 PCCC 契约；IC-047 本轮补实施（场景标注，只读不写主表）
- **能复用优先**：IC-047 复用 kos_engine.brand_profiles；IC-028 复用既有 _NODES/_GLOBAL_NODES/_REGION_NODES
- **不造假**：海南中免 175 条真实采集数据才出 KOS 推荐；空数据返回"需真实采集"不填假
- **不越权**：告警生成≠已发送（状态机 DETECTED→NOTIFIED→ESCALATED→RESOLVED）
- **不重复计算**：IC-020 只消费 canonical_metrics，不重算 MET-RISK-01/03

---

## 四、下轮建议（对接海南中免第一验收场景）
1. 服务重启 → `/api/ic/*` 生产冒烟 → PRODUCTION-VERIFIED
2. 全量回归通过（reg66 待确认）
3. IC-035 安全清单对照盘点（高优先级）
4. IC-021 EMV 契约定稿 → 报告接入
5. IC-047 场景建议 → 对接 KOS 运营/留资/邀约闭环
