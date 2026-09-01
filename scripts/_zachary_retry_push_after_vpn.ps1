# Zachary-OS-AI retry push after VPN recovery (ASCII safe)
# Windows PowerShell 5.1 compatible - no non-ASCII chars in strings or comments
param([int]$MaxTries=4, [int]$RetrySleepSec=10)
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ZBC  = 'd:\Taikoo-monitor-new'
$OSAI = 'D:\Zachary OS AI'

Write-Host '=== STEP 0: TCP probe github.com:443 ==='
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $ias = [System.Net.Dns]::GetHostAddresses('github.com')
    $ok = $false
    foreach ($ip in $ias) {
        try { $tcp.Connect($ip, 443); $ok = $true; $tcp.Close(); break } catch {}
    }
    if (-not $ok) { Write-Host 'WARN github.com:443 still unreachable. Please enable VPN/proxy then rerun.'; exit 1 }
    Write-Host 'OK github.com:443 reachable.'
}
catch {
    Write-Host 'WARN DNS/TCP probe threw; continuing git attempt...'
}

function Push-Repo($Repo, $Label) {
    Write-Host ''
    Write-Host ('=== {0} push + verify @ {1} ===' -f $Label, $Repo)
    Set-Location $Repo
    $before = git rev-parse HEAD
    Write-Host ('LOCAL HEAD before = {0}' -f $before)
    git fetch origin main 2>&1 | Select-Object -Last 6
    $st = git status -sb
    Write-Host ('branch status: {0}' -f $st)

    for ($i=1; $i -le $MaxTries; $i++) {
        Write-Host ('  push attempt {0}/{1}...' -f $i, $MaxTries)
        $out = git push origin main 2>&1 | Out-String
        $trimmed = ($out.Trim() -split "`r?`n") | Where-Object { $_ } | Select-Object -Last 6
        Write-Host ('   ' + ($trimmed -join "`n   "))
        if ($LASTEXITCODE -eq 0) { Write-Host '  push exit=0 OK'; break }
        Write-Host ('  push FAIL, sleep {0}s' -f $RetrySleepSec)
        Start-Sleep -Seconds $RetrySleepSec
    }

    Start-Sleep -Seconds 2
    $after = git rev-parse HEAD
    $remoteLine = git ls-remote origin main 2>&1 | Select-Object -First 1
    $remoteSha = if ($remoteLine) { ($remoteLine -split '\s+')[0] } else { $null }
    Write-Host ('LOCAL HEAD after = {0}' -f $after)
    Write-Host ('REMOTE main SHA = {0}' -f $remoteSha)
    $verified = ($after -eq $remoteSha -and $remoteSha)
    if ($verified) { Write-Host ('OK {0} PUSH VERIFIED' -f $Label) } else { Write-Host ('FAIL {0} BLOCKED' -f $Label) }
    return [PSCustomObject]@{ ok = [bool]$verified; sha = $after }
}

$zbcR  = Push-Repo $ZBC  'ZBC-Z-Brand-Core'
$osaiR = Push-Repo $OSAI 'OSAI-Zachary-OS-AI'

Write-Host ''
Write-Host '====================================== FINAL SUMMARY ======================================'
Write-Host ('ZBC  PATHAUDIT commit : {0}   VERIFIED={1}' -f $zbcR.sha, $zbcR.ok)
Write-Host ('OSAI PATHAUDIT commit : {0}   VERIFIED={1}' -f $osaiR.sha, $osaiR.ok)
Write-Host 'ZBC  T0 baseline pushed: a016a8f15621a8e3b8e4bea158855e4f20905795'
Write-Host 'OSAI T0 baseline pushed: 6cf1420a683b7ef8a24c5ad0801f13f1ab47d74b'
Write-Host '=========================================================================================='

if ($zbcR.ok -and $osaiR.ok) {
    Write-Host ''
    Write-Host 'ALL PUSH VERIFIED OK. DUAL-REPO SYNC COMPLETE.'
    exit 0
} else {
    Write-Host ''
    Write-Host 'STILL BLOCKED. Hints:'
    Write-Host ' (1) VPN/proxy rules must cover github.com (140.82.x.x) port 443.'
    Write-Host ' (2) Check git config --global http.proxy / https.proxy settings.'
    Write-Host ' (3) Open https://github.com/Zachary-1012/Z-Brand-Core in a browser first.'
    exit 3
}
