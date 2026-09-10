# CODEX_ENVIRONMENT_REPORT
generated: 2026-09-10 12:51:54  (read-only inventory; 本轮未安装/升级任何依赖)

## 运行时
| 组件 | 已装 | 需要/备注 |
|---|---|---|
| Python | 3.14.7 | 注意版本较新,部分包兼容性需验证 |
| Node.js | v22.23.2 | |
| npm | 10.9.8 | |
| pnpm | MISSING | 项目用npm即可(package.json scripts: search/inject/login; name=taikoo-monitor 为legacy命名) |
| node_modules | 缺失(False) | 前端依赖未安装,需要时 `npm install`(Codex执行) |
| .venv | 缺失(False) | 无项目虚拟环境 |
| Ollama | 已安装 ollama.exe | `ollama list` 在本会话挂起,本地模型清单=UNKNOWN,不阻塞 |
| OpenCode | 存在(sandbox node) | 本地AI,云AI不得成启动硬依赖 |
| Playwright(python) | MISSING | Critical E2E方案需先决策是否安装(TST-003/RUNTIME-GATE-1) |

## Python 关键包
| 包 | 状态 |
|---|---|
| flask | 3.1.3 OK |
| SQLAlchemy | 2.0.52 OK |
| alembic | 1.19.2 OK |
| openpyxl | 3.1.5 OK |
| requests | 2.34.2 OK |
| httpx | 0.28.1 OK |
| pytest | 9.1.1 OK |
| python-dotenv | **MISSING(import dotenv 失败→3测试失败)** |
| tenacity | **MISSING(→2测试失败)** |
| pandas / numpy | MISSING |
| schedule / apscheduler | MISSING(后台调度相关) |
| websocket-client | MISSING |
| zhipuai / openai | MISSING(云AI SDK,离线降级不依赖) |
| sklearn | MISSING |

requirements.txt 声明 28 个依赖;以上 MISSING 项需 Codex 在兼容环境按需安装并锁版本,禁止为"更先进"升级技术栈。

## 密钥 / .env
- Z-Brand-Core 内 **无 .env**;真实智谱 key 位于 D:\Taikoo-monitor-new\.env(本轮未读取/未打印任何值,后续也禁止回显)。
- app.py `_load_dotenv` 只填充环境变量中不存在的 key;conftest 已注入测试专用隔离凭证。

## Git / 网络
- git 全局代理已设 http://127.0.0.1:7890(http+https),五私库 ls-remote 全部可达。
- 豆包会话沙箱曾禁止 git 写对象；**当前 handoff 文档包已由 ChatGPT GitHub connector 推入 `handoff/codex-zero-discovery-ready-20260910`**。但本地活动仓的 `app_evidence.py + audit/p0d + 两个 P0-D 脚本` 仍需 Codex 执行 GIT-002 在用户可写终端安全备份，不得假装已同步。

## 验证命令
- 版本: `python --version`; `node -v`; `npm -v`; `python -m pip show flask`
- 测试: `python -m pytest tests -m "not online" -q`(conftest 自动隔离,无需手工设DB)
