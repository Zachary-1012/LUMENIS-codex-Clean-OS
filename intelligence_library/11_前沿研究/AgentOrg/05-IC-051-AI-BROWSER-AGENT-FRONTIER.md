# IC-051 · AI 浏览器 / Browser Agent 前沿（研究侧）

> 状态：RESEARCH-DONE（2026-09-04，研究侧资产；待 Contract 后评估生产落点）
> 依据：2026 年 Browser Agent / Computer Use 前沿研究（Browser Use、BrowserOS、微软 Webwright、Index、Steel 等）
> 边界：不引入第三方框架，不绕过平台安全措施；取架构思想完善序境 AI 浏览器
> 反哺对象：序境 AI 浏览器（browser_runtime/ + internal_browser + cdp_helper）

---

## 一、证据基线（核心发现）

| 项目 | 类型 | 核心能力 | 关键数据 |
|---|---|---|---|
| **Browser Use** | 开源 Python 框架 | LLM 结构化访问无头浏览器，vision+DOM hybrid（文本重+canvas 重都能处理），selector 失败时 re-plan 恢复循环 | 40-step workflows 87% 无人值守完成；WebVoyager 89.1%（586 任务） |
| **BrowserOS** | 开源 Chromium fork | AI agent 内置每个新标签页，20+ 内置工具 + 40+ app 集成 | 替代 ChatGPT Atlas / Perplexity Comet |
| **微软 Webwright** | 开源终端原生 Web Agent | 完全跳出单步操作旧模式，终端原生 | 2026-05 发布 |
| **Index** (Laminar AI) | 开源 production-ready | CLI + API，支持 Gemini 2.5 Pro / Claude 3.7 Sonnet / OpenAI o4-mini | 2339 GitHub stars，Apache-2.0 |
| **Steel** | 开源自托管 browser API | Session management（持久 cookie/storage）、Stateful workflows、轻量 REST API | 自托管替代 Browserbase |
| **Nanobrowser** | 开源 Chrome extension | 多 agent + planner，在用户自己浏览器执行，自有 LLM key，无云服务 | — |
| **Open Computer Use** | 开源 Computer Use | 终端命令+文件管理+桌面 UI 自动化+多 agent 编排+流式执行 | 100% 开源自托管 |

## 二、关键架构模式（可迁移）

| 模式 | 内容 | 序境映射 |
|---|---|---|
| **Vision+DOM hybrid** | 同时用视觉理解和 DOM 解析，文本重站点用 DOM，canvas 重站点用视觉 | 序境 cdp_helper（DOM）+ glm_4_6v（视觉）可组合 hybrid |
| **Recovery loop** | selector 失败时 re-plan 而非崩溃 | 序境 browser_runtime policy.py 已有 FailureClass，可增强 re-plan |
| **Stateful sessions** | 持久 cookie/storage，跨多步保持状态 | 序境 edge-cdp-profile 已有持久 profile，可统一 session 管理 |
| **Planner + Executor** | 多 agent：planner 分解任务，executor 执行单步 | 序境 AI 浏览器可增加 planner 层（现有 internal_browser 是单步） |
| **Approval gate** | 高风险动作（提交/购买/发送）需人工确认 | 对齐序境 HCG 人工门控 |

## 三、序境 AI 浏览器现状审计

| 模块 | 行数 | 状态 | 完善优化点 |
|---|---|---|---|
| browser_runtime/contract.py | 10KB | ✅ 完整 | — |
| browser_runtime/policy.py | 8KB | ✅ 完整 | 可增强 re-plan 恢复 |
| browser_runtime/router.py | 4KB | ✅ 完整 | — |
| browser_runtime/cdp_adapter.py | 3KB | ✅ 基础 | 可增强 session 管理 |
| browser_runtime/playwright_adapter.py | 8KB | ✅ 完整 | — |
| browser_runtime/xhs_collector_bridge.py | 9KB | ✅ 完整 | — |
| browser_runtime_api.py | 67行 | ⚠️ 薄 | 增加 session/list/screenshot/extract 端点 |
| browser_discovery.py | 31行 | ⚠️ 薄 | 仅 Bing HTML，可增加多源+质量过滤 |
| internal_browser.py | 514行 | ✅ 完整 | 可增加 planner 层 |
| cdp_helper.py | 522行 | ✅ 完整 | — |

## 四、完善优化建议（研究侧）

1. **API 层增强**：browser_runtime_api.py 增加 `/sessions`（列出活跃 session）、`/screenshot`（截图+视觉分析）、`/extract`（结构化内容提取）端点
2. **Discovery 层增强**：browser_discovery.py 增加多源（Bing+Google News RSS+DuckDuckGo）、去重、质量评分
3. **Vision+DOM hybrid**：cdp_helper 提取 DOM + glm_4_6v 视觉分析组合（视觉模型已放开）
4. **Recovery loop**：policy.py 增强 re-plan 机制（selector 失败时重试替代策略）
5. **Planner 层**：internal_browser 增加任务分解（planner）+ 单步执行（executor）分离

### 红线
- 不绕过验证码/限流/封禁/登录保护（序境采集安全 Gate）。
- 不引入 Browser Use / Playwright 等第三方框架（现有 cdp+playwright adapter 已足够）。
- 高风险动作走 HCG 人工门控。

## 五、Gate
- 进入生产前需 Contract：定 API 端点 schema、session 管理、vision+DOM hybrid 接口、双跑验证、Evidence。

## 六、下一动作
- 优先增强 browser_runtime_api.py（增加 session/screenshot/extract 端点），这是 AI 独立 App 调用浏览器的入口。
