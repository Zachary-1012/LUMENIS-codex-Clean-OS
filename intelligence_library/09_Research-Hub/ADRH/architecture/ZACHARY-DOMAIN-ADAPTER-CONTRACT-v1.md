# Zachary AI Domain Adapter Contract v1

## Purpose

Provide a controlled bridge between the independent Zachary core and a product domain without coupling Zachary to that product's architecture.

## Adapter boundary

```text
Zachary Core
    |
    | generic request / result contract
    v
Domain Adapter
    |
    +-- domain context
    +-- authorized capabilities
    +-- data access policy
    +-- tool mapping
    +-- domain rules
    +-- output normalization
    v
Product Runtime
```

## Required fields

Every adapter invocation must declare:

- `product_id`
- `domain_id`
- `task_id`
- `session_scope`
- `requested_capability`
- `capability_class`
- `authorized_tools`
- `authorized_data_sources`
- `input_context`
- `output_contract`
- `provenance`
- `time_validity`

## Isolation requirements

An adapter MUST:

1. expose only explicitly authorized product capabilities;
2. prevent direct access to unrelated product domains;
3. prevent product implementation details from becoming core memory;
4. prevent product permissions from transferring to another domain;
5. preserve provenance of domain-derived knowledge;
6. identify domain-bound outputs;
7. reject requests outside its authorization scope;
8. support audit logging sufficient to reconstruct what Zachary accessed and why.

## Learning boundary

The adapter may return experience and outcome evidence to Research-Hub. Returned evidence must be labeled by domain and provenance.

```text
Product-specific result
      -> Domain Evidence
      -> Candidate Learning
      -> Cross-domain validation
      -> possible CORE-GENERAL capability
```

The adapter itself must never promote a capability to global status.

## Generalization rule

If Zachary discovers a reusable pattern while working through an adapter, only the abstract pattern may become a transfer candidate. The following remain domain-bound unless separately authorized and validated:

- product architecture
- database/schema
- UI structure
- business rules
- internal identifiers
- permissions
- private data
- product-specific workflows
- product-specific terminology

## Failure handling

If domain context is missing, ambiguous, stale or conflicting, the adapter must fail closed or request clarification rather than guessing the domain.

If a requested capability is not authorized, the adapter must not silently substitute another product's capability.

## Multi-product rule

Zachary may concurrently serve multiple products, but each invocation has an independent domain scope. No adapter may read or write another adapter's domain state unless an explicit, audited cross-domain contract exists.

## Future standalone extraction

When Zachary becomes a standalone product, existing domain adapters remain optional integration boundaries. They must not be folded into the Zachary core merely because they were used during maturation.
