# 需求雷达表内展开 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 demand radar 表格中实现点击行展开/收起详情面板（趋势标签 + 评分拆解进度条）

**Architecture:** 纯前端改动，在现有 `public/dashboard/index.html` 单文件中新增 CSS (~55行)、JS 辅助函数 (~55行)、i18n 条目 (3条)。不涉及任何后端或数据流变更。

**Tech Stack:** Vanilla JS + CSS（无框架），Chart.js（已有但不受影响）

## Global Constraints

- 仅修改 `public/dashboard/index.html`
- 不修改任何 `scripts/*.py`、`config/*.json`、`tracking/*.json`
- 不影响 Workbench mini-radar、其他 tab、watch 按钮功能
- 过渡动画使用 `var(--duration-fast) var(--ease-out)` (<200ms)
- 复用现有 design tokens: `--color-accent`, `--color-green`, `--color-surface-alt`, `--color-border`, `--color-text-muted`, `--font-mono`, `--radius-md`, `--space-1/2/3`
- 移动端 `@media (max-width: 768px)` 详情 grid 改为单列
- 中英文双语支持（i18n 字典形式）

## File Structure

```
public/dashboard/index.html  (single file, 2477 lines)
├── <style>  (~610 lines, lines 25-635)
│   ├── [existing table/score styles ~lines 137-175, 440-457]
│   └── [+ new CSS ~55 lines, insert after .btn-watch block at line 481]
├── I18N dict  (~360 lines, lines 821-1181)
│   ├── dict.zh  (lines 829-998)
│   │   └── [+ 3 keys, insert after demIntersections at line 957]
│   └── dict.en  (lines 1000-1181)
│       └── [+ 3 keys, insert after en demIntersections]
├── <script>  (~1300 lines, lines 1184-2474)
│   ├── [existing demand rendering: demands.forEach lines 1854-1889]
│   └── [+ new JS ~55 lines, insert before demand rendering at line 1853]
└── </html>
```

## Verification

由于是纯前端项目（无测试框架），每步完成后刷新浏览器即可验证：
1. 打开 `public/dashboard/index.html`（通过 local server 访问）
2. 切换到 **Demand Radar** tab
3. 点击任意需求行 → 详情行应出现
4. 再次点击 → 详情行应消失
5. 可同时展开多行
6. Watch 按钮不受影响
7. 缩小窗口到 ≤768px 检查移动端单列布局

---

### Task 1: 添加 i18n 国际化条目

**Files:**
- Modify: `public/dashboard/index.html`

**说明:** 在 `dict.zh` 和 `dict.en` 中各添加 3 个新 key，放在 `demIntersections` 之后。

- [ ] **Step 1: 在 `dict.zh` 中 `demIntersections` 之后插入**

`dict.zh` 中当前（约 line 957）:
```js
      demIntersections: '交叉机会',
```

在其后添加（注意逗号）:
```js
      demIntersections: '交叉机会',

      // Demand detail expand
      detailTrends: '细分趋势',
      detailBreakdown: '评分拆解',
      detailTargetBuyer: '目标用户',
      detailAiReplace: 'AI替代难度',
      detailCompetition: '竞争',
      detailConfidence: '置信度',
      detailStage: '阶段',
```

- [ ] **Step 2: 在 `dict.en` 中 `demIntersections` 之后插入**

在 `dict.en` 中对应位置（约 line 1140+）找到:
```js
      demIntersections: 'Cross Opportunities',
```

在其后添加:
```js
      demIntersections: 'Cross Opportunities',

      // Demand detail expand
      detailTrends: 'Sub Trends',
      detailBreakdown: 'Score Breakdown',
      detailTargetBuyer: 'Target Buyer',
      detailAiReplace: 'AI Durability',
      detailCompetition: 'Competition',
      detailConfidence: 'Confidence',
      detailStage: 'Stage',
```

---

### Task 2: 添加 CSS 样式

**Files:**
- Modify: `public/dashboard/index.html`

**说明:** 在 `</style>` 之前（约 line 634），添加详情面板、进度条、展开行的全部 CSS。

- [ ] **Step 3: 插入 CSS**

在 `.wb-opp-close:hover { color: var(--color-text); }` 之后、`@media (max-width: 900px)` 之前（约 line 462 之后）插入:

