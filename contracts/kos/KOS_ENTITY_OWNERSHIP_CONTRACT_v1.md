# KOS Entity Ownership Contract v1

Status: P0 / Active
Scope: Z-Brand-Core production KOS layer

## Non-negotiable rule

Content relevance is not proof of KOS ownership.

A creator mentioning a target commercial complex, tenant brand, store, event, or product may be relevant to monitoring but must not automatically be classified as the target entity's KOS.

## Ownership classes

- `TARGET_ENTITY_KOS`: direct, evidenced relationship with the monitored target entity.
- `BRAND_KOS`: KOS belonging to a brand associated with the target ecosystem, but not the target entity itself.
- `MERCHANT_KOS`: creator/employee/sales/professional associated with a tenant or merchant brand.
- `PARTNER_KOS`: evidenced partner/agency/cooperation relationship.
- `INDEPENDENT_KOL_KOC`: independent creator with relevant content but no ownership evidence.
- `UGC_CONSUMER`: ordinary consumer/user-generated content.
- `MEDIA`: media/editorial entity.
- `OFFICIAL`: official account/entity.
- `UNKNOWN`: insufficient evidence.

## Hard separation examples

- Guangzhou Taikoo Hui relevance != Guangzhou Taikoo Hui KOS.
- A Taikoo Hui tenant-brand KOS != Taikoo Hui KOS.
- Hainan duty-free relevance != Hainan CDF KOS.
- A CDF/tenant/brand KOS != CDF/target-entity KOS unless direct ownership evidence exists.

## Evidence gate

KOS ownership should be supported by one or more signals, preferably independent signals:

1. Explicit identity/role evidence (employee, BA, sales, product expert, official collaborator, etc.).
2. Repeated role-consistent behavior over time.
3. Direct brand/entity relationship or authorization evidence.
4. Consistent entity-specific operational/content behavior.

Keyword occurrence alone is never sufficient.

## Decision states

`DIRECT` / `INDIRECT` / `MERCHANT` / `PARTNER` / `INDEPENDENT` / `UGC` / `MEDIA` / `OFFICIAL` / `UNKNOWN`.

If evidence is insufficient, downgrade to `UNKNOWN` or the appropriate non-KOS class; do not infer ownership.

## AI boundary

AI may assist semantic classification, evidence extraction, scoring, and ambiguity detection. AI must not override the core subject filter or manufacture ownership evidence.

## Required output fields

- `target_entity`
- `creator_id`
- `creator_name`
- `ownership_class`
- `ownership_state`
- `ownership_confidence`
- `evidence_ids`
- `evidence_count`
- `merchant_or_brand`
- `relevance_score`
- `kos_score`
- `reason`
- `needs_manual_review`

## Regression requirement

Any KOS pipeline change must include a regression set containing tenant-brand creators and ordinary consumers so they cannot be promoted to target-entity KOS solely because their content mentions the target entity.
