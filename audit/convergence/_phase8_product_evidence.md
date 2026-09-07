# Phase 8 产品闭环证据审计报告

> 审计时间：2026-09-07
> 审计模式：只读验证（无 pytest、无文件修改）
> 运行环境：Flask 端口 8201，Basic Auth (Zachary)
> 仓库：D:\Taikoo-monitor-new

---

## 1. 阶段4 采集证据链表

| # | 验证项 | 状态 | 证据文件:行号 | 结论 |
|---|--------|------|----------------|------|
| 1 | dual_account_rotation 双账号轮换 | **VERIFIED** | `dual_account_rotation.py:225` (def select_account_for_collection)<br>`collector_automation.py:7` (import)<br>`collector_automation.py:1051` (真实调用: `account, reason = select_account_for_collection(kos_mode=kos_mode)`)<br>`kos_routes.py:45` (辅助调用) | 模块已接入采集调度层，collector_automation 主循环真实调用 select_account_for_collection()，非仅模块就绪。 |
| 2 | XHSAppTopicAdapter 话题APP采集 | **PARTIAL** | `platform_adapters/xhs_app_topic.py:36` (class 定义)<br>`platform_adapters/xhs_app_topic.py:247` (register_adapter)<br>`topic_campaign.py:16` (import)<br>`topic_campaign.py:1259-1262` (条件判断 + 实例化调用)<br>`app.py:1258` (topic_campaign.register_topic_campaign 注册) | Adapter 已注册并被 topic_campaign 子系统消费，但**主采集链路 collector.py search_xiaohongshu 走 CDP 通道，不经过此 Adapter**。话题采集入口独立于主采集，需单独触发验证。参考 `tests/phase4_collection_verification_evidence.md:98`。 |
| 3 | collect-resume 断点续采 | **VERIFIED** | `collection_api.py:190` (@bp.route('/api/xhs/collect-resume', POST))<br>`collection_api.py:191` (def api_xhs_collect_resume)<br>`collection_api.py:193` (调用 `xhs_cookie_bridge.resume_user_paused()`)<br>`collector_guard/checkpoint.py:2` (按平台+关键词记录断点续采状态) | API 端点存在且调用底层 resume 函数；collector_guard/checkpoint.py 提供按平台+关键词的断点状态记录。为用户主动触发型（POST API），非调度器自动续采。 |
| 4 | 内部浏览器默认strict可切外部 | **VERIFIED** | `collector_browser_mode.py:22` (DEFAULT_MODE = MODE_INTERNAL_CDP)<br>`collector_browser_mode.py:32` (env COLLECTOR_BROWSER_MODE 覆盖)<br>`collector.py:368-371` (search_xiaohongshu 内 `_cbm.get_browser_mode()` 读取)<br>`collector.py:374` (external_standalone 分支)<br>`templates/system/collector.html:112-129` (radio UI: internal_cdp checked 默认, external_standalone 可选)<br>`templates/system/collector.html:609,631` (fetch /api/collector/browser-mode) | 默认 internal_cdp（内部AI浏览器），支持 env 覆盖和前端 radio 切换；collector.py 主函数真实读取模式并分支执行。三层（默认值→代码读取→UI切换）闭环。 |
| 5 | auth_recovery 内弹 | **VERIFIED** | `templates/base.html:393` (auth-recovery-modal 内联 div)<br>`templates/base.html:761` (JS fetch /api/auth-recovery/summary)<br>`v4_upgrade/adapters/auth_recovery.py:362` (def _bridge_to_recovery_center)<br>`v4_upgrade/adapters/auth_recovery.py:403,413` (request_recovery 内调用 bridge)<br>`auth_recovery_api.py:9` (Blueprint url_prefix=/api/auth-recovery)<br>`auth_recovery_api.py:13-14` (@route('/summary') def get_summary)<br>**curl 实测**: `GET /api/auth-recovery/summary` → **HTTP 200** | 全局 Modal 内联于 base.html，前端轮询 summary 端点；adapter 层 bridge_to_recovery_center 确保任务写入 center 对前端可见；端点实测 200。已有真实证据：collection_logs id=526 → auth_recovery_tasks id=6（phase4_collection_verification_evidence.md）。 |
| 6 | 账号保活/限速熔断 | **PARTIAL** | `account_keepalive/manager.py:69` (AccountKeepAlive 类定义，模块存在)<br>`app.py:4476-4510` (内联小红书双平台保活定时检查，每30分钟)<br>`app.py:4542` (`xhs_cookie_bridge.check_rate_limit('auto')` 限速检查)<br>`app.py:3137` (采集守护系统状态端点：限速器/熔断/指标)<br>`collector_guard/__init__.py:4` (六态状态机/动态限速退避/断点续采)<br>**缺失**: `account_keepalive` 模块**仅被 tests/ 导入**，未在 app.py/collector 主链路 import | 限速（xhs_cookie_bridge.check_rate_limit）和熔断（collector_guard）在采集链路中已实现；app.py 有内联保活逻辑。但**独立 account_keepalive 模块未接入主链路**（仅测试覆盖），保活能力以内联形式存在而非模块化调用。 |

