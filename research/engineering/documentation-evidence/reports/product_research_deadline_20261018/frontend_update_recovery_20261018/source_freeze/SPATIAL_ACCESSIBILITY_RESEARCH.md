# 空间、物理与可访问性：本轮官方依据

研究日期2026-10-17。下列为官方说明/原生API，项目设计采用是推论，不能称规范替我们选出全局最优。页面说明为解释材料，不把所有建议冒成强制条文。保留现有Experience更严格要求。

- W3C WCAG2.2 SC2.3.3说明（AAA）：交互触发的非必要移动允许关闭，并可跟随系统减少动态。采用到纸层翻转、聚合卡牌转动、跟手视差；关闭后保真实信息和操作，不能将作品内部需要检查的动画预览一并删去。来源 https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html
- W3C APG modal dialog：模态窗口需真实约束背景操作、键盘循环、合理首焦点与关闭返回。采用到冲突/删除/采用检查，长结构先聚焦标题而非让读屏一口读全部；不可逆行为优先安全动作。项目选择单活动模态，普通依据检查优先非模态侧读，避免嵌套确认负担。来源 https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- W3C SC1.4.10说明（AA）：普通内容在等效320CSS宽度重排，二维例外只属于确实需要二维的表/画布区域。采用到文稿、研究正文和卡牌内文；时间轴/比较表可保专用横向视口，但周围说明不能跟着变成双向滚动。来源 https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- W3C SC2.5.7说明（AA）：拖动须有单指点击可完成的替代，仅键盘替代不够。采用到章节移动、片段时间、引用篮与环形探索：选中后位置菜单/前后按钮/数值输入，同时保键盘；直接路径须得到同一合法状态。来源 https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html
- W3C SC2.4.11说明（AA）：获焦控件不能被作者创建内容完全遮挡。项目拟定更严格可见焦点验收，尤其浮动工具、软键盘、底部播放器和设置覆盖；局部光影不能替代focus环。来源 https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html
- W3C SC2.5.8最小目标说明仅作底线参考，不覆盖当前Experience全局44/局部48产品规则；不能把规范24CSS最低限自动套产品所有控件。来源 https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- Flutter SpringSimulation官方API提供弹簧位置/速度随时间与终止条件。接入可复用既有Flutterphysics机制，但质量/刚度/阻尼与手势中断须按当前锁定工具链实测，不将独立JS通过当Flutter验收。来源 https://api.flutter.dev/flutter/physics/SpringSimulation-class.html
- Flutter performance best practices：采用实际profile与重建/绘制范围控制，不把堆叠透明材质或每帧重建全树作为审美代价默认接受。具体设备预算需当前版本和真实任务测量，不据网页给未经测量的加速倍数。来源 https://docs.flutter.dev/perf/best-practices

## 研究转为本产品设计

空间优先表达“当前可操作对象、支持依据、暂存上下文”三层。正文保持可读不透明平面；微透光可用于非事实外围层。选中对象略抬升并有接触阴影变化，真实焦点仍有明确轮廓；不能仅靠z高度/颜色暗示权限或质量。正文编辑期间锁定阅读面，不因鼠标移动旋转文字。高密度/窄屏/低性能/减少动态收敛为稳定平面，信息与直接路径等价。

标准默认待同任务试验选定，不宣称已全局最优。验收同时看任务时间、错误/撤销、焦点丢失、阅读中断、frame-time及首有用结果；个人偏好统一设置，业务页只留任务操作。
