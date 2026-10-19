# ROUND 06 — publication quality truth (bounded Batch)

Status: **TESTED SOURCE + LOCAL DATA CORRECTION; ROUND 06 remains REWORK**.

The existing note DataQuality contract now distinguishes a missing source
publication time from a malformed supplied time. It accepts the RFC 2822 time
format actually emitted by the existing Atom acquisition path. Missing remains
`valid=False` and counts as incomplete in Evaluation; malformed nonempty times
remain `error`. No capture time is substituted for source publication time.

At the `c81b1832` base, an exact read-only pass over the v18 local product DB
showed 165 quality errors: 135 public HTTP notes with no source publication
time and 30 Atom notes with valid RFC 2822 publication times. The other four
dated public HTTP notes were `ok`. The reclassification tool checks one-to-one
Raw↔Canonical identity, exact `VERIFIED` scope Evidence, and preexisting quality
parity before changing only derived quality status/score in one transaction.

## Verification

- `pytest --noconftest -q tests/test_data_quality_gate.py tests/test_public_http_article_extraction.py`: **19 passed** on the current source snapshot. Tests cover missing, malformed and real Atom date formats; the existing isolated insert path still passes.
- `python scripts/audit_tools/verify_ai_native_constitution.py`: **PASS**.
- Local product DB dry-run: **165 eligible** (`missing=135`, `ok=30`).
- Disposable snapshot apply: **165 updated**. Immediate second run: **0 updated**. Raw and Canonical quality matched (`missing=135`, `ok=34`), source publication times remained **34 known**, and integrity/FK checks passed.
- Actual local v18 product DB was backed up to `C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-publish-quality-backup-laaj4h97\monitor-before.db` before the same bounded apply. The post-write Raw and Canonical quality counts are both `missing=135`, `ok=34`; Raw/Canonical count remains 169, publication times known 34, relation assertions 219, `integrity_check=ok`, FK violations 0, orphan VERIFIED scope refs 0. The tool's source/lineage fingerprint matched before and after.

This corrects derived labels only. It does not fill 135 unknown dates, create
new Source/Evidence records, accept source rights, complete Global coverage,
prove a real user result or establish continuous operation. The local DB is
ignored by Git and is not published by this source Batch. Global Commercial
Coverage = `NO / NOT VERIFIED`; Global Brand Coverage = `NO / NOT VERIFIED`;
Guangzhou Taikoo Hui reference = `PARTIAL`; Full Universe, RELEASED,
OPERATING and COMMERCIAL_READY remain `NO`.

REAL DELIVERY CARD: a user can distinguish an unknown source date from a
malformed date in a real scoped result; the complete GLOBAL→FOCUS→result→Clear
path and user-visible quality binding remain unverified. COMMERCIAL OVERLAY
IMPACT: source rights and live operating cycles remain open.
