# Z-Brand Core scheduled-task installer (idempotent; uses non-elevated schtasks, safe to re-run).
# Creates:
#   ZBrand-HealthGuard   every 5 min  -> idempotently re-raise 8201 supervisor + 9223-9228 headless collectors
#   ZBrand-GitSync-0800  daily 08:00  -> safe source save + rebase + push (no secrets ever)
#   ZBrand-GitSync-1800  daily 18:00
#   ZBrand-GitSync-0000  daily 00:00
# All ASCII for Windows PowerShell 5.1 GBK safety.
$ErrorActionPreference = 'Stop'

$Root = 'D:\Taikoo-monitor-new'
if (-not (Test-Path (Join-Path $Root 'app.py'))) { throw "Project root not found: $Root" }

# 1) Health guard (runs the triple-idempotent launcher every 5 minutes, detached/hidden)
$guardTr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $Root\scripts\start_production.ps1"
schtasks /create /tn "ZBrand-HealthGuard" /tr $guardTr /sc minute /mo 5 /f | Out-Null

# 2) Three daily safe git syncs (no inner quotes: project path has no spaces)
$syncTr = "cmd /c cd /d $Root && .venv\Scripts\python.exe scripts\daily_git_sync.py"
schtasks /create /tn "ZBrand-GitSync-0800" /tr $syncTr /sc daily /st 08:00 /f | Out-Null
schtasks /create /tn "ZBrand-GitSync-1800" /tr $syncTr /sc daily /st 18:00 /f | Out-Null
schtasks /create /tn "ZBrand-GitSync-0000" /tr $syncTr /sc daily /st 00:00 /f | Out-Null

Write-Output 'ZBrand scheduled tasks installed (current state):'
schtasks /query /fo table | Select-String 'ZBrand'
