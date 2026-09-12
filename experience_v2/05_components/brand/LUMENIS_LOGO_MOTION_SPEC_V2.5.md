# LUMENIS Logo / Launch Motion Spec V2.5
实现位置：`10_prototype/assets/brand.js`（结构）、`brand.css`（关键帧）、`launch.js`（编排）。组件化，不写死单帧图片；颜色全部继承 token，深浅自动反相。

## 1. 时长（红线：完整 2.1s 区间 1.8–2.4；短版 0.6–0.9）
| 版本 | 总时长 | 组成 | 触发 |
|---|---|---|---|
| Full 标准/韩文/白银 | 2.3s（在 1.8–2.4 区间内） | drop .72 + sea 1.06@.72 + mark .62@1.46 + word .5@1.72 + bg fade@2.02 | 冷启动一次/会话 |
| Short 纯图形 | .92s（在 .6–.9 略上，mark .4@.04 + word .34@.2 + bg .9） | 再进入、lowPower | 手动/低性能 |
| Reduced-motion | .7s 静态停留后 .3s 淡出 | 无位移、无 drop/sea | prefers-reduced-motion |

每会话仅自动播放一次（sessionStorage `lum-launched`）；与数据加载解耦，**绝不阻塞**应用启动与交互（定时器到点移除遮罩）。

## 2. 缓动（取自 motion token）
- drop：cubic-bezier(.45,0,.7,1)（重力下坠）。
- sea / bg：--lum-ease-standard = cubic-bezier(.2,.7,.2,1)。
- mark settle：--lum-ease-emphasized = cubic-bezier(.2,0,0,1)，60% 处 scale 1.02 微回弹后归 1。
- word：ease-out。

## 3. 动画属性（性能红线）
仅使用 `opacity / transform(translateY,scale) / width(海平线，单一装饰线)`；不用 top/left、不触发 layout 抖动；GPU 合成。`@media (prefers-reduced-motion:reduce)` 全部降级为静态。

## 4. 编排 API（Codex 契约）
```
LumLaunch.play({ locale:'zh-CN'|'ko', short:false })  // 返回遮罩根节点，到点自移除
LumLaunch.auto()                                      // 冷启动自动一次（lowPower→short）
LumLaunch.reduced / .lowPower                         // 只读判定
```
- 遮罩挂载于 `.lum-app` 内部（V2.5 修复：挂 body 会拿不到 token 导致动画失效），z-index 99999，fixed inset-0，背景 var(--lum-bg)。
- locale 决定字标：zh-CN→序境，ko→서경；拉丁文始终 LUMENIS（mono，letter-spacing .56em）。
- 主题：继承 `.lum-app[data-theme]`，light=黑银 mark、dark=白银 mark，Icy Point 分别 #4FC4E8 / #6FD6F2。

## 5. 导出规格（交付资产）
- SVG：mark / mark-silver / logo-standard(±silver) / logo-korean(±silver) / favicon，viewBox symbol 48×64、lockup 232×64。
- PNG：symbol 24/32/64/128（ink+silver）、lockup 128、app-icon 512（黑铬/白银圆角金属底）。
- 视频：mp4(H.264)、gif(480w/12fps)、webm(源)；reduced-motion 静态 mp4/gif。
- 禁止把启动动画导出为整屏位图当运行时背景；运行时只用 CSS/SVG 组件。
