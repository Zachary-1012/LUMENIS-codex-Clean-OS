# Research → Capability Pipeline

## Mandatory loop

```text
GitHub / papers / official docs / industry cases
        ↓
case record
        ↓
pattern extraction
        ↓
architecture fit / rejection
        ↓
own implementation experiment
        ↓
benchmark
        ↓
evidence
        ↓
domain validation
        ↓
cross-domain validation
        ↓
DCC gate
        ↓
Zachary capability candidate
```

## Non-copy rule

Research may use public projects to understand architecture, algorithms, failure modes, test strategies, data contracts, observability and governance. It must not copy source code, selectors, request signatures, credentials, proprietary data, platform security bypasses, or project-specific business logic.

## Required case record

- project/research name
- source URL or repository identity
- date reviewed
- license
- problem solved
- useful pattern
- known limitations
- security/legal concerns
- fit with Z-Brand
- rejected parts and why
- own implementation plan
- benchmark required

## Capability boundary

A pattern is not a Zachary AI capability merely because it works in Z-Brand. It must demonstrate generality beyond the originating domain and pass cross-domain validation.

## Collection-specific rule

Reliability work must improve legitimate, bounded collection and recovery. It must not attempt to defeat authentication, CAPTCHA, access controls, rate limits or platform security controls.
