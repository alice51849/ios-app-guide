import sys
import tempfile
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import restricted_copy_pages as gate  # noqa: E402


class RestrictedCopyPagesTest(unittest.TestCase):
    def _site(self, root, pages):
        for rel, body in pages.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"<html><head><style>.a{{}}</style></head><body>{body}</body></html>", encoding="utf-8")

    def test_kumo_pages_with_banned_words_fail_and_others_are_not_read(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self._site(root, {
                "en-US/kumo.html": "<p>Works with Ozempic. Start your free trial for $4.99.</p>",
                "ja/kumo.html": "<p>確実に痩せる</p>",
                "apps/kumo/support.html": "<p>建議劑量</p>",
                "en-US/mochi.html": "<p>Free trial, only $4.99, guaranteed!</p>",
                "en-US/index.html": "<p>Kumo and others: free trial $4.99</p>",
                "_engine/kumo.html": "<p>Ozempic</p>",
            })
            hits = gate.audit(root)
            files = {rel for rel, _c, _h in hits}
            self.assertEqual({"en-US/kumo.html", "ja/kumo.html", "apps/kumo/support.html"}, files)
            self.assertEqual({"drug brand", "free trial", "price"},
                             {c for rel, c, _h in hits if rel == "en-US/kumo.html"})
            self.assertEqual(1, gate.main(["--site-root", str(root)]))

    def test_glp1_disclaimers_and_scripts_pass(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self._site(root, {
                "en-US/kumo.html": "<script>var p='$4.99 free trial Ozempic';</script><h1>Kumo: GLP-1 tracker</h1>"
                                   "<p>Kumo does not give medical advice, diagnose, or calculate doses.</p>",
                "zh-Hant/kumo.html": "<p>GLP-1 打針紀錄。Kumo 不提供醫療建議、不做診斷、不計算劑量。</p>",
            })
            self.assertEqual([], gate.audit(root))
            self.assertEqual(0, gate.main(["--site-root", str(root)]))


if __name__ == "__main__":
    unittest.main()
