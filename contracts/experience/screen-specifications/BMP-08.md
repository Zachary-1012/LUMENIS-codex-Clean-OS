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

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

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

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-08)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：播客制作室全链（规划 §14 P1–P12、G184/G79/G107/G128）


**4. States**
空 / 导入中 / 转写中（进度，可取消）/ 模型不可用（显示原因，可导入已有字幕稿继续）/ 剪辑提议待确认 / 母带不达标（显示实测值与差值，不自动二次施压）/ 版权未知（导出提醒）/ 数据缺失 / 权限不足。

**9. Acceptance**
- 删词剪点误差 ≤1 帧；词内零切；撤销还原原稿与音频。
- 母带实测 -16 LUFS ±1、真峰 ≤ -1 dBTP，数值显示在界面。
- 脚本事实句 100% 有来源或标 UNKNOWN；配音仅用户开启，声音克隆需本人授权。
- 发布包 RSS 含 podcast:transcript / podcast:chapters 并通过校验；发布需确认。
- 新建→编辑→试听→导出→重开修订完整可走通（G55）；三语；无主体写死。

**增补（2026-10-14 全文读码）**
- 播放器全工作区唯一；点逐字稿句子→跳播；点时间轴标记→打开对应故事节点/证据；点故事节点→筛选稿与素材。
- 选题卡：十信号逐项显示；缺项显示「需补输入」并列出缺哪几项，不出分。
- 嘉宾卡：三标准 Gate 勾选（人工），未过不进入提纲。
- 稿件：原文/校对双视图切换；改稿提示「改稿不改音频」。
- 状态：加载/空/部分/错误/重试/恢复中/成功 均有设计；运行不回传显示「无返回」，不静默。
- 研究阅读器：结论→发现→证据（侧抽屉）→模式与假设→验证状态→可迁移→不可照搬→来源。

### Existing contract — Actions, authorization and effects

- `podcast:draft` saves a local request draft; it does not create a script or call an executor.
- `podcast:render` saves a local render-request draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no audio/cut is generated or claimed ready.
- Publish and rights changes are outside this slice.



### 三语状态文案

| Key | zh-CN | en | ko |
|---|---|---|---|
| loading | 加载中 | Loading | 불러오는 중 |
| missing | 数据缺失 | Data unavailable | 데이터 없음 |
| unavailable | 暂不可用 | Currently unavailable | 현재 사용할 수 없음 |
| denied | 无权执行此操作 | This action is not permitted | 이 작업 권한이 없습니다 |
| retry | 重试 | Retry | 다시 시도 |
| cancel | 取消 | Cancel | 취소 |
| save | 保存 | Save | 저장 |
| revise | 修订 | Revise | 수정 |
| reopen | 重新打开 | Reopen | 다시 열기 |
| recover | 恢复 | Recover | 복구 |
| return | 返回原任务 | Return to task | 원래 작업으로 돌아가기 |

全部新增标签、说明、确认及读屏名称须沿现有三语键实现；上表仅通用状态，不证明全产品翻译/运行完成。逐屏验收覆盖 zh-CN/en/ko、200%字号、键盘/读屏和减少动态。

## 5A. Web Workspace composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：播客制作室全链（规划 §14 P1–P12、G184/G79/G107/G128）

Web：稿件、音轨和检查器可分栏或逐项展开；录音先获浏览器授权，拒绝不阻塞导入/手动编辑；试听与后台渲染状态分开，刷新恢复已保存工程。 录音需浏览器麦克风授权，未授权时只可导入。


## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：播客制作室全链（规划 §14 P1–P12、G184/G79/G107/G128）



### Existing contract — Accessibility and localization

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


### 全项具体工作合同：转录与逐词/填充词/静音提议

绑定transcript artifact/hash、source hash、timeline revision、音轨及选中word IDs；精确审批另由原EDL/Permission owner核验。转录不可用保手工稿和剪辑；取消不提交新稿，恢复核同一音频。验收填充词误匹配、零时长/未对齐词、选流变化、静音穿词、边距、旧转录哈希、取消与迟到回调、采用/撤销/保存重开保持实际音画边界。

