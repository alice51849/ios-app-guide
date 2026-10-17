#!/usr/bin/env python3
"""Tests for store_shot_cards.py (no network; Pillow needed for the drawing tests)."""
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import countdown_cards as cd  # noqa: E402
import store_shot_cards as S  # noqa: E402
import volume_ramp as R  # noqa: E402


TEXT = {"zh-Hant": ("待辦清單也可以這麼可愛", "每天打勾更開心", "可愛待辦清單"),
        "ja": ("ToDoリストがこんなにかわいい", "毎日チェックが楽しい", "かわいいToDo"),
        "en": ("Your to-do list, but make it cute", "Ticking off feels good", "Cute Checklist")}


def clip(app, locale, **kw):
    lead, benefit, keyline = TEXT.get(locale, TEXT["en"])
    c = {"app": app, "locale": locale, "url": "https://files.catbox.moe/x.mp4",
         "store_url": f"https://apps.apple.com/us/app/id100{len(app)}?pt=118326163&ct=h7_{app}&mt=8",
         "hook": lead, "name": f"{app} name", "search": app, "keyline": keyline,
         "tags": [f"#{app}tag"], "hooks": [{"id": "a", "lead": lead, "benefit": benefit}]}
    c.update(kw)
    return c


def data(*pairs):
    clips = {f"{a}/{l}": clip(a, l) for a, l in pairs}
    schedule = [{"date": "2026-10-17", "slot": 1, "channel": "instagram", "clip": k} for k in clips]
    return {"clips": clips, "schedule": schedule}


STORE_LINK = re.compile(r"https?://(?:apps\.apple\.com|play\.google\.com)/\S+")

