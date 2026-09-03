# Podcast Intelligence Module

## Purpose

建立可插拔的播客内容情报与生产基础设施：以「人物 → 采访 → 故事节点 → 问题 → 内容资产 → 平台数据 → 用户反馈」为核心数据链，不改变 ZBC 现有品牌舆情核心链路。

## Design principles

- Preserve existing ZBC architecture and product intent.
- Reuse existing evidence, report, AI gateway, configuration, logging, database migration and health primitives where contracts permit.
- New AI/model behavior starts in Shadow Mode and cannot silently become business truth.
- No platform restriction bypass, CAPTCHA bypass, account switching or rate-limit evasion.
- Podcast data remains isolated from existing brand-monitoring facts; cross-module linkage happens through explicit contracts.
- Every material result must be traceable to source evidence and runtime metadata.

## Planned capability layers

1. **Ingestion** — RSS/Atom, podcast platform metadata, supplied audio/video, transcript files.
2. **Speech intelligence** — ASR, timestamps, speaker diarization, sentence/turn alignment.
3. **Interview intelligence** — people, questions, answers, story nodes, conflicts, turns, emotional/insight peaks.
4. **Content intelligence** — hooks, titles, clips, quotes, topics, series, content-yield graph.
5. **Distribution intelligence** — platform, publish time, runtime, views, likes, comments, saves, shares and observed trend points.
6. **Comparative intelligence** — benchmark episodes, high/medium/low performers, controlled comparisons where data permits.
7. **IP graph** — person ↔ story ↔ problem ↔ episode ↔ clip ↔ platform ↔ audience signal.
8. **Production loop** — research → brief → outline → edit map → derivatives → review → evidence.

## Initial canonical entities

- `podcast_show`
- `podcast_episode`
- `podcast_person`
- `podcast_transcript`
- `podcast_segment`
- `podcast_story_node`
- `podcast_question`
- `podcast_topic`
- `podcast_content_asset`
- `podcast_platform_observation`
- `podcast_audience_signal`
- `podcast_ai_run`
- `podcast_evidence`

## Non-goals for this foundation

- Do not replace ZBC's existing brand subject filtering.
- Do not couple podcast collection to Xiaohongshu collection limits.
- Do not add a second general-purpose AI gateway.
- Do not add a new database engine before evidence shows SQLite is insufficient.
- Do not claim platform metrics that cannot be observed or evidenced.
