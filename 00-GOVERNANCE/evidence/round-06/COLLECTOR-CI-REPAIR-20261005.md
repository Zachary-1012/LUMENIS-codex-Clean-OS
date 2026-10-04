# Collector CI repair — 2026-10-05

Scope: correct the exact failures from Product Gate run `37210553807` on
`8e6d238e`. This is a source/test repair, not live collection or product
acceptance.

## Cause and repair

| Failure | Corrected behavior |
| --- | --- |
| Bilibili `mid` compared as an integer in Canonical output | Raw native `mid` remains unchanged; Canonical author identity is exact text, matching the shared platform contract. |
| Social query limit test still used the retired 120-character bound | The current bounded social query limit is 256; an input of 257 is rejected before network work. Public source URLs retain their separate 4096-character identity bound. |
| Instagram health tests treated a local Cookie/proxy file as a registered worker | An unregistered route returns `NOT_CONFIGURED`; public post inspection stays `NEED_VERIFY` until its actual document is read. No Cookie/session value is used in this check. |
| Failed RedNote detail read replaced earlier measured metrics with null | `database.insert_note` keeps an explicit current-unknown update distinct from an incomplete detail observation. A failed detail read preserves earlier measured values; an observed zero still updates to zero. |

The final distinction is in the existing `insert_note` owner. Its caller metadata
is not persisted as a business field; it only tells the writer whether this
specific acquisition actually measured metrics. Raw source, Evidence and Canonical
writers remain unchanged.

## Local verification

Focused hermetic tests passed with the existing isolated DB setup:

- Bilibili adapter and source-URL identity
- Instagram main adapter status
- RedNote unknown/zero persistence
- Database transaction and current metric semantics

The next Product Gate must validate this exact source on GitHub. A green local
test group does not establish live platform readiness, continuous collection,
user acceptance or `OPERATING`.
