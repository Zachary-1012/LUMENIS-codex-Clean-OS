' 广州太古汇舆情监测系统 - Cloudflare开机自启动（隐藏窗口）
' 指向新路径 D:\Taikoo-monitor-new
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Taikoo-monitor-new"
WshShell.Run chr(34) & "D:\Taikoo-monitor-new\start_cloudflare_stable.bat" & chr(34), 0, False
