# 本轮生产收敛证据（2026-09-13）

仓库：`Zachary-1012/LUMENIS-codex-Clean-OS`

唯一源码目录：`D:/LUMENIS_REBUILD/LUMENIS-codex-Clean-OS`

分支：`codex/production-convergence`
开始 HEAD：`1344fb4`；本轮已形成提交：`a6dfab2`、`c75ea7b`。

## 已验证的源码与 Gate

- CI 的 Python 语法、pytest 与 HIGH/CRITICAL 边界检查恢复为阻断项，测试依赖已显式登记；远端 CI 尚未验收。
- Python 3.11 AST 扫描：1075 个 tracked Python 文件，0 个语法错误，且不生成字节码。
- 数据库隔离、AI intent 权限、Experience 样板联合回归 41 项通过。
- 候选库副本 E2E 5 项通过：44 屏均返回 200，38 屏真实绑定，6 屏诚实标记未绑定；外部指标返回 NULL/notcollected；权限三态可达；源库 SHA 不变。
- 资产准入与并发注册回归 2 项通过。生产知识仅接纳 `FACT/VERIFIED + ADMITTED`，PENDING、CONCEPT、CANDIDATE、NULL 均不得进入运行时知识。
- 边界检查 HIGH 从 2 降到 0；剩余 MEDIUM 8、INFO 11。OSAI 未指定时，跨仓覆盖仍不完整。
- 新增兼容契约 `/api/runtime/identity`，与 `/api/experience/runtime/identity` 返回同一真实身份，不新增第二套实现。

## 唯一路径与运行事实

- `D:/LUMENIS_REBUILD` 已登记为本机唯一序境工作根；根目录 `README.md` 与 `CANONICAL_WORKSPACE.json` 明确源码、运行数据、AI、证据、交付及退役区角色。
- 生产启动脚本已从 `D:/Taikoo-monitor-new` 改为随仓库自身位置解析；旧绝对路径不再是正式启动前提。
- `.venv`、本地 `.env` 与四个浏览器 Profile 已迁入唯一生产仓；`.env` 保持 Git 忽略，未输出或提交凭据。
- Ollama 模型已迁入 `D:/LUMENIS_REBUILD/_LOCAL_AI_RUNTIME/OllamaModels`，用户级 `OLLAMA_MODELS` 已指向新路径；实时 API 可见 3 个模型。OpenCode 当前默认使用 `ollama/qwen2.5-coder:7b-agent`，不再依赖智谱配置。
- 以受保护数据库副本运行官方启动脚本：8201 health、Experience、CTH、BMP、AI-01、CTH-01 与 runtime identity 均为 HTTP 200。
- Supervisor 恢复演练：终止实际监听进程后约 20 秒恢复，新监听 PID 出现，状态记录 `restarts=1`。
- 生产候选数据库 SHA256 在启动、页面/API 验证和恢复演练前后保持 `A8CD46E807830F10CDA0F406A391711C2E6512E2E5B564BF3F6310DAC209E838`。
- 验证结束后已停止候选 Runtime；未部署为正式服务。

## 数据与历史资产保护

- Taikoo 运行数据已迁到 `D:/LUMENIS_REBUILD/_PROTECTED_RUNTIME_DATA_20260913/Taikoo-monitor-new-data`。
- 79 个历史数据库资产共 160243712 字节已复制、逐项 SHA 校验，清单为 `DATABASE_ASSET_INVENTORY.csv`；未删除或覆盖任何生产数据库。
- 两个 Git history bundle 均通过 `git bundle verify`；旧 dirty 工作树另有 patch 证据。
- C 盘扫描确认的 24 个产品资料已迁入 `_SOURCE_INPUT_ARCHIVE/C_DRIVE_20260913` 并生成清单。Codex 自身管理的 attachment/blob 未作为产品工作区移动。
- `D:/Taikoo-monitor-new` 已退出并迁入 `_DECOMMISSIONED_WORKTREES_20260913`；`D:/Z-Brand-Core` 内容已迁出，但空目录仍被当前桌面任务持有句柄。
- 递归删除退役目录被自动执行策略拒绝，因此重复/临时资产被隔离到 `_PENDING_DELETE_AUTOMATION_BLOCKED_20260913`，没有伪称已删除。

## 全量测试真实结果

全量 `tests/` 的 non-online 套件在四个数据库变量统一指向独立空临时库、禁用在线能力后完成。JUnit 记录 4133 项：4026 通过、89 失败、5 错误、13 跳过，用时 295.351 秒，退出码为 1。证据位于 `D:/LUMENIS_REBUILD/_TEST_RUNTIME/full-non-online-20260913-final/junit.xml`。失败集中为四类：

1. 测试夹具仍假设已有完整迁移/种子数据，空库出现 `notes`、`events`、`collection_logs`、`kos_profiles` 等表缺失；
2. 测试仍硬编码已退役的 `D:/Taikoo-monitor-new`，产生 `FileNotFoundError`；
3. Cookie、真实数据或在线适配器依赖未被正确标为 online/fixture，离线运行出现预期外失败；
4. 可验证的源码/契约缺口，包括缺少 `ad_intelligence.models`、若干历史 registry/OSAI/permission 断言漂移。

因此，已通过的 41+5+2 定向回归不能替代全量 Gate；全量失败必须继续逐项修复或按证据重分层，不能删除测试或弱化断言。

## 外部辅助事实

- 智谱唯一探针失败后按用户要求不再消耗时间。
- Ollama API 当前健康并可列出三个本地模型；此前 1.5B 只读审查有真实返回，7B OpenCode 审查曾超时终止。模型意见只作研发辅助，不拥有 Production Truth。

## 未验收

- 全量 non-online 套件未通过。
- 6 个 Experience 屏仍为诚实未绑定状态（4 个外部依赖阻塞，2 个 N/A）。
- 推送 `codex/production-convergence` 已重试，GitHub HTTPS 返回 `Recv failure: Connection was reset`；随后 TCP 443 探测失败。远端分支与远端 CI 因本机网络阻断尚未验收，本地提交与 bundle 证据保留。
- 当前仅验证候选副本 Runtime，未部署、未发布、未证明真实生产持续运行。

`PRODUCTION_READY = NO`
