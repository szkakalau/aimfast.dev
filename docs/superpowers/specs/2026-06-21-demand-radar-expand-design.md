# 需求雷达表内展开 — 设计文档

**Date**: 2026-06-21
**Status**: Approved
**Scope**: `public/dashboard/index.html`

---

## 1. 背景与动机

当前需求雷达（Demand Radar）在 dashboard 中以表格形式展示 5 个大方向（省钱、省时、赚钱、降风险、提产出）。每个方向带有 Market / Business / Competition / AI-pf / Confidence / Stage / Score 等聚合指标，但无法查看评分背后的细分维度（趋势子方向、Market 三子分、Business 四子分）。

用户希望在点击大方向行后，原地展开查看详细信息。

## 2. 目标

- 点击大方向行 → 行下方展开详情面板（toggle 行为）
- 支持多行同时展开（方便对比）
- 详情区包含：5 个趋势标签 + Market/Business 子分拆解 + 关键指标说明
- 改动仅限 `public/dashboard/index.html`，不改数据流、不改其他 tab

## 3. 交互设计

### 3.1 Toggle 展开/收起

- 可展开的行左侧显示 caret 箭头：收起 `▸`，展开 `▾`
- 点击行任意位置（除 watch 按钮外）触发 toggle
- 允许多行同时处于展开状态
- 过渡动画：`duration-200 ease-out`（遵循 Material Design 自然过渡原则）

### 3.2 视觉层级

- 展开态行：左侧边框高亮 accent 色
- 详情行：浅暗背景（`var(--color-surface-alt)`），与数据行区分
- 入场动画：max-height + opacity 过渡

## 4. 布局设计

详情行使用 `colspan="10"` 横跨表格全宽，内部采用左右两栏 grid 布局：

```
┌─ 详情行 ─────────────────────────────────────────────────────┐
│                                                               │
│  📊 细分趋势                     📈 评分拆解                    │
│  ┌─────────────────────────┐   ┌───────────────────────────┐ │
│  │ [Cost Control]          │   │ Market  28   ████░░░░    │ │
│  │ [Token Optimization]    │   │  Trend    1   █░░░░░░░   │ │
│  │ [Model Routing]         │   │  Growth   5   █████░░░   │ │
│  │ [Prompt Compression]    │   │  Consist  5   █████░░░   │ │
│  │ [Local Model Hybrid]    │   │                           │ │
│  │                         │   │ Business 95  ████████    │ │
│  │ 目标用户：               │   │  Pain f10×s10 = 10.0    │ │
│  │ Claude Code 重度用户     │   │  Pay  b10×u9  = 9.0     │ │
│  │                         │   │                           │ │
│  │                         │   │ AI替代难度 2/10 · 竞争 20 │ │
│  │                         │   │ 置信度 56% · Stage forming│ │
│  └─────────────────────────┘   └───────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 左栏 — 细分趋势 (50%)

- 所有 5 个 trend 以 `.trend-tag` 标签展示（复用现有样式）
- 标签下方显示 `target_buyer`（小字 muted）
- 如果该 demand 有关联的 recurring_signals 或有 intersection 标注，在此显示

### 右栏 — 评分拆解 (50%)

- **Market 总分** + 进度条 → 下面列出三个子分（trend_score, growth_score, consistency_score），各带自身进度条
- **Business 总分** + 进度条 → 下面列出 pain_score (freq × severity / 10) 和 pay_score (budget × urgency / 10)，附原始参数
- 底部一行：AI Replaceability、Competition、Confidence、Stage 的简洁标签

### 进度条设计

- 容器：`height: 6px; border-radius: 3px; background: var(--color-surface)`
- 填充：`background: var(--color-accent)`，宽度百分比
- 低分（<30%）：`var(--color-text-muted)`
- 高分（≥70%）：`var(--color-green)`
- 右侧标注数值

## 5. 实现方案

### 5.1 CSS 新增（约 50 行）

```css
/* 可展开行 */
.demand-row { cursor: pointer; transition: background var(--duration-fast) var(--ease-out); }
.demand-row:hover td { background: var(--color-surface-alt); }
.demand-row.expanded td { border-left: 3px solid var(--color-accent); }

/* Caret */
.expand-caret { display: inline-block; width: 12px; font-size: 0.7rem; color: var(--color-text-muted); transition: transform var(--duration-fast) var(--ease-out); }
.expanded .expand-caret { transform: rotate(90deg); }

/* 详情行 */
.demand-detail td { padding: 0; background: var(--color-surface-alt); border-bottom: 1px solid var(--color-border); }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); padding: var(--space-3); }
.detail-section h4 { font-size: 0.75rem; font-weight: 600; margin-bottom: var(--space-2); text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-text-muted); }

/* 进度条 */
.score-bar-wrap { height: 6px; border-radius: 3px; background: var(--color-surface); margin: 2px 0 6px; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 3px; background: var(--color-accent); transition: width var(--duration-slow) var(--ease-out); }
.score-bar-fill.low { background: var(--color-text-muted); }
.score-bar-fill.high { background: var(--color-green); }

/* 子分项 */
.sub-score-row { display: flex; align-items: center; gap: var(--space-1); font-size: 0.72rem; margin-bottom: 2px; }
.sub-score-label { width: 70px; color: var(--color-text-muted); flex-shrink: 0; }
.sub-score-val { font-family: var(--font-mono); width: 28px; text-align: right; }
.sub-score-bar { flex: 1; }

