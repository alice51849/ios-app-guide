#!/usr/bin/env python3
"""store_link_preflight.py: the push preflight names the pages geo-daily's link normalizer would refuse."""
import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import store_link_preflight as preflight  # noqa: E402

ENGINE = HERE.parent.parent / "_engine" / "geo"
WORKFLOWS = HERE.parent / "workflows"
GOOD = "https://apps.apple.com/au/app/id6829184924?pt=118326163&ct=sqb1118n_foldparty_au_catmini&mt=8"
# The link that stopped geo-daily 2026-11-19 00:07-02:39Z: a 33-character ct token (limit 30).
TOO_LONG = "https://apps.apple.com/au/app/id6829184924?pt=118326163&ct=sqb1118n_foldparty_au_catminigame&mt=8"


def page(url: str) -> str:
    return f'<!doctype html><html><body><a href="{url.replace("&", "&amp;")}">Download</a></body></html>\n'


class StoreLinkPreflightTests(unittest.TestCase):
    def run_on(self, files: dict[str, str]):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, text in files.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(text, encoding="utf-8")
            before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = preflight.main(["--pages", str(root), "--engine", str(ENGINE)])
            after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
        self.assertEqual(before, after, "the preflight is read-only")
        return code, out.getvalue()

    def test_valid_links_pass(self):
        code, out = self.run_on({"apps/foldparty/q-cat.en-AU.html": page(GOOD), "index.html": "<p>no link</p>"})
        self.assertEqual(0, code, out)
        self.assertIn("scanned=2, refused=0", out)

    def test_the_over_long_campaign_token_is_named_and_the_run_is_red(self):
        code, out = self.run_on({"apps/foldparty/q-cat.en-AU.html": page(TOO_LONG), "ok.html": page(GOOD)})
        self.assertEqual(1, code)
        self.assertIn("::error file=apps/foldparty/q-cat.en-AU.html::", out)
        self.assertIn("sqb1118n_foldparty_au_catminigame", out)
        self.assertNotIn("file=ok.html", out)
        self.assertIn("refused=1", out)

    def test_it_agrees_with_the_normalizer_geo_daily_runs(self):
        sys.path.insert(0, str(ENGINE))
        import normalize_app_store_links as normalizer
        with self.assertRaises(ValueError):
            normalizer.normalize_source(page(TOO_LONG))
        normalizer.normalize_source(page(GOOD))

    def test_a_long_list_is_capped(self):
        files = {f"p{i:02d}.html": page(TOO_LONG) for i in range(preflight.MAX_REPORTED + 3)}
        code, out = self.run_on(files)
        self.assertEqual(1, code)
        self.assertEqual(preflight.MAX_REPORTED, out.count("::error file="))
        self.assertIn("3 more page(s) refused", out)

    def test_pages_workflow_runs_it_on_pushes_only_and_geo_daily_still_normalizes(self):
        deploy = (WORKFLOWS / "pages.yml").read_text(encoding="utf-8")
        step = deploy.index("python3 .github/scripts/store_link_preflight.py --pages . --engine _engine/geo")
        head = deploy.rfind("- name:", 0, step)
        self.assertIn("if: github.event_name == 'push'", deploy[head:step])  # a paired release is never held by it
        self.assertLess(deploy.index("Install canonical generator dependencies"), step)
        self.assertLess(step, deploy.index("rm -rf _engine"))
        self.assertIn("python3 normalize_app_store_links.py", (WORKFLOWS / "geo-daily.yml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
