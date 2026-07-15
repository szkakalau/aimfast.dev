# AimFast.Dev — Daily Pipeline Orchestrator
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

Write-Log "=== AimFast.Dev Daily Pipeline Start ==="
Write-Log "Date: $Date"
Write-Log "Project: $ProjectRoot"
Write-Log "Python: $Python"

# Day-level lock file to prevent duplicate runs (avoid double LLM cost)
$DailyDir = Join-Path $ProjectRoot "daily\$Date"
$LockFile = Join-Path $DailyDir ".pipeline_done"
New-Item -ItemType Directory -Force -Path $DailyDir | Out-Null
if (Test-Path $LockFile) {
    Write-Log "Pipeline already completed for $Date (lock file exists). Exiting."
    exit 0
}

# --- Step 1: Signal Collection (each collector runs independently) ---

$Collectors = @(
    @{Name="Hacker News"; Script="collect_hackernews"; Enabled=$true},
    @{Name="GitHub Trending"; Script="collect_github"; Enabled=$true},
    @{Name="Google Trends"; Script="collect_trends"; Enabled=$true},
    @{Name="Product Hunt"; Script="collect_producthunt"; Enabled=$true},
    @{Name="DEV Community"; Script="collect_devcommunity"; Enabled=$true},
    @{Name="Reddit (11 subs)"; Script="collect_reddit"; Enabled=$true},
    @{Name="Reddit Consumer"; Script="collect_reddit_consumer"; Enabled=$true},
    @{Name="V2EX"; Script="collect_v2ex"; Enabled=$true},
    @{Name="w2solo"; Script="collect_w2solo"; Enabled=$true},
    @{Name="HuggingFace"; Script="collect_huggingface"; Enabled=$true},
    @{Name="Lobsters"; Script="collect_lobsters"; Enabled=$true},
    @{Name="ArXiv"; Script="collect_arxiv"; Enabled=$true},
    @{Name="豆瓣"; Script="collect_douban"; Enabled=$true},
    @{Name="小红书"; Script="collect_xiaohongshu"; Enabled=$true},
    @{Name="X/Twitter"; Script="collect_x"; Enabled=$true},
    @{Name="npm"; Script="collect_npm"; Enabled=$true},
    @{Name="PyPI"; Script="collect_pypi"; Enabled=$true},
    @{Name="Stack Overflow"; Script="collect_stackoverflow"; Enabled=$true},
    @{Name="YouTube"; Script="collect_youtube"; Enabled=$true}
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
    if ($LASTEXITCODE -ne 0) {
        Write-Log "  [Process] FAIL (exit=$LASTEXITCODE)"
    } else {
        Write-Log "  [Process] OK"
    }
} catch {
    Write-Log "  [Process] FAIL: $_"
}

# --- Step 2.5: Enrich Top Signals with /last30days ---

Write-Log ""
Write-Log "--- Step 2.5: Community Enrichment (/last30days) ---"

try {
    $output = & $Python -m scripts.enrich_signals 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  [Enrich] OK"
    } else {
        Write-Log "  [Enrich] WARN (non-fatal, exit=$LASTEXITCODE)"
    }
} catch {
    Write-Log "  [Enrich] FAIL (non-fatal): $_"
}

# --- Step 2.6: Merge Competitor Targets (merge Dashboard-added pending targets) ---

Write-Log ""
Write-Log "--- Step 2.6: Merge Competitor Targets ---"

try {
    $output = & $Python -m scripts.merge_competitor_targets 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  [MergeTargets] OK"
    } else {
        Write-Log "  [MergeTargets] WARN (non-fatal, exit=$LASTEXITCODE)"
    }
} catch {
    Write-Log "  [MergeTargets] FAIL (non-fatal): $_"
}

# --- Step 2.7: Competitor Matching ---

Write-Log ""
Write-Log "--- Step 2.6: Competitor Matching (Phase 1 双引擎) ---"

try {
    $output = & $Python -m scripts.match_competitors 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  [MatchCompetitor] OK"
    } else {
        Write-Log "  [MatchCompetitor] WARN (non-fatal, exit=$LASTEXITCODE)"
    }
} catch {
    Write-Log "  [MatchCompetitor] FAIL (non-fatal): $_"
}

