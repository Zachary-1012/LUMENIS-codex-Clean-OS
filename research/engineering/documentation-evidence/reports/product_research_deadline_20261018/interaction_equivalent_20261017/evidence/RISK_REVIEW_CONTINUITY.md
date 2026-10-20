# Study 37: preserve risk-review context

Current source read: `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md` BMP-10, lines 771–777: retain filters/selected object/unsubmitted judgment; separate source/rule/human decision/outcome; withdrawal, unknown metrics, permission denial and historical versions remain explicit.

Independent view now preserves selection, exact reason, decision, reviewed proposal, local history, textarea range/direction/scroll and denial across in-memory route return. Switching the object with an unfinished reason stays blocked. Source withdrawal invalidates pending confirmation and marks retained old records without rewriting them. Revocation clears presented evidence/history/reason and remains denied after navigation.

Artificial withdrawal/permission controls are under unified settings. Disposed callbacks cannot mutate old state. Ordinary text edits leave existing history DOM intact instead of recreating it on every keystroke. This is a deterministic render optimization, not a measured browser FPS claim.

The reducer no longer silently truncates reasons or coerces arbitrary objects to text. Invalid/oversized input leaves the accepted draft intact; the view retains the unapplied original input with an error and blocks preview/record of a different old draft. Local history is bounded at 256 records, refusing a new record while preserving all existing history and draft. This limit is a demo safety bound, not product retention policy.

Six adapter regressions cover these transitions, plus existing pure tests. Initial adapter run exposed a missing `replaceChildren` operation in the minimal DOM test harness; it was supplied and rerun. Native UI behavior remains unverified. Real Case creation, escalation/cooldown, owner permissions, save/reopen, true source/rule versions and outcomes are still integration gaps. No extra entry or real risk score is claimed.
