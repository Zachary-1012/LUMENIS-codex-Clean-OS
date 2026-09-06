# 12 — Capability Matrix (能力矩阵)

> Verification: PARTIAL — Capabilities identified from source code; external research comparison NOT_VERIFIED (see Research Matrix)

## 1. Capability Inventory by Repository

### 1.1 ZBC Capabilities (Production)
| Capability ID | Name | Domain | Maturity | Dependencies | Owner |
|---|---|---|---|---|---|
| ZBC-CAP-001 | 多平台内容采集 | Collection | Production | XHS CDP, Bilibili, Weibo, Web | ZBC |
| ZBC-CAP-002 | AI情感分析 | AI Analysis | Production | Multi-provider LLM | ZBC |
| ZBC-CAP-003 | 事件聚类图谱 | Event Intelligence | Production | event_graph.py | ZBC |
| ZBC-CAP-004 | 日报/周报生成 | Reporting | Production | daily_report.py | ZBC |
| ZBC-CAP-005 | 报告导出 (Excel/Word/PDF) | Reporting | Production | export_report.py | ZBC |
| ZBC-CAP-006 | 品牌知识库 | Brand | Production | brand_directory.json | ZBC |
| ZBC-CAP-007 | PR案例匹配 | PR | Production | pr_case_engine.py | ZBC |
| ZBC-CAP-008 | 主题分类 | AI Analysis | Production | subject_classifier.py | ZBC |
| ZBC-CAP-009 | 风险评估 | Security | Production | risk_engine.py | ZBC |
| ZBC-CAP-010 | 安全边界检查 | Security | Production | safety_boundary.py | ZBC |
| ZBC-CAP-011 | 系统监控 | Ops | Production | monitoring.py | ZBC |
| ZBC-CAP-012 | 自动恢复 | Ops | Production | auto_recovery.py | ZBC |
| ZBC-CAP-013 | 微信通知 | Notification | Production | wechat_notifier.py | ZBC |
| ZBC-CAP-014 | 数据反馈循环 | Learning | Production | data_feedback_loop.py | ZBC |
| ZBC-CAP-015 | AI学习引擎 | Learning | Production | ai_learning_engine.py | ZBC |
| ZBC-CAP-016 | 运行时预检 | DevOps | Production | runtime_preflight.py | ZBC |
| ZBC-CAP-017 | 安全扫描 | Security | Production | security_scanner.py | ZBC |
| ZBC-CAP-018 | Web话题发现 | Collection | Production | web_topic_discovery.py | ZBC |
| ZBC-CAP-019 | 系统评估 | Quality | Production | evaluation_system.py | ZBC |
| ZBC-CAP-020 | 认证恢复 | Security | Production | auth_recovery_api.py | ZBC |

### 1.2 SICI Capabilities (Zachary AI Runtime)
| Capability ID | Name | Domain | Maturity | Dependencies | Owner |
|---|---|---|---|---|---|
| SICI-CAP-001 | Zachary AI Runtime | AI Runtime | Beta | zachary-ai-core.js | SICI |
| SICI-CAP-002 | Effective Rules Engine | Governance | Beta | effective-rules.js | SICI |
| SICI-CAP-003 | Runtime Preflight | DevOps | Beta | preflight.js | SICI |
| SICI-CAP-004 | Capability Registry | Governance | Beta | capability-registry.js | SICI |
| SICI-CAP-005 | 移动端PWA UI | UI | Beta | PWA manifest | SICI |
| SICI-CAP-006 | 权限门控工具执行 | Security | Beta | zachary-tool-registry.js | SICI |
| SICI-CAP-007 | ZBC证据读取 (只读) | Integration | Beta | zbc-evidence-adapter.js | SICI |
| SICI-CAP-008 | 浏览器内测试运行 | Testing | Beta | tester.js | SICI |
| SICI-CAP-009 | 代码执行沙箱 | DevOps | Beta | runner.js | SICI |
| SICI-CAP-010 | GitHub集成 | DevOps | Beta | github.js | SICI |
| SICI-CAP-011 | 研究学习UI | Learning | Beta | research-learning.js | SICI |
| SICI-CAP-012 | 三库验证 | Governance | Beta | three-repository-verifier.js | SICI |
| SICI-CAP-013 | 持久化桥接 (契约) | Integration | Contract Only | zachary-ai-persistence.js | SICI |

