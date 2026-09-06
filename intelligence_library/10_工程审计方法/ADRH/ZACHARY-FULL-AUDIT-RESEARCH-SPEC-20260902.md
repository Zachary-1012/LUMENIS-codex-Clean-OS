# Zachary AI Full Source Audit & Research Specification — 2026-09-02

## Scope
This specification defines the required full audit of the four current repositories: DCC, SICI-Core, Research-Hub, and Z-Brand-Core.

## Audit granularity
Audit must descend to:

1. repository
2. branch / commit / SHA
3. directory
4. file
5. symbol / function / class / route / API
6. configuration key
7. database
8. table
9. column / field
10. index / constraint / migration
11. dependency
12. UI interaction
13. runtime flow
14. cross-module communication
15. cross-repository contract
16. evidence / log / baseline / supplement

“Reviewed” means source-backed inspection, not filename-level inference.

## Per-item record
Every audited item must record:

- source repository
- exact path / symbol / DB object
- current SHA/version where applicable
- owner
- purpose
- inputs
- outputs
- dependencies
- callers / consumers
- side effects
- persistence behavior
- security sensitivity
- contract
- test coverage
- current status
- duplicate/overlap candidates
- target Zachary AI location
- migration action
- evidence reference

## Function-by-function research
For every material function/module/capability, research:

- current implementation
- established industry patterns
- strong open-source implementations
- relevant prior art
- current 2026 research where available
- applicability to Zachary
- security implications
- performance implications
- integration cost
- whether to preserve, adapt, merge, replace, or retire

External research is evidence, not authority. Existing Zachary source facts and immutable baseline remain authoritative for product-specific decisions.

## Database audit
For every database:

- schema inventory
- table inventory
- columns and types
- indexes
- constraints
- migrations
- seed/reference data
- ownership
- read/write callers
- retention behavior
- sensitive fields
- duplication
- migration compatibility
- backup/recovery implications

No database object may be deleted during consolidation until source-backed equivalence and consumer impact are verified.

## Cross-product communication audit
Map every:

- API
- event
- callback
- file contract
- database contract
- GitHub operation
- runtime bridge
- persistence bridge
- capability adapter
- evidence flow
- learning flow

Then classify each relationship as authoritative, consumer, adapter, historical, runtime, generated, or candidate.

## Research benchmark baseline
Use current research and strong projects as references. Particularly relevant current directions include contract-first repo-scale engineering, explicit contract SSOTs, bounded reversible migrations, artifact/evidence-centric auditing, cross-repository impact analysis, and cost-sensitive CI security gates. Recent 2026 work reports contract-based repo-level generation and cross-repository contract/impact testing as useful mechanisms for structural integrity and change safety. These are research inputs only and must be adapted to Zachary's actual architecture.

## Final outcome
Produce:

- complete four-repository inventory
- database map
- module map
- function/symbol map
- dependency graph
- communication graph
- ownership matrix
- Contract matrix
- duplicate matrix
- research/evidence matrix
- migration matrix
- immutable-baseline matrix
- security findings
- unresolved conflicts
- proposed convergence plan
- explicit NOT_VERIFIED items

No item may be marked PASS without evidence.
