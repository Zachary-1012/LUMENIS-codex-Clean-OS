# Draft: consolidate the complete LUMENIS candidate on current main

## Scope and status

This PR is a complete candidate repository, not a feature-completion, release or merge approval. Base: `4dab98ed6357133da9307de846180ed4f7bba5f5`, independently read back on 2026-10-18 at 06:09 UTC. All 3,187 official base Git blobs were checked. The complete candidate has 3,315 files: 3,009 base files identical, 178 modified, 128 added, zero base files missing. File presence does not prove semantic preservation.

The candidate source manifest SHA-256 is `2f57b6040192177f319b7a59c015541603ea72179b4c0d23688c4e6e0f98b59e`. A direct main-to-candidate patch was applied to an independent complete main copy and reproduced every candidate file hash exactly. No patch chain is needed.

## Combined backend changes

Preserves the full prior candidate and combines eight pinned stages in dependency order: local BMP read transport, scoped event-graph compatibility, media license declaration/credits custody, speech presentation-relative source-clock correction, CSV dialect parsing, KOS profile compatibility, professional-account historical projections, and financial/MMM integrity guards. These stages affect 22 distinct paths relative to the prior candidate. Existing repository layout and source are retained. Flutter/Website bytes are unchanged from that prior candidate.

The speech-clock repair remains in scope. Recording collection is outside this candidate; existing podcast, voice interaction, ASR/subtitles and authorized voice import remain in scope.

## Verification

Final combined regression result: **2,447 passed, 7 failed, zero skipped** (2,454 unique cases; exit 1, 223.37 seconds). See the final receipt supplied with this candidate. It includes the retained original scoped selection, all new changed-owner regressions and broad historical KOS/BMP assertions; counts are from one exact source, never summed from earlier versions.

- 1,472 Python files compile; original AI-native constitution gate passes.
- Real isolated loopback checks: 156 SavedWork/SourceBrief/four-screen requests, 42 graph requests, 59 real-public-CSV requests; signed scope, revocation and recovery assertions pass.
- Real CC0 source import, license/credits persistence, FFmpeg export, revision and unchanged earlier export pass. ffprobe independently confirms the bounded 0.3-second 48 kHz stereo PCM result.
- All 9,519 original CSV cells, missingness and four sample fractions match an independent oracle. Statistical assumptions and business/causal validity are not asserted.
- Ruff is unavailable in the reused environment; no dependency was installed or upgraded. Full lint is not claimed.
- Tests use isolated data and loopback-only guards. No external model, training, collection, production DB, deployment or frontend build was run.

## Blocking / excluded work

- Historical KOS/retired-provider regression failures remain explicit. No old assertion was deleted, skipped or weakened to turn this candidate green.
- Main-to-prior-candidate semantic review is unfinished. Remaining source/caller, authority and compatibility findings must be resolved before merge; successful patch application is not semantic acceptance.
- Incomplete semantic-memory/catalog changes have a source-review security blocker and are excluded. Incomplete BYOK transport lacks the normal-user confirmation HTTP flow and is excluded. Their limited tests do not establish full acceptance.
- Paused Flutter/parser patches are excluded. Local candidate report and manifest were supplied, but the underlying local dirty-source bytes and detailed evidence were not. All 68 reported path hashes differ from current main, the earlier candidate and this candidate (67 different plus conversations.py absent); line-ending normalization does not explain them. This PR cannot claim all local work has been integrated.
- Full original requirements, 19 groups, 195 G requirements, R01–R15/J1–J8/U01–U25, research adoption and four-surface user outcomes remain applicable. None are closed by these engineering test counts.

This is a draft review candidate. Do not merge until substantive review, required checks, missing candidate reconciliation and the candidate integration gates are satisfied. Review-only archives, private local reports and validation runtime data are not part of the product tree and must not be automatically committed.
