# XHS / RedNote Research Gate

Status: RESEARCH-ONLY / HARD FREEZE

## Research conclusions

Public projects fall into four broad patterns: browser automation, external data APIs, user-owned content sync/RAG, and content-generation MCP tools. These are architecture references, not approval to automate the warned production account.

Open-source anti-bot research and OWASP guidance show that detection is layered: edge/WAF/network reputation, session/identity behavior, endpoint quotas and backend anomaly detection. Therefore the DCC must never convert these findings into an evasion recipe.

## DCC policy

Allowed:
- architecture comparison
- official API/SDK research
- provider due diligence
- provenance/data-quality testing
- user-owned evidence ingestion
- defensive anti-bot threat modeling

Blocked:
- detection-evasion tuning
- fingerprint spoofing
- proxy/IP rotation to evade controls
- account rotation
- CAPTCHA bypass
- private API/signature reverse engineering
- packet replay
- automated human imitation

## Gate

Any proposed XHS integration must declare provider type, authorization basis, data provenance, account dependency, rate policy, failure behavior and rollback path. Unknown authorization status = BLOCKED.
