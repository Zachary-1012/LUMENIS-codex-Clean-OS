# 序境 · LUMENIS

**面向商业运营与品牌市场的证据驱动工作平台。**  
An evidence-driven workspace for commerce operations and brand & market workflows.

> **Development status:** Active development. This repository is not evidence of a released, production-ready, or commercially validated product. Build success, green CI, available APIs, and stored artifacts do not establish end-to-end user acceptance.

## Overview

LUMENIS connects permitted source acquisition, traceable evidence, deterministic analysis, human decisions, versioned deliverables, and outcome evaluation in one product. AI is an **optional enhancement** to ordinary business workflows, not the authority for source facts or a prerequisite for core analytics.

The product has four planned entry surfaces, sharing one Product Core:

| Surface | Role | Delivery priority |
| --- | --- | --- |
| Public Website | Product information and approved public entry points | First |
| Web Workspace (Flutter) | Full business workflows | First |
| Desktop (Windows / macOS) | Native workspace | Subsequent |
| Mobile Companion (iOS) | Mobile review and continuation | Subsequent |

Android and Linux native clients are not active delivery targets. Linux remains relevant for servers and CI. A target is **not** a claim of current availability.

## Architecture

```text
Public Website / Web Workspace / Desktop / Mobile
                       |
                 Product Core
                       |
   +-------------------+-------------------+
   |                   |                   |
 CTH                 BMP                Shared
 Commerce            Brand & Market     Evidence / Database
 Operations          Workflows          Research / Reporting
                                        Content / Evaluation
                                        Learning / Saved Work
                       |
                     SYSTEM
   Runtime / Collector / Browser / Scheduler / Security
            AI Gateway / Agent Runtime
```

A business task follows a **conditional** evidence and delivery chain:

```text
Task purpose + actor + scope + permissions
  -> permitted Source -> Evidence -> Canonical Data
  -> deterministic functions and comparable metrics
  -> CTH decision or BMP / Shared deliverable
  -> human review -> versioned result -> reopen / revise / export
  -> authorized action and independently observed outcome (when applicable)
  -> Evaluation -> approved Learning (when applicable)
```

Read-only research does not require an external action or model training. External execution, publication, commercial effects, and model promotion require separate authorization and evidence. Unknown data must not be represented as zero; an internal status must not be represented as an external receipt.

## Project status and known limits

This README intentionally does **not** pin a supposedly live commit, service status, database count, model readiness, or completion percentage. Verify these against the actual revision and running environment.

Areas requiring independent product-level verification include:

- End-to-end source identity, publication timestamps, scope, permissions, and data coverage across acquisition paths.
- Backend response contracts versus Flutter screens; persistent actions, saved work, and reopening the same result.
- Legacy report/export/task/artifact routes versus current actor, scope, provenance, and authorization boundaries.
- Correct distinctions between observations, estimates, unknowns, internal actions, and externally confirmed outcomes.
- Media rights, playable/editable video and podcast results, runtime recovery, and owned-AI task quality.

These are **audit and verification areas**, not a statement that every affected path is currently failing. Consult the current source and reproducible evidence before assigning severity or declaring a fix.

## Repository guide

| Path | Purpose |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Sole execution router for coding agents and permitted changes |
| [Product Architecture](00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md) | Product blueprint and delivery priorities |
| [Source Owner Index](00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md) | Component ownership, cross-chain requirements, J1–J8 / U01–U25 |
| [Experience Constitution](00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md) | UX and surface-specific rules |
| [Real Delivery Overlay](00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md) | Actual user-result acceptance requirements |
| [Current handoff](00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md) | Dated project observations; reverify before use |
| [`app/`](app/) | Flutter workspace and client surfaces |
| [`website/`](website/) | Public website (Astro) |
| [`lumenis/`](lumenis/) | Shared product domains and system implementation |

**Authority:** The README is orientation, not an execution approval or an alternative to `AGENTS.md` and the named governance contracts. Historical reports and prior chat summaries are not current runtime evidence.

## Local development

The documented Windows workspace is `D:\\LUMENIS_REBUILD\\序\\序境`. Do not assume this path exists on other machines.

### Inspect the baseline (read-only)

```powershell
git rev-parse HEAD
git rev-parse origin/main
git status --short
git rev-list --left-right --count HEAD...origin/main
```

To refresh remote tracking information, use `git fetch origin main` only when network access and repository permissions are available. Protect existing uncommitted work; do not use `reset --hard`, `clean -fd`, or broad staging to manufacture a clean state.

### Start an authorized local runtime

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_production.ps1
```

The documented Core health endpoint is `http://127.0.0.1:8201/healthz`; the workspace route is `/workspace`. Their availability and business correctness must be checked on the actual running build. The website and Flutter application have separate development instructions under [`website/`](website/) and [`app/`](app/).

**Do not start collectors, training, paid resources, deployment, or production migrations merely by following this README.** Those operations require their own current approval, source-use permissions, and owner procedures.

## Verification and contributions

Product changes must be evaluated against the **same task, actor, scope, sources, artifacts, and revision** across Source, Runtime, Database, CI, and User Outcome. A successful compilation or HTTP response is not acceptance. Preserve existing history, original materials, private credentials, sessions, and database backups.

Before proposing a change, read [`AGENTS.md`](AGENTS.md), identify the owning component and callers, verify the current baseline, and describe the user-visible result and rollback. No issue, pull request, or documentation change independently authorizes model training, external collection, deployment, or spending.

## License

The repository includes the [Apache License 2.0](LICENSE). Third-party dependencies, source materials, datasets, model weights, fonts, and media may have **separate licenses or usage restrictions**. The repository license does not grant rights to those external assets.

---

**序境 / LUMENIS** · One product, one evidence chain, independently verifiable outcomes.
