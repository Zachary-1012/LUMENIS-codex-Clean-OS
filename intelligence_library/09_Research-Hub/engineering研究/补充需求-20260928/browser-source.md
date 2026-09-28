# 补充需求：Browser / Session / Permission / SYS-06 源码核验

**核验基线**：当前本地 refs 显示 HEAD = origin/main = ac27acf543b9c9f86eb9ede5e2d9b429f58782cb。首次基线 4ef4a038，之后的比较点为 1b9ffa33。以下源码行号来自指定 Git 提交对象，不采用脏工作树候选。

**DOCX 原文坐标**：统一引用 doc-extraction.md 的 BODY.P001–P1193 原始段落编号。本文只覆盖 BODY.P001–P053、P102–P370、P375–P541、P545–P684、P686–P925。未使用基于 802 个非空段落的二次编号。

**基线差异复核**：
- 4ef4a038..1b9ffa33 的本范围差异并非空：修改了 lumenis/system/collector/adapters/secondary_collection.py、lumenis/system/collector/adapters/x_platform.py、scripts/start_resident_browsers.py，并新增 tests/test_x_readonly_worker_route.py。
- secondary_collection.py:668-700、1011-1056 增加 X 的显式预启动人工采集授权与精确资源绑定；普通 X 搜索未获该预授权时被拒绝。x_platform.py:37-52 增加平台状态映射，110-122 的 health_check 只返回 NEED_VERIFY 或 NOT_CONFIGURED，不证明实时登录。
- scripts/start_resident_browsers.py:103-113、250-286、302-312 增加独立 X_READONLY worker 计划及显式启动入口：9226、loopback、专用 profile 路径、about:blank；默认启动不选择该身份。这里只检查了源码 diff，没有创建、打开或启动该 profile。
- 新增 tests/test_x_readonly_worker_route.py:16-98、269-286 覆盖显式 opt-in/profile binding、默认启动隔离、状态映射和 health metadata 不声称 live session；本次没有运行测试。
- 1b9ffa33..ac27acf5 的本范围差异只有 lumenis/system/collector/adapters/scheduling/prelaunch_baseline.py:335-360：允许每个 source 指定经格式校验的 plan_version。Browser/Session API、Permission、SYS-06、Flutter 投影、相关 spec 和 owner/security governance 在这两个提交间无变化。
- 所以 API/SYS-06/Permission 行号核验仍成立；Round 06 的 Collector 适配器状态与 resident worker 路径必须按 1b9 的增量补充，不能沿用“相关源码差异为空”。

## 当前结论

- 复用既有 SYSTEM Browser / Collector / Permission / Evidence，不新建 owner，与当前结构一致。Source Owner Index 将 SYSTEM browser/session 指向 lumenis/system/browser/runtime/；Round 04 管身份/Permission/Evidence，Round 06 管 Collector/Browser/Session，Round 08 管跨面 Experience，Round 14 管剩余 SYS Experience，Round 15 管真实用户 E2E / Release（00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md:18-27,109-111）。
- 已发布源码有多个 API/session seams，尚不足以证明唯一 Session Authority：browser_runtime_api.py 只提供运行状态/probe；ai_browser_api.py 提供 actor-owned AI Browser session/frame；browser_surface_api.py 提供 Browser Surface；Collector 内存在两套 BrowserSession 文件。以现有 SYSTEM Browser / Collector owners 收敛调用链，不新增并行 owner。
- DOCX 提出的完整 viewport/tab/address/navigation/actions UI 与 SYS-06 当前屏幕合同冲突。SYS-06.md 标记 DESIGN_EXPLORATION、Product Owner approval PENDING；现有约定限于只读能力/状态，无 viewport 或 tab/snapshot action，且要求 authenticated runtime E2E（contracts/experience/screen-specifications/SYS-06.md:1-16,33-60,86-115）。因此全浏览器 UI 仍是待设计决策的候选。
- DOCX 中 SESSION_EXPIRED 是未经 runtime 核验的当前状态主张。源码能表达此状态，但没有验证当前账号、平台登录或 session 状态。
- “不依赖第三方 Cookie 转换网站”可以作为约束。仓库有内部 Cookie helper/vault，但它们不证明用户可导入 Cookie、授权成立或 session 健康；普通用户流不应粘贴 Cookie。

## DOCX 主张映射

