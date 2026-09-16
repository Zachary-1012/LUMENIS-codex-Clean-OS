# LUMENIS Source-Level Repository Audit — 2026-09-16

> Scope: current remote `main` source, runtime entrypoints, manifests, CI/test tiers, Evidence/Canonical implementation, XHS/RedNote collector runtime, Experience V2 and content-generation implementation.  
> This report records source-level facts and explicit limitations. It is not a runtime/live verification certificate.

## 1. Audited remote baseline

```text
repository = Zachary-1012/LUMENIS-codex-Clean-OS
visibility = private
branch     = main
baseline   = 147e3bd331b22236930ae29112a67c613a148f67
commit     = Integrate existing XHS status into CTH surface
```

GitHub repository metadata at audit time showed administrative/push access for the active connection and `main` as the default branch. Branch protection was not enabled at the audited baseline.

The repository-level GitHub license metadata reported:

```text
license.key     = other
license.spdx_id = NOASSERTION
```

No canonical root `LICENSE` file was found at the audited baseline by direct file lookup. A repository-level proprietary license notice is therefore added as part of this documentation update instead of pretending an OSI license already existed.

## 2. Audit method

The audit did not rely on chat memory as implementation proof. It inspected current remote repository resources including:

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

The recursive repository tree was also inspected to confirm the presence of canonical governance, architecture, audit, workflow and source areas.

## 3. Repository / governance findings

### 3.1 Canonical entrypoints exist

Remote source contains:

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

The pre-update README and AGENTS both define current source/runtime truth above historical handoff/chat evidence and enforce a single writable `main` workflow.

### 3.2 Local and remote truth must remain separate

The current working session also has user-supplied local evidence of a local `main` newer than the audited remote baseline and a local `requirements.txt` modification for `feedparser`.

That local state is not reclassified as remote implementation in this audit. Documentation must state:

```text
local evidence != GitHub remote evidence
```

until the actual local changes are reconciled and pushed.

## 4. Runtime findings

### 4.1 Canonical Windows launcher

`scripts/start_production.ps1` is explicitly documented in source as the canonical Windows production entrypoint.

Observed runtime behavior includes:

```text
repo-root resolution from script location
.venv Python validation
production dependency check
8201 supervisor launch
/healthz wait
stale 8201 Python cleanup when unhealthy
9222 / 9223 resident-browser ensure step
```

The script resolves the repository root from its own location; the workstation path is therefore an operational entrypoint rather than a portable code requirement.

### 4.2 Supervisor

`run_supervised.py` supervises `app.py`, writes supervisor state/logs, monitors `/healthz`, restarts actual process exits and kills/restarts zombie-like process trees after repeated health failures.

The supervisor remains Windows-oriented through `msvcrt`, `taskkill`, Windows process flags and the current launcher architecture.

### 4.3 Deployment implication

The current production runtime is not a drop-in Vercel/Railway style deployment because the full operating model includes Windows process control and resident Edge/CDP browser dependencies.

Cloud migration may later separate stateless Flask/API/workers from browser-dependent runtime, but that is a future architecture decision, not a current source fact.

## 5. Application / API findings

`app.py` is the current Flask application entrypoint and registers multiple existing product/runtime APIs.

Source-level examples include registration of:

```text
system health
architecture
settings
export/report
runtime/system features
trend/viz/data-center
intelligence library
content generation
module registry
internal browser
browser surface
evidence API
LUMENIS frontend compatibility layer
Experience V2 runtime
aggregation API
```

The application still contains historical `ZBC`/广州太古汇 naming in comments/docstrings/modules. This is legacy naming evidence, not proof that the product definition remains a single-subject monitoring tool.

## 6. Experience V2 findings

`experience_runtime.py` states that it mounts the current zero-build Experience V2 under:

```text
/experience/
/api/experience/*
```

The source explicitly defines:

```python
BOUND_SCREENS = ("CTH-01", "AI-01")
```

Therefore:

- CTH-01 and AI-01 have explicit backend-binding claims in current source;
- other prototype screens must not be represented as fully production-bound merely because prototype assets exist;
- missing backend data is intended to use explicit states such as `notcollected`, `empty`, `offline`, `error` rather than fabricated values.

The runtime also contains permission-gated AI/composer behavior and explicit permanent-deny handling for direct push/publish-like actions.

## 7. Evidence / Canonical findings

`evidence_chain.py` is a material current Evidence/Canonical owner.

Observed source principles:

```text
Evidence raw source is immutable in meaning
full SHA-256 content hash
provenance metadata
source/task/trace identity fields
subject/domain/product context
AI analysis separated from human correction
rule_version preserved
zbc_evidence + zbc_canonical_data + lifecycle tracking
```

The current remote baseline documentation/comments describe hash-based dedupe and independent Evidence/Canonical tables.

Important distinction: the current working session reports a newer local XHS lineage convergence commit that is not present at the audited remote baseline. This audit does not rewrite remote history by pretending that local commit is already in GitHub.

## 8. XHS / RedNote collector findings

`xhs_cookie_bridge.py` contains current controlled runtime collection behavior.

Observed source facts include:

```text
local/private cookie-file contract
dual logical identities
XHS_CN_PRIMARY / XHS_RETINAUT
CDP 9222 / 9223 mapping
account policy gate
cooldown / run-count safety controls
resident-browser model
no source/log JSON cookie disclosure intent
```

