# CODEX_ENV_BOOTSTRAP
generated 2026-09-10 21:00:25
1. Python 3.14.7;建议建.venv后 pip install -r requirements.txt(必装 python-dotenv/tenacity,其余按票,禁止为升级而升级)。
2. DB隔离: 测试conftest自动绑OS-temp ZBC_DB_PATH;手动runtime先 $env:ZBC_DB_PATH='<tmp>/monitor.db'。
3. 启动 python run_production.py(host/port打开该文件确认并回填ENV_PREFLIGHT)。
4. 探测 python scripts/verify_p0d_runtime_surface.py(已知 /healthz=200、cth=200、identity=404、bmp=404)。
5. Playwright缺失→Critical E2E方案在RUNTIME-GATE-1决策,不阻塞单元/集成。
6. 禁读/泄真实key/cookie/token。环境缺失只报告并进对应Ticket,不假设。
