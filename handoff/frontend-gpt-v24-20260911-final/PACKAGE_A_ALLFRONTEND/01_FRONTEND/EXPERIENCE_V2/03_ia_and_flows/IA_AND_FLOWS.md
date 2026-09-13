# Information Architecture & Core Flows — Experience V2

## Top-level IA (44 screens, 6 domains)
Global Subject Context (subject_id / subject_type / domain / scope / permissions / time_window / locale / context_version) is the single context that every domain reads. Switching subject changes the **view**, never data ownership; the backend re-authorizes on every request. Domain switch (CTH↔BMP) is allowed only where the subject spans both.

- **Account (ACC-01..04)** — domain login (chrome=none), subject selection, global launch (dock), account recovery (chrome=none).
- **CTH · Commerce Operations 序境·商业运营 (CTH-01..10)** — overview (benchmark), subject profile, real-time monitoring, event graph, sentiment calendar, negative comments, trends, case KB (3 tabs), risk decision, report/weekly/evidence (3 tabs).
- **BMP · Brand & Market 序境·品牌市场 (BMP-01..11)** — overview (dock), brand center, market intel, propagation analysis, creators KOS/KOL/KOC/UGC, content center, topic/campaign, podcast studio (script pipeline), brand report/evaluation, brand risk, competitor benchmark.
- **AI (AI-01..05)** — Composer (benchmark), capability→task morph, evidence thread, Agent/Skill Hub, AI Gateway.
- **System (SYS-01..08)** — runtime health, collector, DB truth chain, security/permission, settings (appearance/language), internal browser, acceptance/evaluation, observability logs.
- **Shared · Content & Creation 序境·内容创作 (SH-01..06)** — **Content Studio flagship**, evidence library, canonical metric browser, report export, learning/evaluation asset, notification/task center.

Navigation: PAT-NAV-01 compact rail (≥1025), collapsed icon rail (769–1024), PAT-NAV-02 bottom dock (≤768). Entry screens use chrome=none.

## Core flow 1 — AI-first work (AI nine states)
BOOT → INTENT_HOME → COMPOSING → TASK_ACCEPTED → EXECUTING → ARTIFACT_READY → APPROVAL → ACTION → EVALUATION.
- Composer attaches @Evidence / @Subject / @Time chips (scoped retrieval only — never the whole master asset into a prompt).
- EXECUTING shows real tool/status steps; no indeterminate "thinking" loop to fake work.
- ARTIFACT_READY is artifact-first: the produced artifact is primary, chat secondary; every factual claim carries an evidence citation or is marked UNKNOWN.
- ACTION requires scope/target/permission confirmation; high-risk actions are never primary-blue; after confirm, prototype only toasts `not_wired` (Codex binds).

## Core flow 2 — Content production (SH-01, user priority)
Brief → Context(Subject/Brand) → Evidence(fact wall) → Strategy/Narrative → Create(draft) → Review(fact check) → Approval(human) → Export/Publish(cross-format) → Evaluation → Learning Asset.
- Three tabs: Create (brief form: platform / asset type / audience / goal / language + scoped retrieval), Assets (M12 upload pipeline), Artifacts (artifact-first, one strategy → many cross-format outputs).
- Six Pattern Registries: Narrative/Copy = ADOPT, Visual/Motion = EXPERIMENT, Campaign/Evaluation = ADOPT (each has schema + decision state).
- Factuality wall: availability/date/price/promo/merchant/performance/quote/platform/legal must link Evidence or be supplied by Brief, else UNKNOWN.
- Outputs become a unified ContentLearningAsset; trilingual shares semantic intent, never translates facts loosely.

## Core flow 3 — Observe → Understand → Decide (CTH/BMP data screens)
Context (subject) → Overview KPIs → Observe (monitoring/events/comments) → Understand (trend/graph) → Evidence (case/report) → Decision (risk board + action) → Outcome → Evaluation. Every KPI/event/risk shows source + freshness + evidence pointer; non-ready states (13) replace the block, never silently blank.

## Core flow 4 — Evidence → Canonical → Metric → Report truth chain (SH-02/03/04, SYS-03)
Evidence ingest → canonical record → metric derivation → report export. UI only reads through ViewModel ports; it never creates a second truth store. Duplicate/conflicting owners are surfaced to Codex, not merged in the UI.

## State coverage (every data block)
ready + 13 non-ready: loading, updating, partial, stale, degraded, empty_true, empty_notcollected, empty_filter, empty_permission, permission_denied, blocked, offline, error. Per-screen `*.state-board.html` renders every state; reduced-motion and A11y labels apply to all.

## Responsive reflow (8 viewports, adaptive not scaled)
1920 / 1440 (master) / 1280 / 1024 (master, context→overlay drawer, icon rail) / 768 (rail→bottom dock) / 430 / 390 (master, single column) / 360. Grids collapse 4→2→1; long chains (steps) become horizontal scroll on phones; tables get horizontal scroll; AI composer/dock follow material-tier rules.
