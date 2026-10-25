#!/usr/bin/env python3
"""生成 GitHub Pages 手册站点：扫描技能目录，把 SKILL.md / EXAMPLES.md 渲染为 docs/index.html。

用法：python3 scripts/build_docs.py   （依赖：pip3 install markdown）
新增技能时，在下方的 CATEGORIES 中补充分类与中文名后重跑本脚本。
"""
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
ICONS_DIR = DOCS_DIR / "icons"

CATEGORIES = {
    "电商 · 数据采集": [
        ("tmall-review-report", "天猫评价采集报告"),
        ("tmall-price-checker", "天猫价格核对"),
        ("jd-review-collector", "京东评论采集分析"),
    ],
    "电商 · 经营报表": [
        ("tmall-sales-to-warehouse-reconciliation", "天猫销售仓库对账"),
        ("tmall-monthly-business-report", "天猫月度经营报表"),
    ],
    "语雀": [
        ("yuque-sheet", "语雀表格解析"),
        ("yuque-mcp", "语雀 MCP 操作"),
    ],
    "办公工具": [
        ("invoice-organizer", "发票整理"),
        ("picture-slicer", "图片切割器"),
    ],
}

MD_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def parse_frontmatter(text):
    """返回 (frontmatter dict, body)。无 frontmatter 时返回 ({}, 原文)。"""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"')
    return fm, text[m.end():]


def strip_h1(text):
    return re.sub(r"^#\s+.*\n+", "", text, count=1)


def render_md(text):
    return markdown.markdown(text, extensions=MD_EXTENSIONS)


def add_copy_buttons(html_text):
    """把示例提示词的 blockquote 包一层带复制按钮的容器。"""
    return re.sub(
        r"<blockquote>(.*?)</blockquote>",
        r'<div class="prompt"><button class="copy-btn" type="button">复制</button><blockquote>\1</blockquote></div>',
        html_text,
        flags=re.S,
    )


