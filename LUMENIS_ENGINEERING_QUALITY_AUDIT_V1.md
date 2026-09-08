# LUMENIS 工程质量审计 V1

状态：第 10 类工程质量审计交付物
审计范围：API Contract、前后端一致性、数据库迁移、安全边界、依赖、性能、测试和 CI
结论：`ENGINEERING ASSETS EXIST / RELEASE GATE FAIL`

## 1. 事实摘要

| 项目 | 实测事实 |
|---|---|
| Flask 路由规则 | 813（含 static） |
| OpenAPI 非 static 规则 | 812 |
| OpenAPI 去重路径 | 774 |
| OpenAPI 操作 | 820 |
| Contract 文件 | 9 |
| Python requirements 行数 | 63 |
| Node lockfile | `package-lock.json` v3，4 个 package 节点 |
| GitHub Actions | `.github/workflows/platform-verify.yml` |
| 工程专项测试 | 51 项通过 |
| API smoke/audit/双域测试 | 61 项通过 |
| Security scan | FAIL，46 个规则命中 |
| 当前运行基线 | 8202 使用 `D:\Z-Brand-Core_MAIN_AUDIT`，不是清洁仓库 |

## 2. API Contract

### 已有能力

`openapi_spec.py` 从 Flask `url_map` 自动反射路由，生成 OpenAPI 3.0.3 和路由矩阵，避免手工漏列路径。`api_dual_domain.py` 为 CTH、ZBMP、SYSTEM 提供 `{success, data, error, domain_id, product_id}` 响应格式和域上下文。

### 关键问题

1. 当前 OpenAPI 主要是路由清单，不是完整业务契约：没有逐端点 request body、response schema、错误结构、状态码、权限、幂等和 Evidence 定义。
2. `auth_for()` 仅把 `/healthz` 标为公开，其余简化为 Basic/v4；真实 `app.py` 有更大的公开/旁路集合，因此生成规范与真实认证策略不完全一致。
3. 813 条规则、774 条路径说明 API 面积很大；同一业务能力仍有 legacy、v2、v4、domain、viz、report 等多种路径。
4. `app.py` 与 `viz_api.py` 都注册部分 `/api/viz/*` 路径，需要确认路由优先级和唯一实现。
5. 隔离导入时出现 `evidence_api` 蓝图名称重复注册；异常被记录但应用继续启动，可能造成路由是否生效依赖注册顺序。
6. API 返回格式并未统一：部分使用 `success`，部分使用 `ok`，部分直接返回业务字段；前端需要维护多种错误和空态判断。

结论：API inventory 已有，Canonical API Contract 未完成。

## 3. 前后端一致性

### 已验证

- 前端基础、Domain Context、Viz API 和 API smoke 测试通过。
- `/api/viz/*` 具备 Provider → View Model → Truth Table 的标准设计。
- CTH、BMP、SYSTEM 页面路由真实存在。

### 未闭环

- 55 个模板与 813 条路由尚未形成逐页 Page → API → Schema → DB → Evidence 矩阵。
- 前端仍使用 `ZBMP` 历史命名；目标正式产品为 BMP / 序境·品牌市场。
- 当前页面数据来自 MAIN_AUDIT 空数据库，无法作为清洁仓库前后端一致性的生产证据。
- 旧 API、Domain API 和 Viz API 并行，尚未证明每个页面只消费一个 canonical endpoint。

结论：模块测试通过，生产一致性未验证。

## 4. 数据库迁移

### 已有能力

- `database_migrations.py` 当前版本为 12。
- 支持状态、迁移、回滚、备份和信息查询。
- Alembic 目录、SQL migrations 和传统 Python migration 同时存在。

### 已确认问题

1. `app.py` 先执行 `db.init_db()` 和 migration，再初始化 Evidence/Canonical 专用表。
2. 清洁空库实测 v9→v10 访问不存在的 `canonical_data` 并回滚。
3. 隔离导入再次出现 migration non-fatal warning；编码输出异常可影响迁移结果表达。
4. 工作区数据库 `integrity_check=ok`，但 `foreign_key_check=43`。
5. 数据库测试有 4 项失败：清洁测试库缺少 notes/events 和其他要求表。
6. Alembic、传统 migration、模块自建表之间没有唯一 schema owner。

结论：迁移资产存在，clean bootstrap、upgrade 和 production rollback 未同时通过。

## 5. 安全边界

### 已有能力

- Basic/v4 Auth、PermissionGate、SecurityBoundary、Agent Boundary、Action Firewall、CSRF、rate limit、secret scanner 和生产 Evidence Contract 均存在。
- Agent 生产数据库直接写入已实测拒绝。

### P0 风险

