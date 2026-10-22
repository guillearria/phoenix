#!/usr/bin/env python3
"""After the night's work: run the gate, put the work on its own branch, open a pull request for
the owner with a preview link, and write the morning report. No AI.

Nothing goes live here. The owner merges the pull request, or closes it. A night touches only its
own prototype folder and its own log file, so pull requests never collide; the shared pages are
rebuilt on main by tools/build_site.py after a merge.
Usage: python3 tools/night_ship.py [--dry-run]     (--dry-run commits and pushes nothing)
Env: NIGHT_LOG (the night's log file), REPORT_PATH (default /tmp/phoenix-report.md).
"""
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


def log_lines(text):
    """The '- Did:', '- Why:', '- Look:' and '- Needs the owner:' lines of a night's log."""
    return "\n".join(l for l in text.splitlines() if l.startswith("- ")).strip()


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


def prototype_names(paths):
    """The prototype folders a night touched, e.g. prototypes/tip/index.html -> tip."""
    return sorted({Path(p).parts[1] for p in paths
                   if len(Path(p).parts) >= 3 and Path(p).parts[0] == "prototypes"})


def preview_links(sha, names):
    """Links that show a branch's pages before merging. The free preview service asks for one
    extra click ("Open the page") and serves the files exactly as they are on GitHub."""
    return [f"https://raw.githack.com/guillearria/phoenix/{sha}/prototypes/{n}/index.html" for n in names]


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
    log_path = ROOT / (os.environ.get("NIGHT_LOG") or f"brain/nights/{day}.md")
    entry = log_lines(log_path.read_text(encoding="utf-8")) if log_path.exists() else ""
    state = (ROOT / "STATE.md").read_text(encoding="utf-8") if (ROOT / "STATE.md").exists() else ""
    people = f"People activity on the public projects, last 7 days: {people_total(state)}."
    run = os.environ.get("GITHUB_RUN_NUMBER") or datetime.now(timezone.utc).strftime("%H%M")
    branch = f"night/{day}-{run}"
    compare = f"{REPO}/compare/main...{branch}"
    if not files:
        body, outcome = ["**Quiet night.** Nothing changed and no log was written."], "quiet"
    else:
        problems = gate.check(files, ROOT)
        if not dry:
            git("checkout", "-b", branch)
            git("add", "-A")
            git("commit", "-m", f"night {day}: {did_line(entry)}")
            git("push", "-u", "origin", branch)
        sha = git("rev-parse", "HEAD").strip()
        preview_lines = [f"Preview before merging: {u}" for u in preview_links(sha, prototype_names(files))]
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
    report += [entry if entry else "The night wrote no log."] + ["", people]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"night_ship: {outcome}, {len(files)} file(s) changed" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
