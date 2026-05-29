# KAKAOPC Intel — Windows Task Scheduler Setup
# Run as Administrator to register the daily scheduled task
# Usage: powershell -ExecutionPolicy Bypass -File scripts/setup_scheduler.ps1

$TaskName = "KAKAOPC-Intel-Daily"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ScriptPath = Join-Path $ProjectRoot "scripts\daily_run.ps1"

Write-Host "=== KAKAOPC Intel Task Scheduler Setup ==="
Write-Host "Project: $ProjectRoot"
Write-Host "Script: $ScriptPath"
Write-Host ""

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "[ERROR] Administrator privileges required to create a scheduled task."
    Write-Host "Please run PowerShell as Administrator and try again."
    exit 1
}

# Remove old task if exists
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing old task: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create task action
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$ScriptPath`""

# Create trigger: daily at 08:00
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

# Principal: run as current user
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U -RunLevel Limited

# Settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -WakeToRun:$false

# Register the task
try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "KAKAOPC Intel Daily Pipeline (08:00 trigger)"

    Write-Host ""
    Write-Host "Task installed successfully!"
    Write-Host "  Name: $TaskName"
    Write-Host "  Trigger: Daily at 08:00"
    Write-Host "  Script: $ScriptPath"
    Write-Host "  Logs: $ProjectRoot\logs\"
    Write-Host ""
    Write-Host "Management commands:"
    Write-Host "  View:   Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  Run:    Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  Status: Get-ScheduledTaskInfo -TaskName '$TaskName'"
    Write-Host "  Delete: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
} catch {
    Write-Host "[ERROR] Task registration failed: $_"
    exit 1
}
