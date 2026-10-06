# ============================================================
# Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
#  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
#     powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
# ============================================================
﻿# 启动cloudflared并将输出写入日志文件
$dst = "D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean"
$cloudflared = "%~dp0tools\cloudflared.exe"
Set-Location $dst
Remove-Item "cf_stable.log" -ErrorAction SilentlyContinue

# 启动cloudflared，输出重定向到文件
& $cloudflared tunnel --url http://localhost:8201 --protocol http2 *> "cf_stable.log"