词稿保持主面，候选在右侧“待删”清单；点击候选只定位原音频和受影响轨道，底部固定“试听原段/试听提议、排除、采用所选、取消”。填充词栏与静音栏分开，未知词时用文字状态而非补时码。Desktop/Web多轨同步；iOS句/候选单项审阅与允许轻剪，精剪续接同版；官网只演示真实链。UI适配只把当前候选与上下文并读，不自动删词，不挤走当前选词/播放头。

具体操作与恢复：转录入口先选实际音轨、语言提示和已可用运行时，显示规范化音频与原PTS映射；转录完成只是派生词稿，不代表说话人分离、全语种质量或正式听审。源转录和已渲染工程转录各标输入媒体/工程版本，不能混用时间码。普通改字、仅删字幕、逐词删音视频三种动作分开。
逐词删除逐条给原词/起止/实际删去区间；填充词候选允许编辑本次词表、检查匹配词及排除；静音候选显示阈值/实际静音区间/保留边距及被影响片段。试听原版/提议版后明确选择采用范围；无词级对齐、跨词边界、过期转录或原稿变更拒绝采用并保用户选择。


### 全项具体工作合同：封面、B-roll及音频可视包装

取消候选生成/插入预览不改原Timeline，采用后原父版仍可重开；源变/字体缺失/文本溢出/无匹配/权利未知/复杂轨道拒绝/格式验证失败各有具体说明。验收真实取帧覆盖、文案子串但语义未核、零相似度、顺插导致时长增加、字幕或音轨存在时不误允、音频选段边界、取消/重开与字形检查。

封面台用候选图组＋当前正文与三要素输入，候选边注时点/方法/覆盖；B-roll用素材列表＋标注/命中词＋前后时间线对照，清楚写“总时长增加…，后续音画一起后移”；音频包装用选段播放器、起止控件、标题/引语和实际波形预览，再选保存/导出。Desktop/Web并读，iOS逐候选与单片段审阅；官网仅有证输出。UI可根据候选数/屏宽自动排比较构图，内容封面或波形成片本身不计UI AIGC；布局提议不变所选片段。

具体操作与恢复：封面候选展示真实取帧时点、场景变化或均匀时间候选来源及测量覆盖，三要素文案逐项可编辑并对照正文；精确子串匹配仅是文字检查，仍需人工确认兑现，不能称语义最佳封面或CTR预测。B-roll清单显示用户素材标注、命中词和词项相似度，明确未做视觉语义核验且不自动获权、不联网找片。
当前B-roll插入预览仅支持无叠层单视频轨的静音顺插：先显示插入位置、源入/出点、增加时长及后移的原片和原音频；它不是盖在旁白上的覆盖画面。复杂工程不支持时指出原因并保完整叠层目标OPEN。音频图/引语卡从用户选定0.2–180秒片段、标题、引语和真实音轨产生，波形来自实际音频；引语只按用户文字显示，不冒转录已核。


### 全项具体工作合同：播客选题、嘉宾、前采和节目分析

对应唯一草图BMP-08“复盘”构图：情绪/洞察节点按真实origin显示，当前实现为用户标注派生，未执行AI推断。添加selection_required/manual_gate_blocked及未覆盖日历年份状态。节目分析当前单音轨且≤600秒；超限不截成完整节目。验收三Gate unknown、无匹配词、用户原稿不强制Gate、缺信号无分、无标注与空标注、版本不符、超限、来源撤回、取消/修订/重开。

选题面顶部日/周/月和日期，主区题目清单→十信号/缺项→来源/笔记；嘉宾面左右资料比较，中间选择及三Gate，进入前采后原提纲正视可编辑。复盘面用真实音轨/节点表，密度旁写“用户标注计算”，未测指标保“未提供观测”，不画留存假曲线。Desktop/Web并读；iOS记录题/审Gate/听节点，复杂编辑续接同版；官网限定真实例。UI适配按缺信号/待选嘉宾/标注节点切换专用检查器，不替人打Gate、不把模板变原创或自研AI。

