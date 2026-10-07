# 2026-10-08 Codex 工具维护与前端审计采用

本记录为已执行证据，不能替代 AGENTS、Experience 或当前派工。用户最新要求 M 先更新，其余窗口等确认。原附件 SHA256 `9ddd5bb4884e46c2afb05989b8de4e576b4bbaf0fe9bf3c837620dcc1616be2e`，全文已读并登记材料清单。

## 官方更新复核与采用

| 官方原文 | 核实的适用点 | 归属及处置 |
|---|---|---|
| [Codex 0.160.0](https://github.com/openai/codex/releases/tag/rust-v0.160.0) | 会话续接、设置/权限保留、排队消息恢复与去重 | OFFICIALLY_RELEASED；M/C6沿现有恢复合同采用，不新增运行时 |
| [Codex 0.160.1](https://github.com/openai/codex/releases/tag/rust-v0.160.1) | 远端 stdio MCP 保留 Windows 必需环境变量 | OFFICIALLY_RELEASED / ALREADY_IMPLEMENTED 于旧CLI；不因此恢复旧Cloud任务 |
| [Codex 0.161.0](https://github.com/openai/codex/releases/tag/rust-v0.161.0) | 会话/权限续接、MCP登录、Windows与网络重试修复 | OFFICIALLY_RELEASED / ADAPT_NOW：原npm安装升至稳定0.161.0；未启用实验特性或更改模型 |
| [10/2 iOS 1.2026.267 与 10/7 iOS 1.2026.272](https://learn.chatgpt.com/docs/changelog) | 排队取消保留输入、任务链接、设备/工作树接续和审批呈现 | OFFICIALLY_RELEASED / ACCOUNT_OR_ENV_REQUIRED；手机实际版本、配对及操作 NOT_VERIFIED；不宣称代更新 |
| [GPT-6 Intelligent UI](https://openai.com/index/gpt-6-for-everyone/) | 根据任务组合文字/图形/可操作成果；Chat更新不自动切换Work/Codex模型 | ADAPT_NOW规则；F/C1-C6实现WAIT_DEPENDENCY，详见同目录 INTELLIGENT-UI-ADOPTION |
| [官方开发命令](https://learn.chatgpt.com/docs/developer-commands) | CLI更新与Git市场刷新是不同操作；列表不证明插件实际连接 | 已对照本机help；沿现有安装维护，不新建账号或扩大权限 |

原文研究日期2026-10-08。以上是限定日期/主题的原文核对，不冒称逐篇穷尽全部历史发布。

## 本地实际结果

- `codex --version`：0.160.1 → **0.161.0**。npm官方latest与GitHub正式版本一致，使用原 `D:/devtools/npm-global` 安装，入口仍 `D:/devtools/bin/codex.cmd`，没有增加并行CLI安装。
- 已私下备份原CLI包和两级配置，目录受当前用户/SYSTEM ACL保护：`~/.codex/backups/maintenance-20261008`。未备份/输出账号Token；不向Git发布原配置或doctor完整本地报告。
- 用户/项目 `config.toml` 全文件hash均未改变。没有改模型、effort、tier、登录方式、权限、VPN、系统代理、DNS、防火墙或Git身份。doctor读取的是CLI默认配置，不证明当前聊天后端模型；人工选择保持。
- 安装一致性、配置加载、桌面app-server handshake、现有ChatGPT认证配置、HTTP可达和WebSocket101检查通过。工程MCP、OpenAI文档MCP、Node工具实际只读调用成功。
- **45个已安装插件**版本/启用状态前后一致。Git marketplace upgrade 返回0个可选Git市场、0个更新、0个错误；现有内置/远端托管市场和本地AE Method不是此命令可升级的Git市场。没有批量重新安装、权限提升或新OAuth。托管插件是否另有可用更新仍 NOT_VERIFIED。
- 桌面信息检查为 **unavailable**：Windows Store需要安装资格检查，可能触发下载。当前工具报告26.1002.51308/build13417；未下载、重启或声称最新。正在使用的桌面进程未被中断。
- 当前仓库及项目读取正常；升级不更改产品源码/DB。该批次另有明确产品代码修复，不能把整仓dirty全部归因于工具升级。

## 保留的限制和准确下一步

1. 独立CLI后台daemon控制socket连接被拒绝；桌面app-server handshake通过。这是两个不同运行入口。未重启/重建daemon，不能称远程控制已恢复；需要中断现有会话的修复必须在安全检查点取得精确批准。
2. standalone CLI的node_repl检查缺少 `CODEX_WINDOWS_REGISTERED_CORE`；当前桌面实际Node工具调用成功。不凭诊断新增全局变量或关闭可用工具。
3. doctor报告历史rollout与索引数量不一致，部分Dev Drive/Defender检查未核实。未修改/迁移/删除历史会话、数据库或安全设置。
4. 未重开历史用户会话、验证全部连接器的账号权限、手机端操作或Remote Control配对；这些保持NOT_VERIFIED，现有会话可持续操作并不等于全部恢复用例通过。
5. Figma工程/节点/版本未连接核实，保持NOT_VERIFIED；F后续须按已有规范在获得访问与PO确认后执行，不能用PNG/伪造.fig代交付。

详细去敏版本、插件及诊断分类见同名JSON。没有新付费资源、平台登录、产品窗口派工或生产DB写入。
