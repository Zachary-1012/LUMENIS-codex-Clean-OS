# LUMENIS Test Tiers

This file defines how tests are interpreted in CI. It prevents two failure modes:

1. false-green CI that hides real syntax/test failures;
2. false-red clean-checkout CI caused by tests that require private cookies, protected production data, resident browsers, or a specific developer machine.

## Tier A — Repository Integrity (BLOCKING)

Runs on every PR/push from a clean checkout:

- dependency installation
- `python -m compileall -q .`
- pytest collection and clean-checkout reproducible tests

A failure here is a real repository blocker.

## Tier B — Hermetic Product/Contract Regression (BLOCKING)

Runs all non-online tests except files listed in `tests/ci_environment_tests.txt`.

Requirements for a Tier B test:

- no real cookies/tokens/session files;
- no protected production database;
- no fixed developer-machine path;
- no resident browser/CDP dependency;
- no live external platform/network requirement;
- deterministic fixture setup and teardown.

If a product/contract test can be made hermetic, move it out of the environment list instead of weakening its assertions.

## Tier C — Production / Live / Environment Gate (NOT A CLEAN-CHECKOUT PASS)

Files in `tests/ci_environment_tests.txt` remain required acceptance evidence, but must run only where their prerequisites exist. Examples:

- protected production-candidate DB copy;
- platform credentials/session state;
- resident browser/CDP;
- generated production baseline;
- local recovery/rollback environment.

Excluded does **not** mean PASS, obsolete, or optional. Production readiness cannot be declared from Tier A/B alone.

## Change rule

When adding or moving a test between tiers, record the reason. Do not put a failing deterministic regression into Tier C merely to make CI green.

Preferred migration direction:

`environment-dependent test -> temp fixture / fake adapter / production-candidate copy -> Tier B`

## Release interpretation

- Tier A/B green = clean repository is reproducible and its hermetic contracts pass.
- Tier C evidence green = environment/live acceptance passed for the tested release candidate.
- `PRODUCTION_READY = YES` requires the repository's full release gates, not merely a green GitHub Actions badge.
