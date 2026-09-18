# UI/UX Non-Regression Contract

## Purpose
Apply the new lightweight 2–4 level information architecture without invalidating any previously implemented capability.

## Rules
- Existing intelligence/research capabilities remain enabled and reachable by default.
- Do not delete, disable, rename, relocate, or silently replace working features only to match a new visual hierarchy.
- Preserve existing APIs, data contracts, evidence flow, Runtime, permissions, security, stability, and twin-repository boundaries.
- Keep research truth distinguishable from production truth.
- Map every existing route/function/component/data contract to its retained, reused, merged, or explicitly migrated destination before structural changes.
- Prefer progressive disclosure, tabs, anchors, inline expansion, and Drawer/side panels over adding navigation depth.
- Use the minimum depth needed for the user's task: simple 2 levels, standard 3 levels, complex 4 levels.
- Existing Research, AI, Knowledge, Benchmark, Evaluation, learning, evidence, and research-adoption workflows remain valid; new IA is an adaptation layer, not a reset.
- Reuse existing components, tokens, APIs, data models, and business logic before creating duplicates.
- Research findings intended for production adoption must continue through the established evidence/contract/specification flow.
- Any migration must be validated, auditable, reversible, and recorded with an exact Git SHA.

## Regression Gate
Before completion verify: existing routes/workflows work; APIs/contracts work; existing data remains accessible; Evidence remains traceable; Runtime remains intact; research/production boundary remains intact; permissions remain intact; existing tests remain green; relevant new UI/interaction tests pass; no capability becomes unreachable.