---

## 2. 阶段5 产品闭环表

| # | 验证项 | 路由 | HTTP 状态码 | 证据文件:行号 | 结论 |
|---|--------|------|-------------|----------------|------|
| 1 | ZBMP brand.html → /api/brands/logos | `GET /lumenis/zbmp/brand`<br>`GET /api/brands/logos?domain=zbmp` | **200**<br>**200** | `lumenis_frontend.py:365-368` (路由→render_template zbmp/brand.html)<br>`templates/zbmp/brand.html:204` (loadLogos 函数定义)<br>`templates/zbmp/brand.html:206` (fetch '/api/brands/logos?domain=zbmp')<br>`app.py:3773` (@app.route('/api/brands/logos')) | 页面 200，API 200。返回 **194 品牌，182 有 logo，覆盖率 93.8%**。loadLogos() 函数存在且真实调用 API。 |
| 2 | CTH brands.html | `GET /lumenis/cth/brands` | **200** | `lumenis_frontend.py:455-458` (路由→render_template cth/brands.html)<br>`templates/cth/brands.html:86` (fetch '/api/brands/logos' + X-Domain-Id: cth) | 页面 200。CTH brands.html 同样接入 /api/brands/logos（通过 X-Domain-Id header 区分域）。 |
| 3 | podcast.html 10维打分 8 API | 见下方第3节详表 | 7×200 + 1×000 | `templates/zbmp/podcast.html:140-368` (8个API面板全部标注"✓ 已对接")<br>`podcast_routes.py:22` (Blueprint url_prefix=/api/podcast)<br>`content_generation.py:975` (podcast-research), `:959` (topic-snapshot) | **7/8 API 可用**。story-nodes 端点存在但调用超时（HTTP 000）。详见第3节。 |
| 4 | Settings 标准化 | `GET /system/settings`<br>`GET /api/data-center/platforms` | **200**<br>**200** | `app.py:5953` (@app.route('/system/settings'))<br>`templates/system/settings.html:1079` (平台开关分组注释)<br>`templates/system/settings.html:1085` (引用 /api/data-center/platforms)<br>`templates/system/settings.html:1106` (系统模块快捷入口分组)<br>`templates/system/settings.html:1265` (语言切换注释)<br>`templates/system/settings.html:1321` (fetch /api/data-center/platforms)<br>`data_center_api.py:78-79` (@route /platforms) | 页面 200。三大分组齐全：平台开关（/api/data-center/platforms）、系统模块入口、语言切换。API 返回 **1 个平台（xiaohongshu，ui_visible=1）**。 |
| 5 | 9级 z-index | N/A (CSS) | N/A | `static/css/adaptive-layout.css:57-65` (9个 --z- 变量定义)<br>`templates/base.html:432` (auth-recovery-modal 使用 var(--z-auth-recovery))<br>`templates/cth/realtime.html:618` (唯一魔法数字: z-index:9999) | **9级变量全部定义**：--z-base(0) / --z-sticky(10) / --z-dropdown(100) / --z-embedded-panel(150) / --z-drawer(200) / --z-modal(500) / --z-dialog(800) / --z-toast(1000) / --z-auth-recovery(10000)。仅 1 处魔法数字残留（cth/realtime.html:618 z-index:9999）。 |
| 6 | Motion COVERED/PARTIAL | N/A (JS/CSS) | N/A | `templates/base.html:206` (adaptive-motion.js)<br>`templates/base.html:217` (carousel.js)<br>`templates/base.html:218` (motion-bridge.js)<br>`static/js/motion-bridge.js:33` (querySelectorAll('[data-kpi]')) | 三个 JS 全部在 base.html 加载。motion-bridge 通过 [data-kpi] 选择器覆盖。详见第4节覆盖清单。 |

