> **SUPPORTING HISTORICAL AI POLICY — NOT CURRENT EXECUTION/PROVIDER AUTHORITY.**
> Current product AI owner is the single `lumenis/system/ai_gateway/` route under C2; retired Ollama/Zhipu/Jev/provider paths remain inert. Codex engineering model selection is manual per window and is separate from product AI. If text below conflicts, current AGENTS/Product Architecture/Source Owner Index wins.

# AI_POLICY.md

## 总原则

序境 / LUMENIS 必须在没有外部大模型 API Key 的情况下保持核心监测、分析、风险、事件、统计、报告和数据闭环可运行。

## AI 优先级（当前兼容口径）

1. 系统规则、Canonical Data、Evidence 与数据库事实
2. C2 通过唯一 SYSTEM AI Gateway 训练/评估/服务绑定的 LUMENIS-owned AI
3. AI 未绑定或不可用时，AI依赖结果明确 `UNAVAILABLE` / fail-closed；不以退役外部 Provider 或规则文本伪造 AI 成功
4. 人工确认用于纠错、Outcome/Evaluation 与受控 Learning

## AI 可参与

- 主体类型识别：KOS/KOL/KOC/普通用户/媒体/官方/机构
- 内容类型识别：UGC/商业/官方/测评等
- 事件聚类辅助
- 事件关系辅助
- 消费者诉求提炼
- 风险原因解释
- 报告文字生成

## AI 不得成为唯一事实来源

AI 不得单独决定：主体口径、发布时间、采集数量、报告周期、原始数据是否存在、最终数据库事实。

## Shadow Mode

新模型、新 Prompt、新分类器先旁路运行：读取现有数据 → 生成 AI 结果 → 单独记录 → 与系统判断比较 → 人工抽检 → 再决定是否正式采用。

## 最低审计字段

`ai_run_id`, `target_type`, `target_id`, `model_name`, `model_version`, `prompt_version`, `input_hash`, `output`, `confidence`, `system_result`, `final_result`, `accepted`, `human_correction`, `created_at`。

## 历史：本地 Ollama（已退役）

Ollama 曾是历史本地 AI 方向，当前已退役且不属于产品或研发默认路线。保留相关接口/历史仅为兼容与溯源；不得自动发现、探测、fallback 或重新启用。

产品 AI 的 canonical owner 是 `lumenis/system/ai_gateway/`。`local_ai_client.py` 及现有 `/api/local-ai/*` 仅作为待收敛兼容调用保留其独有行为，不得再建平行 AI Runtime；实际 AI 成功必须来自当前 C2 批准并绑定的 owned Gateway 运行时。

## 工程 AI

Codex / Codex CLI 是当前研发执行器，模型、推理强度和服务档位完全以 Product Owner 在当前窗口的手动选择为准；仓库、Hook、CLI/Profile、Subagent 不指定默认模型或自动切换。OpenCode 当前搁置，不是当前研发 fallback，也不是产品模型路由或 Production Truth owner。

## 隐私与密钥

API Key、Cookie、Token、Secret、个人账号凭证禁止提交 Git。生产配置通过本地环境变量或未纳入版本控制的配置文件提供。
