# DCC V0.4.0 Change Contract

> Task ID: TASK-V040-20260831-001
> Baseline ID: ZB-PROD-2026-08-31-03
> Created: 2026-08-31
> Status: ACTIVE

## 1. 任务目标

实现 DCC V0.4.0 第一批功能：
- Repository Snapshot（仓库快照机制）
- Change Plan（变更计划）
- Remote HEAD Lock（远程 HEAD 锁定）

## 2. 目标仓库

- Repository: Development-Command-Console (Private)
- Branch: main
- Starting HEAD: 51d6a7353af4d244faa09e59fdc92a3d6a03dfd1
- Starting Version: 0.3.0

## 3. 目标文件

### 新增
- `server/snapshot.js` — 仓库快照 + Remote HEAD Lock
- `server/change-plan.js` — 变更计划生成与管理
- `tests/snapshot.test.js` — 快照模块测试
- `tests/change-plan.test.js` — 变更计划模块测试
- `docs/V04-ARCHITECTURE.md` — V0.4 架构文档

### 修改
- `server/server.js` — 注册新 API 端点（仅追加，不修改现有端点）
- `package.json` — 新增 test 脚本（test:v04）
- `docs/DEVELOPMENT-LOG.md` — 追加开发记录

## 4. 允许的操作

- 新增 server/ 下的模块文件
- 新增 tests/ 下的测试文件
- 新增 docs/ 下的文档
- 在 server.js 中追加新端点路由（不修改现有端点逻辑）
- 在 package.json scripts 中追加新测试命令
- 运行本地测试

## 5. 禁止的操作

- 修改 Z-Brand-Core 仓库任何文件
- 修改 Core 的 .gitmodules 或 pinned SHA
- 修改 DCC 的权限配置（config.js permissions）
- 修改 DCC 的安全边界（security.js）
- 修改现有 API 端点的行为
- 修改 index.html / js/ 前端代码
- 修改 .github/workflows/
- 自动 git commit / push / merge
- 自动部署
- 引入任何外部 npm 依赖
- 引入 Token / Secret / Credential
- 修改 package.json version 字段（保持 0.3.0）

## 6. 预期测试

- `tests/snapshot.test.js` 全部通过
- `tests/change-plan.test.js` 全部通过
- 现有 `tests/bridge.test.js`（36 tests）无回归
- 现有 `tests/github-audit.test.js`（46 tests）无回归
- 总计 82 + 新测试 全部通过

## 7. 预期证据

- 测试运行结果（pass/fail 计数）
- git diff（仅允许的文件发生变化）
- 安全扫描（无新增 Token/Secret）
- 权限边界验证（WRITE/COMMIT/MERGE/DEPLOY/EXEC 仍为 DENY）

## 8. 回滚策略

- 删除新增的 server/snapshot.js, server/change-plan.js
- 删除新增的 tests/snapshot.test.js, tests/change-plan.test.js
- 删除新增的 docs/V04-ARCHITECTURE.md, docs/V04-CHANGE-CONTRACT.md
- 还原 server.js 到修改前状态
- 还原 package.json 到修改前状态
- 回滚到 Starting HEAD: 51d6a73

## 9. 晋级影响

- 不影响 Core pinned SHA
- DCC 独立前进，不自动 promotion
- 完成后需人工审核，决定是否进入 V0.4.1（Evidence + Security Gate）

## 10. 验收标准

1. snapshot.js 实现 Repository Snapshot 生成
2. snapshot.js 实现 Remote HEAD Lock（锁定 + 验证）
3. change-plan.js 实现 Change Plan 生成与存储
4. server.js 注册 6 个新端点（snapshot 3个 + change-plan 3个）
5. 所有新测试通过
6. 现有 82 项测试无回归
7. 仅允许的文件发生变化
8. 权限边界未改变
9. 无新增外部依赖
10. 无新增 Token/Secret
