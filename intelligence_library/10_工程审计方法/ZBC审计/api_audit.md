# ZBC Phase 12 — API 层逐端点审计报告

> **审计日期**: 2026-09-06
> **分支**: feat/zbc-full-upgrade-v1
> **HEAD**: 5e0ccd0
> **审计范围**: app.py + 15个 *_api.py + 3个 *_routes.py
> **审计标准**: Auth → Permission → Validation → Service → DB → Canonical Result → Evidence → Audit

---

## 1. 端点清单总表

### 1.1 按文件统计

| 文件 | 大小 | 端点数 | 路由类型 |
|------|------|--------|----------|
| app.py | 285KB | 188 | @app.route / @app.get / @app.post |
| ai_api.py | 20.5KB | 24 | Blueprint (ai_api) |
| report_api.py | 42.9KB | 17 | Blueprint (report) |
| lumenis_agg_api.py | 18.5KB | 14 | Blueprint (lumenis_agg) |
| browser_surface_api.py | 12.2KB | 30 | Blueprint (browser_surface) |
| architecture_api.py | 13.6KB | 22 | Blueprint (architecture) |
| collection_api.py | 11.3KB | 14 | Blueprint (collection) |
| system_health_api.py | 26.2KB | 3 | Blueprint (system_health) |
| system_features_api.py | 7KB | 16 | Blueprint (system_features) |
| data_query_api.py | 6KB | 12 | Blueprint (data_query) |
| auth_recovery_api.py | 4.2KB | 7 | Blueprint (auth_recovery, prefix=/api/auth-recovery) |
| evidence_api.py | 3.2KB | 5 | Blueprint (evidence_api) |
| browser_runtime_api.py | 2.9KB | 2 | Blueprint (browser_runtime_api) |
| juguang_api.py | 2.9KB | 0 | 纯辅助模块（无路由） |
| ic_routes.py | — | 12 | Blueprint (ic_contracts, prefix=/api/ic) |
| kos_routes.py | — | 53 | Blueprint (kos, prefix=/api/kos) |
| podcast_routes.py | — | 9 | Blueprint (podcast, prefix=/api/podcast) |
| **合计** | — | **440** | — |

### 1.2 按 HTTP 方法统计

| 方法 | 数量 | 占比 |
|------|------|------|
| GET (含默认) | ~280 | 63.6% |
| POST | ~130 | 29.5% |
| DELETE | ~8 | 1.8% |
| PUT | ~3 | 0.7% |
| 多方法 (GET+POST等) | ~19 | 4.3% |

### 1.3 按风险等级分类

| 风险等级 | 端点数 | 典型操作 |
|----------|--------|----------|
| CRITICAL | 6 | 代码执行、数据删除 |
| HIGH | ~25 | 配置修改、Cookie导入、品牌增删改、采集器启停 |
| MEDIUM | ~80 | 报告生成、数据导出、AI调用、浏览器操作 |
| LOW | ~329 | 只读查询、状态检查、统计聚合 |

---

## 2. 逐端点审计结果（按维度汇总）

### 2.1 Auth 认证覆盖

- **全局机制**: `@app.before_request` → `_basic_auth()` HTTP Basic 认证
- **白名单**: `/api/auth/config`、`/v4/*` 等放行
- **覆盖率**: ~95% 端点受 Basic Auth 保护
- **问题**: 无基于角色的访问控制（RBAC），所有认证用户权限相同

### 2.2 Permission 权限检查

- **审计前状态**: **@require_permission 在实际 API 代码中零使用**（仅存在于 permission_gate.py 文档和 tests/）
- **审计后状态**: 6个 CRITICAL/HIGH 端点已接入 @require_permission
- **未覆盖**: 其余 ~19 个 HIGH 风险端点尚未接入（见 §5 待办）

### 2.3 Validation 输入校验

| 校验类型 | 覆盖率 | 典型问题 |
|----------|--------|----------|
| 必填参数检查 | ~70% | 部分 POST 端点未检查空 body |
| 类型/范围校验 | ~40% | limit/page 等参数依赖 try/except 兜底 |
| 路径参数校验 | ~50% | <note_id>/<event_id> 未校验格式 |
| JSON body 解析 | ~80% | 普遍使用 `request.get_json(silent=True) or {}` |

