---
name: lumenis-current-truth
description: Must use whenever starting or resuming LUMENIS code work, comparing local with GitHub, assessing completion, or making any claim about what currently exists.
---
# Current Truth
Read the repository root `AGENTS.md` first; it is the only execution router and defines C1–C6 engineering source responsibilities and the current dispatch rules. The Source Owner Index maps retained R01–R15 and J1–J8 coverage into existing owner outcomes, not six product rounds. Actual window, host and model assignment follow the latest direct Product Owner instruction and fresh evidence. Cloud restrictions apply only to an explicitly authorized Cloud task; they do not establish a current local/Cloud split. A worker must use repository rules and must not depend on workstation-only instructions or skills.

Run `git fetch origin` and distinguish local `HEAD`, the working tree, unpushed commits, and `origin/main`. Preserve unknown local work. Never infer current capability from chat, screenshots, README, historical handoffs, or stale SHAs. Trace claims through current source, runtime, DB/API/Permission/Evidence contracts, tests, and required E2E. Remote-missing local work is local pending verification, not absent capability. Cloud candidates are scoped source work; they do not establish deployment or local runtime acceptance.

For an explicitly read-only audit, use `git ls-remote` and the GitHub API instead of updating refs with fetch. Label cached `origin/main` separately, disable optional Git locks, and save deliverables outside the checkout. Read-only source inspection does not authorize runtime probes, imports with startup effects, database operations or tests.
