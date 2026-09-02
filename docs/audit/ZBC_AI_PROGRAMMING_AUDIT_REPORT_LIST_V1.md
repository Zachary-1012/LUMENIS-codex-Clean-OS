# ZBC AI 编程审计输出报告 List v1.0

状态：AI 编程基线审计清单 / 施工前 Gate
目标：把 ZBC 当前源码与 Zachary-OS-AI 的通用 AI Runtime、AI 舆情 Intelligence Upgrade 基线、Browser Runtime 基线统一纳入可执行审计。

## 0. 审计事实基线
- 当前 HEAD / Branch / Version / Working Tree
- Runtime 与启动方式
- Python/Node/Frontend/DB/AI Provider 版本
- Dependencies 与 License
- CI/CD 与测试入口
- 已知生产约束
- 最近变更与回归风险

## 1. 仓库结构审计
- 目录层级
- 模块所有权
- API/Blueprint
- Collector
- Analyzer
- Event Engine
- Risk Engine
- Reporting
- Notification
- Resource Library
- Browser Runtime
- Evidence
- Evaluation
- Guardian/Health
- Tests
- Scripts

输出：Module Ownership Matrix。

## 2. 双子库边界审计
核对 Zachary-OS-AI ↔ Z-Brand-Core：
- Contract
- API
- Adapter
- Dependency
- Import/Runtime coupling
- Context boundary
- Product Truth boundary
- Resource boundary
- Permission boundary
- Runtime State boundary

输出：Cross-Repo Boundary Matrix + Architecture Conflict Matrix。

## 3. 采集系统审计
逐模块确认采集什么、来源、状态、登录/Session、限流、风控、入库、Evidence、失败恢复、去重、增量、调度、数据质量。
重点覆盖：
- 小红书主采集
- 外部导入
- 图片/视频导入
- 文案直接入库
- 批量导入限制
- 平台统一词条
- Collector V2 / Shadow Mode（如存在）

输出：Collector Capability / Progress / Effectiveness Matrix。

## 4. Subject Truth 审计
必须保持主体过滤优先：
- SUBJECT_WORDS
- SUBJECT_EXCLUDE_WORDS
- subject_hit()
- SUBJECT_HARD_FILTER

确认 AI/LLM 不得单独决定“是否属于太古汇”。
输出：Truth Decision Chain。

## 5. AI 舆情 Intelligence 审计
核对现有能力与新基线：
- Sentiment
- Fine-grained Emotion
- Stance
- Advocacy Signal
- Intent
- Topic
- Event Detection
- Event Clustering
- Event Lifecycle
- Volume
- Velocity
- Propagation
- User Behavior
- Multimodal Content Intelligence
- AIGC Signal
- Misinformation/Anomaly Signal
- Risk
- Opportunity

输出：AI Intelligence Gap Matrix，标记 🟢/🟡/🔴/⚠️/♻️。

## 6. 事件智能审计
确认事件是否支持：
Emerging → Growing → Peak → Stable → Declining → Closed。
检查首次出现、增长速度、互动、参与者、核心传播者、情绪变化、立场变化、传播节点、关联品牌/业态、风险/机会。

## 7. 传播智能审计
检查是否能够从“内容量”升级到：
- Volume
- Velocity
- Engagement acceleration
- Author influence
- KOL/KOC/UGC role
- Propagation relationship
- Content duplication/similarity
- Community/cluster signal

输出：Propagation Intelligence Matrix。

## 8. 多模态审计
检查 Text/Image/Video/Audio/Metadata 是否可以形成统一 Content Intelligence Object。
必须验证：
- 文本情绪
- 视觉语义
- 场景
- OCR/ASR（如已有）
- 文本与画面一致性/冲突
- Evidence

## 9. Browser Runtime 审计
P0：
- Browser Contract
- Browser State Machine
- BEEP
- Policy Gate
- Permission Scope
- Session/Profile Isolation
- Failure Classification
- Safe Stop
- Evidence Contract
- Playwright Adapter
- Browser Health
- last_success_at
- Zachary ↔ ZBC Decoupling

核对现有 Internal Browser、CDP、Resident Browser、Domain Whitelist、Session Recovery，禁止重复建设。

## 10. Browser Provider 审计
- Playwright：P0
- PinchTab：P1
- Browser Use：P1
- Browser Harness：P1
- CloakBrowser：Research/Compatibility Lab

逐项 License/Security/Version/Compatibility/Dependency Audit。
第三方项目不得成为 Zachary 核心业务逻辑。

## 11. Adaptive Decode & Compatibility 审计
允许合法授权范围内的：编码、格式、页面结构、Parser、Provider、自适应解析与兼容。
涉及认证、Cookie/Session 窃取、CAPTCHA、DRM、付费权限或明确访问控制绕过时必须 Safe Stop + Evidence + Human Review。

## 12. Resource Library 审计
确认所有学习资料、案例、文件、采集材料进入统一 Resource Library，而不是互相割裂的资料系统。
字段至少考虑：Type / Category / Tag / Source / Domain / Product Scope / Provenance / Evidence / Evaluation Status。

## 13. Zachary Learning Loop 审计
验证：
ZBC Production → Isolation → De-identification → Policy → Evaluation → Learning Signal → Zachary。
禁止产品 Truth、私有数据、Runtime State 自动进入 Zachary 全局记忆。

## 14. 个性化审计
允许改变：Style / Recommendation / Information Density / Interaction Habit。
禁止改变：Truth / Business Rule / Security / Permission / Data Authenticity / Physical Properties。
原则：Style 可个性化，Truth 不可个性化。

## 15. Model/Provider Router 审计
检查：
- 本地 AI
- 云端 AI
- 豆包等 Provider
- Fallback
- Timeout
- Cost/Token Budget
- Model Version
- Prompt Version
- Output Schema
- Evaluation
- Provider Independence

