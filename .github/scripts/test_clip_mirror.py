#!/usr/bin/env python3
"""Tests for clip_mirror.py (no network)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_mirror as M  # noqa: E402


def clip(app, cid):
    return {"app": app, "locale": "en", "url": f"https://files.catbox.moe/{cid}.mp4"}


DATA = {
    "clips": {
        "zeta/en": clip("zeta", "zzzzzz"),
        "alpha/en": clip("alpha", "aaaaaa"),
        "mochidonestamp/en": clip("mochidonestamp", "dddddd"),
        "mochi_b/en": clip("mochi_b", "bbbbbb"),
        "mochi/en": clip("mochi", "mmmmmm"),
        "late/en": clip("late", "llllll"),
        "soon/en": clip("soon", "ssssss"),
        "dup/en": clip("dup", "aaaaaa"),
    },
    "schedule": [
        {"date": "2026-10-27", "slot": 1, "channel": "telegram", "clip": "late/en"},
        {"date": "2026-10-23", "slot": 9, "channel": "telegram", "clip": "soon/en"},
        {"date": "2026-10-22", "slot": 1, "channel": "instagram", "clip": "mochi/en"},
    ],
}


class OrderTest(unittest.TestCase):
    def test_mochi_first_then_the_scheduled_week_then_the_rest(self):
        ids = [i for i, _k, _u in M.ordered(DATA)]
        self.assertEqual(ids[:3], ["mmmmmm", "bbbbbb", "ssssss"])  # mochi, mochi_b, then the 10-22..10-26 schedule
        self.assertEqual(ids[3:], ["aaaaaa", "llllll", "dddddd", "zzzzzz"])  # the rest by key

    def test_mochidonestamp_is_not_mochi(self):
        self.assertFalse(M.is_mochi("mochidonestamp"))
        self.assertTrue(M.is_mochi("mochi") and M.is_mochi("mochi_halloween"))

    def test_each_catbox_id_once_and_non_catbox_urls_skipped(self):
        d = {"clips": {"a/en": clip("a", "aaaaaa"), "b/en": clip("b", "aaaaaa"),
                       "c/en": {"app": "c", "url": "https://example.com/x.mp4"}}, "schedule": []}
        self.assertEqual([i for i, _k, _u in M.ordered(d)], ["aaaaaa"])


class RewriteTest(unittest.TestCase):
    def test_only_mirrored_ids_change_and_formatting_is_kept(self):
        text = '{\n  "u": "https://files.catbox.moe/aaaaaa.mp4",\n "v": "https://files.catbox.moe/bbbbbb.mp4"\n}\n'
        new, n = M.rewrite_text(text, {"aaaaaa"})
        self.assertEqual(n, 1)
        self.assertIn(f'"{M.NEW_BASE}aaaaaa.mp4"', new)
        self.assertIn('"https://files.catbox.moe/bbbbbb.mp4"', new)
        self.assertEqual(M.rewrite_text(new, {"aaaaaa"})[1], 0)  # second pass is a no-op

    def test_cmd_rewrite_reads_results_and_updates_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            clips = Path(d) / "clips.json"
            clips.write_text(json.dumps({"clips": {"a/en": clip("a", "aaaaaa"), "b/en": clip("b", "bbbbbb")}}))
            res = Path(d) / "r.json"
            res.write_text(json.dumps({"aaaaaa": {"ok": True}, "bbbbbb": {"ok": False, "err": "x"}}))
            with mock.patch.object(M, "CLIPS", clips):
                M.main(["rewrite", "--results", str(res)])
            out = json.loads(clips.read_text())["clips"]
            self.assertEqual(out["a/en"]["url"], M.NEW_BASE + "aaaaaa.mp4")
            self.assertEqual(out["b/en"]["url"], "https://files.catbox.moe/bbbbbb.mp4")


class CheckTest(unittest.TestCase):
    def test_a_clip_must_be_an_mp4_of_sensible_size(self):
        with tempfile.TemporaryDirectory() as d:
            good = Path(d) / "g.mp4"
            good.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40_000)
            html = Path(d) / "h.mp4"
            html.write_bytes(b"<html>" + b" " * 40_000)
            tiny = Path(d) / "t.mp4"
            tiny.write_bytes(b"\x00\x00\x00\x18ftypmp42")
            self.assertEqual(M._check(good, None), "")
            self.assertEqual(M._check(good, 40_012), "")
            self.assertIn("content-length", M._check(good, 99))
            self.assertIn("not an mp4", M._check(html, None))
            self.assertIn("too small", M._check(tiny, None))


if __name__ == "__main__":
    unittest.main()
