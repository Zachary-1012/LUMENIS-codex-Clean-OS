# 补充需求.docx → 当前序境 15 轮适配研究（只读，2026-09-28）

## 结论与证据等级

文档的可采纳增量是：用户主动连接获准平台；平台会话与终端用户采集许可分开；凭据留在本地；公开字段优先用公开来源、需要登录的字段才用获准会话；真实数据进入 Raw/Evidence/Canonical 和正确的 CTH Subject 或 BMP BrandFocus；失效、撤销、错误身份和离线均给出真实恢复状态；SYS-06 最终让用户在任务中检查受控来源并返回。此增量属于现有 ROUND 04、06、08、14、15；ROUND 03 的实体和市场关系是业务数据依赖。无第 16 轮、第二套 Browser/Permission/Collector/DB/账号或新的产品域。

本次只读研究未运行服务、登录、采集、数据库查询、测试或真实用户 E2E。源码存在表示 IMPLEMENTED SOURCE 的局部能力，文档转述的 SESSION_EXPIRED、139/139 PASS、69 PASS/12 FAIL 和“后端大半完成”均非本次确认的运行事实。实时登录状态和 SYS-06 可用性分别为 LIVE_NOT_VERIFIED 与未通过现有设计/绑定闸门。

证据快照：起始 fresh fetch 为 4ef4a0382cf51c69f0bb6ea3d5ca4538350b0353；研究中主控连续推进并提交 X 手动采集与公开来源维护：第二次 fresh fetch 为 1b9ffa33f638a31afeb0131005e21b6852802379；随后 HEAD=origin/main=ac27acf543b9c9f86eb9ede5e2d9b429f58782cb（本地只读复核）。1b9ffa33 的 CURRENT 记录报告 3 条 X 手动记录的 Raw/native/Canonical 与签名 Evidence，以及两条 BMP 公共来源；ac27acf5 在原有 190 个计划历史 ID 不变的前提下增加逐来源 plan version。两提交的已发布状态均保留 ROUND 06 REWORK。以上为提交与 CURRENT 记录，不是本次独立运行复验。共享工作树在核验时有大量受保护未提交候选，且暂存状态曾短暂变化；主控分派 Batch 前必须再取当时的 HEAD、origin/main、index 和精确路径 diff。此研究没有改仓库。

原文：D:\wps云空间\WPS Cloud\WPSDrive\280397037\WPS云盘\补充需求.docx，SHA-256 3a5b6689a73301d1f65b29acdfef2aafbcdc284d970995f692656a8202592afb。完整 1,193 个 BODY.P 段落位置见 doc-extraction.md；23 项去重清单见 feature-inventory.md。无原生 Word 表格、图片、批注或脚注；P970–P988 的对照表是普通段落文本。包内声称 27 页，渲染器不可用，故只以稳定段落位置定位，不声称页码。下表按清单逐项对应；“主线”指主控正在推进的真实多平台/全球数据链，不表示该项已经交付。

## 逐项适配表（一）

