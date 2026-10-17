#!/usr/bin/env python3
"""Tests for download_links.py (no network): every promo text carries the app's direct download link."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import download_links as D  # noqa: E402

STORE = "https://apps.apple.com/us/app/id6785004775?pt=118326163&ct=h7_mochi_ig&mt=8"
PLAY = "https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo&referrer=utm_source%3Dx"


class DownloadLinksTest(unittest.TestCase):
    def test_ids_are_read_from_every_store_link_shape(self):
        for url in ("https://apps.apple.com/app/id6785004775", "https://apps.apple.com/us/app/mochi/id6785004775?mt=8",
                    "https://itunes.apple.com/tw/app/id6785004775"):
            self.assertEqual(D.app_store_id(url), "6785004775", url)
        self.assertEqual(D.app_store_id("https://example.com/id123"), "")
        self.assertEqual(D.app_store_id("https://itunes.apple.com/lookup?id=6785004775"), "")
        self.assertEqual(D.play_package(PLAY), "com.alice51849.MochiTodo")
        self.assertEqual(D.play_package("https://play.google.com/store/apps/details?hl=en&id=a.b"), "a.b")

    def test_the_link_must_be_this_apps_own(self):
        other = "see https://apps.apple.com/app/id999999999 now"
        self.assertFalse(D.has_download_link(other, STORE))
        self.assertTrue(D.has_download_link("get it https://apps.apple.com/jp/app/mochi/id6785004775", STORE))
        text = "https://apps.apple.com/app/id6785004775"
        self.assertTrue(D.has_download_link(text, STORE))
        self.assertFalse(D.has_download_link(text, STORE, PLAY), "an Android app needs its Play link too")
        self.assertTrue(D.has_download_link(text + "\n" + PLAY, STORE, PLAY))

    def test_a_write_review_link_is_not_a_download_link(self):
        review = "https://apps.apple.com/app/id6785004775?action=write-review"
        self.assertFalse(D.has_download_link(f"Rate us: {review}", STORE))
        self.assertTrue(D.link_problems(f"Rate us: {review}", STORE))
        both = D.ensure_download_link(f"Rate us: {review}", STORE)
        self.assertIn(f"App Store: {STORE}", both)
        self.assertTrue(D.has_download_link(both, STORE))
        self.assertTrue(D.has_download_link(f"{review}\nGet it: {STORE}", STORE))

    def test_a_wrapped_or_retargeted_link_is_still_this_apps_link(self):
        wrapped = "https%3A%2F%2Fapps.apple.com%2Fapp%2Fid6785004775%3Fct%3Dx"
        self.assertTrue(D.has_download_link(f"see {wrapped}", STORE))
        self.assertTrue(D.links_covered(f"Get it: {STORE}", "App Store: https://apps.apple.com/app/id6785004775?ct=other"))
        self.assertFalse(D.links_covered("nothing here", f"App Store: {STORE}"))
        self.assertFalse(D.links_covered(f"App Store: {STORE}", f"App Store: {STORE}\nGoogle Play: {PLAY}"))
        self.assertFalse(D.links_covered("anything", "no links in here"))

    def test_link_in_bio_words_are_not_a_link(self):
        for text in ("Search “Mochi” on the App Store\nLink in bio", "Also on Google Play", "App Store: soon"):
            self.assertFalse(D.has_download_link(text, STORE), text)
            self.assertTrue(D.link_problems(text, STORE))

    def test_missing_link_is_appended_with_both_stores(self):
        out = D.ensure_download_link("Hook line\nbenefit\n\n#a #b", STORE, PLAY)
        self.assertTrue(out.startswith("Hook line\nbenefit"))
        self.assertTrue(D.has_download_link(out, STORE, PLAY))
        self.assertIn(f"App Store: {STORE}", out)
        self.assertIn(f"Google Play: {PLAY}", out)

    def test_only_what_is_missing_is_added_and_nothing_twice(self):
        have = f"Hook\nGet it: {STORE}"
        out = D.ensure_download_link(have, STORE, PLAY)
        self.assertEqual(out.count(STORE), 1)
        self.assertEqual(out.count(PLAY), 1)
        self.assertEqual(D.ensure_download_link(out, STORE, PLAY), out, "a second pass changes nothing")
        self.assertEqual(D.ensure_download_link(have, STORE), have)

    def test_localized_labels(self):
        out = D.ensure_download_link("鉤子", STORE, PLAY, app_store_label="在 App Store 下載", play_label="Android 版在 Google Play")
        self.assertIn("在 App Store 下載: https://apps.apple.com", out)
        self.assertIn("Android 版在 Google Play: https://play.google.com", out)

    def test_long_text_is_trimmed_so_the_link_stays_inside_the_limit(self):
        text = "Problem line. " * 60 + "\n\n#one #two #three"
        out = D.ensure_download_link(text, STORE, PLAY, max_len=500)
        self.assertLessEqual(len(out), 500)
        self.assertTrue(D.has_download_link(out, STORE, PLAY))
        self.assertTrue(out.startswith("Problem line."))
        tight = D.ensure_download_link("x" * 400 + "\n#tag", STORE, max_len=len(f"App Store: {STORE}") + 30)
        self.assertTrue(D.has_download_link(tight, STORE))

    def test_a_trim_never_drops_a_link_the_text_already_had(self):
        have = "Hook\n" + "word " * 50 + f"\nApp Store: {STORE}\n\n#a #b"  # has the App Store link, lacks Play
        out = D.ensure_download_link(have, STORE, PLAY, max_len=len(have) + 10)
        self.assertLessEqual(len(out), len(have) + 10)
        self.assertTrue(D.has_download_link(out, STORE, PLAY))
        self.assertEqual(out.count(STORE), 1)

    def test_a_trim_never_leaves_half_a_url(self):
        text = "see https://example.com/" + "x" * 300 + " bye"
        out = D.ensure_download_link(text, STORE, PLAY, max_len=300)
        self.assertNotIn("https://example.com", out)
        self.assertLessEqual(len(out), 300)
        self.assertTrue(D.has_download_link(out, STORE, PLAY))

    def test_an_id_must_end_at_the_digits(self):
        self.assertEqual(D.app_store_id("https://apps.apple.com/app/id6785004775abc"), "")
        self.assertFalse(D.has_download_link("https://apps.apple.com/app/id6785004775abc", STORE))

    def test_hashtags_go_before_the_body_is_cut(self):
        out = D.ensure_download_link("Hook\n\n#aaa #bbb", STORE, max_len=len(f"Hook\n\nApp Store: {STORE}") + 2)
        self.assertNotIn("#aaa", out)
        self.assertTrue(out.startswith("Hook"))

    def test_no_link_that_fits_means_no_post(self):
        with self.assertRaises(D.MissingDownloadLink):
            D.ensure_download_link("Hook", STORE, max_len=30)
        for bad in ("", None, "https://example.com/app", "https://apps.apple.com/app/idabc"):
            with self.assertRaises(D.MissingDownloadLink, msg=repr(bad)):
                D.ensure_download_link("Hook", bad)

    def test_threads_reply_check(self):
        reply = f"Get it on the App Store: {STORE}\nGoogle Play: {PLAY}"
        self.assertEqual(D.threads_reply_problems(reply, STORE, PLAY), [])
        self.assertTrue(D.threads_reply_problems("Get it on the App Store", STORE))

    def test_refusal_is_printed_and_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "guard.jsonl"
            out = io.StringIO()   # the ::error:: line is the real thing's output: keep it out of this run's annotations
            with contextlib.redirect_stdout(out):
                self.assertFalse(D.refuse("a/en instagram", ["no link"], log_path=str(log)))
            self.assertIn("::error::a/en instagram: download link guard refused: no link", out.getvalue())
            row = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row, {"label": "a/en instagram", "problems": ["no link"]})

    def test_cli_exit_code(self):
        self.assertEqual(D.main(["check", "hello", "--app-store", STORE]), 1)
        self.assertEqual(D.main(["check", f"hello {STORE}", "--app-store", STORE]), 0)


class InstagramRuleTest(unittest.TestCase):
    """Owner 2026-10-17: 「ig 貼文沒辦法顯示連結的話你用很長的文字沒有比較好耶 改成原版的好了 請大家去個人檔案下載」「但是你的
    tag 可以直接放一個我 app 的名稱」 - an Instagram text carries no URL, closes with the localized "download via the link
    in bio" line, and a caption names the app in ONE brand hashtag. Every other platform keeps its links."""

    GOOD = "Task list too boring?\nMochi: Cute To-Do\n📲 Download via the link in bio\n\n#Mochi #ToDo"

    def test_a_caption_without_a_url_with_the_line_and_the_brand_hashtag_is_fine(self):
        self.assertEqual([], D.instagram_problems(self.GOOD, "Mochi: Cute To-Do", locale="en"))
        zh = "待辦清單好無聊？\n📲 請到個人檔案（bio）的連結下載\n\n#UsageNow #AI額度"
        self.assertEqual([], D.instagram_problems(zh, "UsageNow：AI 用量與額度追蹤", locale="zh-Hant"))

    def test_any_url_is_refused_the_apps_own_store_links_included(self):
        for url in (STORE, PLAY, "https://open.cait518.cc/ig/", "open.cait518.cc/ig/", "apps.apple.com/app/id6785004775",
                    "www.example.org", "lumistudio.com", "http://t.me/lumi"):
            text = self.GOOD.replace("📲 Download via the link in bio", f"📲 Download via the link in bio\n{url}")
            problems = D.instagram_problems(text, "Mochi", locale="en")
            self.assertTrue(any("must not carry a URL" in p for p in problems), (url, problems))
            with self.assertRaises(D.MissingDownloadLink):
                D.ensure_instagram_caption(text, "Mochi", "en")
        for plain in ("Version 1.5/2 is out", "Node.js and e.g. notes", "G+Money", "50% off nothing"):
            self.assertEqual([], D.instagram_url_problems(plain), plain)   # words, not addresses

    def test_the_profile_link_line_is_required_in_the_texts_language(self):
        no_line = self.GOOD.replace("📲 Download via the link in bio", "Link in bio")
        self.assertTrue(any("profile-link line" in p for p in D.instagram_problems(no_line, "Mochi", locale="en")))
        self.assertTrue(any("profile-link line" in p for p in D.instagram_problems(self.GOOD, "Mochi", locale="ja")))
        self.assertEqual([], D.instagram_problems(self.GOOD, "Mochi"))   # no locale given: any language's line
        for locale in ("en", "zh-Hant", "zh-Hans", "ja", "ko", "de", "fr", "es", "it", "pt-BR", "id", "vi", "th", "cs",
                       "pl", "nl", "da", "nb", "el", "ar"):
            line = D.instagram_cta_line(locale)
            self.assertTrue(line.startswith("📲 ") and D.has_instagram_cta(line, locale), locale)
        self.assertEqual(D.instagram_cta("zh"), D.instagram_cta("zh-Hant"))
        self.assertEqual(D.instagram_cta("pt"), D.instagram_cta("pt-BR"))
        self.assertEqual(D.instagram_cta("sw"), D.instagram_cta("en"))

    def test_the_brand_hashtag_is_the_main_store_name_without_spaces_and_symbols(self):
        cases = {"BattAI: Battery Health & Life": "#BattAI", "Lumi Weather": "#LumiWeather", "G+Money": "#GMoney",
                 "dB Halo": "#dBHalo", "100 Notes Studio": "#100NotesStudio", "UsageNow：AI 用量與額度追蹤": "#UsageNow",
                 "HoursTag Lite：買前先算工時": "#HoursTagLite", "Snapport Lite - ID Photos": "#SnapportLite"}
        for name, tag in cases.items():
            self.assertEqual(D.brand_hashtag(name), tag, name)
        # A brand that is not written in Latin letters takes the app's Latin store name.
        self.assertEqual(D.brand_hashtag("Lumi注音星球", "Lumi Bopomofo"), "#LumiBopomofo")
        self.assertEqual(D.brand_hashtag("Lumi ボポモフォ", "Lumi Bopomofo: Zhuyin"), "#LumiBopomofo")
        self.assertEqual(D.brand_hashtag("Lumi注音星球"), "")
        problems = D.instagram_problems(self.GOOD, "Lumi注音星球", locale="en")
        self.assertTrue(any("no brand hashtag can be made" in p for p in problems), problems)

    def test_the_brand_hashtag_must_be_there_as_a_whole_tag(self):
        self.assertTrue(D.has_brand_hashtag("x #mochi y", "#Mochi"))   # any letter case
        self.assertFalse(D.has_brand_hashtag("x #MochiDoneStamp", "#Mochi"))
        self.assertFalse(D.has_brand_hashtag("Mochi", "#Mochi"))
        no_tag = self.GOOD.replace("#Mochi ", "")
        self.assertTrue(any("no brand hashtag #Mochi" in p for p in D.instagram_problems(no_tag, "Mochi", locale="en")))
        self.assertEqual([], D.instagram_problems("Thanks!\n📲 Download via the link in bio", locale="en", brand=False))

    def test_ensure_adds_the_line_and_the_brand_hashtag_first_within_the_tag_limit(self):
        text = "Task list too boring?\nMochi: Cute To-Do\n\n#ToDo #Checklist #Cute #Planner #Habit"
        out = D.ensure_instagram_caption(text, "Mochi: Cute To-Do", "en", tag_limit=5)
        lines = out.split("\n")
        self.assertEqual(lines[2], "📲 Download via the link in bio")
        self.assertEqual(lines[-1].split(), ["#Mochi", "#ToDo", "#Checklist", "#Cute", "#Planner"])
        self.assertEqual(out, D.ensure_instagram_caption(out, "Mochi: Cute To-Do", "en", tag_limit=5))   # idempotent
        moved = D.ensure_instagram_caption("Hook\n\n#ToDo #mochi", "Mochi", "en")
        self.assertEqual(moved.split("\n")[-1].split(), ["#Mochi", "#ToDo"])   # one brand hashtag, first

    def test_a_long_caption_loses_other_hashtags_then_body_never_the_line_or_the_brand(self):
        text = "word " * 600 + "\n\n" + " ".join(f"#tag{i}" for i in range(20))
        out = D.ensure_instagram_caption(text, "BattAI", "zh-Hant", max_len=2200)
        self.assertLessEqual(len(out), 2200)
        self.assertEqual(out.split("\n")[-1], "#BattAI")
        self.assertIn("📲 請到個人檔案（bio）的連結下載", out)
        self.assertEqual([], D.instagram_problems(out, "BattAI", locale="zh-Hant"))
        with self.assertRaises(D.MissingDownloadLink):
            D.ensure_instagram_caption(text, "BattAI", "en", max_len=10)

    def test_other_platforms_still_owe_the_direct_link(self):
        # The Instagram rule is Instagram's: a Telegram / Bluesky text without the link is refused as before.
        self.assertTrue(D.link_problems(self.GOOD, STORE))
        self.assertTrue(D.link_problems(f"{self.GOOD}\n{STORE}", STORE, PLAY))   # Android: Play is owed too
        self.assertEqual([], D.link_problems(f"{self.GOOD}\n{STORE}\n{PLAY}", STORE, PLAY))
        self.assertIn(STORE, D.ensure_download_link(self.GOOD, STORE))
        self.assertTrue(D.is_instagram("instagram") and D.is_instagram("instagram_feed"))
        for channel in ("telegram", "threads", "bluesky", "youtube", "facebook", ""):
            self.assertFalse(D.is_instagram(channel), channel)


if __name__ == "__main__":
    unittest.main()
