# ============================================================
# Z-Brand-Core · Unified Test Entrypoint (GAP-01)
#  Usage:
#    powershell -ExecutionPolicy Bypass -File scripts\run_tests.ps1
#    powershell -ExecutionPolicy Bypass -File scripts\run_tests.ps1 -Quick
#    powershell -ExecutionPolicy Bypass -File scripts\run_tests.ps1 -StagingUrl http://127.0.0.1:8301
#  Levels:
#    L0 Syntax    (py_compile all .py)
#    L1 Import    (pytest collection)
#    L2-L8 Tests  (pytest full: unit/integration/api/db/redline)
#    L9 Health    (healthz probe if staging running)
#    L10 API Smoke (key endpoints if staging running)
# ============================================================
param(
    [switch]$Quick,
    [string]$StagingUrl = ""
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path $PSScriptRoot -Parent
$Py   = Join-Path $Root '.venv\Scripts\python.exe'
$Fail = 0

function Write-Section([string]$msg) {
    Write-Output ""
    Write-Output "===== $msg ====="
}

# ---- L0: Syntax ----
Write-Section "L0 Syntax (py_compile)"
$pyFiles = Get-ChildItem -Path $Root -Filter "*.py" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\\.git\\|\\\.venv\\|node_modules|__pycache__|\\staging\\' }
$synFail = 0
foreach ($f in $pyFiles) {
    $r = & $Py -m py_compile $f.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output "  SYNTAX FAIL: $($f.FullName.Replace($Root,''))"
        $synFail++
    }
}
if ($synFail -eq 0) { Write-Output "  L0 PASS: $($pyFiles.Count) files compiled" }
else { $Fail++; Write-Output "  L0 FAIL: $synFail files" }

# ---- L1-L8: pytest ----
Write-Section "L1-L8 pytest (unit/integration/api/db/redline)"
$pytestArgs = @("-m", "not online", "--tb=short", "-q")
if ($Quick) { $pytestArgs += @("-x", "--timeout=60") }
Push-Location $Root
& $Py -m pytest @pytestArgs
$pytestExit = $LASTEXITCODE
Pop-Location
if ($pytestExit -eq 0) { Write-Output "  L1-L8 PASS" }
else { $Fail++; Write-Output "  L1-L8 FAIL (exit=$pytestExit)" }

# ---- L9: Health (if staging running) ----
if ($StagingUrl) {
    Write-Section "L9 Health ($StagingUrl)"
    try {
        $h = Invoke-RestMethod "$StagingUrl/healthz" -TimeoutSec 5
        Write-Output "  L9 PASS: healthz=$($h | ConvertTo-Json -Compress)"
    } catch {
        Write-Output "  L9 SKIP: healthz unreachable ($($_.Exception.Message.Substring(0,[Math]::Min(50,$_.Exception.Message.Length))))"
    }
}

# ---- L10: API Smoke (if staging running) ----
if ($StagingUrl) {
    Write-Section "L10 API Smoke ($StagingUrl)"
    $endpoints = @("/api/stats", "/api/health", "/api/v4/status")
    $apiFail = 0
    foreach ($ep in $endpoints) {
        try {
            $r = Invoke-WebRequest "$StagingUrl$ep" -TimeoutSec 5 -UseBasicParsing
            Write-Output "  $ep => $($r.StatusCode)"
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            if ($code -eq 401 -or $code -eq 403) {
                Write-Output "  $ep => $code (auth expected, OK)"
            } else {
                Write-Output "  $ep => FAIL ($code)"
                $apiFail++
            }
        }
    }
    if ($apiFail -eq 0) { Write-Output "  L10 PASS" }
    else { $Fail++; Write-Output "  L10 FAIL: $apiFail endpoints" }
}

# ---- Summary ----
Write-Section "SUMMARY"
if ($Fail -eq 0) {
    Write-Output "  ALL TEST LEVELS PASSED"
    exit 0
} else {
    Write-Output "  $Fail LEVEL(S) FAILED"
    exit 1
}
