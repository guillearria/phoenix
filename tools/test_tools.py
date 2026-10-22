import tempfile
import unittest
from pathlib import Path

import gate
import morning
import night_ship


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

    def test_only_prototypes_and_the_log(self):
        self.assertTrue(self.check("README.md", "hi"))
        self.assertTrue(self.check(".github/workflows/x.yml", "on: push"))
        self.assertEqual(self.check("brain/LOG.md", "## 2026-10-22"), [])

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
    LOG = "# Night log\n\n## 2026-10-22\n- Did: Built a tip splitter.\n- Why: People asked ([source](https://x)).\n\n## 2026-10-23\n- Did: Next.\n"

    def test_log_entry_and_did_line(self):
        entry = night_ship.log_entry(self.LOG, "2026-10-22")
        self.assertIn("tip splitter", entry)
        self.assertNotIn("Next.", entry)
        self.assertEqual(night_ship.did_line(entry), "Built a tip splitter.")
        self.assertEqual(night_ship.log_entry(self.LOG, "2026-10-30"), "")

    def test_people_total(self):
        state = "| [A](x) | 0 | 0 | 0 | 0 | 0 | 2 |\n| [B](y) | 1 | 0 | 0 | 0 | 0 | 3 |\n| Project | x |"
        self.assertEqual(night_ship.people_total(state), 5)

    def test_site_index_lists_and_escapes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tip"
            p.mkdir()
            (p / "README.md").write_text("# Split <tips> fairly\n")
            page = night_ship.site_index(Path(d))
            self.assertIn('href="prototypes/tip/"', page)
            self.assertIn("Split &lt;tips&gt; fairly", page)
            self.assertIn("None yet", night_ship.site_index(Path(d) / "empty"))


class PreviewTest(unittest.TestCase):
    def test_prototype_names_and_links(self):
        files = ["prototypes/fair-rota/index.html", "prototypes/fair-rota/script.js",
                 "prototypes/IDEAS.md", "brain/LOG.md", "prototypes/tip/README.md"]
        self.assertEqual(night_ship.prototype_names(files), ["fair-rota", "tip"])
        self.assertEqual(night_ship.preview_links("abc", ["tip"]),
                         ["https://raw.githack.com/guillearria/phoenix/abc/prototypes/tip/index.html"])


class MorningTest(unittest.TestCase):
    def test_no_token_says_how_to_fix(self):
        text = morning.compose({"TOKEN_OK": "false", "RUN_URL": "u"}, "")
        self.assertTrue(text.startswith("@guillearria "))
        self.assertIn("gh secret set CLAUDE_CODE_OAUTH_TOKEN", text)

    def test_report_and_early_stop(self):
        text = morning.compose({"TOKEN_OK": "true", "WORK_EXIT": "124"}, "Morning report.\n\n**Ready for you.**")
        self.assertIn("Ready for you", text)
        self.assertIn("exit 124", text)

    def test_missing_report_is_a_failure(self):
        self.assertIn("failed before it could report", morning.compose({"TOKEN_OK": "true"}, ""))


if __name__ == "__main__":
    unittest.main()
