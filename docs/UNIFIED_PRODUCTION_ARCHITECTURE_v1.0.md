# ZBC / DCC / SICI Unified Production Architecture v1.0

> 生效日期：2026-08-31
> 类型：增项治理基线 / 施工顺序规范
> 目标：架构收敛、运行验证、最小修复、稳定上线；不阻塞现有工程进度。

## 0. 最高级规则

本文件是对现有生产基线的**增项融合**，不是替换，不推翻既有架构。

必须遵守：

1. 先读取/盘点，后修改。
2. 先运行证据，后判断问题。
3. 能不改不改；能小改不大改。
4. 不整仓重写，不无依据删除，不用新包覆盖旧包。
5. 任何清理先做引用、调用链、运行依赖和回归验证。
6. 当前 ZBC 阶段以修复、补全、上线阻塞问题为主；暂停无必要的新功能、大规模重构和纯优化。
7. 达到 Release Gate 后立即上线，不以“继续优化”为上线前置条件。
8. 读取、审计、Staging 测试必须与当前本地生产/临时公网隔离，不得影响正在运行的工程。

## 1. 三仓库职责

```text
SICI-Core
  Research / Learning / Benchmark / Knowledge
          ↓
Development-Command-Console
  Audit / Change Map / Evidence / Release Gate
          ↓
Z-Brand-Core
  Production / CTH-POMS / ZBMP controlled capability
```

三个仓库继续独立 Git 管理，不做粗暴物理合并，不互相覆盖源码。

统一的是：Contracts、Evidence、Version、Change Map、Research Records、Release Gate。

## 2. ZBC 当前生产边界

Z-Brand-Core 继续保持：

- CTH-POMS 为当前主力生产/客户交付入口。
- ZBMP 为 Core 内受控增强能力层，不拆成第二套长期维护 Core。
- DCC 不是 CTH-POMS 生产运行时依赖。
- 当前生产核心业务逻辑优先保持不变。

核心红线继续以 `CURRENT_BASELINE.md` 为准，尤其不得弱化或绕过主体过滤、时间语义、风险/事件/报告口径、历史生产数据及安全边界。

## 3. 第一阶段：INVENTORY，禁止改生产代码

完整盘点 ZBC：

- 全部 Python/JS/CSS/HTML
- 全部依赖
- 全部路由/API
- 数据库 schema / migration / seed / backup
- Scheduler / Jobs
- Collector / Adapter
- Browser Runtime
- AI Provider
- UI/UX
- Tests
- Config
- Legacy / Deprecated / Experimental / Duplicate / Unused

生成：

- `ARCHITECTURE-MAP`
- `DEPENDENCY-MATRIX`
- `MODULE-MATRIX`
- `ROUTE-MATRIX`
- `DATABASE-MATRIX`
- `UI-MATRIX`
- `CLEANUP-MATRIX`

没有证据不得删除任何代码包。

## 4. 第二阶段：ZBC-STAGING-RUNTIME

建立与本地完全隔离的可执行 Staging：

```text
独立 Runtime
独立端口
独立数据库
独立 .env
独立日志
独立测试数据
独立 Browser Profile
XHS_PRODUCTION=false
```

Staging 首次运行必须使用当前 main 基线原样运行，不先改业务代码。

当前本地临时公网、生产数据库、Cookie、Token、进程不得被 Staging 操作。

## 5. 推荐 Runtime 基础

优先采用轻量、成熟、可重复的：

- Docker / Docker Compose：隔离和可重复运行。
- Flask：当前不迁移，避免无收益的大规模重构。
- SQLite：当前不迁移；未来有明确并发/规模证据再评估 PostgreSQL。
- Playwright：优先作为浏览器测试与运行验证基础。
- Selenium：暂保留为 Browser Adapter；逐项确认调用链后再决定是否淘汰。
- 现有 HTML/Jinja + 原生 JS/CSS：当前不换前端框架，先治理层级污染。
- AI Provider：统一抽象，生产仍以现有合法/已验证运行方式为准，不把单一外部云端模型作为系统硬依赖。

任何技术替换必须满足：稳定性、兼容性、轻量性、效率、迁移成本和 Staging 验证全部达标后才可进入候选。

## 6. 第三阶段：真实 Runtime 验证

测试顺序：

```text
Syntax
→ Import
→ Startup
→ Health
→ Database
→ API Smoke
→ Routes
→ Core Pages
→ Scheduler
→ Reports
→ Risk
→ Events
→ Analytics
→ Frontend
→ E2E
→ Browser Runtime
→ Restart
→ Recovery
→ Regression
```

不能用“compileall PASS”代替完整运行验证。

## 7. Browser Runtime 边界

Playwright/Selenium 只验证浏览器基础设施、测试页面、启动/连接/截图/重启等能力。

当前阶段不得为了测试而反复登录真实平台账号，不得把平台账号行为作为 Staging 自动化测试前置条件。

小红书/RedNote 逻辑保持 Platform Adapter 边界；未来合法 API/数据源/Provider 可以替换 Adapter，不应污染 Core。

