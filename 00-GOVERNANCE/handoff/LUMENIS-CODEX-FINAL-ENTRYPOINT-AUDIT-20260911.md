# LUMENIS / 序境 — Final Codex Entrypoint Audit

Date: 2026-09-11
Status: **READY_FOR_CODEX_EXECUTION**
Production Ready: **NO — not asserted by this handoff**

## Canonical entrypoint

```text
Repository: Zachary-1012/LUMENIS-codex-Clean-OS
Branch: handoff/frontend-gpt-v24-20260911-final
Base: main
```

`handoff/frontend-gpt-v24-20260911-codex-ready` is retained only as a historical PR alias and has been fast-forwarded to the exact same converged commit/tree as `final`. Codex must use `final` as the canonical entrypoint.

## Source package baseline

```text
Package A entries: 1331
Package A required non-media: 642
Package A media registered-only: 689
Package A SHA256: c4bbb60c3e21db88d3f271ff63359dd845e052aaf69911aa554bb1a3fdcf202c

Package B entries: 273
Package B required non-media: 40
Package B media registered-only: 233
Package B SHA256: 0e45ab95481de42462b291917cbbc4452e1b07f2dafb7a055776f3bf5c26d4a9

TOTAL_SOURCE_RECORDS: 1604
NON_MEDIA_EXPECTED: 682
MEDIA_EXCLUDED: 922
WOFF2_REQUIRED: 56
```

Package B provenance remains independent even where its 273 records are byte-identical to Package A `03_LEGACY_DELIVERY_EVIDENCE`.

The historical `111-file` import standard is **SUPERSEDED**.

## Remote cryptographic tree proof

The 682-file local import tree was rebuilt as Git objects from the audited closure ZIP and compared with GitHub remote tree objects.

```text
LOCAL/REMOTE HANDOFF TREE:
fe5d2a0e4a1ae8c1435fa3105b80b87baeea4389

PACKAGE_A_ALLFRONTEND LOCAL/REMOTE TREE:
4e5abb0fd2fbe167d20387aaa5c38c8d625305bc

PACKAGE_B_LEGACY_EVIDENCE_ONLY LOCAL/REMOTE TREE:
aa78048b53ad1cea79157959091317cb87fbd6a2
```

All three tree SHAs match exactly. Because Git tree identities include every path, mode, child tree and blob SHA, this proves the remote 682-file handoff tree is byte-for-byte/path-for-path identical to the audited local import tree. Local REPO_PATH_MAP verification also found zero size/blob/path mismatches across all 682 required records.

## Acceptance gates

```text
PACKAGE_A_BASELINE = VERIFIED
PACKAGE_B_BASELINE = VERIFIED
LEGACY_OVERLAP = 273/273 VERIFIED
NON_MEDIA_EXPECTED = 682
NON_MEDIA_PRESENT = 682
NON_MEDIA_MISSING = 0
MEDIA_EXCLUDED = 922
UNEXPLAINED_EXCLUSIONS = 0
WOFF2_REQUIRED = 56
WOFF2_PRESENT_IN_VERIFIED_TREE = 56
REMOTE_PATH_MATCH = PASS
REMOTE_SIZE_MATCH = PASS
REMOTE_BLOB_SHA_MATCH = PASS
SECRET_SCAN = PASS
MAIN_UNTOUCHED = PASS
README = FINAL
AGENTS = FINAL
CODEX_ENTRYPOINT = VERIFIED
SOURCE_IMPORT_STATUS = COMPLETE
READY_FOR_CODEX_EXECUTION = YES
PRODUCTION_READY = NOT ASSERTED
```

## Manifest interpretation

The closure evidence uses compact field names in `FINAL_SOURCE_MANIFEST.json` (`package`, `ext`, `git_blob_sha1`, `decision`) plus `MEDIA_EXCLUDED_MANIFEST.json` and `DUPLICATE_CONTENT_MAP.json`. For final acceptance these map canonically as follows:

```text
source_package        <- package
filename              <- basename(rel_path)
extension             <- ext
git_blob_sha          <- git_blob_sha1
included / excluded   <- decision
exclusion_reason      <- MEDIA_EXCLUDED_MANIFEST.reason
duplicate relationship<- DUPLICATE_CONTENT_MAP joined by SHA-256 + Git Blob SHA
```

No completeness decision may be made by filename alone. Duplicate identity is SHA-256 + Git Blob SHA based.

## Codex execution boundary

Codex does **not** redo frontend discovery, IA, Experience V2, Design Language or a second design system.

Required execution order:

```text
README
→ AGENTS
→ CODEX TAKEOVER
→ Experience V2 formal source
→ Contracts / Registries
→ Current backend / API / DB / Permission / Evidence / Runtime
→ Current Tests / Production Acceptance
→ AI-01 + CTH-01 calibration
→ real backend binding
→ Critical E2E
→ validated propagation
→ remaining modules
→ GPT / MCP public adapter
→ Security / Regression / Recovery
→ Production Acceptance
```

`READY_FOR_CODEX_EXECUTION` only closes the handoff/readiness gate. It does not certify production runtime, release, security or operating readiness.