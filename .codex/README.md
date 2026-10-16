# LUMENIS engineering tools

This directory implements development tooling, not product architecture or production truth.
Root AGENTS.md and the current source/owner/contracts govern product work.

- Lifecycle source: hooks/lumenis_hooks.py; register it once per workstation in ~/.codex/hooks.json after native /hooks trust. Do not duplicate the same handler in both user and project hook registrations. hooks.example.json is a portable-reference template that requires local Python/path review.
- UserPromptSubmit is treated as user input; duplicate-event detection uses its turn ID, never marker text in the prompt body.
- Native Hook trust is required before lifecycle execution. Workstation trust is stored by Codex against the current hook hash; when a hook definition changes, re-review its current hash instead of bypassing trust. Hook trust never grants model-selection authority.
- Authorized isolated engineering-helper regression command: python -X utf8 -m unittest discover -s .codex/tests -v. The helper reads verification_policy.run_unit_integration_allowed from the machine contract and refuses execution while it is false.
- Local MCP: lumenis_engineering. Its server and bounded source/routing helpers are versioned in this repository under .codex/mcp/server.mjs and .codex/engineering.py. It exposes bounded source, routing, Git, health and verification operations; selected regressions follow current explicit machine policy and Owner admission. No arbitrary shell or broad product-suite execution is exposed over MCP.
- Compile/static, build, security/permission and data-consistency checks must use the native Codex sandbox or their existing owner tool. Complete applicable recovery and real-user E2E on the running product with permitted real inputs. Unit/integration regressions are restored under the 2026-10-10 verification_policy; preserve their actual test classification. A check observation never proves full product E2E or release readiness.
- Runtime state is outside the product repository in ~/.codex/lumenis-engineering-state.
- The MCP SDK binary/package, workstation registration and diagnostics stay workstation-local and are never Product Truth. The MCP logic itself is repository-versioned; a clean clone must install/point to a compatible SDK and register the in-repo server locally rather than depend on another machine's hidden helper source.
- `model-routing.toml` records Product Owner manual selection and factual readback, with no M/F/C1-C6 fixed model/effort assignment. Hooks report only available event metadata. Historical workstation launch profiles cannot override the user's selected settings.
- `project_doc_max_bytes = 131072` preserves headroom for the current root AGENTS.md because Codex applies a shared project-instruction byte budget. If the router grows beyond the configured budget, fix the router/budget and fail the governance gate rather than accepting silent instruction truncation.
- `web_search = "live"` is retained so an owning window can resolve technical blockers from current official documentation and maintained upstream GitHub/high-quality implementations, then implement and verify the strongest feasible complete solution without spawning duplicate research windows.
- `goals = true` is retained for multi-turn closure work with a stable finish line: the Goal must mirror the current window's complete approved outcome, verification surface, constraints and blocked-stop conditions. It is thread-scoped continuity, never a new Product Authority or a license to shrink scope.
- `skill_search = true` is retained so Codex can discover and reuse existing engineering workflows instead of re-creating them. Skills remain subordinate to AGENTS/Product Architecture/Owner/Permission and may not redefine product scope.
- The tracked project config registers OpenAI's official read-only developer-documentation MCP as `openaiDeveloperDocs` at `https://developers.openai.com/mcp`; keep this as the single LUMENIS definition rather than duplicating it in user config. It is an optional current-documentation source (`required = false`), never Product Truth or a shipped dependency. Context7 remains a complementary current-library documentation source.
- No top-level repository model/provider/service-tier/review-model override is defined. The only native project model default is `[agents] default_subagent_model = "gpt-6-luna"` with `max` reasoning, matching `model-routing.toml`; an explicit spawn or Product Owner manual choice has precedence.

## Compaction and recovery / 压缩与续接