| DOCX 原文位置与主张 | 当前证据与状态 | 适配 / Round |
|---|---|---|
| BODY.P001–P053：用户明确授权平台和范围；公开源优先；平台 session 与 LUMENIS 产品账户分开；采集 opt-in、可停止/撤销；凭据仅本机 | AI Browser API 要求 actor/account-session 与 SYSTEM/browser grant（ai_browser_api.py:41-58）；Browser Surface API 也检查 actor/Permission（browser_surface_api.py:19-38）。现有精确 Subject/BrandFocus scope checker 在 lumenis/system/security/permission.py:388-449；但 Browser API 的 guard 未显示把平台、字段、Subject/BrandFocus 授权绑定到 session。Security boundary 明确平台 session 与产品账户分开（00-GOVERNANCE/SECURITY-BOUNDARY-CURRENT.md:24-31）。 | ADAPT：Round 04 定义既有 Permission 的授权/撤销/精确范围；Round 06 绑定 collection request。产品账户不作为入口墙，平台 session 不等于产品账户。 |
| BODY.P102–P370：CDP、持久 Profile、默认浏览器、Cookie/身份、安全隔离 | ai_browser_api.py:137-165 固定 CDP 9224、headless、拒收调用方 user_data_dir，并创建 actor/account-session-owned session；ai_browser_runtime.py:1273-1285,2079-2094 拒绝调用方指定 browser/profile。tests/test_browser_surface.py:355-363 的默认浏览器 helper 是 mock 测试。4ef4..1b9 新增 X_READONLY 独立 worker，配置专用 profile 路径，显式启动且默认不启用（scripts/start_resident_browsers.py:103-113,250-286,302-312）。 | 部分静态实现：存在隔离 AI Browser session 与显式 X worker 路径；没有真实默认浏览器/已登录 profile E2E 证据。X_READONLY worker 不等同于产品级跨平台 Session Authority，也不证明某平台已授权。Round 06。 |
| BODY.P375–P541：公开来源不带 Cookie/Auth；授权来源与敏感字段分流；凭据不泄漏 | public_source.py:369-370 拒绝 Authorization/Cookie。Browser Surface API:19-55 执行 actor/Permission 检查并过滤其响应中的 cdp_port/port/profile/ws_url/account；该过滤仅对该 API 路由成立。experience_screens.py:1993-2027 生成的 SYS-06 rows 仍包括 account/port；Flutter projection 只取状态字段，但不能据此说原始 Experience JSON 已脱敏。 | ADOPT 分流原则，Round 06 验证各入口响应脱敏和 public/auth 分流；不得将单一路由的过滤器当全局保证，字段不可用状态不得由 AI 补造。 |
| BODY.P545–P684：Frame API 与 SYS-06 浏览器界面/屏幕不可用 | ai_browser_api.py:233-265 有 actor-owned session 的 no-store PNG frame 与 metadata。Flutter sys06_repository.dart:13-17 仅调用 screen ViewModel；sys06_snapshot.dart:24-55 解析 KPI/实例状态；sys06_screen.dart:89-114,138-209,220-258 展示能力统计与状态，没有 viewport/address/tab/action binding。lumenis_workspace_routes.dart:97-105 将 SYS-06 放入 unavailableScreenIds。SYS-06 spec 仍为 DESIGN_EXPLORATION、approval PENDING。 | 既有 frame API 不代表 SYS-06 已接入。完整浏览器 UI 是 Round 14 的设计候选，先按 Experience Constitution 形成 DESIGN_READY 屏幕规格并解决合同冲突，再决定调用路径。 |
| BODY.P686–P925：第三方 Cookie 转换、会话导入/恢复、session handle 收敛到 Collector | cookie_vault.py:285-294 有内部 helper；tests/test_cookies_import_api.py:59-141 是 API 测试源。4ef4..1b9 的 X Collector 变化只证明显式预授权的人工 X 采集入口和状态映射（secondary_collection.py:668-700,1011-1056；x_platform.py:37-52,110-122），没有证明跨平台唯一 session_handle、授权撤销传播、持久 health/recovery 或真实 E2E。ac27 的 prelaunch_baseline.py:335-360 只改变 source plan_version 校验。 | REJECT 第三方转换网页作为 runtime dependency；内部 helper 不是用户导入能力。ADAPT 会话收敛到既有 Owner：Round 04 Permission → Round 06 Browser/Collector → Round 08 surface → Round 14 SYS-06 → Round 15 real-user E2E。 |

## API / ViewModel / Screen / Tests 的关键边界

