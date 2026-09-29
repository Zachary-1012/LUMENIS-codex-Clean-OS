# ROUND 07 — local workspace Content Artifact binding

Base: `27f25d5ea7a3c3595955615b8b29c9aa57a3d8fb`.
Status: bounded owner integration; App E2E and J4/J5/J6 remain unaccepted.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Existing source/project packages now retain local workspace ownership explicitly
(`actor_id=null`, `principal_kind=local_workspace`, `principal_ref=workspace:local`).
The server-sealed principal is checked by existing Permission on import, render,
read, extracted-source reuse and after long-running work. Account manifests remain
unchanged and are not implicitly transferred. Exact source confirmation is consumed
only on successful import; general COMMIT remains disabled.

The user path under integration is select file -> confirm -> edit -> export ->
reopen -> revise -> retain earlier result. Failure cleans only the new unregistered
package; closure during rendering stops the encoder and preserves the previous
version, which is readable after legitimate workspace restoration.

## Frozen source and proportional verification

SHA256:
- `shared_artifacts.py`: `41eb05d009477efe12406b73d607681a04f5bb50e4bdf1ea1230b2036efd3bae`
- `tests/test_content_project_storage.py`: `4020fdb7b02b4d8ca0ef835a009a23b4168641ba6d0322aec73f15fce9acb257`

Four-file final regression: **70 passed in 16.58s, exit 0** (storage, artifact read
integrity, shared artifact flow, local principal). 593 observed SQLite calls stayed
in temporary DBs, zero production connections and no thread leak. Source stayed
stable before/after. Legacy `artifact_file_path` was separately checked unchanged.
Root also exercised the exact candidate through actual source/export API tests:
**35 passed in 25.33s, exit 0** across routes/execution/inspection. Those route
changes are a separate pending integration Batch in this commit.

## Real licensed media and process recovery

Evidence: `C:/Users/28049/AppData/Local/Temp/lumenis-local-artifact-20260930-tzy1egkw/`.
`local-acceptance.json` records actual loopback Flask principal, no account table,
no global COMMIT/bypass, confirmed sources, two 12-second MP4 revisions (360 frames)
and two 10-second WAV revisions, followed by independent-process reopen/hash
checks (exit 0). Inputs and license/source attribution are recorded there.

The first audio edit affected an effectively silent track; identical media hashes
are not proof of audible mixing. `audible-revision.json` records a third export
changing the audible rain track (gain 0.3, fades 0.4/0.6 seconds). Original media
SHA256 `649628717d5423efd50ebbc74f7644ca5241caa0114c11ca0405ebcb5c0716d8`
is preserved; revised media is
`eff03196890db14bffd135f39b9c25cc3fc7fd31bd4dfe4267bbb986f82b141b`.
Its first diagnostic script exited 1 while printing a nonexistent measurements
key after rendering; this is not counted as PASS. A separate process subsequently
verified the result, distinct hash, old bytes, no account table and zero production
connections, all assertions exit 0.

These are isolated engineering artifacts, not user App acceptance, art direction,
spoken podcast completion or copyright clearance. Rights remain unknown/demo-only.
No production DB, original user media, schema or external publishing changed.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: coverage unchanged and unverified.
COMMERCIAL OVERLAY IMPACT: release, operating and commercial readiness remain NO.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reuse the accepted renderer,
Artifact and Permission; no new dependency, store or account system. UI and real
business content acceptance continue through the same owners.
