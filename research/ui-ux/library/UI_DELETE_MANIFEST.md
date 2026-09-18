# UI_DELETE_MANIFEST.md
# UI/UX HARD RESET · 双库删除清单
# 生成时间：2026-09-04

## 执行原则
- 只删纯 UI 实现（HTML/CSS/前端 JS/Renderer/Animation/Glass/Card/Theme/Responsive/UI Patch/Robot UI）
- 保留 Product Core / Business Logic / API / Data / Runtime / AI / Security / Tests / Research
- 设计思想文档（md）全部保留，不参与旧 UI Runtime

## DELETE

### ZBC (序境-Core 生产)

| path | type | reason | dependency | replacement |
|---|---|---|---|---|
| creative_workbench.html | html | 旧 UI 实现：创意工作台单页应用 | 无生产依赖 | 新 UI 统一重建 |
| v4_upgrade | directory | 旧版本 UI 实现：collect/console/settings/version_center 模板 + auth_global.js | 无生产依赖（v4 已废弃） | 新 UI 统一重建 |
| podcast/ui | directory | Podcast UI 实现：episode_workspace.html + podcast-table.css + model/view JS | podcast 业务逻辑保留在 podcast/ 其他模块 | 新 UI 统一重建 |

### OSAI (序境-Intelligence 研究)

| path | type | reason | dependency | replacement |
|---|---|---|---|---|
| app | directory | 纯 UI 实现：index.html + styles.css + app.js | 无核心依赖 | 新 UI 统一重建 |
| osai-ui | directory | 纯 UI 实现：10 个 HTML 页面 + 4 个 CSS + 5 个 JS | 无核心依赖 | 新 UI 统一重建 |
| components/Development-Command-Console/css | directory | UI 样式：components.css + tokens.css | 仅服务 DevConsole UI | 新 UI 统一重建 |
| components/Development-Command-Console/js | directory | 前端 JS：bridge/github-audit/search/task/theme（DOM/localStorage 操作） | 仅服务 DevConsole UI | 新 UI 统一重建 |
| components/Development-Command-Console/index.html | html | DevConsole UI 入口 | 仅服务 DevConsole UI | 新 UI 统一重建 |
| components/SICI-Core/css | directory | UI 样式：style.css | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/index.html | html | SICI UI 入口 | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/sw.js | service-worker | Service Worker（UI 缓存） | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/app.js | frontend-js | 前端交互层 + 纯前端认证 | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/runner.js | frontend-js | 前端代码运行器（new Function + console 捕获） | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/tester.js | frontend-js | 浏览器内轻量测试运行器 | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/storage.js | frontend-js | 前端 localStorage 封装 | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/deploy.js | frontend-js | 前端部署管理（GitHub Pages API 直接调用） | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/github.js | frontend-js | 前端 GitHub 集成（直接调用 REST API） | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/research-learning.js | frontend-js | 浏览器端 Research Learning Store（localStorage） | 仅服务 SICI UI | 新 UI 统一重建 |
| components/SICI-Core/js/three-repository-verifier.js | frontend-js | 前端三仓库验证 helper（client-side） | 仅服务 SICI UI | 新 UI 统一重建 |
| resources/html-templates | directory | 设计模板实现：80+ widget-code.html / single-page 模板 | 设计实现而非设计思想 | 设计思想保留在 md 文档中 |

## RETAIN（核心能力，不得删除）

### ZBC

| path | type | reason |
|---|---|---|
| inject_cookies.js | runtime-tool | 采集工具：Cookie 注入 |
| xhs_campaign_monitor.js | runtime-tool | 采集工具：小红书活动监控 |
| xhs_cookie_search.js | runtime-tool | 采集工具：Cookie 搜索 |
| xhs_search.js | runtime-tool | 采集工具：小红书搜索 |
| data/cdp_check.js | runtime-tool | 采集工具：CDP 检查 |
| data/rednote_detail.html | runtime-template | 采集 Runtime：rednote 详情页模板 |
| data/rednote_page.html | runtime-template | 采集 Runtime：rednote 页面模板 |
| data/reports/ | data-output | 数据输出：报告 HTML（Data/Report 产物） |
| data/backups/ | historical-evidence | 历史证据：备份 |
| docs/ | documentation | 文档/研究资产 |
| tests/ | tests | 测试 |
| static/ | empty-dir | 空目录（UI 已不存在，保留目录结构） |

### OSAI

| path | type | reason |
|---|---|---|
| components/Development-Command-Console/server/ | backend-logic | 后端核心逻辑：learning-store/evidence-bundle/shadow-learning 等 AI 能力 |
| components/Development-Command-Console/tests/ | tests | 测试 |
| components/SICI-Core/js/capability-registry.js | core-logic | 核心逻辑：能力注册表 |
| components/SICI-Core/js/effective-rules.js | core-logic | 核心逻辑：规则解析器 |
| components/SICI-Core/js/preflight.js | core-logic | 核心逻辑：运行时预检 |
| components/SICI-Core/tests/ | tests | 测试 |
| 00-GOVERNANCE/ | governance | 治理文档 |
| 03-RESEARCH/ | research | 研究资产 |
| docs/ | documentation | 文档/研究资产 |
| contracts/ | contracts | 契约文档 |
| *.md (design/UI research) | research-doc | 设计思想/研究文档（全部保留） |
