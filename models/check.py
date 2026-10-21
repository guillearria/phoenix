#!/usr/bin/env python3
"""Check the model table against OpenRouter's public price list. No AI, no key.

Reads models.json (the picks, chosen by hand from Arena's leaderboards) and writes MODELS.md:
each pick with today's price, or why it has none. Exits 1 if a pick that should be on
OpenRouter is missing, so a stale table turns the run red.
Usage: python3 models/check.py [saved-openrouter-models.json]
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST_URL = "https://openrouter.ai/api/v1/models"
ROLES = [("best", "Best"), ("best_value", "Best value"), ("best_open", "Best open model"),
         ("fallback", "Fallback")]


def load_list(saved=None):
    if saved:
        return json.loads(Path(saved).read_text())["data"]
    req = urllib.request.Request(LIST_URL, headers={"User-Agent": "phoenix-models"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))["data"]


def price(entry):
    p = entry.get("pricing") or {}
    return float(p.get("prompt") or 0) * 1e6, float(p.get("completion") or 0) * 1e6


def render(table, listed, now):
    by_id = {m["id"]: m for m in listed}
    out = ["# Models", "",
           f"Prices checked {now:%Y-%m-%d} against [OpenRouter's public list]({LIST_URL}), in US dollars "
           "per million tokens, input / output. The picks come from "
           "[Arena's leaderboards](https://arena.ai/leaderboard), read by hand because Arena blocks "
           "scripts; they live in [models.json](models.json).", "",
           "| Job | Pick | Model | Price today |", "|---|---|---|---|"]
    missing = []
    for job in table["jobs"]:
        first = True
        for role, label in ROLES:
            pick = job.get(role)
            if not pick:
                continue
            model = pick["model"]
            if "/" not in model:
                cell = pick.get("via", "Outside OpenRouter")
            elif model in by_id:
                pi, po = price(by_id[model])
                cell = f"${pi:.2f} / ${po:.2f}"
                batch = by_id.get(model + ":batch")
                if batch:
                    bi, bo = price(batch)
                    cell += f" (night batch ${bi:.2f} / ${bo:.2f})"
            else:
                cell = "Missing from OpenRouter today"
                missing.append(model)
            out.append(f"| {job['plain'] if first else ''} | {label} | `{model}` | {cell} |")
            first = False
    out += ["", f"{len(listed)} models listed on OpenRouter today."]
    return "\n".join(out) + "\n", missing


def main():
    table = json.loads((ROOT / "models.json").read_text())
    listed = load_list(sys.argv[1] if len(sys.argv) > 1 else None)
    text, missing = render(table, listed, datetime.now(timezone.utc))
    (ROOT / "MODELS.md").write_text(text)
    print(f"models: {len(table['jobs'])} jobs checked, {len(missing)} missing")
    for m in missing:
        print(f"PROBLEM: {m} is not on OpenRouter's list today; update models.json", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
