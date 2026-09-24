# BMP-08 — 播客制作室

```yaml
screen_id: BMP-08
status: OWNER_REVIEW
revision: 2
owner_domain: BMP
binding_ids: [BACKEND-GAP-025]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
presentation_design_decision: DESIGN_READY
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Root (presentation only); podcast scope and source-lineage review remains blocked
reviewed_at: 2026-09-24
presentation_reviewed_by: root
presentation_reviewed_at: 2026-09-24
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to turn approved source material into a reviewable spoken episode while keeping script, source, audio version, publication and rights distinct.
- BMP owns the brand content workflow; the existing podcast store is unfiltered and drops source references, so it cannot currently establish a brand-safe read.
- `BACKEND-GAP-025` blocks real source display. No audio, script or rights status is shown as verified until brand scope and source lineage are returned.
- Scope modes are explicit: a globally scoped `GLOBAL_ALL` production set is valid only with global authorization and source lineage; `FOCUS` material must match the selected BrandFocus.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-08')` / `/api/experience/screen/BMP-08`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected read fields: `materials[]`, `outline[]`, `brand_id`, `evidence_ref`, version and rights state.
- `podcast:draft` saves a local script-request draft. `podcast:render` saves a local render-request draft and does not generate audio.
- Source references are used as a validation gate and are not exposed as internal identifiers.

## 3. State and recovery

- Loading keeps the audio workspace identity.
- Not collected says source material or a recorded audio result is not ready.
- Missing rights or source lineage withholds the affected material and does not render a playable-looking placeholder.
- Offline/error supports retry without stale audio state.
- Local script/render drafts explicitly remain pending and non-executed.

## 4. Purpose-built composition

- Desktop keeps three distinct work zones: the material and section rail, the time-coded script area, and the properties/rights rail. The audio preview area remains separate below them. This composition stays visible as a structural preview while scope is blocked; it does not imply that script, source or audio data was read.
- Mobile remains task-first, with one selected work area at a time. The same single scope boundary appears above the active pane.
- When the read scope is unverified, show one screen-level boundary notice. Keep the zone headings and short semantic prompts, render scope-dependent counts and values as unknown (`—`), and omit per-zone copies of the scope warning. Do not show `0`, “no sources”, or “no script sections” for data that was withheld.
- Only a verified, authorized response may produce real counts or a true empty/not-collected state. The screen keeps local script/render request drafts and their local-only explanation; those controls do not read blocked material or claim generation.
- The primary question remains “can this spoken version be reviewed and released with its source and rights intact?”

## 5. Actions, authorization and effects

- `podcast:draft` saves a local request draft; it does not create a script or call an executor.
- `podcast:render` saves a local render-request draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no audio/cut is generated or claimed ready.
- Publish and rights changes are outside this slice.

## 6. Accessibility and localization

- Waveform has a text timeline equivalent with time, section and source labels.
- Keyboard focus follows material, script, timeline, rights status and staged actions.
- Audio controls use labels that include version and availability; no color-only rights state.
- Integration key inventory: `screen.BMP-08`, `bmp08.subtitle`, `bmp08.audio.*`, `bmp08.script.*`, `bmp08.source.*`, `bmp08.rights.*`, `bmp08.action.*`, `bmp08.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- An unfiltered podcast response is rejected and no material title or audio state is displayed.
- An unverified scope keeps the three-zone desktop structure, shows one scope boundary, uses unknown markers rather than zero counts, and does not repeat the scope warning inside each zone.
- A verified empty response may show an empty state only when the authorized response establishes that state; blocked/unknown data never becomes “no sources” or “no sections”.
- A verified material keeps script, source, audio version and rights as separate states.
- Missing source lineage prevents rendering and remains an honest unavailable state.
- Render is blocked or saves an explicitly local draft without approval; no local audio-success claim occurs.
- Desktop and mobile provide equivalent source, rights and script meaning.

## 8. Presentation review and business decision

- Presentation decision: `DESIGN_READY` after root reviewed the task-specific composition against current source and the guarded browser page on 2026-09-24. This covers the material/section rail, segmented script work area, rights/properties inspector, distinct audio region, and single-active-work-area mobile composition.
- Business decision remains `IMPLEMENTED / BLOCKED_FOR_PODCAST_SCOPE`. The review does not establish that blocked source, script, rights, or audio data was read, and it is not a business PASS. The podcast owner must preserve source references in a verified brand read before real-user E2E acceptance.
- When real audio is absent, the audio region stays explicitly empty; no waveform, recording, generation, or playable result is inferred from the presentation review.
