# AI Coding — Multi-AI + Local Control Architecture

Status: ACTIVE ARCHITECTURE BASELINE

## 1. Objective
Move code authorship, workspace state, repository truth, execution and learning into the user's own system. External AI providers (currently including Zhipu and Doubao) are model/verification resources, not the permanent home of source code.

## 2. Target evolution

```text
Stage 1 — External-assisted local execution
User System
  -> Coding Workspace
  -> Local Sandbox / Runner
  -> External AI (Doubao / Zhipu / other approved models)
  -> Proposal / Patch
  -> Local execution + tests
  -> Human approval
  -> Git

Stage 2 — Multi-AI collaborative coding
User System
  -> Orchestrator
  -> Model Router
      ├─ Zhipu
      ├─ Doubao
      └─ approved models
  -> independent review / critique
  -> Local Sandbox
  -> Tests / Audit
  -> Human approval
  -> Git

Stage 3 — Native local control
User System
  -> Native Coding Agent
  -> Local Model(s)
  -> Local Sandbox / Runner
  -> Tests / Audit
  -> Human approval
  -> Git

External models become optional fallback / benchmark / second-opinion providers.
```

## 3. Non-negotiable ownership
- Source code lives in the user's repository/workspace.
- Execution happens in a controlled local/owned sandbox where possible.
- External AI receives only the context necessary for its task.
- External AI must not become the system of record.
- Learning assets are retained locally as approved engineering knowledge.
- No model may silently alter canonical functionality.

## 4. AI roles

### Builder
Generates or proposes code changes.

### Reviewer
Independently reviews architecture, correctness, security, tests and regression risk. Zhipu can serve as an external review/model role when connected.

### Executor
Runs code/tests in the controlled environment. Doubao is currently an external execution-assistance interface where applicable; the execution environment itself remains owned by the system.

### Orchestrator
Selects model/role, supplies context, collects outputs, resolves disagreements and manages task state.

### Learner
Extracts reusable engineering patterns only from accepted outcomes, tests and human corrections.

## 5. Model independence
The system must not hard-code one provider as its architecture. Provider adapters must expose a common contract:

`Task -> Context -> Model -> Proposal -> Validation -> Result`.

Provider failure must degrade gracefully to another approved model or manual execution.

## 6. Code safety gate
Every proposed change is classified before application:

```text
Bug fix / security / stability / test / refactor / UI implementation
        -> may proceed through normal gate

Potential functionality change
        -> BLOCK -> human confirmation required
```

The existing product functionality is frozen. Architecture may improve only when behavior, business semantics and expected outputs remain compatible, unless an explicit product decision authorizes a feature change.

## 7. Learning loop

```text
Task
 -> Context
 -> AI Proposal
 -> Local Diff
 -> Tests
 -> Runtime Evidence
 -> Human Review / Correction
 -> Accepted Commit
 -> Learning Asset
 -> Pattern / Rule / Retrieval Index
 -> Future Task Context
```

Rejected or unsafe proposals must not automatically become learning truth.

## 8. Security / permissions
Coding Agent should use least privilege. Separate read, propose, execute, write and deploy permissions. Production deploy must remain a distinct approval boundary. Secrets are never included in model context unless an explicit secure mechanism requires them.

## 9. Migration rule for Doubao
Doubao is not to be abruptly removed. First make the internal Coding Workspace independent of the provider; then benchmark native/local execution against the current workflow. Only when native/local capability meets agreed correctness, stability, test and productivity thresholds may Doubao be demoted to fallback/benchmark or removed.

## 10. Migration rule for Zhipu
Zhipu is a complementary external model/reviewer/provider. Its role is to strengthen independent verification and model diversity, not to replace local repository truth.

## 11. Final desired state

```text
                 OWNED SYSTEM
                      │
             Coding Orchestrator
                      │
          ┌───────────┼───────────┐
          │           │           │
       Local AI    External AI  External AI
          │        (Zhipu)      (Doubao)
          │           │           │
          └───────────┼───────────┘
                      ↓
               Consensus / Review
                      ↓
               Local Sandbox
                      ↓
               Test / Audit
                      ↓
                Human Gate
                      ↓
                    Git
                      ↓
               Learning Assets
                      ↺
```

The strategic endpoint is not “replace Doubao immediately”; it is “remove provider dependency by moving orchestration, code ownership, execution, validation and learning into the user's system.”

## 12. Acceptance criteria before external-provider retirement
- Native/local coding agent can inspect repository context reliably.
- Can generate/apply patches safely.
- Can run required tests and capture evidence.
- Can detect and stop suspected functionality changes.
- Can preserve Git history and produce reviewable diffs.
- Can recover from failed execution.
- Can learn only from accepted outcomes.
- Meets or exceeds the baseline productivity/stability metrics established from the current Doubao-assisted workflow.

Until all criteria pass, external providers remain available as controlled collaborators/fallbacks.
