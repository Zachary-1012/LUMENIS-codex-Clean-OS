# Design Philosophy: 芥子·须弥 × 太极 × 一二三 V1

## Scope
This is a design-philosophy and systems-evolution reference, not a business rule or runtime dependency.

## Conceptual model
- 芥子：local, concrete, real production and individual signals.
- 须弥：whole, abstract, reusable capability and knowledge.
- 一：shared order — Contract, Truth, Security, Compliance, Evidence, core physics.
- 二：complementary directions — learning/production, abstraction/concretion, internalization/externalization.
- 三：relationship and generation — feedback, evaluation, validation and contract-mediated exchange.
- 万物：data, cases, user behavior, knowledge, AI capability and product outcomes generated through the loop.

The Buddhist 芥子纳须弥 metaphor and the Daoist 道生一、一生二、二生三、三生万物 formulation are distinct traditions. This document intentionally combines them only as a modern systems analogy; it does not attribute one tradition's concepts to the other's original text.

## System loop
REALITY → local signal (芥子) → ZBC production → feedback/evaluation → abstraction → Zachary capability (须弥) → Contract-mediated capability delivery → ZBC → new reality.

The loop is bidirectional but boundaries remain explicit. Capability may flow; ownership, business Truth, security and permissions do not blur.

## UI / UX / Visualization / Motion
UI is the visible surface where the system's abstract whole becomes a concrete local experience. Visualization should progressively reveal the relationship between signal, context, event, risk, evidence and decision rather than decorate the dashboard.

Principles:
1. One screen should communicate one decision story at the highest level; details are progressively disclosed.
2. Use direct manipulation: selection, filtering, drill-down, cross-highlighting and context-preserving navigation where appropriate.
3. Preserve data mapping during transitions: an object representing a measure should remain semantically attached to that measure while moving/changing.
4. Motion must communicate cause, state or continuity, never exist as decoration. Stage changes progressively and avoid excessive simultaneous movement.
5. Use consistent interaction language across modules and preserve spatial/semantic continuity.
6. Never use color as the sole carrier of state; combine labels, shape, position, iconography or texture as appropriate.
7. Accessibility and keyboard operability are first-class requirements.
8. Performance is part of UX: remove redundant visuals and avoid unnecessary animation or data refresh.
9. Mobile layouts must preserve hierarchy and decision paths, not merely shrink desktop components.

## Dynamic visualization model
Use a semantic state model:
INPUT → DETECTED → VERIFIED → CLASSIFIED → CORRELATED → RISK/IMPACT → DECISION → ACTION → FEEDBACK.

Dynamic visuals should reveal state transitions and evidence. A visual state must never imply a fact that the underlying data/evidence does not support.

## Personalization boundary
"形可变，道不可移": presentation and interaction style may adapt to user behavior; security, permissions, Truth, compliance, Contract and core business physics must not change because of personalization.

## Architecture constraint
Do not create a new philosophy framework merely to implement this document. Reuse existing UI tokens, component primitives, visualization modules, runtime telemetry and Contract layers. Add only the smallest mapping/metadata layer required to connect the concepts.

## Evidence and research basis
Current dashboard/data-visualization guidance supports direct interaction, filtering/drill-down, preserving visual mappings during motion, meaningful animation, reducing chart junk, accessibility, and responsive layouts. See Microsoft Learn: Data visualization style guidelines; Power BI dashboard design tips; interactive dashboard/filtering guidance.

## Definition of Done
- concept mapped to existing modules;
- UI/UX/visualization/motion mapping documented;
- no business Truth changes;
- no duplicate framework introduced;
- interaction and visualization regression tests defined;
- accessibility/performance checks defined;
- runtime Evidence captured before PASS.
