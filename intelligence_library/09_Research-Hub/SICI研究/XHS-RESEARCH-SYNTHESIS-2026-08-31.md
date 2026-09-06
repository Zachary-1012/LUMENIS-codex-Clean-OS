# XHS / RedNote Research Synthesis

Status: RESEARCH-ONLY / COLLECTION FROZEN

## Research map

Domestic Xiaohongshu and overseas RedNote should be treated as related but not identical providers. Public projects show host-specific adapters, browser-based tools, external public-data APIs, and user-owned content/RAG pipelines.

## What we learn

- Adapter abstraction is reusable across mainland and overseas hosts.
- External licensed/public-data providers can decouple the production account from collection, but require authorization, contract, provenance and quality review.
- User-owned likes/favorites plus OCR/RAG is a strong low-risk research pattern.
- Anti-bot systems are layered; IP rotation is not a legitimate production solution for an account that has already received a warning.

## Research boundary

No reverse engineering, private API recreation, CAPTCHA bypass, fingerprint evasion, proxy/IP rotation for detection avoidance, account rotation, or human-behavior simulation.

## Next research tasks

1. Verify official XHS/RedNote API scope and authorization.
2. Build a provider-comparison matrix for official API vs licensed provider vs user evidence vs public source.
3. Define provenance and confidence schemas.
4. Evaluate data quality using offline fixtures only.
5. Keep production XHS frozen until the incident gate is explicitly cleared.