---

## 3. Podcast 8 API 详细状态表

> 页面路由：`/lumenis/zbmp/podcast` → `templates/zbmp/podcast.html`
> Blueprint：`podcast_routes.py:22` → url_prefix=`/api/podcast`
> 测试时间：2026-09-07，带 Basic Auth

| # | API | 方法 | HTTP 状态码 | 响应摘要 | 路由定义 | 结论 |
|---|-----|------|-------------|----------|----------|------|
| 1 | /api/content/podcast-research | POST | **200** | ok=true（AI辅助选题研究） | `content_generation.py:975` | VERIFIED |
| 2 | /api/content/topic-snapshot | GET | **200** | ok=true（话题快照） | `content_generation.py:959` | VERIFIED |
| 3 | /api/podcast/topic-score | POST | **200** | ok=true, total_score=58.5（10维打分） | `podcast_routes.py:114` | VERIFIED |
| 4 | /api/podcast/story-nodes | POST | **000** | 连接超时/重置（端点存在但调用挂起） | `podcast_routes.py:143` | **FAIL** — 端点代码存在，输入格式为 segments[] 数组，但实际调用导致 HTTP 000（worker 未崩溃，后续请求正常），疑似 import story_nodes 路径问题或运行时挂起 |
| 5 | /api/podcast/breakout | POST | **200** | ok=true, state=normal/breakout/viral | `podcast_routes.py:191` | VERIFIED |
| 6 | /api/podcast/content-yield | POST | **200** | ok=true（9种衍生资产规划） | `podcast_routes.py:207` | VERIFIED |
| 7 | /api/podcast/runtime/validate | POST | **200** | ok=true, valid=true, segment_count=2（需 start_ms 字段；错误格式返回500） | `podcast_routes.py:167` | VERIFIED — 正确输入（segments[].start_ms）返回200；缺少 segment_id/start_ms 返回500（符合预期的参数校验） |
| 8 | /api/podcast/entities | GET | **200** | ok=true, returned=0（实体表为空） | `podcast_routes.py:61` | VERIFIED — 端点正常，当前无实体数据 |

**Podcast API 汇总：7/8 VERIFIED，1/8 FAIL（story-nodes 超时）**

---

## 4. Motion 覆盖清单

### 4.1 JS 加载状态（base.html）

| JS 文件 | 加载行号 | 状态 |
|---------|----------|------|
| adaptive-motion.js | `base.html:206` | LOADED |
| carousel.js | `base.html:217` | LOADED |
| motion-bridge.js | `base.html:218` | LOADED |

motion-bridge.js 核心机制：`querySelectorAll('[data-kpi]')`（行33），对带 data-kpi 属性的元素做 count-up 动画和 MutationObserver 变化监听。

### 4.2 COVERED 页面（含 data-kpi 属性，共14个）

| 页面模板 | 路径 |
|----------|------|
| ZBMP Overview | `templates/zbmp/overview.html` |
| ZBMP Content | `templates/zbmp/content.html` |
| CTH Overview | `templates/cth/overview.html` |
| CTH Realtime | `templates/cth/realtime.html` |
| CTH Risk | `templates/cth/risk.html` |
| CTH Events | `templates/cth/events.html` |
| CTH Reports | `templates/cth/reports.html` |
| CTH Brands | `templates/cth/brands.html` |
| System AI | `templates/system/ai.html` |
| System Runtime | `templates/system/runtime.html` |
| System Database | `templates/system/database.html` |
| System Security | `templates/system/security.html` |
| System Collector | `templates/system/collector.html` |
| System Adaptive Demo | `templates/system/adaptive_demo.html` |

### 4.3 PARTIAL 页面（使用不同 class 名，未覆盖 data-kpi，共4个）

