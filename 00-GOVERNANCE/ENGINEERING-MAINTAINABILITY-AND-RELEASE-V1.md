# LUMENIS Engineering Maintainability & Release Standard V1

> Status: APPROVED / CANONICAL ENGINEERING EXECUTION INPUT
> Product: 序境 / LUMENIS
> Scope: production repository engineering, maintainability, testing, release and handoff
> Principle: documentation never overrides current source/runtime truth.

## 1. Purpose

This standard makes the repository understandable and operable by a human engineer without relying on chat history or the original developer.

A feature is not complete because a page, route, service, schema or test exists. Completion requires a real user action to reach real execution, a truthful result/state, traceability, and appropriate tests.

```text
Human can understand it
→ Developer can change it
→ System can start it
→ User can operate it
→ Operation produces a real result
→ Result is traceable
→ Failure is honest
→ Tests prove it
→ Runtime can recover it
→ Release can roll it back
```

## 2. Authority

When sources conflict:

```text
Current Production Source
> Runtime Reality
> Current DB / API / Permission / Evidence Contracts
> Tests / E2E / Production Acceptance
> Current Canonical Governance
> README / AGENTS
> Historical Handoff / Progress Logs
> Chat History
```

Docs that disagree with current executable truth must be corrected, not used to override runtime.

## 3. Documentation hierarchy

Each class of document has one purpose:

- `README.md` — human onboarding, product/engineering entrypoint, quick start, current release state, documentation index and third-party summary.
- `AGENTS.md` — compact coding-agent router: authority, safety, when-to-read-what, execution/test/stop rules.
- `00-GOVERNANCE/*` canonical standards — architecture, ownership, contracts, hard rules and acceptance semantics.
- developer/operations docs — implementation, configuration, testing, deployment and recovery details.
- `00-GOVERNANCE/handoff/*` — point-in-time transition evidence; never permanent current-state truth.
- `99-ARCHIVE/*` and equivalent historical areas — historical evidence only.

Do not duplicate whole canonical rules across multiple files. Link to the owner instead.

## 4. Human-maintainable code standard

### 4.1 Naming

Production modules, classes, functions, variables, routes, tables and configuration keys must communicate responsibility. Do not add ambiguous names such as `new_final`, `utils2`, `temp_fix`, `copy`, `misc`, or `old_new`.

Historical names may be changed only with dependency tracing and tests; do not mass-rename by appearance.

### 4.2 Ownership and responsibility

Every active production capability must have an identifiable owner and boundary. Before moving or splitting code answer:

```text
Who owns this capability?
Who calls it?
Which contract does it implement?
What data does it read/write?
Which runtime uses it?
Which tests prove it?
```

Refactor God modules/functions incrementally only when tests protect behavior. Line count alone is not a reason to rewrite.

### 4.3 Dependency direction

Avoid direct coupling such as:

```text
UI → raw DB
Domain A → Domain B internals
Collector → business conclusion
AI → Production Truth mutation
arbitrary module → production DB
```

Prefer explicit contracts/services/adapters. Do not create a second DB, Evidence, Metric, Permission, Subject Context, Runtime or API truth to solve a local problem.

### 4.4 Error semantics

Forbidden:

- `except Exception: pass`
- silent fallback that changes business meaning
- fake success
- HTTP 200 that hides a failed business action
- `missing → 0`
- `UNKNOWN → healthy`

Errors should be classified, observable, traceable and recoverable when recovery is safe.

### 4.5 Comments and docstrings

Document WHY, invariants, safety boundaries, non-obvious contracts, external constraints and failure semantics. Do not narrate obvious code line by line.

### 4.6 Dead/duplicate code

Before deleting or archiving code, prove no relevant import, runtime registry, dynamic loading, route, script, test or production path still depends on it. Filename age or naming is insufficient evidence.

## 5. Configuration standard

Configuration must have a canonical owner and documented source. Production code must not depend on a developer-specific absolute repository path, committed secret, hidden DB fallback, or scattered magic ports.

`.env.example` must remain non-secret and reflect actually supported variables. Development, test and production semantics must be distinguishable.

Database isolation is a blocking safety concern: tests/staging must use explicit isolated/disposable databases and prove the protected production data path is unchanged.

## 6. Feature Acceptance Matrix contract

Every user-operable production feature must be traceable through this schema:

