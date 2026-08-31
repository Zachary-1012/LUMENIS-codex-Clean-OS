# XHS / RedNote Research Synthesis

Status: RESEARCH-ONLY / XHS PRODUCTION FROZEN

## Scope

Study domestic Xiaohongshu, overseas RedNote, public GitHub projects, open models, scraping architecture, anti-bot systems and WAF/firewall patterns.

## Findings

1. Overseas RedNote and mainland Xiaohongshu share substantial product/web architecture, but hostnames, cookies and some flows differ. Public projects such as OpenCLI model this as one logical adapter with host-specific configuration rather than duplicating business logic.
2. Public GitHub MCP projects demonstrate browser-based integration, but several explicitly depend on logged-in sessions, cookies, Playwright and automated interaction. These are research references only and are NOT approved for the currently warned production account.
3. Public RedNote data API vendors demonstrate an alternative architecture: Core calls an external API and receives public-data results. This is a vendor dependency and must not be treated as an official Xiaohongshu API or as proof that a collection method is permitted.
4. Public RAG projects show a useful low-risk pattern: user-owned likes/favorites -> local cache -> OCR -> index -> source-grounded analysis. This pattern is more suitable for knowledge/research than account automation.
5. OWASP's bot-management guidance confirms that modern anti-automation is layered across edge/CDN/WAF, application/session controls and backend anomaly detection. IP alone is not a reliable identity signal; rate limiting should be applied across IP, session, identity and endpoint dimensions.

## Production decision

Because the production account has received an explicit platform warning, XHS collection remains HARD FROZEN. Do not use research findings to tune around detection.

## Approved future paths

A. Official API/SDK after verified authorization.
B. External licensed/public-data provider after legal, contractual and data-quality review.
C. User-provided evidence / owned-data ingestion, OCR and source-grounded analysis.
D. Public, unauthenticated sources that are permitted by their terms and do not require account automation.

## Blocked paths

Private API reverse engineering, signature recreation, packet replay, device/token spoofing, CAPTCHA bypass, proxy/IP rotation for evasion, fingerprint evasion, multi-account rotation, automated browsing intended to imitate humans, and any attempt to use randomized timing as a detection-evasion mechanism.

## Architecture implication

Keep XHS behind the existing Platform Adapter contract. Add future providers as separate adapters with explicit provenance and policy state:

OFFICIAL_API / LICENSED_PROVIDER / USER_EVIDENCE / PUBLIC_SOURCE / BLOCKED.

All sources must retain provenance, capture time, confidence and provider identity. No source may silently overwrite another source.
