# LUMENIS GitHub / Skill / MCP Contract V1

> 本文是当前实现的边界契约，不把源码存在、来源预检或页面可见误写成已连接、已安装或已上线。

## 1. 三个对象必须分离

```text
GitHub Connector
  = 用户授权后的仓库访问连接；负责身份、仓库白名单和 GitHub API 读取

Skill
  = 可发现、可验证、可注册、可安装、可执行的能力包；来源可以是 LUMENIS 自有或第三方

MCP
  = Skill/工具可选使用的传输协议（stdio / Streamable HTTP / SSE 等）；不是产品线、不是 Skill 注册表、不是权限本身
```

## 2. GitHub 连接模型

```text
User consent
  -> GitHub App user-to-server authorization / installation selection
  -> external secret provider
  -> explicit repository allowlist
  -> read-only GitHub API
  -> GitHub Adapter
  -> Evidence / Canonical Data / AI / CTH / BMP / Shared
```

当前实现：

- `github_connector.py` 只接受进程外凭证提供器，不保存、打印或返回 Token。
- API 路径只允许 `/user`、仓库搜索和白名单仓库下的 `/repos/{owner}/{repo}/...`。
- `platform_adapters/github.py` 负责平台字段映射，不把 GitHub 字段泄漏到 CTH/BMP/Shared 的业务契约。
- 默认 `write_enabled=false`。提交、合并、发布等外部写动作不由本连接器执行。
- `/api/system/account/connectors/github/status` 仅向主账号返回脱敏连接状态。
- `authorization-url` 只生成带 CSRF state 的授权请求；state 的持久化、回调核验和 Token 交换必须由宿主账户/凭证层完成，当前不能将此接口解释为已连接。

状态语义：

| 状态 | 含义 |
| --- | --- |
| `NOT_CONFIGURED` | 没有 App 授权配置或外部凭证 |
| `READY_FOR_AUTHORIZATION` | 已有授权入口配置，但用户授权/凭证还未验证 |
| `CONNECTED` | 外部凭证提供器能提供凭证；仍需 `/user` 健康检查证明可用 |
| `SESSION_EXPIRED` | GitHub 返回认证/权限失败 |
| `BLOCKED` | 仓库或 API 路径未通过白名单 |
| `PROVIDER_UNAVAILABLE` | GitHub 网络/API 暂时不可用 |

## 3. Skill 生命周期

```text
source
 -> discover
 -> manifest parse
 -> compatibility
 -> security review
 -> permission approval
 -> quarantine/install
 -> isolated self-test
 -> registry
 -> router
 -> Evidence / Evaluation / Audit / Trace
```

当前实现先收敛来源事实：

- 识别 LUMENIS `skill.json` 和 Agent Skills 标准 `SKILL.md`。
- `SKILL.md` 至少验证 `name` 与 `description`；没有声明版本时用 `source revision/digest` 做来源锚点，不伪造发布版本。
- 支持本地目录、独立 `SKILL.md`、ZIP 一级目录和 GitHub 仓库/Skill 路径的只读预检。
- 通过验证的本地/ZIP/`SKILL.md` 只能登记为 `disabled + not_installed`，不会下载、解压、导入、执行或授予权限。
- GitHub 远程当前只解析精确 revision；manifest 获取、隔离安装、依赖解析、自测和启用仍是后续明确门禁。

## 4. MCP 失败闭环

MCP 来源预检返回 `MCP_DISCOVERY_REQUIRED`，注册返回
`MCP_DISCOVERY_AND_APPROVAL_REQUIRED`，必须完成：

```text
server discovery
 -> tool schema review
 -> domain / endpoint allowlist
 -> requested permission review
 -> human approval
 -> isolated health/self-test
 -> versioned registration
```

MCP Server 不得直达：

- Collector Session / Cookie / CDP；
- 原始数据库；
- 未经授权的外部写动作；
- CTH/BMP/Shared 的内部实现细节。

## 5. 本轮证据与未完成项

已通过本地专项测试的只是契约和失败边界。当前没有把以下事项标记为完成：

- GitHub App 的真实用户授权回调与加密凭证库；
- GitHub 写权限、提交、推送、合并或发布；
- 任意第三方 Skill 的下载/安装/执行；
- MCP Server 的真实发现、注册、运行和生产部署；
- 公网运行、远端 CI 和线上 E2E。

原因是这些步骤需要真实账户同意、秘密管理、外部副作用和独立上线门禁；没有证据时必须保持 `UNKNOWN / NOT_CONFIGURED / BLOCKED`。

## 6. 研究依据

- [Connecting GitHub to ChatGPT](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)
- [GitHub App authorization](https://docs.github.com/en/apps/using-github-apps/authorizing-github-apps)
- [GitHub App best practices](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app)
- [OpenAI Agents SDK MCP](https://openai.github.io/openai-agents-python/mcp/)
- [Agent Skills specification](https://openagentskills.dev/docs/specification)

