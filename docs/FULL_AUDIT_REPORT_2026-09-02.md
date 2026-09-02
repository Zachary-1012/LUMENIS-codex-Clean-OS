# Z-Brand-Core 全库审计报告 · 2026-09-02

> 审计依据：`AUDIT_HANDOFF_20260902_UNIFIED_RESOURCE.md` + `INGESTION_AND_TERMINOLOGY_STANDARD_20260902.md`
> 仓库：D:\Taikoo-monitor-new，VERSION 5.9.9，分支 main
> 审计范围：平台枚举、文件上传、知识库、Context Isolation、Style Profile、生产安全、Evidence 系统、8200 legacy

---

## 一、已执行修复（P0）

### 1.1 8200 legacy 实例根因修复 ✅

**问题**：8200 端口实例杀掉后反复复活。
**根因**：`auto_recovery.py` 被 `app.py:5505` 导入并启动 60s 后台监控，硬编码检查 `check_port(port=8200)`，发现不在线就调用 `fix_process_crash()` 用 `subprocess.Popen([python, 'app.py', '--port', '8200'])` 启动新实例。
**修复**：4 处硬编码 `8200` → `8201`（check_port 默认值、fix_process_crash 启动命令、验证、health_check）。
**验证**：进程树纯净，仅 8201+9222+9223，8200 彻底消失。
**提交**：`7b08df0` → rebase 后 `6409342`

### 1.2 平台枚举统一 ✅

**问题**：`source_platform` 有三种值混用——`rednote`（app.py:776）、`xiaohongshu`（database.py 多处）、`小红书`（app.py:3853 默认值）。违反标准要求的代码层统一枚举 `xhs`。
**修复（代码层）**：
- app.py：3 处（source_platform 值、默认值、verified notes）
- database.py：4 处（schema 默认值、note_data 默认值、fallback、stats）
**修复（数据库迁移）**：
- 957 行 notes 表数据：`xiaohongshu`(949) + `xiaohongshu-cdp`(8) → `xhs`
- 迁移前备份：`data/backups/before_source_platform_migration_20260902_182540.db`
- 迁移后验证：0 行非标准平台值
**提交**：`fa8ba82`

### 1.3 Evidence 系统 Phase 1 ✅

**问题**：`app_evidence_records` 表已存在但采集链和健康监控未使用；采集异常（验证码/300012/IP风险/登录失效）未落真实状态证据；当前 health 只存状态到 `data/resident_health.json`，不存采集证据。
**修复**：
1. **表结构扩展**：`app_evidence_records` 从 16 字段扩展到 43 字段，新增 27 列对齐 EVIDENCE-PATTERNS.md（project/product/feature_id/level/result/inputs/outputs/expected/actual/root_cause/resolution/account/duration_ms 等）
2. **新建 `evidence_store.py`**：统一 Evidence 写入/查询接口
   - `record_evidence()`：通用 Evidence 记录
   - `record_collection_evidence()`：采集任务 Evidence（强制规则：异常时 result=FAIL，禁止以 0 条充当结果）
   - `record_health_evidence()`：健康检查 Evidence（L1/L2/L3 级别映射）
   - `query_evidence()`：结构化查询（按 source/feature_id/level/result/account 过滤）
   - `get_stats()`：按 result/level/account/source 统计
   - `evidence_hash`：内容哈希用于去重和溯源
3. **集成到 resident_health.py**：新增 `check_account_with_evidence()` 包装函数，`check_all()` 现在每次健康检查都写一条 Evidence
4. **测试**：8/8 evidence_store 单元测试通过，14/14 resident_health 测试通过
5. **生产验证**：调用健康检查 API 后，数据库实际写入 8 条 Evidence 记录（2 PASS + 6 FAIL 重启过程），双账号全覆盖，actual 字段含完整健康详情
**提交**：`7ea03bf`

---

## 二、审计发现（待执行）

### 2.1 文件/媒体上传限制 ⚠️

**审计结果**：

| 上传入口 | 单/多文件 | 大小限制 | 扩展名白名单 | 数量限制 | 全局 MAX_CONTENT_LENGTH |
|---|---|---|---|---|---|
| app_evidence.py:323 | 单文件 | ❌ 无 | ❌ 无 | N/A | ❌ 无 |
| v4_upgrade/importer/service.py:29 | 单文件 | ✅ 50MB | ✅ 8种 | N/A | ❌ 无 |

**问题**：
1. `app_evidence.py` 无文件大小限制和扩展名白名单，存在安全风险
2. `importer` 限制 50MB，标准要求 500MB（差 10 倍）
3. 无 Flask 全局 `MAX_CONTENT_LENGTH` 配置
4. 无多文件批量上传入口（标准要求"标准上传 20 个/500MB"和"批量导入 30 个/500MB"）
5. 无文件夹路径绕过检查