具体操作与恢复：日/周/月选题库分别显示计划日期、题目、十信号及缺项、来源、人工备注和热度未知，2026营销日历仅参考且不自动排期；当前代码的日周月投影只是日期筛选，不能将其标成已完成周主题聚类/月洞察。嘉宾比较显示用户提供的领域/过往节目/观点、共享词项和来源，词法相似度不冒独立核实或自动选人。三Gate每项可选通过/不通过/未知并写理由，未知不当通过；选人后前采明线/暗线、追问、人工答案、研究维度及可选录制SOP均可编辑，未有真实答案不代嘉宾作答。
节目分析先列真实音频版本/解码时长和用户故事、冲突、揭示、情绪、洞察、引语、问题标注。当前密度由USER_ANNOTATION/时长计算且没有模型推理，不标为AI识别情绪峰。无标注是缺失，有空标注列表才可为实际0；问题质量、留存等未有观察继续缺失。
完整G79/G184长播客、留存、采访质量与转化复盘仍是原产品目标，当前单轨600秒及缺观测是实现边界，不是删范围的理由。超限时保原音频、用户手稿和人工阅读，待原Owner完成完整接线；不得虚构自动分段/拼接服务绕过限制。


### 全项具体工作合同：本地成品语音与朗读的区分

字段由实际toolchain/voice owner返回，无工具、语言不支持、文本过长、超时、取消、音频校验失败、产物待归档分开。取消清本任务临时文件并保稿/原音轨，换文本版本使旧试听待重做；重开读取实际输出hash，不自动再生成。验收Flite语言边界、eSpeak可用性、合法WAV、试听停止、取消、不自动入轨、失败保旧版及Web/Windows/macOS/iOS单独核质量。

BMP-08配音页保原稿、实际引擎/语种/音色能力和试听/停止/采用素材；候选声轨与原音轨AB对照，标合成方式及未验质量。SYS-05仅保朗读语言/速率和当前会话控制，入口文案避免两者混淆。Web/Desktop/iOS各显示真实本机/已绑定Core可用能力，手机不因服务器支持便宣称离线合成；官网只述已核范围。UI适配根据是否已有可试听候选重组稿/播放器，不替用户换音色或把合成声音当UI创新。

具体操作与恢复：本地语音制作作为既有可选配音动作，先显示实际已安装引擎/音色/支持语言、输入文本和本次输出限制。当前Flite只支持英语和有限已安装音色；eSpeak NG共振峰适配接受中/韩/英，质量与各端仍未验，不冒自研模型或人物声音克隆。用户明确生成后得到可试听WAV候选，确认采用才作为新素材进入工程；不默认下载工具/权重、不换外部API。系统Read Aloud仍只是当前文本的本机试听，不保存成品、不自动入轨。


### 全项具体工作合同：真实波形、显式母带/降噪与交付编码

状态区分源pre-mix已测、范围外未测、缺工具/音轨、线性目标不可行、降噪未开启、处理候选待采用、编码完成但校验失败。取消只当前处理，原音频/已保存输出不变；继续前核输入版本。验收60秒范围/多流选流、静音、不可行真峰、降噪主动启用与参数边界、AB停止/切版、重复处理不叠加、编码后重测失败、取消/冷开。完整长节目制作目标保留，局部波形/600秒分析不是全节目验收。

音轨顶栏选择“原源/处理候选/母带/交付副本”，真实波形区标源/范围；右侧响度检查器有目标、输入/输出值、试听原版/处理版及采用。降噪独立开关和两参数不与响度混成一键美化。交付区按编码→校验→文件读回逐步列结果。Desktop/Web并读检查器与音轨；iOS试听和已支持参数审阅，未实现处理明确续接；官网有证样例。UI适配因当前在听审或看失败而展开相应检查器，不能改变音量/参数或播放头。

