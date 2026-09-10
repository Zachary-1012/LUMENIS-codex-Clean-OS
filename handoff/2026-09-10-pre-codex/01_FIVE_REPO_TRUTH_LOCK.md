# LUMENIS FIVE-REPO TRUTH LOCK
## Pinned supplement — execute before all other handoff instructions

Priority: highest. This is an additive guardrail; it does not replace the master handoff.

## Repositories to relationship-audit before implementation

1. `Zachary-1012/LUMENIS-codex-Clean-OS`
2. `Zachary-1012/Z-Brand-Core`
3. `Zachary-1012/Zachary-OS-AI`
4. `Zachary-1012/lumenis-command`
5. `Zachary-1012/global-growth-intelligence`

If additional relevant repositories exist at execution time, classify them as RELATED_REPO or UNRELATED_REPO before use. Never merge automatically.

## Canonical rule

Treat `LUMENIS-codex-Clean-OS` as the current canonical production repository candidate, but re-verify current README, AGENTS, governance, Production Acceptance, Capability Registry, branches, latest commits and source. If governance explicitly moved, report `CANONICAL_DRIFT` with evidence rather than guessing.

## Role taxonomy

Classify each repo as one or more of: `PRODUCTION_CORE`, `LEGACY_CAPABILITY_SOURCE`, `AI_RESEARCH_OR_RUNTIME_SOURCE`, `ENGINEERING_GOVERNANCE_SOURCE`, `COMMAND_OR_CONTROL_SOURCE`, `EXPERIMENTAL_SOURCE`, `KNOWLEDGE_SOURCE`, `ARCHIVE_REFERENCE`, `UNKNOWN`.

There must be one Production Truth Owner per production concern unless actual architecture proves a deliberate multi-repo production model.

## Repository-specific rules

### Z-Brand-Core
Do not discard it as old. Use it as historical/legacy production-capability evidence. Recover capability, not obsolete implementation blindly. Audit monitoring, collection, reports, events, cases, Campaign, KOS/KOL/KOC/UGC, Podcast, Research, Evaluation, Operations, AI integration, Browser, Settings, Runtime, Scheduler, Recovery, Evidence, Canonical data, Subject logic and UI capability. Legacy UI is evidence only and must not automatically become final UI.

### Zachary-OS-AI
Determine the real AI boundary: runtime, Agent, routing, skills, tooling, browser, memory/context, research, evaluation, fallback, local AI and provider abstraction. Integrate via explicit API/SDK/service/adapter/package/submodule/event boundary. Do not create two AI truth owners.

### lumenis-command
Determine what belongs to engineering command/governance/control-plane/DCC/local bridge/permission/task/audit/deploy versus product runtime. Preserve READ/TASK/AUDIT/WRITE/DEPLOY boundaries.

### global-growth-intelligence
Classify by source as independent product, growth/research capability source, experiment or post-closure reference. If not required by current Production Closure, mark `REFERENCE_ONLY` or `POST_CLOSURE`; do not force it into the P0 spine.

## Required cross-repo outputs

Create/update `CODEX_FIVE_REPO_RELATIONSHIP_MAP.json`, `CODEX_CROSS_REPO_CAPABILITY_DIFF.json`, capability recovery queue, owner-conflict list and branch/HEAD/merged-vs-unmerged truth.

Capability states: `PRESENT_AND_VERIFIED`, `PRESENT_BUT_PARTIAL`, `PRESENT_BUT_UNREACHED`, `MISSING_IN_CANONICAL`, `LEGACY_ONLY`, `DUPLICATED`, `CONFLICTING`, `SUPERSEDED`, `POST_LAUNCH`, `UNKNOWN`.

Recovery actions: `KEEP_CURRENT`, `PORT_CAPABILITY`, `REIMPLEMENT`, `ADAPT`, `MERGE`, `WRAP`, `DEPRECATE_AFTER_REPLACEMENT`, `ARCHIVE`, `UNKNOWN`.

## Hard truth rules

Docs do not override runtime. File existence does not equal completion. Route declaration does not equal registration. UI entry + API 404 = BROKEN. HTTP 200 with mock/fallback fake data = NOT_VERIFIED/FAKE_200_RISK. UNKNOWN must remain UNKNOWN until evidence proves otherwise.

## No-loss / no-fake red lines

DO NOT LOSE CAPABILITIES.
DO NOT LOSE CODE.
DO NOT LOSE HISTORY.
DO NOT LOSE DATA.
DO NOT LOSE TEST EVIDENCE.
DO NOT LOSE LOCAL WORK.
DO NOT FAKE PASS.
DO NOT FAKE RUNTIME.
DO NOT FAKE E2E.
DO NOT FAKE PRODUCTION READY.
DO NOT TREAT DOCS AS RUNTIME EVIDENCE.
DO NOT TREAT FILE EXISTENCE AS CAPABILITY COMPLETION.
DO NOT MERGE FIVE REPOS BLINDLY.
DO NOT ALLOW MULTIPLE PRODUCTION TRUTH OWNERS.

After this truth lock, execute `02_CODEX_ZERO_DISCOVERY_MASTER.md` without deleting or weakening any requirement.