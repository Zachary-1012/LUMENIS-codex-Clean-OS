# LUMENIS AI Gateway Contract — 序境 AI 网关契约（P0-10）

> 版本：V1.0 ｜ 生效：2026-09-05 ｜ 归属：LUMENIS Intelligence Layer
> 依据源码事实：`osai_engine/ai_gateway.py`

## 1. 定位
Provider-Agnostic AI 网关：OSAI 不再绑死某个模型。
`Task → Model Router → Cost/Latency/Capability/Availability → Model`

## 2. Provider 结构
| Provider | 类别 | 定位 |
|---|---|---|
| zhipu | Cloud | 主力（日常 glm-4.5-air / 深度 glm-5.3 / 视觉 glm-4.6v / 联网 web-search-pro） |
| ark（豆包） | Cloud | 备用最小输出 |
| qwen（千问） | Cloud | 备用 |
| openai-compatible | Cloud | 兼容通道 |
| ollama / gpt-oss | Local | 本地兜底 |

## 3. 路由规则
- `daily→zhipu(text)`、`deep→zhipu(strong)`、`vision→zhipu(vision)`、`search→zhipu(search)`、
  `local_only→ollama`；主不可用按 fallback 链切换。
- 智谱不删除，gpt-oss 不替代智谱——按任务路由共存。

## 4. 纪律（红线④）
- AI 网关只做请求路由与 Provider 抽象，**不是业务事实最终裁判**。
- 主体归属/统计/风险口径等业务事实判定必须回到 ZBC Domain Layer 规则与证据链。
- 密钥只从环境变量读取，永不入库/日志/前端。
- 所有调用可追踪（Trace Contract）：provider/model/时延/用量/失败原因。

## 5. 落点
- `ai_gateway.py`：provider_available / route / gateway_snapshot（确定性可测）
- 后续接 ZBC intelligence 网关的真实调用层（本契约只定接口边界，不改 ZBC 业务逻辑）。
