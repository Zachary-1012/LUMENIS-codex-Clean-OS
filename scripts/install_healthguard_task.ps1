# Z-Brand Core HealthGuard installer (ASCII-only for PowerShell 5.1 / GBK compatibility).
# Registers a Task Scheduler job that runs the idempotent start_production.ps1:
#   trigger = at user logon, then repeat every 5 minutes indefinitely;
#   hosted by Task Scheduler service (parent = svchost), so it survives the end of
#   any interactive / agent shell session and re-launches 8201 watchdog or 9222 if dead.
# Runs as the current interactive user (Limited), which is required so Edge CDP has a desktop.
# Safe to run repeatedly (-Force overwrites). No admin required.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Starter = Join-Path $PSScriptRoot 'start_production.ps1'
if (-not (Test-Path $Starter)) { throw "starter not found: $Starter" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $Starter)

# AtLogon trigger + repeat every 5 minutes (repetition borrowed from a Once trigger).
$logon = New-ScheduledTaskTrigger -AtLogOn
$once  = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$logon.Repetition = $once.Repetition

$principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME) `
    -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName 'ZBrand-HealthGuard' -Action $action -Trigger $logon `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Output '[HealthGuard] scheduled task ZBrand-HealthGuard registered (at logon + every 5 min).'
Get-ScheduledTask -TaskName 'ZBrand-HealthGuard' | Select-Object TaskName, State | Format-Table -AutoSize
