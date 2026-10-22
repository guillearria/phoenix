#!/usr/bin/env python3
"""After the night's work: run the gate, put the work on its own branch, open a pull request
for the owner, rebuild the site's front page, and write the morning report. No AI.

Nothing goes live here. The owner merges the pull request, or ignores it.
Usage: python3 tools/night_ship.py [--dry-run]     (--dry-run commits and pushes nothing)
The report goes to $REPORT_PATH (default /tmp/phoenix-report.md) for tools/morning.py.
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/guillearria/phoenix"
REPORT = Path(os.environ.get("REPORT_PATH") or "/tmp/phoenix-report.md")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def changed():
    return [line[3:].split(" -> ")[-1].strip('"')
            for line in git("status", "--porcelain", "-uall").splitlines()]


def log_entry(text, day):
    m = re.search(rf"^## {re.escape(day)}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def did_line(entry):
    m = re.search(r"^- Did:\s*(.+)$", entry, re.M)
    return m.group(1).strip()[:120] if m else "night work"


def people_total(state_text):
    total = 0
    for line in state_text.splitlines():
        if line.startswith("| ["):
            try:
                total += int(line.strip().strip("|").split("|")[-1])
            except ValueError:
                pass
    return total


def site_index(prototypes_dir):
    items = []
    for readme in sorted(prototypes_dir.glob("*/README.md")):
        title = next((l[2:].strip() for l in readme.read_text(encoding="utf-8").splitlines()
                      if l.startswith("# ")), readme.parent.name)
        items.append(f'      <li><a href="prototypes/{html.escape(readme.parent.name)}/">{html.escape(title)}</a></li>')
    listing = "\n".join(items) if items else "      <li>None yet. The first one is built at night.</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Phoenix prototypes</title>
  <meta name="description" content="Small prototypes for real problems people describe in public, built at night by Phoenix.">
  <style>
    :root {{ color-scheme: light dark; --bg: #f6f7f9; --fg: #1b1f2a; --muted: #5a6273; --link: #2f4fbf; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg: #10131c; --fg: #e8eaf1; --muted: #a2a9ba; --link: #a9b8ff; }} }}
    body {{ margin: 0; background: var(--bg); color: var(--fg); font: 18px/1.55 system-ui, sans-serif; padding: 40px 16px; }}
    main {{ max-width: 640px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    p, li {{ max-width: 60ch; }}
    a {{ color: var(--link); }}
    footer {{ margin-top: 40px; color: var(--muted); font-size: 15px; }}
  </style>
</head>
<body>
  <main>
    <h1>Phoenix prototypes</h1>
    <p>Small tests of ideas for real problems that people describe in public. Each one works offline,
    collects nothing, and has a pass mark set before anyone sees it.</p>
    <ul>
{listing}
    </ul>
    <p><a href="https://github.com/guillearria/phoenix/blob/main/prototypes/IDEAS.md">The problems and their evidence</a></p>
    <footer>A personal project by <a href="https://github.com/guillearria">Guillermo Arria-Devoe</a> ·
    <a href="https://github.com/guillearria/phoenix">Source on GitHub</a></footer>
  </main>
</body>
</html>
"""


def prototype_names(paths):
    """The prototype folders a night touched, e.g. prototypes/fair-rota/index.html -> fair-rota."""
    return sorted({Path(p).parts[1] for p in paths
                   if len(Path(p).parts) >= 3 and Path(p).parts[0] == "prototypes"})


def preview_links(sha, names):
    """Links that show a branch's pages before merging. The free preview service asks for one
    extra click ("Open the page") and serves the files exactly as they are on GitHub."""
    return [f"https://raw.githack.com/guillearria/phoenix/{sha}/prototypes/{n}/index.html" for n in names]


def write_site():
    (ROOT / "index.html").write_text(site_index(ROOT / "prototypes"), encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")


def open_pull_request(branch, title, body):
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not (repo and token):
        return None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls", method="POST",
        data=json.dumps({"title": title, "head": branch, "base": "main", "body": body}).encode(),
        headers={"Accept": "application/vnd.github+json", "User-Agent": "phoenix-night",
                 "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))["html_url"]
    except Exception as e:  # a refused pull request still leaves the branch and a link
        print(f"night_ship: could not open a pull request ({e})", file=sys.stderr)
        return None


def main():
    dry = "--dry-run" in sys.argv
    day = datetime.now(timezone.utc).date().isoformat()
    files = changed()
    entry = log_entry((ROOT / "brain/LOG.md").read_text(encoding="utf-8"), day)
    state = (ROOT / "STATE.md").read_text(encoding="utf-8") if (ROOT / "STATE.md").exists() else ""
    people = f"People activity on the public projects, last 7 days: {people_total(state)}."
    branch = f"night/{day}-{os.environ.get('GITHUB_RUN_NUMBER') or datetime.now(timezone.utc).strftime('%H%M')}"
    compare = f"{REPO}/compare/main...{branch}"
    if not files:
        body, outcome = ["**Quiet night.** Nothing changed and no log entry was written."], "quiet"
    else:
        problems = gate.check(files, ROOT)
        write_site()
        if not dry:
            git("checkout", "-b", branch)
            git("add", "-A")
            git("commit", "-m", f"night {day}: {did_line(entry)}")
            git("push", "-u", "origin", branch)
        sha = git("rev-parse", "HEAD").strip()
        previews = preview_links(sha, prototype_names(files))
        preview_lines = [f"Preview before merging: {u}" for u in previews]
        if problems:
            body = [f"**Held.** Tonight's work failed the safety check, so there is nothing to merge. "
                    f"It stays on its branch for reference: {compare}"] + [f"- {p}" for p in problems]
            outcome = "held"
        else:
            pr = None if dry else open_pull_request(
                branch, f"Night {day}: {did_line(entry)}",
                "\n\n".join([entry] + preview_lines +
                              ["Passed the safety check. Merge to publish it; close to drop it."]))
            body = [f"**Ready for you.** Merge to publish, or close to drop it: {pr or compare}"] + preview_lines
            outcome = "ready"
    report = [f"Morning report, {day}.", ""] + body + [""]
    report += [entry if entry else "The night wrote no log entry."] + ["", people]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"night_ship: {outcome}, {len(files)} file(s) changed" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
