# Media license declaration persistence and credits: bounded backend handoff

Status: IMPLEMENTED / ISOLATED_BACKEND_VERIFIED; not legal clearance, UI acceptance, whole media closure, publication or release. Independent review/integration remains required.

## Scope and exact source

Only existing backend owners were changed:
- shared_artifacts.py
- experience_runtime.py: import_content_source only; the parser owner's earlier BMP change is preserved
- lumenis/system/security/permission.py: ContentSourceImport exact-resource binding
- tests/test_content_media_license.py (37 dedicated cases)

No frontend/Dart/build, new dependencies, API/model calls, production database migration, deployment or external publication. No new product registry, permissions owner or database.

The isolated source directory is a copy of the completed parser verification source, which was based on the complete 2248 baseline; only the four above allowlisted files were overlaid. Protected paused frontend changes in the development workspace were not copied. Upstream main 4dab98ed and original 2248 ancestry receipts establish provenance; this patch does not claim to have fetched Git or to be merged. experience_runtime.py's preimage is exactly the parser preimage SHA256 f16ac02242eb8ff0acb291bd6c2248373bbd294baed2d89dbe0c6e34f5f0e6a2.

Final source-manifest.json SHA256: 6ac2e6bb7617e2545e8cdd4465a16c3b70171090e5ff87e2be3978779cd6bb6d.
Final MEDIA_RIGHTS.diff SHA256: b3ea9cec56164bfb1438a8dc4dd0d194f8898d421acb153fc483ad19a8aba90a.
changed-files.json records all four pre/postimage hashes. All 3,309 inventoried source files were rehashed after tests: no change. Generated Python/pytest caches are excluded from source identity.

## Contract and implemented flow

The existing octet-stream content-source upload accepts an optional X-Lumenis-Media-License header containing a JSON declaration (ASCII JSON escapes are suitable for international text in HTTP headers). The strict 13-key schema is enforced by validate_media_license; requests are bounded to 16 KiB. Duplicate/unknown keys, invalid types, malformed Unicode/JSON, missing required text, invalid hashes, non-media object kinds, credentials/query/fragment URLs, and unsupported licenses fail closed. URLs are inert HTTPS locators and are never fetched. Evidence text remains exact UTF-8, including original license line endings and tabs, with its SHA256 verified; it is not executed or promoted to legal truth.

Only CC0-1.0 and CC-BY-4.0 media-asset declarations are supported by this bounded path. Software, model weights, dependency terms, training data and personal voice consent are separate objects; their permissions are not granted by this schema.

The server computes the declaration digest and binds it to the existing ContentSourceImport Permission resource, with the existing actor/scope/content bytes/name/size. A changed declaration requires a new exact confirmation. Confirmation returns the declaration and digest; approval is not inferred from the license name. Existing no-declaration resource hashes and upload response shape remain unchanged.

source.json v1 remains accepted with its original strict envelope. A declaration creates an immutable v2 source package within the existing Artifact owner, containing the declaration and digest. The original MediaAsset strict key set, evidence_refs and rights_status remain unchanged. Both source/project rights_state stay unknown. The declaration is explicitly labeled declared_not_independently_verified. Missing evidence cannot silently grant rights. The read path verifies the outer package, exact metadata envelope, declaration/evidence hashes and actual archived media bytes. Recovery/idempotency matches the declaration digest as well as the original upload identity.

Revisions use a newly confirmed source Artifact and its immutable reference; previous source/project packages are not overwritten. The existing export gate still controls output. The existing project package automatically includes credits.json and credits.txt when a referenced source has a declaration, with source Artifact and media hashes, source version, author/title, license locator, notices and supplied earlier modifications. The server records actual timeline clip operations, track kind, transitions, overlays and render options separately. Project/timeline version and hash bind these credits. Sources without a declaration stay unknown even when adjacent assets have CC0 declarations.

