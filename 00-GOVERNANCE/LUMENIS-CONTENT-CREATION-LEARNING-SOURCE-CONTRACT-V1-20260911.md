# LUMENIS Content Creation Learning Source Contract V1

> Status: **CANONICAL SHARED-CAPABILITY LEARNING CONTRACT**  
> Effective: 2026-09-11  
> Scope: `Shared Capability / Content & Creation` only  
> Upstream learning source: historical Git blob `8c305e71b9bec7d902d71677c62554702abe6be4:00-GOVERNANCE/LUMENIS-EXPERIENCE-RESEARCH-LEARNING-ASSET-V1-20260911.md` (read-only research provenance; removed from the current tree by `6ef49524`, not a current Experience authority).
> Rule: **Learning Source ≠ Production Truth ≠ automatic model training.**

---

# 0. Purpose

The Experience Research & Learning Asset must not remain only a design-reference document. Its reusable methods are promoted here into a structured learning source for LUMENIS Content & Creation.

This contract defines how reusable research is transformed into content-production intelligence without copying external references, inventing business facts, or coupling creative output to UI implementation.

The upstream research asset remains immutable historical/research evidence. This file defines the **content-consumption contract**.

---

# 1. Authority boundary

Authority order for content creation:

```text
Current verified business/source/Evidence truth
> current campaign/subject/brand/product constraints
> applicable legal/compliance/permission rules
> approved Content Strategy / Brief
> THIS CONTENT LEARNING CONTRACT
> structured learning registries
> upstream Experience Research & Learning Asset
> external references / historical examples
```

The content layer may learn patterns from research, but it must never use research patterns to override real business facts.

Forbidden:

- inventing brands/products/events/offers/claims;
- treating a visual reference as factual Evidence;
- copying third-party wording, scripts, layouts, images, icons, motion clips or branded compositions;
- using a successful output as a new universal rule without evaluation;
- silently fine-tuning or replacing the production AI/model stack;
- turning this learning source into Production Truth.

---

# 2. Content-production chain

The canonical content workflow is:

```text
Brief
→ Context
→ Research / Evidence
→ Strategy
→ Narrative
→ Draft
→ Artifact
→ Review
→ Approval
→ Publish / Export
→ Measurement
→ Evaluation
→ Learning Asset
```

The system should not default to `prompt → copy`. Every generated deliverable should know which stage it belongs to.

---

# 3. Research-to-content promotion chain

Reusable research enters content creation only through this controlled path:

```text
RESEARCH ASSET
→ EXTRACT REUSABLE PRINCIPLE
→ CLASSIFY CONTENT USE
→ STRUCTURE AS PATTERN
→ VALIDATE AGAINST CURRENT CONTEXT
→ RETRIEVE FOR A REAL BRIEF
→ GENERATE ORIGINAL OUTPUT
→ HUMAN / RULE / EVIDENCE REVIEW
→ PUBLISH OR REJECT
→ MEASURE
→ EVALUATE
→ PROMOTE / REVISE / RETIRE LEARNING
```

A research note does not become an active content rule merely because it looks good.

---

# 4. Required structured registries

The Content & Creation capability should progressively structure reusable learning into the following registries.

## 4.1 Narrative Pattern Registry

```text
NarrativePattern {
  id
  name
  applicable_platforms
  applicable_formats
  audience
  occasion
  objective
  opening_pattern
  tension_or_question
  progression
  emotional_curve
  proof_or_evidence_position
  resolution
  CTA_or_next_action
  avoid_patterns
  source_learning_refs[]
  evaluation_refs[]
  status: ADOPT | EXPERIMENT | RETIRE
  version
}
```

Examples of reusable narrative logic:

- detail → relationship → theme → narrative;
- setup → transformation → peak → convergence → identity/action;
- question → evidence → interpretation → action;
- local fact → larger context → return to original evidence.

## 4.2 Copy Pattern Registry

```text
CopyPattern {
  id
  platform
  format
  language
  tone
  audience
  title_logic
  opening_logic
  sentence_rhythm
  information_density
  proof_requirement
  CTA_logic
  prohibited_phrasing
  multilingual_notes
  source_learning_refs[]
  performance_evidence[]
  version
}
```

