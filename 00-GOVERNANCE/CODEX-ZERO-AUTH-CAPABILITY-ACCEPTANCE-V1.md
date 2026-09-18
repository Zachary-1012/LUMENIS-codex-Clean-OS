# LUMENIS / Codex Zero-Auth Capability Acceptance V1

> Status: CANONICAL ACCEPTANCE MATRIX  
> Updated: 2026-09-16  
> Scope: Codex engineering tooling, LUMENIS zero-auth integration foundations, CI/release gates, future integration candidates.

## 1. Truth boundary

Current remote status used for this correction:

```text
repo        = Zachary-1012/LUMENIS-codex-Clean-OS
branch      = main
pre-update  = e50e07701399b1d46b794dd1802dca93defae9d8
CI workflow = Verify LUMENIS #148
CI result   = completed / failure
```

Local workstation evidence remains separate from remote repository truth.

Local evidence already produced in the current acceptance session:

```text
aiohttp 3.14.3     import PASS
feedparser 6.0.14  import PASS
pip check           No broken requirements found
RSS fixture         PASS
Atom library        AVAILABLE
Atom function test  NOT RUN
```

Remote manifest truth at the pre-update SHA:

```text
aiohttp>=3.9.0  = PRESENT in requirements.txt
feedparser       = NOT PRESENT in requirements.txt
```

Therefore:

```text
aiohttp    = dependency-level PASS only; async adapter behavior still requires functional tests
feedparser = local/library-level partial PASS; remote manifest convergence still pending
Atom       = library capability available; functional acceptance NOT RUN
```

Do not upgrade any of the above to adapter, runtime, live or release success without matching evidence.

## 2. Category legend

GitHub Markdown does not reliably preserve Excel row fills, so the Excel classes are represented semantically:

- 🟦 **CODEX DEV** — Codex / engineering tooling
- 🟩 **LUMENIS NOW** — current LUMENIS foundation or approved immediate zero-auth integration
- 🟨 **FUTURE** — future optional/cloud/commercial integration, outside the current zero-auth release path

## 3. Codex engineering tooling

| Category | Tool / Capability | Current status | Cost | Auth | LUMENIS runtime | Purpose | Acceptance state |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 🟦 CODEX DEV | Git CLI | already used | Free | None | indirect only | status/diff/log/commit/compare | AVAILABLE |
| 🟦 CODEX DEV | GitHub Plugin | installed and actually used in this session | Free | GitHub connector/OAuth | No | repository audit, file update, CI/commit inspection | PLUGIN-LEVEL PASS |
| 🟦 CODEX DEV | OpenAI Developers | installed | Free / API usage separate | plugin connection | No | OpenAI API / Agents / SDK development reference | INSTALLED / FUNCTIONAL SMOKE PENDING |
| 🟦 CODEX DEV | Figma | installed and connected | free tier available | OAuth | No | UI/UX, Design System, design-to-code | CONNECTION PASS / TASK SMOKE PENDING |
| 🟦 CODEX DEV | Context7 | installed and connected | provider policy applies | plugin connection | No | current library/API docs and examples | CONNECTION PASS / TASK SMOKE PENDING |
| 🟦 CODEX DEV | Codex Security | installed | plugin capability | plugin connection | No | security scan / analysis / investigation | INSTALLED / FUNCTIONAL SMOKE PENDING |
| 🟦 CODEX DEV | Playwright MCP | user-confirmed installed | Free | local MCP | No | browser/UI/E2E/live acceptance | INSTALLED / 8201 LIVE SMOKE PENDING |
| 🟦 CODEX DEV | Filesystem MCP | optional; not required by current repository work | Free | local | No | outside-workspace file operations only if a real gap exists | OPTIONAL / NOT VERIFIED |
| 🟦 CODEX DEV | ripgrep / rg | local tool | Free | None | No | fast source search | LOCAL CHECK PENDING |
| 🟦 CODEX DEV | fd | local tool | Free | None | No | file discovery | LOCAL CHECK PENDING |
| 🟦 CODEX DEV | jq | local tool | Free | None | script-only | JSON/API verification | LOCAL CHECK PENDING |
| 🟦 CODEX DEV | sqlite3 CLI | optional; Python sqlite3 already available | Free | None | read-only inspection preferred | DB/Evidence/Canonical inspection | CLI CHECK PENDING |
| 🟦 CODEX DEV | curl | usually present on Windows | Free | None | operations/verification only | health/API verification | LOCAL CHECK PENDING |

