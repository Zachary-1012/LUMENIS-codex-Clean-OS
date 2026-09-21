# LUMENIS Multi-Surface Decision — CURRENT

> Status: **PRODUCT OWNER APPROVED / ARCHITECTURE DECISION**
> Approved: **2026-09-21**
> Applies from: **ROUND 02**
> Product Architecture authority: `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`
> Experience authority: `LUMENIS-EXPERIENCE-CONSTITUTION.md`

This decision records how the approved commercial surfaces are delivered. It is not a second Product Architecture, Experience authority, data owner, runtime owner, or completion claim. Current executable source and runtime evidence remain authoritative.

The Product Owner also accepted the ROUND 01 audit, missing-capability register and
15-round mapping on 2026-09-21. That approval authorizes the ordered execution
baseline, not implementation from the audit PDF or its sketches. All generated visual
artifacts remain `DESIGN_EXPLORATION` until the sole Experience authority and a
current detailed screen specification establish `DESIGN_READY`.

## 1. Approved product-surface structure

```text
ONE Product
ONE Repository / main
ONE Product Core
ONE Canonical Data
ONE Evidence
ONE Permission
ONE Runtime Ownership
ONE AI Gateway / Agent Runtime
ONE API / ViewModel Contract
ONE Experience / Design Authority

MULTIPLE EXPERIENCE SURFACES
├─ Public Website
├─ Web Workspace
├─ Desktop App
└─ Mobile Companion
```

The surfaces may recompose navigation, density and interaction for their devices. They may not redefine business objects, state meanings, Permission, Evidence, workflow outcomes or Production Truth.

## 2. Product boundary by surface

| Surface | Product role | Permitted capability | Hard boundary |
| --- | --- | --- | --- |
| Public Website | Commercial introduction and acquisition | Product/domain explanation, industries and use cases, customer cases, truthful demo, trial request, enterprise contact, help, login/workspace entry | No Production Truth, operational workflow, privileged action, Canonical Data owner or client-side provider secret |
| Web Workspace | Primary commercial workspace | Authorized Subject/BrandFocus selection; CTH/BMP/AI/Shared/SYSTEM workflows; Evidence Trace; Case/Insight/Decision/Action; reporting/export; collaboration, approval and light configuration | Uses canonical Product Core/API/ViewModel; must not recreate local Cookie/CDP/filesystem/local-AI capability in the browser or simulate a desktop result |
| Desktop App | Power User Client | Full workspace plus local Browser/CDP, Cookie/session, Collector, long-running tasks, local files, Ollama/Local AI, enterprise LAN/private deployment, recovery and advanced execution | Desktop-only capability remains behind SYSTEM Permission/effect fences and explicit capability state; it does not create separate business truth |
| Mobile Companion | Timely review and light action | Notifications, events, AI results, approvals, task state, report reading and bounded quick actions | Not the primary dense-analysis or local-execution environment; unavailable capability is shown honestly and may hand off to an authorized Web/Desktop task |

## 3. Approved technical route

The approved route is hybrid and keeps one Product Core:

```text
Public Website     SEO-capable independent presentation deployment
Web Workspace      Flutter Web target from the existing app/ codebase
Desktop App        Flutter Windows/macOS/Linux targets from app/
Mobile Companion   Flutter Android/iOS targets from app/
Product Core       existing Python/Flask canonical API and runtime owners
```

`website/` is reserved for a future Public Website implementation. It may contain presentation and acquisition integration only. It must not own CTH/BMP/Shared/SYSTEM workflow logic, production persistence, Permission or Evidence.

`app/` remains the single Flutter Experience implementation for Web Workspace, Desktop and Mobile. A future `app/web/` platform target is generated/configuration support, not a second Web product or design authority.

Public Website and Web Workspace are deployed separately so public SEO/content delivery and authenticated workspace runtime can evolve without mixing trust, caching, release or availability boundaries. Both remain governed by the same Product Architecture and Experience Constitution.

Historical `templates/`, `static/` and `experience_v2/` implementations remain retired. They must not be restored as a shortcut. Any unique business capability found in history must first be traced into the current Product Core/API and then exposed through an approved surface.

## 4. Shared contract and capability boundary

All operational surfaces consume the same canonical meanings:

