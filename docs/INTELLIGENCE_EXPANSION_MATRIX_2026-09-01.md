# Z-Brand-Core Intelligence Expansion Matrix — 2026-09-01

> Research / architecture baseline. This document is additive. It does not change the production collector, subject rules, EventGraph, AI filter, or deployment path.

## 1. Research conclusion

The useful pattern from Xiaohongshu's recent evolution is not to copy individual features. The reusable abstraction is:

`content -> context -> behavior -> event -> risk -> impact -> action`

For Z-Brand-Core, the missing intermediate layer is **Context Intelligence**: understanding a note together with comments, visual/OCR evidence, related notes, and time context before event inference.

The second missing layer is **Behavior Intelligence**: repeated interaction patterns, concentration, escalation, and cross-content signals. It must remain a risk signal rather than a legal conclusion.

## 2. External research map

### Xiaohongshu / RedNote product evolution

- 2024: search and commercial decision support continued to strengthen.
- 2025: 点点 moved into comment/context interaction and progressively became an AI understanding/search surface.
- 2026: community governance and proactive protection became more prominent, including pre-action warning and multi-surface protection concepts.

Learning target: context retrieval, summarization, multi-note reasoning, comment understanding, and proactive safety UX — not platform-specific implementation.

### Open-source model research

RednoteAI public research includes:

- `dots.llm1`: large MoE LLM research; useful as an architecture/reference candidate.
- `dots.vlm1`: multimodal reasoning; relevant to image + text note understanding.
- `dots.mocr`: multimodal OCR/document/web parsing; relevant to posters, screenshots, menus, price cards, store signage, and image-heavy notes.
- `dots.tts`: not a current Core priority, but relevant to future voice interaction.

Research source: https://github.com/RednoteAI/RednoteAI

The model layer must remain pluggable. No external model becomes a production authority merely because it originates from Xiaohongshu research.

### Governance / legal baseline

The architecture must account for:

1. Network-data collection impact and service stability.
2. Data minimization and anonymization where personal information is not necessary.
3. Publicly available personal information being processed only within a reasonable scope and lawful basis.
4. Model inputs, logs, prompts, and inference outputs requiring access control, retention limits, and auditability.
5. If a future service itself provides public generative-AI capability in China, additional generative-AI, algorithm, content-safety, and filing/security-assessment obligations may apply depending on the service characteristics.

Primary references:
- https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm
- https://www.cac.gov.cn/2024-06/14/c_1720043894161555.htm
- https://www.cac.gov.cn/2025-02/14/c_1741233507681519.htm
- https://www.cac.gov.cn/2026-08/12/c_1788195297373459.htm

## 3. Z-Brand-Core target architecture

```text
Collector / Adapter
        |
        v
Normalizer + Quality
        |
        v
Subject Intelligence  ---- hard boundary; remains authoritative
        |
        v
Content Intelligence
        |
        +---- Image/OCR/VLM shadow evidence
        |
        v
Context Intelligence  <--- NEW SHADOW LAYER
        |
        v
Behavior Intelligence  <--- NEW SIGNAL LAYER
        |
        v
Event Intelligence / EventGraph
        |
        v
Risk Intelligence
        |
        v
Impact / Decision / Reporting
        |
        v
Evidence + Governance
```

## 4. What is being added now

### `context_intelligence.py`

A deterministic, dependency-light shadow engine that:

- accepts an existing note and optional comments;
- extracts bounded intent/event/sentiment signals;
- produces comment-derived question/complaint/recommendation/comparison counts;
- emits explainable event candidates;
- generates a small topic fingerprint;
- records provenance and explicitly states that no external call or PII enrichment occurred;
- can convert its output into non-authoritative EventGraph metadata.

**It is not wired into the production path yet.** This is intentional.

## 5. Integration gates

### Gate A — Shadow

Run Context Intelligence beside the current pipeline. Do not change accepted/rejected decisions.

### Gate B — Evaluation

Compare event candidates against a manually reviewed sample. Track precision, false positives, missed events, and human corrections.

### Gate C — EventGraph proposal

Only after evaluation, allow candidates to create *proposals* rather than direct relations.

### Gate D — Production

Production integration requires regression tests, data-retention review, and a feature flag. Existing `subject_hit()` / `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` remain first-order authority.

## 6. App / Web / Server research target

Do not split the current application prematurely. The target architecture is:

`App/Web clients -> API layer -> application services -> workers -> data/AI services`

Current Flask/Blueprint architecture remains the production implementation. Server decomposition is a future target, not a P0 refactor.

Client surfaces should expose:

- note intelligence;
- event timeline;
- evidence chain;
- risk explanation;
- governance status;
- model/provenance metadata where appropriate.

## 7. Data objects to converge toward

`Subject -> Content -> Context -> Behavior -> Event -> Risk -> Impact -> Evidence -> Governance`

The long-term objective is to store durable analytical features rather than unnecessary identity information.

## 8. Explicit non-goals

- No automatic legal determination.
- No automatic cyberbullying accusation.
- No bypass of Xiaohongshu anti-abuse/risk controls.
- No automatic replacement of current subject filtering.
- No automatic adoption of third-party model outputs as truth.
- No production server decomposition in this change.
- No collection expansion merely to increase volume.

## 9. Next engineering sequence

1. Keep Context Intelligence in shadow mode.
2. Add evaluation fixtures covering positive/negative/neutral notes and comment-driven event emergence.
3. Add multimodal adapter interface for OCR/VLM without selecting a production model.
4. Add Behavior Intelligence as a separate signal object.
5. Add EventGraph proposal queue rather than direct auto-linking.
6. Add evidence/provenance persistence.
7. Add Governance Gate for source, purpose, retention, PII level, and model use.
8. Only then consider production feature gates.

## 10. Current baseline

Base commit: `643e0494ecea96af360bd2bc74fb67b03745581b`

Research branch: `research/context-intelligence-20260901`

This branch is intentionally isolated from `main` until review and regression validation are complete.
