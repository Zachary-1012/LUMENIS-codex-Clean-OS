# Manuscript structure: bounded first implementation contract

Current product authority read: FULL-PRODUCT-SKETCH.md line164 (editable proposal structures, no mandatory template, preserve chapters and drafts), line494 (narrative outline), line836 and §5 line1403 (versioned save/reopen and conflict). The existing SH-04 full-field Markdown revision contract remains the only planned write path; a local structural proposal must become a normal user draft and then a separately saved revision. Local SHA/offsets do not become authoritative Owner metadata.

Research, 2026-10-17:
- [CommonMark 0.31.2](https://spec.commonmark.org/0.31.2/#atx-headings) distinguishes ATX, setext, code, HTML and container blocks. Heading-like text is not universally a heading; a regex over all Markdown is unsafe. This first dependency-free implementation accepts a deliberately restricted ATX/plain-paragraph document and refuses code/container/HTML/setext ambiguity. It is not a CommonMark renderer or full parser. Normal editing remains available for unsupported documents; future full-parser integration must retain exact source ranges.
- [WAI APG treeview](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/) describes a composite widget with its own focus/selection model. Initial outline controls will use native select and explicit previous/next sibling actions, avoiding an unimplemented treeview role. Native keyboard/touch/reader validation remains required.

Chosen contract: whole-document exact input binding, stable source offsets for one preview, same-parent sibling moves with descendants, no implicit promote/demote/rewrite/translate, preview before adoption, permission and stale-draft fences, exact-output-bound undo. Preserve every original code unit and line ending by permutation; refuse moves that would join an unterminated final section to another heading. No runtime AI. Interface schemas must distinguish UTF-16 local offsets from Owner whole-field replacement.

Implemented after this research: pure range/permutation contract and the native-select preview/adopt/cancel/undo view inside existing study73. Adoption edits its current draft; the unchanged versioned save/readback flow persists a separate local revision. Twelve pure and six mounted adapter tests exercise this path. Bounds: 262144 UTF-8 bytes, 256 headings; these are demo safety limits, not product capability limits. The outline is read on demand, not reparsed on every keystroke.

Still missing: full Markdown parsing, native drag, cross-platform acceptance, proposal Evaluation and backend structural edit API. The first supported subset is deliberately narrower than eventual full-product requirements. This is an existing-planning capability extension, not an extra product Owner or extra page.

Additional existing-study repair: discard, historical adoption and journal replacement confirmations now bind exact visible draft, current head, selected version, workspace and permissions. Later edits cancel pending intent without moving focus away from the editor; silent input changes are rechecked at confirmation. Three mounted tests cover it.

## Reusable interface and host responsibilities

`src/manuscript-structure.mjs` has no DOM, storage, network or clock dependency.

- `inspectManuscript(markdown) -> {format:'restricted-atx-v1', offsetUnit:'utf16', headings:[{index,start,end,level,label,parent}]}`. Ranges are half-open source ranges, descendants included in `end`. The index is valid only for that exact original document.
- `previewManuscriptMove(markdown,index,'up'|'down') -> {schema:'manuscript-move-v1',before,after,index,direction,selectedStart,offsetUnit}`. No mutation or saving occurs. Only adjacent same-level siblings are permuted. The output contains every original code unit exactly once in its moved section; no added newline, translation, normalization, template or generated prose.
- `applyManuscriptMove(current,proposal,{allowed}) -> {markdown,selectionStart,undo:{before,after}}`. The host passes current permission. Exact original text and recomputed proposal must match; changed input/tampered output is rejected.
- `undoManuscriptMove(current,undo,{allowed}) -> originalMarkdown`. Undo requires the exact post-move body, so it cannot erase later typing. Host retains the token in trusted local state, bound to the same scope; it is not an external authorization token.

All operations are synchronous and bounded. Cancellation discards a preview, with no write to undo. A confirmed draft edit still needs normal Owner save/revision and actual readback; cancel during a separate asynchronous save cannot claim reversal of that write. No server receipt, artifact SHA or draft digest is fabricated here.

Error codes include DOCUMENT_INVALID, STRUCTURE_UNSUPPORTED, OUTLINE_LIMIT, MOVE_INVALID, SECTION_NOT_FOUND, NO_SIBLING, HIERARCHY_CHANGE_REFUSED, NON_ADJACENT_SECTIONS, SECTION_SEPARATOR_REQUIRED, PERMISSION_DENIED, STALE_MANUSCRIPT, PROPOSAL_CHANGED and STALE_UNDO. View retains manual editing and reports the specific reason. The 256-heading cap avoids unbounded range work; unsupported/over-limit content stays editable through the ordinary text path.

`src/manuscript-outline-study.mjs` supplies an optional DOM adapter with `getSnapshot`, `applyDraft`, `sync` and `dispose`. A different frontend can discard this view and reuse the pure contract. Flutter/Dart port/compilation and native text-selection behavior have not been implemented or verified. Do not copy UTF-16 ranges into Python citation offsets; normal report revision uses whole-field `expected`/`value` with the real Owner's exact base.

For reproducible synthetic logic timing, run `node tools/benchmark_manuscript.mjs`; its JSON output explicitly excludes browser layout, input latency, phone performance and end-to-end product acceptance.
