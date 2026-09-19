# Z-Brand 双仓库事实基线

> Baseline ID: ZB-PROD-2026-08-31-04
> 建立/更新：2026-08-31  
> 状态：ACTIVE / HARD PRODUCTION GATE  
> 上一基线：ZB-PROD-2026-08-31-02  
> 生产基线全文：Core 仓库 `docs/PRODUCTION_BASELINE_2026-08-31-V3.md`  
> 事实优先级：当前源码/数据库/运行时实测 > 本基线 > 其他文档 > 聊天记录

## 1. 双仓库身份

| 项目 | 事实 |
|---|---|
| 主业务仓库 | `Zachary-1012/Z-Brand-Core` |
| 研发平台仓库 | `Zachary-1012/Development-Command-Console` |
| Core Visibility | Private |
| DCC Visibility | Private |
| Core Default Branch | `main` |
| DCC Default Branch | `main` |
| Core latest verified HEAD | `ebef23c`（P0 版本校准，v5.9.7） |
| DCC 当前 HEAD | `9525e42a136fdc52bf75a1da00361e2f74d2bade` |
| Core pinned DCC SHA | `0e52b7fb8af003788960a5a54645e890584ddcb7` |
| Core 实际版本 | v5.9.7（VERSION / APP_VERSION / README 已统一） |
| DCC 实际版本 | v0.3.0 Local AI Bridge |

> 注意：DCC HEAD（9525e42）已领先于 Core pinned SHA（0e52b7f）。这是 Submodule 架构的正常状态：DCC 跑在前面（研发最新版本），Core 稳在后面（当前生产认可版本）。DCC 新功能不会因为 DCC 自己升级而把 CTH-POMS 生产系统一起带崩。如需更新 Core 的 pinned SHA，需在 Core 仓库单独执行并经人工批准。

## 2. Source of Truth

- `Z-Brand-Core`：Business Source of Truth。负责生产业务、数据、采集、分析、事件、报告及增强能力。
- `Development-Command-Console`：Development Source of Truth。负责研发任务合同、审计、测试、证据、门禁和受控升级。
- DCC 不属于 CTH-POMS 运行时依赖，不得因 DCC 故障导致 CTH-POMS 停止。
- 两个仓库保持独立 Git 历史，不合并。
- Core 已通过 Private Git Submodule 引用 DCC。
- Core `tools/development-command-console` 当前真实类型为 `submodule`，已固定到 DCC Commit `0e52b7f`。
- Core 中的 submodule 只作为 DCC 接入点，不形成第二份独立 DCC 源码。

## 3. 当前 Core 事实

Core 当前版本 **v5.9.7**，版本链已统一（P0 校准 commit ebef23c）：

| 版本来源 | 实际值 |
|---|---|
| `VERSION` 文件 | 5.9.7 |
| `app.py` APP_VERSION | 5.9.7 |
| `README.md` 版本声明 | v5.9.7 |
| Git 最新功能提交 | 87ec87b feat(v5.9.7) |

v5.9.7 包含：CHANGELOG 补全、品牌知识库、事件关系图谱、品牌分析报告等 V3.0 前端集成，42 项 E2E 测试通过。

Core 已存在 XHS 采集与状态体系，包括生产 collector、CDP collector、runtime state、cookie bridge、Auth Recovery、Platform Adapter、Topic Campaign 和 Web Topic Discovery。

## 4. DCC 事实

DCC 当前 v0.3.0，具备：
- GitHub 只读工程审计（6 个 Reader + Evidence）
- Local AI Bridge（10 个 API，127.0.0.1:8787）
- 任务合同（7 字段 + 13 条执行规则）
- 权限矩阵
- 敏感数据过滤（19 种字段名 + 5 种值模式）
- 82 项自动化测试（46 GitHub Audit + 36 Bridge）
- 自有 CI（test.yml）和 Pages（pages.yml）
- XHS App 生产门禁已 align 到 v3（`docs/PRODUCTION-GATE-XHS-APP.md`，commit 9525e42）

DCC 当前安全边界：
- READ / TASK / AUDIT = ALLOW
- TEST = CONTROLLED / READ-ONLY
- WRITE / COMMIT / MERGE / DEPLOY / SHELL EXEC / CODE EXEC = DENY
- PRODUCTION_WRITE = DENY
- UNKNOWN_CODE_EXECUTION = DENY
- Bridge = 127.0.0.1:8787
- 无 Token / PAT / Secret / Cookie / 凭据

DCC 不连接生产数据库，不自动修改 Core，不自动 Merge，不自动部署生产。

## 5. Submodule 收敛事实

已核实：

