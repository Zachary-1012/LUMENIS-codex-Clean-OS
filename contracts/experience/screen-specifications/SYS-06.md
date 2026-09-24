# SYS-06 — Internal browser capability

```yaml
screen_id: SYS-06
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM Browser / CDP
binding_ids:
  - BACKEND-GAP-041
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: controlled internal browser blueprint, separate personal browsing boundary, provenance and §36.
- Product contract: SYSTEM browser capability supports controlled acquisition; it is not a user personal browser and does not authorize collection effects.
- References: `KEEP_AS_EXPLORATION`; no external browser UI is copied.
- Anti-template check: capability boundary + safe instance state composition, not a browser tab clone or generic dashboard.
- Sol design decision: `DESIGN_EXPLORATION`.

## 1. User problem and product invariant

- Authorized context: SYSTEM operator allowed to read a filtered capability report.
- Real task: know whether controlled browser capacity is available and what read-only capability is bound.
- Completion signal: aggregate counts and safe instance states are shown; identity material remains hidden.
- Out of scope: personal browsing, credential/profile/session/port/path display, arbitrary CDP commands, social write actions and login automation.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-06` → `experience_screens._build_sys06()` → `browser_surface.capability_report()`.
- Current source may return identity/port fields; the Flutter projection reads only KPI values and state.
- Exit/return: originating SYSTEM route; no browser tab or snapshot action is bound.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Safety behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Controlled instances / online / read-only capability counts | KPI ids `sys06.instances`, `sys06.online`, `sys06.capabilities` | Ready integer only; unknown/offline is unavailable | BACKEND-GAP-041; `sys06_snapshot.dart` |
| P0 | Instance state | table row `state/状态` only | Account, port, profile, session and path fields are discarded | Browser Surface owner |
| P1 | Capability boundary | feature-local copy and current report state | No new-tab/snapshot/extract action is inferred | `browser_surface.py`; current builder |

Actor-to-browser-session authorization is explicitly unresolved in the current backend binding.

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | capability report pending | Wait or leave |
| Empty | no controlled instance returned | Show no-instance state; never show identity placeholder |
| Partial | aggregate counts or instance state missing | Keep unavailable distinct; refresh |
| Offline/error | report unavailable or malformed | Retry bounded read; clear old snapshot |
| Blocked | 401/403 or session scope denied | Follow access flow; no browser action |
| Ready | safe counts/states returned | Read only |

## 5. Purpose-built desktop and web composition

- Desktop/Web: capability summary sits beside filtered instance states; a boundary explanation names allowed read scope and unbound operations.
- Tablet/mobile stack summary and instance states; state text remains beside each instance.
- No browser viewport, credential inspector, port list or action toolbar is rendered.
- Any future browser action needs explicit target authorization, Permission, audit and Effect Fence.

## 6. Purpose-built mobile composition

- Single active task: inspect controlled capacity.
- Summary first, instance states second, safety boundary always visible.
- Back/return does not open a personal browser; refresh re-reads capability only.

## 7. Actions, authorization and effects

| Action | Owner/effect | Current behavior |
| --- | --- | --- |
| Read capability | Browser Surface GET; actor/session scope currently unverified | Safe projection only; 401/403/offline distinct |
| Open/snapshot/extract | Future Browser owner + Permission/effect fence | No control; unavailable/unbound |
| Social or account write | Explicitly out of scope | Never rendered or invoked |

## 8. Accessibility, motion and localization

- Aggregate metrics have semantic labels; instance state uses text, icon and color.
- Hidden sensitive fields are not present in the widget tree; screen reader cannot discover them.
- No browser visual capture or chart is shown.
- zh-CN/en/ko boundary copy wraps; reduced motion suppresses decorative state transitions.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS06-LEAK-01 | Account, port, profile, session and path fields never render | Adversarial snapshot/widget tests |
| SYS06-STATE-01 | Empty/offline capability does not become online or zero | Snapshot/widget tests |
| SYS06-BOUNDARY-01 | No personal browsing or write action is exposed | Source/widget review |
| SYS06-REAL-USER-01 | Authorized operator reads a real capability report and can distinguish controlled read scope from unbound action | Authenticated runtime E2E required |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; browser capacity is infrastructure, not global entity coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no business entity sample, count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade until actor-to-session authorization is scoped. Future acquisition improvements must preserve Source/Evidence/Canonical lineage and rollback.
- Decision: `DESIGN_EXPLORATION`; Sol must verify the browser authorization boundary and prohibited identities remain untouched.
