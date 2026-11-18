"""Quality audit 2026-11-19: no medical tags (rule 1.9), no single split-out keyword words, at most 5 tags,
CJK hook lines punctuated with full-width marks instead of half-width spaces."""
import unittest

import search_caption as SC


class MedicalTagTest(unittest.TestCase):
    def test_drug_injection_and_weight_loss_tags_never_go_out(self):
        bad = ["#施打", "#CanetaEmagrecedora", "#Jab", "#Abnehmspritze", "#Adelgazar", "#Glp1", "#GewichtGLP1Tracker", "#WeightGLP1Tracker", "#Injection",
               "#瘦瘦針", "#減重針", "#減肥", "#ダイエット注射", "#살빼기", "#감량", "#Ozempic", "#WeightLoss",
               "#비포애프터", "#ShotLog"]
        for t in bad:
            self.assertTrue(SC.medical(t), t)
        clip = {"locale": "de", "search": "Kumo", "tags": ["#Abnehmspritze", "#Gewichtstagebuch", "#GewichtGLP1Tracker"]}
        self.assertNotIn("#Abnehmspritze", SC.tags(clip, 5))
        self.assertNotIn("#GewichtGLP1Tracker", SC.tags(clip, 5))
        self.assertIn("#Gewichtstagebuch", SC.tags(clip, 5))

    def test_ordinary_tags_are_not_medical(self):
        for t in ["#ShotInbox", "#Screenshot", "#Pomodoro", "#주사위", "#CountDaysNow", "#輕斷食", "#Gewichtstagebuch"]:
            self.assertFalse(SC.medical(t), t)


class PhraseTagTest(unittest.TestCase):
    def test_single_split_words_are_dropped_phrases_and_brand_stay(self):
        clip = {"locale": "es", "search": "MeowParty",
                "tags": ["#Jugadores", "#Personas", "#Mismo", "#JuegosDeGatos", "#MeowParty"]}
        self.assertEqual(SC.tags(clip, 5), ["#JuegosDeGatos", "#MeowParty"])

    def test_brand_alone_when_nothing_else_survives(self):
        clip = {"locale": "en", "search": "Kumo", "tags": ["#Loss", "#Injection", "#Daily"]}
        self.assertEqual(SC.tags(clip, 5), ["#Kumo"])

    def test_fragments_and_short_latin_words_go_real_single_terms_stay(self):
        self.assertTrue(SC.phrase_tag("#수능", "ko"))
        self.assertTrue(SC.phrase_tag("#輕斷食", "zh-Hant"))
        self.assertTrue(SC.phrase_tag("#Decibel", "en"))  # review 11-19: Latin single words are not all dropped
        self.assertTrue(SC.phrase_tag("#Gewichtskontrolle", "de"))
        for t in ("#Intermittent", "#Loss", "#Daily", "#Mismo", "#間歇性", "#計時器", "#鬧鐘", "#마시기", "#타이머", "#a"):
            self.assertFalse(SC.phrase_tag(t, "en"), t)

    def test_never_more_than_five(self):
        clip = {"locale": "en", "search": "UsageNow",
                "tags": ["#AiUsageTracker", "#ClaudeLimits", "#CodexLimits", "#CopilotLimits", "#GeminiLimits",
                         "#TokenCounter", "#UsageNow"]}
        out = SC.tags(clip, 10)
        self.assertLessEqual(len(out), 5)
        self.assertIn("#UsageNow", out)

    def test_generic_cjk_words_are_dropped(self):
        clip = {"locale": "zh-Hant", "search": "Kumo", "tags": ["#記錄", "#管理", "#輕斷食"]}
        self.assertEqual(SC.tags(clip, 5), ["#輕斷食"])


class CjkPunctuationTest(unittest.TestCase):
    def test_space_between_cjk_becomes_fullwidth_comma(self):
        self.assertEqual(SC.tidy("改善案をタップして スコアアップ", "ja"), "改善案をタップして、スコアアップ")
        self.assertEqual(SC.tidy("截圖裡的文字 也搜得到", "zh-Hant"), "截圖裡的文字，也搜得到")
        self.assertEqual(SC.tidy("一般 iPhone 也能完整玩 畫面按鈕", "zh-Hant"), "一般 iPhone 也能完整玩，畫面按鈕")
        self.assertEqual(SC.tidy("照片拍糊了？ 秒變清晰", "zh-Hant"), "照片拍糊了？秒變清晰")
        self.assertEqual(SC.tidy("Blurry photo? Make it clear", "en"), "Blurry photo? Make it clear")
        self.assertEqual(SC.tidy("剩多少、何時重置 一眼看清"), "剩多少、何時重置 一眼看清")  # no locale: unchanged

    def test_variants_use_the_clip_locale(self):
        clip = {"locale": "ja", "hooks": [{"id": "a", "lead": "アカウント不要 端末の中だけ", "benefit": "生理日も ひと目で"}]}
        v = SC.variants(clip)[0]
        self.assertEqual((v["lead"], v["benefit"]), ("アカウント不要、端末の中だけ", "生理日も、ひと目で"))