| # / 原文位置与准确含义 | 当前状态及依据 | 决策、既有 Round/进入依赖、接收建议 |
|---|---|---|
| 1 / P001–P007：现有 Browser、Collector、Permission、Evidence、Canonical、SYS-06 合龙，先核主线与受保护候选 | ADOPT 当前真相规则。两次 fresh fetch 见 main 由 4ef4a038 进至 1b9ffa33；后续只读核验又进至 ac27acf5；本地候选仍独立，文档旧测试数字不可继承。AGENTS.md:47–69、Source Owner Index:12–32。 | 当前任务已覆盖；B0 由“序境12”在下次安全检查点做精确路径 reconciliation；ROUND 01/02 的持续真相职责，无新 Round；主线是。 |
| 2 / P009–P013、P064–P080、P736–P845：主动连接、明确范围、正常登录或复用、失效恢复，不能承诺永久免登录 | ADAPT。ai_browser_api.py:41–58,137–204 有 actor-owned session，但限制 9224/headless/不接 caller profile；它不是终端用户所选平台 Session。当前未见完整连接/恢复 UX 或真实身份 E2E。 | 当前可并行做 B1 合同设计，ROUND 04 权限后 ROUND 06 session；用户操作 UI 交“序境 UI/UX 独立设计方案”按现有 screen gate，之后 ROUND 14；主线在需登录字段时是。 |
| 3 / P015–P020、P042–P048：连接许可不自动采集；MANUAL 默认、AUTO 明确 opt-in；切换焦点不授权；只读、暂停/恢复/撤销和在途响应 | ADOPT 原则，ADAPT 绑定。Global Contract:27–50,94–110 已定 focus 与采集解耦；permission.py:388–449 有 exact scope checker。Browser API 的 SYSTEM/browser grant 还不能证明平台/字段/实体 grant 与撤销传播。 | 当前可并行 B1，ROUND 04 → ROUND 06；现有公开 prelaunch baseline 的获准维护是另一 scope，不被终端用户 AUTO 默认规则误关；主线是。 |
| 4 / P022–P026、P507–P542：Cookie/Token/Profile 本地保管；无关账号不得读；身份和会话能力验证才显示已连接 | ADAPT。browser_surface_api.py:19–55 过滤部分传输字段，但 experience_screens.py:1993–2027 仍生成 account/port rows，需逐 API 检查响应投影；Flutter 当前只取 KPI/state，不证明所有入口安全。静态源码未探测账号。 | 当前可并行 B1 安全核查，ROUND 04/06；HK/international allowlist 是 XHS 唯一许可，CN 个人账号绝不可触碰；主线在授权源时是。 |
| 5 / P028–P033、P1161–P1175：公开字段走公开源，登录字段走获准 Session；Source→Capture/Raw→Evidence→Canonical→准确 CTH/BMP→页面/报告 | ADOPT 现有业务链。public_source.py:369–370 拒 Authorization/Cookie；1b9ffa33 的 CURRENT 记录及源码增加 X 手动与 BMP 公共来源的局部证据；ac27acf5 延续公开基线维护历史。多平台全字段、全国别、网页/报告 E2E 尚未证明。 | 当前任务已覆盖于“序境12”及各国家数据线程；ROUND 03 身份/关系、04 权限、06 采集、09–14 业务、15 E2E；不得新起数据链 Batch 或缩小 14 国家组×双域基线；主线是。 |
| 6 / P375–P450、P1161–P1175：逐平台/字段区分公开、登录、限流和不可得，缺失不得补零或用 AI 补事实 | ADOPT。public_source.py:369–370 是局部来源边界，已有状态枚举不证明平台字段覆盖。文档的“授权即可获得相同维度”反例应作为采集验收矩阵。 | 当前任务已覆盖；ROUND 06 每平台原生字段、跨平台映射、原始/发布/事件/派生时间与历史序列均验；ROUND 03/12/13 消费；主线是。 |
| 7 / P031–P033、P044–P045：至少一个真实 CTH 和 BMP 样例落到正确对象；样例不等于全平台完成 | ADAPT 为最低 E2E 样例。ROUND 03 的已发布投影仍 UNREVIEWED，Global Commercial/Brand Coverage NO，广州深度 PARTIAL；现场品牌与品牌市场不可混同。Source Owner Index:216–219。 | 当前任务已覆盖；ROUND 03 实体身份/市场关系通过后，ROUND 06/09–13/15 按非参考随机实体扩大；“序境12”和国家数据线程继承，主线是。 |
| 8 / P035–P040、P545–P595、P1112–P1155：SYS-06 给出真实来源画面、来源/加载/失败/返回/授权状态，不能把状态面板冒充浏览器 | ADAPT，当前缺真正绑定。app/lib/navigation/lumenis_workspace_routes.dart:97–105 标为 unavailable；sys06_repository.dart:13–17、sys06_snapshot.dart:24–55、sys06_screen.dart:89–258 仅 screen KPI/实例状态。SYS-06.md:1–16 仍 DESIGN_EXPLORATION/approval PENDING。 | 后续既有 ROUND 14；先 B3 设计审查再 B4 UI 绑定，受 ROUND 04/06 的真实 Actor、Frame 和 Permission 依赖；UI 线程接设计，“序境12”接集成；主线的数据采集不因 UI 等待停下。 |
| 9 / P598–P635：sessions/frame/navigate/observe/action/verify/evidence 与 frame ID/target/revision/capture time 是可复用契约 | ADAPT，API 源码确有：ai_browser_api.py:137–204,233–265,289–490；Frame 为 actor-owned no-store PNG。它不是通用登录态 Collector Session；现有 Flutter 无 frame binding。 | 后续 ROUND 06 验权限/目标版本，ROUND 14 的 B4 才消费经确认的 API；旧帧和晚到响应必须丢弃。主线只在受控浏览采集时受影响。 |
| 10 / P042–P052：同候选做首次连接→登录/复用→CTH/BMP 结果→重启→过期恢复→撤销拒绝，拒绝写动作和泄漏，交付真实入口/线上状态 | ADOPT 为验收卡，当前 NOT RUN。当前测试源包括 test_ai_browser_default_engine.py、test_browser_surface.py，但多为模拟/隔离；test_browser_e2e.py:1–14 是废弃个人端口的安全回归，不是用户 E2E。 | 后续 ROUND 04/06/14 各自真实用户工作 E2E，ROUND 15 才综合发布；B5 由“序境12”整合，真实 HK 授权与设备可用才执行；主线的两个样例不能替代全局覆盖。 |
| 11 / P161–P209、P736–P760：只列实际支持的默认浏览器、Chrome/Edge、受控独立浏览器选择 | ADAPT。cdp_helper.py 有默认浏览器识别，test_browser_surface.py:355–363 仅 mock Windows resolver，未证明用户默认个人 Profile 能安全接管；Playwright/Chrome 官方约束见研究节。 | 当前可并行 B3 设计选择语义，ROUND 06 核实际引擎/隔离，ROUND 14 才呈现可用项；不将“默认浏览器”解释为个人 Profile 授权；主线否。 |

