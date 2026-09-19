# Development Command Console · Product Spec

## 1. 产品定位

AI Software Engineering Command Console — 将自然语言开发需求转换为可执行、可验收、可追溯的工程任务，并提供 GitHub 只读工程审计能力和 Local AI Bridge。

不是普通聊天机器人。核心流程：自然语言需求 → 需求结构化 → 工程任务合同 → AI 开发执行指令 → GitHub 只读审计 → 代码/Commit/Diff/Test 证据 → 人工验收。

## 2. 验收等级

| 等级 | 名称 | 升级条件 |
|------|------|----------|
| L0 | Concept | 概念明确 |
| L1 | Planned | 任务合同生成 |
| L2 | Implemented | 代码完成 |
| L3 | Tested | 实际测试通过 |
| L4 | E2E Verified | 端到端验证 |
| L5 | Production | 真实生产部署 |

核心规则：没有证据，不得升级等级。

## 3. 安全边界

- 不连接生产数据库
- 不自动修改 Z-Brand Core
- 不自动部署生产
- 不自动 Merge
- 不自动修改 main
- 不自动执行未知代码
- 不接受、不存储、不展示任何 Token/Secret
- 第一版仅作为开发任务结构化 + AI 指令生成 + 验收记录工具

## 4. 任务合同字段

Goal, Scope, Must Preserve, Forbidden, Acceptance Criteria, Test Plan, Rollback Plan

## 5. AI 开发执行指令规则

不得猜测、不得虚构、不得删除现有稳定功能、不得未经确认改变业务口径、必须先读取现有代码、必须实际运行测试、测试失败不得声称完成、没有证据不得标记为完成。

## 6. GitHub 只读工程审计（V0.2）

### 6.1 Repository Reader
读取并显示：Repository, Default Branch, Visibility, 当前 HEAD, 最近 Commit, 最后更新时间。

### 6.2 Branch Reader
显示：默认分支, 分支名称, 最近 Commit。禁止修改 Branch。

### 6.3 Commit Reader
至少显示最近 10 个 Commit：Commit SHA, Commit Message, Author, Date。点击某个 Commit 可以查看详情。

### 6.4 Changed Files Reader
对于选定 Commit，显示：Added, Modified, Deleted, Renamed，以及文件路径、变更类型、增删行数。

### 6.5 Diff Reader
允许查看选定 Commit 的实际 Diff。必须明确 Actual GitHub Diff，不得由 AI 自己重新生成 Diff 冒充 GitHub Diff。

### 6.6 Workflow / Test Status Reader
如果当前 GitHub API 权限能够读取 GitHub Actions、Workflow Run、Job、Test Status、Check Status，则只读展示。如果 API 当前不能读取某项，必须显示 Unavailable + 原因。禁止猜测、缓存冒充实时、AI 推测。

### 6.7 Evidence 机制
每一项审计结果记录：Source, Timestamp, Repository, Branch, Commit SHA。

### 6.8 错误状态产品化
Repository Not Found, API Rate Limited, Unauthorized, Forbidden, Network Error, Invalid Repository, Commit Not Found, Diff Unavailable, Workflow Unavailable。不能直接显示 undefined/null/空白，也不能把错误包装成可能已经成功。

### 6.9 敏感数据过滤
js/github-audit.js 内置 filterSensitiveData()，深度过滤 19 种敏感字段名 + 5 种敏感值模式（GitHub PAT, PEM 私钥, OpenAI Key, Slack Token 等）。

## 7. 技术架构

- 纯前端单页应用：index.html + js/github-audit.js
- GitHub API：无认证调用（公开仓库，60次/小时/IP）
- 部署：GitHub Pages + GitHub Actions
- 测试：Node.js 内置 node:test
- 存储：localStorage（任务历史，最近 50 条）

## 8. 文件结构

```
Development-Command-Console/
├── index.html
├── README.md
├── package.json
├── js/
│   └── github-audit.js
├── server/
│   ├── server.js
│   ├── config.js
│   └── security.js
├── docs/
│   ├── product-spec.md
│   ├── DEVELOPMENT-LOG.md
│   └── AI-INTEGRATION.md
├── .github/
│   └── workflows/
│       ├── pages.yml
│       └── test.yml
└── tests/
    ├── README.md
    ├── github-audit.test.js
    └── bridge.test.js
```

## 9. V0.3 Local AI Bridge 功能规格

### 9.1 定位

Local AI Bridge 使豆包、Codex、Claude 等 AI Agent 可以通过受控本地端口与 Development Command Console 通信。核心原则：AI 不直接获得写权限。

### 9.2 技术方案

