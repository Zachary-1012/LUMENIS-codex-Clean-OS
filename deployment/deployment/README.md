# 部署与远程访问

## 本地
双击 `启动系统.bat`。

## 手机 5G / 公网演示
双击 `启动远程访问.bat` 或根目录 `start_remote_5g.bat`。

要求：
- `.env` 配置 `TAIKOO_AUTH_USER` / `TAIKOO_AUTH_PASSWORD`
- `cloudflared` 已安装
- 电脑保持开机并联网

## 健康检查
访问：`/api/system/health`

它用于区分：
- 网站是否运行
- SQLite 是否正常
- 最近一次有效数据时间
- AI 是否可用
- 全网发现是否启用

## 备份
使用 `数据库备份.py` 或系统 `/api/backup`。原数据库不删除、不重建。
