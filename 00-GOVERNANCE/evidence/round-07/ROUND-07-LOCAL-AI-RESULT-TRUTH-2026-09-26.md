# ROUND 07 — Local AI completion truth in existing compatibility client

Sol decision: PASS FOR BOUNDED BATCH / ROUND EXIT NOT ACCEPTED. This fixes the existing LocalAIClient compatibility path used by local-AI routes. HTTP 200 alone no longer marks an empty, whitespace-only, non-text, reasoning-only, or explicitly unfinished Ollama completion successful. Nonempty completed replies and explicit unavailability preserve their prior contracts. The canonical SYSTEM AI Gateway, provider routing, Windows user settings, model default, credentials and product UI are unchanged.

## Exact scope and verification

- Base: fetched local main and origin/main at 57c6364c3a5e1b13d9633c1956b8b8a764dc65f4. Exact paths: local_ai_client.py and tests/test_local_ai_client_result_truth.py. The Luna candidate was replayed on an isolated clean main archive; Sol additionally rejected an explicit done=false response with partial text. Protected dirty working-tree versions were neither overwritten nor staged.
- The candidate's eight empty/reasoning-only baseline cases failed before the fix. Sol independently ran 42 selected local-client and neighboring Gateway tests on the final clean snapshot: exit 0, 42 passed, no background-thread leak. Compilation and the AI-native constitution gate passed. Tests used a blank disposable SQLite seed with both ZBC_DB_PATH and LUMENIS_TEST_SEED_DB pointed to it; cloud provider variables were removed in that test process.
- The protected data/monitor.db was not opened or migrated. Its SHA-256 remained A3EB3EF45EF877BBF93B303245248DA1160BBD561473A83AF71B2A326A4A0B45 before and after. No Windows user-level model routing or Codex configuration was edited.
- Ollama was installed and reported local models, but two separate synthetic Gateway probes returned incomplete model responses and honestly fell back to rules. Those probes do not prove live inference, a real user answer or product E2E. Hosted CI for the prior main commit had zero executed job steps; it is EXECUTION-LAYER UNVERIFIED, not a Product Gate PASS.

## REAL DELIVERY CARD / 真实用户工作闭环验收

REAL USER JOB: ask the local model for usable text in an existing AI-assisted workflow. ENTRY: existing local-AI compatibility API. REAL INPUT: synthetic prompt and deliberately controlled Ollama response shapes. END-TO-END PATH: response parse -> completion validation -> truthful result/error. USER-VISIBLE RESULT: an empty or unfinished result now returns an error rather than false success; no running product page was verified. FAILURE/RECOVERY: unavailable or incomplete model replies remain explicit errors, permitting a retry or the already-owned fallback. EVIDENCE: isolated 42-test exit and static gates above. ACCEPTANCE ASSERTION: only this preparatory compatibility Batch passes; the real user-work E2E for ROUND 07 has not passed, so ROUND 07 remains REWORK.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no collection or business coverage changed. Global Commercial Coverage=NO; Global Brand Coverage=NO; Guangzhou Taikoo Hui Reference Coverage=PARTIAL / NOT REVERIFIED; LUMENIS_INTERNAL_FULL_UNIVERSE_READY=NO. Random canonical entity sample count is zero for this local response-state Batch.

COMMERCIAL OVERLAY IMPACT: COMMERCIAL_READY=NO. The product still needs a real authorized input, model or honest fallback, persisted Evidence/decision where required, a user-visible result, and recovery demonstrated through its running workflow.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: Ollama's official Generate and Chat API documentation (accessed 2026-09-26; https://docs.ollama.com/api/generate and https://docs.ollama.com/api/chat) distinguishes final response/content from thinking and exposes a done flag. Decision ADAPT: apply that distinction to the existing compatibility client without adding a provider or dependency. Shadow/targeted regression is the 42-test run; rollback is a normal mainline revert. No model text becomes Evidence, Permission or Production Truth.

NEXT DEPENDENCY: prove a real local inference or honest fallback through the existing product API and user-facing task, with the protected identity and data boundaries intact. Keep the optional Jev typed-decision candidate separate from local Codex tooling and do not promote it on registration alone.
