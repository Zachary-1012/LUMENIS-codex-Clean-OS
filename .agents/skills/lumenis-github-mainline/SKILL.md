---
name: lumenis-github-mainline
description: Must use for LUMENIS Git/GitHub, branch, commit, push, CI, workflow, origin/main, diff, merge, repository cleanup, or release-history work.
---
# GitHub / Mainline
Use scoped task/feature/repair branches and PRs, verify the exact change and review it before merging into main. Main is the integration/release reference, not the only writable branch. Reconcile fresh remote and local baselines, preserve unknown dirty work, and use isolated worktrees when necessary. Never force-push main or automatically delete working branches. CI, source, runtime and user outcomes are separate evidence. A local commit is not remote evidence until pushed. Follow the 2026-10-10 PO receipt and current machine contract.
