#!/usr/bin/env python3
"""Tests for ig_bio.py (the Instagram "where to tap" line) and ig_bio_hub.py (the profile-link hub page).
No network: icon lookups, the live read-back and the Instagram API go through fakes."""
import io
import json
import re
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_posts as CP  # noqa: E402
import comment_replies as R  # noqa: E402
import download_links as DL  # noqa: E402
import ig_bio as B  # noqa: E402
import ig_bio_hub as H  # noqa: E402
import link_backfill as LB  # noqa: E402
import post_qa  # noqa: E402

MOCHI_ID, USAGE_ID, MASK_ID, BOPO_ID = "6785004775", "6818607603", "6792850916", "6773017109"
CATALOG = {"apps": [
    {"key": "mochi", "app_store_id": MOCHI_ID, "name": "Mochi", "category": "productivity", "verified_live": True},
    {"key": "claudeusagemini", "app_store_id": USAGE_ID, "name": "UsageNow", "category": "productivity",
     "verified_live": True},
    {"key": "maskmyfile", "app_store_id": MASK_ID, "name": "Mask My File", "category": "photo-utility",
     "verified_live": True},
    {"key": "lumibopomofo", "app_store_id": BOPO_ID, "name": "Lumi Bopomofo", "category": "kids",
     "verified_live": True},
    {"key": "gone", "app_store_id": "1", "name": "Gone", "category": "kids", "verified_live": False},
]}
CLIPS = {"clips": {
    "mochi/en": {"app": "mochi", "locale": "en", "name": "Mochi: Cute Checklist",
                 "store_url": f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt=118326163&ct=h7_mochi&mt=8",
                 "hooks": [{"id": "a", "lead": "Your to-do list, but make it cute"},
                           {"id": "c", "lead": "Right on your Home Screen"}]},
    "mochi_b/ja": {"app": "mochi_b", "locale": "ja", "name": "Mochi: かわいいToDo",
                   "store_url": f"https://apps.apple.com/jp/app/id{MOCHI_ID}?pt=118326163&ct=h7_mochi_b&mt=8"},
    "claudeusagemini/zh-Hant": {"app": "claudeusagemini", "locale": "zh-Hant", "name": "UsageNow：AI 用量與額度追蹤",
                                "store_url": f"https://apps.apple.com/tw/app/id{USAGE_ID}?pt=118326163&mt=8",
                                "hooks": [{"id": "b", "lead": "寫到一半 AI 額度又爆了？"}]},
    "maskmyfile/cs": {"app": "maskmyfile", "locale": "cs", "name": "Mask My File: Odstraňte údaje",
                      "store_url": f"https://apps.apple.com/cz/app/id{MASK_ID}?pt=118326163&mt=8"},
}}
UTILITY = {"lumibopomofo": {"id": BOPO_ID, "name": "Lumi注音星球"}}
POSTS = {"posts": [
    {"channel": "instagram", "clip": "maskmyfile/cs", "posted_at": "2026-10-15T19:13:18Z"},
    {"channel": "telegram", "clip": "mochi/en", "posted_at": "2026-10-17T09:00:00Z"},        # not Instagram
    {"channel": "instagram", "clip": "claudeusagemini/zh-Hant", "posted_at": "2026-10-16T05:54:54Z", "variant": "b"},
    {"channel": "instagram", "clip": "utility/zhuyin/lumibopomofo/zy01/zh-Hant", "posted_at": "2026-10-16T09:43:35Z"},
    {"channel": "instagram", "clip": "mochi/en", "posted_at": "2026-10-16T18:50:51Z", "variant": "c"},
    {"channel": "instagram_feed", "clip": "feed/claudeusagemini/zh-Hant", "posted_at": "2026-10-16T22:09:00Z"},
    {"channel": "instagram", "clip": "unknownapp/en", "posted_at": "2026-10-17T03:00:00Z"},   # not on the hub
]}
FOCUS = {"apps": [{"key": "claudeusagemini"}]}
ART = {MOCHI_ID: "https://is1-ssl.mzstatic.com/image/thumb/a/100x100bb.jpg"}


def data(**over):
    kw = dict(catalog=CATALOG, clips=CLIPS, posts=POSTS, focus=FOCUS, utility_apps=UTILITY, artwork=dict(ART))
    kw.update(over)
    return H.Data(**kw)