**建议修复（P1）**：
1. app_evidence.py 增加大小限制（500MB）和扩展名白名单
2. importer max_file_size_mb 从 50 → 500
3. app.py 增加 `app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024`
4. 新增多文件批量上传 API（支持 20-30 个文件）

### 2.2 重复/私有知识库 ⚠️

**审计结果**：

| 知识库 | 存储位置 | 数据来源 | 与 Resource Library 关系 |
|---|---|---|---|
| brand_knowledge_base.py | SQLite (monitor.db) + JSON 备份 | 手动添加/采集 | 平行独立 |
| 全网舆情案例库 | SQLite (monitor.db) | 采集/AI生成 | 平行独立 |
| ai_learning_engine.py | JSON (learning_records) | AI 学习 | 平行独立 |

**问题**：
1. `brand_knowledge_base.py` 是独立的品牌营销知识库，有自己的 add/get/stats 接口，与 Resource Library 平行
2. 全网舆情案例库也是独立的知识存储
3. ai_learning_engine 的学习记录存储在 JSON 文件中
4. 这些知识库没有统一进入 Resource Pipeline（Ingestion→Validation→Normalization→Deduplication→Provenance→Evidence→Resource→Zachary Retrieval）

**建议修复（P1）**：
1. 评估 brand_knowledge_base 和案例库是否应迁移到统一 Resource Library
2. 如保留独立知识库，需明确其与 Resource Library 的边界和同步机制
3. ai_learning_engine 的学习记录应纳入 Evidence 系统

### 2.3 Zachary Context Isolation ⚪ N/A

**审计结果**：ZBC 中没有直接调用 Zachary/OSAI 的代码（无 API 调用、无 RPC、无消息队列）。Zachary 相关的都是文档注释、模块命名、前端 JS（zachary_robot.js）。
**结论**：当前架构下无跨系统调用，Context Isolation 不适用。未来 ZBC 调用 Zachary 时需携带明确的 product_context/tenant_context/task_context。

### 2.4 Style Profile 与生产规则隔离 ⚪ N/A

**审计结果**：ZBC 中无 style_profile/user_preference/personalization/writing_style 相关代码。
**结论**：当前未实现千人千篇的 Style Profile 功能，该项不适用。未来实现时需确保用户行为只用于表达层个性化（语气/节奏/长度等），不改变事实/业务规则/风险阈值/权限/安全策略/Runtime/Evidence。

### 2.5 生产安全 ⚪ N/A

**审计结果**：ZBC 中无 Zachary 直接修改核心业务逻辑/DB schema/权限/安全边界的代码（因为无跨系统调用）。
**结论**：当前架构下生产安全不适用。未来 Zachary 接入时需确保其无法直接修改核心业务逻辑/DB schema/权限/安全边界/Release Gate/生产阈值/关键 Runtime。

---

## 三、运行时状态验证

| 项目 | 状态 | 详情 |
|---|---|---|
| 8200 legacy | ✅ 已退役 | 根因修复，不再复活 |
| 8201 生产 | ✅ 健康 | v5.9.9，healthz ok |
| 9222 大陆驻场 | ✅ 在线 | XHS_CN_PRIMARY，登录态有效，70 cookies |
| 9223 香港驻场 | ✅ 在线 | XHS_RETINAUT，登录态有效，14 cookies |
| Evidence 写入 | ✅ 生效 | 8 条记录已落库，双账号全覆盖 |
| 平台枚举 | ✅ 统一 | 代码层 + DB 957 行全部 xhs |
| 测试 | ✅ 全过 | evidence 8/8，resident_health 14/14，agent_security 20/20 |

---

## 四、提交记录

| Commit | 说明 |
|---|---|
| `6409342` | 8200 根因修复（auto_recovery 硬编码端口） |
| `fa8ba82` | 平台枚举统一（source_platform → xhs） |
| `7ea03bf` | Evidence Store Phase 1（统一证据层 + 表扩展 + 健康监控集成） |

---

## 五、下一步建议（按优先级）

| 优先级 | 事项 | 说明 |
|---|---|---|
| P0 | Evidence Phase 2 | Evidence API + 前端 Dashboard 展示 |
| P1 | 文件上传限制修复 | app_evidence 增加大小/扩展名限制，importer 50→500MB，全局 MAX_CONTENT_LENGTH |
| P1 | 知识库收敛评估 | brand_knowledge_base / 案例库是否迁移到统一 Resource Library |
| P1 | 采集链 Evidence 集成 | 在 collector_v2 / collector_automation 中调用 record_collection_evidence |
| P2 | 真实"失效→弹扫码"演练 | 主动破坏登录态，验证全链路 |
| P2 | Zachary OS AI 内置浏览器 | CDP 截图流前端渲染 / noVNC / iframe |
| P2 | 手机版后台静默登录 | 后台长久登录 + 监测采集 |

---

*审计完成时间：2026-09-02 18:35 PDT*
*审计人：Zachary OS AI · ZBC 生产执行侧*
