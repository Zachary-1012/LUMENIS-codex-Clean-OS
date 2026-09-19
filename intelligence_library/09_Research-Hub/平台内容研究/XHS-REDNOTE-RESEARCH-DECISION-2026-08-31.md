# XHS / RedNote Research Decision

## Current account state

The user reports a RedNote account registered with a Hong Kong phone number that is restricted from liking/commenting/posting but can still search and open notes. This state must be treated as platform-controlled and must not be used as an automation test target.

## Research decision

Study external open-source projects for:
- persistent browser profile lifecycle
- session storage/recovery
- browser crash recovery
- OCR/evidence extraction
- provider abstraction
- observability

Do not adopt their anti-detection, stealth, fingerprint spoofing, proxy rotation, or human-simulation techniques.

## Feasible architecture today

Official API/SDK -> licensed provider -> user-controlled evidence -> analysis.

Automation against XHS/RedNote remains frozen until incident review and explicit approval.

## Browser requirement

A built-in browser may be made stable by using a dedicated persistent profile, a one-time manual login, explicit session states, no repeated login probing, isolated storage, and crash recovery. A second browser/OS handoff may be provided as a compatibility fallback, never as an evasion mechanism.
