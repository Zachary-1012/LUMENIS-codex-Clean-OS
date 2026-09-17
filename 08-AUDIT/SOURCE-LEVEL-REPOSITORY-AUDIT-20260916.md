# LUMENIS Source-Level Repository Audit — 2026-09-16

> Status: SOURCE AUDIT + POST-AUDIT CORRECTION  
> Scope: remote `main` source/runtime/manifests/CI tiers/Evidence/Canonical/XHS-RedNote/Experience V2/content-generation plus the post-audit CI result.  
> This document is not a runtime/live verification certificate.

## 1. Source-audit baseline and post-audit state

The source-level audit baseline remains:

```text
repository = Zachary-1012/LUMENIS-codex-Clean-OS
visibility = private
branch     = main
baseline   = 147e3bd331b22236930ae29112a67c613a148f67
commit     = Integrate existing XHS status into CTH surface
```

Documentation/legal updates then advanced remote `main` through:

```text
74f2a662  README truth refresh
2a98f7bb  AGENTS execution alignment
8819c192  zero-auth acceptance matrix
81eb8e00  source-level audit
E50e0770  proprietary LICENSE notice
7d2d2851  corrected tooling + CI acceptance truth
```

The exact current HEAD should always be re-read before engineering work; commit lists in an audit are historical evidence, not a substitute for `git fetch`/remote inspection.

## 2. Audit method

Implementation claims were grounded in current remote source rather than chat memory. Inspected resources included:

```text
README.md
AGENTS.md
requirements.txt
requirements-dev.txt
package.json
.github/workflows/platform-verify.yml
tests/CI_TEST_TIERS.md
scripts/start_production.ps1
run_supervised.py
app.py
experience_runtime.py
evidence_chain.py
xhs_cookie_bridge.py
content_generation.py
00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md
```

The repository tree was also inspected for governance, architecture, audit, workflow and production source areas.

## 3. Repository / governance findings

Canonical entrypoints exist:

```text
README.md
AGENTS.md
00-GOVERNANCE/
02-ARCHITECTURE/
08-AUDIT/
99-ARCHIVE/
.github/workflows/
scripts/
```

Current source/runtime truth has precedence over historical handoff/chat evidence. Local unpushed code and remote GitHub state remain separate facts until actual reconciliation/push.

Hard rule retained:

```text
local evidence != GitHub remote evidence
```

## 4. Runtime findings

### 4.1 Canonical Windows launcher

`scripts/start_production.ps1` is the canonical Windows production entrypoint. Observed responsibilities include:

```text
repository-root resolution from script location
.venv Python validation
production dependency check
8201 supervisor launch
/healthz wait
stale 8201 Python cleanup when unhealthy
9222 / 9223 resident-browser ensure step
```

### 4.2 Supervisor

`run_supervised.py` supervises `app.py`, persists supervisor state/logs, probes `/healthz`, restarts real exits and restarts zombie-like process trees after repeated health failure. The current implementation is Windows-oriented (`msvcrt`, `taskkill`, Windows process behavior).

### 4.3 Deployment implication

The complete current runtime is not a drop-in Vercel/Railway deployment because resident Edge/CDP and Windows process-control behavior are part of the operating model. Any cloud split is a future architecture decision.

## 5. Application / API findings

`app.py` remains the current Flask application entrypoint and wires existing system/product capabilities including health, settings, reports/export, runtime/system features, trend/viz/data-center, intelligence library, content generation, module registry, internal browser/browser surface, Evidence APIs, Experience V2 and aggregation APIs.

Historical `ZBC`/广州太古汇 naming still exists in source comments/docstrings/modules. That is legacy naming debt, not proof that the current product definition is limited to a single-subject monitoring tool.

## 6. Experience V2 findings

`experience_runtime.py` mounts the current Experience V2 at:

```text
/experience/
/api/experience/*
```

Current source explicitly defines:

```python
BOUND_SCREENS = ("CTH-01", "AI-01")
```

Therefore only those screens have explicit current backend-binding claims from that contract. Other prototype assets must not be promoted to production-bound status merely because they exist.

