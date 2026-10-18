# ROUND 07 — Content source and rendered project Artifact integration

Base: `80c2ab040e596676e49c22e47f737f35e009b668`.
Accepted after independent local-principal slice `5f81f35e`.
State: TESTED / ENGINE_RUNTIME_VERIFIED_ISOLATED; J4/J5/J6 remain unaccepted.

## REAL DELIVERY CARD / 真实用户工作闭环验收

User job: preserve supplied media and an editable rendered project, reopen it,
revise it, and keep the previous version. This batch adopts the frozen candidate
into existing `shared_artifacts.py` and the existing Artifact table/repository.
No new schema, database or owner is introduced.

Source import binds actual bytes/name/actor/scope to Permission, rechecks before
registration and consumes the exact approval only on success. Denial, changed
bytes, registration failure and ID collision leave no new usable partial result.
Network share paths are refused before filesystem resolution. Source packages
and rendered projects require their exact scope and pass size/hash/archive
integrity checks on reopen. The legacy unscoped download path cannot read them.

Timeline export uses the accepted renderer, checks permission during encoding,
records parent revisions and preserves earlier versions. Source rights remain
unknown and this integration requires explicit demo acknowledgement. Publication
and source commercial rights are not granted by successful rendering.

## Current snapshot verification

Exact final source SHA256 (root verified):

- `shared_artifacts.py`: `0a250b06d1d9945cc7ab938a14388dab930d1cb231a2310c3ea17d189cc4de02`
- `tests/test_content_project_storage.py`: `8c1668e87478fb84946e6f0a2c5e3439b6109722c909fa0e6c3e7984d083574d`

Six-file final regression: **106 passed, exit 0**, 26.94 seconds, no thread leak.
Storage, artifact read integrity, shared artifact flow, timeline rendering,
audio timeline rendering and video editing core were exercised. All 464 observed
SQLite connections stayed in disposable temporary paths; production connections
were zero. Source hashes were unchanged throughout verification. Two UNC tests
failed before the missing candidate guard was restored and passed afterward;
no real network-share resolution occurred in those tests.

The original `artifact_file_path` implementation was retained byte for byte.
AST comparison retained 16 of 18 original definitions; only asset-path admission
and hiding new scoped artifacts from the old reader required adaptation.

## Real media and recovery evidence

Evidence directory:
`C:/Users/private-user-121dcc385158/AppData/Local/Temp/lumenis-artifact-final-20260930-b440187dfeee492ebd7d469d01fa2765`.

`acceptance-evidence.json` SHA256:
`e8534806e4eabc536c763a5c4c9d0019246b541866c6b5583db64db66c656f1a`.

Two previously sourced, license-recorded real media files were hash-checked and
rendered into two 12-second/360-frame MP4 revisions and two 10-second WAV
revisions. Reopen, volume revision, preserved original version, denied revision,
explicit retry and wrong-actor denial were exercised. A separate process reopened
all four versions, exit 0. All 472 observed SQLite connections stayed inside that
output directory. Inputs were unchanged. FFmpeg/ffprobe paths were process-only;
no global PATH or product configuration changed.

This is a disposable engineering identity, not live product account or local
workspace acceptance. The audio is environmental audio, not a spoken podcast.
Artistic quality and Product Owner USER_VERIFIED were not claimed. API execution
still needs to bind business Evidence; an execution ID alone is insufficient.

## Remaining boundaries

Open local principal ownership, source confirmation, execution/API binding and
App import/edit/export remain separate dependent slices. Existing workspace and
source data were not migrated. Recovery is verified here at the Artifact/engine
layer; cross-surface recovery and release remain J8 obligations.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no coverage claims change.
COMMERCIAL OVERLAY IMPACT: release/operating/commercial readiness remain NO.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reuse the already researched
FFmpeg renderer and frozen candidate in the current owner; no new library or
parallel editor. Developer FFmpeg distribution is not product-license acceptance.

Rollback: revert this exact source slice before dependent API integration;
preserve produced files and data, never delete source media or existing artifacts.
