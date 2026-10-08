# LUMENIS engineering tools

This directory implements development tooling, not product architecture or production truth.
Root AGENTS.md and the current source/owner/contracts govern product work.

- Lifecycle source: hooks/lumenis_hooks.py; register it once per workstation in ~/.codex/hooks.json after native /hooks trust. Do not duplicate the same handler in both user and project hook registrations. hooks.example.json is a portable-reference template that requires local Python/path review.
- Native Hook trust is required before lifecycle execution. Workstation trust is stored by Codex against the current hook hash; when a hook definition changes, re-review its current hash instead of bypassing trust. Hook trust never grants model-selection authority.
- Historical engineering-helper self-test command (retained for provenance; do not execute under the current policy): python -X utf8 -m unittest discover -s .codex/tests -v. The helper reads verification_policy.run_unit_integration_allowed from the machine contract and refuses execution while it is false.
- Local MCP: lumenis_engineering. Its server and bounded source/routing helpers are versioned in this repository under .codex/mcp/server.mjs and .codex/engineering.py. It exposes bounded source, routing, Git, health and verification-planning operations; module-suite execution is prohibited by current machine policy, and no arbitrary shell or product-test execution is exposed over MCP.
- Compile/static, build, security/permission and data-consistency checks must use the native Codex sandbox or their existing owner tool. Complete applicable recovery and real-user E2E on the running product with permitted real inputs. Unit/integration module suites may not be created, run, or renamed under the current verification_policy. A check observation never proves full product E2E or release readiness.
- Runtime state is outside the product repository in ~/.codex/lumenis-engineering-state.
- The MCP SDK binary/package, workstation registration and diagnostics stay workstation-local and are never Product Truth. The MCP logic itself is repository-versioned; a clean clone must install/point to a compatible SDK and register the in-repo server locally rather than depend on another machine's hidden helper source.
- LUMENIS engineering role defaults are recorded in `model-routing.toml`: M/F use GPT-6 Astra ultra, C1-C6 use GPT-6.1 Sol ultra, and task subagents default to GPT-6 Luna max. These are defaults only. The Product Owner's manual selection in a current window always wins, explicit spawn settings override the subagent default, and Hooks never change model/effort/service tier.
- Workstation launch helpers are `codex -p lumenis-m`, `codex -p lumenis-f`, `codex -p lumenis-c` and `codex -p lumenis-task`; the profile files live in `~/.codex`, are not Product Truth, and only provide an initial model/effort. A later manual picker/CLI choice in that window wins immediately.
- `project_doc_max_bytes = 131072` preserves headroom for the current root AGENTS.md because Codex applies a shared project-instruction byte budget. If the router grows beyond the configured budget, fix the router/budget and fail the governance gate rather than accepting silent instruction truncation.
- `web_search = "live"` is retained so an owning window can resolve technical blockers from current official documentation and maintained upstream GitHub/high-quality implementations, then implement and verify the strongest feasible complete solution without spawning duplicate research windows.
- `goals = true` is retained for multi-turn closure work with a stable finish line: the Goal must mirror the current window's complete approved outcome, verification surface, constraints and blocked-stop conditions. It is thread-scoped continuity, never a new Product Authority or a license to shrink scope.
- `skill_search = true` is retained so Codex can discover and reuse existing engineering workflows instead of re-creating them. Skills remain subordinate to AGENTS/Product Architecture/Owner/Permission and may not redefine product scope.
- The tracked project config registers OpenAI's official read-only developer-documentation MCP as `openaiDeveloperDocs` at `https://developers.openai.com/mcp`; keep this as the single LUMENIS definition rather than duplicating it in user config. It is an optional current-documentation source (`required = false`), never Product Truth or a shipped dependency. Context7 remains a complementary current-library documentation source.
- No top-level repository model/provider/service-tier/review-model override is defined. The only native project model default is `[agents] default_subagent_model = "gpt-6-luna"` with `max` reasoning, matching `model-routing.toml`; an explicit spawn or Product Owner manual choice has precedence.

Secrets, data files, browser sessions, production database writes and unknown local changes are outside this tooling task. Do not alter them to make an installation check green.

## Local deterministic developer workflow (2026-10-09)

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
