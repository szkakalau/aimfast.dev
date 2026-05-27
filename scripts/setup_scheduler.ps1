# KAKAOPC 情报科 — Windows Task Scheduler 安装脚本
# 以管理员身份运行此脚本以注册每日定时任务
# 用法: powershell -ExecutionPolicy Bypass -File scripts/setup_scheduler.ps1

$TaskName = "KAKAOPC-Intel-Daily"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ScriptPath = Join-Path $ProjectRoot "scripts\daily_run.ps1"

Write-Host "=== KAKAOPC 情报科 定时任务安装 ==="
Write-Host "项目目录: $ProjectRoot"
Write-Host "调度脚本: $ScriptPath"
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "[错误] 需要管理员权限来创建计划任务。"
    Write-Host "请以管理员身份运行 PowerShell 后重试。"
    exit 1
}

# 删除旧任务（如果存在）
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "删除旧任务: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建任务操作
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$ScriptPath`""

# 创建触发器：每天 08:00
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

# 任务配置
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -WakeToRun:$false

# 注册任务
try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "KAKAOPC 情报科每日情报采集与生成（08:00 触发）"

    Write-Host ""
    Write-Host "定时任务已安装！"
    Write-Host "  任务名称: $TaskName"
    Write-Host "  触发时间: 每天 08:00"
    Write-Host "  执行脚本: $ScriptPath"
    Write-Host "  日志目录: $ProjectRoot\logs\"
    Write-Host ""
    Write-Host "管理命令:"
    Write-Host "  查看任务:   Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  手动运行:   Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  查看状态:   Get-ScheduledTaskInfo -TaskName '$TaskName'"
    Write-Host "  删除任务:   Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
} catch {
    Write-Host "[错误] 任务注册失败: $_"
    exit 1
}
