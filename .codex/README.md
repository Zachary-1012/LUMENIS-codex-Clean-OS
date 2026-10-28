# LUMENIS engineering tools

This page documents repository-controlled developer tools under `.codex/`. It is not a product plan, source-owner map, task router, model-selection policy, or live status record. Repository-wide development instructions are owned by [`../AGENTS.md`](../AGENTS.md); exact product source paths are indexed in [`../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`](../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md).

本页只说明仓库受控的开发工具入口，不是产品规划、源码 Owner 索引、任务路由、模型选择规则或运行状态记录。仓库开发规则唯一入口为 [`../AGENTS.md`](../AGENTS.md)，产品源码精确路径见[源码 Owner Index](../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)。

## Tool entry points / 工具入口

| Path | Purpose |
| --- | --- |
| `engineering.py` | Existing bounded engineering CLI, including `continuity` and `verification_run`; these interfaces consume the current Owner record and the repository's existing verification policy. |
| `local_workflow.py` | Selected-file local engineering actions, invoked through `scripts/local_development.ps1` and the checked-in VS Code tasks. |
| `hooks/` | Repository hook implementation and portable examples. A tracked hook source does not prove that a workstation registered or trusted it. |
| `mcp/` | Repository source for the optional LUMENIS engineering MCP server. Local SDK installation and registration are workstation configuration. |
| `tests/` | Regressions for these developer tools; test execution follows the current repository instructions and machine policy. |

| 路径 | 用途 |
| --- | --- |
| `engineering.py` | 现有有界工程 CLI，包含 `continuity` 与 `verification_run`；接口读取现有 Owner 记录并遵循仓库验证策略。 |
| `local_workflow.py` | 对选定文件执行本地工程操作，由 `scripts/local_development.ps1` 和已跟踪的 VS Code Tasks 调用。 |
| `hooks/` | 仓库 Hook 实现和可移植示例。源码受控不表示某台工作站已注册或信任它。 |
| `mcp/` | 可选 LUMENIS 工程 MCP Server 的仓库源码。本地 SDK 安装和注册属于工作站配置。 |
| `tests/` | 开发工具的回归；执行须遵循仓库当前规则和机器策略。 |

## Owner continuity record / Owner 接续记录

The existing Owner record has one `continuity` object. Its required fields are `owner`, `objective`, `po_source`, `constraints`, `completed`, `remaining`, `next_action`, `pending_effects`, `source_paths`, `evidence_paths`, and `native_goal`. The optional `delivery` object uses `schema_version: 1` and has `status`, `po_source`, `scope_sources`, and `requirements`, with optional `exit` and `effect_ledger`. Each requirement carries `id`, `outcome_class`, `acceptance`, `coverage_refs`, `status`, and `evidence`. The optional `execution` object uses `schema_version: 1` and has `status`, `role`, `po_source`, `allowed_writes`, and `approved_calls`. These are the current tool input fields, not a second source of product scope or live execution state.

现有 Owner 记录包含一个 `continuity` 对象，必需字段包括 `owner`、`objective`、`po_source`、`constraints`、`completed`、`remaining`、`next_action`、`pending_effects`、`source_paths`、`evidence_paths` 和 `native_goal`。可选 `delivery` 使用 `schema_version: 1`，包含 `status`、`po_source`、`scope_sources`、`requirements`，并可选 `exit`、`effect_ledger`。每项 requirement 包含 `id`、`outcome_class`、`acceptance`、`coverage_refs`、`status` 和 `evidence`。可选 `execution` 使用 `schema_version: 1`，包含 `status`、`role`、`po_source`、`allowed_writes` 和 `approved_calls`。这些是现有工具的输入字段，不是另一套产品范围或实时执行状态。

Read or save through the existing CLI:

```powershell
python -X utf8 .codex/engineering.py continuity --params '{"mode":"read"}'
python -X utf8 .codex/engineering.py continuity --params '{"mode":"save","record":"work/<existing-owner-record>.json","section":"continuity"}'
```

