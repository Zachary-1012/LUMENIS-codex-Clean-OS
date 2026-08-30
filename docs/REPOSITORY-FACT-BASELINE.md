# Z-Brand 双仓库事实基线

> Baseline ID: ZB-PROD-2026-08-31-03  
> 建立时间：2026-08-31  
> 生效时间：2026-08-31  
> 状态：ACTIVE / HARD PRODUCTION GATE  
> 上一基线：ZB-PROD-2026-08-31-02  
> 生产基线全文：`docs/PRODUCTION_BASELINE_2026-08-31-V3.md`  
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
| Core 当前 HEAD | `ebef23c`（P0 版本校准提交，v5.9.7） |
| DCC 当前 HEAD | `9525e42`（XHS App 门禁 align v3） |
| Core pinned DCC SHA | `0e52b7fb8af003788960a5a54645e890584ddcb7` |
| Core 实际版本 | v5.9.7（VERSION / APP_VERSION / README 已统一） |
| DCC 实际版本 | v0.3.0 Local AI Bridge |

> 注意：Core 当前 HEAD 与 Core pinned DCC SHA 是两个不同的值。Core HEAD 随 Core 自身业务开发前进（当前 v5.9.7），而 Core pinned DCC SHA 固定指向 DCC 仓库的某个明确 Commit（当前 0e52b7f）。DCC HEAD（9525e42）已领先于 pinned SHA，这是 Submodule 架构的正常状态：DCC 跑在前面，Core 稳在后面。

## 2. Source of Truth

- `Z-Brand-Core`：Business Source of Truth。负责生产业务、数据、采集、分析、事件、报告及增强能力。
- `Development-Command-Console`：Development Source of Truth。负责研发任务合同、审计、测试、证据、门禁和受控升级。
- DCC 不属于 CTH-POMS 运行时依赖，不得因 DCC 故障导致 CTH-POMS 停止。
- 两个仓库保持独立 Git 历史，不合并。
- Core 通过 Private Git Submodule 引用 DCC 的固定 Commit SHA。
- **Submodule 已完成建立。** path = `tools/development-command-console`，url = `https://github.com/Zachary-1012/Development-Command-Console.git`，pinned SHA = `0e52b7f`。
- Core 中的 `tools/development-command-console` 为 Git submodule，只作为 DCC 接入点，不形成第二份独立 DCC 源码。

## 3. Core 当前状态

Core 当前版本 **v5.9.7**，版本链已统一：

| 版本来源 | 实际值 | 状态 |
|---|---|---|
| `VERSION` 文件 | 5.9.7 | ✅ 已校准（P0 commit ebef23c） |
| `app.py` APP_VERSION | 5.9.7 | ✅ 一致 |
| `README.md` 版本声明 | v5.9.7 | ✅ 一致 |
| Git 最新功能提交 | 87ec87b feat(v5.9.7) | ✅ 一致 |
| `PROJECT_STATUS.md` | v5.9.7 | ✅ 已校准 |
| `CURRENT_BASELINE.md` | v3 | ✅ 已校准 |

v5.9.7 包含：CHANGELOG 补全（v5.9.1~v5.9.6）、品牌知识库前端页面、事件关系图谱前端页面、品牌分析报告前端页面、V3.0 三模块前端集成，42 项 E2E 测试通过。

Core 已存在 XHS 采集与状态体系，包括生产 collector、CDP collector、runtime state、cookie bridge、Auth Recovery、Platform Adapter、Topic Campaign 和 Web Topic Discovery。

## 4. DCC 当前状态

DCC 当前 HEAD：`9525e42a136fdc52bf75a1da00361e2f74d2bade`。

最新提交：`docs: align DCC XHS App gate with production baseline v3`。

DCC 版本：`v0.3.0 Local AI Bridge`。
- 82 个自动化测试（46 GitHub Audit + 36 Bridge）
- Local AI Bridge：`127.0.0.1:8787`
- 权限矩阵：READ / TASK / AUDIT = ALLOW，TEST = CONTROLLED，WRITE / DEPLOY = DENY
- 自有 CI：`.github/workflows/test.yml`（push/PR 自动运行测试）
- 自有 Pages：`.github/workflows/pages.yml`
- XHS App 生产门禁：已 align 到 v3（`docs/PRODUCTION-GATE-XHS-APP.md`）
- 仓库可见性：Private

DCC 不连接生产数据库，不自动修改 Core，不自动 Merge，不自动部署生产。

## 5. 不可破坏生产红线

