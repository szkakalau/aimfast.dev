# Newsletter 发布工作流

## 架构

```
每周日 generate_weekly.py 生成周报
        ↓
  创始人改写（人格化）
        ↓
  输出 3 份内容：
  ├─ newsletter/issues/XXX-标题.md          → Buttondown 邮件
  ├─ newsletter/issues/XXX-twitter-thread-en.md → Twitter/X Thread
  └─ 即刻动态（从 Markdown 直接复制中文原文）
```

## 发布步骤

### Step 1: 准备 Markdown 源文件

在 `newsletter/issues/` 下创建文件，命名格式：`NNN-短标题.md`

**文件结构（必须严格遵守）：**
```markdown
# 邮件主题（会作为 Buttondown subject）

**AimFast.Dev 创始人的每周趋势复盘 · 第 N 期**

---

正文内容…

---

*这是 AimFast.Dev 的每周趋势复盘…*
*想看 AI 每天筛选出的全部信号？→ [aimfast.dev](https://aimfast.dev)*
```

- 第一行 `# 标题` → 自动提取为邮件 subject
- 第一个 `---` 之后的全部内容 → 邮件 body
- `---` 渲染为 `<hr>` 分隔线

### Step 2: 创建 Buttondown 草稿（一行命令）

```powershell
python scripts/buttondown_create_draft.py
```

> 脚本默认读取 `newsletter/issues/001-验证管线连败16次.md`。
> 发新一期时，先改脚本里的 `newsletter_path`，或改成命令行参数。
>
> API Key 已在 `.env.local` 的 `BUTTONDOWN_API_KEY` 中。

脚本成功后输出：
```
Subject: 我们的验证管线连败 16 次——但这可能是最好的事情
Body length: 1234 chars

Draft created!
   ID: em_xxxxxxxxxxxxx
   Status: draft
   URL: https://buttondown.com/aimfast/...
```

### Step 3: Buttondown UI 发布

1. 打开 Buttondown，找到刚创建的草稿
2. 检查 Markdown 渲染是否正确（标题、加粗、分隔线、列表）
3. 点击 **Publish → Finalize → Yes, I'm sure**

> ⚠️ 不要用 UI 的富文本编辑器直接粘贴 Markdown——会丢失所有格式。
> 只用 API 创建草稿，UI 只用来 Finalize。

### Step 4: 分发到其他平台

**Twitter/X Thread：**
- 从 `newsletter/issues/XXX-twitter-thread-en.md` 复制
- 手动分条发布

**即刻：**
- 直接复制中文 Markdown 原文
- 手动发布

### Step 5: 验证

- 检查 `https://buttondown.com/aimfast` 归档页是否出现新一期
- 检查订阅邮箱是否收到邮件

---

## 技术细节

| 项目 | 值 |
|------|-----|
| Buttondown 用户名 | `aimfast` |
| API Base | `https://api.buttondown.com/v1` |
| API Key | `.env.local` → `BUTTONDOWN_API_KEY` |
| CTA URL | `.env.local` → `NEXT_PUBLIC_NEWSLETTER_URL` |
| 归档页 | `https://buttondown.com/aimfast` |
| 创建草稿脚本 | `scripts/buttondown_create_draft.py` |

## 下次改进

- [ ] `buttondown_create_draft.py` 支持命令行参数指定文件路径
- [ ] 支持 `--publish` 参数一键发布（跳过 UI）
- [ ] `generate_weekly.py` 输出直接兼容 newsletter 文件格式
