# ROUND 07 — validate encoded audio, then correct once if necessary

Base: `a307b8b8117b17db9c9e072166048fc453c98144`.
Status: real-media correction verified; final integrated regression PASS.
J5/J6 and perceptual quality remain unaccepted.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Actual user source 09 exposed AAC encoding overshoot: the existing pre-encode
sample limiter did not guarantee the final media peak. The existing renderer now
measures the final encoded audio. If it exceeds the bounded -1 dBTP ceiling, it
applies a single constant attenuation to the lossless mix and re-encodes audio,
copying the video stream. It remeasures the final file and verifies duration,
stream timing and video frames before returning a new Artifact candidate.

Relative track gain, fades, ducking and edit timing are retained. Quiet audio is
not boosted; silent audio remains honestly silent. This is not LUFS normalization
or a universal podcast/broadcast delivery specification. Renderer metadata now
records initial and final measurements, correction gain/count and the exact
verification state (`lumenis-timeline-3`). No package already saved is rewritten.

## Actual results and recovery

- The genuine five-second source-09 sample reproduced +2.04 dBTP / -9.03 LUFS.
  One -3.54 dB attenuation produced -4.19 dBTP / -12.58 LUFS. Nonlinear encoder
  response is why measurement, rather than arithmetic, determines acceptance.
- Duration stayed 5.000 seconds, 150 frames, and A/V start timestamps zero;
  video stream hashes matched and the old baseline file remained unchanged.
- A separate 0–3 second sample moved from -0.79 to -1.27 dBTP with one correction.
  This is distinct from root's earlier 1–4 second API revision.
- Independent `ebur128` observations were +2.0, -4.2 and -1.3 dBTP respectively;
  strict decoding exited zero for all three files.
- A real synthesized AAC regression also verified correction, 27 video frames,
  a 0.9-second duration and preservation of delayed audio placement.
- Failed measurement, cancellation or a still-excessive second measurement
  returns failure, removes temporary output, preserves previous files and never
  retries indefinitely or publishes an unverified result.

Private exact evidence lives under the local temporary directory
`lumenis-encoded-peak-20260930-6itaqeh0` (baseline, corrected and independent check
JSON plus media). The earlier 122-test run printed all passes, but its enclosing
snapshot check exited 1 because another active owner changed; it is deliberately
not recorded as final PASS. Root's final five-file integration group passed
**96 tests in 100.33 seconds, exit 0**, including renderer, storage, discovery and
actual-media API tests. Its enclosing snapshot check exited zero: all ten watched
source/test files remained unchanged. No background thread leak was observed.

## CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION

ADAPT, accessed 2026-09-30: official [FFmpeg loudnorm documentation](https://www.ffmpeg.org/ffmpeg-filters.html#loudnorm)
and [EBU Tech 3343, 2023, section 11.2.3](https://tech.ebu.ch/docs/tech/tech3343.pdf).
The local FFmpeg 9.0.2 help was also checked. These support final-media true-peak
measurement and the risk of processing/codec overshoot; they do not certify this
product or prescribe one commercial target for all channels. No new dependency
or broader binary license claim is introduced.

OpenCode/Zhipu's abstract test-checklist attempt timed out and was not adopted;
Ollama qwen3:1.7b returned a bounded checklist only. Actual files/tests/measurements
determine acceptance, not model output.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: unchanged.
COMMERCIAL OVERLAY IMPACT: this closes a measured encoding defect, not the whole
video/podcast workflow, media rights, artistic review or release.
