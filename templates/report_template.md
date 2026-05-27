# KAKAOPC 情报科日报 — {{date}}

> 今日核心判断：[一句话，今天最重要的发现]
> 更新时间：{{time}} Shanghai Time

---

## 🎯 今日一击（Today's One Build）

**{{product_name}}** — {{one_line_description}}
- 信号来源：{{cross_platform_evidence}}
- 谁会付钱：{{specific_buyer_role}} + {{pain_scenario}}
- 2h 交付物：{{deliverable_type}}
- 定价锚点：{{pricing_anchor}}
- 验证方法：{{first_step}}
- Counter-view：{{failure_condition}}
- [跳转 → 完整 Action 方案](#action)

---

## 📊 Top 3 信号

| # | 信号 | 讨论量 | 来源 | 白话翻译 |
|---|------|--------|------|---------|
| 1 | {{signal_1_title}} | {{signal_1_volume}} | {{signal_1_source}} | {{signal_1_translation}} |
| 2 | {{signal_2_title}} | {{signal_2_volume}} | {{signal_2_source}} | {{signal_2_translation}} |
| 3 | {{signal_3_title}} | {{signal_3_volume}} | {{signal_3_source}} | {{signal_3_translation}} |

---

## 📖 Plain-English Brief

| 信号 | 白话含义 | Builder 视角 | 谨慎视角 |
|------|---------|-------------|---------|
| {{signal_a}} | {{signal_a_plain}} | {{signal_a_builder}} | {{signal_a_caution}} |
| {{signal_b}} | {{signal_b_plain}} | {{signal_b_builder}} | {{signal_b_caution}} |

---

## 🔍 Discovery（发现层）

### 今日产品发布
{{#each new_products}}
- **{{name}}**（{{source}}）：{{description}} → **Takeaway**：{{takeaway}} → **Counter-view**：{{counter_view}}
{{/each}}
{{#unless new_products}}*今日无值得关注的新产品发布*{{/unless}}

### 搜索趋势异动
{{#each search_trends}}
- **{{keyword}}**：{{growth_rate}} → 含义：{{meaning}} → 对 Builder 的意义：{{builder_meaning}}
{{/each}}
{{#unless search_trends}}*今日无显著搜索异动*{{/unless}}

### GitHub 涨星项目
{{#each github_trending}}
- **{{name}}**（{{stars}} star，{{growth}}）：为什么在涨：{{why}} → 对 Builder 的启示：{{builder_insight}}
{{/each}}
{{#unless github_trending}}*今日无显著涨星项目*{{/unless}}

### 开发者抱怨热点
{{#each complaint_signals}}
- **{{topic}}**（{{platform}}，{{volume}} 讨论）：抱怨内容：{{summary}} → 产品机会：{{opportunity}}
{{/each}}
{{#unless complaint_signals}}*今日无显著抱怨信号*{{/unless}}

---

## 🛰️ Tech Radar（技术雷达）

### 停运与降级
{{#each shutdowns}}
- **{{service}}**：{{detail}} → 替代品机会：{{replacement_opportunity}}
{{/each}}
{{#unless shutdowns}}*今日无停运/降级消息*{{/unless}}

### 增长最快的开发者工具
{{#each growing_tools}}
- **{{name}}**：{{growth_data}} — {{why}}
{{/each}}
{{#unless growing_tools}}*今日无显著增长工具*{{/unless}}

### 模型动态
{{#each model_updates}}
- **{{model}}**（{{downloads}} 下载）：{{significance}}
{{/each}}
{{#unless model_updates}}*今日无重要模型动态*{{/unless}}

### 开源重要进展
{{#each oss_milestones}}
- **{{project}}**：{{milestone}} → 影响：{{impact}}
{{/each}}
{{#unless oss_milestones}}*今日无重要开源进展*{{/unless}}

---

## 🏭 Competitive Intel（竞争情报）

### 独立开发者定价与收入讨论
{{#each pricing_discussions}}
- **{{topic}}**（{{source}}）：{{insight}}
{{/each}}
{{#unless pricing_discussions}}*今日无显著定价讨论*{{/unless}}

### 复活项目信号
{{#each revival_signals}}
- **{{project}}**：{{detail}} → {{implication}}
{{/each}}
{{#unless revival_signals}}*今日无复活信号*{{/unless}}

### 迁移话题
{{#each migration_signals}}
- **{{from}} → {{to}}**（{{source}}）：{{ecosystem_shift}}
{{/each}}
{{#unless migration_signals}}*今日无显著迁移话题*{{/unless}}

---

## 📈 Trends（趋势层）

### 关键词变迁
{{#each keyword_shifts}}
- {{description}}
{{/each}}
{{#unless keyword_shifts}}*本周关键词格局无明显变化*{{/unless}}

### VC / YC 关注方向
{{#each vc_signals}}
- **{{direction}}**：{{detail}} → ⚠️ 不等于 Builder 该做的方向
{{/each}}
{{#unless vc_signals}}*今日无显著 VC 动态*{{/unless}}

### 降温的 AI 搜索词
{{#each cooling_keywords}}
- **{{keyword}}**：{{detail}}
{{/each}}
{{#unless cooling_keywords}}*无新增降温词*{{/unless}}

### 新词雷达
{{#each new_terms}}
- **{{term}}**（首次出现在 {{first_seen}}）：{{context}}
{{/each}}
{{#unless new_terms}}*今日无新词入库*{{/unless}}

---

## 🎬 Action（行动层）

### 推荐 2h Build：{{product_name}}

**为什么今天这个赢了：**
- 排除 {{alternative_a}}：{{reason_a}}
- 排除 {{alternative_b}}：{{reason_b}}
- 这个方案赢在：{{winning_point}}

**MVP 规格：**
- 输入：{{user_input}}
- 输出：{{deliverable}}
- 不需要：{{not_needed}}
- 技术选型：{{tech_stack}}

**定价策略：**
- 首诊价：{{one_time_price}}
- 订阅价：{{subscription_price}}
- 为什么这个价格：{{pricing_rationale}}

**验证步骤：**
1. {{step_1}}
2. {{step_2}}
3. {{step_3}}

**Weekend Expansion：**
- {{expansion_path}}

**Counter-view：**
- {{failure_condition}}
- {{market_non_existence_condition}}

### 定价教训（来自今日信号）
{{#each pricing_lessons}}
- {{lesson}}
{{/each}}

### 今日最反直觉发现
{{counter_intuitive_finding}}

---

## 📉 降温提醒
{{#each cooling_alerts}}
- **{{topic}}**：{{reason}}
{{/each}}
{{#unless cooling_alerts}}*今日无新增降温提醒*{{/unless}}

---

## 🔗 来源
{{#each sources}}
- [{{label}}]({{url}})
{{/each}}

---

*{{date}} Shanghai Time | 下一篇预告：{{next_preview}}*
