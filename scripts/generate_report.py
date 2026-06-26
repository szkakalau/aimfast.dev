"""
日报生成器
输入: ./daily/YYYY-MM-DD/signals.json（处理后的信号）
输出: ./daily/YYYY-MM-DD/report.md（完整五层日报）
依赖: DeepSeek API（或本地 fallback）
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.llm_client import chat
from scripts.pipeline_status import write as write_pipeline_status

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TEMPLATES_DIR = ROOT / "templates"
METHODOLOGY_PATH = ROOT / "methodology.md"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def load_signals(date_str: str) -> list[dict]:
    path = DAILY_DIR / date_str / "signals.json"
    if not path.exists():
        print(f"[日报] {path} 不存在，无法生成日报")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("signals", [])


def load_methodology() -> str:
    if METHODOLOGY_PATH.exists():
        return METHODOLOGY_PATH.read_text(encoding="utf-8")
    return ""


def _categorize_signals(signals: list[dict]) -> dict:
    """将信号按日报板块分类。v2.1: 新增 C 端消费信号分类。"""
    categories = {
        "new_products": [],       # 新产品发布
        "search_trends": [],      # 搜索趋势异动
        "github_trending": [],    # GitHub 涨星
        "complaints": [],         # 抱怨热点
        "shutdowns": [],          # 停运/降级
        "growing_tools": [],      # 增长工具
        "model_updates": [],      # 模型动态
        "oss_milestones": [],     # 开源进展
        "pricing": [],            # 定价讨论
        "revival": [],            # 复活信号
        "migration": [],          # 迁移话题
        "trending": [],           # 趋势信号
        "cooling": [],            # 降温信号
        "c_end": [],              # C 端消费信号（v2.1 新增）
    }

    for s in signals:
        stype = s.get("signal_type", "")
        tags = [t for t in s.get("tags", []) if isinstance(t, str)]
        tags_str = " ".join(tags).lower()
        title = s.get("title", "").lower()
        summary = s.get("summary", "").lower()
        text = f"{title} {summary} {tags_str} {stype}"

        if stype in ("product-launch", "show_hn") or any(kw in text for kw in ["launch", "发布", "新产品", "just launched"]):
            categories["new_products"].append(s)
        if stype in ("keyword_trend", "trending_search") or "trends" in s.get("source_key", ""):
            if s.get("cooling"):
                categories["cooling"].append(s)
            elif any(kw in text for kw in ["surging", "rising", "暴涨", "上升"]):
                categories["search_trends"].append(s)
            else:
                categories["trending"].append(s)
        if s.get("source_key") == "github" or "github" in s.get("source", "").lower():
            categories["github_trending"].append(s)
        if stype == "complaint" or any(kw in text for kw in ["抱怨", "太贵", "frustrated", "why is", "too expensive", "problem"]):
            categories["complaints"].append(s)
        if any(kw in text for kw in ["shutdown", "停运", "deprecated", "sunset", "discontinued"]):
            categories["shutdowns"].append(s)
        if any(kw in text for kw in ["growth", "增长", "trending", "star"]):
            categories["growing_tools"].append(s)
        if any(kw in text for kw in ["model", "模型", "llm", "gpt", "claude", "deepseek"]):
            categories["model_updates"].append(s)
        if any(kw in text for kw in ["open source", "开源", "oss", "github"]):
            categories["oss_milestones"].append(s)
        if any(kw in text for kw in ["pricing", "定价", "mrr", "revenue", "收入", "subscription"]):
            categories["pricing"].append(s)
        if any(kw in text for kw in ["revival", "复活", "comeback", "rewrite"]):
            categories["revival"].append(s)
        if any(kw in text for kw in ["migration", "迁移", "switch from", "alternative to", "替代"]):
            categories["migration"].append(s)

        # C 端消费信号检测（v2.1 新增）
        # 优先使用 scoring 阶段已计算的 c_end_flag
        if s.get("c_end_flag"):
            categories["c_end"].append(s)
        else:
            # 备用：基于关键词的 C 端检测
            c_kw = [
                "game", "游戏", "play", "gaming",
                "pdf", "scan", "文档", "扫描",
                "audio", "music", "podcast", "音乐", "播客", "有声",
                "video", "视频", "movie",
                "photo", "image", "图片", "照片",
                "health", "fitness", "健康", "运动",
                "travel", "旅行",
                "home", "garden", "家居", "花园", "lawn",
                "pet", "dog", "cat", "宠物",
                "book", "reading", "阅读",
                "mac app", "macos", "menu bar",
                "chrome extension", "浏览器插件",
                "desktop app", "桌面应用",
                "logitech", "razer", "外设", "鼠标", "键盘", "硬件",
                "subscription", "订阅",
            ]
            if any(kw in text for kw in c_kw):
                categories["c_end"].append(s)

    return categories


def _build_system_prompt() -> str:
    """构建系统提示：方法论 + BuilderPulse 蒸馏风格 + 日报模板。"""
    methodology = load_methodology()

    return f"""你是 AimFast.Dev的日报主编。你的任务是基于处理后的信号数据，生成一份 Builder 读得懂、能行动的独立开发者情报日报。