## 逐项适配表（二）

| # / 原文位置与准确含义 | 当前状态及依据 | 决策、既有 Round/进入依赖、接收建议 |
|---|---|---|
| 12 / P102–P158、P350–P371、P927–P943、P966–P1002：CDP、持久 Profile、Cookie helper 与 Browser/Collector 资产复用 | ADAPT。lumenis/system/collector/runtime/browser_session.py:13–61,105–147 与 runtime/session/browser_session.py:13–93 均有实现 seam；Browser 的 canonical owner 是 lumenis/system/browser/runtime/（Owner Index:109–111）。源码存在不等于单一生产调用链。 | 当前可并行 B0 精确 caller/测试/差异盘点后再 B2 收敛，ROUND 06；保护本地重叠候选，绝不另建 owner；主线在登录源时是。 |
| 13 / P213–P290：General、HK RedNote、Douyin 只读身份/Profile 隔离 | ADAPT 安全原则。脚本与代码中有角色痕迹，但 resident 启动配置在 1b9ffa33 有更新，未对账号、Profile、端口运行态做任何检查；文档列出的角色/在线状态不能直接继承。 | 当前可并行 B0 静态范围核对，B2 才验获准身份；ROUND 05/06；CN 个人 XHS 禁止被启动、探测或 fallback；主线在对应平台时是。 |
| 14 / P292–P346、P849–P881、P1082–P1110：RedNote 旧 Cookie 文件门禁、曾 SESSION_EXPIRED，目标为复用获准 Profile 并恢复登录 | ADAPT 目标；REJECT 当前运行断言。xhs_cookie_bridge.py、xhs_p0_orchestrator.py 和 Browser owner 有本地候选，但本研究未读凭据/会话，不能确认现在 SESSION_EXPIRED 或 HK 可用。 | B0 静态 reconciliate → B2 仅获准 HK/international 环境验证，ROUND 06；无合法实际会话则标 BLOCKED/LIVE_NOT_VERIFIED，绝不请求或触碰 CN 个人账号；主线是。 |
| 15 / P686–P734：第三方 Cookie 转换网页可借鉴但不依赖；隐藏粘贴/JSON/Storage State 导入可选 | REJECT 第三方网页作为产品依赖；DEFER 手工导入 UI。lumenis/adapters/cookie_vault.py:285–294 与 tests/test_cookies_import_api.py:59–141 是内部 helper/测试，不证明产品授权或安全迁移完成。 | 仅登记现有 ROUND 04/06/14 技术债；没有本轮 Batch；若未来必要，先单独 Secret/Permission/Experience 决策；主线否。 |
| 16 / P801–P845：连接状态、最近验证、按能力可用性、AUTO 关闭、重新验证/断开、恢复同一 Profile | ADAPT 为真实状态设计，不新增产品线。SYS-06 目前只展示受控实例状态，未见平台/字段级 Session Health 与恢复的 ViewModel/E2E；“已连接”不能由文件存在推断。 | B3 在 UI 线程明确文案/状态/回路，B1/B2 先产真实服务端状态，ROUND 04/06→14；主线在登录源时是。 |
| 17 / P369、P885–P923、P1004–P1038、P1183–P1189：所谓唯一 Session Authority/Cookie Vault/session_handle | ADAPT 为现有 SYSTEM owner 内的统一调用合同；P016 明令禁止新建平行 Session Authority。当前 browser_runtime_api.py:1–60、ai_browser_api.py、browser_surface_api.py 及两份 Collector BrowserSession 仍是多个 seam，未证明同一生产路径。 | B0/B1/B2 按 source owner 裁定，ROUND 04/06；不建新数据库、平台账户或第二运行时，session_handle 只是待验证实现建议；主线在登录源时是。 |
| 18 / P927–P1000、P1181–P1193：复用而非从零重造，后端“大半完成” | ADOPT 复用原则，REJECT 完成比例。已有 API、测试和后端 seam 均属局部 IMPLEMENTED SOURCE；REAL USER WORK E2E 与 AUTHENTICATED RUNTIME 未证。 | 当前任务已覆盖；Owner Index:87–125；主控按 B0–B5 分发，所有依赖原轮次；主线不因此改方向。 |
| 19 / P1042–P1054：按 ROUND 04/06/08/14/15 承接，不新建 16 轮 | ADOPT 导航但补 ROUND 03 的身份/关系、ROUND 05 运行恢复及 ROUND 09–13 的业务消费。Owner Index:12–32；目前 R04/R06 REWORK、R08 非 PASS、R14 局部、R15 NO。 | 当前任务已覆盖；“序境12”在现有队列插入 Batches；不让后轮实现冒充前轮验收；主线是。 |
| 20 / P1058–P1080：文中称 dirty 接口分叉、139/139 与 69 PASS/12 FAIL | ADAPT 保护工作原则，REJECT 旧数字为当前证据。最新共享树仍有大量候选，且 1b9ffa33 新增 X 相关采集代码、ac27acf5 更新公开基线计划版本；两组测试本次未运行。 | B0 是必要安全检查点，ROUND 04/06；精确比较新 main、index、本地候选及 owner，不 reset/clean/bulk-stage；主线在重叠路径时是。 |
| 21 / P637–P684、P947–P952、P1112–P1155：SYS-06 unavailable/状态面板，建议真实浏览器 UI | 静态缺口确认。Flutter 路由仍 unavailable，screen 只取 KPI/state。SYS-06.md:1–16,135–206 当前设计仅探索受控单页预览，允许动作只有 navigate/reload/frame；Back/Forward 与坐标输入尚未声明。 | 后续 ROUND 14；B3 先让 UI 线程提交完整可审核的 DESIGN_READY 方案，B4 再绑定支持的动作；不能删 unavailable 标志冒充完成；主线否。 |
| 22 / P970–P988：用文本表格声称 CDP/Profile/Frame/Permission/Collector/Evidence 等“都已有” | ADOPT 为导航清单，REJECT 为交付证据；逐项源码核验见 #2、#9、#12、#17，运行/业务 E2E 全未由该表证明。 | 仅登记、无新 Batch；原 Round 04/06/14/15；主线不变。 |
| 23 / 全文遗漏：未覆盖主控已明确的全球数据与三类制作任务 | ADAPT 保留原约束。Global Contract:27–110；Owner Index:105–106,216–219。补充文档只涉及 Browser/Session，不得替代 14 国家组、两域各至少 50 的版本化基线/自动维护、Global/Focus/clear、场内品牌与品牌市场、媒体社媒消费者 intelligence、字段映射、诚实缺失、时间/历史序列；视频、audio-first podcast、SH-01 通用制作继续分立。 | 当前任务已覆盖于“序境12”、国家数据线程、“序境 Content & Creation 视频闭环”和 UI 线程；无重派 Batch；ROUND 03/06/07/09–15；主线是。 |

