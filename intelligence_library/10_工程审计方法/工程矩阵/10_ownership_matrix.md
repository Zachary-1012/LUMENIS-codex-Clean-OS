# 10 — Ownership Matrix (所有权矩阵)

> Principle: One shared capability = one authoritative Owner. No cross-repo business logic duplication.  
> Verification: PASS (ownership assigned based on repository primary domain and source code analysis)

## 1. Repository-Level Ownership

| Repository | Owner Role | Primary Domain | Authority Level |
|---|---|---|---|
| Z-Brand-Core (ZBC) | Production System Owner | 品牌舆情监测、数据采集、AI分析、报告生成 | L3 Production Logic (authoritative for brand monitoring domain) |
| SICI-Core | Zachary AI Runtime Owner | 移动AI运行时、Zachary独立身份、移动端UI | L2 Validated Capability (authoritative for Zachary AI runtime) |
| Development-Command-Console (DCC) | DevOps & Learning Owner | AI开发控制台、Shadow Learning、Effective Rules、Snapshot | L2 Validated Capability (authoritative for dev workflow & learning lifecycle) |
| AI-Development-Research-Hub (AIDRH) | Research & Governance Owner | 研究记录、能力注册、跨库基线、协议定义 | L1 Evidence/Research (authoritative for research & governance) |

## 2. Capability-Level Ownership Matrix

| Capability | Authoritative Owner | Secondary Owner | Shared Level | Cross-Repo Copy Allowed? | Status |
|---|---|---|---|---|---|
| 品牌舆情监测 | ZBC | — | L3 (Production) | NO | ACTIVE |
| 数据采集 (XHS/Bilibili/Weibo/Web) | ZBC | — | L3 (Production) | NO | ACTIVE |
| AI内容分析 (sentiment/risk) | ZBC | SICI (runtime) | L2 (Validated) | YES (via contract) | ACTIVE |
| 事件图谱/聚类 | ZBC | — | L3 (Production) | NO | ACTIVE |
| 报告生成/导出 | ZBC | — | L3 (Production) | NO | ACTIVE |
| 品牌知识库 | ZBC | — | L3 (Production) | NO | ACTIVE |
| PR案例库 | ZBC | — | L3 (Production) | NO | ACTIVE |
| 系统监控/健康检查 | ZBC | — | L3 (Production) | NO | ACTIVE |
| 自动恢复 | ZBC | — | L3 (Production) | NO | ACTIVE |
| Zachary AI Runtime | SICI | — | L2 (Validated) | YES (via contract) | ACTIVE |
| Zachary独立AI身份 | SICI | — | L3 (Identity, immutable) | NO | ACTIVE |
| 移动端UI (PWA) | SICI | — | L3 (Production) | NO | ACTIVE |
| Effective Rules Engine | DCC | SICI (frontend impl) | L2 (Validated) | YES (aligned spec) | ACTIVE |
| Shadow Learning Lifecycle | DCC | AIDRH (research) | L2 (Validated) | YES (via contract) | ACTIVE |
| Learning Store | DCC | — | L2 (Validated) | YES (via adapter) | ACTIVE |
| Evidence Bundle | DCC | AIDRH (registry) | L2 (Validated) | YES (via contract) | ACTIVE |
| Snapshot/Change Plan | DCC | — | L3 (DevOps) | NO | ACTIVE |
| Local AI Bridge | DCC | — | L3 (DevOps) | NO | ACTIVE |
| Repository Audit | DCC | — | L2 (Validated) | YES (via API) | ACTIVE |
| Research Records | AIDRH | — | L1 (Evidence) | YES (cross-repo reference) | ACTIVE |
| Capability Registry | AIDRH | — | L1 (Evidence) | YES (cross-repo reference) | ACTIVE |
| Cross-Repo Baseline | AIDRH | — | L3 (Governance, immutable) | NO | ACTIVE |
| Secret Scanning | AIDRH | ZBC (security_scanner) | L2 (Validated) | YES (aligned) | ACTIVE |
| Runtime Preflight | AIDRH | ZBC, SICI, DCC (implementations) | L2 (Validated) | YES (4 implementations, need alignment) | ACTIVE |
| Design Tokens (ZBIP) | **UNASSIGNED** | SICI, DCC (identical), ZBC (divergent) | L2 | YES | **CONFLICT** |
| GitHub Integration | **UNASSIGNED** | ZBC (ci_cd), SICI (github.js), DCC (github-audit.js) | L2 | YES | **GAP** |
| Testing Framework | **UNASSIGNED** | ZBC (pytest), SICI (tester.js), DCC (node), AIDRH (pytest) | L1 | YES | **GAP** |
| Logging | ZBC (logger.py) | — | L3 | NO | ACTIVE |
| Notification (WeChat) | ZBC | — | L3 | NO | ACTIVE |
| Cache Management | ZBC | — | L3 | NO | ACTIVE |

