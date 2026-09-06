# 学习：SQLite/Alembic 可回滚迁移 + T-P1-3 闭环（2026-09-03）

> 来源：ZBC T-P1-3 落地 + 智谱闭环审查（glm-4.5-air）
> 关键词：stamp-only baseline / render_as_batch / 环境变量泄漏 / 生产 Gate

## 本轮学到什么

1. **存量 SQLite 库引入版本化迁移的正确姿势**：zero-state stamp-only baseline（空迁移打版本戳，不重建表）。`--autogenerate` 只适用于有 SQLAlchemy model 层的项目。

2. **关键坑**：无 model 层项目用 `target_metadata.reflect()` 会让 `alembic stamp` 版本写不进去（干净环境对照实验确认）。正确做法 `target_metadata=None` + `render_as_batch=True`。

3. **测试隔离陷阱**：别的测试模块模块级 `os.environ["ZBC_DB_PATH"]=...` 会泄漏到全量 pytest，导致 alembic 误连别的库。测试必须显式 `os.environ.pop("ZBC_DB_PATH", None)`。

4. **生产接入不是"代码写好就完"**：智谱审查指出代码闭环 4/4 正确，但生产接入缺备份/Gate/回滚/监控流程（P1）→ 已补 `docs/DB-MIGRATION-PLAYBOOK.md` 关闭。

## 对 Zachary 的启示

- 数据库变更必须"可逆 + 可追溯 + 有 Gate"，不因"能跑"就无流程上线。
- 测试隔离：环境变量、cwd、全局 sqlite 都可能被跨测试污染，写测试要防御性清理。
- 每次闭环都要有独立验证通道（本地测试 + 智谱第二意见），防"文档完成代码没完成"的假闭环。

## 产物

- ZBC: `alembic/`、`tests/test_alembic_migration.py`、`docs/DB-MIGRATION-PLAYBOOK.md`、`docs/learning/SQLITE-ALEMBIC-MIGRATION-20260903.md`
- Commit: `33e932c`
