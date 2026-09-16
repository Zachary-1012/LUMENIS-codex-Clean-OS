# 序境 / LUMENIS — Codex Takeover CURRENT

> Status: **CURRENT EXECUTION ENTRYPOINT / NO-REDISCOVERY**  
> Verified remote anchor: `main@5a14ff25b51303efb776126d0f6a3a5a936ec73f`  
> Anchor date: 2026-09-17  
> This file records current remote handoff truth. It does **not** upgrade source evidence into LIVE/RELEASE/OPERATING claims.

## 1. Authority and read order

Read in this order before changing product code:

1. `README.md`
2. `AGENTS.md`
3. this file
4. `08-AUDIT/SOURCE-LEVEL-REPOSITORY-AUDIT-20260916.md`
5. `08-AUDIT/SCREENSHOT-ARCHITECTURE-INTAKE-20260917.md`
6. `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
7. the exact current Source / Route / API / DB / Permission / Evidence / Runtime / Tests for the active slice

Current executable source/runtime truth always outranks this handoff. Historical handoffs, chat history and screenshots never override executable truth.

## 2. Current remote facts verified before this handoff

```text
repository = Zachary-1012/LUMENIS-codex-Clean-OS
branch     = main
HEAD       = 5a14ff25b51303efb776126d0f6a3a5a936ec73f
```

The merge at this anchor contains the LUMENIS product gate, baseline repairs and the 序 ecosystem contract/brand convergence.

GitHub Actions evidence at this exact HEAD:

```text
LUMENIS Product Gate          = SUCCESS
Verify LUMENIS-GGI Contract   = SUCCESS
```

The active cross-product contract is `lumenis-ggi-cross-product` v1.1.0 with fingerprint:

```text
68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f
```

Current formal ecosystem identities:

```text
序境 / LUMENIS              = Production Core / Production Truth
序蕴 / LUMENIS Intelligence = Shared Intelligence Assets
序衍 / LUMENIS Growth       = Research / Growth Truth
序枢 / LUMENIS Command      = Engineering Evidence / R&D control sidecar
```

Stable technical aliases/repository/package/API/DB identifiers are compatibility identities and must not be renamed merely for branding.

## 3. Canonical product model — already present, do not rebuild

Canonical production chain:

```text
External Data
→ Evidence
→ Canonical Data
→ Function
→ Metric
→ Truth Table
→ View Model
→ Visualization
→ UI / Report / Export
```

Canonical business chain:

```text
Source
→ Evidence
→ Event
→ Case
→ Insight
→ Decision
→ Action
→ Outcome
→ Evaluation
→ Learning Asset
```

These chains already exist in `README.md` and `AGENTS.md`. Do not create a second architecture or parallel truth to restate them.

Current four-domain ownership remains:

```text
CTH               Subject-first Commerce Operations
BMP               Brand/Market-first
Shared Capability Content & Creation / Evidence / Research / Evaluation / Learning / AI Enhancement
SYSTEM            Collector / Runtime / Scheduler / AI Gateway / DB / Security / Permission / Settings / Recovery / Observability
```

## 4. Current source/runtime facts — source-audited, not live-certified by this handoff

The latest source audit identifies these existing owners/contracts:

```text
scripts/start_production.ps1  canonical Windows launcher
app.py                        Flask application entry
run_supervised.py             process/health supervision
8201 /healthz                 core health target
9222 / 9223                   existing Resident Browser logical identities
experience_runtime.py         Experience V2 runtime binding
CTH-01 / AI-01                explicit bound-screen claims in audited source
evidence_chain.py             Evidence / Canonical lineage owner
xhs_cookie_bridge.py          XHS/RedNote controlled collector runtime
content_generation.py         research → generation → Evidence → Evaluation → human feedback
```

Audited dependency foundations include Flask/Waitress, APScheduler, requests/httpx/aiohttp, BeautifulSoup/lxml, Playwright, SQLite, tenacity and Alembic. `package.json` is Playwright/tooling-oriented; it is not proof of a React/Next/Vite production frontend.

Do not replace these with screenshot-derived or generic stack assumptions.

## 5. Screenshot architecture intake — disposition

The three user-provided screenshots were reviewed against the current repository. The reliably readable architecture principles that match current repository truth are already represented by the canonical chains, truth hierarchy, main/local/origin separation and completion semantics.

Two screenshots are too low-resolution for exact line-by-line extraction. Their unreadable package names, versions, commands or implementation claims were **not imported as truth**. See `08-AUDIT/SCREENSHOT-ARCHITECTURE-INTAKE-20260917.md`.

Rule for later higher-resolution re-ingestion:

```text
Screenshot statement
→ locate current owner/source/manifest/test
→ VERIFIED / ALREADY_COVERED / CANDIDATE / CONFLICT / UNVERIFIED
→ update existing canonical file when possible
→ create a new owner only when no valid owner exists
```

## 6. Current acceptance semantics

Use only these meanings:

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E evidence proves behavior
RELEASED    = required production/security/recovery/rollback gates pass
OPERATING   = real operation produces required live/scheduled evidence
```

At this handoff anchor, the remote product/contract CI is green. This does **not** by itself prove:

```text
8201 live workstation health = NOT VERIFIED by this handoff
Playwright live acceptance   = NOT VERIFIED by this handoff
RELEASED                     = NO NEW CLAIM
OPERATING                    = NO NEW CLAIM
```

Do not repeat the old CI #148 failure as current state: it belongs to the 2026-09-16 source-audit history and was followed by later repairs and a green current main Product Gate.

## 7. Codex resume protocol

On the workstation, first preserve and reconcile local truth:

```powershell
Set-Location D:\LUMENIS_REBUILD
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short --branch
git fetch origin
git rev-parse origin/main
```

Then:

```text
preserve unknown/uncommitted/unpushed valid work
→ compare local HEAD vs origin/main
→ do not repeat already-merged gate/contract/brand repairs
→ inspect exact active owner/caller/contract/tests
→ reuse/adapt/bind before rebuild
→ scoped tests
→ affected regression
→ runtime/E2E when required
→ evidence
→ coherent mainline commit/push
→ current main CI
→ next unresolved production-acceptance gate
```

Never reset/clean valid local work merely to match remote. Never treat local-only code as GitHub-complete.

## 8. Non-regression boundaries

Do not create a second Evidence, Canonical Data, Metric, Permission, DB, Runtime, API, Design System or Collector truth.

Do not make 序蕴、序衍、序枢 hard runtime dependencies of 序境. Do not share production databases across products. Do not allow AI/research artifacts to overwrite LUMENIS Production Truth automatically.

Do not weaken CI, delete legitimate tests, broaden quarantine or use `continue-on-error` to manufacture green status.

## 9. Historical documents

Dated takeover/handoff files before this `CURRENT` entry remain historical evidence only. They may explain provenance but must not be used as a current HEAD, current CI or current completion claim without re-verification.