## 最短执行队列与精确接收边界

- B0（立即可做的只读核对，接收“序境12”）：在下个安全检查点 fresh fetch，列出最新 main/index/dirty 精确路径；只核 browser_runtime_api.py、ai_browser_api.py、browser_surface_api.py、lumenis/system/browser/runtime/、lumenis/system/collector/runtime/session/browser_session.py、lumenis/system/collector/runtime/browser_session.py、xhs_cookie_bridge.py、xhs_p0_orchestrator.py、scripts/start_resident_browsers.py、lumenis/system/security/permission.py 及受影响测试/调用者。输出“main 已有、本地唯一候选、旧接口覆盖、冲突/未知”，保护所有在途工作；尤其不要抢主控刚提交的 X 与国家数据线程所有路径。验收产物是精确 source/caller/contract/diff 清单，不是代码、会话探测或 PASS。
- B1（ROUND 04，依赖 B0 和现有身份/Evidence owner，接收“序境12”调度一张独立 Task Card）：现有 lumenis/system/security/permission.py、lumenis/system/browser/runtime/contract.py、ai_browser_api.py、browser_surface_api.py 与对应 tests 为允许审查范围；证明服务端 Actor、设备/本地执行端、平台身份、来源、字段/动作、CTH Subject/BMP BrandFocus scope、有效期、暂停和撤销的授权决策及在途 fail-closed。禁止从 UI/Focus/CDP/文件存在反推 grant；只读 grant 不通过发布/点赞等写 Effect Fence。若当前产品 Actor 入口未闭合，明确 BLOCKED 并继续独立公开源工作。
- B2（ROUND 06，依赖 B1 合同和 ROUND 03 精确实体/市场关系，接收“序境12”；严格与当前 X/国家 Batch 隔离）：在既有 SYSTEM Browser/Collector owner 中绑定唯一可验证的 session 调用链，涉及 lumenis/system/browser/runtime/、lumenis/system/collector/runtime/、xhs_cookie_bridge.py、xhs_p0_orchestrator.py、lumenis/system/collector/adapters/public_source.py、lumenis/system/collector/adapters/secondary_collection.py 和其精确 caller/tests；不照搬两份 BrowserSession，也不新建 Session owner。验收为获准身份→限定平台字段→真实 Raw/Evidence/Canonical→准确 CTH/BMP；重启、过期、暂停、撤销、离线、错误账号均如实拒绝/恢复，历史、原生字段和真正的零/缺失区分。CN 个人 XHS 始终不得用；无 HK/international 获准会话则该平台 LIVE_NOT_VERIFIED/BLOCKED。
- B3（现在可并行的设计产物，建议主控交“序境 UI/UX 独立设计方案”）：以 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md、contracts/experience/screen-specifications/SYS-06.md 和 SYS-06 viewmodel/actions 合同作唯一输入，交一份完整的 SYS-06 Web/Desktop/Mobile 任务流、授权/离线/过期/返回与 320px/200% 无障碍方案，供 Sol/Product Owner 审核并争取 DESIGN_READY。明确“受控来源阅读”与“个人浏览器”边界；read-only PNG 是带时间的预览，不能叫完整可点击网页，也不能伪称已存 Canonical Evidence。Back/Forward、tabs、坐标操作只在真实 API 宣告且授权/验收后展示。此为设计，不改产品代码。
- B4（ROUND 14 实现，依赖 B1/B2 和 B3 的 DESIGN_READY，接收“序境12”排程）：仅绑定已验证的 ai_browser_api.py 或被 canonical owner 选定的现有 Browser API、experience_runtime.py、experience_screens.py、app/lib/features/system/sys06/{sys06_repository.dart,sys06_view_model.dart,sys06_snapshot.dart,sys06_screen.dart}、app/lib/navigation/lumenis_workspace_routes.dart 与相应 tests/contracts。验收从真实 CTH/BMP 工作进入允许的来源页，Frame 的 session/target/revision/capture time 匹配，A→B 时旧帧晚到不显示，401/403/409/202/503/离线可恢复，Return 恢复原任务和焦点；各目标设备按职责验真。只有通过后才取消 unavailable。
- B5（ROUND 15 发布整链，依赖 B1/B2/B4 和各轮真实用户 E2E）：同一候选、同一运行 Core/Flutter/启动入口，至少真实 CTH 与真实 BMP 样例走连接/采集/证据/结果/重启/再认证/撤销；同时做随机非参考实体与逐平台字段覆盖，不以两例替代 GLOBAL/ALL 或 14 国家基线；发布 accepted source 与 CURRENT 状态，远端验证。主控负责最终 PASS/REWORK/BLOCKED 决定。此研究未启动 B0–B5 实施。

