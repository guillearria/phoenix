#!/usr/bin/env python3
"""Listen: record what people do on the public projects. No AI.

Reads projects.json, asks GitHub's public API, and updates two files:
  ledger/signals.csv  one row per fact: date, project, kind, value, who, url
  STATE.md            one screen, rebuilt from the whole ledger every run

Rules
- "People" means anyone except the owner and bots.
- A fact about a person (an issue, a comment, a star...) is written once, keyed by its link,
  and keeps the date it was first written with.
- Daily counts get one row per project per day; a second run the same day replaces it.
- READ_TOKEN, if set, is used for every read: a read-only token whose access includes
  repository traffic. Without it the workflow's own token reads the public data and visits
  are skipped; STATE.md says so.
- If any read fails, the files are still written from what was read, then the script exits 1
  so the run shows red. A broken run is never silent.
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "ledger" / "signals.csv"
STATE = ROOT / "STATE.md"
FIELDS = ["date", "project", "kind", "value", "who", "url"]
DAILY = ["stars", "watching", "forks", "open_issues", "open_prs"]
PEOPLE = ["issue", "pull_request", "comment", "review_comment", "star", "fork"]
VISITS = ["views", "visitors"]
LABEL = {"issue": "an issue", "pull_request": "a pull request", "comment": "a comment",
         "review_comment": "a review comment", "star": "a star", "fork": "a fork"}
API = "https://api.github.com"


def _get(url, token, accept):
    req = urllib.request.Request(url, headers={
        "Accept": accept, "User-Agent": "phoenix-listen", "X-GitHub-Api-Version": "2022-11-28"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")), resp.headers.get("Link") or ""


def fetch(path, token=None, accept="application/vnd.github+json"):
    """GET a GitHub API path, following every page. Returns a dict or a list.

    The workflow's own token is refused on some lists of other repos (stargazers, for one)
    with "Resource not accessible by integration". That data is public, so the same request
    is retried once without a token."""
    url, out = API + path, None
    while url:
        try:
            try:
                body, link = _get(url, token, accept)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                if token and e.code == 403 and "not accessible by integration" in detail:
                    body, link = _get(url, None, accept)
                else:
                    raise urllib.error.URLError(f"{e.code} on {path}: {detail[:200]}") from e
        except urllib.error.HTTPError as e:
            raise urllib.error.URLError(f"{e.code} on {path} (asked without a token): "
                                        f"{e.read().decode('utf-8', 'replace')[:200]}") from e
        if not isinstance(body, list):
            return body
        out = (out or []) + body
        url = next((part.split(";")[0].strip(" <>") for part in link.split(",")
                    if 'rel="next"' in part), None)
    return out or []


def is_person(user, owner):
    if not user:
        return False
    login = user.get("login") or ""
    return (login.lower() != owner.lower() and user.get("type") != "Bot"
            and not login.endswith("[bot]"))


def row(day, project, kind, value, who="", url=""):
    return {"date": day, "project": project, "kind": kind, "value": str(value),
            "who": who, "url": url}


def collect(owner, repo, today, get):
    """Everything readable about one repo. `get(path, accept=None)` returns parsed JSON."""
    base = f"/repos/{owner}/{repo}"
    items = get(f"{base}/issues?state=all&per_page=100")
    comments = get(f"{base}/issues/comments?per_page=100")
    reviews = get(f"{base}/pulls/comments?per_page=100")
    try:
        stars = [(s.get("user"), s["starred_at"][:10]) for s in
                 get(f"{base}/stargazers?per_page=100", accept="application/vnd.github.star+json")]
    except urllib.error.URLError:
        # Star dates need a user token (READ_TOKEN). Who starred is public, so without the
        # token a star is dated by the day this job first sees it: within a day, run daily.
        stars = [(u, today) for u in get(f"{base}/stargazers?per_page=100")]
    forks = get(f"{base}/forks?per_page=100")
    watchers = get(f"{base}/subscribers?per_page=100")
    rows = []
    for it in items:
        if is_person(it.get("user"), owner):
            kind = "pull_request" if "pull_request" in it else "issue"
            rows.append(row(it["created_at"][:10], repo, kind, 1, it["user"]["login"], it["html_url"]))
    for kind, found in (("comment", comments), ("review_comment", reviews)):
        for c in found:
            if is_person(c.get("user"), owner):
                rows.append(row(c["created_at"][:10], repo, kind, 1, c["user"]["login"], c["html_url"]))
    for user, day in stars:
        if is_person(user, owner):
            rows.append(row(day, repo, "star", 1, user["login"], user["html_url"]))
    for f in forks:
        if is_person(f.get("owner"), owner):
            rows.append(row(f["created_at"][:10], repo, "fork", 1, f["owner"]["login"], f["html_url"]))
    counts = {
        "stars": sum(is_person(user, owner) for user, _ in stars),
        "watching": sum(is_person(w, owner) for w in watchers),
        "forks": sum(is_person(f.get("owner"), owner) for f in forks),
        "open_issues": sum(it.get("state") == "open" and "pull_request" not in it for it in items),
        "open_prs": sum(it.get("state") == "open" and "pull_request" in it for it in items),
    }
    rows += [row(today, repo, k, int(counts[k])) for k in DAILY]
    return rows


def collect_visits(owner, repo, today, get):
    """Finished days of GitHub page views. Today's partial count is left for tomorrow."""
    views = get(f"/repos/{owner}/{repo}/traffic/views")
    rows = []
    for d in views.get("views", []):
        day = d["timestamp"][:10]
        if day < today:
            rows.append(row(day, repo, "views", d["count"]))
            rows.append(row(day, repo, "visitors", d["uniques"]))
    return rows


