# Z-Brand Core / CTH-POMS production idempotent launcher (safe to run repeatedly).
# Starts 8201 supervisor and 9222 Edge CDP only when not already healthy. Does NOT touch 8200.
$ErrorActionPreference = 'SilentlyContinue'

$Root = 'D:\Taikoo-monitor-new'
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$Edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-Http([string]$Url) {
    try { Invoke-RestMethod $Url -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}

# 1) 8201 watchdog (detached hidden process; watchdog keeps app.py alive)
if (-not (Test-Http 'http://127.0.0.1:8201/healthz')) {
    $supOut = Join-Path $LogDir 'supervisor_console.log'
    $supErr = Join-Path $LogDir 'supervisor_console.err'
    Start-Process -FilePath $Py -ArgumentList @('run_supervised.py','--host','0.0.0.0','--port','8201') -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $supOut -RedirectStandardError $supErr
    Write-Output '[start_production] 8201 supervisor starting'
} else {
    Write-Output '[start_production] 8201 already healthy, skip'
}

# 2) 9222 Edge human-browsing CDP (persistent profile, direct connection, about:blank start)
if (-not (Test-Http 'http://127.0.0.1:9222/json/version')) {
    $Profile = Join-Path $Root 'edge-cdp-profile'
    $EdgeArgs = @('--remote-debugging-port=9222',"--user-data-dir=$Profile",'--no-first-run','--no-default-browser-check','--disable-popup-blocking','--disable-extensions','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--disable-component-update','--no-proxy-server','about:blank')
    Start-Process -FilePath $Edge -ArgumentList $EdgeArgs -WorkingDirectory $Root
    Write-Output '[start_production] 9222 Edge starting'
} else {
    Write-Output '[start_production] 9222 already online, skip'
}
