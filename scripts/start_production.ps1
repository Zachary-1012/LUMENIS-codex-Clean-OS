# Z-Brand Core / CTH-POMS production idempotent launcher (safe to run repeatedly).
# Starts 8201 supervisor and 9222 Edge CDP only when not already healthy AND not already starting.
# Triple idempotency: global mutex (no concurrent launchers) + existing-process guard + healthz.
# Does NOT touch 8200. All ASCII for Windows PowerShell 5.1 GBK safety.
$ErrorActionPreference = 'SilentlyContinue'

# --- 0) Single-instance mutex: if another launcher is mid-start, exit immediately ---
$mutex = New-Object System.Threading.Mutex($false, 'Global\ZBrandCoreLauncher8201')
if (-not $mutex.WaitOne(0)) {
    Write-Output '[start_production] another launcher is running, exit'
    return
}
try {

$Root = 'D:\Taikoo-monitor-new'
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$Edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-Http([string]$Url) {
    try { Invoke-RestMethod $Url -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}

function Test-ProcExists([string]$CmdPattern) {
    $hit = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='msedge.exe'" |
        Where-Object { $_.CommandLine -and ($_.CommandLine -match $CmdPattern) }
    return [bool]$hit
}

# 1) 8201 watchdog. Skip when: (a) healthy, or (b) a supervisor is already starting (process exists).
$httpOk = Test-Http 'http://127.0.0.1:8201/healthz'
$procOk = Test-ProcExists 'run_supervised\.py.*8201'
if ($httpOk) {
    Write-Output '[start_production] 8201 already healthy, skip'
} elseif ($procOk) {
    Write-Output '[start_production] 8201 supervisor already present (starting), skip duplicate'
} else {
    $supOut = Join-Path $LogDir 'supervisor_console.log'
    $supErr = Join-Path $LogDir 'supervisor_console.err'
    Start-Process -FilePath $Py -ArgumentList @('run_supervised.py','--host','0.0.0.0','--port','8201') -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $supOut -RedirectStandardError $supErr
    Write-Output '[start_production] 8201 supervisor starting'
}

# 2) 9222 Edge human-browsing CDP. Skip when online or an Edge with 9222 is already present.
$edgeHttpOk = Test-Http 'http://127.0.0.1:9222/json/version'
$edgeProcOk = Test-ProcExists 'remote-debugging-port=9222'
if ($edgeHttpOk) {
    Write-Output '[start_production] 9222 already online, skip'
} elseif ($edgeProcOk) {
    Write-Output '[start_production] 9222 Edge already present (starting), skip duplicate'
} else {
    $Profile = Join-Path $Root 'edge-cdp-profile'
    $EdgeArgs = @('--remote-debugging-port=9222',"--user-data-dir=$Profile",'--no-first-run','--no-default-browser-check','--disable-popup-blocking','--disable-extensions','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--disable-component-update','--no-proxy-server','about:blank')
    Start-Process -FilePath $Edge -ArgumentList $EdgeArgs -WorkingDirectory $Root
    Write-Output '[start_production] 9222 Edge starting'
}

} finally {
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
