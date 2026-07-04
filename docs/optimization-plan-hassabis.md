# 系统优化计划：从哈萨比斯四思维出发

> 基于 2026-06-28 系统审计，将四个思维框架翻译为具体、可执行的工程优化。
> 原则：每个优化必须有可验证的成功标准，不做"理念升级"式的空改动。

---

## 总览

| # | 优化项 | 来源思维 | 优先级 | 预计工作量 | 风险 |
|---|--------|---------|--------|-----------|------|
| 1 | 信号源 ROI 审计 + 精简 | 纯粹专注 | ⭐⭐⭐⭐ | 1 天 | 低 |
| 2 | 新增 `problem_clarity` 评分维度 | 先理解问题 | ⭐⭐⭐ | 2 天 | 中（需调权重） |
| 3 | 跨域痛点模式检测 | 跨学科理解 | ⭐⭐⭐ | 3 天 | 中（复杂度高） |
| 4 | Prediction → 回溯 → 校准闭环 | 信念驱动 | ⭐⭐ | 2 天 | 低 |

---

## 优化 1：信号源 ROI 审计 + 精简

**对应思维**：纯粹专注——"保护深度思考的时间，砍掉噪音比增加功能更重要"

### 当前问题

系统每天从 15 个启用的采集器（含 C-end）拉数据，但从未评估过每个源的实际贡献。类比哈萨比斯把 DeepMind 放在伦敦而非硅谷——不是信息越多越好，是信号/噪音比越高越好。

### 具体方案

#### 1.1 新建审计脚本 `scripts/audit_sources.py`

```
输入: daily/*/signals.json（过去 30 天）
输出: tracking/source_audit.json

统计指标（每个 source_key）:
  - total_signals: 总采集量
  - top10_appearances: 进入当日 Top 10 的次数
  - top10_contribution_rate: top10_appearances / total_signals
  - action_triggered: 触发 Action Plan 的次数
  - avg_score: 该源信号的平均分
  - cross_platform_boost: 该源信号作为跨平台验证的次数（被其他源也覆盖到）
  - unique_insight_rate: 该源独有（未被其他源覆盖）且进入 Top 10 的信号数
  - roi_score: 综合评分 = top10_contribution_rate × 0.4 + action_triggered × 0.3 + unique_insight_rate × 0.2 + cross_platform_boost × 0.1
```

#### 1.2 决策规则

```
roi_score >= 0.5  → 保留，P0
roi_score 0.2-0.5 → 保留，降级为 P2（每周跑一次而非每天）
roi_score < 0.2   → 建议砍掉
```

#### 1.3 省下的预算重分配

砍掉的源每天节省的 API 调用和 LLM token，重新分配到：
- `generate_report.py` 的 top 3 信号深度分析（增加 prompt 长度和推理深度）
- `enrich_signals.py` 的 max_signals 从 2 提升到 3

### 验证标准

- [ ] `source_audit.json` 产出，包含所有源的 ROI 评分
- [ ] 至少识别出 2-3 个低 ROI 源
- [ ] 砍掉后系统仍能产出 ≥ 当前质量 的 Top 10 推荐
- [ ] 深度分析报告的字数和洞察密度有可测量的提升

---

## 优化 2：新增 `problem_clarity` 评分维度

**对应思维**：先理解问题——"在动手解决之前，先问这个问题值不值得解决"

### 当前问题

现有 E-P-A 公式（`cross_platform×3 + volume×2 + freshness×2 + actionability×2 + buyer_clarity×1 + consumer_appeal×2`）能识别"热不热"和"能不能做"，但无法区分：

- **真痛点**："我的 SaaS 每月在 AWS 上烧 $2000，找不到便宜的替代品" → 有人正在痛苦，有付费意愿
- **假热度**："又一个用 Rust 重写的 JavaScript 工具链" → 开发者觉得酷，但没人会付钱

`lessons.json` 中的 6 条失败记录全是"信号强度不足以支撑产品机会"——说明现有公式的 **false positive 率太高**。

### 具体方案

#### 2.1 新增 `problem_clarity` 维度

在 `score_epa()` 中增加第 7 个评分维度：