任何双仓库收敛或 DCC 升级不得弱化、删除、绕过：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime` / `captured_at` 时间语义
- 历史生产数据库及备份
- 已验证 XHS 主采集主链

任何采集异常、IP 风险、300012、验证码、Session 失效、权限问题不得伪装成"0 条"。

AI/Adapter/第三方采集异常不得包装为"0 条数据"。

## 6. DCC 安全边界

保持（`server/config.js` SHA `7198a2b`，零漂移）：

- READ (github.read / github.audit) = ALLOW
- TASK (task.create) = ALLOW
- AUDIT (github.audit) = ALLOW
- TEST (test.read) = CONTROLLED / READ-ONLY
- WRITE (github.push / github.commit) = DENY
- MERGE (github.merge) = DENY
- DEPLOY (production.deploy) = DENY
- SHELL EXEC (shell.exec) = DENY
- CODE EXEC (code.execute) = DENY
- PRODUCTION_WRITE = DENY
- UNKNOWN_CODE_EXECUTION = DENY
- Bridge Host = 127.0.0.1（非 0.0.0.0）
- Bridge Port = 8787
- 最大请求体 = 10KB
- 速率限制 = 60 req/min/IP
- Token = NO TOKEN IN FRONTEND / localStorage / URL / README / Workflow

禁止为了 Private Submodule 或 CI 便利：
- 将任一仓库改为 Public
- 在前端、localStorage、URL、README 或 Workflow 写入 Token/PAT
- 建立万能 shell/exec/run 接口
- 自动 Merge 或自动生产部署

## 7. XHS App 生产门禁（v3）

XHS App 能力必须引用 `ZB-PROD-2026-08-31-03`。

在没有小红书官方明确授权的 App API/SDK 能力前，**XHS App 不是生产自动采集源**。

第一阶段只允许：`App Evidence Adapter`（用户主动提供官方 App 中可见的目标话题页面截图/分享证据，由 Core 做 OCR/结构化、来源记录和 Shadow 融合）。

永久 BLOCK（10 项，详见 `docs/PRODUCTION_BASELINE_2026-08-31-V3.md` 第 5 节和 DCC `docs/PRODUCTION-GATE-XHS-APP.md`）：
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

## 8. 目标架构（已实现）

```text
                    ZB-PROD-2026-08-31-03
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
       Z-Brand-Core                    DCC
       Private                         Private
       Business SoT                    Development SoT
                │                           │
       生产业务系统                     研发/审计/测试
       CTH-POMS                        Task Contract
       ZBMP                            GitHub Audit
       Collector                       Evidence
       Analysis                        Gates
       Events                          AI Bridge
       Reports                         Tests
                │                           │
                └─────── Submodule ────────┘
                   pinned SHA = 0e52b7f
```

架构级禁止事项：
- 禁止把 DCC 源码复制回 Core。
- 禁止 Core 保存 DCC 源码副本。
- Core 只保存 Submodule Path + Pinned Commit SHA。
- 禁止取消 Git Submodule。
- 禁止合并两个 Git 仓库历史。

## 9. 迁移状态（收敛后）

- DCC 独立 Private 仓库：PASS
- Core Private 仓库：PASS
- DCC 当前独立源码事实源：PASS
- Core 旧 DCC copy：REMOVED
- Core 旧 DCC Pages workflow：REMOVED
- Private Git Submodule：ESTABLISHED
- `.gitmodules`：PASS（path/url 正确）
- Submodule pinned SHA：`0e52b7fb8af003788960a5a54645e890584ddcb7`
- DCC HEAD (9525e42) vs pinned SHA (0e52b7f)：MISMATCH（正常 — DCC 领先，Core 稳定）
- DCC 82 tests：PASS（82/82，0 failed）
- 安全扫描：PASS（无 Token/Secret 泄露）
- Submodule integration check：PASS
- 双仓库 CI Private Submodule 权限：NOT YET VERIFIED（Core 当前无 workflow，暂不涉及）
- CTH-POMS：UNCHANGED
- ZBMP：UNCHANGED
- 生产业务逻辑：UNCHANGED
- Core 版本一致性（P0）：PASS（VERSION/APP_VERSION/README/PROJECT_STATUS 已统一为 v5.9.7）

## 10. 生产升级流程

`GitHub HEAD 核对 → 读取生产基线 → 影响范围 → 最小补丁 → 测试 → 安全审计 → Diff → 人工批准 → PR/Release → 二次 HEAD 核验`

未完成、未测试、未部署不得写成 PASS。

任何新能力只有同时满足以下条件才可进入生产：
- CTH-POMS 主链回归通过
- 主体/时间/风险/事件/报告口径回归通过
- 无生产红线修改
- 新能力可独立关闭
- 异常状态可解释
- 无敏感凭据进入仓库
- 有测试证据
- 有回滚方案
- DCC 审计通过
- Core 与 DCC HEAD 二次核验完成

## 11. 变更纪律

任何与本基线冲突的需求必须先提交"基线变更申请"。

不得通过以下名称绕过基线：
- research mode
- experimental mode
- shadow mode
- temporary patch
- debug mode

Shadow 是验证隔离机制，不是绕过安全门禁的名称。

## 12. 冲突处理

若聊天、旧文档、AI 输出与当前源码冲突：

`当前源码/数据库/运行时实测 > ZB-PROD-2026-08-31-03 > 其他文档 > 历史聊天`

任何与本基线冲突的任务先标记 `BLOCKED`，提出基线变更申请，不得静默绕过。

## 13. 事实纪律

- GitHub HEAD / Commit / Diff / Workflow / Test Evidence 优先于聊天记录。
- 计划不是完成。
- 未测试不是测试通过。
- 未部署不是已部署。
- WARN / BLOCKED / FAIL 不得写成 PASS。
- 不得虚构 Commit SHA、测试结果、部署结果或生产状态。
- 无法实际验证的内容必须标记 NOT VERIFIED / BLOCKED。
- 发现远程新 Commit 立即停机重读，不得基于旧状态继续操作。

## 14. 同步标识

该基线必须同时存在于：
- `Zachary-1012/Development-Command-Console`
- `Zachary-1012/Z-Brand-Core`

两边的 Baseline ID 必须保持：`ZB-PROD-2026-08-31-03`。

生产基线全文以 Core 仓库 `docs/PRODUCTION_BASELINE_2026-08-31-V3.md` 为准。
