# Content Intelligence Specification v1

> ZBMP / Z-Brand-Core 内容传播智能中枢架构基线
>
> Research ID: R-2026-CONTENT-0001
> Case seed: CASE-2026-CONTENT-0001
> Status: SPECIFICATION / SHADOW-CANDIDATE
> Owner: Z-Brand-Core
> Research / Benchmark / Shadow Owner: AI-Development-Research-Hub
> Engineering Control: Development-Command-Console
> Mobile Surface: SICI-Core

## 1. Product Definition

Content Intelligence is not an AI copywriter. It is a brand content strategy and decision capability that converts brand context, platform context, time/seasonal context, creative assets, audience intent and observed topic signals into an auditable content strategy, candidate content, pre-publication review and post-publication learning data.

Core loop:

```text
Context / Assets
  -> Understanding
  -> Strategy
  -> Topic / Emotion / Audience Matching
  -> Candidate Generation
  -> Review / Gate
  -> Publish
  -> Performance Feedback
  -> Case / Benchmark
  -> Shadow Learning
  -> Capability Candidate
```

AI must remain an augmentation layer. It cannot independently promote an unverified strategy, trend claim, performance claim or production rule.

## 2. Product Boundary

### Z-Brand-Core owns

- Brand / client / competitor context
- Content strategy business logic
- Content / topic / campaign business entities
- Platform-facing content intelligence
- Production-facing strategy and review surfaces
- Performance records and business outcomes

### AI-Development-Research-Hub owns

- Research records
- Case library
- Benchmark definitions
- Shadow-learning lifecycle
- Capability registry and promotion evidence

### Development-Command-Console owns

- Change audit
- Task contract
- Evidence
- Test / release gates
- Permission and rollback controls
- Cross-repository compatibility verification

### SICI-Core owns

- Mobile workflow and interaction surface
- Device-constrained editing/review experience

No new fifth Core is introduced.

## 3. Domain Model

Minimum entities:

```text
ContentContext
ContentAsset
ContentStrategy
EmotionProfile
AudienceProfile
TopicCandidate
TrendSignal
VisualNarrative
ContentCandidate
ContentReview
ClientExplanation
PublicationRecord
PerformanceRecord
ContentCase
Benchmark
```

### ContentContext

```yaml
id: string
brand_id: string
campaign_id: string|null
platform: string
publish_window: datetime|null
season_node: string|null
business_goal: string
source: manual|import|monitoring|campaign
```

### ContentStrategy

```yaml
id: string
content_context_id: string
content_type: string
primary_emotion: string
secondary_emotions: [string]
audience_intent: string
product_role: carrier|hero|supporting|proof|none
narrative_arc: [string]
visual_order: [string]
strategy_rationale: string
confidence: number|null
status: candidate|shadow|verified|rejected
```

### TopicCandidate

```yaml
id: string
platform: string
topic_text: string
topic_type: search|recommendation|emotion|scene|event|brand
trend_stage: emerging|rising|peak|cooling|expired|unknown
relevance_score: number
semantic_fit: number
brand_fit: number
season_fit: number
risk_score: number
source_refs: [string]
verified_at: datetime|null
```

### ContentReview

```yaml
content_candidate_id: string
platform_fit: pass|fail|not_verified
season_fit: pass|fail|not_verified
brand_fit: pass|fail|not_verified
emotion_consistency: pass|fail|not_verified
visual_narrative: pass|fail|not_verified
topic_fit: pass|fail|not_verified
search_alignment: pass|fail|not_verified
commerciality: pass|fail|not_verified
risk: pass|fail|not_verified
decision: ready|needs_revision|blocked|not_verified
```

## 4. Strategy Engine

The first production-capable decision engine should evaluate at least:

```text
Node / Season
+ Brand
+ Product
+ Audience
+ Platform
+ Objective
+ Asset semantics
+ Emotion
+ Topic signals
+ Historical performance
```

Output is not one forced answer. Produce a small candidate set (normally 2-4) with explicit rationale and trade-offs.

Example strategy pattern from CASE-2026-CONTENT-0001:

