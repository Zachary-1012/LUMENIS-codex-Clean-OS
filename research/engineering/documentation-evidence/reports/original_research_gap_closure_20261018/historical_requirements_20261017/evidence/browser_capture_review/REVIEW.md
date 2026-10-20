# Browser capture independent read-only review

Frozen source: browser-addon-candidate. All six candidate SHA-256 values matched allowlist_manifest.json before review (source_hashes.json). No product edits, browser launches, dependency installation, external accounts, or Source imports. Fixtures and report are under /tmp/browser_capture_review only.

## Findings

1. High, unresolved security gap (also present in baseline): visible text `Authorization: Bearer opaqueSecret123` exports the full opaque secret. Candidate output is `Authorization=[REDACTED] opaqueSecret123`, including structure.blocks text; baseline outputs original full header. ai_browser_runtime.py:288-290 consumes only the authentication scheme, while older token regex expects a delimiter after Bearer. This is NOT a new regression; it is an unclosed requirement despite added authorization handling. Cover complete Bearer/Basic credential headers and quoted/multitoken signatures before generic token replacements. Do not promise arbitrary credential/prompt-injection removal through regex.

2. High for claimed authenticity, existing SavedWork boundary not new admission bypass: entirely invented browser_note URL, exact quote, offsets and browser_evidence_id=999999 are accepted and cold-reopened with no BrowserEvidence. Independent SQLite test passes. SavedWork's generic payload validation (saved_work.py:412-422,676+) does not authenticate browser_note; the new integration fixture assembles this marker on the client. The current NOT_VERIFIED/NOT_IMPORTED/NOT_ADMITTED flags honestly prevent an admission claim, but cannot support “saved reference cannot be forged.” A future owner-approved save binding must derive/validate session actor, capture, locator and content on server; a freely editable note remains user-authored. Do not infer a verified citation from this payload or its ID.

3. Medium, new wrapper timeout regression: ai_browser_runtime.py:1965-1966 invokes _run_on_browser_thread, whose future.result() at 1483 has no timeout, before extract constructs its deadline. A 100ms request queued behind a 400ms fixture operation returns success after 405ms. A stuck worker blocks preview/capabilities/select/discard indefinitely. Establish deadline before scheduling, bound queue wait and preserve the original unknown-commit/cancellation rules for running work.

4. Medium, new lease/replay usability mismatch: preview/select/discard always use agent control. Human lease correctly blocks concurrent agent use, but no user capture path accepts current human lease. Failed preview under human lease is inserted into the 16-record cache before _begin_control_action; broad exception handling records CAPTURE_UNAVAILABLE. After lease release, same request_id returns that generic terminal error instead of the original HUMAN_CONTROL_ACTIVE or a safe retry. All capture attempts during a human lease can exhaust a session without producing captures. Distinguish pre-execution control denial from uncertain execution and preserve a typed original error. A UI should explicitly require lease release unless a separate authorized human-read contract is designed; do not weaken mutual exclusion.

5. Medium, new terminal receipt replay limitation: valid(old) runs before replaying stored error (2003-2005). After an originally timed-out but committed operation, expiry/navigation/revocation may hide its operation_id/evidence_id/receipt_query behind a generic error. The test reproduces initial COMMITTED timeout receipt followed by CAPTURE_EXPIRED {} after expiry. No duplicate evidence is created; receipt endpoint remains independently queryable. Retain non-body operation receipt in an appropriately authorized terminal record independent of expiring page payload, or document this boundary precisely.

## Selection and security interpretation

Selection uses Python Unicode code-point offsets and escaped markdown; `selection.text` is plain untrusted text, never markdown input. With Chinese/emoji fixture selection matches server-held sanitized block, and client response mutation cannot mutate cached block. Offsets/prefix/suffix apply to sanitized, whitespace-normalized text, not original DOM/raw source. Redaction/injection filtering can change text length. Browser Evidence hash covers formats+structure, not the selected excerpt alone; storage of a short quote and parent Evidence ID cannot prove the cryptographic subset relation after the full capture disappears. No original-resource hash, rights, SourceUse admission or canonical claim is justified.

API before_request and owned-session check bind authenticated actor + account session + local principal; request actor/permission fields are rejected. Current valid() checks target, revision, current exact-equivalent URL and firewall. page_revision is an action counter, not a DOM MutationObserver: same-URL dynamic document changes are not detected by it. Snapshot semantics should remain explicit.

Resource metadata is observed only, not fetched. Query/fragment-bearing URLs remain null; host syntax checks do not prove public DNS reachability. Form/editable/input/password safeguards and untrusted flag are useful but not an exhaustive prompt-injection or secret filter. Resource visibility loop does not include text loop's visibility:collapse/contentVisibility:hidden checks; real-browser hidden-resource parity remains untested.

TTL access checks clear result when that entry is accessed, but no timer purges expired payload and close() does not explicitly clear _capture_previews. 16 records bounds memory; 300s should be described as access expiry, not guaranteed memory erasure. Restart cannot restore preview, as intended. Discard is local payload discard, not in-flight cancellation, source deletion or SavedWork deletion.

## Validation and limits

repro.py/repro.log: timeout queue, authorization text, lease failure/retry, expiry receipt masking. test_review.py/forged_note.log: isolated real SQLite forged browser_note acceptance, 1 pass. Source hashes match supplied six-file manifest. Targeted tests rerun separately; these fixtures are not actual Chromium or product UI/AI execution.

Supplied baseline and candidate regression logs show the same six existing failures, separately from findings above:
- tests/test_ai_browser_default_engine.py::test_start_uses_fresh_context_and_closes_only_its_pages
- tests/test_ai_browser_default_engine.py::test_playwright_calls_use_creation_thread_across_request_threads
- tests/test_ai_browser_default_engine.py::test_frame_capture_has_fresh_id_and_real_png_dimensions
- tests/test_ai_browser_default_engine.py::test_frame_api_returns_only_owned_uncached_image
- tests/test_browser_action_verification.py::TestActionVerificationWithRuntime::test_action_with_passing_verification
- tests/browser_runtime/test_browser_frame_stream.py::test_no_screencast_stream_module_outside_owner

Their recorded categories are two missing Playwright dependencies, two frame fixtures, one action-verification fixture, one missing .git inventory. I read both logs; did not launch Browser to rerun them. Formal Source/AI registration, actual user UI flow, actual browser source-return, 15-family collection completeness and end-to-end model execution remain OPEN.

Independent targeted rerun: all 61 selected tests passed (61 dots, 100%, exit 0), from candidate cwd with PYTHONDONTWRITEBYTECODE=1 and pytest cache disabled, excluding real_chromium. The initial run from parent cwd had one fixture setup error locating app.py; correct-cwd rerun resolved it. Logs retained transparently. All six source hashes rechecked unchanged after tests.
