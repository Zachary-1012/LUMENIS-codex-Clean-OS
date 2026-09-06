# Three-Repository Validation Rules

> Additive rule set under the existing DCC-owned system matrix and immutable three-way feedback principle.

## Authorities

| Repository | Truth it owns |
|---|---|
| Z-Brand-Core | business/domain and production applicability |
| Development-Command-Console | engineering control, permissions, verification and Evidence |
| SICI-Core | mobile interaction, device constraints and user-facing workflow |

## Promotion gate

A cross-repository capability is **not reusable merely because one repository passes**.

```text
Candidate
  ↓
Origin Evidence
  ↓
Destination Adaptation
  ↓
Destination Test
  ↓
Three-party evidence review
  ↓
Verified / Hold / Rejected
```

At minimum, each affected repository must provide an explicit status. A repository not affected by a candidate must be marked `not_applicable` with rationale; it must not be silently omitted.

## Non-negotiable rules

1. No AI confidence is Evidence.
2. No README claim is runtime verification.
3. No successful test in one repository proves another repository's compatibility.
4. Shared capability has one owner and explicit adapters.
5. Failed verification remains visible as learning.
6. Production authority stays with the repository that owns the relevant truth.
7. Permission escalation is never inferred from learning or verification success.
8. Promotion requires an auditable Evidence reference and appropriate review.
9. Any change that crosses repository boundaries must re-check the DCC-owned unified system matrix.
10. The rules may be clarified or strengthened, but not weakened or bypassed.

## SICI-specific constraint

The browser/mobile client may collect and present evidence, but cannot self-authorize privileged Runtime, deployment, or production release operations.
