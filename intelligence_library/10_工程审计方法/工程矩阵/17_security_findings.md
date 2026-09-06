# 17 — Security Findings (安全审计发现)

> Verification: PARTIAL — Findings from source code analysis and .env.example review. Live secret scanning NOT_VERIFIED (run_secret_scanning not executed on full repos)

## 1. Critical Findings (HIGH Severity)

### SEC-001: No Encryption at Rest for SQLite Database
- **Repo**: ZBC
- **File**: database.py, data/monitor.db
- **Finding**: SQLite database contains PII (author_id, author_nickname, author_avatar) with no encryption at rest. No field-level encryption for potential credentials in system_config table.
- **Evidence**: database.py uses standard sqlite3 connection with no PRAGMA key or SQLCipher. .env.example has no DB encryption key.
- **Impact**: Anyone with file system access can read all PII and potential credentials.
- **Recommendation**: Migrate to SQLCipher or implement application-level encryption for sensitive fields.
- **Status**: FAIL

### SEC-002: No PII Retention Policy
- **Repo**: ZBC
- **File**: notes table, comments table, note_comments table
- **Finding**: No TTL, no archival, no deletion mechanism for PII fields. Data persists permanently.
- **Evidence**: No DELETE or cleanup jobs identified in source code. notes table has 70+ fields including author PII.
- **Impact**: GDPR/PIPL compliance risk. Unlimited PII accumulation.
- **Recommendation**: Implement retention policy with automated archival/deletion.
- **Status**: FAIL

### SEC-003: DCC Learning State In-Memory Only (Data Loss)
- **Repo**: DCC
- **File**: server/learning-store.js, server/shadow-learning.js
- **Finding**: Learning cases, patterns, lessons, and shadow learning state are stored in memory only. Lost on server restart. No persistence to disk.
- **Evidence**: learning-store.js uses in-memory arrays/objects. No fs.writeFile for learning data.
- **Impact**: All learning progress lost on restart. No audit trail for learning decisions.
- **Recommendation**: Persist to JSON files (like baseline.json) or external store.
- **Status**: FAIL

### SEC-004: SICI Persistence Bridge Has No Server Implementation
- **Repo**: SICI
- **File**: js/zachary-ai-persistence.js
- **Finding**: Persistence bridge contract exists but has no server endpoint. Zachary AI state is stored in localStorage only, lost on browser data clear.
- **Evidence**: zachary-ai-persistence.js is 1504B, defines interface but no fetch calls to a real server.
- **Impact**: AI learning and state not persisted across devices/sessions.
- **Recommendation**: Implement DCC server endpoint for persistence bridge.
- **Status**: FAIL

### SEC-005: ZBC Database Schema/Model Mismatch (7 Tables)
- **Repo**: ZBC
- **File**: database.py (15 CREATE TABLE), models.py (22 registered)
- **Finding**: 7 tables in models.py (weekly_events, web_topics, web_events, brand_industry_monitor, collection_counters, system_config) are not in database.py CREATE TABLE statements. May not exist in production DB, causing runtime errors.
- **Evidence**: database.py extracted 15 CREATE TABLE statements. models.py MODEL_REGISTRY has 22 entries.
- **Impact**: Potential runtime AttributeError or SQL errors when accessing missing tables.
- **Recommendation**: Verify production DB schema. Add missing CREATE TABLE or remove from model registry.
- **Status**: FAIL (CONFLICT — requires Human Gate)

## 2. Medium Findings (MEDIUM Severity)

### SEC-006: Missing Dependencies in requirements.txt
- **Repo**: ZBC
- **File**: requirements.txt
- **Finding**: websocket-client (for CDP in cdp_helper.py) and schedule (for collector_automation.py) are imported but not listed in requirements.txt.
- **Evidence**: requirements.txt has 14 packages. cdp_helper.py imports websocket. collector_automation.py likely imports schedule.
- **Impact**: Fresh deployment may fail with ImportError.
- **Recommendation**: Add missing dependencies to requirements.txt.
- **Status**: FAIL