## 方法论

{methodology}

## 核心写作铁律

### 原子结构（每个分析板块必须遵守）
```
🔍 信号 → 白话解读 → 关键判断 → 反向视角
```
- **信号**: 具体数据 + 来源，绝不模棱两可
- **白话解读**: 把技术信号翻译成 Builder 能行动的人话——这个信号意味着什么产品机会？谁会付钱？
- **关键判断**: 一个明确的、可争论的建议——不要和稀泥
- **反向视角**: 什么情况下这个判断是错的？风险是什么？

### 证据铁律
- 每个判断必须附带**具体数字**（评论数、star 数、金额、百分比）
- **绝对禁用**: "很多人""最近很火""大家觉得""广受好评"
- 引用格式: "引发 XXX 条讨论" / "上涨 +X%" / "$XX/月"

### 买家命名
- 每个推荐必须回答: **谁会最先付钱？**（具体到角色，如"小型产品团队的工程负责人"而非"企业"）
- 回答: **为什么是这周？**（时效性理由——什么变化让今天不同于上周）

### 白话翻译原则
- 每次引入技术术语时，必须在同一句中用白话解释
- 不假设读者知道任何缩写（MCP、RAG、eBPF、CSP 等——全部解释）
- 把"AI agent"翻译成"能代表用户调用工具的软件"
- 把"self-hosted"翻译成"软件跑在你自己的服务器上"

### 定价意识
- 每个产品推荐必须有定价锚点: $19 一次性报告 / $9-29/月监控
- 第一版保持人工——Google Form + Markdown 输出即可，不要一上来就做全自动平台
- 按追回的钱、省下的时间、或避免的成本来定价

### 语气铁律
- 像一个有经验的 Builder 在和朋友聊天，不是分析师报告
- 不装、不吹、不贩卖焦虑
- 承认不确定性——"我可能错了，但数据指向…"
- 用"你"而不是"开发者们"

### SEO 铁律（搜索引擎优化）
- **标题**: H1 标题 50-60 字符，包含核心关键词（如"产品机会""信号情报""独立开发者"），有吸引力但不标题党
- **元描述**: 第一个自然段（150-160 字符）必须能独立作为 Google 搜索结果的描述文字，清晰概括全文内容
- **标题层级**: 严格使用 H1 → H2 → H3，绝不跳级。每个 H2 下至少 150 字正文
- **关键词自然出现**: 核心关键词（"产品机会""信号""Builder""定价"）在前 200 字内至少出现一次
- **链接文字**: 所有链接使用描述性文字（"查看 HN 讨论（417 评论）"），禁止"点击这里"
- **图片替代文字**: 如果引用图表/表格，确保有文字描述版本
- **段落长度**: 每段不超过 4 句，便于 Google 提取 featured snippet

### 🆕 C 端机会专项（v2.1 新增 — 必须执行）

**问题背景**：信号源（GitHub、HN、V2EX）天然偏开发者，评分公式历史上偏 B2B SaaS。但这不意味着 C 端机会不存在——只是被系统性过滤了。

