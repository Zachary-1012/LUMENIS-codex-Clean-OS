# C3 — source-bound creation to business-work E2E

> Status: **LIVE_VERIFIED for the bounded internal Core/API path; not USER_VERIFIED, RELEASED, OPERATING, or commercial acceptance.**
>
> Operation-time checkout was `c57efa29f8d28fb98664fbfeee618b4f6c531a2f`. The Core process started at 2026-10-05 17:14 +08:00; the API/domain source files used by this path were last changed together at `be347f03eb9f2bc470a39644df281be3a3d704c9` (2026-10-04 21:15 +08:00). Runtime did not expose a loaded Git SHA. Later commits `1ab4d1a8` and `c57efa29` only changed documentation.

## Scope and real input

- **Real user job:** turn one focused CTH Source Brief into a
  saved, editable internal operating-review document; record an operator's
  internal review decision; retain an honest unknown business outcome.
- **Entry:** current Core at `127.0.0.1:8201`, scoped local-workspace principal,
  focused CTH Subject. The server resolved the actor, source scope and
  permission receipts; the client did not supply an actor, scope, source receipt
  or Artifact receipt.
- **Source Brief:** `brief-350d84ee6a4b4519ab8815837a49b997`, with 29
  records passing the current signed source/scope checks and report hash
  `55d7114b8512a8d4ac2abe59b1f64ad8e2c486d769ee66a4af9361662dc2bf00`.
  The same snapshot reports collection state, coverage and freshness as
  `UNKNOWN`. This record identifies a valid scoped source chain. It does not
  assert that all underlying material establishes consumer demand, commercial
  performance, rights for training, or causation.
- **No protected material is reproduced here:** no source body, URL, cookie,
  account, private database value, or personal session was copied to Git.

## Actual path and receipts

```text
Focused Source Brief
  -> source-bound/v3 internal-pitch task
  -> committed SavedWork + DOCX attachment
  -> CTH BusinessDecisionWorkflow prepare/choose/action
  -> outcome UNKNOWN + Evaluation record
  -> fresh business-work reopen and DOCX export
```

| Step | Observed result |
| --- | --- |
| Source-bound creation | Task `task-pitch-ad4fa59c9457df95ba8558c2` reopened in `succeeded` state. Its contract is `lumenis.internal-pitch` v3 and its upstream binding is the Source Brief above. |
| Saved result | Committed receipt `ART-5f83533e37194b6b`, version `1`, SHA-256 `7aad329d310388ac8e8cdd538b624d5665231a0f4e697306928166f9fdb59160`, 39,927 bytes. |
| User-visible export | Attachment `ART-c5683ff5c1c74db5`, DOCX, SHA-256 `36ecea297d181c420127adf8c94f1d1ff6694807f97ca5d86a1b390b9cb8d3af`, 37,525 bytes. Fresh export returned the same media type, byte count and response hash. |
| Business decision | Work `work-c70fb7378072364b43fa00f7448bf9f705531831f6be8ae39b777a4dda8eb028` was prepared from the exact Source Brief, selected an internal-review proposal, and linked only the committed task above. |
| Operator input boundary | The local workspace principal submitted the review selection. `owner=LUMENIS local workspace operator` and the future `review_at` were engineering exercise inputs, not a Product Owner assignment, user decision, or real calendar commitment. This operation is **not USER_VERIFIED**. |
| Action boundary | `action_state=EXECUTED` means the existing committed internal document was freshly re-read and associated with the selected internal review. It does **not** mean a campaign, purchase, publication, platform operation or other external effect occurred. |
| Outcome and evaluation | `state=OUTCOME_RECORDED`; `business_outcome=UNKNOWN`; `outcome_state=UNKNOWN`; evaluation `business_decision_usefulness=UNKNOWN`; current revision `app_evidence_records:494`. |
| AI honesty | `owned_analysis=UNAVAILABLE / OWNED_RUNTIME_NOT_BOUND`. No model output was used to claim that the operator decision or business result was completed. |
| Recovery/readback | Fresh `GET /api/experience/business-works/<work_id>` returned the exact terminal business-work result. The source-bound pitch and DOCX were reopened/exported without creating another version. |
| Runtime | `GET /healthz` returned HTTP 200, `healthy`, and database `ok`; TCP listener was on 8201. Process ancestry matched one supervisor tree plus its Windows launcher/interpreter children, not two independent supervisors. Runtime did not expose a loaded Git SHA. |
| DOCX integrity/readability | Reopened export hash matched the committed attachment SHA and byte count; 9 non-empty paragraphs decoded as valid Unicode with no replacement characters. The content states the source, scope and no-effect limits. |

## Result boundaries

This proves one current Core/API path in which the same focused source result
remains bound while work moves from research to a saved document and then to a
recorded business review. It also proves that the normal path preserves an
unknown outcome rather than inferring performance from source existence or
internal document creation.

It does **not** prove a Flutter/Desktop/Mobile user operation, a customer
acceptance test, source withdrawal/revision handling, a measured external
outcome, owned-model usefulness, full six-platform collection coverage, or
release/operating/commercial readiness. The operator fields above must not be
shown as an actual Product Owner assignment or schedule. Those remain separate
acceptance gates.

## Next owned work

1. Exercise the existing changed-source/version-adoption path with a real
   permitted change when it occurs; do not fabricate a source or budget change
   merely to create another version.
2. Bind the same result through the promised four product surfaces and complete
   the corresponding recovery/user-operation acceptance.
3. Replace the owned-analysis unavailable state only after the C2 approved
   training, serving, held-out evaluation and promotion gates have real evidence.
