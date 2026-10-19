# Formal toolchain: static-only preflight addendum

## Result
The official fixed-pin challenge/configuration is now readable. No Lean, Lake, Comparator, landrun, exporter, cache download, build hook or foreign script was run. The current external Comparator documentation introduces a version and sandbox compatibility issue that must be resolved before any replay proposal is approved.

## Exact fixed target
Repository `openai/math`, commit `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.
- `lean/lean-toolchain`: `leanprover/lean4:v4.34.1`; Git blob ba8ebf2dbaf6a668cd2a0e086186d6d569b69ff5.
- `lean/lakefile.lean`: blob 66c3867331c7c607ffc0e60955cc86cccf046e12; entire file read statically.
- mathlib exact revision d13f23b723b8a846827a245b89c10fc7d3f11612. The manifest has further transitive pins; its acquisition is not a review of all dependencies.
- `ComparatorChallenges/MatchingEntropyBounds.json`: blob 8fd1cd5705944e3b6c3b10191840da295d1b29d1. Challenge module ComparatorChallenges.MatchingEntropyBounds; solution OAI.Combinatorics.MatchingEntropy.Main; theorem OAI.MatchingEntropyBounds.Refined.pointwise_entropy. No definition holes. Permitted axioms exactly propext, Quot.sound, Classical.choice. `enable_nanoda=false`.
- Challenge Lean blob 872b7b216a1290086b3cf2adb965cdb3b6210b30 was fully read. Finite loopless labeled multigraph, 2m vertices, m>0, existing perfect matching, x in matching polytope. Entropy is sum Real.negMulLog; maxMatchingEntropy is supremum over probability laws with prescribed mean. Claimed bounds: entropy(x)-(2-2/m)*complementEntropy(x) <= maxMatchingEntropy <= entropy(x).
- The challenge ends in `sorry`, intentionally representing the statement to be matched. That is not evidence that the solution proof contains sorry. Conversely, the challenge declaration alone proves nothing.
- Solution Main blob 454ca68b88c8165cb428d8090d681fb1ed208f29 contains an import and documentation, not the theorem proof. It imports ExpansionSequences (blob 4b0de3427e9055cd264f80e67aa2ffe5caeebea8), which imports EightVertex. ExpansionSequences was acquired and its import/tail inspected, not fully proof-reviewed. The remaining solution and Mathlib import closures remain unreviewed. No absence-of-axioms claim is made.

## Side effects hidden in configuration elaboration
`lakefile.lean` declares many Git dependencies and a default target spanning the OAI library. The pre-resolution `run_cmd` evaluates dependency declarations, checks full lowercase 40-character pins, origin and checkout, then may clone eleven dependencies into staging, detached-checkout their pins, apply local compatibility patches, rename staging and remove temporary directories. This occurs before dependency resolution, not only after explicit build targets. `post_update` verifies those eleven and checks/applies patches to twelve more packages. Reverse applicability is used as the already-applied check. All these actions mutate an environment and may access the network.

Therefore even a seemingly informational Lake command that elaborates this configuration is outside the current static-only authorization. Patch bodies and all third-party build hooks still need review. The recommended README commands `lake update` and `lake exe cache get` were not executed. The whole-library mmap warning is a resource warning, not permission to change vm.max_map_count or system settings.

## Official Comparator upstream, separate version
[Official upstream README](https://github.com/leanprover/comparator/blob/master/README.md), retrieved 2026-10-17 19:43 UTC, blob a905f99fbf8dd6e1031363932d3c8b240e30e883. A first request for `main` returned “No commit found for ref main”; normal `master` reading succeeded. This was a nonexistent branch, not an access denial. This moving upstream branch is separate from the pinned math artifact and does not silently upgrade it.

The upstream states that Comparator moved into Lean core as `lake comparator`/`lake check` in v4.35.0 and recommends migration. That cannot be assumed compatible with the pinned v4.34.1 project. The math README does not pin the external comparator/landrun/exporter versions. Compatible immutable versions and trusted binary provenance are unresolved.

The official threat model requires a trusted challenge import closure and Lake config, no prior unsandboxed compilation of adversarial solution code in the checking environment, correct landrun isolation, a compatible exporter, kernel correctness and a nonprivileged user. Its current invocation uses an additional systemd restriction of AF_UNIX and describes a landrun vulnerability expected to be fixed in Linux 7.1. We did not independently audit that vulnerability or test this host's mitigation capability. It is a documented preflight risk, not a claim that this host is compromised.

The README's `fake-landrun.sh` is explicitly a development substitute. It is unsuitable for security-bearing validation. Optional external kernels require explicit configuration; this challenge disables nanoda. A successful ordinary compilation would not replace statement-equivalence, allowed-axiom and kernel-replay checks. Definition holes require additional interpretation review; this target currently has none.

## Narrow replay plan requiring separate authorization
1. Freeze the exact challenge, solution import closure, patch files, toolchain, manifest and external verifier tool commits. Review every executable build/configuration hook before invoking it. Preserve the original allowed axioms and theorem statement.
2. Choose either a compatible v4.34.1 external Comparator path with independently reviewed mitigations, or a separately reviewed migration experiment. Do not rewrite the fixed evidence to pretend a new toolchain is the same replay.
3. Use a fresh unprivileged isolated environment with no production files/credentials, restricted network and no prior untrusted compiled artifacts. Verify real sandbox properties without fake-landrun. Any network/security-setting change needs its own authority.
4. Measure disk/RAM/core/time requirements for this one import closure. Set explicit limits and record RESOURCE_EXHAUSTED without inflating limits invisibly. Do not default-build the full library.
5. Preserve stdout/stderr, exact command, versions, hashes, exit status, theorem equivalence, transitive allowed axioms and kernel result. Include deliberately mismatched statement/extra-axiom negative controls in a separate fixture, never by weakening the real challenge.

G164 remains OPEN. The verified target is a matching entropy inequality, not the general matching FPRAS, all nine families, or either newly read manuscript. No current evidence supports “all papers formally proved.”
