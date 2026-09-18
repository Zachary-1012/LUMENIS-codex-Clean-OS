# DOUBAO EXECUTION REQUIRED

## 序境 / LUMENIS｜Frontend Design & Experience 交付与回传标准

> 执行对象：豆包（Doubao）
>
> 当前阶段：Design Ecosystem Optimization V2.5 / Frontend Delivery Audit
>
> 基线分支：`handoff/frontend-gpt-v24-20260911-final`
>
> 核心规则：本任务只负责前端、设计生态、页面契约、交互、响应式、动效、可访问性与前端验收。**禁止接入第三方模型、开源 AI Runtime、第三方 Agent Framework、OSS Backend Capability。所有第三方模型 / OSS 能力接入由后续 Codex 阶段执行。**

---

## 0. 执行原则

1. 先审计当前仓库和当前分支，不得凭历史记忆判断。
2. 不得重建第二套前端、第二套设计系统或第二套页面架构。
3. Experience V2.5 负责 IA / UX / Interaction / Screen Contract / Visual Language / Token / Motion / Responsive；不得伪造 Backend / API / DB / Permission / Runtime / Evidence / Metric / Production State。
4. 页面必须明确区分：真实绑定、Mock、Placeholder、Hardcode、Backend Gap、Runtime Gap。
5. 不得把“文件存在”写成“功能已实现”。
6. 不得改 `main`。
7. 不得接第三方模型、OCR/NLP/ASR/Vision/Embedding/Reranker/Vector DB/Agent Framework。
8. 所有需要 Codex 实现的内容放入 `Codex task`。

---

# 1. 必须上传到 GitHub 的前端源码

必须包含当前所有有效前端源码及配置：

- `frontend/` 有效源码
- 页面路由
- Layout / Shell
- Navigation
- Page Components
- Shared Components
- Hooks
- Stores / State
- API client / frontend services
- Types / Interfaces
- Utilities
- Responsive logic
- Motion / animation logic
- Error / Empty / Loading / Permission states
- AI Workspace 前端
- CTH 前端
- BMP 前端
- Shared Capability 前端
- SYSTEM 前端
- CSS / SCSS / Tailwind / token 文件
- 设计系统相关配置
- `package.json`
- lockfile
- build config
- lint / formatter config
- test config

---

# 2. Design System 必须上传

必须生成并提交：

- `DESIGN_ECOSYSTEM_V2.5.md`
- `DESIGN_FOUNDATIONS_V2.5.md`
- `DESIGN_TOKEN_SYSTEM_V2.5.json`
- `COMPONENT_REGISTRY_V2.5.json`
- `PATTERN_REGISTRY_V2.5.json`
- `PAGE_FAMILY_MATRIX_V2.5.json`
- `RESPONSIVE_SYSTEM_V2.5.md`
- `MOTION_SYSTEM_V2.5.md`
- `STATE_SEMANTICS_V2.5.md`
- `ACCESSIBILITY_RULES_V2.5.md`
- `AI_01_CALIBRATION_V2.5.md`
- `CTH_01_CALIBRATION_V2.5.md`
- `DESIGN_ENGINEERING_ACCEPTANCE_V2.5.md`
- `DESIGN_ECOSYSTEM_CHANGELOG_V2.5.md`

---

# 3. 页面级交付清单

每个页面必须登记：

- 页面名称
- Route
- Domain：CTH / BMP / Shared Capability / SYSTEM
- Page Family
- 页面层级
- Desktop 状态
- Large Tablet 状态
- Tablet 状态
- Mobile 状态
- Loading
- Empty
- Error
- Permission Denied
- Stale
- Unknown / Not Available
- 使用的 Component
- 消费的 API / Contract
- 是否真实绑定数据
- 是否仍有 mock / placeholder / hardcoded data
- 是否存在未绑定按钮
- 是否存在死路由
- 是否存在未实现交互

---

# 4. AI Workspace 必须单独交付

必须覆盖：

