# Zachary ↔ ZBC Twin-Repository Contract V1.0

Status: Frozen execution contract
Purpose: establish one unambiguous boundary so both repositories know their responsibilities, shared interfaces and forbidden cross-boundary behavior.

## 1. Two repositories, two responsibilities

### Zachary-OS-AI
Owns the general AI capability layer:
- research and learning infrastructure;
- model/provider abstraction;
- reasoning/orchestration;
- resource retrieval and knowledge operations;
- evaluation methodology;
- AI-assisted engineering capabilities;
- reusable general-purpose tools.

It does not own ZBC production business Truth.

### Z-Brand-Core (ZBC)
Owns the production product:
- business/domain logic;
- Subject Truth;
- collectors and production data flow;
- normalization/filtering;
- event/risk/reporting;
- production UI/API/runtime;
- production tests and release;
- product-specific policies and thresholds.

It does not absorb Zachary's general learning/AI architecture into business modules merely because Zachary can perform the capability.

## 2. Direction of dependency

Zachary may provide a capability to ZBC through an explicit interface/contract.
ZBC may provide approved evaluation signals, anonymized/authorized feedback and product requirements to Zachary.

Neither repository may silently import the other's internal implementation merely to avoid defining an interface.

## 3. Forbidden cross-boundary actions

Zachary must not independently:
- rewrite Subject Truth;
- change SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS or subject_hit();
- change production risk thresholds;
- change production permissions;
- delete/alter production Evidence;
- change compliance/security policy;
- mutate ZBC production data directly.

ZBC must not:
- fork or duplicate Zachary's general AI runtime without review;
- treat product-specific business rules as universal Zachary knowledge;
- feed secrets, credentials, private customer data or uncontrolled production data into learning resources;
- make Zachary dependent on one product's internal database schema.

## 4. Resource / learning boundary

Shared learning material is accessed through a Resource contract. Resource content is reference material, not automatically production Truth.

Zachary may retrieve and reason over approved resources. ZBC may contribute production feedback/evaluation signals under data minimization and authorization rules.

Learning must never silently modify production code or business Truth.

## 5. AI decision boundary

AI output is advisory/analytical unless an explicit, tested ZBC contract states otherwise. Any material production decision must retain source Evidence, model/prompt version and applicable human/rule validation.

## 6. Contract-first integration

Every cross-repository integration must define:
- API/interface name;
- owner repository;
- input schema;
- output schema;
- authentication/authorization;
- timeout/retry/failure behavior;
- version compatibility;
- Evidence requirements;
- test fixture;
- rollback behavior.

## 7. 10× engineering rule across both repositories

Use the same execution loop:
AUDIT → MAP → REUSE → IMPLEMENT → TARGET TEST → SECURITY/COMPLIANCE → REGRESSION → CLEAN → EVIDENCE → COMMIT → PUSH.

Agents must search existing code before creating files, use the project map and path-specific instructions, parallelize only disjoint work, and delete verified dead files instead of accumulating legacy copies.

## 8. Source and license boundary

Code may be shared only through an explicit approved interface or documented reusable component. Third-party code, models and dependencies retain their own provenance and license obligations.

AI-assisted generation is not treated as third-party code by default, but any copied/derived external implementation must be identified and reviewed.

## 9. Conflict resolution

When a requirement conflicts:
1. Security/compliance controls win;
2. repository ownership wins;
3. explicit Contract wins over ad-hoc integration;
4. production Truth remains owned by ZBC;
5. general AI capability remains owned by Zachary.

Do not resolve conflicts by silently copying, weakening controls or changing another repository's core.

## 10. Verification requirement

This contract is considered active only when both repositories contain or explicitly reference this same contract, and both can pass a repository-level verification proving:
- each repository identifies its own responsibilities;
- each identifies the other repository's boundary;
- forbidden actions are understood;
- cross-repository interfaces are contract-first;
- no unauthorized direct data mutation exists.

## 11. Change control

This contract is frozen. Changes require an explicit Contract Change Record and verification in both repositories. Routine product development must not rewrite the boundary.