This registry stores **writing logic**, not reusable copied sentences.

## 4.3 Visual Pattern Registry

```text
VisualPattern {
  id
  format
  hierarchy
  focal_object
  composition_logic
  typography_role
  material_role
  palette_role
  image_text_relationship
  responsive_or_crop_rules
  accessibility_constraints
  originality_boundary
  source_learning_refs[]
  version
}
```

The Experience material hierarchy may be reused as a content-design principle, but product UI tokens must not automatically become campaign artwork.

## 4.4 Motion / Storyboard Pattern Registry

```text
MotionPattern {
  id
  format
  before_state
  trigger_or_story_beat
  continuity_principle
  after_state
  timing_range
  pacing
  audio_or_text_role
  reduced_motion_or_static_fallback
  source_learning_refs[]
  performance_evidence[]
  version
}
```

The key reusable rule is state/narrative continuity, not copying named animation effects.

## 4.5 Campaign Pattern Registry

```text
CampaignPattern {
  id
  campaign_type
  audience_segments[]
  channels[]
  narrative_arc
  content_matrix[]
  asset_matrix[]
  timeline_logic
  evidence_inputs[]
  decision_points[]
  measurement_plan
  evaluation_plan
  reusable_learnings[]
  version
}
```

## 4.6 Evaluation Pattern Registry

```text
EvaluationPattern {
  id
  content_type
  objective
  quality_dimensions[]
  factuality_gate
  brand_fit_gate
  originality_gate
  platform_fit_gate
  accessibility_gate
  performance_metrics[]
  human_review_required
  promotion_threshold
  retirement_threshold
  version
}
```

No content pattern is promoted to stable learning without an evaluation path.

---

# 5. Unified Content Learning Asset schema

All promoted content-learning units should be representable as:

```text
ContentLearningAsset {
  id
  type: narrative | copy | visual | motion | campaign | evaluation
  title
  source_kind: internal_research | approved_output | evaluation | campaign_result
  source_refs[]
  platform_scope[]
  format_scope[]
  audience_scope[]
  subject_scope[]
  language_scope[]
  objective_scope[]
  observed_problem
  extracted_principle
  reusable_pattern
  evidence_requirements[]
  originality_boundary
  legal_or_compliance_boundary
  counterexamples[]
  quality_score
  confidence
  decision: ADOPT | EXPERIMENT | REJECT | RETIRE
  version
  reviewer
  created_at
  updated_at
}
```

This schema is a learning/knowledge contract. Codex must verify the actual storage/API implementation before binding it to Production.

---

# 6. Retrieval rule for AI content creation

Do **not** send the entire 1,000-line research asset into every content-generation prompt.

Use scoped retrieval:

```text
Current Brief
+ Subject / Brand / Campaign Context
+ Platform
+ Format
+ Audience
+ Objective
+ Language
+ Evidence
        ↓
retrieve only relevant:
Narrative Pattern
Copy Pattern
Visual Pattern
Motion Pattern
Campaign Pattern
Evaluation Pattern
        ↓
compose task context
        ↓
generate original artifact
```

This reduces token cost, avoids style contamination and keeps the model focused on the current brief.

---

# 7. Content workspace behavior

The future Content & Creation workspace should expose a production flow rather than a generic blank chat.

```text
BRIEF
  ↓
CONTEXT
  ↓
RESEARCH / EVIDENCE
  ↓
STRATEGY
  ↓
CREATE
  ├── Copy
  ├── Visual
  ├── Carousel / Poster
  ├── Short Video / Storyboard
  ├── Script
  ├── Campaign Matrix
  └── Other Artifact
  ↓
REVIEW
  ↓
APPROVAL
  ↓
EXPORT / PUBLISH
  ↓
EVALUATION
  ↓
LEARNING
```

AI should return artifacts and editable production structures, not only conversational prose.

---

# 8. Evidence and factuality wall

Creative freedom applies to expression, not facts.

```text
FACT / CLAIM
→ must resolve to verified Evidence or explicitly supplied brief data

CREATIVE INTERPRETATION
→ may use learned narrative/copy/visual patterns

UNKNOWN
→ must remain UNKNOWN or request confirmation
```

