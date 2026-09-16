# LUMENIS / Codex Zero-Auth Capability Acceptance V1

> Status: CANONICAL ACCEPTANCE MATRIX  
> Date: 2026-09-16  
> Scope: Codex local development tooling, LUMENIS zero-auth integration foundations, future integration candidates.

## 1. Truth boundary

Remote source-audit baseline before this documentation update:

```text
repo   = Zachary-1012/LUMENIS-codex-Clean-OS
branch = main
sha    = 147e3bd331b22236930ae29112a67c613a148f67
```

The current acceptance session also produced local workstation evidence that `aiohttp 3.14.3` and `feedparser 6.0.14` imported successfully and that `pip check` returned no broken requirements. That local evidence must not be confused with remote repository implementation.

At the audited remote baseline:

```text
aiohttp     = PRESENT in requirements.txt
feedparser  = NOT PRESENT in requirements.txt
```

Therefore `feedparser` is classified as `LOCAL_VERIFIED / REMOTE_NOT_YET_IMPLEMENTED` until its manifest change is actually committed and pushed.

## 2. Category legend

GitHub Markdown does not support reliable row background colors across renderers, so the Excel color classes are represented semantically:

- 🟦 **CODEX DEV** — Codex / local engineering tooling
- 🟩 **LUMENIS NOW** — current LUMENIS foundation or approved immediate zero-auth integration
- 🟨 **FUTURE** — future optional/cloud/commercial integration, not part of current zero-auth release path

## 3. Final acceptance matrix

| Category | Tool / Capability | Remote status | Cost | Key / OAuth | Codex | LUMENIS integration | Purpose | Closed-loop position | Acceptance criterion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 🟦 CODEX DEV | Git CLI | external workstation tool | Free | None | Yes | indirect | status/diff/log/commit/compare | Develop → Release | repository identity/status/log operations work |
| 🟦 CODEX DEV | Playwright MCP | workstation install, not repo runtime | Free | None | Yes | No, not a production dependency | browser/UI/E2E/live acceptance | Test → Live Verify | Codex can open 8201 and execute critical UI path |
| 🟦 CODEX DEV | Filesystem MCP | workstation install, not repo runtime | Free | None | Yes | No, not a production dependency | scoped file read/write/search | Develop | access limited to active workspace/repository |
| 🟦 CODEX DEV | ripgrep / rg | workstation tool | Free | None | Yes | No | fast source search | Discover → Develop | `rg --version`; source search works |
| 🟦 CODEX DEV | fd | workstation tool | Free | None | Yes | No | file discovery | Discover | `fd --version`; repository discovery works |
| 🟦 CODEX DEV | jq | workstation tool | Free | None | Yes | scripting only | JSON/API/test output | API → Verify | `jq --version`; API JSON can be parsed |
| 🟦 CODEX DEV | sqlite3 CLI | workstation tool | Free | None | Yes | direct read-only inspection | DB/Evidence/Canonical/Truth inspection | Data → Verify | CLI opens intended DB and performs scoped read-only checks |
| 🟦 CODEX DEV | curl | Windows/platform tool | Free | None | Yes | operations/verification | HTTP/API/health | Runtime → Verify | `curl` can verify `/healthz` and scoped APIs |
| 🟩 LUMENIS NOW | requests | present in remote requirements | Free | None | Yes | Yes | synchronous public HTTP | External → Evidence | import + adapter test PASS |
| 🟩 LUMENIS NOW | httpx | present in remote requirements | Free | None | Yes | Yes | HTTP client | External → Evidence | import + adapter test PASS |
| 🟩 LUMENIS NOW | aiohttp | present in remote requirements; local runtime verified | Free | None | Yes | Yes | async collector HTTP | Collector → Evidence | import + async acquisition test PASS |
| 🟩 LUMENIS NOW | BeautifulSoup4 | present in remote requirements | Free | None | Yes | Yes | HTML parser | Raw → Canonical | HTML fixture parser PASS |
| 🟩 LUMENIS NOW | lxml | present in remote requirements | Free | None | Yes | Yes | HTML/XML/Sitemap parser | Raw/XML → Canonical | XML/Sitemap fixture PASS |
| 🟩 LUMENIS NOW | Playwright | present in remote requirements | Free | None | Yes | Yes | existing browser runtime / browser adapter | Source → Evidence | existing browser chain remains regression-green |
| 🟩 LUMENIS NOW | SQLite | Python stdlib / current persistence | Free | None | Yes | Yes | Production Truth persistence | Evidence → Canonical → Metric | intended DB identity verified; no protected DB leakage |
| 🟩 LUMENIS NOW | APScheduler | present in remote requirements | Free | None | Yes | Yes | scheduled Collector/runtime tasks | Scheduler → Collector | scheduler behavior test PASS |
| 🟩 LUMENIS NOW | tenacity | present in remote requirements | Free | None | Yes | Yes | retry/backoff | Reliability | retry semantics tested |
| 🟩 LUMENIS NOW | feedparser | **local verified; remote manifest pending** | Free | None | Yes | Approved | RSS/Atom parser | External → Evidence | add to manifest → install/import → RSS/Atom fixtures PASS |
| 🟩 LUMENIS NOW | PublicHttpAdapter | foundation exists; adapter closure not yet proven | Free | None | Codex develops | Approved | unified public-page acquisition | External → Evidence | public HTML → Evidence → Canonical; failure isolation PASS |
| 🟩 LUMENIS NOW | RSSAdapter | not yet remote-verified as closed loop | Free | None | Codex develops | Approved | RSS monitoring | RSS → Evidence | fixture/real public RSS → Evidence → Canonical PASS |
| 🟩 LUMENIS NOW | AtomAdapter | not yet remote-verified as closed loop | Free | None | Codex develops | Approved | Atom monitoring | Atom → Evidence | fixture/real public Atom → Evidence → Canonical PASS |
| 🟩 LUMENIS NOW | SitemapAdapter | not yet remote-verified; no new parser needed | Free | None | Codex develops | Approved | public URL discovery | Sitemap → Fetch → Evidence | XML parse + URL discovery + Evidence PASS |
| 🟩 LUMENIS NOW | BrowserAdapter | existing browser capabilities; unified adapter semantics still require acceptance | Free | None | Codex converges | Yes | browser-based acquisition | Browser → Evidence | no bypass of Evidence/Canonical; XHS/browser regression PASS |
| 🟨 FUTURE | Firecrawl Cloud | not integrated | quota/cloud | Key | possible | Not current | web research provider | Future Research Provider | separate API/commercial/privacy review |
| 🟨 FUTURE | Exa | not integrated | quota/cloud | Key | possible | Not current | search/research provider | Future Research Provider | separate API/commercial/privacy review |
| 🟨 FUTURE | PostHog Cloud | not integrated | free tier/cloud | account/config | possible | Future | product analytics/observability | Observability | privacy/data-boundary review after launch |
| 🟨 FUTURE | Mixpanel | not integrated | free tier/cloud | account/config | possible | Future | product analytics | Observability | choose against PostHog; do not duplicate by default |
| 🟨 FUTURE | Supabase | not integrated | free tier/cloud | account/auth | possible | Not now | Postgres/Auth/Storage | Future SaaS | explicit DB/SaaS migration decision only |
| 🟨 FUTURE | Railway | not integrated | not fully free | account | possible | Not now | cloud Flask/API/worker runtime | Future Deploy | resolve Windows/CDP/Resident Browser dependencies first |
| 🟨 FUTURE | Vercel | not integrated | free tier | account | possible | Not now | separated frontend deployment | Future Frontend | only after actual frontend/runtime split |
| 🟨 FUTURE | Figma | external design tool | free tier | authorization | useful | not core runtime | UI/UX/design-to-code | Design → Develop | external design workflow only |
| 🟨 FUTURE | Runway / Higgsfield / OpenArt | not integrated | quota/cloud | authorization/API | possible | Future | media provider | Content → Artifact | commercial/API/license review before adoption |

