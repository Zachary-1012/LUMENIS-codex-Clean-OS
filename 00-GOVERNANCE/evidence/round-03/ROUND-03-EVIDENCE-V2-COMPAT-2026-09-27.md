# ROUND 03 — Shared Evidence v2 reader/writer compatibility (2026-09-27)

Status: `TESTED / PRODUCT-DB READ-ONLY VERIFIED`; Round 03 remains `REWORK`.

This bounded source Batch adds the existing canonical Evidence owner's v2
writer-authenticated record signing and verification API to main. It preserves
the already deployed material-field and parsed-JSON canonicalization algorithm.
Scoped Evidence requires an active HMAC key and fails closed when the signing
contract or schema is absent. Legacy unscoped rows remain distinguishable from
writer-authenticated records. No historical Evidence row is rewritten.

Verification on the exact staged `ab9affdd` source snapshot: 36 targeted Evidence,
entity-relation and compatibility tests passed. A fixed synthetic digest
regression matches the preexisting v2 canonical payload. After private key
configuration was loaded in memory, a read-only check of the actual local v18
product database classified all 192 existing Evidence rows as v2
`writer-authenticated` (192/192). Before the compatibility correction, the
candidate verifier classified the same 192 rows as tampered; that candidate was
not published. No credential value was printed or stored in this evidence.

The product database was not written, migrated, repaired or copied by this
Batch. This does not establish Global coverage, a real user Job, a completed
Round or release. Hosted CI execution and real user E2E remain unverified.
