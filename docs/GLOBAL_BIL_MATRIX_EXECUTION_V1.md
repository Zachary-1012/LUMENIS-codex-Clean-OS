# Global BIL Matrix Execution v1

## Purpose

Turn the existing ZBMP brand inventory into a measurable capability matrix before any production cutover.

## Matrix

Each brand is evaluated against 17 capability domains:

1. Entity
2. Knowledge
3. Social Voice
4. UGC
5. Consumer Voice
6. Creator
7. Product
8. Campaign
9. Geography
10. Store / Channel
11. Community
12. Competitor
13. Brand Health
14. Business Momentum
15. Lifecycle
16. AI Discovery / GEO
17. Evidence

## Status vocabulary

- `EXISTS`: verified data/module exists and is usable.
- `PARTIAL`: some required fields or observations exist.
- `MISSING`: capability is not currently represented.
- `NOT_APPLICABLE`: capability does not reasonably apply to the entity.
- `CONFLICTED`: multiple sources disagree and require resolution.
- `UNKNOWN`: cannot establish status from current repository evidence.

Never infer `EXISTS` merely because a similarly named module exists.

## Scoring

Coverage score is diagnostic only:

`coverage = verified EXISTS + weighted PARTIAL`

It must never be used as a proxy for brand importance.

Benchmark priority is separate and uses:

- strategic relevance
- mechanism diversity
- market diversity
- lifecycle value
- evidence quality
- transferability
- data availability

## Existing ZBMP inventory

The current Guangzhou Taikoo Hui directory is treated as a local/channel dataset. It must not be promoted to a global master without entity resolution.

Expected flow:

`Existing Brand Entity → Market Presence → China → Guangzhou → Taikoo Hui → Store/Channel Observation`

## Benchmark overlay

Global benchmark cases are used as capability references, not as rankings. The current benchmark seed includes mechanisms covering values/community, cultural growth, UGC/co-development, creator/community, global culture, luxury cultural momentum, retail experience, ambassador communities, product innovation, education/trust, global-local execution, China-to-global niche growth, lifecycle growth/decline, resurgence, creator commerce, fandom commerce, and AI discovery.

## Evidence contract

Every non-static observation should retain:

- source
- source_type
- observed_at
- published_at when available
- market
- platform
- language when applicable
- evidence_type
- confidence
- method_version

Facts, observations, interpretations, hypotheses and recommendations must remain distinct.

## AI Discovery extension

AI visibility is a separate capability from SEO and Social. Track where evidence is available:

- prompt/query
- engine/model
- market/language
- brand mention
- recommendation
- position
- citation
- citation source
- competitor co-mentions
- framing
- observed_at

Do not manufacture AI visibility metrics from model guesses. Third-party benchmark estimates must be labeled as external estimates and must not be mixed with first-party observations.

## Consumer Voice extension

Separate:

- loud social voices: creators, viral posts, media
- consumer voice: purchasers, prospects, former customers, switchers and broader respondent evidence

Social volume is not a substitute for consumer-representativeness.

## Creator extension

Do not rank creators by followers alone. Preserve dimensions for reach, relevance, brand fit, authenticity, community density, content quality, UGC generation, intent and commercial signal.

## Commerce extension

Where evidence exists, model:

`Content → Interest → Consideration → Product → Purchase Intent → Store/E-commerce → Purchase → Review/UGC`

A UGC count alone must not be interpreted as conversion.

## Acceptance gate

Before production integration:

1. enumerate existing brands
2. resolve duplicate entities
3. populate matrix with evidence-backed statuses
4. select S/A benchmark brands
5. validate staging schema
6. compare BIL outputs against existing ZBMP outputs in shadow mode
7. explain metric discrepancies
8. run regression and rollback tests

No production migration is authorized by this document.
