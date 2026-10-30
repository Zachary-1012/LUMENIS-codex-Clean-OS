---
name: oevira-pstack
description: Apply Lauren Tan's pstack engineering methods to OEVIRA architecture, repeated defects, cross-module changes, verification and performance claims. Use during these development tasks; preserves the complete product scope and current user-selected execution settings.
---

# pstack for OEVIRA

This is an OEVIRA adaptation of Lauren Tan's [pstack 0.15.36](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/plugin.json), pinned to commit `1ba91fc25c0977741dd0e267849e6234b037ed0a`. The upstream [MIT license](LICENSE) is retained. This skill supplies engineering methods; the current repository `AGENTS.md` and direct user instructions retain product and execution authority.

Read the source skill linked for the task when its detailed method is needed. Apply the method to the actual change and its consumers; do not substitute another audit report for a repair. Routine changes do not need every mode.

## Repeated corrections: correct and encode lessons

Sources: [correct](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/correct/SKILL.md), [encode lessons in structure](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-encode-lessons-in-structure/SKILL.md).

Find the repeated failure and the condition that allows it. Prefer, in order: eliminate conflicting ownership or duplicate paths; encode the invariant in types/state; add an actionable boundary or repository check; test the actual behavior. Keep the existing owner's implementation and checks rather than creating a second enforcement system. A regression must fail on the real past mistake and pass the valid case. Never remove a meaningful failure assertion to obtain a passing run.

Write instructions only for decisions that genuinely require judgment. Capability completeness, originality, visual quality and professional quality cannot be certified by keyword counts, hashes or model self-scores. Identify the actual work, preserved behaviors and appropriate review evidence. Do not add another full-product rule table when the existing contracts already own these decisions.

## Stateful work: model the domain

Source: [model the domain](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-model-the-domain/SKILL.md).

Model the real business object and permitted transitions before spreading booleans or shape assumptions across callers. Put each invariant and writable state under one owner; use typed values, state machines, relations or indexes when they remove invalid states or repeated policy. Preserve the different semantics of subjects, relationships, evidence, comments, editable objects, versions and real external effects. Shared infrastructure must not collapse all professional objects into generic text. Avoid abstractions that add indirection without removing an actual problem.

## Nontrivial architecture: caller first

Source: [architect](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/architect/SKILL.md).

Read the actual implementation, consumers and constraints. Write the caller's real operation first, then derive the types, signatures and boundary; include failure, cancellation and recovery. Compare materially different designs when there is a genuine ownership or architecture choice. Prefer interfaces that hide implementation work while preserving full professional behavior. Established choices do not require another design competition.

Repeated workarounds, escape casts, multiple writers or callers coordinating internals are evidence to revisit the boundary. Do not publish a sketch, placeholder or partial migration as a working capability. This adaptation uses the current authorized agent/model settings and existing root; upstream arena defaults, model fallbacks and candidate worktrees are not invoked.

## Changes across boundaries: blast radius

Source: [blast radius](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/blast-radius/SKILL.md).

Follow the actual data beyond symbol references: JSON, persisted keys, formats, events, asynchronous work and other-language consumers. State the critical fact on which the change's safety depends. Read the pinned library implementation where relevant, then exercise the real boundary with isolated inputs; use the running product when the claim depends on it. Keep unproved risks explicit. A list of callers alone is not impact verification. For document/repository changes, check the exact publishable tree independently of developer-only files and paths.

## Completion: prove it works

Source: [prove it works](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-prove-it-works/SKILL.md).

Read the actual resulting value/artifact and operate the changed behavior. For user work, include applicable local modification, saving, independent reopening, export and recovery with original content preserved. Separate source checks, running behavior, professional quality and publication. Subagent reports, successful compilation and file timestamps are not substitutes for direct observation. Keep reproducible evidence in the existing appropriate location; do not commit temporary execution status.

## Performance: benchmark checklist

Source: [benchmark checklist](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/benchmark-checklist/SKILL.md).

Define the exact user-visible claim before measuring. Inspect the timed region, correct output, actual work and failures; compare the same versions, realistic data and production-equivalent configuration. Identify the bottleneck, alternate repeated comparisons and report units, distribution and variability. Use existing Windows equivalents for upstream Unix diagnostics. Distinguish first feedback (including the 90 ms target), completed processing and continuous playback. An inconclusive measurement stays inconclusive.

## Adaptation boundaries

The methods improve implementation and reduce redundant work; they do not reduce approved capability. They do not change models, reasoning effort or service tier; enable autonomous schedules; grant external communication, account access, collection, training, spending or deployment; or restore rejected UI. Visual decisions remain with the root. No upstream installer, hook, automation or model runner is bundled or executed by this skill. Apply task-appropriate validation rather than running an entire checklist for every edit.
