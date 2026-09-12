# LUMENIS Haptics & Embodied Interaction V2.5
红线：所有可交互表面都要有触感反馈；即使是 Web，也要为未来硬件/具身设备预留物理反馈通道。实现：`10_prototype/assets/haptics.js`（window.LumHaptics）。

## 1. 三层架构（Web 现在可用，硬件未来可接）
1. **视觉/按压层**：CSS :active scale .97（100–150ms），所有按钮/芯片/列表/导航具备。
2. **Web 振动层**：`navigator.vibrate(pattern)`（Android Chrome 等支持；iOS Safari 按设计为 no-op）。
3. **具身桥接层**：每次 impact 同时 `dispatchEvent(new CustomEvent('lum:haptic',{detail:{channel,verb,at,...}}))`，未来原生壳/可穿戴/手柄/触觉屏监听该事件驱动真实致动器，**UI 代码零改动**。

## 2. 语义通道与品牌动效动词对齐
| 动词 Verb | 通道 Channel | vibrate(ms) | 触发场景 |
|---|---|---|---|
| Touch | press | 12 | 普通按钮按下 |
| —（轻） | tick | 8 | 步进、数值微调、ai-step |
| Shift | select | 10-24-10 | tab/segmented/视图切换 |
| — | toggle | 9 | 开关 |
| Return | nav | 14 | 导航/返回主体 |
| Open | confirm | 12-30-12 | 打开境层/确认弹层 |
| Trace | evidence | 10 | 沿证据链行进/证据锚点 |
| —（结果） | success | 14-36-26 | 成功完成 |
| — | warning | 20-40-20-40-20 | 警告 |
| — | error | 44 | 错误/失败（单次、不刺耳循环） |
| Settle | settle→tick | 8 | 数值 count-up 落定、启动 mark settle |
| — | heavy | 30 | 高风险/重大动作 |

调用：`LumHaptics.impact('confirm')` 或直接用动词 `LumHaptics.impact('open')`。自动委托：pointerdown 命中 button/nav/chip/action-item/dock/list/[role=button]/tabs/segmented 即触发；监听 `lum:toast`（success/error/warning）与 `lum:ai-step` 自动反馈。

## 3. 安全与降级（硬规则）
- 总开关 localStorage `lum-haptics`（on/off，默认 on）；`setEnabled(false)` 全关。
- `prefers-reduced-motion: reduce` 时**强制关闭**振动（视觉动效也降级）。
- 永不抛错：无致动器/不支持 API = 静默 no-op；iOS Web 无振动是已知限制，由视觉按压与未来原生壳补足。
- 高频操作（拖拽、连续滚动）不得连续振动；按动作语义而非按帧触发，避免疲劳。
- 危险动作（data-risk=high / effect-risk）用 warning 双通道，成功/失败给结果触感，形成闭环。

## 4. Clean-room 研究（只学机制，不抄实现/不抄视觉）
- **Apple HIG（Haptics）**：反馈分 Impact（轻/中/重，对应物理材质）、Notification（success/warning/error 节奏型）、Selection（滑块/选择器的轻 tick）；反馈必须与视觉/声音**同步**、强度与信息重要性匹配、避免过度。→ 落到本系统 press/select 与 success/warning/error 节奏型；语义优先而非设备名。
- **Tesla 实体反馈哲学**：座舱以最少实体控件 + 明确到位反馈建立「机械确信」，触控/拨杆有确认段落感。→ 落到关键动作 Open/confirm 的双脉冲「到位感」，以及 EFFECT 动作 confirm 后的结果闭环。
- **Nothing Glyph 跨媒介**：同一语义元素贯通光、声、振，用户不看 Logo 也能识别状态。→ 落到「一个 channel 同时驱动视觉状态 + lum:haptic 事件」，为未来光/声/震同源预留；Lumen Core 状态（idle/processing/done/error）与触感通道一一对应。
- 共性结论：**触感是状态语言的一部分，不是按下的奖励音效**；强度随任务频率递减；必须可关。

## 5. Codex 硬件契约（具身预留）
- 业务代码只调 `LumHaptics.impact(verb|channel, payload)` 或派发/监听 `lum:haptic`，**禁止**直接散落调用 navigator.vibrate（保证单一抽象层、可统一关闭/换致动器）。
- 原生壳（Electron/移动端/未来具身设备）在 window 上监听：
  `window.addEventListener('lum:haptic', e => actuator.play(e.detail.channel, e.detail))`；
  detail 至少含 `{channel, verb?, at, source?, target?}`，可扩展强度/时长但不改事件名。
- 后端不参与触感；触感为纯表现反馈，不得作为业务状态的唯一来源（状态以数据/State 语义为准）。
- 移动验证：Android Chrome 实测 press/select/success；iOS 记录为「视觉+桥接，系统振动不可用」（UNKNOWN 不伪造）。
- 与启动动画：S4 mark settle / S6 定格触发一次 `impact('settle')`（极轻），reduced-motion 时不触发。
