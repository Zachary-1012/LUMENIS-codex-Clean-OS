# 序境｜文件清理审计清单

> 状态：AUDIT / NO-BLIND-DELETE
> 日期：2026-09-04

## 处理规则

1. 生产源码、配置、迁移、测试与运行依赖：KEEP，除非依赖审计证明安全。
2. 当前唯一有效规范：进入 `序境/` Canonical 体系。
3. 历史审计材料：优先归档，不因“旧”直接删除。
4. 重复、无引用、无运行时依赖且已被新 Canonical 文档完整替代：可 DELETE。
5. 无法证明安全删除：交由执行端二次确认，不在此阶段盲删。
6. 删除必须记录 path、reason、reference check、commit。

## 已识别的高概率历史文档群

以下类型应进入逐项引用检查：

- 根目录编号式 inventory / reconciliation / matrix 文档
- 日期型 AUDIT_HANDOFF / EXECUTION_HANDOFF
- 日期型 WORK_LOG
- 已被 `序境/00-GOVERNANCE`、`序境/08-AUDIT` 替代的阶段性规范
- 已废止架构名称相关文档

## 禁止直接删除

- README / VERSION / AGENTS 等当前治理入口
- 生产代码、测试、配置、数据库迁移
- Core 生产业务真相相关实现
- SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit() 相关资产
- 当前 CI/CD、Runtime、Health、Recovery
- 当前 Adapter / Collector
- 当前双库 Contract

## 豆包执行要求

删除前必须：

`grep/reference scan → import scan → runtime scan → test → diff review → delete → test → commit`

如果任何一步无法证明安全，标记 `HUMAN_REVIEW`，不要删除。

---

## 六、遗留多页面版 templates/（LEGACY · 不删除）

> 运行时主入口为 SPA `static/index.html`（序境）。`templates/` 为历史多页面版（base/events/notes/report），被 git 追踪但不被 app.py 渲染（无 render_template 引用）。**LEGACY 保留**，不改不删（git 历史锚点），命名不迁移。

| Path | 判定 | 依据 |
|---|---|---|
| templates/base.html | LEGACY | 历史版基模板，SPA 替代 |
| templates/index.html | LEGACY | 历史版首页 |
| templates/events.html | LEGACY | 历史版事件页 |
| templates/notes.html | LEGACY | 历史版笔记页 |
| templates/report.html | LEGACY | 历史版报告页 |