```css
  /* ── Demand detail expand ── */
  .demand-row { cursor: pointer; }
  .demand-row:hover td { background: var(--color-surface-alt); }
  .demand-row .expand-caret {
    display: inline-block;
    width: 14px;
    font-size: 0.65rem;
    color: var(--color-text-muted);
    transition: transform var(--duration-fast) var(--ease-out);
    text-align: center;
  }
  .demand-row.expanded .expand-caret { transform: rotate(90deg); }

  .demand-detail td {
    padding: 0;
    background: var(--color-surface-alt);
    border-bottom: 2px solid var(--color-accent);
  }
  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
    padding: var(--space-3);
    animation: detailIn var(--duration-fast) var(--ease-out);
  }
  @keyframes detailIn {
    from { opacity: 0; transform: translateY(-6px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .detail-section h4 {
    font-size: 0.7rem;
    font-weight: 600;
    margin: 0 0 var(--space-2) 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
  }

  /* Score bars */
  .score-bar-wrap {
    height: 6px;
    border-radius: 3px;
    background: var(--color-surface);
    overflow: hidden;
    flex: 1;
  }
  .score-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: var(--color-accent);
    transition: width var(--duration-slow) var(--ease-out);
  }
  .score-bar-fill.low  { background: var(--color-text-muted); }
  .score-bar-fill.high { background: var(--color-green); }

  .sub-score-row {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-size: 0.72rem;
    margin-bottom: 2px;
  }
  .sub-score-label {
    width: 80px;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }
  .sub-score-val {
    font-family: var(--font-mono);
    width: 36px;
    text-align: right;
    font-size: 0.7rem;
  }

  .formula-text {
    font-size: 0.62rem;
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    margin-top: 2px;
    padding-left: 4px;
  }

  .meta-row {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    font-size: 0.7rem;
    color: var(--color-text-muted);
    margin-top: var(--space-2);
  }
  .meta-row strong {
    color: var(--color-text);
    font-weight: 600;
  }
```

---

### Task 3: 添加 JS 辅助函数

**Files:**
- Modify: `public/dashboard/index.html`

**说明:** 在 demand rendering 部分的 `var demTbody = document.getElementById('demand-body');` 之前（约 line 1853），插入 4 个新函数。

- [ ] **Step 4: 插入 4 个辅助函数**

在当前 `var demTbody = document.getElementById('demand-body');`（约 line 1853）**之前**插入:

```js
  // ── Demand detail expand helpers ──
  function renderScoreBar(label, value) {
    var cls = value >= 70 ? 'high' : (value < 30 ? 'low' : '');
    return '<div class="sub-score-row">' +
      '<span class="sub-score-label">' + label + '</span>' +
      '<div class="score-bar-wrap"><div class="score-bar-fill ' + cls + '" style="width:' + value + '%"></div></div>' +
      '<span class="sub-score-val">' + value + '</span>' +
      '</div>';
  }

  function renderSubScore(label, value, max) {
    var pct = Math.round((value / max) * 100);
    var cls = pct >= 70 ? 'high' : (pct < 30 ? 'low' : '');
    return '<div class="sub-score-row" style="padding-left:20px;">' +
      '<span class="sub-score-label" style="font-size:0.65rem;width:70px;">↳ ' + label + '</span>' +
      '<div class="score-bar-wrap"><div class="score-bar-fill ' + cls + '" style="width:' + pct + '%"></div></div>' +
      '<span class="sub-score-val">' + value + '/' + max + '</span>' +
      '</div>';
  }

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
        (buyerText ? '<div style="margin-top:10px;font-size:0.7rem;color:var(--color-text-muted);">' + t('detailTargetBuyer') + ': <strong style="color:var(--color-text);">' + buyerText + '</strong></div>' : '') +
        '<div style="margin-top:8px;font-size:0.62rem;color:var(--color-text-muted);">Total signals: <strong>' + (dem.total_appearances||0) + '</strong> over <strong>' + (dem.distinct_days||0) + '</strong> days</div>' +
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
        '<div class="formula-text">Pain f' + (dem.pain_frequency||'?') + '×s' + (dem.pain_severity||'?') + ' = ' + ((dem.pain_score||0).toFixed(1)) + ' | Pay b' + (dem.pay_budget||'?') + '×u' + (dem.pay_urgency||'?') + ' = ' + ((dem.pay_score||0).toFixed(1)) + '</div>' +
        '<div class="meta-row">' +
          '<span>' + t('detailAiReplace') + ': <strong>' + (dem.ai_replaceability||'?') + '/10</strong></span>' +
          '<span>' + t('detailCompetition') + ': <strong>' + (dem.competition||0) + '</strong></span>' +
          '<span>' + t('detailConfidence') + ': <strong>' + (dem.confidence||0) + '%</strong></span>' +
          '<span>' + t('detailStage') + ': <strong>' + (stageLabels[dem.stage] || dem.stage || '?') + '</strong></span>' +
        '</div>' +
      '</div>' +
      '</div>' +
      '</td>';
  }

  function toggleDemandDetail(demId) {
    var row = document.querySelector('[data-demand-id="' + demId + '"]');
    if (!row) return;
    var detailRow = document.getElementById('demand-detail-' + demId);

    if (detailRow) {
      // Collapse
      detailRow.remove();
      row.classList.remove('expanded');
    } else {
      // Expand
      var dem = demands.find(function(d) { return d.id === demId; });
      if (!dem) return;
      detailRow = document.createElement('tr');
      detailRow.className = 'demand-detail';
      detailRow.id = 'demand-detail-' + demId;
      detailRow.innerHTML = renderDemandDetail(dem);
      row.parentNode.insertBefore(detailRow, row.nextSibling);
      row.classList.add('expanded');
    }
  }
```