AI Provider 不得成为核心业务 Truth。

## 16. Evaluation 审计
必须建立：
- Gold Set
- Regression Set
- Edge Cases
- Human Review
- Model Evaluation
- Rule-vs-AI Comparison
- AI Override Rate
- False Positive/Negative
- Drift
- Versioned Prompt/Model

禁止“模型说成功”作为验收标准。

## 17. Evidence 审计
关键执行必须记录可验证证据：
URL / Timestamp / Source / Content ID / Browser / Profile / Session / Action / Before State / After State / Screenshot/Snapshot / Result / Provider / Error / Retry Count。

## 18. 稳定性与自动恢复审计
检查：
- Heartbeat
- last_success_at
- last_failure_at
- watchdog
- retry limit
- cooldown
- circuit breaker
- auto recovery
- crash recovery
- stale session detection
- collector recovery

## 19. 数据闭环审计
验证完整链路：
采集 → 入库 → 主体过滤 → AI分析 → 事件 → 风险/机会 → 报告 → 通知 → Evidence → Evaluation → Learning Signal → 回归。

## 20. 报告体系审计
检查：
- 日报
- 周报
- 月报
- 年报
- 专报
- 风险预警
- 事件快报
- 案例对标

输出必须从“数据罗列”升级为“Decision Intelligence”。

## 21. UI/交互审计
- 模块层级
- 状态反馈
- Loading/Empty/Error/Success
- Evidence 可见性
- AI 判断与规则判断区分
- 用户行为采集
- 多入口交互
- 移动端适配准备

## 22. 安全审计
- SSRF
- Domain Allowlist
- File Validation
- Upload Limits
- Path Traversal
- Secret Handling
- Cookie/Session Isolation
- Prompt Injection
- Tool Permission
- External Action Authorization
- Audit Log

## 23. 文件/外部采集审计
确认：
- 单次外部文件最多 10 个
- 单次文件总大小 ≤500MB
- 视频/图片单次最多 20 个、总大小 ≤500MB
- 文案可直接输入进库
- 可粘贴导入
- 可浏览文件夹后选择文件，但批量导入不得直接接收文件夹
- 单次批量图片/视频 ≤30 个
- 平台词条统一
- Zachary 与 ZBC 使用统一术语表

若现有实现与此不同，以当前最新 Contract 为准并报告差异，不得静默修改。

## 24. 统一术语审计
建立 Canonical Glossary，统一：
平台、内容、笔记、帖子、作者、账号、品牌、业态、事件、话题、情绪、立场、风险、机会、证据、资源、案例、Skill、Provider、Model、Session、Profile、Collector 等词条。

## 25. 测试审计
必须盘点：
- Unit
- Integration
- Contract
- E2E
- Browser
- Security
- Import/Upload
- Collector
- Regression
- Failure Recovery
- Cross-Repo

输出当前通过/失败/缺失，不得用模糊描述。

## 26. 代码质量审计
- 重复代码
- 循环依赖
- God Module
- 隐式全局状态
- 配置散落
- Provider coupling
- Error swallowing
- Async/Sync 风险
- DB migration
- Schema compatibility
- Dead code
- 未覆盖关键路径

## 27. CI/CD 审计
确认 PR/Push 是否执行：
Lint → Unit → Integration → Contract → E2E → Security → Regression。
明确哪些检查属于阻断级 Gate。

## 28. 性能与成本审计
检查：
- Token 消耗
- AI 调用次数
- Cache
- Batch
- Queue
- Concurrency
- Browser resource
- DB query
- Collector throughput
- Report generation

原则：确定性任务优先代码；需要理解的任务才调用 AI。

## 29. 研发变更审计
每次代码修改必须能回答：
Why / Existing Capability / Reuse / Impact / Dependency / Boundary / Test / Evidence / Rollback。

## 30. 最终输出清单
审计完成必须输出：
1. Baseline Snapshot
2. Repository Structure Matrix
3. Module Ownership Matrix
4. Dependency Matrix
5. Contract Matrix
6. Cross-Repo Boundary Matrix
7. Architecture Conflict Matrix
8. Collector Capability/Progress/Effectiveness Matrix
9. Subject Truth Decision Chain
10. AI Intelligence Gap Matrix
11. Event Intelligence Matrix
12. Propagation Intelligence Matrix
13. Multimodal Matrix
14. Browser Runtime Matrix
15. Provider Matrix
16. Adaptive Decode Compatibility Matrix
17. Resource Library Matrix
18. Zachary Learning Loop Matrix
19. Personalization Boundary Matrix
20. Model/Provider Router Matrix
21. Evaluation Matrix
22. Evidence Matrix
23. Stability/Recovery Matrix
24. Data Closure Matrix
25. Reporting/Decision Intelligence Matrix
26. UI/Interaction Matrix
27. Security Matrix
28. Import/Upload Matrix
29. Canonical Glossary Matrix
30. Test Baseline Matrix
31. Code Quality Findings
32. CI/CD Gate Matrix
33. Performance/Cost Matrix
34. P0/P1/P2施工矩阵
35. Rollback Plan
36. Release Gate

## 31. P0 判定规则
P0 只允许处理：
- 生产阻断
- 数据错误
- 主体 Truth 错误
- 双库边界污染
- 安全问题
- Evidence 缺失导致无法验证
- 核心采集链路故障
- 核心 Browser Runtime 稳定性问题
- 明确回归

## 32. 施工 Gate
Audit PASS → Gap Matrix → Minimal Change Plan → User/Owner Review（如涉及核心架构）→ Code → Tests → Evidence → Regression → Cross-Repo Audit → Release Gate。

不得直接跳过审计进入大规模重构。