def play_for(ios_id, ct, channel_level=True):
    """Mochi and Mask My File are on Android in this fixture; the real referrer shape. The hub sends the ig_bio_<app>
    label itself (channel_level=False): the app-level coarsening would turn it into "social", which the root-site
    mirror refuses (the live page stayed on the 10-17 build until 10-22)."""
    if channel_level is not False:
        ct = "social"
    pkg = {MOCHI_ID: "com.alice51849.MochiTodo", MASK_ID: "com.alice51849.MaskMyFile"}.get(str(ios_id))
    if not pkg:
        return None
    return f"https://play.google.com/store/apps/details?id={pkg}&referrer=utm_source%3D{ct}%26utm_campaign%3Dx"


class BioLineTest(unittest.TestCase):
    """Owner 2026-10-17: 「改成原版的好了 請大家去個人檔案下載」「但是你的 tag 可以直接放一個我 app 的名稱」 - an Instagram text
    has no URL, closes with the localized profile-link line, and a caption names the app in one brand hashtag."""

    def test_the_line_names_the_app_by_its_main_store_name_in_the_caption_locale(self):
        # The line is in the caption's locale; the app is named by its brand hashtag (the main store name).
        self.assertEqual(B.bio_line("en"), "📲 Download via the link in bio")
        self.assertEqual(B.bio_line("zh-Hant"), "📲 請到個人檔案（bio）的連結下載")
        self.assertEqual(B.bio_line("ja"), "📲 ダウンロードはプロフィール（bio）のリンクから")
        self.assertEqual(B.bio_line("pt-BR"), B.bio_line("pt"))
        self.assertEqual(B.bio_line("xx"), B.bio_line("en"))   # a locale without its own words: English
        self.assertEqual(B.short_name("TripBee Pro: Trip Planner"), "TripBee Pro")
        self.assertEqual(B.short_name("Lumi注音星球"), "Lumi注音星球")
        self.assertEqual(B.short_name("Snapport Lite - ID Photos"), "Snapport Lite")
        self.assertEqual(B.brand_tag("Mochi: Cute Checklist"), "#Mochi")
        self.assertEqual(B.brand_tag("UsageNow：AI 用量與額度追蹤"), "#UsageNow")
        self.assertEqual(B.brand_tag("TripBee Pro: Trip Planner"), "#TripBeePro")
        self.assertEqual(B.brand_tag("G+Money"), "#GMoney")
        # A brand written in another script takes the app's Latin store name (clips.json / apps.json by App Store id).
        self.assertEqual(B.brand_tag("Lumi注音星球", BOPO_ID), "#LumiBopomofo")
        self.assertEqual(B.brand_tag("Lumi ボポモフォ", f"https://apps.apple.com/jp/app/id{BOPO_ID}"), "#LumiBopomofo")
        self.assertEqual(B.brand_tag("Lumi注音星球"), "")   # no Latin name known: no tag, and the gate refuses

    def test_every_caption_locale_has_its_own_words_and_the_same_bio_phrase_as_the_posters(self):
        for locale in CP.TEXT:
            self.assertIn(locale, B.BIO, locale)   # one table (download_links.INSTAGRAM_CTA) for every poster
            line = B.bio_line(locale)
            self.assertEqual(line, "📲 " + B.BIO[locale], locale)
            self.assertTrue(DL.has_instagram_cta(line, locale), locale)
            self.assertEqual(DL.instagram_url_problems(line), [], locale)
            self.assertEqual(post_qa.locale_problems(line, locale, ("Mochi",)), [], locale)
        self.assertEqual(len(set(B.BIO.values())), len(B.BIO), "every language has its own words")

    def test_qa_refuses_an_instagram_caption_that_does_not_say_where_to_tap(self):
        clip = dict(CLIPS["clips"]["mochi/en"], url="https://x/v.mp4", search="Mochi",
                    compliance={"real_recording": True, "screen_text_ok": True, "board": "0123456789abcdef"})
        real = CP.caption(clip, "instagram")
        self.assertIn("📲 Download via the link in bio", real)
        self.assertEqual(real.splitlines()[-1].split()[0], "#Mochi")   # the brand hashtag leads the tags
        self.assertNotIn("https://", real)
        self.assertEqual(post_qa.clip_problems(clip, "instagram", real, online=False), [])
        generic = real.replace("📲 Download via the link in bio", "Link in bio")
        problems = post_qa.clip_problems(clip, "instagram", generic, online=False)
        self.assertTrue(any("profile-link line" in p for p in problems), problems)
        no_brand = real.replace("#Mochi", "#ToDo")
        self.assertTrue(any("brand hashtag #Mochi" in p for p in post_qa.clip_problems(clip, "instagram", no_brand,
                                                                                       online=False)))
        with_url = real + "\nGet it on the App Store: https://apps.apple.com/app/id" + MOCHI_ID
        self.assertTrue(any("must not carry a URL" in p for p in post_qa.clip_problems(clip, "instagram", with_url,
                                                                                       online=False)))
        # Telegram and Threads links can be tapped: no such line is asked of them.
        self.assertFalse(post_qa.bio_problems(generic, "en", clip["name"], "telegram"))
        # Every Instagram card is held to the rule now, with or without the poster's opt-in.
        store = f"https://apps.apple.com/us/app/id{MOCHI_ID}"
        card = f"Head\nGet it on the App Store: {store}?pt=118326163&ct=ut_mochi_ig&mt=8\nLink in bio"
        good = f"Head\n{B.bio_line('en')}\n\n#Mochi #ToDo"
        with mock.patch("social_post_common.play_store_url", return_value=None):
            for opt_in in (False, True):
                bad = post_qa.card_problems(card, "en", "instagram", store_url=store, name="Mochi", online=False,
                                            require_bio=opt_in)
                self.assertTrue([p for p in bad if "profile-link" in p], opt_in)
                self.assertTrue([p for p in bad if "must not carry a URL" in p], opt_in)
                self.assertEqual([], post_qa.card_problems(good, "en", "instagram", store_url=store, name="Mochi",
                                                           online=False, require_bio=opt_in))

    def test_instagram_comments_and_replies_say_where_to_tap_and_keep_the_link(self):
        # Instagram: no comment is added any more (link_backfill NO_WRITE) and a reply carries no URL, only the
        # profile-link line; Threads keeps its links.
        self.assertIn("instagram", LB.NO_WRITE)
        store = f"https://apps.apple.com/app/id{MOCHI_ID}?pt=118326163&ct=bf_th&mt=8"
        self.assertNotIn("📲", LB.comment_text("ja", store, None, channel="threads"))
        self.assertTrue(DL.has_download_link(LB.comment_text("ja", store, None, channel="threads"), store))
        post = {"app": "mochi", "locale": "en", "ios_id": MOCHI_ID}
        comment = {"id": "1", "text": "Thank you, love it!", "user": "fan", "timestamp": "2026-10-14T10:00:00+0000"}
        now = R.dt.datetime(2026, 10, 14, 12, 0, tzinfo=R.dt.timezone.utc)
        with mock.patch.object(R, "play_store_url", return_value=None):
            ig = R.decide(comment, post, "instagram", "lumi", {}, "M", now)
            th = R.decide(comment, post, "threads", "lumi", {}, "M", now)
        self.assertTrue(ig["text"].endswith("📲 Download via the link in bio"), ig["text"])
        self.assertNotIn("https://", ig["text"])
        self.assertNotIn("📲", th["text"])
        self.assertIn("ct=threads&", th["text"])