# --- Step 2.7: Competitor Intel Generation ---

Write-Log ""
Write-Log "--- Step 2.7: Competitor Intel (LLM) ---"

try {
    $output = & $Python -m scripts.generate_competitor_intel 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  [CompetitorIntel] OK"
    } else {
        Write-Log "  [CompetitorIntel] WARN (non-fatal, exit=$LASTEXITCODE)"
    }
} catch {
    Write-Log "  [CompetitorIntel] FAIL (non-fatal): $_"
}

# --- Step 3: Daily Report ---

Write-Log ""
Write-Log "--- Step 3: Daily Report ---"

try {
    $output = & $Python -m scripts.generate_report 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "  [Report] FAIL (exit=$LASTEXITCODE)"
    } else {
        Write-Log "  [Report] OK"
    }
} catch {
    Write-Log "  [Report] FAIL: $_"
}

# --- Step 3.5: Trend Discovery ---

Write-Log ""
Write-Log "--- Step 3.5: Trend Discovery ---"

try {
    $output = & $Python -m scripts.generate_trends 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  [Trends] OK"
    } else {
        Write-Log "  [Trends] FAIL (non-fatal, exit=$LASTEXITCODE)"
    }
} catch {
    Write-Log "  [Trends] FAIL (non-fatal): $_"
}

# --- Step 3.6: Opportunity Analysis ---

Write-Log ""
Write-Log "--- Step 3.6: Opportunity Analysis ---"

try {
    $output = & $Python -m scripts.generate_opportunity 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "  [Opportunity] OK"
    } else {
        Write-Log "  [Opportunity] FAIL (non-fatal, exit=$LASTEXITCODE)"
    }
} catch {
    Write-Log "  [Opportunity] FAIL (non-fatal): $_"
}

# --- Step 4: Planet Article (DISABLED) ---
# 星球文章生成已禁用 — config.json distribution.planet_article.enabled = false

Write-Log ""
Write-Log "--- Step 4: Planet Article (DISABLED) ---"
Write-Log "  [Article] DISABLED — planet_article generation turned off in config.json"

# --- Step 5: Action Plan ---

Write-Log ""
Write-Log "--- Step 5: Action Plan ---"

try {
    $output = & $Python -m scripts.generate_action 2>&1
    $pipeFile = Join-Path $ProjectRoot "daily\$Date\pipeline.json"
    if (Test-Path $pipeFile) {
        $pipeData = Get-Content $pipeFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($pipeData.steps.action.status -eq "skipped") {
            Write-Log "  [Action] SKIPPED ($($pipeData.steps.action.reason))"
        } else {
            Write-Log "  [Action] OK"
        }
    } else {
        Write-Log "  [Action] OK"
    }
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

# --- Step 6b: Recurring Signal Tracking ---

Write-Log ""
Write-Log "--- Step 6b: Recurring Signal Tracking ---"

try {
    $output = & $Python -m scripts.track_recurring 2>&1
    Write-Log "  [Recurring] OK"
} catch {
    Write-Log "  [Recurring] FAIL: $_"
}

# --- Step 6c: Demand Radar ---

Write-Log ""
Write-Log "--- Step 6c: Demand Radar ---"

try {
    $output = & $Python -m scripts.track_demands 2>&1
    Write-Log "  [DemandRadar] OK"
} catch {
    Write-Log "  [DemandRadar] FAIL: $_"
}

# --- Step 6d: Workbench Report ---

Write-Log ""
Write-Log "--- Step 6d: Workbench Report ---"

try {
    $output = & $Python -m scripts.update_workbench 2>&1
    Write-Log "  [Workbench] OK"
} catch {
    Write-Log "  [Workbench] FAIL: $_"
}

# --- Step 6e: Prediction Logging (daily) ---

Write-Log ""
Write-Log "--- Step 6e: Prediction Logging ---"

try {
    $output = & $Python -m scripts.calibrate_scoring log 2>&1
    Write-Log "  [PredictLog] OK"
} catch {
    Write-Log "  [PredictLog] FAIL (non-fatal): $_"
}

# --- Step 7: Landing Page Generation ---

Write-Log ""
Write-Log "--- Step 7: Landing Page ---"

try {
    $output = & $Python -m scripts.generate_landing_page 2>&1
    $pipeFile = Join-Path $ProjectRoot "daily\$Date\pipeline.json"
    if (Test-Path $pipeFile) {
        $pipeData = Get-Content $pipeFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($pipeData.steps.lp.status -eq "skipped") {
            Write-Log "  [LP] SKIPPED ($($pipeData.steps.lp.reason))"
        } else {
            Write-Log "  [LP] OK"
        }
    } else {
        Write-Log "  [LP] OK"
    }
} catch {
    Write-Log "  [LP] FAIL: $_"
}

# --- Step 8: Translate Content (zh → en) ---

Write-Log ""
Write-Log "--- Step 9: Translate Content (zh → en) ---"

try {
    $output = & $Python -m scripts.translate_content 2>&1
    Write-Log "  [Translate] OK"
} catch {
    Write-Log "  [Translate] FAIL (non-fatal): $_"
}

# --- Step 10: SEO Content Files ---

Write-Log ""
Write-Log "--- Step 10: SEO Content Files ---"

try {
    $output = & $Python -m scripts.generate_seo_files 2>&1
    Write-Log "  [SEO] OK"
} catch {
    Write-Log "  [SEO] FAIL (non-fatal): $_"
}

# --- Step 11: Dashboard Data ---

Write-Log ""
Write-Log "--- Step 11: Dashboard ---"

try {
    $output = & $Python -m scripts.generate_dashboard 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "  [Dashboard] FAIL (exit=$LASTEXITCODE)"
    } else {
        Write-Log "  [Dashboard] OK"
    }
} catch {
    Write-Log "  [Dashboard] FAIL: $_"
}