Use durable context in the existing Owner record; a model summary is lossy.
Keep one `continuity` section in that record, not a new Task Card or scheduler.
Frozen outcome IDs and normalized implementation source paths survive context clear.
Rebinding to a different record requires rereading the prior record and validating
its current closure receipts; cached closure alone is insufficient. A new direct
PO message must be reconciled before reusing a closure, blocker or deferral exit.
必须保留完整目标、最新 PO 来源与更正、约束、已有证据、全部未完项和下一步；
摘要不是新的调度授权。原生 Goal 的旧暂停标记不能覆盖更新的直接 PO 指令。

The JSON section retains these fields; the optional `delivery` object below binds
the current task's complete outcome constraints without creating another queue:

```json
{
  "owner": "M",
  "objective": "The complete approved outcome and acceptance boundary",
  "po_source": "Dated direct PO instruction and existing provenance reference",
  "constraints": ["Current scope, rights, costs, writer boundaries and corrections"],
  "completed": ["Exact achieved result, evidence reference and limits"],
  "remaining": ["Every unmet requirement, including external blockers"],
  "next_action": "The next safe executable step",
  "pending_effects": [],
  "source_paths": [".codex/hooks/lumenis_hooks.py"],
  "evidence_paths": [],
  "native_goal": "Current observed Goal reference/status, or NOT_VERIFIED"
}
```

`pending_effects` records unresolved operation IDs, status and existing receipt
pointers; an empty list asserts none known, not a universal safety proof. Record
no credentials, Cookies, raw private prompts or production data. References are
explicit repository text files; `work/` records are local protected evidence and
are never automatically committed or sent to a service.

When a pending effect is admitted, `delivery.effect_ledger` retains its exact-text
SHA-256 identity with `status: PENDING`; those IDs must match the top-level
`pending_effects` list. Resolve it by changing that entry to `RESOLVED` and
including a declared local JSON receipt path plus the receipt SHA-256. The receipt
identifies the same effect, records a terminal readback (`APPLIED`,
`NOT_APPLIED`, `FAILED`, `CANCELLED` or `RECONCILED`), an observation and current
pins for the complete admitted source scope. The ledger keeps the resolved entry
across sessions; its exact receipt reference is frozen. Its source pins and head
describe the implementation version at the time of the operation. They are checked
when the effect first resolves; a later source edit does not invalidate that
historical readback or authorize replay. Current implementation acceptance still
uses its own current-source receipts. New effects may be appended as `PENDING`,
then become immutable after their receipt is admitted. Removing the pending item
or leaving the list empty alone cannot resolve an effect.
The frozen admission must also survive context clearing. A fresh guard cannot
import already-resolved effects without that prior admission; preserve the old
record, receipt and guard for reconciliation, never replay the external effect.
Admission reserves evidence-list space for pending resolutions and each outcome's
operation/recovery receipts before another effect is added.

```powershell
# Refresh at admission, meaningful outcome/PO correction, or planned handoff.
python .codex/engineering.py continuity --params '{"mode":"save","record":"work/<existing-owner-record>.json","section":"continuity"}'
# On compact/resume, before source writes or any uncertain operation retry.
python .codex/engineering.py continuity --params '{"mode":"read"}'
```

The command uses the current native `CODEX_THREAD_ID`/`CODEX_SESSION_ID` and agent
identity, the existing per-session engineering state, lock and atomic replace.
No stable identity means no shared fallback record. It never changes a native
Goal, dispatch, model, product source, database, service or user configuration.
Locks use the operating system's file locking and release on process death;
an unknown legacy lock requires exact process-owner readback before archival.
Do not remove another window's lock. Verification receipts use the bound source
scope, HEAD and current verification policy; unrelated Owners' edits do not
force repeat validation. Changed in-scope bytes still invalidate that evidence.
Stop compares actual scoped changes with the original baseline, including committed
changes; a clean tracked scoped file is not a change. Other Owners' mutations do
not impose this task's checks. Frontend `.astro`/`.css` and bounded `.log` evidence
are supported text pins; private/session/data exclusions remain enforced.

