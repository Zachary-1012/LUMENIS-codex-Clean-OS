# LUMENIS production idempotent launcher (safe to run repeatedly).
# Starts the 8201 Core. Browser workers are opened by explicit product tasks.
# Triple idempotency: global mutex (no concurrent launchers) + existing-process guard + healthz.
# Does NOT touch 8200. All ASCII-safe for Windows PowerShell 5.1.
#
# Canonical Windows production entry:
#   powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#
param([switch]$EnableScheduledCollection)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $env:PSModulePath

# Background processes inherit the Windows console code page by default.
# Keep every Python child on UTF-8 so non-ASCII migration/runtime diagnostics
# cannot crash production startup before the real health gate is reached.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

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
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Output ''
Write-Output '============================================================'
Write-Output ' LUMENIS production launcher'
Write-Output '   8201 Product Core; collection and browsing remain user initiated'
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

function Test-Http([string]$Url, [int]$TimeoutSec=3, [string]$ExpectedLaunchId='', [string]$ExpectedEntrySha256='') {
    try {
        $health = Invoke-RestMethod $Url -TimeoutSec $TimeoutSec
        if (-not ($health.ok -eq $true -and
                  $health.status -eq 'healthy' -and
                  $health.dependencies.database -eq 'ok')) { return $false }
        if ($ExpectedLaunchId -and $health.core_instance.launch_id -cne $ExpectedLaunchId) { return $false }
        if ($ExpectedEntrySha256 -and $health.core_instance.entry_sha256 -cne $ExpectedEntrySha256) { return $false }
        if (($ExpectedLaunchId -or $ExpectedEntrySha256) -and
            $health.core_instance.boot_id -cnotmatch '^[0-9a-f]{32}$') { return $false }
        return $true
    } catch { return $false }
}
function Get-CoreStartupDecision([bool]$Healthy, [bool]$EntryMatches, [int]$SupervisorCount, [bool]$Occupied, [bool]$SchedulerMatches) {
    if (-not $Healthy) {
        if ($Occupied -or $SupervisorCount -gt 0) { return 'BLOCKED_EXISTING_PROCESS' }
        return 'START_CORE'
    }
    if (-not $EntryMatches) { return 'BLOCKED_SOURCE_IDENTITY' }
    if ($SupervisorCount -ne 1) { return 'BLOCKED_PROCESS_OWNERSHIP' }
    if (-not $SchedulerMatches) { return 'BLOCKED_SCHEDULER_MODE' }
    return 'REUSE_MATCHING_CORE_ENTRY'
}
function Test-CorePortListening {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $attempt = $client.BeginConnect('127.0.0.1', 8201, $null, $null)
        if (-not $attempt.AsyncWaitHandle.WaitOne(1000)) { return $false }
        $client.EndConnect($attempt)
        return $true
    } catch { return $false }
    finally { $client.Dispose() }
}
function Get-CanonicalSupervisor {
    $rootPattern = [regex]::Escape($Root)
    $hits = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match 'run_supervised\.py') -and
            ($_.CommandLine -match '8201') -and
            ($_.CommandLine -match $rootPattern)
        })
    # Windows virtualenv launchers expose both the launcher and its Python
    # child with the same command line.  Count one supervisor tree, not two
    # processes, otherwise every idempotent launch looks like a duplicate.
    $ids = @($hits | ForEach-Object { [int]$_.ProcessId })
    @($hits | Where-Object { -not ($ids -contains [int]$_.ParentProcessId) })
}
function Wait-Healthz([string]$Url, [int]$Seconds=15, [string]$ExpectedLaunchId='', [string]$ExpectedEntrySha256='') {
    for ($i=0; $i -lt $Seconds; $i++) {
        if (Test-Http $Url -TimeoutSec 2 -ExpectedLaunchId $ExpectedLaunchId -ExpectedEntrySha256 $ExpectedEntrySha256) { return $true }
        Start-Sleep -Milliseconds 1000
    }
    return $false
}

