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
        with mock.patch.object(S.SC, "_terms", return_value={}):  # no rank data: the clip's own search phrase
            self.assertEqual([S.card_lines(c, v, i) for i in range(4)],
                             ["待辦清單也可以這麼可愛", "每天打勾更開心", "可愛待辦清單", "在 App Store 搜尋「mochi」"])
        ranked = {"apps": {"mochi": {"TW": {"term": "待辦清單", "rank": 3, "date": S.SC.today().isoformat(),
                                            "locale": "zh-Hant", "paid": True, "weight": 0.3}}}}
        with mock.patch.object(S.SC, "_terms", return_value=ranked):  # rank data: the term closest to the top 3
            self.assertEqual(S.card_lines(c, v, 3), "在 App Store 搜尋「待辦清單」")

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
        self.assertIn("📲 請到個人檔案（bio）的連結下載", plan["caption"])
        # Owner 2026-10-17 (「改成原版的好了 請大家去個人檔案下載」「但是你的 tag 可以直接放一個我 app 的名稱」): the caption
        # carries no URL at all (Instagram cannot tap it; the profile link is the download link) and its hashtags
        # start with the app's brand hashtag. The drawn cards carry no URL either (not tappable on an image).
        self.assertEqual(STORE_LINK.findall(plan["caption"]), [])
        self.assertNotIn("https://", plan["caption"])
        self.assertEqual(plan["caption"].splitlines()[-1].split()[0], "#mochiname")
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
        # Instagram: no link (owner 2026-10-17); an Android app says in words that it is on Google Play too - the
        # profile-link hub carries both store buttons.
        self.assertEqual(STORE_LINK.findall(plan["caption"]), [])
        self.assertIn("Android 版在 Google Play", plan["caption"])
        self.assertIn("📲 請到個人檔案（bio）的連結下載", plan["caption"])
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
            "cards": ["01.jpg", "02.jpg"], "caption": "hook\n📲 Download via the link in bio\n\n#Mochi #ToDo",
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
        # Owner 2026-10-17: the send call adds the profile-link line and the brand hashtag, never a URL.
        self.assertIn("📲 Download via the link in bio", caption)
        self.assertEqual(caption.splitlines()[-1].split()[0], "#Mochi")
        self.assertNotIn("https://", caption)
        self.assertTrue(S.post_qa.card_problems(bare["caption"], "en", "instagram", store_url=bare["store_url"], name="Mochi", online=False))
        self.assertEqual(S.post_qa.card_problems(self.PLAN["caption"], "en", "instagram", store_url=self.PLAN["store_url"], name="Mochi", online=False), [])
        # An Instagram URL cannot be tapped: the gate wants the profile-link line (and the brand hashtag) instead.
        self.assertEqual(S.qa(self.PLAN, online=False), [])
        generic = dict(self.PLAN, caption=self.PLAN["caption"].replace("📲 Download via the link in bio", "Link in bio"))
        self.assertTrue([p for p in S.qa(generic, online=False) if "profile-link line" in p])
        # A plan written while the URL rule held (it carries the link) is refused at the send call, nothing goes out.
        linked = dict(self.PLAN, caption=self.PLAN["caption"] + "\nGet it on the App Store: https://apps.apple.com/us/app/id1")
        self.assertTrue([p for p in S.qa(linked, online=False) if "must not carry a URL" in p])
        calls.clear()
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "t"}), mock.patch.object(S.clip_posts, "_post", side_effect=fake_post), \
                mock.patch.object(S.clip_posts, "_get", side_effect=gets[:1]), mock.patch.object(S.time, "sleep"):
            with self.assertRaises(S.IGB.DL.MissingDownloadLink):
                S.post_instagram(linked, "https://raw.githubusercontent.com/o/r/feed-cards/d/")
        self.assertEqual(calls, [], "nothing is uploaded, not even the cards")

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


def compare_page(ours_rank=8, others=8):
    """A comparison page shaped like support_network/gen_market_snapshot.py writes it."""
    names = [("提醒事項", "Apple"), ("極簡待辦", "InnerGrow"), ("LockDay: 待辦清單與計畫", "Dat Pham"),
             ("今日待辦", "冬魁 岳"), ("便利貼 - 日程計劃清單、便簽小组件", "楠 唐"), ("To Do List", "BetterApp Tech Co., Limited"),
             ("共用行事曆：TimeTree", "TimeTree, Inc."), ("Yondo 待辦清單", "Ryunosuke Nagase")][:others]
    rows, rank = [], 1
    for i, (app, dev) in enumerate(names):
        if rank == ours_rank:
            rows.append('<tr class="ours"><td>%d</td><td><a href="https://apps.apple.com/app/id1?ct=sup_x_cmp">'
                        'mochi name</a> <span class="tag">本站的 App</span></td><td>Guan Feng Lai</td><td>5.0</td>'
                        '<td>4</td><td>免費</td><td>2026-10-09</td></tr>' % rank)
            rank += 1
        rows.append(f"<tr><td>{rank}</td><td>{app}</td><td>{dev}</td><td>4.8</td><td>1,234</td><td>免費</td><td>2026-10-19</td></tr>")
        rank += 1
    return ('<html><script type="application/ld+json">{"dateModified": "2026-10-20"}</script>'
            '<h1>「代辦事項」在台灣 App Store 的前 9 名搜尋結果</h1><table><tr><th>名次</th></tr>' + "".join(rows) + "</table></html>")


