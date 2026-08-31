# Staging & Container Runbook (Z-Brand Core / CTH-POMS)

> UPA v1.0 Phase 2 产物。目标：Staging 与 Production 在端口、数据库、.env、日志、
> Cookie/Profile、任务开关六个维度全部隔离，`XHS_PRODUCTION=false`，绝不触发真实平台采集。

## 1. 两条隔离路径（A/B 都保留）

| 维度 | B. 轻量 Staging（本机，已实测） | A. 容器 Staging（产物就绪，待 Docker 环境） |
|---|---|---|
| 启动 | `.\run.ps1 staging` | `docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build` |
| 端口 | 127.0.0.1:8301 | 8301:8301 |
| 数据库 | `staging/monitor.staging.db`（生产库的在线一致副本） | 命名卷 `zbc-staging-data` 内独立库 |
| 采集开关 | `--no-scheduler` + `XHS_PRODUCTION=false` + `TAIKOO_WEB_DISCOVERY=0` | 同左（compose 注入 + `--no-scheduler`） |
| 专题定时线程 | 环境变量门控，不启动 | 同左（同一门控代码） |
| 日志 | 进程级隔离（文件仍写 logs/，已知共享点） | 独立命名卷 `zbc-staging-logs` |
| 浏览器 | 不主动采集；仅探测到 9222（不调用） | 镜像内不含浏览器，采集走外部/远程 CDP |

生产路径 `.\run.ps1 prod` 与现网计划任务完全不变。

## 2. B：轻量 Staging 操作

```powershell
# 1) 生成/刷新独立库副本（SQLite Online Backup，只读源、不锁生产）
.venv\Scripts\python.exe scripts\staging_setup.py
# 2) 起隔离 Staging（自动建副本；Ctrl+C 停）
.\run.ps1 staging
# 3) 只读状态
.\run.ps1 status
```

隔离实现（向后兼容，不设环境变量时生产行为 100% 不变）：
- `database.py`：`DB_PATH` 支持 `ZBC_DB_PATH` 覆盖，默认仍是 `data/monitor.db`。
- `app.py`：两处局部硬编码库路径统一改为 `db.DB_PATH`。
- `topic_campaign.py start_scheduler()`：`ZBC_ENV=staging` 或 `XHS_PRODUCTION=false`
  时只注册路由、不起定时采集线程。

## 3. A：容器 Staging / Production

产物：`Dockerfile`、`docker/entrypoint.sh`、`docker-compose.yml`、
`docker-compose.staging.yml`、`.dockerignore`。

```bash
# 生产形态模板
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8201/healthz

# Staging（隔离覆盖层）
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build
```

镜像安全：`.dockerignore` 排除 `.venv / node_modules / .trae-cn / data / staging /
logs / *.db / .env / edge-cdp-* / chrome-cdp-* / backups / video_frames`，镜像内
**不含任何数据库、Cookie、密钥、浏览器 Profile**；状态全部走命名卷。

## 4. 当前环境状态（诚实标注，未实测项不冒充完成）

- 本机当前：`docker` 未安装、无 WSL 发行版、`HypervisorPresent=False`、winget 可用。
- Docker Desktop on Windows 依赖 WSL2（需一次性启用「虚拟机平台 / WSL」功能并**重启**）。
  现网 8201 + 9222 + 临时公网正在运行，重启会中断生产，故本轮**不自动安装/重启**。
- 因此：容器 `docker build / up` **未实测**；已完成的是全部可提交工程产物与静态自查，
  待具备 Docker 环境（或 Linux 公网服务器）后执行上面命令出真实 Evidence。

### 容器化遗留（登记，不在本轮扩大改动）
- `G-DOCKER-LINUX`：少量旁路模块仍写死 Windows 绝对路径
  （如 `auth_recovery_center.py`、`brand_knowledge_base.py` 的 `D:\Taikoo-monitor-new\...`）。
  它们在 import 阶段只是字符串、不影响 Web 启动，但在 Linux 容器内被实际调用前需统一改为
  `ZBC_DB_PATH`/相对路径。Staging 不触发这些模块。
- `G-DOCKER-WSGI`：镜像默认用与本机一致的 `python app.py` 路径（已验证可起）；
  生产级 WSGI（gunicorn，1 worker + threads，避免定时线程重复）在实测后再切换。
- `docker compose config` 的 YAML 校验随 Docker 环境执行。
