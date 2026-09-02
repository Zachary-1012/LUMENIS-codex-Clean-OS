' ============================================================
' Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
'  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
'     powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
'  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
' ============================================================
' 广州太古汇舆情监测系统 - 开机自启动（隐藏窗口）
' 指向新路径 D:\Taikoo-monitor-new
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Taikoo-monitor-new"
' 启动系统服务（隐藏窗口）
WshShell.Run "cmd /c .venv\Scripts\python.exe app.py --host 0.0.0.0 --port 8200", 0, False
' 等待3秒后启动Cloudflare
WScript.Sleep 3000
WshShell.Run "cmd /c start_cloudflare_stable.bat", 0, False