## 4. LUMENIS zero-auth closed-loop target

```text
External Source
        ↓
Acquisition Adapter
├── Public HTTP
├── RSS
├── Atom
├── Sitemap
└── Browser
        ↓
Evidence
        ↓
Canonical Data / Canonical Content
        ↓
Function / Research
        ↓
Metric / Truth Table
        ↓
View Model
        ↓
CTH / BMP / Shared Capability
        ↓
UI / Report / Export
```

Forbidden shortcuts:

```text
RSS → AI directly
Web page → UI directly
Browser result → parallel DB truth
Third party → canonical truth owner
```

## 5. Launch Gate

| Gate | Name | Acceptance condition | Current classification |
| --- | --- | --- | --- |
| G01 | DEPENDENCY_READY | required runtime deps import; local zero-auth install verified; manifest truth matches target candidate | **LOCAL PASS / remote feedparser pending** |
| G02 | ADAPTER_IMPLEMENTED | Public HTTP / RSS / Atom / Sitemap / Browser adapter contracts implemented | NOT YET VERIFIED |
| G03 | EVIDENCE_TESTED | every adapter emits provenance-bearing Evidence; idempotence/source semantics correct | NOT YET VERIFIED |
| G04 | CANONICAL_TESTED | Evidence → Canonical works; missing is never fabricated as zero | NOT YET VERIFIED |
| G05 | SIDEWRITE_ISOLATED | non-critical side-write failure does not corrupt/break primary ingestion where contract requires isolation | NOT YET VERIFIED for new adapters |
| G06 | API_VERIFIED | related API status/data/error semantics verified | NOT YET VERIFIED |
| G07 | UI_VERIFIED | Experience V2 renders real data honestly; no dead/fixture-only production claim | NOT YET VERIFIED |
| G08 | TARGETED_TESTS_PASS | new/affected tests pass | NOT YET VERIFIED |
| G09 | 8201_HEALTHY | production candidate starts and `/healthz` is healthy | NOT VERIFIED by this document update |
| G10 | PLAYWRIGHT_LIVE_PASS | critical Experience path passes live browser acceptance | NOT VERIFIED |
| G11 | WORKTREE_CLEAN | candidate contains only intended files | requires local candidate check |
| G12 | P0_P1_ZERO | no unresolved P0/P1 release blockers | NOT VERIFIED |
| G13 | SAFE_TO_COMMIT | scope/tests/rollback point known | candidate-specific |
| G14 | SAFE_TO_PUSH | local/remote relation reconciled; candidate SHA explicit | candidate-specific |
| G15 | LIVE_VERIFIED | post-start/deploy live runtime acceptance passes | NO |

## 6. Status semantics

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E evidence proves behavior
RELEASED    = release/security/recovery/rollback gates pass
OPERATING   = real operation produces required live/time evidence
```

Never convert dependency installation, documentation, CI green, an HTTP 200, or a prototype page into `LIVE_VERIFIED`.
