# Zachary AI Chat / Architecture Sync — 2026-09-01

This log synchronizes the current Zachary AI boundary and learning decisions from the architecture discussion.

- Zachary is an independent general-purpose AI core and is currently internal-only.
- Products are application, validation and maturation environments, not Zachary itself.
- Future standalone extraction is an explicit maturity/release decision.
- Product-specific architecture, functions, data models, permissions, business rules and workflows must never be imported into Zachary Core or another product.
- CORE-GENERAL, DOMAIN-BOUND and ADAPTER capabilities must remain distinct.
- Global, domain, session and evidence memory are scoped; domain memory cannot implicitly become global memory.
- Learning requires evidence, benchmark/shadow validation, transfer checks, repair and regression/isolation checks.
- Promoted capabilities are versioned, auditable and reversible.

DCC role: engineering governance, audit, testing, release gates and protection of the separation above. This log does not authorize product-code changes.
