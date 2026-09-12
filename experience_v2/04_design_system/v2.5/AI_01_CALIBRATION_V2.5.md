# AI-01 Calibration V2.5 — AI 意图入口 / Composer（第一校准母版）
Realm = Intent。AI 不只是聊天框：**conversation + evidence + workspace + action** 的 LUMENIS 原生工作界面。

## 1. 页面目标
从一句任务出发：识别意图 → 检索证据 → 生成可追溯结论 → 形成可执行动作。AI 是增强层，不拥有生产事实。

## 2. 层级（动态 2–4 层，不画流程图）
- L1 Orientation：eyebrow `AI AGENT` + 衬线大标题「AI 意图入口 / Composer」+ 一句边界声明（AI 是增强层）。
- L2 Situation：快捷入口（查看 AI Gateway / 技能中心），发丝 Lumen Line 收束。
- L3 Workspace：Composer（能力→任务选择、输入、引用证据/指定主体/时间范围、发送）。
- L3 Evidence：浮动 KPI 字段（今日已锚定证据、结论可追溯率、Provider 健康、待人工复核）+ 实时 spark。
- L4 Action：能力字段（生成简报/追踪事件/对比竞品/起草内容走审批），Field System 开放字段，非白卡墙。
- 右栏 Context：工作上上下文（主体/领域/范围/时间窗/语言）+ 证据（EV/全局链/subject_context/runtime 引用）。

## 3. Composer 规范
- 表面：raised 金属面 + 顶部 1px 捕光 + 发丝边，圆角 lg；不用厚玻璃雾（OPT GL 层关闭，类名保留）。
- 主操作「发送 →」：primary 黑银（dark 白银反相），反相文字；active scale .97；触控≥44。历史 bug：`.lum-app button{color:inherit}` 特异性压过按钮色 → 已用 `.lum-app .lum-btn*`(0,2,0) 修正，禁止回退。
- 芯片（引用证据/指定主体/时间范围）：ghost hairline，可移除；输入区 auto-grow，占位提示不替 label。

## 4. AI 过程与诚实度
- 步骤状态：understanding/retrieving/tool/reasoning（只显示阶段，不显示私有思维链）/artifact/completed/failed/needs-review。
- 每条结论可展开证据（EV id mono、来源、时间）；展示 confidence 与 limitation；低置信 needs-review。
- **绝不渲染**：private chain-of-thought、system/developer prompt、cookie、token、credentials、browser session、CDP、安全内部。
- EFFECT 动作弹 confirm（scope/target/permission/risk），不假装成功（toast `not_wired_to_backend`）。

## 5. 视觉/主题/响应
- light 黑银、dark 白银精确反相（见 smoke 图）；icy 只在实时点/spark/processing。
- 390：单列、大 tabular KPI、composer 堆叠、发送键右下、底部 dock 中央 Lumen Core 球体可见（黑铬/白银，球内混沌流转，无星星）。
- 一屏一个主焦点（Composer）；能力字段后退，不与输入抢焦点。

## 6. 校准通过证据
- 1440 light/dark、390 light 截图零 console 错误（09_QA/console、04_VISUAL_BASELINES）。
- 发送键文字/底色对比达标；Lumen Core 在 WebGL1（无 fwidth）正常绘制，像素采样非透明。
- 类名/data 钩子未改，Codex 可直接绑定 ViewModel/Action（见契约映射）。

## 7. 作为母版的复用规则
其余 AI-02..05 继承：Composer 语言、步骤状态、证据引用、浮层、主题反相；差异只在密度与具体工件，不另立视觉体系。