Installed/connected does not equal functionally verified. Codex must run one real smoke test per relevant tool after quota recovery.

## 4. LUMENIS current zero-auth foundation

| Category | Tool / Capability | Remote / local truth | Purpose | Closed-loop position | Acceptance criterion | Current state |
| --- | --- | --- | --- | --- | --- | --- |
| 🟩 LUMENIS NOW | requests | remote manifest present | sync Public HTTP | External → Evidence | import + public HTTP adapter test | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | httpx | remote manifest present | HTTP client | External → Evidence | import + request/error behavior test | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | aiohttp | remote manifest present; local 3.14.3 import PASS | async collector HTTP | Collector → Evidence | import/version + `pip check` PASS at dependency gate; adapter behavior tested separately | DEPENDENCY-LEVEL PASS |
| 🟩 LUMENIS NOW | BeautifulSoup4 | remote manifest present | HTML parse | Raw HTML → Canonical | fixture parse PASS | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | lxml | remote manifest present | HTML/XML/Sitemap parse | Raw/XML → Canonical | XML/Sitemap fixture PASS | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | Playwright | remote manifest present | browser runtime / future unified BrowserAdapter | Source → Evidence | browser chain regression + adapter semantics | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | SQLite | Python stdlib/current persistence | Production Truth persistence | Evidence → Canonical → Metric | intended DB identity; no protected-data leakage | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | APScheduler | remote manifest present | scheduler | Scheduler → Collector | scheduling behavior test | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | tenacity | remote manifest present | retry/backoff | Reliability | retry semantics test | FOUNDATION PRESENT |
| 🟩 LUMENIS NOW | feedparser | local 6.0.14 import PASS; remote manifest pending | RSS + Atom parse | External → Evidence | remote manifest convergence; RSS fixture PASS; Atom functional fixture must run | PARTIAL / LIBRARY-LEVEL |
| 🟩 LUMENIS NOW | Public HTTP Adapter | not yet closed | unified public-page acquisition | External → Evidence | public HTML → Evidence → Canonical + failure isolation | TO DEVELOP |
| 🟩 LUMENIS NOW | RSS Adapter | not yet closed | RSS monitoring | RSS → Evidence | RSS → Evidence → Canonical | TO DEVELOP |
| 🟩 LUMENIS NOW | Atom Adapter | not yet closed | Atom monitoring | Atom → Evidence | Atom fixture/real public feed → Evidence → Canonical | TO DEVELOP |
| 🟩 LUMENIS NOW | Sitemap Adapter | not yet closed; no new parser required | URL discovery | Sitemap → Fetch → Evidence | XML parse + URL discovery + Evidence | TO DEVELOP |
| 🟩 LUMENIS NOW | Browser Adapter | existing browser capabilities need unified semantics | browser acquisition | Browser → Evidence | never bypass Evidence/Canonical; existing XHS/browser regression stays green | TO CONVERGE |

Approved closed-loop target:

```text
External Source
→ Acquisition Adapter
   ├─ Public HTTP
   ├─ RSS
   ├─ Atom
   ├─ Sitemap
   └─ Browser
→ Evidence
→ Canonical Data / Canonical Content
→ Function / Research
→ Metric / Truth Table
→ View Model
→ CTH / BMP / Shared Capability
→ UI / Report / Export
```

Forbidden shortcuts:

