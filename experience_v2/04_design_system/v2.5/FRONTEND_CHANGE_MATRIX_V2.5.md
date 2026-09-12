# FRONTEND_CHANGE_MATRIX_V2.5

序境 / LUMENIS Experience Layer — V2(通用模板) → V2.5(自有生态设计语言) 前端差异清单。
原则：Experience Layer 只改呈现/契约，不改 Backend/DB/Runtime/Permission；所有 After 均有真实文件与 QA 证据。

| # | Before（V2 模板态） | After（V2.5） | Reason | File | Page | Risk | Test / Evidence | Status |
|---|---|---|---|---|---|---|---|---|
| C01 | 浅灰 SaaS 卡墙、三层 radial 紫蓝光晕 | 铂金雾黑银(浅)/白银(深)精确反相，Field System 发丝分栏、去卡墙 | 根除模板感、建立金属单色 DNA | assets/tokens.css, base.css, components.css | 全部 44 | 低（仅呈现） | 704 基线 + 对比 15.31:1 | DONE |
| C02 | 残留紫/靛蓝 AI 配色 | 全局零紫零靛蓝，Icy Cyan 仅用于数据/状态/focus | 颜色必须各司其职 | tokens.css, components.css, orb.js | 全部 | 低 | external/legacy css scan=0 | DONE |
| C03 | canvas2d 软糊斑块球体、含星星 | 原生 WebGL1 GLSL：fbm simplex 球内混沌、fresnel 金属边、processing 微混 icy、零星星 | 自有 AI Orb，跨媒介识别 | assets/orb.js | AI-01/02、dock FAB | 中（WebGL 兼容） | compile/link 失败显式报错；390 FAB 可见；M12 视频 | DONE |
| C04 | 左上“序”方块 logo、nav 轴圆点、bell 红 badge、紫消息图标 | 去方块、浅色黑银/深色白银、纯文字导航（商业运营/品牌市场无缩写后缀） | 去模板化、导航只要名字 | assets/shell.css, shell.js | 全部 shell | 低 | 390/1440 双主题目检 | DONE |
| C05 | 功能组固定铺开 | 功能组可折叠、progressive disclosure | 2–4 层动态 IA | shell.js, data/shell.js | 全部 shell | 低 | 交互走查 + M03 | DONE |
| C06 | 内部作业流程被画成编号 stepper/箭头链副标题（Brief→…→Learning、Morph 六步等） | 内部流程仅保留在 viewmodel（`internal:true`，渲染器跳过）；只有 AI 对话内显示思考步骤 | 用户红线：流程是底层逻辑，不在明面；§5 不得做永久装饰流程图 | assets/sections.js(R.steps), data/screens.js | SH-01、AI-02 及全量箭头链文案 | 低（数据保留、仅不渲染） | verify_flow：可见 genericSteps=0、aiSteps 保留(5/4)、chain=false、console 0 | DONE |
| C07 | “处理流水线/脚本流水线/能力→任务”等系统流程措辞 | 改“处理进度/制作进度/能力任务”，实例生命周期状态保留 | 区分系统方法论(隐藏)与实例状态(可见) | data/copy.js(zh/en/ko), screens.js | upload、播客、AI-02 | 低 | node --check + 三语 key 齐全 | DONE |
| C08 | 11 个 input/textarea 缺 accessible name | i18n 增加 data-i18n-aria；form 渲染器补 aria-label；ACC-01 补 autocomplete | A11y 表单标签 | i18n.js, sections.js, screens.js | 10 屏 | 零像素变化 | a11y-recheck remaining=0 | DONE |
| C09 | 字号/间距固定、仅桌面 | 8 断点自适应（1920/1440/1280/1024/768/430/390/360），触控≥44px，表/图自适应重排 | 非缩放式响应式 | tokens.css, shell.css, components.css | 全部 | 中 | 横向溢出全 0、704 基线 | DONE |
| C10 | 无统一动效语义、transition:all | 仅 opacity/transform；duration/easing token；语义化动效 + reduced-motion 兜底 | 动效只表达因果/状态/反馈 | motion.css, motion.js | 全部 | 低 | M01–M15 + reduced 合成视频 | DONE |
| C11 | 无触感 | LumHaptics：12 通道/6 动词，navigator.vibrate + lum:haptic 具身桥，reduced 关闭 | 全场景触感、为具身硬件预留 | haptics.js | 全部可压面 | 低 | HAPTICS_EMBODIED_V2.5.md | DONE |
| C12 | 旧彩色手写 logo | 黑银/白银金属 wordmark + 原创 69 lum-icon；旧彩色仅作历史证据不沿用 | 统一品牌生态 | 05_components/brand, icons | 全局 | 低 | icons-manifest 69、launch 视频 | DONE |
| C13 | 无原创性/外部依赖审计 | 全部依赖本地化（字体 OFL、无 CDN、无外部运行时请求） | 可离线、可审计 | 10_ORIGINALITY/* | 全局 | 低 | EXTERNAL_RUNTIME_SCAN=0 | DONE |
| C14 | 原型与生产事实混淆 | 每屏 data-source=prototype；54 绑定标 BACKEND_GAP/UNBOUND，UNKNOWN 保留 | 不伪造 Production Truth | app.js, 06_CONTRACTS | 全部 | — | validate_handoff、unknown-bindings(54) | DONE（绑定归 Codex） |

## 回滚
- 呈现层为 untracked `experience_v2/`，未改 main 任何 tracked 文件（`git diff` 为空）；回滚只需不采用该目录，无 Git 历史负担。
- C06 的内部步骤数据未删除（`internal:true` + `_note`），Codex 仍可读取底层流程契约。