- Conversation area
- Context
- Evidence
- Source
- Retrieval
- Tool state
- Permission
- Approval
- Artifact
- Provenance
- Confidence
- Limitation
- Error / Fallback
- Loading / Streaming
- Mobile adaptation

禁止：

- 展示 private chain-of-thought
- 暴露 prompt
- 暴露 token / API key
- 暴露 Cookie / Session / CDP 等内部信息

---

# 5. CTH 必须单独交付

必须覆盖：

- Subject selector
- Subject Context
- Situation
- Facts
- Relationships
- Evidence
- Finding
- Risk
- Decision
- Action
- Outcome
- Controls
- 对应真实 API / Contract 标记

规则：

`Selected Subject → Situation → Facts → Relationships → Evidence → Finding/Risk → Decision → Action → Outcome`

不得把业务链做成永久性的装饰流程图。

---

# 6. BMP 必须单独交付

必须覆盖：

- Brand / Market context
- 品牌监测
- 内容
- KOS / KOL / KOC / UGC
- Topic / Campaign
- Sentiment / Risk
- Evidence
- Creator / Post / Interaction
- Media / Content Intelligence 展示入口
- Case / Insight
- Action / Evaluation
- 对应数据来源和 Contract 标记

---

# 7. Shared Capability 必须交付

必须覆盖：

- Content & Creation
- Evidence
- Evaluation
- Learning Asset
- Report / Export
- Search / Retrieval UI
- AI Enhancement UI
- Upload / Import
- 文件状态
- 任务状态
- Trace / Provenance

---

# 8. SYSTEM 前端必须交付

必须覆盖：

- Settings
- Permission
- Security
- Runtime
- Collector 状态
- Database 状态
- Provider / Capability 状态
- Logs / Observability
- Recovery
- Health
- Notification settings
- AI / Model Settings（仅配置入口，不得让前端直接持有敏感 Key）

---

# 9. 视觉资产必须上传

必须登记并提交实际使用资产：

- Logo
- Icon
- AI Orb
- Illustration
- Background
- SVG
- 合法使用的图片资产
- 必要字体引用声明
- Asset manifest
- 文件来源
- License / ownership 状态

禁止提交：

- 重复废弃资产
- 大量未使用媒体
- 本地缓存
- 临时导出
- 敏感信息

---

# 10. Design Token 必须真正代码化

至少包含：

- Color
- Surface
- Text
- Border / Hairline
- Spacing
- Radius
- Typography
- Shadow
- Motion
- Z-index
- Breakpoint
- State
- Domain semantic token

禁止重要视觉参数继续大面积散落 hardcode。

---

# 11. Component Registry 必须说明

每个组件至少记录：

- Component name
- Path
- Purpose
- Variant
- State
- Responsive behavior
- Accessibility
- Used by pages
- Deprecated / Active
- 是否允许继续扩展
- 是否存在重复组件

---

# 12. 前端 Contract 清单必须交付

必须生成：

- Page → API mapping
- Component → Data contract
- Request schema
- Response schema
- Error schema
- Permission requirement
- Evidence / provenance requirement
- 当前真实绑定 / mock / missing

后端尚未实现的接口必须明确标记：

`BACKEND_GAP`

禁止前端自行伪造 Production Truth。

---

# 13. Responsive 验收必须交付

必须覆盖：

- Desktop
- Large Tablet
- Tablet
- Mobile

每类关键页面至少有一个实际验收结果，检查：

- Overflow
- Fixed width
- Broken grid
- Hidden action
- Touch target
- Modal / drawer
- Chart resizing
- Table adaptation
- AI Workspace adaptation

---

# 14. Motion 验收必须交付

每类动效必须记录：

- 动效名称
- Trigger
- Duration
- Purpose
- Reduced Motion 行为

动效只能服务：

- hierarchy
- continuity
- causality
- transition
- feedback
- state change
- focus
- progress
- provenance

禁止 purely decorative motion 成为页面主体。

