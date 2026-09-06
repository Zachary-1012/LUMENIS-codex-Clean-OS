# KOS Entity Ownership Contract v1

Status: P0 / Shared Contract
Consumer: Z-Brand-Core production KOS layer
Governance: Zachary OS AI / DCC research, audit and verification layer

## Purpose

Prevent KOS contamination caused by confusing content relevance with creator ownership.

## Core invariant

`content_relevance != KOS_ownership`

A creator who mentions a target commercial complex, tenant brand, store, event, or product is not automatically a KOS of the target entity.

## Ownership classes

`TARGET_ENTITY_KOS`, `BRAND_KOS`, `MERCHANT_KOS`, `PARTNER_KOS`, `INDEPENDENT_KOL_KOC`, `UGC_CONSUMER`, `MEDIA`, `OFFICIAL`, `UNKNOWN`.

## Required distinction

- Guangzhou Taikoo Hui relevance != Guangzhou Taikoo Hui KOS.
- Taikoo Hui merchant/tenant KOS != Taikoo Hui KOS.
- Hainan duty-free relevance != Hainan CDF KOS.
- Brand/merchant KOS != target-entity KOS without direct evidence.

## Evidence gate

Ownership requires evidence such as explicit role/identity, direct relationship/authorization, repeated role-consistent behavior, or consistent entity-specific operational behavior. Keyword hits alone are insufficient.

## AI governance

AI may classify, extract evidence, score, and flag ambiguity. AI may not override hard subject filters, infer unsupported ownership, or manufacture evidence.

## Contract output

Every KOS decision should expose:

- target entity
- creator id/name
- ownership class/state
- confidence
- evidence ids/count
- merchant/brand
- relevance score
- KOS score
- reason
- manual-review flag

## Verification requirement

DCC/OSAI validation must include negative controls: tenant-brand KOS, independent KOL/KOC, and ordinary consumer content that mentions the target entity. These must not be promoted to target-entity KOS solely from relevance.

This contract is shared with Z-Brand-Core and must be mirrored/validated whenever the KOS classification logic changes.
