# Governance Authority Map — ZBC × OSAI

Status: ACTIVE / CANONICAL INDEX
Effective: 2026-09-04

## Purpose
Prevent rule proliferation, priority collisions, stale instructions and AI context overload. This index does not create a second authority.

## Authority order
1. Safety / security / legal / platform restrictions
2. ZBC Production Truth / protected production rules
3. `CANONICAL-EXECUTION-V3-20260904.md` — sole cross-repository AI execution authority (V3; supersedes V1 baseline which was referenced but absent on disk)
4. Current approved domain contracts
5. Task-specific requirements / acceptance criteria
6. Research recommendations
7. Historical / legacy records

## Current classes

### CANONICAL
`CANONICAL-EXECUTION-V3-20260904.md`
Sole cross-repository AI execution authority (V3, 2026-09-04).
Opening gate: `AI-EXECUTION-MASTER-COMMAND-V2-20260904.md` (开工口令 V2, read-before-execute).

### DOMAIN
`CANONICAL-NAMING-AND-TWIN-SYNC.md` — naming/sync.
`CANONICAL_REGISTRY.md` — canonical registry.
`TWIN_EXECUTION_GATE.md` — twin execution gate.
`UNIFIED_UI_UX_INFORMATION_ARCHITECTURE_V1.md` — UI/UX information architecture.
`WEB-NO-SCROLL-INTEGRATED-UI-EXECUTION-CONTRACT-20260904.md` — fixed viewport and bounded information hierarchy.
`RELEASE_AND_AUTORUN_GATE.md` — release/autorun gate.

### RECORD
Audit, implementation, research and decision records describe evidence and history; they do not create parallel execution authority.

### LEGACY / SUPERSEDED
Old execution directives that duplicate the canonical baseline must not remain active. Historical files may be retained only for provenance.

## Cleanup rule
Before deleting/renaming any rule: scan references in README, AGENTS, governance, code/configuration and automation; migrate unique active policy; update references; run regression/documentation checks; delete only when safe.

## AI startup rule
Read this map, then the canonical baseline, then the applicable domain contract, then the task requirements. Do not load legacy documents as active commands.

## Conflict rule
If documents conflict: classify them, apply authority order, trace evidence, make one recorded decision, and update the map. Never silently obey conflicting rules simultaneously.


## V3 promotion record (2026-09-04)
- `CANONICAL-AI-EXECUTION-BASELINE-V1-20260904.md` was referenced by this map but **absent on disk** (broken link). Classified SUPERSEDED / LEGACY — V3 supersedes it as the sole execution authority.
- `CANONICAL-EXECUTION-V3-20260904.md` (V3) is now the sole cross-repository AI execution authority. Status: ACTIVE / CANONICAL.
- `AI-EXECUTION-MASTER-COMMAND-V2-20260904.md` (V2) is the opening gate (read-before-execute). Status: ACTIVE / DOMAIN (opening procedure).
- Both files exist in ZBC and OSAI `00-GOVERNANCE/`. Authority order now: Safety/Legal/Security → ZBC Production Truth → V3 → V2 (opening gate) → Domain Contracts → Task Requirements → Research → Legacy Records.
