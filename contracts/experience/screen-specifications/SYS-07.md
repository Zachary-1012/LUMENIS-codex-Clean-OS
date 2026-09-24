# SYS-07 — Evaluation and acceptance

```yaml
screen_id: SYS-07
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM Security / AI Gateway
binding_ids:
  - BACKEND-GAP-042
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: evaluation/acceptance blueprint and six-gate truth semantics; registration/configuration is not acceptance.
- Product contract: real result → Evidence → evaluation; PARTIAL/UNKNOWN cannot become PASS.
- References: `KEEP_AS_EXPLORATION`; fixture gates are not production evidence.
- Anti-template check: evidence posture, gates and returned checks form a review sequence, not a scorecard dashboard.
- Sol design decision: `DESIGN_EXPLORATION`.

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

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; evaluation posture does not assert commercial/brand/Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no entity values, sample count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade from registered-status display to acceptance. Promotion remains versioned, evaluated, approved, observable and reversible.
- Decision: `DESIGN_EXPLORATION`; Sol review and real Evidence-backed acceptance are pending.
