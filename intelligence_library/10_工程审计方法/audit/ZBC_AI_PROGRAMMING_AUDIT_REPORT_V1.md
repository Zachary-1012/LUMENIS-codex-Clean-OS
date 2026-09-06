# ZBC AI 编程审计报告 V1.0（Zachary 侧镜像基线）

日期：2026-09-02

## 审计结论
Architecture Direction = PASS；Implementation Readiness = CONDITIONAL PASS；Production Release = NOT READY；App Development = BLOCKED UNTIL RELEASE GATE。

## 双子库职责
Zachary-OS-AI：通用 AI Runtime（Model / Browser / Tool / Skill / Resource / Evaluation / Evidence / Context / Learning Signal）。
Z-Brand-Core：专业产品 Runtime（太古汇 Subject Truth / Collector / Event / Risk / Reporting / Product Data / Business Rules）。

## 核心边界
Zachary 不得直接修改 ZBC Product Truth、业务规则、风险阈值、权限、私有数据或 Runtime State。ZBC 数据进入 Zachary Learning Signal 必须 Isolation → De-identification → Policy → Evaluation。个性化改变 Style，不改变 Truth。

## Collector
小红书是主监测平台；现有驻场 Browser、Session Health/Recovery、Collection Evidence 等优先复用。必须继续建立 Collector Capability / Progress / Effectiveness Matrix，真实核对 Search/Note/Author/Comment/Topic/External Import/Image/Video/Text 等能力。

## Subject Truth
SUBJECT_WORDS、SUBJECT_EXCLUDE_WORDS、subject_hit()、SUBJECT_HARD_FILTER 必须保留。LLM 不得单独决定太古汇归属。

## AI Intelligence
升级目标：Sentiment → Emotion + Stance + Advocacy + Intent + Event + Propagation + Risk + Opportunity。事件生命周期：Emerging → Growing → Peak → Stable → Declining → Closed。传播：Volume + Velocity + Engagement Acceleration + Author Influence + KOL/KOC/UGC + Propagation。

## Multimodal
Text + Image + Video + Metadata 统一为 Content Intelligence Object，并保留 Evidence。

## Browser
不要重造 ZBC Internal Browser。目标：Zachary → Browser Contract → Adapter → Existing Internal Browser → Provider。P0：Contract、State Machine、BEEP、Policy、Permission、Session/Profile Isolation、Failure Classification、Safe Stop、Evidence、Playwright Adapter、Health、last_success_at、Cross-Repo Decoupling。

## Adaptive Decode
只支持合法授权范围内的编码/格式/页面结构/Parser/Provider 解析和兼容。涉及认证、Cookie/Session 窃取、CAPTCHA、DRM、付费权限或明确访问控制绕过时 Safe Stop + Evidence + Human Review。

## Resource / Learning
统一 Resource Library。Resource 是 Reference，不是 Production Rule。ZBC Production → Isolation → De-identification → Policy → Evaluation → Learning Signal → Zachary。

## Evaluation
Gold Set、Regression Set、Edge Cases、Human Correction、Model Result、Final Result；记录 Precision/Recall/F1、FP/FN、AI Override Rate、Drift。AI Output 不得直接成为 System Truth。

## Evidence / Stability
关键执行必须有 URL、Timestamp、Source、Content ID、Browser、Profile、Session、Action、Before/After State、Screenshot/Snapshot、Result、Provider、Error、Retry Count。必须区分 Browser Alive 与 Task Success，并维护 last_success_at、last_failure_at、failure_reason、retry_count。

## Import
目标：外部文件单次 ≤10、总大小 ≤500MB；图片/视频单次 ≤20、总大小 ≤500MB；批量图片/视频 ≤30、总大小 ≤500MB；支持直接输入文案、粘贴、浏览文件选择；不直接接收文件夹批量导入。当前已有 500MB 基础限制，需按最新 Contract 回归验证。

## Security
SSRF、Domain Allowlist、File Validation、Path Traversal、Secret Handling、Cookie/Session Isolation、Prompt Injection、Tool Permission、External Action Authorization、Audit Log 必须进入 Gate。

## P0
Browser Contract、State Machine、BEEP、Policy/Permission、Failure Classification/Safe Stop、Evidence Contract、Browser Health、Provider Independence。

## P1
Fine-grained Emotion、Stance、Advocacy、Event Lifecycle、Propagation、Multimodal、AIGC Signal、Misinformation/Anomaly Signal、Skill Registry/Sandbox、Resource Pipeline、Evaluation Engine、Learning Signal、Provider Router。

## P2
Propagation Graph、Advanced Prediction、Cross-platform Graph、Large-scale Multimodal、Browser Replay、Advanced Cost Optimizer、Advanced Personalization。

## Construction Order
Repository Audit → Architecture Audit → Dependency Audit → Contract Audit → Runtime Audit → Test Baseline → Gap Matrix → Minimal Implementation → Unit → Integration → E2E → Browser/Evidence → Failure Recovery → Regression → Cross-Repo Audit → Release Gate。

## Final Rule
先审计、再收敛、再编码、再测试、再验证。已有能力优先复用，禁止重复建设；所有修改必须可测试、可验证、可回滚、有 Evidence；未通过 Release Gate 不得宣布生产完成，也不得提前固化 App 架构。