---

### Task 4: 修改需求行渲染逻辑

**Files:**
- Modify: `public/dashboard/index.html`

**说明:** 修改 `demands.forEach` 循环中的行渲染（约 lines 1854-1889），给 `tr` 添加 class、data 属性和 onclick handler，并在名称列前插入 caret 箭头。

- [ ] **Step 5: 修改 `demands.forEach` 中的行渲染**

当前代码（约 line 1854）:
```js
    demands.forEach(function(dem) {
      var tr = document.createElement('tr');
```

修改为:
```js
    demands.forEach(function(dem) {
      var tr = document.createElement('tr');
      tr.className = 'demand-row';
      tr.setAttribute('data-demand-id', dem.id);
      tr.onclick = function(e) {
        // Don't toggle if watch button was clicked
        if (e.target.closest('.btn-watch')) return;
        toggleDemandDetail(dem.id);
      };
```

当前 `tr.innerHTML` 中名称列（约 line 1880）:
```js
        '<td><strong>' + dmName + '</strong><br><span class="muted">' + descText + buyerInfo + '</span>' + trendsHtml + '</td>' +
```

修改为（在 `<strong>` 前加 caret）:
```js
        '<td><span class="expand-caret">▸</span><strong>' + dmName + '</strong><br><span class="muted">' + descText + buyerInfo + '</span>' + trendsHtml + '</td>' +
```

---

### Task 5: 添加移动端响应式 CSS

**Files:**
- Modify: `public/dashboard/index.html`

**说明:** 在 `@media (max-width: 768px)` 块中（约 line 623，在 `#tab-demand th, #tab-demand td { padding: 3px 4px; }` 之后）添加详情 grid 单列布局规则。

- [ ] **Step 6: 添加移动端 CSS 规则**

在 `#tab-demand th, #tab-demand td { padding: 3px 4px; }`（约 line 624）之后插入:
```css
    .detail-grid { grid-template-columns: 1fr; gap: var(--space-2); padding: var(--space-2); }
    .meta-row { gap: 8px; }
```

---

### Task 6: 浏览器验证 + 提交

- [ ] **Step 7: 浏览器验证**

打开 dashboard HTML 页面，切换到 Demand Radar tab，验证以下场景:

1. 点击任意 demand 行 → 详情行展开（caret 旋转 90°、进度条动画、趋势标签显示）
2. 再次点击同一行 → 详情行收起
3. 同时展开 2+ 行 → 各行独立工作
4. 点击 watch ☆ 按钮 → 不触发展开/收起
5. 切换到其他 tab 再回到 Demand Radar → 展开状态重置（正常行为，因为 switchTab 会重新渲染）
6. 缩窄浏览器窗口到 ≤768px → 详情 grid 变为单列
7. 切换语言 EN/中文 → 详情行文字跟随变化

- [ ] **Step 8: 提交**

```bash
git add public/dashboard/index.html
git commit -m "feat: demand radar 表格行内展开 — 趋势标签 + 评分拆解进度条

点击需求方向行原位展开详情面板（趋势标签、Market/Business 子分进度条、关键指标）。
支持多行同时展开，带 caret 箭头指示和入场动画，移动端适配单列布局。

Co-Authored-By: Claude <noreply@anthropic.com>"
```