## 影响决策的当期外部核验（2026-09-28 访问）

仅检索现有 Browser 选项的可行性，未提出新依赖或新产品。仓库 requirements.txt:29 为 playwright>=1.30.0；本机查询到 Python Playwright 1.62.0。下列官方文档是技术约束，不是 LUMENIS Production Truth。

1. Google Chrome 官方 2025-03-17 公告：https://developer.chrome.com/blog/remote-debugging-port 。Chrome 136 起，remote-debugging-port/pipe 不再用于默认用户数据目录；需要非标准 user-data-dir。该页许可 CC BY 4.0、代码示例 Apache 2.0。决定 ADAPT：系统默认浏览器可用于识别受支持引擎，但用户许可不自动让序境控制其日常个人 Profile；优先受控独立目录，禁止绕过 Chrome 限制。
2. Playwright Python BrowserType 官方文档：https://playwright.dev/python/docs/api/class-browsertype 。connect_over_cdp 仅 Chromium，保真度低于 Playwright protocol；launch_persistent_context 使用独占 user_data_dir，明确不支持自动化默认 Chrome 用户 Profile。决定 ADAPT：针对当前 1.62.0 与实际 Chrome/Edge/Chromium 各引擎验证连接能力、存储和失败路径，只向用户显示实证通过的选项；不能把端口在线等同正确平台身份。
3. Playwright Python Authentication 官方文档：https://playwright.dev/python/docs/auth 。Storage State 可能包含足以冒用账号的敏感 Cookie/headers，不应提交仓库；sessionStorage 默认不由 storage_state API 持久化。决定 ADAPT：本地资料隔离、保密和重新认证机制必须按实际平台测试，不能保证“登录一次永久保持”，也不能把 Cookie 文件视为完整会话。
4. 现用 Playwright Python 项目官方仓库 pyproject：https://github.com/microsoft/playwright-python/blob/main/pyproject.toml ，许可证 Apache-2.0，仓库仍有近期更新；本次只复用已声明依赖，不新增供应商或许可义务。Edge 的具体默认资料目录/CDP 行为与移动端可执行性仍需目标环境证据，不能从 Chrome 文档自动外推。

