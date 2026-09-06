# 13 — Duplicate Matrix (重复矩阵)

> Verification: PASS — Duplicates identified via SHA comparison, file name analysis, and semantic code analysis

## 1. Exact Duplicates (Identical SHA)

| File | SHA | Repo 1 | Repo 2 | Size | Action |
|---|---|---|---|---|---|
| ZBIP_DESIGN_TOKENS.css | 2210afc983ea7f97f75b1bc031d785b185abcb81 | SICI | DCC | 1399B | Keep shared, assign owner (AIDRH) |

## 2. Near-Duplicates (Same Name, Different Content)

| File Pattern | ZBC | SICI | DCC | AIDRH | Duplication Type | Action |
|---|---|---|---|---|---|---|
| ZBIP_UNIFIED_README.md | 8503B (SHA?) | 4245B | 5814B | 5513B | Similar name, different content | Consolidate to AIDRH as canonical |
| PLATFORM_README.md | 13737B | 9572B | 11816B | — | Similar name, different content | Consolidate to AIDRH |
| README.md | (large) | 3218B | 20954B | 6547B | Repo-specific, expected | Keep separate (repo-specific) |
| effective-rules.js | — | 12455B (frontend) | 8543B (server) | — | Semantic duplicate, separate impl | Align to DCC server as reference |
| preflight / runtime_preflight | 14928B (py) | 9850B (js) | 5223B (js) | (py, adapted) | Semantic duplicate, 4 impls | AIDRH defines standard |
| secret_scan / security_scanner | 14140B | — | — | (py) | Semantic overlap | AIDRH standard, ZBC extends |
| capability-registry / function_registry | 7204B (py) | 6278B (js) | — | 2775B (md) | Different formats, same concept | AIDRH canonical registry |
| learning / ai_learning | 18035B (py) | 2727B (js) | 25690B+20303B (js) | research/ | 4 implementations, different layers | DCC engine + AIDRH registry |
| evidence / app_evidence | 15430B (py) | 1508B (adapter) | 16296B (bundle) | baseline md | 4 implementations, different layers | DCC bundle + AIDRH registry |

## 3. Semantic Duplicates (Different Names, Same Functionality)

| Concept | ZBC Implementation | SICI Implementation | DCC Implementation | AIDRH Implementation | Duplication Level |
|---|---|---|---|---|---|
| Rules resolution | safety_boundary.py (red line checks) | effective-rules.js (4-layer priority) | effective-rules.js (4-layer priority) | PLATFORM_BASELINE.md (rules doc) | HIGH — 3 code impls + 1 doc |
| Startup validation | runtime_preflight.py (10+ checks) | preflight.js (10 checks) | startup-preflight.js (integrity checks) | runtime_preflight.py (7 checks) | VERY HIGH — 4 impls |
| Capability discovery | function_registry.py + function_map.json | capability-registry.js (UMD) | /api/capabilities endpoint | CAPABILITY-REGISTRY.md | HIGH — 4 formats |
| Learning management | ai_learning_engine.py + data_feedback_loop.py | research-learning.js (UI) | learning-store.js + shadow-learning.js | research records JSONL | HIGH — 4 approaches |
| Evidence handling | app_evidence.py | zbc-evidence-adapter.js (read-only) | evidence-bundle.js | GLOBAL-CROSS-REPOSITORY-BASELINE.md | HIGH — 4 layers |
| Secret detection | security_scanner.py | — | security.js (CORS only, not secret scan) | secret_scan.py | MEDIUM — 2 impls |
| GitHub operations | ci_cd.py (CLI) | github.js (API) | github-audit.js (UI + API) | — | MEDIUM — 3 impls |
| Test execution | pytest (55+ files) | tester.js (in-browser) | node tests | pytest (115 tests) | LOW — different frameworks |
| Config management | config.py (env+JSON) | storage.js (localStorage) | config.js (constants) | — | LOW — different scopes |
| Logging | logger.py (structured) | console.log | console.log | print | LOW — different scopes |

## 4. Duplication Risk Assessment

| Duplication | Risk | Severity | Recommended Resolution |
|---|---|---|---|
| Effective Rules (SICI + DCC) | Logic drift between frontend and server | MEDIUM | DCC server as authoritative, SICI calls API or uses shared JSON spec |
| Runtime Preflight (4 repos) | 4 different check sets, no consistency | MEDIUM | AIDRH defines standard check set, DCC provides reference impl |
| Learning (4 repos) | No unified learning, fragmented knowledge | HIGH | DCC owns lifecycle engine, AIDRH owns research registry, ZBC provides data |
| Evidence (4 repos) | No unified evidence flow | HIGH | DCC creates bundles, AIDRH registers, ZBC/SICI consume |
| Capability Registry (4 repos) | No single source of truth | HIGH | AIDRH canonical registry, all repos register capabilities |
| Design Tokens (ZBC divergent) | UI inconsistency | LOW | AIDRH canonical, all repos reference |
| GitHub Integration (3 repos) | 3 separate implementations | LOW | DCC audit tool as standard, others use via API |

## 5. Duplication by Sharing Level Compliance

| Duplicated Item | Current Level | Allowed Level | Compliant? | Action |
|---|---|---|---|---|
| Effective Rules code | L2 (copied) | L2 (via contract) | PARTIAL | Should use contract, not code copy |
| Runtime Preflight code | L2 (copied) | L2 (via contract) | PARTIAL | Should use contract, not code copy |
| ZBC collection logic | L3 (ZBC-only) | L3 (no cross-repo) | PASS | No cross-repo copying found |
| ZBC reporting logic | L3 (ZBC-only) | L3 (no cross-repo) | PASS | No cross-repo copying found |
| AIDRH research docs | L1 (referenced) | L1 (cross-repo OK) | PASS | Correctly referenced, not copied |
| Design tokens | L2 (file copy) | L2 (via contract) | PARTIAL | Should have canonical owner |

## 6. Dead Code / Backup Files (Potential Duplicates)

| File | Repo | Size | Issue | Action |
|---|---|---|---|---|
| app_backup_v589.py | ZBC | 251896B | 95% duplicate of app.py | Remove from repo, use git history |
| ark_analysis.py.txt | ZBC | 1772B | Python code with .txt extension | Either rename to .py or remove |
| user_file | ZBC | 1461B | No extension, unclear purpose | Identify purpose or remove |
| video_frames_grid.jpg | ZBC | 2151622B | Large binary in repo | Move to assets repo or LFS |
| video_part_1-3.jpg | ZBC | ~750KB each | Large binaries in repo | Move to assets repo or LFS |
| 公关话术模板-舆情信息.docx | ZBC | 21206B | Binary docx in repo | Move to docs repo or convert to MD |

**Verification**: PASS — Exact duplicates via SHA comparison. Semantic duplicates via code analysis. Dead code via file extension and size analysis.