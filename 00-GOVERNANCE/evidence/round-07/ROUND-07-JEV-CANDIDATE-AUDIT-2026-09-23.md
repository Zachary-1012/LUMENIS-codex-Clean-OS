# ROUND 07 — Jev candidate and replacement gate (2026-09-23)

Status: `SUPERSEDED HISTORICAL AUDIT / JEV OFF / EXCLUDED`. The newer [open-source-only model decision](ROUND-07-OPEN-MODEL-DECISION-2026-09-23.md) replaces its activation plan. This record preserves the earlier candidate inspection; it is not a current instruction to request a Jev key, call its API, or activate it.

## Current source and runtime truth

- At inspection, local `HEAD`, fetched `origin/main` and live `refs/heads/main` were `71551eccf4f4b3871135742e2a22f7cff0bb11e4`. Mainline has no accepted Jev adapter or real provider result.
- Protected local candidates include untracked `lumenis/system/ai_gateway/jev.py` (SHA256 `D6DCF17A6C2A883D908953CB900C59FA7BA5D24D5ACCAF446E45E3C0E11EBBE0`) and `tests/test_jev_gateway.py`, plus dirty Gateway provider/channel code. These are `LOCAL_ONLY`, not online implementation or Round evidence.
- The candidate is default `OFF`, limits Jev to typed decisions, and records model/latency/hash/usage metadata. It currently has no product business caller or real user-work E2E. No credential was read, no Jev request was sent, and no live provider test passed in this audit.
- Candidate security and truth gaps: arbitrary configured HTTPS host can receive the Bearer key; redirect behavior is unproven; actor/domain/scope string validation is not canonical Permission or Evidence authorization; configured provider is presented as `AVAILABLE` before live verification; cost, legal, privacy and data-residency gates are open.

## Product Owner decision

Keep Jev and a LUMENIS-specific self-developed typed model as shadow candidates under the **one SYSTEM AI Gateway** for now. Jev is transitional. The self-developed candidate may learn the public typed state/question/rubric and probability-calibration approach, using independently authorized input and human-verified labels. Training on Jev outputs or proprietary material requires a separate license/data-use review.

Use the same authorized real CTH/BMP/Shared jobs to compare both candidates. Record accuracy, probability calibration, latency, Chinese/English behavior, abstention/low-confidence handling, failure recovery, user outcome, trace, observability and rollback. Only after the self-developed path meets predeclared thresholds and ROUND 15 prelaunch review approves may the external Jev path be retired. Until then, neither model owns Evidence, Canonical Data, Permission, human decisions or external effects. Missing API access or real labels remains `UNAVAILABLE / NOT VERIFIED`, never synthetic success.

Local Codex may separately use an open-source engineering model. Its configuration, tests and results do not establish product Jev or self-developed-model acceptance.

## Next bounded gates

1. ROUND 07: keep Jev `OFF`; constrain host/redirect and secret handling, preserve `LIVE_UNVERIFIED` status, bind typed schema and input to canonical Permission/Evidence owners, register the external service and evaluate actual account/model availability, price and data-processing terms before any live shadow call.
2. ROUND 07: define the versioned LUMENIS typed-job evaluation set and independently labeled outcomes; build the self-developed candidate behind the same Gateway with honest `NOT_TRAINED / UNAVAILABLE` state until it has real data and a validated version.
3. ROUND 15: run matched real-user-work E2E, human review and rollback; publish the replacement comparison and explicit Jev exit decision. None of these gates is passed by this audit.

## Current external research

Accessed 2026-09-23. Official [TypeSafe API reference](https://docs.typesafe.ai/api) defines `POST /v1/systemone` with typed `state`, `model`, `questions` and `answers`; [model reference](https://docs.typesafe.ai/models) identifies `jev-1.13.0` and a movable alias. [Coding-agent guidance](https://docs.typesafe.ai/introduction/coding-agents) states Jev is not a coding LLM. The [TypeSafe site terms](https://typesafe.ai/legal/terms) reserve proprietary materials and defer separately contracted product terms; API-output training rights are therefore unverified. `ADAPT` only the public typed-decision and evaluation principles to the canonical Gateway; `DEFER` external activation and `REJECT` unlicensed output training. TypeSafe is a hosted service, not an adopted open-source model dependency.
