# CTR-BROWSER-RUNTIME-P0-01
## Browser Runtime 分层 Contract（Contract → Router → Adapter → Provider）

> **Producer**: Zachary OSAI（研究侧，形成 Contract）
> **Consumer**: Z-Brand-Core（生产侧，施工）
> **Status**: APPROVED（用户已确认推进）
> **Date**: 2026-09-02
> **Baseline**: 遵循《Zachary × ZBC AI 编程基线 v1.0》— P0-BR-01 Browser Contract
> **上游审计**: aseline/AI-PROGRAMMING-CONSTRUCTION-REPORT-V1-20260902.md（OSAI 仓库）

---

## 0. 背景与动机

ZBC 现有浏览器能力栈存在**多实现并存**：
- internal_browser.py（CDP 9222/9223 驻场浏览器）
- collector_v2/browser_session.py（Session 层）
- Playwright 1.62.0 已安装但未封装为 Adapter
- 
esident_health.py（Browser Health 权威）

按《AI 编程施工报告 V1》P0-BR-01/P0-BR-10 缺口：**缺少统一 Browser Contract 分层**，导致调用方直接依赖具体 Provider（Zachary = Playwright / CDP 的耦合风险）。

**本 Contract 目标**：在**不破坏现有稳定功能**的前提下，建立 Browser Runtime 统一分层：
`
Zachary (OSAI)
    ↓
Browser Contract      ← 本文件（能力接口定义）
    ↓
Browser Router        ← Provider 选择/降级（P0-4 最小实现）
    ↓
Browser Adapter       ← 统一适配（CDP / Playwright）
    ↓
Browser Provider      ← 具体运行时（CDP 9222/9223 / Playwright 1.62）
`

---

## 1. 范围（Scope）

### 1.1 包含（IN）
- 定义 Browser Contract 能力接口（导航、快照、截图、动作、验证、证据）
- Browser Router：Provider 注册 + 选择 + 降级（含 feature flag）
- Browser Adapter：CDP Adapter（复用 internal_browser 逻辑）+ Playwright Adapter（最小封装）
- Evidence 对接：复用现有 evidence_store.py
- Health 对接：复用现有 
esident_health.py
- 单元测试 + 集成测试

### 1.2 不包含（OUT）——红线，禁止触碰
- **不改动** internal_browser.py / rowser_session.py 现有内部逻辑（仅新增外层封装）
- **不改动** SUBJECT_WORDS / subject_hit() 等产品 Truth
- **不替换** 现有 CDP 驻场浏览器运行方式
- **不引入** 重型第三方框架
- **不进入** App 开发阶段

---

## 2. Browser Contract 能力接口

`python
BrowserContract 能力集（P0）：
  navigate(url)                    → 导航（Precondition: 域名白名单/Policy Check）
  snapshot()                       → Accessibility/DOM 快照
  screenshot(path=None)            → 截图（Evidence）
  click(selector)                  → 点击（BEEP: Locate→Confirm→Click→Observe→Verify）
  type_text(selector, text)        → 输入
  get_text(selector)               → 读取文本
  wait_for(selector, timeout)      → 等待
  evaluate(js)                     → 执行 JS（受限）
  verify(expectation)              → 验证（POST-condition）
  record_evidence(...)             → Evidence（复用 evidence_store）
  health()                         → Browser Health（复用 resident_health）
`

**状态流转（对齐指令 §八）**：
`
INIT → BROWSER_READY → PAGE_READY → SESSION_VALID → TASK_READY
     → ACTION → VERIFY → SUCCESS
失败：VERIFY_FAILED → CLASSIFY_FAILURE（transient/session/page_changed/permission/platform_risk/unknown）
`

---

## 3. Contract 约束（Implementation Requirements）

- **R1**：调用方必须通过 Browser Contract 接口，禁止直接 new Provider。
- **R2**：导航前必须过 Policy Gate（域名白名单 + 安全边界），禁止导航到未授权域名。
- **R3**：点击/输入等写操作必须走 BEEP 流程（Precondition→Observe→Plan→Action→Post-condition→Evidence→Decision→Next），禁止"点击后默认成功"。
- **R4**：所有动作必须产生 Evidence（URL/Timestamp/Before/After/Screenshot/Result），禁止 AI 声称成功即成功。
- **R5**：失败必须分类（transient/session/page_changed/permission/platform_risk/unknown），禁止无限重试。
- **R6**：Provider 选择可配置（CDP/Playwright），feature flag 默认 CDP（不改变现有驻场浏览器行为）。
- **R7**：**禁止**将 Cookie/Token/Session/密钥写入 Evidence 或日志。
- **R8**：Zachary 通用 Browser Runtime 不得包含 ZBC 业务规则（产品规则在 ZBC 侧）。

