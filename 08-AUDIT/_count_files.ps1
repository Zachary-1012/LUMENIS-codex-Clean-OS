Set-Location D:\Taikoo-monitor-new
$log = git log --name-only --format="COMMIT:%h|%an|%ad|%s" --date=short -75
$files = @{}
$currentCommit = $null
foreach ($line in $log) {
    if ($line -match '^COMMIT:([0-9a-f]+)\|(.+?)\|(.+?)\|(.+)$') {
        $currentCommit = @{
            hash = $Matches[1]
            author = $Matches[2]
            date = $Matches[3]
            subject = $Matches[4]
        }
    } elseif ($line -and $line.Trim() -ne '' -and $currentCommit) {
        $f = $line.Trim()
        if (-not $files.ContainsKey($f)) {
            $files[$f] = @{
                count = 0
                first = $null
                last = $null
                lastAuthor = ''
                lastSubject = ''
                lastDate = ''
            }
        }
        $files[$f].count++
        if ($files[$f].first -eq $null) {
            $files[$f].first = $currentCommit.hash
        }
        $files[$f].last = $currentCommit.hash
        $files[$f].lastAuthor = $currentCommit.author
        $files[$f].lastSubject = $currentCommit.subject
        $files[$f].lastDate = $currentCommit.date
    }
}
$files.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | ForEach-Object {
    "$($_.Value.count)`t$($_.Key)`tfirst=$($_.Value.first)`tlast=$($_.Value.last)`tauthor=$($_.Value.lastAuthor)`tdate=$($_.Value.lastDate)`tsubject=$($_.Value.lastSubject)"
}
