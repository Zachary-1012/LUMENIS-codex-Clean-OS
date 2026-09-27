[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Disable','Remove')][string]$Action,
    [string]$TaskName = 'LUMENIS-Prelaunch-Maintenance-5m'
)
$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) { throw "Task '$TaskName' was not found." }
if ($Action -eq 'Disable') {
    Disable-ScheduledTask -TaskName $TaskName -TaskPath $task.TaskPath -ErrorAction Stop | Out-Null
    Write-Output "Disabled '$TaskName'. Private files and product data were left intact."
}
else {
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $task.TaskPath -Confirm:$false -ErrorAction Stop
    Write-Output "Removed '$TaskName'. Private files and product data were left intact."
}