class OldPostMatchTest(unittest.TestCase):
    """Posts that went out with the old half-width-space hook still match the new comma-punctuated hook."""

    def test_link_backfill_lead_key_ignores_blanks_and_commas(self):
        import link_backfill as LB
        self.assertEqual(LB.lead_key("改善案をタップして スコアアップ"), LB.lead_key("改善案をタップして、スコアアップ"))
        self.assertEqual(LB.lead_key("截圖裡的文字 也搜得到"), LB.lead_key("截圖裡的文字，也搜得到"))

    def test_own_posts_resolves_an_old_spaced_caption_to_the_new_hook(self):
        import own_posts as OP
        clips = {"x/ja": {"app": "x", "locale": "ja", "store_url": "https://apps.apple.com/app/id1",
                          "hooks": [{"id": "a", "lead": "アカウント不要、端末の中だけ", "benefit": ""}]}}
        cat = OP.Catalog(clips={"clips": clips}, posts=[], improvements={})
        got = cat.resolve("instagram", {"id": "m1", "caption": "アカウント不要 端末の中だけ\nほか"})
        self.assertEqual((got or {}).get("clip"), "x/ja")


class YoutubeKeywordTest(unittest.TestCase):
    """Rule 1.9: the YouTube description keyword line and hidden tags of an old clips.json entry (Kumo still carries
    loss / injection / glp1 / 瘦瘦針 / abnehmspritze / ダイエット注射 / adelgazar until the planner reruns)."""

    def kumo(self, loc, keywords):
        return {"app": "kumo", "locale": loc, "name": "Kumo: Weight & GLP-1 Tracker", "search": "Kumo",
                "keywords": keywords, "tags": ["#Kumo"], "keyline": ""}

    def test_medical_and_weight_loss_keywords_never_reach_youtube(self):
        cases = {"en": ["loss", "injection", "glp1", "daily", "diary"], "zh-Hant": ["瘦瘦針", "減重針", "輕斷食"],
                 "de": ["abnehmspritze", "spritzen", "gewichtstagebuch"], "ja": ["ダイエット注射", "ファスティング"],
                 "es": ["adelgazar", "perder", "bajar", "pérdida", "registro"]}
        bad = {"loss", "injection", "glp1", "瘦瘦針", "減重針", "abnehmspritze", "spritzen", "ダイエット注射", "adelgazar",
               "perder", "bajar", "pérdida"}
        for loc, kw in cases.items():
            clip = self.kumo(loc, kw)
            title, desc, tags = SC.youtube(clip, {"lead": "Log your weight", "benefit": ""}, [])
            low = (desc + " " + " ".join(tags)).casefold()
            self.assertFalse([b for b in bad if b in low], f"{loc}: {desc!r} {tags}")
            self.assertTrue(set(SC.safe_keywords(clip)) <= set(kw))

    def test_ordinary_apps_keep_their_keywords(self):
        clip = {"name": "Snapport: Passport Photo", "keywords": ["passport", "loss", "visa"]}
        self.assertEqual(SC.safe_keywords(clip), ["passport", "loss", "visa"])  # not a weight app: "loss" stays

    def test_more_languages_are_medical(self):
        for t in ("减肥", "spruta", "zayıflama", "tiêm", "похудеть", "تخسيس", "इंजेक्शन", "schudnąć", "suntik"):
            self.assertTrue(SC.medical(t), t)
        for frag in ("#Gbagbcgb", "#Down", "#Sono", "#Zurücksetzen"):
            self.assertFalse(SC.phrase_tag(frag), frag)


    def test_review_1119c_kumo_is_health_even_with_a_plain_name(self):
        # a localized Kumo name without a medical word, keywords without one either: still a weight app
        clip = {"app": "kumo", "locale": "id", "name": "Kumo: Catatan Berat", "search": "Kumo",
                "keywords": ["turun", "menurunkan", "kurangi", "shot", "Shot ", "diary"], "keyline": ""}
        self.assertEqual(SC.safe_keywords(clip), ["diary"])
        title, desc, tags = SC.youtube(clip, {"lead": "Catat berat", "benefit": ""}, [])
        low = (desc + " " + " ".join(tags)).casefold()
        for bad in ("turun", "menurunkan", "kurangi", "shot"):
            self.assertNotIn(bad, low)

    def test_review_1119c_medical_search_or_keyline_makes_a_health_app(self):
        base = {"app": "other", "name": "Plain Diary", "keywords": ["loss", "diary"]}
        self.assertEqual(SC.safe_keywords(dict(base, search="Plain", keyline="")), ["loss", "diary"])
        self.assertEqual(SC.safe_keywords(dict(base, search="GLP-1 log", keyline="")), ["diary"])
        self.assertEqual(SC.safe_keywords(dict(base, search="Plain", keyline="Abnehmspritze Tagebuch")), ["diary"])

    def test_review_1119d_weight_word_tags_go_only_in_a_health_app(self):
        kumo = {"app": "kumo", "locale": "en", "search": "Kumo weight tracker",
                "tags": ["#Shot", "#Shots", "#Turun", "#CuteCloud"]}
        self.assertEqual(SC.tags(kumo), ["#CuteCloud"])
        kumo_id = dict(kumo, locale="id", search="Kumo", name="Kumo: Catatan Berat")
        self.assertEqual(SC.tags(kumo_id), ["#CuteCloud"])
        shotinbox = {"app": "shotinbox", "locale": "en", "search": "ShotInbox", "name": "ShotInbox",
                     "tags": ["#Shot", "#ScreenshotCleaner"]}
        self.assertIn("#Shot", SC.tags(shotinbox))

    def test_review_1119c_fragment_check_ignores_spaces(self):
        for frag in ("#GåNer", "#Gå ner", "#gåner", "#Gå  Ner"):
            self.assertFalse(SC.phrase_tag(frag, "sv"), frag)
        self.assertTrue(SC.phrase_tag("#Viktdagbok", "sv"))


