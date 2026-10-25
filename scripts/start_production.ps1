# LUMENIS production idempotent launcher (safe to run repeatedly).
# Starts the 8201 Core. Browser workers are opened by explicit product tasks.
# Triple idempotency: global mutex (no concurrent launchers) + existing-process guard + healthz.
# Does NOT touch 8200. All ASCII-safe for Windows PowerShell 5.1.
#
# Canonical Windows production entry:
#   powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#
param(
    [switch]$EnableScheduledCollection,
    [switch]$DesktopBundle,
    [switch]$DescribeBundle,
    [switch]$AdoptExistingDataRoot,
    [string]$DataRoot = ''
)

# The repository launcher retains its original behavior below. A portable bundle
# uses these same Core bytes with the existing explicit manual Workspace mode.
function Get-LumenisDesktopBundlePlan {
    param([string]$LauncherRoot, [string]$RequestedDataRoot)
    $core = [IO.Path]::GetFullPath((Join-Path $LauncherRoot '..'))
    $package = Split-Path -Parent $core
    $manifestPath = Join-Path $package 'bundle-manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'Bundle manifest is missing.' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.schema -ne 'lumenis.windows-portable-bundle/v1' -or
        $manifest.core_base_url -cne $manifest.app_core_base_url -or
        $manifest.core_base_url -cnotmatch '^http://127\.0\.0\.1:([0-9]{4,5})$') {
        throw 'App and Core endpoint declarations are inconsistent.'
    }
    $port = [int]$Matches[1]
    if ($port -ne [int]$manifest.core_port -or $port -lt 1024 -or $port -gt 65535 -or
        $port -in @(5000, 5001, 8200, 8201, 9222, 9223, 9224)) {
        throw 'The bundle Core port is invalid or reserved.'
    }
    if ($manifest.python_base -cne 'runtime/python' -or
        $manifest.python_abi -cnotmatch '^python3[0-9]{1,2}$' -or
        $manifest.source_entry_sha256 -cnotmatch '^[a-f0-9]{64}$') {
        throw 'Bundle runtime identity is invalid.'
    }
    foreach ($relative in @('core/app.py', 'app/lumenis_app.exe', 'app/flutter_windows.dll',
                            'app/data/icudtl.dat', 'runtime/python/python.exe',
                            'app/msvcp140.dll', 'app/vcruntime140.dll', 'app/vcruntime140_1.dll',
                            'runtime/python/msvcp140.dll', 'runtime/python/vcruntime140.dll',
                            'runtime/python/vcruntime140_1.dll',
                            "runtime/python/$($manifest.python_abi).dll",
                            "runtime/python/$($manifest.python_abi)._pth",
                            'runtime/media/ffmpeg.exe', 'runtime/media/ffprobe.exe')) {
        $file = Join-Path $package $relative
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Bundle component missing: $relative" }
        $item = Get-Item -LiteralPath $file -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked bundle files are refused.' }
        if (-not $relative.EndsWith('._pth')) {
            $record = @($manifest.files | Where-Object { $_.path -ceq $relative })
            if ($record.Count -ne 1 -or
                (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $record[0].sha256) {
                throw "Bundle component identity changed: $relative"
            }
        }
    }
    if ((Get-FileHash -LiteralPath (Join-Path $core 'app.py') -Algorithm SHA256).Hash.ToLowerInvariant() -cne
        $manifest.source_entry_sha256) { throw 'The Core entry identity changed.' }
    $expectedPaths = @('.', 'DLLs', 'Lib', 'Lib/site-packages', '../../core')
    $paths = @(Get-Content -LiteralPath (Join-Path $package "runtime/python/$($manifest.python_abi)._pth"))
    if (($paths -join '|') -cne ($expectedPaths -join '|')) { throw 'Python paths must stay inside this bundle.' }
    if (-not $RequestedDataRoot) {
        $RequestedDataRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'OEVIRA/UserData'
    }
    if (-not [IO.Path]::IsPathRooted($RequestedDataRoot)) { throw 'DataRoot must be an absolute directory.' }
    $data = [IO.Path]::GetFullPath($RequestedDataRoot).TrimEnd('\')
    if ($data -eq [IO.Path]::GetPathRoot($data).TrimEnd('\') -or
        $data.Equals($package, [StringComparison]::OrdinalIgnoreCase) -or
        $data.StartsWith($package + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'User data must be outside the portable bundle.'
    }
    $ancestor = [IO.DirectoryInfo]::new($data)
    while ($null -ne $ancestor) {
        if ($ancestor.Exists -and ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'DataRoot must not traverse an existing junction or symbolic link.'
        }
        $ancestor = $ancestor.Parent
    }
    return [pscustomobject]@{ Package = $package; Core = $core; Data = $data;
        Port = $port; BaseUrl = $manifest.core_base_url; EntryHash = $manifest.source_entry_sha256;
        Python = (Join-Path $package 'runtime/python/python.exe');
        App = (Join-Path $package 'app/lumenis_app.exe'); Manifest = $manifest }
}

function Initialize-LumenisDesktopData {
    param($Plan, [switch]$AdoptExisting)
    # No seeded DB, copying, deletion or replacement. Existing user data survives
    # upgrades; a conflicting old package directory is an explicit recovery error.
    [IO.Directory]::CreateDirectory($Plan.Data) | Out-Null
    $marker = Join-Path $Plan.Data '.oevira-user-data.json'
    if (Test-Path -LiteralPath $marker -PathType Leaf) {
        $ownership = Get-Content -LiteralPath $marker -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($ownership.schema -cne 'lumenis.desktop-user-data/v1') { throw 'The data root belongs to another format; it was preserved.' }
    } else {
        $nonempty = @(Get-ChildItem -LiteralPath $Plan.Data -Force).Count -gt 0
        if ($nonempty -and -not $AdoptExisting) {
            throw 'An existing nonempty data root without OEVIRA ownership was preserved. Explicit adoption is required after backup.'
        }
        if ($AdoptExisting) {
            $database = Get-Item -LiteralPath (Join-Path $Plan.Data 'monitor.db') -Force -ErrorAction SilentlyContinue
            if ($null -eq $database -or $database.PSIsContainer -or $database.LinkType) {
                throw 'Explicit adoption requires an existing plain monitor.db; no data was replaced.'
            }
        }
        $stream = [IO.File]::Open($marker, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $bytes = [Text.Encoding]::UTF8.GetBytes('{"schema":"lumenis.desktop-user-data/v1"}')
            $stream.Write($bytes, 0, $bytes.Length)
        } finally { $stream.Dispose() }
    }
    foreach ($pair in @(@('data', $Plan.Data), @('logs', (Join-Path $Plan.Data 'logs')))) {
        [IO.Directory]::CreateDirectory($pair[1]) | Out-Null
        $link = Join-Path $Plan.Core $pair[0]
        $item = Get-Item -LiteralPath $link -Force -ErrorAction SilentlyContinue
        if ($null -eq $item) {
            New-Item -ItemType Junction -Path $link -Target $pair[1] -ErrorAction Stop | Out-Null
        } elseif ($item.LinkType -ne 'Junction' -or
                  [IO.Path]::GetFullPath([string]@($item.Target)[0]).TrimEnd('\') -ine $pair[1].TrimEnd('\')) {
            throw 'Existing package data/logs were preserved; they must not be overwritten.'
        }
    }
}

function Invoke-LumenisDesktopBundle {
    $plan = Get-LumenisDesktopBundlePlan $PSScriptRoot $DataRoot
    if ($DescribeBundle) {
        [pscustomobject]@{ schema = 'lumenis.windows-bundle-start-plan/v1';
            core_base_url = $plan.BaseUrl; core_port = $plan.Port;
            python = $plan.Python; app = $plan.App; data_root = $plan.Data;
            source_entry_sha256 = $plan.EntryHash; automatic_collection = $false;
            starts_product = $false; installer = $false } | ConvertTo-Json
        return
    }
    $mutex = New-Object Threading.Mutex($false, "Local\OEVIRA-Desktop-$($plan.Port)")
    $locked = $false
    $job = $null
    try {
        try { $locked = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked = $true }
        if (-not $locked) { throw 'This desktop bundle is already running.' }
        $socket = New-Object Net.Sockets.TcpClient
        try {
            $attempt = $socket.BeginConnect('127.0.0.1', $plan.Port, $null, $null)
            if ($attempt.AsyncWaitHandle.WaitOne(800)) {
                try { $socket.EndConnect($attempt); $occupied = $true } catch { $occupied = $false }
            } else { $occupied = $false }
        } finally { $socket.Dispose() }
        if ($occupied) {
            $identity = 'UNVERIFIED'
            try {
                $health = Invoke-RestMethod ($plan.BaseUrl + '/healthz') -TimeoutSec 2
                if ($health.core_instance.entry_sha256 -ceq $plan.EntryHash) { $identity = 'ENTRY_MATCHES' }
                else { $identity = 'ENTRY_DIFFERS' }
            } catch {}
            throw "The Core port is occupied ($identity). The existing instance was preserved."
        }
        Initialize-LumenisDesktopData $plan -AdoptExisting:$AdoptExistingDataRoot
        # Job objects are assigned before the process can execute. Closing the
        # launcher closes this job and reaps only its own Core/App descendants.
        # https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
        if (-not ('OeviraDesktopJob' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Collections;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
public sealed class OeviraDesktopJob : IDisposable {
  [StructLayout(LayoutKind.Sequential)] struct IO { public ulong a,b,c,d,e,f; }
  [StructLayout(LayoutKind.Sequential)] struct BASIC {
    public long processTime,jobTime; public uint flags;
    public UIntPtr min,max; public uint active; public UIntPtr affinity; public uint priority,scheduling;
  }
  [StructLayout(LayoutKind.Sequential)] struct LIMITS {
    public BASIC basic; public IO io; public UIntPtr pm,jm,peakP,peakJ;
  }
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct START {
    public uint cb; public string reserved,desktop,title; public uint x,y,xs,ys,xc,yc,fill,flags;
    public ushort show,reserved2; public IntPtr reservedPtr,input,output,error;
  }
  [StructLayout(LayoutKind.Sequential)] struct PI { public IntPtr process,thread; public uint pid,tid; }
  [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr a,string n);
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr j,int c,ref LIMITS l,uint n);
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(
    string a,StringBuilder c,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string dir,ref START s,out PI p);
  [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr t);
  [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr p,uint exit);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
  IntPtr job;
  public OeviraDesktopJob() {
    job=CreateJobObject(IntPtr.Zero,null);
    var limits=new LIMITS(); limits.basic.flags=0x2000;
    if(job==IntPtr.Zero || !SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf(limits))) {
      Dispose(); throw new System.ComponentModel.Win32Exception();
    }
  }
  public Process Start(string exe,string arguments,string directory,IDictionary environment,bool hidden) {
    var entries=new System.Collections.Generic.List<string>();
    foreach(DictionaryEntry entry in environment) entries.Add(entry.Key+"="+entry.Value);
    entries.Sort(StringComparer.OrdinalIgnoreCase);
    var block=Marshal.StringToHGlobalUni(String.Join("\0",entries)+"\0\0");
    var startup=new START(); startup.cb=(uint)Marshal.SizeOf(startup);
    var info=new PI();
    try {
      uint flags=0x4|0x400; if(hidden) flags|=0x08000000;
      if(!CreateProcess(exe,new StringBuilder("\""+exe+"\" "+arguments),IntPtr.Zero,IntPtr.Zero,
                        false,flags,block,directory,ref startup,out info))
        throw new System.ComponentModel.Win32Exception();
      if(!AssignProcessToJobObject(job,info.process)) {
        TerminateProcess(info.process,1); throw new System.ComponentModel.Win32Exception();
      }
      var result=Process.GetProcessById((int)info.pid);
      // Acquire the identity-bound handle while the new process is suspended,
      // before a quick exit could make a later PID-only lookup ambiguous.
      var heldHandle=result.Handle;
      if(ResumeThread(info.thread)==0xffffffff) {
        TerminateProcess(info.process,1); result.Dispose(); throw new System.ComponentModel.Win32Exception();
      }
      return result;
    } finally {
      if(info.thread!=IntPtr.Zero) CloseHandle(info.thread);
      if(info.process!=IntPtr.Zero) CloseHandle(info.process);
      Marshal.FreeHGlobal(block);
    }
  }
  public void Dispose() { if(job!=IntPtr.Zero) { CloseHandle(job); job=IntPtr.Zero; } }
}
'@
        }
        $childEnvironment = @{}
        foreach ($entry in [Environment]::GetEnvironmentVariables().GetEnumerator()) {
            $childEnvironment[[string]$entry.Key] = [string]$entry.Value
        }
        # Keep the user's proxy/network configuration. Remove only named product
        # credential/session bindings; never write or print the parent environment.
        foreach ($name in @('ZBC_API_KEY', 'V4_ACCESS_KEY', 'AI_API_KEY', 'OPENAI_API_KEY',
                            'USER_MODEL_API_KEY', 'LUMENIS_EVIDENCE_HMAC_KEY_RING',
                            'LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID',
                            'LUMENIS_TRAINING_RECEIPT_KEY_RING', 'LUMENIS_TRAINING_SSH_ENDPOINT_PATH',
                            'LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID',
                            'XHS_COOKIE', 'XHS_COOKIE_FILE', 'XHS_PROFILE_DIR', 'XHS_CDP_URL',
                            'XHS_CN_CDP_URL', 'XHS_HK_CDP_URL', 'DOUYIN_CDP_URL',
                            'X_READONLY_CDP_URL', 'ZBC_WEIBO_COOKIE_JSON', 'ZBC_BILI_COOKIE_JSON',
                            'EMAIL_SMTP_PASSWORD', 'SMTP_PASSWORD', 'WECHAT_APP_SECRET',
                            'WECOM_WEBHOOK_URL', 'SERVERCHAN_SEND_KEY', 'PUSHPLUS_TOKEN',
                            'PYTHONHOME', 'PYTHONPATH')) { $childEnvironment.Remove($name) }
        $launchId = [guid]::NewGuid().ToString('N')
        $childEnvironment.PYTHONUTF8 = '1'
        $childEnvironment.PYTHONIOENCODING = 'utf-8'
        $childEnvironment.PYTHONDONTWRITEBYTECODE = '1'
        $childEnvironment.ZBC_REPO_ROOT = $plan.Core
        $childEnvironment.LUMENIS_DESKTOP_BUNDLE_ROOT = $plan.Package
        $childEnvironment.ZBC_CORE_DIR = $plan.Core
        $childEnvironment.ZBC_DATA_DIR = $plan.Data
        $childEnvironment.ZBC_DB_PATH = Join-Path $plan.Data 'monitor.db'
        $childEnvironment.LOG_DIR = Join-Path $plan.Data 'logs'
        $childEnvironment.ZBC_LOG_DIR = $childEnvironment.LOG_DIR
        $childEnvironment.ZBC_RUNTIME_DIR = Join-Path $plan.Data 'browser_runtime'
        $childEnvironment.ZBC_BACKUP_DIR = Join-Path $plan.Data 'backups'
        $childEnvironment.ZBC_EXPORT_DIR = Join-Path $plan.Data 'exports'
        $childEnvironment.ZBC_TEMP_DIR = Join-Path $plan.Data 'temp'
        $childEnvironment.ZBC_AI_RUNTIME_DIR = Join-Path $plan.Data 'ai'
        $childEnvironment.ZBC_CONFIG_DIR = Join-Path $plan.Core 'config'
        $childEnvironment.ZBC_COLLECTOR_DIR = Join-Path $plan.Core 'collector_v2'
        $childEnvironment.LUMENIS_FFMPEG_PATH = Join-Path $plan.Package 'runtime/media/ffmpeg.exe'
        $childEnvironment.LUMENIS_FFPROBE_PATH = Join-Path $plan.Package 'runtime/media/ffprobe.exe'
        $childEnvironment.LUMENIS_CORE_LAUNCH_ID = $launchId
        $childEnvironment.LUMENIS_CORE_ENTRY_SHA256 = $plan.EntryHash
        $childEnvironment.LUMENIS_CORE_BOOT_ID = [guid]::NewGuid().ToString('N')
        $childEnvironment.ZB_WSGI = 'waitress'
        $childEnvironment.APP_ENV = 'prod'
        $childEnvironment.TAIKOO_PORT = '8201'
        $childEnvironment.PATH = (Join-Path $plan.Package 'runtime/python') + ';' +
            (Join-Path $plan.Package 'runtime/media') + ';' +
            (Join-Path $plan.Package 'runtime/python/Lib/site-packages/playwright/driver') + ';' +
            $childEnvironment.PATH
        $childEnvironment.MPLCONFIGDIR = Join-Path $plan.Data 'cache/matplotlib'
        $job = New-Object OeviraDesktopJob
        $arguments = '"' + (Join-Path $plan.Core 'app.py') + '" --manual-workspace --host 127.0.0.1 --port ' + $plan.Port + ' --no-scheduler'
        $coreProcess = $job.Start($plan.Python, $arguments, $plan.Core, $childEnvironment, $true)
        $ready = $false
        for ($i = 0; $i -lt 60; $i++) {
            if ($coreProcess.HasExited) { throw 'The bundled Core exited during startup. See the user-data logs.' }
            try {
                $health = Invoke-RestMethod ($plan.BaseUrl + '/healthz') -TimeoutSec 1
                if ($health.ok -eq $true -and $health.status -eq 'healthy' -and
                    $health.dependencies.database -eq 'ok' -and
                    $health.core_instance.launch_id -ceq $launchId -and
                    $health.core_instance.entry_sha256 -ceq $plan.EntryHash) { $ready = $true; break }
            } catch {}
            Start-Sleep -Milliseconds 500
        }
        if (-not $ready) { throw 'The bundled Core did not confirm this startup attempt. See the user-data logs.' }
        $appProcess = $job.Start($plan.App, '', (Split-Path -Parent $plan.App), $childEnvironment, $false)
        while (-not $appProcess.WaitForExit(500)) {
            if ($coreProcess.HasExited) { throw 'The Core stopped; this desktop session was closed safely.' }
        }
    } finally {
        if ($null -ne $job) { $job.Dispose() }
        if ($locked) { [void]$mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
}

if (($DescribeBundle -or $DataRoot -or $AdoptExistingDataRoot) -and -not $DesktopBundle) { throw 'Bundle data/inspection parameters require DesktopBundle.' }
if ($DesktopBundle -and $EnableScheduledCollection) { throw 'Desktop bundle startup uses manual Workspace; scheduled collection is not a startup action.' }
if ($DesktopBundle) {
    $ErrorActionPreference = 'Stop'
    $inheritedModulePath = $env:PSModulePath
    try {
        # Python/cmd children of PS7 can inherit incompatible PS7 modules.
        # Resolve built-in commands from this host before the first hash check.
        $env:PSModulePath = [IO.Path]::Combine($PSHOME, 'Modules')
        Invoke-LumenisDesktopBundle
        exit 0
    }
    catch {
        if (-not $DescribeBundle) {
            Add-Type -AssemblyName System.Windows.Forms
            [void][Windows.Forms.MessageBox]::Show($_.Exception.Message, 'OEVIRA')
        }
        [Console]::Error.WriteLine($_.Exception.Message)
        exit 1
    }
    finally { $env:PSModulePath = $inheritedModulePath }
}

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'
$env:PSModulePath = (Join-Path $PSHOME 'Modules') + [IO.Path]::PathSeparator + $env:PSModulePath

# Background processes inherit the Windows console code page by default.
# Keep every Python child on UTF-8 so non-ASCII migration/runtime diagnostics
# cannot crash production startup before the real health gate is reached.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# Single-instance mutex. Keep the historical mutex name for process compatibility.
$mutex = New-Object System.Threading.Mutex($false, 'Global\ZBrandCoreLauncher8201')
if (-not $mutex.WaitOne(0)) {
    Write-Output '[LUMENIS-8201] another launcher is running, exit'
    return
}
try {

# Resolve the repository from this script instead of depending on one developer-machine path.
$Root   = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Py     = Join-Path $Root '.venv\Scripts\python.exe'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Output ''
Write-Output '============================================================'
Write-Output ' LUMENIS production launcher'
Write-Output '   8201 Product Core; collection and browsing remain user initiated'
Write-Output '============================================================'
Write-Output "Root: $Root"

if (-not (Test-Path $Py)) {
    Write-Error 'FATAL .venv python.exe missing. Please run:  python -m venv .venv'
    exit 1
}
$pyVer = & $Py --version 2>&1
Write-Output "Python: $pyVer"

$depCheck = Join-Path $Root 'scripts\_prod_dep_check.py'
$check = & $Py $depCheck 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "FATAL missing deps: $check"
    Write-Error 'Please run:  .venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 2
}
Write-Output "Deps:   $check"
Write-Output ''

function Test-Http([string]$Url, [int]$TimeoutSec=3, [string]$ExpectedLaunchId='', [string]$ExpectedEntrySha256='') {
    try {
        $health = Invoke-RestMethod $Url -TimeoutSec $TimeoutSec
        if (-not ($health.ok -eq $true -and
                  $health.status -eq 'healthy' -and
                  $health.dependencies.database -eq 'ok')) { return $false }
        if ($ExpectedLaunchId -and $health.core_instance.launch_id -cne $ExpectedLaunchId) { return $false }
        if ($ExpectedEntrySha256 -and $health.core_instance.entry_sha256 -cne $ExpectedEntrySha256) { return $false }
        if (($ExpectedLaunchId -or $ExpectedEntrySha256) -and
            $health.core_instance.boot_id -cnotmatch '^[0-9a-f]{32}$') { return $false }
        return $true
    } catch { return $false }
}
function Get-CoreStartupDecision([bool]$Healthy, [bool]$EntryMatches, [int]$SupervisorCount, [bool]$Occupied, [bool]$SchedulerMatches) {
    if (-not $Healthy) {
        if ($Occupied -or $SupervisorCount -gt 0) { return 'BLOCKED_EXISTING_PROCESS' }
        return 'START_CORE'
    }
    if (-not $EntryMatches) { return 'BLOCKED_SOURCE_IDENTITY' }
    if ($SupervisorCount -ne 1) { return 'BLOCKED_PROCESS_OWNERSHIP' }
    if (-not $SchedulerMatches) { return 'BLOCKED_SCHEDULER_MODE' }
    return 'REUSE_MATCHING_CORE_ENTRY'
}
function Test-CorePortListening {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $attempt = $client.BeginConnect('127.0.0.1', 8201, $null, $null)
        if (-not $attempt.AsyncWaitHandle.WaitOne(1000)) { return $false }
        $client.EndConnect($attempt)
        return $true
    } catch { return $false }
    finally { $client.Dispose() }
}
function Get-CanonicalSupervisor {
    $rootPattern = [regex]::Escape($Root)
    $hits = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object {
            $_.CommandLine -and
            ($_.CommandLine -match 'run_supervised\.py') -and
            ($_.CommandLine -match '8201') -and
            ($_.CommandLine -match $rootPattern)
        })
    # Windows virtualenv launchers expose both the launcher and its Python
    # child with the same command line.  Count one supervisor tree, not two
    # processes, otherwise every idempotent launch looks like a duplicate.
    $ids = @($hits | ForEach-Object { [int]$_.ProcessId })
    @($hits | Where-Object { -not ($ids -contains [int]$_.ParentProcessId) })
}
function Wait-Healthz([string]$Url, [int]$Seconds=15, [string]$ExpectedLaunchId='', [string]$ExpectedEntrySha256='') {
    for ($i=0; $i -lt $Seconds; $i++) {
        if (Test-Http $Url -TimeoutSec 2 -ExpectedLaunchId $ExpectedLaunchId -ExpectedEntrySha256 $ExpectedEntrySha256) { return $true }
        Start-Sleep -Milliseconds 1000
    }
    return $false
}

$httpOk = Test-Http 'http://127.0.0.1:8201/healthz'
$entrySha256 = (Get-FileHash -LiteralPath (Join-Path $Root 'app.py') -Algorithm SHA256).Hash.ToLowerInvariant()
$entryMatches = $httpOk -and (Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedEntrySha256 $entrySha256)
$supervisors = @(Get-CanonicalSupervisor)
$ownedCore = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
    $_.CommandLine -and $_.CommandLine -match '(?:^|\s)--port\s+8201(?:\s|$)' -and
    $_.CommandLine -match 'app\.py' -and $_.CommandLine -match [regex]::Escape($Root)
})
$schedulerMatches = $false
if ($httpOk -and $supervisors.Count -eq 1) {
    $withoutScheduler = $supervisors[0].CommandLine -match '(?:^|\s)--no-scheduler(?:\s|$)'
    $schedulerMatches = $withoutScheduler -eq (-not $EnableScheduledCollection)
}
$occupied = (Test-CorePortListening) -or $ownedCore.Count -gt 0
$startupDecision = Get-CoreStartupDecision $httpOk $entryMatches $supervisors.Count $occupied $schedulerMatches
if ($startupDecision -like 'BLOCKED_*') {
    throw "Core startup $startupDecision; the running service was preserved. A controlled load requires verified ownership and quiescence."
}
if ($startupDecision -eq 'REUSE_MATCHING_CORE_ENTRY') {
    Write-Output '[LUMENIS-8201] healthy with matching Core entry bytes and one canonical supervisor, skip'
} else {
    if (Test-CorePortListening) { throw '8201 is still owned by a listener; replacement was not started and the supervisor lock was preserved.' }
    $supOut = Join-Path $LogDir 'supervisor_console.log'
    $supErr = Join-Path $LogDir 'supervisor_console.err'
    $launchId = [guid]::NewGuid().ToString('N')
    $supervisorArgs = @('run_supervised.py','--host','0.0.0.0','--port','8201','--launch-id',$launchId)
    if (-not $EnableScheduledCollection) { $supervisorArgs += '--no-scheduler' }
    Start-Process -FilePath $Py -ArgumentList $supervisorArgs -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $supOut -RedirectStandardError $supErr
    Write-Output '[LUMENIS-8201] starting single supervisor (run_supervised.py --port 8201)'
    Write-Output '[LUMENIS-8201] waiting healthz (max 15s)...'
    $up = Wait-Healthz 'http://127.0.0.1:8201/healthz' 15 -ExpectedLaunchId $launchId -ExpectedEntrySha256 $entrySha256
    if ($up) {
        Write-Output '[LUMENIS-8201] OK healthy database and fresh launch match the requested Core entry bytes'
    } else {
        Write-Error '8201 did not pass 15s health check.'
        Write-Error "  stdout: $supOut"
        Write-Error "  stderr: $supErr"
        Write-Error '--- last 20 stderr ---'
        Get-Content $supErr -Tail 20 -ErrorAction SilentlyContinue
    }
}

$coreHealthy = Test-Http 'http://127.0.0.1:8201/healthz' -ExpectedEntrySha256 $entrySha256
$readiness = if ($coreHealthy) { 'CORE_READY' } else { 'CORE_UNAVAILABLE' }
Write-Output ''
Write-Output '============================================================'
Write-Output "  Startup state: $readiness"
if ($coreHealthy) { Write-Output '  Core -> http://127.0.0.1:8201/' }
Write-Output '  HZ  ->  http://127.0.0.1:8201/healthz'
Write-Output '  Browser workers start only from an authorized browse/collection request.'
Write-Output '  Collection, AI and product task readiness require their own runtime evidence.'
Write-Output '============================================================'
if (-not $coreHealthy) { exit 1 }
exit 0

} finally {
    [void]$mutex.ReleaseMutex()
    $mutex.Dispose()
}
