# Zachary OSAI × ZBC UI / IA / Interaction Research Contract V1

Date: 2026-09-03
Status: research/architecture contract

## Purpose

This document records the research-derived product design rules that OSAI should use when proposing, generating or auditing UI and interaction changes for the twin-star system.

## 1. Architecture Boundary

OSAI is the research, knowledge, AI, experiment and decision layer. ZBC is the production/runtime/data/evidence layer. UI recommendations must respect this boundary.

OSAI may define:
- information architecture principles
- capability models
- interaction contracts
- research findings
- visualization decision patterns
- design-system recommendations
- AI-assisted design audits

ZBC owns:
- production routes
- templates and components
- runtime behavior
- collection and evidence flows
- production visual regression

## 2. Research Rule

Every design recommendation must distinguish:
1. observed source evidence
2. inferred principle
3. proposed adaptation
4. implementation constraint

Do not copy brand visuals from luxury/fashion references. Extract the underlying UX pattern: hierarchy, restraint, discoverability, search, filtering, context, service, trust and continuity.

## 3. Product Design Direction

Target language: Editorial Intelligence × Quiet Luxury × Operational UI.

The interface should feel considered and premium without becoming a storefront. Information hierarchy and speed of operation take precedence over visual novelty.

## 4. Icon Research

Adopt a semantic icon registry pattern inspired by modern open icon systems such as Lucide. Business code must depend on semantic aliases, not vendor icon names.

Required qualities:
- thin line construction
- consistent optical size
- consistent stroke behavior
- semantic clarity
- restrained use
- accessible labels/tooltips when icon-only

Potential source libraries are references only; licensing and asset provenance must be checked before bundling.

## 5. Component Research

Use headless/composable principles inspired by Radix: accessibility, functionality, interoperability, composability and customization. Component behavior should be defined independently from presentation so the same semantic capability can adapt to Web/App/Mini Program.

## 6. Interaction Model

The system should favor progressive disclosure:
summary -> preview -> detail -> evidence -> action.

Context must survive transitions: selected entity, filters, time range, scroll position, source and investigation state.

## 7. Visualization Research

Every visualization must answer a question. Approved categories:
Trend, Delta, Timeline, Relationship, Heatmap, Flow, Risk Field, Activity Pulse, Distribution.

Each chart requires:
- primary question
- metric definition
- baseline/comparison
- data freshness
- interaction behavior
- loading/empty/error/stale states
- accessible textual summary where appropriate

Motion is reserved for comprehension of change or system state.

## 8. Luxury / Fashion Adaptation

Research into high-end digital experiences should prioritize:
- clear category and global navigation
- strong search and filtering
- editorial storytelling without sacrificing task completion
- product/entity context
- service and trust signals
- deliberate whitespace
- consistent site-wide interaction
- continuity between discovery, evaluation and action

These patterns are relevant to Brand Intelligence because users often investigate brands through multiple evidence sources before making a judgment. The interface therefore needs both editorial depth and operational speed.

## 9. Domain Interaction Contracts

Monitoring: observe -> preview -> inspect -> capture -> evidence.
Events: detect -> timeline -> related entities -> evidence -> impact/risk -> action.
Brand: identity -> content -> audience -> creators -> events -> benchmark -> insight.
KOS: profile -> content -> propagation -> audience -> comments -> monitoring -> suggestion/reply.
Evidence: source -> capture -> provenance -> associations -> decision context.
Report: insight -> evidence -> output -> export/share.
System: health -> runtime -> collector -> AI -> data -> auth -> permissions.
Browser: monitored resource -> Internal Browser -> capture -> evidence -> return to origin.
Podcast: show -> episode -> research -> idea -> guest -> audience -> performance -> assets.

## 10. Future-Module Rule

A new module must query the capability registry before creating UI. Reuse existing capabilities first, extend adjacent capabilities second, create new capability only when necessary. New top-level navigation requires explicit IA review.

## 11. Web/App/Mini Program

Maintain one semantic information model. Adapt density and task scope by surface rather than duplicating the product. Full investigation belongs on Web; focused action and monitoring on App/PWA; lightweight task/alert/result flows on Mini Program.

## 12. Audit Requirements

OSAI design audits must inspect:
- route ownership
- page/module hierarchy
- icon ownership
- component reuse
- interaction states
- visualization semantics
- responsive behavior
- accessibility
- external navigation behavior
- Internal Browser integration
- evidence continuity
- visual regression coverage

## 13. External Research References

Lucide demonstrates a structured icon metadata model and semantic categories. Radix demonstrates composable, accessible interaction primitives. Baymard's luxury-goods UX research is useful for extracting navigation, search, filtering and site-wide interaction patterns from high-end commerce experiences. These sources inform patterns; they do not replace direct usability validation on ZBC.

## 14. Definition of Done

A proposed UI system is ready when a new capability can be added without introducing a parallel navigation hierarchy, duplicate component family, duplicate icon language, duplicate state model or duplicate responsive rules.