## 冲突与未决事实

- 原文 P016 禁止新建平行 Session Authority，P369/P885–P923 又建议“唯一 Session Authority”。适配为既有 SYSTEM Browser/Collector/Permission owner 内的一个经过调用链验证的合同；是否需要内部统一接口由 B0 证据决定，绝不新增 Owner 或 DB。
- DOCX 的完整 browser shell、Back/Forward、tab、可交互 viewport 与 SYS-06 当前状态不一致。当前 SYS-06.md:5,10 是 DESIGN_EXPLORATION/approval PENDING；:135–206 限定初始单页只读预览，allowed_actions 只列 navigate/reload/frame，Back/Forward/坐标输入尚未声明。文档是新需求材料，不能直接替代 sole Experience Constitution 或 DESIGN_READY 审核；B3 应交具体可审核的差异方案。
- Source Owner Index:40 写明媒体平台继续使用现有 Cookie/session/browser 链，且不增加强制平台登录步骤；DOCX P010–P012 要求“连接平台/用户正常登录”。可相容的解释是：产品全局仍可先使用公开能力，只有获准且确需登录的平台字段才提供自愿连接/恢复；不新增 LUMENIS 账号墙。若主控判断必须改强制入口，应交 Product Owner 裁决，不能靠实现者自行改合同。
- 当前 SYS-06 UI 的 capability report 与 AI Browser actor-owned frame API 是不同 seam；选择哪条 API 作为产品受控阅读路径仍需 canonical Browser Owner 和 Permission Owner 验证。experience_screens.py:1993–2027 的 account/port rows 与 browser_surface_api.py:19–55 的过滤范围不完全等价，存在需审查的 API 投影风险；本研究没有发起 HTTP 调用，故不宣称已泄漏。
- 产品账户密码设计仍后置，且不得用账户墙阻断前期使用；与此同时 Browser API 的真实 server Actor/scope 与读取 Evidence 的权限必须成立。现有 test Actor/Basic transport 证据不能替代真实用户身份和授权。ROUND 04 的 Actor 入口与平台 grant 绑定是待证事实。
- RedNote HK/international 会话当前是否有效、某字段是否需登录、平台访问限制、设备在线、重启后 Session Health、撤销后在途任务反应均未实时测试。旧 SESSION_EXPIRED 不作当前诊断；任何测试都不能接触 CN 个人 XHS 账号/Cookie/Profile。无获准环境则单个平台标 LIVE_NOT_VERIFIED/BLOCKED，同时继续其他安全的公开来源和国家基线工作。
- 原文没有规定 14 国家组×两域各至少 50 的版本化 Global baseline、增添主体后持续扩展、Source/Raw/Evidence/Canonical 与 CTH 场内品牌和 BMP 品牌经营市场关系、媒体/社媒/消费者 intelligence、平台原生字段/跨平台映射、出版/事件/采集/派生时间与历史序列。它们仍由现有 Global/Owner/各 Round 任务继承，不因本补充文件收窄。合法公开事实的已批准内部研究采集不被未决商业复用判断自动拦截；具体平台访问、身份与 Permission/Evidence 仍需遵守。

