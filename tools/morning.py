#!/usr/bin/env python3
"""Post the morning report as one comment on the "Morning report" issue, mentioning the owner so
GitHub notifies him. No AI. Every night run posts exactly one comment; silence means broken.

Reads $REPORT_PATH when the night got that far. Otherwise it says why it stopped, using
SKIPPED, WAITING_LIST, TOKEN_OK, WORK_EXIT and RUN_URL from the workflow. Usage: python3 tools/morning.py [--dry-run]
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OWNER = "guillearria"
TITLE = "Morning report"
API = "https://api.github.com"


def compose(env, report_text):
    day = datetime.now(timezone.utc).date().isoformat()
    if env.get("SKIPPED") == "true":
        waiting = env.get("WAITING_LIST", "").strip()
        body = (f"Morning report, {day}.\n\n**Rested.** Prototypes are already waiting for you, so the "
                "night shift did not build another. Merge or close them and it starts again tonight."
                + (f"\n\n{waiting}" if waiting else ""))
    elif env.get("TOKEN_OK") != "true":
        body = (f"Morning report, {day}.\n\n**Phoenix did not run.** The login token is not saved yet. "
                "One-time fix: in a terminal run `claude setup-token`, then "
                "`gh secret set CLAUDE_CODE_OAUTH_TOKEN -R guillearria/phoenix` and paste the token.")
    elif report_text:
        body = report_text.strip()
        if env.get("WORK_EXIT", "0") not in ("", "0"):
            body += (f"\n\nThe night stopped early (exit {env['WORK_EXIT']}). Whatever it finished went "
                     "through the same check.")
    else:
        body = f"Morning report, {day}.\n\n**The night run failed before it could report.**"
    return f"@{OWNER} {body}\n\nRun: {env.get('RUN_URL', '')}\n"


def api(path, token, method="GET", data=None):
    req = urllib.request.Request(
        API + path, method=method, data=json.dumps(data).encode() if data else None,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "phoenix-morning",
                 "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8") or "null")


def main():
    env = dict(os.environ)
    path = Path(env.get("REPORT_PATH") or "/tmp/phoenix-report.md")
    text = compose(env, path.read_text(encoding="utf-8") if path.exists() else "")
    if "--dry-run" in sys.argv:
        print(text)
        return 0
    repo, token = env["GITHUB_REPOSITORY"], env["GITHUB_TOKEN"]
    issues = api(f"/repos/{repo}/issues?state=open&per_page=100", token)
    issue = next((i for i in issues if i["title"] == TITLE and "pull_request" not in i), None)
    if issue is None:
        issue = api(f"/repos/{repo}/issues", token, "POST", {
            "title": TITLE,
            "body": "Phoenix posts one comment here every morning: what it built overnight, what waits "
                    "for you, and what people did. Leave this issue open."})
    api(f"/repos/{repo}/issues/{issue['number']}/comments", token, "POST", {"body": text})
    print(f"morning: posted to issue #{issue['number']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
