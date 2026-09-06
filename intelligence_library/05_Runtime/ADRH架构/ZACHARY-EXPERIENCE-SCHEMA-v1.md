# Zachary AI Experience Schema v1

## Purpose

Define the minimum evidence-bearing unit that Zachary can learn from during internal maturation. An experience is not a memory dump and not automatically a capability.

## Experience object

```text
experience_id
product_id
domain_id
task_id
session_id
observed_at
source_type
source_ref
input_context
user_intent
constraints
action_taken
reasoning_summary
outcome
outcome_metrics
feedback
failure_or_success
candidate_pattern
counter_pattern
confidence
provenance
valid_from
valid_until
privacy_scope
capability_class
promotion_status
```

## Evidence rule

An experience is only eligible for learning when provenance and scope are known. AI-generated synthetic examples may be used for testing, but must never be represented as real-world evidence.

## Separation

Experience records remain domain-scoped by default. A candidate pattern may be abstracted from the record, but product implementation details remain domain-bound.

## Outcome model

Prefer observable outcomes over subjective labels. Examples include task completion, engagement, conversion, correction rate, latency, user feedback, acceptance/rejection, or other domain-appropriate measures.

## Pattern extraction

```text
Experience
 -> Pattern candidate
 -> Counterexample search
 -> Domain verification
 -> Cross-domain test if generalization is proposed
 -> Evidence
 -> Promotion decision
```

A pattern without counterexample analysis must not be treated as a universal rule.

## Conflict handling

When two experiences conflict, preserve both records and resolve at reasoning time using context, provenance, temporal validity, confidence and domain scope. Do not overwrite historical evidence merely to make the memory consistent.

## Privacy and authorization

Private product data, credentials, identifiers, customer information and restricted content must remain within their authorized domain boundary. Learning extracts must remove unnecessary private implementation details.

## Lifecycle

`OBSERVED -> CANDIDATE -> VERIFIED-DOMAIN -> TRANSFER-CANDIDATE -> VERIFIED-CORE -> RETIRED/REPAIRED`

Retirement does not delete provenance; it marks an experience or learned pattern as no longer valid for future use.
