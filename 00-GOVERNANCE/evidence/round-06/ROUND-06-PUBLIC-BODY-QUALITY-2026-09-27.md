# ROUND 06 — public article body quality

## Source change

The existing SYSTEM `PublicHttpAdapter` excludes page navigation, headers and
footers when choosing a substantive article body. It keeps a bounded 16,000
character excerpt so a later brand/venue passage is not lost to the previous
1,000 character limit. This is still one public HTTP acquisition path, with
the same safe DNS, redirect, TLS, source identity and Evidence boundaries.

## Current-snapshot verification

- A complete clean `fa7e680c8bbd0ea849d8046f1b8b4345079b3686` ZIP archive
  replayed only the adapter diff and two new focused regressions: 12 targeted
  tests PASS; the blocking AI-native Constitution validator PASS. A first TAR
  extraction failed on some Windows Unicode paths and is **not** acceptance
  evidence.
- Shared checkout with an external disposable test seed: 23 affected adapter
  and source tests PASS. The protected product DB was not used as a test seed.
- Live adapter read of the [ELC FY2026 release](https://investors.elcompanies.com/en/news-and-media/newsroom/press-releases/2026/08-19-2026-110037466)
  returned a 16,001-character bounded excerpt containing a Le Labo mention
  at offset 10,651. Its structured and visible publication dates disagree;
  `publish_datetime` remains blank and `publication_date_state=conflict`.
- Live adapter reads of [Swire's Guangzhou Taikoo Hui anniversary release](https://www.swireproperties.com/en/media/press-releases/2021/20210910_taikoo-hui-guangzhou-celebrates-10th-anniversary/)
  and [Nike's running release](https://about.nike.com/en/newsroom/releases/nikelab-running-brings-together-performance-craft-and-style-for-every-run)
  returned relevant body text and their publisher dates. These probes did not
  import new records or alter the actual product DB.

## Product state and next data gate

The ELC page is a parent-company statement, not direct Le Labo sales,
consumer or social-platform Evidence. Source commercial rights remain
`pending_review`; this material is internal development input. The current
actual DB remains at 114 `public_http` Raw/Canonical rows, with 112 older
quality `error` and two quality `ok`. No additional platform is claimed as
persisted. The next bounded gate is a real non-HTTP platform Source → Raw →
Evidence → Canonical capture under an exact Subject/BrandFocus, preserving
platform-specific fields and honest missing metrics. Global coverage, real
user E2E, ROUND 06 exit, release and commercial use remain unaccepted.
