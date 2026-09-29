# Existing version watcher — default-off corrective Batch

Status: TESTED SOURCE; actual legacy autosave configuration disabled. ROUND 05
and product release remain unaccepted. Base: `06d156c7580059eae7295db30555e4e8008e6434`.

## Incident and exact correction

At 23:59 the existing in-product version watcher automatically saved/pushed
renderer candidates and a SH-01 specification in `06d156c7`, before root finished
acceptance. That commit omitted the required CURRENT update; the takeover
validator correctly failed its co-publication gate. Root retained history and all
work. This corrective commit publishes the renderer's subsequent verification,
the separately completed maintenance-runtime evidence and this incident record.
It does not retroactively make the automatic commit an accepted delivery.

The existing `lumenis/blueprint.py` startup caller and `lumenis/version_center/`
owner are reused. Both automatic Git switches default off. Only actual JSON
boolean true enables one; strings/numbers/corrupt configuration cannot do so.
The watcher checks before creating a thread and rereads after each wait; the
manager also checks immediately before an automatic save. Manual version actions
were not changed. No new Git owner or scheduler was introduced.

The actual ignored version-center configuration was backed up under
`data/private/maintenance-upgrade-6ithkrvh/version-center-before.json` and both
automatic switches were set false through its existing configuration owner.
The old running watcher rereads that configuration. The approved public data
maintenance task remains enabled; no product DB or account configuration changed.

## Verification and limitations

The worker's final files were inspected and their Git blobs verified by root:

- git_manager.py: `f6c2c9d8607a10270964400dd59e165658aed1d0`
- watcher.py: `30aee208c4c75b64b5f4a437209ea48445ca962f`
- test_version_center_autosave_policy.py: `2ecb7e90d4ab1fa1da7b21eb94b6a26665e0f794`

Ten targeted tests passed, exit 0, using a disposable SQLite seed and temporary
fake repository directories. Tests stubbed Git status/save operations: no actual
commit/push, product DB access or service restart. Missing/malformed settings,
explicit true, non-boolean push, disabled startup and disabled running-loop paths
were checked. Thread-leak check and scoped diff check passed. The new source has
not yet been verified through a full product restart; current runtime protection
comes from the disabled configuration.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: develop/review a product change without the application publishing it before
acceptance. Entry: existing Core startup/version configuration. Input: current
protected working tree. Bounded result: actual automatic publishing disabled and
default-off behavior regression tested. Recovery: retain Git history, original
config backup and every candidate; do not reset, clean or discard the working tree.
The evidence does not accept the full version-management UI or ROUND 05.

CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: direct current-owner defect;
no dependency or new feature is justified. COMMERCIAL OVERLAY IMPACT: none.
RELEASED / OPERATING / COMMERCIAL_READY remain NO.
