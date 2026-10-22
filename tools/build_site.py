#!/usr/bin/env python3
"""Rebuild the shared pages from the prototype folders. No AI.

Writes index.html (the site's front page) and prototypes/IDEAS.md (every prototype with what it
gives you), both from each prototypes/<name>/README.md. It runs on main after a merge, so a night's
pull request only ever touches its own folder and two pull requests never collide.

README conventions it reads: the first "# " line is the title; a "**You get:**" line is the
promise; an optional "**Status:**" line (idea, live, retired).
Usage: python3 tools/build_site.py
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/guillearria/phoenix"


def card(readme):
    text = readme.read_text(encoding="utf-8")
    title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), readme.parent.name)
    promise = re.search(r"^\*\*You get:\*\*\s*(.+)$", text, re.M)
    status = re.search(r"^\*\*Status:\*\*\s*([A-Za-z]+)", text, re.M)
    has_page = (readme.parent / "index.html").exists()
    return {"name": readme.parent.name, "title": title,
            "promise": promise.group(1).strip() if promise else "",
            "status": status.group(1).lower() if status else ("live" if has_page else "idea"),
            "page": has_page}


def cards(prototypes_dir):
    return [card(r) for r in sorted(prototypes_dir.glob("*/README.md"))]


def index_html(all_cards):
    live = [c for c in all_cards if c["page"] and c["status"] != "retired"]
    items = "\n".join(
        f'      <li><a href="prototypes/{html.escape(c["name"])}/">{html.escape(c["title"])}</a>'
        + (f'<br><span>{html.escape(c["promise"])}</span>' if c["promise"] else "") + "</li>"
        for c in live) or "      <li>None yet. The first one is built at night.</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Phoenix prototypes</title>
  <meta name="description" content="Small free tools for real problems people describe in public, built at night by Phoenix.">
  <style>
    :root {{ color-scheme: light dark; --bg: #f6f7f9; --fg: #1b1f2a; --muted: #5a6273; --link: #2f4fbf; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg: #10131c; --fg: #e8eaf1; --muted: #a2a9ba; --link: #a9b8ff; }} }}
    body {{ margin: 0; background: var(--bg); color: var(--fg); font: 18px/1.55 system-ui, sans-serif; padding: 40px 16px; }}
    main {{ max-width: 640px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    p, li {{ max-width: 60ch; }}
    ul {{ padding-left: 1.1em; }}
    li {{ margin-bottom: 14px; }}
    li span {{ color: var(--muted); font-size: 16px; }}
    a {{ color: var(--link); }}
    footer {{ margin-top: 40px; color: var(--muted); font-size: 15px; }}
  </style>
</head>
<body>
  <main>
    <h1>Phoenix prototypes</h1>
    <p>Small free tools for real problems that people describe in public. Each one works offline,
    collects nothing, and has a pass mark set before anyone sees it.</p>
    <ul>
{items}
    </ul>
    <p><a href="{REPO}/blob/main/prototypes/IDEAS.md">Every problem and its evidence</a></p>
    <footer>A personal project by <a href="https://github.com/guillearria">Guillermo Arria-Devoe</a> ·
    <a href="{REPO}">Source on GitHub</a></footer>
  </main>
</body>
</html>
"""


def ideas_md(all_cards):
    lines = ["# Ideas", "",
             "Every problem Phoenix has worked on, rebuilt from each prototype's README after a merge.", ""]
    for c in all_cards:
        lines.append(f"- [{c['title']}]({c['name']}/README.md), {c['status']}"
                     + (f": {c['promise']}" if c["promise"] else ""))
    if not all_cards:
        lines.append("None yet.")
    return "\n".join(lines) + "\n"


def main():
    all_cards = cards(ROOT / "prototypes")
    (ROOT / "index.html").write_text(index_html(all_cards), encoding="utf-8")
    (ROOT / "prototypes" / "IDEAS.md").write_text(ideas_md(all_cards), encoding="utf-8")
    print(f"site: {len(all_cards)} prototype(s), {sum(c['page'] for c in all_cards)} with a page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
