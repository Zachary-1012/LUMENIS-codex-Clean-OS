# Privacy / Terms / Data-Policy / Support — ENGINEERING DRAFT ONLY

> **TODO(LEGAL) on every legal conclusion.** This is an engineering skeleton built from the
> real intended data flow so legal counsel has something concrete. It is NOT legal advice and
> is NOT a published policy. Do not link it as the public policy until legal signs off and the
> four routes are actually deployed and reachable.

OpenAI requires a published privacy policy covering at minimum:
**(1) categories of personal data, (2) purposes, (3) categories of recipients,
(4) retention timelines, (5) user controls** — plus a reachable support contact.

## Routes to implement (Codex) — must reflect REAL data flow
| Route | Content source | Status |
|---|---|---|
| `/privacy` | this draft, sections 1-5 below | TODO(CODEX) implement + TODO(LEGAL) approve |
| `/terms` | this draft, terms section | TODO(CODEX) + TODO(LEGAL) |
| `/data-policy` | retention/delete/export derived from REAL tables | TODO(CODEX) map tables + TODO(LEGAL) |
| `/support` | real support contact / channel | TODO(HUMAN) |

## 1. Categories of personal data (engineering inventory — TODO(CODEX) confirm against schema)
- Account/auth data handled by `account/` (login, workspace membership). TODO(CODEX): list exact fields.
- Workspace business data the user asks the plugin to process (evidence/metrics/case/report), scoped server-side.
- Inputs explicitly sent to a tool (task-narrow only). The plugin never pulls full chat history.
- TODO: confirm whether coarse system metadata (e.g. coarse region) is used; never collect precise GPS/address.

## 2. Purposes
- Provide the requested evidence/metric/insight/report/action within the authenticated workspace.
- Security, audit, abuse prevention. No surveillance / behavioral profiling / ad targeting.

## 3. Recipients
- The user's own workspace; LUMENIS service operators required to run the product.
- OpenAI as the host transport (per OpenAI terms). No sale of data; no ad recipients.
- Any subprocessors: TODO(LEGAL)/TODO(CODEX) list only real ones.

## 4. Retention (derive from real tables — do not invent numbers)
- TODO(CODEX): produce table -> retention mapping from the actual schema / migrations.
- Account deletion: align to OpenAI expectation that deleted data is removed within the stated window (OpenAI's own reference is 30 days); LUMENIS window = TODO(LEGAL).
- Tool inputs are not retained beyond task need unless the user explicitly saves an artifact.

## 5. User controls
- Access / export / delete / revoke: TODO(CODEX) implement against real data layer; TODO(LEGAL) wording.
- Revoke plugin access disconnects the public layer; internal Production Core data is governed by the main product policy.

## Restricted Data guarantee (engineering, firm)
The public plugin never collects PCI, PHI, government IDs, or credentials/API keys/MFA/passwords,
and never returns cookies/session/raw secrets. Enforce by output-minimizer + contract tests.