具体操作与恢复：波形标实际源媒体、音轨和测量区间，当前PCM波形查询最多60秒；源pre-mix波形不冒最终混音或整节目已测。超出当前测量范围明示未测，保真实播放器和人工定位，不以装饰波形填满。
母带处理需用户明确选择当前支持的-16/-14/-23 LUFS目标，显示处理前后实测响度/真峰、目标与线性可行性；静音不可测、动态范围或真峰不允许线性达到目标时给具体失败原因，不暗改动态处理。FFT降噪单独默认关闭，启用后可调降噪量3–18dB和噪声底-80至-20dB，先AB试听，声学测量变化不等主观质量提高。原声、降噪、母带保持可辨版本，不重复叠增益。
MP3/M4A交付副本显示编码、全解码校验、时长、响度/真峰和文件读回各阶段；母带不被覆盖。编码成功但解码/峰值失败仍未可交付，保原母带和已存工程。


### 全项具体工作合同：播客封面、离线RSS材料和许可署名

取消打包保已验证文件和工程；重试核原revision，不混不同媒体版本。状态：封面字形/溢出、未验审美/平台、RSS仅草稿/缺地址、文件遗漏、来源许可变更、声明未独立核实与发布未执行。验收3000封面实际重开、XML合法但不可发布、四地址缺项/不安全URL、署名hash不符、声明不能变权利、实际clip使用追溯、取消/部分失败/重开。

发布包左为完整文件清单，中间所选封面/字幕/章节/RSS实际预览，右侧“本地已生成/外部待验证/许可声明”分栏；每个缺项有具体去向。封面保文本编辑与前版比较；RSS显示缺地址字段且不把本地相对路径画可订阅链接；署名表可回所用素材。Desktop/Web并读，iOS逐文件/权利审阅与按真实能力分享，复杂交接续接；官网仅真实交付例。UI按缺件/许可问题排列审阅重点，不生成假托管状态，封面图本身不计UI AIGC。

具体操作与恢复：播客封面以最终节目版本和用户标题/副标题/署名文字形成离线3000×3000候选，字形/溢出与实际文件核验分开于审美/品牌/平台接受；只生成固定文字构图不称语义创意或平台已验。
离线发布材料包逐项显示可编辑稿/校对/章节/show notes/feed.xml及音频版本。RSS草稿可以XML合法但仍缺托管地址、可访问性/MIME、平台校验和发布批准；列episode/audio/transcript/chapters缺哪项，所有字段齐也不自动标可发布或已上线。原七件套/完整节目目标继续保留；章节/转录operator-declared不冒ASR已核。
媒体许可栏记录用户声明的素材作者、标题、许可证/来源链接、源版本、变更说明和证明文本，并在交付包给实际工程使用的素材与署名清单。声明格式校验或hash一致不等法律核验、SourceUse准入、代码/模型/声音授权；权利仍unknown时保持原动作边界，不能点声明就绿灯。


### 原要求具体工作合同：成果研究采用、ApplicationTrace与生产准入分账

每项成果在版本/依据详情中提供“本版研究与制作依据”。先显示真实研究采用结论ADOPT/ADAPT/DEFER/REJECT及其人工/Owner出处、理由、未解决问题和具体应用位置；没有记录显示未记录，不由模型补一个采用决定。再按本版ApplicationTrace逐项列learning_asset、pattern、evidence、model_version、prompt_contract_version及准确版本，未使用、未记录和不可读取分开。用户从痕迹返回原件/方法和作品选区，不输入内部ID来完成普通工作。
研究资产的E0 Candidate→E1→E2→E3 Tested→E4 Validated及Production admitted依据原准入Owner原样投影；E1/E2的说明须来自原合同，不临时重定义。该研究阶段与ADOPT研究决定、本地RAW/REVIEWED/VALIDATED/ADOPTED候选状态、交接ACK分列，一者不自动推进另一者。撤回/更版时标受影响成果，旧版仍按当前权限读回；无准入回执不显示已生产采用。

SH-04当前成果右侧“版本与依据”增加可收起的研究采用行，点开后上部采用决定/理由/未知，中部五项制作血缘，底部源→应用段落的已知关系及返回。SH-05所选资产检查器并列“研究验证阶段”“本地参考状态”“生产准入”三条有文字的状态，不画一条自动进度跑道。Web/Windows/macOS并读成果和依据，iOS先成果后单层依据Sheet，保原选区；官网仅有权公开案例。UI自身AIGC可依据真实痕迹组织对读/局部关系图，允许锁定/撤销/简洁；不生成采用理由、未知版本或准入绿灯。