```python
# 痛点信号关键词（强信号：有人在承受痛苦）
pain_signal_patterns = [
    # 付费痛苦
    "paying.*for.*but", "tired of paying", "too expensive", "overpriced",
    "waste of money", "costs.*too much", "alternatives to",
    "cancel.*subscription", "switching from",
    # 功能痛苦
    "missing feature", "wish.*could", "if only", "why doesn't",
    "still can't", "waiting for", "no way to",
    # 流程痛苦
    "spend.*hours", "takes forever", "manual.*process", "every time I",
    "frustrated with", "hate.*when", "pain point",
    # 中文
    "太贵了", "受不了", "每次都要", "找不到", "忍了很久",
    "有没有.*替代", "付费.*但是", "浪费.*时间", "坑爹",
]

# 伪热度信号关键词（弱信号：看起来酷但没人会付钱）
hype_signal_patterns = [
    "built with rust", "rewrite in", "yet another", "show hn",
    "just launched", "my first", "weekend project", "side project",
    "benchmark", "faster than", "zero dependency",
    "built with", "made with", "用.*构建", "开源.*替代",
]
```

**评分规则**（0-5 分）：

| 条件 | 分数 |
|------|------|
| pain_signal ≥ 3 且 hype_signal = 0 | 5（清晰痛点） |
| pain_signal ≥ 2 且 pain_signal > hype_signal | 4 |
| pain_signal ≥ 1 且 hype_signal = 0 | 3（可能是痛点） |
| pain_signal ≥ 1 且 hype_signal ≥ 1 | 2（混合信号） |
| pain_signal = 0 且 hype_signal ≥ 2 | 1（大概率伪热度） |
| 都不匹配 | 2（中性） |

#### 2.2 更新评分公式

```
旧: Score = cp×3 + vol×2 + fresh×2 + act×2 + buyer×1 + consumer×2
新: Score = cp×3 + vol×2 + fresh×2 + act×2 + buyer×1 + consumer×2 + problem_clarity×2
```

总权重从 12 变为 14。`action_trigger` 阈值从 15 调整为 17（按比例）。

#### 2.3 向后兼容

- `config.json` 的 `scoring.weights` 增加 `problem_clarity: 2`
- `scoring.rubrics` 增加 `problem_clarity` 段
- `scoring.formula` 字符串更新
- 旧版 `signals.json` 不受影响（缺少 `problem_clarity` 字段时显示为 0）

### 验证标准

- [ ] 用过去 7 天的数据重跑，Top 10 中"真痛点"信号的排名上升
- [ ] `lessons.json` 中已有的 6 条失败案例（score 28-34, cross_platform=1），在新公式下得分明显降低
- [ ] 至少 1 个原有高分但可能是伪热度的信号被降权

---

## 优化 3：跨域痛点模式检测

**对应思维**：跨学科理解——"多个维度的输入交叉验证，才能逼近真相"

### 当前问题

现有聚类基于 Jaccard keyword similarity——这只能发现"大家在讨论同一个东西"。但真正有价值的信号是：

> "GitHub 上某个 Rust 库在涨" + "Reddit 上非技术用户抱怨某个问题" + "Google Trends 上相关搜索上升" → **同一个用户痛点**被三个不同类型的社区独立验证

这三种信号在你的系统里分属不同 source_key，keyword overlap 几乎为零——**它们永远不会被聚到一起**。

### 具体方案

#### 3.1 新增跨域检测模块

在 `process_signals.py` 的 `cluster()` 之后、`score_epa()` 之前，插入 `detect_cross_domain_patterns()`：

```
输入: 已聚类的信号列表
逻辑:
  1. 将信号按源类型分为三类:
     - tech_sources: github, hn, lobsters, devcommunity, arxiv
     - consumer_sources: reddit_consumer, producthunt, douban, xiaohongshu
     - search_sources: trends (Google Trends)
  
  2. 对每个信号，用 LLM 提取其核心"用户痛点"（不是关键词，是一个自然语言描述）:
     - 缓存到当日 signals.json 的 pain_point 字段
     - 只在 top 20 信号上做（控制成本）
  
  3. 对 top 20 信号两两比较 pain_point 的语义相似度（用 DeepSeek embedding 或简单的 LLM 判断）:
     - 如果两个信号 pain_point 相似度 > 0.7 且来自不同类型源 → 标记为"跨域验证"
     - 跨域验证的信号在 cross_platform 维度额外 +1（相当于被另一个"域"验证了）
```

#### 3.2 成本控制

