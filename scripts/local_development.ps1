#requires -Version 7.5
# Local, non-model developer actions. No service startup, tests or Git writes.
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)]
    [ValidateSet('snapshot', 'check', 'diff', 'format-preview', 'format-apply', 'rollback', 'locale-preview', 'build')]
    [string] $Action,
    [ValidateSet('M', 'F', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6')]
    [string] $Owner = 'M',
    [string[]] $Paths = @(),
    [string] $PathsJson,
    [string] $Manifest,
    [string] $Receipt,
    [ValidateSet('website', 'flutter-web')]
    [string] $Target,
    [string] $ReceiptDir
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$helper = Join-Path $repoRoot '.codex/local_workflow.py'
if (-not (Test-Path -LiteralPath $helper -PathType Leaf)) {
    throw 'Local workflow helper is missing; restore this bounded tooling delivery.'
}
$pythonCommand = Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1
$arguments = @('-X', 'utf8', $helper, $Action, '--owner', $Owner)
if ($PathsJson) {
    if ($Paths.Count -gt 0) { throw 'Choose Paths or PathsJson, not both.' }
    $decodedPaths = ConvertFrom-Json -InputObject $PathsJson -NoEnumerate
    if ($decodedPaths -isnot [array] -or $decodedPaths.Count -gt 100 -or
        @($decodedPaths | Where-Object { $_ -isnot [string] }).Count -gt 0) {
        throw 'PathsJson must be an array of at most 100 exact relative paths.'
    }
    $Paths = $decodedPaths
}
if ($Paths.Count -gt 0) { $arguments += @('--paths') + $Paths }
if ($Manifest) { $arguments += @('--manifest', $Manifest) }
if ($Receipt) { $arguments += @('--receipt', $Receipt) }
if ($Target) { $arguments += @('--target', $Target) }
if ($ReceiptDir) { $arguments += @('--receipt-dir', $ReceiptDir) }
Push-Location -LiteralPath $repoRoot
try {
    & $pythonCommand.Source @arguments
    $actualExitCode = $LASTEXITCODE
}
finally { Pop-Location }
exit $actualExitCode
