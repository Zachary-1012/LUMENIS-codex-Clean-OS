# DB Migration Playbook — 生产数据库可回滚迁移手册

> 关联任务：T-P1-3 Alembic 可回滚 DB 迁移（BACKLOG 落地）
> 关联文件：`alembic.ini`、`alembic/env.py`、`alembic/versions/`、`tests/test_alembic_migration.py`
> 状态：代码/测试闭环已验证 ✅｜生产接入流程（本文档）已补齐 ✅

---

## 0. 一句话

**对既有 SQLite 生产库引入 Alembic 版本化迁移的正确姿势 = zero-state / stamp-only baseline，绝不重建生产库。**

---

## 1. 已落地能力（真实状态）

| 能力 | 实现 | 验证方式 |
|---|---|---|
| alembic 1.19.1 | 已装 `.venv` | `pip show alembic` |
| baseline 迁移 | `alembic/versions/e4278c4d1d79_baseline...py`（空迁移 stamp-only） | `tests/test_alembic_migration.py::test_stamp_baseline_writes_version` |
| 环境变量覆盖 URL | `alembic/env.py` 读 `ZBC_DB_PATH` | 生产切换不改 ini |
| SQLite batch 模式 | `render_as_batch=True`（规避 ALTER 限制） | upgrade/downgrade 实测 |
| 回滚闭环 | upgrade 加列 → downgrade 回滚 → 数据行数不变 | `test_upgrade_then_downgrade_rollback` |
| 测试隔离 | 显式清除其他测试泄漏的 `ZBC_DB_PATH` | 全量 `pytest` 通过 |

生产库 `data/monitor.db` 全程**零触碰**（54 表，无 `alembic_version`）。

---

## 2. 关键设计决策（为什么这么做）

### 2.1 为什么是 stamp-only baseline，不用 `--autogenerate`？
- 本项目是**纯 sqlite3 + 裸 SQL**，无 SQLAlchemy model 层。
- `--autogenerate` 在没有 model 层时无法做增量 diff。
- 对**已有大量数据的库**，唯一安全路径是：先把当前状态"打上版本戳"（stamp），
  之后所有**新** schema 变更才走迁移文件。
- 好处：存量表一个不动，未来变更可追溯、可回滚。

### 2.2 为什么 `target_metadata` 必须是 `None`（不能 `reflect`）？
- 实测：`target_metadata.reflect(bind=connection)` 会导致 `alembic stamp head`
  虽然打印 `Running stamp_revision`，但 `alembic_version` 表**写不进去**（版本为空）。
- 干净环境对照实验确认：与是否排除 `alembic_version` 表无关，`reflect` 本身就是根因。
- 结论：无 model 层项目**不要用 reflection 模式**，`target_metadata=None` + batch 即可。

### 2.3 为什么 `ZBC_DB_PATH` 环境变量覆盖 URL？
- `alembic.ini` 里的 url 指向 staging 副本，**永远不作为生产默认值**。
- 生产切换时通过 `ZBC_DB_PATH` 指向目标库，ini 保持不变、可 git 跟踪。
- 测试也复用同一机制（指向临时库），一套机制三处复用。

### 2.4 为什么 `render_as_batch=True`？
- SQLite 不支持某些在线 DDL（如 drop column 的旧版本语义）。
- batch 模式通过"建新表→拷贝→改名"实现等价操作，是 SQLite 官方推荐做法。

---

## 3. 生产接入前置条件（Gate 清单）

> ⚠️ 以下为**生产库纳入 Alembic 管理之前必须完成**的流程控制。
> 未全部满足前，**不把生产库纳入 alembic 管理**（保持现状：业务代码 create-if-not-exist 不变）。

- [ ] **G1 备份策略**：迁移前必须用 SQLite 在线备份 API 生成一致性副本
      （参考 `staging/alembic_baseline.db` 的生成方式：`sqlite3.Connection.backup()`）。
      副本命名 `<库名>-<日期>-<commit>.db`，异地保存，验证可打开。
- [ ] **G2 变更 Gate**：任何 schema 变更必须：
      1) 先写迁移文件（upgrade + downgrade 成对）
      2) 在 staging 副本上跑 `upgrade` + `downgrade -1` 闭环
      3) 数据行数回归不变
      4) 通过 `tests/test_alembic_migration.py` 对应用例
      5) 走 release gate 评审后才允许对生产执行
- [ ] **G3 版本衔接**：生产库首次纳入管理时，`alembic stamp head`（只打戳，不重建）。
      之后所有变更只允许通过新迁移文件，**禁止手改生产 schema**。
- [ ] **G4 回滚预案**：每次升级记录 `before 版本` / `after 版本`。
      异常时 `alembic downgrade -1` 回退到上一版本；数据在迁移中任何时刻可恢复。
- [ ] **G5 迁移监控**：迁移日志落盘 + 版本号校验（`SELECT version_num FROM alembic_version`）
      与预期一致；迁移窗口内暂停写入（或确认应用层 create-if-not-exist 与新 schema 兼容）。

---

## 4. 常用命令

```bash
# 查看当前版本
alembic current

# 在 staging 副本上打 baseline 戳（首次，不重建表）
alembic -x db=staging/alembic_baseline.db stamp head

# 生成新迁移（手动编辑 upgrade/downgrade）
alembic revision -m "describe change"

# 升级到最新
alembic upgrade head

# 回滚一级
alembic downgrade -1

# 生产切换（示例——需先满足 Gate）
set ZBC_DB_PATH=D:\Taikoo-monitor-new\data\monitor.db
alembic current
alembic stamp head
```

---

## 5. 测试与 Evidence

- 回归测试：`tests/test_alembic_migration.py`（2 用例）
  - `test_stamp_baseline_writes_version`：验证 stamp 后 `alembic_version` 记录 baseline，表结构完整
  - `test_upgrade_then_downgrade_rollback`：验证加列 → 回滚 → 数据行数不变
- 运行：`pytest tests/test_alembic_migration.py -q`
- 全量回归：`pytest -q`（含本测试，全部通过）
- 真实 Evidence：
  - staging 副本 `staging/alembic_baseline.db`（54 表 + alembic_version，已 stamp）
  - 智谱闭环审查（glm-4.5-air）：技术实现 4/4 ✓，生产流程 P1 已由本文档补齐

---

## 6. 已知限制 / 未完成

- 生产库**尚未**纳入 alembic 管理（按 Gate 要求，需用户签字 + 备份策略落地后执行）。
- 无 SQLAlchemy model 层，`--autogenerate` 不可用（这是设计选择，非缺陷）。
- 首次生产 stamp 需停机/暂停写入窗口（或与 app 启动 create-if-not-exist 兼容性验证后执行）。

---

## 7. 关联

- BACKLOG：T-P1-3 Alembic 可回滚 DB 迁移
- 关联 Gap：GAP-13（生产切换走 Gate）
- 依赖：alembic>=1.19.1（requirements.txt 已登记）