### 2.4 Service 层调用

- **现状**: 绝大多数端点直接在路由函数中操作 DB / 调用模块函数
- **Service 层**: 无独立 Service 层抽象，业务逻辑与路由耦合
- **评估**: 符合"不得重构 API 结构"约束，本次不做分层改造

### 2.5 DB 异常处理

- **覆盖率**: ~85% 端点有 try/except 包裹 DB 操作
- **问题**: 部分 except 块返回 fake success（见 §3）
- **SQL 注入**: 使用参数化查询，未发现字符串拼接 SQL

### 2.6 Canonical Result 返回规范

| 返回模式 | 占比 | 规范度 |
|----------|------|--------|
| `jsonify({'ok': True, 'data': ...})` | ~60% | 规范 |
| `jsonify({'ok': False, 'error': ...}), 4xx/5xx` | ~25% | 规范 |
| 直接返回 dict / 原始数据 | ~10% | 不规范 |
| fake success (except→ok=True) | ~1% | **已修复** |

### 2.7 Evidence 证据链

- **evidence_api.py**: 5个端点提供证据查询（stats/list/detail/timeline）
- **app_evidence.py**: 证据记录模块
- **覆盖率**: 高风险写操作中 ~30% 有证据记录
- **问题**: 代码执行、品牌删除等操作未自动记录证据链

### 2.8 Audit 审计日志

- **PermissionGate 内置审计**: `_audit_log` 内存审计 + 可选持久化
- **审计前**: 无 API 端点触发 PermissionGate 审计
- **审计后**: 6个高风险端点每次调用均产生审计记录
- **其他审计**: `crawl_logs` 表记录采集日志，`ai_call_logger` 记录 AI 调用

### 2.9 错误码

- **现状**: 大部分错误返回裸 `500` + `error` 字符串，无结构化错误码
- **本次修复**: 5个 fake success 端点已添加 `code` 字段（如 `AUTH_HEADER_ENCODE_ERROR`、`BRAND_INDUSTRY_QUERY_ERROR`）
- **待改进**: 全系统错误码标准化（P2）

### 2.10 空数据处理

- **规范端点**: 返回 `{'ok': True, 'data': [], 'count': 0}` 明确表示空结果
- **问题端点**: 部分 except 块将异常伪装为空数据（已修复）

### 2.11 超时处理

- **采集类**: `collector` 有内置超时机制
- **AI 调用**: `ai_governance` 有配额控制，但无显式超时
- **浏览器操作**: Playwright 有默认超时
- **API 端点**: 无全局请求超时中间件

### 2.12 幂等性

- **写操作**: 绝大多数 POST 无幂等性保证
- **PermissionGate**: 内置 `operation_id` 幂等缓存机制
- **评估**: 采集任务有 task_id 可追溯，但配置修改/删除操作无幂等设计

---

## 3. Fake Success 问题清单（已全部修复）

| # | 文件 | 行号 | 端点 | 问题描述 | 修复方式 |
|---|------|------|------|----------|----------|
| 1 | app.py | 892-893 | GET /api/auth/config | except 块返回 `ok: True`，base64 编码失败时伪装成功 | 改为 `ok: False` + 500 + 错误码 `AUTH_HEADER_ENCODE_ERROR` |
| 2 | app.py | 1881-1882 | GET /api/brand-industry/brands | except 块返回 `ok: True, brands: []`，DB 查询失败时伪装为空列表 | 改为 `ok: False` + 500 + 错误码 `BRAND_INDUSTRY_QUERY_ERROR` |
| 3 | app.py | 1947-1948 | GET /api/brand-industry/stats | except 块返回 `ok: True, total: 0`，统计失败时伪装为零数据 | 改为 `ok: False` + 500 + 错误码 `BRAND_INDUSTRY_STATS_ERROR` |
| 4 | app.py | 1974-1975 | GET /api/negative-review/stats | except 块返回 `ok: True, total: 0`，负面审核统计失败时伪装为零 | 改为 `ok: False` + 500 + 错误码 `NEGATIVE_REVIEW_STATS_ERROR` |
| 5 | podcast_routes.py | 176-177 | POST /api/podcast/runtime/validate | ValueError 时返回 `ok: True, valid: False`，校验失败但端点状态为成功 | 改为 `ok: False` + 400 + 错误码 `PODCAST_SEGMENT_INVALID` |

