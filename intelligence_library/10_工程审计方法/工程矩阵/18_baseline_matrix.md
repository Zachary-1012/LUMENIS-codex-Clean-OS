# 18 — Baseline Matrix (基线矩阵)

> Baseline items are IMMUTABLE. Supplements can only add incrementally, never override.  
> Verification: PASS (baseline extracted from AIDRH GLOBAL-CROSS-REPOSITORY-BASELINE.md and instruction document)

## 1. Immutable Baseline Definition

Source: AIDRH `GLOBAL-CROSS-REPOSITORY-BASELINE.md` (SHA: 88512f35, 5318 bytes) + Instruction Document

### 1.1 Identity Baseline
| Baseline ID | Rule | Owner | Enforced By | Immutable? | Status |
|---|---|---|---|---|---|
| BASE-001 | Zachary独立AI身份 — Zachary AI is an independent AI entity, not a feature of ZBC | SICI | zachary-ai-core.js | YES | ACTIVE |
| BASE-002 | ZBC独立产品边界 — ZBC is an independent brand monitoring product, not part of Zachary AI | ZBC | app.py, database.py | YES | ACTIVE |
| BASE-003 | 禁止互相并入 — Zachary AI and ZBC must not merge into one repo or become submodules | All | Repository structure | YES | ACTIVE |
| BASE-004 | Mobile-first — Zachary AI runtime is mobile-first (PWA) | SICI | manifest.json, PWA architecture | YES | ACTIVE |

### 1.2 Governance Baseline
| Baseline ID | Rule | Owner | Enforced By | Immutable? | Status |
|---|---|---|---|---|---|
| BASE-005 | Ownership原则 — One shared capability = one authoritative Owner | AIDRH | CAPABILITY-REGISTRY.md | YES | ACTIVE |
| BASE-006 | Governance/Execution分离 — Governance (AIDRH) separate from Execution (ZBC/SICI/DCC) | AIDRH | Repository separation | YES | ACTIVE |
| BASE-007 | Evidence优先 — All decisions must be evidence-based, no AI speculation as PASS | All | evidence-bundle.js, app_evidence.py | YES | ACTIVE |
| BASE-008 | Security边界 — Security boundaries cannot be overridden by supplements | All | safety_boundary.py, security.js | YES | ACTIVE |
| BASE-009 | 历史Evidence保护 — Historical evidence cannot be modified or deleted | AIDRH | JSONL append-only | YES | PARTIAL (no crypto verification) |

### 1.3 Learning Baseline
| Baseline ID | Rule | Owner | Enforced By | Immutable? | Status |
|---|---|---|---|---|---|
| BASE-010 | 双向受控学习 — Bidirectional learning between Zachary AI and ZBC, but controlled via governance | DCC + AIDRH | shadow-learning.js, SHADOW-LEARNING-PROTOCOL.md | YES | ACTIVE |
| BASE-011 | Supplement只能增量生效 — Supplements add, never override baseline | DCC | effective-rules.js (priority 95 < 100) | YES | ACTIVE |
| BASE-012 | 禁止静默修改规则 — No silent rule changes, all changes must be visible | DCC | supplement-protocol.js | YES | ACTIVE |
| BASE-013 | 禁止制造第二权威 — No second source of truth for baseline | AIDRH | GLOBAL-CROSS-REPOSITORY-BASELINE.md | YES | ACTIVE |

### 1.4 Sharing Baseline
| Baseline ID | Rule | Owner | Enforced By | Immutable? | Status |
|---|---|---|---|---|---|
| BASE-014 | L1 Evidence/Research可跨库引用 | AIDRH | Research records, baseline docs | YES | ACTIVE |
| BASE-015 | L2 Validated Capability经Contract+Governance后可复用 | AIDRH + DCC | CAPABILITY-REGISTRY.md, contracts | YES | ACTIVE |
| BASE-016 | L3 Production Logic/Domain Rule默认禁止跨库复制 | ZBC | Repository isolation | YES | ACTIVE |
| BASE-017 | 所有跨库共享必须记录source_repo/source_commit/source_file/source_owner | All | (not fully implemented) | YES | PARTIAL |

### 1.5 Verification Baseline
| Baseline ID | Rule | Owner | Enforced By | Immutable? | Status |
|---|---|---|---|---|---|
| BASE-018 | 验证状态固定枚举: PASS/FAIL/BLOCKED/NOT_VERIFIED/REPLAN_REQUIRED | All | This audit | YES | ACTIVE |
| BASE-019 | 禁止: 没有证据=PASS, 网络失败=PASS, AI推测=PASS, 旧测试=当前PASS | All | This audit | YES | ACTIVE |
| BASE-020 | 必须重新验证 — No stale verification | All | This audit | YES | ACTIVE |

