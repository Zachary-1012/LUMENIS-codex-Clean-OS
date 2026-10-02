# Public Website development brief

Status: implementation foundation for ROUND08, scoped to `website/**`.

## Product and surface assumptions

- The Public Website is a separately deployable SEO/acquisition surface. It
  explains LUMENIS, shows a clearly labelled fictional demonstration, and
  routes people to configured trial, contact, help, and workspace destinations.
- It owns no Product Truth, workflow execution, account, permission, evidence,
  database, provider key, or operational workspace state.
- The public copy uses the current naming contract: full domain names on the
  primary UI and no internal CTH/BMP abbreviations. The Korean display name is
  `서경`; `LUMENIS` remains the product mark.
- The composition follows Point → Axis → Trace → Field → Strata → Boundary and
  Trace/Return. Commercial operations use temporal/causal language; brand and
  market work uses relationship/propagation language. The page is deliberately
  a spatial/editorial field rather than a generic SaaS hero, card grid, or
  dashboard.
- Product demonstration text is fictional, has no customers or metrics, and
  never claims to execute a desktop-only capability. The access ledger reports
  configured/unconfigured public destinations honestly.

## Implementation choices

- Astro `7.3.3` is used only inside this package to prerender semantic HTML and
  three locale routes. No dependency is added to the root acquisition package.
- `/` is Chinese, `/en/` is English, and `/ko/` is Korean. Language links are
  visible and explicit; there is no browser-language redirect.
- `LUMENIS_PUBLIC_SITE_ORIGIN` is required for an indexable deployment build.
  Without it, canonical/hreflang/sitemap output is withheld and robots is
  blocked. Public destination variables are HTTPS-only and reject credentials.
- Reduced motion, keyboard focus, named landmarks, semantic headings/lists,
  contrast-aware focus rings, and a 390px responsive layout are part of the
  foundation. The browser check is a smoke check, not a claim of full E2E.

## Standards and project research

Research was performed 2026-09-22 (Asia/Shanghai) against primary sources:

1. [Google Search Central — Managing multi-regional and multilingual sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)
   (current documentation; accessed 2026-09-22). Decision: separate locale
   URLs, visible language navigation, and no guessed-language redirect.
