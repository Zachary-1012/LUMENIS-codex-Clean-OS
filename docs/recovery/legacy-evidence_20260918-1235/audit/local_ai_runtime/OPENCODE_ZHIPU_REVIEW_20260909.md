# OpenCode × 智谱 Coding Plan 只读复核 — 2026-09-09

## 真实调用

- 执行层：OpenCode 1.3.14
- Provider/Model：`zhipuai-coding-plan/glm-4.7`
- 模式：Plan / 只读
- 写入：无
- 第一次调用：已读取 Git diff，但后续检索因终端权限被拒而中止，不能算完整审查。
- 第二次调用：使用 Read/Glob 完成指定文件与 Evidence 读取，最终结论 `REPAIR`。

## 处理结果

已采纳并修复：

- Zhipu Registry 为 `SHADOW` 时，业务路由必须默认禁止；只有显式 `LUMENIS_ZHIPU_SHADOW_ALLOWED=1`、注入受控 Adapter、凭据存在、云开关开启且错误类型允许时才可升级。
- `/api/ai/test` 从 Legacy `intelligence.test_connection` 收敛到 `LocalFirstAIService`，复用 Router、结构化结果与 Evidence。

经源码复核后不采纳：

- Health 返回 `provider=OLLAMA_LOCAL` 是在描述被检测 Provider，不等于实际分析路由；DOWN 时分析结果会明确返回 `DETERMINISTIC_RULE`。
- 默认 `data/monitor.db` 是生产向后兼容契约；隔离环境显式设置 `ZBC_DB_PATH`。强制在未设置时抛错会破坏 Core 启动。
- `sanitize_trace` 递归构造新 dict/list，不修改调用方对象，无需 deepcopy。
- Ollama 端口保持回环地址可配置是部署需求；安全边界是 loopback-only，而不是固定 11434。

## 结论

OpenCode/智谱的 `REPAIR` 已完成有效项修复。由于它未读取完整 Legacy 云调用链，其审查范围记为 `PARTIAL`；本轮不把 OpenCode 或智谱提升为业务 Production Truth Authority。
