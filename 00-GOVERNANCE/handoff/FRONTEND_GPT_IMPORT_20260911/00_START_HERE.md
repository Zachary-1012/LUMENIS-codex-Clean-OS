# LUMENIS / 序境 — Codex Frontend + GPT Takeover 2026-09-11

> Status: **CODEX_EXECUTION_INPUT / NOT_PRODUCTION_READY**
> Branch base: `main@f548669d82974ea065afb310776ec63935896d7d`
> Frozen source package base: `ab67612367c172ced2dff62b44e98de86469d1e6`

## Why this branch exists

This branch carries the curated canonical Experience V2 + ChatGPT/MCP compliance handoff without dumping 110 MB of duplicate/generated/media assets into normal source history. The package has been reduced to editable source, contracts, runtime, governance and machine-readable evidence needed by a human engineer or Codex.

Source bundle SHA-256: `c4bbb60c3e21db88d3f271ff63359dd845e052aaf69911aa554bb1a3fdcf202c` (1331 entries, CRC clean).
Legacy evidence bundle SHA-256: `0e45ab95481de42462b291917cbbc4452e1b07f2dafb7a055776f3bf5c26d4a9` (273 entries, CRC clean).
Canonical import payload SHA-256: `1f916070e27e5e9a230cca69e4f6ce3901118ddf53be106afde1afe9d6dfc6ff`.

## First command

Run from the repository checkout on this branch:

```bash
python 00-GOVERNANCE/handoff/FRONTEND_GPT_IMPORT_20260911/UNPACK_TO_WORKTREE.py
```

The unpacker verifies the payload SHA-256, refuses conflicting overwrites, extracts the canonical 111-file source set to normal repository paths, and runs basic JSON/Python validation.

After unpacking, read in this order:

1. `README.md`
2. `AGENTS.md`
3. `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
4. `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-READ-FIRST-20260911.md`
5. `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`
6. **`00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-LANGUAGE-V2.4-20260911.md`**
7. `experience_v2/19_handoff/INTEGRATION_START_HERE.md`
8. `experience_v2/12_contracts/**` + `experience_v2/codex_handoff/MANIFEST.json`
9. `00-GOVERNANCE/handoff/CHATGPT_COMPLIANCE_20260911/README.md`
10. current real backend/API/DB/Permission/Evidence/Runtime/Test files for the slice being changed.

## P0 visual redline

The imported frontend is a **high-quality scaffold, not a visual acceptance waiver**. Codex MUST NOT ship or broadly propagate a screen that still reads as generic SaaS, a dashboard template, a card wall, or a Doubao/AI-generated template.

The latest execution language is **Design Language v2.4**: black-silver / white-silver metallic monochrome; editorial serif display + sans body; `Lumen Axis / 序轴`; `Strata / 境层`; de-boxed hierarchy; hairline structure; restrained semantic motion; original AI orb; no purple/indigo product chrome. Icy Cyan is data/state only.

**Calibration gate:** optimize and bind `AI-01 + CTH-01` first. Mask the logo during review. If the result is not still recognizably 序境, the visual gate fails; refine it before propagating to the remaining screens.

Anti-template does not mean decorative art: preserve business density, evidence traceability, accessibility, responsive efficiency and Production Truth.

## Do not rebuild / duplicate

- Do not invent another design system, component taxonomy, motion registry, responsive model, i18n registry, screen inventory or ViewModel/Action/Permission/Evidence registry before auditing the delivered versions.
- Do not copy current production `templates/static` into `experience_v2`; current production UI remains current truth/capability evidence until cutover.
- Do not copy Legacy/ZBC templates into the new Experience; Legacy is read-only capability/evidence.
- Generated `07_screens/**`, prototype data and large regression media are not a second editable truth. Regenerate them from `build/src/**` and registries when needed.
- Internal Browser/CDP/Cookie/session/collector scripts never become public ChatGPT tools.
- Do not create a second Metric/Report/Evidence truth just to fit the frontend.

## Verified before branch packaging

- Experience specs: `44/44`, no missing/extra screens.
- Handoff validator: `34/34`.
- Staged JSON parsing: `0` errors.
- Staged Python compile: `0` errors.
- JavaScript `node --check`: PASS.
- Common secret-token heuristic: `0` hits.

This is an execution handoff. Production Ready remains subject to the repository's six Production Acceptance gates.