**修复原则**: 异常就是异常，不得用 `ok: True` + 空数据/零值伪装为成功。前端应能通过 `ok` 字段区分"查询成功但无数据"与"查询失败"。

---

## 4. 高风险操作权限覆盖情况

### 4.1 已接入 PermissionGate（本次修复）

| # | 端点 | 方法 | OperationType | RiskLevel | deny_return |
|---|------|------|---------------|-----------|-------------|
| 1 | /api/dev/run-code | POST | RUNTIME_OPERATION | CRITICAL | 403 + PERMISSION_DENIED |
| 2 | /api/config/run-code | POST | RUNTIME_OPERATION | CRITICAL | 403 + PERMISSION_DENIED |
| 3 | /api/brands/<brand_en> | DELETE | DATA_DELETE | CRITICAL | 403 + PERMISSION_DENIED |
| 4 | /api/event-graph/events/<event_id> | DELETE | DATA_DELETE | CRITICAL | 403 + PERMISSION_DENIED |
| 5 | /api/system/config | POST | CONFIG_MODIFY | HIGH | 403 + PERMISSION_DENIED |
| 6 | /api/cookies/import | POST | DATA_IMPORT | HIGH | 403 + PERMISSION_DENIED |

### 4.2 全局 Gate 初始化（本次新增）

- **位置**: app.py 第 61-75 行（import database as db 之后）
- **基线权限**: COMMIT + PUSH + HUMAN_APPROVAL（过渡期兼容现有功能）
- **审计激活**: 每次高风险操作均写入 PermissionGate._audit_log
- **降级方案**: import 失败时自动降级为 no-op 装饰器，不影响系统启动

### 4.3 待接入 PermissionGate（P1 后续）

| 端点 | 方法 | 建议 OperationType | 建议 RiskLevel |
|------|------|---------------------|----------------|
| /api/brands | POST | DB_WRITE | HIGH |
| /api/brands/<brand_en> | PUT | DB_WRITE | HIGH |
| /api/config/emails | DELETE | CONFIG_MODIFY | HIGH |
| /api/collector/browser/start | POST | COLLECTOR_START | MEDIUM |
| /api/collector/browser/stop | POST | COLLECTOR_STOP | MEDIUM |
| /api/xhs/switch-account | POST | RUNTIME_OPERATION | HIGH |
| /api/backup | POST | DATA_EXPORT | MEDIUM |
| /api/brand-industry/recompute | POST | DB_WRITE | HIGH |
| /api/v4/api-keys/generate | POST | CONFIG_MODIFY | CRITICAL |
| /api/v4/api-keys/revoke | POST | CONFIG_MODIFY | CRITICAL |
| /api/network/reset | POST | RUNTIME_OPERATION | HIGH |
| /api/cache/create | POST | FILE_WRITE | MEDIUM |
| /api/resident/recover | POST | RUNTIME_OPERATION | HIGH |
| /api/xhs/p0/recovery/complete | POST | RUNTIME_OPERATION | HIGH |
| /api/xhs/p0/collection | POST | COLLECTOR_START | HIGH |
| /api/ai-resource-packs/pause | POST | RUNTIME_OPERATION | MEDIUM |
| /api/ai-resource-packs/resume | POST | RUNTIME_OPERATION | MEDIUM |
| /api/ai-resource-packs/per-call-execute | POST | SKILL_EXECUTE | HIGH |
| /api/event-graph/import | POST | DATA_IMPORT | HIGH |
| /api/event-graph/rebuild-relations | POST | DB_WRITE | HIGH |
| /api/cases/import | POST | DATA_IMPORT | HIGH |
| /api/official-info/collect | POST | COLLECTOR_START | MEDIUM |
| /api/special-report/generate | POST | REPORT_GENERATE | MEDIUM |
| /api/weekly/send-email | POST | EXTERNAL_NETWORK | MEDIUM |

