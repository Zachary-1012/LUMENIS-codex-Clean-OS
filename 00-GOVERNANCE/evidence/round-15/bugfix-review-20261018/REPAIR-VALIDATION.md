# Candidate repair validation — 2026-10-18

## Problem and pinned versions
PR83 published base 57e41b4ff276f03ce9b2efe874768c5defb2d413 passed Flutter analysis/build but failed 13 tracked path names. Existing compatibility Skill/Evidence routes lacked original-owner authorization, a dormant approval facade lacked exact single-use binding, and a larger intermediate regression exited SIGSEGV. This report describes source repairs, not product-release acceptance.

## Method and original sources
Preserve original requirements, source paths except required byte-identical renames, and existing gates. Exercise real disposable sessions, SQLite and Evidence owners with authorization, revocation, replay and same-scope cross-actor counterexamples. Pure CPython probes reproduced native periodic traceback SIGSEGV in 3/3 processes; ordinary Python timer probes exited normally in 3/3. Original incident had a truncated periodic stack rather than a complete native backtrace, so attribution is strongly supported but not uniquely proven. Official context: https://github.com/python/cpython/issues/116008 and https://github.com/python/cpython/issues/140815 ; those issue versions are not asserted identical to this binary.

## Results
Frozen 3955-file source: 3136 passed, no failures/errors/skips; full output in VALIDATION-LATEST.log/XML. Source hashes before/after identical; no denied non-loopback attempt. The prior interrupted intermediate run is retained and not counted as passed. Independent approval/API 312-case and runtime 13-case reviews overlap or differ in scope and are not added to this total.

## Product adaptation and limits
Three compatibility endpoints reuse actual account/Task/scope and original Source/Evidence readers. Five existing bounded local producers preserve results; first response and reopened durable projections agree. Unknown OSAI/MCP producers remain SOURCE_READER_UNBOUND pending source-protocol integration, and historical unowned payloads remain preserved pending provenance-backed migration. The original generic account/Agent path remains unchanged by the opt-in bounded mode.
The diagnostic module preserves fatal handling, a 120-second Python periodic worker and owned lifecycle across reload, replacement failure and blocked sink shutdown. Linux CPython3.12.14 is tested; native Windows is not. Normal restart is required. A permanently GIL-held deadlock cannot schedule periodic Python snapshots.

## Next
Publish this exact repaired candidate, execute both original required CI checks on the new head, merge normally only when eligible, and read back main. Native surfaces, live external providers, complete product E2E, arbitrary external SourceUse protocols and historical migration remain separate required work, not removed requirements.

## PR review feedback reconciliation
The four original discussions are addressed by precise source changes and retained failing regressions: transport/Evidence-only capture metadata cannot manufacture fresh observations; actual business/JSON type changes still do. Reads used for comparison are serialized with the existing writer transaction and rollback remains owned by the caller. FFprobe invalid time bases normalize to the established error; 0/0 already did so and remains protected. Supplied frame rates are accepted only as explicit fallback for missing measured values, not to override measured contradictions. FCPXML rejects nonpositive dimensions. Real FFmpeg/FFprobe and OpenTimelineIO 0.18.1 test parsing were exercised; the optional parser is test-only and not adopted as a product dependency. Prior 3050 results remain separate historical evidence and are not added to this run.
