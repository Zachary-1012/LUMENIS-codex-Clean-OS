# Architecture Cumulative Baseline — 2026-09-04

Status: ACTIVE / EXECUTION BASELINE

## 0. Cumulative rule
Every new research or architecture update MUST carry forward the previous applicable baseline. New decisions supersede older rules only when explicitly marked SUPERSEDED. The repository must not retain conflicting active rules.

## 1. Parent / Child product architecture

ZBP is the final parent system (Parent). CTH is a child system/domain (Child).

Development order is intentionally different from final ownership:

```text
CTH-first development
 -> implement capability
 -> real-data validation
 -> stability
 -> regression / audit
 -> Capability Contract
 -> extract / adapt / merge
 -> ZBP capability absorption
```

CTH must not be weakened or prematurely dismantled merely to satisfy the eventual parent-child structure. Capability ownership is determined by dependency, reuse, data authority, runtime importance, business coverage, and measured stability.

## 2. Twin repositories

Zachary-OS-AI = Research & Intelligence.
Z-Brand-Core = Production Truth.
Research produces evidence/contracts/specifications; it does not directly mutate Production Truth.

## 3. Canonical data chain

```text
External input / collector / file / text / image / video / audio / API / manual input
 -> Universal Ingestion
 -> Raw Asset / Evidence
 -> Parse
 -> Validate
 -> Normalize
 -> Function / Formula
 -> Canonical Dataset / Table
 -> Metric / Time Window
 -> View Model
 -> Visualization Spec
 -> Dynamic Table / Chart / UI
 -> Report / Export
```

Evidence-only assets remain Evidence and must not be fabricated into numeric records.

## 4. Canonical truth rule

Business metrics are calculated once. UI, table, chart, report and export consume canonical outputs. Duplicate business calculations are prohibited.

Required lineage concepts include dataset/version, schema version, source asset/record IDs, transformation/calculation/formula versions, quality status, calculated time, and evidence references.

## 5. UI / interaction hierarchy

```text
App Shell
 -> Workspace
   -> Product / Domain
     -> Module
       -> Page
         -> Section
           -> Component
             -> Window / Action
```

Window and route state must preserve parent context, child context, target, and return context. Dynamic interaction and visualization are governed by the same hierarchy.

## 6. B03 / B04

B03 = architecture reorganization + UI foundation + shell + routes + windows + interaction contracts.

B04 = canonical view model + table engine + chart engine + visualization specification + dynamic/realtime/trend presentation.

No decorative visualization. Each visual must answer a defined analytical question.

## 7. Business domains

CTH currently prioritizes production implementation of collection, notes, topics, sentiment, events, risk, KOS/KOC/UGC, reports, export, runtime, health, recovery and related capabilities. Mature capabilities are later absorbed into ZBP through contracts/adapters/extraction rather than blind code copying.

Podcast is a complete attached business system within the eventual ZBP platform and reuses shared data/evidence/AI/UI/report infrastructure.

## 8. Templates / reports / content

KOS, KOC, UGC, sentiment, event, note, topic monitoring, content production, comment/reply, daily/weekly/monthly/yearly/special reports, and Podcast modules must use the same canonical data and UI/window/visualization contracts.

## 9. Mandatory removal rule — NEW

Obsolete, conflicting, superseded, duplicated, or no-longer-applicable rules/files MUST be removed after dependency and usage verification. Do not preserve obsolete implementation merely for convenience.

Removal sequence:

```text
Identify conflict
 -> dependency/reference scan
 -> confirm replacement
 -> migrate consumers
 -> tests / regression
 -> remove old rule/file
 -> verify repository
 -> record deletion in audit
```

Historical material may remain only when required for immutable history, audit/legal traceability, package compatibility, or explicit historical archive. Such material MUST be marked LEGACY/ARCHIVE and MUST NOT be treated as an active rule.

## 10. Research adoption rule

External research is reference material, not authority. Adopt only when compatibility, measurable benefit, production risk, and regression evidence support the change.

## 11. Hard gates

- subject hard filtering remains authoritative until explicitly replaced by a tested superior contract;
- human decision gates cannot be bypassed;
- no frontend secrets;
- no duplicate metric calculation;
- no silent route/window duplication;
- no research-to-production uncontrolled write;
- no big-bang rewrite of stable collection;
- no active conflicting rule/file may remain after migration.
