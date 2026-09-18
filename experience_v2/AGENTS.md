# AGENTS.md — LUMENIS Experience V3

Scope: experience_v2/** and any work launched with this directory as the Codex working directory.

This file specializes the repository root AGENTS.md. Production truth and safety rules from the root still apply.

## Mandatory read order

Before changing Experience code:

1. ../AGENTS.md
2. ../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION-V3-20260918.md
3. 02_authority/AUTHORITY_ALIGNMENT.md
4. exact current screen ViewModel / state / action / permission / Evidence contracts
5. current implementation and tests for the active slice

Do not use older V2/V2.4/V2.5 presentation language to override Constitution V3.

## Core rule

Shared primitives are reusable. Page skeletons are not automatically reusable.

Do not optimize for “44 screens from ten component families”. Optimize for semantic continuity and truthful workflow composition.

For non-trivial visual work, define the screen's user problem and V3 semantic composition before editing CSS.

## Forbidden defaults

Do not default to:

- Head + KPI + Chart + Table
- four-column KPI hero rows
- generic card grids
- Bento layouts
- identical section sequences across unrelated realms
- Apple / Linear / Notion / ChatGPT / Korean-brand imitation
- glass as the global visual theme
- CRUD rendering for Event / Evidence / Case / Insight
- chat bubbles as the default AI result surface

If a current screen already contains one of these patterns, treat it as migration debt, not as precedent.

## Golden Pages

The first V3 calibration set is:

- AI-01: intent_space + artifact_flow
- CTH-01: now_stream + event_flow + evidence_trace
- BMP-01: market_network + evidence_trace
- SH-01: creation_flow + artifact_flow
- SYS-01: runtime_topology + health_trace

All five must have distinct top-level semantic signatures.

Do not mass-migrate the other screens before these five pass strict acceptance.

## Required gate

Before claiming any core Experience implementation complete, run:

python scripts/audit_tools/verify_experience_anti_template.py --strict

If the gate fails, fix the implementation. Do not weaken thresholds, delete checks, rename a forbidden pattern to bypass detection, or change the gate to advisory.

After Golden Page migration, add/refresh deterministic Playwright screenshot baselines intentionally and review diffs. Use ARIA snapshot/assertion coverage for structural regressions where practical.

## Code Review Rules

Flag as P0 Experience regression when a change:

- adds a new top-level kpis section to a Golden Page
- adds a generic cards section as the Golden Page's main composition
- makes two Golden Pages share the same section signature
- increases anti-template baseline debt
- changes only styling while leaving a known generic dashboard hierarchy intact
- removes or hides Evidence trace from an important conclusion
- treats external brand style as the LUMENIS target
- weakens or bypasses verify_experience_anti_template.py

Safe direction: preserve truth contracts, create/extend semantic V3 primitives, and compose each workflow from its own information relationships.
