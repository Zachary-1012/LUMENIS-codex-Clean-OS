# Study 71: reopen and draft continuity repair

2026-10-17, independent review working copy, after immutable 1418Z freeze.

Current source read: `lumenis_working_20261017/source/00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md`, §14 P12–P13. Research levels, evidence drawer preserving reading location, independent validation/counterexample and explicit unverified state remain the governing behavior. No product Owner change or positive promotion is claimed.

Defects corrected in `src/research-study.mjs`:
- A pending reopen could replace text typed after its preview. Capture draft text, selected research level and state revision; clear on edits, and compare again at confirmation even if an input event was absent.
- A second failed reopen could leave the first confirmation target armed. Clear pending state before reading.
- Re-evaluate encoded version against current time/evidence at confirmation; do not use preview-time eligibility.
- Session continuity now preserves unapplied level as well as exact original draft, textarea selection direction/range and scroll. The reading position and withdrawn fixture sources remain preserved.
- Artificial validation and withdrawal controls move to the unified study settings in the mounted app. The regular workspace retains reading, editing, save/reopen and human review actions. Standalone adapter without a settings host retains a clearly labelled fixture section for test compatibility.

Six new minimal-DOM adapter regressions cover these transitions. Native focus/selection, touch, screen-reader and visual behavior remain unverified. The evidence and validations are self-authored fixtures; all product promotion, source authenticity and authenticated permissions remain UNBOUND. No extra demo count is claimed.