增加逐字段缺失/未使用/撤回/当前不可读、旧成果与新来源版不同的状态。查看/关闭详情无副作用；改变采用记录须用原Owner明确动作/精确版本，未绑定不造控件。验五字段不同版本、模型未参与、旧prompt合同、来源撤回、local ADOPTED但E4/Production未知、取消及冷开同版；研究卡存在不等G7/G11/G91运行完成。


### 原要求具体工作合同：完整播客故事资产链与采访复盘

在同一节目中保Person→Interview→Story→Human Problem→Asset→Platform→Signal→Learning的已有对象引用，用户可从任何已具备稿件/音频进入，不强制八步新建。人物/采访关联为获准资料，故事节点记录原音频起止与用户说明、人类问题为明确人工判断/假设；每个派生章节、短切、金句、人物卡和图文保所用节点、父节目版本及平台包装差异，不复制成片冒平台重做。
采访检查器提供“开头30秒”（不足30秒标实际范围）、问题顺序表、情绪/洞察节点、失败点与补录标记。点一行只定位实际音频/稿件；新增标记保存为人工记录，普通改问题文本不剪声音。产出率/采访质量/留存/转化只用原Owner经核观察与定义/分母，缺观察仍缺。当前单音轨≤600秒解码分析仅人工节点密度，不能拿它替代完整长节目目标；超限保原音频、稿与人工阅读，等待原Owner完整接线，不编自动分段。

节目稿为中心，左侧可收起“人物—采访—故事—问题—资产”关系目录，右侧采访检查器，底部同一播放器/时间线；平台和Signal放选中派生资产的版本详情，Learning只链接真实候选/状态。检查器表列问题序号、原句、时间码、节点/失败标记与来源；“补录标记”不自动录音。Web/Windows/macOS稿和实际声音并读，iOS按节点→定位试听→批注/允许轻改→返回原稿，复杂制作续接同版；官网真实样例。UI自身AIGC可把当前问题和对应节点并读或用同源列表代关系图，不推断情绪真值、重排已录问题或制造产出指标。

验未关联人物/缺音轨、时间码失效、30秒不足、补录后父版变化、节点被删后的派生资产待重审、平台观察未接、600秒超限与长节目人工继续、取消标记/渲染、版本冷开。每类成果保自己的可编辑表示；提交Learning只是候选且须原准入，不用关系图亮灯冒整条闭环。

### 原G107具体终态合同：播客五力与六种合作选择

在嘉宾/合作Brief旁打开合作比较：影响力、内容力、人群力、矩阵力、变现力五列分别有观察/来源/窗口/未知，不压成万能分。合作模式按原方法列冠名贴片、节目定制、播客联合营销、品牌自有播客、整合营销“声音+”、线下活动/IP联名；选择后比较适用目标、所需资源、真实报价/权益、可交付内容和待确认条件。五力资料与模式建议分层，选题关联真实营销节点，选择只保存Brief不联系/采购。

构图：顶部当前品牌可选上下文与选题，中央播客/嘉宾同字段五力表，右侧六模式详情，底部选择理由/待补条件与保存Brief；iOS先单对象五力再两两比较和模式Sheet。

缺受众/播放/报价不补分，模式适配待核或权益未知标明；改节点/预算后列影响，取消保原Brief，保存/重开核同版本；外联和付款不由选择触发。

Public Website仅用获准真实样例说明播客五力与六种合作选择及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按用户目标提出五力证据对照和模式取舍构图，保原始来源、锁定/撤销；不能生成合作事实或擅替用户定模式。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 便利操作合同：CV12 逐词删选连续听审：原句、候选、下一处

适用工作与省步目标：剪口头填充词或明确选中的词时，在同一播放器核前后语意，不为每个候选重新拖时间尺。 关联新增能力：C09, C10, C11, C12；细化J02原有减步与原工作面合同；不是新模块，不增批处理、比较导出、模式复用或独立快捷服务。

