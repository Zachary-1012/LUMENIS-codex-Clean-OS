# ============================================================
# Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
#  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
#     powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
# ============================================================
﻿# Cloudflare Tunnel 进程守护脚本
# 监控cloudflared进程，崩溃后自动重启
$ErrorActionPreference = "SilentlyContinue"
$cloudflaredPath = ".\tools\cloudflared.exe"
$logFile = ".\cloudflared_guardian.log"
function Write-Log($msg) {
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Value "[$time] $msg"
}
Write-Log "=== 进程守护启动 ==="
Write-Log "监控目标: cloudflared.exe"
while ($true) {
    $proc = Get-Process -Name cloudflared -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Log "⚠ cloudflared未运行，正在启动..."
        Start-Process -FilePath $cloudflaredPath -ArgumentList "tunnel","--url","http://127.0.0.1:8201","--protocol","http2","--ha-connections","4","--no-autoupdate" -WindowStyle Hidden
        Start-Sleep -Seconds 10
        $newProc = Get-Process -Name cloudflared -ErrorAction SilentlyContinue
        if ($newProc) {
            Write-Log "✓ cloudflared已重启 (PID: $($newProc.Id))"
        } else {
            Write-Log "✗ 启动失败，30秒后重试"
        }
    }
    Start-Sleep -Seconds 30
}


