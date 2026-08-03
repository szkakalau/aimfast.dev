"""
技术成熟度评估 — 纯规则驱动，不调 LLM。

设计原则:
  - 只加分不扣分：新技术的早期信号本身就很有价值，不应被成熟度压分。
  - 只对 > 1.0 的修正系数生效（即只在有把握时加分）。
  - 未匹配的技术默认 1.0（中性），不影响现有评分。

用法:
  from scripts.tech_maturity import get_feasibility
  modifier = get_feasibility("react")  # → 1.15
  modifier = get_feasibility("unknown-new-thing")  # → 1.00
"""

# 已知技术的成熟度分数（1-5，5 = 生产级大规模部署）
# 分数只用于确定加分幅度，低分不扣分。
TECH_MATURITY: dict[str, float] = {
    # ── 5: 生产级 — 有大规模部署案例，生态完善 ──
    "react": 5.0, "reactjs": 5.0, "next.js": 5.0, "nextjs": 5.0,
    "typescript": 5.0, "javascript": 5.0, "python": 5.0,
    "postgresql": 5.0, "mysql": 5.0, "redis": 5.0,
    "docker": 5.0, "kubernetes": 5.0, "k8s": 5.0,
    "graphql": 5.0, "rest-api": 5.0, "rest api": 5.0,
    "tailwind-css": 5.0, "tailwind": 5.0, "css": 5.0,
    "prisma": 5.0, "fastapi": 5.0, "flask": 5.0, "django": 5.0,
    "node.js": 5.0, "nodejs": 5.0, "express": 5.0,
    "aws": 5.0, "aws-lambda": 5.0, "s3": 5.0,
    "nginx": 5.0, "apache": 5.0,
    "git": 5.0, "github": 5.0, "github-actions": 5.0,
    "linux": 5.0, "unix": 5.0,
    "mongodb": 5.0, "elasticsearch": 5.0,
    "webpack": 5.0, "babel": 5.0,
    "vscode": 5.0, "visual-studio-code": 5.0,
    "openai": 5.0, "openai-api": 5.0, "gpt": 5.0,
    "stripe": 5.0, "twilio": 5.0, "sendgrid": 5.0,

    # ── 4: 早期但可行 — 有稳定文档和活跃社区 ──
    "bun": 4.0, "drizzle": 4.0, "drizzle-orm": 4.0,
    "hono": 4.0, "htmx": 4.0, "astro": 4.0, "astrojs": 4.0,
    "svelte": 4.0, "sveltekit": 4.0, "trpc": 4.0,
    "playwright": 4.0, "vite": 4.0, "vitest": 4.0,
    "ollama": 4.0, "duckdb": 4.0, "supabase": 4.0,
    "cloudflare-workers": 4.0, "cloudflare": 4.0,
    "biome": 4.0, "turborepo": 4.0,
    "vercel": 4.0, "vercel-ai": 4.0,
    "remix": 4.0, "nuxt": 4.0, "solidjs": 4.0,
    "elysia": 4.0, "fastify": 4.0,
    "neon": 4.0, "planetscale": 4.0, "turso": 4.0,
    "claude": 4.0, "anthropic": 4.0, "claude-api": 4.0,
    "gemini": 4.0, "google-ai": 4.0,
    "resend": 4.0, "clerk": 4.0, "lucia-auth": 4.0,
    "shadcn": 4.0, "shadcn-ui": 4.0, "radix-ui": 4.0,
    "zod": 4.0, "t3-stack": 4.0,
    "temporal": 4.0, "trigger.dev": 4.0,
    "warp": 4.0, "ghostty": 4.0,
    "cursor": 4.0, "windsurf": 4.0,
    "railway": 4.0, "fly.io": 4.0, "render": 4.0,
    "polars": 4.0, "arrow": 4.0,

    # ── 3: 实验性 — Beta 阶段，API 可能变动 ──
    "bun.sh": 3.0, "mojo": 3.0, "gleam": 3.0, "zig": 3.0,
    "roc": 3.0, "vale": 3.0,
    "langchain": 3.0, "llama-index": 3.0, "chromadb": 3.0,
    "langgraph": 3.0, "crewai": 3.0, "autogen": 3.0,
    "mastra": 3.0, "vercel-agent": 3.0,
    "pinecone": 3.0, "weaviate": 3.0, "qdrant": 3.0, "milvus": 3.0,
    "modal": 3.0, "replicate": 3.0,
    "continue": 3.0, "continue-dev": 3.0,
    "aider": 3.0, "claude-code": 3.0, "cursor-ai": 3.0,
    "bolt": 3.0, "lovable": 3.0, "v0": 3.0, "v0.dev": 3.0,
    "mcp": 3.0, "mcp-protocol": 3.0, "mcp-server": 3.0,
    "elevenlabs": 3.0, "suno": 3.0,
    "fable": 3.0, "fable-5": 3.0, "claude-sonnet": 3.0,
    "deepseek": 3.0, "deepseek-r1": 3.0, "qwen": 3.0,
    "mistral": 3.0, "mixtral": 3.0,
    "whisper": 3.0, "whisper.cpp": 3.0,

    # ── 2: 前沿 — 新发布、文档不完整（未匹配的技术也默认归此类）──
    # 不在此映射中的技术通过关键词推断，可能得到 2 分

    # ── 1: 研究阶段 — 仅论文/概念验证 ──
    # 通过 research_keywords 检测
}

