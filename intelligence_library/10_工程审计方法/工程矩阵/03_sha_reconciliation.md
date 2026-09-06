# 03 — SHA对账 (SHA Reconciliation)

> Verification: PASS (all SHAs from GitHub API list_branches and list_commits)

## 1. Branch HEAD SHAs

| Repository | Branch | HEAD SHA | Protected |
|---|---|---|---|
| ZBC | main | `bd6ed8d0bc50735c164455ea1a576ae7fc8e8897` | No |
| ZBC | feat/keyboard-shortcuts-modal | `a01d3017516840a5cf60d5f0917a08eb6d749b11` | No |
| ZBC | feat/zb-runtime-preflight | `5a716996757c883a780da54540ac7e059d78af90` | No |
| ZBC | research/context-intelligence-20260901 | `d2b12d9b755cd435fe5f9fda526f32f1934de2ec` | No |
| ZBC | research/zachary-ai-context-convergence-20260901 | `7b02f80fc1a64b36beaa52f8cae3ba5d3f31b59f` | No |
| ZBC | ui/staging-foundation | `580c2cf983560e4ca36d4c336261c3bd1a5cf373` | No |
| SICI | main | `c1b42bb6f7e286875d8a209018a89b69d8435b4f` | No |
| SICI | security/runtime-preflight-hardening | `74f416448efc45a93e23b2877fe20c4a80aaa5ce` | No |
| DCC | main | `b0de3c55e90d52c57a076e96a3d0e140f7ee1cb1` | No |
| DCC | security/runtime-preflight-hardening | `3bc3ab65994e8f2c8c246487fb39daea631b13dd` | No |
| AIDRH | main | `930c6468dcbfc424d5fc65559a27e55fed11bf6e` | No |
| AIDRH | ci/r7-secret-scan-fix | `f244437891402bab34f048f176dd725c196265de` | No |
| AIDRH | research/content-benchmark-expansion | `43f959e0df71a1c13b1152ff1970639f07cbc2e9` | No |
| AIDRH | research/content-benchmark-expansion-001~013 | `43f959e0df71a1c13b1152ff1970639f07cbc2e9` (all identical) | No |
| AIDRH | security/runtime-preflight-hardening | `f87f805f8d46d3aa16a04bfe27f1cf81f0379c12` | No |
| AIDRH | zachary-ai-consolidation-01 | `961e171209002694ff51e455a2d9c935e52403e3` | No |

## 2. Recent Commit Chain (main branch, latest 10 per repo)

### ZBC (main)
| SHA | Message | Author | Date |
|---|---|---|---|
| bd6ed8d | v5.8.9 自动保存版本（01:23 巡检） | Zachary-1012 | 2026-09-01T17:23:26Z |
| 32a313c | docs(handoff): 本地AI接入完成标记-qwen2.5:7b已验证 | Zachary | 2026-09-01T17:19:38Z |
| 8da122a | docs(governance): 会话接续清单20260902 | Zachary | 2026-09-01T16:56:06Z |

### SICI (main)
| SHA | Message | Author | Date |
|---|---|---|---|
| c1b42bb | docs: define full source audit and research specification | Zachary-1012 | 2026-09-01T16:28:59Z |
| 70892a7 | security: remove hardcoded demo credential from SICI README | Zachary-1012 | 2026-09-01T16:28:34Z |
| 17ad3a9 | docs: pin Zachary AI and ZBC immutable baseline | Zachary-1012 | 2026-09-01T16:27:47Z |
| feac1a2 | docs: sync comprehensive Zachary AI research development log | Zachary-1012 | 2026-09-01T16:14:54Z |
| f9991fc | test: verify runtime tool gate and ZBC evidence integration | Zachary-1012 | 2026-09-01T16:12:45Z |
| d0737d1 | feat: add permission-gated tool registry | Zachary-1012 | 2026-09-01T16:12:34Z |
| f9429c1 | feat: add read-only Z-Brand-Core evidence adapter contract | Zachary-1012 | 2026-09-01T16:12:22Z |
| a5b5c80 | feat: add unified Zachary AI runtime API | Zachary-1012 | 2026-09-01T16:12:12Z |
| d231116 | feat: add server persistence bridge contract for Zachary AI core | Zachary-1012 | 2026-09-01T16:10:08Z |
| 7c94694 | docs: establish executable Zachary AI development list | Zachary-1012 | 2026-09-01T16:09:55Z |

