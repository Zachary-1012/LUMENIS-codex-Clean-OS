# ZBC Compliance-by-Design & Release Gate V1.0

Status: Engineering baseline
Scope: Z-Brand-Core / ZBC
Purpose: Keep the existing product architecture and functions intact while embedding legal, security, data, AI, algorithm, provenance and release controls into development.

## 1. Non-destructive principle

This baseline is a control layer, not a product rewrite. Existing collection, Subject Truth, sentiment, event, propagation, risk, reporting, Evidence, Resource Library, Browser and Zachary capabilities remain in place. Compliance controls may restrict, record, validate or block behavior, but must not arbitrarily remove product capability.

## 2. Mandatory development gates

Every material change must pass, in order:

1. CODE SAFE — source provenance, dependencies, licenses, secrets, SSRF, RCE, path traversal, permission boundaries.
2. DATA SAFE — source legitimacy, purpose limitation, minimization, personal-information handling, retention/deletion and access control.
3. AI SAFE — model/prompt/tool permissions, prompt-injection resistance, Evidence traceability, AI cannot silently redefine business Truth or policy.
4. ALGORITHM SAFE — maintain an inventory of algorithm/model functions and assess whether recommendation, ranking, filtering, generation or decision functions trigger applicable regulatory obligations.
5. SECURITY SAFE — authentication/session handling, upload security, browser isolation, external-action controls and incident logging.
6. EVIDENCE COMPLETE — material collection, AI decisions, policy blocks, human corrections and releases are traceable.
7. RELEASE SAFE — assess applicable ICP/公安备案, algorithm filing, security assessment, generative-AI and other regulatory requirements against the actual production service form and current law.

## 3. Collector Safety Constitution

Collectors must use lawful/authorized access paths and respect applicable platform rules and technical limits. A platform block is a state to record and handle, not a challenge to defeat.

Forbidden implementation goals include bypassing authentication/access controls, CAPTCHA circumvention, stealing or reusing credentials/tokens/cookies, account switching to evade platform security or rate limits, or IP/proxy rotation whose purpose is to evade a platform block.

For XHS/Rednote-type states, distinguish normal collection, empty result, rate limit, IP/security risk, CAPTCHA and safety restriction. Security/risk states must stop or cool down according to policy and preserve Evidence.

## 4. Data Source Registry

Every external source/collector must record: Source ID, platform, entry/endpoint, access method, public/authorized status, purpose, fields, personal-information classification, frequency, applicable platform restrictions, stop conditions, Evidence and review status.

## 5. Personal-information minimization

For each field record whether it is personal information/sensitive personal information, why it is necessary, masking/anonymization method, retention period and access scope. Do not store credentials, cookies or sessions in Evidence, source control or ordinary business datasets.

## 6. Zachary AI boundary

Zachary is a general internal AI runtime during the current stage. It may analyze, classify, summarize, research, generate reports, retrieve approved resources and assist engineering. It must not independently change Subject Truth, business policy, risk thresholds, permissions, compliance rules, Evidence or security controls.

AI output is not automatically system Truth. Material decisions require rule/evidence traceability and, where specified, human review.

If Zachary later becomes a public-facing standalone service, perform a fresh regulatory assessment before release; do not assume the internal-runtime assessment transfers automatically.

## 7. Algorithm / model inventory

For every material algorithm/model capability record: ID, purpose, inputs/outputs, implementation type, model and prompt versions, whether it ranks/recommends/filters/generates/decides, whether it affects users, human intervention, evaluation results and regulatory review status.

Regulatory applicability must be determined from the actual service form and current official rules, not from labels alone.

## 8. Evidence and auditability

Material actions must be attributable and reproducible enough to answer who/what/when/where/why/how/result. Preserve source evidence, AI analysis metadata, model/prompt version, policy decisions, human corrections, release commit and test results as appropriate.

## 9. AI Development Provenance

AI-assisted implementation is permitted. For material code record requirement owner, architecture decision, implementation source (human/AI-assisted), third-party/reference status, license, review, tests, security/compliance result and commit. AI generation does not by itself mean third-party copying; direct copying or derivative use must be identified and licensed appropriately.

## 10. Third-party dependency audit

Maintain a third-party inventory covering runtime dependencies, Python/Node packages, browser tooling, SDKs, model weights and vendored code. Record version, source, license, modifications, NOTICE/COPYRIGHT obligations and commercial-use compatibility. Never remove or conceal third-party attribution.

## 11. Upload / import safety

Existing product limits remain authoritative. Validate file count/size, MIME/type, extension, malware risk, metadata/PII handling, storage isolation, retention and deletion. Do not infer that an uploaded file is trusted merely because the user supplied it.

## 12. Release documentation

Maintain a `/compliance/` evidence set (or equivalent) covering product description, data sources, data flow, data classification, personal-information handling, algorithm/model inventory, AI safety, content safety, security, third-party licenses, source provenance, logs, incident response, risk assessment, evidence index and release checklist.

## 13. Legal/filing principle

This document is an engineering control baseline, not legal advice and not a filing determination. Before production release, re-check current PRC laws, regulations, CAC requirements, cybersecurity/data rules, platform terms and the actual service architecture. Determine filing/permit requirements feature-by-feature rather than assuming that every AI or monitoring function has the same regulatory classification.

## 14. Change control

This baseline is frozen as the engineering starting point after approval. Future changes should be evidence-driven: do not weaken a control merely to increase collection success, AI autonomy or release speed. If law, platform rules or actual product form changes, open a compliance change record and update only the affected control with audit evidence.

## 15. Release rule

No production release when a mandatory gate is BLOCKED. REVIEW items require documented disposition. GREEN items require evidence. The goal is not to guarantee zero regulatory friction; the goal is to make compliance-by-design, provenance and release evidence continuous parts of engineering.
