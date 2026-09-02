# AI Frontier Common Primitives — 2026-09-01

## Scope
AI-only research note for synchronization into the fourth-library AI knowledge layer. No Z-Brand collection implementation is changed by this document.

## Research finding
Recent agentic AI and embodied/robotic systems increasingly converge on a workflow rather than a model-only architecture:

Observation → State → Capability/Tool → Action → Evidence → Evaluation → Recovery

The common engineering primitives are:

1. **State** — explicit task/runtime state that survives multi-step execution and interruption.
2. **Capability contract** — tools/devices/services exposed through stable interfaces instead of model-specific wiring.
3. **Evidence** — observations, tool outputs and provenance are first-class runtime artifacts.
4. **Evaluation** — behavior is scored independently from the model's own explanation.
5. **Recovery** — timeout, pause, retry, rollback or escalation are explicit states.
6. **Guardrails** — authority, permissions, sequencing and safety boundaries are enforced outside model intent.
7. **Observability** — runtime traces are required for production diagnosis and capability promotion.

## Frontier cases reviewed

- Anthropic Model Hardware Standard / robotics research: common interface between AI agents and programmable physical devices; capability abstraction and safety boundaries are central.
- Anthropic robotics experiments: models operate through different control abstractions, showing the importance of separating model reasoning from executable control policy.
- Agent engineering surveys/industry reports: production agents emphasize observability, evaluation, state, tools and memory rather than model choice alone.
- Long-horizon / continuous-agent research: persistent state, interruption recovery and log-first diagnostics are recurring design themes.
- Agent safety incidents: evidence integrity, permission boundaries, monitoring and independent evaluation become more important as autonomy increases.

## Zachary AI interpretation

Do not copy any implementation. The reusable abstraction for Zachary AI is:

`Model × State × Capability × Evidence × Evaluation × Recovery`

This is a candidate foundation, not yet a promoted global capability.

## Promotion gate

AI research → internal experiment → benchmark → domain validation → cross-domain validation → DCC governance gate → Zachary AI capability candidate.

A capability must be useful beyond one product/domain before entering the global layer.

## 4-library synchronization boundary

This note is intended to be synchronized **only as AI knowledge** into the fourth library. It must not transfer Z-Brand private business logic, platform-specific collection logic, credentials, user data, or third-party source code.