The command uses the current native session identity. `save` names an existing Owner record and exact top-level section; the tool validates the record and source scope before writing. The record schema has no credential fields. See [`../AGENTS.md`](../AGENTS.md) for the repository development route.

读取或保存使用现有 CLI：

```powershell
python -X utf8 .codex/engineering.py continuity --params '{"mode":"read"}'
python -X utf8 .codex/engineering.py continuity --params '{"mode":"save","record":"work/<existing-owner-record>.json","section":"continuity"}'
```

命令使用当前原生会话身份。`save` 指定已有 Owner 记录及其顶层 section；工具会在写入前校验记录和源码范围。该记录结构没有凭据字段。仓库开发路径见 [`../AGENTS.md`](../AGENTS.md)。

## Selected verification receipt / 选定验证回执

`verification_run` accepts a JSON parameter object with `kind` (`compile`, `static`, or `test`), an argv array, and `timeout_seconds`. It records the subprocess outcome and the source/policy pins required by its implementation. Its current Owner binding and allowed check set are enforced by the tool and current machine contract; a receipt is engineering evidence, not product acceptance.

```json
{"kind":"<compile|static|test>","argv":["<executable>","<argument>"],"timeout_seconds":60}
```

`verification_run` 接收含 `kind`、argv 数组和 `timeout_seconds` 的 JSON 参数对象，并按工具实现记录子进程结果及源码/策略版本 pin。当前 Owner 绑定和允许的检查类型由工具及机器合同校验；回执是工程证据，不等于产品验收。

The CLI consumes argv as a JSON string array; its receipt records that selected command execution. Consult `engineering.py` when the input schema changes. Product outcome and operation records remain with their existing owners.

参数中的 `kind` 只接受 `compile`、`static` 或 `test`，命令按 argv 数组传入，时限用 `timeout_seconds` 指定。源码/策略 pin 和现有 Owner 绑定由工具与机器合同校验；回执只记录工程验证结果。

CLI 的 argv 是 JSON 字符串数组，回执记录所选命令的执行结果。输入结构变更时以 `engineering.py` 为准；产品成果及外部操作记录仍归既有 Owner。

不要将用户数据拼成 shell 命令；按 CLI 要求显式传入 argv 字段。命令结构变更时以 `engineering.py` 为准。验证回执不得用于添加或重放外部操作。

## Local workflow actions / 本地工作流动作

The existing local workflow exposes `snapshot`, `check`, `diff`, `format-preview`, `format-apply`, `rollback`, `locale-preview`, and `build`. `format-apply` accepts `--manifest`; `rollback` accepts `--receipt` for a prior successful apply receipt. The format manifest shape is:

```json
{
  "head": "<current verified HEAD>",
  "owner": "<existing owner>",
  "reservation_path": "<current reservation path>",
  "reservation_sha256": "<current reservation SHA-256>",
  "paths": [
    {"path": "<exact repository-relative file>", "preimage_sha256": "<file SHA-256>"}
  ]
}
```

The tool checks the current reservation, exact file set, and preimage hashes. The source parser is the exact CLI contract; package-specific instructions remain in [`../app/README.md`](../app/README.md), [`../website/README.md`](../website/README.md), and [`../scripts/README.md`](../scripts/README.md). Workstation-only tool paths, receipts, hook trust and editor installation state do not belong in portable repository documentation.

现有本地工作流动作包括 `snapshot`、`check`、`diff`、`format-preview`、`format-apply`、`rollback`、`locale-preview` 和 `build`。`format-apply` 接受 `--manifest`；`rollback` 通过 `--receipt` 指定先前成功的 apply 回执。清单字段示例如上。工具按现有 reservation、精确文件集合和文件改动前 SHA-256 校验；CLI 以源码解析器为准。项目说明见 [`../app/README.md`](../app/README.md)、[`../website/README.md`](../website/README.md) 和 [`../scripts/README.md`](../scripts/README.md)。工作站专属工具路径、回执、Hook 信任和编辑器安装状态不写入可移植仓库文档。
