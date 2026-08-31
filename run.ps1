# =====================================================================
# Z-Brand Core / CTH-POMS   -   UNIFIED ENTRYPOINT (single front door)
# ---------------------------------------------------------------------
# Usage:
#   .\run.ps1 prod      Start production (idempotent): 8201 supervised +
#                       9222 Edge CDP, delegates to the already-proven
#                       scripts/start_production.ps1 (mutex + healthz).
#   .\run.ps1 dev       Foreground dev server on 127.0.0.1:8200.
#   .\run.ps1 staging   Fully isolated lightweight staging on 127.0.0.1:8301:
#                       separate DB copy (staging/monitor.staging.db, auto
#                       created via scripts/staging_setup.py), scheduler OFF,
#                       web discovery OFF, XHS_PRODUCTION=false. Never touches
#                       the production DB and never triggers real collection.
#   .\run.ps1 status    Read-only health probe (8200 / 8201 / 9222).
#
# ASCII-only on purpose: Windows PowerShell 5.1 + GBK console safety.
# This file is a thin orchestration front door. It does NOT replace the
# scheduled tasks (TaikooMonitor / ZBrand-HealthGuard) and does NOT kill
# python processes. Legacy .bat launchers are catalogued in
# docs/governance/LAUNCHERS.md and retired only after an offline window.
# =====================================================================
param(
    [Parameter(Position = 0)]
    [ValidateSet('prod', 'dev', 'staging', 'status')]
    [string]$Mode = 'prod'
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Py   = Join-Path $Root '.venv\Scripts\python.exe'

function Test-Http([string]$Url) {
    try { Invoke-RestMethod $Url -TimeoutSec 3 | Out-Null; return $true }
    catch { return $false }
}

function Show-Status {
    $p8200 = Test-Http 'http://127.0.0.1:8200/healthz'
    $p8201 = Test-Http 'http://127.0.0.1:8201/healthz'
    $cdp   = Test-Http 'http://127.0.0.1:9222/json/version'
    Write-Output '== Z-Brand Core status =='
    Write-Output ('  app  8200 (direct)    : ' + $(if ($p8200) { 'UP' } else { 'down' }))
    Write-Output ('  app  8201 (supervisor): ' + $(if ($p8201) { 'UP' } else { 'down' }))
    Write-Output ('  CDP  9222 (Edge)      : ' + $(if ($cdp)   { 'UP' } else { 'down' }))
}

switch ($Mode) {
    'status' {
        Show-Status
    }
    'prod' {
        if (-not (Test-Path $Py)) { throw "venv python not found: $Py" }
        $launcher = Join-Path $Root 'scripts\start_production.ps1'
        Write-Output '[run] prod -> idempotent production launcher (8201 supervisor + 9222 CDP)'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher
        Start-Sleep -Seconds 2
        Show-Status
        Write-Output '[run] web: http://127.0.0.1:8201/v4/console/  (CDP http://127.0.0.1:9222)'
    }
    'dev' {
        if (-not (Test-Path $Py)) { throw "venv python not found: $Py" }
        Set-Location $Root
        Write-Output '[run] dev foreground on http://127.0.0.1:8200  (Ctrl+C to stop)'
        & $Py app.py --host 127.0.0.1 --port 8200
    }
    'staging' {
        if (-not (Test-Path $Py)) { throw "venv python not found: $Py" }
        $StageDir = Join-Path $Root 'staging'
        $StageDb  = Join-Path $StageDir 'monitor.staging.db'
        if (-not (Test-Path $StageDb)) {
            Write-Output '[run] staging db missing -> creating consistent copy (scripts/staging_setup.py)'
            & $Py (Join-Path $Root 'scripts\staging_setup.py')
        }
        # Lightweight isolation: own DB copy + own port + scheduler OFF + discovery OFF.
        $env:ZBC_ENV              = 'staging'
        $env:XHS_PRODUCTION       = 'false'
        $env:ZBC_DB_PATH          = $StageDb
        $env:TAIKOO_WEB_DISCOVERY = '0'
        Set-Location $Root
        Write-Output ("[run] STAGING isolated db = " + $StageDb)
        Write-Output '[run] STAGING on http://127.0.0.1:8301  (scheduler OFF / discovery OFF / no real collect)'
        & $Py app.py --host 127.0.0.1 --port 8301 --no-scheduler
    }
}