The runtime intentionally distinguishes states such as `notcollected`, `empty`, `offline`, and `error` rather than fabricating numeric values.

## 7. Evidence / Canonical findings

`evidence_chain.py` is a material current Evidence/Canonical owner. Observed source contracts include:

```text
immutable-source Evidence semantics
full SHA-256 content hash
provenance metadata
source/task/trace identity
subject/domain/product context
AI analysis separated from human correction
rule_version preservation
zbc_evidence + zbc_canonical_data + lifecycle tracking
```

The existing app path also contains a side-write Evidence/Canonical integration pattern whose failure must not silently corrupt the primary ingestion path where the contract requires isolation.

## 8. XHS / RedNote collector findings

`xhs_cookie_bridge.py` contains controlled runtime collection behavior including:

```text
local/private cookie-file contract
dual logical identities
XHS_CN_PRIMARY / XHS_RETINAUT
CDP 9222 / 9223 mapping
account policy gate
cooldown / run-count safety controls
resident-browser model
```

The source contains operational configuration/identity conventions; documentation should describe contracts without duplicating credential/session material.

## 9. Content / Research findings

`content_generation.py` implements research-before-generation behavior with structured content types, generation Evidence, Evaluation records, human-feedback/regeneration lineage and local-first/provider-controlled AI behavior.

This supports the architecture rule that AI is an enhancement layer rather than the owner of Production Truth.

## 10. Dependency findings — corrected

Remote `requirements.txt` at the audited source baseline includes, among others:

```text
Flask / Werkzeug / Flask-CORS / Flask-Limiter / waitress
APScheduler / schedule
pandas / openpyxl / xlsxwriter
beautifulsoup4 / lxml
python-docx / reportlab
playwright
psutil
requests / httpx / websocket-client
python-dotenv / python-dateutil / PyYAML / colorama / tqdm
aiohttp / yyds-logger / tenacity / alembic
```

`requirements-dev.txt` layers pytest on top of runtime requirements. Root `package.json` is private and Playwright/tooling-oriented rather than proof of a Next/React/Vite production frontend.

Corrected acceptance for the two newly discussed dependencies:

```text
aiohttp 3.14.3
  local import/version PASS
  pip consistency PASS
  NOT sufficient evidence for async adapter functional PASS

feedparser 6.0.14
  local install/import PASS
  RSS fixture PASS
  Atom library capability AVAILABLE
  Atom functional test NOT RUN
  remote requirements.txt convergence still pending at the audited remote state
```

Therefore neither library installation nor import alone proves the new adapter closed loop.

## 11. Zero-auth capability direction

Existing foundations support a zero-auth acquisition program without adding cloud APIs:

```text
requests / httpx / aiohttp
BeautifulSoup4 / lxml
Playwright
SQLite
APScheduler
tenacity
```

Approved immediate adapter direction:

```text
Public HTTP Adapter
RSS Adapter
Atom Adapter
Sitemap Adapter
Browser Adapter
```

Required production closure:

```text
External Source
→ Adapter
→ Evidence
→ Canonical
→ Function / Research
→ Metric / ViewModel
→ UI / Report / Export
```

No adapter may create a parallel Evidence/Canonical/DB truth.

## 12. Codex tooling status — external engineering layer

The engineering environment now reports these Codex/plugin capabilities as installed/connected:

```text
GitHub               installed; actually used in this audit/update flow
OpenAI Developers    installed
Figma                installed + connected
Context7              installed + connected
Codex Security        installed
Playwright MCP        user-confirmed installed
```

These are engineering tools, not LUMENIS production-runtime dependencies. `installed/connected` is not the same as functional task-level verification. Codex should run real smoke tests after quota recovery.

Filesystem MCP remains optional rather than mandatory for normal repository work. `rg`, `fd`, `jq`, `curl`, and `sqlite3 CLI` are local tools and should be verified on the workstation only as needed; Python `sqlite3` is already sufficient for equivalent scoped read-only DB inspection.

## 13. CI / test findings — corrected with run #148

CI is definitively bound. `.github/workflows/platform-verify.yml` responds to:

```text
push to main
pull_request to main
workflow_dispatch
```

