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
