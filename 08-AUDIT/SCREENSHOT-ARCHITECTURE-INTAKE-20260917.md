# LUMENIS Screenshot Architecture Intake — 2026-09-17

> Status: **INPUT AUDIT / NON-AUTHORITATIVE UNTIL VERIFIED**  
> Remote comparison anchor: `main@5a14ff25b51303efb776126d0f6a3a5a936ec73f`

## 1. Purpose

This record maps three user-provided screenshots into the current 序境 / LUMENIS repository without promoting unreadable or unverified screenshot text into Production Truth.

The screenshots are requirements/reference input. Authority remains:

```text
Current Production Source
> Runtime Reality
> Current DB / API / Permission / Evidence Contracts
> Tests / E2E / Production Acceptance
> Current Canonical Governance
> README
> Historical Handoff / Screenshot / Chat
```

## 2. Reliability of the supplied images

The supplied image files are unusually narrow/low-resolution for long-form text. One image contains several readable architecture sections; the other two cannot be safely reconstructed line-by-line even after visual enlargement.

Therefore:

```text
exact readable statement + repo confirmation → may be recorded as verified/current
readable statement already in canonical docs → ALREADY_COVERED, no duplicate owner
partially readable package/version/command → UNVERIFIED_INPUT
unreadable text → NOT_IMPORTED
screenshot-only implementation claim → never upgraded to IMPLEMENTED/TESTED/VERIFIED
```

No OCR guess, inferred version number, package name or command from the low-resolution areas is treated as repository truth.

## 3. Screenshot concepts that are already canonical in the current repository

### Production chain — ALREADY_COVERED

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

Current owner locations: `README.md` and `AGENTS.md`.

Disposition: **no new architecture file; no duplicate implementation**.

### Business chain — ALREADY_COVERED

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

Current owner locations: `README.md` and `AGENTS.md`.

Disposition: **no duplicate model**.

### Git/main/local truth separation — ALREADY_COVERED

The readable screenshot references development/mainline concepts consistent with the current repository rules. `AGENTS.md` already requires explicit separation of:

```text
local main HEAD
local working tree
local unpushed commits
origin/main
```

Disposition: **keep existing AGENTS authority**.

### Completion/status semantics — ALREADY_COVERED

Current canonical status semantics already distinguish:

```text
IMPLEMENTED
TESTED
VERIFIED
RELEASED
OPERATING
```

Disposition: **screenshots may not collapse these levels**.

## 4. Current stack facts used to reconcile screenshot technology references

The 2026-09-16 source audit and current README identify these actual repository/runtime foundations:

```text
Python + Flask / Waitress
APScheduler / schedule
requests / httpx / aiohttp
BeautifulSoup4 / lxml
Playwright
SQLite
Alembic
tenacity
Windows-oriented supervisor/runtime
8201 core health target
9222 / 9223 Resident Browser/CDP identities
```

The current root Node manifest is Playwright/tooling-oriented. It is not evidence of a React, Next.js or Vite production application.

Any screenshot text suggesting a generic Docker/macOS/cloud/Node/frontend setup is therefore classified only as **candidate/reference** unless the current manifest/source/runtime proves it. The existing Windows production runtime must not be replaced by a generic stack assumption as part of this documentation intake.

## 5. Existing owners found in current source — do not rebuild

```text
scripts/start_production.ps1 → canonical Windows launcher
run_supervised.py            → supervisor / health / restart behavior
app.py                       → current Flask app entry
experience_runtime.py        → Experience V2 runtime
CTH-01 / AI-01               → explicitly bound Experience screens in audited source
evidence_chain.py            → Evidence / Canonical lineage
xhs_cookie_bridge.py         → controlled XHS/RedNote collector runtime
content_generation.py        → research/generation/evaluation/human-feedback flow
```

Screenshot requirements that belong to these areas must be implemented by adapting/binding the existing owner, not by creating parallel runtimes, databases or truth stores.

## 6. Ecosystem placement

The screenshots are about 序境 unless a statement explicitly describes another product. Cross-product capability must respect the active v1.1 contract:

```text
序境 / LUMENIS              → Production Truth
序蕴 / LUMENIS Intelligence → Shared Intelligence Assets
序衍 / LUMENIS Growth       → Research / Growth Truth
序枢 / LUMENIS Command      → Engineering Evidence
```

Allowed exchange is versioned contract/artifact/evidence-reference/validated-learning-candidate based. No shared production database, unrestricted cross-product writer or hard runtime dependency is created by this intake.

## 7. What was intentionally NOT imported

The following are not safe to assert from the supplied image resolution and were deliberately omitted as current truth:

- exact package versions visible only in blurred text;
- exact shell/install commands that cannot be read reliably;
- claims that a generic Docker or cloud deployment is the current canonical production runtime;
- exact CI result/status lines from screenshots when current GitHub Actions provides newer evidence;
- any feature/module name that cannot be matched to a current source owner;
- any claim that prototype/UI existence proves backend binding or production readiness.

If higher-resolution originals are later provided, ingest them incrementally through the same verification process rather than replacing current source truth.

## 8. Current newer evidence that supersedes screenshot-era status lines

At `main@5a14ff25b51303efb776126d0f6a3a5a936ec73f`:

```text
LUMENIS Product Gate        = SUCCESS
LUMENIS-GGI Contract Gate   = SUCCESS
```

This supersedes older screenshot/audit CI status for **current remote CI state only**. It does not prove live workstation runtime, release or operation.

## 9. Required future ingestion rule for Codex

When Codex encounters a screenshot/reference item not yet present:

```text
locate canonical owner
→ inspect caller/data/API/permission/evidence/test/runtime dependencies
→ classify ALREADY_COVERED / GAP / CONFLICT / UNVERIFIED
→ update the existing owner when possible
→ create a new component only for a proven capability gap
→ add proportional tests/evidence
→ preserve product and cross-product boundaries
```

Never create a duplicate subsystem simply because a screenshot uses a different label for an existing capability.
