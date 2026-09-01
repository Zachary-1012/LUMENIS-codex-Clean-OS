# Z-Brand-Core｜Global BIL v1.1 Research Protocol

> 2026-09-01
> Scope: Global Brand Intelligence / ZBMP
> Status: Research + architecture protocol; no production cutover

## 1. Research conclusion

Global Brand Intelligence must measure more than social volume. The research layer combines brand health, consumer voice, social/UGC, creator quality, product, campaign, geography, channel/store, competitor, lifecycle and AI discovery visibility.

External benchmark evidence supports this direction:

- Kantar BrandZ 2026 combines brand value, consumer perceptions and global market data across 54 markets and 22,392 brands; its 2026 report highlights AI-shaped brand experiences and the importance of meaningful difference. 
- Kantar's Brand Tracking/Guidance model explicitly combines consumer research, search, social media and sales, with short-term campaign measures and long-term brand trajectory.
- Recent GEO research indicates that AI answer engines create a separate brand-discovery layer: visibility, citation share, source authority and recommendation framing should be measured independently from conventional search/social visibility.
- Recent creator/fashion cases reinforce that creator value cannot be reduced to follower count; relevance, community, authenticity, content quality and commercial outcomes matter.
- Creator-led commerce cases show a measurable path from UGC/community → storefront/product → purchase/AOV/revenue, so Social→Commerce is a first-class relationship.

## 2. Global BIL capability graph

```text
Brand Entity
 ├─ Brand DNA
 ├─ Market / Geography
 ├─ Consumer Voice
 │   ├─ Loud Voice
 │   └─ Quiet Voice
 ├─ Social Voice
 ├─ UGC
 ├─ Creator
 ├─ Product
 ├─ Campaign
 ├─ Community
 ├─ Store / Channel
 ├─ Competitor
 ├─ Brand Health
 ├─ Business Momentum
 ├─ Lifecycle
 └─ AI Discovery / GEO
```

## 3. Separate the three heat layers

Never collapse these into one score:

```text
Social Heat      = attention / conversation
Brand Health     = awareness / perception / consideration / intent / loyalty
Business Momentum = sales / demand / channel / store / commercial signals where evidence exists
```

A high Social Heat with weak Consumer Intent is a valid and important state, not a contradiction.

## 4. Consumer Voice model

```text
Consumer Voice
 ├─ Awareness
 ├─ Discovery
 ├─ Consideration
 ├─ Purchase Intent
 ├─ Ownership
 ├─ Satisfaction
 ├─ Advocacy
 ├─ Rejection
 ├─ Switching
 └─ Co-development
```

Separate:

```text
Loud Voice  = highly visible creators, viral posts, media
Quiet Voice = lower-volume consumer signals that may not trend
```

The system must never infer population-wide preference from the loudest social content.

## 5. Creator Quality model

Follower count is an input, not the conclusion.

```text
Creator Quality
 = f(
   Reach,
   Engagement,
   Relevance,
   Brand Fit,
   Authenticity,
   Community Density,
   Content Quality,
   UGC Generation,
   Consumer Intent,
   Commercial Signal
 )
```

Creator type taxonomy:

```text
celebrity / macro / mid / micro / niche / expert / athlete / artist / editor / tastemaker / community_leader / customer_creator
```

## 6. Social → Commerce graph

```text
Content
 ↓
Attention
 ↓
Interest
 ↓
Consideration
 ↓
Product Signal
 ↓
Purchase Intent
 ↓
Store / E-commerce
 ↓
Purchase Evidence
 ↓
Review / UGC
 ↓
New Consumer
```

Each edge must be evidence-backed or explicitly marked as an inferred relationship.

## 7. Global → Local Transfer

```text
Global Brand DNA
 + Local Culture
 + Local Consumer
 + Local Platform
 + Local Creator
 + Local Channel
 = Local Strategy Hypothesis
```

Never copy a global campaign mechanism into another market without testing cultural/platform fit.

## 8. Brand Learning loop

```text
Case / Evidence
 ↓
Mechanism
 ↓
Outcome
 ↓
Conditions of Success
 ↓
Failure Conditions
 ↓
Reusable Pattern
 ↓
New Brand Match
 ↓
Strategy Hypothesis
 ↓
Observed Outcome
 ↓
Feedback
 ↓
Pattern Revision
```

This is the long-term learning layer for ZBMP.

## 9. AI Discovery / GEO Intelligence

Add a separate visibility layer for AI answer engines.

Minimum observations:

```text
query
market
language
engine
brand_mentioned
rank_position
recommendation_status
citation_status
citation_source
source_type
competitor_mentions
sentiment/framing
answer_date
model/engine_version
```

Derived metrics:

```text
AI Mention Rate
AI Recommendation Rate
AI Citation Share
AI Share of Voice
AI Position
Competitor Co-mention Rate
Source Authority Mix
Framing Stability
```

Important: AI visibility is not the same as SEO ranking or social visibility.

## 10. Evidence contract

Every research claim should carry:

```text
claim_id
brand_id
market
platform
source_url/source_id
observed_at
published_at (if available)
evidence_type
raw_value
normalized_value
quality_status
confidence
method_version
```

Quality states:

```text
VERIFIED
HISTORICAL
INFERRED
CONFLICTED
UNKNOWN
NOT_VERIFIED
```

No invented numbers. Dynamic follower counts, UGC counts, store status and social volume must always carry capture time.

## 11. Research case taxonomy

Case studies should deliberately cover:

- Global luxury
- Designer fashion
- Outdoor
- Sports
- Beauty
- DTC
- Retail
- Community-led
- Creator-led
- Product-led
- Campaign-led
- Heritage revival
- Brand decline
- Brand comeback
- Market expansion
- Cross-cultural localization
- AI discovery / GEO
- Reputation crisis
- Social-to-commerce

The current benchmark set remains a seed, not a hard-coded whitelist.

## 12. Database boundary

Research data enters the BIL staging domain first.

```text
Web / public evidence / connected datasets
        ↓
Evidence
        ↓
Normalization
        ↓
Entity Resolution
        ↓
BIL Staging
        ↓
Validation
        ↓
ZBMP Adapter
        ↓
Production
```

Do not directly mutate CTH-POMS production facts.

## 13. Existing ZBMP asset reuse

Before adding a table/module, check existing:

- brand_directory.json
- brand_knowledge_base.py
- case_library.json
- case_deep_analysis.py
- brand_report_generator.py
- brand_stats_recompute.py
- intelligence.py
- topic_campaign.py
- ai_learning_engine.py
- data_feedback_loop.py
- database.py
- database_migrations.py

The BIL layer should extend these capabilities rather than duplicate them.

## 14. Next execution order

1. Continue global evidence/case research.
2. Extract mechanisms into structured case records.
3. Build the complete existing-ZBMP brand inventory.
4. Map every existing brand against BIL capabilities.
5. Identify reusable fields and true gaps.
6. Populate BIL staging only with evidence-backed records.
7. Validate metrics and entity resolution.
8. Run Shadow analysis.
9. Add UI/API only after data contracts pass validation.
10. Production cutover only after regression and rollback evidence.

## 15. Non-goals

- No fake/estimated UGC counts presented as facts.
- No follower count treated as influence by itself.
- No AI-generated claim treated as source evidence.
- No automatic scraping that bypasses platform controls.
- No production migration merely because schema exists.
- No replacement of existing ZBMP core modules.
