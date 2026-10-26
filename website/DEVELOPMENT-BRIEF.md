# Public Website development reference

本文件只保存官网相关研究与历史核验依据。当前范围、构图和验收分别引用唯一
[Product Architecture](../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)、
[Experience](../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)、
[完整规划 J01](../00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md)和
[总草图 §2](../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)。
不在本文件维护第二份布局、执行顺序或旧设计指令。

官网按已定2026-10-25录像构图展示寰意产品、场景、公开成果和制作好的演示；
保留播放、章节切换、原创动效、中英韩、无障碍与真实产品/下载链接。
不提供在线试用、功能沙箱、上传、分析、生成或业务保存。真实操作属于Web工作区和Windows产品。
下列历史研究与核验只证明各自记录的版本，不恢复旧视觉，不证明当前官网上线。

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

M (序境12, thread `private-source-id-sha256-c255b5e6a0750867a584692fa6107a7d4df9f561ec97e6faeac199516b522186`) accepted
this bounded Website visitor workflow's local engineering result after reading
the implementation/test diff, the evidence above and desktop/mobile/orbit
screenshots. The five source/test files are frozen. The accepted publication
scope is those five files plus this brief and W6's necessary CURRENT/evidence
update. W6 owns the exact main integration and remote verification.

This accepts the explanatory visitor flow only. It does not accept public
release, configured production destinations, the App SourceBrief candidate,
operational App workflows or the Product Owner's final product review.