The current code still includes real operational identifiers/config conventions and therefore remains sensitive production infrastructure. Documentation should describe the contract, not duplicate credential/session material.

## 9. Content / Research findings

`content_generation.py` implements a structured content-generation engine with multiple content types and a research-before-generation flow.

Observed implementation concepts include:

```text
research lookup from intelligence_assets
filesystem research lookup
structured generation schema
Evidence record per generation
Evaluation record
human feedback / regeneration lineage
local-first AI semantics
explicit cloud enable behavior
```

This supports the product architecture claim that AI is an enhancement layer around research/evidence/evaluation rather than an independent Production Truth owner.

## 10. Dependency findings

### 10.1 Remote Python runtime manifest

The audited `requirements.txt` includes direct runtime/tooling dependencies such as:

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

`sqlite3` is correctly treated as Python stdlib rather than a pip dependency.

### 10.2 Remote development manifest

`requirements-dev.txt` layers on top of `requirements.txt` and adds pytest.

### 10.3 Root Node manifest

`package.json` is marked `private: true`, uses historical package name `taikoo-monitor`, and directly depends only on Playwright with XHS search/inject/login scripts.

The root Node manifest is therefore tooling-oriented; it is not evidence of a Next.js/React/Vite production frontend.

### 10.4 feedparser truth

At the audited remote baseline:

```text
feedparser NOT present in requirements.txt
```

The current acceptance session locally verified `feedparser 6.0.14`, but that remains local evidence until the actual manifest change reaches `main`.

## 11. Zero-auth capability findings

Existing remote foundations already support a zero-auth acquisition program without adding cloud APIs:

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
PublicHttpAdapter
RSSAdapter
AtomAdapter
SitemapAdapter
BrowserAdapter
```

But source audit does **not** prove all of these named adapters currently exist as one completed, unified production contract.

Required closure remains:

```text
External Source
→ Adapter
→ Evidence
→ Canonical
→ Function / Research
→ Metric / ViewModel
→ UI / Report / Export
```

## 12. CI / test findings

`.github/workflows/platform-verify.yml` currently defines a blocking clean-checkout path including:

```text
Python 3.11
requirements-dev install
compileall
CI test-tier manifest validation
hermetic pytest
```

It also reports credential-path boundary diagnostics and classifies boundary/asset scans as advisory/informational.

`tests/CI_TEST_TIERS.md` explicitly separates:

```text
Tier A — Repository Integrity (BLOCKING)
Tier B — Hermetic Product/Contract Regression (BLOCKING)
Tier C — Production / Live / Environment Gate
```

Therefore a green GitHub workflow cannot be used as a substitute for Tier C/live evidence or full release readiness.

## 13. Third-party / OSS findings

`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md` exists and correctly uses `VERIFY_BEFORE_RELEASE` instead of inventing unknown license claims.

The register explicitly requires license reconciliation before release and treats unknown licensing as a blocker.

This audit preserves that rule.

## 14. Repository license finding and action

At baseline:

```text
GitHub license metadata = Other / NOASSERTION
canonical root LICENSE  = not found by direct lookup
repository visibility   = private
package.json private     = true
```

Because no existing OSI license was proven, this update does **not** invent an MIT/Apache/GPL grant.

A root proprietary `LICENSE` notice is added to define a conservative repository-level source-code boundary while explicitly excluding third-party components from that ownership grant.

Any future change from proprietary to an open/source-available license is a legal/governance decision and must be explicit.

## 15. Current acceptance state after this audit

Documentation/source audit can prove:

```text
SOURCE_AUDITED                   = YES
REMOTE_BASELINE_IDENTIFIED       = YES
RUNTIME_ENTRYPOINT_IDENTIFIED    = YES
DEPENDENCY_MANIFEST_AUDITED      = YES
CI_TIER_MODEL_AUDITED            = YES
EVIDENCE_OWNER_AUDITED           = YES
XHS_RUNTIME_AUDITED              = YES
EXPERIENCE_RUNTIME_AUDITED       = YES
CONTENT_ENGINE_AUDITED           = YES
LICENSE_BOUNDARY_DOCUMENTED      = YES after LICENSE commit
```

This audit does **not** prove:

```text
ADAPTER_IMPLEMENTED              = NO CLAIM
ALL_TARGETED_TESTS_PASS          = NO CLAIM
8201_LIVE_HEALTHY                = NO CLAIM
PLAYWRIGHT_LIVE_PASS             = NO CLAIM
P0_P1_ZERO                       = NO CLAIM
LIVE_VERIFIED                    = NO
RELEASED                         = NO CLAIM
OPERATING                        = NO CLAIM
```

## 16. Required next engineering sequence

After the user's current local work is reconciled with the documentation commits now added to remote `main`:

```text
preserve local 005e827... work
→ fetch origin/main
→ reconcile without destructive reset/clean
→ keep intended requirements.txt feedparser delta
→ inspect current diff
→ implement/close zero-auth adapters against existing Evidence/Canonical contracts
→ targeted tests
→ affected regression
→ 8201 runtime acceptance
→ Experience/API live verification
→ release gate decision
```

Do not reopen unrelated historical audits unless current executable evidence proves a regression.
