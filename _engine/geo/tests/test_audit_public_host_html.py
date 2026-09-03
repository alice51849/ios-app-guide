import sys
import tempfile
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import audit_public_host_html as audit  # noqa: E402
from site_config import ORIGIN_SITE, PUBLIC_SITE  # noqa: E402


class AuditPublicHostHtmlTest(unittest.TestCase):
    def test_flags_canonical_hreflang_and_microformat_on_origin(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "en-US" / "answers").mkdir(parents=True)
            (root / "en-US" / "answers" / "a.html").write_text(
                f'<link rel="canonical" href="{ORIGIN_SITE}/en-US/answers/a.html">'
                f'<link rel="alternate" hreflang="de-DE" href="{ORIGIN_SITE}/de-DE/answers/a.html">'
                f'<data class="u-url u-uid" value="{ORIGIN_SITE}/en-US/answers/a.html"></data>',
                encoding="utf-8",
            )
            (root / "ok.html").write_text(
                f'<link rel="canonical" href="{PUBLIC_SITE}/ok.html">'
                f'<a href="{ORIGIN_SITE}/data/verified-ios-app-finder-catalog.json">data</a>',
                encoding="utf-8",
            )
            (root / "_engine").mkdir()
            (root / "_engine" / "x.html").write_text(
                f'<link rel="canonical" href="{ORIGIN_SITE}/x.html">', encoding="utf-8"
            )
            offenders = audit.audit(root)
        self.assertEqual(["en-US/answers/a.html"], sorted(offenders))
        self.assertEqual(3, len(offenders["en-US/answers/a.html"]))

    def test_plain_links_to_origin_data_are_not_identity(self):
        text = f'<a href="{ORIGIN_SITE}/feed.xml">feed</a>'
        self.assertEqual([], audit.origin_identities(text, ORIGIN_SITE))


if __name__ == "__main__":
    unittest.main()
