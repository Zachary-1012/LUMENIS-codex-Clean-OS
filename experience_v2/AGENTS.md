# AGENTS.md — LUMENIS Experience execution router

Scope: `experience_v2/**`.

This file contains **no independent design rules**.

The machine authority registry and sole design authority are:

`../00-GOVERNANCE/LUMENIS-EXPERIENCE-AUTHORITY-CURRENT.json`

`../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`

Root production truth, safety, data, permission, Evidence, runtime, testing and Git rules remain inherited from `../AGENTS.md`.

Before Experience implementation:
1. read `../AGENTS.md`;
2. read `../00-GOVERNANCE/LUMENIS-EXPERIENCE-AUTHORITY-CURRENT.json`;
3. read the sole Constitution above;
3. inspect exact current ViewModel / State / Action / Permission / Evidence / Runtime owners;
4. implement against current truth;
5. run `python scripts/audit_tools/verify_experience_authority_exclusive.py`;
6. run `python scripts/audit_tools/verify_experience_anti_template.py --strict`;
7. run proportional UI/runtime/E2E acceptance.

Do not create another design authority. Do not perform broad legacy-design cleanup during this V3 convergence round; physical cleanup is a separate next-round task.
