# Current Project Alignment Baseline — 2026-09-05

> Status: planning / audit baseline only. This document records the current cross-repository direction and does not authorize implementation changes.

## 1. Current Phase

- Pause feature development and UI reconstruction.
- Establish a source-of-truth audit baseline first.
- Audit Z-Brand-Core and Zachary-OS-AI from repository/file/module/function level through Contract, Requirement, Test, Commit and Lifecycle.
- No automatic cleanup, refactor, UI rebuild, commit or push should be inferred from this document alone.

## 2. Repository Direction

```text
Unified Product Architecture
        |
   +----+----+
   |         |
  CTH       ZBMP
   |         |
   +----+----+
        |
   Shared Core
        |
       OSAI
```

The architecture is a target analysis model, not an instruction to merge repositories or code immediately. Boundaries must be established from source evidence first.

## 3. Source Audit Principle

Source evidence takes precedence over README claims. Every finding should be classified as:

- SOURCE FACT
- USED
- PARTIAL
- DOCUMENTED ONLY
- DEAD
- ORPHANED
- BROKEN
- DUPLICATED
- UNKNOWN

Unknown must remain unknown until evidence is available; do not guess.

## 4. Required Traceability Chain

```text
File
 -> Module
 -> Function
 -> Contract
 -> Requirement
 -> Test
 -> Commit
 -> Lifecycle
```

Lifecycle should cover, where applicable:

```text
Discover -> Requirement -> Research -> Evidence -> Decision -> Architecture
-> Implement -> Test -> Verify -> Release -> Operate -> Monitor
-> Learn -> Improve -> Retire
```

## 5. Audit Deliverables

1. Repository Inventory
2. File Inventory
3. Module Map
4. Function Map
5. Class Map
6. API Map
7. Data Flow
8. Dependency Map
9. CTH Capability Matrix
10. ZBMP Capability Matrix
11. OSAI Capability Matrix
12. Agent Responsibility Matrix
13. Agent Permission Matrix
14. Duplicate Matrix
15. Dead/Orphaned Code Matrix
16. Broken Path Matrix
17. Contract Matrix
18. Requirement Matrix
19. Test Matrix
20. Lifecycle Matrix
21. DELETE / KEEP / MERGE / DEPRECATE Matrix

## 6. Change Governance

Future changes should be evaluated through:

```text
Change
 -> Affected Files
 -> Affected Modules
 -> Affected Functions
 -> Affected APIs
 -> Affected Data
 -> Affected Tests
 -> Affected Lifecycle
 -> Risk
```

No change should be treated as isolated without impact evidence.

## 7. Agent Governance

Known supporting capabilities include codebase analysis, GitHub research, artifact verification/preview, desktop automation, scheduling, local optimization and general research. Their responsibilities must be separated before parallel execution.

Recommended controlled capability sequence:

```text
READ -> AUDIT -> ANALYZE -> RESEARCH -> PLAN -> PATCH PREVIEW
-> TEST -> VERIFY -> HUMAN APPROVAL -> COMMIT -> PUSH
```

Agents should not silently cross from audit into write/commit/push authority.

## 8. Frontend / UI Status

The previous frontend/UI implementation has been cleared. UI/UX reconstruction is intentionally deferred until the source/product baseline is verified.

Future design direction:

- Left functional sidebar.
- Central AI workspace.
- No permanent right-side context panel.
- No endless vertical page scrolling.
- Important real-time information may use compact, draggable/sliding glass-like cards.
- Card quantity is driven by usefulness, not a fixed count.
- Secondary/detail functions move to function pages, drawers or modals.
- Design language is minimal, professional, information-first, restrained and operational.
- Motion and glass effects serve hierarchy/state, not decoration.
- Web and App should share one product/design language while adapting to platform constraints.

## 9. Information Architecture

```text
L0 Product
 -> L1 Module
 -> L2 Function
 -> L3 Workspace / Detail
 -> L4 Drawer / Modal
```

The system should avoid duplicated entry points and excessive nesting. A unified Case Library may serve as the information-asset entry point while preserving appropriate underlying data-model separation.

## 10. AI / Research Governance

External research should flow through:

```text
External Research
 -> Research Note
 -> Finding
 -> Evidence
 -> Applicability
 -> Internal Proposal
 -> Human Review
 -> Implementation
```

Open-source projects, Apple ecosystem research, UI/UX/rendering/state-management research and Xiaohongshu-related engineering research are references for learning, not automatic code import.

## 11. Historical / Legacy Items

Historical capabilities and labels such as SISA, DCC and AIDRH must be inventoried and evidence-checked before any KEEP/MERGE/DEPRECATE/DELETE decision. Names alone are not grounds for removal.

## 12. Current Gate

The immediate gate is:

```text
SOURCE FACT BASELINE
        -> PRODUCT CAPABILITY BASELINE
        -> ARCHITECTURE / BOUNDARY BASELINE
        -> RISK BASELINE
        -> LIFECYCLE BASELINE
        -> HUMAN REVIEW
```

Only after review should cleanup, Core consolidation, UI system reconstruction or App/Web implementation proceed.
