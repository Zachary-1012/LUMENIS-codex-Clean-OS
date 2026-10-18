# Speech source clock correction — 2026-10-18

## Scope and reproduction
Only `lumenis/shared/content_creation/speech_transcription.py` and `tests/test_speech_transcription_timebase.py` change. Candidate starts from the fixed media-rights source freeze; paused frontend changes are excluded. No renderer, ASR model, dependency, production database or runtime configuration changes.

`logs/old-extraction-clock-second.jsonl` records actual FFmpeg reproduction: selected audio starts 0.75 seconds after the presentation origin, but the old normalized WAV begins sounding at 0. Source container origins 0, -0.25 and 2 seconds all exhibit this loss. This is a timestamp transport defect, not recognition-quality evidence.

## Correction
The normalized 16 kHz mono WAV now uses decoded PTS on the same default container-presentation-relative input clock as the existing renderer. The filter trims negative relative time, preserves leading silence with `aresample:first_pts=0`, and pads/trims to the existing source duration. It does not blindly add stream start_time. WAV frame count and hash are checked. Metadata records original bytes hash, selected stream, observed container/stream origins (missing stays null), source time base, rate, actual decoded continuity, normalization filter and hash. Source and clock are rechecked after decoding and during timeline mapping.

Historical zero-origin WAV reports remain usable; historical arbitrary-container reports without verified normalization must be regenerated. Reports retain the existing public `original_source_seconds` label with an explicit presentation-relative clock definition. Existing source-in/out, repeated clips, overlap rejection, cut-word omission and sample-quantized delay mapping remain.

## Honest boundary
Only continuous selected audio PTS is accepted. A bounded actual decoded-frame scan compares PTS and sample counts with explicit timestamp quantization tolerance. Real forward gaps and backward overlaps fail with `CONTENT_ASR_SOURCE_CLOCK_DISCONTINUITY_UNSUPPORTED` before ASR. Missing/unprovable timestamps, excessive scan size or incomplete packet coverage fail closed. Scan cap: 100000 packets/frames, 16 MiB retained JSON, 60 seconds process timeout; existing process runner checks cancellation every 250 ms and kills/reaps the subprocess. File size is checked after the bounded process, not a streaming disk quota.

Piecewise discontinuous clock support remains OPEN, requiring a shared renderer/normalizer segment mapping and end-to-end gap/overlap proof. This rejection is not full original media-scope completion. VFR video does not change an audio clock; tests verify actual varying video frame intervals, with no video-frame alignment claim. Codec-specific AAC/MP3 encoder priming quality is not independently established by these PCM container fixtures.

## Evidence
Real FFmpeg tests cover positive/negative container origins, negative absolute audio PTS, selected delayed audio, 44.1k to16k resampling, absent WAV start_time, VFR, actual render waveform timing after source trim and timeline delay, repeated clips, overlapping selected speech rejection, cut words, forged/stale clock metadata, real PTS discontinuities, cap and cancellation. Decoder tokens are explicitly synthetic alignment fixtures, never ASR recognition or human acceptance.

Intermediate runs and initial reproduction failures remain in logs; final results and hashes are recorded separately. `source-manifest.json`, `changed-files.json` and `SPEECH_TIMEBASE.diff` bind the exact candidate. A unified regression on the exact integrated freeze remains required; independent-stage test counts must not be added together.

## Revision accounting
The initial 352-case runs (`frozen-regression.log`, `final-frozen-regression.log`) are intermediate, not final acceptance: the former overlapped the VFR assertion improvement; the latter overlapped addition of cumulative decoded-sample drift checking. Their output is preserved without claiming either proves the final source. `previous-pin/source` reconstructs the earlier published pin exactly; all 3318 file hashes match its saved manifest. The final stable run is `logs/final-stable-regression.log` only. The cumulative check compares each PTS against first PTS plus all previous decoded samples divided by source sample rate; tolerance is two stream ticks plus two source samples. A dedicated injected one-sample-per-frame drift demonstrates why checking only neighboring frames is insufficient.

## Final result
353 tests passed in 62.92 seconds, no skips, no background-thread leak. Post-run hash comparison: all 3317 inventoried non-cache files unchanged; pytest nodeids cache changed as expected. Initial full-tree unchanged assertion correctly failed and was narrowed explicitly to exclude that generated cache, not source. Python compile of both changed files and final AI-NATIVE CONSTITUTION gate pass. No lint result claimed. See FINAL_RECEIPT.json for final diff/manifest/log SHA256.
