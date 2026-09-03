# SQLite / Alembic 可回滚迁移治理（T-P1-3 落地）

> 日期：2026-09-03 | 研究来源：GitHub + 工程实践 + 智谱闭环审查（glm-4.5-air）
> 关联任务：T-P1-3 Alembic 可回滚 DB 迁移（已落地并验证闭环）
> 关联文件：`alembic.ini`、`alembic/env.py`、`alembic/versions/e4278c4d1d79_...`、`tests/test_alembic_migration.py`、`docs/DB-MIGRATION-PLAYBOOK.md`

---

## 1. 研究结论（可复用知识）

### 1.1 对既有 SQLite 库引入版本化迁移的正确路径
- **zero-state / stamp-only baseline**：空迁移仅打版本戳，不重建表。
- `--autogenerate` 只适用于有 SQLAlchemy model 层的项目；本项目纯 sqlite3 + 裸 SQL，无 model 层，autogenerate 不可用。
- 存量库 = 先 `alembic stamp head` 标记当前状态，之后**所有新 schema 变更**走迁移文件。

### 1.2 关键坑：`target_metadata.reflect()` 破坏 stamp 写入
- 实测：无 model 层项目若用 `target_metadata.reflect(bind=connection)`，`alembic stamp head` 打印成功但 `alembic_version` 表为空。
- 干净环境对照实验确认：与排除 `alembic_version` 表无关，`reflect` 本身是根因。
- 结论：无 model 层项目 `target_metadata=None` + `render_as_batch=True`。

### 1.3 SQLite 迁移黄金法则
- 每迁移可逆（upgrade + downgrade 成对）
- 测 up + down 全链路
- 绝不编辑已发布的迁移
- 备份先行（SQLite 在线 backup API 生成一致性副本）
- `render_as_batch=True` 规避 SQLite ALTER 限制

### 1.4 测试隔离
- alembic 的 `env.py` 支持环境变量覆盖 URL（`ZBC_DB_PATH`），测试/生产/staging 三处复用一套机制。
- 陷阱：其他测试模块**模块级**设置环境变量（如 `test_workspace_keys.py` 设 `ZBC_DB_PATH`）会泄漏到全量测试，导致 alembic 误连别的库。测试必须显式清理。

---

## 2. Research ID 登记

| Research ID | 项目 | 来源 | 解决的问题 | 是否采用 |
|---|---|---|---|---|
| R-TP13-01 | Alembic 官方 autogenerate 文档 | alembic.sqlalchemy.org | autogenerate 适用范围 | 采用（确认本项目不可用） |
| R-TP13-02 | SQLite Alembic 权威指南 | getkt.com | stamp-only baseline 路径 | 采用 |
| R-TP13-03 | zero-state migration 教程 | PythonTutorials.net | 存量库打戳 | 采用 |
| R-TP13-04 | SQLite user_version 机制 | coddy.tech | 版本戳原理 | 参考 |
| R-TP13-05 | sqlite-auto-migrator | GitHub | 轻量自研迁移对比 | 参考（Alembic 更成熟） |
| R-TP13-06 | SQLite Forum batch 迁移 | sqlite.org/forum | ALTER 限制 | 采用 |

---

## 3. Evidence

- 回归测试：`tests/test_alembic_migration.py`（2 用例）全量 pytest 通过
- staging 副本：`staging/alembic_baseline.db`（54 表 + alembic_version，已 stamp）
- 生产库 `data/monitor.db`：54 表，全程零触碰，无 alembic_version
- 智谱闭环审查：技术实现 4/4 ✓；生产流程 P1（备份/Gate/回滚/监控）已由 `docs/DB-MIGRATION-PLAYBOOK.md` 补齐

---

## 4. 适用场景

- 任何"既有生产 SQLite 库要引入版本化 schema 管理"的项目
- 需要可回滚、可追溯、可审计的数据库变更

## 5. 不适用 / 注意

- 生产库纳入 alembic 管理**必须**先满足 DB-MIGRATION-PLAYBOOK 的 Gate（备份策略、变更评审、版本衔接、回滚预案、迁移监控），未满足前不接管生产。