Project reopen/download recomputes expected credits from reauthorized source artifacts and the saved timeline, checks package/file hashes and exact credits bytes, and refuses missing, substituted or stale credits/source pins. Existing total-file/byte/JSON caps apply after credits are added. Failed/cancelled requests do not replace previous exports.

## Final evidence

1. frozen-final-regression.log: 252 passed in 43.23s, no skips. Nine existing/affected test modules, including the parser transport module and 37 dedicated declaration cases. Real FFprobe/FFmpeg, isolated SQLite, actual Permission/confirmation/Evidence path. Includes real loopback HTTP and a fresh interpreter reopening source/project/credits; no media-probe stub.
2. real-cc0-final.log and tmp/real-cc0-final/receipt.json: already-downloaded real Kenney Music Jingles v1.0 member Audio/8-Bit jingles/jingles_NES00.ogg, imported through actual loopback HTTP, confirmed through existing endpoint, rendered, exported/read back, revised and old exported ZIP verified byte-identical.
   - Archive SHA256 b729ba57959bd58793d2c5cafa348aaf2655d354f3da35ec4729e03ec77197b8
   - Original media SHA256 1010c9b566d6c090ff03a4aaaf7439e26eb4cc4f20373800d0b7e6a9057b795d
   - Original License.txt SHA256 373b1c880ee6c7a83c1ccf209f251cf45fc9ea9b1f0330844fa7be64a401adc4
   - Final export ZIP SHA256 95b3e8336bce0ca2de3862f0c0f94a005eacc6df99097fa2a29e69b344e8f3fe
   - Independent ffprobe in real-cc0-final-ffprobe.json: PCM 24-bit WAV, 48 kHz, stereo, 0.300000 seconds, 86,502 bytes. This short edit proves the storage/export chain, not full-program listening quality or a person's voice.
3. compile-final.log: all four files compile. constitution-final.log: existing AI-native constitution gate passes.
4. No production DB was supplied. Tests use explicit disposable databases and the existing SQLite isolation guard. The real CC0 probe also uses an isolated temporary database; its migration fixture initializes only that disposable database.

CC BY automated tests use an explicitly labeled generated-tone declaration fixture. They do not claim that the actual Carefree audio was downloaded, licensed-file identity checked or listened to.

## Preserved failures and limitations

- Default Python lacked pytest: first-regression.log preserved. Reused the existing Python 3.12.14 validation venv, no install.
- Initial new tests exposed a missing optional recovery-function parameter and HTTP success response dropping declaration fields. test-first.log through test-third.log preserve the failures. Both were repaired; final tests cover successful recovery behavior through the existing route regressions.
- First real-asset probe used a directory outside TMPDIR and the existing renderer correctly rejected NEW_PRIVATE_TEMP_OUTPUT_REQUIRED. real-cc0-first.log and its failed-run files are preserved. The probe moved to an isolated temporary directory; renderer safety was not weakened.
- Ruff is unavailable in the reused environment; no lint PASS is claimed. Compilation and substantive targeted regressions ran.
- Host-generated Artifact/log timestamps retain their existing naive local format (22:xx on Oct 17); verification was completed around 2026-10-18 05:51 UTC. No clock/configuration migration was made.
- No four-surface UI/native acceptance, subjective audio review, long podcast/TTS/voice-package acceptance, full source-rights legal review or commercial release is implied. Full 19-item scope remains open in its respective owners.

## Replay / integration

Use env.sh, the existing [LOCAL_WORKSPACE]/lumenis_restored_validation_20261017T2115Z/venv/bin/python, and source as cwd. Read frozen-final-regression.log for the final result. real_cc0_probe.py writes a new isolated run directory; preserve earlier runs instead of overwriting them when replaying. Apply MEDIA_RIGHTS.diff only to its recorded preimages after reconciling current main; preserve the parser change. Product files retain their original relative locations. No standalone evidence directory needs to be copied into the product repository.