# 含以下关键词的技术标记为研究阶段（不给予加分）
RESEARCH_KEYWORDS = [
    "paper", "research", "arxiv", "论文", "研究",
    "benchmark", "preprint", "submission",
    "survey", "review-paper",
]

# 分数到修正系数的映射
# 设计理念：① 1.00 是中性（不改变分数）② 只对 4+ 分给予实际加分
MATURITY_TO_MODIFIER: dict[int, float] = {
    5: 1.15,  # 生产级技术 → +15% 分数
    4: 1.08,  # 可行技术 → +8% 分数
    3: 1.00,  # 实验性技术 → 不加分
    2: 1.00,  # 前沿技术 → 不加分
    1: 1.00,  # 研究阶段 → 不加分
}


def get_feasibility(term_name: str, tags: list[str] | None = None) -> float:
    """返回技术可行性修正系数（0.80 ~ 1.15）。

    1.00 = 中性，不影响现有评分。
    > 1.00 = 成熟技术加分（生产级 +15%，早期可行 +8%）。
    永远不会 < 1.00 扣分 — 新技术的早期信号本身就是价值。

    Args:
        term_name: term 名称（英文或中文）
        tags: 可选标签列表，用于辅助判断

    Returns:
        float: 1.00 ~ 1.15 的修正系数
    """
    if not term_name:
        return 1.00

    name_lower = term_name.lower().strip()

    # 1. 精确匹配已知技术
    if name_lower in TECH_MATURITY:
        raw = TECH_MATURITY[name_lower]
        return MATURITY_TO_MODIFIER.get(int(raw), 1.00)

    # 2. 模糊匹配：检查是否为已知技术的变体
    # 例如 "next.js 15" → 匹配 "next.js"
    for known, maturity in TECH_MATURITY.items():
        if len(known) >= 4 and known in name_lower:
            raw = maturity
            return MATURITY_TO_MODIFIER.get(int(raw), 1.00)

    # 3. 关键词推断：研究/论文阶段
    for kw in RESEARCH_KEYWORDS:
        if kw in name_lower:
            return 1.00  # 研究阶段不加分

    # 4. 标签辅助推断
    if tags:
        tag_lower = [t.lower() for t in tags]
        for tag in tag_lower:
            if tag in TECH_MATURITY:
                raw = TECH_MATURITY[tag]
                return MATURITY_TO_MODIFIER.get(int(raw), 1.00)

    # 5. 未知技术 → 中性（1.00）
    return 1.00


# ─── 自检（模块导入时运行，不影响正常使用）─────────────────────

def _self_test():
    """验证核心逻辑。"""
    assert get_feasibility("react") == 1.15, "生产级应 +15%"
    assert get_feasibility("bun") == 1.08, "早期可行应 +8%"
    assert get_feasibility("langchain") == 1.00, "实验性不加分"
    assert get_feasibility("unknown-new-thing") == 1.00, "未知技术不加分"
    assert get_feasibility("") == 1.00, "空字符串应中性"
    assert get_feasibility("arxiv-paper-2026") == 1.00, "研究词不加分"
    # 模糊匹配
    assert get_feasibility("next.js 15 app router") == 1.15, "模糊匹配生产级"
    assert get_feasibility("react component library") == 1.15, "模糊匹配生产级"
    print("[tech_maturity] 自检通过 — 7/7 assertions")


if __name__ == "__main__":
    _self_test()
    # 打印映射表覆盖范围
    total = len(TECH_MATURITY)
    level_5 = sum(1 for v in TECH_MATURITY.values() if v >= 5)
    level_4 = sum(1 for v in TECH_MATURITY.values() if 4 <= v < 5)
    level_3 = sum(1 for v in TECH_MATURITY.values() if 3 <= v < 4)
    print(f"[tech_maturity] 共 {total} 个已知技术: 5★={level_5}, 4★={level_4}, 3★={level_3}")
