$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$launcherPath = Join-Path $repoRoot 'scripts\start_production.ps1'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $launcherPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) {
    throw ('Launcher parse failed: ' + ($parseErrors -join '; '))
}
$functionAst = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq 'Test-Http'
}, $true)
if (-not $functionAst) { throw 'Test-Http function not found' }

. ([scriptblock]::Create($functionAst.Extent.Text))
$decisionAst = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq 'Get-CoreStartupDecision'
}, $true)
if (-not $decisionAst) { throw 'Get-CoreStartupDecision function not found' }
. ([scriptblock]::Create($decisionAst.Extent.Text))
$script:MockHealth = $null
$script:MockTransportFailure = $false
function Invoke-RestMethod {
    param([string]$Url, [int]$TimeoutSec)
    if ($script:MockTransportFailure) { throw 'mock transport failure' }
    return $script:MockHealth
}

$script:MockHealth = [pscustomobject]@{
    ok = $true
    status = 'healthy'
    dependencies = [pscustomobject]@{ database = 'ok' }
}
if (-not (Test-Http 'http://127.0.0.1:8201/healthz' 1)) {
    throw 'Healthy canonical response was rejected'
}

$launchId = 'a' * 32
$entryHash = 'b' * 64
if (Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedLaunchId $launchId -ExpectedEntrySha256 $entryHash) {
    throw 'Old healthy Core without an attempt identity was accepted as a new launch'
}
$script:MockHealth | Add-Member -NotePropertyName core_instance -NotePropertyValue ([pscustomobject]@{
    launch_id = $launchId
    boot_id = 'c' * 32
    entry_sha256 = $entryHash
})
if (-not (Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedLaunchId $launchId -ExpectedEntrySha256 $entryHash)) {
    throw 'Matching fresh Core launch was rejected'
}
$script:MockHealth.core_instance.launch_id = 'd' * 32
if (Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedLaunchId $launchId -ExpectedEntrySha256 $entryHash) {
    throw 'A previous launch was accepted as the requested launch'
}
$script:MockHealth.core_instance.launch_id = $launchId
$script:MockHealth.core_instance.entry_sha256 = 'e' * 64
if (Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedLaunchId $launchId -ExpectedEntrySha256 $entryHash) {
    throw 'Different Core entry bytes were accepted'
}
if ((Get-CoreStartupDecision $true $false 1) -ne 'BLOCKED_SOURCE_IDENTITY') { throw 'Healthy unknown source was allowed to restart' }
if ((Get-CoreStartupDecision $true $true 0) -ne 'BLOCKED_PROCESS_OWNERSHIP') { throw 'Healthy unowned Core was allowed to restart' }
if ((Get-CoreStartupDecision $true $true 2) -ne 'BLOCKED_PROCESS_OWNERSHIP') { throw 'Duplicate ownership was accepted' }
if ((Get-CoreStartupDecision $true $true 1) -ne 'REUSE_MATCHING_CORE_ENTRY') { throw 'Matching owned Core could not be reused' }
if ((Get-CoreStartupDecision $false $false 0) -ne 'CONVERGE_OWNED_STALE_PROCESS') { throw 'Unhealthy recovery path was lost' }

$script:MockHealth = [pscustomobject]@{
    ok = $false
    status = 'unavailable'
    dependencies = [pscustomobject]@{ database = 'unavailable' }
}
if (Test-Http 'http://127.0.0.1:8201/healthz' 1) {
    throw 'Unavailable database response was accepted'
}

$script:MockHealth = [pscustomobject]@{ ok = $true; status = 'healthy' }
if (Test-Http 'http://127.0.0.1:8201/healthz' 1) {
    throw 'Missing database dependency was accepted'
}

$script:MockTransportFailure = $true
if (Test-Http 'http://127.0.0.1:8201/healthz' 1) {
    throw 'Transport failure was accepted'
}

Write-Output 'PASS: launcher Test-Http accepts only the complete healthy database contract'
