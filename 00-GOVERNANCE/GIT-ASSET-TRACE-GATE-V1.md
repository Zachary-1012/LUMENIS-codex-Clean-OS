# LUMENIS Git Asset Trace Gate V1

## Purpose

Prevent the situation where a document, configuration, source file, or governance asset exists locally but is not actually tracked by Git.

## Mandatory verification flow

Every important asset must pass:

1. File exists on disk
2. `git check-ignore` verification
3. `git status` verification
4. `git diff` review
5. Git tracked verification
6. Commit SHA generated
7. Remote branch verification

## Required report format

```
Asset:
Path:

Disk:
PASS / FAIL

Git Tracked:
PASS / FAIL

Ignored:
YES / NO

Commit SHA:

Remote Verified:
PASS / FAIL

Branch:
```

## Prohibited conclusions

Do not claim:

- file created = pushed
- local file exists = repository contains it
- commit message exists = implementation completed

Only commit SHA + remote verification represents completed synchronization.

## Scope

Applies to:

- Architecture documents
- AI governance
- Model registry
- Prompt/Skill registry
- Runtime configuration
- Source code
- Tests
- Research assets

## Rule

No important LUMENIS asset is considered delivered until Git traceability is proven.
