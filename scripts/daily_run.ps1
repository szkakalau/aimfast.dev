# KAKAOPC 情报科 — 每日调度脚本
# 用法: powershell -ExecutionPolicy Bypass -File scripts/daily_run.ps1
# Windows Task Scheduler: 每天 08:00 触发

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Date = (Get-Date).ToString("yyyy-MM-dd")
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "$Date.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "=== KAKAOPC 情报科 每日调度开始 ==="
Write-Log "日期: $Date"
Write-Log "项目目录: $ProjectRoot"

# ─── Step 1: 采集（每个采集器独立运行，失败不影响后续） ───

$Collectors = @(
    @{Name="Hacker News"; Script="collect_hackernews"; Enabled=$true},
    @{Name="GitHub Trending"; Script="collect_github"; Enabled=$true},
    @{Name="Google Trends"; Script="collect_trends"; Enabled=$true},
    @{Name="Product Hunt"; Script="collect_producthunt"; Enabled=$true},
    @{Name="Reddit"; Script="collect_reddit"; Enabled=$true},
    @{Name="Indie Hackers"; Script="collect_indiehackers"; Enabled=$true},
    @{Name="V2EX"; Script="collect_v2ex"; Enabled=$true},
    @{Name="HuggingFace"; Script="collect_huggingface"; Enabled=$true},
    @{Name="TikTok"; Script="collect_tiktok"; Enabled=$true},
    @{Name="Jike"; Script="collect_jike"; Enabled=$true},
    @{Name="Xiaohongshu"; Script="collect_xiaohongshu"; Enabled=$true}
)

Write-Log ""
Write-Log "--- Step 1: 信号采集 ---"

foreach ($c in $Collectors) {
    if (-not $c.Enabled) {
        Write-Log "  [$($c.Name)] 已禁用，跳过"
        continue
    }
    try {
        $output = python -m "scripts.$($c.Script)" 2>&1
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0) {
            Write-Log "  [$($c.Name)] 完成"
        } else {
            Write-Log "  [$($c.Name)] 异常 (exit=$exitCode)"
        }
    } catch {
        Write-Log "  [$($c.Name)] 失败: $_"
    }
}

# ─── Step 2: 处理 ───

Write-Log ""
Write-Log "--- Step 2: 信号处理 ---"

try {
    $output = python -m scripts.process_signals 2>&1
    Write-Log "  [处理] 完成"
} catch {
    Write-Log "  [处理] 失败: $_"
}

# ─── Step 3: 日报 ───

Write-Log ""
Write-Log "--- Step 3: 日报生成 ---"

try {
    $output = python -m scripts.generate_report 2>&1
    Write-Log "  [日报] 完成"
} catch {
    Write-Log "  [日报] 失败: $_"
}

# ─── Step 4: 文章 ───

Write-Log ""
Write-Log "--- Step 4: 文章生成 ---"

try {
    $output = python -m scripts.generate_article 2>&1
    Write-Log "  [文章] 完成"
} catch {
    Write-Log "  [文章] 失败: $_"
}

# ─── Step 5: Action 方案 ───

Write-Log ""
Write-Log "--- Step 5: Action 方案 ---"

try {
    $output = python -m scripts.generate_action 2>&1
    Write-Log "  [Action] 完成"
} catch {
    Write-Log "  [Action] 失败: $_"
}

# ─── Step 6: 追踪更新 ───

Write-Log ""
Write-Log "--- Step 6: 追踪更新 ---"

try {
    $output = python -m scripts.update_tracking 2>&1
    Write-Log "  [追踪] 完成"
} catch {
    Write-Log "  [追踪] 失败: $_"
}

# ─── Step 7: Landing Page 生成（仅当 Action 方案存在时） ───

Write-Log ""
Write-Log "--- Step 7: Landing Page 生成 ---"

try {
    $output = python -m scripts.generate_landing_page 2>&1
    Write-Log "  [LP] 完成"
} catch {
    Write-Log "  [LP] 失败: $_"
}

# ─── Step 8: Dashboard ───

Write-Log ""
Write-Log "--- Step 8: Dashboard 生成 ---"

try {
    $output = python -m scripts.generate_dashboard 2>&1
    Write-Log "  [Dashboard] 完成"
} catch {
    Write-Log "  [Dashboard] 失败: $_"
}

# ─── Step 9: 周报（仅周日） ───

$DayOfWeek = (Get-Date).DayOfWeek
if ($DayOfWeek -eq 'Sunday') {
    Write-Log ""
    Write-Log "--- Step 9: 周报生成（周日触发） ---"

    try {
        $output = python -m scripts.generate_weekly 2>&1
        Write-Log "  [周报] 完成"
    } catch {
        Write-Log "  [周报] 失败: $_"
    }
}

# ─── 汇总 ───

Write-Log ""
Write-Log "=== 调度完成 ==="

# 统计今日产出
$DailyDir = Join-Path $ProjectRoot "daily" $Date
if (Test-Path $DailyDir) {
    $files = Get-ChildItem $DailyDir -File | ForEach-Object { "$($_.Name) ($($_.Length) bytes)" }
    Write-Log "产出文件: $($files -join ', ')"
}

Write-Log "日志: $LogFile"