# --- Step 12: Weekly Report (Sunday only) ---

$DayOfWeek = (Get-Date).DayOfWeek
if ($DayOfWeek -eq 'Sunday') {
    Write-Log ""
    Write-Log "--- Step 12: Weekly Report (Sunday trigger) ---"

    try {
        $output = & $Python -m scripts.generate_weekly 2>&1
        Write-Log "  [Weekly] OK"
    } catch {
        Write-Log "  [Weekly] FAIL: $_"
    }

    # Weekly community deep-dive (30-day lookback on the week's hottest topic)
    try {
        $output = & $Python -m scripts.enrich_signals --weekly 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "  [WeeklyEnrich] OK"
        } else {
            Write-Log "  [WeeklyEnrich] WARN (non-fatal, exit=$LASTEXITCODE)"
        }
    } catch {
        Write-Log "  [WeeklyEnrich] FAIL (non-fatal): $_"
    }

    # Weekly calibration: analyze prediction accuracy, adjust scoring weights
    try {
        $output = & $Python -m scripts.calibrate_scoring calibrate 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "  [Calibrate] OK"
        } else {
            Write-Log "  [Calibrate] WARN (non-fatal, exit=$LASTEXITCODE)"
        }
    } catch {
        Write-Log "  [Calibrate] FAIL (non-fatal): $_"
    }
}

# --- Step 13: Git commit & push dashboard data ---

Write-Log ""
Write-Log "--- Step 13: Deploy Dashboard Data & SEO Content ---"

try {
    Push-Location $ProjectRoot
    git add public/dashboard/data/dashboard.json tracking/recurring_signals.json tracking/demand_radar.json tracking/competitor_targets.json tracking/trend_terms.json public/sitemap.xml content/reports/ content/articles/ content/trends/ public/*/index.html daily/*/signals.json daily/*/competitor_matches.json daily/*/competitor_intel.json 2>&1 | Out-Null

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

# Write lock file to prevent duplicate runs today
"done" | Out-File -FilePath $LockFile -Encoding UTF8

if (Test-Path $DailyDir) {
    $files = Get-ChildItem $DailyDir -File | ForEach-Object { "$($_.Name) ($($_.Length) bytes)" }
    Write-Log "Output: $($files -join ', ')"
}

Write-Log "Log: $LogFile"