### 1.3 DCC Capabilities (DevOps & Learning)
| Capability ID | Name | Domain | Maturity | Dependencies | Owner |
|---|---|---|---|---|---|
| DCC-CAP-001 | Local AI Bridge | AI Runtime | v0.5.0 | server.js /api/ai/task | DCC |
| DCC-CAP-002 | 仓库审计 | DevOps | v0.5.0 | /api/audit/* | DCC |
| DCC-CAP-003 | 快照管理 | DevOps | v0.5.0 | snapshot.js | DCC |
| DCC-CAP-004 | 变更计划管理 | DevOps | v0.5.0 | change-plan.js | DCC |
| DCC-CAP-005 | 证据包管理 | Governance | v0.5.0 | evidence-bundle.js | DCC |
| DCC-CAP-006 | 学习案例存储 | Learning | v0.5.0 | learning-store.js | DCC |
| DCC-CAP-007 | Shadow Learning生命周期 | Learning | v0.5.0 | shadow-learning.js | DCC |
| DCC-CAP-008 | Effective Rules (服务端) | Governance | v0.5.0 | effective-rules.js | DCC |
| DCC-CAP-009 | Supplement协议管理 | Governance | v0.5.0 | supplement-protocol.js | DCC |
| DCC-CAP-010 | 启动预检 | DevOps | v0.5.0 | startup-preflight.js | DCC |
| DCC-CAP-011 | 安全中间件 | Security | v0.5.0 | security.js | DCC |
| DCC-CAP-012 | GitHub审计UI | DevOps | v0.5.0 | github-audit.js | DCC |
| DCC-CAP-013 | CI验证 | DevOps | v0.5.0 | reusable-verify.yml | DCC |

### 1.4 AIDRH Capabilities (Research & Governance)
| Capability ID | Name | Domain | Maturity | Dependencies | Owner |
|---|---|---|---|---|---|
| AIDRH-CAP-001 | 研究ID生成 | Research | Reusable | tools/research_id.py | AIDRH |
| AIDRH-CAP-002 | Shadow Lifecycle协议 | Governance | Reusable | SHADOW-LEARNING-PROTOCOL.md | AIDRH |
| AIDRH-CAP-003 | DDC研究适配器 | Integration | Reusable | ddc_research_adapter.py | AIDRH |
| AIDRH-CAP-004 | 密钥扫描 | Security | Reusable | tools/secret_scan.py | AIDRH |
| AIDRH-CAP-005 | 运行时预检 (7-check) | DevOps | Reusable | tools/runtime_preflight.py | AIDRH |
| AIDRH-CAP-006 | 跨库基线治理 | Governance | Immutable | GLOBAL-CROSS-REPOSITORY-BASELINE.md | AIDRH |
| AIDRH-CAP-007 | 能力注册中心 | Governance | Reusable | CAPABILITY-REGISTRY.md | AIDRH |
| AIDRH-CAP-008 | 研究记录账本 | Research | Reusable | data/research/records.jsonl | AIDRH |

## 2. Cross-Repo Capability Comparison

| Capability Domain | ZBC | SICI | DCC | AIDRH | Best Implementation | Consolidation Action |
|---|---|---|---|---|---|---|
| AI Analysis | Production (multi-provider) | Beta (runtime) | v0.5 (proxy) | — | ZBC | Keep ZBC as authoritative, SICI/DCC consume via API |
| Learning | Production (feedback loop) | Beta (UI only) | v0.5 (lifecycle) | Research (records) | DCC (lifecycle) + AIDRH (registry) | DCC owns engine, AIDRH owns records, ZBC provides data |
| Evidence | Production (app_evidence) | Beta (read adapter) | v0.5 (bundle) | Governance (baseline) | DCC (bundle) + AIDRH (registry) | DCC creates bundles, AIDRH registers |
| Rules Engine | Production (red lines) | Beta (4-layer) | v0.5 (4-layer) | Governance (baseline) | DCC (server reference) | DCC authoritative, SICI uses shared spec |
| Preflight | Production | Beta | v0.5 | Reusable (7-check) | AIDRH (standard) + DCC (reference) | AIDRH defines spec, all adapt |
| Security Scan | Production | — | v0.5 (middleware) | Reusable | AIDRH (secret scan) + ZBC (full scan) | AIDRH standard, ZBC extends |
| Capability Registry | Production (function) | Beta | v0.5 (API) | Reusable (MD) | AIDRH (canonical registry) | AIDRH owns registry, all register |
| Testing | 55+ pytest | Beta (in-browser) | node tests | 115 pytest | AIDRH (standard) | Define cross-repo test contract |
| Monitoring | Production (6 modules) | — | — | — | ZBC | ZBC-only, no cross-repo need |
| Collection | Production (8 modules) | — | — | — | ZBC | ZBC-only, L3 no sharing |
| Reporting | Production (4 modules) | — | — | — | ZBC | ZBC-only, L3 no sharing |
| GitHub Integration | Production (ci_cd) | Beta | v0.5 (audit UI) | — | DCC (audit tool) | DCC owns audit, others consume |
| Notification | Production (WeChat) | — | — | — | ZBC | ZBC-only |

## 3. Capability Status Assessment

| Status | Count | Capabilities |
|---|---|---|
| Production (ZBC) | 20 | All ZBC-CAP-* |
| Beta (SICI) | 13 | All SICI-CAP-* |
| v0.5 (DCC) | 13 | All DCC-CAP-* |
| Reusable (AIDRH) | 8 | All AIDRH-CAP-* |
| Contract Only | 1 | SICI-CAP-013 (persistence bridge) |
| Total Unique | 54 | — |

## 4. Capability Gap Analysis

| Gap | Missing Capability | Needed By | Current State | Severity |
|---|---|---|---|---|
| No cross-repo event bus | Event-driven communication | All | None | MEDIUM |
| No unified capability registry | Single source of truth for capabilities | All | 4 separate registries | HIGH |
| No contract testing | Automated contract verification | All | None | HIGH |
| No unified logging | Cross-repo log correlation | All | Separate loggers | MEDIUM |
| No unified config management | Cross-repo config | All | Separate config systems | LOW |
| No unified auth | Cross-repo authentication | All | Separate/none | MEDIUM |
| No production deployment for SICI | Server for persistence bridge | SICI | PWA only, no server | HIGH |
| No persistence for DCC learning | Learning data survives restart | DCC | In-memory only | HIGH |

**Verification**: PARTIAL — Capabilities identified from source code analysis. Maturity levels based on repository versioning and code completeness. External benchmark comparison deferred to Research Matrix.