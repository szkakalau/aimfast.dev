"""Create a properly formatted Markdown draft in Buttondown via API.

Usage:
  python scripts/buttondown_create_draft.py                          # defaults to latest issue
  python scripts/buttondown_create_draft.py newsletter/issues/002-xxx.md
  python scripts/buttondown_create_draft.py --publish                # create + publish instantly
"""
import glob
import json
import os
import sys
import urllib.request
import urllib.error

API_KEY = os.environ.get("BUTTONDOWN_API_KEY", "84ab52a2-58dc-4626-bcd7-0a5f5617dfee")
API_BASE = "https://api.buttondown.com/v1"

# ── Resolve markdown file ──────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
issues_dir = os.path.join(project_dir, "newsletter", "issues")

arg_path = None
publish = False

for a in sys.argv[1:]:
    if a == "--publish":
        publish = True
    elif a.endswith(".md"):
        arg_path = a

if arg_path:
    newsletter_path = arg_path if os.path.isabs(arg_path) else os.path.join(project_dir, arg_path)
else:
    # Default: latest .md in issues/ (skip twitter-thread files)
    candidates = sorted(
        [f for f in glob.glob(os.path.join(issues_dir, "*.md"))
         if "twitter-thread" not in os.path.basename(f)],
        reverse=True
    )
    if not candidates:
        print("No newsletter markdown files found in newsletter/issues/", file=sys.stderr)
        sys.exit(1)
    newsletter_path = candidates[0]

if not os.path.exists(newsletter_path):
    print(f"File not found: {newsletter_path}", file=sys.stderr)
    sys.exit(1)

# ── Parse markdown ─────────────────────────────────────────────────
with open(newsletter_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# First line is the H1 title → subject
subject = lines[0].strip().lstrip("# ")

# Body = everything after the first `---` separator
body_lines = []
started = False
for line in lines[1:]:
    if not started:
        if line.strip() == "---":
            started = True
        continue
    body_lines.append(line)

body = "".join(body_lines).strip()

# ── Send to Buttondown ─────────────────────────────────────────────
endpoint = f"{API_BASE}/emails"
status = "published" if publish else "draft"

payload = json.dumps({
    "subject": subject,
    "body": body,
    "status": status
}).encode("utf-8")

req = urllib.request.Request(
    endpoint,
    data=payload,
    headers={
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"Subject : {subject}")
        print(f"Source  : {os.path.basename(newsletter_path)}")
        print(f"Status  : {result.get('status')}")
        print(f"ID      : {result.get('id')}")
        print(f"URL     : https://buttondown.com/aimfast/archive/{result.get('secondary_id', '')}/")
        if not publish:
            print("\nNext: open Buttondown → Publish → Finalize")
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode()}", file=sys.stderr)
    sys.exit(1)
