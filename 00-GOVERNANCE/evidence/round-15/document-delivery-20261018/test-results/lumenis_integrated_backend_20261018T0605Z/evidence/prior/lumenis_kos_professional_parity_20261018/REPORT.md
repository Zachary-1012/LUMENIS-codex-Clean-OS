# Professional-account incremental-history parity repair

Scoped development only; not integrated, deployed or customer-accepted. The working source is `[LOCAL_WORKSPACE]/lumenis_development_20261018/source`. Frozen changed paths, predecessor hashes and current hashes are in `changed-files.json`; exact diffs are in `diffs/`. This stage changes kos_professional.py, kos_ops.py, a two-line resource-limit catch in kos_routes.py, and one new dedicated test file. Its route predecessor is the preceding frozen profile repair; its other existing predecessors are the 2248 candidate. It does not supersede or discard that stage's evidence.

## Reproduced failures
`results/baseline-failures.log` preserves two original failures:
1. Import date 1, then date 2: reading metrics loses date 1 because only the newest batch is projected.
2. Configure account A, then create 201 revisions for account B: account A disappears because the newest 200 versions are sliced before deduplication.

## Repair and original-main meaning
Main kos_professional.import_metrics used account/date replacement and retained dates omitted by subsequent imports. The scoped ledger retains actor, BrandFocus, platform and account isolation; this repair projects the newest entire row for each date from all verified versions. It never sums successive revisions. Omitted dates remain, explicit zero remains zero, missing fields become null rather than borrowing a superseded value or synthesizing zero. Dates are normalized for duplicate identity and range comparison. Each result row carries its producing operation version/id/hash and actual recorded import time. All metrics remain USER_DECLARED / official verification NOT_VERIFIED.

Account status now selects the newest version per account from complete verified history, rather than from the first 200 revisions. Existing legacy unscoped tables remain excluded. The existing ledger still validates digests, full parent chains and current actor/scope authorization. Payload platform/account identity is verified before projection.

No delete/withdraw API was invented. Import omission does not delete an older date, and disabling a professional account preserves its history. Explicit date deletion is not represented by this existing contract; the response states that semantic boundary. Existing writes, exact-resource approvals, transaction-time enablement checks, idempotency and immutable revisions are unchanged.

## Bounded complete-history option
kos_ops.read_scoped_operations adds an explicit boolean `complete_history=False` option. Default visible limits and behavior are unchanged. Complete reads iterate a database cursor, use exact action/author SQL selection, and refuse more than 10,000 candidate rows or 16 MiB of ledger note text. The error is `KOS_OPERATION_HISTORY_RESOURCE_LIMIT`; the professional HTTP boundary returns 503 with no partial metrics/accounts. It never silently returns only the first 100/200 versions, and does not fetch all raw rows into memory. Hash/parent-chain checks still run before a response can escape.

## Verification
- Two original failures preserved; no existing test removed or changed.
- Focused same-version suite: 78 passed, including the prior profile/unknown-state suite, professional workflows, private operations, scoped execution and dispatch revocation/recovery (`results/final-affected.log`).
- Dedicated cases include day retention, exact-day correction, replay, older date beyond 100 batches, account beyond 200 revisions, both resource budgets, invalid history flag, other-scope isolation and tampered older chain rejection.
- Actual loopback HTTP tests traverse existing approval challenge -> exact confirmation -> two separate imports -> replay -> date query -> resource-limit error -> scope disable -> recovery. Receipts: `results/professional-http-receipts.json`. These use generated synthetic data and isolated real SQLite/Flask, not live platform/customer data or product acceptance.
- AST/bytecode compilation passed. Ruff remains NOT_RUN because it is absent from the existing environment; nothing installed/upgraded.
- Same existing Python 3.12, isolated DB/artifacts/tmp/logs only, network/model guard active. No platform network, external campaign effect, production DB, user-computer, frontend or GitHub operation.

The final same-version wide KOS/BMP run is **339 passed, 7 failed** (`results/final-full.log`). Those seven failures match the preceding stage and untouched 2248 baseline exactly; the historical baseline proof remains in `[LOCAL_WORKSPACE]/lumenis_kos_parity_20261018/results/preexisting-2248-failures.log`. Reviewer verdict remains separate; these failures must not be relabeled PASS. Full KOS/BMP/all-product completion, saved-business-result adoption and local/front-end acceptance remain OPEN; all original 19-item and R/J/U/195G scope is retained.
