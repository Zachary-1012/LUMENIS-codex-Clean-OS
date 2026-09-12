# PSD = BLOCKED（显式声明，非伪造）

依据主方案 §14.1 / §32：执行环境未安装 Adobe Photoshop，无法真实生成**分层可编辑 PSD**。
按规则回传 `PSD = BLOCKED`，保留分层可编辑源（HTML/CSS/JS/SVG/JSON Contract），**绝不**把改后缀的位图冒充 PSD。

## 状态
- PSD 可编辑母版：**BLOCKED（环境无 Photoshop）**
- 替代交付（已全部具备，且这些才是 Codex 开发真相）：
  - 结构化、可编辑样式源：`10_prototype/assets/*.css`（tokens/base/components/shell/optical/motion）
  - 设计令牌机器表：`04_design_system/design-tokens.json`
  - 矢量图标（自绘 stroke SVG，可改色/改尺寸）：`10_prototype/assets/icons.js`
  - 每屏 ScreenSpec（结构=分层来源）：`07_screens/<ID>/<ID>.spec.json`
  - 高保真位图母版（1440/1024/390 精修 + 8 视口回归）：`14_visual_regression/shots/<ID>/`
  - 可运行原型（即"活的分层母版"）：`10_prototype/index.html`、`07_screens/<ID>/<ID>.html`

## 主方案要求的 11 个 PSD 分层 → Experience V2 对应来源（非扁平）
| PSD 层（§14.1） | Experience V2 可编辑来源 |
| --- | --- |
| 01_CONTEXT | shell 侧栏/主体上下文 `assets/shell.css` + `data/shell.js`、SubjectContext |
| 02_NAVIGATION | `.lum-shell` rail / topbar / mobile dock（shell.css + shell.js） |
| 03_WORKSPACE_HEADER | `.lum-page-head`（serif 刊头 + 序之线）base.css / sections.R.head |
| 04_DECISION | insight / action-panel 组件（components.css, sections.R.insight/actions） |
| 05_ANALYSIS | chart/table 段（sections.R.chart/table，Icy 仅数据可视化） |
| 06_EVIDENCE | evidence rail / chain（sections.R.evidence，序轴节点） |
| 07_ACTION | action bar / buttons（components.css `.lum-btn*`，Action 四分类） |
| 08_CONTEXT_RAIL | 右侧工作上下文抽屉（shell context drawer） |
| 09_OVERLAY | drawer/modal/sheet/optical（optical.css，HIGH→STANDARD→SOFT_GLASS→OPAQUE） |
| 10_STATES | `07_screens/<ID>/<ID>.state-board.html`（13 态 + ready/disabled） |
| 11_ANNOTATION | spec.json / viewmodel.json / state-board 标注 |

## 如后续需要真实 PSD
在装有 Photoshop 的环境，以 1440 主母版为底、按上表 11 层从 CSS/SVG 反向分层导出即可；此为可选视觉母版工作，**不阻塞 Codex 接后端**（Codex 只需要 HTML/CSS/JS/SVG/JSON Contract，已齐备）。
