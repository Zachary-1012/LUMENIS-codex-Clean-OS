# LUMENIS Baseline Decision Record · P0-A

Decision ID：`LUMENIS-BDR-P0A-20260909-01`

状态：`PROPOSED / HUMAN APPROVAL REQUIRED`

## 决策问题

后续重建必须明确唯一源码起点、唯一生产数据迁移输入和可恢复点，不能凭目录名称或页面可访问性选择。

## 推荐决策

| 决策项 | 推荐 | 理由 |
|---|---|---|
| Canonical source | 私密纯净仓 `LUMENIS-codex-Clean-OS`，冻结 HEAD `f57a45c...` 后在安全分支继续 | 它具有完整版本血缘；原工作区有大量变更；8201/8202 均非已验证 Release |
| Production data migration input | 8201 的在线备份 `05-Taikoo-monitor-new-monitor.db` | 它是冻结时唯一有真实活跃业务数据且与当前运行链关联的候选；只能作为迁移输入，不能直接成为 Clean DB |
| Historical reconciliation input | original `data/monitor.db` 与 8201 staging 副本 | 两者表结构、FK 违规和数据量不同，需在 P0-C 做逐表归属与差异决策 |
| Rollback point | `D:\LUMENIS_REBUILD\P0A_BASELINE_20260909_1040` | 11 份 SQLite 一致性副本全部 integrity ok，且有独立 SHA-256 清单 |
| Runtime policy | 8201/8202 保持观察态，不覆盖、不关闭、不晋级 | P0-B 尚未建立可自证 Release Identity |

## 明确排除

- 不把 8201 或 8202 直接宣布为纯净版本。
- 不把便携包的单表数据库当生产数据。
- 不从原工作区 2,824 条状态记录中自动挑选或覆盖文件。
- 不在 P0-C 前对任何生产候选 DB 执行 Migration。
- 不自动 merge、deploy 或切换生产 Runtime。

## 批准栏

批准人：`PENDING`

批准时间：`PENDING`

批准证据：`PENDING`

批准方式：用户必须明确确认上述 Canonical source、Production data migration input 和 Rollback point；“文件存在”“测试通过”或 Agent 建议不能代替人工批准。