```text
Early autumn
+ fragrance / niche fragrance
+ healing / emotional lifestyle
+ calm visual assets
+ koi visual as positive-luck cue
=> emotional lifestyle strategy
=> fragrance as emotional carrier, not hard-sell hero
=> visual arc: calm atmosphere -> positive-luck cue -> space -> fragrance -> memory
```

This case is a seed for validation, not evidence that the strategy will always outperform alternatives.

## 5. Topic / Tag Architecture

Do not model hashtags as a single popularity list.

Use layered classification:

```text
Reach / broad entry
-> vertical interest
-> emotion / lifestyle
-> season / scene
-> brand / proprietary
```

Topic ranking should combine relevance, recency, trend stage, audience fit, platform fit, brand fit and risk. A topic can be popular but unsuitable.

The system must never promise that a tag guarantees entry into any platform traffic pool. Traffic-pool behavior is not treated as a deterministic business rule.

## 6. Visual Narrative

Assets are interpreted as narrative units rather than only ranked by aesthetic score.

Minimum roles:

```text
Hook
Emotion Establishment
Transition
Scene Reveal
Product / Proof
Detail
Closure
```

A non-product image may be retained when its narrative/emotional contribution is material. This prevents the incorrect rule that every opening image must directly show the product.

## 7. Client Explanation

Every material strategy recommendation should be explainable in business language:

- Why this positioning?
- Why this image order?
- Why this title?
- Why these topics?
- What is being optimized?
- What is verified versus inferred?

Provide both professional rationale and concise client-facing wording.

## 8. Review Gate

Pre-publication review must distinguish:

```text
READY
NEEDS_REVISION
BLOCKED
NOT_VERIFIED
```

AI-generated assumptions cannot be treated as verified trend facts or performance guarantees.

## 9. Learning / Benchmark

Each published content item should be eligible for a structured case after sufficient performance data exists:

```text
Input context
-> Strategy
-> Candidate
-> Published artifact
-> Actual performance
-> Outcome classification
-> What worked / failed
-> Reusable hypothesis
-> Shadow evaluation
```

Benchmarks should compare like-for-like cohorts where possible:

- same brand
- same platform
- same season/node
- same content type
- same objective
- different strategy variables

Do not infer causality from a single post.

## 10. Initial MVP

Phase 1 should implement only:

1. Content Intake / Context Card
2. Strategy Card
3. Emotion / Audience classification
4. Topic candidate ranking
5. Title / copy / tag candidates
6. Visual order recommendation
7. Pre-publication Review
8. Client Explanation
9. Case export to Research-Hub

Performance optimization and automated strategy promotion remain Phase 2+ capabilities.

## 11. Case 0001 Acceptance Criteria

The system must be able to represent the current real-world seed case:

```text
Node: early autumn / September
Category: fragrance / niche fragrance
Direction: emotional lifestyle
Primary emotion: calm / healing
Secondary cue: good luck
Product role: emotional carrier
Visual sequence: book/wood atmosphere -> koi -> venue -> space -> fragrance/details
Primary title: 入秋了，给自己留一点闻香的时间 🍂
Alternatives:
- 入秋第一份好运，藏在一缕香气里 🐟
- 用一缕木质香，收藏初秋的松弛
```

The implementation must preserve the distinction between a recommendation and a verified performance result.

## 12. Non-Goals

- No guaranteed traffic-pool claims
- No autonomous production-rule promotion
- No replacement of Z-Brand monitoring/event systems
- No duplicate DCC Evidence or Release implementation
- No duplicate Research-Hub Shadow infrastructure
- No new independent Core repository

## 13. Next Research / Build Gates

```text
R-2026-CONTENT-0001
 -> schema review
 -> architecture compatibility review
 -> 10-20 real case benchmark set
 -> shadow prototype
 -> DCC audit
 -> Z-Brand integration plan
 -> SICI mobile surface assessment
 -> controlled implementation
```

Promotion requires evidence from multiple real cases and must follow the existing Research-Hub and DCC governance protocols.