class HubDataTest(unittest.TestCase):
    def test_latest_posts_are_instagram_only_newest_first_one_row_per_app(self):
        rows = data().recent()
        self.assertEqual([(r["key"], r["locale"]) for r in rows],
                         [("claudeusagemini", "zh-Hant"), ("mochi", "en"), ("lumibopomofo", "zh-Hant"),
                          ("maskmyfile", "cs")])
        first = rows[0]
        self.assertEqual((first["name"], first["storefront"]), ("UsageNow：AI 用量與額度追蹤", "tw"))
        self.assertEqual(rows[1]["hook"], "Right on your Home Screen")   # the variant that was posted
        self.assertEqual(rows[2]["name"], "Lumi注音星球")                 # utility card: the name its caption quoted
        self.assertEqual(len(data().recent(2)), 2)

    def test_names_follow_the_locale_and_groups_put_the_focus_app_first(self):
        d = data()
        self.assertEqual(d.name("mochi", "ja"), "Mochi: かわいいToDo")
        self.assertEqual(d.name("mochi", "de"), "Mochi")                  # no German store name: the catalog name
        self.assertNotIn("gone", d.apps)                                   # not verified live: not on the hub
        groups = dict(d.groups())
        self.assertEqual(groups["productivity"], ["claudeusagemini", "mochi"])
        self.assertEqual([c for c, _ in d.groups()], ["productivity", "photo-utility", "kids"])

    def test_an_empty_catalog_builds_nothing(self):
        with self.assertRaises(ValueError):
            data(catalog={"apps": []})


