# proposed/ — editable contracts & drafts (NOT wired to production)

Convention for human editors:
- `*.proposed.json` / `*.skeleton.json` are **standard JSON** (JSON-Schema style, 2-space, no comments).
- Field meaning and the decision behind each value lives in the matching `.md` next to it.
- Values you must fill are `null` / `"TODO(CODEX)"` / `"TODO(LEGAL)"` / `"TODO(HUMAN)"`.
- Nothing here is imported by the running app. Codex turns a PROPOSED contract into real
  implementation under the production architecture, then deletes the PROPOSED marker.

Files:
- `public_mcp_tools.proposed.json` + `public_distribution_layer_arch.proposed.md` — public tool surface, hints, schemas, boundary.
- `source_provenance_contract.proposed.json` — source rights registry (default-deny).
- `chatgpt_app_submission.skeleton.json` — submission shape (5 positive / 3 negative); finalize only after tools exist.
- `privacy_terms_data_support.DRAFT.md` — engineering draft; every legal clause is TODO(LEGAL).
