# Z-Brand 双仓库事实基线

> Baseline ID: ZB-RD-2026-08-31-01  
> 建立时间：2026-08-31  
> 收敛时间：2026-08-31  
> 状态：ACTIVE / SUBMODULE-CONVERGED  
> 本文件是双仓库共同事实基线；事实以 GitHub 实际状态为准。

## 1. 双仓库身份

| 项目 | 事实 |
|---|---|
| 主业务仓库 | `Zachary-1012/Z-Brand-Core` |
| 研发平台仓库 | `Zachary-1012/Development-Command-Console` |
| Core Visibility | Private |
| DCC Visibility | Private |
| Core Default Branch | `main` |
| DCC Default Branch | `main` |
| Core Before SHA（收敛前） | `1e251747a5a9d386f6abf443b5f7d4032009d319` |
| Core Baseline Doc SHA | `df80c7ddb9cd4d8ed0008d45383d379cb66e7780` |
| DCC Before SHA（基线建立时） | `6bffaa9f4a8d82bb7c75b436e44d1c4968f220b5` |
| DCC Current HEAD | `0e52b7fb8af003788960a5a54645e890584ddcb7` |
| Pinned Submodule SHA | `0e52b7fb8af003788960a5a54645e890584ddcb7` |

## 2. Source of Truth

- `Z-Brand-Core`：Business Source of Truth。
- `Development-Command-Console`：Development Source of Truth。
- DCC 独立存在，不与 Core 合并 Git 历史。
- Core 通过 Private Git Submodule 引用 DCC 的固定 Commit SHA。
- **Submodule 已完成建立。** path = `tools/development-command-console`，url = `https://github.com/Zachary-1012/Development-Command-Console.git`，pinned SHA = `0e52b7f`。

## 3. Core 收敛后状态

Core 通过 Git Submodule 引用 DCC，不再拥有 DCC 源码副本。

`tools/development-command-console/` 当前为 Git Submodule working tree（gitlink mode 160000），不是源码副本。

Core 旧 DCC Pages Workflow 已退役：
- `.github/workflows/development-command-console-pages.yml` — REMOVED
- 原因：DCC 自有仓库已配置独立 `pages.yml` 和 `test.yml`，Pages URL 为 `https://zachary-1012.github.io/Development-Command-Console/`，Core 内旧 workflow 仅服务旧副本，无其他引用。

## 4. DCC 状态

DCC 当前 HEAD：`0e52b7fb8af003788960a5a54645e890584ddcb7`。

最新提交：`docs: establish dual-repository architecture fact baseline`。

DCC 版本：`v0.3 Local AI Bridge`。
- 82 个自动化测试全部通过（36 Bridge + 46 GitHub Audit）
- Local AI Bridge：`127.0.0.1:8787`
- 权限矩阵：READ / TASK / AUDIT = ALLOW，TEST = CONTROLLED，WRITE / DEPLOY = DENY
- 自有 CI：`.github/workflows/test.yml`（push/PR 自动运行测试）
- 自有 Pages：`.github/workflows/pages.yml`

## 5. 不可破坏业务边界

本次架构收敛不得顺手修改：
- CTH-POMS 核心业务
- ZBMP 核心业务
- 生产数据库与历史业务数据
- 生产部署
- 风险、事件、报告核心判断
- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime` / `captured_at` 语义

AI/Adapter/第三方采集异常不得包装为"0 条数据"。

## 6. DCC 安全边界

保持：
- READ / TASK / AUDIT = ALLOW
- TEST = CONTROLLED
- WRITE = DENY
- DEPLOY = DENY
- PRODUCTION_WRITE = DENY
- UNKNOWN_CODE_EXECUTION = DENY

禁止为了 Private Submodule 或 CI 便利：
- 将任一仓库改为 Public
- 在前端、localStorage、URL、README 或 Workflow 写入 Token/PAT
- 建立万能 shell/exec/run 接口
- 自动 Merge 或自动生产部署

## 7. 目标架构（已实现）

```text
Z-Brand-Core (Private)
│
├── CTH-POMS
├── ZBMP
├── 业务/数据/部署能力
│
└── tools/
    └── development-command-console/   ← Private Git Submodule (pinned 0e52b7f)
                 │
                 └── Zachary-1012/Development-Command-Console

Development-Command-Console (Private)
= DCC 唯一源码事实源
```

## 8. 迁移状态（收敛后）

- DCC 独立 Private 仓库：PASS
- Core Private 仓库：PASS
- DCC 当前独立源码事实源：PASS
- Core 旧 DCC copy：REMOVED
- Core 旧 DCC Pages workflow：REMOVED
- Private Git Submodule：ESTABLISHED
- Submodule pinned SHA：`0e52b7fb8af003788960a5a54645e890584ddcb7`
- `.gitmodules`：PASS（path/url 正确）
- DCC 82 tests：PASS（82/82，0 failed）
- 安全扫描：PASS（无 Token/Secret 泄露）
- Submodule integration check：PASS（7/7）
- 双仓库 CI Private Submodule 权限：待 GitHub Actions 运行后验证
- CTH-POMS：UNCHANGED
- ZBMP：UNCHANGED
- 生产业务逻辑：UNCHANGED

## 9. 收敛执行记录

执行顺序（已完成）：

1. ✅ 记录 Core/DCC Before SHA。
2. ✅ 备份旧 DCC 副本到 `D:\Taikoo-monitor-new-backups\dcc-legacy-<timestamp>\`。
3. ✅ 从 Core 索引移除旧 DCC 副本文件。
4. ✅ 建立 Private Git Submodule（`git submodule add`）。
5. ✅ 固定 DCC pinned SHA = `0e52b7f`。
6. ✅ 验证 `.gitmodules` path/url/SHA 正确。
7. ✅ 确认 Core 无其他 DCC copy/reference。
8. ✅ 运行 DCC 82 tests（全部通过）。
9. ✅ 安全扫描（无敏感信息）。
10. ✅ Submodule integration check（7/7 PASS）。
11. ✅ 确认旧 Pages Workflow 无其他引用后退役。
12. ⏳ Commit & Push（待执行）。
13. ⏳ GitHub Actions + 二次 HEAD 核验（Push 后执行）。

任何权限、依赖或测试问题：标记 `BLOCKED`，不得为了 PASS 降低私密性或安全边界。

## 10. 事实纪律

- GitHub HEAD / Commit / Diff / Workflow / Test Evidence 优先于聊天记录。
- 计划不是完成。
- 未测试不是测试通过。
- 未部署不是已部署。
- WARN / BLOCKED / FAIL 不得写成 PASS。
- 不得虚构 Commit SHA、测试结果、部署结果或生产状态。

## 11. 同步标识

该基线必须同时存在于：
- `Zachary-1012/Development-Command-Console`
- `Zachary-1012/Z-Brand-Core`

两边的 Baseline ID 必须保持：`ZB-RD-2026-08-31-01`。
