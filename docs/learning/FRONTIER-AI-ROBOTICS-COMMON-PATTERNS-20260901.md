# Frontier AI / Robotics Common Patterns — 2026-09-01

## Research objective

Study advanced agentic AI, scientific-agent, robotics and embodied-AI systems for reusable architectural patterns. This is pattern research only; no third-party implementation is copied.

## Cases reviewed this cycle

### Persistent/proactive agents
Observed industry direction: agents are moving from short request-response tasks toward longer-lived execution, proactive follow-up and controlled autonomy.

**Reusable pattern:** explicit task state + permission scope + stop condition + resumability + evidence trail.

**Z-Brand implication:** collector/intelligence jobs should become resumable state machines, not opaque long-running loops.

### Agent benchmark systems
FrontierAgent/Terminal-Bench-style systems separate task registry, runner, isolation, scoring and result aggregation. Some runners use per-task subprocess isolation, timeouts and resumable progress.

**Reusable pattern:** capability evaluation must be reproducible, isolated and resumable.

**Z-Brand implication:** collection/context/event benchmarks should have task IDs, fixed inputs, deterministic scorers where possible, timeouts and resumable result stores.

### AI controlling physical/scientific devices
Recent embodied/scientific-agent work is converging on a model layer separated from hardware/tool adapters, with explicit safety evaluation before broader deployment.

**Reusable pattern:** model → capability/tool contract → constrained executor → evidence/result → evaluation.

**Z-Brand implication:** model providers, OCR/VLM engines and collectors should be replaceable adapters behind contracts; the model must never become the evidence authority.

### Embodied AI / robotics
The strongest common architectural idea is not humanoid hardware itself; it is closed-loop perception → planning → action → observation → correction.

**Z-Brand implication:** collection should evolve toward:

`observe → normalize → assess quality → infer → verify → act/recover → observe again`

rather than one-shot scraping.

## Cross-domain synthesis

The common denominator across advanced AI agents and robotics is **closed-loop, stateful, evidence-aware autonomy**.

Four primitives should therefore become first-class in Zachary systems:

1. **State** — what is currently happening and what remains.
2. **Capability contract** — what a component is allowed to do.
3. **Observation/evidence** — what actually happened.
4. **Evaluation/verification** — whether the result is good enough to promote.

## Guardrails learned from failures

Recent reports of autonomous-agent incidents reinforce that persistence and autonomy increase the need for evidence integrity, permission boundaries, monitoring and independent evaluation. Therefore:

- never let an agent modify its own evaluation criteria;
- never treat model confidence as proof;
- keep write/merge/deploy permissions outside the intelligence layer;
- preserve immutable-enough audit evidence;
- make stop/revoke/retry states explicit;
- separate simulation from real execution.

## Rejection list

Do not copy robotic control loops, agent scaffolds, benchmark code, proprietary prompts, platform-specific bypasses, credentials, selectors or security-sensitive techniques.

## Candidate Z-Brand experiments

1. resumable CollectionJob state machine;
2. observation/evidence envelope shared by Collector and Context;
3. capability adapters for OCR/VLM/LLM;
4. benchmark runner with timeout + resume + deterministic scoring;
5. recovery policy engine that only chooses from bounded, permitted actions.

All five require benchmark evidence before promotion.
