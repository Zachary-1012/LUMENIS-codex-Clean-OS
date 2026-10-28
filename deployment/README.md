# Deployment compatibility tools｜部署兼容工具

SUPPORTING COMPATIBILITY / NOT CURRENT RUNTIME AUTHORITY

`deployment/` contains retained Windows command aliases and deployment-side helper scripts. It does not define a second Product Core, database, or runtime entrypoint.

`deployment/` 保存现有 Windows 命令别名和部署辅助脚本，不另行定义 Product Core、数据库或运行时入口。

## Existing entrypoints｜现有入口

| Path / 路径 | Behavior / 用途 |
| --- | --- |
| [`start_local.bat`](start_local.bat) | Compatibility wrapper for the root `scripts/start_production.ps1` / 转发到仓库根目录的规范启动脚本 |
| [`启动系统.bat`](启动系统.bat) | Chinese compatibility alias for `start_local.bat` / `start_local.bat` 的中文兼容别名 |
| [`backup.py`](backup.py) | Backup helper using the existing database module and configured data path / 使用既有数据库模块与配置路径的备份工具 |
| [`deployment/README.md`](deployment/README.md) | Notes for retained nested compatibility files / 目录内兼容文件说明 |

The canonical Windows runtime entrypoint and its runtime dependencies are documented in [`../scripts/README.md`](../scripts/README.md). These wrapper files are not a frontend, website server, or public deployment configuration.

规范 Windows 运行入口及运行依赖见 [`../scripts/README.md`](../scripts/README.md)。这些包装文件不是前端、官网服务或公开部署配置。

## Canonical references｜唯一权威

- [Repository instructions](../AGENTS.md)
- [Current source and acceptance](../00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md)
- [Product Architecture](../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
- [Experience Constitution](../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)

产品范围、运行边界与体验要求以以上唯一权威及其导航为准；本 README 仅说明本目录内的兼容工具。
