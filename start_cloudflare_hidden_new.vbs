' ============================================================
' Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
'  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
'     powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
'  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
' ============================================================
' 广州太古汇舆情监测系统 - Cloudflare开机自启动（隐藏窗口）
' 指向新路径 D:\Taikoo-monitor-new
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Taikoo-monitor-new"
WshShell.Run chr(34) & "D:\Taikoo-monitor-new\start_cloudflare_stable.bat" & chr(34), 0, False
