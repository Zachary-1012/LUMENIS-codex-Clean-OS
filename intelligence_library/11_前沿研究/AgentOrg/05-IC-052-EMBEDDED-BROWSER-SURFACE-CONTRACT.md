# IC-052 · 平台内置浏览器能力层 Contract（Browser Surface）

> 状态：CONTRACT-SPECIFIED（2026-09-04）；生产已 IMPLEMENTED + TESTED（见 ZBC Evidence）
> 上游：IC-051 AI Browser Agent Frontier（研究）→ 本 Contract（生产落地规格）
> 边界约束（用户 2026-09-04 明确）：
> 1. AI 浏览器必须**平台系统内置**，所有浏览在平台内完成，**不跳转系统外部浏览器/站外**；保留用户选择项。
> 2. 对标 **Safari / Chrome 的原生浏览能力与架构**。
> 3. **开源借鉴仅限 Safari / Chrome 原生能力**；不引入任何第三方 Agent 框架/运行时
>    （Playwright 仅保留既有 adapter，browser-use 等不进生产）；底层用 Chrome 原生 CDP。
> 4. AI 独立 App 架构降级（不着急），本阶段只做平台内置浏览器。

---

## 一、Product Intent / User Goal

- 用户在序境平台内即可完成「打开网页 → 多标签浏览 → 读取页面内容/结构化 DOM → 平台内搜索 →
  收藏/历史回溯」的完整闭环，全程不离开平台、不拉起外部浏览器。
- 对标 Safari/Chrome 的**原生浏览器基线能力**（不是 Agent 自动化框架）：
  Tab 管理、地址栏导航、前进/后退/刷新（既有）、阅读器式内容提取、书签、历史、多引擎搜索。
- 为上层 AI 增强（Vision+DOM hybrid、Agent 操作）提供**确定性、可审计、受策略门控**的底层表面。

## 二、能力清单（Canonical Capability）

| Capability ID | 对标 | 实现 | 说明 |
|---|---|---|---|
| BR-TAB-LIST | Chrome tabs 列表 | `list_tabs` / CDP `GET /json/list` | 列出驻场浏览器全部标签页（id/title/url/active/ws） |
| BR-TAB-NEW | 新建标签页 | `new_tab` / CDP `/json/new`（PUT 优先，GET 回退） | 平台内新建并导航，先过导航门 |
| BR-TAB-CLOSE | 关闭标签页 | `close_tab` / CDP `/json/close/<id>` | |
| BR-TAB-ACTIVATE | 切换标签页 | `activate_tab` / CDP `/json/activate/<id>` | |
| BR-TAB-NAVIGATE | 地址栏导航 | `navigate_tab` / 指定 target WS + `Page.navigate` | 附着任意标签页，不再固定 pages[0] |
| BR-EXTRACT-META | Safari Reader 元数据 | 固定只读 JS | title/description/canonical/og/h1/链接数/图片数 |
| BR-EXTRACT-TEXT | Safari Reader 正文 | 固定只读 JS | article/main 优先，回退 body.innerText，截断保护 |
| BR-EXTRACT-DOM | Chrome 可访问性树（轻量） | 固定只读 JS | a/button/input/[role] 等可交互元素 + bbox/可见性 |
| BR-SEARCH | 地址栏多引擎搜索 | `browser_discovery` | Bing + 百度 + DuckDuckGo，统一结构、去重、可指定引擎 |
| BR-BOOKMARK | 浏览器书签 | 本地 JSON（data/private） | 增/列/删，URL 去重，过导航门 |
| BR-HISTORY | 浏览器历史 | 本地 JSON，环形上限 1000 | 记录/列表/清空，仅 http/https |
| BR-POLICY | 站点设置/隐私 | `evaluate_navigation` | strict / allowlist / open 三模式 + SSRF + 危险协议 |

## 三、导航策略门（Policy，安全核心）

三模式（环境变量 `INTERNAL_BROWSER_NAV_MODE` 或 `data/private/browser_allowlist.json`，默认 allowlist）：

| 模式 | 放行范围 | 用途 |
|---|---|---|
| strict | 仅平台采集域（复用 internal_browser 白名单，采集链路零变化） | 最严格 |
| allowlist（默认） | 平台域 + 用户显式追加可信域（`INTERNAL_BROWSER_EXTRA_DOMAINS` 逗号分隔 / 配置文件） | 安全与通用平衡 |
| open | 任意**公网** http/https | 用户明确选择后通用浏览 |