The documentation/license update triggered:

```text
workflow = Verify LUMENIS
run      = #148
head     = e50e07701399b1d46b794dd1802dca93defae9d8
event    = push
status   = completed
result   = failure
```

Successful steps included dependency installation, Python compile, CI test-tier manifest validation and credential-path boundary diagnostic. The blocking failure was:

```text
Run clean-checkout hermetic pytest (BLOCKING)
```

The run selected 257 hermetic test files. The log contains 21 failing test cases grouped around:

```text
AI provider-policy expectation
Douyin adapter result/status semantics
HK-only collection policy artifact-path expectation
RedNote rotation / resident browser port expectation
Bilibili / Weibo secondary-platform adapter semantics
CDP retry/online expectation
```

Thus the precise CI state is:

```text
CI_BOUND       = YES
CI_TRIGGERED   = YES
CI_COMPLETED   = YES
CI_PASS        = NO
TARGETED_TESTS = NOT GREEN
```

The advisory Boundary Check also reported non-zero findings, but that step is currently classified advisory and did not cause the workflow failure. Those findings are still evidence to review; advisory does not mean resolved.

Do not move deterministic failures into quarantine, weaken assertions or delete tests solely to obtain a green badge. First classify each failure as stale expectation, fixture/mock drift, or production regression.

## 14. CI tier semantics remain valid

`tests/CI_TEST_TIERS.md` separates:

```text
Tier A — Repository Integrity (BLOCKING)
Tier B — Hermetic Product/Contract Regression (BLOCKING)
Tier C — Production / Live / Environment Gate
```

Even when Tier A/B eventually become green, that will not substitute for Tier C/live evidence or full release readiness.

## 15. Third-party / license findings

`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md` uses `VERIFY_BEFORE_RELEASE` instead of inventing package-license claims and requires reconciliation before release.

At the original audit baseline, repository metadata was `Other / NOASSERTION` and no canonical root `LICENSE` was found. A root proprietary `LICENSE` notice was then added at commit `e50e077...`, explicitly preserving third-party components under their own licenses.

Any future change from proprietary to an open/source-available license remains an explicit legal/governance decision.

## 16. Current acceptance state

Proven by current source/audit evidence:

```text
SOURCE_AUDITED                    = YES
REMOTE_BASELINE_IDENTIFIED        = YES
RUNTIME_ENTRYPOINT_IDENTIFIED     = YES
DEPENDENCY_MANIFEST_AUDITED       = YES
CI_BOUND                          = YES
CI_LAST_OBSERVED_PASS             = NO (#148 failure)
EVIDENCE_OWNER_AUDITED            = YES
XHS_RUNTIME_AUDITED               = YES
EXPERIENCE_RUNTIME_AUDITED        = YES
CONTENT_ENGINE_AUDITED            = YES
LICENSE_BOUNDARY_DOCUMENTED       = YES
```

Not proven / currently blocked:

```text
ADAPTER_IMPLEMENTED               = NOT VERIFIED
ALL_TARGETED_TESTS_PASS           = NO
8201_LIVE_HEALTHY                 = NOT VERIFIED by this update
PLAYWRIGHT_LIVE_PASS              = NOT VERIFIED
P0_P1_ZERO                        = NOT VERIFIED
LIVE_VERIFIED                     = NO
RELEASED                          = NO CLAIM
OPERATING                         = NO CLAIM
```

## 17. Required next engineering sequence

When Codex quota is restored:

```text
preserve local unpushed work
→ fetch current origin/main
→ reconcile local main without reset/clean
→ preserve/verify intended feedparser manifest change
→ reproduce and classify CI #148 failures
→ fix legitimate regressions / stale fixtures without weakening gates
→ run Atom functional fixture
→ smoke-test installed Codex tools/plugins
→ implement/converge Public HTTP / RSS / Atom / Sitemap / Browser adapters
→ enforce Adapter → Evidence → Canonical
→ targeted + affected regression
→ 8201 health
→ API verification
→ Playwright E2E
→ CI
→ release gates
```

Do not reopen unrelated historical audits unless current executable evidence requires it.