# LUMENIS Local-First Open-Source AI Runtime V3 最终验收报告

## 基线

- BASE_SHA：`f57a45c4b9a95483d7408a7dbe59a75699bb35ee`
- BRANCH：`integration/local-open-source-ai-runtime-v3`
- 产品边界：仅 CTH / 序境·商业运营、BMP / 序境·品牌市场；没有新增产品线。
- 架构：Production Truth → Evidence / Canonical Data → Intelligence Router → Local Runtime → Advisory Result → Evidence / Trace → API / UI。
- 数据库：全部 E2E 使用仓库外隔离副本；最终运行前后源数据库 SHA-256 一致。

## 本地模型

- Model：`qwen2.5-coder:1.5b-instruct`
- Ollama manifest：`d7372fd82851`
- Weight SHA-256：`29d8c98fa6b098e200069bfb88b9508dc3e85586d20cba59f8dda9a808165104`
- Quantization：Q4_K_M
- License / Weight License：Apache-2.0，已核验
- Runtime：Ollama 0.7.0，loopback only
- Health：3 次真实探针均 `UP / LOADABLE / REAL_CALL_VERIFIED`
- 7B：真实加载因内存不足失败，降为 `SHADOW`，不再是本机默认。

## 验收矩阵

| 项目 | 状态 | 事实证据 |
|---|---|---|
| OLLAMA_RUNTIME | PASS | 安装、模型列表、加载、结构化调用、流式、卸载、停机状态均实测 |
| LOCAL_MODEL | PASS | 六类固定测试质量 1.0，格式通过，错误率 0 |
| LOCAL_ONLY_MODE | PASS | Router 与真实业务调用均选择本地；云开关关闭 |
| ZERO_CLOUD_INDEPENDENCE | PASS | 进程出网守卫记录公网连接尝试 0 |
| BUSINESS_AI_ANALYSIS | PASS | 真实情绪/摘要/主题/Evidence 结果 |
| ROUTER | PASS | LOCAL_ONLY / HYBRID / CLOUD_FALLBACK 单测与真实本地路径通过 |
| STRUCTURED_OUTPUT | PASS | Typed Contract + JSON Schema + 校验 + 显式失败 |
| HEALTH | PASS | installed/configured/reachable/loadable/real call/last success/failure/latency |
| FALLBACK | PASS | Ollama 真停机时 Core 200、业务 API 200、Provider=DETERMINISTIC_RULE |
| RESOURCE_GUARD | PASS | RAM/CPU/model/runtime/concurrency/queue/retry/cooldown/idle unload 均有边界 |
| ZHIPU_OPTIONAL | PASS | Registry=SHADOW，默认不参与业务路由；显式治理门已测试 |
| OPENCODE | PASS | OpenCode 1.3.14 × 智谱 Coding Plan GLM-4.7 真实只读调用 |
| CODEX_SOL | PARTIAL | Codex 已完成实现与复核；当前会话不暴露 Sol 专属运行身份，未伪造证明 |
| AUTO_RESEARCH | PASS | 紧凑 Evidence JSON 实验，质量等价，KEEP，无生产写入 |
| PERFORMANCE_RACE | PASS | Before 8492ms / After 19122ms，质量等价但变慢，按 Gate 正确 REJECT |
| EXECUTION_EFFICIENCY | PASS | Python/SQLite/API/AI 指标已采集；GPU Kernel=NOT_REQUIRED_FOR_CURRENT_NODE |
| LICENSE_TRACE | PASS | 模型、权重、三个研究项目来源/版本/许可已登记；未复制研究项目源码 |
| SECURITY | PASS | 回环限制、路径/模型名、Shell 字符、密钥脱敏、Manifest/Evidence 篡改测试通过 |
| GIT_TRACKING | PASS | Ignore 检查无误，无权重/Runtime/大缓存；提交候选前全部进入 Git |
| CRITICAL_E2E | PASS | Service + Flask API + CTH 真实页面 + 停机降级均通过 |

## 真实页面

CTH 智能问答页以真实输入返回 `OLLAMA_LOCAL`、结构化分析、置信度与 Evidence ID，并显示“仅供辅助分析”。原页面 Legacy API 与参数不一致已收敛到现有 Canonical `/api/ai/analyze`，未新增第二套业务 API。

## 资源与性能

- 最终 Gate：Peak system used 15702MB；Ollama 相关进程 RSS 合计峰值 5354MB；Peak CPU 93.8%。
- 常规短输入约 6.1–8.5 秒；长输入约 32.0 秒；两次 API 合并链约 12.3 秒。
- Ollama 自身日志给出的单模型完整所需内存约 1.5GiB，权重约 934.7MiB；进程合计峰值更高，因此必须维持单并发和资源护栏。

## 测试

- 定向 Unit / Integration / Failure / Security / DB isolation：`74 PASS`。
- 后台线程泄漏：0。
- Python compile：PASS。
- `git diff --check`：PASS。
- 敏感凭据模式：0 文件。
- 模型权重/大文件误入：0 文件。
- 最终 Critical E2E：PASS。
- Ollama 真停机 E2E：PASS。

## OPEN ISSUES

### P0

无。

### P1

- 当前节点内存与 CPU 峰值高，只批准单并发 Shadow 使用；上线前需持续压测和可观察性。
- 智谱业务 Adapter 没有做本轮直接生产调用；当前仅验证 OpenCode Coding Plan 通道，业务 Provider 保持可选 SHADOW。
- Clean 工作区数据库相对 P0-A 冻结快照曾出现非生产测试增量：`ai_call_logs +6`、`auth_recovery_tasks +2`、新增 `schedule_decisions 21`。已修复两个硬编码隔离根因，最终 Gate 源库哈希不再变化；数据库恢复/保留仍等待人工决策，未擅自覆盖。
- 应用启动日志存在 `evidence_api` Blueprint 重复注册警告和 GBK 日志编码警告，不阻断本轮 API，但需独立修复。

### P2

- Interaction Model 仅有 `RESEARCH_ONLY` Adapter Slot。
- 研究优化尚未覆盖 Worker/Browser/Agent 深度性能剖析；本轮只覆盖当前 Local AI Gate 所需链路。
- 后续可研究短时 keep-alive 缓解重复加载，但必须先证明资源与正确性不退化。

## 最终状态

- `LOCAL_OPEN_SOURCE_AI_RUNTIME = VERIFIED / USABLE`
- `LUMENIS INTEGRATION = READY_FOR_AUDIT`
- `PRODUCTION_APPROVED = NO`

本结论只覆盖本轮 Local-First Runtime 与既有业务链集成，不替代最终 Product Audit、人类审批、主分支合并或部署 Gate。
