# ROUND 06 — Atom native source fields

## Accepted source slice

The existing SYSTEM `web_atom` adapter now retains a YouTube Atom entry's
video ID, exact channel ID, feed title, native view count, thumbnail URL and
uninterpreted rating metadata in Raw. It uses the channel ID as the stable
author key. A feed request for a specific channel rejects entries belonging
to another channel. Identity-less Atom entries fail instead of becoming a
silent empty success. Failure Evidence retains the bounded source path. The
adapter remains `web_atom`; this does not activate the planned YouTube API
adapter or infer likes/comments/shares from the feed's rating count.

## Current-snapshot verification

- A complete clean `e81b67120cdcd2062ab581c693a4b02ccb8715ee` ZIP archive
  replayed only this adapter and the new focused tests: 5 Atom tests PASS and
  the blocking AI-native Constitution validator PASS. The first replay found
  an existing source-provenance regression and failed; it was fixed and the
  complete replay rerun successfully.
- The shared checkout passed the same 5 affected Atom tests with an external
  disposable test seed; the Constitution validator passed. The protected
  product DB was not used as a test seed.
- A real manual `AtomAdapter` read of the [Nike-labelled YouTube channel feed](https://www.youtube.com/feeds/videos.xml?channel_id=UCUFgkRb0ZHc4Rpq15VRCICA)
  returned an entry with `video_id=rPdnb7A0NTQ`, the matching channel ID,
  publication time and observed `view_count=3025`. The count is a changing
  observation, not a permanent value. Likes, comments and shares were absent
  and remained `None`. The source was read through the existing public
  transport with a process-only opt-in secure-DNS fallback, public address
  validation, connection pinning and TLS checks intact.

## Real delivery state

`REAL USER JOB`: a brand lead views actual channel content and its source
metrics inside the selected Nike BrandFocus. `ENTRY`: GLOBAL / ALL then focus.
`REAL INPUT`: the feed above. `END-TO-END PATH`: live Source → Raw was observed;
Normalized → signed Evidence → Canonical → BrandFocus → user result was not
completed by this Batch. `USER-VISIBLE RESULT`: not yet verified.
`FAILURE/RECOVERY`: mismatched channel and absent identity fail closed;
retry and product return require later integration evidence. `ACCEPTANCE
ASSERTION`: ROUND 06 remains REWORK. `COMMERCIAL OVERLAY IMPACT`: rights remain
`pending_review`; no commercial collection license or release is asserted.
`GLOBAL UNIVERSE / DATA MATURITY IMPACT`: no global coverage increase is
claimed. This channel sample is not a global brand baseline. Country,
market-presence and venue-tenant relationships remain a separate existing
Shared Database/registry closure gap, including the new Product Owner target
of 14 country categories with at least 50 BMP brands and 50 CTH commercial
subjects per category. `CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION`:
the live YouTube Atom format was inspected on 2026-09-27; only feed-provided
fields were adopted into the existing adapter, without a new provider or owner.