- 只在 score ≥ 15（当前 action threshold）的信号上做 LLM 提取
- 每天最多 10 次 LLM 调用（top 10 信号各一次提取 pain_point）
- 如果审计后砍掉了 3 个源，省下的 token 预算正好覆盖这个开销

#### 3.3 数据结构

在 `signals.json` 每个信号的输出中增加：

```json
{
  "pain_point": "用户在多个平台上抱怨现有的 PDF 编辑工具太贵且功能臃肿",
  "cross_domain_validated": true,
  "cross_domain_sources": ["reddit_consumer", "github"]
}
```

### 验证标准

- [ ] 每天至少检测到 1-2 个跨域验证信号
- [ ] 跨域验证的信号在后续 7 天的 Demand Radar 中显示出持续热度
- [ ] 不增加超过 15% 的 LLM token 消耗

---

## 优化 4：Prediction → 回溯 → 校准闭环

**对应思维**：信念驱动——"系统需要从自己的错误中学习，就像哈萨比斯换掉认为'60 分就够了'的团队负责人"

### 当前问题

系统每天给出 top 推荐，但从不回溯验证这些推荐是否准确。`lessons.json` 有 6 条记录，但全是手动添加的，且没有反馈到评分公式。这等于一个从不校准的测量仪器。

### 具体方案

#### 4.1 新建 `scripts/calibrate_scoring.py`

```
运行频率: 每周日（在 weekly report 之后）

逻辑:
  1. 加载过去 7 天的 signals.json
  2. 对每个触发了 action plan 的信号:
     - 7 天后检查: 该信号对应的 landing page UV 是多少?
     - UV ≥ 30 → 标记为 "validated"
     - UV = 0 → 标记为 "false_positive"
     - UV 1-29 → 标记为 "uncertain"
  
  3. 统计:
     - precision = validated / (validated + false_positive)
     - 如果 precision < 0.5 → 提高 action_trigger 阈值 +2
     - 如果 precision > 0.8 且 action_trigger > 10 → 降低阈值 -1
  
  4. 按维度分析:
     - false_positive 信号在哪个维度得分异常高?
     - 如果某维度在 false_positive 中 consistently 高分 → 降低该维度权重 0.5
  
  5. 输出 calibration_report.json
```

#### 4.2 自动调权规则（保守策略）

```
单次调整幅度上限:
  - action_trigger: ±2
  - 任意维度 weight: ±0.5

调整需要连续 2 周同方向才生效（防止单周噪音）
```

#### 4.3 新增 `tracking/predictions.json`

```json
{
  "_schema": "预测日志 — 系统每日 top 推荐的追踪记录",
  "predictions": [
    {
      "date": "2026-06-28",
      "signal_id": "xxx",
      "title": "...",
      "score": 32,
      "action_triggered": true,
      "landing_page_url": "https://www.aimfast.dev/xxx/",
      "7day_uv": null,
      "7day_signups": null,
      "status": "pending"
    }
  ]
}
```

### 验证标准

- [ ] `calibrate_scoring.py` 首次运行产出完整的校准报告
- [ ] 4 周内，action plan 的 false positive 率有下降趋势
- [ ] 至少 1 次自动权重调整被记录（证明闭环在工作）

---

## 执行顺序

```
Week 1: 优化 1（审计脚本）→ 拿到数据，决定砍哪些源
Week 2: 优化 2（problem_clarity）→ 改善 false positive
Week 3: 优化 3（跨域检测）→ 用省下的 token 预算做更聪明的聚类
Week 4: 优化 4（校准闭环）→ 让系统开始从错误中学习
```

**为什么这个顺序**：
1. 先审计（知道什么值得保留），再改评分（在正确的信号基础上评分才有意义）
2. 先加 problem_clarity（成本最低，直接改善最大痛点），再做跨域检测（需要 LLM 调用，成本高）
3. 校准闭环最后做——需要前三个优化稳定运行几周，有足够的 prediction 数据才能校准

---

## 不做的优化（有意识的选择）

1. **增加更多信号源**：当前问题是信号源已经太多，做深不做广
2. **实时信号处理**：每日批处理是正确的节奏，实时处理会破坏"深度思考"的设计哲学
3. **更复杂的 ML 模型替代规则打分**：当前规则打分可解释、可调试、可手动校准。ML 模型是一个黑盒，在数据量不够大时反而更差
4. **多语言信号源扩展（日语、韩语等）**：先做好中英文的信号质量，再谈扩展
