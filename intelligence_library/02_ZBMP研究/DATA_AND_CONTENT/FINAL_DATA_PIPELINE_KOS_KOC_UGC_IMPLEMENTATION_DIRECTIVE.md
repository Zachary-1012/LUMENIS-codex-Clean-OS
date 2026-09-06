# Final Data + KOS/KOC/UGC Implementation Directive

**Status:** FINAL / execution directive
**Date:** 2026-09-04

## Mission

Implement data, monitoring and content-production UI from existing repository contracts. Do not feed raw imported data directly into dynamic tables/charts.

Mandatory path:

`Raw Import → Schema Validation → Normalization → Programmatic Functions → Deterministic Computation → Canonical Table → Quality Gate → Visualization Adapter → Dynamic Visualization → UI`

## Repository-first search

Before coding, locate the existing implementation:

```bash
find . -maxdepth 4 -type f | sort
rg -n "monitor|sentiment|risk|topic|event|note|brand|KOS|KOC|UGC|evidence|report|template|content|copy|table|chart|visual|metric|function" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
rg -n "subject_hit|SUBJECT_WORDS|SUBJECT_EXCLUDE_WORDS|SUBJECT_HARD_FILTER" .
```

Then map each required object to its actual file, function, schema and route. Reuse existing logic first.

## Data implementation contract

### Layer 0 — Raw
Preserve original payload/source.

### Layer 1 — Normalized
Clean types, dates, text and identifiers without destroying source values.

### Layer 2 — Computed
All derived metrics are produced by named deterministic functions.

### Layer 3 — Canonical Table
One stable row schema for downstream consumption.

### Layer 4 — Visualization View Model
Select/order/format data only. It may not invent business calculations.

### Layer 5 — UI
Render the validated view model.

Required function characteristics:

- explicit inputs/outputs
- null handling
- type/boundary handling
- formula/version ID
- tests
- reproducibility

Typical functions to locate/reuse or implement where genuinely missing:

`interaction_rate`, `risk_score`, `sentiment_score`, `engagement_score`, `trend_delta`, `trend_rate`, `content_type`, `creator_tier`, `event_cluster`, `topic_velocity`.

## Dynamic visualization rule

A chart/table row representing a real record must preserve its stable ID and support:

`Visualization → Object ID → Detail → Evidence/Source`

Do not allow charts or table components to independently calculate production metrics.

## Required monitoring object templates

### KOS

Identity, platform, account, brand/industry association, positioning, expertise, content volume, interaction performance, themes, commercial/cooperation attributes, propagation role, risk, evidence.

### KOC

Identity, platform, account, brand association, content type, authentic-experience signals, interactions, local attributes, themes, propagation, risk, evidence.

### UGC

Identity, platform, author, publication time, raw/normalized content, brand, industry, topic, sentiment, risk, interactions, event, topic, evidence.

Classification must store method/version/confidence/evidence. Do not classify from one arbitrary metric.

### Sentiment / public-opinion event

Event ID, event name/type, first discovered, peak, current state, brands, industries, topics, content count, interactions, sentiment distribution, risk, propagation stage, key nodes, KOS/KOC/UGC composition, evidence, disposition state.

### Note

Note ID, URL, author, creator type, publish time, title, body, brand hit, topic hit, event hit, sentiment, confidence, risk, interactions, content type, AI analysis, human correction, evidence.

### Topic monitoring

Topic ID/name, platform, time window, content count, interactions, velocity, growth, sentiment structure, risk structure, associated brands/events, author composition, trend state, evidence.

### Negative monitoring

Object, time, negative type, severity, interactions, propagation velocity, creator type, concentration/burst status, event, evidence, disposition.

### Risk alert

Trigger rule, object, trigger time, risk level/score, trigger evidence, propagation scale/speed, scope, event, recommended action, disposition.

## Content-production template registry

Locate or create one versioned registry. Every template needs:

`template_id, name, content_type, platform, version, status, owner, input_schema, output_schema, rules, risk_rules, created_at, updated_at`.

### Xiaohongshu note

`Title → Hook → Experience/Fact → Scene Detail → User/Emotional Value → Transition → Brand/Event Info → CTA → Tags`

Facts must be traceable. Never fabricate experience.

### Poster copy

`Main Title → Subtitle → Core Information → Time → Location → Participation → Restrictions → CTA`

### Video script

`Hook → Scene 1 → Scene 2 → Key Message → Emotional Turn → Brand/Event Info → Ending`

Each scene stores visual, dialogue/subtitle, duration, purpose and source material.

### Comment reply

`Original Comment → Intent → Sentiment → Risk → Reply Strategy → Draft → Review State → Final Reply`

Modes: thanks, information, question resolution, negative de-escalation, risk escalation.

Risky replies require configured review gates.

## Content QA chain

`Source → Draft → Fact Check → Brand/Style Check → Risk Check → Human Review → Approved Copy → Publish/Export`

## AI/human audit fields

Where AI is used, preserve:

`original input, AI output, confidence, prompt version, model version, final result, human correction, correction reason`.

AI assists classification/content drafting. It does not silently replace deterministic business rules or human approval gates.

## Final execution order

1. Find existing schemas/functions/components/routes.
2. Map them.
3. Reuse them.
4. Add missing deterministic functions.
5. Generate canonical tables.
6. Validate tables.
7. Connect visualization adapters.
8. Connect dynamic UI.
9. Add drill-down/evidence links.
10. Add template registry and versioning.
11. Test data correctness before visual polish.

## Completion gate

```text
[ ] Raw data preserved
[ ] Normalization deterministic
[ ] Derived metrics function-based
[ ] Canonical table exists
[ ] Quality gate exists
[ ] Visualization consumes validated table
[ ] Stable IDs preserved
[ ] Drill-down reaches evidence
[ ] KOS template implemented
[ ] KOC template implemented
[ ] UGC template implemented
[ ] Event template implemented
[ ] Note template implemented
[ ] Topic template implemented
[ ] Negative/risk template implemented
[ ] Content template registry implemented
[ ] Xiaohongshu note template implemented
[ ] Poster template implemented
[ ] Video script template implemented
[ ] Comment-reply template implemented
[ ] AI/human audit fields preserved
[ ] Existing subject hard-filter/business logic preserved
[ ] Existing routes/contracts preserved
```

**Do not declare completion because the visualization renders. Completion means the data lineage, computation, table contract, visualization, drill-down, templates and validation chain all work together.**