- `PINNED_CONTEXT`: referenced bytes and recorded local version match; read the
  record and latest direct PO instruction. This is not authorization/acceptance.
- `RECONCILE_REQUIRED`: only inspect reported changes/new message/pending effects,
  reconcile the existing record, then bind the reviewed version. Do not blindly
  refresh pins, repeat effects or stop other windows.
- `READBACK_REQUIRED`: bind the actual current Owner record after verifying the
  current instruction; never borrow another thread's context.

PreCompact stores a bounded local snapshot without updating task pins or copying
raw task text into global state. PostCompact records the event; native
SessionStart(source=compact) injects the readback pointer before continuation.
The original verification baseline stays intact; displayed HEAD is fresh local
HEAD, while origin/main is explicitly cached and needs a fresh fetch at integration.
Missing/truncated/disabled hooks require this same manual command, not a new loop.

依据 / Sources: [OpenAI durable project memory](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex),
[official hook lifecycle](https://developers.openai.com/codex/hooks),
[fixed Codex compact prompt](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/prompts/templates/compact/prompt.md),
[fixed SessionStart after compaction](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/session/mod.rs).
These describe recovery mechanics, not a guarantee of error-free model execution.

### Complete-outcome guards / 完整成果约束

The same Owner continuity record can include `delivery` (schema version 1).
Record the complete direct-PO outcome before implementation, with stable existing
requirement IDs, observable acceptance conditions, all coverage references and
hash-pinned source documents. A rebind may add requirements; it cannot silently
remove their IDs, weaken acceptance or drop coverage. Keep prior requirements
when the PO changes scope and record the exact new instruction. `DEFER`, source
presence, a PR or CI success never closes an approved requirement.

`delivery.status` describes this task: `RUNNING`, `REPORT_ONLY`, `PO_PAUSED`,
`APPROVAL_WAIT`, `EXTERNAL_BLOCKED`, `PO_DEFERRED` or `JOB_CLOSED`. Each requirement records
`id`, `outcome_class`, `acceptance`, `coverage_refs`, its actual `status`, and
`evidence`. Freeze `PRODUCT` versus `DEVELOPMENT_TOOL` at admission: a product
outcome requires real user E2E and recovery; a tool workflow cannot replace it.
`scope_sources` records each original scope document's `path` and `sha256`.
Evidence points to bounded existing JSON receipts with the recorded outcome,
historical source HEAD and the complete admitted source/scope-file hashes. An
unrelated commit or later scope addition does not invalidate a closed outcome
whose original source pins are unchanged. Its exact receipt references and bytes
remain frozen under the same record/session binding. New or reopened outcomes
require current complete-scope outcome and recovery receipts. A changed original
source invalidates current closure: explicitly reopen, preserve historical
receipts, verify the new version, then close again. Historical receipts alone
cannot accept changed source. Receipts distinguish real user work, tool workflow
and recovery from isolated automated checks. Original
requirements and source documents remain the coverage authority: a hook cannot
prove that an initial checklist omitted nothing or that a self-authored receipt
describes a real event.

A fresh execution binding first admits a RUNNING outcome with unfinished work;
pre-existing terminal records cannot be stamped as the new instruction. Report-only
turns freeze the bound record, sources, authority and evidence paths, including
ignored files and context-clear recovery, so modifying those inputs remains visible.
For a running task, Stop rejects remaining unclosed work and unaudited completion
claims even when no source changed. Complete status requires current receipt
readback for every requirement and an empty top-level `remaining` list. The concise
continuity narrative is limited to 24,000 serialized Unicode characters; the structured `delivery`
evidence budget is separately limited to 8,000,000 bytes, supporting up to 100
outcomes with full operation and recovery receipts. Up to 220 evidence paths are
allowed. These bounds do not establish that a receipt is truthful. Paths are
normalized before change comparison, including `./` spellings. A report-only reply, direct PO pause, required
approval or evidenced external blocker is a non-completion exit: preserve the
remaining work, exact reason and next/resume condition. `PO_DEFERRED` is a
non-closure exit only when every unfinished requirement is explicitly deferred,
its exact PO source and ID appear in a current hash-pinned local source receipt,
and the exit names those IDs and their resume condition. A new PO message requires
reconciling that deferral; it does not silently inherit a historical stop. Blocker/deferral
proof identities and hashes, unfinished requirement IDs, and the authorizing
prompt-turn binding are retained across rebinding, `RUNNING` and context clear.
Editing display reason or resume wording cannot refresh the authorization. Reusing
an old blocker or deferral cannot become current by refreshing only the prompt hash;
a fresh blocker readback or renewed direct PO receipt is required. Direct
standalone Chinese and English pause/approval instructions are recognized.
A generic blocker cannot
stop independent authorized work. Hooks never dispatch another window, start a
suite, call a model or change account/model/effort/tier. One corrective continuation
is permitted; repeated Stop failure terminates with an explicit incomplete state,
preventing an unbounded retry loop. Legacy records remain readable but do not
claim these additional machine constraints until explicitly bound.

Dynamic maintenance means reconciling this existing record after a new direct PO
instruction, meaningful outcome, changed source/runtime version or invalidated
evidence. Reuse unaffected receipts; recheck affected boundaries. Do not weaken
verification policy or automatically install/upgrade plugins to obtain a PASS.
Current read-only questions must not inherit a demand to rerun checks for older
session edits; those unfinished checks remain required before delivery. Source,
runtime, database, user outcome and publication are separate acceptance facts.

After publishing a hook update, verify the actually registered handler and native
`hooks/list` trust/readback. A source change alone is not active enforcement.
Keep one registration, preserve other handlers and settings, and never edit the
native trust store. If native reapproval is required, report that precise condition
instead of calling the hook active. Rollback uses the reviewed previous published
handler/configuration, not a reset or overwrite of product candidates.

### Actual verification receipts / 真实退出码回执

Some native `Bash` PostToolUse events contain only stdout text and no process
exit code. Empty stdout never establishes success. The hook retains that unknown
observation without replacing a verified result with a fabricated exit code.
For an explicitly selected check whose exit metadata is absent, the existing CLI
can execute a bounded command and record its actual subprocess result:

```powershell
python .codex/engineering.py verification_run --params '{"kind":"compile","argv":["python","-X","utf8","-m","py_compile",".codex/engineering.py"],"timeout_seconds":60}'
```

Bind the reviewed current Owner continuity first. Commands use argv arrays, not
shell strings, and must match the existing compile/static/targeted-regression
allowlist and current machine verification policy. The runner records RUNNING
before execution, actual return code or timeout, and source/HEAD/policy pins
before and after. Changed inputs cannot produce a passing receipt. A missing
receipt is not permission to repeat a completed expensive check: first inspect
its original tool/process result; use this route for necessary subsequent checks.
The current record, Owner, authority/evidence hashes, HEAD and prompt must still
match admission; after a relevant change, read/reconcile and rebind explicitly.
Edits within admitted source scope are expected, but the selected check pins
their exact start/end bytes. Known pending effects remain recorded and are never
replayed by this check. Hook exit status accepts only an actual top-level integer
exit field; output text, nested claims and empty output remain UNKNOWN.

For an Owner-reviewed product regression, the same runner accepts exactly one
literal pytest node, not a folder/suite or arbitrary flags:

```powershell
python .codex/engineering.py verification_run --params '{"kind":"test","argv":["python","-X","utf8","-m","pytest","-q","--no-header","-p","no:cacheprovider","tests/<reviewed_file>.py::<actual_test_node>"],"timeout_seconds":60}'
```

The test file and active conftest/fixture modules require current Owner review;
this readback grants no permission to edit another Owner's files. The runner pins
all configuration/conftest candidates (including ABSENT), fixes pytest -c/rootdir,
and admits only named, recursively reviewed fixture edges with exact source hash,
Owner and purpose. The C3/C4/C5 socket guards remain enabled; a changed hash or
unknown plugin fails closed. Authority, task records, evidence and reviewed shared
fixtures stay immutable even if included in the editable source list. Existing test
setup and data guards still execute. Plugin autoload/cache are disabled, and
zero executed or only skipped tests do not yield passing verification. AST checks
reject recognized unsafe direct actions but cannot prove indirect dependencies
safe: the Owner must review their source/effects first. No model/collection/
production-DB/deployment authority follows from a test command.
Hooks never launch checks themselves. This mechanism records engineering evidence
only; it grants no dispatch, model call, production write or product acceptance.
The upstream limitation is visible in the fixed
[ExecCommand hook payload](https://github.com/openai/codex/blob/a07c8ebd57feedc4cf5dfe854c8e9101de54186b/codex-rs/core/src/tools/context.rs).

Secrets, data files, browser sessions, production database writes and unknown local changes are outside this tooling task. Do not alter them to make an installation check green.

## Local deterministic developer workflow (2026-10-09)

Ruff CLI is a required local static tool when Python paths are checked. This workstation now exposes `ruff --version` through its existing `D:/devtools/bin` entry and pins Ruff 0.16.9 in `D:/devtools/lumenis-engineering/ruff-0.16.9`; the ignored `tools.local.json` binds the exact executable. VS Code keeps its same-version bundled server. On another workstation resolve its installed executable, then use the existing official-source installation authority for a missing tool; do not silently skip a required static check. Record UNAVAILABLE only at a verified permission/resource boundary and continue independent work. Installation hashes/rollback and actual checks stay in protected local receipts; no model calls or production Python dependency changes.


Use PowerShell 7.5+ and Python 3.11+; the existing project's Python/type policy remains unchanged. VS Code's native Tasks call `scripts/local_development.ps1`, backed by `.codex/local_workflow.py`. They do not launch Codex, a provider, module suites, product services, commit or push. The official language extensions supply local completion/diagnostics; automatic save fixes, heavy automatic Tasks, test discovery and AI completion are disabled for this workspace.

```powershell
pwsh -NoProfile -File scripts/local_development.ps1 -Action snapshot -Owner M
pwsh -NoProfile -File scripts/local_development.ps1 -Action check -Owner M -PathsJson '[".codex/local_workflow.py","scripts/local_development.ps1"]'
pwsh -NoProfile -File scripts/local_development.ps1 -Action diff -Owner M -Paths .codex/local_workflow.py
pwsh -NoProfile -File scripts/local_development.ps1 -Action format-preview -Owner M -Paths .codex/local_workflow.py
pwsh -NoProfile -File scripts/local_development.ps1 -Action locale-preview -Owner F
pwsh -NoProfile -File scripts/local_development.ps1 -Action build -Owner F -Target website
pwsh -NoProfile -File scripts/local_development.ps1 -Action build -Owner F -Target flutter-web
```

Checks select exact files, keep actual diagnostic positions/exit codes and never fix automatically. Python uses AST and Ruff, Dart uses existing analyzer/formatter, PowerShell uses parser/PSScriptAnalyzer, JS uses Node syntax; Astro/TS checks require their available existing parser. A syntax parser does not prove full type correctness. Missing tools fail honestly. Locale generation runs the pinned existing Dart generator against existing schemas in a temporary mirror, previews the output, and never overwrites a product-generated file. Formatting supports only the explicitly configured Python/Dart formatters. Builds use fixed Astro/Flutter commands with no dependency installation/lifecycle hooks; success cache requires matching HEAD, input/tool/command and output hashes.

Local absolute executable paths can be supplied in ignored `work/m-governance-20261008/devtools/tools.local.json` (schema `{"version":1,"tools":{"python":"...","ruff":"...","dart":"...","pwsh":"...","node":"...","npm":"..."},"flutter_tools_snapshot":"..."}`). Values must be absolute file paths, not commands or flags. Keep extensions outside the VS Code application installation directory so application updates cannot erase them. Installation/source/version/license evidence stays in the protected local receipt path; the extensions are developer tools, not redistributed product dependencies.

Actual source formatting is a separate explicitly authorized action. Freeze the exact file and current writer first. The manifest below is stored inside the protected default receipt path and pins current raw reservation bytes:

```json
{
  "head": "actual current HEAD",
  "owner": "M",
  "reservation_path": "work/w6-integration-20261002/dispatch-20261008/SHARED-RESERVATIONS.json",
  "reservation_sha256": "actual current raw reservation SHA-256",
  "paths": [{"path": ".codex/local_workflow.py", "preimage_sha256": "actual current file SHA-256"}]
}
```

Only a matching current Owner/RESERVED/head/exact allowed path is eligible. This tooling delivery uses the existing `M_local_development_automation` reservation, not a new writer authority. `-Action format-apply -Paths <exact-file> -Manifest <manifest>` requires the exact manifest; `-Action rollback -Paths <exact-file> -Receipt <prior-format-receipt>` restores only exact format postimages under the same valid grant. Source backups and durable intent are written first. The process lock coordinates this helper's writers; it does not lock external editors or authorize an uncertain writer. Changed HEAD, source, reservation, path links or grant stops the affected write. Do not broaden the manifest to force success.

Every action writes ignored private JSON receipts with times, actual exit, source/version range, bounded error, authorization/recovery and tool-spawned model calls (zero). Failed receipts remain failed; later success records recovery separately. Read-only actions and equal formatting inputs do not write source. Static/build/tool acceptance cannot mark a business Job closed, nor prove Runtime/DB/user acceptance. M/W6 still review the exact accepted source and CURRENT co-publication before ordinary main integration.

Rollback this developer configuration by restoring its private preimage backups after verifying no later user change, disabling these Tasks or uninstalling only this delivery's added extensions via the official Code CLI. Never reset/clean the product tree or restore an entire old profile. Existing C1 and earlier M source/material work stay protected and independently unfinished.

### Editor recovery without another tool stack

Compare the running Code process's actual `--extensions-dir` and `--user-data-dir`
with the installed extension directory before reinstalling anything. A stale
launcher path can leave installed language extensions inactive. Keep the durable
extension directory; repair only the verified missing local alias or launcher
path, with a private preimage and link-target record. Do not bypass publisher or
workspace trust. Restart only the affected language/extension host after checking
that it does not own another active task; do not restart product services.

For PowerShell, select the already-installed compatible PowerShell 7 executable
through `powershell.powerShellAdditionalExePaths` and
`powershell.powerShellDefaultVersion` in the actual profile. Keep machine-specific
paths out of portable repository settings. Do not install a second shell to fix a
discovery error or change the user's general terminal/profile selection.

Dart-Code 3.144 resolves `dart.analysisExcludedFolders` relative to each workspace
folder; it does not expand `${workspaceFolder}` in that setting. Use the checked-in
relative paths, close temporary Dart files inside excluded historical copies, and
restart the Dart analysis server after this setting changes. Retain the real
`app/` project, its existing type/lint policy and diagnostics. Do not suppress
legitimate errors, delete historical tests or set the deprecated
`onlyAnalyzeProjectsWithOpenFiles` to hide the scanning problem.

Use the native **Trigger Suggest** command for non-model completion; do not confuse
it with **Trigger Inline Suggestion**. Check keybindings before diagnostics actions:
the PowerShell extension can bind F8 to run a selection. Inspect Problems directly
instead of executing a script. Real editor acceptance and exact private receipts
are indexed in the existing round-15 bounded delivery record; they are development
tool evidence, not product Job closure or a total Codex-token savings claim.
