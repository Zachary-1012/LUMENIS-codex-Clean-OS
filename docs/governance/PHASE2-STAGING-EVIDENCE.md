# Phase 2/3 Evidence — Isolated Staging & As-Is Runtime (UPA v1.0)

- 时间：2026-08-31
- 范围：ZBC（SICI/DCC 不动）；B=轻量 Staging 已真实运行测试，A=容器 Staging 产物就绪待环境
- 生产保护：全程 8201（supervised，v5.9.9）与 9222 CDP 未中断；生产库 data/monitor.db 只读、未改结构、未清数据

## 1. 为隔离所做的最小代码改动（全部向后兼容）

| 文件 | 改动 | 生产影响 |
|---|---|---|
| `database.py` | `DB_PATH` 支持 `ZBC_DB_PATH` 覆盖，默认仍 `data/monitor.db`（abspath） | 不设变量=原路径，零影响 |
| `app.py` | 两处局部硬编码库路径统一为 `db.DB_PATH`（概览接口、`get_db()`） | 等价改写，路径不变 |
| `topic_campaign.py` | `start_scheduler()` 在 `ZBC_ENV=staging`/`XHS_PRODUCTION=false` 时不起定时线程 | 生产不设变量，照常启动 |
| `run.ps1` | `staging` 子命令：独立副本库+8301+`--no-scheduler`+关发现 | 新增分支，prod/dev 不变 |
| `scripts/staging_setup.py` | 新增：SQLite Online Backup 只读生成一致副本 | 纯新增工具 |
| `Dockerfile` / `docker/entrypoint.sh` / `docker-compose*.yml` / `.dockerignore` | 新增容器产物 | 纯新增 |

## 2. L0–L10 分层测试结果（B 轻量 Staging，已实测）

| 层级 | 检查 | 结果 | 真实证据 |
|---|---|---|---|
| L0 Syntax | `py_compile app.py database.py topic_campaign.py` | PASS | COMPILE_OK |
| L1 Import | 8301 启动加载全部模块 | PASS | 启动日志各模块「已加载/已注册」，无 ImportError |
| L2 Startup | 8301 起服 | PASS | `Running on http://127.0.0.1:8301`，横幅「自动采集：False」 |
| L3 Health | `GET /healthz` | PASS | 200 `{"ok":true,"version":"5.9.9"}` |
| L4 API Smoke | 带 Basic Auth `GET /api/notes` | PASS | 200，主体口径 total=604，返回真实笔记 |
| L5 Database | 独立副本 + 隔离铁证 | PASS | 副本 notes/events/logs=957/427/477；见下「隔离铁证」 |
| L6 Page | `/v4/console/`、`/v4/collect/` | PASS | 均 200（与 8201 行为一致；`/api/*` 与 `/` 均 401 走 Basic，符合预期） |
| L7 E2E Page | 真实内置浏览器打开 8301 控制台 | PASS | 完整渲染：12 平台采集健康、导航、Zachary 助手抽屉；478px 窄视口移动形态正常 |
| L8 Browser | Staging 不主动采集 | PASS(带注记) | 主/专题调度均关，不调用 CDP；启动期仅「探测到 9222」，登记为共享点 GAP |
| L9 Restart | 停 8301→改门控→重启 | PASS | 仅杀监听 8301 的 PID；重启后 `campaign scheduler thread disabled` 生效 |
| L10 Regression | 生产回归 | PASS | 全过程 8201/9222 仍 LISTEN、8201 healthz ok、生产 total 恒 604 未变 |

### 隔离铁证（L5，自动化探针，跑完自清理）
向 Staging 副本插入 1 条含主体词标记笔记，经 HTTP API 观察：

```
baseline total: 8301=604 8201=604
with marker:    8301=605 8201=604      # 只有 Staging 看到写入
after cleanup:  8301=604 (staging rows 957->957)  # 清理后无残留
ISOLATION_VERDICT = PASS
```

结论：8301 只读写独立副本，生产 8201 与生产库全程不受影响。

## 3. 问题分类（PASS / FAIL / ENV / GAP）

- **PASS**：L0–L7、L9、L10（见上）。
- **FAIL**：无。
- **ENV（环境受限，非代码缺陷）**：容器 `docker build/up` 未实测——本机无 docker、无 WSL 发行版、Hypervisor 未启用；装 Docker Desktop 需启用 WSL2 并重启，会中断正在运行的生产与公网，故本轮不自动安装重启。工程产物已全部就绪。
- **GAP（登记，不扩大改动）**：
  1. Staging 日志仍写公共 `logs/system.log`（进程隔离已足够，文件级隔离后续做）。
  2. Staging 启动期会探测到生产 9222 CDP，但不调用（无调度即无采集）。
  3. `G-DOCKER-LINUX`：少数旁路模块硬编码 `D:\...` 绝对路径，Linux 容器内被调用前需相对化。
  4. `G-DOCKER-WSGI`：容器暂用与本机一致的 `python app.py`，gunicorn 实测后再切。

## 4. Phase 3 原样运行结论

当前 ZBC 在「独立端口 + 独立库副本 + 禁一切自动采集」的隔离 Staging 中可原样启动、
页面/API/认证/数据/重启/生产回归全部通过，满足 UPA「Staging 与 Production 六维隔离、
XHS_PRODUCTION=false、不影响现网」的要求。容器路径待 Docker 环境补齐后出 build Evidence。
