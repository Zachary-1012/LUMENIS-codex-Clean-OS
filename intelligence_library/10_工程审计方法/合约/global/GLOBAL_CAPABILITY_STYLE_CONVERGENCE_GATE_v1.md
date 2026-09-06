# Global Capability & Style Convergence Gate v1

## Scope
Applies to every product, module, service, AI capability, report, API, and UI in the Zachary OS AI / Z-Brand-Core twin-repository system.

## Core rule
Reuse existing capabilities first. Adapt existing implementations second. Develop new capability only when an equivalent authoritative implementation does not exist.

## Capability convergence
- Maintain a capability registry with one authoritative implementation per shared capability.
- Shared capabilities include AI Gateway/Budget, Evidence, subject/entity filtering, risk, collection, reporting, notifications, configuration, logging, monitoring, and common UI components.
- New modules must declare reuse/adaptation/new-build status before implementation.
- Duplicate implementations must be consolidated rather than allowed to diverge.

## Code convergence
Use shared conventions for naming, directory boundaries, configuration, errors, logging, typing, API contracts, IDs, timestamps, status values, and versioning. Do not introduce a second convention without an explicit Contract exception.

## API and data convergence
Shared API response envelopes, error semantics, identifiers, timestamps, Evidence references, source metadata, and lifecycle states must remain consistent across products.

## AI convergence
Use the authoritative AI Gateway and Budget controls. Prompt/model versions, fallbacks, outputs, human corrections, and Evidence must remain auditable. AI cannot bypass deterministic business or safety gates.

## UI/design convergence
All products and modules must use the global Design System and tokens for typography, spacing, radius, motion, colors, components, states, charts, tables, forms, and responsive behavior. Do not create local visual systems when an equivalent global component exists.

## Reporting convergence
Reports should use the shared reporting engine and support the common dynamic HTML visualization capability where appropriate. PDF/CSV/JSON exports must derive from the same underlying data and Evidence.

## Verification gate
Before release: capability reuse check -> Contract check -> tests -> Evidence -> runtime verification -> CI. A feature is not considered complete merely because code was written or committed.

## Safety and truthfulness
No fabricated data, metrics, delivery status, collaboration status, ROI, or test results. Failed or uncertain data must remain visible and must not silently contaminate downstream decisions.

## No big-bang refactor
Convergence means incremental consolidation: inventory -> select authoritative implementation -> adapt callers -> regression test -> remove redundant path. Do not rewrite stable unrelated systems merely for stylistic consistency.