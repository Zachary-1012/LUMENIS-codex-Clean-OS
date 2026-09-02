# Z-Brand Core / CTH-POMS production idempotent launcher (safe to run repeatedly).
# Starts 8201 supervisor and 9222 Edge CDP only when not already healthy AND not already starting.
# Triple idempotency: global mutex (no concurrent launchers) + existing-process guard + healthz.
# Does NOT touch 8200. All ASCII-safe for Windows PowerShell 5.1.
#
#  Zachary-OS-AI T0-3 统一生产入口（所有 LEGACY 入口都 REDIRECT 到此）
#    Usage:  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

# Single-instance mutex
$mutex = New-Object System.Threading.Mutex($false, 'Global\ZBrandCoreLauncher8201')
if (-not $mutex.WaitOne(0)) {
    Write-Output '[ZBC-8201] another launcher is running, exit'
    return
}
try {

$Root   = 'D:\Taikoo-monitor-new'
$Py     = Join-Path $Root '.venv\Scripts\python.exe'
$Edge   = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Output ''
Write-Output '============================================================'
Write-Output ' Zachary-OS-AI  Z-Brand-Core production launcher'
Write-Output '   8201 Flask supervisor  +  9222 Edge CDP'
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

# --------------- 8201 watchdog ---------------
$httpOk = Test-Http 'http://127.0.0.1:8201/healthz'
$procOk = Test-ProcExists 'run_supervised\.py.*8201'
if ($httpOk) {
    Write-Output '[ZBC-8201] already healthy, skip'
} elseif ($procOk) {
    Write-Output '[ZBC-8201] supervisor already starting, wait...'
    $up = Wait-Healthz 'http://127.0.0.1:8201/healthz' 15
    if (-not $up) { Write-Error '8201 not ready after 15s. Check logs/supervisor_console.err' }
} else {
    $supOut = Join-Path $LogDir 'supervisor_console.log'
    $supErr = Join-Path $LogDir 'supervisor_console.err'
    Start-Process -FilePath $Py -ArgumentList @('run_supervised.py','--host','0.0.0.0','--port','8201') -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $supOut -RedirectStandardError $supErr
    Write-Output '[ZBC-8201] starting supervisor (run_supervised.py --port 8201)'
    Write-Output '[ZBC-8201] waiting healthz (max 15s)...'
    $up = Wait-Healthz 'http://127.0.0.1:8201/healthz' 15
    if ($up) {
        Write-Output '[ZBC-8201] OK http://127.0.0.1:8201/healthz returned 200'
    } else {
        Write-Error '8201 did not pass 15s health check.'
        Write-Error "  stdout: $supOut"
        Write-Error "  stderr: $supErr"
        Write-Error '--- last 20 stderr ---'
        Get-Content $supErr -Tail 20 -ErrorAction SilentlyContinue
    }
}

# --------------- 9222 Edge CDP ---------------
$edgeHttpOk = Test-Http 'http://127.0.0.1:9222/json/version'
$edgeProcOk = Test-ProcExists 'remote-debugging-port=9222'
if ($edgeHttpOk) {
    Write-Output '[ZBC-9222] 9222 already online, skip'
} elseif ($edgeProcOk) {
    Write-Output '[ZBC-9222] 9222 Edge starting, skip'
} else {
    if (-not (Test-Path $Edge)) {
        Write-Error "9222 Edge not found at: $Edge  (manual launch possible)"
    } else {
        $Profile = Join-Path $Root 'edge-cdp-profile'
        $EdgeArgs = @('--remote-debugging-port=9222',"--user-data-dir=$Profile",'--no-first-run','--no-default-browser-check','--disable-popup-blocking','--disable-extensions','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--disable-component-update','--remote-allow-origins=*','--no-proxy-server','about:blank')
        Start-Process -FilePath $Edge -ArgumentList $EdgeArgs -WorkingDirectory $Root
        Write-Output '[ZBC-9222] started (about:blank, for human XHS/Weibo login)'
    }
}

Write-Output ''
Write-Output '============================================================'
Write-Output '  UP  ->  http://127.0.0.1:8201/'
Write-Output '  HZ  ->  http://127.0.0.1:8201/healthz'
Write-Output '  CDP ->  http://127.0.0.1:9222/json/version'
Write-Output '============================================================'

} finally {
    [void]$mutex.ReleaseMutex()
    $mutex.Dispose()
}