- Core `.gitmodules` 存在：`tools/development-command-console`
- Submodule URL：`https://github.com/Zachary-1012/Development-Command-Console.git`
- Core 中该路径的 GitHub 类型为 `submodule`
- 当前 pinned SHA：`0e52b7fb8af003788960a5a54645e890584ddcb7`
- DCC 当前 HEAD：`9525e42`（领先于 pinned SHA，正常状态）
- 旧的 Core 内 DCC legacy copy 已 REMOVED
- 旧的 Core 内 DCC Pages workflow 已 REMOVED

因此旧的 Core 内 DCC legacy copy 已不再是当前 Source of Truth。

架构级禁止事项：
- 禁止把 DCC 源码复制回 Core
- 禁止 Core 保存 DCC 源码副本
- Core 只保存 Submodule Path + Pinned Commit SHA
- 禁止取消 Git Submodule
- 禁止合并两个 Git 仓库历史

## 6. 不可破坏业务边界

任何双仓库收敛或 DCC 升级不得顺手修改：
- CTH-POMS 核心业务
- ZBMP 核心业务
- 生产数据库与历史业务数据
- 风险、事件、报告核心判断
- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime` / `captured_at` 语义
- 已验证 XHS 主采集主链

采集异常不得包装成"0 条数据"。

## 7. XHS App 生产门禁（v3）

XHS App 能力必须引用 `ZB-PROD-2026-08-31-04`。

在没有小红书官方明确授权的 App API/SDK 能力前，**XHS App 不是生产自动采集源**。

第一阶段只允许：`App Evidence Adapter`（用户主动提供官方 App 中可见的目标话题页面截图/分享证据，由 Core 做 OCR/结构化、来源记录和 Shadow 融合）。

永久 BLOCK（10 项，详见 DCC `docs/PRODUCTION-GATE-XHS-APP.md` 和 Core `docs/PRODUCTION_BASELINE_2026-08-31-V3.md` 第 5 节）：
1. 抓包还原或逆向私有 API 签名
2. 逆向/复制私有加密或签名算法
3. 伪造设备身份、请求签名、Token、安全参数
4. 自动绕过验证码、IP 风险、设备校验或 Session 限制
5. 代理池、频繁换 IP、设备指纹等用于规避平台限制
6. 多账号轮换、批量注册等用于规避账号/设备限制
7. 未经官方授权调用私有接口作为生产数据源
8. App 注入、读取 App 私有数据库、拦截 App 网络流量
9. 自动登录、自动批量点击/滑动/浏览 App
10. 将 App 自动化能力直接接入生产高频调度

## 8. 生产升级流程

`GitHub HEAD 核对 → 读取生产基线 → 影响范围 → 最小补丁 → 测试 → 安全审计 → Diff → 人工批准 → PR/Release → 二次 HEAD 核验`

未完成、未测试、未部署不得写成 PASS。

DCC 新版本发布到 Core 的受控流程（未来 V0.4 Release Gate）：
```
DCC 新版本 → Release Candidate → 读取 Core pinned SHA → 读取 DCC HEAD → Diff
→ 自动化测试 → 安全扫描 → Core 回归 → Evidence → 风险判断 → 人工批准
→ 生成 RC SHA → Core 更新 Submodule → Core 回归 → 最终批准
```

## 9. 冲突处理

若聊天、旧文档、AI 输出与当前源码冲突：

`当前源码/数据库/运行时实测 > ZB-PROD-2026-08-31-04 > 其他文档 > 历史聊天`

任何与本基线冲突的任务先标记 `BLOCKED`，提出基线变更申请，不得静默绕过。

发现远程新 Commit 立即停机重读，不得基于旧状态继续操作。

## 10. 变更纪律

任何与本基线冲突的需求必须先提交"基线变更申请"。

不得通过以下名称绕过基线：
- research mode
- experimental mode
- shadow mode
- temporary patch
- debug mode

Shadow 是验证隔离机制，不是绕过安全门禁的名称。

## 11. 事实纪律

- GitHub HEAD / Commit / Diff / Workflow / Test Evidence 优先于聊天记录。
- 计划不是完成。
- 未测试不是测试通过。
- 未部署不是已部署。
- WARN / BLOCKED / FAIL 不得写成 PASS。
- 不得虚构 Commit SHA、测试结果、部署结果或生产状态。
- 无法实际验证的内容必须标记 NOT VERIFIED / BLOCKED。
- 未经批准不推动 Core pinned SHA。

## 12. 同步标识

该基线必须同时存在于：
- `Zachary-1012/Development-Command-Console`
- `Zachary-1012/Z-Brand-Core`

两边的 Baseline ID 必须保持：`ZB-PROD-2026-08-31-04`。

生产基线全文以 Core 仓库 `docs/PRODUCTION_BASELINE_2026-08-31-V3.md` 为准。
