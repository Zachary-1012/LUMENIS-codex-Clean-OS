# OSAI Agent YAML 规范（蓝本）· 2026-09-03

> 提炼自 **omnigent-ai/omnigent**（Apache-2.0, 9.6k★, 2026-06）meta-harness 范式。
> 定位：OSAI 未来"工程 agent 编排"的声明式配置规范（当前 OSAI 以 zell_trace 脚本编排，
> 本文件为架构蓝本，不引入 omnigent 运行时 / Python3.12+ 依赖）。

## 一、Agent 声明式定义（agent 定义即配置）

```yaml
name: code_audit_agent
prompt: 你是 ZBC 代码审计 agent，负责闭包/死代码/契约分析。

executor:
  harness: local-python          # OSAI 内置执行器（当前为脚本级）

tools:
  # 1) 本地函数（签名自动生成 schema）
  closure_audit:
    type: function
    callable: scripts.app_closure_audit:main

  # 2) MCP 服务器（本地命令或远程 URL）
  github:
    type: mcp
    url: <github-remote MCP endpoint>

  # 3) 子代理（supervisor 可委托；子代理可 inherit 工具）
  contract_checker:
    type: agent
    prompt: 核对 Contract 验收标准
    tools:
      closure_audit: inherit
```

关键范式：
- `agent 定义即配置`：新增工程 agent = 新增一个 YAML，不写胶水代码。
- `agents can build agents`：agent 可在会话中生成新 agent YAML。
- 子代理继承工具（`inherit`），Supervisor 只做拆解/汇总。

## 二、Policies 三层治理（动作级 allow/block/ask + 预算硬上限）

```
server-wide (admin)  ─┐
per-agent   (dev)    ─┼─ 动作每次被检查: allow | block | ask(暂停询问用户)
per-session (用户)    ─┘   (更严的 session 规则优先)
```

```yaml
policies:
  ask_before_shell:
    type: function
    handler: ask_on_os_tools          # shell/文件写操作前询问
  cap_tool_calls:
    handler: max_tool_calls_per_session
    params: { limit: 50 }
  budget:
    handler: cost_budget
    params: { max_cost_usd: 5.00, ask_thresholds_usd: [3.00] }  # 硬上限+软告警
```

OSAI/ZBC 现有能力映射（不重复造轮子）：

| omnigent Policies | ZBC/OSAI 现有 | 缺口 |
|---|---|---|
| spend cap / cost budget | `scripts/ai_budget.py` + `config/ai-quota.json`（token 配额） | 动作级 ask 交互 |
| tool-call cap | 无 | 可后续按 agent 会话加 |
| ask_on_os_tools（危险操作询问） | RuntimeSwitch（运维总闸）+ 部署守则 | 会话级询问弹窗 |

## 三、Polly 范式（多 agent 编排蓝图）

- 技术负责 agent 不写码：只规划、拆解、委托。
- 编码子代理**并行 git worktree** 施工，互不阻塞。
- **跨厂商 reviewer**：diff 由不同模型的 agent 评审（避免自审盲区）。
- 人类只做 merge。

→ 对应 OSAI 目标「Zachary AI Engineering OS」的多 agent 演进路径。

## 四、落地策略（渐进，不引运行时）

1. 阶段 A（现状）：脚本级 zell_trace 编排 + Contract 25 清单。
2. 阶段 B：把高频工程动作（闭包审计/证据流转/合规门/回归）封装为 YAML 可声明的工具。
3. 阶段 C：引入轻量 YAML 解析（PyYAML 已在依赖内），实现 `agent 定义即配置`。
4. 阶段 D：Polly 式多 agent（并行 worktree + 跨模型 reviewer）。

每个阶段保持：功能零减配、数据零丢失、豆包最低、智谱主力。
