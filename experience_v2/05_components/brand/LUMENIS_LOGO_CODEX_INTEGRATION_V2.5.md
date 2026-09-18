# LUMENIS Logo / Launch — Codex Integration V2.5
面向后端接入：品牌与启动是**纯前端呈现组件**，不依赖任何 API/DB；Codex 只负责在正确时机挂载与切换，不改写视觉。

## 1. 运行时文件（不要重写）
- `assets/brand.js`：`window.LumBrand = { mark, lockup, mount, favicon, word }`
  - `mark()` 返回 symbol SVG（currentColor）；`lockup({variant:'standard'|'korean'|'symbol', locale})` 返回 lockup HTML。
  - `mount(root)` 自动渲染所有 `[data-lum-brand]`（值=variant，`data-lum-locale` 可覆盖）；MutationObserver 自动挂载新增节点。
  - `favicon()` 注入 data-URI SVG favicon（ink + Icy Point）。
- `assets/brand.css`：`.lum-brand*` 尺寸/排版 + `.lum-launch*` 启动关键帧。
- `assets/launch.js`：`window.LumLaunch = { play, auto, reduced, lowPower }`。

## 2. 挂载约定
- 顶栏/抽屉/登录页用 `<span data-lum-brand="standard"></span>`（韩文页 `data-lum-locale="ko"`）；小尺寸用 `data-lum-brand="symbol"` + `.lum-brand--sm`。
- 颜色继承 currentColor / token，随 `.lum-app[data-theme]` 自动黑银↔白银，**不要内联 fill/stroke 颜色**。
- 启动遮罩必须在 `.lum-app` 容器内（已修复），否则拿不到 token。

## 3. 启动时机（与数据解耦）
- 应用壳渲染后调用 `LumLaunch.auto()`：每会话一次（sessionStorage `lum-launched`），lowPower(hardwareConcurrency≤4) 自动 short，reduced-motion 自动静态。
- **不得**等待 AI/数据/网络后才播放，也不得用启动遮罩掩盖加载失败；遮罩到点自移除，应用可交互不被阻塞。
- 路由内再进入应用用 `LumLaunch.play({short:true})`；切换语言在 play 时传 locale。
- 登出/切换账号如需重播，调用 `play()` 并自行管理 sessionStorage。

## 4. 可访问性 / 性能 / 硬件准备
- 遮罩 `aria-hidden="true"`（品牌装饰，不读屏）；reduced-motion 必须静态（已内置）。
- 仅 opacity/transform；DPR≤2；不在启动期跑 WebGL 球体（启动用静态 SVG Mark，球体是进入后 dock FAB）。
- 静态资源（SVG/PNG/mp4/gif）路径见 `05_components/brand/{svg,png,launch}`；运行时默认用 CSS/SVG 组件，mp4/gif 仅用于宣传/演示与无法运行 CSS 的外壳。

## 5. 后端/原生壳对接点
- 原生（Electron/移动壳）如要用视频启动：优先 mp4（H.264 yuv420p），并提供 reduced-motion 静态图（launch/frames/S6.png）；冷启动后仍以 CSS 组件为准，避免双启动。
- 未来硬件触感：启动落定（S4 mark settle / S6 定格）可触发一次 `LumHaptics.impact('settle')`（轻），由 haptics 层统一抽象，不在 brand 内直接调振动。

## 6. 禁止
- 不得用位图替换矢量 Mark；不得硬编码颜色；不得把旧彩色/手写 logo 接回；不得让启动动画阻塞或依赖后端返回；不得两个 AI 同改 brand/launch 文件（豆包为 Experience Owner，改动需经其）。
