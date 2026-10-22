import tempfile
import unittest
from pathlib import Path

import gate
import morning
import night_ship
import build_site as phoenix_site


class GateTest(unittest.TestCase):
    def check(self, path, text):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
            return gate.check([path], d)

    def test_clean_prototype_passes(self):
        page = '<!doctype html><form><label for="n">Name</label><input id="n"></form><script src="https://cdnjs.cloudflare.com/x.js"></script>'
        self.assertEqual(self.check("prototypes/tip/index.html", page), [])

    def test_only_one_folder_and_the_nights_log(self):
        self.assertEqual(self.check("brain/nights/2026-10-23-4.md", "# Night"), [])
        for shared in ("README.md", ".github/workflows/x.yml", "prototypes/IDEAS.md",
                       "index.html", "brain/LOG.md", "brain/NIGHT.md"):
            self.assertTrue(self.check(shared, "x"), shared)

    def test_network_and_tracking_blocked(self):
        for code in ['fetch("/x")', "new XMLHttpRequest()", "navigator.sendBeacon(u)",
                     '<form action="https://evil.example">', '<iframe src="x">',
                     '<script src="https://evil.test/a.js"></script>', "document.cookie"]:
            self.assertTrue(self.check("prototypes/x/index.html", code), code)

    def test_personal_data_and_secrets_blocked(self):
        self.assertTrue(self.check("prototypes/x/README.md", "write to someone@gmail.com"))
        self.assertEqual(self.check("prototypes/x/README.md", "like ana@example.com"), [])
        self.assertTrue(self.check("prototypes/x/README.md", "call 305-555-0123"))
        self.assertTrue(self.check("prototypes/x/README.md", "key ghp_" + "a" * 30))


class ShipTest(unittest.TestCase):
    LOG = "# Night 2026-10-23\n- Did: Built a tip splitter.\n- Why: People asked ([source](https://x)).\n"

    def test_log_lines_and_did_line(self):
        entry = night_ship.log_lines(self.LOG)
        self.assertTrue(entry.startswith("- Did:"))
        self.assertNotIn("# Night", entry)
        self.assertEqual(night_ship.did_line(entry), "Built a tip splitter.")
        self.assertEqual(night_ship.did_line(""), "night work")

    def test_people_total(self):
        state = "| [A](x) | 0 | 0 | 0 | 0 | 0 | 2 |\n| [B](y) | 1 | 0 | 0 | 0 | 0 | 3 |\n| Project | x |"
        self.assertEqual(night_ship.people_total(state), 5)

    def test_prototype_names_and_links(self):
        files = ["prototypes/fair/index.html", "prototypes/fair/script.js",
                 "brain/nights/2026-10-23-4.md", "prototypes/tip/README.md"]
        self.assertEqual(night_ship.prototype_names(files), ["fair", "tip"])
        self.assertEqual(night_ship.preview_links("abc", ["tip"]),
                         ["https://raw.githack.com/guillearria/phoenix/abc/prototypes/tip/index.html"])


class SiteTest(unittest.TestCase):
    def test_cards_index_and_ideas(self):
        with tempfile.TemporaryDirectory() as d:
            live = Path(d) / "tip"
            live.mkdir()
            (live / "README.md").write_text("# Split <the> bill\n**You get:** each share in one tap.\n**Status:** live\n")
            (live / "index.html").write_text("<p>x</p>")
            idea = Path(d) / "later"
            idea.mkdir()
            (idea / "README.md").write_text("# Later\n")
            cards = phoenix_site.cards(Path(d))
            self.assertEqual([(c["name"], c["status"], c["page"]) for c in cards],
                             [("later", "idea", False), ("tip", "live", True)])
            page = phoenix_site.index_html(cards)
            self.assertIn('href="prototypes/tip/"', page)
            self.assertIn("Split &lt;the&gt; bill", page)
            self.assertIn("each share in one tap.", page)
            self.assertNotIn("prototypes/later/", page)
            self.assertIn("[Later](later/README.md), idea", phoenix_site.ideas_md(cards))
            self.assertIn("None yet", phoenix_site.index_html([]))


class MorningTest(unittest.TestCase):
    def test_no_token_says_how_to_fix(self):
        text = morning.compose({"TOKEN_OK": "false", "RUN_URL": "u"}, "")
        self.assertTrue(text.startswith("@guillearria "))
        self.assertIn("gh secret set CLAUDE_CODE_OAUTH_TOKEN", text)

    def test_rested_lists_what_waits(self):
        text = morning.compose({"SKIPPED": "true", "TOKEN_OK": "true", "WAITING_LIST": "- #2 A\n- #3 B"}, "")
        self.assertIn("Rested.", text)
        self.assertIn("#3 B", text)

    def test_report_and_early_stop(self):
        text = morning.compose({"TOKEN_OK": "true", "WORK_EXIT": "124"}, "Morning report.\n\n**Ready for you.**")
        self.assertIn("Ready for you", text)
        self.assertIn("exit 124", text)

    def test_missing_report_is_a_failure(self):
        self.assertIn("failed before it could report", morning.compose({"TOKEN_OK": "true"}, ""))


if __name__ == "__main__":
    unittest.main()
