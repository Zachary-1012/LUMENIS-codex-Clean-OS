# UI/UX Non-Regression Contract

## Purpose
Apply the new lightweight 2–4 level information architecture without invalidating any previously implemented capability.

## Rules
- Existing production capabilities remain enabled and reachable by default.
- Do not delete, disable, rename, relocate, or silently replace working features only to match a new visual hierarchy.
- Preserve existing APIs, data contracts, database fields, collection controls, permissions, Runtime, Evidence, Release Gates, deployment, security, and stability behavior.
- Map every existing route/function/component/data contract to its retained, reused, merged, or explicitly migrated destination before structural changes.
- Prefer progressive disclosure, tabs, anchors, inline expansion, and Drawer/side panels over adding navigation depth.
- Use the minimum depth needed for the user's task: simple 2 levels, standard 3 levels, complex 4 levels.
- Podcast, KOS, public opinion, Campaign, Research, AI, Evaluation, Runtime, Monitoring, Audit, Tasks, Deployment, and existing reporting remain valid; new IA is an adaptation layer, not a reset.
- Reuse existing components, tokens, APIs, and business logic before creating duplicates.
- Any migration must be validated, auditable, reversible, and recorded with an exact Git SHA.

## Regression Gate
Before completion verify: existing routes work; existing APIs/contracts work; existing data remains visible; existing collection controls remain intact; Evidence/Runtime chains remain intact; permissions remain intact; existing tests remain green; relevant new UI/interaction tests pass; no capability becomes unreachable.
