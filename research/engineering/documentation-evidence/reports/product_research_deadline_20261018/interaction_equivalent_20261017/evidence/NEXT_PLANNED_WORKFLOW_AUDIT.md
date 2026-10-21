# Next planned workflow: exact local quotation review and later report adoption

Status: source audit and bounded implementation plan, not product runtime acceptance. The read-only research worker was stopped to release a slot for the urgent full-product V2 ledger. Its route finding was then independently re-read below; no product file was changed. The full worker draft was not saved, so this is a newly consolidated report, not a verbatim recovered artifact.

## Confirmed current Owner entrance gap

Read 2026-10-17 14:44 UTC:
`lumenis_working_20261017/source/experience_runtime.py`
SHA256 `0ef5a2877e94b9df0f15fe648d2a1fbb39e3187ccaa2bb9ec0d6d68ea852a830`.

- `_shared_saved_work_route_allowed`, lines2312–2340: exact endpoint/path/method allowlist contains document import POST, SavedWork create/revise/search/read/export/attachment and work-dependency workflow. It does not contain material document read/file/quote.
- `_shared_work_actor_scope`, lines2433–2436: a request carrying the Shared workspace header fails with `SHARED_WORKSPACE_SCOPE_NOT_SUPPORTED` when that allowlist does not match.
- `quote_shared_document`, lines2728–2741: GET `/api/experience/materials/documents/<int:evidence_id>/quote`, exact single `start` and `end` ASCII decimal arguments; it calls `_shared_work_actor_scope('read')` before `lumenis.importer.documents.locate_quote`.
- `_artifact_experiment_route_matches`, lines5215–5218: the extra route exception is specifically `/api/experience/reports/artifact-experiments`, not a general document quotation grant.

Therefore, for the Shared-header path in this static source, the quote route reaches a rejecting scope check before its quote locator. This is a static contract finding, not a live HTTP or permission test. The product Owner must repair/test the correct entrance, rather than the demo bypassing scope or inventing an Evidence ID.

## Product and existing-demo relationship

Current FULL-PRODUCT-SKETCH.md line164 requires ordinary document reading, exact quotations, manual comparison, no-AI work and editable authored results with SourceUse checked for actual external-fact use. SH-04 and its current SavedWork Owner remain the report write authority. Existing73 preserves its v1 local version/hash/save/export contract; it does not carry real source citations. Existing71/72 fixture context does not constitute a real Evidence/SourceUse handoff.

The audit worker additionally reported that ordinary Shared private import produces a research work with `citations=[]` and `source_material` rights `UNKNOWN`/private custody-and-analysis rather than quote-ready Evidence. That detail was retained from its message but is not independently rechecked in this consolidated file; verify the current importer owner before relying on it for a product change.

## Stage A: local reference draft, no report insertion

Implement a separate local-only reference notebook: actual user-pasted/self-authored fixture text → original UTF-8 digest/local version → grapheme-safe exact selection → Unicode-codepoint quotation draft → manual support/counter/context note → reversible exclusion/source-withdrawal marker → explicit local save/readback/reopen.

Reuse `contentSelectionRange`; it converts native UTF-16 selection to Unicode codepoints without silently expanding split graphemes. No normalization/translation. Fields must be explicitly local and reject production `evidence_id`/SourceUse/approval fields. Source rights remain UNKNOWN; no API submission, report-body insertion or reference export is supplied at this stage. Its own journal is not the SavedWork v1 report journal. This supports source review but does not complete citation-to-report delivery.

Acceptance: exact selected text/digest/version, multilingual/bidi/grapheme bounds; changed source or stale local revision rejection; late hashing/cancel/revocation fences; old references preserved/marked when source changes or is withdrawn; corrupt/wrong-scope readback refusal; no hidden product wire fields; no insertion/export method can turn local notes into approved citations. Actual browser selection and real SourceUse remain unverified.

## Stage B: source-backed body adoption and export guard

Before inserting unknown-rights quotes into exportable body, a separate-view check or two independent storage keys is insufficient. A missing/corrupt reference sidecar must not be interpreted as proof of a source-free report.

Candidate design to investigate/test: one local reference-workspace envelope contains the unchanged v1 report journal bytes plus an append-only reference ledger, behind an injected storage adapter. A single write/readback under the same lock boundary avoids a two-key journal/ledger crash window. Every selected historical version's export checks its ledger plus current source status. Removing a visible row never erases an earlier version restriction; an explicit exact-text removal/re-anchor creates a new revision, while old restricted versions stay restricted.

This recommendation is not implemented or accepted as the production schema. It must prove original v1 artifact hashes unchanged, existing lock/cancel/readback semantics, migration/no-silent-fallback, source revocation propagation, body edits and unknown text ranges, downgrade/reopen behavior, permission recheck and crash recovery. True Evidence/SourceUse submission requires the original Owner and real receipts, not local SHA values or draft IDs.
