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
