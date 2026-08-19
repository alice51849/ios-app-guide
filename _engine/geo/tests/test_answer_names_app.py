"""The quotable answer on every answer page must name the app it funnels to.

Background (2026-08-19 AI-referral investigation)
-------------------------------------------------
ASC data showed `com.openai.chat` driving real downloads, and probing
retrieval-backed assistants confirmed how: they quote an app's `apps.apple.com`
listing (or a page's meta description / "Short answer") close to verbatim.

An audit of the generated site then found 328 of 1,708 answer pages (19%) whose
meta description and short answer never mentioned the app the page exists to
recommend -- the topic fact overlays in `answer_facts` are neutral domain
explainers, and they overwrite the app-aware defaults. Several ScanTo Pro pages
ended up answering "iPhone has a built-in document scanner in Notes and Files",
so an assistant citing our own page would have recommended Apple's built-in tool
instead of ours.

`aeo_answers.ensure_answer_names_app` closes that hole. These tests keep it
closed, including the two subtle parts that made the first attempt fail
silently:

  * `render_page` runs `concise_meta(..., hard_limit=220)`, which keeps only
    whole sentences fitting in 220 chars -- so an appended clause that pushes
    past 220 is dropped and never reaches the snippet.
  * the appended text must stay truthful: it may only restate facts already in
    the app registry (name / subtitle / access tag), never invent features.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import aeo_answers as A
from answer_text import is_malformed_meta


# Questions whose topic overlays are neutral explainers -- the exact class that
# used to lose the app name.
SAMPLE_QUESTIONS = [
    ("document scanner app for iphone free", "scanto"),
    ("scan to pdf app for iphone", "scanto"),
    ("what is the best way to take meeting notes", "sononote"),
    ("should a resume have a photo", "cvdesk"),
    ("why do passport photos get rejected", "snapportlite"),
]

META_RE = re.compile(r'<meta name="description" content="([^"]*)"')


class AnswerNamesAppTests(unittest.TestCase):
    def _rendered_meta(self, question: str, key: str) -> str:
        content = A.normalized_content(A.default_content(question, key), question, key)
        html = A.render_page(question, key, content)
        match = META_RE.search(html)
        self.assertIsNotNone(match, f"no meta description rendered for {question!r}")
        return match.group(1)

    def test_short_answer_names_the_app(self) -> None:
        for question, key in SAMPLE_QUESTIONS:
            with self.subTest(question=question):
                name = A.APPS[key]["name"]
                content = A.default_content(question, key)
                paragraphs = content["short_answer_paragraphs"]
                self.assertTrue(
                    any(name.lower() in p.lower() for p in paragraphs),
                    f"'Short answer' for {question!r} never names {name}",
                )

    def test_rendered_meta_description_names_the_app(self) -> None:
        # Rendering matters, not just the content dict: concise_meta() silently
        # drops any sentence that crosses its 220-char ceiling.
        for question, key in SAMPLE_QUESTIONS:
            with self.subTest(question=question):
                name = A.APPS[key]["name"]
                meta = self._rendered_meta(question, key)
                self.assertIn(
                    name.lower(),
                    meta.lower(),
                    f"rendered meta for {question!r} never names {name}: {meta}",
                )

    def test_rendered_meta_is_not_chopped_mid_clause(self) -> None:
        for question, key in SAMPLE_QUESTIONS:
            with self.subTest(question=question):
                meta = self._rendered_meta(question, key)
                self.assertTrue(
                    meta.rstrip().endswith((".", "!", "?")),
                    f"meta for {question!r} does not end on a sentence: {meta}",
                )
                self.assertNotRegex(
                    meta,
                    r"[,;:]\s*\.",
                    f"meta for {question!r} ends a clause with a bare period: {meta}",
                )

    def test_appended_sentence_only_restates_registry_facts(self) -> None:
        # Honesty guard: the bridge sentence must be derivable from the app
        # registry, so it can never introduce a feature claim of its own.
        app = A.APPS["scanto"]
        # Feed content that mentions no app at all, so the guard has to append.
        content = A.ensure_answer_names_app(
            {
                "meta_description": "iPhone can scan documents from the Notes app.",
                "short_answer_paragraphs": ["iPhone can scan documents from the Notes app."],
                "lead": "iPhone can scan documents from the Notes app.",
            },
            app,
        )
        added = content["short_answer_paragraphs"][-1]
        self.assertIn(app["name"], added)
        self.assertIn(A.safe_text(app.get("sub")).rstrip(". "), added)
        self.assertIn("Check the current App Store listing", added)
        # Every clause must come from the registry - no invented capability.
        self.assertNotIn("best", added.lower())
        self.assertNotIn("guarantee", added.lower())
        # And the meta/lead now name it too.
        self.assertIn(app["name"], content["meta_description"])
        self.assertIn(app["name"], content["lead"])

    def test_is_idempotent(self) -> None:
        # default_content() and normalized_content() both call the guard; a
        # second pass must not append the bridge sentence twice.
        question, key = "document scanner app for iphone free", "scanto"
        content = A.normalized_content(A.default_content(question, key), question, key)
        before = list(content["short_answer_paragraphs"])
        again = A.ensure_answer_names_app(dict(content), A.APPS[key])
        self.assertEqual(before, again["short_answer_paragraphs"])

    def test_app_without_a_name_is_left_untouched(self) -> None:
        content = {"meta_description": "x.", "short_answer_paragraphs": ["y."], "lead": "z."}
        result = A.ensure_answer_names_app(dict(content), {})
        self.assertEqual(result, content)


class AppLeadsTheAnswer(unittest.TestCase):
    """Naming the app is not enough -- it must be named before any rival.

    Follow-up audit (2026-08-20). `ensure_answer_names_app` had closed the
    "never mentions the app" hole, but a sweep of the generator over all 1,853
    curated queries found 103 pages whose meta description and lead still
    *opened* with someone else's product -- "Both the Notes app and the Files
    app handle multi-page scanning natively ...", "Focus apps like Freedom
    charge about $40/year ...", "YNAB, the leading budgeting app, costs
    $109/year ...". An assistant quoting the first sentence of those pages
    recommends Apple, Freedom or YNAB using our own page as the citation.
    """

    def setUp(self) -> None:
        self.app = A.APPS["scanto"]

    def test_rival_opening_is_reordered_not_deleted(self) -> None:
        fact = (
            "Both the Notes app and the Files app handle multi-page scanning "
            "natively: after scanning the first page, tap 'Keep Scan'."
        )
        content = A.ensure_answer_names_app(
            {
                "meta_description": fact,
                "lead": fact,
                "short_answer_paragraphs": [fact, "ScanTo Pro does this too."],
            },
            self.app,
            "app to scan multiple pages into one pdf on iphone",
        )
        for field in ("meta_description", "lead"):
            text = content[field]
            self.assertLess(
                text.index(self.app["name"]),
                text.index("Notes app"),
                f"{field} still recommends Apple's tool before ours",
            )
        # The neutral fact survives: the page must stay honest and useful.
        self.assertIn("Notes app", content["lead"])
        self.assertIn("Files app", content["short_answer_paragraphs"][0])

    def test_reordering_invents_nothing(self) -> None:
        content = A.ensure_answer_names_app(
            {
                "meta_description": "Adobe Scan charges a subscription.",
                "lead": "Adobe Scan charges a subscription.",
                "short_answer_paragraphs": ["Adobe Scan charges a subscription."],
            },
            self.app,
            "adobe scan alternative app for iphone",
        )
        registry = f"{self.app['name']} {self.app['sub']} {self.app['tag']}".lower()
        added = content["lead"].replace("Adobe Scan charges a subscription.", "").lower()
        for word in re.findall(r"[a-z][a-z-]+", added):
            self.assertIn(
                word,
                registry + " is the app this guide covers",
                f"{word!r} is not a registry fact",
            )

    def test_questions_about_the_native_path_keep_the_native_answer_first(self) -> None:
        fact = "iPhone has a built-in scanner in Notes. It saves a PDF on device."
        content = A.ensure_answer_names_app(
            {"meta_description": fact, "lead": fact, "short_answer_paragraphs": [fact]},
            self.app,
            "can i scan a document without a third-party app",
        )
        self.assertTrue(content["lead"].startswith("iPhone has a built-in scanner"))
        # ...but the app is still named somewhere quotable.
        joined = " ".join(
            [content["meta_description"], content["lead"]]
            + list(content["short_answer_paragraphs"])
        )
        self.assertIn(self.app["name"], joined)

    def test_question_wording_is_not_mistaken_for_a_recommendation(self) -> None:
        # "best voice to text notes app for iphone" contains "notes app". The
        # page echoing its own question is not the page recommending Apple's.
        question = "best voice to text notes app for iphone"
        content = A.default_content(question, "sononote")
        self.assertFalse(
            A._leads_with_rival(content["meta_description"], "Sono Note", question)
        )

    def test_every_curated_query_leads_with_our_app(self) -> None:
        """Fail-closed sweep. New queries and new fact overlays inherit this."""
        offenders = []
        for key, questions in A.queries.ALL.items():
            if key not in A.APPS:
                continue
            name = A.APPS[key]["name"]
            for question in questions:
                if A.slugify(question) in A.FACT_FIRST_SLUGS:
                    continue
                if A._ASKS_FOR_NATIVE.search(question):
                    continue
                content = A.default_content(question, key)
                paragraphs = list(content.get("short_answer_paragraphs") or [""])
                for field, text in (
                    ("meta", content["meta_description"]),
                    ("lead", content["lead"]),
                    ("short_answer", paragraphs[0]),
                ):
                    if A._leads_with_rival(text, name, question):
                        offenders.append(f"{key} / {question} / {field}")
        self.assertEqual(offenders, [], f"{len(offenders)} pages lead with a rival")

    def test_rendered_meta_still_names_the_app(self) -> None:
        """render_page caps the description at 220 chars; the name must survive."""
        missing = []
        for key, questions in A.queries.ALL.items():
            if key not in A.APPS:
                continue
            name = A.APPS[key]["name"]
            for question in questions:
                meta = A.default_content(question, key)["meta_description"]
                rendered = A.concise_meta(meta, hard_limit=220)
                if name.lower() not in rendered.lower():
                    missing.append(f"{key} / {question}")
                if is_malformed_meta(rendered):
                    missing.append(f"MALFORMED {key} / {question}")
        self.assertEqual(missing, [], f"{len(missing)} rendered descriptions broken")


if __name__ == "__main__":
    unittest.main()