- SYSTEM Runtime facade：browser_runtime_api.py:1-18,20-60 只提供 /api/browser-runtime/status 与 /probe，不是用户 session/frame API。
- AI Browser API：ai_browser_api.py:41-58 要求当前 actor 与 SYSTEM/browser 权限；137-165 强制隔离的 9224/headless session；233-265 提供 no-store PNG frame。tests/test_ai_browser_default_engine.py:171-192,195-207,230-271 覆盖调用方 browser/profile 拒绝、actor/grant、登录隔离与 frame 状态类契约；属于 mock/unit contract tests。
- Browser Surface API：browser_surface_api.py:19-55,63-77,93-114 有 actor/权限 gate，拒绝调用方 account/port 选择并过滤响应字段。tests/test_browser_surface.py:217-253,349-404 是模拟 API/隔离行为测试；默认浏览器测试也 mock resolver。
- SYS-06 绑定：experience_runtime.py:672-690 暴露 screen ViewModel；experience_screens.py:1993-2027 调用 browser_surface.capability_report() 并返回统计/状态 rows。Flutter repository 仅读 screen endpoint；snapshot 只保留 KPI/状态。路由仍将 SYS-06 标为 unavailable（app/lib/navigation/lumenis_workspace_routes.dart:97-105）。
- Experience authority：contracts/experience/screen-specifications/SYS-06.md:1-16 为 DESIGN_EXPLORATION / approval pending；33-60,86-92 限为只读能力状态，没有 viewport/action binding；101-115 要求 authenticated runtime E2E。contracts/experience/screens/SYS-06/SYS-06.viewmodel.json:8-37 把 browser binding 标为 UNKNOWN；SYS-06.actions.json:7-67 的 scope/success/failure/evidence 仍 UNKNOWN。
- E2E truth：tests/test_browser_e2e.py:1-5,14 明确该测试是 retired personal CDP-port safety regression，不是 SYS-06 真实用户 E2E。本次所有测试均未运行。
- 公共来源：public_source.py:369-370 拒绝 Cookie 与 Authorization。登录采集需要 Round 06 证明授权 session、平台限制及 Evidence/Canonical 路径。

## 工作树、Runtime 与安全边界

- 当前 HEAD 与 origin/main refs 为 ac27acf543b9c9f86eb9ede5e2d9b429f58782cb，branch main...origin/main。工作树已有大量 modified/deleted 候选；没有读取其 diff hunks，也没有把候选计入已发布能力。本报告只读 Git 提交对象，没有修改仓库。
- Runtime：NOT VERIFIED / NOT PROBED。没有服务启动、HTTP 调用、浏览器启动或账号/Profile/Cookie/数据库访问。SESSION_EXPIRED 仅为文档中的状态主张，不能当成当前事实。
- Tests：NOT RUN。只读测试源码和 Git 差异；没有执行浏览器、账号或采集测试。
- 安全确认：没有读取或访问任何 Cookie、浏览器 Profile 内容、账号或真实会话，也未启动 resident browser。XHS/RedNote Mainland China 个人账号与 Profile 未触碰；任何实际 XHS 使用仍须遵守 AGENTS.md 的 allowlisted identity 边界。
- 未验证项：X_READONLY worker 的实际运行、profile ownership、跨重启恢复、登录状态、授权撤销传播、采集 E2E、SYS-06 runtime/E2E 均未验证。

## 给主控的最小 Batch 建议

1. Round 04：在现有 Permission/Evidence owner 定义 server actor、平台、资源范围（CTH Subject/BMP BrandFocus、字段/动作）、有效期与撤销；授权不得由 UI/session 反推。
2. Round 06：在最新 main 与受保护候选核对后，跟踪 browser_runtime_api、ai_browser_api、browser_surface_api、lumenis/system/browser/runtime、Collector session callers 和 Cookie vault 的调用链；在同一既有 owner 内证明 session handle → Collector → Evidence → Canonical。验证 public-source 拒凭据、未授权/过期/撤销 fail-closed、真实 allowlisted identity、脱敏、失败恢复与幂等。DOCX 所述大半完成和当前 SESSION_EXPIRED 都不能替代这些证据。
3. Round 14：不直接实现 DOCX 的全浏览器 UI。先产出经审核的 DESIGN_READY SYS-06 specification，处理其与只读能力状态合同的冲突；之后再评估 Web/Desktop/Mobile frame/return/error binding。Round 15 使用真实用户任务闭环验收。
