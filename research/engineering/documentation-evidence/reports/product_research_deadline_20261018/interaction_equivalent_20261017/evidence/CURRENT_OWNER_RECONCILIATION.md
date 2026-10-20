# Owner source reconciliation · 2026-10-17 13:23 UTC

The 13:21 demo freeze's research audit inspected the read-only remote-main archive, commit 4dab98ed6357133da9307de846180ed4f7bba5f5, at:
`recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main`.
It did not inspect the concurrently restored/modified product worktree. Those are different source snapshots. The phrase “actual current Owner” must not transfer archive observations to the modified tree or to a running server.

The current product working tree was subsequently read, without mutation, at:
`lumenis_working_20261017/source`.

| File | Frozen main archive SHA256 | Current working source SHA256 |
|---|---|---|
| lumenis/shared/learning/content_assets.py | 8ba2c3d3edc87e8b0a4a85fe10497be7c06accf77366d287c9e3a5d716070d7b | 02d0e570d0128af9a035a7ce7ae3a2ce6d1a379ed35939c0a0752a80fd630c10 |
| experience_runtime.py | 851a229d138bf6b0d2f2bd8067e04d6814d469471ab247f0c18be17c2f6affb4 | e2d740098bfcffe99e4da32206f2b5a187643102c1c4e4ec34fe5dd6a8886af5 |
| experience_screens.py | fc9602f7074f503e469deac31978cf30fc50d12ffa0dea8f379252134cb15775 | 278c897d84fceae39ed2d87ab55533b63f16e00b825b821bde64e0b9ab3bad70 |

## Concrete correction
- Archive `content_assets.py:268/278` defines `promote_pattern` and raises `CANONICAL_PROMOTION_GATE_NOT_CONNECTED`. The working-tree equivalents are at417/427 and still fail closed as of this read.
- Archive `experience_runtime.py:757` dispatches screens; the legacy data projection was in `experience_screens.py`, not a literal legacy implementation in the route itself.
- Archive `experience_screens.py:1331` BMP-08 reads podcast_store entities. **Current working BMP-08 has already changed**: line1508 calls `_bmp_content_project_screen("BMP-08", binding=binding, podcast=True)`, and runtime includes BMP-08 in its scope binding branch. The archive's legacy BMP-08 finding is not a current-working-tree defect claim.
- Archive SH-05 at1723 and current working SH-05 at1854 both show `get_learning_history` projection in this read. Further typed Learning/API integration is being independently checked by the product task. This document is not that task's runtime or test result.

No product code was changed or executed by this reconciliation. Demo71 remains an independent local review with productPromotion UNBOUND regardless of how the product task closes its Owner. Demo contracts must be reconciled with the resulting actual interface before binding; local tests do not prove production promotion or permissions.

The original13:21 freeze is immutable and retained for reproducibility. This explicit correction belongs to subsequent working documentation and accompanies any backup summary of that freeze.
