# Zachary ↔ ZBC Twin-Repository Contract V1.0

Status: Frozen execution contract

## Repository ownership

Zachary-OS-AI owns general AI capabilities: research, learning infrastructure, model/provider abstraction, reasoning/orchestration, resource retrieval, evaluation and reusable AI engineering tools.

Z-Brand-Core owns the production product: domain/business logic, Subject Truth, production collectors/data flow, event/risk/reporting, production UI/API/runtime, production tests and release, and product-specific policies/thresholds.

## Boundary

Zachary may provide AI capabilities to ZBC through explicit versioned interfaces. ZBC may provide authorized, minimized evaluation signals and product requirements to Zachary. Neither repository may silently copy the other's internal implementation.

Zachary must not independently rewrite ZBC Subject Truth, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit(), production risk thresholds, permissions, Evidence, compliance/security policies or production data.

ZBC must not turn product-specific business rules into universal Zachary knowledge, duplicate Zachary's general AI runtime without review, or send secrets/uncontrolled private production data into learning resources.

## Resource boundary

Shared cases, research, files and learning material are Resources. Resources are references, not automatic production Truth. Zachary can retrieve/reason over approved Resources; ZBC can contribute authorized/minimized feedback and evaluation signals. Learning cannot silently modify production code or business Truth.

## Contract-first integration

Every cross-repository integration must define interface, owner, input/output schema, authorization, timeout/retry behavior, version compatibility, Evidence requirements, tests and rollback behavior.

## Engineering execution

Both repositories use:
AUDIT → MAP → REUSE → IMPLEMENT → TARGET TEST → SECURITY/COMPLIANCE → REGRESSION → CLEAN → EVIDENCE → COMMIT → PUSH.

Agents must search before creating files, use project maps/path-specific instructions, parallelize only disjoint changes, and delete verified dead files rather than keeping legacy copies in the active tree.

## Conflict resolution

Security/compliance controls win first. Repository ownership is authoritative. Explicit contracts beat ad-hoc integration. ZBC owns production Truth; Zachary owns general AI capability.

## Verification

This contract is active only after both repositories contain/reference this same contract and repository-level verification confirms both sides understand ownership, boundaries, forbidden actions and contract-first integration.

## Change control

Frozen. Any change requires an explicit Contract Change Record and verification in both repositories. Routine development must not rewrite this boundary.
