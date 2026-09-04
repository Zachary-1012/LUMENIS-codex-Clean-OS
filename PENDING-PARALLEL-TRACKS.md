# Pending Parallel Tracks · 独立待办标记（不混入浏览器主线）

> 建立时间：2026-09-04
> 目的：用户要求对历史未竟项"进行标记"，明确归属、状态、与当前浏览器主线的隔离关系。
> 原则：每条独立轨道单独推进，不因浏览器开发而阻塞，也不把浏览器改动混入这些轨道。

---

## Track A · ai_api 拆分收尾

- **状态**：PARTIAL（ai_api.py 已拆分，app.py 残留 1 个路由待迁）
- **残留**：`app.py` 中 `@app.route('/api/ai-learning/optimization/<operation_type>')`（约 L1775）待迁入 `ai_api.py`
- **待办**：
  1. 迁移残留路由到 ai_api.py，保持签名与行为不变
  2. 全量回归（pytest + api_smoke）
  3. OpenAPI / 路由清单更新
  4. 删除临时文件 `_split_ai_api.py`、`app.py.bak-ai-api-split`
- **风险**：低（纯代码迁移，无业务逻辑变化）
- **与浏览器主线关系**：完全独立，互不影响

## Track B · 智谱连接 24h 稳固 / 多层通道 / 编码转换

- **状态**：PENDING（用户长期要求"智谱最大算力、24h 连接不断、函数计算转换编码多层稳固通道"）
- **待办**：
  1. 智谱 API 连接保活 / 心跳 / 断线重连（指数退避 + 上限）
  2. 多层通道：主通道 + 备用通道 + 降级（豆包最小输出作为兜底）
  3. 编码转换：函数计算层统一处理 UTF-8 / 流式响应编码 / 特殊字符
  4. 额度分配：智谱主力（glm_4_6v 视觉 + glm_4_5_air 日限 20 万），豆包最小输出
  5. 可观测：连接状态 / 最后成功时间 / 失败计数 / 熔断
- **风险**：中（涉及 AI Provider 抽象层，需双跑验证不破坏现有 ai_channel）
- **与浏览器主线关系**：Vision+DOM hybrid（IC-053）依赖智谱视觉模型，本轨道是其前置基础

## Track C · 既有 39 个测试失败收敛（KOS 类为主）

- **状态**：KNOWN（全量 pytest FAILED=10 / ERROR=29，合计 39，全部为既有类别）
- **失败清单（2026-09-04 全量）**：
  - `test_kos_ops.py` × 9 ERROR（sqlite3 共享临时库污染）
  - `test_kos_paid.py` × 11 ERROR（NoneType / 共享库）
  - `test_dev_exec_guard.py` × 9 ERROR（环境/权限）
  - `test_idea_sit_backing.py` × 7 FAILED（案例库数据）
  - `test_database.py` × 1 FAILED（表结构）
  - `test_evidence_export.py` × 1 FAILED
  - `test_lean_footprint.py` × 1 FAILED
- **待办**：
  1. KOS 测试隔离：每个测试用例独立临时 DB（不共享），修复 sqlite3 污染
  2. dev_exec_guard 环境依赖梳理
  3. idea_sit_backing 案例库数据对齐
  4. 收敛目标：全量 pytest 0 新增失败，逐步清零既有
- **风险**：低-中（测试修复，不碰生产逻辑）
- **与浏览器主线关系**：完全独立；浏览器新增 44 测试全过，未新增任何失败

---

## 推进规则

- 三条轨道**独立排期**，不与浏览器主线（IC-052/053）混在同一个 commit。
- 每条轨道完成时单独：Contract → Implementation → Test → Evidence → Commit → Remote Verify。
- 浏览器主线的改动**不得**顺手修改这三条轨道的代码（避免修 A 坏 B）。
- 状态变更时更新本文件。
