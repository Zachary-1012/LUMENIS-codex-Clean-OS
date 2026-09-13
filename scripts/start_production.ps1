# LUMENIS production idempotent launcher (safe to run repeatedly).
# Starts 8201 supervisor and the 9222/9223 dual Resident Browsers (idempotent).
# Triple idempotency: global mutex (no concurrent launchers) + existing-process guard + healthz.
# Does NOT touch 8200. All ASCII-safe for Windows PowerShell 5.1.
#
# Canonical Windows production entry:
#   powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

# Single-instance mutex. Keep the historical mutex name for process compatibility.
$mutex = New-Object System.Threading.Mutex($false, 'Global\ZBrandCoreLauncher8201')
if (-not $mutex.WaitOne(0)) {
    Write-Output '[LUMENIS-8201] another launcher is running, exit'
    return
}
try {

# Resolve the repository from this script instead of depending on one developer-machine path.
$Root   = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Py     = Join-Path $Root '.venv\Scripts\python.exe'
$Edge   = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Output ''
Write-Output '============================================================'
Write-Output ' LUMENIS production launcher'
Write-Output '   8201 Flask supervisor  +  9222/9223 Resident Browsers'
Write-Output '============================================================'
Write-Output "Root: $Root"

if (-not (Test-Path $Py)) {
    Write-Error 'FATAL .venv python.exe missing. Please run:  python -m venv .venv'
    exit 1
}
$pyVer = & $Py --version 2>&1
Write-Output "Python: $pyVer"

$depCheck = Join-Path $Root 'scripts\_prod_dep_check.py'
$check = & $Py $depCheck 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "FATAL missing deps: $check"
    Write-Error 'Please run:  .venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 2
}
Write-Output "Deps:   $check"
Write-Output ''

function Test-Http([string]$Url, [int]$TimeoutSec=3) {
    try { Invoke-RestMethod $Url -TimeoutSec $TimeoutSec | Out-Null; return $true } catch { return $false }
}
function Test-ProcExists([string]$CmdPattern) {
    $hit = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='msedge.exe'" |
        Where-Object { $_.CommandLine -and ($_.CommandLine -match $CmdPattern) }
    return [bool]$hit
}
function Wait-Healthz([string]$Url, [int]$Seconds=15) {
    for ($i=0; $i -lt $Seconds; $i++) {
        if (Test-Http $Url -TimeoutSec 2) { return $true }
        Start-Sleep -Milliseconds 1000
    }
    return $false
}

# --------------- 8201 watchdog (deterministic: healthy -> skip; unhealthy -> clean stale then single start) ---------------
# Root cause fixed 2026-09-03: HealthGuard fires every 5min; old branch waited on an alive-but-broken
# run_supervised forever and never cleaned, so repeated firings stacked run_supervised->run_supervised
# and app.py -> app.py competing for 8201. Now unhealthy always means: kill stale 8201 python, drop
# stale lock, then start exactly ONE supervisor (whose own lock is atomic-create).
$httpOk = Test-Http 'http://127.0.0.1:8201/healthz'
if ($httpOk) {
    Write-Output '[LUMENIS-8201] already healthy, skip'
} else {
    $stale = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -and ($_.CommandLine -match '8201') -and ($_.CommandLine -match 'run_supervised\.py|app\.py') }
    if ($stale) {
        Write-Output ("[LUMENIS-8201] cleaning stale pids: " + (($stale | ForEach-Object { $_.ProcessId }) -join ','))
        $stale | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
    }
    Remove-Item (Join-Path $Root 'data\supervisor_8201.lock') -Force -ErrorAction SilentlyContinue
    $supOut = Join-Path $LogDir 'supervisor_console.log'
    $supErr = Join-Path $LogDir 'supervisor_console.err'
    Start-Process -FilePath $Py -ArgumentList @('run_supervised.py','--host','0.0.0.0','--port','8201') -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $supOut -RedirectStandardError $supErr
    Write-Output '[LUMENIS-8201] starting single supervisor (run_supervised.py --port 8201)'
    Write-Output '[LUMENIS-8201] waiting healthz (max 15s)...'
    $up = Wait-Healthz 'http://127.0.0.1:8201/healthz' 15
    if ($up) {
        Write-Output '[LUMENIS-8201] OK http://127.0.0.1:8201/healthz returned 200'
    } else {
        Write-Error '8201 did not pass 15s health check.'
        Write-Error "  stdout: $supOut"
        Write-Error "  stderr: $supErr"
        Write-Error '--- last 20 stderr ---'
        Get-Content $supErr -Tail 20 -ErrorAction SilentlyContinue
    }
}

# --------------- 9222/9223 Resident Browsers (dual identity) ---------------
# Delegated to scripts/start_resident_browsers.py (single source of truth = xhs_cookie_bridge):
#   9222 XHS_CN_PRIMARY  profile edge-cdp-newaccount  direct connection (no system proxy)
#   9223 XHS_RETINAUT    profile edge-cdp-retinaut    inherits system/overseas proxy
# The launcher is idempotent: an online port is reused and its platform login tab is ensured.
$resident = Join-Path $Root 'scripts\start_resident_browsers.py'
if (Test-Path $resident) {
    Write-Output '[LUMENIS-Resident] ensuring 9222/9223 dual resident browsers ...'
    & $Py $resident
} else {
    Write-Output "[LUMENIS-Resident] launcher missing: $resident"
}

Write-Output ''
Write-Output '============================================================'
Write-Output '  UP  ->  http://127.0.0.1:8201/'
Write-Output '  HZ  ->  http://127.0.0.1:8201/healthz'
Write-Output '  CDP ->  9222 XHS_CN_PRIMARY | 9223 XHS_RETINAUT'
Write-Output '============================================================'

} finally {
    [void]$mutex.ReleaseMutex()
    $mutex.Dispose()
}
