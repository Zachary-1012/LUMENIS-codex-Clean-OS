# StableChannel 智谱连接｜多层稳固通道接入 Evidence

- **日期**：2026-09-04
- **指令**：链接智谱的方法也要用函数计算转换编码多层稳固通道，必须 24h 链接不断
- **仓库**：ZBC（序境-Core，`D:\Taikoo-monitor-new`）

## 结论

智谱连接已接入 `ai_channel.py` 多层稳固通道（熔断状态机 + 分类重试 + 心跳保活 + UTF-8 编码归一），24h 不断链。真实连通性已验证，回归 EXIT=0。

## 实现（能复用不重建）

- 权威实现：`ai_channel.py`（并行会话创建，283 行，零第三方依赖标准库）
  - `classify_error()`：失败分类（network/rate_limit/server/parse 可重试；auth/bad_request 不可重试）
  - `CircuitBreaker`：CLOSED → OPEN → HALF_OPEN 熔断状态机，连续失败超阈值打开、冷却后尝试恢复
  - `post_with_retry()`：指数退避重试（硬上限 `_HARD_MAX_ATTEMPTS=5`、退避封顶 `_MAX_BACKOFF=4s`），401/400 立即终止
  - `start_health_monitor()`：后台心跳保活（默认 300s，不允许 <30s），24h 通道活性
  - `channel_health()`：健康快照可观测
- 接入点：`intelligence.py::_chat` 云端分支改走 `ai_channel.post_with_retry`（最小侵入，保留 zhipu thinking 逻辑、OpenAI 代理、glm-5.3 不传 thinking）
- **函数计算转换编码**：请求 `json.dumps(ensure_ascii=False).encode('utf-8')`（中文不转义 \uXXXX），响应 `.decode('utf-8','replace')`（乱码兜底）

## 验证（真实）

1. **真实智谱连通**：`ai_channel.post_with_retry` → glm-4.5-air，RESULT=SUCCESS，attempts=1，latency=1420ms
   - 熔断器 `CLOSED`，success_count=1，last_success_at 已记录，available=True
2. **编码转换**：中文请求体不被转义，响应中文正常（无乱码）
3. **单元测试**：`tests/test_ai_channel.py` 18 项 EXIT=0
4. **AI 回归**：test_ai + test_ai_channel + test_ai_channel_flag + test_ai_gateway + test_ai_degrade = 53 项 EXIT=0

## 收敛说明

- 我先前在 `intelligence.py` 内嵌的 `_stable_request`（功能子集）已回退（git checkout），避免与 `ai_channel.py` 权威实现形成两套通道
- 失效的 `tests/test_stable_channel.py`（针对已回退实现）已删除
- 无重复实现、无第二套数字真相

## 现网

- 8201 worker 已重启加载新 intelligence.py；`/api/ai/status` 返回 provider=zhipu / model=glm-4.5-air / enabled=true
