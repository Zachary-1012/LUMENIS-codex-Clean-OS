# Zachary × ZBC AI 编程基线 v1.0

状态：正式施工基线

Zachary 是通用 AI Runtime；ZBC 是专业产品 Runtime。共享通用能力，不共享产品 Truth、业务规则、权限、专属数据和 Runtime State。两库通过 Contract / API / Adapter / Evidence 交互，禁止无边界双向内部依赖。

## P0 Browser Runtime
- Browser Contract
- Browser State Machine
- BEEP：Precondition → Observe → Plan → Action → Post-condition → Evidence → Decision → Next
- Policy / Permission Gate
- Session / Profile Isolation
- Failure Classification + Safe Stop
- Evidence Contract
- Browser Health / last_success_at
- Playwright Adapter
- Zachary ↔ ZBC Contract 收敛
- Resource Library 与 Zachary 的统一调用边界
- Context Isolation
- Model Runtime / Browser Runtime 解耦

## Provider 分层
Playwright 为 P0 确定性执行、测试和 Evidence 基础设施；PinchTab、Browser Use、Browser Harness 为 P1 候选/研究适配层；CloakBrowser 仅作为 Compatibility Lab，未经 License、版本、安全、兼容性审计不得进入生产依赖。

## Adaptive Decode & Compatibility
仅用于合法授权范围内的编码、格式、页面结构解析/转换/适配、Provider/Parser 选择和验证。涉及认证、第三方账号、CAPTCHA、DRM、付费权限或明确访问控制绕过时必须 Safe Stop + Evidence + Human Review。

## Resource / Learning
统一 Resource Library。ZBC 生产数据必须经过隔离、脱敏、Policy、Evaluation 后才可形成 Zachary Learning Signal。产品业务 Truth 不得自动进入 Zachary 全局记忆。

## 个性化
可改变表达风格、推荐偏好、信息密度和交互习惯；不得改变 Truth、核心业务规则、安全边界、权限边界、数据真实性或物理性质。个性化改变 Style，不改变 Truth。

## 施工纪律
先审计后编码；以当前 HEAD/Branch/Version/Runtime/Dependencies/Tests/CI/Working Tree 建立 Baseline Snapshot；已有能力优先复用；重复则合并；冲突则隔离/修正；缺失才最小新增；Provider 可替换；AI 输出不得直接成为 System Truth；失败必须可发现、记录和 Safe Stop；新增修改必须有测试和 Evidence；不得提前进入 App 开发。

## 标准顺序
Repository Audit → Architecture Audit → Dependency Audit → Contract Audit → Runtime Audit → Test Baseline → Minimal Implementation → Unit → Integration → E2E → Browser/Evidence → Failure Recovery → Regression → Cross-Repo Audit → Release Gate。

## App Gate
Model Independence + Browser Independence + Resource System + Context Isolation + Evidence + Evaluation + Stable ZBC Runtime + Release Gate 全部通过后才允许进入客户端阶段；App 只能是 Client Layer，不复制核心 AI 或业务逻辑。
