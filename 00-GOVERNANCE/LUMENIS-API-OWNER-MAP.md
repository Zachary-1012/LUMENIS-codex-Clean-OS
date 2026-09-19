# LUMENIS API Owner Map

> Status: CURRENT IMPLEMENTATION MAP  
> Scope: 序境 / LUMENIS only. This map describes route families and their business owners; it is not a replacement for route-level authorization or runtime acceptance.

## Product domains

| Domain | Product meaning | Route family | Data and behavior owner |
| --- | --- | --- | --- |
| CTH | 序境·商业运营; selected Subject context | `/api/cth/` | CTH capability through canonical database, evidence, evaluation, learning and reporting owners |
| BMP (`ZBMP` stable API identifier) | 序境·品牌市场; selected Brand focus | `/api/zbmp/` | BMP capability through canonical database, evidence, evaluation, learning and reporting owners |
| Shared | Cross-domain reusable services; not a third product | `/api/skills/`, `/api/content/`, `/api/v2/report-center/` and shared service routes | `lumenis/shared/` owners; each request still enforces actor and domain scope |
| SYSTEM | Accounts, permissions, runtime, collection, AI gateway and operations | `/api/system/` and SYSTEM service routes | `lumenis/system/` owners |

CTH is Subject-first. BMP is Brand/Market-first. A selected context may scope a request, but cannot rewrite canonical ownership or move business facts between domains. Shared services do not make CTH and BMP interchangeable.

## Deprecated compatibility routes

Existing route names may remain as compatibility façades while callers migrate. Compatibility does not grant a retired route independent data, permission or execution ownership. The response deprecation header policy is maintained in `app.py` and must be tested alongside the canonical route. Remove a compatibility route only after caller inventory, equivalent behavior, authorization and regression acceptance are recorded.

## Authorization and acceptance

- Every business read and write must be authorized for the authenticated actor, product domain, module and requested action.
- SYSTEM authorization, approvals, Evidence and side-effect controls remain separate canonical owners.
- A route being registered or returning a ViewModel does not prove field-level owner, scope, permission or lineage acceptance.
- Route changes require contract tests for success, denied scope, missing data, failure, and the documented side-effect boundary.
- The Experience binding registry and per-screen specifications record callable, owner, actor, scope, permissions, Evidence and acceptance evidence for the future desktop/mobile App.
