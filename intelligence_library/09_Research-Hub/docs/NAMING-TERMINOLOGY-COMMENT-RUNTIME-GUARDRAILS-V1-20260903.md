# Zachary OS / ZBC Naming, Terminology, Comment and Runtime Guardrails V1

Date: 2026-09-03
Status: normative cross-system contract
Scope: Zachary OS, Zachary OS AI, Z Brand Core, DCC and all future modules.

## 1. Canonical Names

Product family: Zachary OS (ZOS)
AI research subsystem: Zachary OS AI (ZOSAI)
Production subsystem: Z Brand Core (ZBC)
Development execution console: Development Command Console (DCC)
Repository architecture: Twin-Repo Architecture

Use repository names exactly as registered. Do not invent abbreviations in code or UI.

## 2. Responsibility Boundary

ZOS: product-family identity and shared principles.
ZOSAI: research, knowledge, AI, architecture, decisions and development intelligence.
ZBC: production collection, monitoring, events, insights, evidence, reports and runtime.
DCC: controlled development execution, task and audit bridge.

ZOSAI must not duplicate ZBC production business UI.
ZBC must not absorb ZOSAI research knowledge as uncontrolled runtime logic.

## 3. Canonical Vocabulary

Use one semantic term per concept:
Workspace, Domain, Page, Module, Capability, Component, Action, State, Route, Resource, Evidence, Event, Insight, Asset, Monitor, Collector, Capture, Normalizer, Dedup, Subject Rule, Navigation Resolver, Internal Browser, External Browser, AI Context, Report, Runtime, Health.

Avoid informal aliases in normative code, schemas, routes and UI labels.

## 4. Naming Rules

Code identifiers are stable English semantic identifiers.
Display labels are short and standardized Chinese/English pairs.
Do not encode vendor names into business concepts.
Do not create duplicate names for the same capability.

## 5. Comment Rules

Comments explain invariants, safety boundaries and non-obvious intent only.
Keep comments short: normally one sentence, one invariant.
Do not store chat history, temporary debugging notes or obsolete architecture inside code comments.

Preferred examples:
- "平台链接默认进入内置浏览器。"
- "主体规则是生产判断真相。"
- "仅用户主动操作允许外部打开。"
- "失败后进入熔断，不自动重试。"

## 6. Non-Negotiable Runtime Safety

New capability default: SAFE / DRY-RUN / SHADOW.

A new UI module must never implicitly activate a collector, scheduler, automation loop, account rotation or high-concurrency workflow.

Production activation requires registered scope, rate, concurrency, cooldown, retry limit, stop condition, circuit breaker and audit record.

## 7. Collection Safety

Every collection job must be bounded by item/time limits and have:
job_id, source, scope, requested_by, start_at, budget, concurrency, rate limit, cooldown, retry limit, circuit breaker, last_success_at and stop reason.

Do not use speed as a reason to bypass safety controls.

## 8. Platform Risk Handling

If a platform reports risk, restriction, challenge or abnormal behavior:
STOP new collection -> preserve state -> record signal -> open circuit -> require controlled recovery.

Never automatically increase concurrency, rotate accounts or rotate IPs to evade a platform restriction.

## 9. Subject Rules

Deterministic subject rules remain authoritative.
UI, AI and new modules cannot bypass or silently modify subject filters.

## 10. AI Governance

AI is assistive by default.
Safety and deterministic rules take precedence.
Important AI decisions should retain model version, prompt version, input reference, output, confidence, final result and human correction when applicable.

## 11. UI Governance

New modules inherit the unified ZBC UI/IA contract.
Reuse before extend; extend before create.
A new top-level route requires IA review.
A new component, icon or visualization requires registry entry.

## 12. Change Lifecycle

Request -> Capability Registry -> IA -> Safety Review -> Interaction -> Implementation -> Test -> Shadow/Dry-run -> Controlled Activation -> Production.

Rendering a page is not production readiness.

## 13. Enforcement

CI and static audit should flag terminology drift, unregistered routes, direct external navigation for monitored resources, unbounded collection, missing stop/circuit-breaker controls, subject-rule bypass, duplicate UI systems and obsolete comments.

## 14. Principle

The system may grow in capability, but not in semantic ambiguity, UI fragmentation or operational risk.
