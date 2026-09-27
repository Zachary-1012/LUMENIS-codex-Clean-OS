[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$CommittedSourceArchiveRoot,
    [Parameter(Mandatory)][string]$ProjectEnvFile,
    [Parameter(Mandatory)][string]$DatabasePath,
    [Parameter(Mandatory)][string]$PrivateDirectory,
    [string]$TaskName = 'LUMENIS-Prelaunch-Maintenance-5m'
)

$ErrorActionPreference = 'Stop'
$python = 'C:\Python314\python.exe'
$windowsPowerShell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$runnerName = 'scripts\run_prelaunch_maintenance.py'

$sourceRoot = (Resolve-Path -LiteralPath $CommittedSourceArchiveRoot).Path
$envFile = (Resolve-Path -LiteralPath $ProjectEnvFile).Path
$dbFile = (Resolve-Path -LiteralPath $DatabasePath).Path
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $runnerName) -PathType Leaf)) {
    throw 'Committed source archive does not contain scripts\run_prelaunch_maintenance.py.'
}
if ([IO.Path]::GetFileName($envFile) -ne '.env') {
    throw 'ProjectEnvFile must be the explicit project .env file.'
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Required Python executable C:\Python314\python.exe is unavailable.'
}

$projectRoot = Split-Path -Parent $envFile
$privateRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'data\private')).TrimEnd('\')
$privatePath = [IO.Path]::GetFullPath($PrivateDirectory).TrimEnd('\')
$privatePrefix = $privateRoot + '\'
if (-not $privatePath.Equals($privateRoot, [StringComparison]::OrdinalIgnoreCase) -and
    -not $privatePath.StartsWith($privatePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'PrivateDirectory must be inside the ignored project data\private directory.'
}

$existing = Get-ScheduledTask -ErrorAction SilentlyContinue |
    Where-Object { $_.TaskName -eq $TaskName }
if ($existing) {
    throw "Task '$TaskName' already exists; refusing to replace it."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identity.User) { throw 'Current Windows identity has no SID.' }
$sid = $identity.User.Value
New-Item -ItemType Directory -Path $privatePath -Force | Out-Null
$launcher = Join-Path $privatePath 'run_prelaunch_maintenance_task.ps1'
if (Test-Path -LiteralPath $launcher) {
    throw 'Private launcher already exists; refusing to replace it.'
}

$launcherBody = @'
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$CommittedSourceRoot,
    [Parameter(Mandatory)][string]$ProjectEnvFile,
    [Parameter(Mandatory)][string]$DatabasePath,
    [Parameter(Mandatory)][string]$PrivateDirectory
)
$ErrorActionPreference = 'Stop'
$python = 'C:\Python314\python.exe'
$runner = Join-Path $CommittedSourceRoot 'scripts\run_prelaunch_maintenance.py'
$logFile = Join-Path $PrivateDirectory 'prelaunch-maintenance.log'
$exitCode = 1
$safeSummary = [ordered]@{ status = 'FAILED'; reason = 'LAUNCH_FAILURE' }
try {
    $env:ZBC_DB_PATH = $DatabasePath
    $output = @(& $python -u $runner --env-file $ProjectEnvFile 2>&1)
    $exitCode = $LASTEXITCODE
    if ($output.Count -eq 1) {
        $parsed = ConvertFrom-Json -InputObject ([string]$output[0]) -ErrorAction Stop
        if ($parsed.status -notin @('COMPLETED', 'DISABLED', 'FAILED', 'PARTIAL')) {
            throw 'Unexpected runner status.'
        }
        $safeSummary = [ordered]@{ status = [string]$parsed.status }
        foreach ($key in @('reason', 'plan_version', 'summary')) {
            if ($parsed.PSObject.Properties.Name -contains $key) {
                $safeSummary[$key] = $parsed.$key
            }
        }
    }
    else {
        $safeSummary = [ordered]@{ status = 'FAILED'; reason = 'CLI_SUMMARY_UNAVAILABLE' }
        if ($exitCode -eq 0) { $exitCode = 1 }
    }
}
catch {
    # Never persist exception text, settings, raw source content, or environment values.
    $safeSummary = [ordered]@{ status = 'FAILED'; reason = 'LAUNCH_FAILURE' }
    $exitCode = 1
}
$line = '{0} {1} exit={2}{3}' -f [DateTimeOffset]::Now.ToString('o'),
    (ConvertTo-Json -InputObject $safeSummary -Depth 12 -Compress), $exitCode, [Environment]::NewLine
[IO.File]::AppendAllText($logFile, $line, [Text.UTF8Encoding]::new($false))
exit $exitCode
'@
Set-Content -LiteralPath $launcher -Value $launcherBody -Encoding utf8NoBOM

$arguments = '-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -File "{0}" -CommittedSourceRoot "{1}" -ProjectEnvFile "{2}" -DatabasePath "{3}" -PrivateDirectory "{4}"' -f $launcher, $sourceRoot, $envFile, $dbFile, $privatePath
$taskAction = New-ScheduledTaskAction -Execute $windowsPowerShell -Argument $arguments -WorkingDirectory $privatePath
$cadenceTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $sid
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $sid -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger @($cadenceTrigger, $logonTrigger) -Settings $settings -Principal $principal -Description 'LUMENIS pinned-source due-only public maintenance; end-user AUTO remains off.' -ErrorAction Stop | Out-Null
Write-Output "Registered '$TaskName' for $($identity.Name) (InteractiveToken / least privilege)."
