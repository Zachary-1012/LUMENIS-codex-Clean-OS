# 序境 / LUMENIS SYSTEM Ops

SYSTEM Ops 是序境自己的本地运行与交付工作台，不是 TrendHub 的副本，也不与任何其他产品共享数据库、凭据或运行时。

## 真相与边界

- 健康总状态只复用既有 `/api/system/health/summary`，不建立第二套数据库/采集器/健康计算。
- `/system/ops` 是同源、响应式的人类可读入口；`/api/system/ops/*` 提供结构化结果。
- `POST /api/system/ops/costs` 与 `POST /api/system/ops/feedback` 不绕过 `PermissionGate`：在完整 app 中会经过既有统一写操作权限检查。
- 运行指标仅代表当前 Python 进程与受保护数据卷；不把宿主机 CPU、云账单、真实用户增长或外部可用性虚构成已采集数据。
- 成本默认是本地手工登记；未接入云账单时显示未接入，而不是 `$0`。
- 反馈在写入前对 Authorization/Bearer、Cookie、token/key/secret/password、查询参数和长 opaque 值脱敏。
- 不自动重启、部署、回滚、发布、删除或读取 Cookie/API Key。

## 使用

1. 按既有生产入口启动序境：`scripts/start_production.ps1`。
2. 登录后访问 `http://127.0.0.1:8201/system/ops`。
3. 查看既有 System Health、Supervisor、进程/数据卷、构建来源、成本和反馈；复制 SYSTEM Ops Brief 做人工决策。
4. 成本/反馈写入受 `ZBC_DATA_DIR/ops/creator_ops.json` 管理的本地运行数据，不触碰业务 Evidence、Canonical Data 或生产 DB 真相。

## 可选开源扩展

SYSTEM Ops 的字段保留 OpenTelemetry 可映射语义。需要集中 telemetry 时，可在独立受保护的运维环境选配 OpenTelemetry + SigNoz；需要独立外部探针时，可选 Uptime Kuma。它们不是本次提交的默认依赖或已配置能力，启用前必须按 `00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md` 完成许可证、安全、保留期、网络出口、告警与替代方案审查。

- <https://opentelemetry.io/docs/concepts/signals/metrics/>
- <https://github.com/SigNoz/signoz>
- <https://github.com/louislam/uptime-kuma>
