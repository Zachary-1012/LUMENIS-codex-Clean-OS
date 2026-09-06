# Human Control Gate v1

## Scope
Applies globally to all products and modules, with mandatory enforcement for KOS.

## Human-final-control actions
The following actions require human final approval before execution:
- external outreach and private messages
- email sending
- handling or exporting sensitive/non-public lead information
- commercial cooperation confirmation
- contract, quote, budget, or benefit confirmation
- paid-media creation, launch, recharge, budget changes, or publishing
- any action creating financial, legal, brand, privacy, or external-communication risk
- automated replies that contain commitments, commercial terms, or sensitive claims

## Allowed automation before approval
The system may discover, collect from permitted sources, analyze, rank, draft, prefill, recommend, validate, and prepare an execution task.

## Required state machine
AI_GENERATED -> PENDING_HUMAN_REVIEW -> HUMAN_APPROVED -> EXECUTING -> SUCCESS / FAILED

No shortcut from AI_GENERATED or AI_RECOMMENDED directly to SUCCESS/EXECUTING for gated actions.

## Truthfulness
Generated content is not sent content. A recommendation is not an execution. The UI and audit trail must distinguish generated, queued, sent, delivered, replied, accepted, completed, and failed.

## Data minimization
For lead/contact data, collect and retain only what is necessary and lawfully obtained. Non-public or sensitive personal information must be access-controlled and subject to appropriate review.

## Paid media
Recommendations may be automated; final account, budget, creative, launch, recharge, and material budget-change actions require explicit human approval.

## Audit
Every gated execution must retain the actor, approval timestamp, action payload/version, result, failure reason when applicable, and relevant Evidence.