# Local foundation API contract

This document specifies the bounded local foundation routes listed below; it
does not enumerate the complete product API or establish deployment, runtime
acceptance or completion. Full behavior remains defined by [the product
specification](PRODUCT-SPEC.md) and [domain contracts](domains/README.md).
Professional editing and monitoring protocols must be reconciled with their
actual callers and implementation when those capabilities are published.
JSON successes use `{ "data": ... }`; failures use
`{ "error": { "code": "...", "message": "...", "details": {} } }`.
Dates are UTC ISO-8601. IDs are opaque. Unknown values remain null with a reason.

## Session and transport

The local core serves the Web build and `/api` on the same loopback origin
(`http://127.0.0.1:8317` by default). It validates Host and Origin; no wildcard
CORS or implicit access to the user's personal browser profiles is permitted.
The launcher creates a short-lived, single-use local capability in its protected
data root. Web receives it in a fragment, clears the fragment immediately, then
exchanges it; fragments never enter HTTP requests. Windows receives it through
the local launch flow. A capability is not a production or platform credential.
No capability or session value is written to diagnostics or committed evidence.

- `GET /api/status`: `{product:"OEVIRA",version,setup_required,
  runtime:{api:"available",worker:{status,last_heartbeat_at}},ai:{status}}`.
  Worker status and nullable UTC heartbeat come from the running process;
  an available API does not by itself mean background jobs are running.
- `POST /api/local-session`: `{capability, display_name?}` creates or reconnects
  the local workspace. Returns `{token, user:{id,name}, workspace:{id,name}}`
  and sets an HttpOnly SameSite=Strict session cookie. The token supports the
  native client and is never placed in a URL or localStorage.
- `GET /api/session`: authenticated user/workspace; does not return the token.

All following routes require a valid cookie or Bearer session and derive
workspace authorization on the server. Another workspace's IDs return 404.
Member/source revocation is checked again before background writes. Remote
team accounts and invitations retain their full product requirements; a local
capability cannot be used as remote authentication.

## Work, inputs and comparison

| Method / path | Input | Returned data |
| --- | --- | --- |
| GET `/api/works` | — | Work list |
| POST `/api/works` | `{title,goal}` | Persisted Work |
| GET `/api/works/{id}` | — | Work with material/result references |
| PATCH `/api/works/{id}` | `{base_version,title?,goal?,status?}` | New Work version |
| GET `/api/materials` | — | Authorized Material list |
| POST `/api/materials` | multipart `file`, optional `work_id`; or `{title,text,work_id?}` | Stored original and actual parse state |
| GET `/api/materials/{id}` | — | Material and exact source segments |
| GET `/api/materials/{id}/file` | — | Original bytes as attachment |
| POST `/api/materials/url` | `{url,work_id?}` + `Idempotency-Key` | Durable public-acquisition Job |
| POST `/api/works/{id}/compare` | `{material_ids,criteria:[string]}` + `Idempotency-Key` | Durable Job |
| GET `/api/jobs/{id}` | — | Current Job |
| POST `/api/jobs/{id}/cancel` | — | Cancelled/requested state |
| POST `/api/jobs/{id}/retry` | — | Safely resumed Job |

Work fields: `id,title,goal,brief,status,version,material_ids,artifact_ids,created_at,updated_at`.
`brief` is optional structured context: `audience` and `deliverable` are text
(up to 2000 characters); `budget` contains optional finite nonnegative
`minimum,maximum`, optional `currency` and `notes`, with minimum <= maximum
when both exist. A notes-only budget is valid. `required_facts,forbidden_claims,
customer_requests` are lists of up to 50 text entries, each up to 1000 characters.
POST/PATCH work accepts it; updates retain omitted fields and use base_version.
These values are user requirements, not verified source facts. A comparison job
freezes the current goal, brief, criteria and material IDs in its input snapshot;
the resulting artifact retains that snapshot so later work need not re-enter it.
Material fields: `id,title,filename,status,reason,format,text,segments,sha256,created_at,work_id?`.
Segment fields: `id,label,text,start,end,kind`; offsets refer to the saved parser
text in Unicode code points, not UTF-16 indices. PDF page and Office object labels
remain inspectable. Unsupported/partial input is preserved without invented text.
Job fields: `id,kind,status,progress:{completed,total,label},artifact_id,material_id,error,work_id`.
`acquire_url` completes with a material ID, source URL, native/capture time,
method and limitations. It keeps original response bytes separate from the
readable text projection. A denied, unavailable or rate-limited source is not
automatically retried through an account or browser. Known access rules and
public-network destination checks apply to every request and redirect.
Progress is measured work, never decorative percentages.

The deterministic comparison preserves excerpts, dates, numbers and source scope.
Matching is not semantic verification, contradiction proof or an AI answer.
Users can change comparison criteria or remove materials and create a new result.
The result contains useful source-aligned rows and explicit limits; unavailable
inputs remain distinguishable from a successfully searched input with no match.

## Results, versions and delivery

| Method / path | Input | Returned data |
| --- | --- | --- |
| GET `/api/artifacts` | — | Artifact list |
| POST `/api/artifacts` | `{title,body,citations,work_id?}` | Persisted draft |
| GET `/api/artifacts/{id}` | optional `version=n` | Selected immutable version and history |
| POST `/api/artifacts/{id}/versions` | `{base_version,title,body,citations}` | New version |
| POST `/api/artifacts/{id}/restore` | `{base_version,restore_version}` | New version based on history |
| POST `/api/artifacts/{id}/exports` | `{version,format:"md"|"docx"}` + `Idempotency-Key` | Export with authenticated `download_url` |
| GET `/api/exports/{id}/file` | — | Actual validated export bytes |

Artifact fields: `id,title,body,version,versions:[{version,created_at,revision_note}],citations,work_id,input_snapshot,created_at,updated_at`.
Version creation accepts optional `revision_note` describing the user's change.
Citations: `{material_id,segment_id,quote}`; each must resolve to accessible exact
saved source text. Source text is untrusted content, never an instruction.

Stale `base_version` returns 409 `VERSION_CONFLICT` with current version data;
the client retains the user's draft. Restore adds a version and never rewrites
history. A repeated idempotency key with different input returns 409; a completed
request returns its persisted result. File writes, DB metadata and job completion
must survive interrupted execution without silently creating duplicate results.

Markdown/DOCX are the first result delivery bindings, not the full document or
media scope. Office object editing, PDF annotation, video, podcast, acquisition,
monitoring and AI use the same authorization and version foundations as their
corresponding implementations are connected. No empty endpoint represents them.
