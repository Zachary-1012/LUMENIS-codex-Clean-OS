# J1 / ROUND 06 — actual publication quality correction

Status: **TESTED SOURCE + LOCAL DATA CORRECTION; J1 PARTIAL; ROUND 06 REWORK**.
Base: `ffa628310a6403af35aaf922a0510191ad0c4135`. Source, this evidence and
CURRENT are co-published; resolve the containing commit from Git, not this base.

## Scope and result

The existing note contract v1.2 accepts fractional ISO publication times with a
timezone. Six real X notes used legal millisecond timestamps and were incorrectly
classified as errors. A seventh public HTTP note had no publication date and
retained an obsolete error label. No parser, required-field or severity gate was
weakened. Impossible dates and invalid offsets remain invalid.

The existing `scripts/reclassify_note_publish_quality.py` performed the bounded
correction. It checks v18, unique Raw/Canonical binding, matching VERIFIED scope
Evidence and matching quality before changing only derived quality status/score.
It compares source/lineage fingerprints, takes a SQLite backup, uses a transaction,
checks integrity/FK and reopens for readback. No Evidence, source text, timestamp,
scope or Canonical identity was edited.

## Current-snapshot verification

- Full `tests/test_data_quality_gate.py`: 16 tests passed, exit 0, using an explicit
  disposable seed outside the product repository. The bounded worker additionally
  ran the six publication/fractional cases, exit 0.
- Constitution gate and `git diff --check`: exit 0.
- Disposable real-data clone: seven changes (`ok=6`, `missing=1`); second dry-run
  zero eligible; source/lineage fingerprint unchanged, integrity ok, FK zero.
- Actual product DB: same seven corrections, second dry-run zero eligible;
  backup `C:\Users\28049\AppData\Local\Temp\lumenis-publish-quality-backup-kloh175a\monitor-before.db`.
  Reopened totals: Raw=267, Canonical=267, quality `ok=57`, `missing=210`,
  `error=0`; Canonical scope VERIFIED=264, UNASSIGNED=3; integrity ok, FK zero.
- Local existing supervisor restored on `127.0.0.1:8201`; `/healthz` returned
  healthy/database ok. This is service availability, not a business E2E pass.
- Existing scheduled maintenance task inspected: 195 configured public-baseline
  plans; recent evaluation cycles completed with 195 deferred, zero failed and
  zero refreshed. A deferred evaluation does not prove a successful source refresh.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

Job: inspect a source's real date and quality in a scoped commercial/brand result.
Input: existing real production notes. Path: source date → existing contract →
Raw/Canonical derived quality → existing API/ViewModel. Failure/recovery: bad date
remains error, absent date remains missing; backup, rollback source and idempotent
reopen are available. Product-visible quality and full Global→Focus→result→Clear
E2E remain **LIVE_NOT_VERIFIED**, so this is not J1 or Round acceptance.

The three unassigned Douyin records refer to **深圳湾万象城**, not **深圳罗湖万象城**.
They remain unassigned pending the correct identity path, rather than being assigned
to the user's reference subject incorrectly. Missing publication dates are not filled.

## GLOBAL UNIVERSE / DATA MATURITY IMPACT

Coverage and relation review remain open. Global Commercial Coverage = NO / NOT
VERIFIED; Global Brand Coverage = NO / NOT VERIFIED; Guangzhou Taikoo Hui Reference
Coverage = PARTIAL; FULL_UNIVERSE_READY, RELEASED, OPERATING, COMMERCIAL_READY = NO.
The ignored local database is not included in the source commit.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

ADAPT the actual X ISO timestamps through the current DataQuality owner; no new
dependency, quality store or truth layer. The approved whole-product research
report records official platform lifecycle and advertising/fact-checking methods.
Local correctness is improved here; source licensing and user/business acceptance
remain separate. COMMERCIAL OVERLAY IMPACT: no commercial rights or release claim.

Compute: GPT-6 Luna performed the two-file format/regression Batch; root reviewed
the diff, ran the full owner tests, isolated proof and production-safe correction.
No model supplied source facts or quality values to the database.