$httpOk = Test-Http 'http://127.0.0.1:8201/healthz'
$entrySha256 = (Get-FileHash -LiteralPath (Join-Path $Root 'app.py') -Algorithm SHA256).Hash.ToLowerInvariant()
$entryMatches = $httpOk -and (Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedEntrySha256 $entrySha256)
$supervisors = @(Get-CanonicalSupervisor)
$ownedCore = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
    $_.CommandLine -and $_.CommandLine -match '(?:^|\s)--port\s+8201(?:\s|$)' -and
    $_.CommandLine -match 'app\.py' -and $_.CommandLine -match [regex]::Escape($Root)
})
$schedulerMatches = $false
if ($httpOk -and $supervisors.Count -eq 1) {
    $withoutScheduler = $supervisors[0].CommandLine -match '(?:^|\s)--no-scheduler(?:\s|$)'
    $schedulerMatches = $withoutScheduler -eq (-not $EnableScheduledCollection)
}
$occupied = (Test-CorePortListening) -or $ownedCore.Count -gt 0
$startupDecision = Get-CoreStartupDecision $httpOk $entryMatches $supervisors.Count $occupied $schedulerMatches
if ($startupDecision -like 'BLOCKED_*') {
    throw "Core startup $startupDecision; the running service was preserved. A controlled load requires verified ownership and quiescence."
}
if ($startupDecision -eq 'REUSE_MATCHING_CORE_ENTRY') {
    Write-Output '[LUMENIS-8201] healthy with matching Core entry bytes and one canonical supervisor, skip'
} else {
    if (Test-CorePortListening) { throw '8201 is still owned by a listener; replacement was not started and the supervisor lock was preserved.' }
    $supOut = Join-Path $LogDir 'supervisor_console.log'
    $supErr = Join-Path $LogDir 'supervisor_console.err'
    $launchId = [guid]::NewGuid().ToString('N')
    $supervisorArgs = @('run_supervised.py','--host','0.0.0.0','--port','8201','--launch-id',$launchId)
    if (-not $EnableScheduledCollection) { $supervisorArgs += '--no-scheduler' }
    Start-Process -FilePath $Py -ArgumentList $supervisorArgs -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $supOut -RedirectStandardError $supErr
    Write-Output '[LUMENIS-8201] starting single supervisor (run_supervised.py --port 8201)'
    Write-Output '[LUMENIS-8201] waiting healthz (max 15s)...'
    $up = Wait-Healthz 'http://127.0.0.1:8201/healthz' 15 -ExpectedLaunchId $launchId -ExpectedEntrySha256 $entrySha256
    if ($up) {
        Write-Output '[LUMENIS-8201] OK healthy database and fresh launch match the requested Core entry bytes'
    } else {
        Write-Error '8201 did not pass 15s health check.'
        Write-Error "  stdout: $supOut"
        Write-Error "  stderr: $supErr"
        Write-Error '--- last 20 stderr ---'
        Get-Content $supErr -Tail 20 -ErrorAction SilentlyContinue
    }
}

$coreHealthy = Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedEntrySha256 $entrySha256
$readiness = if ($coreHealthy) { 'CORE_READY' } else { 'CORE_UNAVAILABLE' }
Write-Output ''
Write-Output '============================================================'
Write-Output "  Startup state: $readiness"
if ($coreHealthy) { Write-Output '  Core -> http://127.0.0.1:8201/' }
Write-Output '  HZ  ->  http://127.0.0.1:8201/healthz'
Write-Output '  Browser workers start only from an authorized browse/collection request.'
Write-Output '  Collection, AI and product task readiness require their own runtime evidence.'
Write-Output '============================================================'
if (-not $coreHealthy) { exit 1 }
exit 0

} finally {
    [void]$mutex.ReleaseMutex()
    $mutex.Dispose()
}
