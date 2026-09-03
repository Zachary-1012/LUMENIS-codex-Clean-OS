# KOS Collection Accuracy Gate v1

## Purpose
Prevent inaccurate collection from contaminating KOS ranking, tiering, outreach, paid amplification, and reports.

## Hard rules
1. Collection relevance is not KOS ownership.
2. Mentioning Taikoo Hui or a merchant brand does not prove Taikoo Hui KOS ownership.
3. Merchant KOS must remain separate from target-entity KOS.
4. AI may assist semantic classification but cannot bypass deterministic subject filters.
5. Unverified or anomalous collection must not enter official KOS ranking.
6. No fabricated metrics, delivery status, conversion, ROI, or creator relationship.

## Quality gates
Track per collection run: fetch success rate, valid-content rate, subject precision, duplicate rate, author resolution rate, timestamp completeness, engagement completeness, and evidence completeness.

## Precision/recall
Use precision and recall as monitoring metrics. Precision is prioritized for production KOS decisions where false-positive contamination is costly. Recall gaps must remain visible rather than silently filled by AI.

## Quarantine
Anomalous records enter QUARANTINE until validated, repaired, or discarded.

## Evidence chain
KOS result -> author -> content -> collection run -> subject rule hit -> ownership evidence -> AI decision (if used) -> final decision.

## Production gate
If collection quality is below configured thresholds, block the affected batch from official KOS tiering, ranking, outreach, paid-amplification recommendation, and formal reporting.