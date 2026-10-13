# BMP-08 — 播客制作室

## 2026-10-11 当前产品归属：Shared独立播客制作

播客制作能力属于Shared/C4媒体与项目Owner，可以独立使用。用户直接新建节目、填写创作Brief/手写脚本、导入或录制获准音频，再编辑、试听、混音、保存版本、导出、重开与恢复；不需要先有品牌分析、CTH/BMP任务、BrandFocus或SourceBrief。AI增强脚本、转写及剪辑建议，缺模型不阻断正常人工制作。

保留BMP-08既有屏幕ID/路由、历史BMP品牌场景和旧版本数据作为兼容入口；该标签不能把制作内核变成BMP独占。由BMP进入时保留真实品牌范围；从Shared独立创建时沿原制作项目/工作区权限接入，不自动补品牌或越权GLOBAL。跨入口的实际安全绑定仍需代码和运行证明，不由文档修改冒称完成。

与视频使用现有 Shared 媒体编辑基础和项目版本体系，音频模式保留真实波形、剪切、混音、试听及节目导出；不新建另一套编辑器。切换模式不得删除原视频轨道、字幕叠加层或已保存内容。正常制作不要求额外 demo 勾选，真实素材权益和导出/发布权限继续核验。新增 REA 解析与原创适配按 Architecture 审核稿第11节接入，包内有限示例不证明完整播客体验已交付。

下方品牌来源要求仅约束使用品牌业务资料的路径。采用既有研究/业务成果时保留引用、权益和版本；独立原创脚本及用户音频不以业务Evidence存在为前提。验收必须分别覆盖独立节目制作和可选品牌资料续接，保留全部既有音频质量、制作、保存、恢复和版本要求；本段不改变实现或验收状态。

