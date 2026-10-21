import unittest
import urllib.error
from datetime import datetime, timezone

import listen

OWNER = "guillearria"
U = lambda login, kind="User": {"login": login, "type": kind, "html_url": f"https://github.com/{login}"}


def fake_get(path, accept=None):
    if path.endswith("/swing-lab"):
        return {"stargazers_count": 3, "subscribers_count": 1, "forks_count": 0}
    if path.endswith("/issues?state=all&per_page=100"):
        return [
            {"user": U("stranger"), "created_at": "2026-09-03T15:33:47Z", "html_url": "https://x/issues/1", "state": "closed"},
            {"user": U(OWNER), "created_at": "2026-10-01T00:00:00Z", "html_url": "https://x/pull/2", "state": "open", "pull_request": {}},
            {"user": U("claude[bot]", "Bot"), "created_at": "2026-10-02T00:00:00Z", "html_url": "https://x/issues/3", "state": "open"},
        ]
    if path.endswith("/issues/comments?per_page=100"):
        return [{"user": U("reader"), "created_at": "2026-10-19T08:00:00Z", "html_url": "https://x/issues/1#c1"}]
    if path.endswith("/pulls/comments?per_page=100"):
        return []
    if "/stargazers" in path:
        return [{"user": U(OWNER), "starred_at": "2026-08-01T00:00:00Z"},
                {"user": U("fan"), "starred_at": "2026-10-20T10:00:00Z"}]
    if "/forks" in path:
        return []
    if "/subscribers" in path:
        return [U(OWNER)]
    if path.endswith("/traffic/views"):
        return {"views": [{"timestamp": "2026-10-19T00:00:00Z", "count": 5, "uniques": 2},
                          {"timestamp": "2026-10-21T00:00:00Z", "count": 1, "uniques": 1}]}
    raise AssertionError(path)


class ListenTest(unittest.TestCase):
    def test_people_exclude_owner_and_bots(self):
        rows = listen.collect(OWNER, "swing-lab", "2026-10-21", fake_get)[0]
        people = sorted((r["kind"], r["who"]) for r in rows if r["kind"] in listen.PEOPLE)
        self.assertEqual(people, [("comment", "reader"), ("issue", "stranger"), ("star", "fan")])

    def test_daily_counts(self):
        rows = listen.collect(OWNER, "swing-lab", "2026-10-21", fake_get)[0]
        counts = {r["kind"]: r["value"] for r in rows if r["kind"] in listen.DAILY}
        self.assertEqual(counts, {"stars": "1", "watching": "0", "forks": "0", "open_issues": "1", "open_prs": "1"})

    def test_visits_skip_today(self):
        rows = listen.collect_visits(OWNER, "swing-lab", "2026-10-21", fake_get)
        self.assertEqual({(r["date"], r["kind"], r["value"]) for r in rows},
                         {("2026-10-19", "views", "5"), ("2026-10-19", "visitors", "2")})

    def test_merge_is_idempotent_and_same_day_replaces(self):
        first = listen.collect(OWNER, "swing-lab", "2026-10-21", fake_get)[0]
        merged = listen.merge(first, first)
        self.assertEqual(len(merged), len(first))
        bumped = [dict(r, value="9") if r["kind"] == "stars" else r for r in first]
        again = listen.merge(merged, bumped)
        self.assertEqual([r["value"] for r in again if r["kind"] == "stars"], ["9"])

    def test_render_fits_one_screen_and_says_when_visits_are_missing(self):
        cfg = {"owner": OWNER, "projects": [{"name": "Swing Lab", "repo": "swing-lab"}]}
        rows = listen.merge([], listen.collect(OWNER, "swing-lab", "2026-10-21", fake_get)[0])
        text = listen.render(rows, cfg, datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc), False)
        self.assertIn("Not counted yet", text)
        self.assertIn("a star by fan", text)
        self.assertLess(len(text.splitlines()), 40)

    def test_render_empty_ledger(self):
        cfg = {"owner": OWNER, "projects": [{"name": "Phoenix", "repo": "phoenix"}]}
        text = listen.render([], cfg, datetime(2026, 10, 21, tzinfo=timezone.utc), False)
        self.assertIn("Nobody yet.", text)


class StarFallbackTest(unittest.TestCase):
    def test_undated_stars_are_dated_when_first_seen_and_keep_that_date(self):
        def get(path, accept=None):
            if "/stargazers" in path:
                if accept == "application/vnd.github.star+json":
                    raise urllib.error.URLError("401 on stargazers: Requires authentication")
                return [U("fan")]
            return fake_get(path, accept)
        day1, readable = listen.collect(OWNER, "swing-lab", "2026-10-21", get)
        self.assertTrue(readable)
        star = [r for r in day1 if r["kind"] == "star"]
        self.assertEqual([(r["date"], r["who"]) for r in star], [("2026-10-21", "fan")])
        day2 = listen.collect(OWNER, "swing-lab", "2026-10-22", get)[0]
        merged = listen.merge(listen.merge([], day1), day2)
        self.assertEqual([r["date"] for r in merged if r["kind"] == "star"], ["2026-10-21"])


class NoNamesTest(unittest.TestCase):
    def test_public_totals_stand_in_when_lists_are_refused(self):
        def get(path, accept=None):
            if any(x in path for x in ("/stargazers", "/forks", "/subscribers")):
                raise urllib.error.URLError("401 Requires authentication")
            return fake_get(path, accept)
        rows, readable = listen.collect(OWNER, "swing-lab", "2026-10-21", get)
        self.assertFalse(readable)
        counts = {r["kind"]: r["value"] for r in rows if r["kind"] in listen.DAILY}
        self.assertEqual((counts["stars"], counts["watching"], counts["forks"]), ("3", "1", "0"))
        cfg = {"owner": OWNER, "projects": [{"name": "Swing Lab", "repo": "swing-lab"}]}
        text = listen.render(listen.merge([], rows), cfg, datetime(2026, 10, 21, tzinfo=timezone.utc), False, readable)
        self.assertIn("can include the owner", text)


if __name__ == "__main__":
    unittest.main()