---

# 15. Accessibility 必须交付

至少验证：

- Keyboard navigation
- Focus
- Semantic HTML
- ARIA
- Contrast
- Screen-reader basics
- Reduced Motion
- Form label
- Error announcement
- Modal focus trap
- Mobile touch target

---

# 16. 前端测试必须上传并回报

至少执行并记录：

- Unit tests
- Component tests
- Integration tests
- Critical E2E
- Route test
- Responsive test
- Accessibility test
- Build test
- Type check
- Lint
- Dead link / dead button check
- Console error check
- Mock data scan
- Hardcoded value scan

禁止使用 mock 数据冒充 Production Acceptance。

---

# 17. 禁止上传的内容

禁止提交：

- `node_modules`
- build cache
- `.DS_Store`
- local temp files
- screenshots dump
- secrets
- tokens
- API keys
- cookies
- session data
- `.env` secrets
- browser profile
- CDP session
- production credentials

---

# 18. 完成后必须提交的总报告

最终报告至少包含：

- `CURRENT_BRANCH`
- `BASE_HEAD`
- `FINAL_HEAD`
- commit list
- changed files count
- added / modified / deleted files
- pages audited
- pages changed
- components audited
- components created
- components reused
- duplicate components removed
- routes audited
- dead routes
- buttons audited
- dead interactions
- responsive issues fixed
- accessibility issues fixed
- mock / hardcode remaining
- backend gaps
- frontend contract gaps
- design-system violations remaining
- tests passed
- tests failed
- tests skipped
- build result
- E2E result
- known blockers
- rollback commit
- `PRODUCTION_READY = YES / NO`

禁止使用“基本完成”“应该可以”等模糊状态替代事实。

---

# 19. 必须生成前端差异清单

生成：

`FRONTEND_CHANGE_MATRIX_V2.5.md`

每项至少写：

- Before
- After
- Reason
- File
- Page
- Risk
- Test
- Status

---

# 20. 必须生成遗留问题清单

生成：

`FRONTEND_REMAINING_GAPS_V2.5.md`

必须按以下分类：

- P0 blocker
- P1 before production
- P2 optimization
- Design gap
- Backend dependency
- Data dependency
- Runtime dependency
- Codex task

所有以下内容必须放入 `Codex task`，豆包不得自行实现：

- 第三方模型接入
- 开源 OCR / NLP / ASR / Vision 模型接入
- Embedding / Reranker 接入
- Vector Database 接入
- OSS Agent Runtime / Framework 接入
- Provider Adapter 后端实现
- AI_OFF 后端工程实现
- Shadow Mode 后端实现
- OSS License 最终集成决策
- Backend Production Convergence

---

# 21. 最终回传给 ChatGPT 的最小信息

完成并 push 后，仅需回传：

- Repository
- Branch
- HEAD SHA
- 最终总结
- Tests summary
- Blockers
- `PRODUCTION_READY`

无需手工复制全部文件；ChatGPT 将直接读取最新 GitHub 分支进行二次源码审计。

---

# 22. 最终验收问题

豆包完成时必须能明确回答：

1. 所有真实前端代码在哪里？
2. 所有页面当前分别是什么状态？
3. 哪些页面已经绑定真实 Production Contract，哪些仍是 Mock / Missing / Backend Gap？
4. Codex 下一步需要做什么，且哪些任务明确不属于豆包？

以上四项任意一项无法回答，不得宣布本阶段完成。

---

## Completion Gate

最终只允许以下状态：

- `DESIGN_ECOSYSTEM_READY = YES / NO`
- `FRONTEND_DELIVERY_COMPLETE = YES / NO`
- `FRONTEND_REALITY_AUDITED = YES / NO`
- `CODEX_HANDOFF_READY = YES / NO`
- `PRODUCTION_READY = YES / NO`

注意：`CODEX_HANDOFF_READY = YES` 不等于 `PRODUCTION_READY = YES`。