## 8. 代码包治理

每个代码包必须分类：

```text
ACTIVE
STABLE
LEGACY
DEPRECATED
EXPERIMENTAL
DUPLICATE
UNUSED
```

删除流程固定为：

```text
发现候选
→ 引用扫描
→ 调用链扫描
→ 运行依赖扫描
→ 替代实现确认
→ Staging 回归
→ Evidence
→ 删除
```

不得边开发边大批量删除。

## 9. UI/UX 治理

当前 UI 已完成一轮升级，本阶段不再进行无必要的视觉重构。

重点治理：

- 新旧 CSS 覆盖
- JS 重复初始化
- 页面层级冲突
- `!important` 补丁链
- 响应式冲突
- 旧 UI 包引用
- 新 UI 被旧包覆盖

统一目标：

```text
Foundation
→ Components
→ Pages
→ Responsive
→ Theme
```

旧包先标记/验证，再删除；不得直接覆盖。

## 10. Adapter / Provider 治理

统一三类边界：

```text
Collector Adapter
Browser Adapter
AI Provider
```

业务 Core 只依赖稳定的数据/能力接口，不直接绑定单一平台、浏览器或模型实现。

## 11. Evidence 数据库

所有测试/生产故障/修复都必须沉淀 Evidence：

```text
id
project
version
commit
timestamp
test_type
test_name
result
environment
logs
artifacts
root_cause
resolution
```

状态统一：

```text
PASS
FAIL
ENV
GAP
REGRESSION
REJECTED
```

真实生产故障必须转化为 Regression Case。

## 12. SICI Research Database

研究成果不得只停留在聊天记录。统一记录：

```text
research_id
source
category
technology
case
finding
evidence
benchmark
recommendation
confidence
status
```

状态：`NEW / RESEARCHING / VERIFIED / CANDIDATE / ADOPTED / REJECTED`。

只有 VERIFIED/CANDIDATE 且经过 DCC 评估的成果才能进入工程变更候选。

## 13. DCC Change Map

每次跨模块/跨仓库变更先生成：

```text
Change
→ Affected Repositories
→ Affected Modules
→ Dependencies
→ Risk
→ Tests
→ Rollback
→ Release Gate
```

DCC 保持现有安全边界：READ/TASK/AUDIT 可用；TEST 受控；WRITE/DEPLOY 不得因本方案自动开放。

## 14. Git / 版本保护

每次施工：

- 一个明确 TASK ID。
- 一个明确目标。
- 一个最小变更集。
- 一个可回滚 Commit。
- 先 Diff，再 Regression。

不得出现 README、代码、Runtime 指向不同版本的情况。

## 15. 固定豆包施工格式

每次任务必须输出：

```text
TASK ID
VERSION
BASELINE
OBJECTIVE
CURRENT STATE
EVIDENCE
ROOT CAUSE
AFFECTED FILES
ADD
MODIFY
ADAPT
DEPRECATE
DELETE
DATABASE IMPACT
BACKEND
FRONTEND
UI/UX
SECURITY
ZBC IMPACT
DCC IMPACT
SICI IMPACT
TEST
REGRESSION
EVIDENCE LOCATION
ROLLBACK
RELEASE GATE
COMMIT
RESULT
```

没有内容写 `NONE`，不得省略字段。

## 16. Release Gate

达到以下条件立即上线：

```text
无 P0
核心业务 PASS
数据库 PASS
API PASS
页面 PASS
E2E PASS
Browser Runtime PASS
Restart PASS
Backup PASS
Rollback PASS
Staging PASS
```

P2/P3 优化不得阻塞当前生产上线。

## 17. 上线后的持续学习

Production 产生的：

- 运行日志
- 性能数据
- 数据质量
- 故障
- 修复记录
- 用户反馈
- 采集结果

进入 Production Knowledge Base，并持续反馈给 SICI Research 与 DCC Regression。

最终闭环：

```text
Research
→ DCC Verify
→ Staging
→ Release
→ Production
→ Evidence
→ Regression / Research
→ 下一版本
```

## 18. 本文件与现有基线的关系

本文件为**增项融合文件**。

如与现有 `CURRENT_BASELINE.md`、`docs/MASTER_DEVELOPMENT_BASELINE.md` 等生产事实发生冲突：

1. 不自行覆盖旧规则。
2. 停止相关变更。
3. 生成 Change Map。
4. 由 DCC 审核冲突。
5. 明确后再更新正式基线。

本文件不得成为新的代码覆盖源。

## 19. 当前执行顺序

```text
PHASE 1  Inventory
PHASE 2  Staging Runtime
PHASE 3  Baseline Runtime Test
PHASE 4  Evidence / Audit Matrix
PHASE 5  P0/P1 最小修复
PHASE 6  Regression
PHASE 7  公网部署
PHASE 8  24h Stability
PHASE 9  Release Gate
PHASE 10 Production
PHASE 11 Knowledge / Regression Loop
```

**当前优先：PHASE 1 → PHASE 2 → PHASE 3。不得跳过。**
