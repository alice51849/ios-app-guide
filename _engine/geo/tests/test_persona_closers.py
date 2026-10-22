#!/usr/bin/env python3
"""Regression tests for the persona closing sentences.

The retired formula ("<problem> — <App> is built for this.") was translated
once and reused for every app, which made the publisher intent catalog -- and
every social post built from it -- close on the same cadence 1,300 times.
These tests keep the replacement honest: real coverage of all 50 store
locales, no em-dash tic, deterministic assignment, and never a decision
context shorter than the catalog schema allows.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from answer_personas import PERSONAS  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
import persona_closers  # noqa: E402


class PersonaCloserTests(unittest.TestCase):
    def test_self_check_passes(self):
        persona_closers.self_check()

    def test_every_store_locale_is_written_natively(self):
        self.assertEqual(50, len(OFFICIAL_LOCALES))
        self.assertEqual(set(OFFICIAL_LOCALES), set(persona_closers.CLOSERS))
        written = {s for s in persona_closers.SHAPES if s != "none"}
        self.assertEqual(4, len(written) - 1)  # at least four alternatives
        for locale, phrases in persona_closers.CLOSERS.items():
            self.assertEqual(written, set(phrases), locale)
            for shape, text in phrases.items():
                self.assertIn("{name}", text, f"{locale}/{shape}")
                self.assertEqual(1, text.count("{name}"), f"{locale}/{shape}")

    def test_no_locale_reuses_another_locales_wording(self):
        """A translated-once phrasebook would repeat one string across locales."""
        for shape in (s for s in persona_closers.SHAPES if s != "none"):
            texts = [p[shape] for p in persona_closers.CLOSERS.values()]
            # The four English storefronts legitimately share some wording;
            # everything else must be distinct.
            self.assertGreaterEqual(len(set(texts)), len(texts) - 6, shape)

    def test_em_dash_tic_never_returns(self):
        for locale, phrases in persona_closers.CLOSERS.items():
            for shape, text in phrases.items():
                self.assertNotIn("—", text, f"{locale}/{shape}")
                self.assertNotIn("–", text, f"{locale}/{shape}")

    def test_shape_assignment_is_deterministic_and_spread(self):
        keys = sorted(persona_closers.SITUATIONS)
        first = [persona_closers.shape_for(k) for k in keys]
        second = [persona_closers.shape_for(k) for k in keys]
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(set(first)), 4)
        # No single shape may swallow the portfolio.
        for shape in set(first):
            self.assertLess(first.count(shape) / len(first), 0.4, shape)

    def test_every_persona_app_has_a_situation(self):
        for key in PERSONAS:
            self.assertIn(
                key,
                persona_closers.SITUATIONS,
                f"{key} has no situation; it would fall back to 'utility'",
            )

    def test_close_lead_respects_the_catalog_schema_floor(self):
        floor = persona_closers.MIN_DECISION_CONTEXT_CHARS
        short_heads = {
            "zh-Hant": "孩子总是动",
            "ja": "子供は動く",
            "en-US": "Kids move",
        }
        for key in sorted(persona_closers.SITUATIONS):
            for locale, head in short_heads.items():
                text = persona_closers.close_lead(locale, head, key, "Snapport")
                self.assertGreaterEqual(len(text), floor, f"{key}/{locale}")

    def test_persona_lead_drops_the_legacy_tail(self):
        for key, entries in PERSONAS.items():
            lead = persona_closers.persona_lead(
                entries[0]["lead"], key, "Example App"
            )
            self.assertNotIn("is built for this", lead, key)
            self.assertNotIn("— Example App", lead, key)

    def test_join_uses_the_locales_own_sentence_spacing(self):
        self.assertEqual(
            "Kids move. That is why Snapport exists.",
            persona_closers.join("en-US", "Kids move", "That is why Snapport exists."),
        )
        self.assertEqual(
            "孩子一直動。所以才有了 Snapport。",
            persona_closers.join(
                "zh-Hant", "孩子一直動", "所以才有了 Snapport。"
            ),
        )
        self.assertEqual(
            "head", persona_closers.join("en-US", "head", "")
        )


if __name__ == "__main__":
    unittest.main(verbosity=1)
