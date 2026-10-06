# LUMENIS engineering tools

This directory implements development tooling, not product architecture or production truth.
Root AGENTS.md and the current source/owner/contracts govern product work.

- Lifecycle source: hooks/lumenis_hooks.py; register it once per workstation in ~/.codex/hooks.json after native /hooks trust. Do not duplicate the same handler in both user and project hook registrations. hooks.example.json is a portable-reference template that requires local Python/path review.
- Native /hooks trust is required before lifecycle execution. No automatic or forged trust is installed.
- Regression: python -X utf8 -m unittest discover -s .codex/tests -v.
- Local MCP: lumenis_engineering. Its server and bounded source/routing helpers are versioned in this repository under .codex/mcp/server.mjs and .codex/engineering.py. It exposes bounded source, routing, Git, health and test-planning operations; no arbitrary shell or product-test execution is exposed over MCP.
- Build/test commands must use the native Codex sandbox. A check observation never proves full product E2E or release readiness.
- Runtime state is outside the product repository in ~/.codex/lumenis-engineering-state.
- The MCP SDK binary/package, workstation registration and diagnostics stay workstation-local and are never Product Truth. The MCP logic itself is repository-versioned; a clean clone must install/point to a compatible SDK and register the in-repo server locally rather than depend on another machine's hidden helper source.
- Codex model/provider/service-tier/reasoning choices are **not** configured by this repository. The Product Owner's current window selection is authoritative; spawned agents inherit the parent selection unless the Product Owner explicitly chooses otherwise. Do not add repository/profile/env/subagent overrides or automatic model downgrade/fallback. Native Codex UI/session persistence of the Product Owner's own last selection is allowed and must not be treated as a LUMENIS-authored default.
- `project_doc_max_bytes = 131072` preserves headroom for the current root AGENTS.md because Codex applies a shared project-instruction byte budget. If the router grows beyond the configured budget, fix the router/budget and fail the governance gate rather than accepting silent instruction truncation.
- `web_search = "live"` is retained so an owning window can resolve technical blockers from current official documentation and maintained upstream GitHub/high-quality implementations, then implement and verify the strongest feasible complete solution without spawning duplicate research windows.
- The workstation may register OpenAI's official read-only developer-documentation MCP as `openaiDeveloperDocs`; it is an optional current-documentation source, never Product Truth or a shipped dependency. Context7 remains a complementary current-library documentation source.
- No repository `review_model`, subagent model, provider, service tier or reasoning override is defined. Native Codex reviews and spawned agents therefore use the active parent/session selection unless the Product Owner explicitly changes that window.

Secrets, data files, browser sessions, production database writes and unknown local changes are outside this tooling task. Do not alter them to make an installation check green.
