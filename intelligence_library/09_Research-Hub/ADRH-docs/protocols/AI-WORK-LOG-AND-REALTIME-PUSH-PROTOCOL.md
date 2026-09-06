# AI Work Log & Real-Time Git Push Protocol

> Protocol ID: HUB-PROTO-AI-WORKLOG-PUSH-V1
> Scope: ChatGPT / 豆包 / 自动化研发代理
> Nature: 增量工程纪律；不覆盖任何既有永久基线或仓库职责

## 1. Core Rule

**任务完成即收尾整理日志；日志整理完成即提交 Git；提交完成即立即 Push。**

GitHub is the traceable engineering ledger, not a periodic backup location.

The purpose is to prevent:
- quota exhaustion causing lost context;
- AI process interruption causing unknown work state;
- uncommitted local changes becoming invisible;
- duplicated work between ChatGPT and 豆包;
- claims of completion without a corresponding Git record.

## 2. What Counts as a Task Unit

A task unit is a meaningful completed action such as:
- Audit completed;
- Research case completed;
- Architecture review completed;
- Code implementation completed;
- Bug fix completed;
- Test run completed;
- Evidence collected;
- Documentation/protocol updated;
- Capability promoted or rejected.

Do **not** create a noisy commit for every keystroke or trivial intermediate edit.

## 3. Mandatory Closeout Sequence

At the end of every task unit, the executing AI must perform, in order:

1. **Summarize actual work** — what changed, what did not change.
2. **Record evidence** — test command/result, runtime, SHA, workflow/artifact where applicable.
3. **Record failures** — FAIL / WARN / BLOCKED / NOT VERIFIED must remain explicit.
4. **Record next action** — what the next agent/person should do; do not leave implicit context.
5. **Commit** — use a clear, scoped commit message.
6. **Push** — push immediately to the designated branch/repository.
7. **Verify remote state** — confirm the pushed commit exists remotely.

Only after step 7 may the task unit be considered closed.

## 4. Real-Time Rule

For a long-running task, do not wait until the entire multi-stage task is finished.

Push at every meaningful completed checkpoint, especially after:
- Audit;
- Research;
- Plan;
- Implementation;
- Test;
- Evidence;
- Review.

If a task is interrupted by quota exhaustion, process termination, network failure, or human pause, the **latest completed checkpoint must already exist in GitHub**.

## 5. Log Minimum Fields

Every closeout log must contain, when applicable:

| Field | Requirement |
|---|---|
| timestamp | UTC preferred |
| agent | ChatGPT / Doubao / Automation / Human |
| repository | exact repo |
| base_sha | SHA observed before work |
| commit_sha | resulting commit |
| task | concise task identifier |
| changed_scope | files/modules affected |
| tests | exact result |
| evidence | traceable source |
| status | PASS / FAIL / WARN / BLOCKED / NOT VERIFIED |
| next_action | explicit next step |
| handoff | what the other agent must know |

Never write an AI assertion as test evidence.

## 6. Dual-AI Handoff Rule

ChatGPT and 豆包 must treat the latest remote commit as the handoff boundary.

- ChatGPT finishes a task unit → log → commit → push → handoff.
- 豆包 finishes a task unit → log → commit → push → handoff.
- The receiving AI must read the latest SHA before continuing.
- If the remote SHA changed unexpectedly, stop and re-audit before editing.
- Neither AI may overwrite, squash, or silently replace the other agent's work.

## 7. Failure / No-Quota Rule

**Quota exhaustion is not an excuse for losing state.**

Before an AI stops because of quota, timeout, context loss, or other interruption, it must save the latest truthful state to Git whenever Git access is available.

If Git push itself is impossible, record the failure as `BLOCKED` / `NOT VERIFIED`; never claim the push succeeded.

## 8. Repository Separation

Logs must be written to the repository that owns the work or to the designated Hub evidence/log area.

Do not copy product source code into Hub merely to make logging convenient.
Do not copy Hub experimental code into production repositories.
Use references, SHA, Contract, and Adapter where cross-repository linkage is required.

## 9. Relationship to Existing Baseline

This protocol is additive only.

It inherits and must not weaken:
- the permanent three-party baseline;
- AI Intervention Development Protocol;
- repository responsibility boundaries;
- Research / Evidence / Review / Promotion gates;
- no-fabrication rule;
- no-core-copying rule.

If this protocol conflicts with a higher-priority permanent baseline, the permanent baseline wins and the conflict must be marked `BLOCKED`.

## 10. Operational Command

For every meaningful task completion, the executing AI should internally follow:

`WORK → VERIFY → LOG → COMMIT → PUSH → REMOTE VERIFY → HANDOFF`

This is a permanent operating rule unless explicitly superseded by a higher-priority immutable baseline.
