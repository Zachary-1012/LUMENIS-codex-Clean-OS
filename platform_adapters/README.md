# Platform Adapter Layer

## Current release strategy

- **Xiaohongshu (`xhs`)**: primary monitoring platform; deep implementation target.
- **Douyin (`douyin`)**: secondary monitoring platform; deep implementation target.
- **Kuaishou / Bilibili / Weibo / Tieba / Zhihu**: event-monitoring extension points only; do not build deep collectors in this release.

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

- Guangzhou Taikoo Hui subject filtering
- `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- event aggregation
- risk scoring
- report-period filtering
- AI judgment policy
- database business rules

## Safety boundary

Do not implement CAPTCHA bypass, security-check bypass, signature cracking, or aggressive rate escalation here. When a platform reports verification, risk or blocking, the adapter must return an explicit status so the scheduler can pause/cool down and require the normal user/platform verification flow.

## MediaCrawler research rule

The external MediaCrawler repository is a research reference only. Its current LICENSE is a non-commercial learning license. Do not copy its implementation into this production repository without a separate written commercial authorization. Reimplement the required adapter contracts independently and keep this repository's code and business logic separate.
