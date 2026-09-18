# LUMENIS P0-B 唯一 Runtime Identity 实施记录

状态：`IMPLEMENTED / TESTED / ISOLATED RUNTIME VERIFIED / PRODUCTION NOT APPROVED`

## 范围

本项复用既有 `runtime_preflight` 作为启动证明载体，引入唯一的 Runtime Identity 生成器，并由根健康接口、LUMENIS Foundation 健康接口、API 健康接口和受控 Attestation 接口消费同一份进程级缓存快照。

## 身份字段

- Release：`release_id`、`release_state`、Release Manifest 摘要与匹配状态；
- Source：Commit、Git tree digest、branch、tracked dirty 状态；
- Product：LUMENIS service namespace/name/version、product mode、profile digest；
- Database：路径身份摘要、Schema 摘要、SQLite schema/user version；
- Runtime：instance id、启动时间、配置的 worker set；
- Security：公共健康接口只返回最小字段，完整接口不返回绝对数据库路径或凭据。

## 明确边界

- 不把 Manifest 文件存在当作验证通过；Commit 与 tree digest 必须同时匹配。
- 未提供经过验证的 Manifest 时，状态只能是 `UNRELEASED` 或 `DECLARED_UNVERIFIED`。
- 不逐请求计算实时数据库内容哈希；数据库内容变化属于后续 Evidence/Checkpoint，不属于服务身份。
- 本项不选择生产数据库、不启动采集、不迁移数据、不修改 Production Truth。

## 待验收

### 已完成

- Runtime Identity 与 Preflight 定向测试通过；
- 独立 8294 Runtime 使用临时数据库启动成功，`--no-scheduler`；
- `/healthz` 与 `/lumenis/healthz` 返回同一 instance；
- `/api/runtime/attestation` 匿名访问 401，受控访问 200；
- 未返回绝对数据库路径；
- 候选数据库执行前后 SHA-256 一致；
- 隔离 Runtime 已停止。
- P0-B 最终安全测试集 `53/53 PASS`，无后台线程泄漏；强制临时数据库后候选数据库 SHA-256 前后一致。
- 候选提交后已从干净 Git tree 生成源码树外 Manifest，强制 Gate 返回 `MANIFEST_VERIFIED`；Commit 与 tree digest 匹配，`source_dirty=false`。
- 上述提交后终验作为外部 Runtime Evidence 保存，不写回同一源码提交，避免修改 Git tree 后使证明自失效。

### 测试隔离事件

扩大邻接回归时，既有 `test_osai_boundary_audit.py` 在进程内导入 `app.py`；而 `app.py` 导入阶段调用 `db.init_db()`，测试没有先强制设置临时 `ZBC_DB_PATH`。因此清洁仓候选数据库 SHA-256 从隔离 Runtime 验证后的 `594DFBFE...` 变化为 `7AE5533C...`。

只读对比 P0-A 冻结备份后，当前可见行数差异仍为此前记录的：`ai_call_logs 9→15`、`auth_recovery_tasks 0→2`、`schedule_decisions 0→21`；没有发现本轮新增行数，但因缺少测试前数据库副本，不能证明没有字段级幂等更新。未执行覆盖、恢复、删除或清空。该事实进入 P0-C 测试隔离 Gate，后续 P0-B 回归只允许显式临时数据库。

### 尚未满足的生产条件

- 首轮预提交验证诚实显示 `source_dirty=true`；提交后验证已转为 `MANIFEST_VERIFIED`，但它只证明本候选提交，不等于生产发布批准；
- P0-A 唯一生产源码/数据库人工决策尚未签署；
- 既有全量测试仍存在默认数据库写入风险，必须在 P0-C 收敛；
- 因此本项不得声明 `RELEASED` 或 `OPERATING`。

## 研究与交叉复核

- 设计参考 SLSA Build Provenance、NIST SSDF PS.2/PS.3 与 OpenTelemetry service/deployment identity；这些标准只用于校准，不替代本项目证据。
- 本地 Ollama 已完成不出机的抽象设计复核；其“防止 Attestation 泄露/伪造、验证缓存一致性”建议已纳入测试。
- OpenCode/智谱源码复核因私有源码外发安全审批被拒绝，本项没有绕过，也没有伪报调用成功；待用户明确授权具体源码可发送给智谱后再补外部复核。
