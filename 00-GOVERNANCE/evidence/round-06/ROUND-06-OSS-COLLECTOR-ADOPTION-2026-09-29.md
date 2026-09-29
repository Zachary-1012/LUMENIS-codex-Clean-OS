# ROUND 06 — OSS Collector/Importer Adoption Evidence

- Date: 2026-09-29
- Scope: supplied `LUMENIS_采集开源组件对比与商用接入评估_20260929.docx`
- Decision authority: current LUMENIS source owners and contracts; this evidence does not create a new round or owner.
- Current main at intake: `7d4245211f2e1e63e8d880801b006eddbeb3230a`

## Adoption decision

The report was compared with the current Collector, Browser, Scheduler, Evidence, Canonical and Importer owners. No third-party project is allowed to replace those owners or become Product Truth.

| Project | License observed | Decision | Bounded reason |
|---|---|---|---|
| firecrawl/firecrawl | AGPL-3.0 | DEFER | Service boundary and copyleft/commercial review are not justified for the current public-source path. |
| unclecode/crawl4ai | Apache-2.0 with attribution requirement | DEFER | Useful browser/markdown ideas, but existing Browser/Collector owners already own lifecycle and safety. |
| browser-use/browser-use | MIT | DEFER | Long-tail browser interaction remains behind the existing Browser Runtime and AI Gateway. |
| apify/crawlee | Apache-2.0 | DEFER | Queue/resource ideas do not authorize a second scheduler or task store. |
| scrapy/scrapy | BSD-3-Clause | DEFER | Static crawling overlaps the current public adapters; no measured gap requires adoption now. |
| microsoft/markitdown | MIT | ADOPT, bounded | Local HTML/PPTX conversion behind the existing Importer ParseResult contract. |
| D4Vinci/Scrapling | BSD-3-Clause | DEFER | Commercial/research wording and overlap require a later explicit review. |
| Genymobile/scrcpy | Apache-2.0 | REJECT for collection | Device mirroring/control is not a structured source adapter. |
| alirezamika/autoscraper | MIT | DEFER | Rule-prototyping is not a production Evidence path. |
| lwthiker/curl-impersonate | MIT | REJECT as default | TLS/HTTP impersonation cannot be the default acquisition path without a source-specific safety and authorization decision. |

Observed repository commits and license metadata were captured in the local research record; they are research inputs, not Production Truth.

## Implemented bounded change

1. `lumenis/importer/parser.py` routes `.html`, `.htm` and `.pptx` through lazy `MarkItDown` conversion. Inputs are required to be existing local files and are size bounded by the existing importer limit. Plugins are disabled. Parse metadata records format, parser, parser version, `network_mode=local_only`, source name and SHA-256 fingerprint. Missing dependency and empty output remain explicit errors.
2. `requirements.txt` declares the pinned `markitdown[pptx]==0.1.8` dependency; `THIRD-PARTY-COMPONENT-REGISTER.md` records the direct license and the importer-only boundary. Transitive notices remain subject to the existing dependency/license review.
3. `lumenis/system/collector/adapters/sitemap.py` no longer treats sitemap `<lastmod>` as publication time. It preserves the value as `raw.source_updated_at` and leaves `publish_datetime` unknown until a detail source provides it.
4. Existing public-source tests now assert the corrected time semantics. No second collector, scheduler, browser, Evidence or Canonical store was introduced.

## Verification

- MarkItDown was verified with an actual local HTML conversion and an isolated local PPTX conversion; no network input was passed to the converter.
- Targeted tests: `tests/test_public_source_adapters.py` and `tests/test_markitdown_importer.py`.
- Protected `data/monitor.db` was not opened or modified by the importer tests; any DB-dependent pytest invocation must use the disposable `LUMENIS_TEST_SEED_DB`.
- Live commercial authorization, social-platform cookies/sessions, hosted CI and real-user product E2E are not claimed by this batch.

## Official research sources

- https://github.com/microsoft/markitdown
- https://github.com/unclecode/crawl4ai
- https://github.com/firecrawl/firecrawl
- https://github.com/browser-use/browser-use
- https://github.com/apify/crawlee
- https://github.com/scrapy/scrapy
- https://github.com/D4Vinci/Scrapling
- https://github.com/Genymobile/scrcpy
- https://github.com/alirezamika/autoscraper
- https://github.com/lwthiker/curl-impersonate

Status: IMPLEMENTED → TESTED pending final batch gates; no Round or release status is promoted here.
