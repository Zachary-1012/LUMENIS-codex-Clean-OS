# Cross-Repo Canonical Registry V1

> Status: **ACTIVE / CURRENT HUMAN-READABLE MIRROR**  
> Effective protocol: **lumenis-ggi-cross-product v1.1.0**  
> Effective date: 2026-09-17  
> Scope: LUMENIS product-family repository boundary

This registry is the human-readable cross-repository authority map. It does not replace the LUMENIS internal product/domain registry in `CANONICAL_REGISTRY.md` and it does not replace the blocking machine contract in `00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json`.

When this document and the machine contract disagree, **fail closed**: do not infer a new current protocol. The machine contract plus its blocking validator must be reconciled with this registry before cross-product work continues.

## Canonical repositories

| Repository | Product / role | Truth ownership |
| --- | --- | --- |
| `Zachary-1012/LUMENIS-codex-Clean-OS` | 序境 / LUMENIS · Production Core | Production Truth |
| `Zachary-1012/Zachary-OS-AI` | 序蕴 / LUMENIS Intelligence · Shared Intelligence Capability | Shared Intelligence Assets |
| `Zachary-1012/global-growth-intelligence` | 序衍 / LUMENIS Growth · Independent Research & Growth Product | Research / Growth Truth |
| `Zachary-1012/lumenis-command` | 序枢 / LUMENIS Command · R&D Control Sidecar | Engineering Evidence |

Historical repositories are provenance only and are not current canonical production repositories.

Repository names, package names, API identifiers, database identifiers and other stable technical aliases are compatibility identities. Do not rename them merely to match current product branding.

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

Other products may reference these semantics but may not redefine LUMENIS Production Truth ownership.

## Hard boundaries

- no shared production database;
- no production credential sharing;
- no cross-product runtime hard dependency;
- no copying product business implementation as an integration mechanism;
- no unrestricted cross-product writer;
- Research / Growth Truth cannot overwrite LUMENIS Production Truth;
- AI/OSAI output remains advisory until the receiving product validates and releases it locally;
- cross-repository exchange is limited to versioned Contract / Artifact / Evidence references / validated learning candidates.

## Machine contract — CURRENT

The blocking machine-readable contract is:

`00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json`

Current contract identity:

```text
contract_id = lumenis-ggi-cross-product
version     = 1.1.0
fingerprint = 68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f
```

The JSON contract is validated by `scripts/audit_tools/verify_lumenis_ggi_contract.py`. LUMENIS takeover/governance consistency is additionally validated by `scripts/audit_tools/verify_codex_takeover_governance.py`.

A repository may add product-local implementation detail, but it must not change the shared contract identity or hard boundaries unilaterally.

## Codex interpretation rule

For a new LUMENIS coding session:

```text
AGENTS.md
→ 00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md
→ README.md
→ this registry
→ LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json
→ exact current source / runtime / DB / API / Evidence / Permission / tests for the active slice
```

`origin/main` must be fetched at session start. No SHA written in a handoff, audit, README, screenshot or chat is allowed to masquerade as the current HEAD.

Dated/archived handoffs remain provenance only and never override this CURRENT path or executable truth.

## Change gate

Any change to repository role, truth ownership, LUMENIS four-domain semantics, exchange boundary, contribution-state vocabulary or adoption gate requires:

```text
AUDIT CURRENT REPO TRUTH
→ UPDATE VERSIONED CONTRACT
→ UPDATE AFFECTED CONSUMER COPIES
→ CONTRACT VALIDATION
→ TAKEOVER/GOVERNANCE CONSISTENCY VALIDATION
→ PRODUCT TESTS
→ EVIDENCE
→ RELEASE
```

A README statement alone is not protocol evidence.