---

## 4. 验收标准（Acceptance）

| # | 验收项 | 标准 |
|---|---|---|
| T1 | 分层存在 | Browser Contract / Router / Adapter / Provider 四层文件存在且可 import |
| T2 | 路由正确 | Router 按配置选择 CDP/Playwright，未知 Provider 报错 |
| T3 | 降级 | 首选 Provider 失败时能降级到备用（可配置） |
| T4 | 证据 | 关键动作 record_evidence 写入成功，无密钥泄露 |
| T5 | 健康 | health() 对接 resident_health，返回 browser/session/page/task 状态 |
| T6 | 红线 | 现有 internal_browser/browser_session 测试全绿，未改其逻辑 |
| T7 | 回归 | ZBC 全量测试 + E2E 全绿 |
| T8 | 安全 | secret_scanning 无新命中；无密钥入 Git |

---

## 5. 施工顺序

1. Browser Contract 接口定义（本文件 + rowser_runtime/contract.py）
2. Browser Router（rowser_runtime/router.py）
3. Browser Adapter（rowser_runtime/adapters/cdp_adapter.py + playwright_adapter.py）
4. Unit Test → Integration Test
5. E2E（用 staging 环境验证不破坏现有功能）
6. Evidence + Regression
7. Release Gate

---

## 6. 双库分工

| 层 | Owner | 动作 |
|---|---|---|
| 研究/基线/Contract | Zachary OSAI | 本文件 |
| 生产实现/测试/E2E | Z-Brand-Core | rowser_runtime/ 模块施工 |
| Evidence 反哺 | ZBC → OSAI | 运行质量数据回流 |

---

## 7. 完成定义（DoD）

- [ ] rowser_runtime/ 四层落地，feature flag 默认 CDP（不改现有行为）
- [ ] T1–T8 验收全绿
- [ ] Evidence 文档产出
- [ ] 双库交叉验证通过

---

*本 Contract 由 Zachary OSAI 形成，供 Z-Brand-Core 施工；不构成生产业务 Truth 修改。*

---

## 验收结论（2026-09-02 施工后）

**Contract: CTR-BROWSER-RUNTIME-P0-01 | 状态：T1-T8 全过 ✅**

| 验收项 | 结果 | 证据 |
|---|---|---|
| T1 分层存在 | ✅ | browser_runtime/ 四层（contract/policy/router/adapters）+ api 全部落地且可 import |
| T2 路由正确 | ✅ | 单测覆盖（test_policy_router.py）|
| T3 降级 | ✅ | get_with_fallback 可配置，默认不降级保稳定 |
| T4 证据 | ✅ | BEEPExecutor 每次执行回调 on_evidence，无密钥 |
| T5 健康 | ✅ | E2E 实测 CDP health=online（port 9222，XHS_CN_PRIMARY）|
| T6 红线 | ✅ | internal_browser/browser_session 未改，回归通过 |
| T7 回归 | ✅ | ZBC 全量 286 passed（269 基线 + 17 Failure Recovery）|
| T8 安全 | ✅ | 本地 secret scan 8 文件无密钥；HEAD 无 .env 入库（仅 .env.example）|

**E2E 实测（真实系统启动）**：
- `GET /api/browser-runtime/status` → 200，providers=[cdp,playwright]
- `POST /probe cdp health` → 200，online=true（小红书 explore）
- `POST /probe cdp navigate xiaohongshu.com` → 200，Policy Gate 白名单放行
- `POST /probe cdp navigate evil-example.com` → 400，failure_class=platform_risk（Cooldown/Stop）
- `POST /probe playwright health` → 200，status=up

**Failure Recovery 增强**：新增 17 项测试覆盖 transient 有限重试（禁止无限重试）、policy 拒绝→platform_risk 冷却语义、BEEP 失败分类闭环、Safe Stop。
