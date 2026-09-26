# ROUND 07 — local video timeline core, bounded source acceptance

Base: `777f0ae992fbed37d8c4c24c38a95a66664ce1bb`. This record concerns only the four source/test paths in this commit. It is **TESTED SOURCE / ROUND 07 REWORK**, not a user-facing video editor, automatic editing, accepted film quality, or ROUND 07 exit.

## Owner and scope

- Shared Content & Creation owns typed shot/narrative contracts, local media fingerprinting and an in-memory, versioned timeline. `shared_artifacts.render_local_video_artifact` remains the render/Artifact owner. The new timeline returns `status=blocked` for export and does not call that renderer.
- Input must be an explicit absolute local file. The helper hashes its bytes, probes actual video duration, retains rights as `unknown` and Evidence refs as empty, and does not expose the absolute path in its serialized contract. It neither downloads source media nor reads accounts/cookies, writes a database, publishes, or claims an approved AI edit.
- The candidate evaluation and learning files and their combined test remain unaccepted: their caller-supplied pass/approved values can appear as verified facts. They are excluded from this Batch and must be reworked through canonical Evidence/Permission/Evaluation owners.

## Verification on the exact clean candidate

- `python -m py_compile` on the four files: exit 0.
- `python -m pytest -q tests/test_video_editing_core.py tests/test_shared_artifact_flow.py tests/test_content_generation_parent_evidence.py`: **20 passed**, exit 0, no background-thread leak, with disposable `ZBC_DB_PATH` and no production DB access.
- `python scripts/audit_tools/verify_ai_native_constitution.py`: PASS, exit 0.
- A real, user-supplied local MP4 was fingerprinted and probed through an isolated `ffprobe` binary: duration **459.0 seconds**, asset ID `MEDIA-896e3bb32c6031b9`, timeline version 2, rights `unknown`, Evidence refs empty, export `blocked`; exit 0. The probe binary reported `n9.0.2-8-gb135b25c19-20260925`, SHA-256 `22A76F2C075F519F5C8488C03A27CEC49A945AA14B872229FB65C615F17C9A4C`. This is media-probe evidence, not a LUMENIS render or product E2E.
- Twelve separate candidate cuts were produced outside the product for the user's later viewing. Their existence does not validate this timeline's renderer or film quality; no raw media or binary is committed.

## 真实用户工作闭环验收 / REAL DELIVERY CARD

`REAL USER JOB`: content creator starts from media or an automatic proposal, manually trims/reorders or adjusts it, previews, exports and reviews a final film. `ENTRY`: Shared Content & Creation. `REAL INPUT`: authorized source media with rights and provenance. `END-TO-END PATH`: media identity → Evidence/Permission → timeline or proposal → user edits → render/Artifact → reopen/evaluation. `USER-VISIBLE RESULT`: playable final film and editable history. `FAILURE/RECOVERY`: rejected source, unavailable probe, renderer failure, unapproved rights, undo/retry. `EVIDENCE`: only the isolated tests and one real local probe above. `ACCEPTANCE ASSERTION`: **NOT MET**; no in-product render, UI, Canonical Evidence/Permission binding, automatic proposal execution, or user-reviewed output. ROUND 07 remains `REWORK`.

`COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO`; distribution licensing, rights and film-quality acceptance remain open. `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: none proved; Global Commercial Coverage=NO, Global Brand Coverage=NO, Guangzhou Taikoo Hui Reference Coverage=PARTIAL, `LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO`.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

Accessed 2026-09-26: [FFmpeg official filters documentation](https://ffmpeg.org/ffmpeg-filters.html) and [official FFmpeg GitHub source/license](https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md), with [official license guidance](https://ffmpeg.org/legal.html). The maintained FFmpeg project documents trim/concat primitives and LGPL/GPL configuration boundaries. Decision: **ADAPT** its local probe/tooling model under existing Shared Artifact owner; **DEFER** edited-timeline rendering and any product binary distribution until exact FFmpeg build/license, media-rights, Permission/Evidence, render and rollback gates are verified. No external project becomes Production Truth or a new media owner.
