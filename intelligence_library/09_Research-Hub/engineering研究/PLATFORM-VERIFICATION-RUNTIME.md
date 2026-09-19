# Zachary AI Platform — Verification Runtime Contract

Status: **ACTIVE DELIVERY STANDARD**

This document operationalizes the immutable platform baseline. It does not replace repository-specific tests or production controls.

## 1. Purpose

Provide a reproducible, low-dependency verification environment so the platform can validate code without requiring continuous external AI execution.

## 2. Controlled path

```text
GitHub repository
  ↓
fixed commit SHA
  ↓
Dev Container / isolated runtime
  ├─ Node.js 20+
  ├─ Python 3.12+
  ├─ SQLite
  └─ PDF/reportlab support
  ↓
repository-native tests
  ↓
E2E where the repository provides a real E2E runner
  ↓
failure classification / localization
  ↓
Evidence
  ↓
GitHub Actions
  ↓
release gate
```

The browser-only SICI E2E simulator is explicitly a simulation; it must not be represented as real browser automation. A real browser E2E run requires a Playwright/Puppeteer/backend runtime or equivalent controlled executor.

## 3. Verification facts

Every material verification record should capture:

- repository
- branch
- fixed commit SHA
- runtime/container identity
- Node/Python versions when applicable
- dependency installation result
- test command/version
- start/end timestamp
- pass/fail result
- failure classification
- evidence location
- release decision

## 4. Failure localization

Failures are classified before an AI is asked to intervene:

`environment → dependency → syntax/build → unit → integration → E2E → permission/policy → external service → product logic`

If a failure is deterministic and repeatedly verified, it becomes a candidate diagnostic rule/skill. Promotion requires shadow verification and evidence.

## 5. AI quota reduction

The runtime must execute deterministic checks without an LLM. AI is called only when:

- diagnosis is ambiguous;
- a novel repair is required;
- risk/impact needs reasoning;
- human escalation is required.

Repeated successful AI-assisted repairs should be evaluated for conversion into deterministic tests, rules, skills, or automation.

## 6. Release gate

No release is marked verified solely because an AI reports success. The minimum material-change gate is:

`implementation → compatibility → applicable tests → fixed-SHA verification → evidence → risk/permission review → acceptance → release decision`

Failed or unavailable checks remain visible.

## 7. Security boundary

The verification runtime is not a production runtime. It must not receive production credentials by default, and repository write/merge/deploy authority remains outside the test container unless separately authorized by policy.

## 8. Industry-aligned design notes

The separation of UI/control plane/runtime/workspace follows established agent-engineering practice: execution should occur behind a controlled runtime, while the user surface and agent reasoning remain separate. Reproducible containers reduce environment drift; composable components reduce coupling; deterministic CI should handle repeatable checks while AI handles contextual judgment.

## 9. Current maturity

- DDC verification container: **implemented**
- DDC native test suite: **implemented**
- GitHub Actions test gate: **implemented**
- Cross-repository automated verification: **planned; must respect private-repository credentials and least privilege**
- Real browser E2E backend for SICI: **planned**
- Evidence-linked release artifact/attestation: **planned**

Do not upgrade a planned capability to implemented until the corresponding runtime evidence exists.