## 3. Ownership Violations

| Violation | Capability | Repos Involved | Issue | Severity |
|---|---|---|---|---|
| Multiple implementations | Runtime Preflight | ZBC, SICI, DCC, AIDRH | 4 separate implementations, no single source of truth | MEDIUM |
| Multiple implementations | Effective Rules | SICI, DCC | 2 implementations (frontend + server), semantic alignment but code duplication | MEDIUM |
| Divergent shared file | Design Tokens | ZBC vs SICI/DCC | ZBC has different SHA (137a6f0e vs 2210afc9) | LOW |
| No owner assigned | Design Tokens | All | No authoritative owner for ZBIP_DESIGN_TOKENS.css | MEDIUM |
| No owner assigned | GitHub Integration | ZBC, SICI, DCC | 3 separate GitHub integration modules | LOW |
| Learning logic fragmentation | Learning | All 4 | 4 different learning implementations, no unified owner | HIGH |
| Evidence logic fragmentation | Evidence | ZBC, SICI, DCC, AIDRH | 4 different evidence implementations | HIGH |

## 4. Ownership Resolution Recommendations

| Capability | Recommended Owner | Action |
|---|---|---|
| Design Tokens | AIDRH (as shared standard) | Move ZBIP_DESIGN_TOKENS.css to AIDRH as canonical, all repos reference via contract |
| Runtime Preflight | AIDRH (as standard) + DCC (as reference impl) | AIDRH defines spec, DCC provides reference implementation, ZBC/SICI adapt |
| Effective Rules | DCC (as authoritative) | SICI frontend should call DCC API or use shared spec, not duplicate logic |
| Learning | DCC (lifecycle) + AIDRH (research registry) | DCC owns learning engine, AIDRH owns research records, ZBC/SICI consume via API |
| Evidence | DCC (bundle creation) + AIDRH (registry) | DCC creates evidence bundles, AIDRH registers, ZBC/SICI consume |
| GitHub Integration | DCC (as audit tool) | ZBC/SICI should use DCC audit API or shared library |
| Testing | AIDRH (as standard) | Define cross-repo test contract in AIDRH |

## 5. Cross-Repo Sharing Level Compliance

| Shared Item | Level | Compliant? | Evidence |
|---|---|---|---|
| AIDRH research records referenced by all | L1 | PASS | GLOBAL-CROSS-REPOSITORY-BASELINE.md |
| SICI reads ZBC evidence (read-only) | L1 | PASS | zbc-evidence-adapter.js |
| DCC CI-VERIFY used by SICI | L2 | PASS | capability-registry.js dependency |
| AIDRH ddc_research_adapter reads DCC format | L1 | PASS | ddc_research_adapter.py |
| Effective Rules duplicated in SICI+DCC | L2 | PARTIAL | Same logic, separate code — should use contract |
| Runtime Preflight in 4 repos | L2 | PARTIAL | 4 implementations, no shared contract |
| ZBC production logic in other repos | L3 | PASS | No cross-repo copying of ZBC collection/reporting logic found |

**Verification**: PASS — Ownership assigned based on repository primary domain. Violations identified from source code analysis. Recommendations are proposals requiring Human Gate approval.