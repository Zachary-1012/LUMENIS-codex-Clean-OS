# v6.0 Execution Efficiency Policy

Status: active
Scope: ongoing until explicitly paused by the owner

## Objective
Maximize delivery throughput without reducing development, testing, audit, security, stability, or release-gate standards.

## Rules
1. Never skip required development work, tests, audits, or evidence.
2. Parallelize independent workstreams whenever dependencies permit.
3. Reuse research, contracts, fixtures, tests, and tooling instead of repeating work.
4. Keep production mainline isolated from experimental capability branches until release gates pass.
5. Do not claim work is complete without verifiable evidence (commit, test result, CI/E2E result, or documented limitation).
6. Fail fast and stop/revert unsafe directions rather than accumulating speculative changes.
7. Prioritize the production closed loop and release stability over optional enhancements.
8. Treat 20x as an efficiency target for removing waiting, duplication, and rework—not as permission to lower quality.
9. Maintain the existing subject-hard-filter authority: AI/video intelligence cannot override deterministic subject qualification.
10. Keep the three-language product baseline: zh-CN, en, ko-KR, with Korean localization treated as product localization rather than literal translation.

## Workstreams
- v6.0 release and production closed-loop stability
- Passive Video Intelligence (no video downloading as a required pipeline behavior)
- zh-CN / en / ko-KR i18n and Korean localization
- Korean drama dialogue and subtitle/fansub translation research for content-learning assets

## Release rule
Version 6.0.0 is released only after the applicable release gates are actually green. A deadline must never override evidence or production safety.