class HubPageTest(unittest.TestCase):
    def page(self, d=None):
        with mock.patch.object(H, "play_store_url", side_effect=play_for):
            return H.render(d or data())

    def test_every_button_goes_straight_to_the_store_with_the_ig_bio_campaign(self):
        page = self.page()
        self.assertEqual(H.problems(page, min_links=8), [])
        self.assertEqual(H.problems(page), ["only 8 App Store buttons"])     # the real page lists every app
        self.assertTrue(H.problems(page.replace("ct=ig_bio_mochi", "ct=other")))
        self.assertTrue(H.problems(page.replace("</main>", '<script src="https://x/t.js"></script></main>'),
                                   min_links=8))
        links = [u.replace("&amp;", "&") for u in re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', page)]
        self.assertEqual(len(links), 4 + 4)                                   # latest block + every app
        self.assertIn(f"https://apps.apple.com/tw/app/id{USAGE_ID}?pt=118326163&ct=ig_bio_claudeusagemini&mt=8", links)
        self.assertIn(f"https://apps.apple.com/app/id{MOCHI_ID}?pt=118326163&ct=ig_bio_mochi&mt=8", links)
        self.assertIn(f"https://apps.apple.com/cz/app/id{MASK_ID}?pt=118326163&ct=ig_bio_maskmyfile&mt=8", links)
        plays = re.findall(r'href="(https://play\.google\.com/[^"]+)"', page)
        self.assertEqual(len(plays), 4)                                       # Mochi and Mask My File, twice each
        self.assertTrue(all("utm_source%3Dig_bio_" in p for p in plays))
        self.assertIn("Google Play links without the ig_bio referrer",
                      " ".join(H.problems(page.replace("utm_source%3Dig_bio_mochi", "utm_source%3Dsocial"))))

    def test_the_real_play_link_keeps_the_ig_bio_label(self):
        import social_post_common as common
        snapshot = {MOCHI_ID: {"key": "mochitodo", "play_url": "https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo"}}
        with mock.patch.object(common, "android_apps", return_value=snapshot):
            link = H.play_link(MOCHI_ID, "mochi")
        self.assertIn("utm_source%3Dig_bio_mochi%26", link)

    def test_the_page_is_light_static_and_the_same_for_the_same_data(self):
        page = self.page()
        self.assertEqual(page, self.page())
        self.assertNotRegex(page, r"<script[^>]+src=|<iframe|<form|googletagmanager|gtag\(")
        self.assertIn('<meta name="lumi-ig-hub" content="1">', page)
        self.assertIn('<meta name="lumi-ig-hub-latest" content="2026-10-16T22:09:00Z">', page)
        self.assertIn('<link rel="canonical" href="https://open.cait518.cc/ig/">', page)
        self.assertIn('loading="lazy"', page)
        self.assertLess(len(page.encode()), 120_000)
        latest = page.split('<section class="all">')[0]
        self.assertLess(latest.index('data-app="claudeusagemini"'), latest.index('data-app="mochi"'))
        # Every word of the visitor's language is in the page; a name with "</" cannot end the script early.
        words = json.loads(re.search(r'<script type="application/json" id="hub-t">(.*?)</script>', page).group(1))
        self.assertEqual(set(words), set(CP.TEXT))
        for locale, w in words.items():
            self.assertEqual(set(w), set(H.WORDS["en"]), locale)
        evil = data(clips={"clips": {"mochi/fr": dict(CLIPS["clips"]["mochi/en"], locale="fr", name="Mochi</script>x")}})
        self.assertNotIn("Mochi</script>", self.page(evil))

    def test_build_refuses_without_the_android_snapshot_and_fills_icons_once(self):
        with mock.patch.object(H, "android_apps", return_value={}):
            with self.assertRaises(ValueError):
                H.build(offline=True, data=data(), out=Path("/nonexistent/x.html"))
        calls = []

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout=0):
            calls.append(req.full_url)
            rows = [{"trackId": int(USAGE_ID), "artworkUrl100": "https://is1-ssl.mzstatic.com/u/100x100bb.jpg"}]
            return Resp(json.dumps({"results": rows}).encode())

        found = H.fetch_artwork([USAGE_ID, MASK_ID], opener=opener, countries=("us", "tw"))
        self.assertEqual(found, {USAGE_ID: "https://is1-ssl.mzstatic.com/u/100x100bb.jpg"})
        self.assertEqual(len(calls), 2)                                       # the second storefront for the rest
        self.assertIn(f"id={MASK_ID}&", calls[1])

        def broken(req, timeout=0):
            raise OSError("down")

        with redirect_stdout(io.StringIO()):
            self.assertEqual(H.fetch_artwork([USAGE_ID], opener=broken), {})


