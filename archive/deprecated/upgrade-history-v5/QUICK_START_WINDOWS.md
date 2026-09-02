# Windows 快速启动

## 第一次安装
1. 安装 Python 3.11+、Node.js LTS。
2. 双击 `start_windows.bat`。
3. 第一次运行会自动创建 `.venv`、安装 Python 依赖、安装 npm 依赖和 Chromium。
4. 浏览器打开 `http://127.0.0.1:8200`。

## 小红书登录
项目使用持久化 Chromium profile：`%USERPROFILE%\\.skills-router\\rednote\\instances\\taikoo`。
如果该 profile 已有登录态，采集脚本会复用它；不要同时打开多个使用同一 profile 的 Chromium。

如果需要注入 Cookie，使用环境变量 `XHS_COOKIES_JSON`，不要把真实 Cookie 写入源码。

## 手机同 Wi-Fi 查看
双击 `start_lan.bat`，Windows 防火墙允许 Python/Node 在专用网络通信。
在 Windows 执行 `ipconfig` 找到 IPv4，例如 `192.168.1.23`，iPhone Safari 打开 `http://192.168.1.23:8200`。

## 远程查看（方案 B）
推荐后续配置 Cloudflare Tunnel。远程暴露前必须设置：
`TAIKOO_AUTH_USER` + `TAIKOO_AUTH_PASSWORD`。
`start_remote_cloudflare.bat` 会把本机 8200 通过 Cloudflare Tunnel 转发，不需要购买服务器。

注意：Quick Tunnel 网址是临时随机地址；如果以后需要固定网址，再配置 Cloudflare Tunnel 的固定 hostname。