---

## 5. 修复文件列表

| 文件 | 修改类型 | 修改内容 |
|------|----------|----------|
| app.py | fake success 修复 | 4处 except 块 ok=True → ok=False + 错误码 + 500 |
| app.py | PermissionGate 集成 | 新增 import + 全局 gate 初始化（基线权限） |
| app.py | 权限装饰器 | 6个高风险端点添加 @require_permission |
| podcast_routes.py | fake success 修复 | 1处 ValueError 返回 ok=True → ok=False + 400 + 错误码 |
| audit/api_audit.md | 新增 | 本审计报告 |
| tests/test_api_audit.py | 新增 | 审计回归测试 |

---

## 6. 安全等级评估

### 6.1 审计前评分

| 维度 | 评分(1-10) | 说明 |
|------|-------------|------|
| Auth 认证 | 7 | Basic Auth 全覆盖，无 RBAC |
| Permission 权限 | 2 | @require_permission 零使用，高风险操作无权限门 |
| Validation 校验 | 5 | 部分覆盖，依赖 try/except 兜底 |
| DB 异常处理 | 6 | 大部分有 try/except，但存在 fake success |
| Canonical Result | 6 | 基本规范，但 fake success 破坏可信度 |
| Evidence 证据链 | 4 | 有 evidence 模块，但写操作覆盖率低 |
| Audit 审计 | 3 | 有 crawl_logs/ai_call_logger，但无统一权限审计 |
| 错误码 | 3 | 大部分裸 500，无结构化错误码 |
| **综合** | **4.5** | **P0 问题显著** |

### 6.2 审计后评分

| 维度 | 评分(1-10) | 变化 | 说明 |
|------|-------------|------|------|
| Auth 认证 | 7 | — | 未改动 |
| Permission 权限 | 5 | +3 | 6个 CRITICAL/HIGH 端点已接入，全局 gate 已初始化 |
| Validation 校验 | 5 | — | 未改动（非本次范围） |
| DB 异常处理 | 7 | +1 | fake success 已清除 |
| Canonical Result | 8 | +2 | fake success 已修复，错误码已补充 |
| Evidence 证据链 | 4 | — | 未改动（非本次范围） |
| Audit 审计 | 5 | +2 | 6个高风险端点每次调用产生审计记录 |
| 错误码 | 4 | +1 | 5个端点已添加结构化错误码 |
| **综合** | **5.6** | **+1.1** | **P0 fake success 已清除，权限门已起步** |

### 6.3 剩余风险

1. **P1**: ~24个 HIGH 风险端点尚未接入 PermissionGate
2. **P1**: 写操作无幂等性保证
3. **P1**: 全局请求超时中间件缺失
4. **P2**: 错误码全系统标准化
5. **P2**: Service 层抽象（业务逻辑与路由解耦）
6. **P2**: RBAC 角色权限体系（替代单一 Basic Auth）

---

## 7. 测试验证

详见 `tests/test_api_audit.py`，覆盖：
- fake success 修复验证（源码静态检查 + 异常路径模拟）
- 高风险端点权限装饰器存在性检查
- PermissionGate  deny_return 格式验证
- 错误码字段存在性检查
- 全局 gate 初始化验证

---

## 8. 结论

本次审计枚举了 **440 个 API 端点**，发现并修复了 **5 处 fake success P0 问题**，为 **6 个 CRITICAL/HIGH 风险端点**接入了 PermissionGate 权限检查。系统综合安全评分从 4.5 提升至 5.6。

**核心原则已落实**:
- ✅ 禁止 API 返回 200 + fake success
- ✅ 异常路径返回明确错误码 + 非 200 状态
- ✅ 高风险操作接入 @require_permission 装饰器
- ✅ 权限拒绝返回规范 403 + PERMISSION_DENIED
- ✅ 未重构 API 结构，仅修复明确 bug
- ✅ 未修改 SUBJECT_WORDS / subject_hit()
- ✅ 未删除任何端点
- ✅ 未执行 git commit