| Field | Meaning |
| --- | --- |
| Feature | Stable capability identifier/name |
| UI Entry | User-visible entry point |
| User Action | Concrete action the user performs |
| API | Route/contract invoked, if applicable |
| Service | Production owner/executor |
| Permission | Required policy/approval state |
| Data Read | Canonical reads |
| Data Write | Canonical writes/effects |
| Result | User-visible/business result |
| Evidence / Trace | Provenance/audit/application trace |
| Error State | Truthful failure/unknown states |
| Test | Targeted automated evidence |
| E2E | End-to-end evidence |
| Runtime Status | IMPLEMENTED / TESTED / VERIFIED / RELEASED / OPERATING or blocker |

These are invalid shortcuts:

```text
UI EXISTS != FEATURE DONE
API EXISTS != FEATURE DONE
TEST EXISTS != FEATURE DONE
```

A feature closes only when:

```text
User Action
→ Real Execution
→ Real Result
→ Correct State
→ Evidence / Trace
```

## 7. Domain E2E expectations

Important capabilities in CTH, BMP, Shared Capability and SYSTEM should cover, where applicable:

- happy path
- empty state
- missing/unknown state
- permission denied/pending state
- failure path
- recovery path

Representative domain chains:

```text
CTH: Subject → Data → Evidence → Insight → Decision/Action → Result
BMP: Brand/Market Context → Content/Account → Metric/Evidence → Analysis → Result
Shared: Source → Research → Learning → Content Studio → Application Trace
SYSTEM: Collector → Runtime → Permission → Health → Recovery
```

Canonical cross-domain closed loop is owned by `SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md` and must not be duplicated here.

## 8. Test strategy

Use proportional testing:

```text
fast/static check
→ targeted unit
→ affected integration
→ neighbour regression
→ representative/domain E2E
→ full regression at convergence/release gates
```

Do not run the entire suite after every leaf edit. Widen tests when a shared primitive or cross-domain contract changes.

Never delete, skip or weaken a legitimate test merely to make the build green. Unknown skips are not acceptable at release.

## 9. Runtime, observability and recovery

Important requests/jobs/actions must be observable enough to identify owner and failure point. At minimum include the critical request/runtime job, collector run, permission decision, write/effect, retry/recovery and evaluation paths when those capabilities are active.

Recovery requires execution evidence; the existence of a recovery function is not proof that recovery works.

## 10. CI truthfulness

Classify checks as `BLOCKING`, `ADVISORY` or `INFORMATIONAL`.

Blocking failures include at minimum syntax errors, required test infrastructure missing, required tests not executing, production data-integrity failure, critical permission failure, critical E2E failure, and P0 security failures.

Do not use `continue-on-error`, skipped checks or swallowed exceptions to manufacture a green production gate.

## 11. Third-party/open-source boundary

Important non-self-developed components must be registered in `00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md` and summarized at the bottom of `README.md`.

Prefer:

```text
LUMENIS Contract
→ Adapter
→ Third-party implementation
```

Avoid vendor-specific business logic spread throughout the product.

A third party must not silently become the owner of LUMENIS Canonical Data, Evidence, Metric, Permission or business truth. Track license, usage scope, integration boundary and replacement plan. Unknown license status is a release gate, not permission to guess.

## 12. Release semantics

Use these states precisely:

- `IMPLEMENTED` — code exists.
- `TESTED` — scoped automated tests passed.
- `VERIFIED` — runtime/E2E evidence proves the intended behavior.
- `RELEASED` — required production, regression, security, recovery and rollback gates passed.
- `OPERATING` — real operation has produced required live/scheduled evidence.

`RELEASED != OPERATING`.

For the Collector/Shared feedback loop, OPERATING requires real scheduled outcome evidence; future T+ performance must not be fabricated.

## 13. Engineering release checklist

Production acceptance should not be declared unless applicable gates are evidenced:

```text
Repository Human Maintainability
Canonical DB / Configuration
Full Regression
Production Startup / Health
CTH E2E
BMP E2E
Shared Capability E2E
SYSTEM E2E
Closed-loop E2E
Permission / Approval
Evidence / Application Trace
CI Truthfulness
Security
Recovery
Rollback
README current
AGENTS current
Third-party register current
```

Any blocking gate that is not proven keeps `PRODUCTION_READY = NO`.

## 14. Efficient agent execution

This standard is model-neutral. Agents should use progressive disclosure, minimal context loading, reuse-before-rebuild, proportional tests and persistent execution.

Do not start by rediscovering the whole repository. Read only the material needed for the active gate, follow dependencies, batch coherent fixes, run scoped tests, and expand validation only when the change warrants it.

Large file count, long tests or context size are not themselves product blockers; they are reasons to scope work efficiently.