/* 参数说明 */
.formula-text { font-size: 0.65rem; color: var(--color-text-muted); font-family: var(--font-mono); }
```

### 5.2 JS 新增（约 40 行）

**修改 `demands.forEach` 循环（行 1854-1889）：**

1. 给 `tr` 添加 `class="demand-row"` 和 `onclick` handler
2. 在第一列前插入 caret 指示器
3. 为每行生成唯一 `data-demand-id` 属性

**新增 `toggleDemandDetail(demId)` 函数：**

```js
function toggleDemandDetail(demId) {
  var row = document.querySelector('[data-demand-id="' + demId + '"]');
  var detailRow = document.getElementById('demand-detail-' + demId);
  
  if (detailRow) {
    // 收起
    detailRow.remove();
    row.classList.remove('expanded');
  } else {
    // 展开
    var dem = demands.find(function(d) { return d.id === demId; });
    detailRow = document.createElement('tr');
    detailRow.className = 'demand-detail';
    detailRow.id = 'demand-detail-' + demId;
    detailRow.innerHTML = renderDemandDetail(dem);
    row.parentNode.insertBefore(detailRow, row.nextSibling);
    row.classList.add('expanded');
  }
}
```

**新增 `renderDemandDetail(dem)` 函数：**

```js
function renderDemandDetail(dem) {
  var trendTags = (dem.trends || []).map(function(t) {
    return '<span class="trend-tag">' + t + '</span>';
  }).join('');
  
  var buyerText = (LANG === 'en' && dem.target_buyer_en) ? dem.target_buyer_en : (dem.target_buyer || '');
  
  return '<td colspan="10">' +
    '<div class="detail-grid">' +
    // 左栏：趋势
    '<div class="detail-section">' +
      '<h4>' + t('detailTrends') + '</h4>' +
      '<div class="trend-tags">' + trendTags + '</div>' +
      (buyerText ? '<div class="muted" style="margin-top:8px;font-size:0.72rem;">' + t('detailTargetBuyer') + ': ' + buyerText + '</div>' : '') +
    '</div>' +
    // 右栏：评分
    '<div class="detail-section">' +
      '<h4>' + t('detailBreakdown') + '</h4>' +
      renderScoreBar('Market', dem.market_score || 0) +
      renderSubScore('Trend', dem.trend_score || 0, 10) +
      renderSubScore('Growth', dem.growth_score || 0, 10) +
      renderSubScore('Consistency', dem.consistency_score || 0, 10) +
      '<div style="margin-top:8px;"></div>' +
      renderScoreBar('Business', dem.business_score || 0) +
      '<div class="formula-text">Pain: f' + (dem.pain_frequency||'?') + '×s' + (dem.pain_severity||'?') + ' = ' + ((dem.pain_score||0).toFixed(1)) + ' | Pay: b' + (dem.pay_budget||'?') + '×u' + (dem.pay_urgency||'?') + ' = ' + ((dem.pay_score||0).toFixed(1)) + '</div>' +
      '<div style="margin-top:8px;display:flex;gap:12px;flex-wrap:wrap;font-size:0.72rem;">' +
        '<span>AI替代难度: <strong>' + (dem.ai_replaceability||'?') + '/10</strong></span>' +
        '<span>竞争: <strong>' + (dem.competition||0) + '</strong></span>' +
        '<span>置信度: <strong>' + (dem.confidence||0) + '%</strong></span>' +
        '<span>Stage: <strong>' + (stageLabels[dem.stage] || dem.stage) + '</strong></span>' +
      '</div>' +
    '</div>' +
    '</div>' +
    '</td>';
}
```

辅助函数：
```js
function renderScoreBar(label, value) {
  var cls = value >= 70 ? 'high' : (value < 30 ? 'low' : '');
  return '<div class="sub-score-row">' +
    '<span class="sub-score-label">' + label + '</span>' +
    '<span class="sub-score-bar"><div class="score-bar-wrap"><div class="score-bar-fill ' + cls + '" style="width:' + value + '%"></div></div></span>' +
    '<span class="sub-score-val">' + value + '</span>' +
    '</div>';
}

function renderSubScore(label, value, max) {
  var pct = Math.round((value / max) * 100);
  var cls = pct >= 70 ? 'high' : (pct < 30 ? 'low' : '');
  return '<div class="sub-score-row" style="padding-left:16px;">' +
    '<span class="sub-score-label" style="font-size:0.68rem;width:60px;">↳ ' + label + '</span>' +
    '<span class="sub-score-bar"><div class="score-bar-wrap"><div class="score-bar-fill ' + cls + '" style="width:' + pct + '%"></div></div></span>' +
    '<span class="sub-score-val">' + value + '/' + max + '</span>' +
    '</div>';
}
```

### 5.3 国际化（i18n 字典新增约 5 条）

在 `i18n` 对象中新增：
```js
detailTrends: { zh: '细分趋势', en: 'Sub Trends' },
detailBreakdown: { zh: '评分拆解', en: 'Score Breakdown' },
detailTargetBuyer: { zh: '目标用户', en: 'Target Buyer' },
```

## 6. 不改动范围

- 不修改 `scripts/track_demands.py`
- 不修改 `scripts/generate_dashboard.py`
- 不修改 `config/demand_patterns.json`
- 不修改 `tracking/*.json` 数据结构
- 不修改 Workbench mini-radar 的行为
- 不影响其他 tab（tracking, recurring, report, article）
- 不影响 watch 按钮功能

## 7. 验证标准

1. 点击任意 demand 行，详情行出现在下方
2. 再次点击同一行，详情行消失
3. 可同时展开 2+ 行，互不干扰
4. Watch 按钮点击不会触发展开/收起
5. 切换 tab 后回到 demand tab，展开状态重置（表被重新渲染）
6. 移动端（≤768px）详情 grid 改为单列布局
7. 中英文切换后，详情行文字跟随语言变化（重新渲染）