```text
actor + tenant/scope
→ SubjectContext or BrandFocus
→ Permission / approval / effect fence
→ canonical API / typed ViewModel
→ Canonical Data + Evidence lineage
→ state/result/evaluation/return
```

Surface capability must be explicit: `AVAILABLE`, `DEGRADED`, `DESKTOP_REQUIRED`, `PERMISSION_REQUIRED`, `UNAVAILABLE` or `UNKNOWN`. A Web or Mobile request may enqueue or hand off an authorized Desktop/SYSTEM task only through a real canonical contract with status, Evidence and recovery. It may not report success from an optimistic UI, HTTP 200, registration record or fixture.

The pre-beta product-account decision remains in force until the identity/tenant architecture is approved in its scheduled round. Multi-surface approval does not authorize a new login database, browser-side credential store or bypass of protected server routes.

## 5. Jev product decision

Jev is approved as a candidate **typed decision and evaluation provider** behind the one canonical `lumenis/system/ai_gateway/`. Jev is not a replacement for a generative language provider and is not an independent AI gateway.

Approved candidate uses:

- routing and classification over source-backed state;
- Evidence relevance/quality scoring and uncertainty disclosure;
- risk triage and review prioritization;
- Agent route selection and output/claim verification;
- evaluation of business/model outputs against typed questions.

Forbidden ownership:

- no Canonical Data, Evidence, Permission, metric, workflow, final business-decision or effect-authorization ownership;
- no direct API key or provider call from Public Website, Web Workspace, Desktop UI or Mobile;
- no promotion of probabilities, confidence or model output to Production Truth;
- no silent fallback that changes a typed decision into unrelated free-text generation.

Required provider lifecycle:

```text
OFF
→ ROUND 07 adapter/contract implementation
→ SHADOW evaluation against named datasets and human decisions
→ legal/security/privacy/cost/runtime review
→ ACTIVE only for explicitly approved typed tasks
```

Production configuration must pin an accepted model version; a moving alias is limited to development/probing. Every persisted decision record must identify provider, model/version, input/output schema, probabilities, confidence, request ID, latency, token/cost data when supplied, input/output hashes, actor/domain/object scope and Evidence references. Low confidence or schema failure remains `UNKNOWN` or requires human review.

Vendor references used for this decision: [System One / Jev launch](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [API](https://docs.typesafe.ai/api), [models](https://docs.typesafe.ai/models), [primitives](https://docs.typesafe.ai/primitives), [confidence](https://docs.typesafe.ai/confidence), and [Master Customer Agreement](https://typesafe.ai/legal/mca). These references describe a candidate external provider; current source/runtime must independently verify every production claim.

## 6. Current implementation truth

At approval time:

| Item | Current status |
| --- | --- |
| Product Core/API ownership | `IMPLEMENTED` in current Python/Flask owners; completeness varies by workflow |
| Flutter Desktop/Mobile source | `PARTIAL` |
| Flutter Web target / Web Workspace | `ABSENT` |
| Public Website | `ABSENT` |
| Multi-surface deployment | `ABSENT` |
| Jev adapter/provider configuration | `ABSENT` |
| Jev runtime/evaluation evidence | `LIVE_UNVERIFIED` |

Approval is not implementation evidence. No absent surface/provider may be reported as shipped, tested, verified, released or operating.

## 7. Fifteen-round placement and gates

- ROUND 02: record this decision; reconcile sole authorities, naming, validators and compatibility classification. No Web/Jev implementation.
- ROUND 07: implement and evaluate Jev, if its Task Card confirms owner/contract/legal/security prerequisites, inside the one AI Gateway.
- ROUND 08: build the Cross-Surface Experience Foundation: Public Website foundation, Flutter Web Workspace shell, Desktop shell, Mobile Companion shell, shared state/accessibility/localization and capability boundary.
- ROUND 09–14: every workflow specification records a surface matrix: Web primary/available, Desktop enhanced/exclusive, Mobile view/notify/approve/light action, Public Website explanation/demo only.
- ROUND 15: prove Public Website → trial/login entry → Web Workspace → real context/workflow/Evidence → Desktop advanced execution when applicable → Web result → Mobile notification/approval when applicable → Report/Evaluation/Learning.

Stop and return `BLOCKED` rather than creating a second truth when identity/tenant scope, Permission, Evidence, API/ViewModel, desktop handoff, provider legal terms, secret handling or runtime ownership is unresolved.