原Owner与真实接口边界：POST /api/experience/shared-skills/shared.content_project/inspect 的真实词删候选有word_ids、removed_source_intervals、源/转录hash及parent_timeline_version；当前限单无装饰clip、零起点WAV、无视频。候选不自动采用。 待补：前端待接候选列表→同播放器原句/候选试听→下一待核的导航与状态。若当前渲染链不能提供片段候选音频，明确“候选试听未就绪”，只播原片和展示EDL；不能用跳播原片冒已渲染候选。待核/听过可临时驻留，持久化需原工程版本合同，不新增审核服务。 代码依据：lumenis/shared/content_creation/transcript_editing.py:7–71 _word_edit_context / word_deletion_candidate；lumenis/shared/content_creation/transcript_editing.py:82–147 filler_word_deletion_candidate / project_word_deletion_candidate；experience_runtime.py:3397–3430 shared.content_project/inspect

控件位置与四表面操作：逐词稿为主，选中候选后底部出现“原句”“候选试听”“保留原词”“采用本候选”“下一待核”。上下文长度由用户展开选，边界以实际源时间截断；顺序按原时间，下一处不等采用上一处。按住/快捷键听审需有等价按钮且不覆盖正常文字快捷键。 四表面：官网：有真实声音的去敏可控演示，不能假波形。；Web Workspace：BMP-08/SH-01原稿上就地连续听审。；Windows/macOS：宽屏可并读词稿与同一时间线，音频预览使用真实当前工程。；iOS：单候选Sheet与底部播放器，允许听/批注；复杂工程续接同版，缺能力不画采用成功。 省去：省去逐条拖播放头和重选上下文；省去在词稿与时间线反复切页；省去记住未听候选的人工清单。UI自身AIGC：可把当前候选的真实词/区间/按钮排到易触达位置，不能自行删词、改词界或将人审状态升为已通过。

持久化、权限与错误恢复：听过仅本次导航标记，不等准确对齐已确认；采用继续走原明确批准和新工程修订，绑定父工程/候选/转录hash。多次试听不创建版本；保留原词不删除原音频。 父版或转录变化使旧候选过期，保合法选择待重新生成；无词时码、1/30秒下过短残片、全部音频将被删时保原稿和原声。取消试听停止播放并回原头，取消采用不写工程；音轨不支持则保手工阅读与现有编辑路径。 验收：听下一处绝不自动采用上一处；原句与候选有不同的明确播放状态；不把单WAV当前能力写成完整多轨长节目已支持。当前为研发合同，未实测减步数字，未宣称四端接线完成。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

### Existing SavedWork podcast revision binding (2026-10-19)

The studio can list and reopen existing typed `podcast_episode` SavedWork artifacts
through `/api/experience/saved-work`. The explicit independent-workspace entry
uses the existing Shared workspace scope even when the legacy brand screen read
is unavailable; the brand entry retains the current BMP focus/global context.
Neither entry invents a brand, actor, source grant, or globally authorized read.
The server freshly authorizes each list, reopen and write and all cited sources.

Only freshly reopened `lumenis.podcast-plan` version-1 contracts enter the typed
revision surface. Segment identity is `segment_id`, not visual list position.
Original transcript, source ranges, references, stream selection, retained payload
metadata and citations are preserved. Editing corrected text increments the plan
revision and saves a new immutable SavedWork version using the exact parent
artifact, work identity and expected draft digest. A save is shown as confirmed
only after another authorized reopen returns the expected content and version.

Pending reads can be dismissed without presenting their late results. Pending
writes are not represented as cancellable transactions. Failures retain edits;
retry without an edit reuses its idempotency request ID. Conflicts do not overwrite
the latest version; users may copy their retained revisions before reopening.
Closing dirty revisions asks confirmation. Malformed results, denied requests,
unverified list entries and incomplete pagination remain explicitly distinguishable.

This is transcript-revision persistence, not audio generation or source-fact
validation. `media_lineage=W4_W6_NOT_VERIFIED` remains visible as an audio limitation.
The existing manual/independent creation requirements and legacy studio are
preserved; source-backed typed-plan prerequisites apply only to this revision
path. Initial creation, real audio playback/mixing/mastering/render/export, and
native/device acceptance are not closed by this binding. Flutter/widget tests
require execution on the supported toolchain before surface acceptance.
