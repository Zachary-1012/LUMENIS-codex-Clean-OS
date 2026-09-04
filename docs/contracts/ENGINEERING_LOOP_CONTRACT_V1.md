# Engineering Loop Contract v1 — ZBC Consumer Boundary

**Date:** 2026-09-05
**Status:** contract seed / implementation pending source-fact verification

## Purpose

ZBC may be operated by an external engineering Agent Loop, but the production core remains authoritative for business rules, data integrity, and runtime safety.

## Allowed engineering loop phases

```text
READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW → TEST → VERIFY
→ HUMAN APPROVAL → COMMIT → PUSH
```

An agent may repeat the bounded inner cycle:

```text
INSPECT → PLAN → EXECUTE → VERIFY → REPAIR → VERIFY
```

only within an explicit iteration/time budget.

## Hard boundaries

The loop must not:

- silently delete or migrate production data
- bypass existing subject/business rules
- commit or push before human approval
- treat a passing unit test as proof of product correctness when functional/visual verification is required
- rewrite unrelated files
- introduce platform-specific behavior that breaks Windows/macOS portability
- replace source facts with documentation assumptions

## ZBC authority

Business/domain rules and data integrity remain authoritative in ZBC. Agent output is an execution proposal until verified.

## Cross-platform requirement

Agent orchestration must remain platform-neutral. Windows/macOS-specific behavior belongs in an adapter/tool layer, not in business logic.

## Integration rule

OSAI owns the generic engineering-loop primitive. ZBC consumes the contract through controlled tasks and existing test/runtime interfaces. No ZBC production-code integration is authorized by this document alone.

## Exit criteria for future implementation

1. Source-fact baseline confirms exact integration points.
2. Loop tests pass.
3. Regression suite passes.
4. Human approval gate is observable.
5. Commit/push is traceable to task, test, evidence, and lifecycle.
