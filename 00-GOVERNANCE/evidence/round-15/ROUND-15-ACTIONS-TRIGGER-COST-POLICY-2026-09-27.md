# ROUND 15 release-readiness policy evidence — Actions trigger cost

Status: `POLICY IMPLEMENTED / LOCAL_STATIC_VERIFIED`; ROUND 15 is not accepted. This is a bounded CI cost-control Batch under the existing release owner, not a new Gate or Round.

## Current evidence

- Product Owner confirmed GitHub Free `2,000 / 2,000` included Actions minutes used, with approximately five days to reset. This is user-provided billing evidence; repository-level billed-minute breakdown was unavailable to the current CLI token.
- GitHub Actions API inspection on 2026-09-27: LUMENIS had 727 September workflow runs, including 360 Product Gate and 23 App Gate runs. These are run counts, not billed minutes. On the latest source commit, Product Gate run `36264596744` had one job and zero steps, completing in two seconds; its timing API reported `total_ms=0`. App Gate run `36264596756` likewise completed before a test step. Hosted outcome: `HOSTED_CI = EXECUTION_LAYER_UNAVAILABLE / QUOTA_EXHAUSTED`; no product-test PASS or FAIL is inferred.
- The public Zachary-Skill repository had 897 September runs but standard public-repository GitHub-hosted runners do not consume the private-repository included-minute allowance. The three other currently visible private repositories had 184 (lumenis-command), 77 (Zachary-OS-AI), and 29 (global-growth-intelligence) runs. Exact billed minutes by repository remain unknown.

## Bounded change and acceptance

- Remove normal `main` push triggering from the existing Product and App workflows only. Preserve `pull_request` and `workflow_dispatch`; preserve every job, matrix, assertion, timeout, permission, blocking check, and honest Tier C status. No new workflow, test tier or release owner is created.
- Daily mainline work continues through the existing local full blocking Gate. At an explicit PR or Release / Internal Beta / RC milestone, run both full hosted Gates on the same candidate SHA after quota returns. Never rerun zero-step jobs merely to turn a red mark green.
- Local static acceptance must parse both workflow documents, assert no push/schedule trigger, retain PR/dispatch, compare the entire `jobs` subtree to the prior commit, and run the current constitution/governance validators on the exact candidate snapshot. Hosted execution and real-user E2E remain unverified until actually run.
- This policy does not change current L3 / ROUND 03 REWORK / global coverage NO / release NO. It does not interrupt the independent runtime, database, collector, video or frontend Batches.
