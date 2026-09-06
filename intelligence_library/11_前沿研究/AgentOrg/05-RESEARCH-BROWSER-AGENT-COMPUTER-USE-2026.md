# 研究 · Browser Agent / Computer Use 2026 前沿（服务 AI 浏览器完善）

> 状态：RESEARCH-DONE（研究侧资产；服务序境 AI 浏览器完善优化）
> 依据：2026-04~09 公开信息（Microsoft Fara1.5、Magnitude、Browser Use、Index、Wuying-Browser-Agent、Agent-first-browse）
> 边界：仅研究侧沉淀；第三方框架只学习/验证/借鉴，不复制受保护代码；不绕过平台安全措施
> 反哺对象：序境 AI 浏览器（browser_runtime / internal_browser / human_browser / cdp_helper）

---

## 一、行业基线（2026）

| 项目 | 架构 | 关键指标 | License | 发布 |
|---|---|---|---|---|
| **Microsoft Fara1.5** | observe-think-act，截图+对话历史→鼠标键盘坐标，无 a11y 树 | 4B/9B/27B 三档，集成 MagenticLite 沙箱浏览器 | 微软 Foundry | 2026-05 |
| **Magnitude** | vision-first，像人一样看屏幕操作 | WebVoyager 94%（SOTA） | 开源 | 2026-07 |
| **Browser Use** | 开源 Python 框架，连接任意 LLM 到真实浏览器 | WebVoyager 89.1%（580任务） | 开源 | 2026 |
| **Index (Laminar AI)** | 生产级浏览器自动化代理，CLI/API | 2339 GitHub stars，支持 Gemini/Claude/o4-mini | Apache-2.0 | 2026 |
| **Wuying-Browser-Agent** | 真实世界中心的长程浏览器代理 | 长程任务 | arXiv 2608.17319 | 2026-08 |
| **Agent-first-browse** | a11y DOM（快速）→ 歧义时 VISION 消歧（1 shot） | 混合感知降本 | 开源 | 2026-09 |

## 二、核心技术范式（可迁移点）

### 1. Vision-First 感知（Magnitude / Fara1.5）
- 直接看截图理解界面，不依赖 a11y 树/解析模型。
- 优势：跨平台通用、能处理无标准控件的界面。
- 成本：每次调用视觉模型（序境 glm_4_6v 已放开，可承担）。
- **序境映射**：AI 浏览器可采用 vision-first 主感知，glm_4_6v 做界面理解。

### 2. 混合感知降本（Agent-first-browse）
- **a11y DOM 快速路径**：先读无障碍树（快、便宜），无歧义时直接操作。
- **VISION 消歧路径**：a11y 树歧义时，1 shot 视觉模型确认。
- **序境映射**：现有 cdp_helper（CDP 协议）可做 a11y DOM 快速路径，glm_4_6v 做消歧，降低视觉调用成本。

### 3. Observe-Think-Act 循环（Fara1.5）
- 截图 → 推理任务状态 → 输出单一动作（鼠标/键盘/搜索/上下文管理）。
- 无独立解析模型，端到端。
- **序境映射**：AI 浏览器执行循环可采用此模式，但需加 HCG 人工门控（高风险动作确认）。

### 4. 沙箱执行（Fara1.5 MagenticLite / Claude Cowork）
- 浏览器动作在隔离沙箱中执行，不影响用户主浏览器。
- **序境映射**：现有 browser_runtime（独立 Chrome profile）已是沙箱模式，需完善隔离与恢复。

### 5. 长程任务可靠性（Wuying-Browser-Agent）
- 面向真实世界长程任务（多步骤、多页面、异常恢复）。
- **序境映射**：与 IC-043 长任务可靠性方法论联动——状态检查点、异常恢复、Cooldown、熔断。

## 三、序境 AI 浏览器完善建议（研究侧）

### 现状审计
- 已有：`browser_runtime/`、`internal_browser.py`（22KB）、`internal_browser_stream.py`（10KB）、`human_browser.py`（14KB）、`cdp_helper.py`（20KB）、`browser_discovery.py`、`browser_runtime_api.py`。
- 缺口：① 无统一 Agent 执行循环（observe-think-act）；② 视觉感知未集成 glm_4_6v；③ 无 a11y DOM 快速路径；④ 长程任务异常恢复机制待完善。

### 完善路径（建议优先级）
1. **P0**：建立统一 Agent 执行循环（observe→think→act→verify），复用现有 cdp_helper。
2. **P1**：集成 glm_4_6v 视觉感知（已放开，随便用），做界面理解与消歧。
3. **P1**：a11y DOM 快速路径（CDP Accessibility domain），降低视觉调用频率。
4. **P2**：长程任务状态检查点 + 异常恢复 + Cooldown + 熔断（与 IC-043 联动）。
5. **P2**：沙箱隔离完善（独立 profile、Cookie 隔离、不共享用户主浏览器）。

### 红线
- 不绕过验证码、限流、封禁、权限、登录保护或平台安全措施。
- 自动采集频率遵守既定规则（每日最多 2 次，手动最多 30 分钟）。
- AI 浏览器动作受 HCG 人工门控（高风险动作需确认）。
- 第三方框架只学习/验证/借鉴，不复制受保护代码。

## 四、下一动作
- 产品 Owner 确认 AI 浏览器完善的 Contract（执行循环、视觉感知、人工门控范围）。
- 评估现有 browser_runtime/internal_browser 与 Fara1.5/Magnitude 范式的差距。
- 与序境 AI 独立 App（研究1）联动：内置浏览器作为 App 的代理执行层。
