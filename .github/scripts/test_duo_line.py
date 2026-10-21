"""duo_line.py（iPhone Duo 一句）的逐 byte 副本核對＋行為。正本在 00_GrowthEngine aso/duo/（sync_duo_copies.py 複製）。"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
RECORD = REPO / "_engine/aso/duo/duo_copies.json"
sys.path.insert(0, str(HERE))
import duo_line as D  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_root():
    env = os.environ.get("GROWTH_ENGINE_ROOT", "").strip()
    for root in ([Path(env).expanduser()] if env else []) + [REPO.parent / "00_GrowthEngine",
                                                              Path.home() / "00_GrowthEngine"]:
        if (root / "aso" / "duo" / "duo_line.py").is_file():
            return root
    return None


class DuoCopyTest(unittest.TestCase):
    def test_copies_match_their_recorded_hashes(self):
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], "duo-copies/v1")
        self.assertIn(".github/scripts/duo_line.py", record["files"])
        for dst, meta in record["files"].items():
            self.assertEqual(sha(REPO / dst), meta["sha256"], f"{dst} 和正本 {meta['source']} 不一致（不要手改，重跑 sync）")

    def test_copies_match_the_source_checkout_when_present(self):
        root = source_root()
        if root is None:
            self.skipTest("沒有 00_GrowthEngine checkout（雜湊核對仍由上一個測試做）")
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        stale = [dst for dst, meta in record["files"].items() if sha(REPO / dst) != sha(root / meta["source"])]
        self.assertEqual(stale, [], "副本落後正本：python3 aso/duo/sync_duo_copies.py 後 commit")

    def test_reads_the_copied_list_and_lines(self):
        os.environ.pop("DUO_DATA_ROOT", None)
        D.reset()
        by, _all, lines = D._state()
        self.assertGreater(len({a["app_id"] for a in by.values()}), 0)
        self.assertIn("en-US", lines)

    def test_line_rules(self):
        D.reset()
        by, _all, lines = D._state()
        app = next(iter(by.values()))
        live = lambda _id: app["live_version"]
        self.assertEqual(D.line(app["app_id"], "en-US", live), lines["en-US"])
        self.assertEqual(D.line(app["app_id"], "en-US", lambda _id: "0.0.0-not-live"), "")
        self.assertEqual(D.line("1", "en-US", live), "")                  # 不在清單
        self.assertEqual(D.line(app["app_id"], "sw", live), "")           # 沒有句子
        body = "x" * (500 - len(lines["en-US"]) - 1)
        self.assertEqual(D.append(body, app["app_id"], "en-US", 500, lookup=live), body)   # 超長不加
        self.assertEqual(D.append("Hi", app["app_id"], "en-US", 500, lookup=live), "Hi\n\n" + lines["en-US"])



os.environ.setdefault("POST_QA_OFFLINE", "1")
from unittest import mock  # noqa: E402

import clip_posts as C  # noqa: E402
import telegram_post as T  # noqa: E402
import threads_post as TP  # noqa: E402

LINE = "Got an iPhone Duo? The app now fills the whole inner screen, folded or open."
MOCHI = "6785004775"


def pool_item(text="My to-do list used to stress me out more than the tasks did. Now it is cute."):
    return {"app": MOCHI, "url": f"https://apps.apple.com/app/id{MOCHI}", "lang": "en-US", "text": text,
            "app_key": "mochi"}


def clip_item():
    return {"app": "mochi", "locale": "en", "url": "https://files.catbox.moe/x.mp4", "hook": "Too many tasks?",
            "store_url": f"https://apps.apple.com/us/app/id{MOCHI}?pt=118326163&ct=h7_mochi_en&mt=8",
            "name": "Mochi", "search": "mochi", "compliance": {}}


class DuoOutletTest(unittest.TestCase):
    """Threads / Telegram / clip captions: the line after the main text, only when it fits, never a URL on Threads
    or Instagram, links untouched."""

    def setUp(self):
        self.calls = []

        def line(app, lang, lookup=None):
            self.calls.append((D.app_key(app), lang))
            return LINE if D.app_key(app) in (MOCHI, "mochi") and str(lang).startswith("en") else ""

        patcher = mock.patch.object(D, "line", side_effect=line)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_threads_body_carries_the_line_and_no_url(self):
        body = TP.compose_body(pool_item())
        self.assertIn(f"Now it is cute.\n\n{LINE}\n\n", body)
        self.assertNotIn("http", body)
        self.assertLessEqual(len(body), TP.MAX_POST_CHARS)

    def test_threads_no_line_when_too_long_short_other_app_or_error(self):
        long = "x" * (TP.MAX_POST_CHARS - 60)
        self.assertNotIn("iPhone Duo", TP.compose_body(pool_item(long)))                 # would pass 500
        self.assertEqual(TP.with_duo("Short text", MOCHI, "en-US"), "Short text")        # < 40: rerun lookup
        self.assertEqual(TP.with_duo("y" * 60, "1", "en-US"), "y" * 60)                  # not claimable
        self.assertEqual(TP.with_duo("y" * 60, MOCHI, "ja"), "y" * 60)                   # no line in that language
        with mock.patch.object(D, "append", side_effect=RuntimeError("boom")):
            self.assertEqual(TP.with_duo("y" * 60, MOCHI, "en-US"), "y" * 60)

    def test_telegram_line_before_the_links_and_old_texts_still_count_as_sent(self):
        item = pool_item()
        text = T.compose_text(item)
        self.assertLess(text.index(LINE), text.index("https://apps.apple.com/app/id"))
        self.assertEqual(T.download_link_problems(item, text), [])
        self.assertIn(T._digest(T.compose_text(item, duo=False)), T._sent_digests(item))
        self.assertIn(T._digest(text), T._sent_digests(item))

    def test_telegram_caption_limit_with_a_picture(self):
        item = dict(pool_item("z" * 700), image_url="https://example.com/a.jpg")
        with mock.patch.object(T, "item_image_url", return_value="https://example.com/a.jpg"):
            base = len(T.compose_text(item, duo=False))
            if base + len(LINE) + 2 > T.TG_CAPTION_MAX:
                self.assertNotIn("iPhone Duo", T.compose_text(item))
            item = dict(item, text="z" * (T.TG_CAPTION_MAX - (base - 700) - len(LINE) - 1))
            self.assertNotIn("iPhone Duo", T.compose_text(item))                          # one char over
        self.assertIn(LINE, T.compose_text(dict(item, image_url=None)))                    # text post: 4096

    def test_clip_captions(self):
        clip = clip_item()
        ig = C.caption(clip, "instagram")
        self.assertIn(LINE, ig)
        self.assertNotIn("http", ig)                                                      # Instagram: no URL
        tg = C.caption(clip, "telegram")
        self.assertLess(tg.index(LINE), tg.index("https://apps.apple.com/"))
        self.assertIn(LINE, C.caption(clip, "threads"))
        self.assertNotIn("iPhone Duo", C.caption(clip, "bluesky"))                        # its sender adds it
        self.assertNotIn("iPhone Duo", C.caption(dict(clip, locale="ja"), "instagram"))

    def test_clip_caption_too_long_keeps_the_plain_one(self):
        clip = clip_item()
        plain = C._caption(clip, "threads")
        with mock.patch.dict(C.post_qa.LIMITS, {"threads": len(plain) + len(LINE)}):
            self.assertEqual(C.caption(clip, "threads"), plain)

if __name__ == "__main__":
    unittest.main()