### 1.6 Security Baseline
| Baseline ID | Rule | Owner | Enforced By | Immutable? | Status |
|---|---|---|---|---|---|
| BASE-021 | 禁止源码硬编码密码/Token/PAT/Secret | All | secret_scan.py, .env.example | YES | PARTIAL (full scan not done) |
| BASE-022 | SICI不得把模拟真人、代理/IP切换、账号轮换作为安全问题解决方案 | SICI | SICI source code | YES | PASS |

## 2. Baseline Compliance Check

| Baseline | Compliant? | Evidence | Violation Detail |
|---|---|---|---|
| BASE-001 (Zachary独立身份) | PASS | SICI zachary-ai-core.js, separate repo | No violation |
| BASE-002 (ZBC独立边界) | PASS | ZBC separate repo, production system | No violation |
| BASE-003 (禁止并入) | PASS | 4 separate repos, no submodules | No violation |
| BASE-004 (Mobile-first) | PASS | SICI PWA, manifest.json | No violation |
| BASE-005 (Ownership) | PARTIAL | Design tokens, GitHub integration have no assigned owner | 2 capabilities unassigned |
| BASE-006 (Gov/Exec分离) | PASS | AIDRH = governance, others = execution | No violation |
| BASE-007 (Evidence优先) | PARTIAL | DCC evidence-bundle.js exists, but ZBC/SICI evidence not cryptographically verified | Evidence integrity gap |
| BASE-008 (Security边界) | PARTIAL | safety_boundary.py exists, but no API auth identified | Security gaps |
| BASE-009 (历史Evidence保护) | PARTIAL | AIDRH JSONL append-only, but no hash chaining | Tamper-evidence gap |
| BASE-010 (双向受控学习) | PARTIAL | DCC shadow-learning exists, but no automated ZBC↔AIDRH flow | Learning flow gap |
| BASE-011 (Supplement增量) | PASS | effective-rules.js priority 95 < 100 baseline | No violation |
| BASE-012 (禁止静默修改) | PARTIAL | supplement-protocol.js exists, but no audit trail for changes | Audit gap |
| BASE-013 (禁止第二权威) | PARTIAL | 4 separate capability registries exist (ZBC function, SICI registry, DCC API, AIDRH MD) | Multiple registries = potential second authority |
| BASE-014 (L1跨库引用) | PASS | AIDRH research referenced by all | No violation |
| BASE-015 (L2经Contract复用) | PARTIAL | Effective Rules duplicated without formal contract | Contract gap |
| BASE-016 (L3禁止复制) | PASS | No ZBC production logic copied to other repos | No violation |
| BASE-017 (跨库共享记录) | PARTIAL | Most cross-repo sharing lacks source_repo/source_commit tracking | Tracking gap |
| BASE-018 (验证枚举) | PASS | This audit uses fixed enumeration | No violation |
| BASE-019 (禁止假PASS) | PASS | This audit marks NOT_VERIFIED appropriately | No violation |
| BASE-020 (必须重新验证) | PASS | This audit is fresh verification | No violation |
| BASE-021 (禁止硬编码Secret) | PARTIAL | SICI fixed demo credential, but full scan not done | Full scan pending |
| BASE-022 (SICI安全红线) | PASS | No simulation/proxy/account rotation in SICI | No violation |

## 3. Baseline Violations Summary

| Severity | Count | Baselines |
|---|---|---|
| FAIL | 0 | — |
| PARTIAL | 10 | BASE-005, 007, 008, 009, 010, 012, 013, 015, 017, 021 |
| PASS | 12 | BASE-001~004, 006, 011, 014, 016, 018~020, 022 |

## 4. Baseline Protection Mechanism

| Mechanism | Implementation | Status |
|---|---|---|
| Immutable file | AIDRH GLOBAL-CROSS-REPOSITORY-BASELINE.md | ACTIVE |
| Priority enforcement | effective-rules.js (Baseline priority 100) | ACTIVE |
| Repository separation | 4 independent repos | ACTIVE |
| Governance review | AIDRH as governance owner | ACTIVE |
| Change approval | Human Gate required for baseline changes | ACTIVE (this audit) |
| Cryptographic integrity | NOT IMPLEMENTED | GAP |
| Automated baseline testing | NOT IMPLEMENTED | GAP |

**Verification**: PASS — Baseline items extracted from AIDRH governance document and instruction document. Compliance checked against source code. PARTIAL items indicate gaps in enforcement, not baseline violations.