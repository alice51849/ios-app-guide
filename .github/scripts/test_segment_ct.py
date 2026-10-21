import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import segment_ct as M  # noqa: E402

# The same vectors in both repos (00_GrowthEngine lib/test_mochi_segment.py, ios-app-guide test_segment_ct.py).
DAYS = {
    "2026-10-21": "exam", "2026-10-24": "exam", "2026-10-25": "adhd", "2026-10-26": "adhd",  # Sat, Sun, Mon
    "2026-11-15": "adhd", "2026-11-16": "adhd", "2026-11-17": "exam", "2026-11-18": "host",
    "2026-11-24": "host", "2026-11-23": "soft", "2026-11-25": "exam", "2026-11-26": "host",
    "2026-12-18": "kids", "2026-12-19": "host", "2026-12-26": "reset", "2027-01-03": "reset", "2027-01-08": "reset",
    "2027-01-09": "reset", "2027-01-10": "adhd", "2027-01-18": "soft",
}


class SegmentTableTest(unittest.TestCase):
    def test_table_is_well_formed(self):
        cfg = M.load()
        self.assertEqual(M.SCHEMA, cfg["schema"])
        self.assertEqual("6785004775", cfg["app_id"])
        self.assertEqual({"reset", "host", "adhd", "kids", "soft", "exam"}, set(cfg["segments"]))
        self.assertTrue(set(cfg["exits"]) <= set(cfg["channels"]))
        names = set(cfg["segments"])
        windows = cfg["windows"]
        for prev, cur in zip(windows, windows[1:]):
            self.assertLess(prev["to"], cur["from"], "windows must not overlap")
            self.assertEqual(dt.date.fromisoformat(prev["to"]) + dt.timedelta(days=1),
                             dt.date.fromisoformat(cur["from"]), "no gap between windows")
        for rule in windows + [cfg["default"]]:
            self.assertTrue(rule["rotate"] and set(rule["rotate"]) <= names, rule)
            self.assertTrue(set((rule.get("weekdays") or {}).values()) <= names, rule)
            self.assertTrue(set(rule.get("weekdays") or {}) <= set(M.WEEKDAYS), rule)
        self.assertTrue(set(cfg["dates"].values()) <= names)

    def test_timeline(self):
        for day, seg in DAYS.items():
            self.assertEqual(seg, M.segment_for(dt.date.fromisoformat(day)), day)

    def test_every_day_of_a_year_has_a_segment(self):
        start = dt.date(2026, 10, 21)
        for n in range(400):
            self.assertIn(M.segment_for(start + dt.timedelta(days=n)), M.load()["segments"])

    def test_token_only_for_mochi_on_its_exits(self):
        day = dt.date(2026, 10, 21)
        for ch in ("ig", "tg", "bs", "yt"):
            self.assertEqual(f"ln_mochi_exam_br_{ch}_1021", M.segment_token("6785004775", ch, day, country="br"))
        self.assertEqual("ln_mochi_adhd_us_yt_1025",
                         M.segment_token("6785004775", "yt", dt.date(2026, 10, 25), country="US"))
        self.assertEqual("ln_mochi_reset_jp_tg_0101",
                         M.segment_token("6785004775", "tg", dt.date(2027, 1, 1), country="jp"))
        for token in (M.segment_token("6785004775", "bs", dt.date(2026, 12, 18), country=cc) for cc in ("sa", "tw")):
            self.assertLessEqual(len(token), 40)   # App Store ct limit (agent/ct_codes.TOKEN_RE)
        self.assertIsNone(M.segment_token("6785004775", "th", day, country="us"))   # Threads keeps th_mochi_*
        self.assertIsNone(M.segment_token("6785004775", "igc", day, country="us"))
        self.assertIsNone(M.segment_token("6802423998", "ig", day, country="us"))   # any other app keeps its token
        self.assertIsNone(M.segment_token("", "ig", day, country="us"))
        for cc in (None, "", "usa", "u1"):   # no target storefront: the caller keeps its usual token
            self.assertIsNone(M.segment_token("6785004775", "ig", day, country=cc))

    def test_unreadable_table_keeps_the_usual_token(self):
        self.assertEqual({}, M.load("/nonexistent/table.json"))
        self.assertIsNone(M.segment_token("6785004775", "ig", dt.date(2026, 10, 21), cfg={}, country="us"))
        self.assertIsNone(M.segment_for(dt.date(2026, 10, 21), cfg={}))
        bad = dict(M.load(), token="ln_mochi_{segment}_{channel}_x_y")
        self.assertIsNone(M.segment_token("6785004775", "ig", dt.date(2026, 10, 21), cfg=bad, country="us"))
        short = dict(M.load(), token="ln_mochi_{segment}_{channel}")   # the retired short form never leaves
        self.assertIsNone(M.segment_token("6785004775", "ig", dt.date(2026, 10, 21), cfg=short, country="us"))


if __name__ == "__main__":
    unittest.main()
