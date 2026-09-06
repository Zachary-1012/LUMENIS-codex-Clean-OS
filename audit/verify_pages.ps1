$pages = @(
    '/lumenis/cth/realtime',
    '/lumenis/cth/events',
    '/lumenis/cth/risk',
    '/lumenis/cth/xiaohongshu',
    '/lumenis/cth/reports'
)
$base = 'http://127.0.0.1:8201'
foreach ($p in $pages) {
    try {
        $r = Invoke-WebRequest -Uri ($base + $p) -UseBasicParsing -TimeoutSec 15
        Write-Output ($p + ' => ' + $r.StatusCode + ' (' + $r.Content.Length + ' bytes)')
    } catch {
        Write-Output ($p + ' => ERROR: ' + $_.Exception.Message)
    }
}
