# AI_POLICY.md

## 总原则

序境 / LUMENIS 必须在没有外部大模型 API Key 的情况下保持核心监测、分析、风险、事件、统计、报告和数据闭环可运行。

## AI 优先级

1. 系统规则与数据库事实
2. 本地 Ollama 模型辅助理解
3. 外部大模型作为可插拔增强（默认不作为硬依赖）
4. 人工确认用于纠错与样本沉淀

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

## 本地 Ollama

Ollama 是当前默认本地 AI 运行方向。模型名称、地址和参数必须配置化，禁止写死在业务代码中。模型不可用时，业务流程必须降级为系统规则链路，而不是整体失败。

产品 AI 的 canonical owner 是 `lumenis/system/ai_gateway/`。`local_ai_client.py` 及现有 `/api/local-ai/*` 属于待收敛兼容调用，迁移前保留其独有行为，不得再建平行 AI Runtime。

## 工程 AI

OpenCode/Codex 用于研发、审计、测试和自动化。OpenCode 的仓库配置位于 `.opencode/opencode.json`；它不是用户功能、产品模型路由或 Production Truth owner。

## 隐私与密钥

API Key、Cookie、Token、Secret、个人账号凭证禁止提交 Git。生产配置通过本地环境变量或未纳入版本控制的配置文件提供。
