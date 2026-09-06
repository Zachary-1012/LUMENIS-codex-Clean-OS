# Shadow Learning Protocol

Shadow Learning is a non-authoritative learning path. It observes or evaluates a proposed behavior without granting it production authority.

## Flow

```text
Research → Hypothesis → Candidate → Shadow → Evidence → Review → Verify → Promotion Candidate
```

## Rules

1. Shadow output cannot directly change production behavior.
2. The baseline behavior remains authoritative while shadow runs.
3. Every shadow run records the code SHA and evaluation context when code is involved.
4. Compare candidate output with the known baseline or expected result.
5. Record disagreements; do not silently overwrite them.
6. Promotion requires evidence appropriate to the capability and review under the three-repository contract.
7. If evidence is insufficient, status remains `shadowed` or `hold`.
8. When promoted, re-run destination-specific verification; success in SICI does not automatically prove Z-Brand or DDC compatibility.

## AI role

AI may generate hypotheses, summarize evidence, and propose promotion. It cannot self-certify its own hypothesis as verified.

## Exit criteria

A candidate can leave Shadow only as one of:

- `verified` — evidence supports the candidate.
- `hold` — evidence is insufficient.
- `rejected` — evidence contradicts the candidate.

Rejected candidates remain useful learning records and may not be silently deleted merely because they failed.
