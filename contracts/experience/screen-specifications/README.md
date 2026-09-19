# LUMENIS Screen Specifications

This folder holds the reviewed implementation specification for each canonical App screen. The 44 rows in `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §36 are distinct UX blueprints; they do not prove that routes, source fields, permissions, effects or acceptance behavior have been verified.

## Rules

- Create one `<SCREEN-ID>.md` from [`SCREEN_SPEC_TEMPLATE.md`](SCREEN_SPEC_TEMPLATE.md) for each screen before implementing that screen.
- Use `contracts/experience/lumenis_app_binding_registry.json` as the binding inventory. Update it only from current source/runtime evidence; never treat historical `BOUND`, task assignee or ViewModel labels as proof.
- Keep CTH Subject-first, BMP Brand/Market-first, Shared lineage and SYSTEM infrastructure boundaries intact.
- Do not copy screen layouts into a shared renderer. Shared tokens and semantic interaction primitives may be referenced, while each specification must define its own information hierarchy, composition and task choreography.
- `UNKNOWN` owner, callable, field source, actor scope, permission or evidence lineage blocks the dependent behavior. Record a design exploration separately if useful; never describe it as production-ready.
- Set `APPROVED` only after the product owner or delegated design owner has reviewed the specification and its open questions. Record reviewer, date and the accepted change/review reference. A batch approval must list every covered screen ID and cannot silently approve unreviewed exceptions.
- Implementation, test and runtime status must cite current artifacts. A spec approval is not implementation acceptance.

## Status lifecycle

`DRAFT` → `OWNER_REVIEW` → `APPROVED` → `IMPLEMENTED` → `ACCEPTED`

Use `BLOCKED` when a verified owner, contract, authorization or acceptance dependency is missing. Do not skip states or infer status from code presence.

## Delivery order

After the overall product plan is accepted, resolve source bindings and detailed specifications for one end-to-end workflow slice at a time. Review distinct desktop and mobile compositions, then implement and accept that slice before starting dependent screens. Begin with the five proposed Golden Pages (AI-01, CTH-01, BMP-01, SH-01 and SYS-01) only when their bindings and user tasks are verified; this order does not override owner boundaries or authorize a generic shell.
