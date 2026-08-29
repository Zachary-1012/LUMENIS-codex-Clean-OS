# 启动cloudflared并将输出写入日志文件
$dst = "D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean"
$cloudflared = "%~dp0tools\cloudflared.exe"
Set-Location $dst
Remove-Item "cf_stable.log" -ErrorAction SilentlyContinue

# 启动cloudflared，输出重定向到文件
& $cloudflared tunnel --url http://localhost:8200 --protocol http2 *> "cf_stable.log"

