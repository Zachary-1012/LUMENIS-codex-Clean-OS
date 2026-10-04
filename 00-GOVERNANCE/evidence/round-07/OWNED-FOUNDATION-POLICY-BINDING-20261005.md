# Owned foundation policy binding — 2026-10-05

## Integrated static binding

`config/ai-owned-foundation.json` is the existing SYSTEM AI Gateway foundation
manifest. This update binds its checked-in recipe and checkpoint-recovery
policy material to the already tracked training and recovery code:

- `unsloth-rtx4090-nf4` is pinned to its exact Ada compatibility policy;
- `unsloth-rtx5090-nf4` is pinned to its exact Blackwell compatibility policy;
- two immutable Blackwell checkpoint policies are registered by their canonical
  policy SHA-256; and
- the checked-in manifest is covered by a static test that loads each policy
  through the real recovery-policy resolver.

The manifest raw SHA-256 is
`8139a5398fcdcd34103dd94d1e0cb54f0196f9a826b234317451ac58d553a666`.
The two local, private runtime profiles already require that same manifest hash.
Those profiles are not source, were not modified, and were not executed.

## Verification

- Static manifest-policy test: `1 passed` using an external read-only SQLite
  backup solely to seed a disposable pytest DB.
- Existing tracked training-review resource route test: `15 passed` using the
  same disposable seed mechanism.
- Direct resolver readback reconstructed both exact checkpoint recipe identities.

## Boundaries and next gate

This change starts no GPU, model, SSH endpoint, model download, trainer,
inference, promotion, or paid resource. Both GPU recipes remain
`APPROVED_COMPATIBILITY_NOT_LIVE_VERIFIED`.

Before any later user-authorized compute is charged, the normal path still
requires a verified current runtime endpoint, remote preflight, model-file
availability, one actual load and optimizer step/loss, physical checkpoint
retrieval/reload, held-out evaluation, a useful owned CTH/BMP or creation result,
and controlled promotion/rollback evidence. None of those states is established
by this static policy binding.
