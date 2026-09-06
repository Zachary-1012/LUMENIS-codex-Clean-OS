# System App Product Boundaries V1

## Purpose
Establish stable product/capability boundaries for future ecosystem composition without restructuring the existing twin-repository architecture.

## Core principle
Capability can be composed, products can be separated, shared foundations remain shared, boundaries remain explicit, and cross-product exchange occurs through Contract/API/Event/Evidence/Validation.

## Core product domains
1. ZBC Intelligence — monitoring, events, risk, brand intelligence, KOL/KOC, reports and customer decision information.
2. Zachary AI — research, learning, knowledge, reasoning and general intelligence capabilities.
3. Observable + Authorized Decomposition — structured decomposition of observable/authorized platforms, systems, accounts, content and relationships.
4. AI Runtime Center — local/cloud providers, model routing, health, heartbeat, fallback and runtime state.
5. AI Evaluation — benchmarks, quality evaluation, regression, human feedback and evidence.
6. Visual Intelligence — decision-oriented visualization, graph, timeline, interaction and semantic motion.
7. Research / Knowledge — sources, cases, resources, knowledge and learning assets.
8. DCC / AI Development Console — development, audit, runtime verification, tests, evidence and delivery controls.

## Productization model
Do not create 20–30 isolated applications. Treat the 8 domains as stable product boundaries and compose smaller App surfaces from them. Shared capabilities may include Contract, Runtime, Evidence, identity/access primitives, UI tokens and reusable components. Shared capability does not permit internal implementation leakage or business-rule ownership to cross boundaries.

## Boundary rule
A product boundary answers: what this product owns, what it consumes, what it exposes, and what it must never change. It is not equivalent to total data isolation.

Zachary ↔ Contract ↔ ZBC is bidirectional capability exchange; neither product directly modifies the other's internal implementation or business Truth.

## App decomposition hierarchy
Platform/ecosystem → product domain → subsystem → module → function → state → data/interaction.

Account decomposition and platform decomposition are one capability family, with the security boundary defined as Observable + Authorized. No credential theft, private-data access, privilege bypass, security bypass or unauthorized intrusion is implied.

## UI / UX / visualization boundary
UI is the visible product surface. Visualization is an intelligence interface, not decoration. Preserve hierarchy, direct manipulation, drill-down, cross-filtering/highlighting where appropriate, semantic continuity, accessibility, responsive behavior and performance. Motion communicates cause, state or continuity only.

## Personalization
Presentation, interaction style, information density and workflow preference may adapt. Security, permission, Truth, compliance, Contract and core business physics may not change through personalization.

## Evolution after launch
The architecture is intentionally update-friendly. Core foundations remain stable while UI, visualization, AI models/providers, research, decomposition and other capability surfaces may iterate independently behind compatible Contracts. New Apps should compose existing capabilities rather than duplicate foundations.

## Recommended initial App set
Intelligence, Research, Decompose, Visual, AI Runtime, AI Evaluation, Control/DCC, with Report/Case Library/Resource/Notification as workspaces or composable surfaces until independent productization is justified.

## Definition of Done
- boundary and ownership documented;
- dependencies and shared capabilities mapped;
- Contract/API/Event boundaries explicit;
- no duplicate foundation introduced;
- runtime, UI, accessibility, performance and regression checks defined;
- evidence captured before PASS;
- launch and post-launch updates remain backward-compatible unless an explicit versioned Contract change is approved.