class FakeHTTP:
    def __init__(self, body=b"", status=200, error=None):
        self.body, self.status, self.error, self.urls = body, status, error, []

    def __call__(self, req, timeout=0):
        self.urls.append(req.full_url)
        if self.error:
            raise self.error
        outer = self

        class Resp:
            status = outer.status

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return outer.body

        return Resp()


class LiveAndWhoamiTest(unittest.TestCase):
    def test_live_read_back_needs_200_the_marker_and_reports_the_newest_app(self):
        with mock.patch.object(H, "play_store_url", side_effect=play_for):
            page = H.render(data())
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.live("https://x/ig/", opener=FakeHTTP(page.encode()), data=data()), 0)
            self.assertEqual(H.live("https://x/ig/", opener=FakeHTTP(b"<html>other</html>"), data=data()), 1)
            gone = urllib.error.HTTPError("https://x/ig/", 404, "nf", {}, None)
            self.assertEqual(H.live("https://x/ig/", opener=FakeHTTP(error=gone), data=data()), 1)
        self.assertIn("newest post app claudeusagemini on top", out.getvalue())

    def test_whoami_prints_username_and_website_only_never_the_token(self):
        token = "IGAAtesttoken1234567890abcdef"
        out = io.StringIO()
        body = json.dumps({"username": "lumi.apps", "website": "https://open.cait518.cc/ig/", "id": "9"}).encode()
        http = FakeHTTP(body)
        with redirect_stdout(out):
            self.assertEqual(H.whoami(opener=http, token=token)[:2], ("lumi.apps", "https://open.cait518.cc/ig/"))
        self.assertIn("fields=username%2Cwebsite", http.urls[0])
        self.assertNotIn(token, out.getvalue())
        self.assertIn("bio link points to the hub https://open.cait518.cc/ig/: yes", out.getvalue())
        for typed in ("open.cait518.cc/ig", "https://open.cait518.cc/ig", "HTTPS://open.cait518.cc/IG/"):
            self.assertTrue(H.same_page(typed, "https://open.cait518.cc/ig/"), typed)
        for other in ("https://apps.apple.com/developer/guan-feng-lai/id1136144960", "", None,
                      "https://open.cait518.cc/"):
            self.assertFalse(H.same_page(other, "https://open.cait518.cc/ig/"), other)

    def test_whoami_says_so_when_the_api_does_not_give_the_website(self):
        token = "IGAAtesttoken1234567890abcdef"
        calls = []
        err_body = json.dumps({"error": {"message": "Tried accessing nonexisting field (website)"}}).encode()

        def opener(req, timeout=0):
            calls.append(req.full_url)
            if "website" in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(err_body))
            return FakeHTTP(json.dumps({"username": "lumi.apps"}).encode())(req)

        out = io.StringIO()
        with redirect_stdout(out):
            username, website, note = H.whoami(opener=opener, token=token)
        self.assertEqual((username, website), ("lumi.apps", None))
        self.assertIn("nonexisting field (website)", note)
        self.assertIn("website: (not readable", out.getvalue())
        self.assertNotIn(token, out.getvalue())
        self.assertEqual(len(calls), 2)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(H.whoami(opener=opener, token="")[0], None)   # no token: no call at all
        self.assertEqual(len(calls), 2)
        self.assertEqual(H._redact(f"x access_token={token}&y"), "x access_token=***&y")


if __name__ == "__main__":
    unittest.main()
