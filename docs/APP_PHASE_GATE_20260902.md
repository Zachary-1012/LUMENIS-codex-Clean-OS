# App Phase Gate｜2026-09-02

## Status
PLANNED / BLOCKED UNTIL CORE RELEASE GATE

App development starts only after Zachary AI Runtime and Z-Brand-Core pass the agreed Release Gate. The App is a client layer, not a second AI/business core.

## Preconditions

- Zachary Model Independence P0 completed.
- Provider Router / Adapter / Policy / Verification stable.
- ZBC stable API and production Runtime contract.
- Unified Ingestion implemented and tested.
- Unified Resource Library + Zachary retrieval contract verified.
- Context Isolation verified.
- Terminology standardized across UI/API/DB/config/prompt/logs.
- Runtime Evidence and regression tests complete.
- Dual-repository cross-audit passed.
- Release Gate approved.

## Target architecture

Zachary-OS-AI → AI Runtime / Memory / Resource / Provider / Tools
→ Z-Brand-Core → Production business logic / API / data
→ Stable API Contract
→ App Client Layer (iOS first; Android/Web/desktop as required)

## Hard boundaries

- No duplicate Zachary Runtime in App.
- No duplicate ZBC business rules in App.
- No direct App binding to a specific model provider.
- App consumes stable contracts only.
- Personalization changes presentation/style only; it cannot change facts, permissions, business rules, risk logic, database constraints, Runtime semantics, or Evidence.

## Initial App scope

- Zachary conversation/task entry
- Required ZBC dashboard/production functions
- Resource-aware Zachary answers
- Unified Ingestion entry points
- Task status / Evidence / result presentation
- User style preferences
- Authentication/permission boundaries
- Offline/degraded-state handling where applicable

## Implementation gate

Before broad UI coding: freeze API Contract, interaction map, permission model and device capability matrix. Then implement client against those contracts.

Use current open-source AI-runtime and governed-agent patterns as research references; do not copy external architecture blindly.
