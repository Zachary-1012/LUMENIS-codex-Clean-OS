# Global BIL — Creator → AI Discovery Intelligence v1

> 2026-09-01
> Status: research/data-contract layer only; no production cutover

## Purpose

Model the path from creator content to AI-mediated brand/product discovery without conflating reach, engagement, trust, citation, recommendation, or commerce.

## Core Graph

Creator → Content → Audience Response → Search/Discovery → AI Retrieval/Citation → AI Recommendation → Consideration → Commerce Signal → UGC → Brand Health → Learning

## Entities

### Creator
- creator_id
- canonical_name
- market
- language
- platform
- category
- audience_profile

### Creator Content
- content_id
- creator_id
- brand_id
- product_id when known
- platform
- published_at
- content_type
- topic
- claim_type
- engagement_snapshot
- evidence_ref

### AI Discovery Observation
- observation_id
- query
- query_intent
- market
- language
- engine/model
- observed_at
- brand_mentioned
- recommendation_flag
- position when observable
- framing
- competitor_co_mentions
- citation_present
- citation_sources
- evidence_ref

### Creator→AI Link
Only create when evidence supports the relationship.
- creator_content_id
- ai_observation_id
- linkage_type: direct_citation / source_match / thematic_match / unknown
- linkage_confidence
- evidence_ref

## Metrics

Never collapse these into one score:

- Creator Reach
- Creator Engagement
- Creator Relevance
- Creator Trust Proxy
- UGC Generation
- AI Mention Rate
- AI Recommendation Rate
- AI Citation Rate
- AI Share of Voice
- AI Position
- Commerce Signal

## Evidence Rules

1. A creator being mentioned by an AI answer does not prove causal influence.
2. A citation to a creator page does not prove that the creator caused the recommendation.
3. Thematic similarity is not direct attribution.
4. AI output is an observation, not ground truth.
5. Dynamic AI observations must retain timestamp, engine/model, language and query.
6. Follower counts are snapshots, not immutable brand attributes.
7. Commerce outcomes must retain market, channel and observation window.
8. Unknown must never be silently converted to Missing.

## Analysis Layers

FACT
→ OBSERVATION
→ LINKAGE
→ INTERPRETATION
→ HYPOTHESIS
→ RECOMMENDATION

Only FACT and directly supported OBSERVATION may be presented as established evidence.

## Global→Local Application

Compare the same mechanism across:
- country
- city
- language
- platform
- creator tier
- product category
- cultural context

Do not assume transferability. Record:
- transferable
- conditionally transferable
- local-only
- unknown

## ZBMP Integration Boundary

Reuse existing ZBMP Brand Entity, Knowledge, Case, Intelligence and Evidence assets.

Do not create a parallel brand master.
Do not modify CTH-POMS production scoring.
Do not let external AI override existing subject filters or core event logic.
Run new Creator→AI observations in staging/shadow mode first.

## Immediate Research Set

Prioritize mechanisms where creator content plausibly affects discovery:
- creator-led product discovery
- niche community authority
- creator-to-commerce storefronts
- creator content cited by AI/search
- product reviews used as AI evidence
- editorial/creator crossover
- local-language creator content affecting local AI discovery
- UGC that becomes persistent product knowledge

## Acceptance Criteria

A record is ingestion-ready only when its entity, observation time, market/platform, evidence and confidence are available. Any causal claim requires stronger evidence than co-occurrence.