## 本次交付、限度及主控反馈

已完成逐段提取、23 项去重映射、当前 owner/source/API/ViewModel/screen 静态核验、两次新鲜远端核验及 1b9ffa33、ac27acf5 的相关路径增量跟踪；完整佐证见同目录 doc-extraction.md、feature-inventory.md、truth-owners.md、browser-source.md。本报告与附属文件都在独立 Temp，不改变 DOCX 原文、产品/治理文件或服务。源码/测试静态读取不构成运行成功。本研究不提交、不推送、不派发/启动实现；由“序境12”按精确冲突路径和安全入口分发，UI 线程仅接 B3 设计，国家与 Content & Creation 线程保留现有目标。


### Main 增量复核说明（2026-09-28）

4ef4a038→1b9ffa33 修改了 Collector secondary_collection、X adapter 与 resident browser 启动脚本，并新增 X 只读 worker 测试；其中 X worker 为显式启用、loopback 的独立只读路径。仅核源码 diff，未启动/读取 Profile。1b9ffa33→ac27acf5 在本研究范围只修改公开 prelaunch baseline 的逐来源 plan_version 与格式校验（lumenis/system/collector/adapters/scheduling/prelaunch_baseline.py:335–360）及相应测试/状态；Browser/Session API、Permission、SYS-06、screen spec 与 Owner Index 未变。主控仍在连续集成，分派前需再次确认 HEAD。


## 四类归档速览（条目编号与上表一致）

