# ROUND 06 — public page date truth and clean-main preflight

## Source change

The existing SYSTEM `PublicHttpAdapter` accepts a declared publication date
from bounded HTML metadata, `NewsArticle`/`Article`/`BlogPosting` JSON-LD, or
`time[datetime]` only when parseable day-level signals agree. A conflicting
visible date stays unknown with `publication_date_state=conflict`; capture time
is never substituted. The existing note contract now accepts an ISO 8601
timestamp with timezone, retaining the original source time rather than
silently truncating it to a date. Missing or invalid dates still fail the
current quality rule. No stored historical record was rewritten.

On clean main, `collect_search` checked adapter health without forwarding its
manual URL. The existing SYSTEM collector surface now sends the public HTTP
keyword as the URL for that one preflight. A URL-less health check and
`search("")` still return `NOT_CONFIGURED`; a supplied URL permits a bounded
attempt, and the live fetch still validates URL, DNS, redirects and response.
Only this small index hunk was staged from `secondary_collection.py`; its
unrelated large dirty candidate remains untouched and unaccepted.

## Verification at `3b8e5aef` base plus this exact source slice

- Disposable clean archive with only `public_http.py`, `note.yaml`, the
  focused test and the exact staged collector-surface hunk copied in: 45
  targeted/adjacent tests PASS. The existing
  Source → Evidence boundary regression passed in this clean archive.
- Shared dirty checkout: 77 targeted/adjacent tests PASS, including local
  prelaunch and BMP scope regressions, with an external isolated test DB.
- Read-only live fetch of [Nike's 2026-09-09 newsroom page](https://about.nike.com/en/newsroom/releases/nikelab-running-brings-together-performance-craft-and-style-for-every-run)
  returned a `NewsArticle` date of `2026-09-09T07:00:00-07:00`.
- Read-only live fetch of [Estée Lauder's FY2026 results page](https://www.elcompanies.com/en/news-and-media/newsroom/press-releases/2026/08-19-2026-110037466)
  found JSON-LD `2026-08-25` and visible `Aug 19, 2026`; the adapter returned
  an empty publication time and `conflict`. These are page signals, not
  business performance or customer-demand facts.
- No DB write, platform login, personal browser profile or Cookie was used.

## Acceptance boundary

The actual product DB still has 112 earlier rows with unknown publication
times and `data_quality_status=error`; this source fix does not repair or
rewrite them. A new bounded capture requires its own exact Permission,
Evidence, Canonical read-back and quality check. Global CTH/BMP coverage,
real-user E2E, ROUND 06 and release remain unaccepted.
