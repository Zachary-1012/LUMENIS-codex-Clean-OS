' ============================================================
' Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
'  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
'     powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
'  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
' ============================================================
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean\start_cloudflare_stable.bat" & chr(34), 0, False
