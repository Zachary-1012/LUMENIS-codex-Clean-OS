<#
.SYNOPSIS
广州太古汇舆情监测系统 - 自动守护闭环脚本
.DESCRIPTION
自动检测系统运行状态，崩溃后5秒内自动重启，形成稳定运行闭环
#>

$ErrorActionPreference = "SilentlyContinue"
$WorkDir = "D:\Taikoo-monitor-new"
$PythonExe = "$WorkDir\.venv\Scripts\python.exe"
$AppFile = "$WorkDir\app.py"
$Port = 8200
$LogFile = "$WorkDir\guardian_loop.log"
$MaxRestarts = 10  # 1小时内最大重启次数
$RestartWindow = 3600  # 1小时窗口（秒）
$CheckInterval = 10  # 检查间隔（秒）

$restartTimes = @()

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$timestamp] $Message"
    Add-Content -Path $LogFile -Value $logMsg -Encoding UTF8
    Write-Host $logMsg
}

function Test-SystemRunning {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect("127.0.0.1", $Port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne(2000, $false)
        $tcp.Close()
        return $wait
    } catch {
        return $false
    }
}

function Test-ApiResponding {
    try {
        $auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("Zachary:ID082610"))
        $headers = @{Authorization = "Basic $auth"}
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/architecture/status" -Headers $headers -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-System {
    Write-Log "正在启动系统..."
    Set-Location $WorkDir
    $env:PYTHONUNBUFFERED = "1"
    $process = Start-Process -FilePath $PythonExe -ArgumentList $AppFile, "--host", "0.0.0.0", "--port", $Port -WorkingDirectory $WorkDir -WindowStyle Minimized -PassThru
    Write-Log "系统进程已启动，PID: $($process.Id)"
    return $process.Id
}

function Stop-System {
    Write-Log "正在停止系统..."
    Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*Taikoo-monitor-new*" -or $_.MainWindowTitle -like "*python*" } | Stop-Process -Force
    Start-Sleep -Seconds 2
    # 确保端口释放
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
    Write-Log "系统已停止"
}

function Check-RestartLimit {
    $now = Get-Date
    $script:restartTimes = $script:restartTimes | Where-Object { ($now - $_).TotalSeconds -lt $RestartWindow }
    if ($script:restartTimes.Count -ge $MaxRestarts) {
        Write-Log "⚠️ 警告：1小时内重启次数达到$MaxRestarts次，可能存在严重问题，暂停自动重启"
        return $false
    }
    return $true
}

# 主循环
Write-Log "========================================"
Write-Log "广州太古汇舆情监测系统 - 守护闭环启动"
Write-Log "工作目录: $WorkDir"
Write-Log "监控端口: $Port"
Write-Log "检查间隔: ${CheckInterval}秒"
Write-Log "========================================"

$firstStart = $true

while ($true) {
    try {
        $portOpen = Test-SystemRunning
        $apiOk = $false
        
        if ($portOpen) {
            $apiOk = Test-ApiResponding
        }
        
        if (-not $portOpen -or -not $apiOk) {
            if ($firstStart) {
                Write-Log "系统未运行，首次启动..."
                $firstStart = $false
            } else {
                Write-Log "⚠️ 系统异常！端口开放: $portOpen, API响应: $apiOk，准备重启..."
            }
            
            # 检查重启频率限制
            if (-not (Check-RestartLimit)) {
                Write-Log "重启频率超限，等待5分钟后重试..."
                Start-Sleep -Seconds 300
                continue
            }
            
            # 停止旧进程
            Stop-System
            
            # 等待端口释放
            Start-Sleep -Seconds 3
            
            # 启动系统
            $pid = Start-System
            $script:restartTimes += Get-Date
            
            # 等待系统启动（最多60秒）
            Write-Log "等待系统启动..."
            $started = $false
            for ($i = 0; $i -lt 12; $i++) {
                Start-Sleep -Seconds 5
                if (Test-SystemRunning) {
                    if (Test-ApiResponding) {
                        $started = $true
                        Write-Log "✅ 系统启动成功！"
                        break
                    }
                }
            }
            
            if (-not $started) {
                Write-Log "❌ 系统启动超时，将在下一轮检查中重试"
            }
        } else {
            # 系统正常运行
            if ($firstStart) {
                Write-Log "✅ 系统已在运行，守护闭环监控中..."
                $firstStart = $false
            }
        }
        
        Start-Sleep -Seconds $CheckInterval
        
    } catch {
        Write-Log "❌ 守护脚本异常: $($_.Exception.Message)"
        Start-Sleep -Seconds 10
    }
}
