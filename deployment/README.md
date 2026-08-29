# v5.6.3 部署中心

- `start_local.bat`：本机启动，127.0.0.1:8200
- `start_remote.bat`：Basic Auth 检查 + Cloudflare Quick Tunnel
- `health_check.py`：服务、数据库、cloudflared 状态检查
- `backup.py`：SQLite 在线一致性备份

升级时只覆盖代码，不覆盖公司电脑已有的 `.env`、`data/monitor.db`、`data/backups`、`.venv`。
