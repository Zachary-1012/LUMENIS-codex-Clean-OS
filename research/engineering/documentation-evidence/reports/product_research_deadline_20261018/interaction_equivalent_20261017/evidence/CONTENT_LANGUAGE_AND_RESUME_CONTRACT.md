# New language dependency and recovered file-resume integration

## Authority and current source
- Current read-only main: `4dab98ed6357133da9307de846180ed4f7bba5f5`.
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §5, lines168–173: exact user-authored Unicode return, representative sequence checks, no universal font/native coverage claim.
- `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md` line610: browser file/upload and draft progress separately; refresh recovery; no false available-material status; chunk resume for large files.
- `contracts/experience/screen-specifications/BMP-06.md` line110 confirms that Web requirement.
- User-added scope: UI zh/en/ko; content zh/en/ko/ja/fr/de/es/pt/ru/ar/hi/id. Content language is a declared tag, not inferred understanding.

## Exact recovered dependency surface
`resumable-file.mjs` calls `CONTENT_LANGUAGES.includes(tag)` and `contentDiagnostics(file.name)`; the latter result was ignored by the recovered core. The view consumes the language catalogue. Historical tests additionally import `UI_LANGUAGES`.

The recovered file core and view and 35-test file were first copied byte-for-byte from the saved candidate, hashes recorded in RESUMABLE_IMPORT_PROVENANCE.json. The dependency `content-language.mjs` is a NEW implementation with explicit semantics, not a recovered old file and not a stub. After the initial exact-import 35/35 pass, the view was deliberately revised to expose bidi-control diagnostics; that view is no longer byte-identical to its recovered input. The historical candidate and original 35-test file remain unchanged.

## Language module v1
- Frozen 3-UI/12-content tag catalogues. No automatic translation, normalization or spelling replacement.
- Validates string type, a bounded 1,000,000 UTF-16-unit budget and well-formed surrogate pairs. Invalid input throws stable error identifiers rather than silently inserting replacement characters.
- `contentDiagnostics(text)` returns exact original, UTF-16 units, code points, grapheme count with `Intl.Segmenter`, bidi-control code points and original offsets, and a separate control-visible inspection string.
- Segmenter unavailable is explicit: grapheme count null, segmentation UNAVAILABLE. Display excerpt falls back to the entire original rather than slicing through a combining/emoji sequence. This is conservative fidelity, not complete rendering support.
- `contentExcerpt` is display-only and returns original alongside excerpt. It must never replace stored source or filename.
- RTL script presence is a hint only. It is not a detected language or proof of directionality correctness. View uses dir=auto and CSS bidi isolation, displays a control-visible filename copy when needed, and preserves the original name and fingerprint.
- Font coverage UNKNOWN; language understanding NOT_TESTED. No font download, external model or native device test occurred.

## Actual file behavior and boundaries
Demo original number69 is now the 40th restored/current entry, after01–39; missing40–68 are not implied restored. Counter separates current ordinal from original number.

The workbench reads selected actual bytes, computes full/chunk SHA-256, accepts chunks into a local memory sink, and compares exact byte readback. Pause/cancel/new scope/permission/reopen fence old callbacks. Metadata save requires exact readback; reopen does not claim bytes or file permission survive. Re-selection must match the bytes, even if renamed. Preparation, verified-local bytes, server receipt and product material remain separate states.

Limits remain 16MiB per file and up to256 chunks, with configurable next-file chunk size in unified Settings. This is bounded mechanism validation, not arbitrary-large-file performance acceptance. All real backend adapter methods remain uninvoked and UNBOUND. Receipt shape checking is not authentication, durability or product availability.

## New evidence
- 18 direct language/fidelity/diagnostic regressions, including12 language samples, combining marks, complex emoji, bidi controls, missing Segmenter and malformed inputs.
- 35 recovered file-workbench tests actually rerun after dependency implementation, not inherited historical pass counts.
- An additional mounted-adapter check verifies the bidi warning/control-visible copy without changing stored filename or bytes.
- Existing39 regression compatibility and offline export graph are rerun after integration. Browser, touch, native fonts and real backend remain unverified.

## Primary research references (read 2026-10-17)
- [ECMA-402 Segmenter objects](https://tc39.es/ecma402/#segmenter-objects): the API supports grapheme/word/sentence segmentation. The current online document is a living specification; this work does not claim its entire current revision is implemented by the test runtime.
- [Unicode UAX29, Text Segmentation](https://www.unicode.org/reports/tr29/): grapheme boundaries are a better unit than individual code points for user-facing character segmentation, but do not establish actual glyph rendering or every language-specific editing expectation. Hence separate font/native acceptance and a conservative no-segmentation fallback.
- [Unicode UAX9, Bidirectional Algorithm](https://www.unicode.org/reports/tr9/): directional controls and isolates have explicit structural behavior. This review surfaces controls for inspection and delegates display layout to the platform; it does not reimplement or claim full bidi conformance.

No text was copied or normalized from these documents into user source. The 12-language samples are fidelity fixtures, not semantic model evaluation. Runtime Unicode/ICU version is recorded separately from the newest published specification.
