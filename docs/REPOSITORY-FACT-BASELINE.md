# Z-Brand 双仓库事实基线

> Baseline ID: ZB-RD-2026-08-31-01  
> 建立时间：2026-08-31  
> 状态：ACTIVE / PRE-SUBMODULE-CONVERGENCE  
> 本文件是双仓库共同事实基线；事实以 GitHub 实际状态为准。

## 1. 双仓库身份

| 项目 | 当前事实 |
|---|---|
| 主业务仓库 | `Zachary-1012/Z-Brand-Core` |
| 研发平台仓库 | `Zachary-1012/Development-Command-Console` |
| Core Visibility | Private |
| DCC Visibility | Private |
| Core Default Branch | `main` |
| DCC Default Branch | `main` |
| Core 当前 HEAD（建立基线前） | `1e251747a5a9d386f6abf443b5f7d4032009d319` |
| DCC 当前 HEAD（建立基线前） | `6bffaa9f4a8d82bb7c75b436e44d1c4968f220b5` |

## 2. Source of Truth

- `Z-Brand-Core`：Business Source of Truth。
- `Development-Command-Console`：Development Source of Truth。
- DCC 当前独立存在，不与 Core 合并 Git 历史。
- 本基线确认的目标架构是：Core 通过 Private Git Submodule 引用 DCC 的固定 Commit SHA。
- **截至本基线建立时，Submodule 尚未完成建立。** 不得把计划状态写成已完成状态。

## 3. 当前已核实的 Core 状态

GitHub 当前 `Z-Brand-Core` HEAD 为 `1e251747...`，最新提交标题为 `feat(v5.9.4): 案例深度拆解模块 + 行业平台配置 + 知识库扩充至52条`。

Core 当前仍存在旧版 DCC 目录：

`tools/development-command-console/`

已核实该目录当前至少包含：
- `README.md`
- `index.html`

这说明目前仍是 legacy copy，而不是已经核实完成的 Git Submodule。

Core 当前仍存在旧 DCC Pages Workflow：

`.github/workflows/development-command-console-pages.yml`

该 Workflow 当前会从 `tools/development-command-console/` 复制静态文件到 Pages 构建目录，因此在 Submodule 迁移完成并验证前，不得直接删除。

## 4. 当前已核实的 DCC 状态

DCC 当前 HEAD：`6bffaa9f4a8d82bb7c75b436e44d1c4968f220b5`。

最新提交：`docs: align development console with Z-Brand CTH-first integration baseline`。

该提交新增 `docs/Z-BRAND-INTEGRATION.md`，明确：
- DCC 是 Z-Brand 内部 AI 研发中枢。
- CTH-POMS 为 P0 上线优先级。
- ZBMP 为 Core 内受控能力层。
- DCC 保持 READ / TASK / AUDIT = ALLOW、TEST = CONTROLLED、WRITE / DEPLOY = DENY。
- 后续自动化应优先走需求 → 分析 → 补丁候选 → 隔离分支 → 自动测试 → Diff 审计 → 人工批准 → PR → 验收。

DCC README 当前仍声明版本为 `v0.3`，并记录 82 个自动化测试、Local AI Bridge `127.0.0.1:8787`、V0.1/V0.2/V0.3 能力及安全边界。版本声明与最新文档提交需在后续漂移检查中继续核对，不得凭聊天记录猜测。

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

AI/Adapter/第三方采集异常不得包装为“0 条数据”。

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

## 7. 目标架构

```text
Z-Brand-Core (Private)
│
├── CTH-POMS
├── ZBMP
├── 业务/数据/部署能力
│
└── tools/
    └── development-command-console/   ← Private Git Submodule
                 │
                 └── pinned DCC Commit SHA

Development-Command-Console (Private)
= DCC 唯一源码事实源
```

## 8. 当前迁移状态

- DCC 独立 Private 仓库：PASS
- Core Private 仓库：PASS
- DCC 当前独立源码事实源：PASS
- Core 旧 DCC copy：FOUND / LEGACY
- Core 旧 DCC Pages workflow：FOUND / LEGACY
- Private Git Submodule：NOT YET ESTABLISHED
- Submodule pinned SHA：NOT YET ESTABLISHED
- 双仓库 CI Private Submodule 权限：NOT YET VERIFIED
- 旧 copy 退役：NOT YET AUTHORIZED
- 旧 workflow 退役：NOT YET AUTHORIZED

## 9. 下一阶段硬门槛

必须按以下顺序执行：

1. 记录 Core/DCC Before SHA。
2. 建立 Private Git Submodule。
3. 固定 DCC pinned SHA。
4. 验证 Core checkout 与 DCC SHA 一致。
5. 检查 Core 是否存在其他 DCC copy/reference。
6. 验证 Core 与 DCC 现有测试不受影响。
7. 验证旧 Pages Workflow 是否可安全退役。
8. 再退役旧 DCC copy 与旧 Workflow。
9. 更新两个仓库 DEVELOPMENT-LOG。
10. GitHub Actions + 二次 HEAD 核验。

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
