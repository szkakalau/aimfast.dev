# CLAUDE.md - AimFast.Dev

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec

## 信息诚信规则（2026-07-05 事故后设立）

**背景**：Claude 在 Toolify 无法访问（403）时，绕道用通用搜索结果冒充原始数据来源，编造了不存在的竞品分析结论，对用户决策造成极坏影响。

**规则**：
1. **工具失败必须透明报告**。如果某个 URL 返回 403/404/空结果，直接告诉用户"无法访问，不能回答这个问题"——不得用其他数据源的结果包装成原始请求的答案。
2. **区分数据来源**。如果只能通过间接来源推断，必须明确标注"这不是你要求的原始数据，而是从 X 搜索得到的替代结果"。
3. **不知道就说不知道。** "我无法回答"永远比"我编一个答案"更有价值。

## 已知技术债（2026-07-15 Review OS 审查记录）

1. **双 Pipeline 架构不统一** — `scripts/` 下存在两套独立的 term 发现流水线：
   - Pipeline A: `extract_terms → normalize_terms → classify_terms → score_terms → generate_term_research`
   - Pipeline B: `generate_trends → generate_opportunity`
   - 两套使用不同的评分公式、不同的数据文件，长期维护成本高。
   - 建议：统一为单一 Pipeline，以 Pipeline B 为主体，吸收 Pipeline A 的跨源验证和生命周期分类。
2. **React 组件测试框架缺失** — 项目无 JS 测试框架。`TrendFilter`/`TrendCard`/`Pagination` 等客户端组件无法进行单元测试。
   - 建议：安装 `vitest` + `@testing-library/react`，优先覆盖纯函数（`builderScore`、`normalizeCategory`、`stageLabel`）。
