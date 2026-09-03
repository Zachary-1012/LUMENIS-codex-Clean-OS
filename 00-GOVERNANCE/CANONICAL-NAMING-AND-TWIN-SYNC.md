# Canonical Naming & Twin Repository Synchronization

**Status:** ACTIVE  
**Authority:** Cross-repository governance  
**Scope:** `Zachary-OS-AI` ↔ `Z-Brand-Core`

## 1. Current Canonical Identity

| Layer | Canonical |
|---|---|
| Chinese Brand | **序境** |
| Korean Brand | **서경** |
| English Canonical Brand | **TBD** |
| Philosophy | **芥子纳须弥** |
| Philosophy Definition | **微小之中本身就包含通向整体的结构。** |
| Legacy English | `Xujing`, `Xujing Core`, `Xujing Intelligence` — historical compatibility only |

Until the English name passes naming, conflict, trademark and digital-presence review and receives explicit approval, it MUST remain `TBD` in canonical documentation.

## 2. Twin Repository Contract

```text
Zachary-OS-AI
Research & Intelligence
        │
        │ Evidence / Contract / Implementation Specification
        ↓
Z-Brand-Core
Production Truth
```

Research may inform Core, but Research, Agent and external model output MUST NOT directly mutate Production Truth.

## 3. Research-to-Learning Asset Standard

External research must be transformed into structured assets rather than copied as an undifferentiated document collection.

Minimum metadata:

- `asset_id`
- `title`
- `source_type`
- `source_url_or_identifier`
- `publisher_or_author`
- `published_at` / `accessed_at` when available
- `evidence_excerpt_or_summary`
- `evidence_level`
- `claim_scope`
- `status`
- `version`
- `related_concepts`
- `related_modules`
- `validation_method`
- `license_or_usage_note` where applicable

Allowed status values:

`FACT / VERIFIED / PENDING / CONCEPT / RECOMMENDATION / LEGAL REVIEW / LEGACY / REJECT`

## 4. Evidence Levels

Suggested research evidence hierarchy:

`E0 = unverified lead`  
`E1 = single secondary source`  
`E2 = credible multi-source synthesis`  
`E3 = authoritative / primary source`  
`E4 = independently reproduced or internally validated result`

Evidence level is not the same as truth; applicability and scope must also be recorded.

## 5. Citation & Provenance

AI-readable knowledge assets MUST preserve provenance. Generated synthesis must distinguish source claims from system interpretation.

When a claim changes over time, the newest authoritative evidence supersedes older material without silently deleting the historical record.

## 6. Rename / Migration Protocol

Do not perform global search-and-replace solely because a new brand candidate exists.

For a Canonical rename:

```text
Inventory
→ Reference Scan
→ Dependency Scan
→ Canonical Registry Update
→ Documentation Update
→ Code / Config Migration Plan
→ Test
→ Evidence
→ Audit
→ Release
→ Legacy Mapping
```

Old names may remain where required for Git history, immutable identifiers, package compatibility or legal/audit traceability, but must be explicitly marked `LEGACY`.

## 7. Synchronization Rule

Changes affecting either repository's:

- Canonical naming
- repository relationship
- Contract
- evidence boundary
- permission boundary
- production truth boundary
- file governance
- research-to-production workflow

must be reflected in both repositories' relevant governance/documentation assets before the change is considered synchronized.

This does NOT mean copying files between repositories or creating a third source of truth.

## 8. Current Synchronization Event

This policy accompanies the current update of both READMEs to establish:

- the life-level philosophy research framework;
- structured Research → Knowledge → Evidence → Evaluation learning;
- explicit `TBD` status for the future English Canonical Brand;
- Legacy treatment of historical `Xujing` naming;
- file and naming governance;
- the boundary between research concepts and implemented production capabilities.

## 9. Non-Goals

- No third core repository.
- No automatic promotion of research into production.
- No claim that future life-system concepts are already implemented.
- No legal conclusion from a preliminary search.
- No deletion of historical assets solely for naming cleanup.
