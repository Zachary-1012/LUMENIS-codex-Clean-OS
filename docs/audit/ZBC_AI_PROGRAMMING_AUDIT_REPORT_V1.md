# ZBC AI 编程审计报告 V1.0

日期：2026-09-02
范围：Z-Brand-Core × Zachary-OS-AI
状态：施工基线 / Conditional Pass

## 1. Executive Summary

ZBC 当前已经具备较完整的生产基础：小红书主采集、Internal Browser、CDP、Resident Browser、Session Health/Recovery、Resource Library、Evidence Store/API/Dashboard、采集 Evidence、上传限制、平台术语统一、自动恢复、UI 精修和测试基线。近期审计记录显示 Resource Library 已验证 321 个资源可查询，Internal Browser 已完成 CDP 截图/页面控制、双账号以及域名白名单/SSRF 防护；Evidence 基础设施已接入健康与采集链路。

结论：Architecture Direction = PASS；Implementation Readiness = CONDITIONAL PASS；Release Gate = NOT COMPLETE。

核心判断：下一阶段不应重造 Browser、Resource、Evidence 等已有能力，而应通过 Contract / Adapter / Evidence 将现有能力收敛为 Zachary 可调用的通用 Runtime 能力。

## 2. Target Architecture

Zachary-OS-AI：通用 AI Runtime，负责 Model、Browser、Tool、Skill、Resource Retrieval、Evaluation、Evidence Contract、Context Isolation、Learning Signal。

Z-Brand-Core：专业产品 Runtime，负责太古汇 Subject Truth、采集、舆情、品牌/业态、事件、风险、报告、客户业务逻辑和产品数据。

双库通过 Contract / API / Adapter / Evidence 交互；禁止无边界内部依赖。

## 3. Non-Negotiable Boundaries

- SUBJECT_WORDS、SUBJECT_EXCLUDE_WORDS、subject_hit()、SUBJECT_HARD_FILTER 必须保留。
- LLM 不得单独决定“是否属于太古汇”。
- Zachary 不得直接修改 ZBC Product Truth、业务规则、风险阈值、权限、私有数据或 Runtime State。
- ZBC 产品数据进入 Zachary Learning Signal 前必须 Isolation → De-identification → Policy → Evaluation。
- 个性化只能改变 Style，不得改变 Truth、业务规则、安全和权限。
- 第三方 Browser Provider 不得成为 Zachary 核心业务逻辑。

## 4. Collector Audit

主线：小红书采集。现有体系已覆盖驻场浏览器、Session Health、Session Recovery、采集 Evidence 等。

必须继续形成统一 Collector Capability / Progress / Effectiveness Matrix，逐项确认 XHS Search、Note、Author、Comment、Topic、External Import、Image、Video、Text 等真实状态。禁止用旧文档推测当前实现。

采集失败必须形成 FAIL Evidence，不得将失败伪装成 0 条数据。

## 5. Subject Truth

当前方向正确，必须维持：Raw Content → Subject Hard Filter → Relevant → AI Analysis。

禁止 Raw Content → LLM → “我认为相关”。

## 6. AI Intelligence Upgrade

从传统 Sentiment 升级为：Emotion、Stance、Advocacy、Intent、Topic、Event、Propagation、Risk、Opportunity。

Emotion：细粒度情绪 + intensity + target + cause。
Stance：支持/认可/中立/质疑/反对/讽刺等。
Advocacy：推荐、主动传播、持续表达、互动和影响力的综合 Signal。
Event：Emerging → Growing → Peak → Stable → Declining → Closed。
Propagation：Volume + Velocity + Engagement Acceleration + Author Influence + KOL/KOC/UGC + Propagation。
Risk 与 Opportunity 双轨。

## 7. Multimodal

统一 Text + Image + Video + Metadata 为 Content Intelligence Object。后续可扩展 OCR/ASR、视觉语义、文本/画面一致性和冲突检测，但必须保留 Evidence。

## 8. Browser Runtime

现有 ZBC Internal Browser 是主要复用对象。目标结构：Zachary → Browser Contract → Adapter → Existing Internal Browser → Provider。

P0：Browser Contract、State Machine、BEEP、Policy、Permission、Session/Profile Isolation、Failure Classification、Safe Stop、Evidence、Playwright Adapter、Health/last_success_at、Zachary↔ZBC Decoupling。

BEEP：Precondition → Observe → Plan → Action → Post-condition → Evidence → Decision → Next。

Browser Alive 与 Task Success 必须分离。

## 9. Browser Providers

Playwright：P0 确定性执行/测试/Evidence。
PinchTab、Browser Use、Browser Harness：P1 候选适配层。
CloakBrowser：Research/Compatibility Lab，未经 License/Security/Version/Compatibility/Dependency Audit 不进入生产核心依赖。

## 10. Adaptive Decode & Compatibility

允许合法授权范围内的编码、格式、HTML/DOM、JSON/XML/CSV、Parser、Provider 和页面结构适配。

涉及认证绕过、Cookie/Session 窃取、CAPTCHA、DRM、付费权限或明确访问控制绕过时必须 Safe Stop + Evidence + Human Review。

## 11. Resource Library

统一 Resource Library 已落地基础，资料、案例、文件、学习材料、Evidence 等应统一资源模型，通过 Type/Category/Tag/Source/Domain/Product Scope/Provenance/Evaluation Status 分类。

Resource = Reference，不等于 Production Rule。

