#requires -Version 7.2
<#
.SYNOPSIS
Build the existing Windows app through a verified ASCII path to the same files.
.DESCRIPTION
Some Flutter gen_snapshot builds decode Windows narrow argv as UTF-8 although
the CRT supplies the system code page. A junction avoids non-ASCII arguments
without copying source, patching the SDK, changing drives or changing settings.
The junction is kept for repeat builds. Never remove it with recursive deletion.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$FlutterSdk,
    [ValidateSet('release', 'profile', 'debug')][string]$Mode = 'release',
    [string]$AliasRoot = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Lumenis/build-paths')
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
if (-not $IsWindows) { throw 'This build entry requires Windows.' }
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$flutter = Join-Path ([IO.Path]::GetFullPath($FlutterSdk)) 'bin/flutter.bat'
if (-not (Test-Path -LiteralPath $flutter -PathType Leaf)) {
    throw "Flutter SDK entry does not exist: $flutter"
}
$aliasBase = [IO.Path]::GetFullPath($AliasRoot).TrimEnd('\')
if ($aliasBase -match '[^\x20-\x7e]' -or $flutter -match '[^\x20-\x7e]') {
    throw 'Use an ASCII AliasRoot and FlutterSdk; no global path settings are changed.'
}
if ($aliasBase.StartsWith($project + '\', [StringComparison]::OrdinalIgnoreCase) -or
    $aliasBase.Equals($project, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'AliasRoot must be outside the app so the junction cannot loop.'
}
# Reject linked ancestors too: a lexically external root could otherwise point
# back inside the app. The app junction itself is validated separately below.
$ancestor = [IO.DirectoryInfo]::new($aliasBase)
while ($null -ne $ancestor) {
    if ($ancestor.Exists -and ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'AliasRoot must not contain a directory junction or symbolic link.'
    }
    $ancestor = $ancestor.Parent
}
$idBytes = [Security.Cryptography.SHA256]::HashData(
    [Text.Encoding]::UTF8.GetBytes($project.ToLowerInvariant()))
$projectId = [Convert]::ToHexString($idBytes).Substring(0, 16).ToLowerInvariant()
$alias = Join-Path $aliasBase $projectId
[IO.Directory]::CreateDirectory($aliasBase) | Out-Null
$aliasItem = Get-Item -LiteralPath $alias -Force -ErrorAction SilentlyContinue
if ($null -eq $aliasItem) {
    New-Item -ItemType Junction -Path $alias -Target $project | Out-Null
    $aliasItem = Get-Item -LiteralPath $alias -Force
}
if ($aliasItem.LinkType -ne 'Junction' -or
    -not $aliasItem.ResolveLinkTarget($true).FullName.TrimEnd('\').Equals(
        $project, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing an existing alias that does not point to this app: $alias"
}

# CMake caches absolute source locations. Archive just that generated state
# before changing the spelling of the same source path; never clean the app.
$build = [IO.Path]::GetFullPath((Join-Path $project 'build/windows/x64'))
$cache = Join-Path $build 'CMakeCache.txt'
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-ffff')
$recordDirectory = Join-Path $project 'build/native-build-receipts'
[IO.Directory]::CreateDirectory($recordDirectory) | Out-Null
$archived = @()
$movePlan = @()
$pathChanged = $false
if (Test-Path -LiteralPath $cache -PathType Leaf) {
    if ((Get-Item -LiteralPath $cache -Force).LinkType) {
        throw 'Refusing a linked CMake cache.'
    }
    $sourceLine = Get-Content -LiteralPath $cache |
        Where-Object { $_.StartsWith('CMAKE_HOME_DIRECTORY:INTERNAL=') } |
        Select-Object -First 1
    $expectedSource = (Join-Path $alias 'windows').Replace('\', '/')
    if ($sourceLine -ne ('CMAKE_HOME_DIRECTORY:INTERNAL=' + $expectedSource)) {
        $pathChanged = $true
        foreach ($name in @('CMakeCache.txt', 'CMakeFiles')) {
            $target = Join-Path $build $name
            if (Test-Path -LiteralPath $target) {
                $resolved = (Get-Item -LiteralPath $target -Force).FullName
                if (-not $resolved.StartsWith($build + '\', [StringComparison]::OrdinalIgnoreCase) -or
                    (Get-Item -LiteralPath $target -Force).LinkType) {
                    throw "Refusing to move a generated cache outside this build: $target"
                }
                $movePlan += @{ source = $target; name = $name }
            }
        }
    }
}
# This marker is independent of CMake. Inspect it even when CMake's cache was
# removed, and finish every preflight before moving any generated metadata.
$lastBuild = [IO.Path]::GetFullPath((Join-Path $project 'build/.last_build_id'))
if (Test-Path -LiteralPath $lastBuild) {
    $lastBuildItem = Get-Item -LiteralPath $lastBuild -Force
    if ($lastBuildItem.LinkType -or $lastBuildItem.PSIsContainer -or $lastBuildItem.FullName -ne $lastBuild) {
        throw 'Refusing an unexpected Flutter build marker.'
    }
    $lastId = (Get-Content -LiteralPath $lastBuild -Raw).Trim()
    if ($lastId -notmatch '^[a-fA-F0-9]{32}$') {
        throw 'Refusing an invalid Flutter build identifier.'
    }
    $oldOutputs = Join-Path $project ".dart_tool/flutter_build/$lastId/outputs.json"
    if (Test-Path -LiteralPath $oldOutputs -PathType Leaf) {
        if ((Get-Item -LiteralPath $oldOutputs -Force).LinkType) {
            throw 'Refusing a linked Flutter outputs manifest.'
        }
        foreach ($output in @(Get-Content -LiteralPath $oldOutputs -Raw | ConvertFrom-Json)) {
            if ($output -isnot [string]) { throw 'Invalid Flutter outputs manifest.' }
            $normal = $output.Replace('\', '/')
            # Native wrapper outputs identify the Windows path transition.
            # Other targets may retain canonical paths for unrelated cached
            # assets; those must not force marker archival on every build.
            foreach ($suffix in @('/windows/flutter/ephemeral/')) {
                $boundary = $normal.IndexOf($suffix, [StringComparison]::OrdinalIgnoreCase)
                if ($boundary -gt 0 -and -not $normal.Substring(0, $boundary).Equals(
                    $alias.Replace('\', '/'), [StringComparison]::OrdinalIgnoreCase)) {
                    $pathChanged = $true
                }
            }
        }
    }
    if ($pathChanged) {
        # Flutter compares path strings, so an old spelling of this same source
        # would delete newly copied files. Archive its marker, not its outputs.
        $movePlan += @{ source = $lastBuild; name = 'flutter-last-build-id' }
    }
}

$record = [ordered]@{
    started_utc = [DateTime]::UtcNow.ToString('o')
    canonical_project = $project
    alias = $alias
    flutter = $flutter
    arguments = @('build', 'windows', ('--' + $Mode), '--no-pub')
    archived_cache = $archived
    flutter_exit_code = $null
    exit_code = $null
    completed = $false
    output_exe = $null
    output_sha256 = $null
    product_acceptance = 'NOT_VERIFIED'
}
$recordPath = Join-Path $recordDirectory ($stamp + '.json')
$logPath = Join-Path $recordDirectory ($stamp + '.log')
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
$buildExit = 1
$locationPushed = $false
try {
    if ($movePlan.Count) {
        $backup = Join-Path $recordDirectory ('cache-' + $stamp)
        [IO.Directory]::CreateDirectory($backup) | Out-Null
        foreach ($move in $movePlan) {
            $destination = Join-Path $backup $move.name
            Move-Item -LiteralPath $move.source -Destination $destination
            $archived += $destination
            $record.archived_cache = $archived
            $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
        }
    }
    Push-Location -LiteralPath $alias
    $locationPushed = $true
    Write-Output "Building existing app through $alias"
    $buildArguments = $record.arguments
    & $flutter @buildArguments 2>&1 | Tee-Object -FilePath $logPath
    $buildExit = $LASTEXITCODE
    $record.flutter_exit_code = $buildExit
    $configuration = $Mode.Substring(0, 1).ToUpperInvariant() + $Mode.Substring(1)
    $exe = Join-Path $project "build/windows/x64/runner/$configuration/lumenis_app.exe"
    if ($buildExit -eq 0) {
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
            throw 'Flutter returned success without the expected Windows executable.'
        }
        $record.output_exe = $exe
        $record.output_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
        $record.completed = $true
    }
} catch {
    $buildExit = 1
    $record['error'] = $_.Exception.Message
    [Console]::Error.WriteLine($_.Exception.Message)
} finally {
    if ($locationPushed) { Pop-Location }
    $record.exit_code = $buildExit
    $record['finished_utc'] = [DateTime]::UtcNow.ToString('o')
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
    Write-Output "Build receipt: $recordPath"
}
exit $buildExit
