# Research Learning Database — DDC

This is the engineering-side contract for the shared Research Hub. It is intentionally additive to the permanent three-repository baseline.

## Record lifecycle

```text
research → experiment → shadow → evidence → review → verified → promoted
                         └──────────────→ hold / rejected
```

`verified` and `promoted` require explicit Evidence references. AI confidence is never Evidence.

## Minimum record

Every record must contain:

- `id`
- `record_type`
- `created_at`
- `source`
- `owner`
- `summary`
- `status`

When a claim concerns repository code, record `repository` and the observed `commit_sha`.

When a capability is verified, record `evidence_refs` and applicable `test_refs`.

## Privacy boundary

Learning records must never contain credentials or sensitive session material. The implementation redacts common credential keys including token, password, cookie, secret, and API-key fields.

## Promotion rule

Promotion is a decision, not a side effect of writing a record. The current tool validates the evidence prerequisite but deliberately does not auto-promote code or permissions.

## Shared-Hub integration

The future `AI-Development-Research-Hub` is the cross-product research workspace. DDC owns the engineering validation semantics. Z-Brand owns business/production applicability. SICI owns mobile interaction and device/workflow applicability.

The Hub should consume this contract through versioned adapters rather than importing DDC internals.
