# Study 26: exact-target review lifecycle

Current source inspected: `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md`, AI-01 “免命令行工具调用与高风险确认”, lines 904 onward, plus §5 object/state/permission feedback. This local reversible archive is an interaction fixture, not a real tool approval or persistent permission.

- Cancel, a new preview, changed target, revocation and completion clear the typed confirmation text. A cancelled previous name is not silently reused for the next authorization.
- Route return preserves local result and denial but clears pending confirmation. Returning is not approval.
- An already archived fixture cannot execute twice; cancel clears pending intent, not an existing result.
- Undo requires current permission and the same exact target version. A changed version leaves the earlier receipt intact and reports stale undo rather than restoring a different object.
- Fixture mutation/reset belongs to unified settings; ordinary workspace exposes preview, confirm, cancel and undo.
- Disposal fences callbacks and removes settings controls.

Six adapter regressions plus existing pure contracts run locally. This is a single local object, no backend Task/Permission/Approval transaction or actual archive. Real dialog focus, browser, keyboard, screen-reader and native acceptance remain pending.