| 页面模板 | 路径 | 未覆盖原因 |
|----------|------|-----------|
| CTH Evidence | `templates/cth/evidence.html` | 使用 `xj-state` 系列 class（行27-46），无 data-kpi |
| CTH Industries | `templates/cth/industries.html` | 使用 `xj-state` 系列 class（行27-46），无 data-kpi |
| CTH Launch | `templates/cth/launch.html` | 无 data-kpi / lm-card / kpi / metric class |
| ZBMP Launch | `templates/zbmp/launch.html` | 无 data-kpi / lm-card / kpi / metric class |

### 4.4 MISSING / 未评估页面

| 页面模板 | 路径 | 说明 |
|----------|------|------|
| ZBMP Podcast | `templates/zbmp/podcast.html` | 无 data-kpi（以 API 面板为主，非 KPI 数值展示页） |
| ZBMP KOS | `templates/zbmp/kos.html` | 未含 data-kpi |
| ZBMP Reports | `templates/zbmp/reports.html` | 未含 data-kpi |
| ZBMP Risk | `templates/zbmp/risk.html` | 未含 data-kpi |
| ZBMP Evaluation | `templates/zbmp/evaluation.html` | 未含 data-kpi |
| ZBMP Intelligence | `templates/zbmp/intelligence.html` | 未含 data-kpi |
| ZBMP Competition | `templates/zbmp/competition.html` | 未含 data-kpi |
| CTH Topics | `templates/cth/topics.html` | 未含 data-kpi |
| CTH Xiaohongshu | `templates/cth/xiaohongshu.html` | 未含 data-kpi |
| CTH KOS | `templates/cth/kos.html` | 未含 data-kpi |

**Motion 覆盖汇总：14 COVERED / 4 PARTIAL / 10+ MISSING（多为非KPI展示页）**

---

## 5. 结论

### 阶段4 采集证据链：**PARTIAL VERIFIED**

| 状态 | 数量 | 项 |
|------|------|-----|
| VERIFIED | 4 | dual_account_rotation、collect-resume、内部浏览器模式切换、auth_recovery内弹 |
| PARTIAL | 2 | XHSAppTopicAdapter（仅topic_campaign子系统，主链路未走）、账号保活/限速熔断（account_keepalive模块未接入主链路，内联保活+限速+熔断已存在） |

**关键发现：**
- 主采集链路（collector_automation → search_xiaohongshu）已接入双账号轮换、浏览器模式切换、auth_recovery、限速检查。
- XHSAppTopicAdapter 是话题采集子系统的独立通道，不经过主采集器，需在话题活动场景下单独验证。
- account_keepalive 独立模块存在但仅测试覆盖，生产保活以内联代码（app.py:4476-4510）实现。

### 阶段5 产品闭环：**PARTIAL VERIFIED**

| 状态 | 数量 | 项 |
|------|------|-----|
| VERIFIED | 5 | ZBMP brand/logos、CTH brands、Settings标准化、9级z-index、Motion JS加载 |
| PARTIAL | 1 | podcast 8 API（7/8可用，story-nodes超时） |

**关键发现：**
- 品牌Logo体系双域（ZBMP/CTH）均已接入 /api/brands/logos，194品牌覆盖率93.8%。
- Settings页面三大分组（平台开关/系统模块/语言切换）齐全，平台API正常。
- 9级z-index变量完整定义，仅1处魔法数字残留。
- Podcast 7/8 API正常，**story-nodes 端点调用超时（HTTP 000）是唯一阻塞项**，需排查 `import story_nodes` 路径或运行时挂起问题。
- Motion 覆盖14个核心KPI页面，4个PARTIAL页面（evidence/industries/launch）使用非标准class名。

### 总体判定

- **阶段4：PARTIAL VERIFIED**（4/6 完全验证，2/6 部分验证，无完全缺失项）
- **阶段5：PARTIAL VERIFIED**（5/6 完全验证，1/6 部分验证，核心阻塞为 podcast story-nodes 超时）

**建议优先修复：**
1. `podcast_routes.py:143` story-nodes 端点 HTTP 000 问题（排查 `import story_nodes` 路径）
2. `templates/cth/realtime.html:618` z-index:9999 魔法数字替换为 --z-modal 或 --z-dialog
3. account_keepalive 模块接入主链路（或明确标注为 Legacy/Optional）

---

*本报告为只读审计产物，未运行 pytest，未修改任何源码文件。*
