# Motion & Interaction Patterns（动效与交互模式库）

> UI-20260831 配套，2026-08-31。原则：**动效表达意义，否则删除**。所有数值与 ZBIP-DESIGN-SYSTEM §10 一致，这里给“什么场景用什么模式”。只学模式，不引动画库（CSS/原生实现）。

## 1. 时长与缓动（统一标尺）
| 场景 | 时长 | 缓动 | 说明 |
|---|---|---|---|
| Hover 描边/底色 | 120ms | ease-out | 即时反馈 |
| Press 按压 | 100ms | scale(.98) | 触感确认 |
| 开关/选中/状态点变色 | 200–220ms | standard | 状态变化可被感知但不拖沓 |
| Tooltip/Popover | 150ms | ease-out | 快进快出 |
| Drawer/Modal 进 | 300ms | cubic-bezier(.16,1,.3,1) | 减速入场 |
| Drawer/Modal 退 | 220ms | ease-in | 略快退出 |
| 路由/页面切换 | 320ms | fade + translateY(4–8px) | 仅轻微位移表达层级 |
| 列表增量插入 | 220ms | fade+高度展开 | 新数据出现引导视线 |
| 状态点呼吸(关注/风险) | 2000ms 循环 | opacity .4↔1 | 极弱，不干扰阅读 |

红线：无 >400ms 的阻塞转场；无循环装饰动画（状态呼吸除外）；`prefers-reduced-motion:reduce` 时全部降为瞬时（0ms），仅保留状态颜色/文字。

## 2. 反馈模式（操作→反馈→状态→引导）
- 异步操作四态：Idle → Loading（按钮内 spinner+禁用，列表用 Skeleton 保持布局不跳动）→ Success（Toast 3s 或就地变绿点）→ Error（就地错误+可重试，Toast 错误需手动关）。
- 危险操作：点击 → ConfirmDialog（说明后果/影响范围）→ 执行（loading）→ 结果；删除/回滚/熔断重置必须二次确认。
- Disabled：不是灰掉就完，必须 title/就地说明原因（如“未验证平台不可接管”“Ollama 未运行”）。

## 3. 状态变化叙事（以采集风险升级为例，替代弹窗轰炸）
gray 未知点 →（开始采集）green 正常 →（轻度风险）yellow 点开始 2s 呼吸 + 行底色微暖 →（风险升高）orange + 文案“延长冷却中，至 HH:mm” →（300012/IP）red 常亮 + 行进入冷却、停止请求；全程**当前页就地演进**，仅在需要人工时才弹 AuthRecoveryModal。降级路径反向：恢复→健康检查→低频试探→连续成功→逐级回到 green（不瞬间拉满频率）。

## 4. 导航与层级模式
- 单页为主：状态中心、概览、列表都在主区切换；详情用 Drawer 保留列表上下文（Stripe 模式），避免“跳到陌生页”。
- ⌘K Command Menu：⌘K/Ctrl K 唤起，模糊搜“页面/操作/最近对象”，键盘 ↑↓ Enter Esc，分组 跳转/操作/最近（Linear 模式）。
- 面包屑始终回答“我在哪”；返回保持列表滚动位置与筛选状态（URL 同步 query）。

## 5. 加载与空态模式
- 首屏/翻页：Skeleton 保持形状 > 转圈 Spinner；>1s 给提示，>10s 给进度与取消。
- 四态分离：有数据 / 筛选无结果（给“清空筛选”）/ 规划中占位（gray 点+说明，PLANNED/RESERVED）/ 异常（错误码+重试）。**采集异常、登录失效、熔断一律不是“0 条”。**

## 6. 数据与图表交互
- 数字 tabular-nums 等宽，更新时不跳动；迷你趋势线只用语义色描线不填充大色块。
- 图表 hover 显示精确值 tooltip；时间窗 Segmented 切换 220ms 过渡；下钻在 Drawer，不整页跳。

## 7. 移动端交互差异（非桌面缩放）
- 导航：Sidebar→抽屉 + 底部 ≤5 项 Tab；浮层：Modal→全屏 sheet，Drawer→全屏；表格→卡片或横向滚动固定关键列；触控目标 ≥44；手势：左滑出现行操作、下拉刷新、边缘返回；Auth 扫码流在手机端当前页内完成。

## 8. 性能约束
- 动效只改 `transform` 与 `opacity`（不触发 layout/paint 风暴）；避免 box-shadow 动画（用 opacity 伪元素替代）；列表长时虚拟滚动或分页；不引动画库、不远程字体。

## 9. 反例（明确禁止）
大面积渐变流动、背景粒子/3D（zachary_3d 类只作历史保留，不进主界面）、果冻弹跳、自动轮播、多层 Modal 叠 Modal、无意义进度条、用弹窗表达普通状态变化、纯颜色表达状态。
