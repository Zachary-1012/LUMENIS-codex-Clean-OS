# 2026-10-13 — bounded reuse diagnostics source integration

## Exact input and authority

Direct Product Owner instruction in the current conversation authorizes execution
of `LUMENIS_Reuse_20261013(1).zip`, SHA-256
`79ea56ad35ae1acb2e2953c2229a6d428a2503d7c7a41f3f6ddbc6867b946329`.
The archive's CODEX_EXECUTION is a task input, not a replacement for AGENTS,
Collector/Build/Shared ownership or product acceptance. Original package: 21
manifest hashes verified and 20 package self-checks passed. Original read-only
review_guard returned SNAPSHOT_MATCHES_REVIEW before source writes.

Fresh initial baseline (2026-10-13 02:32 +08): primary HEAD
`dded08273de58ddc5a010b55375ec437764881f7`, branch
`codex/product-reuse-experience-20261011`; independently verified GitHub main and
origin/main `3b6adcb999a2e43a7eefad711118cbad17153869`; ahead 5, behind 0;
172 pre-existing dirty paths, staged 0, stash 4. Six exact target preimages
matched the archive. The publication branch `codex/reuse-diagnostics-20261013`
is isolated on that current main, not a promotion of the primary dirty tree.

## Actual source and impact

| Existing owner / boundary | Exact implemented change | Preserved behavior |
| --- | --- | --- |
| SYSTEM Collector | response_shape.py; compatible final AdapterResult.diagnostics field; current Douyin requestfinished callback and upper CollectionResult metadata binding | Same response read once; no new request, source, account, provider or cursor execution; original notes and business completeness remain separate |
| Diagnostic boundary | Per invocation at most 8 summarized objects, 4 unique shapes, default per-shape budgets, aggregate <=64 KiB; independent typed validator | Scalar values never emitted; counters/types only; explicit truncation; malformed optional diagnostics cannot change business status |
| Existing native build tooling | Preserved build_windows.ps1 plus optional StaticImportDiagnostics/PythonExecutable/DumpbinPath; two single-file helpers | Build failure never calls inspection; unavailable tools do not change build success; no install/PATH change/target execution/DLL loading |
| Existing third-party record | Append-only MIT provenance and full upstream/delivery notices | Root Apache-2.0 unchanged; no runtime dependency or upstream app copied |

The two existing Douyin files already contained necessary local improvements
not yet in main: stop/retain observations on authentication/risk/network failure,
exact-detail identity, optional native views/time, search-summary preservation and
truthful unfinished-detail states. Their complete diffs were separately inspected
and validated because CODEX_EXECUTION section 1.4 explicitly requires preserving
them. They are included as reviewed prerequisites; no other unreviewed collector,
canonicalization, browser, database or owner dirty work is promoted. The original
main test assertions remain, with an explicit exact-detail fixture and bounded
search/risk/metric regression additions. Full local downstream tests remain local.

## Verification, explicitly separated

| Layer | Observation and limit |
| --- | --- |
| SOURCE | Implemented in protected primary workspace and isolated publication branch. This record does not assert main merge or loaded runtime. |
| TEST | Before edits: 56 related local adapter regressions passed. Final local slice: 82 passed. Isolated main-based publication slice: 59 passed. These are different scopes, not additive product acceptance. |
| BUILD TOOL TEST | Existing 5 Windows build-helper regressions and 5 new optional-stage regressions passed locally and in publication worktree. They use synthetic Flutter output, not a real current-source application build. |
| STATIC | Changed Python compilation, Ruff F checks, PowerShell parse and exact diff whitespace checks passed. AI-native constitution gate passed before publication. |
| CI | Current branch/PR Actions and required check state must be read after push. Local tests are not remote CI. |
| RUNTIME | No service/app was restarted or deployed. Real platform acquisition, same authorized task recovery, and new-source app build/launch: LIVE_NOT_VERIFIED. |
| DATABASE | No production DB access/write, migration, schema or separate Evidence store. Diagnostic metadata is not Canonical fact. |
| USER OUTCOME | The operator used the actual helper to inspect one existing EXE statically. Actual acquisition-diagnostic recovery inside a real authorized task remains unverified. No Job/Release/Operating/Commercial-ready promotion. |

Isolation used an empty temporary seed DB, disabled external network through a
Python audit boundary, no automatic pytest plugin loading, and bounded subprocess
execution. Failure evidence is retained: the first new-test import-path failure,
a publication fixture mismatch, and the audit runner's path-assertion failure.
The fixture mismatch was corrected without weakening the original main assertions;
no failing test was relabeled as real E2E or silently skipped to obtain green.

## Real static artifact observation

