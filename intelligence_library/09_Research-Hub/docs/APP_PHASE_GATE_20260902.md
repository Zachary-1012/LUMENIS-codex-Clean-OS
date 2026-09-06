# App Phase Gate｜2026-09-02

## Status
PLANNED / BLOCKED UNTIL CORE RELEASE GATE

## Principle
App development starts only after Zachary AI Runtime and Z-Brand-Core pass the agreed Release Gate. The App is a client layer, not a second AI/business core.

## Required preconditions

1. Zachary Model Independence P0 completed.
2. Provider Router / Adapter / Policy / Verification stable.
3. ZBC stable API and production Runtime contract.
4. Unified Ingestion implemented and tested.
5. Unified Resource Library + Zachary retrieval contract verified.
6. Context Isolation verified.
7. Terminology standardization verified across UI/API/DB/config/prompt/logs.
8. Runtime Evidence and regression tests complete.
9. Dual-repository cross-audit passed.
10. Release Gate approved.

## App architecture target

```text
Zachary-OS-AI
  └─ AI Runtime / Memory / Resource / Provider / Tools
          ↓
Z-Brand-Core
  └─ Production business logic / API / data
          ↓
     Stable API Contract
          ↓
     App Client Layer
       ├─ iOS
       ├─ Android (later as required)
       └─ Web/desktop clients as required
```

## Hard boundary

- App must not duplicate Zachary Runtime.
- App must not duplicate ZBC business rules.
- App must not directly bind to a specific model provider.
- App must consume stable contracts.
- App personalization may alter presentation/style only; it cannot alter facts, permissions, business rules, risk logic, database constraints, Runtime semantics, or Evidence.

## First App scope

- Zachary conversation / task entry
- ZBC dashboard and production functions required for the first release
- Resource-aware AI answers through Zachary
- Ingestion entry points defined by the unified Ingestion contract
- Task status / Evidence / result presentation
- User style preferences
- Authentication and permission boundaries
- Offline/degraded-state handling where applicable

## Release rule

Do not start broad UI implementation before the core contracts stabilize. First produce API Contract + interaction map + permission model + device capability matrix, then implement the client.

## Research principle

Use current open-source AI-runtime and governed-agent patterns as references, but do not copy architecture blindly. Zachary remains the system-specific source of truth.