- Node.js 实现，零外部依赖（仅使用内置 http、url 模块）
- 默认监听 127.0.0.1:8787（不默认 0.0.0.0，不暴露公网）
- 允许通过环境变量 DCC_PORT 和 DCC_HOST 修改
- 文件结构：server/server.js, server/config.js, server/security.js

### 9.3 API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /api/status | 服务信息 |
| GET | /api/ai/ping | AI 探测 Bridge |
| GET | /api/ai/capabilities | AI 读取自身权限 |
| POST | /api/ai/task | 创建工程任务 |
| GET | /api/audit/repository | 读取仓库信息 |
| GET | /api/audit/branches | 读取分支列表 |
| GET | /api/audit/commits | 读取 Commit 列表 |
| GET | /api/audit/commit | 读取 Commit 详情 |
| GET | /api/audit/workflows | 读取 Workflow 状态 |

### 9.4 权限矩阵

| 权限 | 状态 | 说明 |
|------|------|------|
| READ | ALLOW | 读取仓库、分支、Commit、Diff、Workflow |
| TASK | ALLOW | 创建工程任务合同 |
| AUDIT | ALLOW | GitHub 只读审计 |
| TEST | CONTROLLED | 仅读取测试状态，不执行未知代码 |
| WRITE | DENY | 禁止 Commit/Push/Merge/删除文件 |
| DEPLOY | DENY | 禁止自动部署生产 |

Permission Gate 函数：canReadRepository(), canCreateTask(), canRunTest(), canWriteRepository()=false, canDeployProduction()=false。

### 9.5 AI Agent 身份

支持 source 标签：doubao, codex, claude, local-agent, unknown。source 只是身份标签，不代表拥有权限。绝不能 source=doubao → 自动获得 GitHub 写权限。

### 9.6 安全层

- CORS：只允许本地来源（http://127.0.0.1:8787, http://localhost:8787, https://zachary-1012.github.io），不使用通配符 *
- Origin 校验：非允许来源不返回 ACAO 头
- Content-Type 校验：POST 必须为 application/json，否则 415
- 请求大小限制：10KB，超过返回 413
- 速率限制：60次/分钟/IP，超过返回 429
- 敏感数据过滤：复用 github-audit.js 的 filterSensitiveData()
- 安全响应头：X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy: no-referrer
- 无万能执行接口：/api/shell, /api/exec, /api/run 均不存在
- 无 child_process，无 eval

### 9.7 Evidence

所有 Audit API 返回 evidence 字段：source, repository, branch, commitSha, checkedAt。没有证据的数据不得标记为 verified/passed/completed。

### 9.8 错误处理

| HTTP | 错误码 | 说明 |
|------|--------|------|
| 400 | INVALID_REQUEST | request 为空 |
| 400 | INVALID_SOURCE | source 不在允许列表 |
| 400 | INVALID_JSON | 请求体不是有效 JSON |
| 400 | MISSING_PARAM | 缺少必要参数 |
| 403 | PERMISSION_DENIED | 权限闸门拒绝 |
| 404 | NOT_FOUND | 端点不存在 |
| 413 | PAYLOAD_TOO_LARGE | 请求体超过 10KB |
| 415 | UNSUPPORTED_MEDIA_TYPE | Content-Type 错误 |
| 429 | RATE_LIMITED | 请求频率超限 |

### 9.9 前端 Bridge 状态

index.html 新增 section 07：Local AI Bridge 状态。显示真实 Online/Offline（调用 /api/ai/ping），不显示假 Online。提供检查连接和读取能力按钮。Bridge Offline 时显示启动指引（npm run bridge）。

### 9.10 CI 工作流

.github/workflows/test.yml：push/PR 到 main 时自动运行 github-audit 测试 + bridge 测试 + npm test。测试失败则 Workflow = failure，不得伪装成成功。

### 9.11 手机端

127.0.0.1 代表当前运行 Bridge 的那台设备。iPhone ≠ 电脑 localhost。V0.3 仅保证 AI Agent → 同一台电脑 → 127.0.0.1:8787。如需局域网访问需 V0.4 安全 LAN Bridge。禁止为了手机访问把 V0.3 暴露到公网。

## 10. 路线图

- V0.1 ✅ 任务结构化 + AI 指令生成 + 验收等级 + 历史记录
- V0.2 ✅ GitHub 只读工程审计（6 个 Reader）
- V0.3 ✅ Local AI Bridge（AI Agent 受控接入，权限矩阵，安全层，CI）
- V0.4 安全 LAN Bridge（iPhone 局域网访问）+ 自动化 E2E 测试套件
- V0.5 后端代理层（私有仓库安全访问 Token）+ Test Result 详情读取
- V0.6 形成需求 → 开发 AI → GitHub → 测试 → 审计 → 验收闭环

---
最后更新：2026-08-30 · v0.3 Local AI Bridge