2026-10-13 03:07 +08, actual Microsoft dumpbin /imports against the existing
`app/build/windows/x64/runner/Release/lumenis_app.exe` returned 20 direct imports.
Before/after EXE SHA-256:
`43119bce300a5d265f1b0a2b0e3c34c53dfa5cddab564426fabd98ce458f0a88`.
Transcript SHA-256:
`060fa703c70b8cd0f67f59f88891c186668f8ac2bf2afe57831c2e8eae4576c9`.
The helper returned IMPORTS_OBSERVED with runtime_verified=false,
dependency_resolution_verified=false and current_source_build_verified=false.
System DLL/API-set names are not assumed missing merely because they are not
beside the EXE. No target process was started and no imported DLL was loaded.

## Open boundaries and existing-owner continuation

The next already-authorized acquisition may validate same-task/run/source/actor
continuity and later reopening of the failure diagnostic. This batch does not
start another collection or access any protected identity. Existing result/Evidence
persistence must consume the bounded derivative metadata under the current C5/C6
contract; no durable diagnostic readback is claimed. App packaging and actual
runtime dependency resolution stay separate from static import discovery.

PR #21 governance cleanup is independent of this source branch. Its later head
`44475ef0713cabc283aade7256ba27d337437021` does not merge or verify this reuse
change. The primary Git index remains unchanged by this integration. Four other
pre-existing screen files changed concurrently in another authorized workstream;
this task did not overwrite those files. Source edits, source publication,
review, required checks, main merge and live acceptance remain separate.

Rollback is the exact reviewed source delta (or a reviewed revert after merge),
never reset/clean/restore of the protected primary tree. Original file preimages,
failed attempts, final checks and hashes remain in the local audit receipt.

## Publication source hashes

These are exact worktree file bytes before Git newline normalization. Commit/blob
identity and PR readback are authoritative for published bytes.

| Path | SHA-256 |
| --- | --- |
| `lumenis/adapters/base.py` | `2c298efef886a02b2efe3cc0d80dbbb30e99570dc19361b6e36beb2b22b30ed4` |
| `lumenis/adapters/douyin.py` | `ba9f2461fd3a05aee0477e407509d2e08dbe466dd282efdd39fec7bd53014675` |
| `lumenis/system/collector/adapters/douyin.py` | `f0526316ce258320687918ca99525898432fd2149c007bb24bc171521b41c2de` |
| `THIRD_PARTY_NOTICES.md` | `bf5a1dbae2a565f0aed86d98078891af3210316611e495bf3694450b42b834bb` |
| `00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md` | `b5cbef9e7c1c42f4f3376e71be2a30fab31238f02eae4abcfd1591f720e20e7f` |
| `lumenis/system/collector/adapters/response_shape.py` | `ac2346d0d47c0ed75af0992f03f4deca2b1e4c01bdd94c6ee925914e1f55b14c` |
| `scripts/audit_tools/binnexus_imports.py` | `9fd4e2cc9741240b0efe74bf809061047e7439ee9618ef8ede67125545cd9853` |
| `scripts/audit_tools/dll_imports.py` | `2ea7f5c447467bb97e10f0d4a84a82d93b368b0e6a9c85305668c9bbbaefcf10` |
| `vendor/lumenis-reuse-notices/Dvurechensky-MIT.txt` | `c45d598b36f543843a0f3fdddd6747b209697901e6308161832bd339e6e31a4e` |
| `vendor/lumenis-reuse-notices/Delivery-MIT.txt` | `3535c4e9dba25f4393a1ed255e438ec95b2facb418e17fdee959d4a0eb7335db` |
| `app/tool/build_windows.ps1` | `a69ba2ddc83bbf3b6bb445c4d5c8ee00c828f317fdbeea42c5a549cfe8f18242` |
| `tests/test_response_shape_diagnostics.py` | `e87b53a8fac2fde29b3a440f8ad92811cf23d19bb86b7b011ba634312f0ceeba` |
| `app/tool/test_build_windows.py` | `9db7bad292f26b987c521e7696b76324951a6be4843e0f1fec0a99ac03853ce5` |
| `app/tool/test_build_windows_static_imports.py` | `5ee2783a28afcf1c05b251cce0298a119f31b474cdc893fbc0e6dff67ac682b5` |
| `tests/test_douyin_search_capture_page.py` | `b627cc2e10a89b45508fa298abd0a2b2eecb39f5785720d0dcb00b5482ee09a4` |

## Fixed verification receipts

| Check | Log SHA-256 |
| --- | --- |
| local-adapter-final | `7627c2af561e928b43a556496e9351be7693a8d2f13faff80734e0cf6e90c8b3` |
| publication-adapter-corrected | `0546992af3018025916b3c9411a779c336f100e4d7fb8c58c0ac66c4ffde20a6` |
| publication-test_build_windows | `3a392249314dd4ba2f3539eba8d510755cbc80851668f87619f0c520b7fb4fbc` |
| publication-test_build_windows_static_imports | `bf22ee64d0e23f1b3573c5542320be87e85ab24b3d5e8ea281c5e01c6ad4a610` |
| publication-constitution | `e30d82c88700d83e334b9d746d862749bb960251f028c8d76450046dcbfcaeca` |
