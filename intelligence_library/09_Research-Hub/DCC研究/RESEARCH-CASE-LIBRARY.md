# Research Case Library — Zachary AI Platform

Status: additive research support; not an authority over the immutable platform baseline.

## Purpose

This library converts external engineering research into reusable, reviewable patterns for DDC, Z-Brand-Core, and SICI-Core. Research is not considered adopted until it is adapted, tested, and supported by evidence in our repositories.

## Case 001 — Reusable GitHub workflows

**Source:** GitHub Actions documentation.

GitHub recommends reusable workflows to avoid copying deterministic CI logic. Reusable workflows can be centrally maintained and called by multiple workflows; GitHub also notes that SHA references provide stronger stability/security than mutable branches or tags. citeturn0search1turn0search2turn0search7

**Adaptation:** Keep deterministic verification logic in DDC-owned reusable workflows where it genuinely crosses repository boundaries. Do not create a giant universal workflow. Prefer a small contract surface and fixed references for security-sensitive reusable dependencies.

**Application:** DDC verification; Z-Brand domain tests remain owned by Z-Brand; SICI mobile checks remain owned by SICI.

## Case 002 — Agentic workflows as a reasoning layer

**Source:** GitHub Agentic Workflows documentation/blog, public preview in 2026.

GitHub describes agentic workflows as AI-powered repository automation that can reason over repository context, while standard Actions remain the execution substrate. GitHub explicitly documents security guardrails and safe-output patterns; the feature is currently public preview and subject to change. citeturn0search0turn0search6turn0search9

**Adaptation:** AI should propose, diagnose, summarize, and classify contextual engineering problems; deterministic Actions should execute known verification. We do not make preview technology a hard production dependency.

**Application:** Future learning/failure-analysis assistant in DDC, initially read-only/shadow mode.

## Case 003 — Token/compute efficiency

**Source:** GitHub engineering research on improving token efficiency in Agentic Workflows.

GitHub has publicly described measuring agent workflow cost and reducing inefficient repeated context. citeturn0search10

**Adaptation:** Record repeated inspection findings and stable diagnostics so future AI runs can consume compact Evidence instead of repeatedly re-reading the entire platform. This directly supports the AI-dependency-reduction rule.

**Application:** Evidence summaries, failure fingerprints, reusable diagnostics, and learning candidates.

## Case 004 — Artifact provenance

**Source:** GitHub Artifact Attestations.

GitHub artifact attestations provide signed provenance connecting a released artifact to repository, workflow, environment, commit SHA, and build context. GitHub specifically recommends attestations for software intended for distribution and says they are not a substitute for security policy. citeturn0search5turn0search11

**Adaptation:** Do not generate attestations for every five-times-daily inspection. Reserve them for actual release artifacts once the platform has a stable release artifact pipeline.

**Application:** Future D6 Release gate for distributable packages/images/binaries.

## Case 005 — Three-way feedback architecture

**Internal synthesis:** External practices support separating deterministic automation from contextual reasoning, centralizing reusable verification, and preserving evidence. Our platform adds a domain-specific boundary:

`Z-Brand-Core = production/domain truth`

`DDC = engineering/control/verification truth`

`SICI-Core = mobile interaction/real workflow feedback`

**Adoption rule:** Evidence can flow across repositories only through explicit Contract + Test + Evidence + Learning records. One repository's successful execution is never assumed valid in another environment.

## Research-to-code rule

Every adopted case follows:

`Research → relevance test → adaptation → implementation → test → evidence → promotion`

A source can influence design without becoming copied code. License/provenance must be checked before external code is reused.