class Top5Test(unittest.TestCase):
    def test_the_list_has_ours_and_at_least_three_other_developers(self):
        snap = S.parse_compare(compare_page(ours_rank=8))
        self.assertEqual(snap["term"], "代辦事項")
        self.assertEqual(snap["date"], "2026-10-20")
        picks = S.top5_rows(snap["rows"])
        self.assertEqual(len(picks), 5)
        self.assertEqual([r["rank"] for r in picks], [1, 2, 3, 4, 8])      # ours is shown with its real position
        self.assertTrue(picks[-1]["ours"])
        inside = S.top5_rows(S.parse_compare(compare_page(ours_rank=2))["rows"])
        self.assertEqual([r["rank"] for r in inside], [1, 2, 3, 4, 5])
        self.assertIsNone(S.top5_rows(S.parse_compare(compare_page(ours_rank=1, others=2))["rows"]))
        self.assertIsNone(S.parse_compare("<h1>「x」</h1><table><tr><td>1</td></tr></table>"))   # no own row

    def test_due_once_a_week(self):
        day = dt.date(2026, 10, 23)
        self.assertTrue(S.top5_due([], day))
        posts = [{"channel": S.CHANNEL, "clip": "feed/mochi/zh-Hant/top5/2026-10-20", "posted_at": "2026-10-20T07:30:00Z"}]
        self.assertFalse(S.top5_due(posts, day))
        self.assertTrue(S.top5_due(posts, dt.date(2026, 10, 28)))

    def test_make_builds_the_list_plan_and_its_caption_passes_the_gate(self):
        d = data(("mochi", "zh-Hant"))
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(S, "compose_text_card", side_effect=lambda lines, clip, out, badge=None, footer=False: Path(out)), \
                mock.patch.object(S.volume_ramp, "room", return_value=(1, 0, 1)):
            plan = S.make(tmp, dt.date(2026, 10, 23), 7, data=d, posts=[],
                          fetcher=lambda url: compare_page().encode() if "compare" in url else b"")
        self.assertIn("/top5/", plan["key"])
        self.assertEqual(len(plan["cards"]), 6)                               # cover + 5 apps
        self.assertIn("TimeTree, Inc.", plan["listed"]) if "TimeTree" in plan["caption"] else None
        cap = plan["caption"]
        self.assertIn("8. mochi name（Guan Feng Lai）", cap)
        self.assertIn("1. 提醒事項（Apple）", cap)
        self.assertNotRegex(cap, r"https?://")                               # Instagram: no URL, the bio line instead
        self.assertNotIn("免費", cap)                                          # no price words
        self.assertEqual(S.qa(plan, online=False), [])

    def test_a_list_naming_a_known_competitor_passes_only_through_the_listed_names(self):
        d = data(("mochi", "zh-Hant"))
        page = compare_page(ours_rank=8).replace("<td>提醒事項</td>", "<td>TimeTree</td>")
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(S, "compose_text_card", side_effect=lambda lines, clip, out, badge=None, footer=False: Path(out)):
            plan = S.make_top5(tmp, dt.date(2026, 10, 23), 7, d, [], page_fetcher=lambda url: page)
        self.assertIn("TimeTree", plan["caption"])
        self.assertEqual(S.qa(plan, online=False), [])
        self.assertTrue(S.qa(dict(plan, listed=[]), online=False))         # without them the gate refuses it

    def test_no_comparison_page_falls_back_to_the_screenshot_carousel(self):
        d = data(("mochi", "zh-Hant"))
        def fetcher(url):
            if "compare" in url:
                raise OSError("404")
            return shot_png()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(S, "shot_urls", return_value=["https://x/1.jpg", "https://x/2.jpg"]), \
                mock.patch.object(S, "compose", side_effect=lambda b, h, c, out: Path(out)):
            plan = S.make(tmp, dt.date(2026, 10, 23), 7, data=d, posts=[], fetcher=fetcher)
        self.assertNotIn("/top5/", plan["key"])

    @unittest.skipUnless(FONT, "needs a TrueType font")
    def test_text_cards_are_drawn(self):
        index = cd.FONT_INDEX if "NotoSansCJK" in FONT else {}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(cd, "FONT", FONT), \
                mock.patch.object(cd, "FONT_INDEX", index):
            out = S.compose_text_card(["8", "mochi name", "Guan Feng Lai"], clip("mochi", "zh-Hant"),
                                      Path(tmp) / "c.jpg", badge="我們做的 App")
            self.assertGreater(out.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()


class QueuedCarouselTest(unittest.TestCase):
    """2026-10-22 carousel line: queued 5-card carousels (00_GrowthEngine social/carousel) after the weekly list."""

    def entry(self, **kw):
        e = {"id": "mochi-zh-Hant-pain-20261022", "app": "mochi", "app_id": "6785004775", "locale": "zh-Hant",
             "country": "TW", "format": "pain", "name": "mochi name", "hook": "每天看到待辦清單就好累？",
             "text": "每天看到待辦清單就好累？\n\n點一下就完成\n\n在 App Store 搜尋「Mochi」", "tags": ["#可愛待辦清單"],
             "alt": "alt", "listed": [], "channels": ["instagram", "pinterest"], "start": "2026-10-22",
             "images": [f"https://github.com/o/r/releases/download/carousel-cards/x-0{i}.jpg" for i in range(1, 6)]}
        e.update(kw)
        return e

    def make(self, entries, day=dt.date(2026, 10, 23), slot=7, posts=()):
        tmp = tempfile.mkdtemp()
        q = Path(tmp) / "carousels.json"
        q.write_text(json.dumps({"items": entries}, ensure_ascii=False), encoding="utf-8")
        got = []
        plan = S.make_queued(Path(tmp) / "out", day, slot, list(posts), fetcher=lambda u: got.append(u) or b"x" * 20000,
                             path=q)
        return plan, got, Path(tmp) / "out"

    def test_due_entry_becomes_an_instagram_plan_with_the_bio_line_and_no_url(self):
        plan, got, out = self.make([self.entry()])
        self.assertEqual(plan["key"], "feed/mochi/zh-Hant/carousel/mochi-zh-Hant-pain-20261022")
        self.assertEqual(plan["cards"], [f"0{i}.jpg" for i in range(1, 6)])
        self.assertEqual(len(got), 5)
        self.assertNotRegex(plan["caption"], r"https?://")
        self.assertIn("📲 請到個人檔案（bio）的連結下載", plan["caption"])
        self.assertIn("ct=", plan["store_url"])
        self.assertTrue((out / "plan.json").exists())

    def test_not_due_wrong_slot_posted_cooling_or_not_for_instagram_is_skipped(self):
        self.assertIsNone(self.make([self.entry(start="2026-10-30")])[0])
        self.assertIsNone(self.make([self.entry()], slot=19)[0])                     # zh-Hant is the Asia slot
        self.assertIsNone(self.make([self.entry(channels=["bluesky"])])[0])
        done = [{"channel": S.CHANNEL, "clip": "feed/mochi/zh-Hant/carousel/mochi-zh-Hant-pain-20261022",
                 "posted_at": "2026-10-10T07:21:00Z"}]
        self.assertIsNone(self.make([self.entry()], posts=done)[0])
        week = [{"channel": S.CHANNEL, "clip": "feed/mochi/en", "posted_at": "2026-10-21T19:21:00Z"}]
        self.assertIsNone(self.make([self.entry()], posts=week)[0])                   # app featured this week
        en = self.entry(id="mochi-en-pain-20261022", locale="en", country="US", text="Your list feels like a chore?")
        self.assertEqual(self.make([self.entry(), en], slot=19)[0]["locale"], "en")
        # one the pre-post gate would refuse (wrong script for its locale) gives its slot to the next one
        bad = self.entry(id="mochi-de-pain-20261022", locale="de", country="DE", text="Spielerisch 注音 lernen")
        de = self.entry(id="mochi-de-pain-20261023", locale="de", country="DE", text="Deine To-do-Liste, nur viel süßer")
        with mock.patch("sys.stdout"):
            self.assertEqual(self.make([bad, de])[0]["key"], "feed/mochi/de/carousel/mochi-de-pain-20261023")

    def test_make_takes_the_queue_after_the_list_and_before_the_screenshot_carousel(self):
        d = data(("mochi", "zh-Hant"))
        tmp = tempfile.mkdtemp()
        q = Path(tmp) / "carousels.json"
        q.write_text(json.dumps({"items": [self.entry()]}, ensure_ascii=False), encoding="utf-8")
        posts = [{"channel": S.CHANNEL, "clip": "feed/sereno/en/top5/2026-10-20", "posted_at": "2026-10-20T07:30:00Z"}]
        with mock.patch.object(S, "QUEUE", q), mock.patch.object(S.volume_ramp, "room", return_value=(1, 0, 1)), \
                mock.patch("sys.stdout"):
            plan = S.make(Path(tmp) / "out", dt.date(2026, 10, 23), 7, data=d, posts=posts, fetcher=lambda u: b"x" * 20000)
        self.assertIn("/carousel/", plan["key"])
        self.assertEqual(S.qa(plan, online=False), [])
