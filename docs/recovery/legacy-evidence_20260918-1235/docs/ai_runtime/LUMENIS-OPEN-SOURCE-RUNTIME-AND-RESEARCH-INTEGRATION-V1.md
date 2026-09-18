# LUMENIS 本地优先开源 AI Runtime 与研究集成 V1

状态：`SHADOW_READY / READY_FOR_AUDIT`。本文定义运行边界，不构成 `PRODUCTION_APPROVED`。

## 架构边界

`Production Truth → Evidence / Canonical Data → Intelligence Router → Local Open-Source AI Runtime → Advisory Intelligence → Evidence / Trace → UI / Report / Agent / Research`

- 序境仍只有 CTH（序境·商业运营）与 BMP（序境·品牌市场）两条产品线。
- AI 只生成派生分析、解释与草稿，不拥有 Production Truth、Canonical Data、主体规则、指标口径或不可逆业务状态。
- `LOCAL_ONLY` 禁止云端；`HYBRID` 本地优先；`CLOUD_FALLBACK` 仅在策略列明的本地失败类型下允许升级。
- 模型缺失、Ollama 停止或云端不可用均不得阻止 Core 启动；失败必须显式并进入确定性路径。

## 当前实现

- Canonical runtime：`local_ai_runtime/`。
- Registry：`config/ai_runtime/providers.json`、`models.json`、`runtime.json`。
- 当前业务入口：既有 `/api/ai/analyze`，未建立第二套业务 API。
- 结构化结果包含 provider、model、confidence、fact basis、prompt version、trace、evidence、timestamp。
- Evidence 为仓库外可配置的追加式 JSONL 哈希链，敏感字段递归脱敏。
- 默认模型为 `qwen2.5-coder:1.5b-instruct`；7B 在当前节点真实触发内存不足，降为 `SHADOW`。

## 运行与恢复

1. 安装 Ollama 后设置可配置模型目录；不得将权重、缓存或 Runtime 二进制提交 Git。
2. 拉取 Registry 中精确模型标签，并核对 manifest ID、权重 SHA-256 与许可。
3. 默认 `LUMENIS_AI_RUNTIME_MODE=LOCAL_ONLY`；云端只有在显式启用、凭据注入、健康通过与策略允许时可用。
4. Evidence 目录通过 `LUMENIS_AI_EVIDENCE_DIR` 指向仓库外受控路径。
5. 恢复验证运行 `scripts/verify_local_ai_runtime_v3.py`；它复制数据库到隔离目录，不写生产库。

## 资源边界

当前节点为 Ryzen 5 5500U、16GB RAM、无可用高性能独显。单并发、最多 2 个排队、超时 120 秒、一次重试、空闲卸载。本节点不需要 GPU Kernel 优化。7B/32K 真实加载需要约 7.6GiB 可用内存而失败；1.5B/Q4_K_M 的真实 Ollama 进程峰值以验收证据为准。

## 后续替换

模型与 Provider 通过 Registry + Adapter 解耦。未来自研模型只能先进入 `RESEARCH_ONLY`，完成来源、许可、权重、质量、资源、失败恢复、安全与真实业务 E2E 后，依次进入 `SHADOW`、`PRODUCTION_CANDIDATE`；最终批准仍需人工 Gate。
