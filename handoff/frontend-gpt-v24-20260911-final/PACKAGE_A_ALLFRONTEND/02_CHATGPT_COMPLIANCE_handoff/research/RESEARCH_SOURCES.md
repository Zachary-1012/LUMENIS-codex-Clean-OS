# Research Sources (clean-room: principles only, no third-party code copied)

Researched GitHub + web before each compliance module, per red line. Captured 2026-09-11.

## OpenAI (authoritative)
- Plugin guidelines (LIVE, captured full text): https://developers.openai.com/plugins/app-guidelines
  - Tool names unique/verb-first; write/destructive tools MUST set readOnlyHint+destructiveHint; openWorldHint=true for public-internet incl. read-only web search, =false for bounded private workspace; missing/incorrect labels = common rejection; justify each at submit.
  - Minimal inputs (no full chat transcript/raw log, no precise GPS); response minimization (no session/trace/request IDs or internal timestamps unless required).
  - Restricted Data banned from collection: PCI, PHI, government IDs, credentials/API keys/MFA/passwords.
  - Authorized third-party access only; no unofficial pass-through connectors; no scraping/rate-limit bypass.
  - Auth transparent; review needs a fully-featured demo account (gated signup/2FA -> reject).
  - Commerce: physical goods only; no subscription/digital checkout in plugin; external checkout; no ads.
  - Privacy policy must publish: data categories, purposes, recipients, retention timelines, user controls; verified developer; support contact required.
- App Developer Terms (updated 2026-07-09): apps/connectors/plugins/actions incl. those exposed **via an MCP server**; admins warned on write apps; registry apps pre-reviewed. https://openai.com/policies/developer-apps-terms/
- Apps in ChatGPT help / Apps SDK / usage policies (see Word appendix A for the 7 URLs; re-verify at build).

## MCP spec & SDK
- Tool annotations defaults are **pessimistic**: readOnlyHint=false, destructiveHint=true (only meaningful when readOnly=false), idempotentHint=false, openWorldHint=true. Cross-confirmed by MCP spec mirrors, IBM mcp-context-forge, FastMCP v2/v3 docs, sunpeak (2026-07), Codex KB.
- `outputSchema` is official per MCP spec **2025-06-18**: server MUST return structured results conforming; client SHOULD validate. Missing = warning, never fabricate.
- FastMCP (Python) exposes annotations as a dict on `@mcp.tool(annotations={...})`; structured output via Pydantic/TypedDict/dataclass. Docs: https://gofastmcp.com/v2/servers/tools
- NOTE: https://modelcontextprotocol.io/docs/concepts/tools returned a client-side error at audit; use the 2025-06-18 spec on GitHub (modelcontextprotocol/specification) as the authoritative field reference.

## MCP security (defense principles adopted)
- OWASP MCP Security Cheat Sheet (2026-04): per-server/per-tool least privilege; pin descriptions/schemas; sandbox; **human approval for sensitive/destructive calls**; validate inputs+outputs at server layer; central audit log.
- HITL: confirmation must show the **fully resolved parameters**, not just a tool name; never auto-approve; confirmation not bypassable by model text.
- Transport: OAuth 2.1 + PKCE for user flows, token exchange (RFC 8693), mTLS/audience/scope, default-deny egress, pin tool-description hashes on tools/list.

## What LUMENIS adopts (our own design, no copied code)
- Explicit-hint contract per tool with a written justification; read/compute first, writes last.
- Public adapter calls only `contracts/` versioned internals; Collector/Browser/Cookie/raw-DB stay private.
- Effect fence + idempotency key + resolved-param confirmation for any write/open-world tool; default read-first launch.