**你必须做到**：
1. 在每个日报的「发现机会」板块中，**优先列出 3 个 C 端消费信号**（面向普通用户，非 AI 开发者工具）
2. C 端信号的特征识别：Mac App / Chrome 插件 / 桌面工具 / 游戏 / 生活效率 / 音频视频 / 健康 / 家居 / 宠物 / 旅行 / 有声书 / 播客 / 外设硬件 / 订阅制服务
3. 对于每个 C 端信号，回答：**普通用户（非程序员）会用它做什么？为什么愿意付钱？**
4. 定价锚点改为 C 端友好的：$2.99-9.99 一次性 / $4.99-14.99/月（而非 B2B 的 $19-29/月）
5. 验证路径改为 C 端友好的：App Store 预注册 / Reddit 消费者子版块 / 直接 Dribbble/ProductHunt 发布 / 社交媒体传播

**C 端 vs B 端判断规则**：
- 如果买方是"工程经理/CTO/开发者团队"→ B 端，放入「发现机会」的 Solo-founder 子板块
- 如果买方是"普通 Mac 用户/上班族/学生/宠物主/旅行者/创意工作者"→ C 端，放入独立的「🛍️ C端消费机会」子板块
- 如果一个信号两者都可以，**优先放入 C 端板块**（因为历史上 C 端被系统性低估）

## 日报结构

### 📝 主编说（~200 字人话开场）
结构: 大家都在聊 X → 但真正可构建的信号是 Y → 谁会先付钱 → 为什么是这周 → $19 报告值不值 → 真正麻烦的活是什么

### 🎯 今日 2 小时构建
- 产品名（英文 + 中文解释）
- 一句话描述 + 支撑证据（讨论量）
- **为什么不选另外两个**（显式排除 2 个候选方向）
- 定价: $19 一次性报告 → $9-29/月监控
- 最快验证路径: 今天就能做的验证动作
- MVP 保持人工: Google Form + Markdown 即可

### 📊 今日 Top 3 信号
- 每个信号是**复合观察**（连接多个数据点到一起）
- 附带具体讨论量/star 数/增长率
- 交叉参考来源列表

### 📖 白话简报
- 一句核心判断
- 证据表格: 证据 | 讨论量 | 白话含义
- 读者行动表: 技术爱好者 | Builder | 谨慎点

### 🔍 发现机会
4 个子板块，每个必须遵守原子结构:
- Solo-founder 产品发布
- 搜索词暴涨
- GitHub 快速增长开源项目（无商业版本）
- 开发者在抱怨什么

### 🛍️ C端消费机会（v2.1 新增 — 独立板块，级别等同于「发现机会」）
**目的**: 识别面向普通消费者（非程序员）的产品机会。从今日信号中挖掘那些被评分公式低估的 C 端信号。

**必须包含**：
- **C 端信号 Top 3**: 每个用「信号 → 白话解读 → 谁会付钱（普通人角色）→ 定价（C端友好价）→ 验证路径」格式
- **为什么日报过去漏掉了它**：一句话解释（如"因为被评分公式的 actionability 维度低估"）
- **可复制的模式**：这个 C 端信号暗示了什么可复制的产品模式？

**定价参考**：
- 工具类: $4.99-9.99 一次性
- 订阅类: $4.99-14.99/月
- 游戏类: 免费 + $2.99 去广告 / $9.99 年费

**验证路径参考**：
- Mac App: App Store 预注册页 + Reddit r/macapps 发帖
- Chrome 插件: Chrome Web Store 上架 + 相关论坛签名档
- 游戏: itch.io 发布 + HN Show HN（HN偏好极简游戏）

### 🛰️ 技术选型
4 个子板块，每个必须遵守原子结构:
- 大公司关停/降级产品
- 增长最快的开发者工具
- HuggingFace 最热模型 → 消费者产品机会
- 开源 AI 重要进展

### 🏭 竞争情报
3 个子板块，每个必须遵守原子结构:
- Indie 开发者收入与定价讨论
- 沉寂老项目突然复活
- "XX 已死"或迁移文章