def key(r):
    if r["kind"] in PEOPLE:
        return (r["project"], r["kind"], r["url"])
    return (r["date"], r["project"], r["kind"])


def merge(old, new):
    """Counts and visits: the newest read wins. A fact about a person keeps its first row."""
    out = {key(r): r for r in old}
    for r in new:
        if r["kind"] in PEOPLE and key(r) in out:
            continue
        out[key(r)] = r
    return sorted(out.values(), key=lambda r: (r["date"], r["project"], r["kind"], r["url"], r["who"]))


def read_ledger():
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="") as fh:
        return list(csv.DictReader(fh))


def write_ledger(rows):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def render(rows, cfg, now, visits_counted):
    owner, projects = cfg["owner"], cfg["projects"]
    name = {p["repo"]: p["name"] for p in projects}
    today = now.date()
    week_ago = (today - timedelta(days=7)).isoformat()
    latest = {}
    for r in rows:
        if r["kind"] in DAILY:
            k = (r["project"], r["kind"])
            if k not in latest or r["date"] >= latest[k][0]:
                latest[k] = (r["date"], r["value"])
    people = [r for r in rows if r["kind"] in PEOPLE]
    out = ["# State", "",
           f"Updated {now:%Y-%m-%d %H:%M} UTC by the daily listen job. Every number comes from "
           "[the ledger](ledger/signals.csv). People means anyone except the owner and bots.", "",
           "| Project | Stars | Watching | Forks | Open issues | Open pull requests | People activity, 7 days |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for p in projects:
        repo = p["repo"]
        val = lambda k: latest.get((repo, k), ("", "0"))[1]
        recent = sum(1 for r in people if r["project"] == repo and r["date"] > week_ago)
        out.append(f"| [{p['name']}](https://github.com/{owner}/{repo}) | {val('stars')} | "
                   f"{val('watching')} | {val('forks')} | {val('open_issues')} | {val('open_prs')} | {recent} |")
    out += ["", "## Visits on GitHub, last 7 days", ""]
    visit_rows = [r for r in rows if r["kind"] in VISITS and r["date"] > week_ago]
    if not visits_counted and not visit_rows:
        out.append("Not counted yet. Counting needs a token that can read repository traffic.")
    else:
        out += ["| Project | Views | Visitors |", "|---|---:|---:|"]
        for p in projects:
            v = sum(int(r["value"]) for r in visit_rows if r["project"] == p["repo"] and r["kind"] == "views")
            u = sum(int(r["value"]) for r in visit_rows if r["project"] == p["repo"] and r["kind"] == "visitors")
            out.append(f"| {p['name']} | {v} | {u} |")
        out += ["", "Visitors are summed per day, so one person on two days counts twice."]
    out += ["", "## Latest from people", ""]
    last = sorted(people, key=lambda r: (r["date"], r["url"]), reverse=True)[:5]
    if not last:
        out.append("Nobody yet.")
    for r in last:
        out.append(f"- {r['date']}: {name.get(r['project'], r['project'])}, {LABEL[r['kind']]} "
                   f"by {r['who']}. [Link]({r['url']})")
    return "\n".join(out) + "\n"


def main():
    cfg = json.loads((ROOT / "projects.json").read_text())
    owner = cfg["owner"]
    traffic_token = os.environ.get("READ_TOKEN") or None
    token = traffic_token or os.environ.get("GITHUB_TOKEN") or None
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    get = lambda path, accept="application/vnd.github+json": fetch(path, token, accept)
    get_traffic = lambda path, accept="application/vnd.github+json": fetch(path, traffic_token, accept)
    new, problems, visits_counted = [], [], bool(traffic_token)
    for p in cfg["projects"]:
        try:
            new += collect(owner, p["repo"], today, get)
        except (urllib.error.URLError, KeyError, ValueError) as e:
            problems.append(f"{p['repo']}: could not read GitHub ({e})")
        if traffic_token:
            try:
                new += collect_visits(owner, p["repo"], today, get_traffic)
            except (urllib.error.URLError, KeyError, ValueError) as e:
                visits_counted = False
                problems.append(f"{p['repo']}: could not read visits ({e})")
    rows = merge(read_ledger(), new)
    write_ledger(rows)
    STATE.write_text(render(rows, cfg, now, visits_counted))
    people = sum(1 for r in rows if r["kind"] in PEOPLE)
    print(f"listen: {len(new)} rows read, ledger {len(rows)} rows, {people} from people, "
          f"visits {'counted' if visits_counted else 'not counted'}")
    for msg in problems:
        print(f"PROBLEM: {msg}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
