# Zachary × ZBC AI 编程基线 v1.0

状态：正式施工基线

## 目标
以当前 GitHub 源码为唯一施工事实，完成 Zachary-OS-AI 与 Z-Brand-Core 的源码级审计、差距识别、最小化收敛和可验证施工。不得为了新能力破坏现有稳定功能。

## 核心架构
Zachary 是通用 AI Runtime；ZBC 是专业产品 Runtime。共享通用能力，不共享产品 Truth、业务规则、权限、专属数据和 Runtime State。两库通过 Contract / API / Adapter / Evidence 交互，禁止无边界双向内部依赖。

## Browser Runtime P0
1. Browser Contract
2. Browser State Machine
3. BEEP：Precondition → Observe → Plan → Action → Post-condition → Evidence → Decision → Next
4. Policy / Permission Gate
5. Session / Profile Isolation
6. Failure Classification + Safe Stop
7. Evidence Contract
8. Browser Health / last_success_at
9. Playwright Adapter
10. Zachary ↔ ZBC Contract 收敛
11. Resource Library 与 Zachary 的统一调用边界
12. Context Isolation
13. Model Runtime / Browser Runtime 解耦

## Browser Provider 分层
Playwright：P0，确定性执行、测试和 Evidence 基础设施。
PinchTab：P1，Browser Control Plane 候选。
Browser Use：P1，学习 Agent Loop、Planning、Recovery、Loop Detection、Structured Output 等思想，不绑定核心架构。
Browser Harness：P1，研究 CDP / Existing Browser / Browser Attachment。
CloakBrowser：Research/Compatibility Lab，不作为默认生产依赖；必须 License、版本、安全和兼容性审计后再决定。

## Adaptive Decode & Compatibility
作为 Zachary 通用自适应能力，支持合法授权范围内的编码/格式/页面结构解析、转换、适配、Provider/Parser 选择、失败后重新观察和验证。任何涉及认证、第三方账号、CAPTCHA、DRM、付费权限或明确访问控制绕过的行为必须 Safe Stop + Evidence + Human Review，不得无限重试。

## Evidence
AI 声称成功不等于系统成功。关键执行必须形成 URL、Timestamp、Browser、Profile、Session、Action、Before/After State、Screenshot/Snapshot、Result、Provider、Error、Retry Count 等可验证证据。

## Skill Registry
Skill 与 Business Rule 分离。新 Skill 必须经历 Candidate → Sandbox → Test → Evaluation → Evidence → Review → Registry → Production，不得一次成功即永久进入生产。

## Resource / Learning
统一 Resource Library。资料、案例、文件、学习材料通过 Type/Category/Tag/Source/Domain/Product Scope 分类，不再建立互相割裂的底层资源系统。ZBC 生产数据只能经过隔离、脱敏、Policy、Evaluation 后形成 Zachary Learning Signal。

## 个性化
允许根据用户行为调整表达风格、推荐偏好、信息密度和交互习惯；不得改变系统 Truth、核心业务规则、安全边界、权限边界、数据真实性或物理性质。原则：个性化改变 Style，不改变 Truth。

## 施工纪律
1. 先审计后编码。
2. 以当前 HEAD、Branch、Version、Runtime、Dependencies、Tests、CI、Working Tree 为 Baseline Snapshot。
3. 先判断能力是否已存在、位置、所有者、调用关系、重复/冲突/缺失，再决定复用、收敛或新增。
4. 能复用绝不重造；只有真正缺失才最小新增。
5. Provider 可替换，业务逻辑不得与 Provider 耦合。
6. AI 输出不得直接成为 System Truth。
7. 失败必须可发现、记录和安全停止。
8. 新增修改必须有测试和 Evidence。
9. 不提前进入 App 开发。

## 标准施工顺序
Repository Audit → Architecture Audit → Dependency Audit → Contract Audit → Runtime Audit → Test Baseline → Minimal Implementation → Unit Test → Integration Test → E2E → Browser/Evidence → Failure Recovery → Regression → Cross-Repo Audit → Release Gate。

## P0/P1
P0：Browser Contract、State Machine、BEEP、Policy、Permission、Session/Profile Isolation、Failure Classification、Safe Stop、Evidence、Playwright Adapter、Browser Health、ZBC Browser Decoupling。
P1：PinchTab、Browser Use、Browser Harness、Skill Registry、Skill Sandbox、Browser Replay、Adaptive Decode & Compatibility、CloakBrowser Lab、Provider Benchmark、Browser Cost/Token Router。

## App Gate
Model Independence + Browser Independence + Resource System + Context Isolation + Evidence + Evaluation + Stable ZBC Runtime + Release Gate 全部通过后，才允许进入 Web/PC/iOS/Android 客户端阶段。App 只能是 Client Layer，不复制核心 AI 或业务逻辑。
