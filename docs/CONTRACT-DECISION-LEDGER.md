# CONTRACT-DECISION-LEDGER（P1-1 契约逐项决策台账）

> 2026-09-02。依据 OSAI `reconciliation/06_CONTRACT_RECONCILIATION.md`（25 契约 + Violation V-01~07 + Implicit I-01~10），
> 在 ZBC 侧逐项给出处置决策。合法流向不变：OSAI → Contract/Plan → ZBC；ZBC → Result/Evidence → OSAI。
> 本轮已先闭环 P1-2（OpenAPI）、P1-3（safe_collection 旁路）、P1-5（Schema Registry），本台账与之对齐。

## 决策枚举
- **CLOSED**：ZBC 侧已具备且有证据/测试。
- **ADOPT-BYPASS**：已在 ZBC 旁路实现，待真实链路验证后接管（不直接进生产主链）。
- **REVISE-SCOPE**：契约缺适用边界，ZBC 用分级/等价物化解，回写 OSAI 修订建议（ZBC 不照搬）。
- **NOT-APPLICABLE**：该契约属 OSAI/研究侧职责，ZBC 生产侧正确地不实现。
- **ZBC-OWNS**：ZBC 自有子系统契约，ZBC 是 SoT，OSAI 无需反向定义；按需补本地声明。
- **BACKLOG**：确有价值但不在本轮，登记后续（不阻塞上线）。

## 1. 代码级 / 采集契约
| OSAI 契约/条款 | 06 状态 | ZBC 决策 | 依据 / 落地 |
|---|---|---|---|
| safe_collection · PII 字段级/文本脱敏 (V-03/04) | MISSING | **ADOPT-BYPASS** | `platform_adapters/safe_collection.py` redact_record/redact_text，10 测；待作为采集「后处理」接入，不改现役 insert_note |
| safe_collection · 采集审计 audit schema (V-05) | MISSING | **ADOPT-BYPASS** | 同上 build/validate_collection_audit（独立 `zbc.collection-audit.v1`，不强行套 hub schema 名）；与现役 collection_logs 互补，接管时做字段映射 |
| safe_collection · 离线 Shadow Pipeline | MISSING | **ADOPT-BYPASS** | run_offline_pipeline 已实现并测（限速→脱敏→审计，遇风控即停不伪装 0） |
| safe_collection · 速率下限 2s/日上限 200 | PARTIAL | **ADOPT-BYPASS** | 契约常量 MIN_INTERVAL_FLOOR=2/DEFAULT_DAILY_CAP=200 已建；运行时另有 collector_guard.AdaptiveRateLimiter，接管时对齐 |
| safe_collection · 风险信号即停 | PARTIAL | **CLOSED** | 现役 collector_guard 七态 + ResponseAnalyzer 已即停（300012/验证码/登录过期）；契约信号表已与之对齐 |
| safe_collection · 只读 | PARTIAL | **REVISE-SCOPE** | 采集只读；cookie 桥同步属「认证态维护」非内容写入，collector_automation 不做发布/互动。在契约注明 read_only 指平台内容侧 |
| 单账号/禁账号池 (V-01)、禁代理池 (V-02) | VIOLATION | **REVISE-SCOPE** | 06 §3 备注已自陈：契约定位是「低风险人工 QR 单账号」场景。ZBC 用 `deployment_target` 分级化解：**internal/侧端允许受控双池，public_web 由 policy 硬拦截**（已实现并测）。这不是违规，是契约缺场景边界；回写 OSAI 建议补 scope 字段 |

## 2. 研究/协作类（OSAI 内部职责）
| 契约 | 决策 | 说明 |
|---|---|---|
| research_record.py（R-YYYY、三向验证字段） | **NOT-APPLICABLE** | 生产侧不产生 Research Record，由 OSAI 产出，分工正确 |
| AI-COLLABORATION-PROTOCOL（Research ID/互相 Review） | **NOT-APPLICABLE** | OSAI 研究流程，ZBC 不实现 |
| CAPABILITY-REGISTRY（3 个 reusable 能力） | **NOT-APPLICABLE** | OSAI 内部能力，ZBC 经 Contract 消费而非内嵌，used_by 为空正常 |
| Research-Learning-Schema / 持续研发政策 / 工作日志推送 / ChatGPT 介入 / 任务队列 | **NOT-APPLICABLE** | 研究治理协议，ZBC 仅遵循跨库基线，不落地为运行时代码 |