### DCC (main)
| SHA | Message | Author | Date |
|---|---|---|---|
| b0de3c5 | docs: define full source audit and research specification | Zachary-1012 | 2026-09-01T16:29:10Z |
| 12bc10c | docs: pin Zachary AI and ZBC immutable baseline | Zachary-1012 | 2026-09-01T16:28:11Z |
| bbdc50e | docs: sync Zachary AI and ZBC research development log | Zachary-1012 | 2026-09-01T16:14:38Z |
| f996154 | docs: define bidirectional Zachary AI and ZBC learning | Zachary-1012 | 2026-09-01T15:52:22Z |
| 9d4c66e | docs: synchronize Zachary AI consolidation positioning | Zachary-1012 | 2026-09-01T15:36:18Z |
| dd6a51f | audit(security): V0.5 Effective Rules + Supplement Protocol audit | Zachary-1012 | 2026-09-01T03:43:56Z |
| 8968ef3 | feat(server): V0.5 Effective Rules + Supplement Protocol + Capabilities API | Zachary-1012 | 2026-09-01T03:41:58Z |
| 2297b02 | test(security): Add Effective Rules + Supplement Protocol tests (43 new) | Zachary-1012 | 2026-09-01T03:31:16Z |
| 88bc787 | feat(security): Add Effective Rules resolver + Supplement Protocol manager | Zachary-1012 | 2026-09-01T03:30:02Z |
| fa3577a | feat(security): Effective Rules + Supplement Protocol P0 implementation | Zachary-1012 | 2026-09-01T03:28:39Z |

### AIDRH (main)
| SHA | Message | Author | Date |
|---|---|---|---|
| 930c646 | docs: define full source audit and research specification | Zachary-1012 | 2026-09-01T16:28:49Z |
| 1bcc295 | docs: pin Zachary AI and ZBC immutable baseline | Zachary-1012 | 2026-09-01T16:28:21Z |
| 31146e3 | docs: archive comprehensive Zachary AI and ZBC research log | Zachary-1012 | 2026-09-01T16:15:17Z |
| 7e659d4 | docs: track accelerated full Zachary AI integration | Zachary-1012 | 2026-09-01T16:13:55Z |
| 2dd6039 | docs: add bidirectional Zachary AI and ZBC learning contract | Zachary-1012 | 2026-09-01T15:51:35Z |
| 4e3ac90 | docs: track full Zachary AI integration status | Zachary-1012 | 2026-09-01T15:39:58Z |
| 8f47cd3 | docs: synchronize Zachary AI consolidation positioning | Zachary-1012 | 2026-09-01T15:36:01Z |
| 6c16fbc | logs: sync Zachary AI integration log | Zachary-1012 | 2026-09-01T08:26:27Z |
| c00335f | architecture: add executable Zachary learning data contract | Zachary-1012 | 2026-09-01T07:47:36Z |
| c923c01 | architecture: add governed Zachary learning promotion engine | Zachary-1012 | 2026-09-01T07:45:52Z |

## 3. Cross-Repo Coordinated Commits (same timestamp pattern)

The following commit messages appear across multiple repos within seconds of each other, indicating coordinated documentation pushes:

| Message Pattern | SICI SHA | DCC SHA | AIDRH SHA | ZBC |
|---|---|---|---|---|
| define full source audit and research specification | c1b42bb (16:28:59) | b0de3c5 (16:29:10) | 930c646 (16:28:49) | — |
| pin Zachary AI and ZBC immutable baseline | 17ad3a9 (16:27:47) | 12bc10c (16:28:11) | 1bcc295 (16:28:21) | — |
| define bidirectional Zachary AI and ZBC learning | 99fa98c (15:52:07) | f996154 (15:52:22) | 2dd6039 (15:51:35) | — |
| synchronize Zachary AI consolidation positioning | a3991b9 (15:36:36) | 9d4c66e (15:36:18) | 8f47cd3 (15:36:01) | — |

**Finding**: SICI, DCC, AIDRH have coordinated documentation commits. ZBC has separate commit cadence (auto-save pattern + handoff docs).

## 4. Branch Anomalies

| Repo | Branch | Issue |
|---|---|---|
| AIDRH | research/content-benchmark-expansion-001~013 | 13 branches all pointing to SAME SHA `43f959e0` — likely accidental branch proliferation |
| ZBC | feat/keyboard-shortcuts-modal | Feature branch, not merged to main |
| ZBC | feat/zb-runtime-preflight | Feature branch, not merged to main |
| ZBC | research/context-intelligence-20260901 | Research branch, not merged |
| ZBC | research/zachary-ai-context-convergence-20260901 | Research branch, not merged |
| ZBC | ui/staging-foundation | UI branch, not merged |
| SICI | security/runtime-preflight-hardening | Security branch (merged via PR? Need to verify) |
| DCC | security/runtime-preflight-hardening | Security branch (merged via PR #1 at b633ccb) |
| AIDRH | zachary-ai-consolidation-01 | Consolidation branch, not merged |

## 5. File SHA Cross-Reference (identical content across repos)

| File | SHA | Repos with identical SHA |
|---|---|---|
| ZBIP_DESIGN_TOKENS.css | `2210afc983ea7f97f75b1bc031d785b185abcb81` | SICI, DCC |
| (ZBC version differs) | `137a6f0eb028b009a3186baf2869c3621aa50296` | ZBC only |

**Verification**: PASS — All SHAs obtained via GitHub API. Branch proliferation in AIDRH is factual observation, not speculation.