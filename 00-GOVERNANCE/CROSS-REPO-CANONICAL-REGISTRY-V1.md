# Cross-Repo Canonical Registry V1

> Status: ACTIVE  
> Effective: 2026-09-16  
> Scope: LUMENIS product family repository boundary

This registry is the cross-repository authority. It does not replace the LUMENIS internal product/domain registry in `CANONICAL_REGISTRY.md`; it defines which repository owns which truth and how repositories may exchange assets.

## Canonical repositories

| Repository | Product / role | Truth ownership |
| --- | --- | --- |
| `Zachary-1012/LUMENIS-codex-Clean-OS` | 序境 / LUMENIS · Production Core | Production Truth |
| `Zachary-1012/Zachary-OS-AI` | LUMENIS Intelligence / OSAI · Shared Intelligence Capability | Shared Intelligence Assets |
| `Zachary-1012/global-growth-intelligence` | Global Growth Intelligence · Independent Research & Growth Product | Research / Growth Truth |
| `Zachary-1012/lumenis-command` | 序枢 / LUMENIS Command · R&D Control Sidecar | Engineering Evidence |

`Zachary-1012/Z-Brand-Core` is legacy engineering history and is not a current canonical production repository.

## LUMENIS domain contract consumed across repositories

```text
CTH
= Commerce Operations · Subject-first

BMP
= Brand & Market · Brand-first / Primary Focus

Shared Capability
= Content & Creation + Evidence + Research + Evaluation + Learning Asset + AI Enhancement

SYSTEM
= Collector + Runtime + Scheduler + AI Gateway + Database + Security + Permission + Settings + Recovery + Observability
```

GGI may reference these semantics but may not redefine their Production Truth ownership.

## Hard boundaries

- no shared production database;
- no production credential sharing;
- no cross-product runtime hard dependency;
- no copying product business implementation as an integration mechanism;
- no unrestricted cross-product writer;
- GGI Research / Growth Truth cannot overwrite LUMENIS Production Truth;
- AI/OSAI output remains advisory until the receiving product validates and releases it locally;
- cross-repository exchange is limited to versioned Contract / Artifact / Evidence references / validated learning candidates.

## Machine contract

The blocking machine-readable contract is:

`00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json`

Contract identity:

```text
contract_id = lumenis-ggi-cross-product
version     = 1.0.0
fingerprint = a5e8d6e16bb99d1b5b0985d9fb406d53c853097315699c3a99ecfa914004a9c7
```

The same semantic contract must exist in GGI. A repository may add product-local implementation detail, but it must not change the shared contract identity or hard boundaries unilaterally.

## Change gate

Any change to repository role, truth ownership, LUMENIS four-domain semantics, exchange boundary, contribution state vocabulary or adoption gate requires:

```text
AUDIT CURRENT REPO TRUTH
→ UPDATE VERSIONED CONTRACT
→ UPDATE BOTH CONSUMER COPIES
→ CONTRACT VALIDATION
→ PRODUCT TESTS
→ EVIDENCE
→ RELEASE
```

A README statement alone is not protocol evidence.
