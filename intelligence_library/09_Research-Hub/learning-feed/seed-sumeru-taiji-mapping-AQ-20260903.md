# Seed-Sumeru × Taiji 哲学映射与落地记录（A–Q 交付）

> 日期：2026-09-03 ｜ 依据：`DESIGN_PHILOSOPHY_SEED_MUSTERY_TAIJI_V1.md`（ZBC a7ee4fab / OSAI 7d92ef0）
> 原则：**REUSE → MAP → MINIMAL CHANGE**，不新建框架、不重做架构、不删在用模块、不改业务 Truth/风险规则/权限/Contract。
> 适用范围：不只 UI——本哲学同时统摄**学习沉淀**与**创意 idea 生成**（用户 2026-09-03 明确）。

---

## A. 当前 UI 架构映射
- Flask Jinja：`templates/base.html` 为壳（header / nav 7 项 / main block / footer），子页 index/notes/events/report。
- 静态层：`static/` 下 50 个 html/js；主框架全局加载 13 个 JS（app.js 112KB 为主控）。
- 独立工作台：`creative_workbench.html`（创意卡/视频/社媒/拆解四 Tab）。
- 映射结论：哲学的"抽象能力显化层"落在现有 main block 与各工作台，**不新增路由框架**。

## B. 当前交互架构映射
- 已有：`keyboard_shortcuts.js`（键盘基础）、`modal_simplify.js`、`design-v9-interactions.js`、`ui_interactions_v5.8.0.js`、`frontend_enhancement.js`。
- 案例深度分析 `case_deep_analysis.js` 已含 stage/drill-down 雏形（7 处）。
- 缺口：无统一的"状态管线 + 证据下钻 + cross-highlight"原语 → 本次以**一个**可复用原语补齐（见 G）。

## C. 当前可视化模块映射
- **未引入 echarts/chart.js/d3**（全仓 grep 0 命中）；图表为手写 DOM/CSS，另有 `three.min.js`(654KB)+`zachary_3d.js`。
- 现有仪表盘：architecture_dashboard / evidence_dashboard / resident_health / case_deep_analysis。
- 映射：九态语义模型（INPUT→…→FEEDBACK）由新原语承载，纯展示、数据由调用方传入；不替换任何现有图表。

## D. 当前动态模块映射
- 动效分散于各 CSS；`tokens.css` 已定义 **MOTION TOKENS（第6章）** 但主框架未统一引用。
- 映射：新原语动效仅两类——当前态"呼吸"（表达进行中）、推进过渡（表达连续性），并加 `prefers-reduced-motion` 关闭；无装饰动画。

## E. 可复用模块（直接复用，不重造）
1. `static/css/tokens.css`：440 行 / 287 个设计令牌（颜色/字体/间距/圆角/阴影/动效/布局/断点/毛玻璃/AI 分层）——作为"一（共享秩序）"的视觉源。
2. `case_deep_analysis.js` 的 stage/drill-down 模式。
3. `keyboard_shortcuts.js` 的键盘范式；`auth_recovery_poller.js` 的纯 createElement+textContent 防 XSS 范式。
4. 后端 `ai_gateway`（固定前缀+budget）、`prompt_registry`、`compliance` 角色。

## F. 重复模块（记录，本轮不删——删除需走 Usage/Dependency/Runtime/Contract/Replacement/Rollback 六证 Gate）
- CSS 多套并行：design-v8 / design-v9-gpt-codex、components / components-minimal、layout / layout-minimal、tokens / tokens-minimal、style / ui_optimized。
- 交互 JS 多套：ui_interactions_v5.8.0 / frontend_enhancement / design-v9-interactions / modal_simplify 职责重叠。
- 处置：仅**登记**到 P2 收敛清单，本轮零删除（守功能零减配）。

## G. 最小修改方案（本轮实际落地，全部为新增、零全局污染）
| 新增/改动 | 文件 | 作用 | 是否动旧代码 |
|---|---|---|---|
| 状态管线样式原语 | `static/css/taiji-state.css` | `.tj-` 命名空间九态；序号+✓+形状+文字四重编码（颜色非唯一载体）；aria；reduced-motion；移动端折行 | 纯新增 |
| 状态管线渲染原语 | `static/js/taiji-state.js` | `TaijiState.renderPipeline`：点击/键盘(Tab/Enter/方向键)下钻证据、cross-highlight 句柄；纯 createElement 防 XSS | 纯新增 |
| 参考实现+使用文档 | `static/taiji-state-demo.html` | 两个真实形状实例：九态信号管线 / 创意芥子→须弥循环 | 纯新增 |
| idea 上下文指纹 | `scripts/idea_generator.py` | 每个 idea 强制挂 `provenance`（见 H/I） | 仅新增字段，旧字段全保留 |
| 创意卡证据链 | `creative_workbench.html` | 原生 `<details>` 渐进披露溯源（键盘可达，零额外 JS） | 仅新增区块 |
| 元审阅固定前缀 | `config/prompts/lumenis-prompts.yaml` | 新增 `meta_reviewer` 角色（固定前缀收敛，bump 即版本化） | 纯新增 role |

