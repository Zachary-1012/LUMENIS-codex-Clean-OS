# DCC V0.4.1 P1 — Evidence Contract Change Contract

> Task ID: TASK-V041-P1-20260831-001
> Baseline ID: ZB-PROD-2026-08-31-04
> Created: 2026-08-31
> Status: ACTIVE
> Phase: P1 — Evidence Contract（证据标准与契约，不含业务代码实现）

## 1. 任务目标

在 DCC V0.4.0 已完成 Snapshot + Change Plan + Remote HEAD Lock 的基础上，建立 V0.4.1 Evidence Contract。

本阶段只建立"证据标准与契约"，暂不实现 Evidence Bundle 业务代码。

Evidence 必须能够回答：
- WHO：谁产生/提交了证据
- WHAT：发生了什么操作/检查
- WHEN：什么时候检查
- WHERE：针对哪个仓库/文件/对象
- WHICH VERSION：针对哪个版本
- WHICH BASELINE：针对哪个 Baseline
- WHICH SHA：针对哪个 Git commit / pinned SHA
- SOURCE：证据来自哪里
- RESULT：检查结果是什么
- DECISION：系统因此允许、阻止还是要求重新规划

## 2. 目标仓库

- Repository: Development-Command-Console (Private)
- Branch: main
- Starting HEAD: b6b047cd79d46f16eb0397d2a7a83df71cc327f3
- Starting Version: 0.3.0

## 3. Core 边界

Core 只读验证。本阶段禁止：
- 修改 Core 业务代码
- 修改 Core 前端
- 修改 Core submodule
- 主动更新 Core pinned DCC SHA
- 修改 Core 用户未提交文件
- 自动处理 Core stash
- reset --hard
- git clean
- force push

除非后续单独获得明确授权。

## 4. 允许修改的文件

只允许：
- `docs/V041-CHANGE-CONTRACT.md`（本文件）
- `docs/V041-EVIDENCE-SCHEMA.md`（Evidence 数据契约）
- `docs/DEVELOPMENT-LOG.md`（追加 P1 开发记录）

## 5. 禁止修改的文件（全部 LOCK）

- `server/` 下所有文件
- `tests/` 下所有文件
- `package.json`
- `index.html`
- `js/`
- `config.js`
- `security.js`
- `.github/`
- Core 仓库任何文件

## 6. 允许的操作

- 新增 docs/ 下的文档文件
- 在 docs/DEVELOPMENT-LOG.md 追加开发记录
- 读取双仓库状态（只读）

## 7. 禁止的操作

- 实现 evidence-bundle.js
- 修改 server.js
- 修改 tests/
- 修改 package.json
- 更新 DCC version
- 更新 Core submodule
- 修改 Core
- 部署
- 修改生产环境
- 自动修复用户代码
- 删除用户文件
- 删除备份
- 处理 stash
- reset --hard
- git clean
- force push
- rebase 已被 Core 引用的 commit
- 新增 npm dependency

## 8. 预期产出

1. `docs/V041-CHANGE-CONTRACT.md` — P1 变更合同（本文件）
2. `docs/V041-EVIDENCE-SCHEMA.md` — Evidence 数据契约，包含：
   - 完整字段定义（21个字段）
   - Evidence Source 分类（14种）
   - Result 枚举（5种）
   - Decision 枚举（4种）
   - expected vs observed 区分规则
   - Evidence 完整性规则
   - 禁止伪证据规则
   - 历史记录规则
3. `docs/DEVELOPMENT-LOG.md` — 追加 P1 开发记录

## 9. 预期测试

文档修改无需运行功能测试。必须执行：
- git diff 检查（仅允许的 3 个文档文件变化）
- git diff --check（无 whitespace 错误）
- 安全扫描（无新增 Token/Secret/Credential）
- Evidence Schema 自洽性检查（字段定义与枚举定义一致，无矛盾）

## 10. 预期证据

- 双仓库事实基线（DCC/Core HEAD、pinned SHA、workspace、Baseline ID）
- Remote HEAD Lock
- 修改文件清单
- 未修改文件清单
- git diff --stat
- git diff --check 结果
- 安全扫描结果
- Evidence Schema 自洽性验证结果
- Commit SHA（如获得授权）
- Push 结果（如获得授权）
- 二次 GitHub 核验结果（如获得授权）

## 11. 回滚策略

- 删除新增的 docs/V041-CHANGE-CONTRACT.md
- 删除新增的 docs/V041-EVIDENCE-SCHEMA.md
- 还原 docs/DEVELOPMENT-LOG.md 到修改前状态
- 回滚到 Starting HEAD: b6b047c

## 12. 晋级影响

- 不影响 Core pinned SHA
- DCC 独立前进，不自动 promotion
- P1 完成后不自动进入 P2，需重新建立 Baseline 并获得授权

## 13. 验收标准

1. docs/V041-CHANGE-CONTRACT.md 存在且内容完整
2. docs/V041-EVIDENCE-SCHEMA.md 存在且包含全部 21 个字段定义
3. Evidence Source 分类包含至少 14 种
4. Result 枚举包含 5 种（PASS/FAIL/BLOCKED/NOT_VERIFIED/REPLAN_REQUIRED）
5. Decision 枚举包含至少 4 种（ALLOW/STOP/REPLAN/REVIEW_REQUIRED）
6. expected 与 observed 字段明确区分
7. Evidence 完整性规则明确（Baseline → Snapshot → Lock → Change Plan → Operation → Evidence → Decision）
8. 禁止伪证据规则明确
9. 历史记录规则明确（不篡改历史事实）
10. docs/DEVELOPMENT-LOG.md 追加 P1 记录
11. 仅允许的 3 个文档文件变化
12. 无代码文件误改
13. 无新增外部依赖
14. 无新增 Token/Secret/Credential
15. git diff --check 通过
16. Evidence Schema 自洽性验证通过
17. 权限边界未改变
18. Core 未触碰
19. NOT_VERIFIED 项明确列出
20. Remaining Issues 明确列出

## 14. 权限边界（维持不变）

- READ = ALLOW
- TASK = ALLOW
- AUDIT = ALLOW
- TEST = CONTROLLED
- WRITE = DENY
- COMMIT = DENY
- MERGE = DENY
- DEPLOY = DENY
- SHELL EXEC = DENY
- CODE EXEC = DENY

本阶段不扩大任何权限。

## 15. Commit / Push Gate

本阶段默认允许完成文档修改。但 Commit / Push 必须经过以下五道 Gate 全部 PASS 后才能请求授权：
1. Diff Gate
2. Security Gate
3. Remote HEAD Gate
4. 文件范围 Gate
5. Evidence Contract 自身一致性 Gate

不得因为"测试通过"就自动 Push。

## 16. 下一阶段

P1 完成后不要自动进入 P2。

下一阶段候选：
- P2：Evidence Bundle 实现（server/evidence-bundle.js + tests）
- P3：Security Gate
- P4：Release Candidate

每阶段必须重新建立 Baseline。