2. [Google Search Central — Localized versions of your pages](https://developers.google.com/search/docs/specialty/international/localized-versions)
   (current documentation; accessed 2026-09-22). Decision: emit fully-qualified
   self/alternate `hreflang` links and locale-aware sitemap links when origin is
   configured.
3. [Google Search Central — Organization structured data](https://developers.google.com/search/docs/appearance/structured-data/organization)
   and [General structured data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)
   (current documentation; accessed 2026-09-22). Decision: use minimal visible
   WebSite JSON-LD only; omit unverified address, telephone, logo, reviews,
   prices, and availability. JSON-LD describes visible content; rich-result
   display is not guaranteed.
4. [W3C WCAG 2.2 — Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible)
   and [W3C H101 — Using semantic HTML landmarks](https://www.w3.org/WAI/WCAG21/Techniques/html/H101)
   (current standards guidance; accessed 2026-09-22). Decision: visible focus
   rings and header/nav/main/section/footer landmarks with semantic HTML.
5. [Astro repository](https://github.com/withastro/astro) and [Astro package manifest](https://github.com/withastro/astro/blob/main/packages/astro/package.json)
   (main repository and package metadata; accessed 2026-09-22). The current
   primary repository identifies Astro as MIT-licensed, with active main/release
   maintenance and package version `7.3.3`. This is relevant to maintenance,
   compatibility, and security review, but no Astro source or assets are copied.
   The MIT license therefore governs the dependency only; it does not add
   permission for unrelated LUMENIS code or content.

Astro was selected over a bespoke generator because its official static output,
locale routing, and maintained release path reduce SEO and build mistakes while
keeping the package isolated. No network integration, analytics, auth, or paid
hosting is introduced.

## Impeccable/design-skill boundary

The Product Owner pinned the public composition grammar and the task card limits
changes to `website/**`. Impeccable context was run once; its `concept-seed`
workflow would require a separate product/design artifact outside this scoped
package, so it is not applicable. This brief records the local assumption
without creating a second global authority.

## 2026-10-02 bounded task-path refinement

Status: **DESIGN_READY — reviewed by M / 序境12 on 2026-10-02**. This is a
subordinate implementation specification, not a new design authority. It does
not accept the operational product, a model, or a deployed public destination.

M review (thread `01a0cd84-7685-7a73-97d9-83a14a546e71`): approved this complete
bounded candidate under the sole Experience Constitution §§31–36, only for the
listed Website files and interactions. Workflow explanations and the fictional
nine-step Trace must remain visibly identified as previews/demonstrations.
Destinations must be actually configured or explicitly unavailable; no business
or model availability may be implied. Preserve three languages, no-JS reading,
hash/back/forward, keyboard, narrow layouts and reduced motion. W6 owns shared
CURRENT status, integration and publication; F returns the exact diff, evidence
and limits for actual-product acceptance. This design approval is not runtime
acceptance or authorization for a public deployment.

### Context and exclusive scope

- Resume 2026-10-02: freshly verified `main` = `origin/main` =
  `a85c35ee619ae75052f91b3b924e467bd8bc1622`. The current C1-C6/W1-W6 delivery
  router supersedes the earlier ROUND08 scheduling label. This candidate stays
  within F's Website surface; W6 coordinates integration/publication and M
  reviews this design. The earlier read-only base below is provenance only.
- Base: local `main` and freshly fetched `origin/main` both
  `03740bc74e645f8c4212103b8aa0f2cef02e0102` when this batch opened.
- Exclusive write scope: `website/**`. Preserve concurrent `work/`,
  `tests/test_timeline_rendering.py`, `lumenis/system/ai_gateway/owned_inference.py`
  and `tests/test_owned_inference.py`; this batch does not inspect or edit them.
- Authority: root `AGENTS.md`, the current AI-native Product Constitution,
  Product Architecture, Experience Constitution, Multi-Surface Decision,
  Source Owner Index, Product Positioning and Real Delivery Overlay under
  `00-GOVERNANCE/`. The Experience Constitution remains the sole design owner.
- Navigation: the capability locator routed `--path website --query
  'public website interaction and product entry'` to Experience. Read current
  `SitePage.astro`, `i18n.ts`, `site.css`, `site-motion.js`, destination/host
  validation and `tests/site.test.mjs`. `contracts/experience/README.md` and
  ACC-02/CTH-03/SH-01 specifications preserve this surface's public role.
- No dedicated Public Website screen specification was found. Review this
  exact bounded candidate before implementation; do not borrow an operational
  screen's approval or promote this brief automatically.
- No API, new account design, production data, model/provider, external form,
  dependency, analytics, hosting or platform-availability change is proposed.
  Shared staging, commit, push and CURRENT updates belong to 序境12.

### Observed reference research, not copied design

Accessed 2026-10-02 (Asia/Shanghai), official OpenAI sources only:

| Source | Observed evidence | Decision and local mapping |
| --- | --- | --- |
| [OpenAI homepage](https://openai.com/) | Browser-rendered feature announcement can be dismissed; this reveals the primary intent entry and focuses its input. Product navigation opens separately. | ADAPT: make the visitor's next action explicit in our existing hero; keep return paths. Do not add an unbound prompt box. |
| [Codex product page](https://openai.com/codex/) | Current page pairs task descriptions and actual interface imagery with explicit desktop/web entry choices. | ADAPT: pair each of our two existing business questions with necessary input, decision and deliverable; show only configured destinations as actionable. |
| [Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) | Dated 2026-02-02; page labels itself historical. Selecting the 800k-token tab visibly changed the selected state and associated embedded result. Video controls rendered, but attempted playback remained blank at 00:00. | ADAPT: reversible selection with a clearly associated panel. DEFER media: no claim that its video was reviewed, no borrowed recording or simulated live LUMENIS output. |
| [DevDay 2026 recap](https://openai.com/index/devday-2026-recap/) | Official publication dated 2026-09-29 was read; a text source is not playback evidence. | Context only. No new LUMENIS capability or delivery promise follows from an external launch. |

These are maintained publisher pages, accessed as current web material (the
dated launch article is explicitly historical). No source code, logo, image,
video, typography asset or layout is imported; therefore no new third-party
component/license is introduced. The references only explain the abstract
principles already allowed by the Experience Constitution. Public descriptions
do not grant permission to publish private product data or user artifacts.

### Reviewable composition and interaction

Preserve the paper field, restrained optical trace, LUMENIS wordmark and
Point / Trace / Return grammar. Avoid a dashboard, feature-card grid, fake chat
or animated metric display. Keep the existing site sections and their anchors.

1. **Entry / hero.** Keep the existing title and mark. Add a prominent product
   entry bound to the existing `workspace` destination. If not configured,
   show its truthful unavailable state and an active in-page path to the two
   business questions. No guessed local URL, new login, or implied availability.
2. **Choose a question / existing `#scenarios`.** Present the two existing
   commercial-operations and brand-market questions as selectable editorial
   rows. On wide screens, a narrow question rail accompanies one spacious
   reading panel; on small screens, the controls precede the same panel in
   document order. A question selection does not execute a business task.
3. **Three reading stages.** For each question, use scenario-specific copy for
   “materials to bring”, “judgment to make” and “deliverable to prepare”.
   Commercial operations names store/activity/resource confirmation and a
   content/operations plan. Brand work names market/competitor/consumer inputs,
   target audience/content/channel/creator choices and a Brief. All copy is
   a labelled workflow preview, not invented source findings or saved output.
   No numbers, customers, actual-report snippets or fictional success states.
4. **Progressive details.** Selecting a stage changes the adjacent reading
   panel and its accessible selected state. Previous/next and return-to-question
   actions provide explicit traversal; touch swipe is not the only way to
   discover a panel. Optional native disclosure exposes what still needs human
   confirmation. Switching the question resets to materials and announces it.
5. **Trace / existing `#demo`.** Retain the clearly labelled fictional nine-step
   trace and linear/orbit choice. Resolve hash navigation to the correct visible
   panel after enhancement, including back/forward; prevent a hidden deep-link
   target. Preserve all anchor content when JavaScript is absent.
6. **Product access / existing `#access`.** Preserve the four configured-link
   contracts and HTTPS/host protections. Do not rewrite an absent destination as
   healthy, connect private artifacts publicly, or call a successful static
   navigation a working Core/model workflow. Remove the stale public promise of
   local AI without changing the approved surface/platform roster.

### Accessibility, states and performance

- Chinese, English and Korean have equivalent question/stage/action/state copy.
- Use native buttons, labelled groups and explicit panel relationships; visible
  focus, keyboard previous/next/Home/End where applicable, touch targets at least
  44 px and no hover-only disclosure. Active selection must be readable without
  color. No focus trap or automatic scrolling while reading.
- No-JS fallback: both questions and every stage remain readable in order;
  enhancement-only controls are hidden until handlers are ready.
- No remote demo content is loaded, so do not invent a loading spinner or retry
  state. Missing public destinations remain unavailable. A failed script leaves
  the static explanation and anchors useful. Browser back/return restores a
  discoverable stage, not a hidden panel.
- Reduced motion removes translation/tilt and unnecessary transitions, including
  preference changes during the session. Tiny focus/selection changes remain
  instantaneous. No autoplay, WebGL, copied media or new network dependencies.
- Check 1920/1440/1280/1024/768/430/390/360 px layouts. At narrow widths, the
  question/stage choice and its content stay together; no fixed-height text crop
  or orbit-induced horizontal overflow. Existing header/access links remain
  reachable without overlapping the content.

### Bounded implementation and acceptance

Allowed implementation files: `src/components/SitePage.astro`, `src/i18n.ts`,
`src/styles/site.css`, `src/scripts/site-motion.js`, and affected
`tests/site.test.mjs`, relative to `website/`. Package configuration changes need
a demonstrated defect; no dependency additions are planned.

REAL USER JOB: a visitor understands which existing LUMENIS workflow fits their
business question, what materials they need and what deliverable they seek,
then follows a configured product entry or sees why it is unavailable.

ENTRY / REAL INPUT: public page, visitor's selection between the two approved
business questions. END-TO-END PATH: select question → inspect its three stages
→ return/change question → trace a source relationship → product entry.
VISIBLE RESULT: the chosen workflow's distinct inputs/decision/deliverable and
honest destination state. No production data is necessary for this explanatory
job. FAILURE/RECOVERY: missing destination, no JavaScript, direct/deep-link,
browser back/forward, reduced motion and narrow viewport remain usable.

Verification after the final edits: package build and Node tests in preview
and isolated configured environments; browser operation of question/stage
selection, keyboard navigation, Trace/Return/deep-link, locales, responsive
widths, no-JS fallback and reduced motion. Record exact exit codes and source
snapshot. Then run the current constitution and three Experience blocking
validators without weakening existing tests. A test/build/screenshot alone is
not public release or operational-product acceptance.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: no coverage change; all coverage claims
remain unverified by this batch. COMMERCIAL OVERLAY IMPACT: public-hosting,
configured real destinations and actual operational product acceptance remain
separate. Return the diff, tests, browser evidence and limits to 序境12 for
acceptance and co-publication; the Product Owner retains final product review.

### F verification record — 2026-10-02, local candidate

Source base: `a85c35ee619ae75052f91b3b924e467bd8bc1622` plus the protected
Website files above. M's same-day copy review was applied: each workflow has
one path-preview label; stage copy describes the visitor's work and intended
deliverable. It does not assert an executed business result.

- `npm test` with the five public destination/origin variables unset: Astro
  build and **12/12 Node tests PASS**, exit 0, after the final copy edits.
- Configured-branch contract check used process-only HTTPS fixture values
  (`https://github.com` origin and the existing public repository URL for
  destinations), without opening those links. Build and **12/12 PASS**, exit 0.
  A subsequent unset-variable run restored the unavailable-entry, no-index
  preview; build and **12/12 PASS**, exit 0. No deployment configuration changed.
- Actual IAB operation at `http://127.0.0.1:4321/`: hero question entry, switching
  the commerce/brand question, three stages, keyboard End, return-to-question
  focus, and Trace Action deep link with browser back/forward all produced the
  expected visible panel. English and Korean stage controls were operated too.
- Widths 1920, 1440, 1280, 1024, 768, 430, 390 and 360: no document horizontal
  overflow. Desktop question rail and mobile stage layout inspected visually.
- JavaScript disabled: both questions and all six stage bodies remained
  readable; enhancement-only buttons were hidden. With reduced-motion media
  preference, orbit selection remained operable at 360px without overflow.
  These temporary browser overrides were restored.
- Browser warning/error log for these operations was empty. Screenshots are
  local artifacts in `work/frontend-2026-10-02/website-desktop-1440.jpg` and
  `website-mobile-360.jpg`; they supplement the operations, not replace them.
- Final touch-target repair: linear/orbit controls measured 38px, then were
  raised to 44px. A fresh preview build plus 12 tests passed (exit 0); actual
  360px browser readback measured both at 44px, orbit Outcome selection worked,
  and horizontal overflow remained absent. The final orbit screenshot is
  `work/frontend-2026-10-02/website-orbit-360.jpg`.

Disposition: this bounded explanatory flow has local build, tests and browser
operation evidence. Required repository blocking validators and W6 integration
publication are recorded separately with the final F package. Public hosting,
real configured destinations, Product Owner review and operational App work
are not established by this Website result.

### M acceptance — 2026-10-02

M (序境12, thread `01a0cd84-7685-7a73-97d9-83a14a546e71`) accepted
this bounded Website visitor workflow's local engineering result after reading
the implementation/test diff, the evidence above and desktop/mobile/orbit
screenshots. The five source/test files are frozen. The accepted publication
scope is those five files plus this brief and W6's necessary CURRENT/evidence
update. W6 owns the exact main integration and remote verification.

This accepts the explanatory visitor flow only. It does not accept public
release, configured production destinations, the App SourceBrief candidate,
operational App workflows or the Product Owner's final product review.
