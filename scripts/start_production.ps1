# LUMENIS production idempotent launcher (safe to run repeatedly).
# Starts 8201 supervisor, the HK/International 9223 collector resident, and 9224 general browser (idempotent).
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
Write-Output '   8201 Flask supervisor  +  9223 HK Collector + 9224 General Browser'
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
function Get-CanonicalSupervisor {
    $rootPattern = [regex]::Escape($Root)
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match 'run_supervised\.py') -and
            ($_.CommandLine -match '8201') -and
            ($_.CommandLine -match $rootPattern)
        })
}
function Wait-Healthz([string]$Url, [int]$Seconds=15) {
    for ($i=0; $i -lt $Seconds; $i++) {
        if (Test-Http $Url -TimeoutSec 2) { return $true }
        Start-Sleep -Milliseconds 1000
    }
    return $false
}

# --------------- 8201 watchdog (deterministic: healthy + supervisor -> skip; otherwise converge) ---------------
# Root cause fixed 2026-09-03: HealthGuard fires every 5min; old branch waited on an alive-but-broken
# run_supervised forever and never cleaned, so repeated firings stacked run_supervised->run_supervised
# and app.py -> app.py competing for 8201. Now unhealthy always means: kill stale 8201 python, drop
# stale lock, then start exactly ONE supervisor (whose own lock is atomic-create).
$httpOk = Test-Http 'http://127.0.0.1:8201/healthz'
$supervisors = @(Get-CanonicalSupervisor)
if ($httpOk -and $supervisors.Count -eq 1) {
    Write-Output '[LUMENIS-8201] healthy with exactly one canonical supervisor, skip'
} else {
    if ($httpOk -and $supervisors.Count -eq 0) {
        Write-Output '[LUMENIS-8201] healthy but supervisor missing; converging orphan app tree'
    } elseif ($supervisors.Count -gt 1) {
        Write-Output ("[LUMENIS-8201] duplicate canonical supervisors detected: " + $supervisors.Count)
    } else {
        Write-Output '[LUMENIS-8201] health check failed; converging stale 8201 tree'
    }
    $stale = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match '8201') -and
            ($_.CommandLine -match 'run_supervised\.py|app\.py') -and
            ($_.CommandLine -match [regex]::Escape($Root))
        })
    if ($stale.Count -gt 0) {
        $stalePids = @($stale | ForEach-Object { [int]$_.ProcessId })
        $treeRoots = @($stale | Where-Object { $stalePids -notcontains [int]$_.ParentProcessId })
        if ($treeRoots.Count -eq 0) { $treeRoots = $stale }
        Write-Output ("[LUMENIS-8201] cleaning exact stale tree roots: " + (($treeRoots | ForEach-Object { $_.ProcessId }) -join ','))
        foreach ($rootProc in $treeRoots) {
            & taskkill.exe /PID $rootProc.ProcessId /T /F 2>$null | Out-Null
        }
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

# --------------- 9223/9224 Resident Browsers (HK collection + general browse) ---------------
# Delegated to scripts/start_resident_browsers.py (single source of truth = xhs_cookie_bridge):
#   9223 XHS_RETINAUT    profile edge-cdp-retinaut    inherits system/overseas proxy
#   9224 GENERAL_BROWSE  profile edge-cdp-general     general browsing only
#   9222 XHS_CN_PRIMARY  is retained for diagnostics/history only and is not launched here
# The launcher is idempotent: an online port is reused and its platform login tab is ensured.
$resident = Join-Path $Root 'scripts\start_resident_browsers.py'
if (Test-Path $resident) {
    Write-Output '[LUMENIS-Resident] ensuring 9223 HK collector + 9224 general browser ...'
    & $Py $resident
} else {
    Write-Output "[LUMENIS-Resident] launcher missing: $resident"
}

Write-Output ''
Write-Output '============================================================'
Write-Output '  UP  ->  http://127.0.0.1:8201/'
Write-Output '  HZ  ->  http://127.0.0.1:8201/healthz'
Write-Output '  CDP ->  9223 XHS_RETINAUT (HK) | 9224 GENERAL_BROWSE'
Write-Output '============================================================'

} finally {
    [void]$mutex.ReleaseMutex()
    $mutex.Dispose()
}
