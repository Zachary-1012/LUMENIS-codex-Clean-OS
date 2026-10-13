# Z-Brand Core · 启动入口台账与收敛方案（LAUNCHERS）

> G-LAUNCH 交付物。原则：**新增唯一对人入口 `run.ps1`，但运行期间不改、不删任何旧脚本、不改计划任务**；
> 旧入口下线必须在停机窗口，经「引用分析→改派计划任务→回归→删除」五步。

## 1. 唯一推荐入口（新增）

| 命令 | 作用 | 实测 |
|---|---|---|
| `.\run.ps1 prod`（默认） | 幂等拉起生产：转发已验证的 `scripts/start_production.ps1`（8201 看门狗 + 9223–9228 内置无头采集浏览器，带 mutex/healthz/进程守卫三重幂等） | 语法 OK；转发链路为现网在用 |
| `.\run.ps1 dev` | 前台开发直跑 `.venv python app.py 127.0.0.1:8200` | 未实测（不在运行期触发） |
| `.\run.ps1 staging` | 127.0.0.1:8301 + `XHS_PRODUCTION=false`；**端口/任务开关已隔离，独立 DB/.env/profile 待 G-STAGE**，未完成前不触发真实采集 | 预留，未实测 |
| `.\run.ps1 status` | 只读探测 8200/8201/9223 | **已实测**：8201 UP、9222 UP、8200 down |

> run.ps1 只用 .venv 解释器、不做全局 taskkill、不写死 D 盘（用 `$PSScriptRoot`）、全 ASCII 兼容 PS5.1/GBK。

## 2. 现网计划任务链路（实测 `schtasks /query`，勿运行时改动）

| 计划任务 | 实际执行 | 现状 |
|---|---|---|
| `\TaikooMonitor` | `cmd /c start /min start_system.bat`（8200 直跑 app.py + 9223 内置无头采集浏览器，无看门狗） | Enabled；实测 8200 当前 down |
| `\ZBrand-HealthGuard` | `powershell -File scripts/start_production.ps1`（8201 supervised + 9223–9228 内置无头采集浏览器，幂等） | Enabled；**当前实际生产链路** |
| `\ZBrand-GitSync-0000/0800/1800` | `.venv python scripts/daily_git_sync.py` | Enabled，每日三次版本同步 |

**技术债登记（不在运行期合并）**：8200（直跑无看门狗，profile=newaccount）与 8201（supervised，profile=profile）双实例/双 profile 并存。最终应统一为 8201 supervised 一条链；需停机窗口把 TaikooMonitor 改派 `run.ps1 prod` 后再停 8200 旧链。

## 3. 旧入口分类（共 34 个，本阶段只登记不删）

### A. 现网在用·保留不动（计划任务/看门狗依赖）
`scripts/start_production.ps1`、`run_supervised.py`、`run_production.py`、`start_system.bat`（TaikooMonitor 依赖）、`scripts/daily_git_sync.py`、`start_xhs_cookie_sync.bat`、`scripts/install_scheduled_tasks.ps1`、`scripts/install_healthguard_task.ps1`。

### B. 危险·建议停用（含全局杀进程，会误伤其它 Python）
| 文件 | 风险点（实测） |
|---|---|
| `start_stable.bat` | `taskkill /F /IM python.exe` 杀全部 python；用**全局 python**而非 .venv；版本号写死 v5.8.0 |
| `系统守护闭环_可靠版.bat` | 含 taskkill |
| `系统守护闭环_优化版.bat` | 含 taskkill |
| `系统守护闭环.ps1` | 含 Stop-Process/taskkill |

### C. 公网访问边界
当前工程无临时公网隧道启动或自动恢复入口。旧书签 `/remote` 只返回不可用状态，不读取历史外部地址；本机工作区及 canonical Core 启动不受影响。任何新公网部署需独立批准。本次仅改仓库源码，未修改工作站计划任务或运行进程。

### D. CDP / Cookie 相关·保留
`start_cdp_auto.bat`、`start_xhs_cookie_sync.bat`。

### E. 历史/重复/多版本守护·DEPRECATED 候选（下线前逐个引用分析）
`start_all.bat`、`start_lan.bat`、`start_windows.bat`、`start_v4.bat`、`启动系统.bat`、`一键启动系统.bat`、`一键安装依赖.bat`、`一键登录微博.bat`、`启动系统守护闭环.bat`、`start_system_hidden.vbs`、`check_local_ai.bat`，以及 `deployment/` 下重复的 `start_local.bat/启动系统.bat`（其中 `deployment/deployment/` 存在编码损坏的乱码文件名，列 G-CLEAN 后续）。

## 4. 收敛路线（后续，不在运行期执行）
1. 停机窗口：把 `\TaikooMonitor` 改派为 `powershell -File run.ps1 prod`，停用 8200 直跑链，统一到 8201 supervised。
2. B 类危险脚本先改名为 `.deprecated.bat` 观察一个版本，确认无人工/任务依赖后删除。
3. E 类逐个引用分析（grep 计划任务/其它脚本/快捷方式）后归档 `archive/launchers/`。
4. 全程每步：回归启动 + status 探测 + 可回滚（git 还原/改回计划任务）。

## 5. 回滚
本次仅**新增** `run.ps1` 与本文档，未改任何旧入口与计划任务；回滚 = 删除新增的 run.ps1（`git rm run.ps1` 或 `git revert <commit>`），现网链路完全不受影响。
