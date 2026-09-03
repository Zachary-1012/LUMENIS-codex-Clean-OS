# Podcast UX Architecture V1

## Direction

Use Xiaoyuzhou as an interaction reference, not a visual clone. Preserve ZBC's existing Wabi-sabi black/white/gray foundation, semantic status colors, 10/14/20px radius system and restrained motion language. The podcast module is an intelligence/production workspace, so information density may be higher than a consumer player, but hierarchy must remain calm.

## Core navigation hierarchy

### Level 0 — ZBC global shell
- Global navigation
- workspace/project context
- system health / evidence / AI status

### Level 1 — Podcast workspace
1. Overview
2. Shows
3. Episodes
4. People
5. Story & Problem Graph
6. Content Assets
7. Platform Intelligence
8. Research / Benchmarks
9. Production Queue

### Level 2 — Episode workspace
- Overview
- Player / waveform
- Transcript
- Story map
- Questions
- Highlights
- Audience / platform data
- Derivatives
- Evidence / AI runs

### Level 3 — atomic interaction
- play/pause
- seek
- speed
- chapter jump
- timestamp comment/annotation
- highlight
- evidence open
- create derivative

## Reference lessons from Xiaoyuzhou

1. Keep primary navigation small and task-oriented. Historical product analyses describe a compact main navigation centered on discovery, subscriptions/profile and a persistent player bar.
2. The persistent mini-player is a key continuity primitive: users can browse without losing the current listening context.
3. Timestamp comments connect community discussion directly to an audio moment; the same interaction should become an internal editorial annotation in ZBC.
4. High-energy moments on the timeline are valuable because they reduce the cost of finding useful content. ZBC should combine observed audience markers with AI-suggested story/insight markers, clearly separating observed from inferred.
5. Episode detail, comments, profile and player are tightly linked in the consumer experience; ZBC should translate this into Episode ↔ Person ↔ Story ↔ Asset navigation.

## ZBC adaptation — do not copy consumer UI literally

Consumer app:
`Discover → Episode → Player → Comment → Profile`

ZBC intelligence workspace:
`Discover/Research → Episode → Player/Timeline → Evidence/Annotation → Person/Story/Asset → Benchmark`

## Primary desktop layout

```text
┌────────────────────────────────────────────────────────────┐
│ ZBC shell / workspace / health                             │
├──────────────┬─────────────────────────────────────────────┤
│ Podcast nav  │ Episode / workspace header                 │
│              ├─────────────────────────────────────────────┤
│ Overview     │ Cover | title | person | status | actions  │
│ Shows        ├─────────────────────────────────────────────┤
│ Episodes     │ Timeline / waveform / runtime / markers    │
│ People       ├───────────────────────┬─────────────────────┤
│ Story Graph  │ Transcript            │ Insight / evidence  │
│ Assets       │ speaker + timestamp   │ Story nodes         │
│ Platforms    │                       │ AI suggestions      │
│ Research     ├───────────────────────┴─────────────────────┤
│ Production   │ Audience / platform observations            │
└──────────────┴─────────────────────────────────────────────┘
```

## Interaction rules

- Player state is persistent within Podcast workspace.
- Selecting a transcript sentence seeks the player to its timestamp.
- Selecting a timeline marker opens the linked evidence/annotation.
- Selecting a StoryNode filters transcript, assets and platform observations to that node.
- Selecting a person opens the person dossier without losing episode context.
- AI suggestions are visually labeled and never silently become verified facts.
- Observed platform metrics and derived metrics use different evidence states.
- Empty/loading/error states are first-class and must not collapse layout.

## Mobile adaptation

Prioritize:
`Player → Transcript → Story → Highlights → Assets → Evidence`

Use a bottom mini-player and bottom sheet for episode context. Do not reproduce the entire desktop sidebar on mobile.

## Visual foundation

- Near-black primary operational surface and off-white reading surface.
- Semantic colors only for state meaning, not decoration.
- High text contrast and restrained borders.
- 10/14/20px radius hierarchy.
- 140/220/360ms motion hierarchy.
- Waveform/timeline is a data visualization surface; never use decorative gradients that compete with evidence.

## Validation gates

UX implementation must pass keyboard navigation, responsive layout, player state persistence, transcript seek synchronization, loading/error/empty states, evidence visibility and regression checks against existing ZBC routes before merge.
