# Z-Brand-Core｜Global BIL Capability Matrix v1

> 2026-09-01
> Status: inventory/mapping specification; no production cutover

## Purpose

Map every existing ZBMP brand entity against the Global BIL capability graph before adding new production modules.

The current local brand directory is a Guangzhou Taikoo Hui market/channel/store dataset, not the global brand master. The current directory declares 198 brands.

## Capability columns

- entity — canonical identity, aliases, parent/group relationships
- knowledge — historical knowledge, strategy, cases and brand facts
- social_voice — public conversation / attention signals
- ugc — consumer-generated content observations
- consumer_voice — discovery, consideration, intent, satisfaction, advocacy, rejection, switching
- creator — creator identity, relevance, quality and commercial contribution
- product — product/topic demand and product-level signals
- campaign — campaign entity, timing, market and outcomes
- geography — country/region/city/market hierarchy
- store_channel — store, stockist, e-commerce and channel presence
- community — community structure, fandom and advocacy
- competitor — competitive set and co-mention/consideration relationships
- brand_health — awareness, perception, consideration, intent, loyalty and reputation
- business_momentum — demand, sales/store/channel/commercial signals where evidenced
- lifecycle — emerging/growth/peak/mature/decline/revival states and transitions
- ai_discovery — AI answer-engine mentions, recommendations, citations and framing
- evidence — source, date, market, platform, quality and confidence traceability

## Coverage status

Use only: `EXISTS`, `PARTIAL`, `MISSING`, `NOT_APPLICABLE`, `CONFLICTED`, `UNKNOWN`.

Never use `EXISTS` merely because a filename or class exists. The underlying behavior and data contract must be verified.

## Priority dimensions

Coverage and importance are separate.

Data Coverage measures usable evidence available for the brand.

Strategic Importance considers:
- strategic relevance
- archetype representation
- market relevance
- mechanism diversity
- lifecycle learning value
- consumer/cultural relevance
- evidence quality
- transferability

A brand with low data coverage can still be a high-priority research target.

## Benchmark tiers

- `S` — mandatory deep benchmark
- `A` — high-value benchmark
- `B` — continuous observation
- `C` — long-tail/reference

Benchmark tier must never be assigned from follower count alone.

## Initial global benchmark archetypes

The seed set deliberately covers global luxury, designer fashion, Chinese designer global expansion, outdoor/value-led, sports/performance, beauty/community, DTC/digital-native, creator-led commerce, product-led growth, heritage revival, decline/recovery, cross-cultural localization, retail/store experience, social-to-commerce and AI discovery/GEO.

Research seeds include Jacquemus, Patagonia, SHUSHU/TONG, BY FAR, Molly Goddard, Nike, Adidas, Uniqlo, Lululemon, Glossier, Miu Miu, Loewe, Dr. Martens, On, Gymshark, The Ordinary, Gentle Monster, Aesop, Crocs, AllSaints, Gucci, CSB, Salomon, ASOS, ba&sh, boohoo and Weekday. These are seeds, not a fixed whitelist.

## Required machine-readable output

```text
brand_id
canonical_name
aliases
local_presence
industry
entity_status
knowledge_status
social_voice_status
ugc_status
consumer_voice_status
creator_status
product_status
campaign_status
geography_status
store_channel_status
community_status
competitor_status
brand_health_status
business_momentum_status
lifecycle_status
ai_discovery_status
evidence_status
benchmark_tier
strategic_importance
coverage_score
priority_reason
last_audited_at
method_version
```

## Mapping rules

1. Reuse the existing ZBMP Brand Entity whenever identity is the same.
2. Do not create duplicate brands because of Chinese/English names, store suffixes or platform naming differences.
3. A store record is not a new brand entity unless it represents a distinct legal/consumer brand.
4. Parent groups and brand portfolios are represented separately from individual brands.
5. Market presence is an observation attached to the brand, not a replacement for the brand entity.
6. Dynamic metrics require capture timestamps.
7. Missing evidence stays `UNKNOWN`/`MISSING`; do not estimate silently.
8. Evidence quality travels with every derived insight.

## Immediate execution

1. Enumerate all current ZBMP brand entities.
2. Normalize aliases and parent/group relationships.
3. Map existing modules/data fields to the 17 BIL capabilities.
4. Identify true gaps versus capabilities hidden in current modules.
5. Select S/A benchmark brands using strategic criteria.
6. Populate BIL staging only after evidence validation.
7. Run shadow comparison before any production adapter.
