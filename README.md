# 序境 / LUMENIS

> **Production Core · Production Truth Owner**
>
> Current phase: **PRODUCTION CONVERGENCE**. This repository contains the active production implementation, runtime, data contracts, Evidence, API, Permission, Metric, UI binding, tests and release evidence for 序境 / LUMENIS.

`README.md` is the human engineering entrypoint. It is not a historical progress log and does not by itself prove that a feature or release gate has passed.

---

## 1. What LUMENIS is

序境 / LUMENIS is an operational and brand/market product whose AI layer enhances — but does not own — production truth.

Canonical internal production chain:

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

The UI must expose useful context, facts, relationships, state, evidence, findings, risk, decisions, actions and outcomes. Internal production chains are not decorative page flows.

---

## 2. Product domains

### CTH · Commerce Operations

Subject-first operational domain for subjects, venues/projects, events, cases, risk, decisions and actions.

### BMP · Brand & Market

Brand/market-first domain for brands, competitors, creators/accounts, campaigns, market/communication performance, benchmarks, risk and evaluation.

### Shared Capability

Shared product capabilities including Content & Creation, Evidence, Research, Evaluation, Learning Assets and AI Enhancement.

### SYSTEM

Infrastructure and control plane: Collector, Runtime, Scheduler, AI Gateway, Database, Security, Permission, Settings, Recovery and Observability.

CTH and BMP may share Subject Context semantics and infrastructure, but their domain models, metrics, relationships and action semantics must not silently collapse into one model.

---

## 3. Authority and truth

When artifacts disagree, use this precedence:

```text
Current Production Source
> Runtime Reality
> Current DB / API / Permission / Evidence Contracts
> Tests / E2E / Production Acceptance
> Current Canonical Governance
> Experience V2 / current UI capability evidence
> Historical Handoff / Legacy Evidence
> Chat History
```

`IMPLEMENTED`, `TESTED`, `VERIFIED`, `RELEASED` and `OPERATING` are different states. A document or commit message never upgrades runtime state by itself.

---

## 4. Canonical closed loop

The approved Shared Capability × Collector production direction is:

```text
SYSTEM Collector
→ Source / Evidence
→ Canonical Content
→ Research
→ Learning Asset
→ Content Studio
→ Application Trace
→ Collector Tracking
→ Evaluation
→ Learning Version Update
```

Key invariants:

- Collector remains a single SYSTEM-owned Runtime capability.
- Upload / Import / API / Collector are acquisition adapters into one Production Truth.
- Tracking observations append `MetricSnapshot`; historical observations are not overwritten.
- `missing != 0` and future T+ performance must not be fabricated.
- AI may propose Pattern candidates but may not autonomously promote `Pattern → ADOPT`.
- Logged-in social Collector behavior is read-only; any future Publisher is a separate permission/effect capability.
- `RELEASED != OPERATING`.

Canonical detail: [`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`](00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md)

---

## 5. Repository orientation

Important entry areas currently present in the repository:

```text
README.md                       human product + engineering entrypoint
AGENTS.md                       coding-agent execution router
00-GOVERNANCE/                 canonical rules, release/handoff evidence
02-ARCHITECTURE/                architecture material
08-AUDIT/                       audit evidence
99-ARCHIVE/                     historical/archive evidence
.github/                        CI/workflow configuration
scripts/                        operational/startup/maintenance scripts
app.py                          current Flask application entry implementation
run_supervised.py               current process supervisor implementation
requirements.txt                current direct Python dependency manifest
package.json                    current root Node tooling manifest
.env.example                    non-secret configuration template
```

This is an orientation, not a claim that every root file is optimally placed. Do not mass-move production code by filename. Use dependency tracing, runtime ownership and tests before restructuring.

Canonical engineering standard: [`00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md`](00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md)

---

## 6. Engineering onboarding

### 6.1 Verify repository identity first

Never assume a developer-specific local path.

```bash
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status
git fetch origin
```

Confirm that the local repository points to:

