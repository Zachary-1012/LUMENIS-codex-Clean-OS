# ROUND 07 — Artifact file read integrity

Status: TESTED SOURCE + ACTUAL MEDIA READ PROOF / ROUND 07 REWORK.

Against current main `2937d9c2d732784293bbf305f601e416798970d9`, the existing `shared_artifacts.py` registry reader was extended only at `artifact_file_path`: a root-confined file must match its registered positive byte count and SHA-256 before its Path is returned. Invalid legacy metadata and changed/unreadable files fail explicitly without rewriting the record. No second table, store or Permission path was added. The protected local audio rendering edits in the same working file were excluded from this Batch and remain local.

Sol replayed 11 targeted integrity tests and 22 neighboring Artifact/report tests on an explicit disposable DB seed. In an independent runtime proof, the actual 179,512-byte MP4 from the accepted renderer was registered solely as isolated test setup, read back, altered by one byte without changing file size, rejected, restored in the test copy and read back again. The original media stayed unchanged. The test's 13 DB opens were guarded to its disposable DB; production DB opens were zero. Root receipt: `C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-root-artifact-integrity-20260928.json`.

The direct isolated registration did not pass real Actor, Permission, approval or Effect Fence and is not product Artifact-write acceptance. The reader still returns a Path, so a later streaming caller must handle mutation after this check. Scoped authorized write/reopen, Evidence, rights, UI, review, evaluation and real-user E2E remain open.
