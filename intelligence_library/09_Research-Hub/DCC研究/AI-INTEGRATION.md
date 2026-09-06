# AI Integration Guide — Development Command Console Local AI Bridge

## 概述

Local AI Bridge 使豆包、Codex、Claude 等 AI Agent 可以通过受控本地端口与 Development Command Console 通信。

**核心原则：AI 不直接获得写权限。**

## 安全边界

| 权限 | 状态 | 说明 |
|------|------|------|
| READ | ALLOW | 读取仓库、分支、Commit、Diff、Workflow |
| TASK | ALLOW | 创建工程任务合同 |
| AUDIT | ALLOW | GitHub 只读审计 |
| TEST | CONTROLLED | 仅读取测试状态，不执行未知代码 |
| WRITE | DENY | 禁止 Commit / Push / Merge / 删除文件 |
| DEPLOY | DENY | 禁止自动部署生产 |

**绝对禁止：**
- 不建立万能 shell/exec/run 接口
- 不把 GitHub Token 放入前端 / localStorage / URL
- 不默认监听 0.0.0.0（仅 127.0.0.1）
- 不自动 Merge / 自动生产部署
- source 标签不代表权限

## 第一步：启动 Bridge

```bash
npm install
npm run bridge
```

预期输出：Version 0.3.0, Listening http://127.0.0.1:8787

验证：`curl http://127.0.0.1:8787/health`

## 第二步：AI 探测 Bridge

```
GET http://127.0.0.1:8787/api/ai/ping
```

响应：`{"ok":true,"bridge":"ready","protocol":"dcc-ai-bridge/0.3"}`

## 第三步：AI 读取自身权限

```
GET http://127.0.0.1:8787/api/ai/capabilities
```

响应包含：permissions (task.create, github.read, github.audit, test.read), denied (github.push, github.commit, github.merge, production.deploy, shell.exec, code.execute), permissionMatrix (READ=ALLOW, WRITE=DENY, DEPLOY=DENY)

## 第四步：创建工程任务

```
POST http://127.0.0.1:8787/api/ai/task
Content-Type: application/json

{"request":"自然语言需求","source":"doubao"}
```

响应（201）：task (7字段合同 + id + level L1 + evidence), executionPolicy (权限矩阵 + 8条规则), evidenceRequired: true

允许的 source：doubao, codex, claude, local-agent, unknown

## 第五步：GitHub 只读审计

- `GET /api/audit/repository?repo=owner/name`
- `GET /api/audit/branches?repo=owner/name`
- `GET /api/audit/commits?repo=owner/name&per_page=10`
- `GET /api/audit/commit?repo=owner/name&sha=xxx`
- `GET /api/audit/workflows?repo=owner/name&per_page=5`

所有响应包含 evidence 字段（source, repository, branch, commitSha, checkedAt）

## 错误处理

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

## 手机端注意

127.0.0.1 代表当前运行 Bridge 的那台设备。iPhone ≠ 电脑 localhost。V0.3 仅保证 AI Agent → 同一台电脑 → 127.0.0.1:8787。如需局域网访问需 V0.4。禁止为了手机访问把 V0.3 暴露到公网。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DCC_HOST | 127.0.0.1 | 监听地址（禁止 0.0.0.0） |
| DCC_PORT | 8787 | 监听端口 |

## 完整接入流程（豆包示例）

1. 用户要求豆包执行开发任务
2. 豆包 GET /api/ai/ping → 确认 Bridge 在线
3. 豆包 GET /api/ai/capabilities → 确认自身权限
4. 豆包 POST /api/ai/task → 创建工程任务合同
5. 豆包 GET /api/audit/repository → 读取目标仓库状态
6. 豆包根据任务合同和仓库状态生成 AI 开发执行指令
7. 豆包不自动 Commit/Push/Merge，将指令和证据交给人工验收
8. 人工确认后由人工或受控流程执行写操作

---
最后更新：2026-08-30 · v0.3 Local AI Bridge
