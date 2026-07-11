"""
共享工具函数与默认值 — config fallback + LLM sanitize + common helpers。
"""
import json
import os
import re
import tempfile
from pathlib import Path


def sanitize_for_llm(text: str, strip_markdown: bool = True) -> str:
    """清理 LLM 提示注入风险字符。

    Args:
        text: 待清理文本。
        strip_markdown: 是否额外移除 **/*/__/_ 格式符。
                       信号标题（可能含 markdown）用 True，term 名用 False。
    """
    if not text:
        return ""
    # 移除 markdown 代码块/行内代码
    text = re.sub(r"```[^`]*```", "[code block]", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 花括号 → 圆括号（防止 LLM 误解析为 JSON）
    text = text.replace("{", "(").replace("}", ")")
    # 可选：剥离 markdown 格式符
    if strip_markdown:
        text = re.sub(r"\*\*|\*|__|_", "", text)
    # 截断超长文本
    if len(text) > 300:
        text = text[:297] + "..."
    return text.strip()


def atomic_write_json(path: Path, data: dict):
    """原子化 JSON 写入——先写临时文件，再 rename。

    避免进程崩溃留下损坏的半截 JSON 文件。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=".json", prefix=".tmp-", dir=str(path.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))  # 原子 rename (Windows 也支持)
    except Exception:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ══════════════════════════════════════════════════════
# 配置默认值 — 当 config.json 不可用时回退。
# 原则: config.json 是唯一真相源。此处仅用于容错。
# ══════════════════════════════════════════════════════
# ── GitHub Releases 默认仓库 ──────────────────────
DEFAULT_GITHUB_RELEASE_REPOS = [
    "openai/openai-python",
    "anthropics/anthropic-sdk-python",
    "vercel/ai-chatbot",
    "supabase/supabase",
    "google-gemini/generative-ai-python",
    "cloudflare/workers-sdk",
    "microsoft/TypeScript",
    "facebook/react",
    "shadcn-ui/ui",
    "langchain-ai/langchain",
    "ollama/ollama",
    "continuedev/continue",
    "microsoft/vscode",
    "n8n-io/n8n",
    "mastra-ai/mastra",
]

# ── Google News 默认搜索话题 ──────────────────────
DEFAULT_GOOGLENEWS_QUERIES = [
    "AI developer tools launch",
    "open source AI release",
    "indie hacker SaaS",
    "YC startup",
    "new API product",
]

# ── 来源权威权重 ──────────────────────────────────
# source_key → authority (1-10)
DEFAULT_SOURCE_AUTHORITY: dict[str, int] = {
    # 官方源头 — 一手信息
    "openai": 9, "anthropic": 9, "google-ai": 8,
    "vercel": 8, "supabase": 7, "cloudflare": 7,
    "apple-ml": 8, "huggingface-blog": 7,
    # 技术社区 — 高质量讨论
    "github": 10, "hn": 10, "arxiv": 9, "huggingface": 9,
    "lobsters": 8, "devcommunity": 7,
    # 发布平台 — 新产品/更新
    "producthunt": 7, "github-releases": 6,
    # 混合社区
    "reddit": 6, "v2ex": 5, "w2solo": 5, "indiehackers": 6,
    # 新闻/搜索 — 高信号量
    "googlenews": 4, "trends": 4, "x": 4, "x-trends": 3,
    # 消费者源 — 真实需求
    "reddit-consumer": 4, "douban": 3, "xiaohongshu": 3, "xhs": 3,
    # 未知
    "unknown": 3,
}
