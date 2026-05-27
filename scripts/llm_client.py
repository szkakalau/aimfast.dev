"""
共享 LLM 客户端
支持 DeepSeek API（OpenAI 兼容格式）和本地 fallback。
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# DeepSeek API 配置
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_CHAT = f"{DEEPSEEK_BASE}/v1/chat/completions"

# 从环境变量或 config.json 获取配置
def _get_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        try:
            config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
            key = config.get("llm", {}).get("api_key", "")
        except Exception:
            pass
    return key


def _get_model() -> str:
    try:
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        return config.get("llm", {}).get("model", "deepseek-chat")
    except Exception:
        return "deepseek-chat"


def chat(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    dry_run: bool = False,
) -> str:
    """
    调用 DeepSeek API 生成文本。

    参数:
        system_prompt: 系统提示（方法论 + 模板）
        user_prompt: 用户提示（信号数据 + 具体指令）
        temperature: 温度参数
        max_tokens: 最大输出 token
        dry_run: 不实际调用 API，返回占位内容（调试用）

    返回:
        LLM 生成的文本，失败时返回空字符串
    """
    api_key = _get_api_key()
    if not api_key and not dry_run:
        print("[LLM] 未配置 DEEPSEEK_API_KEY，使用模板 fallback 模式")
        return _template_fallback(system_prompt, user_prompt)

    if dry_run:
        print("[LLM] DRY RUN — 不调用 API")
        return _template_fallback(system_prompt, user_prompt)

    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": _get_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(DEEPSEEK_CHAT, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)
                print(f"[LLM] 生成完成 ({tokens} tokens)")
                return content
            elif resp.status_code == 429:
                wait = (attempt + 1) * 10
                print(f"[LLM] 429 限流，{wait}s 后重试...")
                time.sleep(wait)
            else:
                print(f"[LLM] API 错误 HTTP {resp.status_code}: {resp.text[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(3)
        except requests.RequestException as e:
            print(f"[LLM] 请求失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)

    print("[LLM] 所有重试均失败，使用 fallback")
    return _template_fallback(system_prompt, user_prompt)


def _template_fallback(system_prompt: str, user_prompt: str) -> str:
    """
    当 LLM 不可用时的模板 fallback。
    生成结构化的占位日报，标注为自动生成。
    """
    return (
        "> ⚠️ 本文由模板自动生成（LLM 不可用或未配置 API Key）\n"
        + "> 配置 DEEPSEEK_API_KEY 环境变量或 config.json → llm.api_key 以启用 AI 生成。\n\n"
        + "---\n\n"
        + "## 信号数据已就绪\n\n"
        + "处理后的信号已保存至 daily/ 目录。请检查 signals.json 获取完整数据。\n\n"
        + "---\n\n"
        + "*自动生成于 KAKAOPC 情报科 v1.0*\n"
    )
