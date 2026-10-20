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
  -> GitHub Adapter (registered, disabled by default)
  -> formal collector task / Evidence / product UI: OPEN
```

当前实现：

- `github_connector.py` 只接受进程外凭证提供器，不保存、打印或返回 Token。
- API 来源固定为 `https://api.github.com`；API 路径只允许 `/user`、仓库搜索和白名单仓库下的 `/repos/{owner}/{repo}/...`。默认 HTTP 重定向逐跳检查 API 来源与路径，拒绝在未核验目标前转发授权头。
- `lumenis/system/collector/adapters/github.py` 负责现有平台字段映射，不把 GitHub 字段泄漏到 CTH/BMP/Shared 的业务契约。
- GitHub Adapter 仍为 `enabled = false`，也未接入现行 secondary collection 平台列表；本地可直接调用 adapter 的实现，不代表正式采集任务、Evidence 写入或界面链路已经接通。
- 默认 `write_enabled=false`。提交、合并、发布等外部写动作不由本连接器执行。
- `/api/system/account/connectors/github/status` 仅向主账号返回脱敏连接状态。
- `authorization-url` 只生成带 CSRF state 的授权请求；state 的持久化、回调核验和 Token 交换必须由宿主账户/凭证层完成，当前不能将此接口解释为已连接。

状态语义：

| 状态 | 含义 |
| --- | --- |
| `NOT_CONFIGURED` | 没有 App 授权配置或外部凭证 |
| `READY_FOR_AUTHORIZATION` | 已有授权入口配置，但用户授权/凭证还未验证 |
| `CONNECTED` | 仅在显式 `/user` 探针成功时成立；证明当前凭证识别出的用户可用，不证明任一所选仓库权限 |
| `SESSION_EXPIRED` | GitHub 返回 401，当前凭证认证失败或过期 |
| `BLOCKED` | 仓库/API 路径未通过本地白名单，或 GitHub 明确拒绝该读取权限 |
| `COOLING_DOWN` | GitHub 429，或可识别的 403 限流信号；适配器不会将其误报为认证失效 |
| `PROVIDER_UNAVAILABLE` | 凭证探针尚未完成，或 GitHub 网络/API 暂时不可用；以 `code` 区分具体原因 |
| `COLLECT_ERROR` | 响应/分页不完整或其他读取失败；不能据此宣称本次结果完整 |

单次成功读取只证明该条路径对应的请求成功，不能扩大为所有仓库权限已验证。GitHub 对不可见仓库可能返回 404；当前仍按 `NOT_FOUND` 处理，不能据此区分不存在与当前身份不可见。

### 分页、覆盖与限流

- 覆盖感知接口 `search_repositories_page_result` 与 `repository_collection_page_result` 每页最多请求 50 条，单次请求最多返回 1,000 条，最多读取 20 页（默认 5 页）。搜索还受 GitHub 搜索接口自身的结果上限约束。
- `GitHubCollectionPage` 区分本次实际读取的 `api_items_observed`、搜索接口报告的 `reported_total_count`、`pages_fetched`、`coverage_complete`、`partial_reason` 和 `next_cursor`。搜索结果在映射前按显式仓库白名单过滤；接口报告的总量不能当成用户可见的白名单结果总量。完整遍历时报告总量缺失、前后变化或与实际读取量不符会降低覆盖状态，不能把未知数改写成零或完整数。
- 到达结果数或页预算、有取消信号、后续页请求失败、响应不完整或分页链接越界时，adapter 保留已读到的项目并返回非成功状态，同时准确标记覆盖与可继续位置；部分项目不会伪装成完整结果。续页响应的 `coverage_scope` 标明这是从 cursor 起点开始的 continuation segment。
- 游标仅绑定 API 路径、查询、结果上限、仓库白名单和页号，不包含结果数据。GitHub 当前分页查询没有提供可供本接口固定的快照版本，因此各页是分别观察到的来源结果，不是事务性一致快照。游标不是用户/actor、任务或来源版本绑定的持久化 checkpoint，也不能作为跨上下文缓存键；目前调用链没有持久化这些绑定和分页进度，必须保持为集成 OPEN 项。
- 429 或明确的 403 限流信号映射为 `RATE_LIMITED` / `COOLING_DOWN`；只有存在可解析且不超过 3 秒的 Retry-After / reset 等待时，连接器才自动短等并重试一次。否则返回限流与可用的重试秒数，交由调用方处理。普通 403 映射为 `PERMISSION_DENIED` / `BLOCKED`；401 单独映射为认证失败。
- 默认 transport 在每个重定向跳次都检查 HTTPS API host、允许路径与仓库白名单，然后才继续请求。受注入的测试 opener 由离线测试直接控制，不用于生产路径。

本轮修复追踪：

| 原问题 ID | 源码位置 | 原验收关联 |
| --- | --- | --- |
| FIX-055 `E03-GITHUB-PAGINATION-50` | `github_connector.py:_collect_pages`、`lumenis/system/collector/adapters/github.py:_page_result` | S17 / S18 |
| FIX-056 `E03-GITHUB-RATE-AS-SESSION-EXPIRED` | `github_connector.py:_request_json`、`lumenis/system/collector/adapters/github.py:_error` | S17 / S18 |
| FIX-057 `E03-GITHUB-CONTRACT-STALE` | 本文第 2 节与分页、覆盖语义 | S16 / S19 |

专项离线回归位于 `tests/test_github_connector_adapter.py` 与 `tests/test_github_status_verification.py`。上述源码和单测不证明真实 GitHub 账户、仓库权限或正式采集链路已验收。

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

- GitHub Adapter 到 secondary collection 的正式任务/界面分发、actor/task/source-version 绑定的持久分页和真实 Evidence 流转；仓库授权保留文件缺失，本轮未修改 `account/api.py`。
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