```text
RSS → AI directly
Web page → UI directly
Browser result → parallel DB truth
Third party → Canonical/Evidence/Metric/Permission truth owner
```

## 5. Future / optional integration

| Category | Capability | Current decision |
| --- | --- | --- |
| 🟨 FUTURE | Firecrawl Cloud | not current; requires API/commercial/privacy review |
| 🟨 FUTURE | Exa | not current; requires API/commercial/privacy review |
| 🟨 FUTURE | PostHog Cloud | future observability candidate after privacy/data-boundary review |
| 🟨 FUTURE | Mixpanel | future alternative to PostHog; do not dual-adopt by default |
| 🟨 FUTURE | Supabase | do not migrate current SQLite merely to adopt it; reassess at SaaS/multi-tenant stage |
| 🟨 FUTURE | Railway | not a drop-in fit for current Windows/CDP resident-browser runtime |
| 🟨 FUTURE | Vercel | evaluate only after an actual frontend/runtime split |
| 🟨 FUTURE | Runway / Higgsfield / OpenArt | future media providers after commercial/API/license review |

Figma is no longer classified as a FUTURE product integration in this matrix; it is installed Codex/design tooling and is not a LUMENIS production-runtime dependency.

## 6. CI binding and run #148 correction

CI binding is proven:

```text
workflow = .github/workflows/platform-verify.yml
trigger  = push to main / pull_request to main / workflow_dispatch
run      = Verify LUMENIS #148
head     = e50e07701399b1d46b794dd1802dca93defae9d8
status   = completed
result   = failure
```

Successful steps in #148 included:

```text
Checkout
Set up Python
Install development/test dependencies
Compile Python sources (BLOCKING)
Validate CI test-tier manifests (BLOCKING)
Credential-path boundary diagnostic
Production/live and quarantine inventory
Boundary Check (ADVISORY)
Asset Impact Scan (INFORMATIONAL)
```

Blocking failure:

```text
Run clean-checkout hermetic pytest (BLOCKING) = FAILURE
```

The log shows 257 hermetic test files selected and 21 failing test cases across these areas:

```text
AI provider-policy expectation
Douyin adapter status/result semantics
HK-only collection policy artifact-path expectation
RedNote rotation / resident-browser port expectation
Bilibili / Weibo secondary-platform adapter semantics
CDP retry/online expectation
```

Therefore:

```text
CI_BOUND       = YES
CI_TRIGGERED   = YES
CI_COMPLETED   = YES
CI_PASS        = NO
TARGETED_TESTS = NOT GREEN
```

Do not weaken, quarantine or delete legitimate deterministic tests merely to obtain green CI. First classify whether each failure is stale-test expectation, fixture/mock drift, or production regression.

## 7. Launch Gate

| Gate | Name | Acceptance condition | Current classification |
| --- | --- | --- | --- |
| G00-A | CODEX_TOOLING_READY | GitHub/OpenAI Developers/Figma/Context7/Codex Security installed; Playwright MCP installed; relevant tools pass real Codex smoke tests | INSTALLED / FUNCTIONAL SMOKE PENDING |
| G00-B | CI_BOUND | workflow reacts to main push/PR/manual dispatch | **PASS** |
| G01 | DEPENDENCY_READY | required runtime deps import; manifest truth matches candidate | **PARTIAL** — local imports/pip check pass; remote feedparser manifest convergence pending |
| G02 | ADAPTER_IMPLEMENTED | Public HTTP / RSS / Atom / Sitemap / Browser adapter contracts implemented | NOT VERIFIED |
| G03 | EVIDENCE_TESTED | every adapter emits provenance-bearing Evidence; idempotence/source semantics correct | NOT VERIFIED |
| G04 | CANONICAL_TESTED | Evidence → Canonical works; missing is never fabricated as zero | NOT VERIFIED |
| G05 | SIDEWRITE_ISOLATED | adapter/side-write failure does not corrupt primary Production Truth | NOT VERIFIED for new adapters |
| G06 | API_VERIFIED | related API data/status/error semantics verified | NOT VERIFIED |
| G07 | UI_VERIFIED | Experience V2 shows real state; no fixture-only production claim | NOT VERIFIED |
| G08 | TARGETED_TESTS_PASS | new/affected + clean-checkout blocking regression green | **FAIL at CI #148** |
| G09 | 8201_HEALTHY | production candidate starts and `/healthz` is healthy | NOT VERIFIED by this update |
| G10 | PLAYWRIGHT_LIVE_PASS | critical Experience path passes browser acceptance | NOT VERIFIED |
| G11 | WORKTREE_CLEAN | candidate contains only intended files | current local/remote relation must be rechecked; old `ahead 1` snapshot is historical |
| G12 | P0_P1_ZERO | no unresolved P0/P1 release blockers | NOT VERIFIED |
| G13 | SAFE_TO_COMMIT | scope/tests/rollback point known | candidate-specific |
| G14 | SAFE_TO_PUSH | local/remote relation reconciled; candidate SHA explicit | candidate-specific |
| G15 | LIVE_VERIFIED | post-start/deploy live runtime acceptance passes | NO |