class HealthKeylineTest(unittest.TestCase):
    """Coordinator 11-19: Kumo keyword line, keywords and tags on the GE health_terms list (ダイエット / 다이어트)."""

    def test_kumo_keyline_drops_the_diet_part_everywhere_it_is_shown(self):
        clip = {"app": "kumo", "locale": "ja", "search": "Kumo", "name": "Kumo",
                "keyline": "かわいい雲と1日10秒、ダイエット管理を習慣に"}
        self.assertEqual(SC.safe_keyline(clip), "かわいい雲と1日10秒")
        variant = {"lead": "体重が気になる", "benefit": "10秒で記録"}
        self.assertNotIn("ダイエット", "\n".join(SC.body(clip, variant)))
        self.assertNotIn("ダイエット", SC.alt_text(clip, variant))
        self.assertNotIn("ダイエット", SC.pin_title(clip, variant))
        ko = {"app": "kumo", "locale": "ko", "keyline": "귀여운 구름과 하루 10초 체중 관리·다이어트 일기"}
        self.assertEqual(SC.safe_keyline(ko), "귀여운 구름과 하루 10초 체중 관리")

    def test_kumo_diet_tags_and_keywords_never_go_out(self):
        clip = {"app": "kumo", "locale": "ja", "search": "Kumo", "tags": ["#ダイエット記録", "#体脂肪率", "#다이어트일기"],
                "keywords": ["ダイエット", "体脂肪率", "다이어트"]}
        self.assertEqual(SC.safe_keywords(clip), ["体脂肪率"])
        self.assertNotIn("#ダイエット記録", SC.tags(clip, 5))
        self.assertNotIn("#다이어트일기", SC.tags(clip, 5))

    def test_health_banned_list_matches_ge_pin(self):
        # GE shorts/scripts/test_health_terms.py HEALTH_BANNED_SHA256: change both lists and both pins together
        import hashlib
        self.assertEqual(hashlib.sha256("\n".join(SC.HEALTH_BANNED).encode("utf-8")).hexdigest(),
                         "aba6e81a5587883e04fdf2b0fa4c9a5d63aa3ea7c99ecc4b65c0ba4197832bb7")
        for t in ("#Dieta", "#Dietă", "#RekodBeratBadanDiet", "régime"):
            self.assertTrue(SC.health_banned(t), t)

    def test_other_apps_keep_their_keyline(self):
        clip = {"app": "foldparty", "keyline": "ダイエット中でも遊べる、猫ゲーム"}
        self.assertEqual(SC.safe_keyline(clip), clip["keyline"])


if __name__ == "__main__":
    unittest.main()
