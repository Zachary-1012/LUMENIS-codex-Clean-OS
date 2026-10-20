# Study 24: conflict continuity and stale-adoption repair

Current working source inspected 2026-10-17: `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md`, lines 164 (research draft continuity and conflict), 836 (saved-work receipt and failure distinctions), 1403 (§5 save/failure/conflict row).

Existing independent simulator repaired, no new entry:
- Editing the original draft invalidates any earlier merge proposal. An old merge can no longer silently overwrite later typing.
- Ordinary local save consumes pending proposal, preventing a second acceptance from making a duplicate local revision.
- Invalid/noninteger remote versions and invalid/oversized texts are rejected. History retains the most recent 32 items; current version/base remain intact. This is a bounded demo journal, not product retention policy.
- Revoked users may keep editing their own local text; status stays denied, remote result is cleared and saving/adoption remains unavailable.
- Both original and pending merge, selection/range/direction, scroll, permission denial and version baseline survive navigation in the same in-memory review session.
- Fixture injection, simulated revocation and reset are in unified settings. Workspace actions remain save/compare/edit/adopt/cancel.
- Disposed callbacks are fenced; settings nodes and listeners are removed.

Five pure and four minimal-DOM regressions added. No real server write or authentication. No native browser focus/selection, mobile, screen-reader or visual acceptance yet. This simulator does not implement product Save As, a real diff renderer or rollback receipt; those remain separate planned integration requirements, not silently counted as covered.