For brand/product/campaign content, the system must not manufacture:

- product availability;
- dates;
- prices;
- promotions;
- venue/tenant facts;
- performance results;
- quotes;
- platform statistics;
- legal claims.

---

# 9. Learning feedback loop

Evaluation is not an appendix; it is what makes the content module improve over time.

```text
Published Artifact
→ Performance / Human Review / Business Outcome
→ Evaluation Record
→ What worked?
→ What failed?
→ Why?
→ Pattern-level attribution
→ Learning candidate
→ Review
→ Promote / revise / retire
```

Do not learn blindly from engagement alone. A high-engagement output can still fail factuality, brand fit, compliance or business objective.

---

# 10. Cross-format reuse

A single approved strategy may generate multiple artifacts without restarting research from zero:

```text
ONE VERIFIED CONTENT STRATEGY
        ↓
Title / Hook
Poster / KV
Carousel
Xiaohongshu note
Short-video script
Storyboard
Motion opener
Podcast outline
Report / internal presentation copy
Campaign calendar
```

Each artifact must preserve the same factual/evidence core while adapting its narrative and format grammar.

---

# 11. Multilingual content rule

Chinese / English / Korean outputs share semantic intent but should not be literal line-by-line translations when cultural or platform context requires adaptation.

Store:

```text
semantic intent
→ language-specific expression
→ platform-specific expression
```

Never allow translation convenience to alter factual claims, dates, names, quantities or Evidence.

---

# 12. Relationship to Experience Research & Learning Asset

The upstream research remains available as an immutable historical Git blob:

`8c305e71b9bec7d902d71677c62554702abe6be4:00-GOVERNANCE/LUMENIS-EXPERIENCE-RESEARCH-LEARNING-ASSET-V1-20260911.md`

This contract promotes selected parts of that research into content-production intelligence.

Use this relationship:

```text
Experience Research & Learning Asset
        ↓ principles only
Content Creation Learning Source Contract
        ↓ structured registries
Content & Creation Workspace
        ↓ real brief + real Evidence
Original Artifact
        ↓
Evaluation
        ↓
Learning Asset
```

Do not reverse the dependency: content output must not redefine the canonical Experience Design Authority or Production Truth.

---

# 13. Codex implementation boundary

When Codex later implements/binds this capability:

1. Re-audit the current repository and existing Content/Creation capability before creating storage, API or routes.
2. Reuse existing canonical data/Evidence/Evaluation/Learning owners where verified; do not create duplicate truth stores.
3. Treat all schemas in this file as semantic contracts until actual backend ownership is verified.
4. Implement adapters/contracts rather than coupling UI directly to arbitrary backend tables.
5. Preserve current compliance, permission and Evidence boundaries.
6. Add tests for factuality source mapping, UNKNOWN handling, registry retrieval scope, multilingual semantic consistency and learning promotion/retirement.
7. Do not install or connect an external model merely because a research asset mentions one.

---

# 14. Acceptance criteria

This learning-source design is considered implemented only when all of the following are true:

```text
[ ] upstream research can be retrieved by structured topic rather than whole-file injection
[ ] narrative/copy/visual/motion/campaign/evaluation patterns have explicit schemas
[ ] every generated factual claim has a verified source path or explicit UNKNOWN state
[ ] content artifacts can move through Draft → Review → Approval → Export/Publish → Evaluation
[ ] evaluated outputs can become versioned learning candidates
[ ] learning promotion requires explicit quality/evidence gates
[ ] external references remain research-only and final assets remain original
[ ] no duplicate Production Truth / Evidence / Evaluation owner is introduced
[ ] Chinese / English / Korean semantic consistency is testable
[ ] Content Learning does not redefine Experience Design Authority
```

---

# 15. Final rule

```text
Research teaches principles.
Evidence supplies facts.
Strategy chooses the direction.
Creation turns direction into artifacts.
Evaluation decides what was effective.
Learning preserves only what deserves to be reused.
```

The goal is not to make LUMENIS generate more content. The goal is to make each production cycle leave behind **structured, evidence-aware, reusable creative intelligence**.
