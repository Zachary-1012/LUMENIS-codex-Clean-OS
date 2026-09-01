# ZBMP 工作区访问授权（API Key + 用户体系）v1.0

> 阶段：Step5b。仅在 `ui/staging-foundation` 分支与 Staging 8301 验证，验收前不合 main、不动 8201。
> 决策来源：用户在「本地配置口令 vs 正式 API Key+用户体系」中选择**方案 2（正式体系）**。

## 1. 设计原则
- **复用而非新造**：直接建立在既有 `v4_upgrade/auth`（v4_users 三级角色 / v4_sessions / PBKDF2 / require_* 装饰器）之上，只新增“工作区级密钥授权”薄层。
- CTH-POMS 默认进入；**ZBMP 为受限工作区，必须凭工作区密钥解锁**。
- 明文密钥**仅签发时返回一次**；库内只存 PBKDF2 hash（复用 `security.hash_password/verify_password`）。
- 全部 `CREATE TABLE IF NOT EXISTS`，向后兼容、不删不改任何既有表/数据；不改动 HTTP Basic 与现有登录。
- AI 不参与授权判定；授权完全由本模块规则与数据库状态决定。

## 2. 数据表（新增，幂等）
- `v4_workspace_keys`：id / workspace / label / key_prefix（仅前 10 位辨识）/ key_hash / created_by / status(active|revoked) / expires_at / last_used_at / created_at。
- `v4_workspace_grants`：id / user_id / workspace / key_id / session_token / expires_at / created_at —— 记录某会话被授予进入某工作区（默认 12h）。

## 3. HTTP 接口（挂在既有 /v4 蓝图，前缀 /v4/auth）
| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | /v4/auth/workspace/status | 登录可选 | 返回各工作区可进入状态：CTH-POMS 恒 true，ZBMP 看有效 grant |
| POST | /v4/auth/workspace/unlock | 无（凭密钥） | body{workspace,key}；校验密钥，无会话时以 owner 建立会话并 Set-Cookie，再写 12h grant |
| GET | /v4/auth/workspace/keys | 登录 | 列出密钥（只回 prefix，绝不含 hash/明文） |
| POST | /v4/auth/workspace/keys | owner | 签发，body{workspace,label,expires_days?}，明文 key 仅此一次返回 |
| POST | /v4/auth/workspace/keys/revoke | owner | body{id} 吊销（保留记录、连带失效 grant） |

## 4. 前端流程（static/js/zbip-shell.js）
- 左上工作区切换器点 ZBMP → 先 GET status：已授权直接进；未授权弹统一密钥门。
- 密钥门 POST unlock：错钥显示“工作区密钥无效或已吊销/过期”且留在 CTH；对钥进入 ZBMP，会话获 12h 授权，期间再次进入不再弹门。
- sessionStorage 的 `zbmp_unlocked` 仅作 UI 提示，**权威以后端会话 cookie + grant 为准**（已移除旧的“非空即过”localStorage 占位）。

## 5. 密钥从哪来（不硬编码）
1. owner 登录（Zachary）后调 POST /v4/auth/workspace/keys 签发，明文只显示一次，分发给需要进入 ZBMP 的人/设备。
2. 可设置 expires_days 过期；随时 revoke，吊销立即连带失效其授权。
3. 密钥管理 UI（签发/列表/吊销）将并入 Step7 设置页（接口已就绪）。

## 6. 数据库路径隔离修复（向后兼容）
- v4 `config.DB_PATH` 原先只读 `MONITOR_DB_PATH`，未设置时回落到生产 `data/monitor.db`，与主数据层的 `ZBC_DB_PATH` 不一致，会让 Staging 的认证操作误连生产库。
- 现改为优先级 `ZBC_DB_PATH` → `MONITOR_DB_PATH` → 默认生产库。**生产环境不设 ZBC_DB_PATH，行为与历史完全一致**；Staging 设了 ZBC_DB_PATH 指向只读副本，认证也随之隔离。

## 7. 测试与证据（已实测 2026-09-01）
- 单元：tests/test_workspace_keys.py 6/6（临时库：签发一次明文/对错钥/工作区隔离/吊销连带失效/列表不泄密/grant/open_owner_session）。
- HTTP 全链路（8301）：匿名 status=CTH true·ZBMP false；owner 登录；签发返回明文一次；错钥 401；对钥 200 且 Set-Cookie+grant；再查 status ZBMP=true；列表无 hash；吊销 200。
- 浏览器 E2E：未授权弹门；错钥留 CTH 并报错；对钥进入 ZBMP；切回再进凭授权直接放行。
- 回归：test_ai/test_api 主体 + 新测共 33 passed；6 项失败为 Staging 既有 ENV（test_database 写死 data/monitor.db、TestAuthAPI 依赖开启 HTTP Basic），与本改动无关。

## 8. 回滚
删除 v4_upgrade/auth/workspace.py、移除 blueprint.py 中 workspace import 与 5 段路由、前端密钥门可退回；新增两表为独立 IF NOT EXISTS 表，保留不影响任何既有功能（无需删表、更不涉及历史数据）。