### 📈 趋势判断
4 个子板块，每个必须遵守原子结构:
- 本周最常见技术关键词及变化
- VC 和 YC 关注话题
- 降温的 AI 搜索词
- 新词雷达: 哪些概念正在从零升起

### 🎬 行动触发
4 个子板块:
- 2 小时/完整周末做什么（详细版——比顶部更展开）
- 定价和变现模型研究
- 今天最反直觉的发现
- Product Hunt 与开发者工具重叠点

### 🔗 来源
所有引用的信号链接列表。

---

## 输出要求
- 格式: 完整 Markdown，不要用代码块包裹
- 篇幅: 正文 3000-6000 字（比之前更详细，每个子节至少 150 字）
- 语言: 全程中文，专业术语首次出现时用白话解释
- 结尾: 加 `---` 分隔线 + `*— AimFast.Dev日报*` 签名
- 🆕 **C端消费机会板块为必选项**，即使今日 C 端信号较少，也要基于现有数据给出至少 1 个 C 端方向（可以是从开发者信号中推导出的消费者版本）"""


def _build_user_prompt(signals: list[dict], categories: dict, date_str: str) -> str:
    """构建用户提示：信号数据 + 具体生成指令。"""
    top5 = signals[:5]
    top_signal = top5[0] if top5 else None

    # Top 5 信号详情
    top5_lines = []
    for i, s in enumerate(top5, 1):
        bd = s.get("score_breakdown", {})
        top5_lines.append(
            f"### {i}. [{s.get('score', 0)}分] {s.get('title', 'N/A')}\n"
            f"- 来源: {s.get('source', '?')} | 跨平台数: {s.get('cross_platform_count', 0)}\n"
            f"- 互动: {s.get('discussion_count', 0)} 讨论 | 参与度: {s.get('engagement', {}).get('total', 0)}\n"
            f"- 链接: {s.get('url', 'N/A')}\n"
            f"- 摘要: {s.get('summary', 'N/A')}\n"
            f"- 标签: {', '.join([t for t in s.get('tags', []) if t])}\n"
            f"- 打分明细: {json.dumps(bd, ensure_ascii=False)}\n"
        )

    # 各部门信号摘要
    def _section_signals(key: str, label: str, limit: int = 5) -> str:
        items = categories.get(key, [])[:limit]
        if not items:
            return f"**{label}**: 无"
        lines = [f"**{label}** ({len(categories.get(key, []))} 条):"]
        for s in items:
            lines.append(f"- [{s.get('score', 0)}分] {s.get('title', '')[:80]} — {s.get('source', '')} — {s.get('summary', '')[:100]}")
        return "\n".join(lines)

    sections = [
        _section_signals("new_products", "新产品发布"),
        _section_signals("search_trends", "搜索趋势异动"),
        _section_signals("github_trending", "GitHub 涨星项目"),
        _section_signals("complaints", "开发者抱怨热点"),
        _section_signals("shutdowns", "停运与降级"),
        _section_signals("growing_tools", "增长最快的开发者工具"),
        _section_signals("model_updates", "模型动态"),
        _section_signals("oss_milestones", "开源重要进展"),
        _section_signals("pricing", "独立开发者定价与收入讨论"),
        _section_signals("revival", "复活项目信号"),
        _section_signals("migration", "迁移话题"),
        _section_signals("trending", "趋势信号"),
        _section_signals("cooling", "降温信号"),
        _section_signals("c_end", "🛍️ C端消费信号（v2.1 — 非AI SaaS，面向普通用户）"),
    ]

    # 信号总览
    all_signals_brief = []
    for s in signals[:30]:
        all_signals_brief.append(
            f"- [{s.get('score', 0)}分 | {s.get('source', '?')}] {s.get('title', '')[:100]}"
        )

    # 加载配置以获取阈值
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    min_score = cfg["scoring"]["thresholds"]["action_trigger"]
    min_platforms = cfg["scoring"]["thresholds"]["cross_platform_min"]

    # 跨平台验证的信号（优先关注）
    cross_platform = [s for s in signals if s.get("cross_platform_count", 0) >= min_platforms]
    cp_brief = []
    for s in cross_platform[:10]:
        cp_brief.append(
            f"- [{s.get('score', 0)}分 | {s.get('cross_platform_count', 0)}平台] {s.get('title', '')[:100]}"
        )

    return f"""## 日期: {date_str}