**任何模式都强制（不可被模式关闭）**：
1. 危险/受限协议拒绝：`file/chrome/edge/about/data/javascript/view-source/blob/devtools/*-extension`。
2. SSRF 防护：回环（127/::1/localhost）、私网（10/8、172.16/12、192.168/16）、链路本地
   （169.254/16、fe80）、保留/多播/未指定地址一律拒绝（getaddrinfo 解析后逐 IP 判定）。
3. 仅 http/https；主机名必须可解析。

> 「不跳站外」由 CDP 在驻场 Chromium 内导航 + 平台 SSE 截图流/DOM 提取消费实现；
> 用户「保留选择项」= 三模式可切换 + 白名单可追加，默认安全（allowlist）。

## 四、API Contract（/api/browser-surface/*，Blueprint）

| Method | Path | 入参 | 输出要点 |
|---|---|---|---|
| GET | /capabilities | — | nav_mode/mode 列表/能力清单/驻场在线状态 |
| GET | /policy | url? | 当前策略 + 对该 url 的 evaluation |
| GET | /tabs | account?/port? | tabs[] |
| POST | /tab/new | url,mode?,background?,account?/port? | tab + gate |
| POST | /tab/close | target_id | closed |
| POST | /tab/activate | target_id | activated |
| POST | /tab/navigate | url,target_id?,mode?,wait_ms? | gate + target_id |
| GET/POST | /extract | kind=meta/text/dom/all,target_id?,max_chars? | 结构化内容 |
| GET/POST | /search | q,engines?,limit? | items[]（统一搜索结构） |
| GET/POST | /bookmarks | title?,url? | bookmarks[] |
| POST | /bookmark/remove | url | bookmarks[] |
| GET/POST | /history | title?,url?/limit? | history[] |
| POST | /history/clear | — | cleared |

统一响应 `{ok:bool,...}`；CDP 离线时能力查询返回 ok=True/online=False（优雅降级），
动作类返回 ok=False + 原因，不抛 500、不泄露内网细节。

## 五、Change Boundary（修改边界）

- **新增**：browser_surface.py、browser_surface_api.py、tests/test_browser_surface.py。
- **增强（向后兼容）**：browser_discovery.py（保留 search/discover 旧签名，新增 engines 可选参数字段 engine）。
- **仅一处接线**：app.py 在 internal_browser_stream 注册块后追加 browser_surface_api 注册（try 包裹，失败不拖垮启动）。
- **不改动**：internal_browser.py 采集身份链路、xhs_cookie_bridge 双账号体系、browser_runtime 四层、
  采集频率/熔断/HCG、任何 Production Truth 数据。
- 复用而非复制：端口解析、CDP 命令收发复用 internal_browser._port_for/_cdp。

## 六、安全与红线

- 提取 JS 全部为**内置固定只读表达式**，不接受调用方传入任意 JS（区别于 internal_browser.evaluate）。
- 不读写 Cookie/Token/密钥；不绕过验证码/限流/登录保护；高风险动作仍走 HCG。
- 不引入第三方 Agent 框架；开源借鉴范围严格限定 Safari/Chrome 原生能力。
- 搜索为独立普通浏览器预算，不调用 RedNote 采集器、不消耗其检索次数（沿用 browser_discovery 定位）。

## 七、验收 Gate 与 Evidence

- [x] 静态语法：app.py（utf-8-sig）/browser_surface.py/browser_surface_api.py/browser_discovery.py 全通过
- [x] 离线单测：tests/test_browser_surface.py **34 passed**（策略门/SSRF/解析器/书签历史/API）
- [x] 真实 CDP 端到端：9222 驻场在线，tabs 列出小红书页；meta 7ms（167 链接/65 图）；
      dom 提取 200 可交互元素；text 1750 字符正确截断
- [x] API 冒烟：test_api_smoke ALL_PASS，新蓝图注册成功，既有端点 200/401 不变
- [x] 全量回归：FAILED=10/ERROR=29 全部为既有类别（KOS sqlite/dev_exec_guard/idea_sit/lean_footprint），
      **浏览器相关零失败、零新增回归**
- [ ] 生产 UI 表面（内置浏览视图：标签栏 + 地址栏 + 截图流 + Reader/DOM 面板）→ 下一阶段（P2 UI）

## 八、下一阶段（不在本次范围）

1. P2 内置浏览 UI：左导航 + 中央工作区内嵌标签栏/地址栏，复用既有 SSE screencast，侧边 Reader/DOM 面板。
2. 页内查找（find-in-page）、下载管理（CDP Browser.setDownloadBehavior）。
3. Vision(glm_4_6v)+DOM hybrid 表面（受 AI Gate 治理，另立 Contract）。
4. 通用浏览独立驻场实例（可选，独立 profile/端口，与采集双账号物理隔离）。
