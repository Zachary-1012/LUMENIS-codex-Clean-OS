# Platform Adapter Layer

## Product coverage

Root `AGENTS.md`, the complete Product Architecture and the Collector closed-loop
contract define scope. Platform names, provider availability and this directory
do not narrow it. Approved platforms and public webpages have equal source-category
weight. Search, independent detail, comments/replies, pagination, authors/history,
media, refresh and recovery retain their original per-platform requirements.
All providers feed the existing Source/Evidence/Canonical and task owners.

## Boundary

Adapters own platform transport concerns only:

- legal/normal login and session state
- search discovery
- content detail retrieval
- comments/replies when supported
- creator/profile retrieval when supported
- platform IDs and URLs
- platform-specific normalization
- platform health/status signals

Core business remains outside adapters:

- authenticated subject/brand focus and business relevance
- entity aliases, relationships and query purpose
- event aggregation
- risk scoring
- report-period filtering
- AI judgment policy
- database business rules

## Safety boundary

Do not implement CAPTCHA bypass, security-check bypass, signature cracking, or aggressive rate escalation here. When a platform reports verification, risk or blocking, the adapter must return an explicit status so the scheduler can pause/cool down and require the normal user/platform verification flow.

## MediaCrawler research rule

The external MediaCrawler repository is a research reference only. Its current LICENSE is a non-commercial learning license. Do not copy its implementation into this production repository without a separate written commercial authorization. Reimplement the required adapter contracts independently and keep this repository's code and business logic separate.