## 信号总览（Top 30 / 共 {len(signals)} 条）

{chr(10).join(all_signals_brief)}

## 跨平台验证信号（≥{min_platforms} 独立源，共 {len(cross_platform)} 条 — 优先关注）

{chr(10).join(cp_brief) if cp_brief else '无跨平台验证信号'}

## Top 5 信号详情

{chr(10).join(top5_lines)}

## 分类信号

{chr(10).join(sections)}

---

请基于以上数据生成 {date_str} 的 AimFast.Dev日报。

## 生成指令

1. **主编说**: 从今天数据中找出"大家都在聊的表面话题"vs"真正可构建的信号"，200 字以内
2. **今日 2 小时构建**: {'如果 Top1 信号达到 Action 阈值（≥' + str(min_score) + ' 分 + 跨平台 ≥' + str(min_platforms) + '），生成完整产品方案，包括产品名、定价、验证路径、为什么不选另外两个方向' if top_signal and top_signal.get('score', 0) >= min_score and top_signal.get('cross_platform_count', 0) >= min_platforms else '即使未达 Action 阈值，也从数据中找出一个可 2 小时构建的方向'}
3. **Top 3 信号**: 优先选跨平台验证的信号——真实趋势而非单一平台噪音
4. **白话简报**: 用表格呈现——证据 | 讨论量 | 白话含义，加读者行动表
5. **每个子板块**: 严格遵守 信号→白话解读→关键判断→反向视角 四段式
6. **技术术语**: 首次出现必须白话解释
7. **定价**: 每个产品推荐必须有定价锚点和验证路径
8. **无数据板块**: 如实写"今日无显著发现"，不要编造
9. **篇幅**: 3000-6000 字，比常规日报更详细
10. 🆕 **C端消费机会板块为必填**: 从 c_end 分类信号中提取至少 3 个面向普通消费者的产品机会。如果 c_end 信号不足 3 个，从其他分类中发掘可以"C端化"的信号。每个 C 端机会必须回答: 普通人用它做什么？为什么愿意付钱？用什么渠道验证（非 Landing Page）？"""


def generate_report(signals: list[dict], date_str: str) -> str:
    """调用 LLM 生成完整五层日报。"""
    if not signals:
        return f"# AimFast.Dev日报 — {date_str}\n\n> 今日无信号数据。\n"

    categories = _categorize_signals(signals)
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(signals, categories, date_str)

    print(f"[日报] 上下文: {len(system_prompt)} + {len(user_prompt)} = {len(system_prompt) + len(user_prompt)} 字符")

    report = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=8192,
    )

    # 如果返回内容已包含 markdown 代码块，去掉包裹
    if report.startswith("```"):
        lines = report.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        report = "\n".join(lines)

    return report


def run(date_str: str | None = None) -> str:
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[日报] 日报生成 — {date}")
    print(f"{'='*50}")

    signals = load_signals(date)
    if not signals:
        print("[日报] 无处理后信号，跳过日报生成")
        write_pipeline_status(date, "report", "skipped",
            reason="no_signals_data",
            message="No signals.json found for today — report generation skipped.")
        return ""

    # 按 score 降序
    signals.sort(key=lambda s: s.get("score", 0), reverse=True)

    report = generate_report(signals, date)

    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "report.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"[日报] 日报已保存 → {output_path}")
    print(f"[日报] 字数: {len(report)} 字符")

    write_pipeline_status(date, "report", "generated",
        message=f"Daily report saved ({len(report):,} chars)")

    return report


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    report = run(today)
    if report:
        try:
            print("\n" + report[:500] + "...")
        except UnicodeEncodeError:
            print(f"\n[Report preview: {len(report)} chars, see daily/{today}/report.md]")
