#!/usr/bin/env python3
"""The night shift's gate. No AI. Checks every file the night changed before anything ships.

A prototype must be one offline page that collects nothing. So: changes only inside one
prototype folder or the night's own log file, only a few file types, small files, no code that talks to other
sites, no secrets, no email addresses or phone numbers. Returns a list of plain-language problems.
"""
import re
from pathlib import Path

ALLOWED_EXT = {".html", ".css", ".js", ".md", ".svg", ".json", ".txt"}
MAX_BYTES = 300_000
MAX_FILES = 30
CODE_EXT = {".html", ".js", ".css", ".svg"}
BLOCKED_CODE = [
    (r"<form[^>]*\baction\s*=", "a form that sends data somewhere"),
    (r"\bfetch\s*\(", "a network request (fetch)"),
    (r"XMLHttpRequest", "a network request (XMLHttpRequest)"),
    (r"sendBeacon", "a tracking beacon"),
    (r"new\s+WebSocket", "a live connection to a server"),
    (r"<iframe", "an embedded page from elsewhere"),
    (r"navigator\.geolocation", "a location request"),
    (r"document\.cookie", "cookies"),
    (r"<script[^>]+src\s*=\s*[\"']?(?:https?:)?//(?!cdnjs\.cloudflare\.com/)", "a script loaded from another site"),
    (r"<link[^>]+href\s*=\s*[\"']?(?:https?:)?//(?!fonts\.googleapis\.com/|fonts\.gstatic\.com/|cdnjs\.cloudflare\.com/)[^>]*>",
     "a file loaded from another site"),
    (r"@import\s+url\(\s*[\"']?(?:https?:)?//(?!fonts\.googleapis\.com/)", "a stylesheet loaded from another site"),
    (r"<img[^>]+src\s*=\s*[\"']?(?:https?:)?//", "an image loaded from another site"),
]
SECRETS = [r"sk-[A-Za-z0-9_-]{20,}", r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}",
           r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY"]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"@(?:example\.(?:com|org|net)|users\.noreply\.github\.com)$", re.I)
PHONE = re.compile(r"(?<![\d.])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\d.])")


def allowed_path(path):
    """A night may write files inside prototypes/<name>/ and its own brain/nights/<file>.md.
    Shared files (the front page, the ideas list) are rebuilt on main and never edited here."""
    p = Path(path)
    if len(p.parts) == 3 and p.parts[:2] == ("brain", "nights") and p.suffix == ".md":
        return True
    return len(p.parts) >= 3 and p.parts[0] == "prototypes" and p.suffix.lower() in ALLOWED_EXT


def check(paths, root="."):
    root = Path(root)
    problems = []
    if len(paths) > MAX_FILES:
        problems.append(f"too many files changed ({len(paths)}; the limit is {MAX_FILES})")
    for path in sorted(paths):
        if not allowed_path(path):
            problems.append(f"{path}: the night may only change files inside prototypes/<name>/ and its own log in brain/nights/")
            continue
        f = root / path
        if not f.exists():
            continue  # a deletion inside prototypes/ is allowed
        if f.stat().st_size > MAX_BYTES:
            problems.append(f"{path}: larger than {MAX_BYTES // 1000} KB")
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if f.suffix.lower() in CODE_EXT:
            for rx, what in BLOCKED_CODE:
                if re.search(rx, text, re.I):
                    problems.append(f"{path}: contains {what}")
        for rx in SECRETS:
            if re.search(rx, text):
                problems.append(f"{path}: contains something that looks like a secret key")
        for m in EMAIL.finditer(text):
            if not EMAIL_OK.search(m.group(0)):
                problems.append(f"{path}: contains an email address")
                break
        if PHONE.search(text):
            problems.append(f"{path}: contains a phone number")
    return problems
