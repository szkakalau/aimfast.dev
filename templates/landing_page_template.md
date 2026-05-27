# Landing Page 方案：{{project_name}}

> 关联信号：{{signal_reference}} | 信号强度：{{score}} 分
> 生成时间：{{timestamp}} | 追踪 ID：{{tracking_id}}

---

## 市场 & 语言

- 目标市场：{{target_market}}（海外 / 国内）
- Landing Page 语言：{{lp_language}}（English / 中文）— 按目标付费用户所在地决定
- 判断依据：{{language_rationale}}

---

## 页面结构

| 区域 | 内容 | 规则 |
|------|------|------|
| **主标题** | {{headline}} | 一句话价值主张，≤ 10 个词 |
| **副标题** | {{subheadline}} | 具体说明解决什么问题，≤ 20 个词 |
| **卖点 1** | {{selling_point_1}} | 核心功能点 + 好处 |
| **卖点 2** | {{selling_point_2}} | 差异化点 |
| **卖点 3** | {{selling_point_3}} | 信任背书 / 数据 |
| **CTA** | {{cta_text}} | 动作导向，如 "Get Free Report" / "开始审计" |
| **定价锚点** | {{pricing_display}} | 标价 $XX，early bird $XX |

---

## 信号 → 产品映射

| 信号 | 平台 | 讨论量 |
|------|------|--------|
| {{signal_1}} | {{platform_1}} | {{volume_1}} |
| {{signal_2}} | {{platform_2}} | {{volume_2}} |
| {{signal_3}} | {{platform_3}} | {{volume_3}} |

**为什么这个信号适合用 Landing Page 验证**：{{why_landing_page}}

---

## 竞争定位

| 竞品 | 做什么 | 差距 / 我们的切入点 |
|------|--------|-------------------|
| {{competitor_1}} | {{competitor_1_desc}} | {{competitor_1_gap}} |
| {{competitor_2}} | {{competitor_2_desc}} | {{competitor_2_gap}} |

**差异化**：不是在功能上竞争，是在 **{{workflow_position}}** 中替代 **{{replaces_what}}**。

---

## 部署方案

### 一域千弹

```
aimfast.dev/
├── /{{project_slug}}/          ← 本 LP
├── /{{other_active_project}}/  ← 验证中
├── /{{abandoned_project}}/     ← 已放弃（保留，不删）
└── /                            ← 首页（最新机会 + 成功案例）
```

### 技术方案

| 维度 | 选择 |
|------|------|
| 平台 | Vercel（免费） |
| 框架 | Next.js / 纯 HTML（选最快的） |
| 部署 | push GitHub → Vercel 自动部署 |
| 域名 | aimfast.dev/{{project_slug}}/ |

---

## 流量策略（7 天验证周期）

### 第一阶段：社区投放（Day 1-7）

| 步骤 | 操作 | 话术要点 |
|------|------|---------|
| 1 | 找到信号来源帖 | {{source_post_url}} |
| 2 | 写有价值的回复 | 先认同痛点 → 提出方案 → 附链接 |
| 3 | 交叉发布 | {{cross_post_platforms}} |

**投放清单**：
{{#each distribution_channels}}
- [ ] {{channel}}：{{specific_action}}
{{/each}}

### 第二阶段：判断（Day 7）

| 数据 | 判断 | 行动 |
|------|------|------|
| > 100 UV + 注册/咨询 | ✅ 验证通过 | 投入做产品 + SEO + 内容 |
| < 30 UV | ❌ 放弃 | 问题不痛或方案不对，保留页面，标注"实验已结束" |
| 30-100 UV + 0 注册 | ⚠️ 调整 | 流量对但转化差，调整 LP 或放弃 |

### 第三阶段：只有验证通过才投入长期流量（Day 7+）

- [ ] SEO 长尾词内容页
- [ ] Medium / 知乎 / DEV 教程文章
- [ ] Product Hunt 正式发布
- [ ] 付费广告（仅当 LTV 测算成立）

---

## 反方检验

- **这个 LP 方案什么情况下无效**：{{lp_failure_condition}}
- **什么信号出现说明方向错了**：{{contrary_signal}}
- **最可能失败的原因**：{{most_likely_failure}}

---

## 验证目标

| 指标 | 7 天目标 | 实际（Day 7 填写） |
|------|---------|------------------|
| UV | {{target_uv}} | — |
| 注册 / 咨询 | {{target_signups}} | — |
| 邮件收集 | {{target_emails}} | — |

---

*方案生成时间：{{timestamp}} | 7 天判定日：{{judgment_date}}*
