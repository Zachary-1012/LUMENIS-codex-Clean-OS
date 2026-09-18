# LUMENIS 旧资产回收与唯一实现映射

日期：2026-09-18 12:35（Asia/Shanghai）

本记录把退役目录与旧 `Z-Brand-Core` 的候选能力逐域映射到序境当前主仓。结论只基于本地源码、当前远端源码、运行探测和 Ollama 实际 `/api/tags` 返回，不把文件存在当作生产完成。

## 研究结论

| 领域 | 旧资产 | 当前序境事实 | 处置 |
|---|---|---|---|
| CTH / XHS Collector | `collector_v2/run_xhs_live.py` | 当前 `collector_v2/xhs/live_engine.py` 已拥有采集、规范化、去重、主体过滤、Evidence/Canonical Data 旁路写入 | 恢复同名兼容入口；唯一采集实现仍是 `live_engine` |
| Local AI Runtime | `local_ai_runtime/*` | 当前已存在 `local_ai_client.py`、`intelligence.py`、`provider_registry.py`；旧包未被当前序境导入 | 不复制第二套 Runtime；旧包只作为设计/回归参考 |
| Model Registry | `config/ai_runtime/*` | 旧配置包含旧绝对路径和旧 Qwen2.5 模型；当前 Ollama 实际模型为 `qwen3:4b`、`bge-m3:latest` | 不原样迁移；以当前运行探测和现有 Provider Registry 为准 |
| AI Runtime Evidence | `audit/local_ai_runtime/*`、`docs/ai_runtime/*` | 报告与证据可用于审计，但不应进入生产代码路径 | 纳入本恢复记录/证据索引，不接管 Production Truth |
| Runtime / DB Isolation | `database_isolation.py`、旧 P0 脚本和测试 | 序境已有运行身份、数据库注册、测试隔离和历史 Heritage 索引 | 不复制旧脚本；按当前 canonical DB 契约维护 |
| 历史数据库 | 退役目录中的 `monitor.db`、备份库、测试库 | 存在多份历史库，不能仅凭名称判断可合并；生产数据库不能被旧库覆盖 | 保留原始证据，不直接写入生产库；后续逐库 schema/行级 Evidence 审核 |
| 启动脚本 | 多个 `.bat/.ps1`、旧 `run_production.py` | 与当前唯一主路径、当前运行入口存在路径漂移 | 不复制；只保留当前主路径稳定入口 |

## 当前真实 Ollama 事实

当前本机 Ollama `/api/tags` 返回：

- `qwen3:4b`，Q4_K_M，具备 completion/tools/thinking；
- `bge-m3:latest`，embedding 模型；
- 未发现可证明为 `7.5b` 的已安装模型。

因此旧配置中的 `qwen2.5-coder:1.5b-instruct`、`qwen2.5-coder:7b-agent` 不能直接标记为当前可运行模型，也不能把旧的 `D:/OllamaModels/...` 权重路径写入生产配置。

## 安全边界

Skill/MCP 只提供可发现、可审计的工具和资源，不取得 Production Truth、数据库所有权或业务规则所有权。工具调用必须具备输入校验、权限、人工确认、超时、审计和失败态；AI 输出只能作为分析增强或建议，不能覆盖 Evidence、Canonical Data、风险阈值或最终决策。

## 清理判定

- 可清理：已被当前实现替代的旧兼容入口副本、重复交接文件、旧前端交付归档、空临时目录。
- 不直接合并：旧数据库、浏览器状态、含 Cookie/会话的 Profile、旧模型权重路径、未验证的供应商配置。
- 只有在本记录对应的能力已有当前序境实现或远端 Git 历史可恢复时，才允许移除本地退役副本。
