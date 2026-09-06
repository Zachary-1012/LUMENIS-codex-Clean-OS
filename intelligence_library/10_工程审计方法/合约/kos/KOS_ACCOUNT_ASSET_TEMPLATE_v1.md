# KOS Account Asset Template v1 — OSAI Contract

This contract defines the shared account-asset schema and validation expectations for KOS account collection and operations.

## Required layers
1. Account identity: KOS_ID, platform, UID, nickname, profile URL, region, domain, tags.
2. Entity ownership: target entity, ownership type, confidence, evidence IDs, merchant/brand relationship.
3. Performance: followers, growth, posting volume, average engagement, content match, expertise, consistency, reach, comment handling, paid amplification potential.
4. Classification: S/A/B/C, lifecycle, risk, data freshness, account health.
5. Content intelligence: tags, topics, formats, publish time, top content, audience intents, comment intents, content genes.
6. Lead/CRM: business contact fields, lead source, completeness, last verification, lawful/legitimate contact basis.
7. Cooperation: cooperation types, budget/quote, benefits, availability, status, rejection, last contact, next action, campaign ID, history.
8. AI decisions: recommendations and rationale with Evidence.

## Ownership guard
Content relevance is not ownership. MERCHANT_KOS must remain separate from TARGET_ENTITY_KOS and BRAND_KOS unless direct relationship evidence supports the target classification. AI cannot bypass deterministic ownership/subject gates.

## Data integrity
Never fabricate contact information, metrics, delivery status, cooperation status, conversions, ROI, or creator relationships. Missing data remains missing/unknown.

## Production gate
Collection-quality or ownership failures quarantine the account from official ranking, outreach, paid-amplification recommendation, and formal reporting until validated.

## UI acceptance
The production UI should provide a clear table plus a 360° account profile, lead panel, cooperation history, data-quality badges, and action controls for reply/outreach/email/campaign/report generation.

## Evidence chain
KOS_ID -> account -> content -> collection run -> subject rule -> ownership evidence -> AI decision -> final decision.