# 小红书官方快捷搜索扩展：采集适配评估

> Research Material only. This note does not change the XHS/RedNote source, session, or collection policy and is not Production Truth.

## Record

- `id`: `XHS-RESEARCH-2026-09-28-QUICK-SEARCH-EXTENSION`
- `record_type`: `research_case`
- `created_at`: `2026-09-28`
- `repository`: `Zachary-1012/LUMENIS-codex-Clean-OS`
- `commit_sha`: `39285eac20c2068983603826108c2a3a13a93360` (research baseline)
- `owner`: existing SYSTEM Collector / Browser owners
- `status`: `RESEARCHED / NO COLLECTOR ADOPTION`
- `verification_status`: static archive review and Chrome Web Store identity match; extension was not installed or executed; no runtime behavior or signature verification is claimed

## Question

Can the supplied Chrome extension be reused or reverse-engineered as a reliable, cookie-free Xiaohongshu content collector?

## Artifact and provenance

- Supplied ZIP SHA-256: `fb506a52abc93391f654d87de37cd73eeb1cb82c0ba80321a727a773e5a8ba84`.
- The archive contains a CRX3 package named **小红书快捷搜索**, version `0.0.4`, Manifest V3. Its embedded extension ID is `njcijfmdpfjfnohempndpojfgiopkgol`, matching the Chrome Web Store listing ID. The listing identifies `pcweb`, `web@xiaohongshu.com`, and describes the extension as an official product. This is a package/listing identity match; the CRX signature itself was not independently verified.
- The Chrome Web Store describes three user-facing functions: an XHS search new-tab page, an in-site hot-search overview, and right-click search for user-selected text. It does not describe a note export, collection API, or evidence feed.
- The package has no `LICENSE`, `NOTICE`, or `README`. The store privacy panel contains the developer's disclosure that it does not collect or use user data; that disclosure was not independently runtime-audited.
- Manifest permissions include `storage`, `contextMenus`, `cookies`, `webRequest`, and `declarativeNetRequest*`, with XHS and `apm-fe.xiaohongshu.com` host access. The content script contains `document.cookie` references. This is a browser-context search helper, not evidence of a cookie-free acquisition route.
- Review was read-only: the CRX was inspected in memory and not extracted to disk, installed, or executed. No browser profile, Cookie, session, or account was accessed.

## Official-source cross-check (accessed 2026-09-28)

1. [Chrome Web Store listing](https://chromewebstore.google.com/detail/%E5%B0%8F%E7%BA%A2%E4%B9%A6%E5%BF%AB%E6%8D%B7%E6%90%9C%E7%B4%A2/njcijfmdpfjfnohempndpojfgiopkgol) — same name, extension ID, and version `0.0.4`; describes search and hot-search discovery.
2. [Xiaohongshu Open Platform API reference](https://openaccount.xiaohongshu.com/docs/api-reference) and [authorization scopes](https://openaccount.xiaohongshu.com/docs/scope) — describe explicit user authorization and scoped APIs. The scope page says `basic_info` is open while `read_notes` is planned; it is not a general public-note-search feed.
3. [Xiaohongshu Marketing API overview](https://ad-market.xiaohongshu.com/) — describes account management, advertising insights/management, and creator services. The public overview does not establish a generic, unauthenticated public-note collection endpoint.

These sources support a narrow conclusion: this browser extension is a search/discovery interface, while official API access is a separately scoped integration. They do not establish a blanket commercial data license or prove that every desired public field is available.

## Decision

| Proposal | Decision | Reason |
|---|---|---|
| Reuse the extension's user-initiated search/hot-search idea as a possible entry into the existing content research flow | `ADAPT / OPTIONAL` | Could support explicit manual discovery if the existing approved Experience screen already owns that task; retain source URL and collection state. This is a UX principle, not copied code or a new collector. |
| Ingest this extension's output or automate its new-tab/search UI | `REJECT` | No export contract or Evidence/Canonical output is described. It would couple collection to a browser UI and account/session state. |
| Reuse its CRX/JavaScript, cookie handling, or private request/signing behavior | `REJECT` | The package exposes no source license; cookie/network permissions conflict with the cookie-free goal and create account/session risk. Do not bypass signatures, authentication, or platform controls. |
| Automatically collect hot searches or notes based on this package | `DEFER` | First require a documented, authorized source contract and a real Source → Evidence → Canonical path with freshness, idempotence, failure states, and field-level missing semantics. |

## LUMENIS owner mapping

- Any future acquisition remains inside the existing `SYSTEM Collector / Browser` owner and the current source → Evidence → Canonical chain. Do not create a plugin runtime, a parallel collector, or a second content store.
- `MANUAL` remains the user default. A future search affordance must be an explicit user action; opening a page or changing Focus must not trigger collection.
- A public, no-cookie source remains the preferred path for baseline collection. If a platform-authorized session is separately used, follow current repository identity allowlists and secret-safe controls; never import browser Cookies through this extension.
- Do not change the current XHS/RedNote automation hold or account boundary based on this package. The existing XHS research decisions remain authoritative until their owner and Product Owner revise them through the existing gate.

## Outcome

The package is plausibly the official Chrome Web Store extension matching the supplied CRX, but it is **not a collector and supplies no justified ingestion adapter**. The useful transferable idea is user-directed search discovery only. No product source or collection behavior was changed in this research batch.