## H. 芥子→须弥 反馈链（具体生产 → 抽象能力）
真实信号（ZBC 舆情/Topic/人群，芥子）→ `brand_insight` 诊断 → `idea_generator` 抽象为机制/L1 公式（须弥）→ 知识库沉淀可复用法则 → Observatory 评估 → 下一轮调用。
**防语义坍塌（采纳 glm-4.7）**：每条抽象强制带 `evidence_level`（assumption/single_case/repeated/validated）与 `confidence`，无真实样本封顶 0.35–0.4，禁止把孤例伪装成通用法则；`counter_example_check` 留 P2 负样本接口。

## I. 须弥→芥子 能力链（抽象能力 → 具体生产）
L1 公式/调性坐标（须弥）→ `video_script`/`social_ops`/`campaign_plan` 生成具体内容（芥子）→ 经 Contract 交付 ZBC 生产 → 投放 FEEDBACK 回流。
每个 idea 的 `provenance.trace` 显式记录这条链；`parent_L1_formula`/`parent_L2_tone` 保证**不产生孤立 L0 技巧**（层间不跳跃）。

## J. 个性化边界（"形可变，道不可移"的执行主体——补 glm-4.7 指出的"谁守护道"）
- **可个性化（形）**：信息密度、排序、主题、交互偏好、表达方式。
- **不可变（道）与守护主体分层**：
  1. 后端 Schema / 校验 = 硬约束（Truth、风险规则、权限边界），前端无权改；
  2. Contract 层 = 能力边界，跨仓只流能力不流 ownership；
  3. AI 生成内容过 `compliance` 固定前缀审查（合规打标），边缘内容 BLOCK/HUMAN REVIEW；
  4. UI 只**呈现**后端给定的状态与证据，视觉状态不得暗示数据不支持的事实。
- 结论："道"由后端 Schema + Contract + compliance 三重守护，非前端口号。

## K. UI/UX 回归　L. 可视化回归
- 新原语独立命名空间，不改任何既有选择器；既有页面 DOM/CSS 零变更（base.html 本轮**未**全局引入 tokens，避免大面积视觉回归）。
- 回归方式：全量 pytest EXIT=0；静态资源 8201 现网 HTTP 200；demo 页两实例可渲染、可点、可键盘操作。

## M. 无障碍检查
- 节点 `role=button`/`aria-current=step`/`aria-expanded`/`aria-label`；证据面板有关闭按钮；focus-visible 3px 蓝环；触控目标 ≥32–44px；颜色不作唯一状态载体（序号/✓/文字同步）；`prefers-reduced-motion` 关动效。

## N. 性能检查（性能即 UX）
- 新 CSS 5.5KB / JS 5.4KB，无第三方依赖、无轮询、无持续动画（仅当前态单次呼吸）；不新增全局请求；provenance 为同步字典构造，O(1)。

## O. Runtime Evidence
- 8201 已重启（新 pid 21828，加载最新代码），4 路创意 API 真实 HTTP 全 200（ideas/video/social 9 平台/pitch 8 章节）。
- 3 个 taiji 静态资源现网 200；test_client 验证 ideas 带 framework + 完整 provenance。
- 调度心跳正常；采集 PARTIAL_BLOCKED 为生产既有熔断保护，非本次引入。

## P/Q. Commit / Push
- 见本轮 git 提交（ZBC：taiji 原语+provenance+meta_reviewer；OSAI：第九期 glm-4.7 第二意见 + 本映射文档），SHA 以 git log 为准。

---

## 附：glm-4.7 第二意见的我方采纳判断（不全盘照收）
| glm-4.7 意见 | 我方判断 | 处置 |
|---|---|---|
| ① 抽象阶梯"语义坍塌"/幸存者偏差，缺反事实 | **采纳** | provenance 加 evidence_level+confidence+反例接口（本轮） |
| ② "道不可移"缺执行主体 | **采纳** | 见 J，三层守护（本轮文档化 + compliance 既有） |
| ③ 相关≠因果，算法变迁致公式失效 | **采纳** | 每个 idea 标 causal_type=相关性，提示需复核（本轮） |
| 补 Cynefin 问题域 / XAI 置信度 / 商业量化倒推 | 部分采纳 | confidence 即轻量 XAI；Cynefin 域判断、商业假设层列入 P1/P2 迭代 |
| 与 Material/HIG/Tufte 重复造轮子 | 接受批评 | 不另立设计语言，复用 tokens.css + 只补"决策导向/证据链"差异化原语 |
| 一句话：坚持真实信号、警惕相关当因果 | 完全采纳 | 作为学习与 idea 生成的长期铁律 |