def load_skills():
    skills = []
    for category, entries in CATEGORIES.items():
        for name, zh_name in entries:
            skill_dir = ROOT / name
            fm, skill_body = parse_frontmatter(
                (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            )
            examples_html = ""
            examples_path = skill_dir / "EXAMPLES.md"
            if examples_path.exists():
                examples_html = add_copy_buttons(
                    render_md(strip_h1(examples_path.read_text(encoding="utf-8")))
                )
            icon_src = skill_dir / "icon.svg"
            if icon_src.exists():
                ICONS_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(icon_src, ICONS_DIR / f"{name}.svg")
            skills.append(
                {
                    "name": name,
                    "zh_name": zh_name,
                    "category": category,
                    "description": fm.get("description", ""),
                    "skill_html": render_md(strip_h1(skill_body)),
                    "examples_html": examples_html,
                }
            )
    return skills


CSS = """
:root {
  --sidebar-w: 264px;
  --text: #1f2328;
  --muted: #656d76;
  --border: #e5e7eb;
  --accent: #4f46e5;
  --bg: #f7f8fa;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 24px; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB",
    "Microsoft YaHei", "Segoe UI", sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.75;
}
a { color: var(--accent); text-decoration: none; }

/* 侧边栏 */
.sidebar {
  position: fixed; inset: 0 auto 0 0; width: var(--sidebar-w);
  background: #fff; border-right: 1px solid var(--border);
  overflow-y: auto; padding: 24px 16px; z-index: 10;
}
.sidebar .brand { font-size: 18px; font-weight: 700; margin: 0 8px 4px; }
.sidebar .brand-sub { font-size: 12px; color: var(--muted); margin: 0 8px 20px; }
.sidebar .cat { font-size: 12px; font-weight: 600; color: var(--muted);
  margin: 18px 8px 6px; letter-spacing: .05em; }
.sidebar a.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 8px; border-radius: 8px; color: var(--text); font-size: 14px;
}
.sidebar a.nav-item img { width: 22px; height: 22px; border-radius: 5px; flex: none; }
.sidebar a.nav-item:hover { background: var(--bg); }
.sidebar a.nav-item.active { background: #eef0ff; color: var(--accent); font-weight: 600; }

.menu-btn {
  display: none; position: fixed; top: 12px; left: 12px; z-index: 20;
  border: 1px solid var(--border); background: #fff; border-radius: 8px;
  padding: 8px 12px; font-size: 14px; cursor: pointer;
}

/* 主内容 */
.main { margin-left: var(--sidebar-w); padding: 0 40px 120px; }
.content { max-width: 860px; margin: 0 auto; }

.hero { padding: 64px 0 32px; }
.hero h1 { font-size: 34px; margin: 0 0 12px; }
.hero p { color: var(--muted); font-size: 16px; max-width: 640px; }
.hero .badges { margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }
.hero .badge {
  background: #fff; border: 1px solid var(--border); border-radius: 999px;
  padding: 4px 14px; font-size: 13px; color: var(--muted);
}

.section-title { font-size: 22px; margin: 40px 0 16px; }

/* 总览卡片 */
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; }
.card {
  display: block; background: #fff; border: 1px solid var(--border);
  border-radius: 12px; padding: 18px; color: var(--text);
  transition: box-shadow .15s, transform .15s;
}
.card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.08); transform: translateY(-2px); }
.card .card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.card img { width: 34px; height: 34px; border-radius: 8px; }
.card .card-zh { font-weight: 600; font-size: 15px; }
.card .card-en { font-size: 12px; color: var(--muted); word-break: break-all; }
.card .card-desc { font-size: 13px; color: var(--muted);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

/* 技能详情节 */
.skill {
  background: #fff; border: 1px solid var(--border); border-radius: 14px;
  padding: 32px 36px; margin-top: 36px;
}
.skill-head { display: flex; align-items: center; gap: 14px;
  padding-bottom: 18px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
.skill-head img { width: 48px; height: 48px; border-radius: 11px; }
.skill-head .zh { font-size: 21px; font-weight: 700; }
.skill-head .en { font-size: 13px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.skill-cat { font-size: 12px; color: var(--muted); margin-left: auto; flex: none;
  border: 1px solid var(--border); border-radius: 999px; padding: 2px 12px; }

/* Markdown 内容 */
.skill h1, .skill h2 { font-size: 18px; margin: 26px 0 10px; }
.skill h3 { font-size: 16px; margin: 22px 0 8px; }
.skill p, .skill li { font-size: 14.5px; }
.skill code {
  background: #eff1f3; border-radius: 5px; padding: 2px 6px; font-size: 13px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.skill pre {
  background: #0f172a; color: #e2e8f0; border-radius: 10px;
  padding: 16px 18px; overflow-x: auto; font-size: 13px; line-height: 1.6;
}
.skill pre code { background: none; padding: 0; color: inherit; }
.skill table { border-collapse: collapse; width: 100%; font-size: 14px; margin: 12px 0; }
.skill th, .skill td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
.skill th { background: var(--bg); }
.skill hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }

/* 示例提示词块 */
.prompt { position: relative; margin: 14px 0; }
.prompt blockquote {
  margin: 0; background: #f6f4ff; border: 1px solid #ddd6fe; border-left: 4px solid var(--accent);
  border-radius: 10px; padding: 14px 16px; color: #3b3566; font-size: 14px;
}
.prompt blockquote p { margin: 6px 0; }
.copy-btn {
  position: absolute; top: 8px; right: 8px;
  border: 1px solid #ddd6fe; background: #fff; color: var(--accent);
  border-radius: 7px; padding: 3px 12px; font-size: 12px; cursor: pointer;
}
.copy-btn:hover { background: var(--accent); color: #fff; }
.copy-btn.done { background: #16a34a; border-color: #16a34a; color: #fff; }

footer { color: var(--muted); font-size: 13px; text-align: center; margin-top: 64px; }

@media (max-width: 900px) {
  .sidebar { transform: translateX(-100%); transition: transform .2s; }
  .sidebar.open { transform: none; box-shadow: 0 0 40px rgba(0,0,0,.15); }
  .menu-btn { display: block; }
  .main { margin-left: 0; padding: 56px 18px 100px; }
  .skill { padding: 22px 18px; }
}
"""

JS = """
document.querySelectorAll('.copy-btn').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var text = btn.parentElement.querySelector('blockquote').innerText;
    navigator.clipboard.writeText(text).then(function () {
      btn.textContent = '已复制';
      btn.classList.add('done');
      setTimeout(function () { btn.textContent = '复制'; btn.classList.remove('done'); }, 1600);
    });
  });
});

var links = Array.from(document.querySelectorAll('.sidebar a.nav-item'));
var sections = links.map(function (a) { return document.getElementById(a.hash.slice(1)); });
var spy = new IntersectionObserver(function (entries) {
  entries.forEach(function (e) {
    if (e.isIntersecting) {
      links.forEach(function (a) { a.classList.toggle('active', a.hash === '#' + e.target.id); });
    }
  });
}, { rootMargin: '-20% 0px -70% 0px' });
sections.forEach(function (s) { if (s) spy.observe(s); });

var menuBtn = document.querySelector('.menu-btn');
var sidebar = document.querySelector('.sidebar');
menuBtn.addEventListener('click', function () { sidebar.classList.toggle('open'); });
links.forEach(function (a) { a.addEventListener('click', function () { sidebar.classList.remove('open'); }); });
"""


def build_html(skills):
    total = len(skills)
    cats = []
    for cat in CATEGORIES:
        members = [s for s in skills if s["category"] == cat]
        if members:
            cats.append((cat, members))

    nav = []
    for cat, members in cats:
        nav.append(f'<div class="cat">{cat}</div>')
        for s in members:
            nav.append(
                f'<a class="nav-item" href="#skill-{s["name"]}">'
                f'<img src="icons/{s["name"]}.svg" alt="">{s["zh_name"]}</a>'
            )

    cards = []
    for cat, members in cats:
        cards.append(f'<h2 class="section-title">{cat}</h2>')
        cards.append('<div class="cards">')
        for s in members:
            cards.append(
                f'<a class="card" href="#skill-{s["name"]}">'
                f'<div class="card-head"><img src="icons/{s["name"]}.svg" alt="">'
                f'<div><div class="card-zh">{s["zh_name"]}</div>'
                f'<div class="card-en">{s["name"]}</div></div></div>'
                f'<div class="card-desc">{s["description"]}</div></a>'
            )
        cards.append("</div>")

    sections = []
    for cat, members in cats:
        for s in members:
            examples_block = ""
            if s["examples_html"]:
                examples_block = (
                    "<h2>使用示例</h2>" + s["examples_html"]
                )
            sections.append(
                f'<section class="skill" id="skill-{s["name"]}">'
                f'<div class="skill-head">'
                f'<img src="icons/{s["name"]}.svg" alt="{s["zh_name"]}">'
                f'<div><div class="zh">{s["zh_name"]}</div>'
                f'<div class="en">{s["name"]}</div></div>'
                f'<span class="skill-cat">{s["category"]}</span></div>'
                + s["skill_html"]
                + examples_block
                + "</section>"
            )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>skill-hub · Agent 技能使用手册</title>
<style>{CSS}</style>
</head>
<body>
<button class="menu-btn" type="button">☰ 技能目录</button>
<nav class="sidebar">
  <div class="brand">skill-hub</div>
  <div class="brand-sub">Agent 技能使用手册 · {total} 个技能</div>
  {''.join(nav)}
</nav>
<div class="main">
  <div class="content">
    <header class="hero">
      <h1>skill-hub 技能使用手册</h1>
      <p>通用 Agent 技能仓库：客户端无关，任意支持技能 / MCP 的 agent 客户端均可使用。每个技能一个文件夹，内含 SKILL.md 与配套脚本。</p>
      <div class="badges">
        <span class="badge">{total} 个技能</span>
        <span class="badge">{len(cats)} 个分类</span>
        <span class="badge">复制示例提示词即可使用</span>
      </div>
    </header>
    {''.join(cards)}
    {''.join(sections)}
    <footer>由 scripts/build_docs.py 自动生成 · 数据来源为各技能目录的 SKILL.md 与 EXAMPLES.md</footer>
  </div>
</div>
<script>{JS}</script>
</body>
</html>
"""


def main():
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()
    skills = load_skills()
    (DOCS_DIR / "index.html").write_text(build_html(skills), encoding="utf-8")
    print(f"已生成 {DOCS_DIR / 'index.html'}（{len(skills)} 个技能）")


if __name__ == "__main__":
    main()