```yaml
screen_id: BMP-08
status: OWNER_REVIEW
revision: 2
owner_domain: BMP
owner_domain_role: compatibility screen and brand-business context, not exclusive production ownership
production_capability_owner: Shared Capability / C4-W4
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
- BMP owns the brand-business context only; Shared/C4 owns podcast production, including independent creation. The retained brand-path finding is that the podcast store is unfiltered and drops source references, so that read cannot establish brand-safe access. This does not make brand scope a prerequisite for user-owned independent audio.
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

### 2026-10-03 approved Script/Audio refinement

M reviewed the existing episode composition and approved task-appropriate Script
and Audio views within the current material/section and properties/rights areas.
Keep the selected segment and known time when switching views. Distinguish the
script version, corrected transcript, spoken-audio revision and actual rendered
output; text changes do not imply changed sound. Show actual audio only when its
canonical result exists. Narrow/large-text layouts keep one active work area and
reversible layers with visible focus, touch targets and honest recovery states.
This is a bounded DESIGN_READY presentation clarification, without a new episode
store, persisted preference or audio engine. Implementation, complete podcast
persistence, actual AI/rights binding and live user acceptance remain open.

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

## 9. Manual audio editing through the Shared owner — DESIGN_READY 2026-10-03

From the existing Audio area, an explicit Edit audio action opens the existing
Shared media workbench in audio mode. A new manual project uses actual local
voice/music/effect files admitted by the current source confirmation and
Permission owner. The legacy podcast material reader remains under its v2
scope/lineage gate: its labels and audioAvailable flag are never source refs.
An unavailable legacy catalog does not itself prohibit a separately authorized
new manual project. Current server context and source-use checks still govern
that action; default GLOBAL_ALL does not require artificial BrandFocus selection.

Reuse Snapshot, Timeline, Controller, Artifact and the existing audio export
callable. Show real sources and clip ranges, an actual saved audio player and
voice/music/effects tracks. Support existing trim/split/placement/gain/fades,
fixed-duration source replacement, Delete and Undo. Hide video-ratio, video
track and caption-overlay controls in audio mode without deleting stored data.
Any waveform, meter or beat-grid visualization must derive from actual decoded
audio and its exact time range; never fabricate a visual substitute. Do not
claim live draft sound, transcription or synthesis unless the corresponding
existing owner returns it. Source stream choices must describe the actual
inspected asset.

The existing scope-approved, user-visible local script draft may use a
transient local Read Aloud preview with an exact installed zh-CN, en-US or
ko-KR device voice and 0.75×/1.0×/1.25× rates. It reads only the current local
draft; it does not synthesize final podcast audio, create/persist an audio
Artifact, translate the script or call a remote voice. Draft, selected section,
scope or screen changes stop the session. It remains separate from the real
audio editing/export path below.

Keep output_kind consistent across save, export, retrieval and reopen. A video
project is never silently converted to audio or stripped of its tracks/overlays;
offer the appropriate existing editor or an honest unsupported result. A failed
new export preserves the previous authorized playable sound and current edit.

Returning restores the studio's Script/Audio selection, segment, notes and known
position. Retain pending edits through the existing leave guard and pause hidden
playback through the existing lifecycle owner. Do not create a second player or
discard live state on cosmetic tab changes. Narrow/200% text keeps one active
work area with reversible source/properties/result layers, keyboard access and
Chinese/English/Korean copy.

Continuing known research or a project requires the real inherited Task/Brief,
selected material/Evidence, constraints and upstream versions. Ask only for
missing production inputs. A new manually imported project does not substitute
for that cross-capability requirement or remove the older source binding gap.

Independent podcast acceptance is a separate normal path: direct Shared entry ->
user-authored creative intent/script and permitted imported or recorded audio ->
edit/listen -> save/export -> close/reopen/revise/recover. No inherited business
Brief, BrandFocus or research job is required. Workspace/project Permission and
the actual audio/source rights remain mandatory. Keep the BMP-specific scope
when continuing a brand task; do not infer it for independent creation.

Required actual outcome: admitted files -> actual playback/listening -> actual
waveform and stream/range/mix editing -> actual WAV export and listening -> saved
version -> reopen -> meaningful revision and re-export -> return to the same
studio. Verify revoked source/scope, invalid media, stale revision,
retrieval/render failure, cancellation and retained prior output. Web and Windows
audio playback require their own real evidence; other native platforms remain
explicitly unavailable until verified. Builds and local request drafts cannot
establish podcast completion. Owned audio understanding and synthesis retain
their separate C2/C4 acceptance.

F owns the existing BMP-08/workbench/player interface and affected tests; W4
owns media processing, W5 source/Evidence/Artifact lineage and W6 shared binding,
runtime and publication. This decision adds no backend, endpoint, store or model.
The older podcast read remains blocked wherever its real scope/lineage is absent.

## Audio timeline panning completeness — 2026-10-03

### 2026-10-11 audio entry continuation (LOCAL_ONLY; acceptance open)

The BMP-08 audio entry reuses SH-01's existing media timeline with initial
`outputKind=audio`; its BMP caller scope is explicit, and GLOBAL/ALL does not
invent a BrandFocus. The entry remains reachable when the legacy brand/script
read is unavailable. A saved project's returned output kind stays authoritative.
Audio controls use audio-specific copy and hide inapplicable video presentation;
conflicting video/overlay material is retained and explained rather than lost.
Export still checks actual media streams, source rights and server state.

Script and audio editors retain separate unsaved guards under the existing
route guard. Returning to the script switches the visible area while preserving
audio edits; the inactive editor stops media/read-aloud playback. A real route
exit or context change protects both drafts. This does not make local script
editing modify audio bytes. Actual import/playback/waveform/edit/export/version
and recovery evidence remains required by the full outcome below; widget
regressions are not that acceptance.

Podcast/audio editing must satisfy Experience §37 through the existing shared Timeline owner. Horizontal panning, actual audio seek/playhead, segment selection, zoom anchor and long-episode endpoints must work without forcing page-level vertical travel or corrupting segment/source positions. Reopen/Return retains the appropriate viewing context. F owns the viewport, C4 owns actual audio behavior, C6 integration; an existing video scrollbar cannot alone accept podcast behavior.

## Complete podcast creation and editing — requirement update 2026-10-08

This update completes the existing BMP-08 outcome through the existing Shared
media and Artifact owners. It does not create a second audio engine, player,
timeline, store, Evidence owner, AI service or permission path. This document
update does not change frontmatter or promote any design, implementation,
runtime or acceptance status, and does not dispatch or resume F or C1–C6.

The earlier note that live recording was postposed is superseded for the product
target by P0-C below; it remains a truthful description of that earlier
presentation snapshot only. Podcast Read Aloud remains a transient text preview:
it is not recording, an episode, generated audio, an audio Artifact or proof of
playback. Script changes never claim to change already recorded sound.

### P0-A — actual audio playback

Import or record authorized audio through existing Source/Permission owners and
play the actual returned bytes in the shared player. Support pause/resume,
seek, replay, timecode and the current segment/source relation. Playback must
identify the exact audio and version; unavailable media, decoder errors,
permission denial and interruption remain honest states. Reuse the existing
player and lifecycle owner rather than creating a competing player.

### P0-B — actual waveform

Render a time-aligned waveform from decoded samples of the exact authorized
audio, with horizontal zoom/pan and selection aligned to the real playhead and
timeline. The waveform is not a placeholder inferred from text, guessed
duration, random bars or a decorative asset. Keep the text/timecode equivalent
accessible. If sample extraction or the media is unavailable, show an honest
unavailable state and keep playback/editing state truthful.

### P0-C — authorized recording

Provide user-initiated local microphone recording through the current platform
permission and media owners, with explicit permission, record, pause/resume and
stop controls, real elapsed time and recovery after denial, interruption or
device loss. The resulting recording is a source with actual bytes, scope,
rights and version; it is not a final episode until edited, rendered, saved and
reopened. No background or remote recording and no permission bypass. All four
surface roles remain in scope; unsupported device/runtime paths stay
`NOT_VERIFIED` while the applicable behavior is retained for acceptance.

### P0-D — edit and mix

Use the existing Shared Timeline/render owner for real clip placement,
selection, move, trim, split, delete, replacement and multi-track voice,
background music and effect editing. Provide actual per-track/clip volume or
gain, fades, Duck and applicable mix controls such as mute/solo/loop; preserve exact
source ranges and synchronization. Support undo/redo, cancellation,
interruption-safe recovery, actual listening before and after edits, playable
export, immutable parent-linked save and exact reopen. The timeline scrolls and
zooms horizontally across the full episode without unnecessary page-level
vertical travel. It must not lose unaffected tracks, clips or script bindings.

### P1-E — audio quality and transcript

Keep manual transcript entry and correction fully usable without an AI provider.
Support the approved noise-reduction and loudness workflow with actual processed
audio and measured results; never claim a quality change from a control or
preview alone. ASR is optional and, when available, goes through the existing
C2 AI Gateway and its model/version, rights, Permission and evaluation rules.
Provider/model unavailability does not disable manual transcript work. Preserve
source transcript, machine suggestion and human correction as distinct,
versioned records; never make ASR output truth by itself.

### P1-F — script and audio binding

Bind the existing Brief/script, paragraph or segment, speaker, chapter,
transcript, timecode, actual audio clip and exact versions through current
Task/Brief/Artifact owners. A script edit changes script intent only; it does
not modify audio bytes or transcript automatically. Show the affected segment
and let the user record, replace or edit only the audio range that requires it.
Save a new child version, retain prior script/audio and their source lineage,
and restore the binding on reopen. Scope, rights or source changes trigger a
fresh owner check and isolate stale versions.

### Real podcast task acceptance

Verify both independent creation and optional continuation. Use a user-authored
creative Brief or an explicitly inherited business/research Brief with permitted
imported or user-recorded audio. In continuation, retain the same source/goal
without re-entering or reselecting it; in independent creation, impose no prior
business task. Then listen to the actual audio
-> inspect its real waveform -> edit/delete one selected passage and mix voice,
music or effects -> adjust and verify audio quality -> enter or correct a
transcript manually, with optional Gateway ASR only if actually available ->
verify script/speaker/chapter/timecode bindings -> export and play the actual
episode -> formally save -> close and reopen the exact project/result -> change
one passage, undo/redo and save/re-export a child while preserving the parent.
Exercise source revocation, scope change, permission denial, missing platform
voice/device, interruption and render/save failure without false success or
loss of recoverable work.

Web Workspace, Desktop App, Mobile Companion and Public Website remain within
their existing four-surface roles and the applicable review/acceptance scope.
Operational editing uses the authorized workspace surfaces; the Public Website
only presents approved public episodes and does not expose private editing or
recording. Retain the full user outcome on every applicable surface and record
unexercised platform/device behavior as `NOT_VERIFIED`, not as a reason to omit
it. These requirements do not promote the existing `DESIGN_READY` presentation
field or the `BLOCKED` business decision; current status fields remain unchanged
until their own evidence gates pass.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 把授权来源变成可审阅脚本及可编辑播客音轨。
- **屏幕专属呈现：** 脚本、来源、rights、音轨和发布状态分层；横向拖动时间轴
- **来源、范围与版本连续性：** 同Brief/来源/audio version连续；本地Read Aloud不等于成片
- **四端差异：** Web/Desktop脚本与音轨并列；Mobile分段查看；官网只放授权成片
- **失败与恢复：** 源/版权未知不导出；scope/文本变更停止本地朗读
- **补充验收：** 保存重开实际工程，改一段不损其它段；无回执不称完成。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
