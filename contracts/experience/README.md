# LUMENIS Experience Contracts

This folder is the canonical contract family for user-visible Product Core bindings.
It is not a Product Architecture, Experience design authority, generic page schema or
proof that a screen is implemented.

## Authority and routing

```text
current source / runtime / Permission / Evidence truth
→ 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
→ screen-specifications/<SCREEN-ID>.md
→ screen binding/action/state/permission/evidence contracts
→ implementation and executable acceptance
```

- `lumenis_app_binding_registry.json` and `BACKEND_GAP.json` are fail-closed truth,
  owner, Permission and Evidence inventories. They do not define layout.
- `screens/`, `actions/`, `states/`, `permissions/`, `evidence/` and `viewmodels/`
  constrain the product meaning that every approved surface must preserve.
- `screen-specifications/` is the pre-implementation design gate. Only a current,
  Sol-reviewed `DESIGN_READY` specification may guide a screen implementation.
- Audit PDFs, taskbooks, screenshots, wireframes, Figma frames and fixtures remain
  `DESIGN_EXPLORATION`; they cannot become a second authority or direct code target.
- Web Workspace, Desktop and Mobile may recompose interaction and density over the
  same Product Core/API/ViewModel, Permission, Evidence and state semantics. Public
  Website explains/acquires only and never owns production business truth.
- `UNKNOWN` never authorizes a new API, owner, permission, metric or successful UI.

Any implementation copied directly from a generated artifact, generic card grid or
substituted-title renderer without the detailed screen gate is rejected as `REWORK`.