FONT = next((f for f in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                         "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if Path(f).exists()), None)


def shot_png(color=(120, 60, 200)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (390, 844), color).save(buf, "PNG")
    return buf.getvalue()


class PickTest(unittest.TestCase):
    def test_planner_order_slot_locale_and_cooldowns(self):
        d = data(("mochi", "zh-Hant"), ("mochi", "en"), ("cyca", "ja"), ("cyca", "en"), ("mochi_b", "zh-Hant"))
        d["clips"]["mochi_b/zh-Hant"]["base"] = "mochi"
        day = dt.date(2026, 10, 20)
        self.assertEqual(S.pick(d, [], day, 7)[0], "feed/mochi/zh-Hant")   # Asia slot: zh-Hant first
        self.assertEqual(S.pick(d, [], day, 19)[0], "feed/mochi/en")
        week = [{"channel": S.CHANNEL, "clip": "feed/mochi/en", "posted_at": "2026-10-18T19:21:00Z"}]
        self.assertEqual(S.pick(d, week, day, 7)[0], "feed/cyca/ja")       # mochi featured this week: next app
        old = [{"channel": S.CHANNEL, "clip": "feed/mochi/zh-Hant", "posted_at": "2026-09-01T07:21:00Z"}]
        self.assertEqual(S.pick(d, old, day, 7)[0], "feed/cyca/ja")        # the pair within 60 days: skipped
        very_old = [{"channel": S.CHANNEL, "clip": "feed/mochi/zh-Hant", "posted_at": "2026-06-01T07:21:00Z"}]
        self.assertEqual(S.pick(d, very_old, day, 7)[0], "feed/mochi/zh-Hant")
        self.assertEqual(S.pick({"clips": {}, "schedule": []}, [], day, 7), (None, None))

    def test_card_lines_rotate_problem_benefit_keyline_search(self):
        c = clip("mochi", "zh-Hant")
        v = c["hooks"][0]
        self.assertEqual([S.card_lines(c, v, i) for i in range(4)],
                         ["待辦清單也可以這麼可愛", "每天打勾更開心", "可愛待辦清單", "在 App Store 搜尋「mochi」"])

    def test_shot_urls_use_the_slot_storefront_and_a_large_size(self):
        rec = {"screenshotUrls": [f"https://is1-ssl.mzstatic.com/image/thumb/x/{i}.png/320x480bb.jpg" for i in range(6)]}
        with mock.patch.object(S.post_qa, "store_lookup", return_value=rec) as look:
            urls = S.shot_urls(clip("mochi", "ja"), "ja")
        self.assertEqual(look.call_args[0][1], "jp")
        self.assertEqual(len(urls), S.CARDS_MAX)
        self.assertTrue(all(u.endswith("/" + S.SHOT_SIZE) for u in urls))
        with mock.patch.object(S.post_qa, "store_lookup", return_value=None):
            self.assertEqual(S.shot_urls(clip("mochi", "ja"), "ja"), [])


@unittest.skipIf(FONT is None, "no font to draw with")
class DrawTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for p in (mock.patch.object(cd, "FONT", FONT), mock.patch.object(cd, "FONT_INDEX", {k: 0 for k in cd.FONT_INDEX})):
            p.start()
            self.addCleanup(p.stop)

    def test_make_draws_the_cards_and_a_plan_with_the_search_first_caption(self):
        from PIL import Image
        d = data(("mochi", "zh-Hant"), ("mochi", "en"))
        urls = [f"https://is1-ssl.mzstatic.com/image/thumb/x/{i}.png/320x480bb.jpg" for i in range(3)]
        ramp = {"schema": R.SCHEMA, "stage_days": 3, "hold_days": 7,
                "channels": {"instagram_feed": {"start": "2026-10-17", "stages": [1, 2], "slots": [7, 19]}}}
        with mock.patch.object(S.post_qa, "store_lookup", return_value={"screenshotUrls": urls}), \
                mock.patch.object(S.volume_ramp, "load", return_value=ramp), \
                mock.patch.object(S, "compose", wraps=S.compose) as drawn:
            plan = S.make(self.tmp.name, dt.date(2026, 10, 17), 7, data=d, posts=[], fetcher=lambda u: shot_png())
        self.assertEqual(plan["key"], "feed/mochi/zh-Hant")
        self.assertEqual(plan["cards"], ["01.jpg", "02.jpg", "03.jpg"])
        img = Image.open(Path(self.tmp.name) / "01.jpg")
        self.assertEqual(img.size, (S.W, S.H))
        self.assertIn("待辦清單也可以這麼可愛", plan["caption"])
        self.assertIn("下載連結在個人檔案", plan["caption"])
        # Owner rule 2026-10-17: the caption carries the app's direct App Store link (pt + ct) and no other
        # store link; this app is iOS-only, so no Google Play link. The drawn cards carry no URL at all
        # (a URL on an image is not tappable and reads as spam).
        self.assertEqual(STORE_LINK.findall(plan["caption"]),
                         ["https://apps.apple.com/us/app/id1005?pt=118326163&ct=h7_mochi_ig&mt=8"])
        drawn_text = [t for c in drawn.call_args_list for t in (c.args[1], c.args[2].get("name", ""))]
        self.assertEqual(len(drawn.call_args_list), 3)
        self.assertFalse([t for t in drawn_text if "http" in t or "apps.apple.com" in t])
        self.assertEqual(json.loads((Path(self.tmp.name) / "plan.json").read_text())["key"], plan["key"])
        self.assertEqual(S.qa(plan, online=False), [])
        # The day's allowance used up: nothing is made.
        posted = [{"channel": S.CHANNEL, "clip": "feed/x/en", "posted_at": "2026-10-17T07:21:00Z"}]
        with mock.patch.object(S.volume_ramp, "load", return_value=ramp), mock.patch("sys.stdout"):
            self.assertIsNone(S.make(self.tmp.name, dt.date(2026, 10, 17), 19, data=d, posts=posted))

    def test_the_plan_caption_adds_the_google_play_link_when_the_app_is_on_android(self):
        d = data(("mochi", "zh-Hant"))
        d["clips"]["mochi/zh-Hant"]["store_url"] = "https://apps.apple.com/us/app/id6785004775?pt=118326163&ct=h7_mochi&mt=8"
        urls = [f"https://is1-ssl.mzstatic.com/image/thumb/x/{i}.png/320x480bb.jpg" for i in range(2)]
        with mock.patch.object(S.post_qa, "store_lookup", return_value={"screenshotUrls": urls}), \
                mock.patch.object(S.volume_ramp, "load", return_value={}):
            plan = S.make(self.tmp.name, dt.date(2026, 10, 17), 7, data=d, posts=[], fetcher=lambda u: shot_png())
        self.assertEqual(STORE_LINK.findall(plan["caption"]), [
            "https://apps.apple.com/us/app/id6785004775?pt=118326163&ct=h7_mochi_ig&mt=8",
            "https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo"
            "&referrer=utm_source%3Dh7_mochi_ig%26utm_campaign%3Dmochi"])
        self.assertEqual(S.qa(plan, online=False), [])

    def test_too_few_screenshots_or_failed_downloads_make_nothing(self):
        d = data(("mochi", "en"))
        with mock.patch.object(S.post_qa, "store_lookup", return_value={"screenshotUrls": ["https://x/1.png/320x480bb.jpg"]}), \
                mock.patch.object(S.volume_ramp, "load", return_value={}), mock.patch("sys.stdout"):
            self.assertIsNone(S.make(self.tmp.name, dt.date(2026, 10, 17), 19, data=d, posts=[]))
        urls = [f"https://x/{i}.png/320x480bb.jpg" for i in range(3)]

        def boom(url):
            raise OSError("404")

        with mock.patch.object(S.post_qa, "store_lookup", return_value={"screenshotUrls": urls}), \
                mock.patch.object(S.volume_ramp, "load", return_value={}), mock.patch("sys.stdout"):
            self.assertIsNone(S.make(self.tmp.name, dt.date(2026, 10, 17), 19, data=d, posts=[], fetcher=boom))


class PostTest(unittest.TestCase):
    PLAN = {"key": "feed/mochi/en", "app": "mochi", "locale": "en", "slot": 19, "date": "2026-10-17", "variant": "a",
            "cards": ["01.jpg", "02.jpg"], "caption": "hook\nGet it on the App Store: https://apps.apple.com/us/app/id1?pt=118326163&ct=h7_mochi_ig&mt=8\nLink in bio",
            "store_url": "https://apps.apple.com/us/app/id1",
            "name": "Mochi", "alt": "Mochi — hook"}

    def test_carousel_children_then_container_then_publish(self):
        calls = []

        def fake_post(url, fields, timeout=60):
            calls.append((url.rsplit("/", 1)[-1], fields))
            return {"id": f"id{len(calls)}"}

        gets = [{"user_id": "u"}, {"status_code": "FINISHED"}, {"permalink": "https://www.instagram.com/p/x/"}]
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "t"}), mock.patch.object(S.clip_posts, "_post", side_effect=fake_post), \
                mock.patch.object(S.clip_posts, "_get", side_effect=gets), mock.patch.object(S.time, "sleep"):
            out = S.post_instagram(self.PLAN, "https://raw.githubusercontent.com/o/r/feed-cards/d/")
        self.assertEqual(out, {"id": "id4", "link": "https://www.instagram.com/p/x/"})
        self.assertEqual(calls[0][1]["image_url"], "https://raw.githubusercontent.com/o/r/feed-cards/d/01.jpg")
        self.assertEqual(calls[0][1]["is_carousel_item"], "true")
        self.assertEqual(calls[0][1]["alt_text"], "Mochi — hook")
        self.assertEqual((calls[2][1]["media_type"], calls[2][1]["children"]), ("CAROUSEL", "id1,id2"))
        self.assertEqual(calls[3][0], "media_publish")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(S.post_instagram(self.PLAN, "u"))

    def test_the_carousel_caption_always_carries_the_download_link(self):
        bare = dict(self.PLAN, caption="hook\nLink in bio")   # a plan written before the link rule
        calls = []

        def fake_post(url, fields, timeout=60):
            calls.append(fields)
            return {"id": f"id{len(calls)}"}

        gets = [{"user_id": "u"}, {"status_code": "FINISHED"}, {"permalink": "p"}]
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "t"}), mock.patch.object(S.clip_posts, "_post", side_effect=fake_post), \
                mock.patch.object(S.clip_posts, "_get", side_effect=gets), mock.patch.object(S.time, "sleep"):
            S.post_instagram(bare, "https://raw.githubusercontent.com/o/r/feed-cards/d/")
        caption = next(c["caption"] for c in calls if c.get("media_type") == "CAROUSEL")
        self.assertIn("https://apps.apple.com/app/id1", caption.replace("/us/app/", "/app/"))
        self.assertTrue(S.post_qa.card_problems(bare["caption"], "en", "instagram", store_url=bare["store_url"], name="Mochi", online=False))
        self.assertEqual(S.post_qa.card_problems(self.PLAN["caption"], "en", "instagram", store_url=self.PLAN["store_url"], name="Mochi", online=False), [])

    def test_main_posts_records_and_throttles_on_a_slow_down_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "plan.json").write_text(json.dumps(self.PLAN))
            argv = ["post", "--dir", tmp, "--base-url", "https://raw.githubusercontent.com/o/r/feed-cards/d"]
            with mock.patch.object(S, "post_instagram", return_value={"id": "m", "link": "l"}), \
                    mock.patch.object(S.clip_progress, "record_post") as rec, mock.patch("sys.stdout"):
                self.assertEqual(S.main(argv), 0)
            self.assertEqual(rec.call_args[0][:3], (S.CHANNEL, "feed/mochi/en", "l"))
            with mock.patch.object(S, "post_instagram", side_effect=RuntimeError("HTTP 429: too many")), \
                    mock.patch.object(S.volume_ramp, "handle_error") as handle, mock.patch("sys.stdout"):
                with self.assertRaises(RuntimeError):
                    S.main(argv)
            self.assertEqual(handle.call_args[0][0], S.CHANNEL)
            with mock.patch("sys.stdout"):   # the ::error:: line is the real thing's output, not this run's
                self.assertEqual(S.main(["post", "--dir", tmp]), 1)  # no base url

    def test_committed_workflow_and_ramp_agree_on_the_slots(self):
        ramp = R.load()
        slots = ramp["channels"]["instagram_feed"]["slots"]
        self.assertEqual(sorted(slots), sorted(S.SLOT_LOCALES))
        text = (Path(__file__).resolve().parents[1] / "workflows" / "ig-feed-daily.yml").read_text(encoding="utf-8")
        for h in slots:
            self.assertIn(f'cron: "20 {h} * * *"', text)
        self.assertIn("--slots " + ",".join(str(h) for h in sorted(slots)), text)


if __name__ == "__main__":
    unittest.main()