1. `/api/auth/config` 位于认证白名单，并在认证启用时返回完整 Basic Authorization header。它等价于把后端凭据交给任何可访问该端点的客户端，必须视为 P0 凭据暴露设计风险。
2. `app.py` 启动时为全局 PermissionGate 授予 COMMIT、PUSH、HUMAN_APPROVAL；需要证明这些权限不会被普通 HTTP/Agent 调用复用。
3. PermissionGate 写入旁路包含 `/api/developer/run`、`/api/config/run-code`、`/api/dev/run-code` 等高影响端点。即使仍受其他认证层保护，也违反最小旁路原则。
4. 多个 runtime、system、risk 状态接口在 Basic Auth 白名单，需逐项确认最小信息暴露。
5. 安全扫描报告 46 个命中并失败；其中包含检测规则自身、归档和测试样例，说明扫描结果需要分级和基线化，但不能因此忽略真实命中。

结论：控制构件丰富，但认证凭据端点和权限旁路使生产发布门禁失败。

## 6. 依赖与供应链

### Python

`requirements.txt` 主要使用 `>=` 下限，没有完整锁文件、hash 或已验证组合，清洁安装不可重复。当前已有 venv 执行 `pip check` 返回 `No broken requirements found`，只能证明当前环境内部依赖没有声明冲突，不能证明另一台机器安装结果一致。

### Node

`package-lock.json` 为 lockfile v3，根依赖为 Playwright；`package.json` 使用 `^1.62.1`，lockfile 可固定当前解析版本。当前打包环境只有 pnpm，pnpm audit 因无 `pnpm-lock.yaml` 无法执行；不能据此声明 Node 依赖安全或不安全。

### CI

GitHub Actions 使用 Python 3.11，但 compile、pytest、boundary check、asset scan 均设置 `continue-on-error: true`。因此语法、测试和边界失败仍可能让工作流呈现成功，无法作为 Release Gate。

结论：依赖可安装，供应链可重复性和阻断式 CI 未完成。

## 7. 性能

- `app.py` 集中注册大量 API 和初始化逻辑，隔离导入即加载大量模块并进行数据库初始化。
- 813 条路由增加启动、契约、权限和回归测试复杂度。
- 性能与系统测试通过，但没有本轮生产负载、并发写、SQLite 锁竞争、Collector 长时间运行、内存增长或 p95/p99 延迟证据。
- Runtime 当前 workers 为空，无法用现有服务证明生产吞吐。

结论：存在测试级性能资产，没有生产容量结论。

## 8. 测试事实

| 测试组 | 结果 |
|---|---|
| OpenAPI、Domain API、前端基础、Alembic、性能/系统 | 51 通过 |
| API smoke、API audit、双域 API | 61 通过 |
| Security scan | FAIL，并在收集阶段 `SystemExit(1)` |
| Database | 4 项失败 |
| Registry hardcoded path | 1 项失败 |
| Evidence/Canonical/Viz/Report | 既有专项测试通过 |

安全扫描模块在测试文件导入阶段直接退出，使同一 pytest 批次无法继续收集其他测试。应改为普通断言/测试结果，但本轮不修改代码。

API 三组补跑时 pytest 进程返回 61 项通过，但同时把受版本控制的 `audit/CONTENT_TEST_RESULTS.json` 从 30/30 改写为 27/30，并在产物内记录 `intelligence/library`、`intelligence/library/search`、`SEC-10 DB integrity` 失败。说明当前测试退出状态、内部审计状态与测试数据基线没有形成单一真相，且测试会污染工作树。本轮已恢复该测试副作用，未把它作为产品源码变更提交。

## 9. 优先级

### P0

1. 移除客户端可读取的 Basic 凭据返回设计，改为正常会话/令牌交换。
2. 收紧 PermissionGate 自动授权和高影响旁路。
3. 修复 clean bootstrap 与迁移顺序，建立唯一 schema owner。
4. 让 CI 的 compile、pytest、安全、边界检查成为阻断式 Gate。
5. 固定唯一运行仓库和数据库。
6. 消除测试对版本化审计产物的持久化副作用，并统一 pytest 退出状态与内部审计状态。

### P1

1. 建立逐端点 request/response/error/security/Evidence 契约。
2. 统一 `success/ok/status/error` 响应模型。
3. 建立 Page → API → DB → Evidence 消费矩阵。
4. 收敛重复 API、蓝图和 legacy 路径。
5. 建立锁定的 Python 依赖清单与供应链扫描。

### P2

1. 生产负载、长稳、锁竞争、故障注入与恢复测试。
2. API 版本退役和兼容窗口自动化。
3. 完整性能预算、SLO 和可观测性。

## 10. 七项验收

| 验收项 | 结果 |
|---|---|
| Source | PASS |
| Call Graph | PARTIAL |
| Data / API | FAIL |
| Frontend / Consumer | PARTIAL |
| Runtime | FAIL |
| Tests | PARTIAL |
| Production Evidence | FAIL |

第 10 类工程质量审计完成。当前代码具备大量生产化构件，但安全、迁移、CI、运行基线和 API 契约仍阻断发布，禁止声明 Production Ready。
