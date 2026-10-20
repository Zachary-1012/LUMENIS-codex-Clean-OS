# Demo 25: command modal and route continuity

Date: 2026-10-17. Scope: independent interaction review copy only. Changes are limited to `src/command-study.mjs`, `tests/command-adapter.test.mjs`, and this evidence file. Product source, database, runtime, app integration and generated offline bundle are outside this adapter change. The parent owns app session injection and offline rebuild.

## Existing authorities consulted read-only

Existing source root: `recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main/`. This is the existing remote-main readback, not a newly fetched main claim.

- `AGENTS.md`: current existing-owner reuse, state recovery, protected Permission/evidence and actual acceptance boundaries. SHA-256 `f748d46d7a18c357d27576f44c345023601e452344f5da56f74106f52e850367`.
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`: Return context/selection/scroll at lines 813–820 and 1055; presentation state must not become Permission or business truth at line 992. SHA-256 `ccc2e93e52bafde51e2b41e1c61003d6f67d436e27b72a06f8193566c15830fc`.
- `00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md`: §18.1 keyboard access and command shortcuts, useful feedback without fabricated save; §18.2 F0 command panel and state retention. SHA-256 `8ab5a992502df46bf1c32cbffa3b167d8ee3bffa1a0f54edd76f024ea72bc954`.
- Existing review owners reused: `src/review-session.mjs` and its `canOpenDialog` guard; `src/command-palette.mjs` retains the unchanged local-only registry/search/choose functions.

## Corrected gap and behavior

Previously leaving demo 25 discarded the editor and local result. The actual adapter now accepts optional `session` and writes a version-1 snapshot to the existing `commands` slot on disposal. It keeps raw text, selection start/end/direction, editor scroll, body scroll, and the ID of an already-executed registered local result. Restoring that ID only displays its fixed local text; it does not execute a command.

Only matching version and string drafts are restored. Selection and scroll are sanitized; result IDs are whitelisted to own properties of the fixed local results map. Injected permission, open-modal or arbitrary result-text fields are not interpreted. Missing or throwing session storage does not prevent mount or cleanup. This is current-page memory, not durable/backend saving; refreshing or closing the review page loses it.

The panel never automatically reopens across routes. Search and panel focus ownership are transient. An existing settings dialog prevents both button and shortcut command opening; the same existing `canOpenDialog` guard prevents settings from opening over commands. A blocked shortcut is left unconsumed. Already-defaultPrevented shortcuts and query key events are respected.

Escape uses the native dialog cancel event, prevents its default, and closes through the same path as the explicit close button. That path returns focus to the original connected element, falling back to the current connected editor if the origin disappeared. No-results Enter performs no command. Arrow keys and Enter continue to use only the existing local action registry.

Disposal writes one snapshot, removes all adapter listeners, closes/removes the dialog and invalidates callbacks. Repeated disposal and captured stale result/open/keyboard callbacks cannot write results, overwrite the saved snapshot, reopen a modal or steal focus after return. No remote command or arbitrary execution path was added.

## Verification

- `node --test tests/command-adapter.test.mjs`: 6/6 passed.
- All tests except the parent-owned pending offline bundle test: 227/227 passed. Dated local observation; other workers may add coverage concurrently.

The six adapter tests mount the real `createCommands` implementation against a minimal DOM/event double and cover:

1. Raw draft, text selection/direction, both scroll positions and local result across route return; no restored open modal.
2. Settings/command modal ownership and existing-defaultPrevented shortcut behavior.
3. Native cancel event and explicit-close focus return, including disconnected-origin fallback.
4. Empty-result Enter, wrapped arrow selection, and prevented Enter.
5. Modal/listener cleanup and captured stale callback isolation across a new mount.
6. Absent/throwing session, malformed numeric state and rejected injected result/open/permission fields.

These are Node adapter contract tests. The settings side invokes the shared guard with an actual mounted command adapter and a minimal settings-dialog double; this is not full app/settings E2E. Native browser focus restoration, focus trapping/inert behavior, real Escape dispatch, rendering/scroll geometry, visual quality, keyboard/accessibility devices, screen readers and cross-browser behavior remain unverified. This work does not claim browser focus/visual or product acceptance.
