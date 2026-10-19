# OEVIRA Canonical Naming & Compatibility Boundary

> **Protocol state:** `IMPLEMENTED`
> **Current product identity:** **寰意 / OEVIRA**
> **Scope:** display naming, legacy-name disposition and compatibility migration gates
> **Sole product architecture authority:** [`LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`](LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
> **Current source-owner index:** [`LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`](LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)

This document is a compatibility protocol, not a second product architecture, runtime owner, data owner or proof of migration. If it conflicts with current executable source or the sole Product Architecture, those authorities win and this ledger must be repaired.

## 1. Current naming boundary

2026-10-18 main-product display migration: 寰意 / OEVIRA, oevira.com, “An Open Space for Thought and Creation.” The existing canonical registry remains the naming authority. This migration does not rename repository URLs, package/class names, Bundle IDs, API routes, environment/header names, DB/Evidence/Permission identities, launch/recovery paths, sibling products, copyright owners or historical evidence. Former 序境 / LUMENIS display text is retained only in marked history, source quotations or compatibility references. Source edits and protocol state do not prove deployment, device installation or CI/PR acceptance.

| Layer | Current user-facing identity | Boundary |
| --- | --- | --- |
| Product | **寰意 / OEVIRA** | The only current product name. |
| CTH | **CTH / OEVIRA Commerce Operations** | Subject-first commercial operations. |
| BMP | **BMP / OEVIRA Brand & Market** | Brand/Market-first. `ZBMP` and `zbmp` remain compatibility IDs only. |
| Shared Capability | **Shared Capability** | Content & Creation, Evidence, Research, Evaluation, Learning, Reporting and AI enhancement; not a separate product. |
| SYSTEM | **SYSTEM** | Runtime, Collector, Browser, AI Gateway, Database, Security, Permission, Settings, Recovery and Observability. |
| Repository | `Zachary-1012/LUMENIS-codex-Clean-OS` | Current canonical repository identity. Historical `Z-Brand-Core` references do not redefine it. |

Current App copy, operator guidance and new entry points use 寰意 / OEVIRA / BMP / CTH. Historical Z-Brand/ZBC names may remain only where the compatibility ledger or a clearly marked provenance document requires them.

## 2. Compatibility ledger

`COMPATIBILITY-KEEP` is a disposition, not a completion or live-runtime state. No row below claims that a migration has occurred.

| Compatibility surface | Identifier or path | Disposition | Evidence state | Owner | Why it is retained | Migration gate | Rollback gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Historical repository identity | `Z-Brand-Core`, `Zachary-1012/Z-Brand-Core` and checkout/link references that still use those names | `COMPATIBILITY-KEEP` | `LIVE_UNVERIFIED` | Repository governance and Operations | Git history, external links, local checkouts, shortcuts or automation may still resolve the historical name. | Inventory every external clone, link, script, automation and documentation consumer; provide an explicit redirect/mapping; prove callers use the current repository identity before retiring any alias. | Keep or restore the historical mapping/redirect and re-run the caller inventory without rewriting history. |
| Product storage/API ID | `product_id=ZBMP` | `COMPATIBILITY-KEEP` | `IMPLEMENTED` | BMP adapters, Shared Database and SYSTEM Security | Current authorization, storage history, API adapters and acceptance tests consume this stable identifier. | Account, database, API, adapter and acceptance-test owners approve a data-preserving migration; old and new IDs are reconciled with history and Permission parity. | Continue accepting and emitting `ZBMP`; restore the pre-migration mapping from a verified backup without dropping stored history. |
| Domain storage/API ID | `domain_id=zbmp` | `COMPATIBILITY-KEEP` | `IMPLEMENTED` | BMP adapters, Shared Database and SYSTEM Security | Current domain isolation, Evidence, reports and tests depend on this stable identifier. | Prove complete read/write caller coverage, domain/Permission isolation, data migration, Evidence lineage and affected regression before a coordinated cutover. | Restore `zbmp` acceptance/mapping and verify historical rows remain readable and correctly isolated. |
| Environment variables | Existing `ZBC_*` variables, including `ZBC_DB_PATH` | `COMPATIBILITY-KEEP` | `IMPLEMENTED` | SYSTEM Runtime and each consuming owner; Shared Database owns `ZBC_DB_PATH` semantics | Deployed configuration, data-path isolation, collectors, tests and secrets injection still use these names. | Inventory every producer/consumer and deployment profile; introduce documented dual-read precedence; prove secret handling, path equivalence, isolated tests and staged rollback before changing names. | Retain the old variables throughout the migration window and restore their precedence without changing their values or target paths. |
| Persisted schema/table/skill identifiers | Existing `zbc_*` schema, table and skill IDs | `COMPATIBILITY-KEEP` | `IMPLEMENTED` | Shared Database, Shared Evidence and Shared Agent Skills according to the specific identifier | Persisted rows, foreign references, Evidence lineage, packages and tests require stable physical IDs. | The owning round must provide schema/ID inventory, data-preserving migration, reader/writer parity, backup, rollback rehearsal and affected acceptance evidence. | Restore the old reader/writer and physical identifier from a verified backup; never drop the old object before parity and retention gates pass. |
| Runtime single-instance mutex | `Global\ZBrandCoreLauncher8201` | `COMPATIBILITY-KEEP` | `IMPLEMENTED / LIVE_UNVERIFIED` | SYSTEM Runtime (`scripts/start_production.ps1`) | Existing and current launchers must contend on one mutex; changing it prematurely could allow duplicate 8201 launcher trees. Live external launcher usage has not been inspected in this Batch. | Inventory deployed processes, startup tasks and every launcher version; perform one coordinated cutover that proves old/new launchers cannot run concurrently and recovery remains intact. | Revert all launchers to the historical mutex and prove single-instance startup plus health/recovery before another migration attempt. |
| Legacy Windows autostart path | `scripts/start-zbrand-autostart.cmd` | `COMPATIBILITY-KEEP` | `IMPLEMENTED / LIVE_UNVERIFIED` | SYSTEM Runtime and Windows Operations | Task Scheduler or external shortcuts may call the file by its exact path. The repository does not prove their live configuration. | Inspect the real Task Scheduler and shortcut callers, redirect each to `scripts/start-lumenis-autostart.cmd`, and observe a successful scheduled run before considering retirement. | Keep the legacy wrapper callable and redirect it back to the canonical launcher if an external caller fails. |

## 3. Launcher naming rule

- `scripts/start-lumenis-autostart.cmd` is the canonical Windows autostart entry and resolves `start_production.ps1` relative to its own directory.
- `scripts/start-zbrand-autostart.cmd` is a legacy compatibility wrapper. It remains callable at the old path and only forwards to the canonical entry.
- `scripts/start_production.ps1` remains the canonical runtime launcher and keeps `Global\ZBrandCoreLauncher8201` until the mutex migration gate above is satisfied.
- Repository tests may establish `TESTED` static behavior. They do not establish a live Task Scheduler migration; that remains `LIVE_UNVERIFIED` until the external state is inspected.

## 4. Historical material disposition

The following files retain provenance but do not define current architecture, ownership or runtime truth:

| Path | Disposition | State | Current authority |
| --- | --- | --- | --- |
| `docs/ZBRAND_INTELLIGENCE_REPORTING_SPEC.md` | Historical reporting provenance only | `EXISTS_BUT_UNSCOPED` | Product Architecture + Source Owner Index |
| `docs/Z-Brand双产品线最终基线_V1.0.docx` | Historical UTF-8/Markdown provenance retained under its original extension | `EXISTS_BUT_UNSCOPED` | Product Architecture + Source Owner Index |
| `intelligence_library/09_Research-Hub/engineering研究/Z-BRAND-INTEGRATION.md` | Historical engineering provenance only | `EXISTS_BUT_UNSCOPED` | Product Architecture + Source Owner Index |

Their legacy statements may support dependency tracing. They may not be used as CURRENT implementation, release, Permission, Evidence, database or runtime proof.

## 5. Migration protocol

Do not perform a repository-wide string replacement. For each identifier:

```text
Owner and caller inventory
→ persisted-data and external-caller inventory
→ compatibility design
→ isolated migration and rollback plan
→ affected tests
→ runtime/E2E where applicable
→ Evidence
→ coordinated release
→ retirement decision
```

If a real caller, Task Scheduler entry, stored record, credential source, Cookie/session boundary or rollback path cannot be inspected, keep the compatibility identifier and record `LIVE_UNVERIFIED` instead of guessing.

## 6. Cross-repository synchronization boundary

Current ecosystem repository roles and exchange boundaries are owned by [`CROSS-REPO-CANONICAL-REGISTRY-V1.md`](CROSS-REPO-CANONICAL-REGISTRY-V1.md) and the blocking machine contract. A compatibility alias does not authorize copying files between repositories, creating another Production Truth, or treating a historical twin-repository statement as current authority.
