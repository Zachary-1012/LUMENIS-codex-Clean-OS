# Continuous Engineering Research — 2026-08-31

## Decision

The platform will keep two layers deliberately separate:

- **Deterministic GitHub Actions:** scheduled inspection, tests, artifacts, release gates, and other operations whose correctness can be expressed as rules.
- **AI/ChatGPT research layer:** repository understanding, industry/GitHub research, judgment, optimization candidates, and learning proposals.

This matches current GitHub guidance: reusable workflows reduce duplicated CI logic, while agentic workflows are better suited to contextual repository judgment; agentic automation should augment rather than replace deterministic CI/CD.

## Applied to Zachary AI

1. Five daily inspections remain read-only and evidence-producing.
2. Inspection candidates are explicitly labeled as candidates, never failures.
3. Actual test status can only be promoted after real execution.
4. Repeated deterministic inspection logic should become reusable code rather than repeated AI reasoning.
5. Dependency caching may improve runner efficiency, but cached data is not trusted state.
6. Artifact attestations should be considered for real release artifacts, not routine inspection snapshots.
7. Third-party Actions/workflows should be reviewed and preferably pinned/controlled before production use.

## Three-repository feedback

Research is not considered complete until a useful conclusion becomes one or more of:

`code → test → evidence → rule/skill → automation`

The destination repository must re-verify adapted behavior. No result from one repository is assumed valid in another without evidence.

## Sources

- GitHub Docs — Reusing workflow configurations: https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations
- GitHub Docs — Artifact attestations: https://docs.github.com/en/actions/concepts/security/artifact-attestations
- GitHub Docs — Dependency review: https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review
- GitHub Docs — Secure use of Actions: https://docs.github.com/en/actions/reference/security/secure-use
- GitHub Blog — Automate repository tasks with GitHub Agentic Workflows: https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/

## Baseline constraint

This research note is additive evidence for the platform baseline. It does not override the immutable three-repository contract, production protection, permission boundaries, or delivery standard.
