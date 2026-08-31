# UI Evidence Process（UI 设计评审与证据流程）

> v1.0 2026-08-31。目的：根治“昨天改的 UI 怎么没了 / 文档说完成但页面没到”。以后**所有 UI 开发必须经过固定门禁，每一步留 Evidence**，与 DCC Release Gate、Feature Final Verification 对齐。本文件只定流程，不改代码。

## 1. 七步门禁（不可跳步）
设计评审 → 组件确认 → 页面确认 → 开发 → 视觉测试 → 性能测试 → 上线。
| 阶段 | 进入条件 | 产出（Evidence） | 通过标准 |
|---|---|---|---|
| 1 设计评审 | Design System + Page Map 已冻结 | 设计评审记录、Token 引用清单 | 无硬编码色值/私有样式；IA 覆盖全部 Feature（含占位） |
| 2 组件确认 | 评审通过 | 组件规格勾选、组件状态矩阵 | 组件来自 COMPONENT-SYSTEM，状态齐全（含 disabled 原因/空态） |
| 3 页面确认 | 组件就绪 | 页面线框/区块与组件映射表 | 区块都能映射到既有组件；不新增重复组件 |
| 4 开发 | 页面确认 | commit SHA、改动文件清单、一任务一 commit | 只动 UI 层，同期不改业务逻辑/DB/采集；Staging(8301) 进行，生产 8201 不动 |
| 5 视觉测试 | 开发完成 | 六断点截图 + 全状态截图 | 390/430/768/1024/1280/1440 无横向溢出/重叠/截断；深浅文本对比达标 |
| 6 性能测试 | 视觉通过 | Lighthouse/首屏与交互指标 | 无远程大字体/大动画库；动效只改 transform/opacity；无明显长任务 |
| 7 上线 | 6 步全过 | Release 记录 + 回滚点 | 视觉/功能回归通过，可一键回滚 commit |

## 2. UI Evidence 记录结构（每次 UI 变更一条）
| 字段 | 内容 |
|---|---|
| ui_evidence_id | UI-EV-日期-序号 |
| design_version | 对应 Design System 版本（如 v1.0） |
| feature_id | 关联 FEATURE-xxx（可多） |
| page / component | 页面 / 组件名与组件版本 |
| commit | 变更 SHA（可回滚点） |
| screenshots | 六断点 + 各状态截图路径（统一存 docs/UI/evidence/） |
| states_covered | default/hover/active/focus/disabled/loading/empty/error |
| a11y | 对比度/键盘/焦点环/颜色非唯一信息 勾选 |
| perf | 首屏、交互响应、是否仅 transform/opacity |
| result | PASS / FAIL + 问题与修复 commit |
| reviewer / date | 评审人 / 日期 |

## 3. 防覆盖机制（针对 22 CSS 层叠根因）
- 单一 Token 真相：只允许 `zbip-tokens.css` 定义变量，组件只引用语义 Token；grep 检查不得出现裸色值。
- 旧 CSS 退役走“引用扫描 → 标记 DUPLICATE/LEGACY → 六断点回归 → 移除 link → Evidence”，不直接删文件、不新增 fix-final 式覆盖层。
- 每次合并前对比上一版截图（视觉回归），发现“旧样式反覆盖新 UI”即 FAIL 并定位层叠顺序。

## 4. 视觉测试最小清单（逐页）
六断点各 1 张；关键状态（正常/空/加载/错误/无权限/危险确认）各 1 张；Auth 三分支（登录失效/需验证/IP 熔断）各 1 张；移动端 Auth 扫码恢复流 1 套。截图命名 `页面_断点_状态.png`。

## 5. 与功能验收的关系
UI 完成不等于 Feature 完成：Feature 的 ACTIVE 仍以代码+Owner+运行路径+测试+Evidence 五要素为准（见 FEATURE-FINAL-VERIFICATION-MATRIX）；UI Evidence 只证明“界面层达成”，不得用界面截图替代后端/数据证据。
