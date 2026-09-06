# KOS Account Asset Template v1

## Purpose
Standardize post-collection creator/account records for KOS review, qualification, lead capture, outreach, cooperation tracking, and Evidence traceability.

## 1. Account identity
- KOS_ID
- platform
- UID
- nickname
- profile_url
- avatar/reference
- region
- content_domain
- tags

## 2. Entity ownership gate
- target_entity
- ownership_type: TARGET_ENTITY_KOS | BRAND_KOS | MERCHANT_KOS | PARTNER_KOS | INDEPENDENT_KOL_KOC | UGC_CONSUMER | MEDIA | OFFICIAL | UNKNOWN
- ownership_confidence
- ownership_evidence_ids
- merchant_entity
- brand_entity
- relationship_status

Hard rule: content relevance does not prove KOS ownership. Merchant KOS must not enter the target-entity KOS pool unless direct ownership evidence exists.

## 3. Performance metrics
- follower_count
- follower_growth_rate
- posts_30d
- avg_likes
- avg_comments
- avg_collects
- avg_shares
- engagement_rate
- content_match_score
- expertise_score
- consistency_score
- reach_score
- comment_handling_score
- paid_amplification_potential

## 4. KOS classification
- tier: S | A | B | C
- lifecycle: DISCOVERED | ACTIVATING | GROWING | STABLE | BREAKOUT | DORMANT | CHURNED | REACTIVATION
- risk_level
- account_asset_health
- data_freshness

## 5. Content intelligence
- content_tags
- strongest_topics
- best_content_formats
- best_publish_time
- top_content_ids
- audience_intents
- comment_intents
- content_genes

## 6. Lead / CRM fields
- contact_name
- mobile
- wechat
- email
- company
- MCN
- business_contact
- region
- available_platforms
- lead_source
- lead_completeness
- last_verified_at
- consent_or_contact_basis

Do not fabricate or infer private contact details. Store only legitimately obtained business contact information.

## 7. Cooperation
- cooperation_types: SEEDING | CAMPAIGN | EVENT | STORE_VISIT | LIVE | LONG_TERM_KOS | PAID_AMPLIFICATION
- budget_range
- quoted_price
- benefits
- availability
- cooperation_status: NEW | TO_CONTACT | INVITED | SENT | REPLIED | NEGOTIATING | ACCEPTED | CONTENT_PUBLISHED | COMPLETED | REJECTED | DO_NOT_CONTACT
- rejection_reason
- last_contact_at
- next_action
- next_action_at
- campaign_id
- cooperation_history

## 8. AI / decision fields
- AI recommendation
- recommended_content_direction
- recommended_campaign
- recommended_reply_action
- recommended_outreach_channel
- recommended_paid_amplification_action
- rationale

AI recommendations must cite source data/Evidence and cannot override deterministic entity ownership gates.

## 9. Evidence chain
KOS_ID -> account -> content -> collection_run -> subject_rule_hit -> ownership_evidence -> AI decision (if used) -> final decision.

## 10. UI views
Required views:
1. KOS account table: sortable/filterable by tier, ownership, lifecycle, risk, platform, cooperation status.
2. 360 account profile: identity, performance, ownership evidence, content, comments, lead, cooperation history, AI actions.
3. Lead panel: business contact and verification state.
4. Action bar: generate reply, generate outreach, generate email, create campaign task, generate report.
5. Data-quality badges: ownership confidence, data freshness, lead completeness, account health.

## 11. Production rule
An account with failed collection-quality or ownership gates must not enter official KOS ranking, outreach, paid-amplification recommendation, or formal reporting until validated.