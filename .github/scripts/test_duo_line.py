"""duo_line.py（iPhone Duo 一句）的逐 byte 副本核對＋行為。正本在 00_GrowthEngine aso/duo/（sync_duo_copies.py 複製）。

11-24 改：正本 duo_line 加閘——claim_lines.json 頂層 status 以「暫停」開頭（11-21 統籌第 53 項）就一律不附句。
真實副本資料的測試改成「依副本狀態」斷言；附句規則（live／非 live／不在清單／無語系／超長）改用暫存目錄假資料照舊驗。
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
RECORD = REPO / "_engine/aso/duo/duo_copies.json"
CLAIMS = REPO / "_engine/aso/duo/claim_lines.json"
sys.path.insert(0, str(HERE))
import duo_line as D  # noqa: E402

EN = "Got an iPhone Duo? The app now fills the whole inner screen, folded or open."


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_root():
    env = os.environ.get("GROWTH_ENGINE_ROOT", "").strip()
    for root in ([Path(env).expanduser()] if env else []) + [REPO.parent / "00_GrowthEngine",
                                                              Path.home() / "00_GrowthEngine"]:
        if (root / "aso" / "duo" / "duo_line.py").is_file():
            return root
    return None


def copied_paused():
    doc = json.loads(CLAIMS.read_text(encoding="utf-8"))
    return str(doc.get("status") or "").strip().startswith("暫停")


def fake_root(tmp, status=None):
    """可宣稱 1 款（111111111 / alpha，線上 1.2）；en-US 句已複審 PASS。duo_list.py 用副本。"""
    tmp = Path(tmp)
    (tmp / "aso" / "duo").mkdir(parents=True)
    (tmp / "ops" / "company").mkdir(parents=True)
    (tmp / "geo").mkdir()
    shutil.copyfile(REPO / "_engine/aso/duo/duo_list.py", tmp / "aso" / "duo" / "duo_list.py")
    (tmp / "geo" / "live_app_manifest.json").write_text(json.dumps({"apps": {
        "alpha": {"app_id": "111111111", "name": "Alpha"}}}))
    (tmp / "ops" / "company" / "duo_verified.json").write_text(json.dumps({
        "verified": [{"key": "A", "asc_app_id": "111111111", "verdict": "pass", "pass_version": "1.2",
                      "pass_build": "5", "live_version": "1.2", "live_build": "5", "via": "direct"}],
        "needs_duo_run": [], "not_live": []}))
    claims = {"social_line": {"en-US": EN}}
    if status is not None:
        claims["status"] = status
    (tmp / "aso" / "duo" / "claim_lines.json").write_text(json.dumps(claims))
    (tmp / "aso" / "duo" / "review_second_model.json").write_text(json.dumps({"items": [
        {"field": "social_line", "locale": "en-US", "verdict": "PASS"}]}))
    return tmp


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
        by, all_lines, lines = D._state()
        self.assertGreater(len({a["app_id"] for a in by.values()}), 0)
        self.assertIn("en-US", all_lines)          # 已發過比對用的全部句子照常讀得到
        if copied_paused():
            self.assertEqual(lines, {})            # 暫停引用中：可附的句表為空
            for app in list(by.values())[:5]:
                self.assertEqual(D.line(app["app_id"], "en-US", lambda _id, v=app["live_version"]: v), "")
        else:
            self.assertIn("en-US", lines)
            app = next(iter(by.values()))       # 非暫停：真實副本照原測試驗一次會附句
            self.assertEqual(D.line(app["app_id"], "en-US", lambda _id: app["live_version"]), lines["en-US"])


class DuoLineRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = os.environ.get("DUO_DATA_ROOT")

    def tearDown(self):
        if self.old is None:
            os.environ.pop("DUO_DATA_ROOT", None)
        else:
            os.environ["DUO_DATA_ROOT"] = self.old
        D.reset()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def use(self, status=None):
        os.environ["DUO_DATA_ROOT"] = str(fake_root(Path(self.tmp) / "r", status))
        D.reset()

    def test_line_rules(self):
        self.use()
        live = lambda _id: "1.2"
        self.assertEqual(D.line("111111111", "en-US", live), EN)
        self.assertEqual(D.line("111111111", "en-US", lambda _id: "0.0.0-not-live"), "")   # 線上版本對不上
        self.assertEqual(D.line("1", "en-US", live), "")                                  # 不在清單
        self.assertEqual(D.line("111111111", "sw", live), "")                             # 沒有句子
        body = "x" * (500 - len(EN) - 1)
        self.assertEqual(D.append(body, "111111111", "en-US", 500, lookup=live), body)    # 超長不加
        self.assertEqual(D.append("Hi", "111111111", "en-US", 500, lookup=live), "Hi\n\n" + EN)

    def test_paused_status_claims_nothing(self):
        self.use(status="暫停引用（測試）：實機驗證前不引用")
        live = lambda _id: "1.2"
        self.assertEqual(D._state()[2], {})
        self.assertEqual(D.line("111111111", "en-US", live), "")
        self.assertEqual(D.append("Hi", "111111111", "en-US", 500, lookup=live), "Hi")
        self.assertIn(EN, D.known_lines("en-US"))


os.environ.setdefault("POST_QA_OFFLINE", "1")
from unittest import mock  # noqa: E402

import clip_posts as C  # noqa: E402
import telegram_post as T  # noqa: E402
import threads_post as TP  # noqa: E402

LINE = "Got an iPhone Duo? The app now fills the whole inner screen, folded or open."
MOCHI = "6785004775"


def pool_item(text="My to-do list used to stress me out more than the tasks did. Now it is cute, and I check it."):
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
        self.assertIn(f"and I check it.\n\n{LINE}\n\n", body)
        self.assertNotIn("http", body)
        self.assertLessEqual(len(body), TP.MAX_POST_CHARS)

    def test_threads_no_line_when_too_long_short_other_app_or_error(self):
        long = "x" * (TP.MAX_POST_CHARS - 60)
        self.assertNotIn("iPhone Duo", TP.compose_body(pool_item(long)))                 # would pass 500
        self.assertEqual(TP.with_duo("Short text", MOCHI, "en-US"), "Short text")        # < 80: rerun lookup
        self.assertEqual(TP.with_duo("s" * 79, MOCHI, "en-US"), "s" * 79)
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
        with mock.patch.object(D, "line", return_value=""):                               # line not due any more
            self.assertIn(T._digest(text), T._sent_digests(item))                          # still counts as sent

    def test_threads_rerun_without_the_line_still_finds_the_post(self):
        posted = TP.compose_body(pool_item())
        self.assertIn(LINE, posted)
        rows = [{"id": "p1", "text": posted, "timestamp": "2026-10-21T03:00:00+0000"}]

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"data": rows}).encode()

        with mock.patch.object(D, "line", return_value=""):
            again = TP.compose_body(pool_item())
        self.assertNotIn("iPhone Duo", again)
        import datetime as _dt
        self.assertEqual(TP.find_own_post("t", again, _dt.date(2026, 10, 21), opener=lambda *a, **k: Resp()), "p1")

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
