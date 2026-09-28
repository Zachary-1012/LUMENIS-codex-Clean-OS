# ROUND 06 — Bilibili native detail fields

Status: TESTED SOURCE ONLY / ROUND 06 REWORK.

At main `0576ce971dccaef5047ed4765f441222b3654716`, the existing Bilibili detail adapter discarded first-party `mid`, `pubdate`, `like`, `reply`, `favorite`, and `share` from its `raw_data`. Its downstream native-to-Canonical mapping already expects those keys. The bounded change retains the returned values alongside the previously retained view, danmaku and coin fields; missing source values remain `None`. It changes no request, Cookie, scheduler, permission or platform-enable behavior.

Current-snapshot verification: 70 targeted adapter/delegation/platform mapping tests passed on an explicit disposable SQLite seed. The new regression proves exact native values and the existing Canonical mapping, including an absent share count remaining unknown. The blocking AI-native Constitution gate passed. Production data was not opened or written by this Batch.

No Bilibili live acquisition, authorized source session, Evidence persistence, business scope, user result, automatic collection or real-user E2E was verified. The platform remains disabled in the SYSTEM adapter. This Batch does not advance Global Coverage, ROUND 06 acceptance, release or operating status.
