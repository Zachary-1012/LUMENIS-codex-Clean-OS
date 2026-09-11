# LUMENIS CODEX TAKEOVER — READ FIRST — 2026-09-11

> Status: **EXECUTION ENTRYPOINT / NO-REDISCOVERY HANDOFF**  
> Import base audited against GitHub `main@f548669d82974ea065afb310776ec63935896d7d`.  
> Goal: use Codex quota on real binding, optimization, gates and closure — not on rebuilding assets already delivered.

## Read order
1. `README.md`
2. `AGENTS.md`
3. `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
4. `00-GOVERNANCE/LUMENIS-EXPERIENCE-CURRENT-DIRECTION-READ-FIRST-20260911.md`
5. `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`
6. **`00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-LANGUAGE-V2.4-20260911.md`**
7. `experience_v2/19_handoff/INTEGRATION_START_HERE.md`
8. `experience_v2/codex_handoff/MANIFEST.json` and `experience_v2/12_contracts/**`
9. `00-GOVERNANCE/handoff/CHATGPT_COMPLIANCE_20260911/README.md`
10. current real Source / Route / API / DB / Permission / Evidence / Runtime / Tests for the exact slice being changed.

## Do not rebuild these
- Do not invent another design system, component taxonomy, motion registry, responsive model, i18n registry, screen inventory, ViewModel/Action/Permission/Evidence registry, or ChatGPT compliance plan before auditing the delivered equivalents.
- Do not import current production `templates/static` into `experience_v2` as duplicate source. They remain current production/capability evidence until cutover.
- Do not copy Legacy/ZBC templates into the new Experience. Legacy is capability/evidence only.
- Do not expose internal Browser/CDP/Cookie/session/collector scripts as public ChatGPT tools.
- Do not create a second Metric/Report/Evidence truth to make the UI easier.

## But do not freeze bad presentation
The imported Experience is **not** an instruction to preserve a generic/template-looking screen. The latest v2.4 Design Language is a P0 visual gate. Codex is expected to improve the scaffold when needed so production has a coherent, recognizable 序境 language.

## Execution order
```text
Current main truth
→ drift check
→ cheap parse/spec gates
→ AI-01 + CTH-01 design-language calibration
→ real ViewModel/API/Permission/Evidence/State binding
→ critical E2E
→ propagate proven grammar and binding pattern across remaining screens
→ ChatGPT/MCP public adapter + provenance/auth/effect fence
→ regression/security/recovery
→ Production Acceptance
→ RC / submission-ready
```

## Source-of-truth policy for generated screens
`experience_v2/build/src/**` + registries/contracts are the editable canonical screen-generation source. Generated `07_screens/**` and large visual-regression media are intentionally not imported as a second editable truth. Regenerate them when needed and attach resulting evidence to audit/release artifacts.

## Legacy evidence
`08-AUDIT/LEGACY-DELIVERY-EVIDENCE/2026-09-11/**` is READ_ONLY historical evidence/provenance. It may prove prior work, QA or originality; it may not override current Experience source or Production Truth.
