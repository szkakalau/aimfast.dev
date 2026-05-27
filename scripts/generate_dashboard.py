"""
Dashboard 生成器
读取 daily/ + tracking/ 数据，生成自包含 HTML Dashboard。
输出: dashboard/index.html
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
OUTPUT_DIR = ROOT / "dashboard"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def collect_dashboard_data() -> dict:
    """收集所有 dashboard 需要的数据。"""
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    # 1. 今日信号
    today_signals = []
    today_path = DAILY_DIR / today / "signals.json"
    if today_path.exists():
        data = json.loads(today_path.read_text(encoding="utf-8"))
        today_signals = data.get("signals", [])[:30]
        today_summary = data.get("summary", {})
        today_date = today
    else:
        today_summary = {}
        today_date = today

    # 2. 历史数据（最近 14 天）
    history = []
    for i in range(14):
        d = (datetime.now(TZ_SHANGHAI) - timedelta(days=i)).strftime("%Y-%m-%d")
        signals_path = DAILY_DIR / d / "signals.json"
        if signals_path.exists():
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            summary = data.get("summary", {})
            history.append({
                "date": d,
                "total_signals": data.get("total_raw", 0),
                "top_score": summary.get("top_score", 0),
                "avg_score": summary.get("avg_score", 0),
                "action_qualified": summary.get("action_qualified", 0),
                "cross_platform": summary.get("cross_platform_signals", 0),
            })

    # 3. 机会追踪
    opportunities = []
    opp_path = TRACKING_DIR / "opportunities.json"
    if opp_path.exists():
        data = json.loads(opp_path.read_text(encoding="utf-8"))
        opportunities = data.get("opportunities", [])

    # 4. 今日日报（markdown 原文）
    report_md = ""
    report_path = DAILY_DIR / today / "report.md"
    if report_path.exists():
        report_md = report_path.read_text(encoding="utf-8")

    return {
        "date": today_date,
        "signals": today_signals,
        "summary": today_summary,
        "history": list(reversed(history)),
        "opportunities": opportunities,
        "report_md": report_md,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
    }


def generate_html(data: dict) -> str:
    """生成完整的 HTML dashboard。"""
    signals_json = json.dumps(data["signals"], ensure_ascii=False)
    history_json = json.dumps(data["history"], ensure_ascii=False)
    opps_json = json.dumps(data["opportunities"], ensure_ascii=False)
    summary = data["summary"]
    report_md_json = json.dumps(data["report_md"], ensure_ascii=False)

    html = _HTML_TEMPLATE
    html = html.replace("__DATE__", data["date"])
    html = html.replace("__SIGNAL_COUNT__", str(len(data["signals"])))
    html = html.replace("__TOP_SCORE__", str(summary.get("top_score", 0)))
    html = html.replace("__AVG_SCORE__", str(summary.get("avg_score", 0)))
    html = html.replace("__ACTION_COUNT__", str(summary.get("action_qualified", 0)))
    html = html.replace("__CROSS_PLATFORM__", str(summary.get("cross_platform_signals", 0)))
    html = html.replace("__GENERATED_AT__", data["generated_at"][:19])
    html = html.replace("__SIGNALS_JSON__", signals_json)
    html = html.replace("__HISTORY_JSON__", history_json)
    html = html.replace("__OPPS_JSON__", opps_json)
    html = html.replace("__REPORT_MD__", report_md_json)
    return html


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KAKAOPC 情报科 — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
:root {
  --bg: #0d0f12;
  --bg-card: #14171c;
  --bg-elevated: #1a1d24;
  --border: #252830;
  --text: #d1d5db;
  --text-muted: #6b7280;
  --accent: #f59e42;
  --accent-dim: #b45309;
  --green: #34d399;
  --red: #f87171;
  --blue: #60a5fa;
  --radius: 8px;
  --font-mono: 'DM Mono', monospace;
  --font-sans: 'DM Sans', -apple-system, sans-serif;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:var(--font-sans); line-height:1.6; }
header { background:var(--bg-card); border-bottom:1px solid var(--border); padding:16px 24px; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:10; }
header h1 { font-size:18px; font-weight:600; }
header .date { color:var(--text-muted); font-size:13px; }
.badge { display:inline-block; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:500; }
.badge-green { background:rgba(52,211,153,0.15); color:var(--green); }
.badge-red { background:rgba(248,113,113,0.15); color:var(--red); }
.badge-accent { background:rgba(245,158,66,0.15); color:var(--accent); }
main { max-width:1280px; margin:0 auto; padding:24px; display:grid; grid-template-columns:1fr 1fr; grid-template-rows:auto auto auto auto; gap:20px; }
.card { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); padding:20px; }
.card h2 { font-size:15px; font-weight:600; margin-bottom:14px; color:var(--text); }
.card-full { grid-column:1/-1; }
.stat-row { display:flex; gap:16px; flex-wrap:wrap; }
.stat { background:var(--bg-elevated); border-radius:var(--radius); padding:14px 18px; flex:1; min-width:120px; }
.stat-value { font-family:var(--font-mono); font-size:28px; font-weight:500; color:var(--accent); }
.stat-label { font-size:12px; color:var(--text-muted); margin-top:2px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; padding:8px 10px; color:var(--text-muted); font-weight:500; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid var(--border); }
td { padding:8px 10px; border-bottom:1px solid var(--border); }
tr:hover td { background:var(--bg-elevated); }
.signal-link { color:var(--blue); text-decoration:none; }
.signal-link:hover { text-decoration:underline; }
.score { font-family:var(--font-mono); font-weight:500; }
.score-high { color:var(--accent); }
.score-mid { color:var(--blue); }
.score-low { color:var(--text-muted); }
.chart-wrap { height:280px; position:relative; }
.report-body { font-size:14px; line-height:1.7; max-height:70vh; overflow-y:auto; }
.report-body h1,.report-body h2,.report-body h3 { margin-top:16px; margin-bottom:8px; }
.report-body h1 { font-size:20px; }
.report-body h2 { font-size:16px; color:var(--accent); }
.report-body p { margin-bottom:10px; }
.report-body table { margin:12px 0; }
.report-body a { color:var(--blue); }
.report-body code { background:var(--bg-elevated); padding:2px 6px; border-radius:4px; font-family:var(--font-mono); font-size:13px; }
.report-body blockquote { border-left:3px solid var(--accent-dim); padding-left:14px; color:var(--text-muted); margin:12px 0; }
@media (max-width:900px) { main { grid-template-columns:1fr; } }
.tab-bar { display:flex; gap:4px; margin-bottom:16px; }
.tab { padding:6px 14px; border-radius:6px; cursor:pointer; font-size:13px; color:var(--text-muted); border:1px solid transparent; background:none; }
.tab.active { background:var(--bg-elevated); color:var(--text); border-color:var(--border); }
.track-status { font-size:12px; }
.track-status.pending { color:var(--text-muted); }
.track-status.passed { color:var(--green); }
.track-status.failed { color:var(--red); }
.empty { color:var(--text-muted); font-size:14px; text-align:center; padding:32px 0; }
.footer { grid-column:1/-1; text-align:center; color:var(--text-muted); font-size:12px; padding:8px; }
</style>
</head>
<body>

<header>
  <h1>KAKAOPC 情报科 Dashboard</h1>
  <span class="date">__DATE__</span>
</header>

<main>
  <div class="card card-full">
    <h2>今日概览</h2>
    <div class="stat-row">
      <div class="stat">
        <div class="stat-value">__SIGNAL_COUNT__</div>
        <div class="stat-label">处理信号</div>
      </div>
      <div class="stat">
        <div class="stat-value">__TOP_SCORE__</div>
        <div class="stat-label">最高分</div>
      </div>
      <div class="stat">
        <div class="stat-value">__AVG_SCORE__</div>
        <div class="stat-label">平均分</div>
      </div>
      <div class="stat">
        <div class="stat-value">__ACTION_COUNT__</div>
        <div class="stat-label">Action 触发</div>
      </div>
      <div class="stat">
        <div class="stat-value">__CROSS_PLATFORM__</div>
        <div class="stat-label">跨平台信号</div>
      </div>
    </div>
  </div>

  <div class="card card-full">
    <h2>Top 10 信号</h2>
    <table id="signals-table">
      <thead><tr><th>#</th><th>信号</th><th>来源</th><th>分数</th><th>跨平台</th><th>互动</th></tr></thead>
      <tbody id="signals-body"></tbody>
    </table>
  </div>

  <div class="card">
    <h2>14 天分数趋势</h2>
    <div class="chart-wrap"><canvas id="scoreChart"></canvas></div>
  </div>

  <div class="card">
    <h2>14 天信号量</h2>
    <div class="chart-wrap"><canvas id="volumeChart"></canvas></div>
  </div>

  <div class="card card-full">
    <div class="tab-bar">
      <button class="tab active" onclick="switchTab('report')">日报</button>
      <button class="tab" onclick="switchTab('tracking')">机会追踪</button>
    </div>
    <div id="tab-report" class="report-body"></div>
    <div id="tab-tracking" class="report-body" style="display:none;">
      <table><thead><tr><th>ID</th><th>日期</th><th>机会</th><th>分数</th><th>LP</th><th>验证</th><th>判决</th></tr></thead>
      <tbody id="tracking-body"></tbody></table>
      <div id="tracking-empty" class="empty" style="display:none;">暂无机会追踪记录</div>
    </div>
  </div>

  <div class="footer">KAKAOPC 情报科 v1.0 · __GENERATED_AT__ · 数据刷新: 每日 08:30 CST</div>
</main>

<script>
var signals = __SIGNALS_JSON__;
var history = __HISTORY_JSON__;
var opps = __OPPS_JSON__;
var reportMd = __REPORT_MD__;

(function() {
  var tbody = document.getElementById('signals-body');
  var top = signals.slice(0, 10);
  top.forEach(function(s, i) {
    var score = s.score || 0;
    var cls = score >= 20 ? 'score-high' : (score >= 10 ? 'score-mid' : 'score-low');
    var title = (s.title || 'N/A').substring(0, 80);
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + (i+1) + '</td>' +
      '<td><a class="signal-link" href="' + (s.url || '#') + '" target="_blank">' + title + '</a></td>' +
      '<td>' + (s.source || '?') + '</td>' +
      '<td class="score ' + cls + '">' + score + '</td>' +
      '<td>' + (s.cross_platform_count || 0) + '</td>' +
      '<td>' + (s.discussion_count || 0) + '</td>';
    tbody.appendChild(tr);
  });
})();

(function() {
  if (reportMd) {
    document.getElementById('tab-report').innerHTML = marked.parse(reportMd);
  } else {
    document.getElementById('tab-report').innerHTML = '<div class="empty">今日日报尚未生成</div>';
  }
})();

(function() {
  if (opps.length === 0) {
    document.getElementById('tracking-empty').style.display = 'block';
    return;
  }
  var statusLabels = {pending: '待验证', passed: '通过', failed: '失败', adjust: '需调整'};
  var tbody = document.getElementById('tracking-body');
  opps.forEach(function(op) {
    var statusCls = op.verification_result || 'pending';
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><code>' + op.id + '</code></td>' +
      '<td>' + op.date + '</td>' +
      '<td>' + (op.opportunity || '').substring(0, 40) + '</td>' +
      '<td class="score">' + (op.score || 0) + '</td>' +
      '<td><span class="badge ' + (op.lp_status === 'live' ? 'badge-green' : '') + '">' + (op.lp_status || 'not_built') + '</span></td>' +
      '<td class="track-status ' + statusCls + '">' + (statusLabels[statusCls] || statusCls) + '</td>' +
      '<td>' + (op.day7_decision || '--') + '</td>';
    tbody.appendChild(tr);
  });
})();

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
  event.target.classList.add('active');
  document.getElementById('tab-report').style.display = tab === 'report' ? '' : 'none';
  document.getElementById('tab-tracking').style.display = tab === 'tracking' ? '' : 'none';
}

(function() {
  var ctx = document.getElementById('scoreChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: history.map(function(d) { return d.date.substring(5); }),
      datasets: [
        { label: '最高分', data: history.map(function(d) { return d.top_score; }), borderColor: '#f59e42', backgroundColor: 'transparent', tension: 0.3, pointRadius: 3 },
        { label: '平均分', data: history.map(function(d) { return d.avg_score; }), borderColor: '#60a5fa', backgroundColor: 'transparent', tension: 0.3, pointRadius: 3, borderDash: [4,4] }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#6b7280', font: { size:11 } } } },
      scales: {
        x: { ticks: { color: '#6b7280', font: { size:10 } }, grid: { color: '#252830' } },
        y: { ticks: { color: '#6b7280', font: { size:10 } }, grid: { color: '#252830' }, beginAtZero: true }
      }
    }
  });
})();

(function() {
  var ctx = document.getElementById('volumeChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: history.map(function(d) { return d.date.substring(5); }),
      datasets: [
        { label: '信号量', data: history.map(function(d) { return d.total_signals; }), backgroundColor: '#f59e4240', borderColor: '#f59e42', borderWidth: 1 },
        { label: '跨平台', data: history.map(function(d) { return d.cross_platform; }), backgroundColor: '#34d39940', borderColor: '#34d399', borderWidth: 1 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#6b7280', font: { size:11 } } } },
      scales: {
        x: { ticks: { color: '#6b7280', font: { size:10 } }, grid: { color: '#252830' } },
        y: { ticks: { color: '#6b7280', font: { size:10 } }, grid: { color: '#252830' }, beginAtZero: true }
      }
    }
  });
})();
</script>
</body>
</html>"""


def run(date_str: str | None = None) -> str:
    """生成 dashboard HTML。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[Dashboard] Dashboard 生成 — {date}")
    print(f"{'='*50}")

    data = collect_dashboard_data()
    html = generate_html(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"[Dashboard] Dashboard 已保存 → {output_path}")
    print(f"[Dashboard] 大小: {len(html):,} 字符 | 日期: {data['date']}")
    return str(output_path)


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        print(f"\n打开 Dashboard: {result}")