## 3. Shadow / 跨库基线 / 领域适配器
| 契约/条款 | 06 状态 | 决策 | 依据 |
|---|---|---|---|
| SHADOW · 9 阶段 / 不自动改生产 | PARTIAL | **ZBC-OWNS** | v4_ai_shadow + ai_learning_engine 以 SQLite 承载，严格 shadow 不接管生产（GAP-05 门控仍默认 shadow） |
| SHADOW · data/shadow JSONL 介质 | PARTIAL | **REVISE-SCOPE** | 介质差异（SQLite vs JSONL）等价，不要求改文件形态；以「不自动改生产 + 可追溯」为实质判准 |
| SHADOW · production_unchanged 字段 (V-06) | MISSING | **BACKLOG** | 可在 v4_ai_shadow 增列（向后兼容迁移）或在导出 Evidence 时补该标记，不本轮改表 |
| GLOBAL 基线 · Before Gate | PARTIAL | **CLOSED** | runtime_preflight.py 启动前检查（import/红线模块/依赖） |
| GLOBAL 基线 · After Gate / 三向验证 (V-07) | MISSING | **ZBC-OWNS+BACKLOG** | 流程层：本仓 Release 前跑 tests 全量 + 红线回归即 ZBC 向 After Gate 的实现；DCC/SICI 维度由跨仓流程承担 |
| GLOBAL · Capability Delta | MISSING | **BACKLOG** | before/after 能力计数（可由 Feature 矩阵 diff 生成） |
| DOMAIN-ADAPTER（13 字段/8 隔离/不自动晋级/fail-closed） | PARTIAL | **REVISE-SCOPE** | v4_upgrade/adapters 是「采集平台适配器」，与 Zachary「领域适配器」非同一概念，不强行套 13 字段；fail-closed 已由 base.safe_collect + risk_controller 覆盖 |
| 双向学习契约 · 隔离/不越界 | EXISTS | **CLOSED** | 无跨仓 import、OSAI 无 ZBC 生产写权限（已复核） |
| 双向学习 · approved 导出通道 | PARTIAL | **BACKLOG（=P1-8）** | ZBC→OSAI 证据/approved 数据自动流转，单独任务 |

## 4. Implicit Contracts（ZBC 自有、OSAI 未声明，I-01~10）
| # | 子系统 | 决策 | 依据 |
|---|---|---|---|
| I-01 | API 路由契约 | **CLOSED** | 本轮 P1-2：openapi_spec 自动生成 OpenAPI3.0.3（364 规则/350 path，认证标注） |
| I-02 | 主体口径（SUBJECT_WORDS/subject_hit/_subject_sql_and_values） | **ZBC-OWNS** | subject_rules.py 为最高保护 SoT，OSAI 不反向定义；函数级测试持续锁定 |
| I-03 | DB Schema（52 表） | **CLOSED** | 本轮 P1-5：schema_registry 只读反射清单，0 无主表 |
| I-04 | v4 认证/权限（8 张 v4_* 表） | **ZBC-OWNS** | v4_upgrade/auth 是 SoT；API Key + 用户体系按方案②推进中 |
| I-05 | 话题活动监测（4 表） | **ZBC-OWNS** | topic_campaign.py，GAP-05 门控在线 |
| I-06 | 事件图谱（2 表，16 事件/关系） | **ZBC-OWNS** | event_graph.py，GAP-07 已补三类四关系 |
| I-07 | Swire 多项目（3 表） | **ZBC-OWNS** | swire_group.py（swire_notes 空表见 GAP-22） |
| I-08 | 审核工作流（3 表） | **ZBC-OWNS** | review_workflow.py |
| I-09 | 自适应调度（schedule_decisions） | **ZBC-OWNS** | adaptive_engine + platform_adapters/scheduling gate |
| I-10 | 品牌知识库（brand_knowledge 103 行） | **ZBC-OWNS** | brand_knowledge_base.py |

## 5. 版本一致性（06 §5）
| 项 | 06 记录 | 现状（2026-09-02 实测） | 决策 |
|---|---|---|---|
| VERSION / package.json / app.APP_VERSION | 5.9.9 vs 5.6.2 不一致 | 三者均 **5.9.9**（另一窗口已统一，06 滞后） | **CLOSED** |
| models.py 注释/打印 v5.8.0/v5.8.9 | 不一致 | 本轮统一为 v5.9.9（纯注释/打印） | **CLOSED** |
| database_migrations CURRENT_VERSION=8 vs schema_version 记录 | PARTIAL | 迁移版本号与历史记录表本就允许「当前版本 vs 已执行记录」并存，非冲突 | **CLOSED**，加 versions 一致性测试锁定 |
| test_version_consistency.py 锁定 VERSION=package.json=APP_VERSION，且 models.py 无残留旧版本号 | — | 本轮新增 | **CLOSED** |

## 6. 需要回写 OSAI 的契约修订建议（ZBC 不替 OSAI 改，只提建议）
1. safe_collection 增加 `scope`/`deployment_target` 语义：区分「低风险人工 QR 只读（单账号/无池）」与「internal 受控生产采集（允许受控双池，public_web 仍硬禁）」，消除 V-01/02 的伪冲突。
2. Shadow 介质接受 SQLite 等价物，以 production_unchanged 语义而非 JSONL 形态为判准。
3. collection-audit schema 允许产品侧命名空间（zbc.*），字段语义对齐即可，不强制同名。

## 7. 本轮结论
- 25 契约 + 7 Violation + 10 Implicit 全部给出决策，无「UNKNOWN 悬挂」。
- 真正需写代码的缺口已由 P1-2/P1-3/P1-5 与本轮版本对齐覆盖；剩余均为 NOT-APPLICABLE / ZBC-OWNS / BACKLOG（P1-8 证据流转、production_unchanged 字段、Capability Delta），不阻塞 CTH 上线。
- 未改任何生产主链、DB schema、采集行为与主体口径；生产 8201 未碰。
