# SYS-07 — Evaluation and acceptance

```yaml
screen_id: SYS-07
status: DESIGN_EXPLORATION
revision: 2
owner_domain: SYSTEM Security / AI Gateway
binding_ids:
  - BACKEND-GAP-042
product_owner_approval: APPROVED_FINAL_RELEASE_TARGET_2026-10-07
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: M target-convergence review
reviewed_at: 2026-10-07
approval_reference: Product Owner-approved final product closure requires same-SHA Product/App/Critical E2E, packaging/runtime/user-repeat/release evidence; current builder remains incomplete
```

## 0. Authority basis and artifact disposition

- Constitution basis: evaluation/acceptance blueprint and six-gate truth semantics; registration/configuration is not acceptance.
- Product contract: real result → Evidence → evaluation; PARTIAL/UNKNOWN cannot become PASS.
- References: `KEEP_AS_EXPLORATION`; fixture gates are not production evidence.
- Anti-template check: evidence posture, gates and returned checks form a review sequence, not a scorecard dashboard.
- Sol design decision: `DESIGN_EXPLORATION`; the current builder remains a bounded read-only slice.

## 0.1 Approved final release-evidence target — 2026-10-07

SYS-07's final product role is to make release truth legible. It consumes existing C6/M release evidence and does not itself run acceptance actions or change release state.

Final evidence order:

```text
candidate source SHA
→ source/config/DB/Experience checks
→ Product Gate
→ App Gate
→ Critical E2E
→ package/build artifact where promised
→ loaded runtime identity matches the accepted release composition
→ rollback/recovery evidence
→ Product Owner repeats the core job
→ RELEASED
→ real elapsed operating evidence
→ OPERATING
```

Each stage reports PASS / FAIL / NOT_RUN / UNKNOWN / STALE with exact evidence, time and SHA when available. An earlier green stage never hides a later missing stage. Evidence from different SHAs stays visibly separate until the accepted release composition proves them compatible. Source presence, a build, or an HTTP response alone is not release.

Public Website, Web Workspace, Desktop and Mobile keep distinct release roles. Only actually published/supported packages are shown as downloadable; unavailable packages remain explicitly unavailable.

## 1. User problem and product invariant

- Authorized context: SYSTEM/security operator reading returned evaluation checks.
- Real task: see which checks actually returned and whether evidence-backed production gates are complete.
- Completion signal: unknown/incomplete posture stays visible; no acceptance pass is claimed from registered skills or OWASP count alone.
- Out of scope: executing tests, promoting skills, changing AI policy, autonomous approval, or declaring release.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-07` → `experience_screens._build_sys07()` → `ai_governance.get_owasp_security_status()` and `get_skills_light_status()`.
- Current source returns enabled checks and skill light status, not a complete production gate record.
- Return: originating SYSTEM route; no promotion or release route is bound.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing-data behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Returned OWASP checks | table rows from `checks_enabled` | Empty remains no verifiable check; no pass inference | BACKEND-GAP-042; `ai_governance.py` |
| P1 | OWASP/skill counts | KPI ids `sys07.owasp_checks`, `sys07.skills` | Only `ready` numeric state displays a value; empty 0 is not fabricated | Current SYS-07 builder |
| P0 | Acceptance gates | No current verified gate section in builder | Screen stays UNKNOWN until real gate + evidence rows arrive | Evaluation owner |
| P1 | Evidence reference | Only explicit safe reference fields | Missing evidence is not a pass | `sys07_snapshot.dart` |

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | checks pending | Wait or leave |
| Empty | no checks/gates returned | Show unknown/no data |
| Partial | checks returned but gates/evidence incomplete | Keep “no PASS conclusion”; refresh or follow evidence workflow outside this page |
| Offline/error | read failed or malformed | Retry bounded GET; clear old state |
| Blocked | 401/403 | Follow access flow; no promotion action |
| Ready | checks returned | Still not production acceptance until complete gate evidence exists |

## 5. Purpose-built desktop and web composition

- Desktop/Web: posture rail makes the acceptance boundary explicit; returned checks and evidence-backed gates occupy separate review panels.
- Tablet/mobile stack posture → gates → checks; no pass badge is shown from count alone.
- No score, release button or trend chart is rendered without a canonical callable.

## 6. Purpose-built mobile composition

- One active question: “what evidence is actually present, and what remains unknown?”
- Posture stays first; every gate/check shows state and evidence reference or not returned.
- Back/refresh is safe and read-only; no evaluation mutation occurs.

## 7. Actions, authorization and effects

| Action | Owner/effect | Current behavior |
| --- | --- | --- |
| Read checks | SYSTEM Security / AI Gateway GET | Read only; access failures are distinct |
| Approve/promote/release | Evaluation/Permission owner, not this screen | No control; no autonomous effect |

## 8. Accessibility, motion and localization

- Unknown, partial and ready states are textual and semantically announced.
- Evidence references are readable text; no chart alternative is needed.
- Long check names wrap; zh-CN/en/ko copy keeps the “not PASS” boundary explicit.
- Reduced motion avoids animated pass-like celebrations.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS07-UNKNOWN-01 | Missing acceptance gate evidence remains UNKNOWN | Snapshot/widget tests |
| SYS07-NO-PASS-01 | OWASP/skill registration does not become production acceptance | Snapshot/widget/source tests |
| SYS07-EVIDENCE-01 | A gate is not complete without explicit evidence and ready/pass result | Future contract test; current screen fails closed |
| SYS07-REAL-USER-01 | Operator reviews a real check and sees exactly why production acceptance remains incomplete | Authenticated runtime E2E plus evaluation Evidence required |
| SYS07-SHA-02 | Product/App/Critical/runtime/package evidence carries its actual SHA/version; different SHAs remain visibly separate until an accepted release composition proves compatibility | Future release-evidence contract + widget test |
| SYS07-LADDER-02 | PASS/FAIL/NOT_RUN/UNKNOWN/STALE are shown for every promised release stage; an earlier PASS never hides a missing later stage | Future widget/contract test |
| SYS07-RELEASE-02 | RELEASED requires the accepted release composition plus applicable package/runtime/rollback and Product Owner repeat evidence; OPERATING requires later real operating evidence | Future same-release E2E + Product Owner acceptance |
| SYS07-SURFACE-02 | Public Website/Web/Desktop/Mobile show only their actually promised package/runtime state; an unavailable installer is not fabricated or borrowed from another surface | Future cross-surface release E2E |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; evaluation posture does not assert commercial/brand/Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no entity values, sample count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade from registered-status display to acceptance. Promotion remains versioned, evaluated, approved, observable and reversible.
- Decision: `DESIGN_EXPLORATION`; Sol review and real Evidence-backed acceptance are pending.
