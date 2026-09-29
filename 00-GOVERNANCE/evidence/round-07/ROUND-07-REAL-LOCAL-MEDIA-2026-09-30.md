# ROUND 07 — actual user media through the running local product

Source/API base: `a307b8b8117b17db9c9e072166048fc453c98144`.
Status: bounded live API and process-restart recovery VERIFIED; visible user work,
creative quality and J5 remain unaccepted.

## REAL DELIVERY CARD / 真实用户工作闭环验收

The actual loopback Product Core imported source 09 from the user's twelve-file
manifest, saved a five-second video, trimmed a separate three-second revision,
and served both project packages and playable media. This used the existing
Content API, Permission, Skill, Evidence and Artifact owners, not direct writes
to the Artifact table or a separate FFmpeg export script.

- Original source SHA-256: `af8c0b9f5a642f44d54e22c4a3b9280c6ab3d6c7aebdf815df83079f8dedee6c`.
- Source Artifact: `ART-e41a37ff37d54417`; source execution: `1d60135c169f436d`.
- Five-second project: `ART-2abfe1f7a0924d45`, execution `5fff7cc396864be2`.
- Trimmed revision: `ART-73b3307a011d48f4`, execution `9f6ed5487cbc4424`.
- Both exports recorded execution Evidence. No external publishing occurred.
- Rights remain unknown/demo-only. Engineering acceptance does not grant rights
  to use these source materials in a commercial campaign.

The confirmation was first cancelled and could not be replayed; a fresh exact
file confirmation then allowed import. BMP GLOBAL scope was retained; reading
these projects in CTH was denied. A new client reopened them. After a controlled
Core child-process restart, detail/package/media reads preserved both hashes:

| Version | Package SHA-256 | Media SHA-256 |
|---|---|---|
| 1 | `292f107f262d5ed91185ba75fb045c9db568137dfa3578eda7f996cf74069ae2` | `73cab2618ecfa08bf64e6284627a3c6207becc3274d4edcc0e87afc022b74c43` |
| 2 | `33b1553a86e5b8447fed541d7759f1f52839c4c03613a113664a44703722b37f` | `4c3c1b282ecc421669cf177faa9730cd2d1a65daedbe04e60fca893b24df709b` |

## Recovery and source/runtime limits

An online SQLite backup preceded the bounded product writes. Integrity remained
`ok`, foreign-key violations remained zero, and the new records were one source
and two separate projects. Old project bytes remained unchanged.

The first driver attempt called an unavailable Timeline convenience method after
successful import. It did not pass. The driver was corrected to the existing
`Timeline.trim` operation and resumed using the saved source receipt, avoiding a
duplicate import. Final driver execution exited zero.

The supervisor was retained; only its verified Core child was restarted. Product
local configuration selected the already verified FFmpeg/ffprobe binaries.
Windows user environment, registry, Codex model/provider and credentials were
not changed. Other protected local candidates existed, so these observations
verify this source/API path and do not certify a clean whole-product runtime.

Private reproducibility records are under
`data/private/content-api-upgrade-20260930/`: `live-api-results.json`, the source
receipt, exact media downloads and the bounded integration driver. User media,
database backups and private runtime records are not published to Git.

## Quality finding, not a completed film

The five-second output had 150 frames, five seconds and zero A/V stream start
offsets, but encoded audio measured **+2.04 dBTP**. The three-second revision had
90 frames and measured **-0.63 dBTP**. Existing metadata honestly said true peak
was not verified. These outputs therefore are not audio-quality acceptance.
The resulting bounded renderer correction is tracked separately; original
Artifacts are preserved rather than rewritten to appear newly compliant.

User-visible editing/reopening is being integrated by the independent frontend
task. API drivers are not a substitute for that E2E. Multi-source composition,
subtitles, perceptual review, full podcast creation and complete client delivery
still require their own real results.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: unchanged; representative media does not
advance commercial/brand data coverage.

COMMERCIAL OVERLAY IMPACT: J4/J5/J6, rights, multi-surface, release and operating
remain unaccepted. No J delivery package is counted as complete by this report.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: actual final-media
measurement exposed a concrete owner-level correction; no new render system.
