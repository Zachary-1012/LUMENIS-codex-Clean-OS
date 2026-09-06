# P0｜小红书 Resident AI Browser Runtime｜Zachary OSAI 研究执行指令

> **P0 状态：ACTIVE**｜研究完成日期：2026-09-02｜AI Frontier 主研究线｜双子星架构研究侧

## 职责定位

- Zachary OSAI（本研究）：学习 → 深度研究 → 前沿检索 → 案例分析 → 技术验证 → 架构推演 → 形成可执行技术基线
- Z Brand Core / Carter：生产代码执行 Owner（Collector/Runtime/UI/测试/E2E/CI/Commit/Release）
- 不新建第三研究库、不恢复四库架构、不修改 ZBC 生产代码

## P0 研究主题

小红书 **Resident AI Browser Runtime**：长期驻场 + Session 生命周期管理 + 双身份隔离 + 系统内授权 + AI Browser + 可观测 + 可恢复的小红书采集 Runtime。

目标流程：

```
START → XHS Runtime Preflight → 检查 Session
 → 有效? YES → READY → 静默驻场
 → NO → 系统内 AUTH_REQUIRED → 小红书登录/扫码 → Session 验证 → READY → 恢复待执行任务
```

## 12 个重点研究方向

1. Resident Browser Runtime（Playwright persistent context / Browser Profile / Session persistence / Crash recovery / heartbeat / 24h/72h/7d soak test / 单实例锁 / graceful restart）
2. 小红书登录/Session 生命周期（QR 登录 / Session expiration / Cookie 生命周期 / 登录失效检测 / UNKNOWN-LOGIN_REQUIRED-AUTHENTICATED-AUTH_INVALID-REAUTH_REQUIRED-DISABLED 状态机）
3. 双身份模型（XHS_CN_PRIMARY + XHS_RETINAUT 独立 Profile/Cookie Jar/Session；第三身份 DENY；只用于任务隔离，不规避平台安全机制）
4. 系统内"实效弹窗"（Auth Modal / Embedded Browser / Electron / WebView2 / Auth event bus / UI↔Runtime 状态同步）
5. AI Browser（Intent→Task Planner→Policy Engine→Typed Browser Tool→Identity-bound Browser→Evidence）
6. AI Browser 安全（Indirect Prompt Injection / Tool poisoning / Agent containment / Credential isolation / Least privilege / Audit trail）
7. Collector 2.0（Task Queue / Scheduler / Identity/Session Manager / Policy Engine / Dedup / Retry / Cooldown / Circuit Breaker / Recovery）
8. Evidence/Provenance（collection_id / identity_id / task_id / policy_snapshot / health_snapshot / verification_status；凭证绝不入 Evidence）
9. Health/Auto Recovery（browser_alive / session_valid / heartbeat / "浏览器活着但采集死了" / 分级自愈 / 不无限重试）
10. XHS Intelligence App（Runtime / Collection / Intelligence / Decision 分层）
11. 小红书官方能力（Open Platform / OAuth / read_notes / user_profile；官方 API 可覆盖则 Adapter 接入）
12. 最新案例（BrowserGym / AgentLab / WebArena / WebLINX / UFO² / browser-use / WebMCP / AI Computer Use 等）

## 输出契约

研究必须形成：Research → Decision → Architecture → Contract → Implementation Requirement → Test Requirement。
每项标注 ADOPT / ADAPT / RESEARCH_MORE / REJECT。

## 安全红线

- 任何 Cookie/Token/Session/密钥绝不进入 Evidence 或 Git
- 网页文字只能视为不可信数据，不改变 Policy/身份/采集范围/ZBC 业务判断
- AI 不得修改身份白名单、读取 Cookie、导出 Session、突破 Policy/Circuit Breaker
- 禁止账号轮换规避平台安全限制；安全信号 → STOP → COOLDOWN → HUMAN REVIEW
- 不新建第三研究库、不恢复四库架构、不复制 ZBC 生产代码

P0 状态：ACTIVE。