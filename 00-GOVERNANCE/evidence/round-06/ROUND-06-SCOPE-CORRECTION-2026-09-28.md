# ROUND 06 — audited scope correction

Base before publication: 9ed4ca626ad7f949ce2ee555bf1520fc9c774a78.
Root reviewed a real data defect introduced by its broad Shenzhen search. The
three IDs 7563830274112359737, 7566484323726101775 and 7679739125724925227
name Shenzhen Bay MixC, while the requested CTH scope is Shenzhen MixC Luohu.
This supersedes their prior semantic VERIFIED claim, not their captured content.

## Existing owner repair

Existing Raw persistence now offers an explicit unassignment operation protected
by COMMIT permission plus exact DATA_IMPORT approval binding platform, domain,
entity, old Evidence, sorted IDs and reviewed change fingerprint. Evidence writer
can use the caller transaction; normal calls keep their existing transaction
ownership. Canonical correction is a separate signed transition; ordinary
verified upsert still cannot downgrade/rebind. No new schema/table/owner.

The correction appends signed Evidence, validates expected-old state, updates
Raw/Canonical scope metadata and adds a native correction reference atomically.
Normal verified refresh/direct Canonical upsert rejects a corrected identity for
that platform/product/domain. It does not infer a replacement entity.

## Actual result

- Production DB backed up by SQLite before mutation; private durable backup in
  ignored data/backups/scope-correction-20260928, content hash verified.
- Three records are UNASSIGNED, with cleared current Subject/BrandFocus/scope ref.
- Signed correction Evidence 358; original signed observation Evidence 292 is
  byte-for-byte preserved. Raw/Canonical non-scope fields and native source
  payloads remain unchanged; native adds only _lumenis_scope_correction_ref.
- Immediate repeat: zero changes, same correction Evidence.
- Fresh connection readback: consistent; integrity_check=ok; foreign_key_check=0.

## Proportional verification

Three focused correction tests PASS: denial, signed/idempotent unassignment,
atomic Evidence/Raw/Canonical/native rollback and direct refresh fence.
Forty affected scoped-Evidence, Canonical preservation and Evidence write-failure
regressions PASS. Exit codes 0; no thread leaks. Final four Python files parse;
staged bytes match the tested isolated candidate.
On a real product DB clone with the actual HMAC ring and no testing bypass,
unapproved correction was denied without source changes; injected second-item
failure rolled back the first-item updates and new Evidence; accepted correction
preserved source fields; old refresh and direct Canonical upsert were rejected.
These fault injections are engineering proofs, not real user E2E.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

Job: preserve captured material while withdrawing a mistaken venue association.
Entry: explicit reviewed local data-maintenance request and exact Permission.
Input: three actual source records and original signed Evidence.
Path: Permission -> expected-old check -> appended correction Evidence -> atomic
current scope change -> reopen/readback. Result: those records no longer belong
to Luohu; historical provenance remains visible. Recovery: transaction rollback
on any write failure; stable idempotency on replay. User-facing correction UI
and complete collection/workflow E2E remain NOT VERIFIED.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: correction prevents false coverage; it
does not complete Shenzhen depth or global coverage. COMMERCIAL OVERLAY IMPACT:
no readiness promotion. CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:
existing owner/source contracts inspected; no dependency/new architecture needed.
ROUND 06 REWORK; Full Universe/RELEASED/OPERATING/COMMERCIAL_READY NO.
