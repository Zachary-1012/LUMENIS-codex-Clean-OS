# C1 controlled runtime activation — 2026-10-05

## Activated local scope

The canonical Windows supervisor started the current 8201 Core after the
Product Owner's approved continuous-collection rule was made explicit in the
ignored local runtime configuration:

```text
REDNOTE_AUTO_RUN=true
REDNOTE_AUTO_SCOPE=GUANGZHOU_TAIKOO_HUI
REDNOTE_AUTO_SOURCE=rednote_hk
REDNOTE_AUTO_CADENCE_MINUTES=720
```

These values match the existing narrow `rednote_policy` contract. The launcher
starts only the approved HK/international `XHS_RETINAUT` resident on 9223 and
the separate 9224 general browser. It does not launch, inspect, import, export
or use the protected Mainland personal XHS profile.

## Runtime readback

- `http://127.0.0.1:8201/healthz` returned `ok=true` and database `ok`.
- The HK resident status returned `RESIDENT_ACTIVE`, `session_ok=true`,
  `user_paused=false`, `recovery_active=false`.
- `GET /api/collector-guard/status` reported the enabled guards healthy for
  its currently registered platform adapters.
- No source content, Cookie, account ID, page URL or credential was read into
  this record.

## Scope and limits

This is a product-owned resident/scheduler activation, not a Codex-driven
collection run. At observation time the resident `collections` count was zero.
It therefore does not prove that a scheduled collection has yet produced a
Source, Evidence, Canonical record, task result or user-visible answer.

The current activated automatic scope is only the existing HK RedNote Guangzhou
Taikoo Hui path. Instagram, Facebook, WeChat Official Accounts, RedNote/XHS,
Douyin and X remain the required six-platform program, but this record does not
claim their continuous collection, coverage or result acceptance.