- 当前任务已覆盖：#1、#5、#6、#7、#18、#19、#23。含已在主控与国家数据线程推进的公开/授权来源、真实数据链、Global/ALL、双域实体和诚实状态；“已覆盖”指已纳入工作和验收，不表示实现完成或 Round PASS。
- 当前可并行补入：#2、#3、#4、#11、#12、#13、#14、#17、#20。先做 B0 只读 owner/dirty reconciliation 与 B3 独立 SYS-06 设计；B1/B2 要在确立边界并避开正在写入的 Collector/国家路径后作为有界 Batch 派发。
- 后续既有 Round：#8、#9、#10、#16、#21。SYS-06 Frame/状态/返回实现等在 R14 等待 DESIGN_READY 与真实后端 Actor/Session，R15 综合真实用户验收。
- 仅登记技术债或不采纳：#15、#22。第三方 Cookie converter 不进产品；手工导入仅在日后有安全、Permission、Experience 决策时考虑；旧“已有能力表”只作导航，不作交付证据。

## 停止钩子补充核验（同一研究任务）

2026-09-28 在当前 HEAD=origin/main=ac27acf543b9c9f86eb9ede5e2d9b429f58782cb 上运行独立研究产物/源码锚点校验，退出码 0：原文提取的 BODY.P001–P1193 连续完整；去重清单与本报告分别且仅有 #1–#23；两份产物保留提取时原件 SHA；当前提交的 SYS-06 unavailable、DESIGN_EXPLORATION/PENDING、只宣告 navigate/reload/frame、公开源拒 Authorization/Cookie、AI Browser frame target/revision/no-store 以及 Playwright manifest 均与报告引用一致。验证脚本与输出在同目录 verify_research.py。本校验只证明研究映射在该源快照上的静态锚点，不证明产品测试或运行 E2E。

另一次尝试重算 WPS 原件当前 SHA 时，Get-FileHash 退出码 1，原因是原件被另一进程独占占用；因此只保留首次成功提取时记录的 SHA，不把这次失败称为 PASS。未关闭或干预持有原件的进程。产品测试、登录态、真实采集、运行 Core 和真实用户 E2E 仍为 NOT RUN / LIVE_NOT_VERIFIED；本研究没有实现变更，不据此宣布任何 Round 或产品能力完成。

### 后续主线变动（停止钩子复核）

在产物校验期间 main 又推进到 4849cfe0f6a10d2a49b06dc0366fa09507ebeead，提交范围是 Web emoji 字体回退与 AI-01 画布简化；相对 ac27acf5，Browser/Session/Permission/SYS-06/API/路由及报告核验的公开源路径无改动。Experience Constitution 的增量针对字体和 AI-01，并未改变 SYS-06 的 DESIGN_EXPLORATION 状态。该新提交的测试由主控自行记录，本研究未重跑产品测试。以下脚本最后一次成功退出的 SHA 才是本报告静态源锚点的最终快照。

补充的当前快照自动校验：独立 Temp 测试 test_research_snapshot.py 在 4849cfe0 的 HEAD=origin/main 上运行 6 个只读测试，6/6 OK、退出码 0、0.628 秒。覆盖主线祖先关系、DOCX 段落连续性、23 条双清单一致性、SYS-06 当前 gate、公开来源拒凭据和 Frame/manifest 源锚点。它不执行任何产品代码路径，不能替代 Browser/Collector/Permission 的单元、集成、运行或真实用户 E2E 测试。


## Root adoption and dispatch

Research received at main 4849cfe0. This is a historical research/navigation asset, not an execution router or proof of product completion. All 23 items were retained. B0 is assigned to one bounded Luna for source/session seam mapping; B3 is assigned to the existing UI/UX thread for an approval-ready SYS-06 design candidate. B1/B2 implementation waits for the exact seam and collision decision; B4/B5 retain their existing design/runtime/E2E gates. Current data/platform collection, 14 country groups, CTH/BMP identities and the three creation workflows keep their prior scope. Product password/account UX stays deferred; server Permission and platform identity boundaries remain. No round accepted by this research.
