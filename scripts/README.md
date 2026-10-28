# Repository scripts｜仓库脚本

`scripts/` contains existing Python and PowerShell engineering, verification, and runtime entrypoints. It is a tooling directory, not a product surface or a separate owner of business, data, permission, or runtime truth.

`scripts/` 存放现有 Python 与 PowerShell 工程、验证及运行入口。它是工具目录，不是产品表面，也不另行拥有业务、数据、权限或运行时事实。

## Directory map｜目录导航

| Path / 路径 | Contents / 内容 |
| --- | --- |
| `scripts/audit_tools/` | Governance, boundary, database-authority, and Experience validators / 治理、边界、数据库权威与体验校验器 |
| `scripts/inventory/` | Repository asset inventory utilities / 仓库资源清单工具 |
| `scripts/data_candidates/` | Candidate data and manifests, not executable entrypoints / 候选数据与清单，不是可执行入口 |
| `scripts/` | Existing focused Python and PowerShell tools / 现有 Python 与 PowerShell 专项工具 |

Use each script's source or `--help` for its exact arguments and effects. Examples of current entrypoints:

```powershell
# From the repository root: validate the AI-native constitution gate
python scripts/audit_tools/verify_ai_native_constitution.py

# From the repository root: run the repository test entrypoint
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1 -Quick
```

`run_tests.ps1` uses the repository `.venv` and runs Python syntax checks plus pytest; `-Quick` enables fail-fast behavior and a per-test timeout, while `-StagingUrl` additionally probes the supplied URL. The canonical Windows Product Core launcher is [`start_production.ps1`](start_production.ps1), whose package runtime dependencies are declared in [`../requirements.txt`](../requirements.txt).

`run_tests.ps1` 使用仓库 `.venv`，执行 Python 语法检查与 pytest；`-Quick` 启用遇错即停和单测超时限制，传入 `-StagingUrl` 还会探测对应地址。Windows Product Core 的规范启动入口是 [`start_production.ps1`](start_production.ps1)，其运行依赖声明在 [`../requirements.txt`](../requirements.txt)。

Python dependency manifests at the repository root:

- [`requirements.txt`](../requirements.txt) — Product Core/runtime dependencies.
- [`requirements-dev.txt`](../requirements-dev.txt) — development and test dependencies layered over runtime dependencies.
- [`requirements-browser-use.txt`](../requirements-browser-use.txt) — isolated browser-use dependency set; it is separate from the Product Core runtime.

仓库根目录的 Python 依赖清单：

- [`requirements.txt`](../requirements.txt) — Product Core/运行依赖。
- [`requirements-dev.txt`](../requirements-dev.txt) — 在运行依赖之上的开发与测试依赖。
- [`requirements-browser-use.txt`](../requirements-browser-use.txt) — 隔离的 browser-use 依赖，与 Product Core 运行环境分开。

## Product and engineering references｜产品与工程权威

- [Repository instructions](../AGENTS.md)
- [Current source and acceptance](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)
- [Product Architecture](../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
- [Experience Constitution](../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)

具体脚本的职责和边界以源码及以上唯一权威为准；本 README 仅提供目录与依赖入口。
