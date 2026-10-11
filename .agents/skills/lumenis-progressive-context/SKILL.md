---
name: lumenis-progressive-context
description: Use for LUMENIS work to resolve the smallest current owner context with progressive disclosure, preserving historical research and acceptance evidence without repeating full-repository audits.
---

# LUMENIS Progressive Context

Use this skill before changing an existing LUMENIS capability or accepting a
bounded implementation Batch. It is a navigation and context-loading workflow;
it does not create a new product authority, owner, data store, design system,
or release gate.

Use repository `AGENTS.md` as the only execution router. Its C1–C6 rows retain
engineering source responsibilities, not six product rounds or a fixed local/Cloud
assignment. Product outcomes follow SYSTEM, CTH, BMP, Shared and Agent Groups / AI;
the Source Owner Index maps and preserves R01–R15 and J1–J8 acceptance coverage. Actual
dispatch and model settings require current Product Owner instruction and evidence.
Any explicitly authorized Cloud worker follows the existing isolation constraints
and these checked-in instructions without workstation-only skills or personal settings.

## Purpose

Load the context needed for the active slice in this order:

```text
current remote/local truth
→ active owner
→ current contract and governing rules
→ exact source and callers
→ targeted tests/runtime evidence
→ relevant historical research
→ bounded context manifest
```

This prevents two common failures:

- treating a short README as the whole product history;
- repeating a full-repository scan when one capability can be routed locally.

Historical research, handoffs, screenshots, reports, and sketches are inputs
for reasoning and provenance. They may reveal an intended capability or a
useful constraint, but they cannot override executable source, current
contracts, runtime evidence, Permission, Evidence, Canonical Data, or the
Experience Constitution.

## Required workflow

1. Resolve the repository root, branch, `HEAD`, `origin/main`, and dirty paths.
   Preserve all pre-existing work. Never reset, clean, bulk-stage, or overwrite
   an unknown path.
2. Run the bounded locator for the capability and task term:

   ```powershell
   python scripts/audit_tools/locate_capability_context.py `
     --capability <existing-family> `
     --query <specific-task-term>
   ```

   Use `--path <source-path>` when the source owner is already unambiguous.
   Treat the locator output as a map, not as a replacement for source or
   runtime truth. If it fails closed, resolve the owner from the current
   Source Owner Index before editing.
3. Read only the current rules and contracts named by the locator and the
   active owner row. Include the relevant Permission, Evidence, data, runtime,
   Experience, and real-user acceptance contract when that slice uses them.
   For Codex Cloud work, also follow the exact base-SHA, approved-input,
   protected-data and W6 patch-return rules in root `AGENTS.md`.
4. Inspect the exact source, callers, view models/API bindings, and targeted
   tests. Follow the existing owner chain and reuse before creating anything.
5. Search historical research only with terms from the active capability. Record
   the source path, date/version if available, and whether it is `ADOPT`,
   `ADAPT`, `DEFER`, `REJECT`, or `REFERENCE_ONLY`. Do not import historical
   text into production truth just because it sounds authoritative.
6. Stop loading context once the active owner, contract, implementation path,
   acceptance evidence, and unresolved boundary are known. Do not run a repository-wide audit for a local gap, stale note, or runner failure.
7. Before implementation or acceptance, write a bounded context manifest in
   the task artifact location or the owning evidence path. Do not add a new
   product registry solely for this manifest.

## Bounded context manifest

The manifest may be JSON or Markdown, but it must contain these fields:

```yaml
capability: <name>
query: <task term>
remote_head: <verified SHA>
local_head: <verified SHA>
dirty_paths_preserved: true
owner: <current owner>
current_rules:
  - path: <current rule or contract>
    role: authority | constraint | acceptance
implementation_paths:
  - <source/caller/view-model path>
tests_and_runtime_evidence:
  - path: <targeted evidence>
    status: PASS | FAIL | LIVE_NOT_VERIFIED | BLOCKED | UNKNOWN
historical_inputs:
  - path: <research or handoff>
    decision: ADOPT | ADAPT | DEFER | REJECT | REFERENCE_ONLY
    reason: <one sentence>
unresolved_boundary: <known gap or NONE>
next_action: <one bounded action>
```

`remote_head` and `local_head` must come from Git commands in the current
checkout. A manifest never promotes a local-only change to online truth and
never turns a test, fixture, HTTP 200, model response, or static document into
real-user acceptance.

## Loading and search limits

- Prefer `rg` with a capability-specific path or term. Read the smallest useful
  slice of a file, then expand only when a caller or contract requires it.
- Read current governance before historical documents when the two disagree.
- Use the existing locator families and Source Owner Index. If no family fits,
  record the missing route and resolve it explicitly; do not invent a parallel
  owner to avoid the ambiguity.
- A full-repository re-audit is allowed only for a structural trigger defined
  by the current Source Owner Index or when the active owner cannot be resolved
  after targeted inspection. Record that trigger in the manifest.
- Keep secrets, cookies, production databases, and private session material out
  of manifests, command output, commits, and research notes.

## Completion

Before returning the Batch to Sol, report:

```text
CONTEXT_READY | CONTEXT_BLOCKED
owner and exact paths
current rules/contracts read
historical inputs and decisions
targeted tests/runtime evidence
unresolved boundary
next bounded action
```

This skill does not authorize implementation, migration, collection, publishing,
external effects, or release. Those actions still require their canonical owner,
Permission/Evidence boundary, proportional verification, and Sol acceptance.
