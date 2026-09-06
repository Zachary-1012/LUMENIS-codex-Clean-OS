# 模式卡｜AI 通道稳固层 + 调用点单入口收敛（2026-09-04）

## 背景
ZBC(序境-Core) 生产 8201 智谱通道此前为"单次请求、失败即降级"，不符合 24h 不断链要求；
且存在"AI 调用分散、重复拼 prompt"的隐性重复风险。

## 已落地（PRODUCTION-VERIFIED）
1. **ai_channel.py 状态与策略内核**（零依赖标准库）：
   - `ensure_env_loaded`：配置自加载，**纯显式入口**，import 无全局副作用（关键：避免污染 os.environ 破坏测试隔离）
   - `classify_error`：失败分类纯函数，401/400 不重试、429/5xx/网络瞬时可重试
   - `CircuitBreaker`：CLOSED/OPEN/HALF_OPEN 状态机，线程安全，半开探测，连续失败阈值+冷却有界（禁无限重试）
   - `channel_health`：健康快照（last_success/failure、延迟、计数、暂停态）
   - `start_health_monitor`：daemon 幂等心跳保活线程（24h 主动探活）
2. **intelligence._chat 云端分支**改走 `ai_channel.post_with_retry`（有限重试+熔断放行+UTF-8 归一）；ollama 本地分支不动；脱敏仍在发前执行
3. **app.py 启动区**拉起 24h 心跳线程 + 新增 `/api/ai/channel-health` 健康端点
4. 单测 18 项 + 真实智谱连通（glm-4.5-air 0.49s / glm-5.3 31.3s 分级验证）

## 关键判断（KEEP 不重构）
- 全仓 13 处 AI 业务调用**已收敛到唯一权威入口 intelligence._chat**（ai_gateway_v570 已废弃统一）
- 智谱聚类三模式：A 问答/对话、B 分析/评分/分类、C 摘要/生成——各调用点业务语义独立、已工作正确 → 不强行合并 prompt，登记 KEEP
- 唯一共享模式 Grounded QA（app.py:2472 诺米 RAG 与 ai_hub:142 数据限定 QA）收敛收益低、风险中 → KEEP

## 反模式（避免重复）
- ❌ import 模块时隐式 `load_dotenv(override=True)` 或 `ensure_env_loaded()` 全局副作用 → 破坏测试隔离（本仓已踩坑：config.py override 使 flag 测试与 gateway 测试共跑失败）
- ❌ 每模块各建一套 AI Gateway / 各写一套重试熔断 → 必须收敛单入口 + 共享状态内核
- ❌ 无限重试 / 熔断无界 → 一律有界（阈值/冷却/半开探测）

## 可复用资产
- `ai_channel.py` 内核 + `intelligence.chat(system,user,level=...,pack_id='glm_4_5_air')`（分级：low/medium→glm-4.5-air 快、high/critical→glm-5.3 强；确定性任务 use_cache=True）
- 智谱 token 包（glm_4_5_air 1191万）与按次包（per_call 20，已用尽）分账：token 任务走 pack_id='glm_4_5_air'，高价值一次性走 per_call
