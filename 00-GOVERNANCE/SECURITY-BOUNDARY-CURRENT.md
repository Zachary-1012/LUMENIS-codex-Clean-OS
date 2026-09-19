# 序境安全边界 / Current Security Boundary

This document defines the security boundary that every 序境 product path must follow. It preserves the security layers formerly scattered through dated audit notes. It is a design and ownership contract; it does not claim that every control has passed implementation or production verification.

## Required layers

1. **Input Guardrails / 输入护栏** — validate and bound untrusted requests before they reach product actions.
2. **Identity and Permission / 身份权限** — authorize the actor, target, scope and requested effect through the canonical SYSTEM Permission owner.
3. **Execution Sandbox / 执行沙箱** — restrict tools, side effects, data access, retries and outbound operations to the approved action boundary.
4. **Output Guardrails / 输出护栏** — validate and label generated or transformed output before it is stored, shown, exported or used for an action.
5. **Observable Audit / 可观测审计** — record actor, decision, evidence, effect, outcome and failure in traceable security evidence.

## Current source owners

- Permission and action policy: lumenis/system/security/permission.py and lumenis/system/security/action_firewall.py.
- Side-effect boundary: lumenis/system/security/effect_fence.py.
- Product truth and Evidence: the canonical owners listed in 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md.
- API, model, output-validation and audit adapters must bind to these owners; they must not create parallel permission or action-policy truth.

## Acceptance rule

For each affected workflow, trace all five layers through its current source, API, data, Permission, Evidence, tests and runtime acceptance. Missing or unverified layers remain explicit blockers; a document, test file or archived audit is not proof of implementation.

Platform acquisition and interaction must respect the platform authorization context, account safety limits and the product permission boundary. Credentials are not shared across products.
