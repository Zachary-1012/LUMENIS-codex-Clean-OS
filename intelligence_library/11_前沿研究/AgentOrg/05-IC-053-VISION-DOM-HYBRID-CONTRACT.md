# IC-053 · Vision + DOM Hybrid 表面 Contract（受 AI Gate 治理）

> 状态：CONTRACT-SPECIFIED（2026-09-04）；**未实现**，待 Release Gate 后进入 IMPLEMENT
> 上游：IC-051（Browser Agent Frontier，Vision+DOM hybrid 模式）+ IC-052（Browser Surface 已提供 DOM 提取）
> 用户决策（2026-09-04）：批准 Vision(glm_4_6v)+DOM hybrid，**另立 Contract、受 AI Gate**，不直接进生产

---

## 一、为什么需要 Hybrid

| 站点类型 | DOM  alone | Vision alone | Hybrid |
|---|---|---|---|
| 文本重（资讯/博客/文档） | ✅ 精确、快、省 token | ❌ 浪费、慢 | DOM 优先 |
| Canvas 重（地图/游戏/Figma） | ❌ 无 DOM | ✅ 唯一可行 | Vision 优先 |
| 动态渲染（SPA/无限滚动） | ⚠️ 需滚动+等待 | ✅ 直观 | DOM+Vision 互补 |
| 验证码/滑块 | ❌ 无法读 | ✅ 可理解 | Vision（受 HCG） |

browser-use 实证：vision+DOM hybrid 在 40-step workflows 达 87% 无人值守完成，WebVoyager 89.1%。

## 二、序境实现路径（复用现有，不新建）

| 层 | 现有能力 | Hybrid 用法 |
|---|---|---|
| DOM 提取 | `browser_surface.extract(kind="dom")`（可交互元素树 + bbox + 可见性，上限 400 节点） | 文本重站点直接用，零 AI 成本 |
| 截图 | `internal_browser_stream` SSE screencast（~16fps）+ `internal_browser.screenshot` | 取当前帧传给视觉模型 |
| 视觉模型 | 智谱 glm_4_6v（用户已放开"视觉模型随便用"） | canvas 重 / DOM 失败时回退 |
| AI Gate | 既有 ai_channel / HCG 人工门控 / Evidence 记录 | 所有 Vision 调用必须过 Gate |

**决策逻辑（确定性，不交给 AI 自由选）**：
1. 先 DOM 提取 → 若可交互元素 ≥ 阈值且目标文本可定位 → 用 DOM（零 AI 调用）。
2. DOM 提取失败 / 元素不可见 / 目标在 canvas → 触发 Vision 回退（过 AI Gate）。
3. Vision 结果必须与 DOM 交叉校验；冲突时标记 `HYBRID_CONFLICT` 进人工审核，不自动执行。

## 三、AI Gate 硬约束（不可绕过）

- Vision 调用必须记录：model/version、input（截图 hash + DOM 摘要）、output、confidence、耗时、cost。
- Vision **不得**直接修改 Production Truth、不得自动点击提交/购买/发送等高风险动作（HCG 人工确认）。
- 外部页面内容视为不可信输入，Vision 输出必须经 Prompt Injection 检测（既有 ai_security）。
- 不因"视觉模型随便用"而无限制调用：保留 token / 日额度预算（智谱日限 20 万 glm_4_5_air，glm_4_6v 另计）。
- 模型、版本、Prompt、Input、Output、Confidence、人工修正全部可追溯（Evidence）。

## 四、API 契约（待实现）

```
POST /api/browser-surface/hybrid/analyze
  { target_id, query, prefer: "dom"|"vision"|"auto", max_dom_nodes, screenshot_quality }
  → { mode: "dom"|"vision"|"hybrid", elements[], vision_annotation?, confidence,
      evidence: {model, input_hash, output_hash, elapsed_ms, cost}, gate_status }
```

- `prefer=auto`（默认）走上述决策逻辑；`prefer=dom` 强制不调 AI；`prefer=vision` 必须过 HCG。
- 响应必须含 `evidence`，缺 Evidence 视为失败。

## 五、验收 Gate

- [ ] Contract 评审通过（本文档）
- [ ] DOM-only 路径零 AI 调用、与现有 extract 结果一致（Oracle 双跑）
- [ ] Vision 回退路径：glm_4_6v 真实调用 + Evidence 完整 + Prompt Injection 检测通过
- [ ] Hybrid 冲突标记 + 人工审核流程可演示
- [ ] 不破坏 internal_browser 采集链路、不消耗采集账号
- [ ] 单测 + 集成测试 + E2E（至少 3 类站点：文本重 / canvas 重 / 动态 SPA）
- [ ] 性能：DOM 路径 < 200ms；Vision 路径 < 8s（含截图+模型）
- [ ] 成本预算：日调用上限可配置，超额降级 DOM-only

## 六、不在本次范围

- 不实现自动 Agent 多步操作（planner/executor 分离另立 IC）。
- 不绕过验证码/登录保护（Vision 只用于理解，不用于破解）。
- 不引入 browser-use / Playwright 等第三方框架（CDP 自研）。
