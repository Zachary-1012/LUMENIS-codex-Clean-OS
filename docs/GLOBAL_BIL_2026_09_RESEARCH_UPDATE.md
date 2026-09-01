# Global BIL｜2026-09 Research Update

## Purpose

This update records the latest external research signals that affect the Global Brand Intelligence architecture. It is research-only and does not alter production behavior.

## New evidence

### 1. AI is becoming a discovery and decision layer

NIQ reported in August 2026 that nearly three-quarters of shoppers use AI for product discovery. Its May 2026 research also describes AI as increasingly influencing evaluation, comparison and selection, with agentic commerce beginning to discover, evaluate and purchase on behalf of consumers.

Implication:
- AI Discovery must be a first-class BIL domain.
- AI visibility must be measured separately from SEO and Social.
- Product attributes, reviews, creator content and other evidence sources need to be traceable because they can influence AI recommendations.

### 2. Social discovery is increasingly connected to commerce

NIQ reported in June 2026 that nearly one in three Western consumers purchase products first discovered on social platforms. Its global commerce research describes the convergence of content, creators, commerce infrastructure and AI.

Implication:
- Social → Interest → Consideration → Product → Commerce must be modeled as a relationship chain.
- UGC volume alone is insufficient.
- Commerce evidence must be time-stamped and market-specific.

### 3. Brand Intelligence is becoming a coverage problem

G2's 2026 Brand Intelligence review identifies fragmented coverage across TikTok, Reddit, AI search and private communities as a major practical challenge.

Implication:
- BIL must retain channel/platform provenance.
- UNKNOWN must not be treated as MISSING.
- Evidence quality and coverage must be separate scores.

### 4. Search, social, shopping and GenAI are converging

Brandwatch's Search Intelligence describes monitoring across traditional search, shopping, social and generative AI in 150+ countries.

Implication:
- Search Intelligence should feed BIL as a cross-channel signal layer.
- The architecture should not assume one platform is the canonical consumer truth.

### 5. Creator selection is shifting from reach to relevance

Current 2026 industry reporting emphasizes micro/niche creators, cultural relevance, community alignment, credibility and content quality over follower count alone.

Implication:
- Creator Quality must not equal follower count.
- Creator Value should include relevance, authenticity, community density, brand fit, content quality, UGC generation and commercial signals.

### 6. AI visibility is moving toward closed-loop optimization

Adobe's June 2026 Brand Visibility announcement describes AI visibility measurement combined with owned-channel signals, competitive share of voice, citations and optimization actions across major AI surfaces.

Implication:
- AI Discovery should eventually support Observation → Diagnosis → Recommendation → Action → Measurement.
- Production integration remains gated until staging/shadow validation passes.

## Architecture decisions confirmed

```text
Social Heat
    !=
Brand Health
    !=
Business Momentum

SEO Visibility
    !=
Social Visibility
    !=
AI Visibility

UGC Volume
    !=
UGC Quality
    !=
Commerce Impact

Creator Reach
    !=
Creator Value

UNKNOWN
    !=
MISSING
```

## Required evidence fields

Every dynamic observation should retain, when available:

- brand_id
- market
- platform
- observation_date
- published_date
- source
- evidence_type
- metric_name
- metric_value
- unit
- methodology
- confidence
- collection_method
- analysis_version

## Research guardrails

1. Do not fabricate platform counts, follower counts, UGC counts, sales, purchase intent or store data.
2. Public case-study metrics are evidence for the specific case, not universal benchmarks.
3. Preserve market, time and platform context.
4. Separate fact, observation, interpretation, hypothesis and recommendation.
5. Respect platform terms and access controls.
6. Do not write research observations into production CTH-POMS facts without validation.

## Next execution

1. Enumerate the real ZBMP brand inventory from repository assets.
2. Resolve brand identities and aliases.
3. Populate the 17-domain capability matrix with evidence-backed states.
4. Select S/A benchmark brands by mechanism relevance, not popularity.
5. Import validated observations into staging only.
6. Run shadow comparison before any production adapter.
