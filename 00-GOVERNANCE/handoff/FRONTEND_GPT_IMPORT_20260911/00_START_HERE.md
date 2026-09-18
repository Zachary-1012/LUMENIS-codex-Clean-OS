# LUMENIS / 序境 — Codex Frontend + GPT Takeover 2026-09-11

> Status: **CODEX_EXECUTION_INPUT / NOT_PRODUCTION_READY**
> Branch base: `main@f548669d82974ea065afb310776ec63935896d7d`
> Frozen source package base: `ab67612367c172ced2dff62b44e98de86469d1e6`
> Source bundle SHA-256: `c4bbb60c3e21db88d3f271ff63359dd845e052aaf69911aa554bb1a3fdcf202c`
> Legacy evidence SHA-256: `0e45ab95481de42462b291917cbbc4452e1b07f2dafb7a055776f3bf5c26d4a9`

## 0. What this handoff is

Doubao / Trae delivered **product scaffold + design research + contracts + engineering assets**. They did **not** deliver a visual template that Codex must reproduce literally.

Codex must understand 序境 / LUMENIS and finish 序境. Functional binding is never a reason to preserve generic SaaS/dashboard/template presentation.

Current Production Source / Runtime / Data / Permission / Evidence / Tests remain higher truth than this handoff. This handoff supplies Experience and ChatGPT integration input; it does not replace Production Truth.

## 1. Mandatory reading order

1. `README.md`
2. `AGENTS.md`
3. `00-GOVERNANCE/LUMENIS-PRODUCTION-ACCEPTANCE-MASTER-CHECKLIST-V1.md`
4. this file
5. `00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-READ-FIRST-20260911.md`
6. `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`
7. `00-GOVERNANCE/LUMENIS-EXPERIENCE-DESIGN-LANGUAGE-V2.4-20260911.md`
8. `experience_v2/19_handoff/INTEGRATION_START_HERE.md`
9. `experience_v2/12_contracts/**`
10. `00-GOVERNANCE/handoff/CHATGPT_COMPLIANCE_20260911/**`
11. only then the real backend/API/DB/Permission/Evidence/Runtime/Test files for the active slice.

Do not start by rediscovering the entire repository. Reuse the delivered registries/contracts first; audit current truth only where binding or verification requires it.

## 2. P0 design-language redline

The Experience package is a **high-quality scaffold, not a visual acceptance waiver**.

Mandatory LUMENIS execution language:

- black-silver / white-silver metallic monochrome;
- editorial serif display + restrained sans body;
- `Lumen Axis / 序轴` as spatial/navigation grammar;
- `Strata / 境层` as hierarchy grammar;
- de-boxed composition; do not build card walls;
- hairline structure, whitespace and typography before shadows/containers;
- Icy Cyan only for truthful data/state semantics, never decorative brand chrome;
- original LUMENIS AI orb, not sparkle/star/ChatGPT-like AI iconography;
- motion explains state, continuity, causality or focus; motion is not decoration;
- no purple/indigo generic SaaS chrome when it conflicts with v2.4.

**Mask Logo Test:** hide the logo during review. If the product no longer feels recognizably LUMENIS, the visual gate fails.

Anti-template does not mean decorative art. Preserve information density, evidence traceability, accessibility, responsive efficiency and Production Truth.

## 3. P0 hidden-logic redline

The internal production chains are **backend/product logic, not ordinary page content**.

Do NOT render these chains as decorative diagrams, stepper rails, permanent process ribbons or explanatory cards on normal CTH/BMP/Content/Report pages:

- `External Data → Evidence → Canonical Data → Function → Metric → Truth Table → View Model`;
- `Source → Evidence → Event → Case → Insight → Decision → Action → Outcome → Evaluation`;
- `Task → Permission → Skill/Tool → Action Firewall → Effect Fence → Execute → Evidence → Evaluation → Trace`;
- internal Collector / Runtime / Permission / MCP / Agent orchestration.

Ordinary product pages should expose only what the user needs to work: **context, facts, relationships, state, evidence, findings, decisions, actions, outcomes and controls**.

### Allowed exceptions

**AI conversation / assistant experience:** may show user-facing execution transparency such as retrieval status, cited evidence, tool/action status, permission/approval request, generated artifact and result provenance. It must not expose private chain-of-thought, hidden model reasoning, secrets, raw credentials, browser sessions or internal security mechanisms.

**System / diagnostics / engineering views:** may expose real operational state when required for administration or diagnosis, but only as truthful observability. Do not turn the product's conceptual logic chains into decorative UI.

## 4. First vertical slice — calibration before propagation

Codex must optimize and bind **AI-01 + CTH-01 first**:

`Design Language calibration → Mask Logo Test → anti-template review → real ViewModel/API → Permission → Evidence → State → Critical E2E`.

Do not propagate the visual implementation to the remaining screens until this slice passes both design-language and Production Truth gates.

## 5. Do not rebuild / duplicate

- Do not invent another design system, component taxonomy, motion registry, responsive model, i18n registry, screen inventory or ViewModel/Action/Permission/Evidence registry before auditing the delivered versions.
- Do not copy current production `templates/static` into `experience_v2`; they remain current production/capability evidence until cutover.
- Do not copy Legacy/ZBC templates into the new Experience. Legacy is read-only capability/evidence only.
- Generated `07_screens/**`, prototype data and large regression media are not a second editable truth. Regenerate from canonical specs/registries when needed.
- Internal Browser/CDP/Cookie/session/collector scripts never become public ChatGPT tools.
- Do not create a second Metric/Report/Evidence truth to fit the frontend.
- Do not surface backend logic chains merely because the contracts describe them.

## 6. ChatGPT boundary

Public ChatGPT/MCP integration is an adapter over LUMENIS Production Truth, never direct access to Collector, Cookie, Browser Session, CDP, raw DB or hidden internal tools.

Target boundary:

`ChatGPT → MCP/App Adapter → allowlisted schema → Auth/Subject/Domain/Permission → Provenance/Policy → versioned internal contract → LUMENIS Production Truth`.

Engineering can reach `SUBMISSION_READY`; legal approval, third-party rights, developer verification/account controls and external platform approval remain human/external dependencies.

## 7. Acceptance sequence

`Current repo drift check → AI-01 + CTH-01 calibration/binding → design gate → critical E2E → remaining screen binding → GPT/MCP adapter → security/contract/regression/recovery → Production Acceptance → RC`.

Production Ready still requires all repository Production Acceptance gates. File presence, generated previews and green-looking UI are not completion evidence.