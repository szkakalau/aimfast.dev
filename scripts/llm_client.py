"""
共享 LLM 客户端
支持 DeepSeek API（OpenAI 兼容格式）和本地 fallback。
v2.3: 添加月度 token 预算追踪，接近预算时自动降级为模板 fallback。
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# DeepSeek API 配置
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_CHAT = f"{DEEPSEEK_BASE}/v1/chat/completions"

TZ_SHANGHAI = timezone(timedelta(hours=8))
TOKEN_USAGE_PATH = ROOT / "tracking" / "token_usage.json"

# 从环境变量获取配置
def _get_api_key() -> str:
    # API key 仅从环境变量读取，不在 config.json 中存储
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    return _sanitize_key(key) if key else key


def _get_model() -> str:
    try:
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        return config.get("llm", {}).get("model", "deepseek-chat")
    except Exception:
        return "deepseek-chat"


def _get_monthly_budget() -> int:
    """从 config.json 获取月度预算（美元），转换为估算 token 数。"""
    try:
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        budget_usd = config.get("llm", {}).get("monthly_budget_usd", 20)
        # DeepSeek 定价约 ¥1/百万 token ≈ $0.14/百万 token（输入+输出混合约 $0.50/百万）
        # 保守估算: $1 ≈ 2M tokens
        return int(budget_usd * 2_000_000)
    except Exception:
        return 40_000_000  # 默认 $20 ≈ 40M tokens


def _read_token_usage() -> dict:
    """读取当月 token 使用记录。每月自动重置。"""
    current_month = datetime.now(TZ_SHANGHAI).strftime("%Y-%m")
    if TOKEN_USAGE_PATH.exists():
        try:
            data = json.loads(TOKEN_USAGE_PATH.read_text(encoding="utf-8"))
            if data.get("month") == current_month:
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {"month": current_month, "total_tokens": 0, "calls": 0, "budget_exceeded": False}


def _write_token_usage(data: dict):
    """写入 token 使用记录。"""
    TOKEN_USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_USAGE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _check_and_record_tokens(tokens_used: int, is_retry: bool = False):
    """记录 token 消耗。如果超过月度预算的 90%，打印警告；超过 100%，设置预算超限标志。"""
    if tokens_used <= 0:
        return

    usage = _read_token_usage()
    # 重试不计入（避免重复计数同一请求）
    if not is_retry:
        usage["total_tokens"] += tokens_used
        usage["calls"] += 1

    budget = _get_monthly_budget()
    ratio = usage["total_tokens"] / budget

    if ratio >= 1.0 and not usage.get("budget_exceeded"):
        usage["budget_exceeded"] = True
        print(f"[LLM] ⚠️ 月度 token 预算已用尽！（{usage['total_tokens']:,}/{budget:,} = {ratio:.0%})")
        print(f"[LLM] 后续调用将使用模板 fallback 直到下个月")
    elif ratio >= 0.9 and not usage.get("budget_warned"):
        usage["budget_warned"] = True
        print(f"[LLM] ⚠️ 月度 token 预算已用 {ratio:.0%}（{usage['total_tokens']:,}/{budget:,}）")

    _write_token_usage(usage)


def _is_budget_exceeded() -> bool:
    """检查月度预算是否已超限。"""
    usage = _read_token_usage()
    return usage.get("budget_exceeded", False)


def _sanitize(text: str) -> str:
    """去除 BOM 等不可编码字符，防止 UnicodeEncodeError"""
    # 移除 BOM (U+FEFF) 和 BOM-reversed (U+FFFE)
    return text.replace("﻿", "").replace("￾", "").replace("​", "")


def _sanitize_key(key: str) -> str:
    """清理 API key，确保只含可打印 ASCII"""
    return "".join(c for c in key if 32 <= ord(c) <= 126)


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

    # 防御性清理 API key（避免 BOM 等不可编码字符）
    api_key = _sanitize(api_key).strip()

    if dry_run:
        print("[LLM] DRY RUN — 不调用 API")
        return _template_fallback(system_prompt, user_prompt)

    # 月度预算检查
    if _is_budget_exceeded():
        print("[LLM] 月度 token 预算已超限，使用模板 fallback")
        return _template_fallback(system_prompt, user_prompt)

    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 防御性清理：去除 BOM 等不可编码字符
    system_prompt = _sanitize(system_prompt)
    user_prompt = _sanitize(user_prompt)

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
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            resp = requests.post(DEEPSEEK_CHAT, headers=headers, data=body, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)
                print(f"[LLM] 生成完成 ({tokens} tokens)")
                _check_and_record_tokens(tokens, is_retry=(attempt > 0))
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
        + "*自动生成于 AimFast.Dev v1.0*\n"
    )
