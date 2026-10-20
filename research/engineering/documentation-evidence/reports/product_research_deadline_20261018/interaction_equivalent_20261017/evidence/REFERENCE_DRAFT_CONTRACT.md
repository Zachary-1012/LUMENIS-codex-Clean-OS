# Stage A: local reference notebook inside existing study73

This is new independent code, not restored missing40–68 code, and not a product Owner. Source/API boundary findings are in NEXT_PLANNED_WORKFLOW_AUDIT.md. The original report journal schema and Artifact hash inputs remain unchanged.

## Implemented behavior

Actual local text -> SHA-256 of UTF-8 bytes -> monotonically versioned local source -> grapheme-safe selection -> exact Unicode-codepoint quote -> human support/counter/context note -> reversible exclusion/source-withdrawal status -> explicit journal save/readback/reopen. Older source versions and quote bytes remain available after a new source version. All source rights remain UNKNOWN. The UI labels these local drafts and has no report insertion, production citation or reference export action.

`reference-draft.mjs` owns a DOM-free bounded state machine. Permission is supplied by the host and defaults closed. Source hashing and restore recheck generation, exact revision and permission. Quote creation binds the current source version/hash; loading verifies every source byte hash, exact quote range, grapheme boundary, scope and exact schema. Production Evidence/SourceUse fields are rejected. The explicit `ownerCitation`, `insertIntoReport` and `exportReferences` methods fail closed.

`reference-draft-study.mjs` is the optional DOM adapter. It lives in the report's reversible source details, while the report body and report versions remain untouched. Artificial sample/withdrawal controls are in unified settings. Original source selection/scroll and unsaved notes survive route return through an in-memory scope-bound session snapshot, without pretending to save. Read revocation clears presentation and session recovery; regrant requires an explicit journal reopen. New text input cancels pending source/restore work. Previewed reopen checks local revision, pending input and the stored bytes again before replacing the notebook.

## Persistence and concurrency

Separate key: `review-reference-draft:v1:<scope>`. The saved report's v1 journal is not migrated, augmented or silently rewritten. Save checks the expected last-read raw journal, writes a bounded snapshot and requires exact readback. Existing unknown storage requires reopen before overwrite. Native host storage uses the existing explicit lock adapter; injected test storage without a lock has only same-view/CAS simulation semantics, not cross-tab atomicity. Scope change before an awaited write baseline completes aborts that old-scope write. A write already completed cannot be undone by cancellation or route leave; uncertain writes require explicit reopen.

Limits: 64KiB UTF-8 per source,16 local source versions,128 quote drafts,2000 UTF-16 units for notes,2MiB journal. These are independent demo safety bounds, not product capability limits. Reusable `createContentSelectionIndex` computes source grapheme/codepoint boundaries once per validation pass; it avoids rescanning the same source for every quote. All12 content-language labels are accepted without automatic translation. Full zh/en/ko UI, font coverage and language understanding are not demonstrated by that preservation test.

## Explicit gaps / next stage

This completes only the local reference-workdraft cycle. It does not complete real source acquisition, authenticated Evidence/SourceUse, approved quotation-to-report adoption, actual source revocation, report provenance or export rights. The report export remains a source-free authoring path; this notebook never copies its quote into it. User manual typing is not presented as a verified citation.

Stage B must bind actual Owner receipts and persist a report-version reference ledger atomically, including missing/corrupt ledger behavior and historical export restrictions. Merely hiding or deleting a visible notebook row cannot be used as that future export gate. The proposed single-envelope compatibility design is still research/implementation work, not shipped product functionality.

Node and minimal-DOM tests verify these state contracts. Native browser text selection, focus, touch, reader, layout, locks and real end-to-end platform behavior remain pending.