```text
Zachary-1012/LUMENIS-codex-Clean-OS
```

Preserve unknown local changes until classified.

### 6.2 Python environment

Current root manifest is `requirements.txt`.

Windows example:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Do not commit `.env`, credentials, cookies, sessions or real production data.

### 6.3 Node tooling

The root `package.json` currently exists for Playwright-based browser/login/search tooling. Install it only when the task requires those scripts:

```bash
npm install
```

Do not assume the Node tooling is the main application runtime.

---

## 7. Configuration and data safety

`.env.example` is the configuration template. It still contains historical naming and multiple generations of configuration keys; production convergence must preserve behavior while consolidating canonical ownership rather than deleting keys by appearance.

Rules:

- no committed secrets or live cookies/sessions;
- no developer-machine absolute repository path as a production requirement;
- tests/staging must use isolated/disposable databases;
- no silent fallback from a test DB into the protected production DB;
- DB isolation and migration behavior require runtime evidence before being marked PASS;
- missing/unknown data states must remain distinct from numeric zero.

Configuration cleanup is a dependency-traced engineering task, not a text-search rename exercise.

---

## 8. Start and health

The current repository identifies the Windows production launcher as:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

The current launch chain includes the supervisor and `/healthz` checks. The launcher in the present main lineage also contains legacy machine-specific assumptions; therefore **do not hardcode a local path in new work and do not claim cross-machine startup verified until the portability gate is tested**.

Current health target used by the production launcher:

```text
http://127.0.0.1:8201/healthz
```

Startup acceptance is more than a live process:

```text
dependencies
→ configuration
→ launcher
→ application boot
→ supervisor stability
→ port bind
→ health
→ required runtime initialization
→ critical APIs / Experience
```

External browser/login/source availability should be reported separately from core application health.

---

## 9. Development workflow

For each change:

```text
Current Gate / Ticket
→ Dependency Trace
→ Reuse Existing Owner
→ Implement
→ Scoped Test
→ Neighbour Regression
→ Runtime / E2E when required
→ Evidence
→ Coherent Commit
→ Update State / Registry when required
```

Prefer reuse → adapt → bind → verify. Do not create a second DB, Evidence, Metric, Permission, Runtime, Subject Context, Design System or API truth to solve a local problem.

Do not start every task with a full repository rediscovery. Load only the files and canonical documents required by the active change.

Coding-agent rules: [`AGENTS.md`](AGENTS.md)

---

## 10. Testing and E2E

Use proportional testing:

```text
fast/static
→ targeted unit
→ affected integration
→ neighbour regression
→ representative/domain E2E
→ full regression at convergence/release gates
```

Do not run the complete suite after every leaf edit. Conversely, do not treat a small targeted test as proof of an entire domain.

Every important user-operable feature should eventually be traceable through:

```text
UI Entry
→ User Action
→ API / Service
→ Permission
→ Canonical Read/Write
→ Real Result
→ Evidence / Trace
→ Error State
→ Automated Test
→ E2E
```

`UI EXISTS`, `API EXISTS` or `TEST EXISTS` alone does not mean `FEATURE DONE`.

The canonical Feature Acceptance Matrix contract is defined in the engineering standard.

---

## 11. Production convergence DAG

The currently approved execution line is:

```text
G0  Repository Truth Convergence
→ G1  DB / Safety Foundation
→ G2  Source + Evidence Unification
→ G3  Collector Runtime
→ G4  Canonical Content Intelligence
→ G5  Research Engine
→ G6  Learning Asset Engine
→ G7  Write / Permission / Approval Closure
→ G8  Content Studio Production Binding
→ G9  Application Trace
→ G10 Performance Collector
→ G11 Evaluation → Pattern Validation
→ G12 Learning Version Update
→ G13 Shared + SYSTEM UI Binding
→ G14 凉子访谈录 60期真实 Acceptance Dataset
→ G15 Regression / Security / Recovery / E2E
→ G16 Release Gates
```

