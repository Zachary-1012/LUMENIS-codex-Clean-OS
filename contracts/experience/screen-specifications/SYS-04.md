# SYS-04 — Security and permission

```yaml
screen_id: SYS-04
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM Permission
binding_ids:
  - BACKEND-GAP-039
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: SYS-04 actor × product/domain × operation/risk boundary and §36.
- Product contract: UI displays posture only; the service Permission owner authorizes every consequential operation.
- References: `KEEP_AS_EXPLORATION`; raw policy expressions and enum metadata are not a second authority.
- Anti-template check: the composition is a permission matrix plus audit boundary, not a settings dashboard or effect console.
- Sol design decision: `DESIGN_EXPLORATION`.

## 1. User problem and product invariant

- Authorized context: operator permitted to inspect a safe security posture.
- Real task: understand the visible permission level and whether an audit decision is available without seeing policy internals.
- Completion signal: safe labels and scope states are readable; no screen action grants access.
- Out of scope: token/cookie/key/session display, policy expression display, permission mutation, and effect execution.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-04` → `experience_screens._build_sys04()`; current source enumerates `PermissionLevel`/`OperationType` metadata but does not return an actor-specific decision.
- Exit: return to SYSTEM context; no operation target route is bound.
- Return: preserve shell context only. Changing Subject context, if later provided by the shell, must not grant permission.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing/safety behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Safe access level | table row `权限级别/level`; allowlisted READ/TASK/AUDIT/WRITE/DEPLOY | Unknown values become “unconfirmed”; raw policy names are discarded | BACKEND-GAP-039; `sys04_snapshot.dart` |
| P0 | User-visible scope | row scope only as controlled/unknown state | Raw scope text is never echoed | Permission boundary |
| P1 | Operation count | `truth.operation_types` length only | Missing count is unavailable; operation names are not shown | Current SYS-04 builder |
| P1 | Audit availability | `truth.audit_available` only when explicit boolean true | Missing/false stays unavailable | BACKEND-GAP-039 |

The actual actor/target/risk Permission decision is unresolved in the current screen response and must not be inferred.

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | Posture read pending | Wait or leave |
| Empty / unknown | No safe permission row or decision returned | Show binding-unavailable/unknown |
| Partial | Some levels returned but audit or scope is absent | Read-only refresh; no authorization inference |
| Offline / error | Response unavailable or malformed | Retry bounded read; clear old state |
| Blocked | 401/403 | Follow access flow; do not expose policy internals |
| Ready | Safe posture fields are returned | No write/effect action |

## 5. Purpose-built desktop and web composition

- Desktop: a two-column matrix shows safe level/scope pairs; an audit panel explains server revalidation and operation count.
- Web Workspace shares the same safe projection; no effect control is shown.
- Tablet/mobile stack the matrix and audit explanation, keeping the scope label beside each level.
- No raw policy drawer, token inspector or operation button exists.

## 6. Purpose-built mobile composition

- One task: read the current access posture and its boundary.
- Each row pairs a level with controlled/unknown scope; audit availability follows.
- Back returns to the originating SYSTEM route; refresh re-reads without changing permission.

## 7. Actions, authorization and effects

| Action | Server owner and operation | Read/write/external effect | Evidence/failure |
| --- | --- | --- | --- |
| Read posture | SYSTEM Permission; existing GET currently has only global auth gap | Read only | 401/403/offline/error are distinct |
| Execute protected operation | Existing canonical Permission decision + effect fence, not this screen | Not implemented here | No control; no fake success |

## 8. Accessibility, motion and localization

- Matrix headers and row scope states have semantic labels; status is not color-only.
- Screen readers hear “access level” and “user-visible scope”, never raw policy expressions.
- No chart alternative is required; reduced motion avoids decorative transitions.
- zh-CN/en/ko copy must not expose implementation terms or secrets and must wrap on mobile.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS04-SAFE-01 | Unknown permission names are projected to unconfirmed | Snapshot/widget tests |
| SYS04-LEAK-01 | Secret/token/policy material does not reach rendered text | Adversarial snapshot/widget tests |
| SYS04-AUTH-01 | UI cannot turn context selection or enum metadata into authorization | Source review; backend Permission acceptance pending |
| SYS04-REAL-USER-01 | Authorized operator reads current safe posture and sees unknown where actor-specific decision is absent | Authenticated runtime E2E required |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; permission posture is not business coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no Subject/Brand entity sample is displayed, sample count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade to the incomplete actor/target decision binding. Any future control requires canonical Permission, Approval, Effect Fence, Audit and rollback.
- Decision: `DESIGN_EXPLORATION`; Sol must verify server-side authorization before acceptance.