## 8. Codex next takeover sequence

When Codex quota is available again:

```text
1. preserve local unpushed work
2. git fetch origin and reconcile local main with current remote main without reset/clean
3. keep and verify the intended feedparser manifest delta
4. reproduce/classify/fix CI #148 blocking failures
5. run Atom functional fixture
6. smoke-test installed Codex tools/plugins
7. implement/converge Public HTTP / RSS / Atom / Sitemap / Browser adapters
8. enforce Adapter → Evidence → Canonical
9. targeted + affected regression
10. 8201 health → API → Playwright E2E → CI → release gates
```

## 9. Status semantics

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E evidence proves behavior
RELEASED    = release/security/recovery/rollback gates pass
OPERATING   = real operation produces required live/time evidence
```

Never convert dependency installation, plugin installation, documentation, a CI trigger, an HTTP 200 or a rendered page into `LIVE_VERIFIED`.

## 2026-09-18 closure update — current evidence, not a historical overwrite

This dated addendum records the current implementation after the original baseline above. It does not rewrite the earlier failure record or claim public deployment.

| Area | Current evidence | Classification |
|---|---|---|
| Dependency | `requirements.txt` contains `feedparser>=6.0.11` | MANIFEST_PRESENT |
| Public HTTP | `platform_adapters/public_http.py` uses the shared SSRF-safe public fetch boundary | IMPLEMENTED / TESTED |
| RSS | Existing `web_monitor_v570.fetch_google_news_rss` is normalized by `WebRSSAdapter` and covered by a fixture test | IMPLEMENTED / TESTED |
| Atom | `AtomAdapter` uses `feedparser`, shared public fetch, provenance, and bounded item normalization | IMPLEMENTED / TESTED |
| Sitemap | `SitemapAdapter` discovers URL entries without creating a second content store | IMPLEMENTED / TESTED |
| Evidence boundary | `tests/test_public_source_adapters.py` proves adapter output enters the existing `secondary_collection` evidence/canonical boundary | TESTED |
| Hermetic regression | The repository CI selector reached 100% locally with `pytest -m 'not online'`; no production DB was used by the new fixtures | LOCAL_PASS |
| Runtime | Canonical 8201 was converged to one supervisor-owned process tree; `/healthz` returned 200 after restart | RUNTIME_VERIFIED_LOCAL |
| Internal browser | Codex In-app Browser tab 3 operated CTH-03: platform selector, keyword input, and read-only collection action were visible and controllable | UI_VERIFIED_LOCAL |
| External release | GitHub Actions billing/account gate and public deployment are separate release gates | NOT_CLAIMED |

The current runtime boundary remains: human-triggered, public or authorized read-only collection; no platform write and no automatic publishing. The built-in browser is the product interaction surface for this acceptance path; an external browser is not evidence for this gate.
