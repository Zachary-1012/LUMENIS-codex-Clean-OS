# ROUND-03-B001D — v14–v17 owner and contract reconciliation

Status: NEXT READ-ONLY TASK CARD. This is ROUND 03 dependency work under the current Charter. It does not authorize ROUND 04, migration, or promotion of the protected dirty candidate.

| Field | Boundary |
| --- | --- |
| Entry | Fresh `git fetch origin --prune`; resolve exact `HEAD`, `origin/main`, status, branch inventory and protected production DB/WAL/SHM file fingerprints. The documented checkpoint after B001C is `98729908`. |
| Job | Trace the uncommitted v14–v17 migration calls and schema fields to their actual Subject Registry, Shared Evidence, Content Evidence, Canonical Data, Permission, reporting and Product Core owners. For each, identify owner approval, current source and caller, schema/input/output contract, existing/unknown behavior, backward compatibility and required isolated test. |
| Read-only scope | `lumenis/shared/database/{business_schema,migrations,scope}.py`, `canonical_data.py`, `subject_registry.py`, `lumenis/shared/evidence/`, `lumenis/system/security/permission.py`, exact affected reporting/Content Evidence callers, paired tests and current governance. Expand only to a proven direct dependency. |
| Safety | Preserve every dirty and untracked path. Do not SQLite-open, checkpoint, back up, migrate, copy over, delete or repair `data/monitor.db` or sidecars. Do not access the personal Mainland XHS identity. No source edit, staging, commit, push or product runtime restart. |
| Output | Hunk-to-owner/dependency matrix with the smallest independently buildable next implementation slice, explicit `PASS/REWORK/SPLIT/BLOCKED` recommendation for each candidate, source/test evidence, base/final SHA and protected fingerprints. Record actor-to-Subject authorization gaps separately from registry row existence and Evidence integrity. |
| Stop | Sol alone may issue a new exact allowed-file implementation card after reviewing this map. B002 caller parity and B003 real-user E2E stay dependent on B001 acceptance. |

The prior isolated public-source report and API payloads are leads only. They do not prove a rendered CTH page, user Return, global non-reference coverage or Permission acceptance.