## 12. Zachary Learning

ZBC Production → Isolation → De-identification → Policy → Evaluation → Learning Signal → Zachary。

禁止产品 Truth、私有数据和 Runtime State 自动进入 Zachary 全局记忆。

## 13. Model Router

需要保持 Model Provider 独立：Local AI / Doubao / Cloud / Future Provider 均通过 Router 接入。

记录 Model、Prompt Version、Token、Latency、Provider、Success/Failure、Cost/Quality。

AI Output 不得直接成为 System Truth。

## 14. Evaluation

必须建立 Gold Set、Regression Set、Edge Cases、Human Correction、Model Result、Final Result，并计算 Precision/Recall/F1、False Positive/Negative、AI Override Rate、Drift。

模型更换、Prompt 更换、Provider 更换都必须经过回归。

## 15. Evidence

关键执行至少记录 URL、Timestamp、Source、Content ID、Browser、Profile、Session、Action、Before State、After State、Screenshot/Snapshot、Result、Provider、Error、Retry Count。

AI 声称成功 ≠ 系统成功。

## 16. Stability / Recovery

必须统一 Heartbeat、last_success_at、last_failure_at、watchdog、retry limit、cooldown、circuit breaker、crash recovery、stale session detection、collector recovery。

近期已修复 8200 legacy 端口硬编码导致旧实例复活的问题；后续必须以当前 HEAD 为事实，不得依赖旧记录。

## 17. External Import

目标限制：单次外部文件最多 10 个、总大小 ≤500MB；图片/视频单次最多 20 个且总大小 ≤500MB；批量图片/视频最多 30 个且总大小 ≤500MB；支持直接输入文案、粘贴导入、浏览文件选择；不直接接受文件夹作为批量导入对象。

当前已有 500MB 全局限制及 importer 相关修复，仍需按最新 Contract 做逐项测试。

## 18. Canonical Glossary

统一平台、内容、笔记、帖子、作者、账号、品牌、业态、事件、话题、情绪、立场、风险、机会、证据、资源、案例、Skill、Provider、Model、Session、Profile、Collector 等词条。Zachary 与 ZBC 必须使用同一 Canonical Glossary。

## 19. Security

重点检查 SSRF、Domain Allowlist、File Validation、Path Traversal、Secret Handling、Cookie/Session Isolation、Prompt Injection、Tool Permission、External Action Authorization、Audit Log。

网页内容属于不可信输入，不得直接升级为 System Instruction。

## 20. Reporting

报告体系应从数据罗列升级为 Decision Intelligence：发生了什么 → 为什么 → 谁推动 → 传播多快 → 风险 → 机会 → 建议。

## 21. Data Closure

最终闭环：采集 → Normalization → Dedup → Subject Truth → Content Intelligence → Emotion → Stance → Topic → Event → Propagation → Risk/Opportunity → Evidence → Report → Notification → Evaluation → Learning Signal → Zachary。

## 22. P0 Construction

P0-01 Browser Contract
P0-02 Browser State Machine
P0-03 BEEP
P0-04 Policy / Permission Gate
P0-05 Failure Classification + Safe Stop
P0-06 Evidence Contract 对齐
P0-07 Browser Health 状态统一
P0-08 Model Provider Independence 验证

## 23. P1 Construction

Fine-grained Emotion、Stance、Advocacy、Event Lifecycle、Propagation Intelligence、Multimodal Intelligence、AIGC Signal、Misinformation/Anomaly Signal、Skill Registry/Sandbox、Resource Pipeline、Evaluation Engine、Learning Signal、Provider Router。

## 24. P2 Construction

Propagation Graph、Advanced Prediction、Cross-platform Graph、Large-scale Multimodal、Browser Replay、Advanced Cost Optimizer、Advanced Personalization。

## 25. App Gate

当前 App Gate = NOT READY。

必须先通过 Model Independence + Browser Independence + Resource System + Context Isolation + Evidence + Evaluation + Stable ZBC Runtime + Release Gate。客户端只能作为 Client Layer，不复制核心 AI/业务逻辑。

## 26. Risk Ranking

1. 双库重复建设：Critical
2. AI 越权修改 Product Truth：Critical
3. Browser 与 ZBC 耦合：Critical
4. AI Output 直接成为 Truth：Critical
5. Evidence 与业务链断开：High
6. Event/Propagation 未完全工程化：High
7. Multimodal 尚未完全统一：High
8. Evaluation 不完整：High
9. Provider coupling：High
10. Personalization boundary：Medium

## 27. Test Gate

必须执行 Unit、Integration、Contract、E2E、Browser、Security、Import/Upload、Collector、Regression、Failure Recovery、Cross-Repo。

所有修改必须：可测试、可验证、可回滚、有 Evidence。

## 28. Construction Order

Repository Audit → Architecture Audit → Dependency Audit → Contract Audit → Runtime Audit → Test Baseline → Gap Matrix → Minimal Implementation → Unit → Integration → E2E → Browser/Evidence → Failure Recovery → Regression → Cross-Repo Audit → Release Gate。

## 29. Final Audit Decision

Architecture Direction：PASS
Implementation Readiness：CONDITIONAL PASS
Production Release：NOT READY
App Development：BLOCKED UNTIL RELEASE GATE

下一轮应从真实 HEAD 重新建立 Baseline，然后仅按 P0 Gap Matrix 进行最小施工；任何“大规模重构”均需要重新审计并证明必要性。
