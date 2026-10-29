# 寰意 / OEVIRA — Development entry

The only working root is `D:\寰意`; the repository is
`Zachary-1012/OEVIRA`. The Product Owner approved the new product
specification on 2026-10-29 and authorized implementation at this path.

## Product authority

Read `PRODUCT.md`, `docs/PRODUCT-SPEC.md`, `DESIGN.md`, `docs/ARCHITECTURE.md`
and `docs/ACCEPTANCE.md` for their respective responsibilities. The approved
new product replaces the former product's architecture, navigation, source
layout and execution sequence. Git history is reference material, not a second
set of instructions. Do not restore the rejected UI or copy old architecture.

Serve commercial operations teams, brand/agency teams and independent research
and creative users. Build self-developed product logic; only already planned,
license-compatible components may be adopted. Research is not integration.
Keep one acquisition system, strong controlled browsing, explicit user-owned
platform authorization, reliable sources, editable results and recovery.

## Engineering

- Every filesystem tool uses absolute paths under `D:\寰意`; every shell call
  specifies that working directory. A stale tool default is not authorization
  to write the previous workspace. Never access or recreate the retired root.
- First publish this approved repository/specification baseline through a checked
  PR; product implementation follows it. A framework starter is not this baseline.
- Work on a `codex/` branch. Preserve unrelated changes. Review exact changes,
  meaningful tests and builds before a PR. Never push directly to main or
  weaken required checks. Do not describe a partial foundation as the product.
- UI, API and domain services share explicit contracts. Validate untrusted
  input at boundaries; keep logic direct and responsibilities clear.
- Use an isolated data root in tests. Do not read, migrate or delete old user
  databases, credentials, personal browser profiles or research originals.
- Product platform accounts belong to each user; no developer identity or
  region allowlist is a product eligibility rule. Development does not grant
  access to personal sessions. No live platform collection without its scope.
- Preserve facts, unknowns, native times, citations and version history.
  Model output cannot authorize effects or become observed fact by itself.
- No paid resources, production deployment, model training, account changes,
  network changes or external business effects are implicit in implementation.
- Build real vertical outcomes. Empty states are valid; fabricated data,
  placeholder handlers, fake saves and decorative progress are not completion.
- Record stable product decisions in the owning document. Do not put developer
  dispatch, busy status or progress logs in product specifications.

## Layout

`server/oevira/`: product API/domain/runtime; `server/tests/`: isolated tests.
`app/`: Flutter Web/Windows client; `website/`: public presentation when built.
`scripts/`: controlled development/run/verification; `docs/`: complete functional
specification, architecture, acceptance and interface contracts. `PRODUCT.md` and
`DESIGN.md` at the root own product definition and presentation respectively.
`data/`, build outputs, credentials and local runtime state are ignored.
