# LUMENIS P0-C 数据库与测试隔离实施报告

日期：2026-09-10

分支：`integration/p0c-test-migration-isolation-v1`

基线提交：`79819ef18bcc127957c969acab1f5896c9ea8c6d`

## 1. 结论

P0-C 的源码实施与专项 Gate 已完成：测试默认数据库被绑定到操作系统临时目录；仓库数据库及其 WAL/SHM 被纳入身份保护；直接 SQLite 连接（含 `file:` URI）会在 pytest 收集期起被拒绝；迁移在单一事务内更新 schema 与版本；备份使用 SQLite Backup API 从只读源生成一致快照；内容生成 Evidence 的空父键被归一化为 `NULL`。

本报告不声明产品已上线，也不把全量测试失败隐藏为成功。

## 2. 实施范围

- 新增 production / test / experiment 数据目录约定与路径解析。
- 新增数据库身份、只读备份、行级外键检查能力。
- pytest 收集前创建系统临时数据库并设置 `ZBC_DB_PATH`。
- pytest 会话前后校验仓库数据库、`-wal`、`-shm` 的 SHA-256、大小和 mtime。
- 拒绝测试直接连接仓库 `data/monitor.db`，含相对路径、绝对路径和 SQLite `file:` URI。
- Alembic 测试改用临时 Alembic 环境，不再向仓库 `alembic/versions` 写临时 revision。
- KOS、负面事件、Evidence 导出等测试改用临时数据与临时输出。
- `ark_llm` 的 token 统计路径改为调用时遵守 `ZBC_DB_PATH`。
- `content_generation_evidence.parent_evidence_id` 的空字符串/空白字符串改写为 `NULL`；真实父 Evidence ID 保持不变；连接启用 FK。

## 3. 迁移证据

`P0C_MIGRATION_EVIDENCE_20260910.json` 的总体结果为 PASS：

- 生成式 clean bootstrap：v0 → v12 通过。
- 生成式历史库：v9 → v12 通过，历史行保留。
- 故障注入：v9 → v10 的 schema 与 version 同时回滚。
- 三份冻结源库只在临时副本上迁移，源文件身份未变化。
- 冻结历史库、生产候选库、纯净候选库的既有 FK 债务分别为 43、35、7；这些数字是待修复事实，不因迁移可执行而被声明清零。

## 4. 测试结果

专项回归：`69 passed in 4.53s`，0 失败，0 跳过；后台线程泄漏为 0；受保护数据库身份在该次专项回归前后未变化。

全量测试：`4074 passed, 49 failed, 14 skipped, 1 error`。失败主要属于：历史缺失模块、依赖真实 Cookie、旧 AI Provider 状态断言、未初始化的生产数据字典、鉴权假设和旧 Adapter 契约。它们没有被删除或弱化，必须进入后续上线阻断清单。

## 5. 全量测试污染事件

首次全量测试证明旧测试/模块仍可绕过环境变量并写仓库数据库：

- 运行前 SHA-256：`7ae5533ca848c0b7801986f8980c5f396aae5ebeb41eebc21ae422a1c4c52828`
- 污染后 SHA-256：`c860c7503767cba64954fd94e5c0566ed7cb17dc536e0429dc03b6a3df1b7267`
- 新增污染对象：`schedule_decisions`（21 条测试记录）、`token_stat`（0 条）
- 两表在 P0-A 冻结纯净候选库中均不存在。
- 清理前可恢复备份：`D:\LUMENIS_REBUILD\P0C_TEST_POLLUTION_BEFORE_CLEANUP_20260910.db`
- 依据“纯测试污染可删除”授权，只移除上述两表；其他表和业务行未修改。
- 清理后：64 张表，`PRAGMA integrity_check=ok`，SHA-256 为 `fa10e00c9eb98995a643a47823e72b533ffc11763b22e9516bd13a6c40c1fa6f`。

SQLite 的物理页已发生变化，因此不能声称恢复到运行前字节哈希。新增硬门禁用于防止后续 pytest 再次发生同类污染。

## 6. AI 协作证据

- OpenCode 1.18.29 已调用。
- 智谱普通通道返回“身份验证失败”；已绑定的智谱 Coding Plan 通道随后返回“余额不足或无可用资源包”。未取得可采纳审查结论，也未伪造 ACCEPT。
- Ollama `qwen2.5-coder:7b-agent` 已对精简差异发起本地只读审查；输出未形成完整、稳定的结构化结论，进程已主动终止以避免继续浪费本地资源。因此最终验收仍以源码、专项测试和迁移证据为准。
- 两类审查均未读取 `.env`、API Key 或数据库内容，且未获得写权限。

## 7. 状态边界

- P0-C 源码实施：IMPLEMENTED。
- P0-C 专项测试：TESTED / VERIFIED。
- 全仓测试：NOT VERIFIED（49 failed + 1 error）。
- 真实页面、生产 Runtime 与 Release：本轮未验证，不得声明 OPERATING / RELEASED。
- 产品上线：BLOCKED，需继续完成历史能力找回、全量失败分类与上线 Gate。
