# KAKAOPC Intel — Daily Pipeline Orchestrator
# Usage: powershell -ExecutionPolicy Bypass -File scripts/daily_run.ps1
# Windows Task Scheduler trigger: daily at 08:00

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Date = (Get-Date).ToString("yyyy-MM-dd")
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "$Date.log"

# CRITICAL: Task Scheduler runs with CWD = C:\Windows\System32.
# Python -m needs the project root as CWD to find the scripts package.
Set-Location $ProjectRoot

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Resolve Python path — Task Scheduler may not have user PATH
$Python = $null
$PythonCandidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "python"
)
foreach ($candidate in $PythonCandidates) {
    try {
        $null = & $candidate --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $Python = $candidate
            break
        }
    } catch {}
}
if (-not $Python) {
    Write-Host "[FATAL] Python not found. Tried: $($PythonCandidates -join ', ')"
    exit 1
}

function Write-Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "=== KAKAOPC Intel Daily Pipeline Start ==="
Write-Log "Date: $Date"
Write-Log "Project: $ProjectRoot"
Write-Log "Python: $Python"

# --- Step 1: Signal Collection (each collector runs independently) ---

$Collectors = @(
    @{Name="Hacker News"; Script="collect_hackernews"; Enabled=$true},
    @{Name="GitHub Trending"; Script="collect_github"; Enabled=$true},
    @{Name="Google Trends"; Script="collect_trends"; Enabled=$true},
    @{Name="Product Hunt"; Script="collect_producthunt"; Enabled=$true},
    @{Name="Reddit"; Script="collect_reddit"; Enabled=$true},
    @{Name="Indie Hackers"; Script="collect_indiehackers"; Enabled=$true},
    @{Name="V2EX"; Script="collect_v2ex"; Enabled=$true},
    @{Name="w2solo"; Script="collect_w2solo"; Enabled=$true},
    @{Name="HuggingFace"; Script="collect_huggingface"; Enabled=$true},
    @{Name="TikTok"; Script="collect_tiktok"; Enabled=$true},
    @{Name="Jike"; Script="collect_jike"; Enabled=$true},
    @{Name="Xiaohongshu"; Script="collect_xiaohongshu"; Enabled=$true}
)

Write-Log ""
Write-Log "--- Step 1: Signal Collection ---"

foreach ($c in $Collectors) {
    if (-not $c.Enabled) {
        Write-Log "  [$($c.Name)] disabled, skip"
        continue
    }
    try {
        $output = & $Python -m "scripts.$($c.Script)" 2>&1
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0) {
            Write-Log "  [$($c.Name)] OK"
        } else {
            Write-Log "  [$($c.Name)] ERROR (exit=$exitCode)"
        }
    } catch {
        Write-Log "  [$($c.Name)] FAIL: $_"
    }
}

# --- Step 2: Signal Processing ---

Write-Log ""
Write-Log "--- Step 2: Signal Processing ---"

try {
    $output = & $Python -m scripts.process_signals 2>&1
    Write-Log "  [Process] OK"
} catch {
    Write-Log "  [Process] FAIL: $_"
}

# --- Step 3: Daily Report ---

Write-Log ""
Write-Log "--- Step 3: Daily Report ---"

try {
    $output = & $Python -m scripts.generate_report 2>&1
    Write-Log "  [Report] OK"
} catch {
    Write-Log "  [Report] FAIL: $_"
}

# --- Step 4: Planet Article ---

Write-Log ""
Write-Log "--- Step 4: Planet Article ---"

try {
    $output = & $Python -m scripts.generate_article 2>&1
    Write-Log "  [Article] OK"
} catch {
    Write-Log "  [Article] FAIL: $_"
}

# --- Step 5: Action Plan ---

Write-Log ""
Write-Log "--- Step 5: Action Plan ---"

try {
    $output = & $Python -m scripts.generate_action 2>&1
    Write-Log "  [Action] OK"
} catch {
    Write-Log "  [Action] FAIL: $_"
}

# --- Step 6: Tracking Update ---

Write-Log ""
Write-Log "--- Step 6: Tracking Update ---"

try {
    $output = & $Python -m scripts.update_tracking 2>&1
    Write-Log "  [Tracking] OK"
} catch {
    Write-Log "  [Tracking] FAIL: $_"
}

# --- Step 7: Landing Page Generation ---

Write-Log ""
Write-Log "--- Step 7: Landing Page ---"

try {
    $output = & $Python -m scripts.generate_landing_page 2>&1
    Write-Log "  [LP] OK"
} catch {
    Write-Log "  [LP] FAIL: $_"
}

# --- Step 8: Dashboard Data ---

Write-Log ""
Write-Log "--- Step 8: Dashboard ---"

try {
    $output = & $Python -m scripts.generate_dashboard 2>&1
    Write-Log "  [Dashboard] OK"
} catch {
    Write-Log "  [Dashboard] FAIL: $_"
}

# --- Step 9: Weekly Report (Sunday only) ---


# --- Step 10: Jike Post Generation ---

Write-Log ""
Write-Log "--- Step 10: Jike Post ---"

try {
    $output = & $Python -m scripts.generate_jike_post 2>&1
    Write-Log "  [JikePost] OK"
} catch {
    Write-Log "  [JikePost] FAIL: $_"
}

# --- Step 11: Weekly Report (Sunday only) ---

$DayOfWeek = (Get-Date).DayOfWeek
if ($DayOfWeek -eq 'Sunday') {
    Write-Log ""
    Write-Log "--- Step 9: Weekly Report (Sunday trigger) ---"

    try {
        $output = & $Python -m scripts.generate_weekly 2>&1
        Write-Log "  [Weekly] OK"
    } catch {
        Write-Log "  [Weekly] FAIL: $_"
    }
}

# --- Step 12: Git commit & push dashboard data ---

Write-Log ""
Write-Log "--- Step 10: Deploy Dashboard Data ---"

try {
    Push-Location $ProjectRoot
    git add public/dashboard/data/dashboard.json 2>&1 | Out-Null

    # Check if there are staged changes
    $diffOut = git diff --cached --name-only 2>&1
    if ($diffOut) {
        git commit -m "Dashboard data update: $Date" 2>&1 | Out-Null
        Write-Log "  [Git] Committed dashboard data for $Date"

        git push origin master 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "  [Git] Pushed to origin/master → Vercel deploy triggered"
        } else {
            Write-Log "  [Git] Push FAILED (exit=$LASTEXITCODE)"
        }
    } else {
        Write-Log "  [Git] No changes to deploy"
    }
    Pop-Location
} catch {
    Write-Log "  [Git] FAIL: $_"
}

# --- Summary ---

Write-Log ""
Write-Log "=== Pipeline Complete ==="

$DailyDir = Join-Path $ProjectRoot "daily\$Date"
if (Test-Path $DailyDir) {
    $files = Get-ChildItem $DailyDir -File | ForEach-Object { "$($_.Name) ($($_.Length) bytes)" }
    Write-Log "Output: $($files -join ', ')"
}

Write-Log "Log: $LogFile"
