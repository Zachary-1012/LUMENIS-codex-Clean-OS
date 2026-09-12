# 04 — Open Blockers (do NOT technically bypass)

| ID | Blocker | Who closes | Why it cannot be auto-closed |
|---|---|---|---|
| B1 | Final Privacy / Terms / Data-Policy legal text + reachable public URLs `/privacy /terms /data-policy /support` | LEGAL + HUMAN | Legal conclusions are `TODO(LEGAL)`; Doubao/Codex must not invent legal rulings; URL must be live to be VERIFIED |
| B2 | Third-party data-source rights/authorization evidence for any public-facing data | HUMAN/LEGAL | Public-visible content != licensed; default-deny until rights_verified; no scraping/unofficial connector/rate bypass |
| B3 | OpenAI review demo account: fully-featured, sample data, no gated signup/2FA | HUMAN | OpenAI rejects inaccessible/2FA-locked review accounts; credentials never enter git/tool IO |
| B4 | OpenAI developer/organization verification | HUMAN | Identity/affiliation verification on platform dashboard |
| B5 | Plugin OAuth + server-side tenant/workspace->subject->domain->scope enforcement | CODEX | Production backend = Codex; reuse `account/`, never trust client-supplied subject_id |
| B6 | Public MCP adapter implementation (versioned-contract calls only) | CODEX | Production code owner; Doubao delivered proposed contracts only |
| B7 | Per-real-table retention / user export-delete-revoke schedule | CODEX + LEGAL | Must be derived from actual schema, not invented |
| B8 | Branch/commit/push authorization | HUMAN | Not granted; work left local & untracked, PUSH=NOT_PERFORMED; suggested branch `integration/chatgpt-plugin-compliance-doubao-v1` |
| B9 | Re-verify live OpenAI submit portal + MCP spec pages at implementation time | CODEX | At audit, modelcontextprotocol.io docs page returned a client-side error and developers.openai.com/plugins/submit fetch errored; guidelines page was live and captured |

## UNVERIFIED (keep, do not guess)
- Real handler side-effects of each future public tool (trace when adapter is built).
- MCP Inspector / ChatGPT Developer Mode runtime result (no server yet).
- Whether any blueprint serves privacy-like content under an unexpected name (filename=0, route=0; exhaustive per-blueprint read not performed).
