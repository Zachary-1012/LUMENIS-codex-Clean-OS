# LUMENIS 启动动画 Storyboard V2.5（S0–S7）
叙事保留旧 Brief 哲学：芥子纳须弥 · 一点开境（A Point Opens A Realm）——小→大→归一。材质重制为单色金属 + 唯一 Icy Point，不再使用旧版彩色液态海。

时间轴（完整版 2.3s，关键帧来自真实录制 `launch/mp4/standard-full.mp4`，分镜图在 `launch/frames/S0..S7.png`）：

| 帧 | 时刻 | 名称 | 画面 | 动效 |
|---|---|---|---|---|
| S0 | 0.10–0.12s | Point 出现 | 铂金雾底，顶端一枚 Icy 点（--lum-c-icy-500）出现并微亮 | drop opacity 0→1，scale .6→1 |
| S1 | 0.42s | Point 沿序轴落下 | Icy 点沿中轴（序轴）向下坠落 30→150px | lum-drop 0.72s，cubic(.45,0,.7,1) |
| S2 | 0.76s | 海平线展开 | 触点处向两侧展开一条 1px 金属海平线（界 Boundary 的水平投影），宽至 64–72vw | lum-sea 开始，width 0→260→300 |
| S3 | 1.10s | 海平线回收 | 海平线向中心收束（Return 归点），同时 Lumen Mark 容器将显 | sea width→0、opacity→0 |
| S4 | 1.50s | Mark 落定 | 双层 Boundary + 序轴 + 内核的 Lumen Mark 自 scale .86 落定（60% 处 1.02 微回弹） | lum-mark-settle .62s @1.46s emphasized |
| S5 | 1.76s | 字标进入 | 「序境 / 서경」display serif 与 LUMENIS mono 宽字距自下方淡入 | lum-word-in .5s @1.72s |
| S6 | 2.05s | 整体定格 | Mark + 字标完整、居中、静止，金属对比最清晰 | 全部 forwards 定格 |
| S7 | 2.26–2.30s | 退场进入产品 | 整屏 opacity→0、visibility:hidden，移除遮罩，露出应用 | lum-launch-bg 88%→100% |

## 三版本 × 完整/短版
- **standard-full**：标准中文版（序境 / LUMENIS），完整版，冷启动默认。
- **korean-full**：韩文版（서경 / LUMENIS），locale=ko。
- **standard-full-silver**：深色白银底版本（dark theme 冷启动）。
- **symbol-short**：纯图形短版（.9s，仅 mark settle + 字标），再进入 / 轻量启动 / low-power。
- **reduced-motion-static**：`prefers-reduced-motion` 或硬件并发≤4 时，静态 mark 停留 .7s 后淡出，无位移。

文件：`launch/webm`（源）、`launch/mp4`（H.264 yuv420p，全平台/移动端可播）、`launch/gif`（480w/12fps 预览）、`launch/frames`（S0–S7 PNG）。运行时实现为纯 CSS/SVG 组件（非视频），视频仅作设计交付与演示。
