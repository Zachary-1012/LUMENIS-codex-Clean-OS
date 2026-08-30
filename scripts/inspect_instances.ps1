# Z-Brand Core instance read-only inspector (never kills; reports port ownership and duplicate instances)
# Usage: powershell -File scripts/inspect_instances.ps1
# 8200=production, 8201=test. LISTEN=holds the port, DUPLICATE=extra stacked instance.
$ErrorActionPreference = 'SilentlyContinue'

function Get-ListenPid([int]$Port) {
    $c = Get-NetTCPConnection -State Listen -LocalPort $Port
    if ($c) { return ($c | Select-Object -First 1).OwningProcess } else { return $null }
}

foreach ($port in 8200, 8201) {
    $listen = Get-ListenPid $port
    Write-Output "===== PORT $port  LISTEN PID = [$listen] ====="
    try {
        $h = Invoke-RestMethod "http://127.0.0.1:$port/healthz" -TimeoutSec 3
        Write-Output ("  healthz: ok={0} version={1}" -f $h.ok, $h.version)
    } catch { Write-Output "  healthz: no-response" }
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'app\.py' -and $_.CommandLine -match "$port" }
    foreach ($p in $procs) {
        $role = if ($p.ProcessId -eq $listen) { 'LISTEN(KEEP)' } else { 'DUPLICATE' }
        $mb = [math]::Round($p.WorkingSetSize / 1MB)
        Write-Output ("  PID={0} PPID={1} {2} mem={3}MB start={4}" -f $p.ProcessId, $p.ParentProcessId, $role, $mb, $p.CreationDate)
    }
    $dup = ($procs | Where-Object { $_.ProcessId -ne $listen }).Count
    Write-Output ("  SUMMARY: total={0} duplicate={1}" -f $procs.Count, $dup)
    Write-Output ""
}

$cdp = 'offline'
try { $cdp = (Invoke-RestMethod 'http://127.0.0.1:9222/json/version' -TimeoutSec 3).Browser } catch {}
Write-Output "9222 human browser: $cdp"
Write-Output "NOTE: clearing duplicates is a production action requiring manual authorization; kill a stack together with its parent cmd."