The 60-episode dataset is an acceptance dataset/configuration; its 20/20/20 cohort split must not become a universal hardcoded research rule.

Future performance windows stay pending/scheduled until real time and real source data exist.

---

## 12. CI, security and recovery

CI checks must distinguish:

```text
BLOCKING
ADVISORY
INFORMATIONAL
```

Syntax errors, required tests not executing, critical data-integrity/permission/E2E failures and P0 security failures cannot be hidden by `continue-on-error` or exception swallowing.

Production acceptance also requires appropriate evidence for:

- secret/credential handling;
- permission/approval boundaries;
- production DB protection;
- Collector/browser/session boundaries;
- critical error/retry/recovery paths;
- rollback lineage.

A recovery function existing in source is not proof that recovery has been exercised.

---

## 13. Documentation map

Use documentation by purpose instead of reading everything before every task:

| Need | Start here |
| --- | --- |
| Product + engineering onboarding | `README.md` |
| Coding-agent routing/safety | `AGENTS.md` |
| Human maintainability, E2E and release semantics | `00-GOVERNANCE/ENGINEERING-MAINTAINABILITY-AND-RELEASE-V1.md` |
| Shared Capability × Collector closed loop | `00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md` |
| Third-party/open-source inventory and replacement boundary | `00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md` |
| Point-in-time takeover evidence | `00-GOVERNANCE/handoff/` |
| Historical evidence | `99-ARCHIVE/` and historical governance/audit material |

Historical handoff/progress files must not be used as current runtime truth without re-verification.

---

## 14. Release state

This README does **not** assert `PRODUCTION_READY = YES`.

Production readiness requires evidence for the applicable gates, including repository integrity/human maintainability, canonical DB/configuration, regression, startup/health, domain and closed-loop E2E, permission, Evidence/Trace, truthful CI, security, recovery and rollback.

Use states precisely:

```text
IMPLEMENTED
TESTED
VERIFIED
RELEASED
OPERATING
```

If a blocking gate is not proven, treat production readiness as NO rather than inferring success from documentation or commit count.

---

## 15. Third-Party / Open-Source Components

This section is intentionally the **final README section**. Full canonical inventory: [`00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md`](00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md).

Current direct manifests show important non-self-developed components including:

| Area | Direct components observed | Boundary / replacement intent |
| --- | --- | --- |
| Web runtime | Flask, Werkzeug, Flask-CORS, Flask-Limiter, waitress | Keep business truth outside framework-specific code where practical |
| Scheduling | APScheduler, schedule | Runtime/scheduler boundary; replace through owned scheduling contracts |
| Data/import/export | pandas, openpyxl, xlsxwriter, beautifulsoup4, lxml | Data/parser/import-export boundaries |
| Document/report | python-docx, reportlab | Report/export adapters |
| Browser/Collector | Playwright (Python and root Node manifest) | Browser/Collector adapter boundary; never Production Truth owner |
| Runtime/monitoring | psutil | Runtime/process observation boundary |
| Network | requests, httpx, websocket-client, optional aiohttp | Network adapters |
| Configuration/utilities | python-dotenv, python-dateutil, PyYAML, colorama, tqdm | Utility/config/CLI boundaries |
| Resilience/logging | optional yyds-logger, tenacity | Logging/retry boundaries with fallbacks recorded in the manifest |
| DB migration tooling | Alembic | Migration tooling; production migration remains gated |
| Platform/runtime | Python SQLite stdlib, Windows PowerShell 5.1, Microsoft Edge in current launcher | Platform dependencies; portability must be tested, not assumed |

The repository has **not yet verified every shipped dependency license in the canonical register**. Entries that are not verified are deliberately marked `VERIFY_BEFORE_RELEASE`; license/attribution reconciliation is a release gate.

Future candidates such as OpenTelemetry, Langfuse OSS or Temporal are **not current dependencies merely because they are evaluated**. They may be adopted only when a real capability gap is proven and only behind a bounded LUMENIS-owned adapter/contract so they can later be replaced without replacing Production Truth.