### SEC-007: Monolithic app.py (264KB) — Security Audit Impossible
- **Repo**: ZBC
- **File**: app.py
- **Finding**: 264KB single file containing routes, business logic, and data access. Cannot be effectively security-audited. Potential for hidden vulnerabilities.
- **Evidence**: app.py size 264628 bytes. No route inventory available without full parsing.
- **Impact**: Security blind spot. Hard to verify auth, input validation, injection prevention.
- **Recommendation**: Decompose into blueprints/modules. At minimum, extract routes into separate files.
- **Status**: NOT_VERIFIED (full content not read)

### SEC-008: No API Authentication for ZBC Web API
- **Repo**: ZBC
- **File**: app.py (routes)
- **Finding**: No authentication middleware identified for ZBC API endpoints. SICI zbc-evidence-adapter.js reads ZBC API without auth tokens.
- **Evidence**: .env.example has no API_KEY or AUTH_TOKEN. No auth decorators in read source files.
- **Impact**: Unauthenticated access to brand monitoring data and PII.
- **Recommendation**: Add API key authentication for all /api/* endpoints.
- **Status**: NOT_VERIFIED (app.py not fully read for auth decorators)

### SEC-009: No Rate Limiting on ZBC API
- **Repo**: ZBC
- **File**: app.py
- **Finding**: No rate limiting identified for API endpoints.
- **Evidence**: No Flask-Limiter or similar in requirements.txt.
- **Impact**: API abuse, brute force, data scraping.
- **Recommendation**: Implement rate limiting (Flask-Limiter).
- **Status**: NOT_VERIFIED

### SEC-010: Cross-Repo Evidence Sharing Without Contract
- **Repo**: SICI → ZBC
- **File**: js/zbc-evidence-adapter.js
- **Finding**: SICI reads ZBC evidence via API with no formal contract, no versioning, no auth. Breaking changes in ZBC will silently break SICI.
- **Evidence**: zbc-evidence-adapter.js is 1508B, no API schema reference.
- **Impact**: Silent failures, data inconsistency.
- **Recommendation**: Define OpenAPI contract, add versioning, add auth.
- **Status**: FAIL

### SEC-011: No Cross-Repo Event Bus — Polling Required
- **Repo**: All
- **Finding**: No event-driven communication between repos. All integration is via polling or manual file copying.
- **Impact**: Stale data, missed state changes.
- **Recommendation**: Implement webhook-based event notification.
- **Status**: GAP (not a vulnerability, but architecture risk)

### SEC-012: Large Binaries in Repository
- **Repo**: ZBC
- **Files**: video_frames_grid.jpg (2.1MB), video_part_1-3.jpg (~750KB each), 公关话术模板-舆情信息.docx (21KB)
- **Finding**: Large binary files in git repository. Increases clone time, potential for sensitive data in binaries.
- **Impact**: Repository bloat. Binaries may contain sensitive information.
- **Recommendation**: Move to Git LFS or separate assets repository.
- **Status**: FAIL

### SEC-013: Backup File in Production Repo
- **Repo**: ZBC
- **File**: app_backup_v589.py (251KB)
- **Finding**: Full backup of app.py in production repository. Potential for confusion, accidental import, or outdated code execution.
- **Impact**: Code confusion, potential execution of outdated code.
- **Recommendation**: Remove from repo, rely on git history.
- **Status**: FAIL

## 3. Low Findings (LOW Severity)

### SEC-014: No Dependency Locking
- **Repo**: ZBC
- **Finding**: No Pipfile.lock, poetry.lock, or requirements.lock. Dependency versions are >= constraints only.
- **Impact**: Non-reproducible builds, potential supply chain risk.
- **Recommendation**: Use pip-tools or poetry for dependency locking.
- **Status**: FAIL

### SEC-015: Design Token Divergence
- **Repo**: ZBC vs SICI/DCC
- **Finding**: ZBC ZBIP_DESIGN_TOKENS.css has different SHA (137a6f0e) than SICI/DCC (2210afc9). No single source of truth.
- **Impact**: UI inconsistency across platforms.
- **Recommendation**: Assign AIDRH as canonical owner, all repos reference.
- **Status**: FAIL

### SEC-016: AIDRH Branch Proliferation
- **Repo**: AIDRH
- **Finding**: 13 branches (research/content-benchmark-expansion-001~013) all pointing to same SHA. Accidental branch creation.
- **Impact**: Repository clutter, potential confusion.
- **Recommendation**: Delete duplicate branches.
- **Status**: FAIL

### SEC-017: No Security Headers in ZBC
- **Repo**: ZBC
- **Finding**: No Flask-Talisman or security headers (CSP, HSTS, X-Frame-Options) identified.
- **Evidence**: No Flask-Talisman in requirements.txt.
- **Impact**: XSS, clickjacking, MIME-sniffing risks.
- **Recommendation**: Add security headers via Flask-Talisman or nginx.
- **Status**: NOT_VERIFIED

### SEC-018: SICI Auto-Push Script
- **Repo**: SICI
- **File**: auto_push.ps1
- **Finding**: PowerShell auto-push script may contain credentials or automate git operations without verification.
- **Evidence**: auto_push.ps1 exists (2173B). Content not fully read.
- **Status**: NOT_VERIFIED

## 4. Positive Security Findings

| Finding | Repo | Evidence |
|---|---|---|
| Zero npm dependencies (attack surface reduction) | DCC | package.json has no runtime deps |
| Localhost binding (no external exposure) | DCC | config.js: HOST=127.0.0.1, PORT=8787 |
| Hardcoded credential removed | SICI | commit 70892a7 "security: remove hardcoded demo credential" |
| Read-only evidence adapter | SICI | zbc-evidence-adapter.js (no write operations) |
| Immutable baseline governance | AIDRH | GLOBAL-CROSS-REPOSITORY-BASELINE.md |
| Append-only research ledger | AIDRH | data/research/records.jsonl |
| Permission-gated tool execution | SICI | zachary-tool-registry.js (READ=ALLOW, WRITE=DENY, DEPLOY=DENY) |
| Safety boundary module | ZBC | safety_boundary.py (red line checks) |
| .env.example template | ZBC | .env.example (3697B, no real secrets) |
| Secret scanning tool | AIDRH | tools/secret_scan.py (R-2026-0007) |
| Runtime preflight | All 4 repos | Preflight checks before execution |
| CORS/security middleware | DCC | server/security.js |

## 5. SICI-Specific Security Red Line Check

Per instruction: "SICI 不得把模拟真人、代理/IP切换、账号轮换作为安全问题解决方案"

| Check | Finding | Status |
|---|---|---|
| Simulate real person | No simulation of real human behavior identified in SICI source | PASS |
| Proxy/IP switching | No proxy or IP rotation code in SICI | PASS |
| Account rotation | No account轮换 logic in SICI | PASS |
| Note: ZBC has proxy_pool/ directory | ZBC has proxy_pool, but this is ZBC (production collection), not SICI | ZBC-ONLY, not SICI violation |

**SICI Security Red Line**: PASS — No simulation, proxy switching, or account rotation in SICI.

## 6. Secret Scanning Status

| Repo | Scanner Present | Full Scan Executed | Push Protection | Hardcoded Secrets Found |
|---|---|---|---|---|
| ZBC | security_scanner.py | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED (app.py 264KB not scanned) |
| SICI | No | NOT_VERIFIED | NOT_VERIFIED | Fixed in commit 70892a7 (demo credential) |
| DCC | No (security.js = CORS) | NOT_VERIFIED | NOT_VERIFIED | None identified |
| AIDRH | secret_scan.py | NOT_VERIFIED | NOT_VERIFIED | None identified |

**Recommendation**: Run run_secret_scanning on all repos' full source code in follow-up audit.

## 7. Security Gate Assessment

| Gate | Status | Notes |
|---|---|---|
| No hardcoded secrets | NOT_VERIFIED | Full scan not executed |
| Encryption at rest | FAIL | ZBC SQLite unencrypted |
| PII protection | FAIL | No retention, no encryption |
| API authentication | NOT_VERIFIED | ZBC app.py not fully read |
| Rate limiting | NOT_VERIFIED | Not identified |
| Security headers | NOT_VERIFIED | Not identified |
| Dependency management | FAIL | Missing deps, no locking |
| SICI red line | PASS | No simulation/proxy/account rotation |
| Cross-repo auth | FAIL | No auth on evidence API |
| Evidence integrity | FAIL | No cryptographic verification |

**Overall Security Gate**: BLOCKED — Multiple HIGH severity findings require resolution before consolidation.

**Verification**: PARTIAL — Findings from source code analysis. Live secret scanning, penetration testing, and runtime security verification NOT_VERIFIED. All NOT_VERIFIED items require follow-up audit.