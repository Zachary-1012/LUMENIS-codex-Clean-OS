# CASE-2026-0011: Dev Container 可复现验证环境研究

## 案例来源
- **来源仓库：** Zachary-1012/Development-Command-Console
- **来源文件：** `.devcontainer/devcontainer.json`
- **来源 SHA：** `878ebbf5546976cfb49238fd2bd5003022ae2c5b`
- **License：** Internal (Zachary AI Platform)
- **基础镜像：** mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm
- **维护状态：** active

## 为什么值得研究
DDC 的 Dev Container 定义了"可复现验证运行时"：Node.js 20 + Python 3.12 + SQLite + ReportLab，基于 Microsoft 官方 devcontainers 镜像。这是 DDC PLATFORM_README 第8节定义的"Verification infrastructure"的实际实现。Hub 作为纯 Python 项目，可以参考此模式建立更轻量的验证环境。

## 原项目解决什么问题
1. **可复现开发环境：** 任何开发者/Agent 打开仓库即获得一致的 Node 20 + Python 3.12 环境
2. **官方镜像基础：** 使用 `mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm`，不是自维护镜像
3. **Feature 机制：** 通过 `ghcr.io/devcontainers/features/python:1` 叠加 Python 3.12，不污染基础镜像
4. **postCreateCommand：** 自动安装 ReportLab 并验证 node/python/sqlite3 版本
5. **VSCode 扩展：** 预装 ms-python.python

## 我们可以吸收什么
| 模式 | Hub 适配方式 |
|---|---|
| 官方 devcontainers 镜像 | Hub 可使用 `mcr.microsoft.com/devcontainers/python:1-3.12-bookworm`（纯 Python，更轻量） |
| Feature 叠加机制 | Hub 如需 Node.js 可通过 feature 添加，当前不需要 |
| postCreateCommand 版本验证 | Hub 可验证 python --version 和运行测试 |
| 固定版本号 | Hub 锁定 Python 3.12，与 CI 一致 |

## 哪些不能照搬
1. **Node.js 20 基础镜像** — Hub 是纯 Python 项目，不需要 Node.js 运行时
2. **ReportLab 依赖** — Hub 不生成 PDF
3. **SQLite** — Hub 使用 JSONL 文件存储，不需要数据库
4. **DDC 的验证运行时是三仓库共享的** — Hub 不需要建立跨仓库验证环境，DDC 已经是 Owner

## 如何适配三方平台
- **Z-Brand：** 业务项目可能需要特定依赖，Dev Container 由 Z-Brand 自行维护
- **DDC：** 已有 Dev Container，是验证运行时 Owner，Hub 引用其设计原则
- **SICI：** PWA 项目需要 Node.js，可参考 DDC 的 Node 基础镜像
- **Hub：** 如需 Dev Container，使用纯 Python 3.12 镜像，不叠加 Node/SQLite/ReportLab

## 是否值得写代码
**当前不值得：**
- ❌ Hub 当前 CI 直接用 `actions/setup-python@v5`，足够覆盖测试
- ❌ 添加 Dev Container 会增加维护成本，而 Hub 没有本地开发环境一致性的强需求
- ✅ 记录此案例，未来如果 Hub 需要本地可复现环境，再创建轻量 Python Dev Container
- ✅ 在 architecture/ 中记录"Hub 不建立 Dev Container，复用 DDC 验证运行时设计原则"的决策

## 实验结果
- **实验：** 读取 DDC devcontainer.json，分析镜像、feature、postCreateCommand
- **结果：** DDC 验证运行时 = Node 20 + Python 3.12 + SQLite + ReportLab；Hub 只需 Python 3.12
- **Evidence：** DDC commit 878ebbf, devcontainer.json SHA ff4b8be9838e926bea5f472f86e1d97137847cbd
- **决策：** Hub 当前不创建 Dev Container（复杂度 > 收益），记录为 ADR

## 适配判断
- **研究价值：** medium
- **适配价值：** low（当前阶段）
- **风险：** low
- **下一步：** 在 architecture/ADR-0001-hub-no-devcontainer.md 记录此决策
